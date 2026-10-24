"""Explicit setup-time persistence of boundary models, without Stim parsing."""

import json
import os
from pathlib import Path

from .temporal_dem import TemporalDemModel


def write_temporal_model(path, model: TemporalDemModel) -> str:
    """Exclusively create/fsync one JSON artifact; return its payload SHA256.

    The later preparation runner owns its path/publication. This function
    never overwrites an existing file or constructs a live matching graph.
    """
    artifact = model.to_artifact()
    data = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    with Path(path).open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return artifact["sha256"]


def read_temporal_model(path, *, expected_sha256: str | None = None) -> TemporalDemModel:
    """Validate saved full-column model and optional owning-run hash, no DEM."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate model artifact key: {key}")
            result[key] = value
        return result

    artifact = json.loads(Path(path).read_bytes(), object_pairs_hook=unique_object)
    model = TemporalDemModel.from_artifact(artifact)
    if expected_sha256 is not None and model.artifact_sha256 != expected_sha256:
        raise ValueError("Temporal model artifact does not match owning-run SHA256")
    return model
