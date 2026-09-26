"""Bounded native-object cache; all physical sampling occurs inside spawned workers."""
from collections import OrderedDict
import hashlib
import os
from time import perf_counter_ns,process_time_ns
import numpy as np
from knill_bench.adapters.decoders import construct
from knill_bench.circuits.builders import build
from knill_bench.config import canonical,digest
from knill_bench.data.provenance import sha
from knill_bench.models import Predictions
from knill_bench.simulation.seeds import seed,selected_indices

CACHE=OrderedDict()


def pack(bits): return np.packbits(bits,bitorder='little').tobytes()


def model(case,cfg):
    key=digest([case,cfg['decoders']])
    if key not in CACHE:
        compiled=build(case);compiled.metadata['basis']=case['basis']
        decoders,aliases,details=construct(compiled,case,cfg)
        CACHE[key]=(compiled,decoders,aliases,details,compiled.circuit.compile_m2d_converter())
        if len(CACHE)>2: CACHE.popitem(last=False)
    CACHE.move_to_end(key)
    return CACHE[key]


def case_id(case,name): return digest([case['sampling_case_id'],name,case.get('decoder_specs',{}).get(name)])


def execute(task):
    case,cfg,rep,chunk,start,count=task
    compiled,decoders,aliases,details,converter=model(case,cfg)
    sid=case['sampling_case_id'];master=cfg['experiment']['master_seed']
    common=dict(sampling_case_id=sid,replicate=rep,chunk_id=chunk)
    tables={k:[] for k in ('batches','decoder_batches','shots','decoder_calls','diagnostics','retained_samples')}
    physical_seed=seed(master,sid,rep,chunk)
    sampler=compiled.circuit.compile_sampler(seed=physical_seed)
    wall=perf_counter_ns();cpu=process_time_ns()
    measurements=sampler.sample(count)
    sw=perf_counter_ns()-wall;sc=process_time_ns()-cpu
    wall=perf_counter_ns()
    syndromes,obs=converter.convert(measurements=measurements,separate_observables=True)
    conversion=perf_counter_ns()-wall
    tables['batches'].append(dict(common,seed=physical_seed,shot_start=start,shots=count,requested_shots=count,
                                 sampling_wall_ns=sw,sampling_cpu_ns=sc,conversion_wall_ns=conversion,pid=os.getpid(),
                                 workers=cfg['sampling']['workers'],status='complete',error=None,
                                 sample_hash=hashlib.sha256(measurements.tobytes()+syndromes.tobytes()+obs.tobytes()).hexdigest()))
    total=cfg['sampling']['shots_per_case'] if cfg['sampling']['stop_rule']=='fixed_shots' else cfg['sampling']['max_shots']
    replicates=cfg['experiment']['replicates']
    latency={i-rep*total for i in selected_indices(master,sid,0,total*replicates,cfg['timing']['latency_sample_count_per_case'],'timing') if rep*total<=i<(rep+1)*total}
    uniform={i-rep*total for i in selected_indices(master,sid,0,total*replicates,cfg['storage']['retained_uniform_samples_per_case'],'retention') if rep*total<=i<(rep+1)*total}
    any_failure=np.zeros(count,dtype=bool)
    predictions={}
    for name,decoder in decoders.items():
        warm=min(count,cfg['timing']['warmup_shots'])
        if warm: decoder.decode_batch(syndromes[:warm],measurements[:warm])
        wall=perf_counter_ns();cpu=process_time_ns()
        try:
            prediction=decoder.decode_batch(syndromes,measurements)
            failure_message=None
        except (ValueError,RuntimeError) as exc:
            # Runtime inference errors are explicit computational failures; never change decoder.
            prediction=Predictions(np.zeros_like(obs,dtype=np.uint8),np.zeros(count,dtype=bool),[None]*count)
            failure_message=f'{type(exc).__name__}: {exc}'
        dw=perf_counter_ns()-wall;dc=process_time_ns()-cpu
        predictions[name]=prediction
        failure=np.any(prediction.logical_flips!=obs,axis=1)&prediction.valid
        any_failure |= failure | ~prediction.valid
        effective_id=case_id(case,name)
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
        for local in range(count):
            index=start+local
            diag=prediction.diagnostics[local] if prediction.diagnostics else {}
            if cfg['storage']['save_shot_results']:
                tables['shots'].append(dict(common,case_id=effective_id,shot_index=index,actual=pack(obs[local]),
                    predicted=pack(prediction.logical_flips[local]) if prediction.valid[local] else None,
                    logical_failure=bool(failure[local]) if prediction.valid[local] else None,
                    decoder_status='valid' if prediction.valid[local] else 'failed',syndrome_weight=int(syndromes[local].sum()),
                    residual_weight=prediction.residual[local],bp_converged=diag.get('bp_converged'),bp_iterations=diag.get('bp_iterations'),lsd_used=diag.get('lsd_used')))
            if index in latency:
                wall=perf_counter_ns();cpu=process_time_ns()
                try:
                    replay=decoder.decode_one(syndromes[local],measurements[local])
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
    failed_retained=0
    for local in range(count):
        index=start+local
        reasons=[]
        if cfg['storage']['save_all_syndromes']: reasons.append('all')
        if index in uniform: reasons.append('uniform')
        if any_failure[local] and failed_retained<cfg['storage']['retained_failure_samples_per_case']:
            reasons.append('failure'); failed_retained+=1
        if reasons:
            tables['retained_samples'].append(dict(common,shot_index=index,syndrome=pack(syndromes[local]),measurements=pack(measurements[local]),actual=pack(obs[local]),
                syndrome_bits=compiled.dem.num_detectors,measurement_bits=compiled.circuit.num_measurements,observable_bits=compiled.dem.num_observables,
                bit_order='little',reason='+'.join(reasons),policy='uniform_without_replacement_and_first_failures',circuit_hash=sha(str(compiled.circuit)),model_hash=sha(str(compiled.dem))))
    # Alias metadata lives in cases. No redundant sample or timing tables.
    return tables
