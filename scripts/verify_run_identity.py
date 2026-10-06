"""Compare pre/post-refactor chunk IDs and retained scientific records.

Run with a temporary worktree at the baseline commit:
  .venv/bin/python scripts/verify_run_identity.py /tmp/knill-baseline
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def projection(rows,fields):
    return sorted(tuple(row[field].hex() if isinstance(row[field],bytes) else row[field]
                        for field in fields) for row in rows)


def emit():
    import yaml
    from knill_bench.config import load
    from knill_bench.simulation.runner import prepare,execute_run
    from knill_bench.data.storage import read_rows
    cfg=load(Path(__file__).parents[1]/'configs/smoke.yaml')
    cfg['experiment'].update(distances=[5],bases=['z'],cycles=[2],physical_error_rates=[.001])
    cfg['protocols']=[p for p in cfg['protocols'] if p['id'] in
                      ('se_memory','knill_hex_dminus2','knill_aft_postgate')]
    cfg['sampling'].update(workers=1,shots_per_case=8,chunk_size=4,max_pending_chunks_per_worker=1)
    cfg['sampling'].pop('model_cache_size',None)  # Baseline predates this optional field.
    cfg['timing'].update(latency_sample_count_per_case=0,warmup_shots=0)
    cfg['storage'].update(save_shot_results=True,retained_uniform_samples_per_case=2,
                          retained_failure_samples_per_case=2)
    with tempfile.TemporaryDirectory() as directory:
        cfg['experiment']['output_root']=directory
        path=Path(directory)/'config.yaml';path.write_text(yaml.safe_dump(cfg))
        run=prepare(path)
        execute_run(run,max_new_chunks=2)
        assert json.loads((run/'manifest.json').read_text())['status']=='interrupted'
        execute_run(run)
        checkpoints=[json.loads(p.read_text()) for p in (run/'checkpoints').glob('*.json')]
        cases=read_rows(run,'cases')
        protocol={r['sampling_case_id']:r['protocol'] for r in cases}
        retained=[]
        for row in read_rows(run,'retained_samples'):
            fields=('sampling_case_id','replicate','chunk_id','shot_index','syndrome','actual',
                    'syndrome_bits','observable_bits','reason','policy')
            values=tuple(row[k].hex() if isinstance(row[k],bytes) else row[k] for k in fields)
            # Detector-only execution intentionally omits raw records.
            if protocol[row['sampling_case_id']]=='knill_hex_dminus2':
                values+=(row['measurements'].hex(),)
            retained.append(values)
        result=dict(
            checkpoints=projection(checkpoints,('sampling_case_id','replicate','chunk_id','seed','shots','status')),
            cases=projection(cases,('sampling_case_id','requested_decoder','effective_decoder','fallback_reason')),
            batches=projection(read_rows(run,'batches'),('sampling_case_id','replicate','chunk_id','seed','shot_start','shots')),
            decoders=projection(read_rows(run,'decoder_batches'),('sampling_case_id','replicate','chunk_id',
                'effective_decoder','shots','errors','valid','failed','status')),
            shots=projection(read_rows(run,'shots'),('sampling_case_id','replicate','chunk_id','case_id',
                'shot_index','actual','predicted','logical_failure','decoder_status','residual_weight')),
            retained=sorted(retained))
        print(json.dumps(result))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('baseline',type=Path,nargs='?')
    parser.add_argument('--emit',action='store_true')
    args=parser.parse_args()
    if args.emit:emit();return
    if args.baseline is None:parser.error('baseline checkout is required')
    results=[]
    for source in (args.baseline/'src',Path(__file__).parents[1]/'src'):
        command=[sys.executable,str(Path(__file__).resolve()),'--emit']
        env=dict(os.environ,PYTHONPATH=str(source))
        output=subprocess.run(command,env=env,text=True,capture_output=True,check=True)
        results.append(json.loads(output.stdout.splitlines()[-1]))
    differences=[key for key in results[0] if results[0][key]!=results[1][key]]
    print(json.dumps(dict(exact_match=not differences,differences=differences,
                          chunks=len(results[1]['checkpoints']),retained=len(results[1]['retained']))))
    if differences:raise SystemExit(1)


if __name__=='__main__':main()
