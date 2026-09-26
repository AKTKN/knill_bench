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
