"""Tiny actual deep workers, saved labels/statistics, provenance and restart."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import stim
import shutil
import yaml

from knill_bench.converter import deep_simulation as deep_models
from knill_bench.experiments import adaptive_execution, dispatcher
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.converter_deep_clifford import run
from knill_bench.analysis.converter_deep import summarize_saved
from knill_bench.experiments.cli import main
from knill_bench.experiments.run_v2 import RunStore


def document(tmp_path,regime="ideal",**updates):
    raw=dict(schema_version=2,kind="converter_deep_clifford",noise="converter_uniform",name="deep_test",
             resource_preparation=regime,depth=1,circuit_seed=19,sweep=dict(d=[3],p=[.001]),shots=3,batch_size=2,
             buffer_shot=2,workers=1,output_root=str(tmp_path/"runs"))
    raw.update(updates)
    p=tmp_path/"input.yaml";p.write_text(yaml.safe_dump(raw))
    return load_config(p)


@pytest.mark.parametrize("regime",["ideal","noisy"])
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
    assert len(info["files"])==6 and all(n.startswith(p.directory+"/") for n in info["files"])
    for name,sha in info["artifacts"].items():assert hashlib.sha256((path/name).read_bytes()).hexdigest()==sha
    sidecar=json.loads((path/p.directory/"metadata.json").read_text())
    saved=stim.Circuit((path/p.directory/"circuit.stim").read_text())
    reconstructed=stim.Circuit()
    for inst in sidecar["model"]["converter_export"]["selected_instructions"]:
        reconstructed.append(inst["name"],[stim.GateTarget(t) for t in inst["targets"]],inst["arguments"],tag=inst["tag"])
    assert saved[:len(reconstructed)]==reconstructed and saved[-1].name=="MPP"
    assert saved.num_measurements==reconstructed.num_measurements+4
    assert info["execution"]["temporal_policy"]=="native_decomposed_components_independent_explicit_parallel_paths"
    before={str(f.relative_to(path)):f.read_bytes() for f in path.rglob("*") if f.is_file()}
    def forbidden(*a,**kw):raise AssertionError("completed resume built or sampled a circuit")
    with monkeypatch.context() as patch:
        patch.setattr(deep_models.ConverterDeepClifford,"__init__",forbidden)
        patch.setattr(stim.Circuit,"compile_sampler",forbidden)
        assert dispatcher.resume(path)==path
    assert before=={str(f.relative_to(path)):f.read_bytes() for f in path.rglob("*") if f.is_file()}


def test_fixed_serial_spawn_repeatability_and_parent_worker_cache(tmp_path,monkeypatch):
    snapshots=[]
    original=deep_models.ConverterDeepClifford.__init__
    count=0
    def counted(self,*a,**kw):
        nonlocal count
        count+=1;original(self,*a,**kw)
    monkeypatch.setattr(deep_models.ConverterDeepClifford,"__init__",counted)
    for workers in (1,2):
        doc=document(tmp_path,workers=workers,shots=7,batch_size=3)
        path=run(doc);p=next(doc.config.points())
        meta=json.loads((path/"metadata.json").read_text())["points"][p.case_id]
        snapshots.append((pq.read_table(path/p.filename("logical_error")).to_pydict(),meta["execution"]["chunk_partition_sha256"]))
    assert snapshots[0]==snapshots[1]
    # Exactly one parent model per run; serial artifact and chunk use the same one.
    assert count==2 and deep_models._CACHED is None and adaptive_execution._MODEL is None


def test_native_chunk_cache_has_no_sampler_or_per_shot_constructor_reuse(tmp_path,monkeypatch):
    doc=document(tmp_path,"noisy")
    p=next(doc.config.points())
    deep_models.clear_deep_cache();adaptive_execution._MODEL=None
    try:
        task=adaptive_execution.ChunkTask(p,0,0,3,84)
        first=adaptive_execution.run_chunk(task)
        model=deep_models._CACHED[1]
        def forbidden(*a,**kw):raise AssertionError("rebuilt a static native model on a later chunk")
        monkeypatch.setattr(deep_models.ConverterDeepClifford,"__init__",forbidden)
        later=adaptive_execution.run_chunk(replace(task,chunk_id=1,start=3,seed=85))
        replay=adaptive_execution.run_chunk(task)
        assert np.array_equal(first.labels,replay.labels)
        assert later.execution is None and deep_models._CACHED[1] is model
    finally:
        deep_models.clear_deep_cache();adaptive_execution._MODEL=None


def test_failed_point_restarts_at_zero_and_completed_data_stays_byte_identical(tmp_path,monkeypatch):
    doc=document(tmp_path,sweep=dict(d=[3],p=[.001,.002]))
    worker=adaptive_execution.run_chunk
    def fail(task,**kw):
        if task.point.p==.002 and task.start:raise RuntimeError("injected deep chunk failure")
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


@pytest.fixture(scope="module")
def saved_run(tmp_path_factory):
    doc=document(tmp_path_factory.mktemp("deep_saved"),"noisy",sweep=dict(d=[3],p=[.03]),shots=7,batch_size=3)
    return run(doc),doc


@pytest.mark.parametrize("field,value",[("depth",99),("enable_correlations",True),("resource_post_se_probability",.1),
    ("decoder_model_sha256","a"*64),("joint_cross_block_matching",True),("terminal_decoder_inputs",True),
    ("error_definition","per_round"),("original_measurement_count",1),("source_fingerprint","b"*64)])
def test_resume_rejects_changed_physics_policy_and_model_metadata(tmp_path,field,value,saved_run):
    original,doc=saved_run;path=tmp_path/"copy";shutil.copytree(original,path);p=next(doc.config.points())
    meta_path=path/"metadata.json";meta=json.loads(meta_path.read_text())
    meta["points"][p.case_id]["execution"][field]=value
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError,match="deep"):dispatcher.resume(path)
    assert (path/p.filename("logical_error")).exists()


def test_external_resume_document_rejected_before_partial_files_are_deleted(tmp_path):
    doc=document(tmp_path)
    with RunStore.create(doc) as store:path=store.path
    p=next(doc.config.points());sentinel=path/p.directory/"circuit.stim"
    sentinel.write_bytes(b"unfinished point")
    with pytest.raises(ValueError,match="resume document"):
        run(replace(doc,config=replace(doc.config,depth=3)),resume_path=path)
    assert sentinel.read_bytes()==b"unfinished point"


def test_saved_labels_rate_wilson_cli_and_sampling_forbidden(saved_run,tmp_path,monkeypatch,capsys):
    path,doc=saved_run;p=next(doc.config.points())
    labels=pq.read_table(path/p.filename("logical_error"))["logical_error"].to_numpy()
    def forbidden(*a,**kw):raise AssertionError("saved summary constructed or sampled a physical model")
    monkeypatch.setattr(stim.Circuit,"compile_sampler",forbidden)
    monkeypatch.setattr(deep_models.ConverterDeepClifford,"__init__",forbidden)
    summary=summarize_saved(path);row=summary["points"][0]
    k,n=int(labels.sum()),len(labels);z=1.959963984540054
    center=(k/n+z*z/(2*n))/(1+z*z/n)
    half=z*np.sqrt((k/n)*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    assert row["logical_errors"]==k and row["shots"]==n
    assert row["logical_error_rate"]==k/n
    assert row["lower"]==pytest.approx(max(0,center-half))
    assert row["upper"]==pytest.approx(min(1,center+half))
    assert summary["rate_units"]=="full_circuit_failure_probability"
    capsys.readouterr()
    assert main(["summarize-deep",str(path)])==0
    assert json.loads(capsys.readouterr().out)==summary
    target=tmp_path/"summary.json"
    assert main(["summarize-deep",str(path),"--output",str(target)])==0
    assert json.loads(target.read_text())==summary


@pytest.mark.parametrize("damage",["count","ids","probe","stages"])
def test_saved_summary_rejects_inconsistent_records_and_artifacts(saved_run,tmp_path,damage):
    original,doc=saved_run;path=tmp_path/"copy";shutil.copytree(original,path);p=next(doc.config.points())
    metadata_path=path/"metadata.json";meta=json.loads(metadata_path.read_text())
    if damage=="count":
        old=meta["points"][p.case_id]["logical_errors"]
        meta["points"][p.case_id]["logical_errors"]=(old+1)%8
        metadata_path.write_text(json.dumps(meta))
    elif damage=="ids":
        import pyarrow as pa
        data=pq.read_table(path/p.filename("logical_error"))
        data=data.set_column(0,"shot_id",pa.array([0]*7,type=pa.uint64()))
        pq.write_table(data,path/p.filename("logical_error"))
    else:
        f=path/p.directory/("logical_stabilizers.json" if damage=="probe" else "metadata.json")
        f.write_bytes(f.read_bytes()+b" ")
    with pytest.raises(ValueError):summarize_saved(path)
