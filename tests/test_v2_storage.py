"""B0 bounded streaming, publication/crash recovery, and parent-only metadata."""

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from knill_bench.data import storage_v2 as storage
from knill_bench.data.storage_v2 import PointWriter, schemas
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments import run_v2
from knill_bench.experiments.run_v2 import RunStore


@pytest.fixture
def document(tmp_path, monkeypatch):
    env = dict(python="unit-test", os="test-os", dependencies={"test": "1"},
               cpu=dict(count=1), bench=dict(commit="bench", source_sha256="b"),
               hex=dict(commit="hex", source_sha256="h"))
    monkeypatch.setattr(run_v2, "collect_environment", lambda: env)
    path = tmp_path / "input.yaml"
    path.write_text("# exact comment and input formatting must survive\n" + yaml.safe_dump(dict(
        schema_version=2, name="test_run", kind="logical_zero_factory", output_root=str(tmp_path / "runs"),
        sweep=dict(d=[3], p=[.001]), r_0=2, r_plus=2, T_tel=3, shots=7, batch_size=3,
    )))
    return load_config(path)


def write_point(run, point, *, count=7):
    with PointWriter(run, point, expected_shots=count) as writer:
        for start in range(0, count, 3):
            n = min(3, count - start)
            ids = np.arange(start, start + n, dtype=np.uint64)
            gaps = np.repeat(ids[:, None], point.T_tel, axis=1).astype(np.float64)
            gaps[0, -1] = np.nan
            writer.write_batch(ids, (ids % 2 == 1), gaps if "logical_gaps" in point.tables else None)
        return writer.commit()


def test_stream_two_writers_close_both_before_rename_and_aligned_ids(document, tmp_path, monkeypatch):
    point = next(document.config.points())
    original, promote = pq.ParquetWriter, os.replace
    opened, renamed = [], []

    def count_writer(*args, **kwargs):
        opened.append(args[0])
        return original(*args, **kwargs)

    def check_promote(source, target):
        assert all(pq.ParquetFile(path).metadata.num_rows == 7 for path in opened if path.exists())
        renamed.append(Path(target).name)
        return promote(source, target)

    monkeypatch.setattr(pq, "ParquetWriter", count_writer)
    monkeypatch.setattr(storage.os, "replace", check_promote)
    result = write_point(tmp_path, point)
    assert len(opened) == len(renamed) == 2
    assert result.shots == 7 and result.logical_errors == 3
    assert sorted(p.name for p in tmp_path.glob("*.parquet")) == sorted(result.files)
    assert not list(tmp_path.glob(".*.incomplete")) and not list(tmp_path.glob("*.lock"))
    error = pq.ParquetFile(tmp_path / point.filename("logical_error"))
    gaps = pq.ParquetFile(tmp_path / point.filename("logical_gaps"))
    assert error.metadata.num_row_groups == gaps.metadata.num_row_groups == 3
    assert error.schema_arrow.equals(schemas(point)["logical_error"], check_metadata=True)
    assert gaps.schema_arrow.equals(schemas(point)["logical_gaps"], check_metadata=True)
    assert error.read()["shot_id"].to_pylist() == gaps.read()["shot_id"].to_pylist() == list(range(7))
    assert error.read()["shot_id"].type == pa.uint64()
    assert gaps.read()["gap_t003"].null_count == 3


def test_one_table_fig4d_and_null_factory_gaps(document, tmp_path):
    point = replace(next(document.config.points()), kind="fig4d_reproduction")
    result = write_point(tmp_path, point)
    assert len(result.files) == 1
    with pytest.raises(ValueError):
        point.filename("logical_gaps")
    factory = replace(point, kind="logical_zero_factory")
    for file in result.files:
        (tmp_path / file).unlink()
    with PointWriter(tmp_path, factory, expected_shots=2) as writer:
        writer.write_batch(np.arange(2, dtype=np.uint64), np.zeros(2, dtype=bool))
        writer.commit()
    assert pq.ParquetFile(tmp_path / factory.filename("logical_gaps")).read()["gap_t001"].null_count == 2


@pytest.mark.parametrize("bad", ["id_type", "id_order", "id_duplicate", "label_shape", "label_type", "gap_shape", "gap_type", "gap_negative", "gap_infinite"])
def test_invalid_batch_rejected_before_any_append(document, tmp_path, bad):
    point = next(document.config.points())
    ids = np.arange(3, dtype=np.uint64)
    labels = np.zeros(3, dtype=bool)
    gaps = np.ones((3, 3), dtype=np.float64)
    if bad == "id_type": ids = ids.astype(np.int64)
    if bad == "id_order": ids = ids[::-1]
    if bad == "id_duplicate": ids[1] = ids[0]
    if bad == "label_shape": labels = labels[:2]
    if bad == "label_type": labels = labels.astype(float)
    if bad == "gap_shape": gaps = gaps[:, :1]
    if bad == "gap_type": gaps = gaps.astype(np.float32)
    if bad == "gap_negative": gaps[0, 0] = -1
    if bad == "gap_infinite": gaps[0, 0] = np.inf
    with PointWriter(tmp_path, point, expected_shots=3) as writer:
        with pytest.raises(ValueError): writer.write_batch(ids, labels, gaps)
        assert writer.rows == 0
    assert not list(tmp_path.glob("*.parquet"))


def test_incomplete_append_failure_second_rename_failure_and_no_overwrite(document, tmp_path, monkeypatch):
    point = next(document.config.points())
    with pytest.raises(ValueError, match="incomplete point"):
        with PointWriter(tmp_path, point, expected_shots=2) as writer:
            writer.write_batch(np.array([0], np.uint64), np.array([False]), np.ones((1, 3)))
            writer.commit()
    assert not list(tmp_path.glob("*.parquet"))
    original = storage.os.replace

    def fail_second(source, target):
        if str(target).endswith(point.filename("logical_gaps")):
            raise OSError("second rename failed")
        return original(source, target)

    with monkeypatch.context() as context:
        context.setattr(storage.os, "replace", fail_second)
        with pytest.raises(OSError, match="second rename"):
            write_point(tmp_path, point)
    assert not list(tmp_path.glob("*.parquet")) and not list(tmp_path.glob(".*.incomplete"))
    write_point(tmp_path, point)
    with pytest.raises(FileExistsError, match="already exists"):
        PointWriter(tmp_path, point, expected_shots=7)
    assert pq.ParquetFile(tmp_path / point.filename("logical_error")).metadata.num_rows == 7


def test_write_failure_aborts_both_tables(document, tmp_path, monkeypatch):
    point = next(document.config.points())
    original = pq.ParquetWriter

    class FailingWriter:
        def __init__(self, path, *args, **kwargs):
            self.writer = original(path, *args, **kwargs)
            self.fail = "logical_gaps__" in str(path)
        def write_table(self, table):
            if self.fail:
                raise OSError("controlled append failure")
            self.writer.write_table(table)
        def close(self): self.writer.close()

    monkeypatch.setattr(pq, "ParquetWriter", FailingWriter)
    with pytest.raises(OSError, match="append failure"):
        write_point(tmp_path, point)
    assert not list(tmp_path.glob("*.parquet")) and not list(tmp_path.glob(".*.incomplete"))


def test_exclusive_writer_ownership_and_parent_only_metadata(document, tmp_path, monkeypatch):
    point = next(document.config.points())
    with PointWriter(tmp_path, point, expected_shots=3):
        with pytest.raises(FileExistsError): PointWriter(tmp_path, point, expected_shots=3)
    with RunStore.create(document) as run:
        with pytest.raises(RuntimeError, match="live process"):
            RunStore.resume(run.path)
        monkeypatch.setattr(run_v2.os, "getpid", lambda: -1)
        with pytest.raises(RuntimeError, match="owning parent"):
            run.start_point(point)
        monkeypatch.undo()


@pytest.mark.parametrize("instant,stamp,next_stamp", [
    (datetime(2026, 10, 16, 1, 2, 3, tzinfo=timezone.utc), "20261016100203", "20261016100204"),
    (datetime(2026, 10, 16, 14, 59, 59, tzinfo=timezone.utc), "20261016235959", "20261017000000"),
])
def test_exact_config_minimal_metadata_run_collision_and_complete(document, monkeypatch,
                                                                 instant, stamp, next_stamp):
    monkeypatch.setattr(run_v2, "utc_now", lambda: instant)
    suffix = f"{document.config.config_hash[:8]}_test_run"
    with RunStore.create(document) as first:
        assert first.path.name == f"{stamp}_{suffix}"
        point = next(document.config.points())
        first.start_point(point)
        first.record_complete(write_point(first.path, point))
        first.finish()
        first_path = first.path
    first_bytes = {file.name: file.read_bytes() for file in first_path.iterdir()}
    with RunStore.create(document) as second:
        assert second.path != first_path
        assert second.path.name == f"{next_stamp}_{suffix}"
        assert second.metadata["status"] == "running" and second.metadata["resume_count"] == 0
        assert all(p["status"] == "pending" and p["shots"] == 0
                   for p in second.metadata["points"].values())
        assert not list(second.path.glob("*.parquet"))
    changed = document.config.as_dict()
    changed.update(create_codecapacity_dem=True, theta=4.)
    document.source_path.write_text(yaml.safe_dump(changed))
    changed_document = load_config(document.source_path)
    changed_hash = changed_document.config.config_hash
    assert changed_hash[:8] != document.config.config_hash[:8]
    with RunStore.create(changed_document) as different_policy:
        assert different_policy.path.name == f"{stamp}_{changed_hash[:8]}_test_run"
        assert different_policy.metadata["prior_policy"] == "module_local_stim_dem"
    assert first_bytes == {file.name: file.read_bytes() for file in first_path.iterdir()}
    assert (first_path / "config.yaml").read_bytes() == document.contents
    assert sorted(p.name for p in first_path.iterdir()) == sorted(["config.yaml", "metadata.json", *[point.filename(t) for t in point.tables]])
    metadata = json.loads((first_path / "metadata.json").read_text())
    assert metadata["status"] == "complete" and metadata["ended_at"].endswith("+00:00")
    assert metadata["config_hash"] == document.config.config_hash
    assert metadata["prior_policy"] == "hex_legacy_hamming"
    assert metadata["final_readout"] == "noiseless_terminal_Z_factory_oracle"
    assert metadata["points"][point.case_id]["logical_errors"] == 3
    assert metadata["points"][point.case_id]["shots"] == 7
    with RunStore.resume(first_path) as unchanged:
        assert unchanged.metadata["status"] == "complete"
    # Run loading/resume accepts legacy directory names; no output is renamed.
    legacy_path = first_path.with_name("20261016T010203.000000Z_test_run")
    first_path.rename(legacy_path)
    with RunStore.resume(legacy_path) as legacy:
        assert legacy.metadata["status"] == "complete"


def test_failed_run_and_restart_removes_partial_public_pair(document):
    point = next(document.config.points())
    with pytest.raises(RuntimeError, match="controlled failure"):
        with RunStore.create(document) as run:
            path = run.path
            run.start_point(point)
            # Complete files without the metadata marker represent a crash
            # after either rename, or before parent metadata publication.
            write_point(path, point)
            raise RuntimeError("controlled failure")
    assert json.loads((path / "metadata.json").read_text())["status"] == "failed"
    (path / point.filename("logical_gaps")).unlink()
    (path / ("." + point.filename("logical_gaps") + ".incomplete")).write_bytes(b"broken footer")
    with RunStore.resume(path) as resumed:
        assert not list(path.glob("*.parquet")) and not list(path.glob("*.incomplete"))
        assert resumed.metadata["points"][point.case_id]["status"] == "pending"
        resumed.start_point(point)
        resumed.record_complete(write_point(path, point))
        resumed.finish()
    assert json.loads((path / "metadata.json").read_text())["status"] == "complete"


def test_resume_preserves_completed_points_but_rejects_corruption_and_config_change(document):
    with RunStore.create(document) as run:
        point = next(document.config.points())
        run.start_point(point)
        run.record_complete(write_point(run.path, point))
        run.finish()
        path = run.path
    before = {p.name: p.read_bytes() for p in path.glob("*.parquet")}
    with RunStore.resume(path): pass
    assert before == {p.name: p.read_bytes() for p in path.glob("*.parquet")}
    saved = (path / "config.yaml").read_bytes()
    (path / "config.yaml").write_bytes(saved + b"# changed\n")
    with pytest.raises(ValueError, match="config changed"): RunStore.resume(path)
    (path / "config.yaml").write_bytes(saved)
    (path / point.filename("logical_error")).write_bytes(b"corrupted")
    with pytest.raises(Exception, match="Parquet|parquet"): RunStore.resume(path)


def test_cannot_finish_early_and_resume_environment_guard(document, monkeypatch):
    with RunStore.create(document) as run:
        path = run.path
        with pytest.raises(ValueError, match="unfinished"): run.finish()
    original = run_v2.collect_environment()
    monkeypatch.setattr(run_v2, "collect_environment", lambda: dict(original, dependencies={"test": "2"}))
    with pytest.raises(ValueError, match="environment changed"): RunStore.resume(path)


def test_failed_metadata_promotion_leaves_old_json_and_restart_discards_uncommitted_pair(document, monkeypatch):
    point = next(document.config.points())
    run = RunStore.create(document)
    run.start_point(point)
    result = write_point(run.path, point)
    original = storage.os.replace
    previous = (run.path / "metadata.json").read_bytes()

    def fail_metadata(source, target):
        if Path(target).name == "metadata.json": raise OSError("metadata promotion failed")
        return original(source, target)

    with monkeypatch.context() as context:
        context.setattr(storage.os, "replace", fail_metadata)
        with pytest.raises(OSError, match="metadata promotion"):
            run.record_complete(result)
    run.close()
    assert (run.path / "metadata.json").read_bytes() == previous
    with RunStore.resume(run.path) as resumed:
        assert resumed.metadata["points"][point.case_id]["status"] == "pending"
        assert not list(run.path.glob("*.parquet"))


@pytest.mark.parametrize("field,value", [("seed", 0), ("d", 99), ("files", ["../outside.parquet"])])
def test_resume_rejects_changed_point_identity_without_deleting_files(document, field, value):
    with RunStore.create(document) as run:
        path = run.path
        point = next(document.config.points())
    sentinel = path / point.filename("logical_error")
    sentinel.write_bytes(b"unfinished but must not be deleted after identity rejection")
    saved = json.loads((path / "metadata.json").read_text())
    saved["points"][point.case_id][field] = value
    (path / "metadata.json").write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="changed"):
        RunStore.resume(path)
    assert sentinel.exists()


def test_stale_crash_locks_cleared_and_foreign_locks_refused(document, monkeypatch):
    with RunStore.create(document) as run:
        path = run.path
    point = next(document.config.points())
    for name in (".run.lock", f".point-{point.case_id}.lock"):
        (path / name).write_text(json.dumps(dict(pid=1234567, host=socket.gethostname())))
    def dead(pid, signal): raise ProcessLookupError()
    monkeypatch.setattr(storage.os, "kill", dead)
    with RunStore.resume(path): pass
    (path / ".run.lock").write_text(json.dumps(dict(pid=1234567, host="another-host")))
    with pytest.raises(RuntimeError, match="stale lock ownership"): RunStore.resume(path)


def test_real_imported_hex_n2_api_provenance_without_sampler_or_decoder(monkeypatch):
    from knill_bench.experiments import provenance
    import pymatching
    def forbidden(*args, **kwargs): raise AssertionError("infrastructure constructed a scientific backend")
    import stim
    from hex_qec.protocols import FactoryCircuitBuilder
    monkeypatch.setattr(FactoryCircuitBuilder, "build", forbidden)
    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", forbidden)
    env = provenance.collect_environment()
    assert env["hex"]["commit"] == provenance.HEX_REVISION
    assert env["hex"]["branch"] == "auxiliary-system" and not env["hex"]["dirty"]
    assert env["dependencies"]["hex-qec"] == "0.1.0"
    assert env["cpu"]["count"] > 0
    actual = env["hex"]
    monkeypatch.setattr(provenance, "source_info", lambda module: dict(actual, commit="5de58f2f80791054411ad3c0885a4fe3671ed56a"))
    with pytest.raises(RuntimeError, match="must descend from HEX-N2"): provenance.validate_hex()
