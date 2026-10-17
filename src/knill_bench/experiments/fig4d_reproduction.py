"""Fixed eight-cycle Fig.4(d) experiment; point workers stream B0 tables."""

import numpy as np

from knill_bench.data.storage_v2 import PointBuffer, PointWriter
from .execution import execute_points
from .run_v2 import RunStore


def validate_experiment(config):
    if config.kind != "fig4d_reproduction" or config.T_tel != 8:
        raise ValueError("Fig.4(d) requires kind fig4d_reproduction and exactly T_tel=8")
    if config.theta is not None or config.create_codecapacity_dem:
        raise ValueError("Fig.4(d) requires no theta and create_codecapacity_dem=False")


def _run_point(path, point, shots, batch_size, seed, *, buffer_shot=None):
    # Construct native samplers/graphs/maps inside the worker, never pickle them.
    from knill_bench.adapters.hex_full_knill import HexFullKnill
    model = HexFullKnill(point, seed=seed)
    with PointWriter(path, point, expected_shots=shots) as writer:
        output = writer if buffer_shot is None else PointBuffer(writer, buffer_shot)
        for start in range(0, shots, batch_size):
            count = min(batch_size, shots - start)
            raw = model.sample(count)
            decoded = model.decode_batch(raw)  # Offline, after physical sampling.
            output.write_batch(np.arange(start, start + count, dtype=np.uint64), decoded.logical_error)
        result = output.commit()
    return result, model.metadata


def _execute(store):
    execute_points(store, _run_point)


def run(document, *, resume_path=None):
    validate_experiment(document.config)  # Reject protocol changes before output creation.
    with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
        validate_experiment(store.document.config)
        if store.document.config != document.config:
            raise ValueError("resume document must match the saved run configuration")
        if store.metadata["status"] != "complete":
            _execute(store)
        return store.path
