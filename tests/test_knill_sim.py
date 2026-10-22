"""General Knill entry point and two explicit prior scopes; <=7 physical shots."""

from dataclasses import replace
import importlib
import json

import numpy as np
import pyarrow.parquet as pq
import pymatching
import pytest
import stim
import yaml

from hex_qec.decoders.codecapacity_dem import UnsupportedProjectedModel
from hex_qec.modularisation import modularised_circuit
from knill_bench.adapters.hex_full_knill import HexFullKnill
from knill_bench.adapters import knill_priors as priors
from knill_bench.analysis.fig4d import summarize_saved
from knill_bench.analysis.saved_data import RunRegistry
from knill_bench.codes import Code
from knill_bench.experiments import dispatcher, knill_sim
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config, parse_config
from knill_bench.experiments.noise_v2 import validate_noise_execution
from knill_bench.experiments.seeds import point_seed


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="knill_sim", name="knill_sim_test",
               output_root=str(tmp_path / "runs"), sweep=dict(d=[3], p=[.001]),
               T_tel=1, r_0="d", r_plus="d", shots=3, batch_size=3, workers=1,
               create_codecapacity_dem=True, codecapacity_prior="module_local")
    raw.update(updates)
    source = tmp_path / "config.yaml"
    source.write_text(yaml.safe_dump(raw))
    return load_config(source)


@pytest.mark.parametrize("kind", ["knill_sim", "knill_ec_memory"])
@pytest.mark.parametrize("mode", ["module_local", "full_prefix"])
def test_general_config_with_user_grid_is_parsed_without_large_construction(tmp_path, monkeypatch, kind, mode):
    monkeypatch.setattr(stim.Circuit, "compile_sampler", lambda *a, **k: pytest.fail("sampled user grid"))
    doc = document(tmp_path, kind=kind, codecapacity_prior=mode,
                   sweep=dict(d=[5, 7, 9, 11], p=[.001, .002, .004, .006, .008, .01]),
                   shots=200000, workers=36, batch_size="auto", buffer_shot=10000)
    assert len(list(doc.config.points())) == 24
    assert parse_config(doc.config.as_dict()) == doc.config
    assert doc.config.prior_policy == ("knill_module_local_stim_dem" if mode == "module_local" else "knill_full_prefix_projected")
    knill_sim.validate_experiment(doc.config)
    other = replace(doc.config, codecapacity_prior="full_prefix" if mode == "module_local" else "module_local")
    assert doc.config.config_hash != other.config_hash
    assert next(doc.config.points()) == next(other.points())
    assert point_seed(77, next(doc.config.points())) == point_seed(77, next(other.points()))


def test_default_mode_and_false_hash_compatibility(tmp_path):
    doc = document(tmp_path)
    raw = doc.config.as_dict()
    raw.pop("codecapacity_prior")
    assert parse_config(raw).codecapacity_prior == "module_local"
    raw.update(create_codecapacity_dem=False)
    false = parse_config(raw)
    assert "codecapacity_prior" not in false.as_dict()
    assert false.prior_policy == "hex_legacy_hamming"
    assert false.projected_approximation is None


@pytest.mark.parametrize("updates", [dict(codecapacity_prior="typo"), dict(codecapacity_prior=["module_local"]),
    dict(create_codecapacity_dem=False), dict(kind="logical_zero_factory"), dict(kind="fig4d_reproduction"),
    dict(kind="se_memory")])
def test_invalid_or_irrelevant_scopes_are_rejected(tmp_path, updates):
    with pytest.raises(ValueError):
        document(tmp_path, **updates)
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("kind", ["knill_sim", "knill_ec_memory"])
@pytest.mark.parametrize("noise", ["hex_uniform", "noiseless_bellpair", "code_capacity_noise"])
def test_local_prior_physical_identity_and_cache_at_d_rounds(kind, noise, monkeypatch):
    point = ExperimentPoint(kind, 3, .01, 3, 3, 2, noise=noise)
    false = HexFullKnill(point, seed=91)
    priors.clear_knill_prior_cache()
    true = HexFullKnill(point, seed=91, create_codecapacity_dem=True)
    assert true.engine.circuit == false.engine.circuit
    a, b = false.sample(7), true.sample(7)
    np.testing.assert_array_equal(a, b)
    validate_noise_execution(point, true.metadata, create_codecapacity_dem=True)
    info = priors.knill_prior_cache_info()
    assert info['misses'] == 2 and info['hits'] == 2
    assert len(true.metadata['projected_priors']) == 2
    def forbidden(*a, **k):
        raise AssertionError("rebuilt sampler/prior/graph while decoding")
    monkeypatch.setattr(priors, '_stim_dem', forbidden)
    monkeypatch.setattr(stim.Circuit, 'compile_sampler', forbidden)
    monkeypatch.setattr(pymatching.Matching, 'from_check_matrix', forbidden)
    assert true.decode_batch(a[:3]).logical_error.shape == (3,)
    assert true.decode_batch(a[3:]).logical_error.shape == (4,)


def test_local_d5_real_preparation_and_prior_excludes_depths_final_and_previous_stage():
    point = ExperimentPoint('knill_sim', 5, .001, 5, 5, 2)
    priors.clear_knill_prior_cache()
    model = HexFullKnill(point, seed=88, create_codecapacity_dem=True)
    assert model.decode_batch(model.sample(3)).logical_error.shape == (3,)
    hashes = model.metadata['projected_priors']
    assert hashes[0] == hashes[1]
    other = HexFullKnill(replace(point, r_0=1, r_plus=1), seed=99, create_codecapacity_dem=True)
    assert hashes == other.metadata['projected_priors']
    assert model.engine.circuit != other.engine.circuit
    assert model.metadata['preparation_residual_errors_in_prior'] is False
    assert model.metadata['earlier_stage_residual_errors_in_prior'] is False
    noisy = model.engine.circuit_modules[-1].circuit
    assert any(op.name == 'X_ERROR' and op.gate_args_copy() == [.001] for op in noisy)
    assert model.metadata['final_readout'] == 'noisy_destructive_Z'


def test_local_ideal_bell_and_capacity_analytic_sector_dems():
    # These are inference-only exact DEM comparisons, with no physical shots.
    p = .01
    models = [HexFullKnill(ExperimentPoint('knill_sim', 3, q, 1, 1, 1, noise=noise), seed=7)
              for noise, q in [('noiseless_bellpair', p), ('code_capacity_noise', 2.3*p-1.6*p*p)]]
    events = []
    for model in models:
        pieces = [m for m, role in zip(model.engine.circuit_modules, model.roles)
                  if role in {'bell_entangle', 'data_code_capacity_noise', 'bell_measure_and_correct'}]
        support = next(s for s, role in zip(model.supports, model.roles) if role == 'bell_measure_and_correct')
        body = priors._local_body(pieces, support)
        spec = priors._code_spec(Code.rotated(3))
        events.append([{e.signature: e.probability for e in priors._event_model(
            priors._stim_dem(priors._analysis_circuit(spec, body, sector))).events}
                       for sector in ('x','z')])
    for first, second in zip(*events):
        assert first.keys() == second.keys()
        for signature in first:
            assert first[signature] == pytest.approx(second[signature], abs=1e-14)


@pytest.mark.parametrize("noise", ['hex_uniform', 'noiseless_bellpair', 'code_capacity_noise'])
def test_full_prefix_uses_native_causal_callbacks_and_global_map_results(monkeypatch, noise):
    from test_fig4d import legacy_process
    point = ExperimentPoint('knill_sim', 3, .001, 1, 1, 2, noise=noise)
    model = HexFullKnill(point, seed=43, create_codecapacity_dem=True, codecapacity_prior='full_prefix')
    # Independently built native modules/global-map processing, same physical records.
    native = HexFullKnill(point, seed=43)
    native.engine.generate_correction_to_measurement_flip_map()
    from hex_qec.modularisation.online_context import configure_knill_projected_priors
    configure_knill_projected_priors(native.engine, Code.rotated(3).matrices)
    raw = model.sample(3)
    expected, repaired = legacy_process(native.engine, raw)
    decoded = model.decode_batch(raw)
    np.testing.assert_array_equal(decoded.logical_error, expected)
    np.testing.assert_array_equal(decoded.corrected_measurements, repaired)
    validate_noise_execution(point, model.metadata, create_codecapacity_dem=True, codecapacity_prior='full_prefix')
    assert model.metadata['preparation_residual_errors_in_prior'] is True
    assert model.metadata['projected_priors'][0] != model.metadata['projected_priors'][1]


@pytest.mark.parametrize('mode,p,rounds', [('module_local',0.,3),('full_prefix',.001,3)])
def test_unsupported_models_raise_before_sampler_without_fallback(monkeypatch, mode,p,rounds):
    monkeypatch.setattr(stim.Circuit,'compile_sampler',lambda *a, **k: pytest.fail('sampled unsupported model'))
    with pytest.raises(UnsupportedProjectedModel):
        HexFullKnill(ExperimentPoint('knill_sim',3,p,rounds,rounds,1), seed=1,
                     create_codecapacity_dem=True, codecapacity_prior=mode)


@pytest.mark.parametrize('mode', ['module_local','full_prefix'])
@pytest.mark.parametrize('batch', [3,'auto'])
def test_run_resume_analysis_metadata_and_policy_mismatch(tmp_path,mode,batch):
    doc = document(tmp_path, codecapacity_prior=mode, r_0=1, r_plus=1,batch_size=batch)
    path = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    file = path / point.filename('logical_error')
    before = file.read_bytes()
    meta = json.loads((path/'metadata.json').read_text())
    info = meta['points'][point.case_id]
    assert meta['prior_policy'] == info['execution']['prior_policy'] == doc.config.prior_policy
    assert meta['projected_approximation'] == doc.config.projected_approximation
    assert pq.read_table(file)['shot_id'].to_pylist() == [0,1,2]
    assert dispatcher.resume(path) == path and before == file.read_bytes()
    assert summarize_saved(path)[0]['shots'] == 3
    saved, = RunRegistry({'knill':path}).select()
    assert sum(len(labels) for labels,_ in saved.batches()) == 3
    info['execution']['codecapacity_prior'] = 'full_prefix' if mode=='module_local' else 'module_local'
    (path/'metadata.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError,match='inference scope'):
        dispatcher.resume(path)
    with pytest.raises(ValueError,match='inference scope'):
        summarize_saved(path)


@pytest.mark.parametrize('mode', ['module_local','full_prefix'])
def test_fixed_spawn_equals_serial(tmp_path,mode):
    options=dict(codecapacity_prior=mode,r_0=1,r_plus=1,shots=3,sweep=dict(d=[3],p=[.001,.002]))
    doc = document(tmp_path,workers=2,**options)
    parallel=knill_sim.run(doc)
    serial=knill_sim.run(document(tmp_path,workers=1,**options))
    for point in doc.config.points():
        assert pq.read_table(parallel/point.filename('logical_error')).equals(pq.read_table(serial/point.filename('logical_error')))
