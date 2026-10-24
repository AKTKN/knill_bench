"""Preparation result schema 1, separate from legacy logical_failure tables."""
import pyarrow as pa

S=pa.string(); I=pa.int64(); F=pa.float64(); B=pa.bool_(); BIN=pa.binary()
C=[('sampling_case_id',S),('replicate',I),('chunk_id',I)]
SCHEMAS={
 'preparation_cases':[('case_id',S),('sampling_case_id',S),('protocol',S),('distance',I),('rounds',I),
    ('p',F),('decoding_p',F),('decoder',S),('circuit_hash',S),('model_hash',S),('metadata_json',S)],
 'preparation_chunks':C+[('case_id',S),('decoder',S),('shots',I),('assigned_shots',I),('baseline_valid',I),
    ('complementary_valid',I),('z_decoder_valid',I),('sign_miss_x',I),('sign_miss_z',I),('code_sign_miss',I),
    ('sign_bit_errors_x',I),('sign_bit_errors_z',I),('logical_z_errors',I),('summary_json',S),('gap_bins_json',S),
    ('warmup_ns',I),('x_baseline_ns',I),('x_complementary_ns',I),('z_decode_ns',I),('decode_overhead_ns',I),
    ('evaluation_ns',I),('status',S)],
 'preparation_shots':C+[('case_id',S),('shot_index',I),('baseline_valid',B),('complementary_valid',B),
    ('z_decoder_valid',B),('sign_miss_x',B),('sign_miss_z',B),('code_sign_miss',B),('logical_z_error',B),
    ('sign_bit_errors_x',I),('sign_bit_errors_z',I),('baseline_weight',F),('complementary_weight',F),('gap',F),('status',S)],
 'preparation_retained':C+[('shot_index',I),('online_x',BIN),('online_z',BIN),('truth_tau_x',BIN),('truth_tau_z',BIN),
    ('truth_logical_z',BIN),('decoder_results_json',S),('reason',S),('sample_hash',S),('circuit_hash',S),('maps_hash',S)],
 'preparation_calls':C+[('case_id',S),('shot_index',I),('phase',S),('shots',I),('wall_ns',I),('replay',B),('warmup',B)],
 'preparation_stopping':[('sampling_case_id',S),('replicate',I),('actual_shots',I),('status',S),('elapsed_seconds',F)],
}
SCHEMAS={k:pa.schema(v,metadata={b'knill_bench_schema_version':b'1',b'preparation_result_version':b'1',b'table':k.encode()})
         for k,v in SCHEMAS.items()}
TABLES=('batches','preparation_chunks','preparation_shots','preparation_retained','preparation_calls')
GAP_EDGES=(0.,1.,2.,4.,8.,16.,32.,64.)
