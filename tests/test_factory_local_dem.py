"""Local-prior physics, frame integration, cache boundaries and old-data labels."""

from dataclasses import replace
from itertools import product
import json

import numpy as np
import pytest
import stim

from hex_qec.decoders import codecapacity_dem as legacy
from hex_qec.protocols import FactoryCircuitBuilder, RotatedSurfaceCodeAdapter
from hex_qec.protocols.logical_zero_factory import FactoryCircuitBundle
from hex_qec.simulation import CompiledFactory
from knill_bench.adapters import hex_factory as local
from knill_bench.analysis.factory import analyze_saved
from knill_bench.experiments import logical_zero_factory as runner
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config
from knill_bench.experiments.run_v2 import RunStore


def point(d=3, p=.003, T=2):
    return ExperimentPoint("logical_zero_factory", d, p, 2, 2, T)


@pytest.fixture(autouse=True)
def empty_cache():
    local.clear_local_prior_cache()
    yield
    local.clear_local_prior_cache()


@pytest.mark.parametrize("d", [3, 5])
def test_stim_dem_matches_forward_fault_propagation_and_analytic_probabilities(d):
    bundle, compiled = runner.compile_point(point(d=d), seed=17, create_codecapacity_dem=True)
    prior = compiled.projected_priors[0]
    code = bundle.code
    body = stim.Circuit(local._local_body(bundle, bundle.stages[0]))
    # Independent forward check: physical fault mechanisms only, no decoder
    # projection, prep histories or noiseless raw measurement reference.
    faults = legacy._enumerate_prefix_faults(body, ((0, "local", 0, len(body)),))
    flips = legacy._propagate_faults(body, faults)
    expected = {}
    for fault, row in zip(faults, flips):
        detectors = tuple(i for i, support in enumerate(code.z_checks) if row[list(support)].sum() % 2)
        logical = (0,) if row[list(code.logical_z)].sum() % 2 else ()
        if not (detectors or logical):
            continue
        signature = legacy.FaultSignature(detectors, logical)
        old = expected.get(signature, 0.)
        q = fault.probability
        expected[signature] = old*(1-q) + q*(1-old)
    actual = {e.signature: e.probability for e in prior.model.events}
    assert actual.keys() == expected.keys()
    assert all(actual[k] == pytest.approx(expected[k], abs=1e-14) for k in actual)
    # Closed-form target-bit marginal for CX depolarization + noisy Z readout.
    q = 23*.003/15 - 16*.003**2/15
    analytic = {}
    for j in range(code.num_data_qubits):
        signature = legacy.FaultSignature(tuple(i for i,r in enumerate(code.z_checks) if j in r),
                                          (0,) if j in code.logical_z else ())
        old = analytic.get(signature, 0.)
        analytic[signature] = old*(1-q)+q*(1-old)
    assert all(actual[k] == pytest.approx(analytic[k], abs=1e-14) for k in actual)
    analysis = local._analysis_circuit(code, str(body))
    assert analysis.num_measurements == code.num_data_qubits
    assert not analysis.without_noise().compile_detector_sampler(seed=71).sample(7).any()
    assert len(compiled.projected_priors) == 2
    assert compiled.projected_priors[0] is compiled.projected_priors[1]


def test_pauli_logical_boundary_is_needed_and_known_frames_leave_dem_unchanged():
    bundle, compiled = runner.compile_point(point(T=1), seed=9, create_codecapacity_dem=True)
    code = bundle.code
    circuit = local._analysis_circuit(code, local._local_body(bundle, bundle.stages[0]))
    prefix_end = len(stim.Circuit(local._ideal_input(code)))
    # A raw random logical parity is not itself a deterministic observable.
    raw_logical = circuit[:prefix_end] + circuit[prefix_end+1:]
    with pytest.raises(ValueError, match="non-deterministic observables"):
        raw_logical.detector_error_model()
    changed = circuit[:prefix_end]
    changed.append("X", [0, code.num_data_qubits+1])
    changed.append("Z", [1, code.num_data_qubits+2])
    changed += circuit[prefix_end:]
    assert local._stim_dem(changed) == local._stim_dem(circuit)
    assert str(local._stim_dem(circuit)) == compiled.projected_priors[0].dem_text


def test_native_physics_and_causal_frames_match_independent_sector_enumeration():
    case = point(T=3)
    bundle, compiled = runner.compile_point(case, seed=87, create_codecapacity_dem=True)
    baseline = CompiledFactory.from_bundle(bundle, seed=87)
    assert baseline.circuit == compiled.circuit == bundle.circuit
    raw = compiled.sample_measurements(7)
    assert np.array_equal(raw, baseline.sample_measurements(7))
    result = compiled.decode(raw)
    code = bundle.code
    plans = {p.region.measurements.start:p for p in bundle.preparation_frames}
    initial = plans[bundle.stages[0].preparations[0].measurements.start]
    frame = initial.resolve(raw[:, initial.region.measurements.slice])
    memory_x, memory_z = frame.x, frame.z
    lx = np.zeros(code.num_data_qubits, bool)
    lx[list(code.logical_x)] = True
    for j, stage in enumerate(bundle.stages):
        prep = plans[stage.preparations[-1].measurements.start]
        plus = prep.resolve(raw[:, prep.region.measurements.slice])
        measured = raw[:, stage.measurement.measurements.slice] ^ memory_x ^ plus.x
        syndrome = np.column_stack([measured[:,r].sum(axis=1)%2 for r in map(list,code.z_checks)])
        h, logical, weights = compiled.projected_priors[j].model.matching_matrices()
        candidates = np.array(list(product((0,1), repeat=len(weights))), dtype=np.uint8)
        signs, classes, costs = candidates @ h.T % 2, candidates @ logical % 2, candidates @ weights
        minima = np.array([[costs[np.all(signs==s,axis=1)&(classes==b)].min() for b in (0,1)]
                           for s in syndrome])
        byproduct = (measured[:,list(code.logical_z)].sum(axis=1)%2).astype(bool) ^ (minima[:,1]<minima[:,0])
        memory_x = plus.x ^ (byproduct[:,None] & lx)
        memory_z = plus.z ^ memory_z
        np.testing.assert_array_equal(result.corrected_syndromes[:,j], syndrome)
        np.testing.assert_array_equal(result.logical_byproducts[:,j], byproduct)
        np.testing.assert_array_equal(result.output_frame_x[:,j], memory_x)
        np.testing.assert_array_equal(result.output_frame_z[:,j], memory_z)
        np.testing.assert_allclose(result.gaps[:,j], abs(minima[:,1]-minima[:,0]), atol=1e-12)


def test_cache_reuses_across_stages_depths_seeds_and_never_calls_legacy_projection(monkeypatch):
    counts = dict(prior=0, validation=0)
    build, validate = local._build_local_prior, FactoryCircuitBundle.validate

    def record_prior(*args):
        counts["prior"] += 1
        return build(*args)

    def record_validation(self):
        counts["validation"] += 1
        return validate(self)

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy projection/per-shot construction is forbidden")

    monkeypatch.setattr(local, "_build_local_prior", record_prior)
    monkeypatch.setattr(FactoryCircuitBundle, "validate", record_validation)
    monkeypatch.setattr(legacy.EffectivePriorBuilder, "inspect", forbidden)
    monkeypatch.setattr(legacy, "merge_independent_events", forbidden)
    _, first = runner.compile_point(point(T=3), seed=1, create_codecapacity_dem=True)
    _, second = runner.compile_point(replace(point(T=1), r_0=1,r_plus=3), seed=2, create_codecapacity_dem=True)
    assert counts == dict(prior=1, validation=2)  # Complete native validation once per physical bundle.
    assert first.projected_priors[0] is second.projected_priors[0]
    assert local.local_prior_cache_info()["hits"] == 3
    assert local.local_prior_cache_info()["maxsize"] == 16
    _, other = runner.compile_point(point(p=.004,T=1), seed=1, create_codecapacity_dem=True)
    assert counts["prior"] == 2
    assert other.projected_priors[0].configuration_sha256 != first.projected_priors[0].configuration_sha256
    monkeypatch.setattr(local, "_build_local_prior", forbidden)
    monkeypatch.setattr(FactoryCircuitBuilder, "build", forbidden)
    monkeypatch.setattr(local.native, "_compile_sampler", forbidden)
    for n in (3,4):
        result = first.decode(first.sample_measurements(n))
        assert result.gaps.shape == (n,3)


def test_cache_is_bounded_and_changed_body_invalidates_it():
    bundle, _ = runner.compile_point(point(T=1), seed=7)
    body = local._local_body(bundle,bundle.stages[0])
    for k in range(18):
        changed = stim.Circuit()
        changed.append("X_ERROR", [0], .00001*(k+1))
        changed += stim.Circuit(body)
        local._cached_local_prior(bundle.code, str(changed))
    assert local.local_prior_cache_info()["currsize"] == 16
    assert local.local_prior_cache_info()["misses"] == 18


def test_new_saved_policy_and_legacy_analysis_without_relabeling(tmp_path):
    path = tmp_path / "input.yaml"
    path.write_text(f"""schema_version: 2
kind: logical_zero_factory
name: local_test
output_root: {tmp_path / 'runs'}
sweep: {{d: [3], p: [0.003]}}
r_0: 1
r_plus: 1
T_tel: 1
shots: 3
batch_size: 2
create_codecapacity_dem: true
""")
    run = runner.run(load_config(path))
    assert analyze_saved(run)["rows"][0]["prior_policy"] == "module_local_stim_dem"
    metadata_path = run / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["prior_policy"] = "circuit_informed_projected"
    metadata["projected_approximation"] = "single_fault_at_noiseless_reference_independent_superposition_v1"
    metadata_path.write_text(json.dumps(metadata))
    assert analyze_saved(run)["rows"][0]["prior_policy"] == "circuit_informed_projected"
    with pytest.raises(ValueError,match="prior policy changed"):
        RunStore.resume(run)
