"""Versioned, explicitly nullable Arrow tables and atomic single-writer parts."""
import json
import os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

S=pa.string(); I=pa.int64(); F=pa.float64(); B=pa.bool_(); BIN=pa.binary()
COMMON=[('sampling_case_id',S),('replicate',I),('chunk_id',I)]
SCHEMAS={
 'cases': [('case_id',S),('sampling_case_id',S),('protocol',S),('distance',I),('basis',S),('p',F),('cycles',I),('prep_rounds',I),('post_gate_rounds',I),('post_gate_scope',S),('geometry',S),('boundary_id',S),('noise_id',S),('schedule_id',S),('rates_json',S),('requested_decoder',S),('effective_decoder',S),('decoder_kind',S),('decoder_parameters_json',S),('fallback_reason',S),('validation_status',S),('circuit_hash',S),('model_hash',S),('metadata_json',S)],
 'batches':COMMON+[('seed',pa.uint64()),('shot_start',I),('shots',I),('requested_shots',I),('sampling_wall_ns',I),('sampling_cpu_ns',I),('conversion_wall_ns',I),('pid',I),('workers',I),('status',S),('error',S),('sample_hash',S)],
 'decoder_batches':COMMON+[('case_id',S),('effective_decoder',S),('shots',I),('errors',I),('valid',I),('failed',I),('wall_ns',I),('cpu_ns',I),('postprocessing_ns',I),('observables',I),('history_measurements',I),('scope',S),('status',S)],
 'shots':COMMON+[('case_id',S),('shot_index',I),('actual',BIN),('predicted',BIN),('logical_failure',B),('decoder_status',S),('syndrome_weight',I),('residual_weight',I),('bp_converged',B),('bp_iterations',I),('lsd_used',B)],
 'decoder_calls':COMMON+[('case_id',S),('shot_index',I),('phase',S),('cycle',I),('block',I),('sector',S),('input_size',I),('backend',S),('batch_size',I),('timing_mode',S),('wall_ns',I),('cpu_ns',I),('preprocessing_ns',I),('postprocessing_ns',I),('warmup',B),('profiling',B),('concurrent_load',B),('replay',B)],
 'diagnostics':COMMON+[('case_id',S),('shot_index',I),('kind',S),('detectors',I),('faults',I),('observables',I),('h_nnz',I),('l_nnz',I),('hyperedges',I),('residual_weight',I),('bp_converged',B),('bp_iterations',I),('lsd_used',B),('cluster_count',I),('availability',S),('details_json',S)],
 'retained_samples':COMMON+[('shot_index',I),('syndrome',BIN),('measurements',BIN),('actual',BIN),('syndrome_bits',I),('measurement_bits',I),('observable_bits',I),('bit_order',S),('reason',S),('policy',S),('circuit_hash',S),('model_hash',S)],
 'paired_chunks':COMMON+[('first_case_id',S),('second_case_id',S),('paired_valid_shots',I),('disagreements',I),('first_only_error',I),('second_only_error',I)],
 'summary':[('case_id',S),('protocol',S),('distance',I),('basis',S),('p',F),('cycles',I),('requested_decoder',S),('effective_decoder',S),('shots',I),('errors',I),('valid',I),('failed',I),('ler',F),('ci_low',F),('ci_high',F),('interval_kind',S),('computational_failure_rate',F),('total_task_failure_rate',F),('decode_wall_seconds',F),('decode_cpu_seconds',F),('throughput_shots_per_second',F),('amortized_wall_ns_per_shot',F),('work_ns_per_cycle',F),('latency_count',I),('latency_mean_ns',F),('latency_std_ns',F),('latency_median_ns',F),('latency_p90_ns',F),('latency_p95_ns',F),('latency_p99_ns',F),('latency_max_ns',F),('peak_live_qubits',I),('elapsed_time',F),('spacetime_volume',F),('timing_scope',S)],
 'paired_disagreements':[('sampling_case_id',S),('first_case_id',S),('second_case_id',S),('paired_valid_shots',I),('disagreements',I),('first_only_error',I),('second_only_error',I)],
 'latency_statistics': [('case_id',S),('backend',S),('replay',B),('concurrent_load',B),('clock',S),('count',I),('mean_ns',F),('std_ns',F),('median_ns',F),('p90_ns',F),('p95_ns',F),('p99_ns',F),('max_ns',F)],
 'decoder_diagnostics_summary': [('case_id',S),('logical_failure',B),('samples',I),('bp_counter_samples',I),('bp_converged_count',I),('lsd_used_count',I),('mean_bp_iterations',F),('cluster_counter_samples',I),('mean_cluster_count',F)],
 'native_cost_summary': [('case_id',S),('phase',S),('scope',S),('calls',I),('shots',I),('wall_ns',I),('cpu_ns',I),('hierarchy',S)],
 'model_cost': [('case_id',S),('detectors',I),('faults',I),('hyperedges',I),('selected_detectors',I),('amortized_wall_ns',F)],
 'fault_audit': [('sampling_case_id',S),('case_id',S),('distance',I),('basis',S),('cycles',I),('protocol',S),('event_id',I),('physical_locations',I),('fault_weight',I),('syndrome',BIN),('actual',BIN),('predicted',BIN),('decoder_valid',B),('logical_failure',B),('undetectable_logical',B),('ambiguous_single_fault_syndrome',B),('representative_location',S),('validation_scope',S)],
 'stopping':[('sampling_case_id',S),('replicate',I),('stop_rule',S),('actual_shots',I),('actual_reference_errors',I),('shot_overshoot',I),('error_overshoot',I),('status',S),('elapsed_seconds',F),('time_overshoot_seconds',F)],
}
SCHEMAS={k:pa.schema(v,metadata={b'knill_bench_schema_version':b'1',b'table':k.encode()}) for k,v in SCHEMAS.items()}


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def write_table(path,name,rows,compression='zstd'):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    table=pa.Table.from_pydict(rows,schema=SCHEMAS[name]) if isinstance(rows,dict) else pa.Table.from_pylist(rows,schema=SCHEMAS[name])
    tmp=path.with_name(path.name+'.tmp')
    pq.write_table(table,tmp,compression=None if compression=='none' else compression,
                   row_group_size=1024 if name=='retained_samples' else None)
    with tmp.open('rb') as f: os.fsync(f.fileno())
    os.replace(tmp,path)


def file_sha256(path):
    import hashlib
    digest=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()


def filter_retained_samples(path,available_failures,compression='zstd',batch_size=1024):
    """Apply the global failure quota without loading an all-syndrome part."""
    path=Path(path)
    tmp=path.with_name(path.name+'.filtered.tmp')
    kept=failures=0
    try:
        with pq.ParquetWriter(tmp,SCHEMAS['retained_samples'],
                              compression=None if compression=='none' else compression) as writer:
            for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size):
                rows=[]
                for row in batch.to_pylist():
                    reasons=row['reason'].split('+')
                    if 'failure' in reasons:
                        if failures>=available_failures:reasons.remove('failure')
                        else:failures+=1
                    if reasons:
                        row['reason']='+'.join(reasons)
                        rows.append(row)
                if rows:
                    writer.write_table(pa.Table.from_pylist(rows,schema=SCHEMAS['retained_samples']))
                    kept+=len(rows)
        with tmp.open('rb') as f:os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)
    return kept,failures


def read_rows(run,name):
    run=Path(run)
    direct=run/'data'/f'{name}.parquet'
    if direct.exists(): return pq.read_table(direct).to_pylist()
    rows=[]
    for p in sorted((run/'data'/name).glob('*.parquet')):
        table=pq.read_table(p)
        if not table.schema.equals(SCHEMAS[name],check_metadata=True): raise ValueError(f'schema mismatch: {p}')
        rows.extend(table.to_pylist())
    return rows
