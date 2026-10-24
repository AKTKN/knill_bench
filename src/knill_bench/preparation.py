"""Contracts for fixed-R preparation; no circuit construction or execution.

These types are separate from the schema-v1 ``models`` classes. Indices are
absolute, zero-based indices in the named circuit's flattened measurement or
detector stream; round indices are one-based full X-then-Z SE rounds. Static
observable maps describe hypothetical faults, never sampled truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Protocol, TypeAlias

import numpy as np
from numpy.typing import NDArray
import stim

from knill_bench.decoding.temporal_dem import DetectorRole, TemporalDemModel
from knill_bench.decoding.temporal_matching import TemporalMatchingResult


BoolArray: TypeAlias = NDArray[np.bool_]
FloatArray: TypeAlias = NDArray[np.float64]
# One implementation/column-order authority, not a second H/P/F/S/B container.
BoundaryConstraintModel: TypeAlias = TemporalDemModel
PREPARATION_SEMANTICS = "surface_prep_fixed_v1"


class PreparationCapabilityError(ValueError):
    """The requested preparation/model cannot establish the required premises."""


@dataclass(frozen=True)
class PreparationSettings:
    """Resolved protocol settings, not a YAML parser or an execution config.

    R is an explicit positive signed-int64 integer, independent of distance.
    ``adaptive`` means physical stopping; time-adaptive chunk partitioning is
    also excluded from this baseline's later worker contract.
    """

    rounds: int
    prep_basis: Literal["z"] = "z"
    sign_sector: Literal["x"] = "x"
    readout_basis: Literal["z"] = "z"
    logical_evaluation: Literal["prefix_frame_only"] = "prefix_frame_only"
    adaptive: Literal[False] = False

    def __post_init__(self) -> None:
        if type(self.rounds) is not int or not 1 <= self.rounds <= 2**63 - 1:
            raise ValueError("preparation rounds must be an explicit positive signed-int64 integer")
        if ((self.prep_basis, self.sign_sector, self.readout_basis,
             self.logical_evaluation) != ("z", "x", "z", "prefix_frame_only")
                or self.adaptive is not False):
            raise PreparationCapabilityError(
                "surface_prep_fixed requires z/x/z, prefix_frame_only, adaptive=false")


@dataclass(frozen=True)
class PreparationRecord:
    """A measurement record in its owning circuit, with an explicit source.

    SE and probe records use check_index; destructive records use data_qubit.
    Only SE records have round_index. Offline past-probe records belong only
    to completed_ledger; production evaluation records are evaluator-only.
    """

    record_id: int
    source: Literal["se", "output_x_probe", "destructive_z", "past_x_probe"]
    sector: Literal["x", "z"]
    round_index: int | None
    check_index: int | None
    data_qubit: int | None


@dataclass(frozen=True)
class PreparationDetector:
    """A row in the named production/completed circuit, never a mechanism ID."""

    detector_id: int
    sector: Literal["x", "z"]
    round_index: int
    check_index: int
    role: DetectorRole
    record_ids: tuple[int, ...]


@dataclass(frozen=True)
class PreparationLabels:
    """Production observable IDs in Hex matrix check order; one logical Z.

    Canonical ordering is all tau_X, all tau_Z, then logical_Z. The builder
    stores these explicit maps even when some observables never flip at p=0.
    Completed model feature rows are mapped explicitly to the same labels.
    """

    tau_x: tuple[int, ...]
    tau_z: tuple[int, ...]
    logical_z: tuple[int, ...]


@dataclass(frozen=True)
class PreparationOutputCut:
    """Exclusive prefix limits, after R full rounds and before all evaluation.

    instruction_count counts flattened Stim instructions, including noise and
    annotations. measurement_count excludes output probes/destructive readout.
    Last X readout is earlier than this cut and is not output-state truth.
    """

    instruction_count: int
    measurement_count: int
    completed_rounds: int
    location: Literal["after_final_z_extraction"] = "after_final_z_extraction"


@dataclass(frozen=True)
class CompiledPreparationExperiment:
    """Builder output, owned by setup/sampler/evaluator, never the decoder.

    physical_prefix contains initialization and exactly R full noisy rounds.
    circuit adds only ideal evaluation; its detectors are all online.
    completed_circuit is the offline X-sector model with hidden boundary
    probes. Its record/detector IDs have their own namespace. No sampler for
    this circuit belongs in a production worker.

    source_hashes names imported source/resource hashes; model_hashes names
    circuit, ledger, row/label maps and inference-policy hashes. Names and
    SHA256 values are stored as ordered tuples, without mutable dict aliases.
    """

    settings: PreparationSettings
    physical_prefix: stim.Circuit
    circuit: stim.Circuit
    completed_circuit: stim.Circuit
    ledger: tuple[PreparationRecord, ...]
    completed_ledger: tuple[PreparationRecord, ...]
    detectors: tuple[PreparationDetector, ...]
    completed_detectors: tuple[PreparationDetector, ...]
    labels: PreparationLabels
    completed_labels: PreparationLabels
    output_cut: PreparationOutputCut
    source_hashes: tuple[tuple[str, str], ...]
    model_hashes: tuple[tuple[str, str], ...]

    @property
    def online_x_detector_ids(self) -> tuple[int, ...]:
        return tuple(d.detector_id for d in self.detectors if d.sector == "x")

    @property
    def online_z_detector_ids(self) -> tuple[int, ...]:
        return tuple(d.detector_id for d in self.detectors if d.sector == "z")


def _boolean_batch(value: BoolArray, name: str) -> None:
    if not isinstance(value, np.ndarray) or value.dtype != np.bool_ or value.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional bool ndarray")


def _storage_owners(value: np.ndarray) -> set[int]:
    """Include exposed backing objects, even for disjoint slices of one buffer."""
    owners: set[int] = set()
    current: object | None = value
    while current is not None and id(current) not in owners:
        owners.add(id(current))
        if isinstance(current, np.ndarray):
            current = current.base
        elif isinstance(current, memoryview):
            current = current.obj
        else:
            break
    return owners


@dataclass(frozen=True)
class PreparationObservations:
    """The entire online interface: two unpacked bool[shots, detectors] arrays.

    No raw records, last absolute signs, boundary outcomes, truth, compiled
    circuit, or back-reference to PreparationBatch is exposed. Arrays are
    borrowed for one batch and must not be mutated by the decoder.
    """

    online_x_detectors: BoolArray
    online_z_detectors: BoolArray

    def __post_init__(self) -> None:
        _boolean_batch(self.online_x_detectors, "online_x_detectors")
        _boolean_batch(self.online_z_detectors, "online_z_detectors")
        if len(self.online_x_detectors) != len(self.online_z_detectors):
            raise ValueError("online detector arrays must have equal shot counts")


@dataclass(frozen=True)
class PreparationTruth:
    """Evaluator-only flip labels, never absolute random X signs.

    tau_X = last_X XOR ideal output_X; tau_Z = last_Z XOR H_Z r_Z;
    logical_Z = L_Z r_Z. Arrays are bool[shots, checks] and bool[shots, 1].
    These labels do not identify the actual sampled fault mechanisms.
    """

    tau_x: BoolArray
    tau_z: BoolArray
    logical_z: BoolArray

    def __post_init__(self) -> None:
        for name in ("tau_x", "tau_z", "logical_z"):
            _boolean_batch(getattr(self, name), name)
        if len({len(self.tau_x), len(self.tau_z), len(self.logical_z)}) != 1:
            raise ValueError("truth arrays must have equal shot counts")
        if self.logical_z.shape[1] != 1:
            raise ValueError("surface preparation requires exactly one logical Z label")


@dataclass(frozen=True)
class PreparationBatch:
    """Sampler output; only observations' two arrays cross the decoder API.

    Truth must have independent storage: even following an observation's NumPy
    base buffer must not expose evaluator data. Frozen dataclasses protect
    field bindings; they do not make borrowed arrays or Stim circuits immutable.
    """

    observations: PreparationObservations
    truth: PreparationTruth

    def __post_init__(self) -> None:
        if len(self.observations.online_x_detectors) != len(self.truth.tau_x):
            raise ValueError("observations and truth must have equal shot counts")
        for online in (self.observations.online_x_detectors, self.observations.online_z_detectors):
            for hidden in (self.truth.tau_x, self.truth.tau_z, self.truth.logical_z):
                if (_storage_owners(online) & _storage_owners(hidden)
                        or np.may_share_memory(online, hidden)):
                    raise ValueError("online observations must not share truth storage")


class PreparationStatus(str, Enum):
    OK = "ok"
    INVALID_SYNDROME = "invalid_syndrome"
    NO_COMPLEMENTARY_SOLUTION = "no_complementary_solution"
    Z_DECODER_INVALID = "z_decoder_invalid"


@dataclass(frozen=True)
class PreparationPrediction:
    """Adapter output; masks define availability of zero placeholder features.

    baseline_weight/complementary_weight are float64 representations of common
    integer costs (infinity when unavailable); gap is (W1-W0)/weight_scale,
    a quantized natural-log score, NaN when unavailable. It is never clipped.
    status=ok requires all three validity masks; a valid X-only gap may still
    exist when Z decoding fails. Structural/numerical failures raise instead
    of creating an ok row. No Pauli correction is applied to physical data.

    debug is a seed-core full-witness result for the active-column subset;
    expand through BoundaryConstraintModel.expand_errors before reporting
    original DEM columns. It is absent from ordinary compact production.
    """

    tau_x_prediction: BoolArray
    tau_z_prediction: BoolArray
    logical_z_prediction: BoolArray
    baseline_weight: FloatArray
    complementary_weight: FloatArray
    gap: FloatArray
    baseline_valid: BoolArray
    complementary_valid: BoolArray
    z_decoder_valid: BoolArray
    status: NDArray[np.str_]
    weight_scale: float
    debug: TemporalMatchingResult | None = None


class PreparationDecoder(Protocol):
    """Construct from static models only; no compiled evaluator or sampled truth."""

    def decode_batch(self, online_x_detectors: BoolArray,
                     online_z_detectors: BoolArray) -> PreparationPrediction: ...
