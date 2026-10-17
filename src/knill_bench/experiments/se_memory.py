"""Hex d-round Z memory, optional complementary gap, shared bounded execution."""

import numpy as np

from knill_bench.data.storage_v2 import PointBuffer, PointWriter
from .execution import execute_points
from .run_v2 import RunStore


def _run_point(path, point, shots, batch_size, seed, *, buffer_shot=None):
    from knill_bench.adapters.hex_memory import HexMemory
    model = HexMemory(point, seed=seed)
    with PointWriter(path, point, expected_shots=shots) as writer:
        output = writer if buffer_shot is None else PointBuffer(writer, buffer_shot)
        for start in range(0, shots, batch_size):
            count = min(batch_size, shots - start)
            decoded = model.decode_batch(model.sample(count))
            if point.get_logicalgap and (decoded.gaps is None or decoded.gaps.dtype != np.float64
                                        or decoded.gaps.shape != (count, 1)
                                        or not np.isfinite(decoded.gaps).all() or (decoded.gaps < 0).any()):
                raise ValueError("requested memory gaps must be present, finite and nonnegative")
            output.write_batch(np.arange(start, start + count, dtype=np.uint64), decoded.logical_error, decoded.gaps)
        result = output.commit()
    return result, model.metadata


def run(document, *, resume_path=None):
    if document.config.kind != "se_memory":
        raise ValueError("memory runner requires kind se_memory")
    with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
        if store.document.config != document.config:
            raise ValueError("resume document must match saved memory configuration")
        if store.metadata["status"] != "complete":
            execute_points(store, _run_point)
        return store.path
