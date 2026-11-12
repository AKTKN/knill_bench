"""Real subprocess CLI, spawn, interruption/recovery and manifest checks."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pyarrow.parquet as pq
import pytest
import yaml

ROOT=Path(__file__).parents[1]


def cli(tmp_path,*args,ok=True):
    result=subprocess.run([sys.executable,"-m","knill_bench.experiments.cli",*map(str,args)],
                          cwd=tmp_path,capture_output=True,text=True,timeout=180)
    assert (result.returncode==0)==ok,(result.returncode,result.stdout,result.stderr)
    return result.stdout.strip() if ok else result.stderr.strip()


def document(tmp_path,kind="converter_se_memory",**options):
    raw=dict(schema_version=2,kind=kind,noise="converter_uniform",sweep=dict(d=[3],p=[.003]),
             shots=3,batch_size=2,buffer_shot=2,workers=1,master_seed=82,
             output_root=str(tmp_path/"runs"))
    if kind=="converter_knill_memory":raw.update(T_tel=1)
    if kind=="converter_deep_clifford":raw.update(depth=1,circuit_seed=19)
    raw.update(options);path=tmp_path/"input.yaml";path.write_text(yaml.safe_dump(raw))
    return path


@pytest.mark.parametrize("kind",["converter_se_memory","converter_knill_memory","converter_deep_clifford"])
def test_actual_subprocess_validate_prepare_multiworker_run_resume_summary(tmp_path,kind):
    path=document(tmp_path,kind,batch_size="auto" if kind.endswith("deep_clifford") else 2)
    original=path.read_bytes();parsed=json.loads(cli(tmp_path,"validate-config",path))
    prepared=Path(cli(tmp_path,"prepare",path,"--workers","2"))
    meta=json.loads((prepared/"metadata.json").read_text())
    assert meta["config"]["workers"]==2 and meta["converter_execution_contract"]=="converter_execution_v2"
    assert all(p["status"]=="pending" for p in meta["points"].values())
    assert not list(prepared.rglob("*.parquet"))
    assert Path(cli(tmp_path,"resume",prepared))==prepared
    # run always creates fresh output; both paths honor effective worker overrides.
    run=Path(cli(tmp_path,"run",path,"--workers","2"));assert run!=prepared
    assert original==path.read_bytes()
    meta=json.loads((run/"metadata.json").read_text());assert meta["status"]=="complete"
    assert meta["config"]["workers"]==2 and meta["config_hash"]!=parsed["config_hash"]
    assert b"original input SHA256" in (run/"config.yaml").read_bytes()
    for case_id,info in meta["points"].items():
        assert info["status"]=="complete" and info["shots"]==3
        labels=pq.read_table(run/f"points/{case_id}/logical_error.parquet")
        assert labels["shot_id"].to_pylist()==[0,1,2]
        assert sum(labels["logical_error"].to_pylist())==info["logical_errors"]
        assert info["execution"]["logical_error_rate"]==info["logical_errors"]/3
        for f,sha in info["artifacts"].items():assert hashlib.sha256((run/f).read_bytes()).hexdigest()==sha
        assert len(info["files"])==(6 if kind.endswith("deep_clifford") else 5)
    before={str(p.relative_to(run)):p.read_bytes() for p in run.rglob("*") if p.is_file()}
    assert Path(cli(tmp_path,"resume",run))==run
    assert before=={str(p.relative_to(run)):p.read_bytes() for p in run.rglob("*") if p.is_file()}
    summary=json.loads(cli(tmp_path,"summarize-converter",run));assert summary["kind"]==kind
    if kind.endswith("deep_clifford"):
        assert json.loads(cli(tmp_path,"summarize-deep",run))["points"][0]["shots"]==3


def test_cli_multidistance_probability_points_and_interrupt_restart(tmp_path):
    path=document(tmp_path,sweep=dict(d=[3,5],p=[0.,.003]))
    raw=yaml.safe_load(path.read_text());raw["sweep"]=dict(d=[3],p=[.003]);path.write_text(yaml.safe_dump(raw))
    code='''import os,sys
from knill_bench.experiments import adaptive_execution as a
from knill_bench.experiments.cli import main
original=a.run_chunk
def interrupted(task,**options):
    if task.start:os._exit(23)
    return original(task,**options)
a.run_chunk=interrupted
main(["run",sys.argv[1]])
'''
    failed=subprocess.run([sys.executable,"-c",code,str(path)],cwd=tmp_path,capture_output=True,text=True,timeout=180)
    assert failed.returncode==23,(failed.stdout,failed.stderr)
    run,=(tmp_path/"runs").iterdir();meta=json.loads((run/"metadata.json").read_text())
    point,=meta["points"].values();seed=point["seed"]
    assert point["status"]=="running" and list(run.rglob("*.incomplete"))
    assert Path(cli(tmp_path,"resume",run))==run
    complete=json.loads((run/"metadata.json").read_text());point,=complete["points"].values()
    assert complete["status"]=="complete" and complete["resume_count"]==1 and point["seed"]==seed
    assert not list(run.rglob("*.incomplete"))
    fresh=Path(cli(tmp_path,"run",path))
    assert next(run.rglob("logical_error.parquet")).read_bytes()==next(fresh.rglob("logical_error.parquet")).read_bytes()
    raw["sweep"]=dict(d=[3,5],p=[0.,.003]);path.write_text(yaml.safe_dump(raw))
    multiple=Path(cli(tmp_path,"run",path,"--workers","2"))
    summary=json.loads(cli(tmp_path,"summarize-converter",multiple))
    assert len(summary["points"])==4
    assert all(r["logical_errors"]==0 for r in summary["points"] if r["parameters"]["p"]==0)


@pytest.mark.parametrize("damage",["circuit_missing","circuit_corrupt","labels_corrupt","ledger_missing","converter_revision","physical_parameters","logical_seed","noise"])
def test_resume_rejects_corruption_before_cleanup(tmp_path,damage):
    # One small physical run reused below by byte copies, no compile per mutation.
    path=document(tmp_path)
    run=Path(cli(tmp_path,"run",path));meta_path=run/"metadata.json";meta=json.loads(meta_path.read_text())
    info,=meta["points"].values();directory=run/"points"/next(iter(meta["points"]))
    sentinel=run/"untouched";sentinel.write_bytes(b"preserve")
    if damage=="circuit_missing":(directory/"circuit.stim").unlink()
    elif damage=="circuit_corrupt":(directory/"circuit.stim").write_text("R 0\n")
    elif damage=="labels_corrupt":(directory/"logical_error.parquet").write_bytes(b"corrupt")
    elif damage=="ledger_missing":(directory/"sampling_chunks.parquet").unlink()
    elif damage=="converter_revision":meta["environment"]["converter"]["commit"]="0"*40
    elif damage=="physical_parameters":info["p"]=.4
    elif damage=="logical_seed":meta["config"]["circuit_seed"]=900
    else:meta["config"]["noise"]="other"
    meta_path.write_text(json.dumps(meta))
    before={str(f.relative_to(run)):f.read_bytes() for f in run.rglob("*") if f.is_file()}
    assert cli(tmp_path,"resume",run,ok=False)
    assert before=={str(f.relative_to(run)):f.read_bytes() for f in run.rglob("*") if f.is_file()}


@pytest.mark.parametrize("extra",["workers: 0\n","extra: 1\n","shots: !!python/object:bad {}\n"])
def test_subprocess_invalid_config_rejected_before_output(tmp_path,extra):
    path=tmp_path/"bad.yaml"
    path.write_text("schema_version: 2\nkind: converter_se_memory\nnoise: converter_uniform\nsweep: {d: [3], p: [0.001]}\noutput_root: runs\n"+extra)
    assert cli(tmp_path,"validate-config",path,ok=False)
    assert cli(tmp_path,"run",path,ok=False)
    assert not (tmp_path/"runs").exists()
