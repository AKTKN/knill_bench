"""Six-row hand-derived masks/joint counts; no simulation or storage."""

from dataclasses import replace
import json

import numpy as np
import pytest
import stim

from knill_bench.decoding.preparation_prefix import prefix_dem_to_model
from knill_bench.preparation import PreparationPrediction, PreparationTruth
from knill_bench.simulation.preparation_metrics import evaluate_preparation, preparation_acceptance, summarize_preparation


def fixture():
    xvalid = np.array([1, 1, 1, 0, 1, 1], dtype=bool)
    cvalid = np.array([1, 1, 0, 0, 1, 1], dtype=bool)
    zvalid = np.array([1, 1, 1, 1, 0, 1], dtype=bool)
    pred = PreparationPrediction(
        np.zeros((6, 2), dtype=bool), np.zeros((6, 1), dtype=bool), np.zeros((6, 1), dtype=bool),
        np.array([0, 0, 0, np.inf, 0, 0]), np.array([0, 2, np.inf, np.inf, 4, 4]),
        np.array([0, 2, np.nan, np.nan, 4, 4]), xvalid, cvalid, zvalid,
        np.array(["ok", "ok", "no_complementary_solution", "invalid_syndrome", "z_decoder_invalid", "ok"]), 1.,
    )
    truth = PreparationTruth(np.array([[0, 0], [1, 0], [0, 0], [1, 1], [1, 0], [0, 1]], dtype=bool),
        np.array([[0], [0], [1], [0], [1], [0]], dtype=bool),
        np.array([[0], [1], [1], [1], [1], [0]], dtype=bool))
    return truth, pred


def test_independent_validity_baselines_per_check_histograms_joint_and_logical_given_code():
    truth, pred = fixture()
    evaluation = evaluate_preparation(truth, pred)
    summary = summarize_preparation(evaluation, threshold=2)
    assert summary["eligible"] == 3 and summary["accepted"] == 2 and summary["acceptance"] == 2 / 6
    assert summary["invalid_reasons"] == dict(x_baseline=1, no_complement=1, z_decoder=1)
    assert summary["below_cut"] == 1
    raw = summary["unconditional"]
    assert raw["sign_x"] == dict(shots=5, errors=3, rate=3 / 5)
    assert raw["sign_z"] == dict(shots=5, errors=1, rate=1 / 5)
    assert raw["code_space"] == dict(shots=4, errors=3, rate=3 / 4)
    assert raw["logical_z"] == dict(shots=5, errors=3, rate=3 / 5)
    assert raw["per_check_errors_x"] == [2, 1] and raw["per_check_errors_z"] == [1]
    assert raw["error_count_histogram_x"] == [2, 3, 0]
    assert raw["error_count_histogram_z"] == [4, 1]
    assert raw["joint_denominator"] == 4
    assert raw["joint_counts"] == [1, 0, 0, 1, 1, 1, 0, 0]
    assert raw["logical_z_given_code_correct"] == dict(shots=1, errors=0, rate=0.)
    selected = summary["selected"]
    assert selected["sign_x"] == selected["code_space"] == dict(shots=2, errors=2, rate=1.)
    assert selected["logical_z"] == dict(shots=2, errors=1, rate=.5)
    assert selected["logical_z_given_code_correct"] == dict(shots=0, errors=0, rate=None)
    assert selected["joint_counts"] == [0, 0, 0, 0, 1, 1, 0, 0]
    assert not evaluation.error_bits_x[3].any() and not evaluation.error_bits_z[4].any()
    # Row2 has no gap but its valid Z/code baseline error was retained above.
    assert evaluation.code_space_miss[2] and not evaluation.eligible[2]
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("cut,expected", [(-np.inf, [0, 1, 5]), (0, [0, 1, 5]),
                                         (2, [1, 5]), (4, [5]), (np.inf, [])])
def test_inclusive_cut_validity_and_truth_independent_acceptance(cut, expected):
    truth, pred = fixture()
    a = preparation_acceptance(pred, cut)
    assert np.flatnonzero(a).tolist() == expected
    first = evaluate_preparation(truth, pred)
    changed = evaluate_preparation(PreparationTruth(~truth.tau_x, ~truth.tau_z, ~truth.logical_z), pred)
    np.testing.assert_array_equal(first.accepted(cut), changed.accepted(cut))
    assert summarize_preparation(first, threshold=cut)["accepted"] == len(expected)


def test_single_software_frame_is_applied_once_with_double_application_negative_control():
    _, pred = fixture()
    # A predicted nonzero logical frame cancels matched truth exactly once.
    pred = replace(pred, logical_z_prediction=np.ones((6, 1), dtype=bool))
    matching = PreparationTruth(np.zeros((6, 2), dtype=bool), np.zeros((6, 1), dtype=bool),
                               np.ones((6, 1), dtype=bool))
    assert not evaluate_preparation(matching, pred).logical_z_error.any()
    physically_already_corrected = replace(matching, logical_z=np.zeros((6, 1), dtype=bool))
    after_twice = evaluate_preparation(physically_already_corrected, pred)
    assert after_twice.logical_z_error[pred.z_decoder_valid].all()


def test_empty_batches_and_zero_acceptance_produce_null_rates():
    truth, pred = fixture()
    kwargs = {name: getattr(pred, name)[:0] for name in (
        "tau_x_prediction", "tau_z_prediction", "logical_z_prediction", "baseline_weight", "complementary_weight",
        "gap", "baseline_valid", "complementary_valid", "z_decoder_valid", "status")}
    empty = replace(pred, **kwargs)
    empty_truth = PreparationTruth(truth.tau_x[:0], truth.tau_z[:0], truth.logical_z[:0])
    summary = summarize_preparation(evaluate_preparation(empty_truth, empty))
    assert summary["shots"] == summary["accepted"] == 0 and summary["acceptance"] is None
    assert summary["unconditional"]["sign_x"]["rate"] is None
    assert summary["unconditional"]["joint_counts"] == [0] * 8
    none = summarize_preparation(evaluate_preparation(truth, pred), threshold=np.inf)
    assert none["accepted"] == 0 and none["selected"]["logical_z"]["rate"] is None
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("value", [np.nan, True, "1", [1], 2**2048])
def test_invalid_thresholds_rejected(value):
    truth, pred = fixture()
    with pytest.raises(ValueError, match="threshold"):
        preparation_acceptance(pred, value)
    with pytest.raises(ValueError, match="threshold"):
        summarize_preparation(evaluate_preparation(truth, pred), threshold=value)


@pytest.mark.parametrize("change,match", [
    (dict(gap=np.array([-1, 2, np.nan, np.nan, 4, 4])), "nonnegative"),
    (dict(gap=np.array([np.inf, 2, np.nan, np.nan, 4, 4])), "finite"),
    (dict(gap=np.array([0, 2, np.inf, np.nan, 4, 4])), "NaN"),
    (dict(gap=np.array([1, 2, np.nan, np.nan, 4, 4])), "objective"),
    (dict(weight_scale=2), "objective"),
    (dict(weight_scale=0), "weight_scale"),
    (dict(weight_scale=2**2048), "weight_scale"),
    (dict(status=np.array(["ok"] * 6)), "status"),
    (dict(baseline_weight=np.zeros(6)), "integer costs"),
    (dict(logical_z_prediction=np.zeros((6, 2), dtype=bool)), "logical Z"),
])
def test_prediction_contract_rejects_inconsistent_costs_gaps_status_and_shapes(change, match):
    _, pred = fixture()
    with pytest.raises(ValueError, match=match):
        replace(pred, **change)


def test_mutated_prediction_is_revalidated_and_misaligned_truth_is_rejected():
    truth, pred = fixture()
    with pytest.raises(ValueError, match="dimensions"):
        evaluate_preparation(replace(truth, tau_x=np.zeros((6, 1), dtype=bool)), pred)
    pred.gap[0] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_preparation(truth, pred)


def test_prefix_model_projects_explicit_Z_rows_without_inventing_temporal_boundaries_or_merging():
    dem = stim.DetectorErrorModel("""
        error(.1) D0 D1 D2 D3 L0
        error(.2) D0 D1 D2 D3 L1
        error(0) D0 L0
        error(.05) L1
    """)
    model = prefix_dem_to_model(dem, detector_ids=[1, 3], observable_ids=[1, 0],
                               feature_ids=["logical_z", "tau_z:0"])
    assert model.h.shape == (2, 4) and model.h[:, :2].nnz == 4
    assert model.active_columns.tolist() == [0, 1, 3]
    assert len(set(model.mechanism_ids)) == 4
    np.testing.assert_array_equal(model.feature_map.toarray(), [[0, 1, 0, 1], [1, 0, 1, 0]])
    assert model.full_detector_support[0] == (0, 1, 2, 3)  # Both CSS sectors, before selection.
    assert model.model_sha256 != prefix_dem_to_model(dem, detector_ids=[1, 3], observable_ids=[0, 1],
        feature_ids=["tau_z:0", "logical_z"]).model_sha256


@pytest.mark.parametrize("dem,ids", [("error(.5) D0", [0]), ("error(.1) D0 ^ D1", [0, 1]),
    ("error(.1) D0 D1 D2", [0, 1, 2])])
def test_prefix_solver_rejects_unsupported_probabilities_correlations_and_selected_hyperedges(dem, ids):
    with pytest.raises(ValueError):
        prefix_dem_to_model(stim.DetectorErrorModel(dem), detector_ids=ids, observable_ids=[], feature_ids=[])
