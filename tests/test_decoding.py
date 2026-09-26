import numpy as np
import pytest
import stim
import pymatching
from knill_bench.decoding.dem import convert_dem
from knill_bench.adapters.decoders import GlobalBPLSD,MatchingAdapter,NonmatchableModel,construct
from knill_bench.adapters.hex_native import NativeHex,TRANSITIONS
from knill_bench.config import load,grid
from knill_bench.circuits.builders import build


def test_dem_event_semantics():
    dem=stim.DetectorErrorModel('''
    error(0.1) D0 D1 ^ D1 D2 L0
    error(0.2) D0 D2 L0
    error(0.3) D0 D2
    error(0.4) L0
    error(0.01) D0 D0
    repeat 2 {
        error(0.05) D0 D1
        shift_detectors 2
    }
    ''')
    model=convert_dem(dem)
    assert model.h.shape==(4,5)
    assert model.trivial_events==1
    assert np.isclose(model.q[0],.26)
    assert model.h[:,0].toarray().ravel().tolist()==[1,0,1,0]
    assert model.l[:,0].toarray()[0,0]==1 and model.l[:,1].toarray()[0,0]==0
    assert model.h[:,2].nnz==0 and model.l[:,2].nnz==1
    s,o,_=dem.compile_sampler(seed=123).sample(1000,return_errors=True)
    # Independent merged DEM sampler has matching supports; verify unmerged sample algebra exactly.
    raw=convert_dem(dem,merge=False)
    _,_,faults=dem.compile_sampler(seed=123).sample(1000,return_errors=True)
    # Fully trivial event occupies its own sampler column; manually include its zero column.
    full_events=[]
    for op in dem.flattened():
        if op.type=='error':full_events.append(op)
    h=[];l=[]
    for op in full_events:
        one=stim.DetectorErrorModel(str(op));m=convert_dem(one)
        hv=np.zeros(dem.num_detectors,dtype=np.uint8);lv=np.zeros(dem.num_observables,dtype=np.uint8)
        if m.q.size:
            hv[:m.h.shape[0]]=m.h.toarray()[:,0];lv[:m.l.shape[0]]=m.l.toarray()[:,0]
        h.append(hv);l.append(lv)
    assert np.array_equal(faults@np.array(h)%2,s)
    assert np.array_equal(faults@np.array(l)%2,o)


def test_undetectable_logical_prior_and_zero_faults():
    decoder=GlobalBPLSD(stim.DetectorErrorModel('error(0.8) L0\ndetector D0'),dict(kind='bplsd_global'))
    r=decoder.decode_batch(np.array([[0],[1]],dtype=np.uint8))
    assert r.logical_flips[:,0].tolist()==[1,1]
    assert r.valid.tolist()==[True,False]
    empty=GlobalBPLSD(stim.DetectorErrorModel('detector D0\nlogical_observable L0'),dict(kind='bplsd_global'))
    r=empty.decode_batch(np.zeros((2,1),dtype=np.uint8))
    assert r.valid.all() and not r.logical_flips.any()


def test_same_circuit_matching_and_mapping():
    cfg=load('configs/smoke.yaml');case=next(grid(cfg));c=build(case);c.metadata['basis']=case['basis']
    s,o=c.circuit.compile_detector_sampler(seed=99).sample(128,separate_observables=True)
    adapter=MatchingAdapter(c,'pymatching')
    trusted=pymatching.Matching.from_detector_error_model(c.circuit.detector_error_model(decompose_errors=True))
    assert np.array_equal(adapter.decode_batch(s).logical_flips,trusted.decode_batch(s))
    lom=MatchingAdapter(c,'lomatching')
    ids=lom.metadata['selected_detectors']
    assert all(c.detectors[i]['sector']==case['basis'] for i in ids)
    assert np.array_equal(lom.decode_batch(s).logical_flips,trusted.decode_batch(s))


def test_controlled_nonmatchable_fallback_and_no_invalid_circuit_fallback():
    from knill_bench.models import CompiledExperiment
    circuit=stim.Circuit('R 0\nX_ERROR(.1) 0\nM 0\nDETECTOR rec[-1]\nDETECTOR rec[-1]\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]')
    c=CompiledExperiment(circuit,circuit.detector_error_model(),[],[dict(sector='x')]*3,[0],{'basis':'x'})
    cfg={'decoders':{'lom':{'kind':'lomatching','on_nonmatchable':'bplsd_global','fallback_decoder':'lsd'},'lsd':{'kind':'bplsd_global'}}}
    decs,aliases,details=construct(c,{'decoders':['lom','lsd']},cfg)
    assert len(decs)==1 and aliases['lom']=='lsd' and details['lom']['fallback_reason']
    bad=stim.Circuit('RX 0\nM 0\nDETECTOR rec[-1]')
    c.circuit=bad
    with pytest.raises(ValueError,match='non-deterministic'):
        construct(c,{'decoders':['lom']},cfg)


@pytest.mark.parametrize('basis',['x','z'])
def test_native_original_pipeline_same_raw_samples(basis,monkeypatch):
    from hex_qec.protocols.knill_online_offline import knill_online_offline
    import hex_qec.protocols.knill_online_offline as module
    from hex_qec.modularisation import modularised_circuit
    cfg=load('configs/smoke.yaml')
    case=next(c for c in grid(cfg) if c['protocol']=='knill_hex_dminus2' and c['basis']==basis and c['cycles']==2 and c['distance']==5)
    c=build(case);native=NativeHex(case,c)
    original_simulate=modularised_circuit.simulate
    def capture(engine,*args,**kwargs):
        # Compare exact raw sampler results and final error count using the legacy engine.
        raw=engine.circuit.compile_sampler(seed=432).sample(256)
        syndromes,obs=c.circuit.compile_m2d_converter().convert(measurements=raw,separate_observables=True)
        prediction=native.decode_batch(syndromes,raw)
        assert prediction.valid.all()
        assert sum(e['phase'].startswith('backend_') for e in native.events)==21
        expected=int(np.any(prediction.logical_flips!=obs,axis=1).sum())
        shots,errors=original_simulate(engine,256,10000,seed=432)
        assert shots==256 and errors==expected
        return shots,errors
    monkeypatch.setattr(modularised_circuit,'simulate',capture)
    from knill_bench.codes import Code
    shots,errors=knill_online_offline(Code.rotated(5).matrices,3,pymatching.Matching.from_check_matrix,pymatching.Matching.from_check_matrix,True,.001,256,10000,basis,2,surface_code=True,seed=432)
    assert shots==256


def test_physical_fault_insertion_and_noisy_native():
    from knill_bench.decoding.audit import insert_fault
    circuit=stim.Circuit('R 0\nX_ERROR(.01) 0\nM 0\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-1]')
    fault=circuit.explain_detector_error_model_errors()[0].circuit_error_locations[0]
    injected=insert_fault(circuit,[fault])
    s,o=injected.compile_detector_sampler(seed=1).sample(2,separate_observables=True)
    # Fault is now a deterministic Pauli gate; compare raw records with original converter.
    raw=injected.compile_sampler(seed=1).sample(2)
    s,o=circuit.compile_m2d_converter().convert(measurements=raw,separate_observables=True)
    assert s.all() and o.all()
    cfg=load('configs/smoke.yaml')
    case=next(c for c in grid(cfg) if c['protocol']=='knill_hex_dminus2')
    case['initial_boundary']={'kind':'noisy_preparation'}
    c=build(case);native=NativeHex(case,c)
    raw=c.circuit.without_noise().compile_sampler(seed=8).sample(8)
    s,o=c.circuit.compile_m2d_converter().convert(measurements=raw,separate_observables=True)
    r=native.decode_batch(s,raw)
    assert r.valid.all() and np.array_equal(r.logical_flips,o)


def test_native_uses_local_cached_transitions_across_cycles_and_p():
    cfg=load('configs/smoke.yaml')
    case=next(c for c in grid(cfg) if c['protocol']=='knill_hex_dminus2'
              and c['distance']==3 and c['cycles']==2 and c['basis']=='z')
    TRANSITIONS.clear()
    compiled=build(case);native=NativeHex(case,compiled)
    first_keys=set(TRANSITIONS)
    assert first_keys
    assert native.metadata['global_correction_map'] is False
    assert all(not hasattr(m,'correction_to_measurement_flips')
               for m in native.engine.circuit_modules)
    # Same-shaped per-cycle modules share the exact immutable transition.
    assert native.transitions[1] is native.transitions[5]
    assert native.transitions[2] is native.transitions[6]
    changed=dict(case,p=case['p']*2)
    changed['rates']={k:changed['p']*v for k,v in
                      case['noise'].get('multipliers',dict(p1=0,p2=1,reset=1,measurement=1,idle=0)).items()}
    NativeHex(changed,build(changed))
    assert set(TRANSITIONS)==first_keys
