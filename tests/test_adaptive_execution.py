"""Adaptive scheduling uses synthetic clocks/data; physical fixtures stay <=7 shots."""

from concurrent.futures import Future
from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np
import pyarrow.parquet as pq
import pytest
import yaml

from knill_bench.data.storage_v2 import PointBuffer, PointWriter
from knill_bench.experiments import adaptive_execution as adaptive, dispatcher
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config, parse_config
from knill_bench.experiments.run_v2 import RunStore
from knill_bench.experiments.seeds import chunk_seed


def raw_config(**updates):
    raw = dict(schema_version=2, kind="logical_zero_factory", name="adaptive_test",
               sweep=dict(d=[3], p=[.002]), r_0=2, r_plus=2, T_tel=2, shots=7,
               workers=1, buffer_shot=3, master_seed=912)
    return dict(raw, **updates)


def document(tmp_path, **updates):
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(raw_config(output_root=str(tmp_path / "runs"), **updates)))
    return load_config(path)


def test_default_auto_and_fixed_legacy_hash_and_workers_override(tmp_path):
    raw = raw_config()
    config = parse_config(raw)
    assert config.batch_size == "auto" and config.output_buffer_shots == 3
    assert parse_config(config.as_dict()) == config
    default = parse_config(dict(raw, buffer_shot=10_000))
    assert default.output_buffer_shots == 10_000
    fixed = parse_config(dict(raw, batch_size=2))
    assert fixed.batch_size == 2
    legacy_raw = dict(raw, batch_size=2)
    legacy_raw.pop("buffer_shot")
    legacy = parse_config(legacy_raw)
    assert legacy.output_buffer_shots == 2
    assert "buffer_shot" not in legacy.as_dict() and "target_chunk_seconds" not in legacy.as_dict()
    doc = document(tmp_path)
    original = doc.source_path.read_bytes()
    override = load_config(doc.source_path, workers=2)
    assert override.config.workers == 2 and override.config.config_hash != doc.config.config_hash
    assert load_config(doc.source_path).contents == original
    saved = tmp_path / "effective.yaml"
    saved.write_bytes(override.contents)
    assert load_config(saved).config == override.config
    assert "original input SHA256" in override.contents.decode()


@pytest.mark.parametrize("updates", [
    dict(buffer_shot=0), dict(buffer_shot=True), dict(buffer_shot=2.5), dict(buffer_shot=None),
    dict(buffer_shot=2**63), dict(target_chunk_seconds=0), dict(target_chunk_seconds=-1),
    dict(target_chunk_seconds=float("nan")), dict(target_chunk_seconds=float("inf")),
    dict(target_chunk_seconds=True), dict(batch_size="automatic"), dict(batch_size=None),
    dict(batch_size=3, target_chunk_seconds=1), dict(buffer_shots=4),
])
def test_invalid_adaptive_settings_fail_before_run(updates):
    with pytest.raises(ValueError):
        parse_config(raw_config(**updates))


def test_sizer_targets_time_ramps_up_caps_and_handles_zero_timing():
    fast, slow = adaptive.ChunkSizer(1., 1000), adaptive.ChunkSizer(1., 1000)
    for size in (1, 2, 4, 8, 16, 32, 64, 128):
        fast.observe(size, size * .01)
        slow.observe(size, size * .1)
    assert fast.count(1000) == 100 and slow.count(1000) == 10
    assert fast.count(17, slots=3) == 6
    fast.cap = 4
    assert fast.count(1000) == 4 and fast.count(0) == 0
    probe = adaptive.ChunkSizer(1., 1000)
    assert probe.count(100) == 1
    probe.observe(1, 0.)
    assert probe.count(100) == 1
    probe.observe(1, 1e-12)
    assert probe.count(100) == 2
    probe.observe(2, float("nan"))
    assert probe.count(100) == 4


@pytest.mark.parametrize("factory", [False, True])
def test_buffer_exact_flush_boundaries_and_aligned_pairs(tmp_path, factory):
    point = ExperimentPoint("logical_zero_factory" if factory else "fig4d_reproduction", 3, 0., 2, 2, 2)
    with PointWriter(tmp_path, point, expected_shots=7) as writer:
        output = PointBuffer(writer, 3)
        for start, count in ((0, 2), (2, 4), (6, 1)):
            ids = np.arange(start, start + count, dtype=np.uint64)
            output.write_batch(ids, ids % 2 == 0,
                               np.repeat(ids[:, None], 2, axis=1).astype(np.float64) if factory else None)
            assert writer.rows == ((start + count) // 3) * 3
        result = output.commit()
    assert result.shots == 7 and result.logical_errors == 4
    for name in point.tables:
        file = pq.ParquetFile(tmp_path / point.filename(name))
        assert [file.metadata.row_group(i).num_rows for i in range(3)] == [3, 3, 1]
        assert file.read()["shot_id"].to_pylist() == list(range(7))
    if factory:
        gaps = pq.read_table(tmp_path / point.filename("logical_gaps"))
        assert gaps["gap_t001"].to_pylist() == list(range(7))


class MemoryStore:
    def __init__(self, tmp_path, **updates):
        self.document = SimpleNamespace(config=parse_config(raw_config(**updates)))
        self.path = tmp_path
        self.metadata = {"points": {}}
        self.results = []

    def start_point(self, point):
        self.started = point

    def record_complete(self, result, *, execution):
        self.results.append((result, execution))


def synthetic_worker(task, **options):
    ids = np.arange(task.start, task.start + task.shots, dtype=np.uint64)
    return adaptive.ChunkResult(task.chunk_id, task.start, task.shots, ids % 2 == 0,
                                np.repeat(ids[:, None], task.point.T_tel, axis=1).astype(np.float64),
                                .01 * task.shots, 100., 3, 123, {"physical": "synthetic"})


def test_out_of_order_window_bounded_and_single_point_uses_multiple_slots(tmp_path, monkeypatch):
    store = MemoryStore(tmp_path, workers=3)
    point = next(store.document.config.points())
    tasks = []
    max_window = 0

    class Pool:
        def submit(self, worker, task, **options):
            future = Future()
            future.task = task
            tasks.append(task)
            return future

    def out_of_order(pending, **kwargs):
        nonlocal max_window
        max_window = max(max_window, len(pending))
        # Complete the newest first. A scheduler that ignores ready results
        # would keep submitting while the first result is delayed.
        future = max(pending, key=lambda f: f.task.chunk_id)
        future.set_result(synthetic_worker(future.task))
        return {future}, set(pending) - {future}

    monkeypatch.setattr(adaptive, "wait", out_of_order)
    adaptive._execute_point(store, point, Pool(), synthetic_worker, {})
    assert max_window == 3 and [t.start for t in tasks[:3]] == [0, 1, 2]
    assert sum(t.shots for t in tasks) == 7
    assert all(t.shots <= 3 for t in tasks)
    for task in tasks:
        assert task.seed == chunk_seed(store.document.config.master_seed, point, task.chunk_id, stream=adaptive.POLICY)
    result, execution = store.results[0]
    assert result.shots == 7 and execution["worker_setup_seconds"] == 100 * len(tasks)
    assert execution["sampling_decode_seconds"] == pytest.approx(.07)
    assert execution["chunk_shots_max"] <= 3
    assert len(execution["chunk_partition_sha256"]) == 64
    assert pq.read_table(tmp_path / point.filename("logical_error"))["shot_id"].to_pylist() == list(range(7))


@pytest.mark.parametrize("bad", ["identity", "labels", "gaps", "timing", "model"])
def test_adaptive_failure_aborts_pair_before_publication(tmp_path, bad):
    store = MemoryStore(tmp_path, buffer_shot=1)
    point = next(store.document.config.points())

    def worker(task, **options):
        result = synthetic_worker(task)
        if task.chunk_id == 1:
            if bad == "identity":
                return replace(result, start=999)
            if bad == "labels":
                return replace(result, labels=result.labels.astype(np.uint8))
            if bad == "gaps":
                return replace(result, gaps=np.full((task.shots, 2), np.nan))
            if bad == "timing":
                return replace(result, seconds=float("inf"))
            return replace(result, execution={"physical": "different model"})
        return result

    with pytest.raises(ValueError):
        adaptive._execute_point(store, point, None, worker, {})
    assert not store.results and not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind,prior", [("fig4d_reproduction", False),
                                        ("logical_zero_factory", False),
                                        ("logical_zero_factory", True)])
def test_real_auto_serial_spawn_pair_counts_and_completed_resume(tmp_path, kind, prior, monkeypatch):
    doc = document(tmp_path, kind=kind, T_tel=8 if kind == "fig4d_reproduction" else 2,
                   create_codecapacity_dem=prior, workers=2)
    parallel = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    meta = json.loads((parallel / "metadata.json").read_text())
    execution = meta["points"][point.case_id]["execution"]
    assert execution["parallel_execution"] == adaptive.POLICY
    assert execution["buffer_shot"] == 3 and execution["chunk_count"] >= 3
    assert meta["status"] == "complete" and meta["points"][point.case_id]["shots"] == 7
    for name in point.tables:
        file = pq.ParquetFile(parallel / point.filename(name))
        assert file.read()["shot_id"].to_pylist() == list(range(7))
        assert [file.metadata.row_group(i).num_rows for i in range(3)] == [3, 3, 1]
    serial_doc = document(tmp_path, kind=kind, T_tel=point.T_tel, create_codecapacity_dem=prior)
    serial = dispatcher.dispatch(serial_doc.source_path)
    assert pq.read_table(serial / point.filename("logical_error")).num_rows == 7
    # Timing-dependent partitions are allowed to differ. Exact replay tests
    # below use the same explicit tasks, independent of worker cache lifetime.
    before = {p.name: p.read_bytes() for p in parallel.glob("*.parquet")}
    monkeypatch.setattr(adaptive, "_compile_model", lambda *a, **kw: pytest.fail("completed resume compiled"))
    assert dispatcher.resume(parallel) == parallel
    assert before == {p.name: p.read_bytes() for p in parallel.glob("*.parquet")}


def test_real_chunk_seeds_replay_cache_and_prior_independence(tmp_path, monkeypatch):
    point = next(document(tmp_path).config.points())
    original_compile = adaptive._compile_model
    calls = []

    def track(*args):
        calls.append(args)
        return original_compile(*args)

    monkeypatch.setattr(adaptive, "_compile_model", track)
    adaptive._MODEL = None
    try:
        tasks = [adaptive.ChunkTask(point, j, start, count, chunk_seed(912, point, j, stream=adaptive.POLICY))
                 for j, (start, count) in enumerate(((0, 1), (1, 2), (3, 4)))]
        first = [adaptive.run_chunk(t) for t in tasks]
        assert len(calls) == 1
        replay = [adaptive.run_chunk(t) for t in reversed(tasks)]
        assert len(calls) == 1
        for a, b in zip(first, reversed(replay)):
            assert np.array_equal(a.labels, b.labels) and np.array_equal(a.gaps, b.gaps)
        # Inference may differ, but the physical raw circuit and seeded records agree.
        _, hamming, _ = original_compile(point, tasks[0].seed, {})
        _, local, _ = original_compile(point, tasks[0].seed, {"create_codecapacity_dem": True})
        assert hamming == local
        assert np.array_equal(hamming.compile_sampler(seed=tasks[0].seed).sample(shots=7),
                              local.compile_sampler(seed=tasks[0].seed).sample(shots=7))
    finally:
        adaptive._MODEL = None


def test_auto_failed_point_restarts_and_preserves_completed_point(tmp_path, monkeypatch):
    doc = document(tmp_path, sweep=dict(d=[3], p=[.001, .002]), buffer_shot=1)
    calls = []

    def failing(task, **options):
        calls.append((task.point.p, task.start, task.seed))
        if task.point.p == .002 and task.chunk_id == 1:
            raise RuntimeError("synthetic adaptive failure")
        return synthetic_worker(task)

    monkeypatch.setattr(adaptive, "run_chunk", failing)
    with pytest.raises(RuntimeError, match="adaptive failure"):
        dispatcher.dispatch(doc.source_path)
    path = next((tmp_path / "runs").iterdir())
    points = list(doc.config.points())
    before = {name: (path / points[0].filename(name)).read_bytes() for name in points[0].tables}
    assert all(not (path / points[1].filename(name)).exists() for name in points[1].tables)
    first_seed = next(seed for p, start, seed in calls if p == .002 and start == 0)
    calls.clear()

    def resumed(task, **options):
        calls.append(task)
        return synthetic_worker(task)

    monkeypatch.setattr(adaptive, "run_chunk", resumed)
    dispatcher.resume(path)
    assert calls[0].point.p == .002 and calls[0].start == 0 and calls[0].seed == first_seed
    assert before == {name: (path / points[0].filename(name)).read_bytes() for name in points[0].tables}
    assert json.loads((path / "metadata.json").read_text())["resume_count"] == 1


def test_fixed_batch_can_use_independent_output_buffer(tmp_path):
    doc = document(tmp_path, batch_size=2, buffer_shot=3, shots=7)
    path = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    for name in point.tables:
        file = pq.ParquetFile(path / point.filename(name))
        assert [file.metadata.row_group(i).num_rows for i in range(3)] == [3, 3, 1]


@pytest.mark.parametrize("kind", ["fig4d_reproduction", "logical_zero_factory"])
def test_saved_legacy_omitted_batch_default_still_loads_and_analyzes(tmp_path, kind):
    from knill_bench.experiments.config_v2 import load_saved_config
    from knill_bench.analysis.fig4d import summarize_saved
    from knill_bench.analysis.factory import analyze_saved
    doc = document(tmp_path, kind=kind, T_tel=8 if kind == "fig4d_reproduction" else 2)
    # Simulate the canonical config saved by the old parser for omitted batch_size.
    legacy = replace(doc, config=replace(doc.config, batch_size=32))
    with RunStore.create(legacy) as store:
        point = next(legacy.config.points())
        store.start_point(point)
        with PointWriter(store.path, point, expected_shots=7) as writer:
            writer.write_batch(np.arange(7, dtype=np.uint64), np.zeros(7, dtype=bool),
                               np.ones((7, point.T_tel), dtype=np.float64) if kind == "logical_zero_factory" else None)
            store.record_complete(writer.commit())
        store.finish()
        path = store.path
    assert load_saved_config(path).config.batch_size == 32
    if kind == "fig4d_reproduction":
        assert summarize_saved(path)[0]["shots"] == 7
    else:
        assert analyze_saved(path)["rows"]
    assert dispatcher.resume(path) == path
