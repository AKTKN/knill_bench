"""Tiny real converter-memory execution, bounded output and restart tests."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import stim
import yaml

from knill_bench.converter import se_memory
from knill_bench.experiments import adaptive_execution, dispatcher
from knill_bench.experiments.cli import main
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.converter_se_memory import run
from knill_bench.experiments.run_v2 import RunStore


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="converter_se_memory", noise="converter_uniform",
               name="converter_memory_test", sweep=dict(d=[3], p=[.003]), rounds="2/3*d",
               shots=7, batch_size=3, workers=1, buffer_shot=2, output_root=str(tmp_path / "runs"))
    raw.update(updates)
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(raw))
    return load_config(path)


def reconstruct_export(export):
    circuit = stim.Circuit()
    for inst in export["selected_instructions"]:
        circuit.append(inst["name"], [stim.GateTarget(t) for t in inst["targets"]], inst["arguments"], tag=inst["tag"])
    return circuit


@pytest.mark.parametrize("batch", [3, "auto"])
@pytest.mark.parametrize("workers", [1, 2])
def test_run_artifacts_counts_metadata_and_completed_resume(tmp_path, batch, workers, monkeypatch):
    doc = document(tmp_path, batch_size=batch, workers=workers, sweep=dict(d=[3, 5], p=[.003]))
    path = run(doc)
    assert (path / "config.yaml").read_bytes() == doc.contents
    metadata = json.loads((path / "metadata.json").read_text())
    assert metadata["status"] == "complete" and metadata["prior_policy"] == doc.config.prior_policy
    assert metadata["environment"]["converter"]["commit"] == "457dc519adec6a11b38843a03e1c8fbbd6495f5a"
    assert "hex" not in metadata["environment"]
    for point in doc.config.points():
        info = metadata["points"][point.case_id]
        assert info["status"] == "complete" and info["shots"] == 7
        assert len(info["files"]) == 5 and all(n.startswith(f"points/{point.case_id}/") for n in info["files"])
        error_path = path / point.filename("logical_error")
        parquet = pq.ParquetFile(error_path)
        table = parquet.read()
        assert table["shot_id"].to_pylist() == list(range(7))
        assert info["logical_errors"] == sum(table["logical_error"].to_pylist())
        assert parquet.metadata.num_row_groups == 4
        sidecar = json.loads((path / point.directory / "metadata.json").read_text())
        circuit_bytes = (path / point.directory / "circuit.stim").read_bytes()
        circuit = stim.Circuit(circuit_bytes.decode())
        assert reconstruct_export(sidecar["model"]["converter_export"]) == circuit
        execution = info["execution"]
        assert execution["rounds"] == point.rounds and execution["additional_se_rounds"] == point.rounds-1
        assert execution["enable_correlations"] is False and execution["decompose_errors"] is False
        assert execution["terminal_ideal_oracle"] is False
        assert execution["stim_sha256"] == hashlib.sha256(circuit_bytes).hexdigest()
        for name, sha in info["artifacts"].items():
            assert hashlib.sha256((path / name).read_bytes()).hexdigest() == sha
    before = {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs): raise AssertionError("completed resume compiled or sampled")
    with monkeypatch.context() as patch:
        patch.setattr(se_memory.ConverterSEMemory, "__init__", forbidden)
        patch.setattr(stim.Circuit, "compile_sampler", forbidden)
        assert dispatcher.resume(path) == path
    assert before == {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_fixed_partition_real_serial_spawn_and_repeatability(tmp_path):
    saved = []
    for workers in (1, 2, 1):
        doc = document(tmp_path, workers=workers, sweep=dict(d=[3, 5], p=[.003]))
        path = run(doc)
        meta = json.loads((path / "metadata.json").read_text())
        saved.append([(pq.read_table(path / p.filename("logical_error")).to_pydict(),
                       meta["points"][p.case_id]["execution"]["chunk_partition_sha256"],
                       meta["points"][p.case_id]["execution"]["source_fingerprint"])
                      for p in doc.config.points()])
    assert saved[0] == saved[1] == saved[2]


def test_serial_builds_native_static_objects_once_per_point_not_per_chunk(tmp_path, monkeypatch):
    import logical_to_stim_converter as api
    counts = dict(compile=0, view=0, graph=0)
    parse = api.parse_logical_circuit
    view = api.make_decoder_view
    graph = se_memory.MemoryDecoder.__init__
    def parse_spy(*a, **kw):
        counts["compile"] += 1
        return parse(*a, **kw)
    def view_spy(*a, **kw):
        counts["view"] += 1
        return view(*a, **kw)
    def decoder_spy(self, *a, **kw):
        counts["graph"] += 1
        graph(self, *a, **kw)
    monkeypatch.setattr(api, "parse_logical_circuit", parse_spy)
    monkeypatch.setattr(api, "make_decoder_view", view_spy)
    monkeypatch.setattr(se_memory.MemoryDecoder, "__init__", decoder_spy)
    doc = document(tmp_path, sweep=dict(d=[3], p=[.001, .002]))
    run(doc)
    assert counts == dict(compile=2, view=2, graph=2)
    assert se_memory._CACHED is None and adaptive_execution._MODEL is None


def test_chunk_worker_cache_and_chunk_seeds_without_sampler_reuse(tmp_path, monkeypatch):
    doc = document(tmp_path)
    point = next(doc.config.points())
    se_memory.clear_memory_cache()
    adaptive_execution._MODEL = None
    try:
        task = adaptive_execution.ChunkTask(point, 0, 0, 3, 123)
        a = adaptive_execution.run_chunk(task)
        original = se_memory._CACHED[1]
        def forbidden(*args, **kwargs): raise AssertionError("reconstructed a native object for a later chunk")
        monkeypatch.setattr(se_memory.ConverterSEMemory, "__init__", forbidden)
        b = adaptive_execution.run_chunk(replace(task, chunk_id=1, start=3, seed=124))
        replay = adaptive_execution.run_chunk(task)
        assert se_memory._CACHED[1] is original
        assert b.execution is None and b.setup_seconds == 0
        assert np.array_equal(a.labels, replay.labels)
    finally:
        adaptive_execution._MODEL = None
        se_memory.clear_memory_cache()


def test_failed_chunk_restarts_zero_preserves_completed_and_matches_clean_fixed_run(tmp_path, monkeypatch):
    doc = document(tmp_path, sweep=dict(d=[3], p=[.001, .002]))
    worker = adaptive_execution.run_chunk
    def fail_later(task, **options):
        if task.point.p == .002 and task.start:
            raise RuntimeError("injected memory chunk failure")
        return worker(task, **options)
    with monkeypatch.context() as patch:
        patch.setattr(adaptive_execution, "run_chunk", fail_later)
        with pytest.raises(RuntimeError, match="chunk failure"):
            run(doc)
    path, = (tmp_path / "runs").iterdir()
    a, b = doc.config.points()
    complete = (path / a.filename("logical_error")).read_bytes()
    failed = json.loads((path / "metadata.json").read_text())
    seed = failed["points"][b.case_id]["seed"]
    assert failed["points"][a.case_id]["status"] == "complete"
    assert failed["points"][b.case_id]["status"] == "failed"
    assert not (path / b.filename("logical_error")).exists()
    assert dispatcher.resume(path) == path
    resumed = json.loads((path / "metadata.json").read_text())
    assert resumed["points"][b.case_id]["seed"] == seed
    assert complete == (path / a.filename("logical_error")).read_bytes()
    fresh = run(doc)
    for p in doc.config.points():
        assert (fresh / p.filename("logical_error")).read_bytes() == (path / p.filename("logical_error")).read_bytes()


@pytest.mark.parametrize("field,value", [("rounds", 999), ("enable_correlations", True), ("stim_sha256", "a"*64)])
def test_resume_refuses_inconsistent_execution_before_pending_cleanup(tmp_path, field, value):
    doc = document(tmp_path, sweep=dict(d=[3], p=[.001, .002]))
    # Complete a real first point through the common runner, reserve a second
    # point using the normal RunStore failure lifecycle.
    worker = adaptive_execution.run_chunk
    from unittest.mock import patch
    def fail_second(task, **kw):
        if task.point.p == .002: raise RuntimeError("stop second point")
        return worker(task, **kw)
    with patch.object(adaptive_execution, "run_chunk", fail_second), pytest.raises(RuntimeError):
        run(doc)
    path, = (tmp_path / "runs").iterdir()
    a, b = doc.config.points()
    sentinel = path / b.directory / ".circuit.stim.incomplete"
    sentinel.write_bytes(b"must survive failed compatibility checks")
    meta_path = path / "metadata.json"
    metadata = json.loads(meta_path.read_text())
    metadata["points"][a.case_id]["execution"][field] = value
    meta_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="converter memory"):
        dispatcher.resume(path)
    assert sentinel.exists()


def test_resume_rejects_external_document_mismatch_without_cleaning(tmp_path):
    doc = document(tmp_path)
    with RunStore.create(doc) as store:
        path = store.path
    point = next(doc.config.points())
    sentinel = path / point.directory / "circuit.stim"
    sentinel.write_bytes(b"unfinished")
    with pytest.raises(ValueError, match="resume document"):
        run(replace(doc, config=replace(doc.config, shots=5)), resume_path=path)
    assert sentinel.read_bytes() == b"unfinished"


def test_cli_and_large_example_parse_without_running_user_budget(tmp_path, capsys):
    doc = document(tmp_path, shots=3, sweep=dict(d=[3], p=[0.]))
    assert main(["validate-config", str(doc.source_path)]) == 0
    capsys.readouterr()
    assert main(["run", str(doc.source_path)]) == 0
    path = Path(capsys.readouterr().out.strip())
    assert main(["resume", str(path)]) == 0
    assert capsys.readouterr().out.strip() == str(path)
    metadata = json.loads((path / "metadata.json").read_text())
    assert next(iter(metadata["points"].values()))["logical_errors"] == 0
    raw = yaml.safe_load(doc.contents)
    raw.update(shots=100000, workers=8, batch_size="auto", sweep=dict(d=[3, 5, 7], p=[.001, .002]), rounds="d")
    raw.pop("buffer_shot")
    doc.source_path.write_text(yaml.safe_dump(raw))
    large = load_config(doc.source_path).config
    assert len(list(large.points())) == 6 and large.shots == 100000
