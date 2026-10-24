"""Exact small-model tests of temporal constraints, not noise-performance claims."""

from itertools import product

import numpy as np
import pytest
from scipy.sparse import csc_matrix

from knill_bench.decoding.temporal_matching import TemporalMatching, TemporalStatus


def bits(size):
    return np.asarray(list(product((0, 1), repeat=size)), dtype=np.uint8).reshape(-1, size)


def assert_temporal_path(model, difference):
    """Independently traverse the original unmerged selected mechanism support."""
    n = model.num_detectors
    adjacency = [set() for _ in range(n + 2)]
    h = model.h_online.toarray()
    for j in np.flatnonzero(difference):
        endpoints = list(np.flatnonzero(h[:, j]))
        if model.past[j]:
            endpoints.append(n)
        if model.future[j]:
            endpoints.append(n + 1)
        if len(endpoints) == 2:
            a, b = endpoints
            adjacency[a].add(b)
            adjacency[b].add(a)
        else:
            assert not endpoints
    seen = {n}
    stack = [n]
    while stack:
        node = stack.pop()
        for other in adjacency[node] - seen:
            seen.add(other)
            stack.append(other)
    assert n + 1 in seen


@pytest.mark.parametrize("weights", [
    [2, 3, 5, 7, 1, 11, 13, 17, 19],
    [0, 2, 2, 0, 1, 3, 2, 0, 0],
])
def test_exhaustive_all_syndromes_and_frozen_one(weights):
    # A three-vertex temporal path, two spatial ports, parallel internal
    # mechanisms, a zero-online P--F event, and an invisible labelled event.
    h = np.array([[1, 1, 0, 0, 1, 0, 1, 0, 0],
                  [0, 1, 1, 0, 0, 1, 1, 0, 0],
                  [0, 0, 1, 1, 0, 0, 0, 0, 0]], dtype=np.uint8)
    past = np.array([1, 0, 0, 0, 0, 0, 0, 1, 0], dtype=np.uint8)
    future = np.array([0, 0, 0, 1, 0, 0, 0, 1, 0], dtype=np.uint8)
    frozen = [4, 5]
    feature_map = np.array([[1, 0, 1, 0, 1, 0, 0, 1, 0],
                            [0, 1, 0, 1, 0, 1, 1, 0, 1]], dtype=np.uint8)
    model = TemporalMatching(h, past, future, frozen, weights, feature_map=feature_map)
    syndromes = bits(3)
    result = model.decode_batch(syndromes, return_errors=True)
    errors = bits(h.shape[1])
    costs = errors @ np.asarray(weights)
    signatures = errors @ h.T % 2
    assert model.has_temporal_path
    assert np.all(result.status == TemporalStatus.OK.value)
    assert not result.baseline_errors[:, 7:].any()  # Unseen baseline events use zero.
    for i, syndrome in enumerate(syndromes):
        baseline = result.baseline_errors[i]
        complementary = result.complementary_errors[i]
        feasible = np.all(signatures == syndrome, axis=1)
        assert result.baseline_weights[i] == costs[feasible].min()
        constrained = (feasible
                       & np.all(errors[:, frozen] == baseline[frozen], axis=1)
                       & (errors @ past % 2 == (baseline @ past % 2) ^ 1)
                       & (errors @ future % 2 == (baseline @ future % 2) ^ 1))
        assert constrained.any()
        assert result.complementary_weights[i] == costs[constrained].min()
        assert result.gaps[i] == result.complementary_weights[i] - result.baseline_weights[i]
        assert np.array_equal(complementary[frozen], baseline[frozen])
        assert np.array_equal(complementary @ h.T % 2, syndrome)
        assert_temporal_path(model, baseline ^ complementary)
    np.testing.assert_array_equal(result.baseline_features, result.baseline_errors @ feature_map.T % 2)
    np.testing.assert_array_equal(result.complementary_features,
                                  result.complementary_errors @ feature_map.T % 2)
    compact = model.decode_batch(syndromes)
    agrees = result.debug_matches_compact
    for field in ("baseline_features", "complementary_features", "baseline_weights",
                  "complementary_weights", "gaps"):
        np.testing.assert_array_equal(getattr(result, field)[agrees], getattr(compact, field)[agrees])
    # Validate the compact backend independently as well: use enumeration to
    # establish that all its returned parities describe a real optimum, without
    # assuming a second MWPM API resolves shortest-path ties identically.
    compact_labels, _, _, _ = model._baseline.decode_batch(syndromes)
    all_features = errors @ feature_map.T % 2
    for i, syndrome in enumerate(syndromes):
        matching_syndrome = np.all(signatures == syndrome, axis=1)
        same_fixed = np.all(errors[:, frozen] == compact_labels[i, :2], axis=1)
        p0, f0 = compact_labels[i, 2:4]
        baseline_class = (matching_syndrome & same_fixed
                          & (errors @ past % 2 == p0)
                          & (errors @ future % 2 == f0)
                          & np.all(all_features == compact.baseline_features[i], axis=1))
        assert np.any(baseline_class & (costs == compact.baseline_weights[i]))
        opposite_class = (matching_syndrome & same_fixed
                          & (errors @ past % 2 == (p0 ^ 1))
                          & (errors @ future % 2 == (f0 ^ 1)))
        assert compact.complementary_weights[i] == costs[opposite_class].min()
        assert np.any(opposite_class & (costs == compact.complementary_weights[i])
                      & np.all(all_features == compact.complementary_features[i], axis=1))


def test_r2_parallel_temporal_and_spatial_ports_keep_original_ids():
    # The first and last readout faults have the SAME online detector column.
    # Merging by smallest weight would remove the opposite temporal class.
    model = TemporalMatching([[1, 1, 1]], [1, 0, 0], [0, 1, 0], [2], [2, 3, 4],
                             feature_map=np.eye(3, dtype=np.uint8),
                             mechanism_ids=("first_readout", "last_readout", "spatial"))
    result = model.decode_batch([[1]], return_errors=True)
    assert model.mechanism_ids == ("first_readout", "last_readout", "spatial")
    np.testing.assert_array_equal(result.baseline_errors, [[1, 0, 0]])
    np.testing.assert_array_equal(result.complementary_errors, [[0, 1, 0]])
    assert result.baseline_weights.tolist() == [2]
    assert result.complementary_weights.tolist() == [3]
    assert result.gaps.tolist() == [1]
    assert_temporal_path(model, result.baseline_errors[0] ^ result.complementary_errors[0])


def test_static_frozen_one_cost_offset_and_feature_offset():
    model = TemporalMatching([[1, 1, 1]], [1, 0, 0], [0, 1, 0], [2], [2, 3, 1],
                             feature_map=[[0, 0, 1]])
    result = model.decode_batch([[1]], return_errors=True)
    np.testing.assert_array_equal(result.baseline_errors, [[0, 0, 1]])
    np.testing.assert_array_equal(result.complementary_errors, [[1, 1, 1]])
    assert result.baseline_weights.tolist() == [1]
    assert result.complementary_weights.tolist() == [6]
    assert result.gaps.tolist() == [5]
    assert result.baseline_features.tolist() == [[1]]
    assert result.complementary_features.tolist() == [[1]]


def test_frozen_temporal_column_moves_its_parity_to_rhs():
    # A fixed past edge may still be one while a different past route is changed.
    model = TemporalMatching([[1, 1, 1]], [1, 1, 0], [0, 0, 1], [0], [1, 3, 5])
    result = model.decode_batch([[1]], return_errors=True)
    np.testing.assert_array_equal(result.baseline_errors, [[1, 0, 0]])
    np.testing.assert_array_equal(result.complementary_errors, [[1, 1, 1]])
    assert result.gaps.tolist() == [8]
    assert_temporal_path(model, result.baseline_errors[0] ^ result.complementary_errors[0])


def test_zero_online_past_future_event_and_invisible_feature():
    model = TemporalMatching(np.zeros((0, 2), dtype=np.uint8), [1, 0], [1, 0], [], [7, 2],
                             feature_map=np.eye(2, dtype=np.uint8))
    result = model.decode_batch(np.zeros((3, 0), dtype=np.uint8), return_errors=True)
    assert model.has_temporal_path
    np.testing.assert_array_equal(result.baseline_errors, np.zeros((3, 2), dtype=np.uint8))
    np.testing.assert_array_equal(result.complementary_errors, [[1, 0]] * 3)
    assert result.gaps.tolist() == [7, 7, 7]


def test_infeasible_syndromes_and_missing_complement_are_distinct():
    # Detector 0 is isolated. The sole P--F event is frozen, removing all paths.
    model = TemporalMatching([[0]], [1], [1], [0], [2])
    result = model.decode_batch([[0], [1]], return_errors=True)
    assert not model.has_temporal_path
    assert result.status.tolist() == [TemporalStatus.NO_COMPLEMENTARY_SOLUTION.value,
                                      TemporalStatus.INVALID_SYNDROME.value]
    assert result.baseline_weights[0] == 0
    assert np.isnan(result.gaps[0])
    assert np.isnan(result.gaps[1])
    assert np.isinf(result.baseline_weights[1])
    assert np.isinf(result.complementary_weights).all()


def test_batch_single_and_repeat_calls_use_same_static_matchers():
    model = TemporalMatching([[1, 1, 0, 1], [0, 1, 1, 0]],
                             [1, 0, 0, 0], [0, 0, 1, 0], [3], [4, 2, 7, 1],
                             feature_map=[[1, 1, 0, 1]])
    syndromes = bits(2)
    matcher_ids = id(model._baseline.matcher), id(model._comparison.matcher)
    batched = model.decode_batch(syndromes, return_errors=True)
    assert batched.debug_matches_compact.all()
    again = model.decode_batch(syndromes)
    assert matcher_ids == (id(model._baseline.matcher), id(model._comparison.matcher))
    for field in ("baseline_features", "complementary_features", "baseline_weights",
                  "complementary_weights", "gaps", "status"):
        np.testing.assert_array_equal(getattr(batched, field), getattr(again, field))
        separately = [getattr(model.decode_batch([shot], return_errors=True), field)[0]
                      for shot in syndromes]
        np.testing.assert_array_equal(getattr(batched, field), separately)
    empty = model.decode_batch(np.zeros((0, 2), dtype=np.uint8), return_errors=True)
    assert empty.gaps.shape == (0,)
    assert empty.baseline_errors.shape == (0, 4)


def test_common_integer_weights_survive_removing_largest_weight():
    model = TemporalMatching([[1, 1, 1]], [1, 0, 0], [0, 1, 0], [2],
                             [1234567, 2345678, 16000000])
    result = model.decode_batch([[0], [1]], return_errors=True)
    assert result.gaps.tolist() == [3580245, 1111111]
    assert result.baseline_weights.tolist() == [0, 1234567]
    assert result.complementary_weights.tolist() == [3580245, 2345678]


@pytest.mark.parametrize("change, message", [
    ({"h_online": [[1, 2]]}, "binary"),
    ({"past": [1]}, "binary vector"),
    ({"future": [0, 2]}, "binary vector"),
    ({"past": [1, 1], "future": [1, 0]}, "graphlike"),
    ({"past": [0, 0]}, "must be frozen"),
    ({"weights": [1.1, 2]}, "integers"),
    ({"weights": [-1, 2]}, "integers"),
    ({"weights": [np.inf, 2]}, "integers"),
    ({"weights": [2**24, 2]}, "integers"),
    ({"frozen_columns": [0, 0]}, "distinct"),
    ({"frozen_columns": [2]}, "distinct"),
    ({"feature_map": [[1]]}, "one column"),
    ({"mechanism_ids": ["same", "same"]}, "unique"),
])
def test_rejects_malformed_input(change, message):
    arguments = dict(h_online=[[1, 1]], past=[1, 0], future=[0, 1],
                     frozen_columns=[], weights=[1, 2])
    arguments.update(change)
    with pytest.raises(ValueError, match=message):
        TemporalMatching(**arguments)


def test_rejects_unfrozen_single_port_with_no_online_detector():
    with pytest.raises(ValueError, match="must be frozen"):
        TemporalMatching(np.zeros((0, 1)), [1], [0], [], [1])
    # Explicitly freezing that port gives an admissible, but disconnected model.
    model = TemporalMatching(np.zeros((0, 1)), [1], [0], [0], [1])
    result = model.decode_batch(np.zeros((1, 0), dtype=np.uint8))
    assert result.status[0] == TemporalStatus.NO_COMPLEMENTARY_SOLUTION.value


def test_rejects_nonbinary_shots_and_supports_boolean_masks():
    model = TemporalMatching(csc_matrix([[1, 1, 1]]), [1, 0, 0], [0, 1, 0],
                             np.array([False, False, True]), [1, 2, 3])
    with pytest.raises(ValueError, match="binary"):
        model.decode_batch([[2]])
    with pytest.raises(ValueError, match="num_detectors"):
        model.decode_batch([[0, 0]])
    assert model.frozen_columns.tolist() == [2]
