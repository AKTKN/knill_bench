"""Analytic Wilson and paired-count transforms; no physical sampling."""

import math
from statistics import NormalDist

import numpy as np
import pytest
from scipy.stats import binomtest

from knill_bench.analysis import WilsonInterval


@pytest.mark.parametrize("confidence", [.90, .95, .99])
def test_bounds_match_independent_scipy_score_implementation(confidence):
    interval = WilsonInterval(confidence)
    for shots in (1, 2, 7, 20):
        for errors in range(shots + 1):
            reference = binomtest(errors, shots).proportion_ci(confidence_level=confidence, method="wilson")
            np.testing.assert_allclose(interval.bounds(errors, shots), [reference.low, reference.high], atol=2e-15)


def test_vector_broadcast_boundaries_empty_selection_and_frequency_units():
    interval = WilsonInterval()
    lower, upper = interval.bounds(np.array([0, 3, 7]), 7)
    z2 = NormalDist().inv_cdf(.975) ** 2
    assert lower[0] == 0 and upper[-1] == 1
    assert upper[0] == pytest.approx(z2 / (7 + z2))
    assert lower[-1] == pytest.approx(7 / (7 + z2))
    assert all(math.isnan(v) for v in interval.bounds(0, 0))
    assert math.isfinite(lower[1])
    counts = interval.frequency([0, 3, 7], 7)
    rates = interval.frequency([0, 3, 7], 7, normalize=True)
    np.testing.assert_allclose(np.asarray(counts), np.asarray(rates) * 7)
    np.testing.assert_allclose(interval.bounds(1, [2, 7]), np.array([interval.bounds(1, n) for n in [2, 7]]).T)


def test_per_round_endpoints_follow_monotone_normalization():
    interval = WilsonInterval()
    errors, shots, rounds = np.array([0, 3, 7]), np.array([7, 7, 7]), np.array([3, 6, 8])
    raw = np.array(interval.bounds(errors, shots))
    expected = 1 - (1 - raw) ** (1 / rounds)
    np.testing.assert_allclose(interval.per_round(errors, shots, rounds), expected)


def test_reduction_uses_paired_error_retention_and_bonferroni_adjustment():
    interval = WilsonInterval()
    accepted_errors, accepted, errors, shots = 1, 2, 3, 6
    # For fixed cuts, LER_selected/LER_all = P(accept|error)/P(accept).
    a = binomtest(accepted, shots).proportion_ci(confidence_level=.975, method="wilson")
    b = binomtest(accepted_errors, errors).proportion_ci(confidence_level=.975, method="wilson")
    expected = [1 - b.high / a.low, 1 - b.low / a.high]
    result = interval.reduction(accepted_errors, accepted, errors, shots)
    np.testing.assert_allclose(result, expected)
    point = 1 - (accepted_errors / accepted) / (errors / shots)
    assert result[0] < point < result[1]
    assert result[0] < 0  # deterioration is not clipped away
    assert interval.reduction(3, 6, 3, 6, no_cut=True) == (0., 0.)
    observed_all_pass = interval.reduction(3, 6, 3, 6)
    assert observed_all_pass[0] < 0 < observed_all_pass[1]


def test_reduction_preserves_undefined_cases_and_paired_count_constraints():
    interval = WilsonInterval()
    lower, upper = interval.reduction([0, 0, 1], [0, 4, 2], [3, 0, 3], 6)
    assert np.isnan(lower[:2]).all() and np.isnan(upper[:2]).all()
    assert np.isfinite(lower[2]) and np.isfinite(upper[2])
    for counts in ((0, 6, 3, 6), (3, 2, 3, 6), (2, 3, 1, 6), (1, 7, 3, 6)):
        with pytest.raises(ValueError):
            interval.reduction(*counts)
    with pytest.raises(ValueError, match="identical"):
        interval.reduction(3, 5, 3, 6, no_cut=True)


@pytest.mark.parametrize("confidence", [0, 1, -.1, math.nan, math.inf, True, "95%"])
def test_invalid_confidence(confidence):
    with pytest.raises(ValueError, match="confidence"):
        WilsonInterval(confidence)


@pytest.mark.parametrize("counts", [(True, 7), (1.5, 7), (1, 7.), (-1, 7), (8, 7), (0, -1)])
def test_invalid_counts_are_rejected(counts):
    with pytest.raises(ValueError):
        WilsonInterval().bounds(*counts)


def test_invalid_shapes_and_round_counts():
    with pytest.raises(ValueError, match="shapes"):
        WilsonInterval().bounds([1, 2], [2, 3, 4])
    for rounds in (0, 1.5, True):
        with pytest.raises(ValueError, match="rounds"):
            WilsonInterval().per_round(1, 7, rounds)
