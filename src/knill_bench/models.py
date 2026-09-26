from dataclasses import dataclass, field
from typing import Any
import numpy as np
import stim


@dataclass
class CompiledExperiment:
    circuit: stim.Circuit
    dem: stim.DetectorErrorModel
    ledger: list[dict]
    detectors: list[dict]
    observable_records: list[int]
    metadata: dict
    native: Any = None


@dataclass
class RawSamples:
    measurements: np.ndarray
    syndromes: np.ndarray
    observables: np.ndarray


@dataclass
class Predictions:
    logical_flips: np.ndarray
    valid: np.ndarray
    residual: list[int | None]
    diagnostics: list[dict] = field(default_factory=list)
    output_kind: str = "logical_observable_flip_predictions"
