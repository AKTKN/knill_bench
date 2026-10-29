"""Independent finite fixtures and saved-report contracts; physical batches <=7."""
from dataclasses import replace
from itertools import product
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import stim
import yaml
from scipy.sparse import csc_matrix

from knill_bench.analysis.preparation_report import from_shots,check_summary,interval,analyze_saved
from knill_bench.analysis.preparation_validation import spatial_escape_example,temporal_path,validate_witness,unpack
from knill_bench.circuits.preparation import build_preparation
from knill_bench.codes import Code
from knill_bench.decoding.temporal_matching import TemporalMatching
from knill_bench.simulation.preparation_metrics import paired_counts
from knill_bench.simulation.runner import prepare,execute_run


def test_independent_exhaustive_spatial_escape_and_readout_only_hand_costs():
    example=spatial_escape_example();h=csc_matrix(example['h_online']);p=np.array(example['past']);f=np.array(example['future'])
    with pytest.raises(ValueError,match='open endpoint'):temporal_path(h,p,f,np.array(example['unfrozen']))
    assert temporal_path(h,p,f,np.array(example['fixed']))==[0,1]
    core=TemporalMatching(h,p,f,example['frozen_columns'],example['weights'])
    errors=np.array(list(product((0,1),repeat=4)),dtype=np.uint8);costs=errors@np.array(example['weights'])
    for syndrome in (0,1):
        result=core.decode_batch([[syndrome]],return_errors=True)
        feasible=(errors@h.T.toarray()).ravel()%2==syndrome
        baseline=result.baseline_errors[0]
        opposite=feasible & np.all(errors[:,2:]==baseline[2:],axis=1)&(errors@p%2==(baseline@p%2)^1)&(errors@f%2==(baseline@f%2)^1)
        assert result.baseline_weights[0]==costs[feasible].min()
        assert result.complementary_weights[0]==costs[opposite].min()
        assert result.gaps[0]==(12 if syndrome==0 else 2)
    # Every possible fixed zero/one spatial assignment and temporal RHS,
    # independently compared to the static constrained graph kernel.
    rhs=np.array(list(product((0,1),repeat=3)),dtype=np.uint8)
    for frozen in product((0,1),repeat=2):
        for y,pbit,fbit in rhs:
            feasible=(errors@h.T.toarray()).ravel()%2==y
            feasible&=np.all(errors[:,2:]==frozen,axis=1)&(errors@p%2==pbit)&(errors@f%2==fbit)
            constrained_rhs=np.array([[y,int(pbit)^frozen[0],int(fbit)^frozen[1]]],dtype=np.uint8)
            assert bool(core._comparison.feasible(constrained_rhs)[0])==bool(feasible.any())
            if not feasible.any():continue
            labels,weights,witness,_=core._comparison.decode_batch(constrained_rhs,return_errors=True)
            assert weights[0]+np.array(example['weights'])[2:]@frozen==costs[feasible].min()


@pytest.mark.parametrize('rounds',[2,3])
@pytest.mark.parametrize('pauli',['X','Z'])
@pytest.mark.parametrize('qubit',[0,4])
def test_diagnostic_Z_MPP_and_direct_terminal_stabilizer_state(rounds,pauli,qubit):
    compiled=build_preparation(dict(protocol='surface_prep_fixed',distance=3,rounds=rounds,p=0))
    code=Code.rotated(3);circuit=compiled.physical_prefix.copy();circuit.append(pauli,[qubit])
    hx,hz=code.matrices[0].toarray(),code.matrices[1].toarray()
    def operators(matrix,sector):
        return [stim.PauliString(''.join(sector if bit else 'I' for bit in row)) for row in matrix]
    xs,zs=operators(hx,'X'),operators(hz,'Z')
    # A tableau trajectory gives direct terminal-state expectations before probes.
    state=stim.TableauSimulator(seed=51);state.do_circuit(circuit)
    old=stim.TableauSimulator(seed=51);old.do_circuit(compiled.physical_prefix)
    for op in xs+zs:
        anti=stim.PauliString('I'*qubit+pauli+'I'*(8-qubit)).commutes(op)
        assert state.peek_observable_expectation(op)==old.peek_observable_expectation(op)*(1 if anti else -1)
    count=circuit.num_measurements
    for matrix,sector in ((hz,'Z'),(hx,'X')):
        for row in matrix:
            circuit+=stim.Circuit('MPP '+'*'.join(f'{sector}{q}' for q in np.flatnonzero(row)))
    circuit.append('M',list(range(9)))
    raw=circuit.compile_sampler(seed=15).sample(7)
    np.testing.assert_array_equal(raw[:,-9:]@hz.T%2,raw[:,count:count+len(zs)])


def compact_row(i, *,x=True,z=True,c=True,gap=2,sx=False,sz=False,lz=False):
    return dict(shot_index=i,baseline_valid=x,z_decoder_valid=z,complementary_valid=c,
        sign_miss_x=sx if x else None,sign_miss_z=sz if z else None,code_sign_miss=(sx or sz) if x and z else None,
        logical_z_error=lz if z else None,baseline_weight=0. if x else None,
        complementary_weight=float(gap*1000) if c else None,gap=float(gap) if c else None,
        status='invalid_syndrome' if not x else 'no_complementary_solution' if not c else 'z_decoder_invalid' if not z else 'ok')


def test_nullable_denominators_joint_contingency_inclusive_threshold_and_Wilson():
    rows=[compact_row(0),compact_row(1,sx=True),compact_row(2,sz=True,lz=True),
          compact_row(3,c=False,sx=True),compact_row(4,x=False,c=False,lz=True),compact_row(5,z=False)]
    summary=from_shots(rows);check_summary(summary)
    assert summary['shots']==6 and summary['eligible']==3
    assert summary['unconditional']['sign_x']==dict(shots=5,errors=2)
    assert summary['unconditional']['logical_z']==dict(shots=5,errors=2)
    assert summary['selected']['code_space']==dict(shots=3,errors=2)
    assert summary['selected']['joint_counts']==[1,0,0,1,1,0,0,0]
    assert from_shots(rows,2)['eligible']==3 and from_shots(rows,2.001)['eligible']==0
    assert interval(0,6)['rate']==0 and interval(0,6)['upper']>0
    assert interval(0,0)==dict(rate=None,lower=None,upper=None)
    damaged=dict(summary);damaged['unconditional']=dict(summary['unconditional'],joint_counts=[0]*8)
    with pytest.raises(ValueError,match='joint'):check_summary(damaged)


def tiny(tmp_path,compact=True):
    config=yaml.safe_load((Path(__file__).parents[1]/'configs/templates/surface_prep_fixed.yaml').read_text())
    config['experiment'].update(output_root=str(tmp_path/'results'),physical_error_rates=[.02])
    config['protocols'][0]['rounds']=2
    config['sampling'].update(shots_per_case=7,chunk_size=3)
    config['decoders']['temporal']['output_mode']='full_witness'
    config['decoders']['other']=dict(config['decoders']['temporal'],weight_scale=2000)
    config['protocols'][0]['decoders']=['temporal','other']
    config['storage'].update(save_shot_results=compact,retained_uniform_samples_per_case=2,retained_failure_samples_per_case=1)
    path=tmp_path/'report.yaml';path.write_text(yaml.safe_dump(config));return path


def test_saved_reports_no_simulation_new_directory_witnesses_pairs_and_arbitrary_cuts(tmp_path,monkeypatch):
    run=prepare(tiny(tmp_path));execute_run(run,workers=2)
    before={str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()}
    with monkeypatch.context() as patch:
        patch.setattr(stim.Circuit,'compile_detector_sampler',lambda *a,**k:pytest.fail('analysis sampled'))
        patch.setattr(TemporalMatching,'__init__',lambda *a,**k:pytest.fail('analysis constructed decoder'))
        rows,out=analyze_saved(run,output=run/'analysis'/'review',thresholds=[-np.inf,0,2.5,np.inf])
    assert len(rows)==2
    doc=json.loads((out/'preparation_summary.json').read_text())
    assert doc['preparation_result_version']==1 and doc['status']==json.loads((run/'manifest.json').read_text())['status']
    assert doc['failed_attempt_assigned_shots_unpublished']==0
    assert all((run/name).read_bytes()==value for name,value in before.items())
    assert not (run/'report.md').exists()
    validation=json.loads((out/'validation_summary.json').read_text())
    assert validation['status']=='pass' and validation['path_pass']>0
    assert validation['compact_aggregate_counts']=='pass'
    pairs=json.loads((out/'paired_comparisons.json').read_text());assert pairs['available'] and len(pairs['comparisons'])==4
    assert all(sum(p['counts'])==7 for p in pairs['comparisons'])
    curves=pq.read_table(out/'threshold_curve.parquet').to_pylist()
    assert all(r['attempts']==7 and r['accepted']==0 and r['Q'] is None for r in curves if r['threshold']==np.inf)
    assert all(np.isclose(r['A']+r['invalid']/r['attempts']+r['rejected_valid']/r['attempts'],1) for r in curves)
    assert len(list((out/'figures').glob('*.pdf')))>=4
    assert len(list((out/'figures').glob('*.png')))>=4
    assert len(list((out/'figures').glob('*.svg')))>=4
    with pytest.raises(FileExistsError):analyze_saved(run,output=out)
    with pytest.raises(ValueError,match='separate'):analyze_saved(run,output=run/'data'/'oops')
    # Directly corrupt each independently checked full witness convention.
    from knill_bench.analysis.preparation_report import _audit_model
    from knill_bench.data.storage import read_rows
    retained=read_rows(run,'preparation_retained')[0];saved=json.loads(retained['decoder_results_json'])['temporal']
    case=next(c for c in read_rows(run,'preparation_cases') if c['decoder']=='temporal')
    meta,x,z,_=_audit_model(run,case)
    for field in ('gap','baseline_weight','complementary_weight','baseline_past'):
        bad=dict(saved);bad[field]=not bad[field] if field=='baseline_past' else bad[field]+1
        with pytest.raises(ValueError):validate_witness(x,z,retained,bad)
    bad=dict(saved,output_mode='compact')
    with pytest.raises(ValueError,match='compact'):validate_witness(x,z,retained,bad)
    part=next((run/'data'/'preparation_chunks').glob('part-*c00000000.parquet'))
    original=part.read_bytes();part.write_bytes(original+b'corrupt')
    try:
        with pytest.raises(ValueError,match='changed or missing'):
            analyze_saved(run,output=tmp_path/'corrupted')
        assert json.loads((tmp_path/'corrupted'/'validation_summary.json').read_text())['status']=='fail'
    finally:part.write_bytes(original)


def test_aggregate_report_exact_saved_edges_and_rejected_unavailable_cut(tmp_path):
    run=prepare(tiny(tmp_path,compact=False));execute_run(run)
    rows,out=analyze_saved(run,output=tmp_path/'aggregate',thresholds=[-np.inf,0,2,np.inf])
    assert len(rows)==2 and json.loads((out/'validation_summary.json').read_text())['status']=='pass'
    with pytest.raises(ValueError,match='gap-bin edges'):
        analyze_saved(run,output=tmp_path/'invalid_cut',thresholds=[2.5])
    assert json.loads((tmp_path/'invalid_cut'/'validation_summary.json').read_text())['status']=='fail'
    full=prepare(tiny(tmp_path,compact=True));execute_run(full)
    _,fullout=analyze_saved(full,output=tmp_path/'compact',thresholds=[-np.inf,0,2,np.inf])
    assert pq.read_table(out/'conditional_rates.parquet').to_pylist()==pq.read_table(fullout/'conditional_rates.parquet').to_pylist()
    assert pq.read_table(out/'threshold_curve.parquet').to_pylist()==pq.read_table(fullout/'threshold_curve.parquet').to_pylist()


@pytest.mark.parametrize('flipped_rounds',[(1,),(3,),(1,2,3)])
def test_finite_readout_faults_and_continuous_temporal_ambiguity(flipped_rounds):
    from knill_bench.preparation import split_preparation_samples
    compiled=build_preparation(dict(protocol='surface_prep_fixed',distance=3,rounds=3,p=0))
    circuit=compiled.circuit.copy()
    targets={r.record_id for r in compiled.ledger if r.source=='se' and r.sector=='x' and r.check_index==0 and r.round_index in flipped_rounds}
    replacement=stim.Circuit();record=0
    for op in circuit:
        if op.name=='MR':
            for target in op.targets_copy():
                replacement.append('MR',[target],int(record in targets));record+=1
        else:
            replacement.append(op);record+=stim.Circuit(str(op)).num_measurements
    det,obs=replacement.compile_detector_sampler(seed=123).sample(7,separate_observables=True)
    batch=split_preparation_samples(compiled,det,obs)
    expected=[(r-1 in flipped_rounds)^(r in flipped_rounds) for r in (2,3)]
    np.testing.assert_array_equal(batch.observations.online_x_detectors[:,[0,4]],np.tile(expected,(7,1)))
    assert np.all(batch.truth.tau_x[:,0]==(3 in flipped_rounds))
    assert not batch.truth.tau_x[:,1:].any() and not batch.truth.tau_z.any() and not batch.truth.logical_z.any()
    if flipped_rounds==(1,2,3):
        assert not batch.observations.online_x_detectors.any() and batch.truth.tau_x.any()


@pytest.mark.parametrize('raw,count',[(b'\x80',1),(b'',1),(b'\x00\x00',1)])
def test_saved_witness_padding_or_size_corruption_rejects(raw,count):
    with pytest.raises(ValueError):unpack(raw,count)



def test_zero_nominal_graph_report_tracks_null_complements_and_positive_zero_event_bounds(tmp_path):
    path=tiny(tmp_path);cfg=yaml.safe_load(path.read_text())
    cfg['experiment']['physical_error_rates']=[0.]
    cfg['protocols'][0]['decoders']=['temporal'];cfg['decoders'].pop('other')
    cfg['sampling']['shots_per_case']=3
    path.write_text(yaml.safe_dump(cfg));run=prepare(path);execute_run(run)
    rows,out=analyze_saved(run,output=tmp_path/'p0',thresholds=[-np.inf,0,np.inf])
    assert rows[0]['baseline_valid']==3 and rows[0]['complementary_valid']==0 and rows[0]['logical_valid']==3
    rates=pq.read_table(out/'conditional_rates.parquet').to_pylist()
    assert any(r['bin']==-1 and r['scope']=='metric_valid' and r['denominator']==3 and r['events']==0 and r['upper']>0 for r in rates)
    assert all(r['accepted']==0 and r['invalid']==3 and r['Q'] is None for r in pq.read_table(out/'threshold_curve.parquet').to_pylist())
