"""Contract gates without constructing a physical circuit or a new runner."""

from dataclasses import fields, replace
import hashlib
import inspect

import numpy as np
import pytest

from knill_bench.preparation import (
    BoundaryConstraintModel, PreparationBatch, PreparationCapabilityError,
    PreparationDecoder, PreparationObservations, PreparationSettings, PreparationTruth,
)
from knill_bench.decoding.temporal_dem import TemporalDemModel, completed_dem_to_temporal_model
from knill_bench.decoding.temporal_matching import TemporalMatching


@pytest.mark.parametrize("rounds", [0, -1, True, 2.0, "d", "2*d", 2**63])
def test_rounds_cannot_reuse_distance_rules_or_cycles(rounds):
    with pytest.raises(ValueError, match="explicit positive signed-int64"):
        PreparationSettings(rounds)


@pytest.mark.parametrize("change", [
    {"prep_basis": "x"}, {"sign_sector": "z"}, {"readout_basis": "x"},
    {"logical_evaluation": "terminal_recovery"}, {"adaptive": True}, {"adaptive": 0},
])
def test_unsupported_scientific_modes_are_capability_errors(change):
    with pytest.raises(PreparationCapabilityError):
        replace(PreparationSettings(3), **change)


def test_truth_is_separate_from_decoder_inputs_and_changing_it_cannot_change_core_score():
    observations = PreparationObservations(np.array([[False], [True]]), np.zeros((2, 1), dtype=bool))
    zeros = np.zeros((2, 1), dtype=bool)
    first = PreparationBatch(observations, PreparationTruth(zeros.copy(), zeros.copy(), zeros.copy()))
    second = replace(first, truth=PreparationTruth(~zeros, ~zeros, ~zeros))
    assert {f.name for f in fields(PreparationObservations)} == {
        "online_x_detectors", "online_z_detectors"}
    assert tuple(inspect.signature(PreparationDecoder.decode_batch).parameters) == (
        "self", "online_x_detectors", "online_z_detectors")
    model = completed_dem_to_temporal_model(
        "error(.1) D0 D1 L0\nerror(.2) D1 D2 L0",
        detector_roles=["past", "online", "future"],
    )
    core = TemporalMatching(**model.matching_kwargs())
    a = core.decode_batch(first.observations.online_x_detectors)
    b = core.decode_batch(second.observations.online_x_detectors)
    for name in ("baseline_features", "complementary_features", "gaps", "status"):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))


@pytest.mark.parametrize("shots", [1, 2])
def test_buffer_backreference_cannot_expose_truth_through_online_numpy_views(shots):
    shared = np.zeros((shots, 3), dtype=bool)
    observations = PreparationObservations(shared[:, :1], np.zeros((shots, 1), dtype=bool))
    truth = PreparationTruth(shared[:, 1:2], shared[:, 2:3], shared[:, 2:3])
    with pytest.raises(ValueError, match="must not share truth storage"):
        PreparationBatch(observations, truth)


def test_batch_rejects_misaligned_shots_and_nonboolean_arrays():
    with pytest.raises(ValueError, match="bool ndarray"):
        PreparationObservations(np.zeros((2, 1), dtype=np.uint8), np.zeros((2, 1), dtype=bool))
    with pytest.raises(ValueError, match="equal shot counts"):
        PreparationObservations(np.zeros((2, 1), dtype=bool), np.zeros((3, 1), dtype=bool))
    with pytest.raises(ValueError, match="one logical Z"):
        PreparationTruth(*(np.zeros((2, 2), dtype=bool) for _ in range(3)))
    with pytest.raises(ValueError, match="equal shot counts"):
        PreparationTruth(np.zeros((2, 1), dtype=bool), np.zeros((3, 1), dtype=bool),
                         np.zeros((2, 1), dtype=bool))
    observations = PreparationObservations(*(np.zeros((2, 1), dtype=bool) for _ in range(2)))
    with pytest.raises(ValueError, match="equal shot counts"):
        PreparationBatch(observations, PreparationTruth(*(np.zeros((3, 1), dtype=bool) for _ in range(3))))


def test_boundary_contract_reuses_seed_columns_and_identifies_its_source_and_strictness():
    assert BoundaryConstraintModel is TemporalDemModel
    model = completed_dem_to_temporal_model(
        "error(.1) D0 D1 L0\nerror(0) D1 D2", detector_roles=["past", "online", "future"])
    import stim
    expected = hashlib.sha256(str(stim.DetectorErrorModel(
        "error(.1) D0 D1 L0\nerror(0) D1 D2")).encode()).hexdigest()
    assert model.source_dem_sha256 == expected
    assert model.strictness == "completed_individual_degree_le_2_no_separators_v1"
    assert model.weight_rounding == "numpy_rint_ties_to_even"
    assert model.matching_kwargs()["mechanism_ids"] == (model.mechanism_ids[0],)
    np.testing.assert_array_equal(model.expand_errors([[1]]), [[1, 0]])
