"""Hand-derived boundary columns, cost policy and strict portable artifacts."""

from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest
import stim

from knill_bench.decoding.temporal_artifact import read_temporal_model, write_temporal_model
from knill_bench.decoding.temporal_dem import TemporalDemModel, completed_dem_to_temporal_model
from knill_bench.decoding.temporal_matching import TemporalMatching
from knill_bench.decoding.temporal_validation import compare_marginal_models, marginal_parity_probabilities


def fixture_model():
    return completed_dem_to_temporal_model("""
        error(0) D0 D1 L0
        error(0.2) D0 D1 L0
        error(0.1) D1 D2 L1
        error(0.01) D1 L0
        error(0.03) D2 L1
        error(0.07) D2 D3 L0
        error(0.04) L2
        error(0.499999999999) D0 D2 L2
    """, detector_roles=["past", "online", "future", "future"],
        num_observables=4, feature_observable_ids=[2, 0, 3, 1],
        feature_ids=["logical", "tau:0", "unused", "tau:1"],
        model_provenance={"fixture": "R2", "completed_by": "explicit_rows"})


def test_model_metadata_full_support_unidentifiable_and_common_float_costs():
    model = fixture_model()
    assert model.full_detector_support == ((0, 1), (0, 1), (1, 2), (1,), (2,), (2, 3), (), (0, 2))
    np.testing.assert_array_equal(model.unidentifiable_columns, [6])
    np.testing.assert_array_equal(model.frozen_columns, [3, 4])
    assert model.past[5] == model.future[5] == model.h_online[:, 5].nnz == 0
    np.testing.assert_array_equal(model.feature_map[:, 5].toarray().ravel(), [0, 1, 0, 0])
    assert np.isinf(model.float_weights[0])
    assert model.float_weights[1] == pytest.approx(np.log(4))
    assert model.weights[-1] == 0 and model.float_weights[-1] > 0
    metadata = model.metadata
    assert metadata["float_weights"][0] is None
    assert metadata["active_zero_policy"] == "retain_quantized_zero_no_clipping"
    assert metadata["max_edge_weight"] == 2**24 - 1
    assert metadata["max_exact_total_weight"] == 2**53 - 1
    json.dumps(metadata, allow_nan=False)
    assert model.matching_kwargs()["weights"][-1] == 0


def test_active_rounded_zero_remains_a_feasible_zero_cost_temporal_path():
    model = completed_dem_to_temporal_model("error(.499999999999) D0 D2 L0",
        detector_roles=["past", "online", "future"])
    result = TemporalMatching(**model.matching_kwargs()).decode_batch([[0]], return_errors=True)
    assert model.active_columns.tolist() == [0]
    assert result.status.tolist() == ["ok"]
    assert result.baseline_weights.tolist() == result.complementary_weights.tolist() == [0]
    assert result.gaps.tolist() == [0]
    assert result.baseline_features.tolist() == [[0]]
    assert result.complementary_features.tolist() == [[1]]


def test_roundtrip_preserves_original_columns_feature_order_and_solver_without_stim(tmp_path, monkeypatch):
    model = fixture_model()
    path = tmp_path / "boundary.json"
    digest = write_temporal_model(path, model)
    # Loading/decoding must not reconstruct or reparse a Stim DEM.
    monkeypatch.setattr(stim, "DetectorErrorModel", lambda *a, **k: pytest.fail("unexpected DEM parsing"))
    loaded = read_temporal_model(path, expected_sha256=digest)
    assert loaded.to_artifact() == model.to_artifact()
    assert loaded.feature_ids == ("logical", "tau:0", "unused", "tau:1")
    for name in ("h_completed", "h_online", "feature_map"):
        np.testing.assert_array_equal(getattr(loaded, name).toarray(), getattr(model, name).toarray())
    for name in ("past", "future", "weights", "float_weights", "active_columns", "inactive_columns", "frozen_columns"):
        np.testing.assert_array_equal(getattr(loaded, name), getattr(model, name))
    a = TemporalMatching(**model.matching_kwargs()).decode_batch([[0], [1]], return_errors=True)
    b = TemporalMatching(**loaded.matching_kwargs()).decode_batch([[0], [1]], return_errors=True)
    for name in ("baseline_features", "complementary_features", "gaps", "status"):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))
    assert not loaded.expand_errors(b.baseline_errors)[:, 0].any()
    with pytest.raises(FileExistsError):
        write_temporal_model(path, loaded)
    with pytest.raises(ValueError, match="owning-run"):
        read_temporal_model(path, expected_sha256="0" * 64)


def _rehash(artifact):
    artifact["sha256"] = hashlib.sha256(json.dumps(artifact["payload"], sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return artifact


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(artifact_version=True),
    lambda p: p.update(extra="unknown"),
    lambda p: p["terms"][0].update(detector_ids=[4]),
    lambda p: p["terms"][0].update(observable_ids=[4]),
    lambda p: p["terms"][0].update(detector_ids=[0, 0]),
    lambda p: p["terms"][0].update(detector_ids=[0, 1, 2]),
    lambda p: p["terms"][1].update(term_index=0),
    lambda p: p["terms"][1].update(instruction_index=0),
    lambda p: p["detector_roles"].__setitem__(0, "spatial"),
    lambda p: p["detector_roles"].__setitem__(0, {"id": 0, "role": "past"}),
    lambda p: p["metadata"].update(feature_observable_ids=[0, 0, 1, 2]),
    lambda p: p["metadata"].update(feature_ids=["x", "x", "y", "z"]),
    lambda p: p["metadata"].update(weight_rounding="floor"),
    lambda p: p["metadata"].update(provenance_kind="unique_physical_fault"),
    lambda p: p["metadata"].update(provenance=[]),
    lambda p: p["metadata"]["float_weights"].__setitem__(1, 0.),
    lambda p: p["weights"].__setitem__(1, 0),
    lambda p: p["probabilities"].__setitem__(0, -.1),
    lambda p: p["probabilities"].__setitem__(0, .5),
    lambda p: p["probabilities"].append(.1),
])
def test_even_rehashed_artifacts_reject_invalid_or_inconsistent_columns_and_policy(mutation):
    artifact = deepcopy(fixture_model().to_artifact())
    mutation(artifact["payload"])
    with pytest.raises(ValueError, match="Invalid temporal model artifact"):
        TemporalDemModel.from_artifact(_rehash(artifact))


def test_artifact_checksum_and_duplicate_json_keys_fail(tmp_path):
    artifact = fixture_model().to_artifact()
    artifact["payload"]["probabilities"][0] = .1
    with pytest.raises(ValueError, match="SHA256"):
        TemporalDemModel.from_artifact(artifact)
    path = tmp_path / "duplicate.json"
    path.write_text('{"payload":{},"payload":{},"sha256":"x"}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_temporal_model(path)


@pytest.mark.parametrize("ids", [[0, 0], [3], [-1], [True], [.5]])
def test_invalid_explicit_feature_mapping_rejected(ids):
    with pytest.raises(ValueError, match="feature_observable_ids"):
        completed_dem_to_temporal_model("error(.1) L2", detector_roles=[], feature_observable_ids=ids)


@pytest.mark.parametrize("names", ["abc", ["x", "x", "z"], ["", "y", "z"], [[], "y", "z"], 1])
def test_invalid_feature_names_rejected(names):
    with pytest.raises(ValueError, match="feature_ids"):
        completed_dem_to_temporal_model("error(.1) L2", detector_roles=[], feature_ids=names)


@pytest.mark.parametrize("provenance", [[], "location", {"unknown": np.nan}, {"unknown": object()}])
def test_non_mapping_or_nonfinite_provenance_rejected(provenance):
    with pytest.raises((ValueError, TypeError)):
        completed_dem_to_temporal_model("error(.1) L0", detector_roles=[], model_provenance=provenance)


def test_fixed_zero_and_one_are_both_preserved_through_model_and_artifact():
    # D0 has only a spatial edge, forcing it to one; D1's spatial edge is
    # cheaper than a path but baseline zero fixes it out of the complement.
    model = completed_dem_to_temporal_model("""
        error(.3) D1
        error(.3) D2
        error(.1) D0 D2
        error(.1) D2 D3
    """, detector_roles=["past", "online", "online", "future"])
    loaded = TemporalDemModel.from_artifact(model.to_artifact())
    result = TemporalMatching(**loaded.matching_kwargs()).decode_batch([[1, 0]], return_errors=True)
    np.testing.assert_array_equal(result.baseline_errors[0, loaded.frozen_columns], [1, 0])
    np.testing.assert_array_equal(result.complementary_errors[0, loaded.frozen_columns], [1, 0])
    assert result.complementary_weights[0] == 847 + 2 * 2197


def test_same_signature_uses_independent_xor_probability_not_sum_and_retains_invisible_labels():
    dem = stim.DetectorErrorModel("error(.1) D0 L0\nerror(.2) D0 L0\nerror(.07) L1\nerror(0) L2")
    probabilities = marginal_parity_probabilities(dem, detector_ids=[0], observable_ids=[0, 1, 2])
    assert probabilities == pytest.approx({((0,), (0,)): .26, ((), (1,)): .07})
    compare_marginal_models(dem, stim.DetectorErrorModel("error(.26) D0 L0\nerror(.07) L1\nlogical_observable L2"),
        production_detector_ids=[0], completed_detector_ids=[0], production_observable_ids=[0, 1, 2],
        completed_observable_ids=[0, 1, 2])
    with pytest.raises(ValueError, match="probabilities differ"):
        compare_marginal_models(dem, stim.DetectorErrorModel("error(.3) D0 L0\nerror(.07) L1\nlogical_observable L2"),
            production_detector_ids=[0], completed_detector_ids=[0], production_observable_ids=[0, 1, 2],
            completed_observable_ids=[0, 1, 2])


def test_marginalization_is_validation_only_and_keeps_distinct_temporal_graph_terms():
    model = fixture_model()
    assert model.num_mechanisms == 8
    assert model.matching_kwargs()["h_online"].shape[1] == 7
    # Same online support is not a reason to merge P-online, online-F or
    # spatial events. The seed core retains each separate mechanism ID.
    assert len(set(model.matching_kwargs()["mechanism_ids"])) == 7


@pytest.mark.parametrize("text", ["error(.1) D0 ^ D1", "error(.5) D0"])
def test_validation_comparison_does_not_approximate_invalid_models(text):
    with pytest.raises(ValueError):
        marginal_parity_probabilities(stim.DetectorErrorModel(text), detector_ids=[0], observable_ids=[])


def test_comparison_rejects_dropped_labels_and_duplicate_or_out_of_range_selected_ids():
    dem = stim.DetectorErrorModel("error(.1) D0 L0\nerror(.2) L1")
    for ids in ([0, 0], [-1], [1], [True]):
        with pytest.raises(ValueError, match="detector_ids"):
            marginal_parity_probabilities(dem, detector_ids=ids, observable_ids=[0, 1])
    with pytest.raises(ValueError, match="observable_ids"):
        marginal_parity_probabilities(dem, detector_ids=[0], observable_ids=[2])
    # Keeping declared label dimensions while stripping the actual responses
    # must still fail: the lost undetected L1 event matters to output truth.
    stripped = stim.DetectorErrorModel("error(.1) D0 L0\nlogical_observable L1")
    with pytest.raises(ValueError, match="signature supports differ"):
        compare_marginal_models(dem, stripped, production_detector_ids=[0], completed_detector_ids=[0],
            production_observable_ids=[0, 1], completed_observable_ids=[0, 1])
