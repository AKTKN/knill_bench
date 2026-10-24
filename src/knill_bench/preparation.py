"""Contracts and production sample splitting for fixed-R preparation.

These types are separate from the schema-v1 ``models`` classes. Indices are
absolute, zero-based indices in the named circuit's flattened measurement or
detector stream; round indices are one-based full X-then-Z SE rounds. Static
observable maps describe hypothetical faults, never sampled truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
class PreparationObservable:
    """A deterministic evaluation parity in its owning circuit's records."""

    observable_id: int
    metric: Literal["tau_x", "tau_z", "logical_z"]
    check_index: int | None
    record_ids: tuple[int, ...]


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
    distance: int
    physical_probability: float
    decoding_probability: float
    data_qubits: tuple[int, ...]
    physical_prefix: stim.Circuit
    circuit: stim.Circuit
    model_circuit: stim.Circuit
    completed_circuit: stim.Circuit
    dem: stim.DetectorErrorModel
    model_dem: stim.DetectorErrorModel
    completed_dem: stim.DetectorErrorModel
    ledger: tuple[PreparationRecord, ...]
    completed_ledger: tuple[PreparationRecord, ...]
    detectors: tuple[PreparationDetector, ...]
    completed_detectors: tuple[PreparationDetector, ...]
    labels: PreparationLabels
    completed_labels: PreparationLabels
    observables: tuple[PreparationObservable, ...]
    completed_observables: tuple[PreparationObservable, ...]
    output_cut: PreparationOutputCut
    source_hashes: tuple[tuple[str, str], ...]
    model_hashes: tuple[tuple[str, str], ...]
    hex_revision: str
    hex_dirty: bool

    @property
    def online_x_detector_ids(self) -> tuple[int, ...]:
        return tuple(d.detector_id for d in self.detectors if d.sector == "x")

    @property
    def online_z_detector_ids(self) -> tuple[int, ...]:
        return tuple(d.detector_id for d in self.detectors if d.sector == "z")

    @property
    def metadata(self) -> dict:
        """JSON-compatible setup descriptor; no sampled values or timing claims."""
        return dict(
            protocol="surface_prep_fixed", semantics_version=PREPARATION_SEMANTICS,
            distance=self.distance, settings=asdict(self.settings), noise_profile="hex_legacy",
            physical_probability=self.physical_probability, decoding_probability=self.decoding_probability,
            native_noise_scope="native_reset_readout_flips_and_two_qubit_depolarization_no_idle_or_one_qubit_noise",
            z_prefix_anchor="known_initial_zero", sign_target="output_state_after_final_Z_extraction",
            output_cut=asdict(self.output_cut), physical_se_rounds=self.settings.rounds,
            physical_blocks=1, teleportations=0, physical_measurements=self.physical_prefix.num_measurements,
            physical_qubits=self.physical_prefix.num_qubits,
            elapsed_time=None, spacetime_volume=None,
            evaluation_measurements=self.circuit.num_measurements-self.output_cut.measurement_count,
            offline_past_probes=len(self.labels.tau_x),
            online_x_detector_ids=self.online_x_detector_ids, online_z_detector_ids=self.online_z_detector_ids,
            evaluation_labels=asdict(self.labels), completed_evaluation_labels=asdict(self.completed_labels),
            completed_detector_roles=tuple(d.role.value for d in self.completed_detectors),
            logical_evaluation="prefix_frame_only", physical_correction_applied=False,
            software_correction="evaluation_parity_xor_once", terminal_recovery=False,
            output_probe="ideal_X_stabilizer_MPP", final_readout="ideal_destructive_Z_evaluation_only",
            offline_completion_sampled=False, instrument_validation="signed_CSS_and_logical_flows",
            source_hashes=dict(self.source_hashes), model_hashes=dict(self.model_hashes),
            hex_revision=self.hex_revision, hex_dirty=self.hex_dirty,
        )


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
class PreparationDiagnostics:
    """Selected X baseline fiber, masked by baseline_valid, and Z cost.

    Frozen IDs index the full completed DEM; assignments include zeros and
    ones in that order. Full-mode Z witnesses use its active-column order,
    with a separate same-mode agreement flag. No sampled hidden values appear.
    """

    frozen_original_columns: tuple[int, ...]
    baseline_frozen: BoolArray
    baseline_past: BoolArray
    baseline_future: BoolArray
    z_weight: FloatArray
    z_errors: NDArray[np.uint8] | None = None
    z_debug_matches_compact: BoolArray | None = None


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
    diagnostics: PreparationDiagnostics | None = None

    @property
    def x_baseline_valid(self) -> BoolArray:
        """Explicit sector name for the existing baseline_valid contract."""
        return self.baseline_valid

    def __post_init__(self) -> None:
        for name in ("tau_x_prediction", "tau_z_prediction", "logical_z_prediction"):
            _boolean_batch(getattr(self, name), name)
        count = len(self.tau_x_prediction)
        if (len(self.tau_z_prediction) != count or self.logical_z_prediction.shape != (count, 1)):
            raise ValueError("preparation predictions must align shots and one logical Z")
        for name in ("baseline_valid", "complementary_valid", "z_decoder_valid"):
            value = getattr(self, name)
            if not isinstance(value, np.ndarray) or value.dtype != np.bool_ or value.shape != (count,):
                raise ValueError(f"{name} must be bool[shots]")
        if (self.complementary_valid & ~self.baseline_valid).any():
            raise ValueError("complementary validity requires baseline validity")
        for name, valid in (("baseline_weight", self.baseline_valid),
                            ("complementary_weight", self.complementary_valid)):
            value = getattr(self, name)
            if (not isinstance(value, np.ndarray) or value.dtype != np.float64 or value.shape != (count,)
                    or not np.isfinite(value[valid]).all() or (value[valid] < 0).any()
                    or (value[valid] > 2**53 - 1).any() or not np.equal(value[valid], np.rint(value[valid])).all()
                    or not np.isposinf(value[~valid]).all()):
                raise ValueError(f"{name} must contain valid integer costs or unavailable +infinity")
        try:
            scale = float(self.weight_scale)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("weight_scale must be finite and positive") from error
        if (isinstance(self.weight_scale, (bool, np.bool_)) or not isinstance(self.weight_scale, (int, float))
                or not np.isfinite(scale) or scale <= 0):
            raise ValueError("weight_scale must be finite and positive")
        if (not isinstance(self.gap, np.ndarray) or self.gap.dtype != np.float64 or self.gap.shape != (count,)
                or not np.isnan(self.gap[~self.complementary_valid]).all()
                or not np.isfinite(self.gap[self.complementary_valid]).all()
                or (self.gap[self.complementary_valid] < 0).any()):
            raise ValueError("gap must be finite nonnegative when available, NaN otherwise")
        mask = self.complementary_valid
        if not np.array_equal(self.gap[mask], (self.complementary_weight[mask] - self.baseline_weight[mask]) / self.weight_scale):
            raise ValueError("gap disagrees with the common integer objective/scale")
        expected = np.full(count, PreparationStatus.INVALID_SYNDROME.value, dtype="<U26")
        expected[self.baseline_valid] = PreparationStatus.NO_COMPLEMENTARY_SOLUTION.value
        expected[mask] = PreparationStatus.Z_DECODER_INVALID.value
        expected[mask & self.z_decoder_valid] = PreparationStatus.OK.value
        if not isinstance(self.status, np.ndarray) or self.status.shape != (count,) or not np.array_equal(self.status, expected):
            raise ValueError("preparation status disagrees with independent validity masks")
        if self.diagnostics is not None:
            diag = self.diagnostics
            if (diag.baseline_frozen.dtype != np.bool_ or diag.baseline_frozen.shape != (count, len(diag.frozen_original_columns))
                    or diag.baseline_past.dtype != np.bool_ or diag.baseline_past.shape != (count,)
                    or diag.baseline_future.dtype != np.bool_ or diag.baseline_future.shape != (count,)
                    or diag.z_weight.dtype != np.float64 or diag.z_weight.shape != (count,)
                    or not np.isfinite(diag.z_weight[self.z_decoder_valid]).all()
                    or (diag.z_weight[self.z_decoder_valid] < 0).any()
                    or not np.isposinf(diag.z_weight[~self.z_decoder_valid]).all()):
                raise ValueError("preparation diagnostic dimensions/costs disagree with validity")


class PreparationDecoder(Protocol):
    """Construct from static models only; no compiled evaluator or sampled truth."""

    def decode_batch(self, online_x_detectors: BoolArray,
                     online_z_detectors: BoolArray) -> PreparationPrediction: ...


def split_preparation_samples(compiled: CompiledPreparationExperiment,
                              detectors: BoolArray, observables: BoolArray) -> PreparationBatch:
    """Split a production detector-sampler batch using explicit compiled maps.

    This does not simulate, decode, repair or score. Copies detach online input
    buffers from both raw sampler buffers and all evaluator labels. Never pass
    completed-circuit samples here; its row namespace includes hidden probes.
    """
    _boolean_batch(detectors, "detectors")
    _boolean_batch(observables, "observables")
    if detectors.shape != (len(observables), compiled.circuit.num_detectors):
        raise ValueError("production detector count/shot count does not match compiled maps")
    if observables.shape[1] != compiled.circuit.num_observables:
        raise ValueError("production observable count does not match compiled labels")
    return PreparationBatch(
        PreparationObservations(detectors[:, compiled.online_x_detector_ids].copy(),
                                detectors[:, compiled.online_z_detector_ids].copy()),
        PreparationTruth(observables[:, compiled.labels.tau_x].copy(),
                         observables[:, compiled.labels.tau_z].copy(),
                         observables[:, compiled.labels.logical_z].copy()),
    )
