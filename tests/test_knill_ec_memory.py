"""General Knill EC: native policy, physical targets, small streamed runs."""

from dataclasses import replace
import importlib
import json

import numpy as np
import pyarrow.parquet as pq
import pymatching
import pytest
import yaml

from hex_qec.modularisation import modularised_circuit
from knill_bench.adapters.hex_full_knill import HexFullKnill
from knill_bench.analysis.fig4d import summarize_saved, plot_saved
from knill_bench.codes import Code
from knill_bench.experiments import dispatcher
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config, parse_config
from knill_bench.experiments.noise_v2 import validate_noise_execution
from knill_bench.experiments.seeds import point_seed

MODELS = ("hex_uniform", "noiseless_bellpair", "code_capacity_noise")


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="knill_ec_memory", name="knill_test",
               output_root=str(tmp_path / "runs"), sweep=dict(d=[3], p=[.02]),
               T_tel=2, r_0=1, r_plus=2, shots=7, batch_size=3, workers=1, master_seed=25)
    raw.update(updates)
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(raw))
    return load_config(path)


@pytest.mark.parametrize("noise", MODELS)
def test_roundtrip_identities_and_defaults(tmp_path, noise):
    doc = document(tmp_path, noise=noise)
    config = doc.config
    assert parse_config(config.as_dict()) == config
    point = next(config.points())
    assert f"noisemodel={noise}" in point.filename("logical_error")
    assert "r_+=" in point.filename("logical_error")
    assert point.final_readout == ("noisy_destructive_Z" if noise == "hex_uniform" else "ideal_destructive_Z")
    changed = replace(config, shots=99, workers=2, theta=3.)
    assert point_seed(config.master_seed, point) == point_seed(changed.master_seed, next(changed.points()))
    other = replace(point, noise=MODELS[(MODELS.index(noise)+1) % 3])
    assert point.case_id != other.case_id
    assert point_seed(25, point) != point_seed(25, other)
    raw = config.as_dict()
    raw.pop("T_tel")
    assert parse_config(raw).T_tel == 8


@pytest.mark.parametrize("noise", MODELS[1:])
@pytest.mark.parametrize("kind", ["fig4d_reproduction", "logical_zero_factory", "se_memory"])
def test_special_models_rejected_for_other_protocols(tmp_path, noise, kind):
    with pytest.raises(ValueError, match="only for kind=knill_ec_memory"):
        document(tmp_path, kind=kind, noise=noise)
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("updates", [dict(create_codecapacity_dem=True), dict(theta=0.),
                                     dict(T_tel=0), dict(T_tel=True), dict(noise="code_capacity"),
                                     dict(noise=["hex_uniform", "code_capacity_noise"]),
                                     dict(noise={"model": "custom"})])
def test_invalid_knill_requests_before_output(tmp_path, updates):
    with pytest.raises(ValueError):
        doc = document(tmp_path, **updates)
        dispatcher.dispatch(doc.source_path)
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("noise", MODELS)
def test_native_circuit_and_supplied_raw_decode_parity(tmp_path, monkeypatch, noise):
    from test_fig4d import legacy_process
    point = next(document(tmp_path, noise=noise, r_plus=1).config.points())
    model = HexFullKnill(point, seed=19)
    module = importlib.import_module("hex_qec.protocols.knill_online_offline")
    captured = []
    def capture(modules):
        engine = modularised_circuit(modules)
        captured.append(engine)
        engine.simulate = lambda *a, **kw: (0, 0)
        return engine
    monkeypatch.setattr(module, "modularised_circuit", capture)
    module.knill_online_offline(Code.rotated(3).matrices, 1,
        pymatching.Matching.from_check_matrix, pymatching.Matching.from_check_matrix,
        True, point.p, 1, 1, "z", point.T_tel, surface_code=True, noise_model=noise)
    native = captured[0]
    assert model.engine.circuit == native.circuit
    raw = model.sample(7)
    before = raw.copy()
    expected, corrected = legacy_process(native, raw)
    actual = model.decode_batch(raw)
    assert np.array_equal(raw, before)
    assert np.array_equal(actual.logical_error, expected)
    assert np.array_equal(actual.corrected_measurements, corrected)
    validate_noise_execution(point, model.metadata, create_codecapacity_dem=False)
    for key, value in (("noise_scope_version", "unknown"), ("terminal_ideal_oracle", True),
                       ("create_codecapacity_dem", True), ("physical_error", .3)):
        with pytest.raises(ValueError, match="noise execution"):
            validate_noise_execution(point, dict(model.metadata, **{key: value}),
                                     create_codecapacity_dem=False)


@pytest.mark.parametrize("noise", MODELS[1:])
@pytest.mark.parametrize("d,T", [(3, 1), (3, 3), (5, 2)])
def test_no_noise_frames_and_cached_native_handles(tmp_path, monkeypatch, noise, d, T):
    point = next(document(tmp_path, noise=noise, sweep=dict(d=[d], p=[0.]), T_tel=T).config.points())
    model = HexFullKnill(point, seed=19)
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstructed native matching during decode")
    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", forbidden)
    for n in (3, 4):
        assert not model.decode_batch(model.sample(n)).logical_error.any()


@pytest.mark.parametrize("noise", MODELS[1:])
@pytest.mark.parametrize("batch", [3, "auto"])
def test_run_resume_saved_analysis_and_metadata_guard(tmp_path, monkeypatch, noise, batch):
    doc = document(tmp_path, noise=noise, batch_size=batch, buffer_shot=3)
    path = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    file = path / point.filename("logical_error")
    table = pq.read_table(file)
    assert table["shot_id"].to_pylist() == list(range(7))
    meta_path = path / "metadata.json"
    meta = json.loads(meta_path.read_text())
    info = meta["points"][point.case_id]
    assert meta["final_readout"] == info["execution"]["final_readout"] == "ideal_destructive_Z"
    assert info["execution"]["final_readout_error"] == 0.
    assert info["execution"]["terminal_ideal_oracle"] is False
    original = file.read_bytes()
    assert dispatcher.resume(path) == path and original == file.read_bytes()
    import knill_bench.adapters.hex_full_knill as adapter
    monkeypatch.setattr(adapter, "HexFullKnill", lambda *a, **k: pytest.fail("analysis simulated"))
    assert summarize_saved(path)[0]["shots"] == 7
    assert plot_saved(path, tmp_path / "knill.svg").is_file()
    info["execution"]["noise_probabilities"]["final_readout"] = .02
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="noise execution"):
        summarize_saved(path)
    with pytest.raises(ValueError, match="noise execution"):
        dispatcher.resume(path)


@pytest.mark.parametrize("noise", MODELS[1:])
def test_fixed_spawn_equality_and_failed_point_restart(tmp_path, monkeypatch, noise):
    from knill_bench.experiments import knill_ec_memory as runner
    doc = document(tmp_path, noise=noise, sweep=dict(d=[3], p=[0., .02]), workers=2, shots=3)
    parallel = runner.run(doc)
    serial_doc = document(tmp_path, noise=noise, sweep=dict(d=[3], p=[0., .02]), shots=3)
    serial = runner.run(serial_doc)
    for point in doc.config.points():
        assert pq.read_table(parallel / point.filename("logical_error")).equals(
            pq.read_table(serial / point.filename("logical_error")))
    actual = runner._run_point
    def fail(*args, **kwargs):
        if args[1].p:
            raise RuntimeError("intentional chunk failure")
        return actual(*args, **kwargs)
    monkeypatch.setattr(runner, "_run_point", fail)
    with pytest.raises(RuntimeError, match="intentional"):
        runner.run(serial_doc)
    failed = sorted((tmp_path / "runs").iterdir())[-1]
    points = list(doc.config.points())
    completed = (failed / points[0].filename("logical_error")).read_bytes()
    monkeypatch.setattr(runner, "_run_point", actual)
    assert dispatcher.resume(failed) == failed
    assert (failed / points[0].filename("logical_error")).read_bytes() == completed
