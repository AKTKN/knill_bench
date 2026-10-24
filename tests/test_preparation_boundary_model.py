"""Native circuit certification and independent single readout/Pauli responses.

No production sampling: every injected circuit has one explicit independent
fault, whose expected check/time/label response is derived below by hand.
"""

from dataclasses import replace
import json

import numpy as np
import pytest
import stim

from knill_bench.circuits.preparation import build_preparation
from knill_bench.codes import Code
from knill_bench.decoding.preparation_model import compile_preparation_boundary_model
from knill_bench.decoding.temporal_artifact import read_temporal_model, write_temporal_model
from knill_bench.decoding.temporal_dem import completed_dem_to_temporal_model
from knill_bench.decoding.temporal_matching import TemporalMatching
from knill_bench.decoding.temporal_validation import compare_marginal_models
from knill_bench.preparation import DetectorRole, PreparationCapabilityError


def build(d=3, r=2, p=0, **kw):
    return build_preparation(dict(protocol="surface_prep_fixed", distance=d, rounds=r, p=p, **kw))


@pytest.mark.parametrize("distance,rounds", [(3, 1), (3, 2), (3, 3), (5, 2), (5, 5)])
@pytest.mark.parametrize("p", [0, .003])
def test_native_model_certifies_exact_same_outputs_and_roundtrips(distance, rounds, p, tmp_path):
    compiled = build(distance, rounds, p)
    model = compile_preparation_boundary_model(compiled)
    certificate = model.metadata["provenance"]["marginal_certificate"]
    assert certificate["max_probability_difference"] < 1e-14
    assert certificate["signatures"] > 0 if p else certificate["signatures"] == 0
    assert model.feature_ids == tuple(r.metric if r.check_index is None else f"{r.metric}:{r.check_index}"
                                      for r in compiled.completed_observables)
    assert model.h_online.shape[0] == len(compiled.online_x_detector_ids)
    path = tmp_path / "X_boundary.json"
    digest = write_temporal_model(path, model)
    restored = read_temporal_model(path, expected_sha256=digest)
    result = TemporalMatching(**restored.matching_kwargs()).decode_batch(
        np.zeros((3, model.h_online.shape[0]), dtype=bool), return_errors=True)
    assert not result.baseline_features.any()
    assert restored.to_artifact() == model.to_artifact()
    json.dumps(model.metadata, allow_nan=False)


def test_nominal_comparison_uses_decode_probability_and_compilation_never_samples_or_matches(monkeypatch):
    compiled = build(p=0, decoding_p=.003)
    def forbidden(*args, **kw):
        pytest.fail("boundary compilation must not sample or construct matching graphs")
    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    monkeypatch.setattr(stim.Circuit, "compile_detector_sampler", forbidden)
    monkeypatch.setattr(TemporalMatching, "__init__", forbidden)
    model = compile_preparation_boundary_model(compiled)
    assert model.num_mechanisms > 0
    assert model.metadata["provenance"]["decoding_p"] == .003
    assert model.metadata["provenance"]["completion_certified"]
    assert len(model.metadata["provenance"]["boundary_source_hashes"]) == 3


@pytest.mark.parametrize("change", ["labels", "rows", "probability", "strip_eval"])
def test_certification_rejects_wrong_maps_or_completed_model(change):
    compiled = build(p=.003)
    if change == "labels":
        compiled = replace(compiled, completed_observables=tuple(reversed(compiled.completed_observables)))
    elif change == "rows":
        rows = list(compiled.completed_detectors)
        i = next(i for i, r in enumerate(rows) if r.role == DetectorRole.ONLINE)
        rows[i] = replace(rows[i], check_index=999)
        compiled = replace(compiled, completed_detectors=tuple(rows))
    elif change == "probability":
        compiled = replace(compiled, completed_dem=build(p=.004).completed_dem)
    else:
        stripped = stim.DetectorErrorModel()
        for op in compiled.completed_dem.flattened():
            if op.type == "error":
                stripped.append(stim.DemInstruction("error", op.args_copy(),
                    [t for t in op.targets_copy() if not t.is_logical_observable_id()]))
            elif op.type != "logical_observable":
                stripped.append(op)
        compiled = replace(compiled, completed_dem=stripped)
    with pytest.raises(PreparationCapabilityError, match="certification failed"):
        compile_preparation_boundary_model(compiled)


def _after_measurement(circuit, record):
    for i in range(len(circuit)):
        if circuit[:i + 1].num_measurements > record:
            return i + 1
    raise AssertionError("missing test record")


def _readout_fault(circuit, record):
    index = _after_measurement(circuit, record) - 1
    op = circuit[index]
    assert op.name == "MR"
    start = circuit[:index].num_measurements
    replacement = stim.Circuit()
    for j, target in enumerate(op.targets_copy()):
        replacement.append("MR", [target], .125 if start + j == record else 0)
    return circuit[:index] + replacement + circuit[index + 1:]


def _one_fault(compiled, completed, kind):
    circuit = compiled.completed_circuit if completed else compiled.circuit
    ledger = compiled.completed_ledger if completed else compiled.ledger
    r = 1 if kind in {"first_readout", "spatial"} else 2
    records = [row.record_id for row in ledger if row.source == "se" and row.sector == "x" and row.round_index == r]
    if kind in {"first_readout", "last_readout"}:
        return _readout_fault(circuit, records[0])
    # Z on data just after X extraction, at the next native gate boundary.
    # A corner has one X neighbour, an interior data qubit has two.
    hx = Code.rotated(3).matrices[0].toarray()
    degree = 2 if kind == "two_future" else 1
    q = int(np.flatnonzero(hx.sum(axis=0) == degree)[0])
    cut = _after_measurement(circuit, records[-1])
    return circuit[:cut] + stim.Circuit(f"Z_ERROR(.125) {q}") + circuit[cut:]


@pytest.mark.parametrize("kind", ["first_readout", "last_readout", "spatial", "future_spatial", "two_future"])
def test_R2_readout_and_gate_pauli_fault_maps_are_independently_predicted(kind):
    compiled = build()
    production, completed = (_one_fault(compiled, value, kind) for value in (False, True))
    pdem, cdem = (c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=False,
                                      allow_gauge_detectors=False) for c in (production, completed))
    model = completed_dem_to_temporal_model(cdem, detector_roles=[r.role for r in compiled.completed_detectors],
        num_observables=compiled.completed_circuit.num_observables)
    assert model.num_mechanisms == 1 and model.probabilities[0] == .125
    readout = kind in {"first_readout", "last_readout"}
    if readout:
        checks = [0]
    else:
        hx = Code.rotated(3).matrices[0].toarray()
        q = int(np.flatnonzero(hx.sum(axis=0) == (2 if kind == "two_future" else 1))[0])
        checks = list(np.flatnonzero(hx[:, q]))
    # Hand-derived propagation: first readout flips past+next difference;
    # last readout flips last difference+future+tau; post-X data faults flip
    # the next difference if present, otherwise only future+tau.
    expected_roles = {"first_readout": {"past", "online"}, "last_readout": {"online", "future"},
                      "spatial": {"online"}, "future_spatial": {"future"}, "two_future": {"future"}}[kind]
    expected = tuple(r.detector_id for r in compiled.completed_detectors
                     if r.role.value in expected_roles and r.check_index in checks)
    assert model.full_detector_support == (expected,)
    np.testing.assert_array_equal(model.past, [kind == "first_readout"])
    np.testing.assert_array_equal(model.future, [kind in {"last_readout", "future_spatial"}])
    expected_features = np.zeros(model.feature_map.shape[0], dtype=np.uint8)
    if kind in {"last_readout", "future_spatial", "two_future"}:
        expected_features[list(np.asarray(compiled.completed_labels.tau_x)[checks])] = 1
    np.testing.assert_array_equal(model.feature_map.toarray()[:, 0], expected_features)
    assert model.frozen_columns.tolist() == ([0] if kind in {"spatial", "future_spatial"} else [])
    if kind == "two_future":
        assert not model.h_online.nnz and not model.past.any() and not model.future.any()
        assert model.feature_map.nnz == 2  # Not dropped after temporal contraction.
    compare_marginal_models(pdem, cdem, production_detector_ids=compiled.online_x_detector_ids,
        completed_detector_ids=[r.detector_id for r in compiled.completed_detectors if r.role == DetectorRole.ONLINE],
        production_observable_ids=range(compiled.circuit.num_observables),
        completed_observable_ids=range(compiled.completed_circuit.num_observables))


def test_coordinates_and_gate_location_guesses_do_not_classify_boundaries():
    compiled = build(p=.003)
    original = compile_preparation_boundary_model(compiled)
    changed = stim.DetectorErrorModel()
    for op in compiled.completed_dem.flattened():
        if op.type == "detector":
            changed.append("detector", [1000, -1000, 999], op.targets_copy())
        else:
            changed.append(op)
    model = completed_dem_to_temporal_model(changed, detector_roles=[r.role for r in compiled.completed_detectors],
        num_observables=compiled.circuit.num_observables)
    for name in ("past", "future", "frozen_columns", "weights"):
        np.testing.assert_array_equal(getattr(original, name), getattr(model, name))
    assert original.full_detector_support == model.full_detector_support


def test_correlated_two_qubit_gate_pauli_uses_actual_propagation_without_splitting():
    compiled = build()
    circuits = []
    # Last native first-round X-check CNOT: ancilla 12 -> data 2. A Z on
    # each endpoint flips first readout check3 and the next data syndrome
    # check3. Those two effects cancel in online D(check3, round2), leaving
    # only the past spatial port. This remains ONE independent mechanism.
    code = Code.rotated(3)
    assert code.matrices[0].toarray()[:, 2].tolist() == [0, 0, 0, 1]
    for source, ledger in ((compiled.circuit, compiled.ledger),
                            (compiled.completed_circuit, compiled.completed_ledger)):
        first_se = min(r.record_id for r in ledger if r.source == "se")
        before_readout = _after_measurement(source, first_se) - 1
        index = max(i for i in range(before_readout) if source[i].name == "CX")
        assert [t.value for t in source[index].targets_copy()] == [12, 2]
        fault = stim.Circuit("CORRELATED_ERROR(.125) Z12 Z2")
        circuits.append(source[:index + 1] + fault + source[index + 1:])
    pdem, cdem = (c.detector_error_model(decompose_errors=False,
        approximate_disjoint_errors=False, allow_gauge_detectors=False) for c in circuits)
    model = completed_dem_to_temporal_model(cdem,
        detector_roles=[r.role for r in compiled.completed_detectors], num_observables=9)
    past_check3 = next(r.detector_id for r in compiled.completed_detectors
                      if r.role == DetectorRole.PAST and r.check_index == 3)
    assert model.num_mechanisms == 1
    assert model.full_detector_support == ((past_check3,),)
    assert model.frozen_columns.tolist() == [0]
    assert not model.h_online.nnz and not model.future.any() and model.past.tolist() == [1]
    assert not model.feature_map.nnz
    compare_marginal_models(pdem, cdem, production_detector_ids=compiled.online_x_detector_ids,
        completed_detector_ids=[r.detector_id for r in compiled.completed_detectors if r.role == DetectorRole.ONLINE],
        production_observable_ids=range(9), completed_observable_ids=range(9))
