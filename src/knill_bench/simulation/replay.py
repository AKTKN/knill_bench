from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
from time import perf_counter_ns,process_time_ns
import uuid
import numpy as np
from knill_bench.simulation.worker import model,case_id
from knill_bench.simulation.runner import ensure_threads
from knill_bench.data.storage import read_rows,write_table,atomic_json
from knill_bench.data.provenance import environment,compatibility,utc


def replay_case(task):
    case,cfg,samples,workers=task
    compiled,decoders,aliases,details,_=model(case,cfg)
    rows=[]
    for sample in samples:
        if 'uniform' not in sample['reason']:continue
        s=np.unpackbits(np.frombuffer(sample['syndrome'],dtype=np.uint8),bitorder='little')[:sample['syndrome_bits']]
        m=np.unpackbits(np.frombuffer(sample['measurements'],dtype=np.uint8),bitorder='little')[:sample['measurement_bits']]
        for name,decoder in decoders.items():
            for _ in range(cfg['timing']['warmup_shots']):decoder.decode_one(s,m)
            wall=perf_counter_ns();cpu=process_time_ns()
            prediction=decoder.decode_one(s,m)
            w=perf_counter_ns()-wall;c=process_time_ns()-cpu
            rows.append(dict(sampling_case_id=case['sampling_case_id'],replicate=sample['replicate'],chunk_id=sample['chunk_id'],case_id=case_id(case,name),
                shot_index=sample['shot_index'],phase='terminal',input_size=len(m) if decoder.kind=='hex_native_pipeline' else len(s),backend=decoder.kind,batch_size=1,timing_mode='latency',wall_ns=w,cpu_ns=c,
                warmup=False,profiling=False,concurrent_load=workers>1,replay=True))
    return rows


def benchmark_latency(run,workers=1):
    if workers<1:raise ValueError('workers must be positive')
    run=Path(run);p=json.loads((run/'parameters.json').read_text());cfg=p['config']
    ensure_threads(cfg['sampling']['native_threads_per_worker'])
    manifest=json.loads((run/'manifest.json').read_text())
    if compatibility(environment())!=manifest['compatibility_hash']:raise ValueError('replay environment/code mismatch')
    samples=read_rows(run,'retained_samples')
    replay_id=uuid.uuid4().hex[:12];parts=[]
    tasks=[(case,cfg,[s for s in samples if s['sampling_case_id']==case['sampling_case_id']],workers) for case in p['grid']]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        # One future per worker at a time bounds replay model/sample memory.
        for offset in range(0,len(tasks),workers):
            futures=[pool.submit(replay_case,t) for t in tasks[offset:offset+workers]]
            for j,future in enumerate(futures):
                rows=future.result();name=f'part-replay-{replay_id}-{offset+j:04d}.parquet'
                write_table(run/'data/decoder_calls'/name,'decoder_calls',rows,cfg['storage']['compression']);parts.append(name)
    atomic_json(run/'logs'/f'replay-{replay_id}.json',dict(workers=workers,finished=utc(),parts=parts,policy='retained_uniform_only'))
    return parts
