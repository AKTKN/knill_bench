"""Run identical isolated setup and fixed-record profiles on two checkouts.

Uses the current benchmark script with each checkout's import path and the
same Python environment. Results are single runs, not statistical estimates.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('baseline',type=Path)
    parser.add_argument('--shots',type=int,default=16)
    args=parser.parse_args()
    script=Path(__file__).with_name('benchmark_refactor.py')
    for protocol,cycles in (('knill_hex_dminus2',7),('knill_aft_postgate',21)):
        for mode in ('prepare','profile'):
            measurements={}
            for label,root in (('before',args.baseline),('after',Path(__file__).parents[1])):
                env=dict(os.environ,PYTHONPATH=str(root/'src'))
                command=[sys.executable,str(script),'--protocol',protocol,'--distance','7',
                         '--cycles',str(cycles),'--shots',str(args.shots),'--mode',mode]
                result=subprocess.run(command,env=env,text=True,capture_output=True,check=True)
                measurements[label]=json.loads(result.stdout.splitlines()[-1])
            print(json.dumps(dict(protocol=protocol,cycles=cycles,mode=mode,
                                  before=measurements['before'],after=measurements['after'])),flush=True)


if __name__=='__main__':main()
