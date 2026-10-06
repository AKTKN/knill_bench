"""Compare fixed physical records and decoder outputs with a baseline checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

CASES=[('se_memory',5,2),('knill_hex_dminus2',5,2),('knill_hex_dminus2',7,3),
       ('knill_aft_postgate',5,2),('knill_aft_postgate',7,3),('knill_aft_prep_only',5,2)]
FIELDS=('sampling_case_id','circuit_hash','model_hash','raw_sha256','detector_sha256',
        'observable_sha256','aliases','fallback','predictions')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('baseline',type=Path,help='checkout at the pre-refactor commit')
    parser.add_argument('--shots',type=int,default=8)
    args=parser.parse_args()
    script=Path(__file__).with_name('benchmark_refactor.py')
    for protocol,distance,cycles in CASES:
        outputs=[]
        for source in (args.baseline/'src',Path(__file__).parents[1]/'src'):
            env=dict(os.environ,PYTHONPATH=str(source))
            command=[sys.executable,str(script),'--protocol',protocol,'--distance',str(distance),
                     '--cycles',str(cycles),'--shots',str(args.shots)]
            result=subprocess.run(command,env=env,capture_output=True,text=True,check=True)
            outputs.append(json.loads(result.stdout.splitlines()[-1]))
        differences=[field for field in FIELDS if outputs[0][field]!=outputs[1][field]]
        print(json.dumps(dict(protocol=protocol,distance=distance,cycles=cycles,shots=args.shots,
                              exact_match=not differences,differences=differences)),flush=True)
        if differences:raise SystemExit(1)


if __name__=='__main__':main()
