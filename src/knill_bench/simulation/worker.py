"""Bounded native-object cache; all physical sampling occurs inside spawned workers."""
from collections import OrderedDict
import hashlib
import json
import os
import pickle
from pathlib import Path
try:
    import resource
except ImportError:
    resource=None
from time import perf_counter_ns,process_time_ns
import numpy as np
import stim
from scipy import sparse
from knill_bench.adapters.decoders import construct
from knill_bench.circuits.builders import build
from knill_bench.config import canonical,digest
from knill_bench.data.storage import write_table,file_sha256
from knill_bench.data.storage import SCHEMAS
from knill_bench.data.provenance import sha
from knill_bench.models import Predictions,CompiledExperiment
from knill_bench.simulation.seeds import seed,selected_indices

CACHE=OrderedDict()


def rss_bytes():
    try:lines=Path('/proc/self/status').read_text().splitlines()
    except OSError:return None
    for line in lines:
        if line.startswith('VmRSS:'):return int(line.split()[1])*1024
    return None


def pack(bits): return np.packbits(bits,bitorder='little').tobytes()


def decoder_sparse_bytes(decoders):
    """Count unique Python-visible sparse buffers; opaque native backends are excluded."""
    seen=set();total=0
    for decoder in decoders.values():
        objects=[decoder]
        engine=getattr(decoder,'engine',None)
        if engine is not None:objects.extend(engine.circuit_modules)
        for obj in objects:
            for value in vars(obj).values():
                if not sparse.issparse(value):continue
                for buffer in (value.data,value.indices,value.indptr):
                    root=buffer
                    while isinstance(root.base,np.ndarray):root=root.base
                    if id(root) not in seen:
                        seen.add(id(root));total+=root.nbytes
    return total


def model(case,cfg,run=None):
    key=digest([case,cfg['decoders']])
    if key not in CACHE:
        build_start=perf_counter_ns();rss_before=rss_bytes()
        if run is None or case['protocol']=='knill_hex_dminus2':
            compiled=build(case)
        else:
            sid=case['sampling_case_id'];root=Path(run)
            metadata=json.loads((root/'models'/f'{sid}.metadata.json').read_text())
            metadata['model_artifact_root']=str(root/'models')
            compiled=CompiledExperiment(stim.Circuit.from_file(str(root/'circuits'/f'{sid}.stim')),
                stim.DetectorErrorModel.from_file(str(root/'models'/f'{sid}.dem')),
                metadata['ledger'],metadata['detectors'],metadata['observable_records'],metadata)
        compiled.metadata['basis']=case['basis']
        build_ns=perf_counter_ns()-build_start
        construct_start=perf_counter_ns()
        decoders,aliases,details=construct(compiled,case,cfg)
        construct_ns=perf_counter_ns()-construct_start
        compiled.metadata['runtime_setup_timing']=dict(
            circuit_build_ns=build_ns-compiled.metadata.get('dem_build_ns',0) if case['protocol']=='knill_hex_dminus2' or run is None else None,
            dem_build_ns=compiled.metadata.get('dem_build_ns') if case['protocol']=='knill_hex_dminus2' or run is None else None,
            artifact_load_ns=build_ns if run is not None and case['protocol']!='knill_hex_dminus2' else None,
            decoder_construct_ns=construct_ns,
            native_transition_construct_ns=sum(getattr(d,'native_transition_construct_ns',0) for d in decoders.values()) or None,
            lom_subgraph_construct_ns=sum(getattr(d,'lom_subgraph_construct_ns',0) or 0 for d in decoders.values()) or None,
            bplsd_construct_ns=sum(getattr(d,'bplsd_construct_ns',0) for d in decoders.values()) or None,
            decoder_sparse_matrix_bytes=decoder_sparse_bytes(decoders),
            model_rss_delta_bytes=(rss_bytes()-rss_before) if rss_before is not None else None)
        requires_raw=any(d.kind=='hex_native_pipeline' for d in decoders.values())
        CACHE[key]=(compiled,decoders,aliases,details,compiled.circuit.compile_m2d_converter() if requires_raw else None)
    CACHE.move_to_end(key)
    while len(CACHE)>cfg['sampling'].get('model_cache_size',1): CACHE.popitem(last=False)
    return CACHE[key]


def case_id(case,name): return digest([case['sampling_case_id'],name,case.get('decoder_specs',{}).get(name)])


def execute(task):
    case,cfg,rep,chunk,start,count,*rest=task
    run=Path(rest[0]) if rest else None
    cache_hit=digest([case,cfg['decoders']]) in CACHE
    compiled,decoders,aliases,details,converter=model(case,cfg,run)
    chunk_rss_start=rss_bytes()
    chunk_rss_samples=[chunk_rss_start]
    sid=case['sampling_case_id'];master=cfg['experiment']['master_seed']
    common=dict(sampling_case_id=sid,replicate=rep,chunk_id=chunk)
    tables={k:[] for k in ('batches','decoder_batches','shots','decoder_calls','diagnostics','retained_samples','paired_chunks')}
    shot_columns={field.name:[] for field in SCHEMAS['shots']}
    physical_seed=seed(master,sid,rep,chunk)
    wall=perf_counter_ns();cpu=process_time_ns()
    if converter is None:
        syndromes,obs=compiled.circuit.compile_detector_sampler(seed=physical_seed).sample(shots=count,separate_observables=True)
        measurements=None
    else:
        measurements=compiled.circuit.compile_sampler(seed=physical_seed).sample(count)
    sw=perf_counter_ns()-wall;sc=process_time_ns()-cpu
    wall=perf_counter_ns()
    if converter is not None:
        syndromes,obs=converter.convert(measurements=measurements,separate_observables=True)
    conversion=perf_counter_ns()-wall if converter is not None else None
    chunk_rss_samples.append(rss_bytes())
    sample_digest=hashlib.sha256()
    for array in (measurements,syndromes,obs):
        if array is not None:
            sample_digest.update(memoryview(np.ascontiguousarray(array)).cast('B'))
    tables['batches'].append(dict(common,seed=physical_seed,shot_start=start,shots=count,requested_shots=count,
                                 sampling_wall_ns=sw,sampling_cpu_ns=sc,conversion_wall_ns=conversion,pid=os.getpid(),
                                 workers=cfg['sampling']['workers'],status='complete',error=None,
                                 sample_hash=sample_digest.hexdigest()))
    total=cfg['sampling']['shots_per_case'] if cfg['sampling']['stop_rule']=='fixed_shots' else cfg['sampling']['max_shots']
    replicates=cfg['experiment']['replicates']
    latency={i-rep*total for i in selected_indices(master,sid,0,total*replicates,cfg['timing']['latency_sample_count_per_case'],'timing') if rep*total<=i<(rep+1)*total}
    uniform={i-rep*total for i in selected_indices(master,sid,0,total*replicates,cfg['storage']['retained_uniform_samples_per_case'],'retention') if rep*total<=i<(rep+1)*total}
    latency_locals=sorted(i-start for i in latency if start<=i<start+count)
    any_failure=np.zeros(count,dtype=bool)
    prior=[]
    if cfg['storage']['save_shot_results']:
        actual_packed=np.packbits(obs,axis=1,bitorder='little')
        syndrome_weights=np.count_nonzero(syndromes,axis=1).tolist()
    for decoder_index,(name,decoder) in enumerate(decoders.items()):
        warm=min(count,cfg['timing']['warmup_shots'])
        if warm: decoder.decode_batch(syndromes[:warm],measurements[:warm] if measurements is not None else None)
        wall=perf_counter_ns();cpu=process_time_ns()
        try:
            prediction=decoder.decode_batch(syndromes,measurements)
            failure_message=None
        except (ValueError,RuntimeError) as exc:
            # Runtime inference errors are explicit computational failures; never change decoder.
            prediction=Predictions(np.zeros_like(obs,dtype=np.uint8),np.zeros(count,dtype=bool),[None]*count)
            failure_message=f'{type(exc).__name__}: {exc}'
        dw=perf_counter_ns()-wall;dc=process_time_ns()-cpu
        chunk_rss_samples.append(rss_bytes())
        failure=np.any(prediction.logical_flips!=obs,axis=1)&prediction.valid
        any_failure |= failure | ~prediction.valid
        effective_id=case_id(case,name)
        for other_id,other_valid,other_failure,other_flips in prior:
            both=other_valid & prediction.valid
            first_id,second_id=sorted((other_id,effective_id))
            first_failure,second_failure=(other_failure,failure) if first_id==other_id else (failure,other_failure)
            tables['paired_chunks'].append(dict(common,first_case_id=first_id,second_case_id=second_id,
                paired_valid_shots=int(both.sum()),disagreements=int(np.count_nonzero(np.any(other_flips!=prediction.logical_flips,axis=1)&both)),
                first_only_error=int(np.count_nonzero(first_failure&~second_failure&both)),
                second_only_error=int(np.count_nonzero(second_failure&~first_failure&both))))
        if decoder_index+1<len(decoders):
            prior.append((effective_id,prediction.valid.copy(),failure.copy(),prediction.logical_flips.copy()))
        # Timings are stored once per effective decoder; aliases reference these rows.
        tables['decoder_batches'].append(dict(common,case_id=effective_id,effective_decoder=name,shots=count,
             errors=int(failure.sum()),valid=int(prediction.valid.sum()),failed=int((~prediction.valid).sum()),
             wall_ns=dw if cfg['timing']['collect_batch_times'] else None,cpu_ns=dc if cfg['timing']['collect_batch_times'] else None,
             postprocessing_ns=sum(d.get('postprocessing_ns',0) for d in prediction.diagnostics) or None,
             observables=compiled.dem.num_observables,history_measurements=compiled.circuit.num_measurements,scope='terminal_full_history',
             status='complete' if failure_message is None else failure_message))
        def call_row(phase,mode,bsize,w,c,shot=None,input_size=None,post=None):
            return dict(common,case_id=effective_id,shot_index=shot,phase=phase,input_size=input_size if input_size is not None else (compiled.circuit.num_measurements if decoder.kind=='hex_native_pipeline' else compiled.dem.num_detectors),
                        backend=decoder.kind,batch_size=bsize,timing_mode=mode,wall_ns=w,cpu_ns=c,
                        postprocessing_ns=post,warmup=False,profiling=False,concurrent_load=cfg['sampling']['workers']>1,replay=False)
        if cfg['storage']['save_decoder_calls']:
            tables['decoder_calls'].append(call_row('terminal','throughput',count,dw,dc))
            for event in getattr(decoder,'events',[]):
                tables['decoder_calls'].append(call_row(event['phase'],'throughput',count,event['wall_ns'],event['cpu_ns'],input_size=event['input_size']))
        if cfg['storage']['save_shot_results']:
            def add(field,values): shot_columns[field].extend(values)
            add('sampling_case_id',[sid]*count);add('replicate',[rep]*count);add('chunk_id',[chunk]*count)
            add('case_id',[effective_id]*count);add('shot_index',range(start,start+count))
            predicted_packed=np.packbits(prediction.logical_flips,axis=1,bitorder='little')
            add('actual',(bytes(row) for row in actual_packed))
            add('predicted',(bytes(row) if prediction.valid[i] else None for i,row in enumerate(predicted_packed)))
            add('logical_failure',(bool(failure[i]) if prediction.valid[i] else None for i in range(count)))
            add('decoder_status',('valid' if v else 'failed' for v in prediction.valid))
            add('syndrome_weight',syndrome_weights)
            add('residual_weight',prediction.residual)
            for field in ('bp_converged','bp_iterations','lsd_used'):
                add(field,(d.get(field) for d in prediction.diagnostics) if prediction.diagnostics else [None]*count)
        for local in latency_locals:
            index=start+local
            diag=prediction.diagnostics[local] if prediction.diagnostics else {}
            if index in latency:
                wall=perf_counter_ns();cpu=process_time_ns()
                try:
                    replay=decoder.decode_one(syndromes[local],measurements[local] if measurements is not None else None)
                except (ValueError,RuntimeError):
                    continue  # Throughput failure remains counted. No fabricated latency result.
                lw=perf_counter_ns()-wall;lc=process_time_ns()-cpu
                if not np.array_equal(replay.logical_flips,prediction.logical_flips[local:local+1]):
                    raise RuntimeError('individual and batch decoder predictions disagree')
                if cfg['storage']['save_decoder_calls']:
                    tables['decoder_calls'].append(call_row('terminal','latency',1,lw,lc,shot=index))
                    for event in getattr(decoder,'events',[]):
                        tables['decoder_calls'].append(call_row(event['phase'],'latency',1,event['wall_ns'],event['cpu_ns'],shot=index,input_size=event['input_size']))
                if cfg['diagnostics']['bp_lsd_stats']=='sampled' and diag:
                    profile_start=perf_counter_ns();profile_cpu=process_time_ns()
                    extra=decoder.diagnose(syndromes[local]) if hasattr(decoder,'diagnose') else {}
                    profile_wall=perf_counter_ns()-profile_start;profile_cpu=process_time_ns()-profile_cpu
                    if cfg['storage']['save_decoder_calls']:
                        diagnostic_call=call_row('diagnostic_replay','profiling',1,profile_wall,profile_cpu,shot=index)
                        diagnostic_call['profiling']=True
                        tables['decoder_calls'].append(diagnostic_call)
                    tables['diagnostics'].append(dict(common,case_id=effective_id,shot_index=index,kind='sampled_decoder',
                        residual_weight=prediction.residual[local],bp_converged=diag.get('bp_converged'),bp_iterations=diag.get('bp_iterations'),
                        lsd_used=diag.get('lsd_used'),cluster_count=extra.get('cluster_count'),availability=extra.get('availability','BP public counters only'),
                        details_json=canonical(dict(logical_failure=bool(failure[local]),recovery_weight=diag.get('recovery_weight'),cluster_stats=extra.get('cluster_stats')))))
    failure_locals=set(np.flatnonzero(any_failure)[:cfg['storage']['retained_failure_samples_per_case']].tolist())
    uniform_locals={i-start for i in uniform if start<=i<start+count}
    selected_locals=(range(count) if cfg['storage']['save_all_syndromes'] else sorted(uniform_locals|failure_locals))
    if len(selected_locals):
        circuit_hash=compiled.metadata.get('circuit_hash') or sha(str(compiled.circuit))
        model_hash=compiled.metadata.get('model_hash') or sha(str(compiled.dem))
    for local in selected_locals:
        index=start+local
        reasons=[]
        if cfg['storage']['save_all_syndromes']: reasons.append('all')
        if local in uniform_locals: reasons.append('uniform')
        if local in failure_locals: reasons.append('failure')
        if reasons:
            tables['retained_samples'].append(dict(common,shot_index=index,syndrome=pack(syndromes[local]),measurements=pack(measurements[local]) if measurements is not None else None,actual=pack(obs[local]),
                syndrome_bits=compiled.dem.num_detectors,measurement_bits=compiled.circuit.num_measurements,observable_bits=compiled.dem.num_observables,
                bit_order='little',reason='+'.join(reasons),policy='uniform_without_replacement_and_first_failures',circuit_hash=circuit_hash,model_hash=model_hash))
    # Alias metadata lives in cases. No redundant sample or timing tables.
    tables['shots']=shot_columns
    if run is None:return tables
    key=f'{sid}-r{rep:04d}-c{chunk:08d}'
    stage=run/'staging'/key
    stage.mkdir(parents=True,exist_ok=True)
    staged={}
    stage_start=perf_counter_ns()
    for table,rows in tables.items():
        path=stage/f'{table}.parquet'
        write_table(path,table,rows,cfg['storage']['compression'])
        staged[table]=dict(path=str(path),rows=len(rows['case_id']) if table=='shots' else len(rows),sha256=file_sha256(path),bytes=path.stat().st_size)
    staging_ns=perf_counter_ns()-stage_start
    chunk_rss_samples.append(rss_bytes())
    observed=max(v for v in chunk_rss_samples if v is not None) if any(v is not None for v in chunk_rss_samples) else None
    result=dict(key=key,sampling_case_id=sid,replicate=rep,chunk_id=chunk,seed=physical_seed,
                status='complete',files=staged,decoder_batches=tables['decoder_batches'],
                retained_failure_candidates=len(failure_locals),
                staged_bytes=sum(v['bytes'] for v in staged.values()),staging_write_ns=staging_ns,
                setup_timing=None if cache_hit else compiled.metadata['runtime_setup_timing'],
                raw_chunk_bytes=0 if measurements is None else measurements.nbytes,
                detector_chunk_bytes=syndromes.nbytes,worker_rss_bytes=rss_bytes(),
                active_chunk_rss_delta_bytes=max(0,observed-chunk_rss_start) if observed is not None and chunk_rss_start is not None else None,
                worker_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 if resource else None)
    result['ipc_payload_bytes']=len(pickle.dumps(result,protocol=5))
    return result
