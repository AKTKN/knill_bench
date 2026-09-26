"""Thin command dispatch; simulation imports follow native-thread setup."""
import argparse
import json
from pathlib import Path
import os
from knill_bench.config import load,grid,canonical


def main(argv=None):
    parser=argparse.ArgumentParser(prog='knill-bench')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('validate-config','build','run'):
        p=sub.add_parser(name);p.add_argument('config')
    p=sub.add_parser('resume');p.add_argument('run');p.add_argument('--workers',type=int);p.add_argument('--max-new-chunks',type=int,help=argparse.SUPPRESS)
    p=sub.add_parser('benchmark-latency');p.add_argument('run');p.add_argument('--workers',type=int,default=1)
    p=sub.add_parser('analyze');p.add_argument('run')
    p=sub.add_parser('validate-references')
    p=sub.add_parser('audit-faults');p.add_argument('run');p.add_argument('--budget',type=int,default=1000)
    args=parser.parse_args(argv)
    if hasattr(args,'config'):cfg=load(args.config)
    elif hasattr(args,'run'):cfg=json.loads((Path(args.run)/'parameters.json').read_text())['config']
    else:cfg={'sampling':{'native_threads_per_worker':1}}
    threads=cfg['sampling']['native_threads_per_worker']
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        if key in os.environ and os.environ[key]!=str(threads):parser.error(f'{key} must equal native_threads_per_worker={threads}')
        os.environ.setdefault(key,str(threads))
    if args.command=='validate-config':
        print(canonical(dict(config=cfg,resolved_grid=list(grid(cfg)))))
    elif args.command in ('build','run'):
        from knill_bench.simulation.runner import prepare,execute_run
        run=prepare(args.config)
        if args.command=='run':execute_run(run)
        print(run)
    elif args.command=='resume':
        from knill_bench.simulation.runner import execute_run
        print(execute_run(args.run,args.workers,args.max_new_chunks))
    elif args.command=='analyze':
        from knill_bench.analysis.report import analyze
        rows=analyze(args.run);print(f'Analyzed {len(rows)} cases: {Path(args.run)/"report.md"}')
    elif args.command=='benchmark-latency':
        from knill_bench.simulation.replay import benchmark_latency
        print(f'Wrote {len(benchmark_latency(args.run,args.workers))} replay timing parts')
    elif args.command=='validate-references':
        from knill_bench.adapters.references import native_reference,lom_reference,bp_reference
        print(json.dumps(dict(native=native_reference(),lom=lom_reference(),bplsd=bp_reference()),indent=2))
    elif args.command=='audit-faults':
        from knill_bench.decoding.audit import audit_run
        print(audit_run(args.run,args.budget))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
