from collections import Counter
import pytest
import numpy as np
from knill_bench.config import load,grid
from knill_bench.circuits.builders import build
from knill_bench.codes import Code


@pytest.mark.parametrize('distance',[3,5])
@pytest.mark.parametrize('basis',['x','z'])
@pytest.mark.parametrize('cycles',[1,2])
@pytest.mark.parametrize('protocol',['se_memory','knill_hex_dminus2','knill_aft_postgate','knill_aft_prep_only'])
def test_boundaries_ledger_counts(distance,basis,cycles,protocol):
    case=dict(distance=distance,basis=basis,cycles=cycles,protocol=protocol,prep_rounds=distance-2 if protocol=='knill_hex_dminus2' else 1,
              post_gate_rounds=int(protocol=='knill_aft_postgate'),post_gate_scope='all_active',noise={'profile':'hex_legacy'},p=0,initial_boundary={'kind':'ideal_encoded'})
    c=build(case)
    m=c.circuit.compile_sampler(seed=123).sample(32)
    s,o=c.circuit.compile_m2d_converter().convert(measurements=m,separate_observables=True)
    assert not s.any() and not o.any()
    assert len(c.ledger)==c.circuit.num_measurements
    assert c.dem.num_observables==1
    import stim
    assert c.circuit.has_all_flows([stim.Flow(measurements=d['records']) for d in c.detectors]+[stim.Flow(measurements=c.observable_records)])
    counts=c.metadata['se_counts']
    if protocol=='se_memory':assert counts=={'0:memory':cycles}
    else:
        for j in range(cycles):
            for b in (2*j+1,2*j+2):assert counts[f'{b}:preparation']==case['prep_rounds']
        assert sum(v for k,v in counts.items() if k.endswith(':post_gate'))==(6*cycles if case['post_gate_rounds'] else 0)
        random_bell=[r['record'] for r in c.ledger if r['operation']=='bell']
        assert np.any(m[:,random_bell].std(axis=0)>0)
    assert c.metadata['elapsed_time'] is None


def test_noise_location_and_hook_order():
    cfg=load('configs/smoke.yaml');case=next(grid(cfg));c=build(case)
    names={op.name for op in c.circuit}
    assert 'DEPOLARIZE2' in names and 'DEPOLARIZE1' not in names
    assert not any(op.name=='TICK' for op in c.circuit)
    code=Code.rotated(5)
    from hex_qec.circuit_generation.circuit_generation import measure_X_stabilizers_surface_code,measure_Z_stabilizers_surface_code
    import stim
    for sector,fn in enumerate((measure_X_stabilizers_surface_code,measure_Z_stabilizers_surface_code)):
        frag=stim.Circuit();fn(frag,code.stabilizers[sector],code.template,0)
        for check in range(code.matrices[sector].shape[0]):
            support=code.matrices[sector].getrow(check).indices.tolist()
            anc=code.template['x_ancillas' if sector==0 else 'z_ancillas'][check]
            actual=[]
            for op in frag:
                if op.name in {'CX','CZ'}:
                    qs=[t.value for t in op.targets_copy()]
                    actual.extend(qs[k+1] for k in range(0,len(qs),2) if qs[k]==anc)
            expected=support if sector==0 or len(support)==2 else [support[i] for i in (0,2,1,3)]
            assert actual==expected


def test_noisy_boundary_explicit_schedule():
    cfg=load('configs/smoke.yaml');cfg['protocols']=[p for p in cfg['protocols'] if p['id']!='knill_hex_dminus2']
    cfg['experiment']['initial_boundary']={'kind':'noisy_preparation'}
    cfg['noise']=dict(profile='explicit',multipliers=dict(p1=1,p2=1,reset=1,measurement=1,idle=.1),durations=dict(p1=1,p2=2,reset=2,measurement=3),time_unit='gate_unit',preparation_schedule='serial_wait')
    from knill_bench.config import resolve
    for case in list(grid(resolve(cfg)))[:3]:
        c=build(case)
        assert c.metadata['se_counts']['0:initial_boundary']==case['distance']
        schedule=c.metadata['physical_schedule']
        assert c.metadata['elapsed_time']==sum(r['duration'] for r in schedule)
        assert c.metadata['spacetime_volume']>0
        assert all('preparation' not in k for k in c.metadata['se_counts'] if k.startswith('0:'))
        assert not c.circuit.without_noise().compile_detector_sampler(seed=1).sample(8,append_observables=True).any()


def test_invalid_distances():
    for d in (1,2,4,3.0,True):
        with pytest.raises(ValueError):Code.rotated(d)
