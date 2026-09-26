"""Small upstream reference checks, kept separate from the rotated comparison."""
import numpy as np
import pymatching
import stim
from scipy.sparse import csc_matrix
from ldpc.bplsd_decoder import BpLsdDecoder
from hex_qec.protocols.knill_online_offline import knill_online_offline
from knill_bench.codes import Code


def native_reference():
    return knill_online_offline(Code.rotated(3).matrices,1,pymatching.Matching.from_check_matrix,
        pymatching.Matching.from_check_matrix,True,.001,256,10000,'z',1,surface_code=True,seed=321)


def lom_reference():
    from surface_sim.models import CircuitNoiseModel
    from surface_sim import Detectors
    from surface_sim.experiments import experiment_from_circuit
    from surface_sim.circuit_blocks.unrot_surface_code_css import gate_to_iterator
    from surface_sim.layouts import unrot_surface_codes
    from lomatching import MoMatching
    logical=stim.Circuit('RX 0\nR 1\nTICK\nCX 0 1\nMX 0 1\nOBSERVABLE_INCLUDE(0) rec[-1] rec[-2]')
    layouts=unrot_surface_codes(2,distance=3)
    detectors=Detectors.from_layouts(*layouts,frame='pre-gate')
    model=CircuitNoiseModel.from_layouts(*layouts)
    model.setup.set_var_param('prob',1e-3)
    circuit=experiment_from_circuit(logical,layouts,model,detectors,gate_to_iterator,anc_reset=True)
    coords=[{p:[v for k,v in layout.anc_coords.items() if k[0]==p] for p in ('X','Z')} for layout in layouts]
    decoder=MoMatching.from_circuit(circuit,coords,allow_gauge_detectors=False)
    s,o=circuit.compile_detector_sampler(seed=321).sample(32,separate_observables=True)
    predictions=decoder.decode_batch(s)
    # Count physical measurement operations on each layout's check qubits.
    per_block=[]
    for layout in layouts:
        anc={layout.qubit_inds[q] for q in layout.anc_qubits}
        count=sum(sum(t.value in anc for t in op.targets_copy()) for op in circuit.flattened() if op.name in {'M','MX','MR','MRX'})
        per_block.append(dict(check_measurements=count,checks=len(anc),se_rounds=count/len(anc)))
    return dict(shots=32,errors=int(np.any(o!=predictions,axis=1).sum()),detectors=circuit.num_detectors,
                check_measurements=per_block,logical_ticks=1,physical_ticks=sum(op.name=='TICK' for op in circuit.flattened()))


def bp_reference():
    h=csc_matrix(np.array([[1,1,0],[0,1,1]],dtype=np.uint8))
    decoder=BpLsdDecoder(h,error_channel=[.01,.02,.01],max_iter=20,bp_method='minimum_sum',ms_scaling_factor=.75,schedule='parallel',lsd_method='LSD_0',lsd_order=0)
    outcomes=[]
    for syndrome in ([0,0],[1,0],[0,1],[1,1]):
        correction=decoder.decode(np.array(syndrome,dtype=np.uint8))
        assert np.array_equal(h@correction%2,syndrome)
        outcomes.append(dict(syndrome=syndrome,correction=correction.tolist(),bp_converged=bool(decoder.converge),iterations=int(decoder.iter)))
    return outcomes
