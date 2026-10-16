"""Schedule-independent uint64 identities; no physical sampler construction."""

import hashlib

from .config_v2 import ExperimentPoint, _integer, canonical

SEED_DERIVATION = "sha256_auxiliary_v2_uint64_little_endian_v1"


def _derive(master: int, point: ExperimentPoint, stream: str, chunk: int | None):
    _integer(master, "master_seed", 0, 2**64 - 1)
    payload = canonical([SEED_DERIVATION, master, point.sampling_identity, stream, chunk])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def point_seed(master: int, point: ExperimentPoint) -> int:
    return _derive(master, point, "point", None)


def chunk_seed(master: int, point: ExperimentPoint, chunk: int, *, stream: str = "chunk") -> int:
    _integer(chunk, "chunk", 0)
    if not isinstance(stream, str) or not stream:
        raise ValueError("stream must be nonempty")
    return _derive(master, point, stream, chunk)
