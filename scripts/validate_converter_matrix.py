#!/usr/bin/env python3
"""Opt-in small numerical matrix; exact/fault correctness lives in pytest.

No production budgets. Results remain under the explicit output directory.
Depth 32 is opt-in and samples just one shot after full physical compilation.
"""

import argparse
import json
from pathlib import Path
import time

import yaml


def configurations(*, include_depth32=False):
    common=dict(schema_version=2,noise="converter_uniform",shots=3,batch_size=2,
                buffer_shot=2,workers=1,master_seed=12345)
    for rounds in (1,"d","2*d"):
        yield dict(common,kind="converter_se_memory",name=f"se_{str(rounds).replace('*','')}",
                   sweep=dict(d=[3,5],p=[0.,.003]),rounds=rounds,workers=2)
    for policy in ("noisy_d_rounds","ideal_post_se_depolarizing"):
        for cycles in (1,2,3):
            yield dict(common,kind="converter_knill_memory",name=f"knill_{policy}_{cycles}",
                sweep=dict(d=[3,5],p=[0.,.003]),resource_preparation=policy,T_tel=cycles,
                workers=2 if cycles==1 else 1)
    # Cross the two depths, repetitions, resources and probabilities. Alternate
    # two independent circuit seeds; exact signed groups are checked by pytest.
    for depth in (2,3):
        for nr in (1,2):
            for policy in ("noisy","ideal"):
                seed=19 if nr==1 else 41
                yield dict(common,kind="converter_deep_clifford",name=f"deep_{depth}_{nr}_{policy}",
                    sweep=dict(d=[3],p=[0.,.003]),logical_qubits=4,depth=depth,n_r=nr,circuit_seed=seed,
                    resource_preparation=policy,workers=2 if depth==2 and nr==1 else 1)
    if include_depth32:
        yield dict(common,kind="converter_deep_clifford",name="deep_32_smoke",shots=1,batch_size=1,
            sweep=dict(d=[3],p=[.003]),logical_qubits=4,depth=32,n_r=1,circuit_seed=19,
            resource_preparation="noisy")


def main(argv=None):
    from knill_bench.analysis.converter import summarize_saved
    from knill_bench.experiments.config_v2 import load_config
    from knill_bench.experiments.dispatcher import dispatch, resume
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    parser.add_argument("--include-depth32",action="store_true")
    parser.add_argument("--only-depth32",action="store_true")
    args=parser.parse_args(argv)
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=False)
    reports=[];started=time.monotonic()
    configs=list(configurations(include_depth32=args.include_depth32 or args.only_depth32))
    if args.only_depth32:configs=[c for c in configs if c.get("depth")==32]
    for raw in configs:
        raw=dict(raw,output_root=str(output/"runs"))
        config=output/(raw["name"]+".yaml");config.write_text(yaml.safe_dump(raw))
        t=time.monotonic();run=dispatch(config);assert resume(run)==run
        summary=summarize_saved(run)
        for row in summary["points"]:
            assert row["logical_error_rate"]==row["logical_errors"]/row["shots"]
            ci=row["confidence_interval"]
            assert ci["lower"]<=row["logical_error_rate"]<=ci["upper"]
            if row["parameters"]["p"]==0:assert row["logical_errors"]==0
        reports.append(dict(name=raw["name"],path=str(run),seconds=time.monotonic()-t,summary=summary))
        (output/"validation.json").write_text(json.dumps(dict(cases=reports,seconds=time.monotonic()-started),indent=2))
        print(raw["name"],len(summary["points"]),"points validated",flush=True)
    print(output/"validation.json")


if __name__=="__main__":main()
