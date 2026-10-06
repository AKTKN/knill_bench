"""Deterministic ordered chunk commits, bounded spawn pool, resumable Parquet parts."""
from concurrent.futures import ProcessPoolExecutor
from collections import deque,Counter
import json
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import time
import uuid
import pyarrow.parquet as pq
from datetime import datetime,timezone
from knill_bench.config import canonical,digest,grid,load
from knill_bench.circuits.builders import build
from knill_bench.adapters.decoders import describe
from knill_bench.decoding.dem import convert_dem
from knill_bench.data.storage import atomic_json,write_table,read_rows,SCHEMAS,file_sha256,filter_retained_samples
from knill_bench.data.provenance import environment,compatibility,utc,sha
from knill_bench.simulation.worker import execute,case_id
from knill_bench.simulation.seeds import seed


TABLES=('batches','decoder_batches','shots','decoder_calls','diagnostics','retained_samples','paired_chunks')


def ensure_threads(count):
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        existing=os.environ.get(key)
        if existing is not None and existing!=str(count):
            raise ValueError(f'{key}={existing} conflicts with native_threads_per_worker={count}; set a compatible value explicitly')
        os.environ.setdefault(key,str(count))


def prepare(config_path):
    cfg=load(config_path)
    ensure_threads(cfg['sampling']['native_threads_per_worker'])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run=Path(cfg['experiment']['output_root']).resolve()/f'{stamp}_{uuid.uuid4().hex[:10]}'
    run.mkdir(parents=True)
    shutil.copyfile(config_path,run/'config.original.yaml')
    for d in ('circuits','models','data','plots','logs','checkpoints'):
        (run/d).mkdir()
    for table in TABLES:
        (run/'data'/table).mkdir()
        write_table(run/'data'/table/'part-empty.parquet',table,[],cfg['storage']['compression'])
    env=environment(run)
    atomic_json(run/'environment.json',env)
    cases=list(grid(cfg))
    # Equal-time grid may coalesce nominal cycle choices; do not duplicate samples.
    unique={c['sampling_case_id']:c for c in cases};cases=list(unique.values())
    atomic_json(run/'parameters.json',dict(schema_version=1,config=cfg,grid=cases,config_hash=digest(cfg),batch_partition=cfg['sampling']['chunk_size'],seed_derivation_version=1))
    manifest=dict(schema_version=1,status='building',started=utc(),ended=None,compatibility_hash=compatibility(env),config_hash=digest(cfg),grid_hash=digest(cases),completed_chunks=[],failed_chunks=[],
                  commit_policy='ordered_chunks_per_case; excess_running_chunks_discarded',stopping_interval_policy='Wilson_fixed_n; descriptive_only_under_sequential_stopping')
    atomic_json(run/'manifest.json',manifest)
    rows=[];diags=[]
    for case in cases:
        build_start=time.perf_counter_ns()
        compiled=build(case);compiled.metadata['basis']=case['basis']
        total_build_ns=time.perf_counter_ns()-build_start
        circuit_build_ns=max(0,total_build_ns-compiled.metadata['dem_build_ns'])
        descriptor_start=time.perf_counter_ns()
        aliases,details,decoder_models,graphs,descriptor_timing=describe(compiled,case,cfg)
        structural_validation_ns=time.perf_counter_ns()-descriptor_start
        sid=case['sampling_case_id'];ch=sha(str(compiled.circuit));mh=sha(str(compiled.dem))
        (run/'circuits'/f'{sid}.stim').write_text(str(compiled.circuit))
        (run/'models'/f'{sid}.dem').write_text(str(compiled.dem))
        for name,graph in graphs.items():
            filename=f'{sid}-{digest([name,"graph"])}.graph.dem'
            graph_text=str(graph)
            (run/'models'/filename).write_text(graph_text)
            decoder_models[name]['graph_artifact']=filename
            decoder_models[name]['graph_hash']=sha(graph_text)
        metadata=dict(compiled.metadata,circuit_hash=ch,model_hash=mh,ledger=compiled.ledger,detectors=compiled.detectors,
                      observable_records=compiled.observable_records,dem_options=dict(allow_gauge_detectors=False,approximate_disjoint_errors=False,decompose_errors=False),
                      decoder_details=details,decoder_models=decoder_models,
                      setup_timing=dict(circuit_build_ns=circuit_build_ns,dem_build_ns=compiled.metadata['dem_build_ns'],
                          structural_validation_ns=structural_validation_ns,decoder_construct_ns=None,
                          native_transition_construct_ns=None,
                          lom_subgraph_construct_ns=descriptor_timing['lom_subgraph_construct_ns'],bplsd_construct_ns=None))
        atomic_json(run/'models'/f'{sid}.metadata.json',metadata)
        for name in case['decoders']:
            effective=aliases[name]
            rows.append(dict(case_id=case_id(case,name),sampling_case_id=sid,protocol=case['protocol'],distance=case['distance'],basis=case['basis'],p=case['p'],cycles=case['cycles'],
                prep_rounds=case['prep_rounds'],post_gate_rounds=case['post_gate_rounds'],post_gate_scope=case['post_gate_scope'],geometry='rotated_surface_hex_order',
                boundary_id=digest(case['initial_boundary']),noise_id=digest(case['noise']),schedule_id=digest(compiled.metadata['schedule']),rates_json=canonical(case['rates']),
                requested_decoder=name,effective_decoder=effective,decoder_kind=cfg['decoders'][effective]['kind'],decoder_parameters_json=canonical(cfg['decoders'][effective]),
                fallback_reason=details[name]['fallback_reason'],validation_status='strict_dem_pass',circuit_hash=ch,model_hash=mh,
                metadata_json=canonical(dict({k:v for k,v in compiled.metadata.items() if k not in {'schedule','physical_schedule','coordinates'}},effective_case_id=case_id(case,effective)))))
        dm=convert_dem(compiled.dem).diagnostics()
        diags.append(dict(sampling_case_id=sid,kind='structural',**{k:dm[k] for k in ('detectors','faults','observables','h_nnz','l_nnz','hyperedges')},
                          availability='measured_from_undecomposed_dem',details_json=canonical(dm)))
        print(f"built {case['protocol']} d={case['distance']} {case['basis']} N={case['cycles']}",flush=True)
    write_table(run/'data/cases.parquet','cases',rows,cfg['storage']['compression'])
    write_table(run/'data/diagnostics/part-models.parquet','diagnostics',diags,cfg['storage']['compression'])
    manifest['status']='built';atomic_json(run/'manifest.json',manifest)
    return run


def chunk_key(sid,rep,chunk): return f'{sid}-r{rep:04d}-c{chunk:08d}'


def execute_run(run,workers=None,max_new_chunks=None):
    run=Path(run).resolve()
    parameters=json.loads((run/'parameters.json').read_text());cfg=parameters['config']
    original_manifest=json.loads((run/'manifest.json').read_text())
    if digest(cfg)!=original_manifest['config_hash'] or digest(parameters['grid'])!=original_manifest['grid_hash']:
        raise ValueError('resolved config/grid changed; resume rejected')
    if workers is not None:
        if workers<1: raise ValueError('workers must be positive')
        cfg['sampling']['workers']=workers
    ensure_threads(cfg['sampling']['native_threads_per_worker'])
    manifest=json.loads((run/'manifest.json').read_text())
    current=environment()
    if compatibility(current)!=manifest['compatibility_hash']:
        raise ValueError('resume code/dependency/environment mismatch: create a new run; snapshots are in provenance/')
    # A checkpoint is the transaction commit marker. Remove orphaned parts.
    done={p.stem for p in (run/'checkpoints').glob('*.json')}
    for table in TABLES:
        for part in (run/'data'/table).glob('part-*.parquet'):
            key=part.stem[5:]
            if key not in done and key not in {'empty','models'} and not key.startswith('replay-'):
                part.unlink()
    staging=run/'staging'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    cases=parameters['grid'];retained=Counter();committed={}
    for key in sorted(done):
        ck=json.loads((run/'checkpoints'/f'{key}.json').read_text());committed[key]=ck
        retained[ck['sampling_case_id']]+=ck.get('retained_failures',0)
    # Compatibility also includes saved artifact hashes, not only source revisions.
    case_rows=read_rows(run,'cases')
    for row in case_rows:
        sid=row['sampling_case_id']
        if sha((run/'circuits'/f'{sid}.stim').read_text())!=row['circuit_hash'] or sha((run/'models'/f'{sid}.dem').read_text())!=row['model_hash']:
            raise ValueError('saved circuit/model was changed; resume rejected')
    rows_by_sid={}
    for row in case_rows:rows_by_sid.setdefault(row['sampling_case_id'],[]).append(row)
    for case in cases:
        sid=case['sampling_case_id']
        metadata=json.loads((run/'models'/f'{sid}.metadata.json').read_text())
        for row in rows_by_sid[sid]:
            detail=metadata['decoder_details'][row['requested_decoder']]
            if detail['effective']!=row['effective_decoder'] or detail['fallback_reason']!=row['fallback_reason']:
                raise ValueError('saved decoder resolution conflicts with cases; resume rejected')
        for descriptor in metadata['decoder_models'].values():
            artifact=descriptor.get('graph_artifact')
            if artifact:
                graph_path=(run/'models'/artifact).resolve()
                if graph_path.parent!=(run/'models').resolve() or sha(graph_path.read_text())!=descriptor['graph_hash']:
                    raise ValueError('saved matching graph was changed; resume rejected')
    manifest['status']='running';manifest['last_resumed']=utc();manifest['workers']=cfg['sampling']['workers']
    atomic_json(run/'manifest.json',manifest)
    count_new=0;stopping=[];started=time.monotonic()
    previous_wall=manifest.get('active_wall_seconds',0.)
    limit=cfg['sampling']['shots_per_case'] if cfg['sampling']['stop_rule']=='fixed_shots' else cfg['sampling']['max_shots']
    pool=ProcessPoolExecutor(max_workers=cfg['sampling']['workers'],mp_context=mp.get_context('spawn'))
    pending=deque();capacity=cfg['sampling']['workers']*cfg['sampling']['max_pending_chunks_per_worker']
    stop_groups=set();counts=Counter();errors=Counter();elapsed_previous=Counter()
    for ck in committed.values():
        group=(ck['sampling_case_id'],ck['replicate'])
        counts[group]+=ck['shots'];errors[group]+=ck['reference_errors'];elapsed_previous[group]+=ck.get('task_elapsed_seconds',0)
    def stopped(group):
        rule=cfg['sampling']['stop_rule']
        return counts[group]>=limit or (rule=='target_errors' and errors[group]>=cfg['sampling']['target_errors']) or (rule=='time_budget' and previous_wall+time.monotonic()-started>=cfg['sampling']['time_budget_seconds'])
    def tasks():
        for case in cases:
            for rep in range(cfg['experiment']['replicates']):
                for chunk,start in enumerate(range(0,limit,cfg['sampling']['chunk_size'])):
                    key=chunk_key(case['sampling_case_id'],rep,chunk)
                    if key not in done:
                        yield key,(case,cfg,rep,chunk,start,min(cfg['sampling']['chunk_size'],limit-start),str(run))
    iterator=iter(tasks());exhausted=False
    try:
        while pending or not exhausted:
            while len(pending)<capacity and not exhausted:
                try: key,task=next(iterator)
                except StopIteration: exhausted=True;break
                group=(task[0]['sampling_case_id'],task[2])
                if stopped(group): continue
                pending.append((key,task,pool.submit(execute,task),time.monotonic()))
            if not pending: break
            key,task,future,task_start=pending.popleft()
            case,_,rep,chunk,start,count,_=task;group=(case['sampling_case_id'],rep)
            if stopped(group):
                future.cancel();continue
            try:
                result=future.result()
            except Exception as exc:
                failure=dict(key=key,sampling_case_id=group[0],replicate=rep,chunk_id=chunk,shots=count,status='worker_failed',error=f'{type(exc).__name__}: {exc}',seed=seed(cfg['experiment']['master_seed'],group[0],rep,chunk))
                atomic_json(run/'logs'/f'{key}-failure.json',failure)
                manifest['failed_chunks'].append(failure);manifest['status']='failed'
                common=dict(sampling_case_id=group[0],replicate=rep,chunk_id=chunk)
                write_table(run/'data/batches'/f'part-{key}.parquet','batches',[dict(common,seed=failure['seed'],shot_start=start,shots=0,requested_shots=count,workers=cfg['sampling']['workers'],status='worker_failed',error=failure['error'])],cfg['storage']['compression'])
                effective_ids={json.loads(r['metadata_json'])['effective_case_id']:r['effective_decoder'] for r in read_rows(run,'cases') if r['sampling_case_id']==group[0]}
                failed_rows=[dict(common,case_id=cid,effective_decoder=name,shots=count,errors=0,valid=0,failed=count,status='worker_failed_unobserved_assigned_shots',scope='terminal_full_history') for cid,name in effective_ids.items()]
                write_table(run/'data/decoder_batches'/f'part-{key}.parquet','decoder_batches',failed_rows,cfg['storage']['compression'])
                atomic_json(run/'manifest.json',manifest)
                raise RuntimeError(f'worker failed for {key}; chunk remains pending for exact-identity retry; see logs') from exc
            # Global bounded failure retention; uniform samples use fixed preselected indices.
            if result['status']!='complete' or result['key']!=key or result['sampling_case_id']!=group[0] or result['replicate']!=rep or result['chunk_id']!=chunk or result['seed']!=seed(cfg['experiment']['master_seed'],group[0],rep,chunk):
                raise ValueError(f'worker returned incorrect chunk identity for {key}')
            commit_start=time.perf_counter_ns()
            if set(result['files'])!=set(TABLES):raise ValueError(f'incomplete staged tables for {key}')
            for table,entry in result['files'].items():
                path=Path(entry['path']).resolve()
                if path.parent!=staging/key or path.name!=f'{table}.parquet':raise ValueError(f'unsafe staged path for {key}')
                info=pq.ParquetFile(path)
                if info.metadata.num_rows!=entry['rows'] or not info.schema_arrow.equals(SCHEMAS[table],check_metadata=True) or file_sha256(path)!=entry['sha256']:
                    raise ValueError(f'corrupt staged {table} for {key}')
            retained_path=Path(result['files']['retained_samples']['path'])
            kept,new_failures=filter_retained_samples(retained_path,
                max(0,cfg['storage']['retained_failure_samples_per_case']-retained[group[0]]),
                cfg['storage']['compression'])
            if new_failures>result['retained_failure_candidates']:
                raise ValueError(f'worker retained-failure count mismatch for {key}')
            result['files']['retained_samples']['rows']=kept
            for table,entry in result['files'].items():
                os.replace(entry['path'],run/'data'/table/f'part-{key}.parquet')
            (staging/key).rmdir()
            ref=cfg['sampling'].get('reference_decoder')
            ref_effective=ref
            if ref is not None:
                ref_effective=next(r['effective_decoder'] for r in read_rows(run,'cases') if r['sampling_case_id']==group[0] and r['requested_decoder']==ref)
            reference_errors=next((r['errors']+r['failed'] for r in result['decoder_batches'] if r['effective_decoder']==ref_effective),0)
            ck=dict(sampling_case_id=group[0],replicate=rep,chunk_id=chunk,shots=count,reference_errors=reference_errors,
                    retained_failures=new_failures,status='complete',seed=result['seed'],task_elapsed_seconds=time.monotonic()-task_start,
                    table_rows={name:entry['rows'] for name,entry in result['files'].items()},staged_bytes=result['staged_bytes'],
                    staging_write_ns=result['staging_write_ns'],setup_timing=result['setup_timing'],
                    raw_chunk_bytes=result['raw_chunk_bytes'],detector_chunk_bytes=result['detector_chunk_bytes'],
                    active_chunk_rss_delta_bytes=result['active_chunk_rss_delta_bytes'],
                    worker_rss_bytes=result['worker_rss_bytes'],worker_peak_rss_bytes=result['worker_peak_rss_bytes'],
                    ipc_payload_bytes=result['ipc_payload_bytes'],parent_commit_ns=time.perf_counter_ns()-commit_start)
            atomic_json(run/'checkpoints'/f'{key}.json',ck)
            retained[group[0]]+=new_failures;done.add(key);counts[group]+=count;errors[group]+=reference_errors
            manifest['completed_chunks']=sorted(done);atomic_json(run/'manifest.json',manifest)
            count_new+=1
            print(f'committed {key}: {count} shots',flush=True)
            if max_new_chunks is not None and count_new>=max_new_chunks:
                manifest['status']='interrupted';break
        else:
            pass
        if manifest['status']=='running': manifest['status']='complete';manifest['ended']=utc()
    except BaseException:
        if manifest['status']=='running':manifest['status']='interrupted'
        raise
    finally:
        for _,_,f,_ in pending: f.cancel()
        pool.shutdown(wait=True,cancel_futures=True)
        shutil.rmtree(staging)
        staging.mkdir()
        manifest['active_wall_seconds']=previous_wall+time.monotonic()-started
        atomic_json(run/'manifest.json',manifest)
    for case in cases:
        for rep in range(cfg['experiment']['replicates']):
            group=(case['sampling_case_id'],rep)
            stopping.append(dict(sampling_case_id=group[0],replicate=rep,stop_rule=cfg['sampling']['stop_rule'],actual_shots=counts[group],
                actual_reference_errors=errors[group],shot_overshoot=max(0,counts[group]-limit),error_overshoot=max(0,errors[group]-cfg['sampling'].get('target_errors',errors[group])),
                status=manifest['status'],elapsed_seconds=manifest['active_wall_seconds'],time_overshoot_seconds=max(0.,manifest['active_wall_seconds']-cfg['sampling'].get('time_budget_seconds',manifest['active_wall_seconds']))))
    write_table(run/'data/stopping.parquet','stopping',stopping,cfg['storage']['compression'])
    return run
