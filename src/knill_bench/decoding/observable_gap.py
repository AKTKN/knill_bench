"""MWPM with an optional opposite-observable constraint on a graphlike DEM.

The observable is an edge cochain. Its internal XOR potential moves that
constraint onto two constrained boundary vertices, preserving degree two.
This works on spacetime graphs; no spatial planarity assumption is made.
"""

from dataclasses import dataclass
import hashlib

import numpy as np
import pymatching
from scipy import sparse


@dataclass(frozen=True)
class ObservableBatch:
    prediction: np.ndarray
    correction: np.ndarray
    weight: np.ndarray
    gap: np.ndarray | None = None
    opposite_correction: np.ndarray | None = None
    opposite_weight: np.ndarray | None = None


def _binary(value, name):
    result = sparse.csc_matrix(value, copy=True)
    result.sum_duplicates()
    result.eliminate_zeros()
    if not np.all(result.data == 1):
        raise ValueError(f"{name} must be binary")
    result = result.astype(np.uint8)
    result.sort_indices()
    return result


class ObservableMWPM:
    """Cache one unconstrained graph and, optionally, one constrained graph.

    Complete independent DEM events must have one/two detector endpoints.
    Opposite-class scoring additionally requires positive weights, a consistent
    internal observable potential, and a connected two-boundary lift. No
    degree-three observable-row append, per-shot graph build or oracle input.
    """

    def __init__(self, check_matrix, observable_matrix, weights, *, get_logicalgap=False):
        if type(get_logicalgap) is not bool:
            raise ValueError("get_logicalgap must be bool")
        self.h = _binary(check_matrix, "check matrix")
        self.l = _binary(observable_matrix, "observable matrix")
        m, n = self.h.shape
        if self.l.shape != (1, n) or m < 1:
            raise ValueError("require one observable row aligned to a nonempty detector axis")
        self.weights = np.asarray(weights, dtype=np.float64).copy()
        if (self.weights.shape != (n,) or not np.isfinite(self.weights).all()
                or np.any(np.abs(self.weights) > 2**24 - 1)):
            raise ValueError("require finite aligned weights within PyMatching's native range")
        degree = np.diff(self.h.indptr)
        if np.any((degree < 1) | (degree > 2)):
            raise ValueError("require complete graphlike DEM events with one/two detector endpoints")
        self.get_logicalgap = get_logicalgap
        self.matching = self.opposite_matching = None
        self.extended = self.potential = None
        self.cost_atol = max(1e-10, n * np.max(np.abs(self.weights), initial=0.) / (2**24 - 1))
        if n:
            self.matching = pymatching.Matching.from_check_matrix(
                self.h, weights=self.weights, merge_strategy="smallest-weight")
            self.matching.ensure_num_fault_ids(n)
        if get_logicalgap:
            if not n or np.any(self.weights <= 0):
                raise ValueError("complementary gap requires positive finite event weights")
            if np.min(self.weights) / np.max(self.weights) < 1 / (2**24 - 1):
                raise ValueError("weight dynamic range exceeds native matching precision")
            self._build_lift()
        sha = hashlib.sha256()
        for matrix in (self.h, self.l):
            for value in (np.asarray(matrix.shape, dtype=np.int64), matrix.indptr, matrix.indices):
                sha.update(value.tobytes())
        sha.update(self.weights.tobytes())
        sha.update(b"observable_mwpm_two_boundary_spacetime_v1")
        sha.update(pymatching.__version__.encode())
        self.model_sha256 = sha.hexdigest()

    def _build_lift(self):
        h = self.h
        m, n = h.shape
        logical = self.l.toarray()[0]
        degree = np.diff(h.indptr)
        neighbours = [[] for _ in range(m)]
        for edge in np.flatnonzero(degree == 2):
            a, b = h.indices[h.indptr[edge]:h.indptr[edge + 1]]
            neighbours[a].append((int(b), int(logical[edge])))
            neighbours[b].append((int(a), int(logical[edge])))
        potential = np.full(m, -1, dtype=np.int8)
        for root in range(m):
            if potential[root] >= 0:
                continue
            potential[root] = 0
            todo = [root]
            while todo:
                a = todo.pop()
                for b, bit in neighbours[a]:
                    expected = int(potential[a]) ^ bit
                    if potential[b] < 0:
                        potential[b] = expected
                        todo.append(b)
                    elif potential[b] != expected:
                        raise ValueError("observable has inconsistent internal-cycle potential")
        boundary_edges = np.flatnonzero(degree == 1)
        boundary_ids = [int(logical[e] ^ potential[h.indices[h.indptr[e]]]) for e in boundary_edges]
        boundaries = sparse.csc_matrix((np.ones(len(boundary_edges), dtype=np.uint8),
                                         (boundary_ids, boundary_edges)), shape=(2, n))
        extended = sparse.vstack((h, boundaries), format="csc")
        if (not np.all(np.diff(extended.indptr) == 2)
                or np.any(((potential @ h % 2) ^ boundaries.getrow(1).toarray()[0]) != logical)):
            raise ValueError("two-boundary lift does not preserve H and the observable matrix")
        # All vertices, including both logical boundaries, must be connected.
        graph = [[] for _ in range(m + 2)]
        for edge in range(n):
            a, b = extended.indices[extended.indptr[edge]:extended.indptr[edge + 1]]
            graph[a].append(int(b))
            graph[b].append(int(a))
        seen, todo = {0}, [0]
        while todo:
            for b in graph[todo.pop()]:
                if b not in seen:
                    seen.add(b)
                    todo.append(b)
        if len(seen) != m + 2:
            raise ValueError("require a connected lift reaching both observable boundaries")
        matching = pymatching.Matching.from_check_matrix(
            extended, weights=self.weights, merge_strategy="smallest-weight")
        matching.ensure_num_fault_ids(n)
        if matching.boundary or matching.num_detectors != m + 2:
            raise ValueError("logical boundary vertices must remain constrained detectors")
        self.extended, self.potential, self.opposite_matching = extended, potential.astype(np.uint8), matching

    def _decode(self, matching, syndrome, h):
        correction, native_weight = matching.decode_batch(syndrome, return_weights=True)
        if (correction.shape != (len(syndrome), self.h.shape[1])
                or np.any((correction @ h.T % 2) != syndrome)):
            raise ValueError("matching correction violates the supplied syndrome constraints")
        weight = correction @ self.weights
        if (not np.isfinite(weight).all() or not np.isfinite(native_weight).all()
                or not np.allclose(weight, native_weight, rtol=1e-12, atol=self.cost_atol)):
            raise ValueError("native weight disagrees with returned event correction")
        return correction.astype(bool), weight

    def decode_batch(self, syndromes):
        s = np.asarray(syndromes)
        if (s.ndim != 2 or s.shape[1] != self.h.shape[0] or not len(s)
                or not np.all((s == 0) | (s == 1))):
            raise ValueError("require a nonempty binary detector batch")
        s = s.astype(np.uint8, copy=False)
        if self.matching is None:
            if s.any():
                raise ValueError("nonzero syndrome in an empty zero-noise DEM")
            return ObservableBatch(np.zeros(len(s), dtype=bool), np.empty((len(s), 0), dtype=bool),
                                   np.zeros(len(s), dtype=np.float64))
        correction, weight = self._decode(self.matching, s, self.h)
        predicted = (correction @ self.l.T % 2).ravel().astype(bool)
        if not self.get_logicalgap:
            return ObservableBatch(predicted, correction, weight)
        lifted = np.empty((len(s), len(self.potential) + 2), dtype=np.uint8)
        lifted[:, :-2] = s
        lifted[:, -1] = (1 ^ predicted.astype(np.uint8)) ^ (s @ self.potential % 2)
        lifted[:, -2] = np.bitwise_xor.reduce(s, axis=1) ^ lifted[:, -1]
        opposite, opposite_weight = self._decode(self.opposite_matching, lifted, self.extended)
        if np.any((opposite @ self.l.T % 2).ravel() == predicted):
            raise ValueError("constrained correction did not change logical class")
        gap = opposite_weight - weight
        # A negative difference beyond floating summation error signals an
        # unresolved native weight discretization/order issue; never take abs.
        if np.any(gap < -1e-10):
            raise ValueError("opposite solution is lighter than first decode at native precision")
        return ObservableBatch(predicted, correction, weight, np.maximum(gap, 0.), opposite, opposite_weight)
