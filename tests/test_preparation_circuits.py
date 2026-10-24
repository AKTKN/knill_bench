"""Fixed-R native physics and evaluator contracts; all new batches <=7 shots."""

from dataclasses import fields
import hashlib
import json

import numpy as np
import pytest
import stim

from hex_qec.circuit_generation.circuit_generation import (
    qubit_initialisation, measure_X_stabilizers_surface_code, measure_Z_stabilizers_surface_code,
)
from knill_bench.circuits.builders import build
from knill_bench.circuits.preparation import build_preparation
from knill_bench.codes import Code
from knill_bench.decoding.temporal_dem import completed_dem_to_temporal_model
from knill_bench.decoding.temporal_matching import TemporalMatching
from knill_bench.preparation import (
    DetectorRole, PreparationCapabilityError, PreparationObservations, split_preparation_samples,
)


def case(d=3, r=3, p=0, **kwargs):
    result = dict(protocol="surface_prep_fixed", distance=d, rounds=r, p=p)
    result.update(kwargs)
    return result


@pytest.fixture(scope="module")
def ideal():
    return build_preparation(case())


def _without_detectors(circuit):
    out = stim.Circuit()
    for op in circuit:
        if op.name != "DETECTOR":
            out.append(op)
    return out


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("rounds", [2, 3, 4, 5])
def test_exact_native_prefix_signed_flows_and_ideal_evaluation(distance, rounds):
    compiled = build(case(distance, rounds, .001))
    code = Code.rotated(distance)
    nx, nz = (m.shape[0] for m in code.matrices[:2])
    block = code.blocks(1)[0]
    expected = stim.Circuit()
    qubit_initialisation(expected, "z", block, .001)
    for _ in range(rounds):
        measure_X_stabilizers_surface_code(expected, code.stabilizers[0], block, .001)
        measure_Z_stabilizers_surface_code(expected, code.stabilizers[1], block, .001)
    assert _without_detectors(compiled.physical_prefix) == expected
    assert compiled.physical_prefix == compiled.circuit[:compiled.output_cut.instruction_count]
    assert compiled.output_cut.measurement_count == rounds * (nx + nz)
    assert compiled.circuit.num_measurements == rounds * (nx + nz) + nx + distance**2
    assert compiled.completed_circuit.num_measurements == rounds * (nx + nz) + 2 * nx + distance**2
    assert len(compiled.online_x_detector_ids) == (rounds - 1) * nx
    assert len(compiled.online_z_detector_ids) == rounds * nz
    assert all(d.role == DetectorRole.ONLINE for d in compiled.detectors)
    assert all(d.round_index != 1 for d in compiled.detectors if d.sector == "x")
    assert sum(d.role == DetectorRole.PAST for d in compiled.completed_detectors) == nx
    assert sum(d.role == DetectorRole.FUTURE for d in compiled.completed_detectors) == nx
    assert len(compiled.completed_detectors) == (rounds + 1) * nx
    assert all(d.sector == "x" for d in compiled.completed_detectors)
    assert tuple(r.record_id for r in compiled.ledger) == tuple(range(compiled.circuit.num_measurements))
    assert tuple(r.record_id for r in compiled.completed_ledger) == tuple(range(compiled.completed_circuit.num_measurements))
    suffix = compiled.circuit[compiled.output_cut.instruction_count:]
    assert {op.name for op in suffix} == {"MPP", "M", "OBSERVABLE_INCLUDE"}
    assert not any(r.source == "past_x_probe" for r in compiled.ledger)
    first_completed_se = min(r.record_id for r in compiled.completed_ledger if r.source == "se")
    assert first_completed_se == nx
    for circuit, detectors, observables in (
            (compiled.circuit, compiled.detectors, compiled.observables),
            (compiled.completed_circuit, compiled.completed_detectors, compiled.completed_observables)):
        assert circuit.without_noise().has_all_flows(
            [stim.Flow(measurements=r.record_ids) for r in (*detectors, *observables)])
    d, o = compiled.circuit.without_noise().compile_detector_sampler(seed=51).sample(7, separate_observables=True)
    assert not d.any() and not o.any()
    metadata = compiled.metadata
    assert metadata["physical_se_rounds"] == rounds
    assert metadata["physical_qubits"] == 2 * distance**2 - 1
    assert metadata["evaluation_measurements"] == nx + distance**2
    assert metadata["offline_past_probes"] == nx
    assert not metadata["physical_correction_applied"] and not metadata["terminal_recovery"]
    assert not metadata["offline_completion_sampled"] and metadata["logical_evaluation"] == "prefix_frame_only"
    json.dumps(metadata, allow_nan=False)
    assert all(len(value) == 64 for _, value in compiled.source_hashes + compiled.model_hashes)


def test_first_x_is_random_but_tau_and_logical_z_are_deterministic(ideal):
    raw = ideal.circuit.compile_sampler(seed=123).sample(7)
    first_x = [r.record_id for r in ideal.ledger if r.source == "se" and r.sector == "x" and r.round_index == 1]
    assert not ideal.circuit.has_flow(stim.Flow(measurements=[first_x[0]]))
    assert np.any(raw[:, first_x].std(axis=0) > 0)
    last_x = [r.record_id for r in ideal.ledger if r.source == "se" and r.sector == "x" and r.round_index == 3]
    probe_x = [r.record_id for r in ideal.ledger if r.source == "output_x_probe"]
    np.testing.assert_array_equal(raw[:, last_x], raw[:, probe_x])
    reference = ideal.circuit.reference_sample()
    assert np.any(raw[:, probe_x] != reference[probe_x])  # Negative control, not a logical error.
    det, obs = ideal.circuit.compile_m2d_converter().convert(measurements=raw, separate_observables=True)
    batch = split_preparation_samples(ideal, det, obs)
    assert not batch.truth.tau_x.any() and not batch.truth.tau_z.any() and not batch.truth.logical_z.any()
    first_z = [r.record_id for r in ideal.ledger if r.source == "se" and r.sector == "z" and r.round_index == 1]
    assert all(ideal.circuit.has_flow(stim.Flow(measurements=[r])) for r in first_z)


def _after_record(circuit, record):
    for i in range(len(circuit)):
        if circuit[:i + 1].num_measurements > record:
            return i + 1
    raise AssertionError("missing test injection record")


def _inject(circuit, cut, pauli, qubit):
    fault = stim.Circuit()
    fault.append(pauli + "_ERROR", [qubit], 1)
    return circuit[:cut] + fault + circuit[cut:]


def _flip_readout(circuit, record):
    index = _after_record(circuit, record) - 1
    op = circuit[index]
    assert op.name == "MR"
    start = circuit[:index].num_measurements
    replacement = stim.Circuit()
    for j, target in enumerate(op.targets_copy()):
        replacement.append("MR", [target], int(start + j == record))
    return circuit[:index] + replacement + circuit[index + 1:]


def _sample(compiled, circuit):
    d, o = circuit.compile_detector_sampler(seed=71).sample(3, separate_observables=True)
    return d, split_preparation_samples(compiled, d, o).truth


@pytest.mark.parametrize("sector,round_index", [("x", 1), ("x", 3), ("z", 1), ("z", 3)])
def test_first_and_last_readout_flips_have_independent_expected_parities(ideal, sector, round_index):
    record = next(r.record_id for r in ideal.ledger if
                  r.source == "se" and r.sector == sector and r.round_index == round_index and r.check_index == 0)
    d, truth = _sample(ideal, _flip_readout(ideal.circuit, record))
    expected = np.zeros(d.shape[1], dtype=bool)
    # One record participates in the known-Z initial comparison (if applicable)
    # and in each adjacent temporal difference, never a standalone random X row.
    for row in ideal.detectors:
        expected[row.detector_id] = row.sector == sector and row.check_index == 0 and (
            row.round_index == round_index or row.round_index == round_index + 1)
    np.testing.assert_array_equal(d, np.tile(expected, (3, 1)))
    for a in ("x", "z"):
        expected_tau = np.zeros_like(getattr(truth, "tau_" + a))
        if a == sector and round_index == 3:
            expected_tau[:, 0] = True
        np.testing.assert_array_equal(getattr(truth, "tau_" + a), expected_tau)
    assert not truth.logical_z.any()


@pytest.mark.parametrize("round_index", [1, 3])
def test_data_z_between_x_and_z_extraction_including_invisible_output_tail(ideal, round_index):
    code = Code.rotated(3)
    q = int(code.matrices[0].getrow(0).indices[0])
    last = max(r.record_id for r in ideal.ledger if r.source == "se" and r.sector == "x" and r.round_index == round_index)
    d, truth = _sample(ideal, _inject(ideal.circuit, _after_record(ideal.circuit, last), "Z", q))
    syndrome = code.matrices[0].toarray()[:, q].astype(bool)
    expected = np.zeros(d.shape[1], dtype=bool)
    for row in ideal.detectors:
        if row.sector == "x" and row.round_index == round_index + 1:
            expected[row.detector_id] = syndrome[row.check_index]
    np.testing.assert_array_equal(d, np.tile(expected, (3, 1)))
    expected_tau = np.tile(syndrome if round_index == 3 else np.zeros_like(syndrome), (3, 1))
    np.testing.assert_array_equal(truth.tau_x, expected_tau)
    assert not truth.tau_z.any() and not truth.logical_z.any()
    if round_index == 3:
        assert not d[:, ideal.online_x_detector_ids].any() and truth.tau_x.any()


def test_space_time_corner_y_fault_has_both_sector_and_logical_effects(ideal):
    code = Code.rotated(3)
    q = int(code.matrices[3].getrow(0).indices[0])
    record = max(r.record_id for r in ideal.ledger if r.source == "se" and r.sector == "x" and r.round_index == 3)
    d, truth = _sample(ideal, _inject(ideal.circuit, _after_record(ideal.circuit, record), "Y", q))
    hx = code.matrices[0].toarray()[:, q].astype(bool)
    hz = code.matrices[1].toarray()[:, q].astype(bool)
    expected = np.zeros(d.shape[1], dtype=bool)
    for row in ideal.detectors:
        if row.sector == "z" and row.round_index == 3:
            expected[row.detector_id] = hz[row.check_index]
    np.testing.assert_array_equal(d, np.tile(expected, (3, 1)))
    np.testing.assert_array_equal(truth.tau_x, np.tile(hx, (3, 1)))
    assert not truth.tau_z.any() and truth.logical_z.all()


def test_terminal_x_fault_and_single_software_frame_convention(ideal):
    code = Code.rotated(3)
    q = int(code.matrices[3].getrow(0).indices[0])
    cut = ideal.output_cut.instruction_count
    injected = _inject(ideal.circuit, cut, "X", q)
    d, truth = _sample(ideal, injected)
    assert not d.any() and not truth.tau_x.any()
    np.testing.assert_array_equal(truth.tau_z, np.tile(code.matrices[1].toarray()[:, q].astype(bool), (3, 1)))
    assert truth.logical_z.all()
    prediction = np.ones_like(truth.logical_z)
    assert not (truth.logical_z ^ prediction).any()  # Software frame, exactly once.
    double_corrected = _inject(injected, cut, "X", q)
    _, physically_corrected_truth = _sample(ideal, double_corrected)
    assert not physically_corrected_truth.logical_z.any()
    assert (physically_corrected_truth.logical_z ^ prediction).all()  # Negative double-application control.


def _projected_signature(dem, selected_detectors):
    # Validation-only marginalization. This never constructs the inference graph.
    mapping = {d: i for i, d in enumerate(selected_detectors)}
    products = {}
    for op in dem.flattened():
        if op.type != "error":
            continue
        detector, labels = set(), set()
        for target in op.targets_copy():
            assert not target.is_separator()
            if target.is_relative_detector_id() and target.val in mapping:
                detector.symmetric_difference_update([mapping[target.val]])
            elif target.is_logical_observable_id():
                labels.symmetric_difference_update([target.val])
        key = (tuple(sorted(detector)), tuple(sorted(labels)))
        if any(key):
            products[key] = products.get(key, 1.) * (1 - 2 * op.args_copy()[0])
    return {key: (1 - product) / 2 for key, product in products.items()}


@pytest.mark.parametrize("distance,rounds", [(3, 2), (3, 3), (5, 2), (5, 5)])
def test_current_pin_production_and_completed_same_sector_marginals(distance, rounds):
    compiled = build_preparation(case(distance, rounds, .003))
    a = _projected_signature(compiled.model_dem, compiled.online_x_detector_ids)
    online = [row.detector_id for row in compiled.completed_detectors if row.role == DetectorRole.ONLINE]
    b = _projected_signature(compiled.completed_dem, online)
    assert a.keys() == b.keys()
    assert max(abs(a[key] - b[key]) for key in a) < 1e-13


def test_physical_samples_and_hashes_are_independent_of_nominal_decoding_noise():
    physical = build_preparation(case(p=0))
    noisy_model = build_preparation(case(p=0, decoding_p=.003))
    assert physical.circuit == noisy_model.circuit and physical.physical_prefix == noisy_model.physical_prefix
    assert noisy_model.decoding_probability == .003 and noisy_model.physical_probability == 0
    assert noisy_model.model_circuit != noisy_model.circuit
    assert len(noisy_model.completed_dem) > len(physical.completed_dem)
    assert dict(physical.model_hashes)["production_circuit"] == dict(noisy_model.model_hashes)["production_circuit"]
    assert dict(physical.model_hashes)["completed_dem"] != dict(noisy_model.model_hashes)["completed_dem"]
    a = physical.circuit.compile_detector_sampler(seed=9).sample(3, separate_observables=True)
    b = noisy_model.circuit.compile_detector_sampler(seed=9).sample(3, separate_observables=True)
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


def test_real_sampler_truth_is_detached_and_cannot_change_kernel_predictions():
    compiled = build_preparation(case(p=.001))
    d, o = compiled.circuit.compile_detector_sampler(seed=31).sample(7, separate_observables=True)
    batch = split_preparation_samples(compiled, d, o)
    assert {f.name for f in fields(PreparationObservations)} == {"online_x_detectors", "online_z_detectors"}
    model = completed_dem_to_temporal_model(compiled.completed_dem,
        detector_roles=[row.role for row in compiled.completed_detectors], num_observables=compiled.circuit.num_observables)
    core = TemporalMatching(**model.matching_kwargs())
    a = core.decode_batch(batch.observations.online_x_detectors)
    o[:] ^= True
    changed = split_preparation_samples(compiled, d, o)
    b = core.decode_batch(changed.observations.online_x_detectors)
    for name in ("baseline_features", "complementary_features", "gaps", "status"):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))
    assert not np.shares_memory(batch.observations.online_x_detectors, d)
    assert not np.shares_memory(batch.truth.tau_x, o)
    with pytest.raises(ValueError, match="detector count"):
        split_preparation_samples(compiled, d[:, :-1], o)
    with pytest.raises(ValueError, match="observable count"):
        split_preparation_samples(compiled, d, o[:, :-1])


@pytest.mark.parametrize("change", [dict(rounds="d"), dict(rounds=0), dict(rounds=True),
    dict(adaptive=True), dict(readout_basis="x"), dict(logical_evaluation="terminal_recovery"),
    dict(noise={"profile": "explicit"}), dict(code="color"), dict(cycles=3), dict(decoding_p=.5),
    dict(T_tel=1), dict(oracle_cut="last_x_readout"), dict(p=2**2048), dict(decoding_p=2**2048)])
def test_unsupported_or_malformed_preparation_fails_before_geometry(monkeypatch, change):
    monkeypatch.setattr(Code, "rotated", lambda *a: pytest.fail("geometry must not be constructed"))
    with pytest.raises(ValueError):
        build_preparation(case(**change))


def test_changed_native_instrument_raises_capability_error(monkeypatch):
    import knill_bench.circuits.preparation as module
    native = module.measure_X_stabilizers_surface_code
    def wrong_sign(circuit, stabilizers, block, p):
        native(circuit, stabilizers, block, p)
        circuit.append("Z", [block["data_qubits"][0]])
    monkeypatch.setattr(module, "measure_X_stabilizers_surface_code", wrong_sign)
    with pytest.raises(PreparationCapabilityError, match="nondemolition"):
        build_preparation(case())


def test_unapproved_native_noise_is_rejected_even_when_ideal_flows_are_valid(monkeypatch):
    import knill_bench.circuits.preparation as module
    native = module.measure_X_stabilizers_surface_code
    def extra_noise(circuit, stabilizers, block, p):
        native(circuit, stabilizers, block, p)
        if p:
            circuit.append("DEPOLARIZE1", [block["data_qubits"][0]], p)
    monkeypatch.setattr(module, "measure_X_stabilizers_surface_code", extra_noise)
    with pytest.raises(PreparationCapabilityError, match="DEPOLARIZE1"):
        build_preparation(case(p=.001))


def test_native_noise_probabilities_must_match_declared_uniform_p(monkeypatch):
    import knill_bench.circuits.preparation as module
    native = module.measure_X_stabilizers_surface_code
    def wrong_probability(circuit, stabilizers, block, p):
        native(circuit, stabilizers, block, p)
        if p:
            circuit.append("Z_ERROR", [block["data_qubits"][0]], 2 * p)
    monkeypatch.setattr(module, "measure_X_stabilizers_surface_code", wrong_probability)
    with pytest.raises(PreparationCapabilityError, match="declared p"):
        build_preparation(case(p=.001))


def test_dem_extraction_keeps_all_strict_options_and_surfaces_capability_errors(monkeypatch):
    native = stim.Circuit.detector_error_model
    calls = []
    def inspected(circuit, **kwargs):
        calls.append(kwargs)
        return native(circuit, **kwargs)
    monkeypatch.setattr(stim.Circuit, "detector_error_model", inspected)
    build_preparation(case())
    assert calls == [dict(decompose_errors=False, allow_gauge_detectors=False, approximate_disjoint_errors=False)] * 2
    def unsupported(*args, **kwargs):
        raise ValueError("unsupported diagnostic channel")
    monkeypatch.setattr(stim.Circuit, "detector_error_model", unsupported)
    with pytest.raises(PreparationCapabilityError, match="unsupported diagnostic channel"):
        build_preparation(case())


def test_compilation_never_samples_or_constructs_a_terminal_decoder(monkeypatch):
    import pymatching
    def forbidden(*args, **kwargs):
        pytest.fail("circuit compilation must not sample, decode, or construct matching")
    for name in ("compile_sampler", "compile_detector_sampler"):
        monkeypatch.setattr(stim.Circuit, name, forbidden)
    for name in ("from_check_matrix", "from_detector_error_model", "decode", "decode_batch"):
        monkeypatch.setattr(pymatching.Matching, name, forbidden)
    compiled = build_preparation(case(p=.001))
    assert not compiled.metadata["terminal_recovery"]


def test_legacy_memory_native_circuit_golden_is_unchanged():
    compiled = build(dict(protocol="se_memory", distance=3, basis="z", cycles=2, p=.001,
        prep_rounds=0, post_gate_rounds=0, post_gate_scope="all_active", noise={"profile": "hex_legacy"},
        initial_boundary={"kind": "noisy_preparation"}))
    # Generated at prompt-00 checkpoint using the unchanged legacy builder.
    assert hashlib.sha256(str(compiled.circuit).encode()).hexdigest() == "1c5706d386c7089b0fbe71a9949e32a77244cce99c77772f9df801eeb6c74a9d"
