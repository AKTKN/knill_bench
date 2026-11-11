"""Exact public mappings and controlled faults, with <=7 physical shots/batch."""

from dataclasses import replace
import math

import numpy as np
import pymatching
import pytest
import stim

from logical_to_stim_converter import (
    BlockUseId, CodeSpec, NoiseModel, PostInitializationNoise, parse_logical_circuit,
)
from knill_bench.converter.decoding import GraphlikeModelError, MemoryDecoder, checked_matching
from knill_bench.converter.se_memory import ConverterSEMemory, exact_stim_text, memory_source
from knill_bench.experiments.config_v2 import parse_config


def point(d=3, p=.003, rounds=3, **options):
    config = parse_config(dict(schema_version=2, kind="converter_se_memory", noise="converter_uniform",
                              sweep=dict(d=[d], p=[p]), rounds=rounds, **options))
    return next(config.points())


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("policy", ["noisy", "ideal"])
def test_noiseless_dual_basis_and_preparation_gauges(d, basis, policy):
    compiled = parse_logical_circuit(memory_source(d, 2, basis=basis, input_preparation=policy)).compile(
        noise_model=NoiseModel.uniform_depolarizing(0))
    decoder = MemoryDecoder(compiled, basis=basis)
    raw = compiled.circuit.compile_sampler(seed=51).sample(7)
    assert raw.any()  # Random opposite-sector preparation gauges are retained.
    assert not decoder.view.events_from_raw(raw).any()
    assert not decoder.view.observable_flips_from_raw(raw).any()
    assert not decoder.decode_batch(raw).logical_error.any()


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("rounds", [1, 2, 3])
def test_exact_total_rounds_and_equivalence_to_requested_program(d, rounds):
    model = ConverterSEMemory(point(d, rounds=rounds))
    syndromes = [m for m in model.compiled.measurements if m.key.kind == "syndrome"]
    assert len(syndromes) == rounds * (d*d-1)
    assert {m.key.round_index for m in syndromes} == set(range(rounds))
    assert {d.basis for d in model.compiled.detectors} >= {"Z"}
    assert {m.key.local_id[0] for m in syndromes} == {"X", "Z"}
    assert model.circuit.num_measurements == rounds*(d*d-1) + d*d
    assert ("SE[storage]" in model.lstim_source) == (rounds > 1)
    assert "SE[storage](0)" not in model.lstim_source
    bare = (f"FORMAT(1)\nCODE sc ROTATED_SURFACE({d})\nPATCH P0 sc index=0\nBIND D P0\n"
            "INIT_Z(1) D\n" + (f"SE({rounds-1}) D\n" if rounds > 1 else "") + "MZ D\n")
    expected = parse_logical_circuit(bare).compile(noise_model=NoiseModel.uniform_depolarizing(model.point.p))
    assert model.circuit == expected.circuit
    assert model.frame_plan.source_fingerprint == model.decoder.view.source_fingerprint


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("policy", ["noisy", "ideal"])
def test_raw_batch_public_view_direct_stim_and_independent_mwpm_agree(d, policy):
    model = ConverterSEMemory(point(d, p=.02, input_preparation=policy))
    raw = model.circuit.compile_sampler(seed=52).sample(7)
    before = raw.copy()
    decoder, view = model.decoder, model.decoder.view
    dets, flips = model.circuit.compile_m2d_converter().convert(measurements=raw, separate_observables=True)
    selected_ids = tuple(info.index for info in model.compiled.detectors if info.basis == "Z")
    assert view.detector_map.global_ids == selected_ids
    assert view.observable_map.global_ids == (model.compiled.observables[0].index,)
    assert all(info.basis == "Z" for info in view.detectors)
    events = view.events_from_raw(raw)
    actual = view.observable_flips_from_raw(raw)
    assert np.array_equal(events, dets[:, selected_ids])
    assert np.array_equal(events, view.project_detection_events(dets))
    assert np.array_equal(actual, flips[:, view.observable_map.global_ids])
    local_dets, local_obs = view.circuit.compile_m2d_converter().convert(measurements=raw, separate_observables=True)
    assert np.array_equal(events, local_dets) and np.array_equal(actual, local_obs)
    reference = pymatching.Matching.from_detector_error_model(decoder.dem, enable_correlations=False)
    expected = reference.decode_batch(local_dets, enable_correlations=False).astype(bool)
    assert np.array_equal(expected, decoder.predict(events))
    assert np.array_equal(model.decode_batch(raw).logical_error, (expected ^ local_obs)[:, 0])
    assert np.array_equal(model.decode_batch(raw).logical_error, (decoder.predict(dets[:, selected_ids]) ^ actual)[:, 0])
    assert np.array_equal(raw, before)


def perfect_syndrome_fixture(d):
    """Use the converter's public preparation cut for TEST-ONLY pure-X faults.

    No independent physical layout or detector geometry is constructed here.
    The registered runner never inserts these fault channels.
    """
    compiled = parse_logical_circuit(memory_source(d, 2)).compile(noise_model=NoiseModel(
        post_initialization=(PostInitializationNoise("initial", BlockUseId("P0", 0), 0.),)))
    decoder = MemoryDecoder(compiled)
    boundary, = compiled.post_initialization_boundaries
    cut = boundary.ideal_boundary_instruction
    wires = [compiled.physical_qubit_map[site] for site in boundary.data_sites]
    noise = stim.Circuit()
    noise.append("X_ERROR", wires, .1)  # Independent pure-X q=.1, NOT depolarizing p.
    test_circuit = compiled.circuit[:cut] + noise + compiled.circuit[cut:]
    full_dem = test_circuit.detector_error_model(decompose_errors=False).flattened()
    # Independent TEST projection of the pure-X reference DEM using the public
    # view maps. All physical errors must lie in the selected sector; drop none.
    dem = stim.DetectorErrorModel()
    det_map = decoder.view.detector_map.global_to_local
    obs_map = decoder.view.observable_map.global_to_local
    for instruction in full_dem:
        if instruction.type != "error":
            continue
        targets = []
        for t in instruction.targets_copy():
            if t.is_relative_detector_id():
                assert t.val in det_map
                targets.append(stim.target_relative_detector_id(det_map[t.val]))
            else:
                assert t.is_logical_observable_id() and t.val in obs_map
                targets.append(stim.target_logical_observable_id(obs_map[t.val]))
        dem.append("error", instruction.args_copy(), targets)
    for i in range(len(decoder.view.detectors)):
        dem.append("detector", [], [stim.target_relative_detector_id(i)])
    dem.append("logical_observable", [], [stim.target_logical_observable_id(0)])
    matching = checked_matching(dem)
    columns, logicals = [], []
    for wire in wires:
        fault = stim.Circuit()
        fault.append("X", [wire])
        physical = compiled.circuit[:cut] + fault + compiled.circuit[cut:]
        raw = physical.compile_sampler(seed=53).sample(1)
        # Use ORIGINAL ideal-circuit m2d: the deterministic injected X changes
        # the faulted circuit's own noiseless reference, so it cannot label truth.
        dets, obs = compiled.circuit.compile_m2d_converter().convert(measurements=raw, separate_observables=True)
        projected = decoder.view.project_detection_events(dets)
        assert np.array_equal(projected, decoder.view.events_from_raw(raw))
        assert np.array_equal(obs, decoder.view.observable_flips_from_raw(raw))
        columns.append(projected[0])
        logicals.append(obs[0, 0])
    return decoder, matching, np.asarray(columns, dtype=np.uint8), np.asarray(logicals, dtype=np.uint8)


@pytest.mark.parametrize("d", [3, 5])
def test_every_single_physical_x_fault_with_perfect_syndromes_including_boundaries(d):
    decoder, matching, columns, logicals = perfect_syndrome_fixture(d)
    code = CodeSpec.rotated_surface(d)
    # Independently check native observable support and the nonzero syndrome rows
    # against the mathematical CSS code, without decoding via those matrices.
    assert np.array_equal(logicals, code.L_Z[0])
    nonzero_rows = columns.T[np.any(columns.T, axis=1)]
    assert sorted(map(tuple, nonzero_rows)) == sorted(map(tuple, code.H_Z))
    boundary = np.sum(code.H_Z, axis=0) == 1
    assert boundary.any() and (~boundary).any()
    predicted = matching.decode_batch(columns.astype(bool), enable_correlations=False)[:, 0]
    assert np.array_equal(predicted, logicals)
    assert np.array_equal(predicted[boundary], logicals[boundary])


def test_exhaustive_d3_pure_x_classes_against_exact_css_minimum_weight_reference():
    _, matching, columns, logical_columns = perfect_syndrome_fixture(3)
    code = CodeSpec.rotated_surface(3)
    patterns = ((np.arange(2**9)[:, None] >> np.arange(9)) & 1).astype(np.uint8)
    syndromes = patterns @ code.H_Z.T % 2
    logicals = (patterns @ code.L_Z.T % 2)[:, 0]
    weights = patterns.sum(axis=1)
    # Enumerate ALL patterns independently of Stim/PyMatching. For iid pure-X
    # 0<q<.5, minimum individual-pattern weight determines the MWPM class.
    # This is not a maximum-likelihood logical-coset/posterior claim.
    best = {}
    for syndrome, logical, weight in zip(syndromes, logicals, weights, strict=True):
        key = tuple(syndrome)
        if key not in best or weight < best[key][0]:
            best[key] = (weight, {int(logical)})
        elif weight == best[key][0]:
            best[key][1].add(int(logical))
    assert len(best) == 2**code.H_Z.shape[0]
    assert all(len(classes) == 1 for _, classes in best.values())
    expected = np.array([next(iter(best[tuple(s)][1])) for s in syndromes], dtype=bool)
    physical_events = (patterns @ columns % 2).astype(bool)
    physical_truth = patterns @ logical_columns % 2
    assert np.array_equal(physical_truth, logicals)
    predicted = matching.decode_batch(physical_events, enable_correlations=False)[:, 0].astype(bool)
    assert np.array_equal(predicted, expected)
    # Second independent inference path starts from CSS alone, not a Stim DEM.
    from scipy.sparse import csc_matrix
    reference = pymatching.Matching.from_check_matrix(
        csc_matrix(code.H_Z), weights=np.full(9, math.log(9)),
        error_probabilities=np.full(9, .1), faults_matrix=csc_matrix(code.L_Z))
    assert np.array_equal(reference.decode_batch(syndromes, enable_correlations=False)[:, 0], expected)
    assert np.array_equal(predicted ^ physical_truth, expected ^ logicals)


@pytest.mark.parametrize("dem", [
    "error(.01) D0 D1 D2", "error(.01) D0 ^ D1", "error(.01) L0",
    "error(.01) D0\nerror(.01) D0 L0",
])
def test_unsupported_dem_information_is_never_silently_dropped(dem):
    with pytest.raises(GraphlikeModelError): checked_matching(stim.DetectorErrorModel(dem))


def test_exact_stim_artifact_roundtrips_long_probabilities_tags_and_repeat_blocks():
    circuit = stim.Circuit()
    circuit.append("R", [0])
    circuit.append("X_ERROR", [0], .12345678901234567, tag="test(tag)")
    body = stim.Circuit()
    body.append("M", [0], .012345678901234567)
    circuit += body * 3
    text = exact_stim_text(circuit)
    assert stim.Circuit(text) == circuit
    assert ".12345678901234566" in text or ".12345678901234568" in text


def test_same_raw_partition_and_seed_repeat_exactly():
    model = ConverterSEMemory(point())
    first = model.circuit.compile_sampler(seed=54).sample(7)
    second = model.circuit.compile_sampler(seed=54).sample(7)
    assert np.array_equal(first, second)
    a = model.decode_batch(first).logical_error
    b = np.concatenate([model.decode_batch(first[:3]).logical_error, model.decode_batch(first[3:]).logical_error])
    assert np.array_equal(a, b) and np.array_equal(a, model.decode_batch(second).logical_error)
