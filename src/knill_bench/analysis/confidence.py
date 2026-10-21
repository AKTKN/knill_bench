"""Pointwise Wilson score intervals and transforms for saved-data figures.

References/derivations: docs/notebook_plotting.md. No simulation or resampling.
The reduction envelope uses paired acceptance/error counts, with Bonferroni
adjustment of two Wilson intervals; it is not a binomial interval on a ratio.
"""

from dataclasses import dataclass
import math
from statistics import NormalDist

import numpy as np


def _counts(successes, trials):
    k, n = np.asarray(successes), np.asarray(trials)
    if not all(np.issubdtype(a.dtype, np.integer) for a in (k, n)):
        raise ValueError("successes/trials must be integer counts, not bool or floats")
    try:
        k, n = np.broadcast_arrays(k, n)
    except ValueError as error:
        raise ValueError("successes/trials must have broadcast-compatible shapes") from error
    if np.any(n < 0) or np.any(k < 0) or np.any(k > n):
        raise ValueError("require 0 <= successes <= trials")
    return k, n


def _result(lower, upper):
    return (float(lower), float(upper)) if lower.ndim == 0 else (lower, upper)


@dataclass(frozen=True)
class WilsonInterval:
    """Two-sided score interval, default confidence=0.95, no continuity correction.

    Scalar or broadcast integer arrays are accepted. Zero trials yields NaN
    endpoints, preserving undefined selected LERs instead of inventing a rate.
    Wilson coverage is approximate and pointwise, not simultaneous across cuts.
    """

    confidence: float = .95

    def __post_init__(self):
        if (type(self.confidence) not in (int, float) or not math.isfinite(self.confidence)
                or not 0 < self.confidence < 1):
            raise ValueError("confidence must be a finite number strictly between 0 and 1")

    def _bounds(self, successes, trials, comparisons=1):
        k, n = _counts(successes, trials)
        # Compute from the lower tail, avoiding rounding a near-one quantile
        # to exactly 1, including the Bonferroni calculation below.
        z = -NormalDist().inv_cdf((1 - self.confidence) / (2 * comparisons))
        z2 = z * z
        p = np.divide(k, n, out=np.zeros(k.shape, float), where=n > 0)
        denominator = n.astype(float) + z2
        with np.errstate(divide="ignore", invalid="ignore"):
            center = (k.astype(float) + z2 / 2) / denominator
            radius = z * np.sqrt(p * (n - k) + z2 / 4) / denominator
        lower = np.maximum(0., center - radius)
        upper = np.minimum(1., center + radius)
        lower = np.where(k == 0, 0., lower)
        upper = np.where(k == n, 1., upper)
        return np.where(n > 0, lower, np.nan), np.where(n > 0, upper, np.nan)

    def bounds(self, successes, trials):
        """Wilson probability bounds; k=0/n remains well-defined for n>0."""
        return _result(*self._bounds(successes, trials))

    def frequency(self, counts, shots, *, normalize=False):
        """Marginal category interval, in count units or relative-frequency units."""
        if type(normalize) is not bool:
            raise ValueError("normalize must be bool")
        lower, upper = self._bounds(counts, shots)
        if not normalize:
            lower, upper = lower * np.asarray(shots), upper * np.asarray(shots)
        return _result(lower, upper)

    def per_round(self, successes, trials, rounds):
        """Apply the monotone 1-(1-p)**(1/r) normalization to both endpoints."""
        r = np.asarray(rounds)
        if not np.issubdtype(r.dtype, np.integer) or np.any(r < 1):
            raise ValueError("rounds must be positive integers")
        lower, upper = self._bounds(successes, trials)
        with np.errstate(divide="ignore", invalid="ignore"):
            return _result(-np.expm1(np.log1p(-lower) / r),
                           -np.expm1(np.log1p(-upper) / r))

    def reduction(self, accepted_errors, accepted, errors, shots, *, no_cut=False):
        """Nominal confidence Wilson/Bonferroni envelope for 1-selected_LER/raw_LER.

        Write a=P(accept), b=P(accept|error). Then selected_LER/raw_LER=b/a.
        Build two Bonferroni-adjusted score intervals for these paired rates
        (97.5% each at the default), without assuming their independence.
        The rectangular envelope is [1-b_upper/a_lower, 1-b_lower/a_upper].
        Wilson remains approximate; the envelope is conservative relative to
        those two component score intervals. This is a fixed-cut calculation.
        no_cut is only for structurally absent selection, not observed all-pass.
        """
        # Validate all four cells of the implicit accept/error 2x2 table.
        ae, a = _counts(accepted_errors, accepted)
        e, n = _counts(errors, shots)
        ae, a, e, n = np.broadcast_arrays(ae, a, e, n)
        if np.any(a > n) or np.any(ae > e) or np.any(e - ae > n - a):
            raise ValueError("inconsistent paired acceptance/error counts")
        identity = np.asarray(no_cut)
        if identity.dtype != np.dtype(bool):
            raise ValueError("no_cut must be boolean")
        ae, a, e, n, identity = np.broadcast_arrays(ae, a, e, n, identity)
        if np.any(identity & ((a != n) | (ae != e))):
            raise ValueError("no_cut requires identical selected/unselected samples")
        alo, ahi = self._bounds(a, n, comparisons=2)
        blo, bhi = self._bounds(ae, e, comparisons=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            lower, upper = 1 - bhi / alo, 1 - blo / ahi
        defined = (a > 0) & (e > 0)
        lower, upper = np.where(identity, 0., lower), np.where(identity, 0., upper)
        return _result(np.where(defined, lower, np.nan), np.where(defined, upper, np.nan))
