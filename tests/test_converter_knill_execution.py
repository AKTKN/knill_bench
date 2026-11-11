"""Tiny actual fixed/adaptive Knill workers, provenance and restart output."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import stim
import yaml

from knill_bench.converter import knill_memory
from knill_bench.converter.knill_program import IDEAL_POST, NOISY_D
from knill_bench.experiments import adaptive_execution, dispatcher
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.converter_knill_memory import run
from knill_bench.experiments.run_v2 import RunStore


def document(tmp_path,regime=IDEAL_POST,**updates):
    raw=dict(schema_version=2,kind="converter_knill_memory",noise="converter_uniform",name="knill_test",
             resource_preparation=regime,T_tel=2,sweep=dict(d=[3],p=[.001]),shots=3,batch_size=2,
             buffer_shot=2,workers=1,output_root=str(tmp_path/"runs"))
    raw.update(updates)
    p=tmp_path/"input.yaml";p.write_text(yaml.safe_dump(raw))
    return load_config(p)


@pytest.mark.parametrize("regime",[IDEAL_POST,NOISY_D])
@pytest.mark.parametrize("batch",[2,"auto"])
def test_two_worker_fixed_auto_parquet_artifacts_and_completed_resume(tmp_path,regime,batch,monkeypatch):
    doc=document(tmp_path,regime,batch_size=batch,workers=2)
    path=run(doc)
    metadata=json.loads((path/"metadata.json").read_text())
    p=next(doc.config.points()); info=metadata["points"][p.case_id]
    assert metadata["status"]==info["status"]=="complete" and info["shots"]==3
    assert metadata["prior_policy"]==doc.config.prior_policy
    assert metadata["environment"]["converter"]["commit"]=="457dc519adec6a11b38843a03e1c8fbbd6495f5a"
    assert "hex" not in metadata["environment"]
    table=pq.read_table(path/p.filename("logical_error"))
    assert table["shot_id"].to_pylist()==[0,1,2]
    assert info["logical_errors"]==sum(table["logical_error"].to_pylist())
    assert pq.ParquetFile(path/p.filename("logical_error")).metadata.num_row_groups==2
    assert len(info["files"])==4 and all(n.startswith(p.directory+"/") for n in info["files"])
    for name,sha in info["artifacts"].items():assert hashlib.sha256((path/name).read_bytes()).hexdigest()==sha
    sidecar=json.loads((path/p.directory/"metadata.json").read_text())
    saved=stim.Circuit((path/p.directory/"circuit.stim").read_text())
    reconstructed=stim.Circuit()
    for inst in sidecar["model"]["converter_export"]["selected_instructions"]:
        reconstructed.append(inst["name"],[stim.GateTarget(t) for t in inst["targets"]],inst["arguments"],tag=inst["tag"])
    assert saved==reconstructed and not any(i.name=="MPP" for i in saved)
    assert info["execution"]["temporal_policy"]=="native_decomposed_components_independent_explicit_parallel_paths"
    before={str(f.relative_to(path)):f.read_bytes() for f in path.rglob("*") if f.is_file()}
    def forbidden(*a,**kw):raise AssertionError("completed resume built or sampled a circuit")
    with monkeypatch.context() as patch:
        patch.setattr(knill_memory.ConverterKnillMemory,"__init__",forbidden)
        patch.setattr(stim.Circuit,"compile_sampler",forbidden)
        assert dispatcher.resume(path)==path
    assert before=={str(f.relative_to(path)):f.read_bytes() for f in path.rglob("*") if f.is_file()}


def test_fixed_serial_spawn_repeatability_and_parent_worker_cache(tmp_path,monkeypatch):
    snapshots=[]
    original=knill_memory.ConverterKnillMemory.__init__
    count=0
    def counted(self,*a,**kw):
        nonlocal count
        count+=1;original(self,*a,**kw)
    monkeypatch.setattr(knill_memory.ConverterKnillMemory,"__init__",counted)
    for workers in (1,2):
        doc=document(tmp_path,workers=workers,shots=7,batch_size=3)
        path=run(doc);p=next(doc.config.points())
        meta=json.loads((path/"metadata.json").read_text())["points"][p.case_id]
        snapshots.append((pq.read_table(path/p.filename("logical_error")).to_pydict(),meta["execution"]["chunk_partition_sha256"]))
    assert snapshots[0]==snapshots[1]
    # Exactly one parent model per run; serial artifact and chunk use the same one.
    assert count==2 and knill_memory._CACHED is None and adaptive_execution._MODEL is None


def test_native_chunk_cache_has_no_sampler_or_per_shot_constructor_reuse(tmp_path,monkeypatch):
    doc=document(tmp_path,NOISY_D)
    p=next(doc.config.points())
    knill_memory.clear_knill_cache();adaptive_execution._MODEL=None
    try:
        task=adaptive_execution.ChunkTask(p,0,0,3,84)
        first=adaptive_execution.run_chunk(task)
        model=knill_memory._CACHED[1]
        def forbidden(*a,**kw):raise AssertionError("rebuilt a static native model on a later chunk")
        monkeypatch.setattr(knill_memory.ConverterKnillMemory,"__init__",forbidden)
        later=adaptive_execution.run_chunk(replace(task,chunk_id=1,start=3,seed=85))
        replay=adaptive_execution.run_chunk(task)
        assert np.array_equal(first.labels,replay.labels)
        assert later.execution is None and knill_memory._CACHED[1] is model
    finally:
        knill_memory.clear_knill_cache();adaptive_execution._MODEL=None


def test_failed_point_restarts_at_zero_and_completed_data_stays_byte_identical(tmp_path,monkeypatch):
    doc=document(tmp_path,sweep=dict(d=[3],p=[.001,.002]))
    worker=adaptive_execution.run_chunk
    def fail(task,**kw):
        if task.point.p==.002 and task.start:raise RuntimeError("injected Knill chunk failure")
        return worker(task,**kw)
    with monkeypatch.context() as patch:
        patch.setattr(adaptive_execution,"run_chunk",fail)
        with pytest.raises(RuntimeError,match="chunk failure"):run(doc)
    path,=(tmp_path/"runs").iterdir();a,b=doc.config.points()
    before=(path/a.filename("logical_error")).read_bytes()
    meta=json.loads((path/"metadata.json").read_text());seed=meta["points"][b.case_id]["seed"]
    assert meta["points"][a.case_id]["status"]=="complete" and meta["points"][b.case_id]["status"]=="failed"
    assert not (path/b.filename("logical_error")).exists()
    assert dispatcher.resume(path)==path
    assert (path/a.filename("logical_error")).read_bytes()==before
    assert json.loads((path/"metadata.json").read_text())["points"][b.case_id]["seed"]==seed
    fresh=run(doc)
    assert (fresh/b.filename("logical_error")).read_bytes()==(path/b.filename("logical_error")).read_bytes()


@pytest.mark.parametrize("field,value",[("T_tel",99),("enable_correlations",True),("resource_post_se_probability",.1),
    ("decoder_model_sha256","a"*64),("joint_cross_block_matching",True)])
def test_resume_rejects_changed_physics_policy_and_model_metadata(tmp_path,field,value):
    doc=document(tmp_path);path=run(doc);p=next(doc.config.points())
    meta_path=path/"metadata.json";meta=json.loads(meta_path.read_text())
    meta["points"][p.case_id]["execution"][field]=value
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError,match="Knill"):dispatcher.resume(path)
    assert (path/p.filename("logical_error")).exists()


def test_external_resume_document_rejected_before_partial_files_are_deleted(tmp_path):
    doc=document(tmp_path)
    with RunStore.create(doc) as store:path=store.path
    p=next(doc.config.points());sentinel=path/p.directory/"circuit.stim"
    sentinel.write_bytes(b"unfinished point")
    with pytest.raises(ValueError,match="resume document"):
        run(replace(doc,config=replace(doc.config,T_tel=3)),resume_path=path)
    assert sentinel.read_bytes()==b"unfinished point"
