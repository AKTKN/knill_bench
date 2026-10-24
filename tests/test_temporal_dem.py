"""Semantic tests of completed DEM boundaries and retained evaluation labels."""

from itertools import product

import numpy as np
import pytest
import stim

from knill_bench.decoding.temporal_dem import (
    DetectorRole,
    bernoulli_integer_weights,
    completed_dem_to_temporal_model,
)
from knill_bench.decoding.temporal_matching import TemporalMatching, TemporalStatus


def test_temporal_and_spatial_ports_are_distinguished_before_contraction():
    # First/last readout faults and a spatial data fault share the same ONLINE
    # column.  The next spatial fault has no online detector at all.
    dem = stim.DetectorErrorModel("""
        error(0.10) D0 D1 L0
        error(0.20) D1 D2 L1
        error(0.02) D1
        error(0.03) D2 L2
        error(0.04) D0 D2 L2
        error(0.05) D0 D3 L0
        error(0.06) D2 D4 L1
        error(0.07) L2
        error(0.08)
    """)
    model = completed_dem_to_temporal_model(
        dem, detector_roles=["past", "online", "future", "past", "future"])
    np.testing.assert_array_equal(model.h_online.toarray(), [[1, 1, 1, 0, 0, 0, 0, 0, 0]])
    np.testing.assert_array_equal(model.past, [1, 0, 0, 0, 1, 0, 0, 0, 0])
    np.testing.assert_array_equal(model.future, [0, 1, 0, 1, 1, 0, 0, 0, 0])
    np.testing.assert_array_equal(model.frozen_columns, [2, 3])
    np.testing.assert_array_equal(model.invisible_columns, [7, 8])
    np.testing.assert_array_equal(model.zero_online_columns, [3, 4, 5, 6, 7, 8])
    assert model.h_completed.shape == (5, 9)
    assert model.feature_map.shape == (3, 9)
    assert model.provenance_kind == "completed_dem_term"
    assert model.terms[3].detector_ids == (2,)
    assert model.terms[7].observable_ids == (2,)

    # Boundary-to-boundary mechanisms cancelled by contraction remain in the
    # full truth map, just like completely detector-invisible mechanisms.
    actual_faults = np.zeros((1, 9), dtype=np.uint8)
    actual_faults[0, [5, 6, 7]] = 1
    np.testing.assert_array_equal(actual_faults @ model.h_online.T % 2, [[0]])
    np.testing.assert_array_equal(actual_faults @ model.feature_map.T % 2, [[1, 1, 1]])
    result = TemporalMatching(**model.matching_kwargs()).decode_batch([[0]], return_errors=True)
    assert result.status[0] == TemporalStatus.OK.value
    assert not result.baseline_errors.any()
    assert not result.baseline_features.any()  # Unobserved truth was NOT supplied.
    assert result.complementary_errors[0, 3] == 0  # Future/spatial escape is fixed.


def test_same_online_column_keeps_temporal_roles_features_and_duplicate_terms():
    model = completed_dem_to_temporal_model("""
        error(0.2) D0 D1 L0
        error(0.1) D1 D2 L1
        error(0.05) D1 L2
        error(0.1) D0 D1 L2
        error(0.2) D0 D1 L0
    """, detector_roles={0: DetectorRole.PAST, 1: DetectorRole.ONLINE, 2: DetectorRole.FUTURE})
    assert model.num_mechanisms == 5
    assert len(set(model.mechanism_ids)) == 5
    np.testing.assert_array_equal(model.h_online.toarray(), np.ones((1, 5), dtype=np.uint8))
    np.testing.assert_array_equal(model.h_completed[:, 0].toarray(), model.h_completed[:, 4].toarray())
    assert model.probabilities[0] == model.probabilities[4] == 0.2
    assert model.weights[0] == model.weights[4] == 1386
    assert model.terms[0] != model.terms[4]
    decoder = TemporalMatching(**model.matching_kwargs())
    result = decoder.decode_batch([[1]], return_errors=True)
    assert result.status[0] == TemporalStatus.OK.value
    assert result.baseline_weights[0] == 1386
    assert result.complementary_weights[0] == 2197
    assert result.gaps[0] == 811
    np.testing.assert_array_equal(result.baseline_features, [[1, 0, 0]])
    np.testing.assert_array_equal(result.complementary_features, [[0, 1, 0]])


def test_retained_model_and_matching_costs_agree_with_exhaustive_small_dem():
    model = completed_dem_to_temporal_model("""
        error(0.10) D0 D1 L0
        error(0.20) D1 D2
        error(0.30) D2 D3 L1
        error(0.40) D1 L0
        error(0.05) D3 L1
        error(0.02) L0 L1
    """, detector_roles=["past", "online", "online", "future"])
    decoder = TemporalMatching(**model.matching_kwargs())
    shots = np.asarray(list(product((0, 1), repeat=2)), dtype=np.uint8)
    result = decoder.decode_batch(shots, return_errors=True)
    all_errors = np.asarray(list(product((0, 1), repeat=6)), dtype=np.uint8)
    all_syndromes = all_errors @ model.h_online.T % 2
    all_costs = all_errors @ model.weights
    assert np.all(result.status == TemporalStatus.OK.value)
    for i, shot in enumerate(shots):
        baseline = result.baseline_errors[i]
        compatible = np.all(all_syndromes == shot, axis=1)
        assert result.baseline_weights[i] == all_costs[compatible].min()
        opposite = (compatible
                    & np.all(all_errors[:, model.frozen_columns] == baseline[model.frozen_columns], axis=1)
                    & (all_errors @ model.past % 2 == (baseline @ model.past % 2) ^ 1)
                    & (all_errors @ model.future % 2 == (baseline @ model.future % 2) ^ 1))
        assert result.complementary_weights[i] == all_costs[opposite].min()
    np.testing.assert_array_equal(result.baseline_features, result.baseline_errors @ model.feature_map.T % 2)


def test_zero_probability_terms_are_preserved_but_cannot_supply_a_temporal_path():
    model = completed_dem_to_temporal_model("""
        error(0) D0 D1 L0
        error(0.2) D1 D2 L1
        error(0.1) D1 L2
        error(0) L2
    """, detector_roles=["past", "online", "future"])
    np.testing.assert_array_equal(model.active_columns, [1, 2])
    np.testing.assert_array_equal(model.inactive_columns, [0, 3])
    np.testing.assert_array_equal(model.weights, [0, 1386, 2197, 0])
    kwargs = model.matching_kwargs()
    assert kwargs["h_online"].shape == (1, 2)
    np.testing.assert_array_equal(kwargs["frozen_columns"], [1])
    assert kwargs["mechanism_ids"] == (model.mechanism_ids[1], model.mechanism_ids[2])
    decoder = TemporalMatching(**kwargs)
    assert not decoder.has_temporal_path
    result = decoder.decode_batch([[1]], return_errors=True)
    assert result.status[0] == TemporalStatus.NO_COMPLEMENTARY_SOLUTION.value
    full = model.expand_errors(result.baseline_errors)
    np.testing.assert_array_equal(full, [[0, 1, 0, 0]])
    np.testing.assert_array_equal(full @ model.feature_map.T % 2, result.baseline_features)
    with pytest.raises(ValueError, match="active_errors"):
        model.expand_errors([[0, 0, 0, 0]])


def test_noiseless_dem_keeps_declared_rows_and_requested_feature_dimension():
    model = completed_dem_to_temporal_model(
        "detector D2", detector_roles=["past", "online", "future"], num_observables=5)
    assert model.h_completed.shape == (3, 0)
    assert model.h_online.shape == (1, 0)
    assert model.feature_map.shape == (5, 0)
    assert model.weights.shape == (0,)
    assert model.active_columns.shape == (0,)
    result = TemporalMatching(**model.matching_kwargs()).decode_batch([[0], [1]])
    assert result.baseline_features.shape == (2, 5)
    assert result.status.tolist() == [TemporalStatus.NO_COMPLEMENTARY_SOLUTION.value,
                                     TemporalStatus.INVALID_SYNDROME.value]


def test_repeat_and_detector_shift_keep_absolute_row_roles_and_term_order():
    model = completed_dem_to_temporal_model("""
        repeat 2 {
            error(0.1) D0 D1 L0
            shift_detectors 1
        }
        error(0.2) D0 D1 L1
    """, detector_roles=["past", "online", "online", "future"])
    assert tuple(term.detector_ids for term in model.terms) == ((0, 1), (1, 2), (2, 3))
    assert tuple(term.term_index for term in model.terms) == (0, 1, 2)
    assert tuple(term.instruction_index for term in model.terms) == (0, 1, 2)
    np.testing.assert_array_equal(model.h_online.toarray(), [[1, 1, 0], [0, 1, 1]])
    np.testing.assert_array_equal(model.past, [1, 0, 0])
    np.testing.assert_array_equal(model.future, [0, 0, 1])


def test_repeated_targets_are_xor_reduced_not_merged_with_other_terms():
    model = completed_dem_to_temporal_model("""
        error(0.1) D0 D0 L0 L0 L1
        error(0.2) L1
    """, detector_roles=["online"])
    assert model.num_mechanisms == 2
    assert model.h_completed.nnz == 0
    np.testing.assert_array_equal(model.feature_map.toarray(), [[0, 0], [1, 1]])
    np.testing.assert_array_equal(model.invisible_columns, [0, 1])


@pytest.mark.parametrize("roles", [None, [], ["online"], ["past", "online", "future", "online"],
                                      {0: "past", 2: "future"}, {0: "past", 1: "online", 3: "future"},
                                      {False: "past", 1: "online", 2: "future"},
                                      ["past", "spatial", "future"], "pof"])
def test_rejects_missing_incomplete_or_unrecognized_row_metadata(roles):
    with pytest.raises(ValueError, match="detector_roles"):
        completed_dem_to_temporal_model("error(0.1) D0 D2", detector_roles=roles)


def test_rejects_correlated_separators_even_when_components_are_individually_graphlike():
    with pytest.raises(ValueError, match="separators"):
        completed_dem_to_temporal_model(
            "error(0.1) D0 D1 ^ D2 D3 L0",
            detector_roles=["past", "online", "online", "future"])


def test_rejects_completed_hyperedge_before_boundary_xor_could_hide_it():
    with pytest.raises(ValueError, match="before temporal contraction"):
        completed_dem_to_temporal_model("error(0.1) D0 D1 D2",
                                        detector_roles=["past", "past", "online"])


@pytest.mark.parametrize("count", [-1, 1, 2.5, True])
def test_rejects_invalid_or_truncated_observable_dimension(count):
    with pytest.raises(ValueError, match="num_observables"):
        completed_dem_to_temporal_model("error(0.1) L2", detector_roles=[], num_observables=count)


def test_correct_common_bernoulli_costs_and_near_half_tie():
    probs = np.asarray([0.0, 0.001, 0.01, 0.1, 0.2, np.nextafter(0.5, 0.0)])
    actual = bernoulli_integer_weights(probs, weight_scale=10000)
    expected = np.zeros(len(probs), dtype=np.int64)
    expected[1:] = np.rint(10000 * np.log((1 - probs[1:]) / probs[1:])).astype(np.int64)
    np.testing.assert_array_equal(actual, expected)
    assert actual[-1] == 0
    assert actual.dtype == np.int64
    # This specifically prevents inheriting Hex's historical log((1+p)/p).
    assert actual[3] != round(10000 * np.log((1 + 0.1) / 0.1))


@pytest.mark.parametrize("probabilities", [[np.nan], [np.inf], [-0.1], [0.5], [0.9], [1],
                                              [1.1], [[0.1]], [0.1 + 0.2j]])
def test_rejects_invalid_probabilities_and_unsupported_nonpositive_cost_priors(probabilities):
    with pytest.raises(ValueError, match="probabilities"):
        bernoulli_integer_weights(probabilities)


@pytest.mark.parametrize("probability", [0.5, 0.9, 1.0])
def test_parser_does_not_bypass_probability_contract(probability):
    with pytest.raises(ValueError, match="0 <= p < 0.5"):
        completed_dem_to_temporal_model(f"error({probability}) D0", detector_roles=["online"])


@pytest.mark.parametrize("scale", [0, -1, np.nan, np.inf, True, "invalid"])
def test_rejects_invalid_common_scale(scale):
    with pytest.raises(ValueError, match="weight_scale"):
        bernoulli_integer_weights([0.1], weight_scale=scale)


def test_edge_cost_overflow_is_rejected_not_clipped_or_renormalized():
    with pytest.raises(ValueError, match=r"2\*\*24-1"):
        bernoulli_integer_weights([0.1], weight_scale=10**8)
    with pytest.raises(ValueError, match=r"2\*\*24-1"):
        bernoulli_integer_weights([1e-300], weight_scale=1e308)


def test_total_cost_exactness_guard_without_allocating_half_a_billion_edges(monkeypatch):
    # The production bound is 2**53-1.  Lowering only the bound exercises the
    # same accumulation guard without an unreasonable multi-gigabyte fixture.
    import knill_bench.decoding.temporal_dem as adapter
    monkeypatch.setattr(adapter, "MAX_EXACT_TOTAL_WEIGHT", 4000)
    with pytest.raises(ValueError, match="Total integer cost"):
        bernoulli_integer_weights([0.1, 0.1])
