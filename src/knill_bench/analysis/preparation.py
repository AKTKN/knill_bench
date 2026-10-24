"""Prompt-04 saved-count summary; calibration curves/figures belong to 05."""
from collections import defaultdict
import json
from pathlib import Path

import pyarrow.parquet as pq
import numpy as np

from knill_bench.data.storage import atomic_json, read_rows
from knill_bench.simulation.preparation import validate_run


def analyze(run):
    """Validate published parts and stream chunk counters; never simulate/resume."""
    run=Path(run).resolve()
    parameters=json.loads((run/'parameters.json').read_text())
    manifest=json.loads((run/'manifest.json').read_text())
    validate_run(run,parameters,manifest)
    cases=read_rows(run,'preparation_cases'); totals={}
    latencies=defaultdict(list); checkpoints=[]
    for case in cases:
        totals[case['case_id']]=dict(case_id=case['case_id'],sampling_case_id=case['sampling_case_id'],
            distance=case['distance'],rounds=case['rounds'],p=case['p'],decoder=case['decoder'],shots=0,
            baseline_valid=0,complementary_valid=0,z_decoder_valid=0,sign_miss_x=0,sign_miss_z=0,
            code_sign_miss=0,logical_z_errors=0,x_baseline_ns=0,x_complementary_ns=0,z_decode_ns=0,
            code_valid=0,logical_valid=0,joint_counts=[0]*8)
    for checkpoint in sorted((run/'checkpoints').glob('*.json')):
        checkpoints.append(json.loads(checkpoint.read_text()))
        path=run/'data/preparation_chunks'/f'part-{checkpoint.stem}.parquet'
        for row in pq.read_table(path).to_pylist():
            target=totals[row['case_id']]
            for key in ('shots','baseline_valid','complementary_valid','z_decoder_valid','sign_miss_x','sign_miss_z',
                        'code_sign_miss','logical_z_errors','x_baseline_ns','x_complementary_ns','z_decode_ns'):
                target[key]+=row[key]
            summary=json.loads(row['summary_json'])['unconditional']
            target['code_valid']+=summary['code_space']['shots']
            target['logical_valid']+=summary['logical_z']['shots']
            target['joint_counts']=[a+b for a,b in zip(target['joint_counts'],summary['joint_counts'])]
        for call in pq.read_table(run/'data/preparation_calls'/f'part-{checkpoint.stem}.parquet').to_pylist():
            if call['phase']=='latency' and call['replay'] and not call['warmup']:
                latencies[call['case_id']].append(call['wall_ns'])
    rows=list(totals.values())
    for row in rows:
        for key,num,denom in (('sign_x_rate','sign_miss_x','baseline_valid'),('sign_z_rate','sign_miss_z','z_decoder_valid'),
                              ('code_sign_rate','code_sign_miss','code_valid'),('logical_z_readout_rate','logical_z_errors','logical_valid')):
            row[key]=row[num]/row[denom] if row[denom] else None
        samples=latencies[row['case_id']]
        row['latency']=dict(count=len(samples),**{f'p{q}_ns':float(np.percentile(samples,q)) if samples else None for q in (50,95,99)})
        sid=row['sampling_case_id'];points=[c for c in checkpoints if c['sampling_case_id']==sid]
        decode=sum(row[k] for k in ('x_baseline_ns','x_complementary_ns','z_decode_ns'))
        row['measured_costs']=dict(
            decode_shots_per_second=row['shots']*1e9/decode if decode else None,
            x_baseline_ns_per_shot=row['x_baseline_ns']/row['shots'] if row['shots'] else None,
            x_complementary_ns_per_shot=row['x_complementary_ns']/row['shots'] if row['shots'] else None,
            output_bytes_per_shot=sum(sum(f['bytes'] for f in c['table_files'].values()) for c in points)/row['shots'] if row['shots'] else None,
            worker_peak_rss_bytes=max((c.get('worker_peak_rss_bytes') or 0 for c in points),default=0),
            graph_sparse_bytes=max((c['setup_timing']['decoder_sparse_matrix_bytes'] for c in points if c['setup_timing']),default=None),
            sample_array_bytes=max((c['detector_chunk_bytes'] for c in points),default=0),
            setup_ns=sum(c['setup_timing']['decoder_construct_ns']+c['setup_timing']['artifact_load_ns'] for c in points if c['setup_timing']),
            sampling_ns=sum(c['sampling_ns'] for c in points),sampler_compile_ns=sum(c['sampler_compile_ns'] for c in points))
    published={p.stem for p in (run/'checkpoints').glob('*.json')}
    pending_failed=sum(f['shots'] for f in manifest['failed_chunks'] if f['key'] not in published)
    atomic_json(run/'preparation_summary.json',dict(preparation_result_version=1,status=manifest['status'],
        failed_attempt_assigned_shots_unpublished=pending_failed,cases=rows))
    text='# Fixed-R preparation saved-count summary\n\n'
    text+='Logical-Z errors use prefix_frame_only readout semantics. Gap calibration and confidence curves are not included in this count summary.\n\n'
    text+='| d | R | p | decoder | shots | X misses/valid | Z misses/valid | code misses/valid | logical-Z errors/valid |\n|---|---|---|---|---|---|---|---|---|\n'
    for r in rows:
        text+=f"| {r['distance']} | {r['rounds']} | {r['p']} | {r['decoder']} | {r['shots']} | {r['sign_miss_x']}/{r['baseline_valid']} | {r['sign_miss_z']}/{r['z_decoder_valid']} | {r['code_sign_miss']}/{r['code_valid']} | {r['logical_z_errors']}/{r['logical_valid']} |\n"
    (run/'report.md').write_text(text)
    return rows
