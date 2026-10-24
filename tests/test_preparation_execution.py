"""Bounded d3 preparation execution through the existing ordered spawn runner."""
from concurrent.futures import Future
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import stim
import yaml

from knill_bench.config import load,grid,resolve
from knill_bench.data.storage import read_rows,SCHEMAS
from knill_bench.simulation.runner import prepare,execute_run
from knill_bench.simulation.preparation import sample_hash,validate_run


def tiny(tmp_path, **options):
    cfg=load(Path(__file__).parents[1]/'configs/templates/surface_prep_fixed.yaml')
    cfg['experiment'].update(output_root=str(tmp_path/'results'),physical_error_rates=[.003])
    cfg['protocols'][0]['rounds']=2
    cfg['sampling'].update(shots_per_case=7,chunk_size=3,workers=1,model_cache_size=1)
    cfg['timing'].update(warmup_shots=1,latency_sample_count_per_case=2)
    cfg['storage'].update(retained_uniform_samples_per_case=2,retained_failure_samples_per_case=1)
    cfg['storage'].update(options)
    path=tmp_path/'tiny.yaml';path.write_text(yaml.safe_dump(cfg));return path


def events(run):
    drop={'warmup_ns','x_baseline_ns','x_complementary_ns','z_decode_ns','decode_overhead_ns','evaluation_ns'}
    return [{k:v for k,v in row.items() if k not in drop} for row in read_rows(run,'preparation_chunks')]


def test_one_two_workers_interrupted_resume_schemas_and_saved_analysis(tmp_path):
    from knill_bench.analysis.report import analyze
    path=tiny(tmp_path)
    one=prepare(path);execute_run(one,workers=1)
    two=prepare(path);execute_run(two,workers=2,max_new_chunks=1)
    assert json.loads((two/'manifest.json').read_text())['status']=='interrupted'
    execute_run(two,workers=2)
    keys=('sampling_case_id','replicate','chunk_id','seed','shot_start','shots','sample_hash','status')
    assert [[r[k] for k in keys] for r in read_rows(one,'batches')]==[[r[k] for k in keys] for r in read_rows(two,'batches')]
    assert read_rows(one,'preparation_shots')==read_rows(two,'preparation_shots')
    assert events(one)==events(two)
    assert read_rows(one,'preparation_retained')==read_rows(two,'preparation_retained')
    assert len(read_rows(two,'preparation_retained'))<=3
    for part in (two/'data').rglob('*.parquet'):
        name=part.stem if part.parent.name=='data' else part.parent.name
        assert pq.ParquetFile(part).schema_arrow.equals(SCHEMAS[name],check_metadata=True)
    before=sorted(p.read_bytes() for p in (two/'checkpoints').glob('*.json'))
    execute_run(two,workers=1)
    assert sorted(p.read_bytes() for p in (two/'checkpoints').glob('*.json'))==before
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(stim.Circuit,'compile_detector_sampler',lambda *a,**k:pytest.fail('analysis cannot sample'))
        result=analyze(two)
    assert result[0]['shots']==7 and (two/'preparation_summary.json').exists()


def test_aggregate_only_matches_compact_rows_and_gap_bins(tmp_path):
    path=tiny(tmp_path);full=prepare(path);execute_run(full)
    cfg=load(path);cfg['storage']['save_shot_results']=False;path.write_text(yaml.safe_dump(cfg))
    aggregate=prepare(path);execute_run(aggregate)
    assert not read_rows(aggregate,'preparation_shots')
    assert events(full)==events(aggregate)
    shots=read_rows(full,'preparation_shots')
    assert sum(r['sign_miss_x'] or 0 for r in shots)==sum(r['sign_miss_x'] for r in read_rows(aggregate,'preparation_chunks'))
    assert sum(r['logical_z_error'] or 0 for r in shots)==sum(r['logical_z_errors'] for r in read_rows(aggregate,'preparation_chunks'))
    for row in read_rows(aggregate,'preparation_chunks'):
        bins=json.loads(row['gap_bins_json'])
        assert sum(b['summary']['shots'] for b in bins)==row['shots']
        assert sum(b['summary']['unconditional']['code_space']['errors'] for b in bins)==row['code_sign_miss']
    for p in (aggregate/'checkpoints').glob('*.json'):
        assert json.loads(p.read_text())['ipc_payload_bytes']<10000


def test_prepare_builds_no_live_graphs_and_worker_loads_without_dem_parsing(tmp_path,monkeypatch):
    import pymatching
    from knill_bench.simulation.worker import CACHE,model
    path=tiny(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(pymatching.Matching,'from_check_matrix',lambda *a,**k:pytest.fail('prepare built a live graph'))
        run=prepare(path)
    params=json.loads((run/'parameters.json').read_text());case=params['grid'][0]
    CACHE.clear()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(stim,'DetectorErrorModel',lambda *a,**k:pytest.fail('worker reparsed DEM'))
            first=model(case,params['config'],run)
            assert model(case,params['config'],run) is first
        decoder=next(iter(first[1].values()))
        count=first[0].metadata['runtime_setup_timing']['graph_construct_count']
        with monkeypatch.context() as patch:
            patch.setattr(pymatching.Matching,'from_check_matrix',lambda *a,**k:pytest.fail('decode built a graph'))
            a=decoder.decode_batch(np.zeros((3,4),dtype=bool),np.zeros((3,8),dtype=bool))
        assert count==3 and np.isfinite(a.gap).all()
        CACHE.clear();other=model(case,params['config'],run)[1]['temporal']
        b=other.decode_batch(np.zeros((3,4),dtype=bool),np.zeros((3,8),dtype=bool))
        np.testing.assert_array_equal(a.gap,b.gap)
    finally:CACHE.clear()


@pytest.mark.parametrize('target',['x','z','map','circuit','partition','committed'])
def test_tampered_artifacts_and_partitions_reject_before_orphan_cleanup(tmp_path,target):
    path=tiny(tmp_path);run=prepare(path)
    if target=='committed':execute_run(run,max_new_chunks=1)
    orphan=run/'staging'/'must_survive_rejection';orphan.mkdir(exist_ok=True)
    sentinel=orphan/'sentinel';sentinel.write_text('keep')
    if target in {'x','z'}:
        artifact=next((run/'models').glob(f'*.{target}.json'));artifact.write_text(artifact.read_text()+' ')
    elif target=='map':
        artifact=next((run/'models').glob('*.metadata.json'));value=json.loads(artifact.read_text())
        value['sample_map']['labels']['tau_x'].reverse();artifact.write_text(json.dumps(value))
    elif target=='circuit':
        artifact=next((run/'circuits').glob('*.production.stim'));artifact.write_text(artifact.read_text()+'\nTICK\n')
    elif target=='partition':
        artifact=run/'parameters.json';value=json.loads(artifact.read_text());value['batch_partition']+=1;artifact.write_text(json.dumps(value))
    else:
        artifact=next((run/'data/preparation_shots').glob('part-*-r*.parquet'));artifact.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='changed|missing'):
        execute_run(run)
    assert sentinel.read_text()=='keep'


def test_failed_chunk_is_assigned_unobserved_retry_uses_same_seed(tmp_path,monkeypatch):
    import knill_bench.simulation.runner as runner
    path=tiny(tmp_path);run=prepare(path)
    class FailingPool:
        def __init__(self,*a,**k):pass
        def submit(self,*a,**k):
            result=Future();result.set_exception(RuntimeError('controlled failure'));return result
        def shutdown(self,**kwargs):pass
    with monkeypatch.context() as patch:
        patch.setattr(runner,'ProcessPoolExecutor',FailingPool)
        with pytest.raises(RuntimeError,match='worker failed'):execute_run(run)
    row=read_rows(run,'preparation_chunks')[0]
    assert row['assigned_shots']==3 and row['shots']==0 and row['baseline_valid']==0
    failed_seed=read_rows(run,'batches')[0]['seed']
    assert not list((run/'checkpoints').glob('*.json'))
    execute_run(run)
    assert read_rows(run,'batches')[0]['seed']==failed_seed
    assert sum(r['shots'] for r in read_rows(run,'preparation_chunks'))==7


def test_retained_samples_match_original_hash_verified_chunk_and_same_mode_witnesses(tmp_path):
    from knill_bench.simulation.worker import CACHE,model
    from knill_bench.preparation import split_preparation_samples
    path=tiny(tmp_path);cfg=load(path);cfg['decoders']['temporal']['output_mode']='full_witness'
    path.write_text(yaml.safe_dump(cfg));run=prepare(path);execute_run(run)
    params=json.loads((run/'parameters.json').read_text());case=params['grid'][0]
    CACHE.clear()
    try:
        runtime,decoders,_,_,_=model(case,params['config'],run)
        for chunk in read_rows(run,'batches'):
            det,obs=runtime.circuit.compile_detector_sampler(seed=chunk['seed']).sample(chunk['shots'],separate_observables=True)
            batch=split_preparation_samples(runtime.sample_map,det,obs)
            assert sample_hash(batch)==chunk['sample_hash']
            prediction=decoders['temporal'].decode_batch(batch.observations.online_x_detectors,batch.observations.online_z_detectors)
            for retained in read_rows(run,'preparation_retained'):
                if retained['chunk_id']!=chunk['chunk_id']:continue
                local=retained['shot_index']-chunk['shot_start']
                assert retained['online_x']==np.packbits(batch.observations.online_x_detectors[local],bitorder='little').tobytes()
                assert retained['truth_tau_z']==np.packbits(batch.truth.tau_z[local],bitorder='little').tobytes()
                saved=json.loads(retained['decoder_results_json'])['temporal']
                assert saved['output_mode']=='full_witness' and saved['gap']==prediction.gap[local]
                assert saved['baseline_errors']==np.packbits(decoders['temporal'].x_model.expand_errors(prediction.debug.baseline_errors[local:local+1])[0],bitorder='little').tobytes().hex()
    finally:CACHE.clear()


def test_sample_hash_shapes_padding_order_truth_and_decoder_independence():
    from knill_bench.preparation import PreparationBatch,PreparationObservations,PreparationTruth
    zero=np.zeros((2,1),dtype=bool)
    batch=PreparationBatch(PreparationObservations(zero.copy(),zero.copy()),PreparationTruth(zero.copy(),zero.copy(),zero.copy()))
    assert sample_hash(batch)==sample_hash(batch)
    assert sample_hash(replace(batch,truth=PreparationTruth(~zero,zero.copy(),zero.copy())))!=sample_hash(batch)
    wider=PreparationBatch(PreparationObservations(np.zeros((2,2),dtype=bool),zero.copy()),batch.truth)
    assert sample_hash(wider)!=sample_hash(batch)


def test_bounded_retention_config_rejects_all_syndromes(tmp_path):
    path=tiny(tmp_path);cfg=load(path);cfg['storage']['save_all_syndromes']=True
    with pytest.raises(ValueError,match='bounded retention'):resolve(cfg)


def test_worker_truth_changes_only_evaluation_not_prediction_and_native_sample_stays_fixed(tmp_path,monkeypatch):
    from knill_bench.simulation.worker import CACHE,execute
    import knill_bench.simulation.preparation as module
    from knill_bench.preparation import PreparationTruth
    path=tiny(tmp_path,retained_uniform_samples_per_case=7);run=prepare(path)
    params=json.loads((run/'parameters.json').read_text());case=params['grid'][0];cfg=params['config']
    task=(case,cfg,0,0,0,3,str(run));CACHE.clear()
    try:
        first=execute(task)
        before=pq.read_table(first['files']['preparation_retained']['path']).to_pylist()
        splitter=module.split_preparation_samples
        def changed(*args):
            batch=splitter(*args)
            return replace(batch,truth=PreparationTruth(~batch.truth.tau_x,~batch.truth.tau_z,~batch.truth.logical_z))
        monkeypatch.setattr(module,'split_preparation_samples',changed)
        second=execute(task)
        after=pq.read_table(second['files']['preparation_retained']['path']).to_pylist()
        assert [r['decoder_results_json'] for r in before]==[r['decoder_results_json'] for r in after]
        assert [r['online_x'] for r in before]==[r['online_x'] for r in after]
        assert first['sample_hash']!=second['sample_hash']  # Evaluation labels are part of the canonical sample identity.
    finally:CACHE.clear()


def test_cache_eviction_and_rebuild_preserve_predictions(tmp_path):
    import weakref
    from knill_bench.simulation.worker import model,CACHE
    path=tiny(tmp_path);cfg=load(path);cfg['experiment']['physical_error_rates']=[.001,.002]
    path.write_text(yaml.safe_dump(cfg));run=prepare(path);params=json.loads((run/'parameters.json').read_text())
    one,two=params['grid'];cfg=params['config'];CACHE.clear()
    try:
        first=model(one,cfg,run)
        a=first[1]['temporal'].decode_batch(np.zeros((3,4),dtype=bool),np.zeros((3,8),dtype=bool)).gap
        reference=weakref.ref(first[0]);del first
        model(two,cfg,run)
        assert len(CACHE)==1 and reference() is None
        rebuilt=model(one,cfg,run)
        b=rebuilt[1]['temporal'].decode_batch(np.zeros((3,4),dtype=bool),np.zeros((3,8),dtype=bool)).gap
        np.testing.assert_array_equal(a,b)
    finally:CACHE.clear()


def test_prefix_artifact_roundtrip_and_validation_without_Stim_parsing(monkeypatch):
    from copy import deepcopy
    import hashlib
    from knill_bench.decoding.preparation_prefix import prefix_dem_to_model,PrefixDemModel
    from knill_bench.config import canonical
    model=prefix_dem_to_model(stim.DetectorErrorModel('error(0) D0 L0\nerror(.2) D0 L1'),
        detector_ids=[0],observable_ids=[1,0],feature_ids=['logical_z','tau_z:0'])
    monkeypatch.setattr(stim,'DetectorErrorModel',lambda *a,**k:pytest.fail('unexpected parse'))
    restored=PrefixDemModel.from_artifact(model.to_artifact())
    assert restored.model_sha256==model.model_sha256
    np.testing.assert_array_equal(restored.feature_map.toarray(),model.feature_map.toarray())
    invalid=json.loads(json.dumps(model.to_artifact()));invalid['payload']['full_detector_support'][0]=[2]
    invalid['sha256']=hashlib.sha256(canonical(invalid['payload']).encode()).hexdigest()
    with pytest.raises(ValueError,match='artifact'):PrefixDemModel.from_artifact(invalid)


def test_larger_template_is_parse_only(monkeypatch):
    from knill_bench.codes import Code
    monkeypatch.setattr(Code,'rotated',lambda *a,**k:pytest.fail('large template must only parse'))
    cfg=load(Path(__file__).parents[1]/'configs/templates/surface_prep_fixed_sweep.yaml')
    assert len(list(grid(cfg)))==12 and cfg['protocols'][0]['rounds']==3


def test_multiple_decoders_share_physical_chunks_with_separate_modes_and_nullable_p0(tmp_path):
    path=tiny(tmp_path);cfg=load(path)
    cfg['experiment']['physical_error_rates']=[0]
    cfg['protocols'][0]['rounds']=1
    cfg['sampling'].update(shots_per_case=3,chunk_size=3)
    cfg['decoders']['full']=dict(cfg['decoders']['temporal'],output_mode='full_witness')
    cfg['protocols'][0]['decoders'].append('full')
    path.write_text(yaml.safe_dump(cfg));run=prepare(path);execute_run(run)
    assert len(read_rows(run,'batches'))==1
    rows=read_rows(run,'preparation_chunks')
    assert len(rows)==2 and all(r['baseline_valid']==3 and r['complementary_valid']==0 for r in rows)
    shots=read_rows(run,'preparation_shots')
    assert len(shots)==6 and all(r['gap'] is None and r['complementary_weight'] is None for r in shots)
    for row in read_rows(run,'preparation_retained'):
        assert set(json.loads(row['decoder_results_json']))=={'temporal','full'}


def test_partial_parent_promotion_has_no_checkpoint_and_restarts_same_chunk(tmp_path,monkeypatch):
    import knill_bench.simulation.runner as runner
    path=tiny(tmp_path);cfg=load(path);cfg['sampling'].update(shots_per_case=3,chunk_size=3)
    path.write_text(yaml.safe_dump(cfg));run=prepare(path)
    original=runner.os.replace
    def fail_on_second_table(src,dst):
        dst=Path(dst)
        if dst.parent.name=='preparation_chunks' and dst.name.startswith('part-'):
            raise OSError('controlled publication failure')
        return original(src,dst)
    with monkeypatch.context() as patch:
        patch.setattr(runner.os,'replace',fail_on_second_table)
        with pytest.raises(OSError,match='publication failure'):execute_run(run)
    assert not list((run/'checkpoints').glob('*.json'))
    first=read_rows(run,'batches')[0]
    execute_run(run)
    assert len(read_rows(run,'batches'))==1
    assert read_rows(run,'batches')[0]['sample_hash']==first['sample_hash']
    assert len(list((run/'checkpoints').glob('*.json')))==1
