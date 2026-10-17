"""Time-adaptive v2 chunks with worker-local models and bounded ordered output.

Seeds identify assigned chunks, never a process. As in sinter-style collection,
wall-time feedback changes the partition: fixed seeds alone do not promise
bitwise-identical data across runs. Fixed batch_size retains the legacy path.
"""

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
import hashlib
import math
import multiprocessing
import os
import time

import numpy as np

from knill_bench.data.storage_v2 import PointBuffer, PointWriter
from .config_v2 import canonical
from .seeds import chunk_seed

POLICY = "time_adaptive_chunks_v1"
# A heuristic bound on raw records plus decoder temporaries, not an RSS limit.
WORKING_BYTES = 64 * 1024 * 1024
MAX_CHUNK_SHOTS = 65_536
_MODEL = None


@dataclass(frozen=True)
class ChunkTask:
    point: object
    chunk_id: int
    start: int
    shots: int
    seed: int


@dataclass(frozen=True)
class ChunkResult:
    chunk_id: int
    start: int
    shots: int
    labels: np.ndarray
    gaps: np.ndarray | None
    seconds: float
    setup_seconds: float
    max_shots: int
    pid: int
    execution: dict | None


@dataclass
class ChunkSizer:
    target_seconds: float
    cap: int
    previous: int = 1
    seconds_per_shot: float | None = None

    def observe(self, shots, seconds):
        if math.isfinite(seconds) and seconds > 0:
            observed = seconds / shots
            if math.isfinite(observed) and observed > 0:
                self.seconds_per_shot = (observed if self.seconds_per_shot is None else
                                        .5 * observed + .5 * self.seconds_per_shot)
        self.previous = shots

    def count(self, remaining, slots=1):
        if remaining <= 0:
            return 0
        if self.seconds_per_shot is None:
            desired = 1  # A real one-shot probe, never discarded calibration data.
        else:
            ratio = self.target_seconds / self.seconds_per_shot
            desired = self.cap if not math.isfinite(ratio) else max(1, round(ratio))
        # Slow ramp avoids multiplying an optimistic one-shot estimate at once.
        # Reserve a tail share for each available worker, including one-point runs.
        return min(self.cap, max(1, min(desired, 2 * self.previous)),
                   max(1, (remaining + slots - 1) // slots))


def _compile_model(point, seed, options):
    if point.kind == "se_memory":
        from knill_bench.adapters.hex_memory import HexMemory
        model = HexMemory(point, seed=seed)
        return model, model.circuit, model.metadata
    if point.kind == "fig4d_reproduction":
        from knill_bench.adapters.hex_full_knill import HexFullKnill
        model = HexFullKnill(point, seed=seed)
        return model, model.engine.circuit, model.metadata
    from .logical_zero_factory import _prepare_point
    _, model, execution = _prepare_point(point, seed, **options)
    return model, model.circuit, execution


def run_chunk(task, **options):
    """Cache one physical model/decoder per process; reseed only the sampler.

    Theta is absent. Only decoded labels/gaps cross the process boundary.
    Setup is measured separately and excluded from throughput feedback.
    """
    global _MODEL
    key = (task.point, tuple(sorted(options.items())))
    setup_started = time.monotonic()
    fresh = _MODEL is None or _MODEL[0] != key
    if fresh:
        _MODEL = None  # Release the previous point before allocating the next.
        model, circuit, execution = _compile_model(task.point, task.seed, options)
        _MODEL = (key, model, circuit, execution)
    _, model, circuit, execution = _MODEL
    setup_seconds = time.monotonic() - setup_started if fresh else 0.
    started = time.monotonic()
    # Model/graphs/maps remain cached. A new sampler gives each chunk a stream
    # independent of which worker receives it; no dependency globals are patched.
    sampler = circuit.compile_sampler(seed=task.seed)
    raw = sampler.sample(shots=task.shots)
    if task.point.kind in {"fig4d_reproduction", "se_memory"}:
        decoded = model.decode_batch(raw)
        labels = decoded.logical_error
        gaps = getattr(decoded, "gaps", None)
    else:
        from .logical_zero_factory import _decode_chunk
        decoded = _decode_chunk(model, raw, task.start, task.point, execution["score_units"])
        labels, gaps = decoded.logical_error, decoded.gaps
    elapsed = time.monotonic() - started
    # Raw bool records, repaired copies, detector/frame/matching arrays. Large
    # native graphs remain model-dependent and outside this heuristic budget.
    width = max(1, circuit.num_measurements + 4 * circuit.num_qubits + 8 * task.point.T_tel)
    cap = max(1, min(MAX_CHUNK_SHOTS, WORKING_BYTES // (8 * width)))
    return ChunkResult(task.chunk_id, task.start, task.shots, labels, gaps, elapsed,
                       setup_seconds, cap, os.getpid(), execution if fresh else None)


def _validate_result(task, result):
    if ((result.chunk_id, result.start, result.shots) != (task.chunk_id, task.start, task.shots)
            or not isinstance(result.labels, np.ndarray) or result.labels.dtype != bool
            or result.labels.shape != (task.shots,)
            or not math.isfinite(result.seconds) or result.seconds < 0
            or not math.isfinite(result.setup_seconds) or result.setup_seconds < 0
            or type(result.max_shots) is not int or result.max_shots < 1):
        raise ValueError("adaptive worker result identity/count/timing mismatch")
    gaps = result.gaps
    if "logical_gaps" in task.point.tables:
        if (not isinstance(gaps, np.ndarray) or gaps.dtype != np.float64
                or gaps.shape != (task.shots, task.point.T_tel) or not np.isfinite(gaps).all()
                or (gaps < 0).any()):
            raise ValueError("adaptive worker requires finite nonnegative aligned gaps")
    elif gaps is not None:
        raise ValueError("Fig.4(d) cannot return gaps")


def _execute_point(store, point, pool, worker, options):
    config = store.document.config
    store.start_point(point)
    sizer = ChunkSizer(config.target_chunk_seconds, min(config.output_buffer_shots, MAX_CHUNK_SHOTS))
    next_start = next_chunk = write_chunk = 0
    pending, ready = {}, {}
    execution = None
    partition = hashlib.sha256()
    pids = set()
    chunks = total_seconds = setup_seconds = 0
    min_count = config.shots
    max_count = 0
    min_seconds = math.inf
    max_seconds = 0.

    def task_for_next():
        nonlocal next_start, next_chunk
        count = sizer.count(config.shots - next_start, config.workers)
        task = ChunkTask(point, next_chunk, next_start, count,
                         chunk_seed(config.master_seed, point, next_chunk, stream=POLICY))
        partition.update(canonical([task.chunk_id, task.start, task.shots, task.seed]).encode() + b"\n")
        next_start += count
        next_chunk += 1
        return task

    with PointWriter(store.path, point, expected_shots=config.shots) as writer:
        output = PointBuffer(writer, config.output_buffer_shots)
        try:
            while next_start < config.shots or pending or ready:
                if pool is None:
                    task = task_for_next()
                    results = [(task, worker(task, **options))]
                else:
                    # Keep completed out-of-order chunks in the SAME window.
                    # A delayed head can retain at most workers-1 results.
                    while next_start < config.shots and len(pending) + len(ready) < config.workers:
                        task = task_for_next()
                        pending[pool.submit(worker, task, **options)] = task
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    results = [(pending.pop(future), future.result()) for future in done]
                for task, result in results:
                    _validate_result(task, result)
                    sizer.cap = min(sizer.cap, result.max_shots)
                    sizer.observe(task.shots, result.seconds)
                    if result.execution is not None:
                        if execution is not None and execution != result.execution:
                            raise ValueError("worker model metadata disagree")
                        execution = result.execution
                    ready[task.chunk_id] = result
                    chunks += 1
                    pids.add(result.pid)
                    total_seconds += result.seconds
                    setup_seconds += result.setup_seconds
                    min_count, max_count = min(min_count, task.shots), max(max_count, task.shots)
                    min_seconds, max_seconds = min(min_seconds, result.seconds), max(max_seconds, result.seconds)
                while write_chunk in ready:
                    result = ready.pop(write_chunk)
                    output.write_batch(np.arange(result.start, result.start + result.shots, dtype=np.uint64),
                                       result.labels, result.gaps)
                    write_chunk += 1
            if execution is None:
                raise ValueError("worker omitted model metadata")
            result = output.commit()
        except BaseException:
            for future in pending:
                future.cancel()
            raise
    execution = dict(execution)
    execution.update(sampling="independently_chunk_seeded_stim_samplers", parallel_execution=POLICY,
                     buffer_shot=config.output_buffer_shots, target_chunk_seconds=config.target_chunk_seconds,
                     chunk_seed_stream=POLICY, chunk_partition_sha256=partition.hexdigest(),
                     chunk_count=chunks, chunk_shots_min=min_count, chunk_shots_max=max_count,
                     chunk_seconds_min=min_seconds, chunk_seconds_max=max_seconds,
                     sampling_decode_seconds=total_seconds, worker_setup_seconds=setup_seconds,
                     workers_used=len(pids), automatic_chunk_shot_cap=sizer.cap,
                     timing_excludes="model_setup_ipc_and_output", bitwise_replay_requires_fixed_partition=True)
    store.record_complete(result, execution=execution)


def execute_adaptive(store, *, worker=None, **options):
    """Use all workers within each point; parent owns writers and metadata.

    One pool persists across points, with one cached model per worker. Results
    and reorder storage are bounded by workers * min(buffer_shot, automatic cap).
    An unfinished point always restarts at zero; complete point files survive.
    """
    global _MODEL
    _MODEL = None
    if worker is None:
        worker = run_chunk
    config = store.document.config
    completed = {key for key, info in store.metadata["points"].items() if info["status"] == "complete"}
    points = (point for point in config.points() if point.case_id not in completed)
    try:
        if config.workers == 1:
            for point in points:
                _execute_point(store, point, None, worker, options)
        else:
            with ProcessPoolExecutor(max_workers=config.workers,
                                     mp_context=multiprocessing.get_context("spawn")) as pool:
                for point in points:
                    _execute_point(store, point, pool, worker, options)
        store.finish()
    finally:
        _MODEL = None
