import json
from pathlib import Path
import pytest
import pyarrow.parquet as pq
import yaml
from knill_bench.config import load,resolve,grid
from knill_bench.simulation.runner import prepare,execute_run
from knill_bench.data.storage import read_rows,SCHEMAS
from knill_bench.analysis.report import wilson


def small_config(tmp_path):
    cfg=load(Path(__file__).parents[1]/'configs/smoke.yaml')
    cfg['experiment'].update(output_root=str(tmp_path/'results'),distances=[3],bases=['z'],cycles=[1])
    cfg['sampling'].update(shots_per_case=12,chunk_size=6,workers=1)
    cfg['timing'].update(latency_sample_count_per_case=2,warmup_shots=1)
    cfg['storage'].update(retained_uniform_samples_per_case=2,retained_failure_samples_per_case=2)
    path=tmp_path/'test.yaml';path.write_text(yaml.safe_dump(cfg));return path


def test_one_two_workers_resume_and_schemas(tmp_path):
    path=small_config(tmp_path)
    one=prepare(path);execute_run(one,workers=1)
    two=prepare(path);execute_run(two,workers=2,max_new_chunks=2)
    assert json.loads((two/'manifest.json').read_text())['status']=='interrupted'
    execute_run(two,workers=2)
    rows1=read_rows(one,'batches');rows2=read_rows(two,'batches')
    keys=('sampling_case_id','replicate','chunk_id','seed','shot_start','shots','sample_hash','status')
    assert [{k:r[k] for k in keys} for r in rows1]==[{k:r[k] for k in keys} for r in rows2]
    shots1=read_rows(one,'shots');shots2=read_rows(two,'shots')
    assert shots1==shots2
    assert len(rows2)==8
    assert len({(r['sampling_case_id'],r['replicate'],r['chunk_id']) for r in rows2})==8
    for part in (two/'data').rglob('*.parquet'):
        name=part.stem if part.parent.name=='data' else part.parent.name
        assert pq.read_table(part).schema.equals(SCHEMAS[name],check_metadata=True)
    for sid in {r['sampling_case_id'] for r in rows2}:
        samples=[r for r in read_rows(two,'retained_samples') if r['sampling_case_id']==sid]
        assert len(samples)<=4
    before=[p.name for p in (two/'checkpoints').glob('*.json')]
    execute_run(two,workers=1)
    assert before==[p.name for p in (two/'checkpoints').glob('*.json')]
    calls=read_rows(two,'decoder_calls')
    assert all(r['batch_size']==1 for r in calls if r['timing_mode']=='latency')
    assert all(not r['warmup'] for r in calls)
    assert wilson(0,100)[1]>0


def test_bad_config_rejected(tmp_path):
    cfg=load(small_config(tmp_path))
    for modification in ({'unknown':1},{'schema_version':2}):
        with pytest.raises(ValueError):resolve(dict(cfg,**modification))
    cfg['experiment']['distances']=[4]
    with pytest.raises(ValueError):resolve(cfg)


def test_stopping(tmp_path):
    path=small_config(tmp_path);cfg=load(path)
    cfg['protocols']=[cfg['protocols'][0]]
    cfg['experiment']['physical_error_rates']=[.1]
    cfg['sampling'].update(stop_rule='target_errors',target_errors=1,max_shots=36,reference_decoder='global_lsd')
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path);execute_run(run)
    rows=read_rows(run,'stopping')
    assert rows[0]['actual_shots']<=36 and rows[0]['actual_shots']%6==0
    assert rows[0]['actual_reference_errors']>=1
    execute_run(run)
    assert read_rows(run,'stopping')[0]['actual_shots']==rows[0]['actual_shots']


def test_time_budget_and_resume_compatibility(tmp_path):
    path=small_config(tmp_path);cfg=load(path)
    cfg['protocols']=[cfg['protocols'][0]]
    cfg['sampling'].update(stop_rule='time_budget',max_shots=12,time_budget_seconds=0.001)
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path);execute_run(run)
    before=len(read_rows(run,'batches'))
    execute_run(run)
    assert len(read_rows(run,'batches'))==before
    params=json.loads((run/'parameters.json').read_text());params['config']['sampling']['chunk_size']=7
    (run/'parameters.json').write_text(json.dumps(params))
    with pytest.raises(ValueError,match='config/grid changed'):execute_run(run)


def test_installed_outside_repository(tmp_path):
    import subprocess,sys
    path=small_config(tmp_path)
    result=subprocess.run([sys.executable,'-m','knill_bench.cli','validate-config',str(path)],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['resolved_grid']


def test_prepare_does_not_construct_live_decoders(tmp_path,monkeypatch):
    from knill_bench.adapters import decoders
    from knill_bench.adapters import hex_native
    path=small_config(tmp_path)
    def forbidden(*args,**kwargs):
        raise AssertionError('live decoder constructed during prepare')
    monkeypatch.setattr(decoders,'construct',forbidden)
    monkeypatch.setattr(decoders,'GlobalBPLSD',forbidden)
    monkeypatch.setattr(decoders,'BpLsdDecoder',forbidden)
    monkeypatch.setattr(decoders,'MoMatching',forbidden)
    monkeypatch.setattr(decoders,'MatchingAdapter',forbidden)
    monkeypatch.setattr(hex_native,'NativeHex',forbidden)
    run=prepare(path)
    assert read_rows(run,'cases')


def test_worker_loads_saved_matching_graphs(tmp_path,monkeypatch):
    from knill_bench.adapters import decoders
    from knill_bench.simulation.worker import CACHE,model
    path=small_config(tmp_path);run=prepare(path)
    params=json.loads((run/'parameters.json').read_text())
    case=next(c for c in params['grid'] if c['protocol']=='knill_aft_postgate')
    metadata=json.loads((run/'models'/f"{case['sampling_case_id']}.metadata.json").read_text())
    for descriptor in metadata['decoder_models'].values():
        if 'graph_artifact' in descriptor:
            assert (run/'models'/descriptor['graph_artifact']).exists()
    def forbidden(*args,**kwargs):
        raise AssertionError('worker repeated prepared matching graph extraction')
    CACHE.clear()
    try:
        monkeypatch.setattr(decoders,'get_circuit_subgraph',forbidden)
        monkeypatch.setattr(decoders,'decompose',forbidden)
        _,loaded,aliases,details,_=model(case,params['config'],run)
        assert loaded and all(aliases[name]==metadata['decoder_details'][name]['effective'] for name in case['decoders'])
    finally:CACHE.clear()


def test_resume_rejects_changed_matching_graph(tmp_path):
    path=small_config(tmp_path);run=prepare(path)
    graph=next((run/'models').glob('*.graph.dem'))
    graph.write_text(graph.read_text()+'\nerror(0.1) D0\n')
    with pytest.raises(ValueError,match='matching graph was changed'):
        execute_run(run)


def test_resume_rejects_changed_fallback_metadata(tmp_path):
    path=small_config(tmp_path);run=prepare(path)
    metadata_path=next((run/'models').glob('*.metadata.json'))
    metadata=json.loads(metadata_path.read_text())
    name=next(iter(metadata['decoder_details']))
    metadata['decoder_details'][name]['effective']='different_decoder'
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError,match='decoder resolution conflicts'):
        execute_run(run)


def test_equal_time_schedule_and_cross_replicate_bounds(tmp_path):
    path=small_config(tmp_path);cfg=load(path)
    cfg['experiment'].update(replicates=2,comparison={'kind':'equal_time','target_time':150})
    cfg['protocols']=[cfg['protocols'][0]]
    cfg['noise']=dict(profile='explicit',multipliers=dict(p1=1,p2=1,reset=1,measurement=1,idle=.1),durations=dict(p1=1,p2=2,reset=2,measurement=3),time_unit='gate_unit',preparation_schedule='serial_wait')
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path);execute_run(run)
    param=json.loads((run/'parameters.json').read_text())
    assert param['grid'][0]['target_time']==150 and 'time_mismatch' in param['grid'][0]
    retained=read_rows(run,'retained_samples')
    assert sum('uniform' in r['reason'] for r in retained)==2
    assert sum('failure' in r['reason'] for r in retained)<=2


def test_worker_failure_is_explicit_and_retryable(tmp_path,monkeypatch):
    from concurrent.futures import Future
    import knill_bench.simulation.runner as runner
    path=small_config(tmp_path);cfg=load(path);cfg['protocols']=[cfg['protocols'][0]]
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path)
    class FailingPool:
        def __init__(self,*args,**kwargs):pass
        def submit(self,*args,**kwargs):
            future=Future();future.set_exception(RuntimeError('controlled worker failure'));return future
        def shutdown(self,**kwargs):pass
    with monkeypatch.context() as local:
        local.setattr(runner,'ProcessPoolExecutor',FailingPool)
        with pytest.raises(RuntimeError,match='worker failed'):execute_run(run)
    assert json.loads((run/'manifest.json').read_text())['status']=='failed'
    b=read_rows(run,'batches')[0]
    assert b['status']=='worker_failed' and b['shots']==0 and b['requested_shots']==6
    assert all(r['failed']==6 for r in read_rows(run,'decoder_batches'))
    execute_run(run)
    assert len(read_rows(run,'batches'))==2
    assert all(r['status']=='complete' for r in read_rows(run,'batches'))


def test_aggregate_only_streaming_resume_and_analysis(tmp_path):
    from knill_bench.analysis.report import analyze
    path=small_config(tmp_path);cfg=load(path)
    cfg['storage']['save_shot_results']=False
    cfg['sampling']['workers']=2
    cfg['timing']['latency_sample_count_per_case']=0
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path);execute_run(run,max_new_chunks=3)
    execute_run(run)
    batches=read_rows(run,'batches')
    assert len(batches)==8
    assert len({(r['sampling_case_id'],r['replicate'],r['chunk_id']) for r in batches})==8
    assert not read_rows(run,'shots')
    assert len(read_rows(run,'paired_chunks'))>0
    assert all(len(list((run/'staging').glob('*')))==0 for _ in [0])
    checkpoints=[json.loads(p.read_text()) for p in (run/'checkpoints').glob('*.json')]
    assert all(ck['table_rows']['shots']==0 and ck['active_chunk_rss_delta_bytes']>=0 for ck in checkpoints)
    assert all(ck['setup_timing']['decoder_sparse_matrix_bytes']>=0
               for ck in checkpoints if ck['setup_timing'])
    summary=analyze(run)
    assert summary and (run/'data/paired_disagreements.parquet').exists()


def test_streaming_aggregate_only_matches_full_shot_run(tmp_path):
    path=small_config(tmp_path);base=load(path)
    base['protocols']=[p for p in base['protocols'] if p['id'] in ('knill_hex_dminus2','knill_aft_postgate')]
    base['sampling'].update(workers=2,shots_per_case=12,chunk_size=4,max_pending_chunks_per_worker=1)
    base['timing'].update(latency_sample_count_per_case=0,warmup_shots=0)
    runs=[]
    for save_shots in (True,False):
        cfg=yaml.safe_load(yaml.safe_dump(base))
        cfg['storage']['save_shot_results']=save_shots
        path.write_text(yaml.safe_dump(cfg))
        run=prepare(path);execute_run(run,max_new_chunks=2);execute_run(run)
        runs.append(run)
    full,aggregate=runs
    assert len(read_rows(full,'shots'))>0 and not read_rows(aggregate,'shots')
    batch_fields=('sampling_case_id','replicate','chunk_id','seed','shot_start','shots','sample_hash')
    assert [[r[k] for k in batch_fields] for r in read_rows(full,'batches')]==[
        [r[k] for k in batch_fields] for r in read_rows(aggregate,'batches')]
    decoder_fields=('sampling_case_id','replicate','chunk_id','case_id','errors','valid','failed')
    assert [[r[k] for k in decoder_fields] for r in read_rows(full,'decoder_batches')]==[
        [r[k] for k in decoder_fields] for r in read_rows(aggregate,'decoder_batches')]
    assert read_rows(full,'paired_chunks')==read_rows(aggregate,'paired_chunks')
    assert read_rows(full,'retained_samples')==read_rows(aggregate,'retained_samples')
    assert len(read_rows(aggregate,'batches'))==6
    assert max(json.loads(p.read_text())['ipc_payload_bytes'] for p in (aggregate/'checkpoints').glob('*.json'))<10000


def test_all_syndromes_parent_filter_stays_chunked(tmp_path):
    path=small_config(tmp_path);cfg=load(path)
    cfg['protocols']=[p for p in cfg['protocols'] if p['id']=='se_memory']
    cfg['experiment']['physical_error_rates']=[.1]
    cfg['sampling'].update(workers=2,shots_per_case=24,chunk_size=8)
    cfg['storage'].update(save_all_syndromes=True,retained_failure_samples_per_case=1)
    cfg['timing']['latency_sample_count_per_case']=0
    path.write_text(yaml.safe_dump(cfg))
    run=prepare(path);execute_run(run)
    retained=read_rows(run,'retained_samples')
    assert len(retained)==24
    assert all('all' in r['reason'] for r in retained)
    assert sum('failure' in r['reason'] for r in retained)<=1
    assert all(json.loads(p.read_text())['table_rows']['retained_samples']==8
               for p in (run/'checkpoints').glob('*.json'))


@pytest.mark.parametrize('protocol,distance,cycles',[
    ('se_memory',5,2),('knill_aft_postgate',5,2),
    ('knill_aft_prep_only',5,2),('knill_aft_postgate',7,3)])
def test_detector_sampler_matches_raw_stream_for_fixed_seed(protocol,distance,cycles):
    from knill_bench.circuits.builders import build
    cfg=load(Path(__file__).parents[1]/'configs/smoke.yaml')
    cfg['experiment'].update(distances=[distance],bases=['z'],cycles=[cycles],physical_error_rates=[.001])
    case=next(c for c in grid(cfg) if c['protocol']==protocol)
    circuit=build(case).circuit
    raw=circuit.compile_sampler(seed=913).sample(32)
    expected=circuit.compile_m2d_converter().convert(measurements=raw,separate_observables=True)
    actual=circuit.compile_detector_sampler(seed=913).sample(shots=32,separate_observables=True)
    assert all((a==b).all() for a,b in zip(expected,actual))


def test_model_cache_bound_and_config_validation(tmp_path):
    import weakref
    from knill_bench.simulation.worker import CACHE,model
    path=small_config(tmp_path);cfg=load(path)
    for value in (0,-1,1.5,True):
        bad=yaml.safe_load(path.read_text());bad['sampling']['model_cache_size']=value
        with pytest.raises(ValueError):resolve(bad)
    bad=yaml.safe_load(path.read_text());bad['sampling']['chunk_size']=0
    with pytest.raises(ValueError,match='chunk_size'):resolve(bad)
    cases=list(grid(cfg))
    CACHE.clear()
    try:
        first=weakref.ref(model(cases[0],cfg)[0])
        for case in cases[1:]:model(case,cfg)
        assert len(CACHE)==1
        if len(cases)>1:assert first() is None
        if len(cases)>1:
            CACHE.clear()
            cfg['sampling']['model_cache_size']=2
            model(cases[0],cfg);model(cases[1],cfg)
            assert len(CACHE)==2
            cfg['sampling']['model_cache_size']=1
            model(cases[1],cfg)  # A cache hit must also enforce a smaller bound.
            assert len(CACHE)==1
    finally:CACHE.clear()
