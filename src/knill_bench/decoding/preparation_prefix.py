"""Unmerged single-sector prefix MWPM model, with no temporal completion.

Z has a known initial zero anchor. Its prefix detector rows are explicit
builder inputs; no ideal final detector or guessed temporal port is added.
This model shares the supplied static multigraph kernel, not its comparative
P/F classification. Evaluation L responses are static maps, never outcomes.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

import numpy as np
from scipy.sparse import csc_matrix
import stim

from .temporal_dem import _canonical_json, _ordered_ids, bernoulli_integer_weights


@dataclass(frozen=True)
class PrefixDemModel:
    """Original DEM columns for a single ordinary prefix solve.

    Zero-detector columns remain in provenance/features; the minimum-cost
    representative chooses them zero, also at quantized-zero cost. p0 terms
    are inactive. No P/F/S constraint container is introduced for this model.
    """

    h: csc_matrix
    feature_map: csc_matrix
    probabilities: np.ndarray
    weights: np.ndarray
    active_columns: np.ndarray
    detector_ids: tuple[int, ...]
    feature_observable_ids: tuple[int, ...]
    feature_ids: tuple[str, ...]
    full_detector_support: tuple[tuple[int, ...], ...]
    full_observable_support: tuple[tuple[int, ...], ...]
    instruction_indices: tuple[int, ...]
    weight_scale: float
    source_dem_sha256: str
    provenance_json: str
    scope: str = "known_zero_Z_prefix_v1"
    logical_evaluation: str = "prefix_frame_only"

    def __post_init__(self):
        n = len(self.probabilities)
        if (self.h.shape != (len(self.detector_ids), n) or self.feature_map.shape != (len(self.feature_ids), n)
                or not np.isin(self.h.data, [0, 1]).all() or not np.isin(self.feature_map.data, [0, 1]).all()
                or (np.diff(self.h.indptr) > 2).any()):
            raise ValueError("prefix incidence/features must be binary graphlike with original columns")
        if (self.weights.shape != (n,) or not np.issubdtype(self.weights.dtype, np.integer)
                or (self.weights < 0).any() or (self.weights > 2**24 - 1).any()
                or sum(map(int, self.weights)) > 2**53 - 1):
            raise ValueError("prefix common integer cost bounds exceeded")
        if (self.probabilities.shape != (n,) or not np.isfinite(self.probabilities).all()
                or (self.probabilities < 0).any() or (self.probabilities >= .5).any()
                or not np.array_equal(self.active_columns, np.flatnonzero(self.probabilities > 0))):
            raise ValueError("prefix probabilities/active columns disagree")

    @property
    def mechanism_ids(self):
        return tuple(f"production_dem_error_{j}" for j in range(len(self.probabilities)))

    @property
    def metadata(self):
        floats = np.full(len(self.probabilities), np.inf)
        active = self.probabilities > 0
        floats[active] = np.log1p(-self.probabilities[active]) - np.log(self.probabilities[active])
        return dict(scope=self.scope, logical_evaluation=self.logical_evaluation,
                    provenance_kind="production_dem_term",
                    source_dem_sha256=self.source_dem_sha256, weight_scale=self.weight_scale,
                    weight_rounding="numpy_rint_ties_to_even", provenance=json.loads(self.provenance_json),
                    float_weight_formula="log1p(-p)-log(p)",
                    float_weights=[float(w) if np.isfinite(w) else None for w in floats],
                    inactive_policy="p0_excluded_from_solver", active_zero_policy="retain_quantized_zero_no_clipping",
                    max_edge_weight=2**24 - 1, max_exact_total_weight=2**53 - 1,
                    detector_ids=list(self.detector_ids), feature_ids=list(self.feature_ids),
                    feature_observable_ids=list(self.feature_observable_ids),
                    active_columns=self.active_columns.tolist(),
                    inactive_columns=np.flatnonzero(self.probabilities == 0).tolist(),
                    zero_detector_policy="minimum_representative_zero_including_zero_cost_ties")

    @property
    def model_sha256(self):
        payload = dict(metadata=self.metadata, probabilities=self.probabilities.tolist(),
                       weights=self.weights.tolist(), full_detector_support=self.full_detector_support,
                       full_observable_support=self.full_observable_support,
                       instruction_indices=self.instruction_indices)
        return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()

    def expand_errors(self, errors):
        value = np.asarray(errors)
        if (value.ndim != 2 or value.shape[1] != len(self.active_columns)
                or not np.isin(value, [0, 1]).all()):
            raise ValueError("prefix errors must be binary (shots, active_columns)")
        result = np.zeros((len(value), len(self.probabilities)), dtype=np.uint8)
        result[:, self.active_columns] = value
        return result


def prefix_dem_to_model(dem: stim.DetectorErrorModel, *, detector_ids, observable_ids,
                        feature_ids, weight_scale=1000, model_provenance=None) -> PrefixDemModel:
    """Project explicit rows, retaining every independent error term separately.

    This ordinary DEM is sufficient for one Z-prefix MWPM solve, not for
    inferring missing P/F boundaries or the X comparative problem. Separators,
    selected-sector hyperedges and unsupported probabilities fail strictly.
    """
    selected = _ordered_ids(detector_ids, dem.num_detectors, "detector_ids")
    labels = _ordered_ids(observable_ids, dem.num_observables, "observable_ids")
    if isinstance(feature_ids, (str, bytes)):
        raise ValueError("feature_ids must be unique nonempty names")
    names = tuple(feature_ids)
    if model_provenance is not None and not isinstance(model_provenance, Mapping):
        raise ValueError("prefix model_provenance must be a finite JSON mapping")
    if (len(names) != len(labels) or any(not isinstance(s, str) or not s for s in names)
            or len(set(names)) != len(names)):
        raise ValueError("feature_ids must be unique nonempty names")
    dmap, fmap = ({j: i for i, j in enumerate(ids)} for ids in (selected, labels))
    dr, dc, fr, fc, probs, supports, observables, instructions = [], [], [], [], [], [], [], []
    for index, op in enumerate(dem.flattened()):
        if op.type in {"detector", "logical_observable"}:
            continue
        if op.type != "error":
            raise ValueError(f"Unsupported prefix DEM instruction: {op.type}")
        ds, ls = set(), set()
        for target in op.targets_copy():
            if target.is_separator():
                raise ValueError("prefix DEM separators cannot be independent mechanisms")
            if target.is_relative_detector_id() and 0 <= target.val < dem.num_detectors:
                ds.symmetric_difference_update([target.val])
            elif target.is_logical_observable_id() and 0 <= target.val < dem.num_observables:
                ls.symmetric_difference_update([target.val])
            else:
                raise ValueError("prefix DEM detector/observable target out of range")
        rows = sorted(dmap[j] for j in ds if j in dmap)
        if len(rows) > 2:
            raise ValueError("selected Z-prefix DEM mechanism is not graphlike")
        features = sorted(fmap[j] for j in ls if j in fmap)
        column = len(probs)
        dr.extend(rows); dc.extend([column] * len(rows))
        fr.extend(features); fc.extend([column] * len(features))
        probs.append(op.args_copy()[0])
        supports.append(tuple(sorted(ds))); observables.append(tuple(sorted(ls))); instructions.append(index)
    probabilities = np.asarray(probs, dtype=np.float64)
    weights = bernoulli_integer_weights(probabilities, weight_scale=weight_scale)
    return PrefixDemModel(
        csc_matrix((np.ones(len(dr), dtype=np.uint8), (dr, dc)), shape=(len(selected), len(probs))),
        csc_matrix((np.ones(len(fr), dtype=np.uint8), (fr, fc)), shape=(len(labels), len(probs))),
        probabilities, weights, np.flatnonzero(probabilities > 0), selected, labels, names,
        tuple(supports), tuple(observables), tuple(instructions), float(weight_scale),
        hashlib.sha256(str(dem).encode()).hexdigest(), _canonical_json(model_provenance or {}),
    )
