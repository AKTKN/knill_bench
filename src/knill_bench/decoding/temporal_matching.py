"""Static, batched temporal comparative MWPM on a labelled mechanism graph.

This module does not infer temporal ports from detector coordinates or parse a
Stim DEM.  Its caller must supply physically justified past/future port labels
and preserve mechanism columns before merging.  A graph proof is then available:
after the frozen columns cancel, the difference between the two corrections has
only the past and future vertices odd, and hence contains a past--future path.
The cost difference is a minimum-representative score, not a posterior or an LLR.

Two immutable matching topologies are compiled.  Frozen columns are removed from
the second topology once; their selected contribution is moved into each shot's
right-hand side and cost.  Parallel mechanisms are retained exactly by private
degree-two subdivision vertices with zero syndrome.  No shot changes graph
weights, builds a new matcher, or uses a large penalty to approximate a constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

import numpy as np
import pymatching
from scipy.sparse import csc_matrix, issparse, vstack


class TemporalStatus(str, Enum):
    OK = "ok"
    INVALID_SYNDROME = "invalid_syndrome"
    NO_COMPLEMENTARY_SOLUTION = "no_complementary_solution"


@dataclass(frozen=True)
class TemporalMatchingResult:
    """Shot-major results, in the common integer cost units of the input.

    Feature arrays are GF(2) parities of original mechanism columns.  Error
    arrays, when requested, also use the original column order.  Entries for an
    unavailable correction are zero placeholders and must be masked by status.
    An unavailable solution has infinite weight and a NaN gap.  The status is
    a structural obstruction, not evidence of high confidence.  In debug mode,
    debug_matches_compact says whether tracked baseline/alternative labels and
    costs agree with compact mode; a false entry identifies a separate tie
    resolution, never a witness attached to the compact correction.
    """

    baseline_features: np.ndarray
    complementary_features: np.ndarray
    baseline_weights: np.ndarray
    complementary_weights: np.ndarray
    gaps: np.ndarray
    status: np.ndarray
    baseline_errors: np.ndarray | None = None
    complementary_errors: np.ndarray | None = None
    debug_matches_compact: np.ndarray | None = None


def _binary_matrix(value, name: str) -> csc_matrix:
    if not issparse(value) and np.asarray(value).ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional binary matrix")
    matrix = csc_matrix(value, copy=True)
    matrix.sum_duplicates()
    matrix.eliminate_zeros()
    matrix.sort_indices()
    if not np.isin(matrix.data, [0, 1]).all():
        raise ValueError(f"{name} must be binary")
    return matrix.astype(np.uint8)


def _binary_vector(value, length: int, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (length,) or not np.isin(array, [0, 1]).all():
        raise ValueError(f"{name} must be a binary vector with {length} entries")
    return array.astype(np.uint8, copy=True)


def _parities(shots: np.ndarray, matrix: csc_matrix) -> np.ndarray:
    # uint8 overflow is harmless for reduction modulo two.
    return np.asarray(shots @ matrix.T, dtype=np.uint8) % 2


class _StaticMatcher:
    """A simple graph implementation of an unmerged labelled multigraph."""

    def __init__(self, incidence: csc_matrix, weights: np.ndarray,
                 features: csc_matrix) -> None:
        self.incidence = incidence
        self.weights = weights
        self.features = features
        self.num_rows, self.num_columns = incidence.shape
        self.num_features = features.shape[0]
        self._closed_components, self.components = self._components(incidence)

        supports = [tuple(map(int, incidence.indices[incidence.indptr[j]:incidence.indptr[j + 1]]))
                    for j in range(self.num_columns)]
        counts: dict[tuple[int, ...], int] = {}
        for support in supports:
            if support:
                counts[support] = counts.get(support, 0) + 1

        rows: list[int] = []
        columns: list[int] = []
        costs: list[int] = []
        feature_rows: list[int] = []
        feature_columns: list[int] = []
        source_rows: list[int] = []
        source_columns: list[int] = []
        next_node = self.num_rows

        def add_edge(u: int, v: int | None, cost: int,
                     source: int | None) -> None:
            edge_id = len(costs)
            rows.append(u)
            columns.append(edge_id)
            if v is not None:
                rows.append(v)
                columns.append(edge_id)
            costs.append(cost)
            if source is not None:
                start, end = features.indptr[source:source + 2]
                feature_rows.extend(map(int, features.indices[start:end]))
                feature_columns.extend([edge_id] * (end - start))
                source_rows.append(source)
                source_columns.append(edge_id)

        for j, support in enumerate(supports):
            if not support:
                # Positive-cost unobserved events are zero in a minimum solution;
                # at weight zero, choosing zero fixes the otherwise arbitrary tie.
                continue
            u = support[0]
            v = support[1] if len(support) == 2 else None
            if counts[support] > 1:
                middle = next_node
                next_node += 1
                add_edge(u, middle, int(weights[j]), j)
                add_edge(middle, v, 0, None)
            else:
                add_edge(u, v, int(weights[j]), j)

        self.num_matching_rows = next_node
        self._debug_matcher = None
        if costs:
            self._graph = csc_matrix((np.ones(len(rows), dtype=np.uint8), (rows, columns)),
                                     shape=(next_node, len(costs)))
            self._graph_weights = np.asarray(costs, dtype=np.int64)
            self._source_labels = csc_matrix((np.ones(len(source_rows), dtype=np.uint8),
                                              (source_rows, source_columns)),
                                             shape=(self.num_columns, len(costs)))
            labels = csc_matrix((np.ones(len(feature_rows), dtype=np.uint8),
                                 (feature_rows, feature_columns)),
                                shape=(self.num_features, len(costs)))
            self.matcher = pymatching.Matching.from_check_matrix(
                self._graph, weights=self._graph_weights,
                faults_matrix=labels, merge_strategy="disallow",
                use_virtual_boundary_node=True)
        else:
            self.matcher = None

    @staticmethod
    def _components(incidence: csc_matrix) -> tuple[tuple[np.ndarray, ...], np.ndarray]:
        """Closed graph components are precisely the syndrome-parity constraints."""
        size = incidence.shape[0]
        parent = np.arange(size)

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = int(parent[node])
            return node

        boundary_nodes = []
        for j in range(incidence.shape[1]):
            support = incidence.indices[incidence.indptr[j]:incidence.indptr[j + 1]]
            if len(support) == 2:
                a, b = map(find, map(int, support))
                parent[a] = b
            elif len(support) == 1:
                boundary_nodes.append(int(support[0]))
        roots = np.asarray([find(i) for i in range(size)], dtype=np.int64)
        open_roots = {find(i) for i in boundary_nodes}
        closed = tuple(np.flatnonzero(roots == root)
                       for root in np.unique(roots) if root not in open_roots)
        return closed, roots

    def feasible(self, syndromes: np.ndarray) -> np.ndarray:
        valid = np.ones(len(syndromes), dtype=bool)
        for nodes in self._closed_components:
            valid &= np.bitwise_xor.reduce(syndromes[:, nodes], axis=1) == 0
        return valid

    def _pad(self, syndromes: np.ndarray) -> np.ndarray:
        if self.num_matching_rows == self.num_rows:
            return np.ascontiguousarray(syndromes, dtype=np.uint8)
        padded = np.zeros((len(syndromes), self.num_matching_rows), dtype=np.uint8)
        padded[:, :self.num_rows] = syndromes
        return padded

    def decode_batch(self, syndromes: np.ndarray, *, return_errors: bool = False
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
        if self.matcher is None or not len(syndromes):
            return (np.zeros((len(syndromes), self.num_features), dtype=np.uint8),
                    np.zeros(len(syndromes), dtype=np.float64),
                    np.zeros((len(syndromes), self.num_columns), dtype=np.uint8) if return_errors else None,
                    np.ones(len(syndromes), dtype=bool) if return_errors else None)
        if not return_errors:
            predictions, weights = self.matcher.decode_batch(self._pad(syndromes), return_weights=True)
            return predictions, weights, None, None
        # Obtain every label from ONE solve.  A separate decode_to_edges_array
        # call need not choose the same shortest path on zero-weight/tied cycles.
        if self._debug_matcher is None:
            self._debug_matcher = pymatching.Matching.from_check_matrix(
                self._graph, weights=self._graph_weights, faults_matrix=self._source_labels,
                merge_strategy="disallow", use_virtual_boundary_node=True)
        errors, weights = self._debug_matcher.decode_batch(self._pad(syndromes), return_weights=True)
        if (not np.array_equal(_parities(errors, self.incidence), syndromes)
                or not np.array_equal(errors @ self.weights, weights)):
            raise RuntimeError("MWPM mechanism witnesses violate their syndrome or cost")
        predictions = _parities(errors, self.features)
        compact_predictions, compact_weights = self.matcher.decode_batch(self._pad(syndromes), return_weights=True)
        agrees = np.all(predictions == compact_predictions, axis=1) & (weights == compact_weights)
        return predictions, weights, errors, agrees


class TemporalMatching:
    """Compile two static MWPM problems for temporal comparative decoding.

    Parameters
    ----------
    h_online:
        Binary online detector-by-mechanism matrix; every column has degree <=2.
    past, future:
        Binary vectors marking each mechanism's missing temporal endpoints.
        The completed column [H; past; future] must have degree <=2.  These are
        endpoint labels supplied by the circuit/model adapter, not inferred here.
    frozen_columns:
        Original mechanism indices (or a length-E Boolean mask) fixed to their
        baseline values, including both zero and one.  This must contain every
        remaining non-temporal open port.  Temporal columns may also be frozen.
    weights:
        Common finite, nonnegative INTEGER edge costs.  Quantize physical log
        odds once before constructing this object, using the same scale for all
        mechanisms.  Different graph-dependent floating scales are not accepted.
    feature_map:
        Optional binary feature-by-mechanism matrix, e.g. final sign residuals
        and logical response labels.  Sampled truth values never enter this API.
    mechanism_ids:
        Optional unique stable IDs in original column order; defaults to indices.

    All unfrozen nonzero completed columns must have degree two.  Zero-online
    columns have baseline value zero (also the tie convention for zero costs).
    A zero-online mechanism joining past to future remains in the second graph.
    The topology theorem is for these supplied mechanism columns; it is not a
    certificate that a decomposed DEM has a consistent physical-fault lift.
    """

    def __init__(self, h_online, past, future, frozen_columns: Iterable[int],
                 weights, *, feature_map=None,
                 mechanism_ids: Sequence[object] | None = None) -> None:
        self.h_online = _binary_matrix(h_online, "h_online")
        self.num_detectors, self.num_mechanisms = self.h_online.shape
        n = self.num_mechanisms
        self.past = _binary_vector(past, n, "past")
        self.future = _binary_vector(future, n, "future")
        costs = np.asarray(weights)
        if (costs.shape != (n,) or not np.issubdtype(costs.dtype, np.number)
                or not np.isrealobj(costs) or not np.isfinite(costs).all()
                or (costs < 0).any() or (costs > 2**24 - 1).any()
                or not np.equal(costs, np.round(costs)).all()):
            raise ValueError("weights must be nonnegative integers no larger than 2**24-1")
        self.weights = costs.astype(np.int64, copy=True)
        if sum(map(int, self.weights)) > 2**53 - 1:
            raise ValueError("Total integer cost exceeds exact float64 return precision")

        frozen = np.asarray(list(frozen_columns))
        if frozen.dtype == bool:
            if frozen.shape != (n,):
                raise ValueError("Boolean frozen_columns mask must have one entry per mechanism")
            frozen = np.flatnonzero(frozen)
        elif frozen.ndim != 1 or (frozen.size and not np.issubdtype(frozen.dtype, np.integer)):
            raise ValueError("frozen_columns must contain integer column indices")
        frozen = frozen.astype(np.int64)
        if (frozen < 0).any() or (frozen >= n).any() or len(np.unique(frozen)) != len(frozen):
            raise ValueError("frozen_columns must contain distinct valid column indices")
        self.frozen_columns = np.sort(frozen)
        self.active_columns = np.setdiff1d(np.arange(n), self.frozen_columns)

        self.feature_map = (csc_matrix((0, n), dtype=np.uint8) if feature_map is None
                            else _binary_matrix(feature_map, "feature_map"))
        if self.feature_map.shape[1] != n:
            raise ValueError("feature_map must have one column per mechanism")
        self.num_features = self.feature_map.shape[0]
        self.mechanism_ids = tuple(range(n)) if mechanism_ids is None else tuple(mechanism_ids)
        try:
            unique_ids = len(set(self.mechanism_ids))
        except TypeError as error:
            raise ValueError("mechanism_ids must contain unique hashable IDs") from error
        if len(self.mechanism_ids) != n or unique_ids != n:
            raise ValueError("mechanism_ids must contain one unique hashable ID per column")

        online_degree = np.diff(self.h_online.indptr)
        completed_degree = online_degree + self.past + self.future
        if (online_degree > 2).any() or (completed_degree > 2).any():
            raise ValueError("Online or augmented mechanism column is not graphlike")
        if (completed_degree[self.active_columns] == 1).any():
            raise ValueError("Every non-temporal open column must be frozen")

        size = len(self.frozen_columns)
        fixed_ids = csc_matrix((np.ones(size, dtype=np.uint8),
                               (np.arange(size), self.frozen_columns)), shape=(size, n))
        base_features = vstack((fixed_ids, csc_matrix(self.past[None, :]),
                                csc_matrix(self.future[None, :]), self.feature_map), format="csc")
        self._baseline = _StaticMatcher(self.h_online, self.weights, base_features)

        self._h_fixed = self.h_online[:, self.frozen_columns]
        self._p_fixed = self.past[self.frozen_columns]
        self._f_fixed = self.future[self.frozen_columns]
        self._feature_fixed = self.feature_map[:, self.frozen_columns]
        active = self.active_columns
        completed = vstack((self.h_online[:, active], csc_matrix(self.past[None, active]),
                            csc_matrix(self.future[None, active])), format="csc")
        comparison_features = vstack((csc_matrix(self.past[None, active]),
                                       csc_matrix(self.future[None, active]),
                                       self.feature_map[:, active]), format="csc")
        self._comparison = _StaticMatcher(completed, self.weights[active], comparison_features)
        self.has_temporal_path = bool(
            self._comparison.components[self.num_detectors]
            == self._comparison.components[self.num_detectors + 1])

    def decode_batch(self, syndromes, *, return_errors: bool = False) -> TemporalMatchingResult:
        """Decode an unpacked binary batch without observing any evaluation truth.

        Ordinary runs execute two native batch calls and vectorized right-hand-
        side/feature/cost calculations.  The debug option uses lazily cached
        full-mechanism output matchers, so each witness and its feature parities
        come from the same solve.  A degenerate optimum may be resolved
        differently from compact-output mode; the frozen fiber and gap then
        refer to the returned debug baseline.  debug_matches_compact explicitly
        marks those differences by checking both modes.  Use a fixed mode
        within a run; a false flag must not be treated as a compact-shot witness.
        """
        shots = np.asarray(syndromes)
        if (shots.ndim != 2 or shots.shape[1] != self.num_detectors
                or not np.isin(shots, [0, 1]).all()):
            raise ValueError("syndromes must be binary (shots, num_detectors)")
        shots = shots.astype(np.uint8, copy=False)
        count = len(shots)
        base_features = np.zeros((count, self.num_features), dtype=np.uint8)
        comp_features = np.zeros_like(base_features)
        w0 = np.full(count, np.inf)
        w1 = np.full(count, np.inf)
        gaps = np.full(count, np.nan)
        status = np.full(count, TemporalStatus.INVALID_SYNDROME.value, dtype="<U26")
        errors0 = np.zeros((count, self.num_mechanisms), dtype=np.uint8) if return_errors else None
        errors1 = np.zeros_like(errors0) if return_errors else None
        debug_matches = np.zeros(count, dtype=bool) if return_errors else None

        valid_ids = np.flatnonzero(self._baseline.feasible(shots))
        valid_shots = shots[valid_ids]
        predictions0, weights0, witnesses0, matches0 = self._baseline.decode_batch(
            valid_shots, return_errors=return_errors)
        fixed_count = len(self.frozen_columns)
        fixed = predictions0[:, :fixed_count]
        base_features[valid_ids] = predictions0[:, fixed_count + 2:]
        w0[valid_ids] = weights0
        status[valid_ids] = TemporalStatus.NO_COMPLEMENTARY_SOLUTION.value

        rhs = np.empty((len(valid_ids), self.num_detectors + 2), dtype=np.uint8)
        rhs[:, :self.num_detectors] = valid_shots ^ _parities(fixed, self._h_fixed)
        rhs[:, self.num_detectors] = (predictions0[:, fixed_count] ^ 1
                                       ^ (fixed @ self._p_fixed % 2))
        rhs[:, self.num_detectors + 1] = (predictions0[:, fixed_count + 1] ^ 1
                                           ^ (fixed @ self._f_fixed % 2))
        comp_local_ids = np.flatnonzero(self._comparison.feasible(rhs))
        comp_ids = valid_ids[comp_local_ids]
        predictions1, active_weights, active_errors, matches1 = self._comparison.decode_batch(
            rhs[comp_local_ids], return_errors=return_errors)
        selected_fixed = fixed[comp_local_ids]
        w1[comp_ids] = active_weights + selected_fixed @ self.weights[self.frozen_columns]
        gaps[comp_ids] = w1[comp_ids] - w0[comp_ids]
        if (gaps[comp_ids] < 0).any():
            raise RuntimeError("A constrained correction is cheaper than the baseline")
        comp_features[comp_ids] = predictions1[:, 2:] ^ _parities(selected_fixed, self._feature_fixed)
        status[comp_ids] = TemporalStatus.OK.value

        if return_errors:
            errors0[valid_ids] = witnesses0
            errors1[np.ix_(comp_ids, self.active_columns)] = active_errors
            errors1[np.ix_(comp_ids, self.frozen_columns)] = selected_fixed
            debug_matches[valid_ids] = matches0
            debug_matches[comp_ids] &= matches1

        return TemporalMatchingResult(base_features, comp_features, w0, w1, gaps,
                                      status, errors0, errors1, debug_matches)
