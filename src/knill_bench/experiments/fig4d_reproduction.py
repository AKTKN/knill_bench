"""Fixed eight-cycle Fig.4(d) experiment; point workers stream B0 tables."""

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import multiprocessing

import numpy as np

from knill_bench.data.storage_v2 import PointWriter
from .run_v2 import RunStore
from .seeds import point_seed


def validate_experiment(config):
    if config.kind != "fig4d_reproduction" or config.T_tel != 8:
        raise ValueError("Fig.4(d) requires kind fig4d_reproduction and exactly T_tel=8")
    if config.theta is not None or config.create_codecapacity_dem:
        raise ValueError("Fig.4(d) requires no theta and create_codecapacity_dem=False")
    if any(p.r_0 != p.d or p.r_plus != p.d for p in config.points()):
        raise ValueError("Fig.4(d) requires d noisy preparation rounds on EACH resource block")


def _run_point(path, point, shots, batch_size, seed):
    # Construct native samplers/graphs/maps inside the worker, never pickle them.
    from knill_bench.adapters.hex_full_knill import HexFullKnill
    model = HexFullKnill(point, seed=seed)
    with PointWriter(path, point, expected_shots=shots) as writer:
        for start in range(0, shots, batch_size):
            count = min(batch_size, shots - start)
            raw = model.sample(count)
            decoded = model.decode_batch(raw)  # Offline, after physical sampling.
            writer.write_batch(np.arange(start, start + count, dtype=np.uint64), decoded.logical_error)
        result = writer.commit()
    return result, model.metadata


def _execute(store):
    config = store.document.config
    pending = iter(p for p in config.points() if store.metadata["points"][p.case_id]["status"] != "complete")

    def arguments(point):
        store.start_point(point)
        return store.path, point, config.shots, config.batch_size, point_seed(config.master_seed, point)

    if config.workers == 1:
        for point in pending:
            result, execution = _run_point(*arguments(point))
            store.record_complete(result, execution=execution)
    else:
        # At most workers whole-point tasks exist at once. Each task retains
        # one compiled physical model and one batch, regardless of shot count.
        with ProcessPoolExecutor(max_workers=config.workers,
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            active = {}

            def submit_next():
                point = next(pending, None)
                if point is not None:
                    active[pool.submit(_run_point, *arguments(point))] = point

            for _ in range(config.workers):
                submit_next()
            try:
                while active:
                    completed, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in completed:
                        active.pop(future)
                        result, execution = future.result()
                        store.record_complete(result, execution=execution)
                        submit_next()
            except BaseException:
                for future in active:
                    future.cancel()
                raise
    store.finish()


def run(document, *, resume_path=None):
    validate_experiment(document.config)  # Reject protocol changes before output creation.
    with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
        validate_experiment(store.document.config)
        if store.document.config != document.config:
            raise ValueError("resume document must match the saved run configuration")
        if store.metadata["status"] != "complete":
            _execute(store)
        return store.path
