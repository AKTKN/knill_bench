"""Independent small graph constraints and native <=7-shot adapter fixtures."""

from dataclasses import replace
import inspect

import numpy as np
import pytest
import stim

from knill_bench.adapters.temporal_gap import TemporalGapDecoder, prepare_preparation_decoder
from knill_bench.circuits.preparation import build_preparation
from knill_bench.codes import Code
from knill_bench.decoding.preparation_model import compile_preparation_prefix_model
from knill_bench.decoding.preparation_prefix import prefix_dem_to_model
from knill_bench.decoding.temporal_dem import completed_dem_to_temporal_model
from knill_bench.preparation import PreparationCapabilityError, PreparationTruth, split_preparation_samples
from knill_bench.simulation.preparation_metrics import evaluate_preparation, preparation_acceptance, summarize_preparation


def synthetic(*, mode="compact", xdem=None, zdem=None):
    # Scale one gives hand-derived exact integer costs 2,3,1 respectively.
    x = completed_dem_to_temporal_model(xdem or """
        error(0) D0 D1 L0
        error(.11920292202211755) D0 D1
        error(.04742587317756678) D1 D2 L0
        error(.2689414213699951) D1 L0
    """, detector_roles=["past", "online", "future"], feature_ids=["tau_x:0"], weight_scale=1)
    z = prefix_dem_to_model(stim.DetectorErrorModel(zdem or "error(.2) D0 L0 L1"),
        detector_ids=[0], observable_ids=[0, 1], feature_ids=["tau_z:0", "logical_z"], weight_scale=1)
    return TemporalGapDecoder(x, z, output_mode=mode)


def test_adapter_keeps_fixed_zero_one_cost_offsets_and_maps_same_solve_witnesses():
    decoder = synthetic(mode="full_witness")
    x = np.array([[0], [1]], dtype=bool)
    result = decoder.decode_batch(x, np.array([[0], [1]], dtype=bool))
    np.testing.assert_array_equal(result.baseline_weight, [0, 1])
    np.testing.assert_array_equal(result.complementary_weight, [5, 6])
    np.testing.assert_array_equal(result.gap, [5, 5])
    np.testing.assert_array_equal(result.tau_x_prediction, [[0], [1]])
    np.testing.assert_array_equal(result.tau_z_prediction, [[0], [1]])
    np.testing.assert_array_equal(result.logical_z_prediction, [[0], [1]])
    assert result.x_baseline_valid is result.baseline_valid
    diag = result.diagnostics
    assert diag.frozen_original_columns == (3,)
    np.testing.assert_array_equal(diag.baseline_frozen, [[0], [1]])
    full0 = decoder.x_model.expand_errors(result.debug.baseline_errors)
    full1 = decoder.x_model.expand_errors(result.debug.complementary_errors)
    assert not full0[:, 0].any() and not full1[:, 0].any()
    for value in (full0, full1):
        np.testing.assert_array_equal(value @ decoder.x_model.h_online.T % 2, x)
    np.testing.assert_array_equal(full0[:, 3], full1[:, 3])
    np.testing.assert_array_equal(full0 @ decoder.x_model.past % 2, diag.baseline_past)
    np.testing.assert_array_equal(full0 @ decoder.x_model.future % 2, diag.baseline_future)
    np.testing.assert_array_equal(full1 @ decoder.x_model.past % 2, diag.baseline_past ^ True)
    np.testing.assert_array_equal(full1 @ decoder.x_model.future % 2, diag.baseline_future ^ True)
    np.testing.assert_array_equal(full0 @ decoder.x_model.weights, result.baseline_weight)
    np.testing.assert_array_equal(full1 @ decoder.x_model.weights, result.complementary_weight)
    zfull = decoder.z_model.expand_errors(diag.z_errors)
    np.testing.assert_array_equal(zfull @ decoder.z_model.feature_map.T % 2,
                                  np.hstack([result.tau_z_prediction, result.logical_z_prediction]))


@pytest.mark.parametrize("mode", ["compact", "full_witness"])
def test_batch_single_cached_graphs_no_dem_parsing_or_quantization_during_decode(monkeypatch, mode):
    decoder = synthetic(mode=mode)
    x = np.array([[0], [0], [1], [1]], dtype=bool)
    z = np.array([[0], [1], [0], [1]], dtype=bool)
    before_x, before_z = x.copy(), z.copy()
    def forbidden(*args, **kwargs):
        pytest.fail("decode must reuse static graphs and prequantized costs")
    import pymatching
    import knill_bench.decoding.temporal_dem as dem_module
    monkeypatch.setattr(stim, "DetectorErrorModel", forbidden)
    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", forbidden)
    monkeypatch.setattr(dem_module, "bernoulli_integer_weights", forbidden)
    batched = decoder.decode_batch(x, z)
    for name in ("tau_x_prediction", "tau_z_prediction", "logical_z_prediction", "baseline_weight",
                 "complementary_weight", "gap", "baseline_valid", "complementary_valid", "z_decoder_valid", "status"):
        singles = np.concatenate([getattr(decoder.decode_one(a, b), name) for a, b in zip(x, z)])
        np.testing.assert_array_equal(getattr(batched, name), singles)
    np.testing.assert_array_equal(x, before_x)
    np.testing.assert_array_equal(z, before_z)
    empty = decoder.decode_batch(x[:0], z[:0])
    assert empty.gap.shape == (0,) and empty.tau_x_prediction.shape == (0, 1)
    assert (batched.debug is None) == (mode == "compact")


def test_output_mode_and_frame_are_part_of_definition_and_no_terminal_recovery_is_implied():
    compact, full = synthetic(), synthetic(mode="full_witness")
    assert compact.model_sha256 != full.model_sha256
    assert compact.metadata["definition"]["output_mode"] == "compact"
    assert full.metadata["definition"]["logical_evaluation"] == "prefix_frame_only"
    assert not full.metadata["definition"]["physical_correction_applied"]
    with pytest.raises(AttributeError):
        compact.output_mode = "full_witness"
    with pytest.raises(AttributeError):
        compact.weight_scale = 2
    with pytest.raises(PreparationCapabilityError, match="separate protocol"):
        TemporalGapDecoder(compact.x_model, compact.z_model, logical_evaluation="terminal_recovery")
    assert tuple(inspect.signature(compact.decode_batch).parameters) == ("online_x_detectors", "online_z_detectors")
    assert not any(isinstance(v, stim.Circuit) for v in vars(compact).values())


def test_full_mode_reports_a_different_valid_equal_cost_tie_without_attaching_it_to_compact(monkeypatch):
    xdem = "error(.2) D0 D1 L0\nerror(.2) D1 D2"
    compact, full = synthetic(xdem=xdem), synthetic(xdem=xdem, mode="full_witness")
    shot = np.ones((1, 1), dtype=bool)
    base = compact.decode_batch(shot, shot)
    # Supply another VALID optimum through the debug backend, independently
    # of whichever tied solution the native compact call happened to choose.
    alternative = 1 if base.tau_x_prediction[0, 0] else 0
    class OtherOptimum:
        def decode_batch(self, padded, **kwargs):
            errors = np.zeros((len(padded), 2), dtype=np.uint8)
            errors[:, alternative] = padded[:, 0]
            return errors, padded[:, 0].astype(float)
    monkeypatch.setattr(full.x_core._baseline, "_debug_matcher", OtherOptimum())
    result = full.decode_batch(shot, shot)
    assert not result.debug.debug_matches_compact[0]
    assert result.tau_x_prediction[0, 0] != base.tau_x_prediction[0, 0]
    np.testing.assert_array_equal(result.debug.baseline_errors @ full.x_core.feature_map.T % 2,
                                  result.tau_x_prediction)
    assert result.baseline_weight[0] == base.baseline_weight[0] == 1


def test_packed_little_endian_has_explicit_api_and_rejects_padding():
    decoder = synthetic()
    values = np.array([[0], [1]], dtype=bool)
    packed = np.packbits(values, axis=1, bitorder="little")
    a, b = decoder.decode_batch(values, values), decoder.decode_packed_batch(packed, packed)
    np.testing.assert_array_equal(a.gap, b.gap)
    np.testing.assert_array_equal(a.logical_z_prediction, b.logical_z_prediction)
    with pytest.raises(ValueError, match="padding"):
        decoder.decode_packed_batch(packed | 128, packed)
    with pytest.raises(ValueError, match="bool ndarray"):
        decoder.decode_batch(packed, packed)
    with pytest.raises(ValueError, match="packed detectors"):
        decoder.decode_packed_batch(packed.astype(bool), packed)


def test_unavailable_complement_and_invalid_z_keep_independent_valid_baselines():
    decoder = synthetic(xdem="error(0) D0 D1 L0\nerror(.2) D1 D2 L0")
    values = np.array([[0], [1]], dtype=bool)
    pred = decoder.decode_batch(values, values)
    assert pred.status.tolist() == ["no_complementary_solution"] * 2
    assert pred.baseline_valid.all() and pred.z_decoder_valid.all()
    assert np.isnan(pred.gap).all() and not preparation_acceptance(pred).any()
    # A Z row with no active incident edge is independently unmatchable.
    zempty = "detector D0\nlogical_observable L0\nlogical_observable L1"
    other = synthetic(zdem=zempty)
    result = other.decode_batch(values, values)
    assert result.status.tolist() == ["ok", "z_decoder_invalid"]
    assert result.complementary_valid.all() and result.baseline_valid.all()
    assert result.z_decoder_valid.tolist() == [True, False]
    assert preparation_acceptance(result).tolist() == [True, False]


@pytest.mark.parametrize("d,r", [(3, 1), (3, 2), (3, 3), (5, 2), (5, 3)])
@pytest.mark.parametrize("mode", ["compact", "full_witness"])
def test_actual_native_noiseless_preparation_with_positive_nominal_model(d, r, mode):
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=d, rounds=r, p=0, decoding_p=.003))
    decoder = prepare_preparation_decoder(compiled, output_mode=mode)
    det, obs = compiled.circuit.compile_detector_sampler(seed=617).sample(3, separate_observables=True)
    batch = split_preparation_samples(compiled, det, obs)
    prediction = decoder.decode_batch(batch.observations.online_x_detectors, batch.observations.online_z_detectors)
    assert np.isfinite(prediction.gap).all() and (prediction.status == "ok").all()
    evaluation = evaluate_preparation(batch.truth, prediction)
    assert not evaluation.code_space_miss.any() and not evaluation.logical_z_error.any()
    assert all(r.sector == "z" and r.role.value == "online" for r in compiled.detectors if r.detector_id in decoder.z_model.detector_ids)
    assert len(decoder.z_model.detector_ids) == r * len(compiled.labels.tau_z)
    assert decoder.z_model.metadata["scope"] == "known_zero_Z_prefix_v1"
    before = prediction.gap.copy(), prediction.logical_z_prediction.copy()
    changed_truth = PreparationTruth(~batch.truth.tau_x, ~batch.truth.tau_z, ~batch.truth.logical_z)
    changed = decoder.decode_batch(batch.observations.online_x_detectors, batch.observations.online_z_detectors)
    np.testing.assert_array_equal(before[0], changed.gap)
    np.testing.assert_array_equal(before[1], changed.logical_z_prediction)
    assert evaluate_preparation(changed_truth, changed).sign_miss_x.all()
    if mode == "full_witness":
        e0 = decoder.x_model.expand_errors(prediction.debug.baseline_errors)
        e1 = decoder.x_model.expand_errors(prediction.debug.complementary_errors)
        np.testing.assert_array_equal(e0 @ decoder.x_model.h_online.T % 2, batch.observations.online_x_detectors)
        np.testing.assert_array_equal(e1[:, decoder.x_model.frozen_columns], e0[:, decoder.x_model.frozen_columns])


def test_actual_zero_nominal_model_does_not_invent_a_gap_or_erase_baseline_statistics():
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=2, p=0))
    decoder = prepare_preparation_decoder(compiled)
    pred = decoder.decode_batch(np.zeros((3, 4), dtype=bool), np.zeros((3, 8), dtype=bool))
    truth = PreparationTruth(*(np.zeros((3, 4 if i < 2 else 1), dtype=bool) for i in range(3)))
    summary = summarize_preparation(evaluate_preparation(truth, pred))
    assert summary["accepted"] == 0 and summary["invalid_reasons"]["no_complement"] == 3
    assert summary["unconditional"]["code_space"]["shots"] == 3
    assert summary["selected"]["code_space"]["rate"] is None


@pytest.mark.parametrize("pauli", ["X", "Z", "Y"])
def test_native_terminal_pauli_faults_separate_x_sign_z_sign_and_logical_z(pauli):
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=2, p=0, decoding_p=.003))
    decoder = prepare_preparation_decoder(compiled)
    code = Code.rotated(3)
    q = int(code.matrices[3].getrow(0).indices[0])
    cut = compiled.output_cut.instruction_count
    circuit = compiled.circuit[:cut] + stim.Circuit(f"{pauli}_ERROR(1) {q}") + compiled.circuit[cut:]
    det, obs = circuit.compile_detector_sampler(seed=74).sample(3, separate_observables=True)
    assert not det.any()  # Terminal data errors are outside observed prefix.
    batch = split_preparation_samples(compiled, det, obs)
    pred = decoder.decode_batch(batch.observations.online_x_detectors, batch.observations.online_z_detectors)
    ev = evaluate_preparation(batch.truth, pred)
    np.testing.assert_array_equal(ev.error_bits_x, np.tile(code.matrices[0].toarray()[:, q].astype(bool)
        if pauli in {"Z", "Y"} else np.zeros(len(compiled.labels.tau_x), dtype=bool), (3, 1)))
    np.testing.assert_array_equal(ev.error_bits_z, np.tile(code.matrices[1].toarray()[:, q].astype(bool)
        if pauli in {"X", "Y"} else np.zeros(len(compiled.labels.tau_z), dtype=bool), (3, 1)))
    assert ev.logical_z_error.tolist() == [pauli in {"X", "Y"}] * 3
    assert ev.code_space_miss.all() and ev.eligible.all()


def test_z_prefix_model_rejects_missing_initial_anchor_and_terminal_record_input():
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=2, p=0))
    rows = list(compiled.detectors)
    first = next(i for i, r in enumerate(rows) if r.sector == "z")
    with pytest.raises(PreparationCapabilityError, match="initial anchor"):
        compile_preparation_prefix_model(replace(compiled, detectors=tuple(rows[:first] + rows[first + 1:])))
    record = next(r.record_id for r in compiled.ledger if r.source == "destructive_z")
    rows[first] = replace(rows[first], record_ids=(record,))
    with pytest.raises(PreparationCapabilityError, match="non-prefix"):
        compile_preparation_prefix_model(replace(compiled, detectors=tuple(rows)))


@pytest.mark.parametrize("sector", ["x", "z"])
def test_actual_middle_readout_fault_has_known_temporal_response_and_no_output_error(sector):
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=3, p=0, decoding_p=.003))
    decoder = prepare_preparation_decoder(compiled)
    record = next(r.record_id for r in compiled.ledger if r.source == "se" and r.sector == sector
                  and r.round_index == 2 and r.check_index == 0)
    index = next(i for i in range(len(compiled.circuit)) if compiled.circuit[:i + 1].num_measurements > record)
    op = compiled.circuit[index]
    assert op.name == "MR"
    start = compiled.circuit[:index].num_measurements
    replacement = stim.Circuit()
    for j, target in enumerate(op.targets_copy()):
        replacement.append("MR", [target], int(start + j == record))
    circuit = compiled.circuit[:index] + replacement + compiled.circuit[index + 1:]
    det, obs = circuit.compile_detector_sampler(seed=17).sample(3, separate_observables=True)
    expected = np.array([r.sector == sector and r.check_index == 0 and r.round_index in {2, 3}
                         for r in compiled.detectors], dtype=bool)
    np.testing.assert_array_equal(det, np.tile(expected, (3, 1)))
    assert not obs.any()  # Intermediate flip never reaches final tau/readout.
    batch = split_preparation_samples(compiled, det, obs)
    pred = decoder.decode_batch(batch.observations.online_x_detectors, batch.observations.online_z_detectors)
    assert not pred.tau_x_prediction.any() and not pred.tau_z_prediction.any() and not pred.logical_z_prediction.any()
    assert not evaluate_preparation(batch.truth, pred).code_space_miss.any()


def test_actual_noisy_batch_full_witnesses_match_original_syndromes_costs_and_independent_Z_features():
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=2, p=.01))
    decoder = prepare_preparation_decoder(compiled, output_mode="full_witness")
    det, obs = compiled.circuit.compile_detector_sampler(seed=716).sample(7, separate_observables=True)
    batch = split_preparation_samples(compiled, det, obs)
    pred = decoder.decode_batch(batch.observations.online_x_detectors, batch.observations.online_z_detectors)
    e0 = decoder.x_model.expand_errors(pred.debug.baseline_errors)
    e1 = decoder.x_model.expand_errors(pred.debug.complementary_errors)
    np.testing.assert_array_equal(e0 @ decoder.x_model.h_online.T % 2, batch.observations.online_x_detectors)
    np.testing.assert_array_equal(e1 @ decoder.x_model.h_online.T % 2, batch.observations.online_x_detectors)
    np.testing.assert_array_equal(e0 @ decoder.x_model.weights, pred.baseline_weight)
    np.testing.assert_array_equal(e1 @ decoder.x_model.weights, pred.complementary_weight)
    assert np.array_equal(e0[:, decoder.x_model.frozen_columns], e1[:, decoder.x_model.frozen_columns])
    z = decoder.z_model.expand_errors(pred.diagnostics.z_errors)
    np.testing.assert_array_equal(z @ decoder.z_model.h.T % 2, batch.observations.online_z_detectors)
    np.testing.assert_array_equal(z @ decoder.z_model.feature_map.T % 2,
                                  np.hstack([pred.tau_z_prediction, pred.logical_z_prediction]))
    for i in range(7):
        single = decoder.decode_one(batch.observations.online_x_detectors[i], batch.observations.online_z_detectors[i])
        for name in ("tau_x_prediction", "logical_z_prediction", "baseline_weight", "complementary_weight", "gap", "status"):
            np.testing.assert_array_equal(getattr(pred, name)[i:i + 1], getattr(single, name))


def test_empty_X_packed_sector_and_invalid_input_dimensions():
    compiled = build_preparation(dict(protocol="surface_prep_fixed", distance=3, rounds=1, p=0, decoding_p=.003))
    decoder = prepare_preparation_decoder(compiled)
    pred = decoder.decode_packed_batch(np.empty((3, 0), dtype=np.uint8), np.zeros((3, 1), dtype=np.uint8))
    assert (pred.status == "ok").all()
    with pytest.raises(ValueError, match="dimensions"):
        decoder.decode_batch(np.zeros((3, 1), dtype=bool), np.zeros((3, 4), dtype=bool))
    with pytest.raises(ValueError, match="equal shot"):
        decoder.decode_batch(np.empty((2, 0), dtype=bool), np.zeros((3, 4), dtype=bool))
    with pytest.raises(ValueError, match="one-dimensional"):
        decoder.decode_one(np.empty((1, 0), dtype=bool), np.zeros((1, 4), dtype=bool))


def test_incompatible_static_models_fail_before_matching_construction(monkeypatch):
    decoder = synthetic()
    import pymatching
    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", lambda *a, **k: pytest.fail("unexpected graph setup"))
    with pytest.raises(ValueError, match="weight_scale"):
        TemporalGapDecoder(decoder.x_model, replace(decoder.z_model, weight_scale=2))
    with pytest.raises(ValueError, match="different nominal"):
        TemporalGapDecoder(decoder.x_model, replace(decoder.z_model,
            provenance_json='{"model_hashes":{"model_circuit":"other"}}'))
    with pytest.raises(PreparationCapabilityError, match="known-initial"):
        TemporalGapDecoder(decoder.x_model, replace(decoder.z_model, scope="terminal_closed"))
    with pytest.raises(ValueError, match="output_mode"):
        TemporalGapDecoder(decoder.x_model, decoder.z_model, output_mode="other")
    with pytest.raises(ValueError, match="tau_x"):
        TemporalGapDecoder(replace(decoder.x_model, feature_ids=("other",)), decoder.z_model)
