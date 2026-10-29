"""Fixed-R setup and worker delegation for the existing ordered chunk runner.

No process pool or seed scheme is implemented here. Native models share the
worker's bounded CACHE. Workers stage parts; the existing parent owns ordered
publication and checkpoint markers. Truth crosses only the evaluator boundary.
"""
from collections import Counter
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import time
import uuid

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import stim

from knill_bench.adapters.decoders import describe, construct
from knill_bench.circuits.builders import build
from knill_bench.config import canonical, digest, grid
from knill_bench.data.preparation import GAP_EDGES, TABLES
from knill_bench.data.provenance import environment, compatibility, utc, git
from knill_bench.data.storage import atomic_json, write_table, read_rows, SCHEMAS, file_sha256
from knill_bench.decoding.temporal_artifact import write_temporal_model
from knill_bench.preparation import (
    PreparationLabels, PreparationSampleMap, preparation_sample_map, split_preparation_samples,
)
from .preparation_metrics import evaluate_preparation, summarize_preparation
from .seeds import seed, selected_indices

SAMPLE_HASH_VERSION='preparation_bool_rows_little_endian_v1'


def is_preparation(cfg):
    return any(p.get('id')=='surface_prep_fixed' for p in cfg['protocols'])


def sample_hash(batch):
    """Canonical bool semantics, shapes, ordered names and little-endian rows."""
    arrays=(('online_x_detectors',batch.observations.online_x_detectors),
            ('online_z_detectors',batch.observations.online_z_detectors),
            ('truth_tau_x',batch.truth.tau_x),('truth_tau_z',batch.truth.tau_z),
            ('truth_logical_z',batch.truth.logical_z))
    h=hashlib.sha256()
    descriptor=canonical(dict(version=SAMPLE_HASH_VERSION,dtype='bool',bit_order='little',row_padding='zero',
        arrays=[dict(name=n,shape=list(a.shape)) for n,a in arrays])).encode()
    h.update(len(descriptor).to_bytes(8,'little'));h.update(descriptor)
    for _,array in arrays:
        if array.dtype!=np.bool_ or array.ndim!=2: raise ValueError('sample hash requires bool matrices')
        data=np.packbits(array,axis=1,bitorder='little').tobytes()
        h.update(len(data).to_bytes(8,'little'));h.update(data)
    return h.hexdigest()


def map_from_json(value):
    if set(value)!={'num_detectors','num_observables','online_x_detector_ids','online_z_detector_ids','labels'}:
        raise ValueError('invalid saved preparation sample map')
    labels=value['labels']
    if set(labels)!={'tau_x','tau_z','logical_z'}: raise ValueError('invalid saved preparation labels')
    return PreparationSampleMap(value['num_detectors'],value['num_observables'],
        tuple(value['online_x_detector_ids']),tuple(value['online_z_detector_ids']),
        PreparationLabels(*(tuple(labels[k]) for k in ('tau_x','tau_z','logical_z'))))


def prepare(config_path,cfg):
    from .runner import ensure_threads
    from .worker import case_id
    ensure_threads(cfg['sampling']['native_threads_per_worker'])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run=Path(cfg['experiment']['output_root']).resolve()/f'{stamp}_{uuid.uuid4().hex[:10]}'
    run.mkdir(parents=True)
    shutil.copyfile(config_path,run/'config.original.yaml')
    for name in ('circuits','models','data','plots','logs','checkpoints','staging'): (run/name).mkdir()
    for table in TABLES:
        write_table(run/'data'/table/'part-empty.parquet',table,[],cfg['storage']['compression'])
    env=environment(run)
    repo=Path(__file__).resolve().parents[3]
    env['bench_git']=dict(head=git(repo,'rev-parse','HEAD'),branch=git(repo,'branch','--show-current'),
                         dirty=bool(git(repo,'status','--porcelain')))
    atomic_json(run/'environment.json',env)
    cases=list({c['sampling_case_id']:c for c in grid(cfg)}.values())
    parameters=dict(schema_version=1,preparation_result_version=1,config=cfg,grid=cases,
        config_hash=digest(cfg),batch_partition=cfg['sampling']['chunk_size'],seed_derivation_version=1,
        sample_hash_version=SAMPLE_HASH_VERSION,gap_bin_edges=list(GAP_EDGES),
        gap_interval='[left,right); final [64,+infinity); unavailable separate',tables=list(TABLES))
    atomic_json(run/'parameters.json',parameters)
    manifest=dict(schema_version=1,preparation_result_version=1,status='building',started=utc(),ended=None,
        compatibility_hash=compatibility(env),config_hash=digest(cfg),grid_hash=digest(cases),
        completed_chunks=[],failed_chunks=[],commit_policy='ordered_chunks; checkpoint is publication marker')
    atomic_json(run/'manifest.json',manifest)
    rows=[]
    for case in cases:
        sid=case['sampling_case_id']; begin=time.perf_counter_ns()
        compiled=build(case); build_ns=time.perf_counter_ns()-begin
        aliases,details,models,graphs,timing=describe(compiled,case,cfg)
        mapping=asdict(preparation_sample_map(compiled))
        for role,circuit in (('production',compiled.circuit),('nominal',compiled.model_circuit),
                             ('completed',compiled.completed_circuit)):
            (run/'circuits'/f'{sid}.{role}.stim').write_text(str(circuit))
        for role,dem in (('production',compiled.dem),('nominal',compiled.model_dem),('completed',compiled.completed_dem)):
            (run/'models'/f'{sid}.{role}.dem').write_text(str(dem))
        for name,(x,z) in graphs.items():
            base=f'{sid}-{digest([name,"preparation"])}'
            xfile=f'{base}.x.json';zfile=f'{base}.z.json'
            write_temporal_model(run/'models'/xfile,x)
            atomic_json(run/'models'/zfile,z.to_artifact())
            models[name].update(x_artifact=xfile,z_artifact=zfile)
        metadata=dict(compiled.metadata,preparation_result_version=1,sample_map=mapping,
            maps_hash=digest(mapping),decoder_models=models,decoder_details=details,
            production_circuit=f'{sid}.production.stim',circuit_hash=file_sha256(run/'circuits'/f'{sid}.production.stim'),
            ledger=[asdict(r) for r in compiled.ledger],completed_ledger=[asdict(r) for r in compiled.completed_ledger],
            detectors=[asdict(r) for r in compiled.detectors],completed_detectors=[asdict(r) for r in compiled.completed_detectors],
            observables=[asdict(r) for r in compiled.observables],completed_observables=[asdict(r) for r in compiled.completed_observables],
            setup_timing=dict(circuit_and_dem_build_ns=build_ns,**timing),
            validity_policy='X baseline for X; Z baseline for Z/logical; both for code/joint; all three for gap acceptance',
            sample_hash_version=SAMPLE_HASH_VERSION,boundary_freezing='all_completed_individual_degree_one',
            gap_definition='same_syndrome_all_spatial_fixed_both_temporal_parities_flipped_v1',
            retention_policy='uniform_without_replacement_and_first_global_failures',
            raw_fault_trajectories_saved=False)
        atomic_json(run/'models'/f'{sid}.metadata.json',metadata)
        for name in case['decoders']:
            rows.append(dict(case_id=case_id(case,name),sampling_case_id=sid,protocol=case['protocol'],
                distance=case['distance'],rounds=case['rounds'],p=case['p'],decoding_p=case['decoding_p'],decoder=name,
                circuit_hash=metadata['circuit_hash'],model_hash=models[name]['model_sha256'],metadata_json=canonical(metadata)))
        print(f"built surface_prep_fixed d={case['distance']} R={case['rounds']}",flush=True)
    write_table(run/'data/preparation_cases.parquet','preparation_cases',rows,cfg['storage']['compression'])
    artifacts=[run/'parameters.json',run/'environment.json',run/'config.original.yaml',run/'data/preparation_cases.parquet']
    artifacts+=list((run/'circuits').iterdir())+list((run/'models').iterdir())
    manifest['preparation_artifacts']={str(p.relative_to(run)):file_sha256(p) for p in artifacts}
    for path in artifacts:
        with path.open('rb') as handle:os.fsync(handle.fileno())
    manifest['status']='built';atomic_json(run/'manifest.json',manifest)
    return run


def validate_run(run,parameters,manifest):
    """Read-only preflight BEFORE orphan/staging cleanup, including committed parts."""
    from .runner import chunk_key
    run=Path(run).resolve()
    if manifest.get('preparation_result_version')!=1 or parameters.get('preparation_result_version')!=1:
        raise ValueError('unsupported preparation result schema')
    for name,expected in manifest.get('preparation_artifacts',{}).items():
        path=(run/name).resolve()
        if not path.is_relative_to(run) or not path.is_file() or file_sha256(path)!=expected:
            raise ValueError(f'saved preparation artifact changed: {name}; resume rejected')
    if not manifest.get('preparation_artifacts'): raise ValueError('missing preparation artifacts')
    cfg=parameters['config']
    if parameters['batch_partition']!=cfg['sampling']['chunk_size'] or parameters['sample_hash_version']!=SAMPLE_HASH_VERSION:
        raise ValueError('preparation chunk partition/sample semantics changed')
    cases={c['sampling_case_id']:c for c in parameters['grid']}; groups={}
    checkpoint_names={p.stem for p in (run/'checkpoints').glob('*.json')}
    if not set(manifest['completed_chunks']).issubset(checkpoint_names):
        raise ValueError('published preparation checkpoint is missing')
    for ckpath in sorted((run/'checkpoints').glob('*.json')):
        ck=json.loads(ckpath.read_text());sid=ck['sampling_case_id']; rep=ck['replicate'];chunk=ck['chunk_id']
        limit=cfg['sampling']['shots_per_case'];size=cfg['sampling']['chunk_size']
        if (sid not in cases or type(rep) is not int or not 0<=rep<cfg['experiment']['replicates']
                or type(chunk) is not int or not 0<=chunk<(limit+size-1)//size
                or ckpath.stem!=chunk_key(sid,rep,chunk) or ck['shots']!=min(size,limit-chunk*size)
                or ck['seed']!=seed(cfg['experiment']['master_seed'],sid,rep,chunk)
                or set(ck.get('table_files',{}))!=set(TABLES)):
            raise ValueError('invalid preparation checkpoint/chunk identity')
        groups.setdefault((sid,rep),[]).append(chunk)
        for table,entry in ck['table_files'].items():
            path=run/'data'/table/f'part-{ckpath.stem}.parquet'
            if not path.exists() or file_sha256(path)!=entry['sha256']:
                raise ValueError('committed preparation part changed or missing')
            info=pq.ParquetFile(path)
            if info.metadata.num_rows!=entry['rows'] or not info.schema_arrow.equals(SCHEMAS[table],check_metadata=True):
                raise ValueError('committed preparation schema/count changed')
        batches=pq.read_table(run/'data/batches'/f'part-{ckpath.stem}.parquet').to_pylist()
        if len(batches)!=1 or any(batches[0][k]!=ck[k] for k in ('sampling_case_id','replicate','chunk_id','seed','shots','sample_hash')):
            raise ValueError('preparation checkpoint/sample identity changed')
    if any(sorted(ids)!=list(range(len(ids))) for ids in groups.values()):
        raise ValueError('preparation committed chunks must form contiguous prefixes')


def validate_staged(result,case,cfg,count,start):
    """Validate bounded counter payloads and retained identities before promotion."""
    from .worker import case_id
    rows=pq.read_table(result['files']['preparation_chunks']['path']).to_pylist()
    expected={case_id(case,n):n for n in case['decoders']}
    if len(rows)!=len(expected) or {r['case_id'] for r in rows}!=set(expected):
        raise ValueError('incomplete preparation decoder counters')
    for row in rows:
        summary=json.loads(row['summary_json']);bins=json.loads(row['gap_bins_json'])
        if (row['decoder']!=expected[row['case_id']] or row['shots']!=count or row['assigned_shots']!=count
                or summary['shots']!=count or sum(b['summary']['shots'] for b in bins)!=count
                or any(not 0<=row[k]<=count for k in ('baseline_valid','complementary_valid','z_decoder_valid',
                                                     'sign_miss_x','sign_miss_z','code_sign_miss','logical_z_errors'))):
            raise ValueError('preparation assigned/valid/event counters disagree')
    expected_shots=count*len(expected) if cfg['storage']['save_shot_results'] else 0
    if result['files']['preparation_shots']['rows']!=expected_shots:
        raise ValueError('preparation compact shot count mismatch')
    for row in pq.read_table(result['files']['preparation_retained']['path']).to_pylist():
        if not start<=row['shot_index']<start+count or row['sample_hash']!=result['sample_hash']:
            raise ValueError('retained preparation sample identity mismatch')


@dataclass
class _Runtime:
    circuit: stim.Circuit
    sample_map: PreparationSampleMap
    metadata: dict


def model(case,cfg,run,cache):
    if run is None: raise ValueError('preparation workers require saved model artifacts')
    from .worker import rss_bytes
    key=digest(['preparation',str(Path(run).resolve()),case,cfg['decoders']])
    if key not in cache:
        begin=time.perf_counter_ns(); before=rss_bytes();root=Path(run)
        metadata=json.loads((root/'models'/f"{case['sampling_case_id']}.metadata.json").read_text())
        metadata['model_artifact_root']=str(root/'models')
        circuit=stim.Circuit.from_file(str(root/'circuits'/metadata['production_circuit']))
        mapping=map_from_json(metadata['sample_map'])
        if circuit.num_detectors!=mapping.num_detectors or circuit.num_observables!=mapping.num_observables:
            raise ValueError('production circuit/sample-map dimensions changed')
        runtime=_Runtime(circuit,mapping,metadata);load_ns=time.perf_counter_ns()-begin
        begin=time.perf_counter_ns();decoders,aliases,details=construct(runtime,case,cfg)
        setup=dict(artifact_load_ns=load_ns,decoder_construct_ns=time.perf_counter_ns()-begin,
            graph_construct_count=sum(int(m.matcher is not None)+int(m._debug_matcher is not None)
                for d in decoders.values() for m in (d.x_core._baseline,d.x_core._comparison,d.z_matcher)),
            decoder_sparse_matrix_bytes=sum(sum(a.nbytes for a in (m.data,m.indices,m.indptr))
                for d in decoders.values() for m in (d.x_model.h_completed,d.x_model.feature_map,d.z_model.h,d.z_model.feature_map)),
            model_rss_delta_bytes=max(0,(rss_bytes() or 0)-(before or 0)))
        metadata['runtime_setup_timing']=setup
        cache[key]=(runtime,decoders,aliases,details,None)
    cache.move_to_end(key)
    while len(cache)>cfg['sampling']['model_cache_size']: cache.popitem(last=False)
    return cache[key]


def _summary_bins(evaluation):
    indices=np.full(len(evaluation.gap),-1,dtype=int)
    good=np.isfinite(evaluation.gap)
    indices[good]=np.searchsorted(GAP_EDGES,evaluation.gap[good],side='right')-1
    rows=[]
    for index in range(-1,len(GAP_EDGES)):
        mask=indices==index
        subset=replace(evaluation,**{f.name:getattr(evaluation,f.name)[mask] for f in fields(evaluation)})
        summary=summarize_preparation(subset)
        rows.append(dict(bin=index,left=None if index<0 else GAP_EDGES[index],
            right=GAP_EDGES[index+1] if 0<=index<len(GAP_EDGES)-1 else None,summary=summary))
    return rows


def execute(task):
    from .worker import model as cached_model, CACHE, rss_bytes, case_id, pack, resource
    case,cfg,rep,chunk,start,count,run=task;run=Path(run)
    key_cache=digest(['preparation',str(run.resolve()),case,cfg['decoders']]);hit=key_cache in CACHE
    runtime,decoders,_,_,_=cached_model(case,cfg,run)
    sid=case['sampling_case_id'];master=cfg['experiment']['master_seed']; physical_seed=seed(master,sid,rep,chunk)
    common=dict(sampling_case_id=sid,replicate=rep,chunk_id=chunk)
    rss_start=rss_bytes();begin=time.perf_counter_ns()
    sampler=runtime.circuit.compile_detector_sampler(seed=physical_seed)
    compile_ns=time.perf_counter_ns()-begin;begin=time.perf_counter_ns()
    det,obs=sampler.sample(count,separate_observables=True)
    sampling_ns=time.perf_counter_ns()-begin;begin=time.perf_counter_ns()
    batch=split_preparation_samples(runtime.sample_map,det,obs)
    split_ns=time.perf_counter_ns()-begin; signature=sample_hash(batch)
    total=cfg['sampling']['shots_per_case']; reps=cfg['experiment']['replicates']
    def local_indices(n,stream):
        return {i-rep*total-start for i in selected_indices(master,sid,0,total*reps,n,stream)
                if rep*total+start<=i<rep*total+start+count}
    uniform=local_indices(cfg['storage']['retained_uniform_samples_per_case'],'retention')
    latency=local_indices(cfg['timing']['latency_sample_count_per_case'],'timing')
    tables={name:[] for name in TABLES};predictions={};evaluations={};failures=np.zeros(count,dtype=bool)
    tables['batches']=[dict(common,seed=physical_seed,shot_start=start,shots=count,requested_shots=count,
        sampling_wall_ns=sampling_ns,sampling_cpu_ns=None,conversion_wall_ns=split_ns,pid=os.getpid(),
        workers=cfg['sampling']['workers'],status='complete',sample_hash=signature)]
    x=batch.observations.online_x_detectors;z=batch.observations.online_z_detectors
    for name,decoder in decoders.items():
        cid=case_id(case,name);warm=min(count,cfg['timing']['warmup_shots']);warm_ns=0
        if warm:
            begin=time.perf_counter_ns();decoder.decode_batch(x[:warm],z[:warm]);warm_ns=time.perf_counter_ns()-begin
        prediction=decoder.decode_batch(x,z);predictions[name]=prediction
        timings=decoder.last_decode_timings_ns.copy();begin=time.perf_counter_ns()
        evaluation=evaluate_preparation(batch.truth,prediction);evaluations[name]=evaluation;summary=summarize_preparation(evaluation)
        bins=_summary_bins(evaluation);eval_ns=time.perf_counter_ns()-begin
        failures |= evaluation.code_space_miss | evaluation.logical_z_error | ~evaluation.eligible
        tables['preparation_chunks'].append(dict(common,case_id=cid,decoder=name,shots=count,assigned_shots=count,
            baseline_valid=int(prediction.baseline_valid.sum()),complementary_valid=int(prediction.complementary_valid.sum()),
            z_decoder_valid=int(prediction.z_decoder_valid.sum()),sign_miss_x=int(evaluation.sign_miss_x.sum()),
            sign_miss_z=int(evaluation.sign_miss_z.sum()),code_sign_miss=int(evaluation.code_space_miss.sum()),
            sign_bit_errors_x=int(evaluation.error_bits_x.sum()),sign_bit_errors_z=int(evaluation.error_bits_z.sum()),
            logical_z_errors=int(evaluation.logical_z_error.sum()),summary_json=canonical(summary),gap_bins_json=canonical(bins),
            warmup_ns=warm_ns,x_baseline_ns=timings['x_baseline'],x_complementary_ns=timings['x_complementary'],
            z_decode_ns=timings['z_prefix'],decode_overhead_ns=max(0,timings['total']-timings['x_baseline']-timings['x_complementary']-timings['z_prefix']),
            evaluation_ns=eval_ns,status='complete'))
        if cfg['storage']['save_shot_results']:
            columns={f.name:[common.get(f.name)]*count for f in SCHEMAS['preparation_shots']}
            columns.update(case_id=[cid]*count,shot_index=list(range(start,start+count)),
                baseline_valid=prediction.baseline_valid.tolist(),complementary_valid=prediction.complementary_valid.tolist(),
                z_decoder_valid=prediction.z_decoder_valid.tolist(),status=prediction.status.tolist())
            for field,values,valid in (
                ('sign_miss_x',evaluation.sign_miss_x,evaluation.x_valid),('sign_miss_z',evaluation.sign_miss_z,evaluation.z_valid),
                ('code_sign_miss',evaluation.code_space_miss,evaluation.code_valid),('logical_z_error',evaluation.logical_z_error,evaluation.logical_valid),
                ('sign_bit_errors_x',evaluation.error_bits_x.sum(axis=1),evaluation.x_valid),
                ('sign_bit_errors_z',evaluation.error_bits_z.sum(axis=1),evaluation.z_valid),
                ('baseline_weight',prediction.baseline_weight,prediction.baseline_valid),
                ('complementary_weight',prediction.complementary_weight,prediction.complementary_valid),
                ('gap',prediction.gap,prediction.complementary_valid)):
                columns[field]=pa.array(values,mask=~valid,type=SCHEMAS['preparation_shots'].field(field).type)
            # Build one Arrow table per chunk from columns, never shot dataclasses.
            if isinstance(tables['preparation_shots'],list):tables['preparation_shots']={field:[] for field in columns}
            for field,values in columns.items():
                tables['preparation_shots'][field].append(pa.array(values,type=SCHEMAS['preparation_shots'].field(field).type))
        if cfg['storage']['save_decoder_calls']:
            for phase,key in (('x_baseline','x_baseline'),('x_complementary','x_complementary'),('z_prefix','z_prefix')):
                tables['preparation_calls'].append(dict(common,case_id=cid,phase=phase,shots=count,wall_ns=timings[key],replay=False,warmup=False))
            if warm: tables['preparation_calls'].append(dict(common,case_id=cid,phase='warmup',shots=warm,wall_ns=warm_ns,replay=False,warmup=True))
        for local in sorted(latency):
            begin=time.perf_counter_ns();single=decoder.decode_one(x[local],z[local]);elapsed=time.perf_counter_ns()-begin
            for field in ('tau_x_prediction','tau_z_prediction','logical_z_prediction','baseline_weight',
                          'complementary_weight','gap','baseline_valid','complementary_valid','z_decoder_valid','status'):
                actual=getattr(single,field);expected=getattr(prediction,field)[local:local+1]
                agrees=np.array_equal(actual,expected) if field=='status' else np.array_equal(actual,expected,equal_nan=True)
                if not agrees:
                    raise RuntimeError('preparation batch/single replay mismatch')
            if cfg['storage']['save_decoder_calls']:
                tables['preparation_calls'].append(dict(common,case_id=cid,shot_index=start+local,phase='latency',shots=1,wall_ns=elapsed,replay=True,warmup=False))
    if len(evaluations)>1:
        from .preparation_metrics import paired_counts
        first=tables['preparation_chunks'][0]
        summary=json.loads(first['summary_json']);summary['paired_comparisons']=paired_counts(evaluations)
        first['summary_json']=canonical(summary)
    failure_locals=set(np.flatnonzero(failures)[:cfg['storage']['retained_failure_samples_per_case']].tolist())
    def nullable(value): return float(value) if np.isfinite(value) else None
    for local in sorted(uniform|failure_locals):
        details={}
        for name,pred in predictions.items():
            decoder=decoders[name];diag=pred.diagnostics
            details[name]=dict(case_id=case_id(case,name),model_sha256=decoder.model_sha256,output_mode=decoder.output_mode,
                tau_x_prediction=pack(pred.tau_x_prediction[local]).hex(),tau_z_prediction=pack(pred.tau_z_prediction[local]).hex(),
                logical_z_prediction=pack(pred.logical_z_prediction[local]).hex(),gap=nullable(pred.gap[local]),
                baseline_weight=nullable(pred.baseline_weight[local]),complementary_weight=nullable(pred.complementary_weight[local]),
                baseline_valid=bool(pred.baseline_valid[local]),complementary_valid=bool(pred.complementary_valid[local]),
                z_decoder_valid=bool(pred.z_decoder_valid[local]),status=str(pred.status[local]),
                frozen_original_columns=list(diag.frozen_original_columns),baseline_frozen=pack(diag.baseline_frozen[local]).hex(),
                baseline_past=bool(diag.baseline_past[local]),baseline_future=bool(diag.baseline_future[local]))
            if pred.debug is not None:
                details[name].update(baseline_errors=pack(decoder.x_model.expand_errors(pred.debug.baseline_errors[local:local+1])[0]).hex(),
                    complementary_errors=pack(decoder.x_model.expand_errors(pred.debug.complementary_errors[local:local+1])[0]).hex(),
                    debug_matches_compact=bool(pred.debug.debug_matches_compact[local]),
                    z_errors=pack(decoder.z_model.expand_errors(diag.z_errors[local:local+1])[0]).hex())
        tables['preparation_retained'].append(dict(common,shot_index=start+local,
            online_x=pack(x[local]),online_z=pack(z[local]),truth_tau_x=pack(batch.truth.tau_x[local]),
            truth_tau_z=pack(batch.truth.tau_z[local]),truth_logical_z=pack(batch.truth.logical_z[local]),
            decoder_results_json=canonical(details),reason='+'.join(r for r,yes in (('uniform',local in uniform),('failure',local in failure_locals)) if yes),
            sample_hash=signature,circuit_hash=runtime.metadata['circuit_hash'],maps_hash=runtime.metadata['maps_hash']))
    key=f'{sid}-r{rep:04d}-c{chunk:08d}';stage=run/'staging'/key;stage.mkdir(parents=True,exist_ok=True)
    staged={};begin=time.perf_counter_ns()
    for table,rows in tables.items():
        if isinstance(rows,dict):
            rows={field:pa.chunked_array(chunks,type=SCHEMAS[table].field(field).type) for field,chunks in rows.items()}
        path=stage/f'{table}.parquet';write_table(path,table,rows,cfg['storage']['compression'])
        staged[table]=dict(path=str(path),rows=pq.ParquetFile(path).metadata.num_rows,sha256=file_sha256(path),bytes=path.stat().st_size)
    rss_end=rss_bytes()
    result=dict(key=key,sampling_case_id=sid,replicate=rep,chunk_id=chunk,seed=physical_seed,status='complete',files=staged,
        decoder_batches=[],sample_hash=signature,sampler_compile_ns=compile_ns,sampling_ns=sampling_ns,split_ns=split_ns,
        retained_failure_candidates=len(failure_locals),staged_bytes=sum(v['bytes'] for v in staged.values()),
        staging_write_ns=time.perf_counter_ns()-begin,setup_timing=None if hit else runtime.metadata['runtime_setup_timing'],
        raw_chunk_bytes=0,detector_chunk_bytes=det.nbytes+obs.nbytes,worker_rss_bytes=rss_end,
        active_chunk_rss_delta_bytes=max(0,(rss_end or 0)-(rss_start or 0)),
        worker_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 if resource else None)
    result['ipc_payload_bytes']=len(pickle.dumps(result,protocol=5))
    return result
