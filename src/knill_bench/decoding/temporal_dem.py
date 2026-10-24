"""Typed temporal matching inputs from an explicitly completed Stim DEM.

The input is the selected-CSS *completed* detector model: every detector row
must be labelled ``past``, ``online``, or ``future`` by the circuit builder.
Past/future rows retain their individual check identities until graphlikeness
and spatial ports have been checked.  Only then are the rows of each temporal
slice XORed into a virtual vertex.  An ordinary open-window DEM and detector
coordinates cannot supply this information unambiguously.

Boundary completion is a model assumption, not something this parser proves.
Its builder must validate the noiseless measurement flows and the response of
the completed circuit against the original public records/evaluation labels.
For a shadow-probe construction this includes establishing that the discarded
ideal probes preserve those statistics.  The graph certificate here concerns
``completed_dem_term`` columns, not original physical fault locations or an
automatic lift of a decomposed DEM back to physical Pauli mechanisms.

Each error instruction is retained as a distinct independent DEM variable,
including duplicate signatures, zero-online columns and evaluation-only terms.
Separators are rejected: silently treating correlated decomposition components
as independent graph edges would change both the model and the cost.  ``L``
targets become feature labels; their sampled values are never decoder inputs.

Probabilities must satisfy 0 <= p < 1/2.  All positive-probability costs use one
specified scale for round(scale * log((1-p)/p)).  A zero-probability term stays
in the truth/provenance arrays but is excluded by ``matching_kwargs()``.  Its
stored zero cost is a placeholder, NOT permission to choose an impossible
event.  Always use that method when constructing ``TemporalMatching``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from numbers import Integral
from typing import Mapping, Sequence

import numpy as np
from scipy.sparse import csc_matrix
import stim


MAX_EDGE_WEIGHT = 2**24 - 1
MAX_EXACT_TOTAL_WEIGHT = 2**53 - 1


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash_payload(value) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class DetectorRole(str, Enum):
    PAST = "past"
    ONLINE = "online"
    FUTURE = "future"


@dataclass(frozen=True)
class CompletedDemTerm:
    """Provenance of one flattened error instruction, before any merging.

    ``instruction_index`` indexes all instructions in ``dem.flattened()``;
    ``term_index`` indexes only error instructions and is also the full column
    index.  Detector/observable IDs are their parity-reduced full signatures.
    Neither index claims to identify an original circuit noise instruction.
    """

    term_index: int
    instruction_index: int
    detector_ids: tuple[int, ...]
    observable_ids: tuple[int, ...]


@dataclass(frozen=True)
class TemporalDemModel:
    """Unmerged full-column model and its explicit decoder projection.

    Matrix columns and mechanism IDs always include inactive p=0 terms.
    ``active_columns`` is the ordered subset with p>0; it is distinct from the
    matching core's subset of *unfrozen* columns.  ``frozen_columns`` identifies
    spatial open ports from degree one in the individual completed-row graph,
    including ports having no online detector.  Zero-online columns have a
    baseline estimate of zero under minimum-weight decoding, not known truth.
    """

    h_completed: csc_matrix
    h_online: csc_matrix
    past: np.ndarray
    future: np.ndarray
    frozen_columns: np.ndarray
    feature_map: csc_matrix
    probabilities: np.ndarray
    weights: np.ndarray
    mechanism_ids: tuple[str, ...]
    detector_roles: tuple[DetectorRole, ...]
    online_detector_ids: np.ndarray
    past_detector_ids: np.ndarray
    future_detector_ids: np.ndarray
    active_columns: np.ndarray
    inactive_columns: np.ndarray
    terms: tuple[CompletedDemTerm, ...]
    float_weights: np.ndarray
    num_observables: int
    feature_observable_ids: tuple[int, ...]
    feature_ids: tuple[str, ...]
    provenance_json: str
    weight_scale: float
    source_dem_sha256: str
    provenance_kind: str = "completed_dem_term"
    strictness: str = "completed_individual_degree_le_2_no_separators_v1"
    weight_rounding: str = "numpy_rint_ties_to_even"

    @property
    def full_detector_support(self) -> tuple[tuple[int, ...], ...]:
        return tuple(term.detector_ids for term in self.terms)

    @property
    def unidentifiable_columns(self) -> np.ndarray:
        """Evaluation-labelled events with no completed syndrome evidence."""
        return np.flatnonzero((np.diff(self.h_completed.indptr) == 0)
                              & (np.diff(self.feature_map.indptr) != 0))

    @property
    def metadata(self) -> dict:
        """Finite JSON weight policy and full-column provenance descriptor.

        Null float costs mean +infinity for impossible p=0 events. Active
        rounded-zero costs are allowed, without clipping; the matching core
        chooses zero for invisible columns and may choose tied visible edges.
        """
        return dict(
            provenance_kind=self.provenance_kind, strictness=self.strictness,
            provenance=json.loads(self.provenance_json), source_dem_sha256=self.source_dem_sha256,
            weight_scale=self.weight_scale, weight_rounding=self.weight_rounding,
            float_weight_formula="log1p(-p)-log(p)", cost_unit="common_integer_scaled_natural_log",
            probability_range="0 <= p < 0.5", max_edge_weight=MAX_EDGE_WEIGHT,
            max_exact_total_weight=MAX_EXACT_TOTAL_WEIGHT,
            inactive_policy="p0_excluded_from_solver_float_cost_positive_infinity",
            active_zero_policy="retain_quantized_zero_no_clipping",
            float_weights=[float(w) if np.isfinite(w) else None for w in self.float_weights],
            active_columns=self.active_columns.tolist(), inactive_columns=self.inactive_columns.tolist(),
            unidentifiable_columns=self.unidentifiable_columns.tolist(),
            mechanism_ids=list(self.mechanism_ids), feature_ids=list(self.feature_ids),
            feature_observable_ids=list(self.feature_observable_ids),
        )

    def to_artifact(self) -> dict:
        """Versioned full-column artifact; no DEM text or live solver needed.

        Explicit terms, roles and label order are authoritative. Loading
        validates and reconstructs sparse arrays, never reparses a Stim DEM.
        The hash detects accidental modification; it is not authentication.
        """
        payload = dict(
            artifact_version=1, num_observables=self.num_observables,
            detector_roles=[role.value for role in self.detector_roles],
            terms=[dict(term_index=t.term_index, instruction_index=t.instruction_index,
                        detector_ids=list(t.detector_ids), observable_ids=list(t.observable_ids))
                   for t in self.terms],
            probabilities=self.probabilities.tolist(), weights=self.weights.tolist(),
            metadata=self.metadata,
        )
        return dict(payload=payload, sha256=_hash_payload(payload))

    @property
    def artifact_sha256(self) -> str:
        return self.to_artifact()["sha256"]

    @classmethod
    def from_artifact(cls, artifact: Mapping) -> TemporalDemModel:
        """Load with schema, hash, range and derived-policy checks (no Stim)."""
        return _model_from_artifact(artifact)

    @property
    def num_mechanisms(self) -> int:
        return len(self.mechanism_ids)

    @property
    def zero_online_columns(self) -> np.ndarray:
        """Columns invisible to the online syndrome, retained in truth maps."""
        return np.flatnonzero(np.diff(self.h_online.indptr) == 0)

    @property
    def invisible_columns(self) -> np.ndarray:
        """Columns with no completed detector; labels/noise are still retained."""
        return np.flatnonzero(np.diff(self.h_completed.indptr) == 0)

    def matching_kwargs(self) -> dict:
        """Return safe ``TemporalMatching`` constructor inputs, excluding p=0.

        Returned error witnesses use ``active_columns`` order.  Mechanism IDs
        retain their original full-column identity; ``expand_errors`` maps
        witnesses back to the full truth/provenance arrays.  Every retained
        term keeps the same precomputed integer weight in both matchers.
        """
        selected = self.active_columns
        frozen = np.flatnonzero(np.isin(selected, self.frozen_columns))
        return {
            "h_online": self.h_online[:, selected],
            "past": self.past[selected].copy(),
            "future": self.future[selected].copy(),
            "frozen_columns": frozen,
            "weights": self.weights[selected].copy(),
            "feature_map": self.feature_map[:, selected],
            "mechanism_ids": tuple(self.mechanism_ids[j] for j in selected),
        }

    def expand_errors(self, active_errors) -> np.ndarray:
        """Restore original columns in binary shot-major decoder witnesses."""
        errors = np.asarray(active_errors)
        if (errors.ndim != 2 or errors.shape[1] != len(self.active_columns)
                or not np.isin(errors, [0, 1]).all()):
            raise ValueError("active_errors must be binary (shots, active_columns)")
        full = np.zeros((len(errors), self.num_mechanisms), dtype=np.uint8)
        full[:, self.active_columns] = errors
        return full


def bernoulli_integer_weights(probabilities, *, weight_scale: float = 1000) -> np.ndarray:
    """Quantize independent Bernoulli costs once, without clipping or rescaling.

    Zero probabilities receive an inactive placeholder of zero; callers must
    exclude these columns from optimization.  p>=1/2 is intentionally outside
    this baseline implementation (no negative-cost/reference-frame transform).
    """
    try:
        scale = float(weight_scale)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("weight_scale must be finite and positive") from error
    if isinstance(weight_scale, (bool, np.bool_)) or not np.isfinite(scale) or scale <= 0:
        raise ValueError("weight_scale must be finite and positive")
    raw = np.asarray(probabilities)
    if raw.ndim != 1 or not np.isrealobj(raw):
        raise ValueError("probabilities must be a real one-dimensional array")
    try:
        probs = raw.astype(np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("probabilities must be finite and satisfy 0 <= p < 0.5") from error
    if not np.isfinite(probs).all() or (probs < 0).any() or (probs >= 0.5).any():
        raise ValueError("probabilities must be finite and satisfy 0 <= p < 0.5")
    positive = probs > 0
    quantized = np.zeros(len(probs), dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        quantized[positive] = np.rint(
            scale * (np.log1p(-probs[positive]) - np.log(probs[positive])))
    if (not np.isfinite(quantized).all() or (quantized < 0).any()
            or (quantized > MAX_EDGE_WEIGHT).any()):
        raise ValueError("Quantized edge weights must be finite integers <= 2**24-1; reduce weight_scale")
    weights = quantized.astype(np.int64)
    if sum(map(int, weights)) > MAX_EXACT_TOTAL_WEIGHT:
        raise ValueError("Total integer cost exceeds exact float64 precision (2**53-1)")
    return weights


def _roles(detector_roles, count: int) -> tuple[DetectorRole, ...]:
    if detector_roles is None:
        raise ValueError("Complete detector_roles metadata is required; online DEM boundaries cannot be inferred")
    if isinstance(detector_roles, Mapping):
        keys = tuple(detector_roles)
        if (any(isinstance(k, (bool, np.bool_)) or not isinstance(k, Integral) for k in keys)
                or set(keys) != set(range(count))):
            raise ValueError("detector_roles must cover every completed detector ID exactly")
        values = [detector_roles[j] for j in range(count)]
    else:
        if isinstance(detector_roles, (str, bytes)):
            raise ValueError("detector_roles must contain one role per completed detector")
        try:
            values = list(detector_roles)
        except TypeError as error:
            raise ValueError("detector_roles must contain one role per completed detector") from error
        if len(values) != count:
            raise ValueError("detector_roles must cover every completed detector ID exactly")
    try:
        return tuple(DetectorRole(role) for role in values)
    except (TypeError, ValueError) as error:
        raise ValueError("detector_roles entries must be 'past', 'online', or 'future'") from error


def completed_dem_to_temporal_model(
    dem: stim.DetectorErrorModel | str,
    *,
    detector_roles: Sequence[DetectorRole | str] | Mapping[int, DetectorRole | str] | None,
    num_observables: int | None = None,
    weight_scale: float = 1000,
    feature_observable_ids: Sequence[int] | None = None,
    feature_ids: Sequence[str] | None = None,
    model_provenance: Mapping | None = None,
) -> TemporalDemModel:
    """Parse a completed selected-CSS DEM without inferring missing boundaries.

    ``num_observables`` may exceed ``dem.num_observables`` to preserve declared
    evaluation dimensions when a p=0 circuit has no terms mentioning them.
    Detector metadata must cover precisely ``range(dem.num_detectors)``;
    builders should declare zero-response detector rows in the DEM explicitly.
    Row order within each returned block is ascending original detector ID.
    DEM L targets are the evaluation response map. Optional ordered unique
    ``feature_observable_ids`` selects/reorders its rows; ``feature_ids`` names
    them. All original observable signatures remain in ``terms``. Provenance
    is static finite JSON, never a sampled fault location or hidden outcomes.
    Standalone ordinary DEMs lack the required boundary information; passing
    invented roles does not establish a valid completion/equivalence proof.

    Every error term must have at most two *individual* completed detector
    endpoints before boundary contraction.  A single endpoint means a spatial
    open port and is frozen, even if that endpoint is itself on a temporal
    slice.  Two endpoints in the same temporal slice cancel after contraction,
    but the mechanism and all evaluation labels are preserved.
    """
    if isinstance(dem, str):
        dem = stim.DetectorErrorModel(dem)
    if not isinstance(dem, stim.DetectorErrorModel):
        raise TypeError("dem must be a Stim DetectorErrorModel or its text")
    if model_provenance is not None and not isinstance(model_provenance, Mapping):
        raise ValueError("model_provenance must be a finite JSON mapping")
    roles = _roles(detector_roles, dem.num_detectors)
    if num_observables is None:
        num_observables = dem.num_observables
    if (isinstance(num_observables, (bool, np.bool_))
            or not isinstance(num_observables, Integral)
            or num_observables < dem.num_observables):
        raise ValueError("num_observables must be an integer at least dem.num_observables")
    num_observables = int(num_observables)

    probabilities: list[float] = []
    terms: list[CompletedDemTerm] = []
    for instruction_index, instruction in enumerate(dem.flattened()):
        if instruction.type in {"detector", "logical_observable"}:
            continue
        if instruction.type != "error":
            raise ValueError(f"Unsupported flattened DEM instruction: {instruction.type}")
        detectors: set[int] = set()
        observables: set[int] = set()
        for target in instruction.targets_copy():
            if target.is_separator():
                raise ValueError("DEM separators are unsupported: correlated components cannot be independent edges")
            if target.is_relative_detector_id():
                if not 0 <= target.val < len(roles):
                    raise ValueError("DEM detector ID out of range")
                detectors.symmetric_difference_update((target.val,))
            elif target.is_logical_observable_id():
                if not 0 <= target.val < num_observables:
                    raise ValueError("DEM observable ID out of range")
                observables.symmetric_difference_update((target.val,))
            else:
                raise ValueError(f"Unsupported DEM error target: {target}")
        if len(detectors) > 2:
            raise ValueError(
                f"Completed DEM error term {len(terms)} is not graphlike: "
                f"{len(detectors)} individual endpoints before temporal contraction")
        column = len(terms)
        detector_ids = tuple(sorted(detectors))
        observable_ids = tuple(sorted(observables))
        probabilities.append(instruction.args_copy()[0])
        terms.append(CompletedDemTerm(column, instruction_index, detector_ids, observable_ids))

    return _assemble_model(
        roles, tuple(terms), probabilities, num_observables, weight_scale,
        feature_observable_ids, feature_ids,
        _canonical_json(dict(model_provenance) if model_provenance is not None
                        else {"source": "caller_supplied_completed_dem", "completion_certified": False}),
        hashlib.sha256(str(dem).encode("utf-8")).hexdigest(),
    )


def _ordered_ids(values, count, name):
    try:
        ids = tuple(values)
    except TypeError as error:
        raise ValueError(f"{name} must be unique integer IDs in range") from error
    if (any(isinstance(j, (bool, np.bool_)) or not isinstance(j, Integral) or not 0 <= j < count for j in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError(f"{name} must be unique integer IDs in range")
    return tuple(map(int, ids))


def _assemble_model(roles, terms, probabilities, num_observables, weight_scale,
                    feature_observable_ids, feature_ids, provenance_json, source_dem_sha256):
    """Single column/feature construction path for DEM parsing and artifacts."""
    count = len(terms)
    selected = _ordered_ids(range(num_observables) if feature_observable_ids is None else feature_observable_ids,
                            num_observables, "feature_observable_ids")
    if isinstance(feature_ids, (str, bytes)):
        raise ValueError("feature_ids must be unique nonempty strings, one per feature")
    try:
        names = tuple(f"L{j}" for j in selected) if feature_ids is None else tuple(feature_ids)
    except TypeError as error:
        raise ValueError("feature_ids must be unique nonempty strings, one per feature") from error
    if (len(names) != len(selected) or any(not isinstance(name, str) or not name for name in names)
            or len(set(names)) != len(names)):
        raise ValueError("feature_ids must be unique nonempty strings, one per feature")
    mapping = {label: row for row, label in enumerate(selected)}
    detector_rows, detector_columns, feature_rows, feature_columns = [], [], [], []
    for column, term in enumerate(terms):
        detector_rows.extend(term.detector_ids)
        detector_columns.extend([column] * len(term.detector_ids))
        rows = [mapping[j] for j in term.observable_ids if j in mapping]
        feature_rows.extend(rows)
        feature_columns.extend([column] * len(rows))
    h_completed = csc_matrix((np.ones(len(detector_rows), dtype=np.uint8),
                              (detector_rows, detector_columns)),
                             shape=(len(roles), count))
    features = csc_matrix((np.ones(len(feature_rows), dtype=np.uint8),
                           (feature_rows, feature_columns)),
                          shape=(len(selected), count))
    online_ids = np.asarray([i for i, role in enumerate(roles) if role == DetectorRole.ONLINE], dtype=np.int64)
    past_ids = np.asarray([i for i, role in enumerate(roles) if role == DetectorRole.PAST], dtype=np.int64)
    future_ids = np.asarray([i for i, role in enumerate(roles) if role == DetectorRole.FUTURE], dtype=np.int64)
    h_online = h_completed[online_ids, :].tocsc()
    past = np.asarray(h_completed[past_ids, :].sum(axis=0)).ravel().astype(np.uint8) % 2
    future = np.asarray(h_completed[future_ids, :].sum(axis=0)).ravel().astype(np.uint8) % 2
    full_degree = np.diff(h_completed.indptr)
    augmented_degree = np.diff(h_online.indptr) + past + future
    if (augmented_degree > 2).any():
        # Defensive invariant: endpoint contraction cannot create new incidence.
        raise ValueError("Temporally augmented mechanism columns are not graphlike")
    if ((full_degree != 1) & (augmented_degree == 1)).any():
        raise ValueError("Unfrozen degree-one augmented mechanism: completed boundary scope is insufficient")
    probs = np.asarray(probabilities, dtype=np.float64)
    weights = bernoulli_integer_weights(probs, weight_scale=weight_scale)
    float_weights = np.full(len(probs), np.inf)
    positive = probs > 0
    float_weights[positive] = np.log1p(-probs[positive]) - np.log(probs[positive])
    return TemporalDemModel(
        h_completed=h_completed,
        h_online=h_online,
        past=past,
        future=future,
        frozen_columns=np.flatnonzero(full_degree == 1),
        feature_map=features,
        probabilities=probs,
        weights=weights,
        mechanism_ids=tuple(f"completed_dem_error_{j}" for j in range(count)),
        detector_roles=roles,
        online_detector_ids=online_ids,
        past_detector_ids=past_ids,
        future_detector_ids=future_ids,
        active_columns=np.flatnonzero(probs > 0),
        inactive_columns=np.flatnonzero(probs == 0),
        terms=tuple(terms),
        float_weights=float_weights, num_observables=num_observables,
        feature_observable_ids=selected, feature_ids=names, provenance_json=provenance_json,
        weight_scale=float(weight_scale),
        source_dem_sha256=source_dem_sha256,
    )


def _model_from_artifact(artifact) -> TemporalDemModel:
    try:
        if not isinstance(artifact, Mapping) or set(artifact) != {"payload", "sha256"}:
            raise ValueError("invalid artifact envelope")
        payload = artifact["payload"]
        if artifact["sha256"] != _hash_payload(payload):
            raise ValueError("artifact SHA256 mismatch")
        if (set(payload) != {"artifact_version", "num_observables", "detector_roles", "terms",
                             "probabilities", "weights", "metadata"}
                or type(payload["artifact_version"]) is not int or payload["artifact_version"] != 1):
            raise ValueError("unsupported artifact schema/version")
        num_observables = payload["num_observables"]
        if type(num_observables) is not int or num_observables < 0:
            raise ValueError("invalid num_observables")
        roles = _roles(payload["detector_roles"], len(payload["detector_roles"]))
        terms = []
        last_instruction = -1
        for column, raw in enumerate(payload["terms"]):
            if set(raw) != {"term_index", "instruction_index", "detector_ids", "observable_ids"}:
                raise ValueError("invalid term schema")
            if (type(raw["term_index"]) is not int or raw["term_index"] != column
                    or type(raw["instruction_index"]) is not int or raw["instruction_index"] <= last_instruction):
                raise ValueError("invalid original term/instruction order")
            detectors = _ordered_ids(raw["detector_ids"], len(roles), "detector_ids")
            observables = _ordered_ids(raw["observable_ids"], num_observables, "observable_ids")
            if tuple(sorted(detectors)) != detectors or len(detectors) > 2 or tuple(sorted(observables)) != observables:
                raise ValueError("invalid individual completed support")
            terms.append(CompletedDemTerm(column, raw["instruction_index"], detectors, observables))
            last_instruction = raw["instruction_index"]
        if len(payload["probabilities"]) != len(terms):
            raise ValueError("probability/column count mismatch")
        meta = payload["metadata"]
        if not isinstance(meta["provenance"], Mapping):
            raise ValueError("model provenance must be a finite JSON mapping")
        source = meta["source_dem_sha256"]
        if not isinstance(source, str) or len(source) != 64 or any(c not in "0123456789abcdef" for c in source):
            raise ValueError("invalid source DEM hash")
        model = _assemble_model(roles, tuple(terms), payload["probabilities"], num_observables,
                                meta["weight_scale"], meta["feature_observable_ids"], meta["feature_ids"],
                                _canonical_json(meta["provenance"]), source)
        if _canonical_json(model.to_artifact()["payload"]) != _canonical_json(payload):
            raise ValueError("artifact derived metadata/weights disagree with original columns")
        return model
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"Invalid temporal model artifact: {error}") from error
