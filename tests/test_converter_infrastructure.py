"""Synthetic <=7-row publication, parent ownership and spawn contracts."""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path, PureWindowsPath
import pickle

import numpy as np
import pyarrow.parquet as pq
import pytest
import yaml

from knill_bench.converter.artifacts import PointArtifacts, relative_path
from knill_bench.converter.execution import execute_converter_points
from knill_bench.data import storage_v2
from knill_bench.data.storage_v2 import PointWriter
from knill_bench.experiments.adaptive_execution import ChunkResult, ChunkTask, _validate_result
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments import run_v2
from knill_bench.experiments.run_v2 import RunStore


def artifact_builder(point):
    return PointArtifacts("# synthetic program contract\n", "# synthetic circuit contract\n",
                          {"test_only": True}, [] if point.kind == "converter_deep_clifford" else None)


def synthetic_worker(task):
    labels = np.random.default_rng(task.seed).integers(0, 2, task.shots).astype(bool)
    return ChunkResult(task.chunk_id, task.start, task.shots, labels, None, .001, 0., 7,
                       os.getpid(), {"test_only": True})


def failed_worker(task):
    if task.start:
        raise RuntimeError("synthetic failed chunk")
    return synthetic_worker(task)


def worker_write_attempt(path, point):
    with PointWriter(path, point, expected_shots=1):
        pass


def changed_document(document, **updates):
    config = replace(document.config, **updates)
    return replace(document, config=config, contents=yaml.safe_dump(config.as_dict()).encode())


@pytest.fixture
def document(tmp_path, monkeypatch):
    source = dict(commit="a"*40, source_sha256="b"*64, required_revision="a"*40,
                  origin_url="https://example.invalid/source.git", subdirectory=None, version="0")
    env = dict(python="unit-test", os="test-os", cpu=dict(count=1), dependencies=dict(test="1"),
               bench=dict(commit="bench", source_sha256="b"), converter=source, stimflow=source.copy())
    monkeypatch.setattr(run_v2, "collect_environment", lambda kind=None: env)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(dict(schema_version=2, kind="converter_deep_clifford",
        noise="converter_uniform", sweep=dict(d=[3], p=[.001]), output_root=str(tmp_path / "runs"),
        shots=7, batch_size=3, buffer_shot=2)))
    return load_config(path)


def write_point(store, point, *, artifacts=True):
    store.start_point(point)
    if artifacts:
        store.publish_point_artifacts(point, artifact_builder(point))
    with PointWriter(store.path, point, expected_shots=7) as writer:
        writer.write_batch(np.arange(7, dtype=np.uint64), np.arange(7) % 2 == 1)
        result = writer.commit()
    return result


@pytest.mark.parametrize("workers", [1, 2])
@pytest.mark.parametrize("batch", [3, "auto"])
def test_shared_execution_parent_publishes_point_relative_files(document, workers, batch):
    document = changed_document(document, workers=workers, batch_size=batch)
    point = next(document.config.points())
    with RunStore.create(document) as store:
        path = store.path
        assert (path / point.directory).is_dir()
        assert not list((path / point.directory).iterdir())
        execute_converter_points(store, worker=synthetic_worker, artifact_builder=artifact_builder)
        saved = store.metadata
    assert saved["status"] == "complete"
    info = saved["points"][point.case_id]
    assert len(info["files"]) == 5 and all((path / n).is_file() for n in info["files"])
    assert all(not PureWindowsPath(n).is_absolute() for n in info["files"])
    table = pq.read_table(path / point.filename("logical_error"))
    assert table["shot_id"].to_pylist() == list(range(7))
    assert info["logical_errors"] == sum(table["logical_error"].to_pylist())
    assert pq.ParquetFile(path / point.filename("logical_error")).metadata.num_row_groups == 4
    assert info["execution"]["chunk_count"] >= 3
    before = {n: (path / n).read_bytes() for n in info["files"]}
    with RunStore.resume(path) as completed:
        assert completed.metadata["status"] == "complete"
    assert before == {n: (path / n).read_bytes() for n in info["files"]}


def test_fixed_serial_spawn_labels_and_seed_partition_match(document):
    output = []
    for workers in (1, 2):
        doc = changed_document(document, workers=workers)
        with RunStore.create(doc) as store:
            execute_converter_points(store, worker=synthetic_worker, artifact_builder=artifact_builder)
            point = next(doc.config.points())
            output.append((pq.read_table(store.path / point.filename("logical_error")).to_pydict(),
                           store.metadata["points"][point.case_id]["execution"]["chunk_partition_sha256"]))
    assert output[0] == output[1]


def test_failed_chunk_restart_retains_completed_point(document):
    document = changed_document(document, probabilities=(.001, .002))
    a, b = document.config.points()
    with pytest.raises(RuntimeError, match="failed chunk"):
        with RunStore.create(document) as store:
            path = store.path
            store.record_complete(write_point(store, a))
            first = {n: (path / n).read_bytes() for n in store.metadata["points"][a.case_id]["files"]}
            execute_converter_points(store, worker=failed_worker, artifact_builder=artifact_builder)
    assert (path / b.directory / "circuit.stim").is_file()
    with RunStore.resume(path) as store:
        assert not list((path / b.directory).iterdir())
        assert store.metadata["points"][b.case_id]["shots"] == 0
        assert store.metadata["points"][b.case_id]["seed"] == json.loads((path / "metadata.json").read_text())["points"][b.case_id]["seed"]
        execute_converter_points(store, worker=synthetic_worker, artifact_builder=artifact_builder)
    assert first == {n: (path / n).read_bytes() for n in first}


def test_uncommitted_table_and_sidecar_rename_recovery(document):
    with RunStore.create(document) as store:
        path = store.path
        point = next(document.config.points())
        write_point(store, point)  # No metadata completion: simulate crash after renames.
    before = json.loads((path / "metadata.json").read_text())
    (path / point.directory / ".circuit.stim.incomplete").write_bytes(b"partial")
    with RunStore.resume(path) as store:
        assert not list((path / point.directory).iterdir())
        assert "artifacts" not in store.metadata["points"][point.case_id]
        assert before["points"][point.case_id]["seed"] == store.metadata["points"][point.case_id]["seed"]


def test_artifact_failure_rolls_back_all_promotions(document, monkeypatch):
    point = next(document.config.points())
    with RunStore.create(document) as store:
        store.start_point(point)
        original = os.replace
        def fail(source, target):
            if Path(target).name == "circuit.stim":
                raise OSError("injected artifact promotion failure")
            return original(source, target)
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", fail)
            with pytest.raises(OSError, match="promotion failure"):
                store.publish_point_artifacts(point, artifact_builder(point))
        assert not list((store.path / point.directory).iterdir())
        assert "artifacts" not in store.metadata["points"][point.case_id]


def test_cannot_complete_without_artifacts(document):
    with RunStore.create(document) as store:
        point = next(document.config.points())
        result = write_point(store, point, artifacts=False)
        with pytest.raises(ValueError, match="artifact registration"):
            store.record_complete(result)
        assert store.metadata["points"][point.case_id]["status"] == "running"


@pytest.mark.parametrize("change", ["artifact", "counts", "registry", "environment", "config"])
def test_resume_rejects_changes_before_incomplete_cleanup(document, monkeypatch, change):
    doc = replace(document, config=replace(document.config, probabilities=(.001, .002)))
    # The saved YAML must describe the same two-point config.
    doc.source_path.write_text(yaml.safe_dump(doc.config.as_dict()))
    doc = load_config(doc.source_path)
    a, b = doc.config.points()
    with RunStore.create(doc) as store:
        path = store.path
        store.record_complete(write_point(store, a))
    sentinel = path / b.directory / "circuit.stim"
    sentinel.write_bytes(b"unfinished; must survive compatibility rejection")
    metadata_path = path / "metadata.json"
    meta = json.loads(metadata_path.read_text())
    if change == "artifact": (path / a.directory / "circuit.stim").write_text("changed")
    if change == "counts": meta["points"][a.case_id]["logical_errors"] = 0
    if change == "registry": meta["points"][a.case_id]["artifacts"]["../escape"] = "a"*64
    if change == "environment": meta["environment"]["stimflow"]["commit"] = "f"*40
    if change == "config": (path / "config.yaml").write_bytes(doc.contents + b"# change\n")
    metadata_path.write_text(json.dumps(meta))
    with pytest.raises((ValueError, RuntimeError)):
        RunStore.resume(path)
    assert sentinel.read_bytes().startswith(b"unfinished")


def test_parent_only_writer_and_artifact_registration(document, monkeypatch):
    point = next(document.config.points())
    with RunStore.create(document) as store:
        store.start_point(point)
        with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn")) as pool:
            with pytest.raises(RuntimeError, match="owning parent"):
                pool.submit(worker_write_attempt, store.path, point).result()
        real_pid = os.getpid()
        with monkeypatch.context() as patch:
            patch.setattr(run_v2.os, "getpid", lambda: real_pid + 1)
            with pytest.raises(RuntimeError, match="owning parent"):
                store.publish_point_artifacts(point, artifact_builder(point))


@pytest.mark.parametrize("path", ["../x", "/tmp/x", "a/../x", "a//x", "./x", "a\\x", "C:/x", "C:x", "//server/x", "a/./x"])
def test_rejects_nonportable_paths(tmp_path, path):
    with pytest.raises(ValueError): relative_path(tmp_path, path)


def test_symlink_escape_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    run = tmp_path / "run"
    run.mkdir()
    (run / "points").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        relative_path(run, "points/file")


def test_chunk_contract_serializes_numbers_not_native_objects(document):
    point = next(document.config.points())
    task = ChunkTask(point, 0, 0, 7, 13)
    result = synthetic_worker(pickle.loads(pickle.dumps(task)))
    copied = pickle.loads(pickle.dumps(result))
    _validate_result(task, copied)
    assert np.array_equal(copied.labels, result.labels)
    for execution in ({"graph": object()}, {"data": "x"*65537}, {"v": float("nan")}):
        with pytest.raises(ValueError, match="compact JSON"):
            _validate_result(task, replace(result, execution=execution))
    with pytest.raises(ValueError): _validate_result(task, replace(result, labels=np.zeros(6, dtype=bool)))
