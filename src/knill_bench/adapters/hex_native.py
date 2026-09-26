"""Native Hex decoding using cached module-local Pauli-frame transitions."""
from dataclasses import dataclass
from time import perf_counter_ns,process_time_ns
import re
import numpy as np
import pymatching
from scipy.sparse import csc_matrix
import stim
from hex_qec.circuit_generation.circuit_generation import noiseless_unitary_state_prep
from hex_qec.modularisation import (css_detector_module,logical_measurement_module,
    measurement_module,modularised_circuit,no_measurement_module)
from hex_qec.modularisation.module_generation import (generate_state_prep_modules,
    generate_transversal_cnot_module,generate_bell_measurement_and_correction_module,
    generate_logical_measurement_module)
from knill_bench.codes import Code
from knill_bench.models import Predictions

PAULI=re.compile(r'([IXYZ])(\d+)')
TRANSITIONS={}

class TimedMatching:
    def __init__(self,owner,backend):self.owner=owner;self.backend=backend
    def decode_batch(self,syndromes):
        w=perf_counter_ns();c=process_time_ns();result=self.backend.decode_batch(syndromes)
        if getattr(self.owner,'record_calls',False):
            self.owner.events.append(dict(phase='backend_'+self.owner.current_role,
                wall_ns=perf_counter_ns()-w,cpu_ns=process_time_ns()-c,batch_size=len(syndromes),
                input_size=syndromes.shape[1],module_index=self.owner.current_module))
        return result

@dataclass(frozen=True)
class LocalTransition:
    # shape of x/z: (decoder correction variables, qubits in module support)
    x:np.ndarray
    z:np.ndarray

class PackedFrame:
    """Pauli frame with the shot axis packed into bytes."""
    def __init__(self,qubits,shots):
        self.shots=shots;self.x=np.zeros((qubits,(shots+7)//8),np.uint8);self.z=np.zeros_like(self.x)
    def advance(self,circuit):
        out=[]
        for op in circuit.without_noise():
            name=op.name;qs=[t.value for t in op.targets_copy() if t.is_qubit_target]
            if name in {'DETECTOR','OBSERVABLE_INCLUDE','QUBIT_COORDS','TICK','I'}:continue
            if name=='H':old=self.x[qs].copy();self.x[qs]=self.z[qs];self.z[qs]=old
            elif name=='CX':
                for c,t in zip(qs[::2],qs[1::2]):self.x[t]^=self.x[c];self.z[c]^=self.z[t]
            elif name=='CZ':
                for a,b in zip(qs[::2],qs[1::2]):self.z[a]^=self.x[b];self.z[b]^=self.x[a]
            elif name in {'R','RX'}:self.x[qs]=0;self.z[qs]=0
            elif name in {'M','MR'}:
                out.extend(self.x[q].copy() for q in qs)
                if name=='MR':self.x[qs]=0;self.z[qs]=0
            elif name in {'MX','MRX'}:
                out.extend(self.z[q].copy() for q in qs)
                if name=='MRX':self.x[qs]=0;self.z[qs]=0
            else:raise ValueError(f'unsupported operation in packed Pauli frame: {name}')
        if not out:return np.zeros((self.shots,0),bool)
        return np.unpackbits(np.asarray(out,np.uint8),axis=1,count=self.shots,bitorder='little').T.astype(bool,copy=False)
    def apply(self,corrections,transition,support):
        # Dense multiplication is local (O(shots * one block)), then packed.
        for frame,matrix in ((self.x,transition.x),(self.z,transition.z)):
            local=np.asarray(corrections@matrix%2,dtype=np.uint8)
            frame[support]^=np.packbits(local.T,axis=1,bitorder='little')

def _circuit_key(circuit,support):
    rel={q:i for i,q in enumerate(support)}
    def target(t):return ('q',rel[t.value]) if t.is_qubit_target else ('r',str(t))
    return tuple((op.name,tuple(op.gate_args_copy()),tuple(target(t) for t in op.targets_copy()))
                 for op in circuit.without_noise())

def _correction_key(corrections,support):
    rel={q:i for i,q in enumerate(support)}
    return tuple((tuple((p,rel[int(q)]) for p,q in PAULI.findall(s)),loc) for s,loc in corrections)

def _sparse_key(m):
    m=m.tocsr();return m.shape,tuple(m.indptr),tuple(m.indices),tuple(np.asarray(m.data,dtype=np.uint8)&1)

def _end_frames(circuit,corrections,after):
    n=len(corrections)
    if not n:return np.zeros((0,circuit.num_qubits),bool),np.zeros((0,circuit.num_qubits),bool)
    sim=stim.FlipSimulator(batch_size=n,num_qubits=circuit.num_qubits,disable_stabilizer_randomization=True)
    at={}
    for k,(p,loc) in enumerate(corrections):at.setdefault(loc,[]).append((k,p))
    def inject(items):
        for k,s in items:
            for p,q in PAULI.findall(s):sim.set_pauli_flip(p,qubit_index=int(q),instance_index=k)
    for loc,op in enumerate(circuit):
        if not after:inject(at.get(loc,()))
        g=stim.gate_data(op.name)
        if not(g.is_noisy_gate and not g.produces_measurements):sim.do(op)
        if after:inject(at.get(loc,()))
    inject(at.get(len(circuit),()))
    x,z,_,_,_=sim.to_numpy(transpose=True,output_xs=True,output_zs=True)
    return x,z

def _restrict(x,z,support):
    outside=np.ones(x.shape[1],bool);outside[support]=False
    if x[:,outside].any() or z[:,outside].any():raise ValueError('local correction escaped support')
    return LocalTransition(x[:,support].astype(bool),z[:,support].astype(bool))

def _transition(module,support):
    if isinstance(module,css_detector_module):
        key=('css',_circuit_key(module.x_det_circuit,support),_circuit_key(module.z_det_circuit,support),
            _correction_key(module.x_correction_array,support),_correction_key(module.z_correction_array,support),
            _sparse_key(module.x_dem_hyperedge_to_edge),_sparse_key(module.z_dem_hyperedge_to_edge))
        if key not in TRANSITIONS:
            xx,xz=_end_frames(module.x_det_circuit,module.x_correction_array,True)
            zx,zz=_end_frames(module.z_det_circuit,module.z_correction_array,True)
            xx=np.asarray(module.x_dem_hyperedge_to_edge@xx,dtype=np.uint8)&1
            xz=np.asarray(module.x_dem_hyperedge_to_edge@xz,dtype=np.uint8)&1
            zx=np.asarray(module.z_dem_hyperedge_to_edge@zx,dtype=np.uint8)&1
            zz=np.asarray(module.z_dem_hyperedge_to_edge@zz,dtype=np.uint8)&1
            nq=module.num_data_qubits;n=module.circuit.num_qubits;data=module.new_support[:nq]
            rx=np.zeros((nq,n),bool);rz=np.zeros((nq,n),bool)
            rx[np.arange(nq),data]=1;rz[np.arange(nq),data]=1
            TRANSITIONS[key]=_restrict(np.vstack((xx,zx,np.zeros_like(rx),rx)),
                np.vstack((xz,zz,rz,np.zeros_like(rz))),support)
        return TRANSITIONS[key]
    if isinstance(module,measurement_module):
        key=('measurement',_circuit_key(module.circuit,support),_correction_key(module.correction_array,support))
        if key not in TRANSITIONS:
            TRANSITIONS[key]=_restrict(*_end_frames(module.circuit,module.correction_array,False),support)
        return TRANSITIONS[key]
    return None

class NativeHex:
    kind='hex_native_pipeline'
    def __init__(self,case,compiled):
        code=Code.rotated(case['distance']);blocks=code.blocks(2*case['cycles']+1)
        pcm=code.matrices;p=case['p'];basis=case['basis'];self.events=[];self.record_calls=False
        def generator(*a,**kw):return TimedMatching(self,pymatching.Matching.from_check_matrix(*a,**kw))
        modules=[];roles=[];supports=[]
        if case['initial_boundary']['kind']=='ideal_encoded':
            c=stim.Circuit();c.append('R',blocks[0]['data_qubits']);c+=noiseless_unitary_state_prep(pcm,basis,0)
            modules.append(no_measurement_module(c,blocks[0]['data_qubits']));roles.append('initial');supports.append(blocks[0]['data_qubits'])
        else:
            s=sum((blocks[0][k] for k in ('data_qubits','x_ancillas','z_ancillas')),[])
            modules+=generate_state_prep_modules(pcm,case['distance'],basis,p,[s],generator,matchable=True,surface_code=True)
            roles.append('offline_initial');supports.append(s)
        zs=[sum((blocks[2*j+1][k] for k in ('data_qubits','x_ancillas','z_ancillas')),[]) for j in range(case['cycles'])]
        xs=[sum((blocks[2*j+2][k] for k in ('data_qubits','x_ancillas','z_ancillas')),[]) for j in range(case['cycles'])]
        # Construct each same-shaped decoder/template once, then remap its copies.
        zm=generate_state_prep_modules(pcm,case['prep_rounds'],'z',p,zs,generator,matchable=True,surface_code=True)
        xm=generate_state_prep_modules(pcm,case['prep_rounds'],'x',p,xs,generator,matchable=True,surface_code=True)
        for j in range(case['cycles']):
            a,b,d=2*j+1,2*j+2,2*j
            for m,r,s in ((zm[j],'offline_z',zs[j]),(xm[j],'offline_x',xs[j])):modules.append(m);roles.append(r);supports.append(s)
            s=blocks[b]['data_qubits']+blocks[a]['data_qubits'];modules.append(generate_transversal_cnot_module(p,*[blocks[q]['data_qubits'] for q in (b,a)]));roles.append('gate');supports.append(s)
            s=blocks[d]['data_qubits']+blocks[a]['data_qubits']+blocks[b]['data_qubits']
            modules.append(generate_bell_measurement_and_correction_module(pcm,p,*[blocks[q]['data_qubits'] for q in (d,a,b)],generator));roles.append('bell');supports.append(s)
        modules.append(generate_logical_measurement_module(pcm,p,basis,blocks[-1]['data_qubits'],generator));roles.append('final_readout');supports.append(blocks[-1]['data_qubits'])
        self.engine=modularised_circuit(modules);self.roles=roles;self.supports=supports
        self.transitions=[_transition(m,s) for m,s in zip(modules,supports)]
        self.converter=self.engine.circuit.compile_m2d_converter();self.observable_records=compiled.observable_records
        self.metadata=dict(prior_policy='legacy',offline_matchable=True,output_kind='logical_observable_flip_predictions',
            frame_semantics='cached_local_numpy_pauli_frame',prior_noise_profile='hex_legacy_at_sweep_p',
            sampling_noise_profile=case['noise']['profile'],timing_instrumentation='nested backend calls; timestamp overhead included in module/terminal totals',
            measurement_records=self.engine.circuit.num_measurements,local_transition_cache=True,global_correction_map=False)
        if self.engine.circuit.num_measurements!=compiled.circuit.num_measurements:raise ValueError('native and shared measurement ledgers differ')
        def physical(c):
            if case['noise']['profile']=='explicit':c=c.without_noise()
            out=stim.Circuit()
            for op in c.flattened():
                if op.name not in {'DETECTOR','OBSERVABLE_INCLUDE','QUBIT_COORDS','TICK','I'}:out.append({'MRX':'MX','MR':'M'}.get(op.name,op.name),op.targets_copy(),op.gate_args_copy())
            return str(out)
        if physical(self.engine.circuit)!=physical(compiled.circuit):raise ValueError('native and shared quantum circuits differ beyond retired/reset-redundant qubits')

    def decode_batch(self,syndromes,measurements=None):
        if measurements is None:raise ValueError('native Hex requires raw measurements')
        raw=np.asarray(measurements,dtype=bool);records=raw.copy();shots=len(raw);offset=0;corrected=None
        frame=PackedFrame(self.engine.circuit.num_qubits,shots)
        self.events=[];self.record_calls=True
        for idx,(m,role,support,tr) in enumerate(zip(self.engine.circuit_modules,self.roles,self.supports,self.transitions)):
            flips=frame.advance(m.circuit);n=m.num_measurements
            if n:local=np.logical_xor(raw[:,offset:offset+n],flips);records[:,offset:offset+n]=local
            if isinstance(m,logical_measurement_module):
                self.current_role=role;self.current_module=idx;w=perf_counter_ns();c=process_time_ns();corrected=np.asarray(m.c_func(local),dtype=np.uint8)
                self.events.append(dict(phase=role,wall_ns=perf_counter_ns()-w,cpu_ns=process_time_ns()-c,batch_size=shots,input_size=n,module_index=idx))
            elif tr is not None:
                self.current_role=role;self.current_module=idx;w=perf_counter_ns();c=process_time_ns();corr=np.asarray(m.c_func(local),dtype=np.uint8)
                self.events.append(dict(phase=role,wall_ns=perf_counter_ns()-w,cpu_ns=process_time_ns()-c,batch_size=shots,input_size=n,module_index=idx));w=perf_counter_ns();c=process_time_ns()
                frame.apply(corr,tr,support)
                if isinstance(m,css_detector_module):
                    nx=m.x_dem_check_matrix.shape[1];nz=m.z_dem_check_matrix.shape[1]
                    update=(csc_matrix(corr[:,:nx])@m.x_dem_correction_to_local_measurement_flips+csc_matrix(corr[:,nx:nx+nz])@m.z_dem_correction_to_local_measurement_flips).toarray()%2
                    records[:,offset:offset+n]^=update.astype(bool)
                self.events.append(dict(phase='frame_propagation',wall_ns=perf_counter_ns()-w,cpu_ns=process_time_ns()-c,batch_size=shots,input_size=n,module_index=idx))
            offset+=n
        residual=self.converter.convert(measurements=records,separate_observables=True)[0].sum(axis=1)
        parity=np.bitwise_xor.reduce(raw[:,self.observable_records],axis=1).astype(np.uint8)
        return Predictions(corrected^parity[:,None],residual==0,residual.astype(int).tolist())
    def decode_one(self,syndrome,measurements=None):return self.decode_batch(syndrome[None,:],measurements[None,:])
