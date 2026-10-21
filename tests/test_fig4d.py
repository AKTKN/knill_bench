"""B1 protocol fidelity, per-shot persistence and saved-data statistics.

Physical fixtures are d=3/5 and <=11 shots. Production YAML is parsed only.
"""

from dataclasses import replace
import importlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pymatching
import pytest
from scipy.sparse import csc_matrix
import yaml

from hex_qec.modularisation import css_detector_module, logical_measurement_module, measurement_module
from hex_qec.modularisation.results import normalize_module_decode_output
from knill_bench.adapters.hex_full_knill import HexFullKnill
from knill_bench.analysis.fig4d import agresti_coull, plot_saved, summarize_saved
from knill_bench.codes import Code
from knill_bench.experiments import dispatcher, fig4d_reproduction as runner
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config
from knill_bench.experiments.seeds import point_seed

ROOT = Path(__file__).resolve().parents[1]


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="fig4d_reproduction", name="fig4d_test",
               output_root=str(tmp_path / "runs"), sweep=dict(d=[3], p=[.007]),
               r_0="d", r_plus="d", T_tel=8, shots=7, batch_size=3, workers=1,
               master_seed=5678)
    raw.update(updates)
    path = tmp_path / "input.yaml"
    path.write_text("# Preserve this comment exactly.\n" + yaml.safe_dump(raw))
    return load_config(path)


def test_production_config_is_explicit_approximate_grid_only():
    doc = load_config(ROOT / "configs/fig4d.yaml")
    assert doc.config.distances == (9, 11, 15, 21)
    assert doc.config.probabilities == (.004, .005, .006, .007, .008, .009, .010)
    assert doc.config.T_tel == 8 and doc.config.r_0 == doc.config.r_plus == "d"
    assert not doc.config.create_codecapacity_dem
    assert "NOT unpublished exact paper" in doc.contents.decode()
    from knill_bench.experiments.knill_ec_memory import validate_experiment
    validate_experiment(doc.config)  # No large circuits or shots.


@pytest.mark.parametrize("updates", [dict(T_tel=1), dict(theta=0.)])
def test_runner_rejects_wrong_protocol_before_output(tmp_path, updates):
    doc = document(tmp_path, **updates)
    with pytest.raises(ValueError, match="Fig.4"):
        dispatcher.dispatch(doc.source_path)
    assert not (tmp_path / "runs").exists()


def capture_legacy(point, monkeypatch, *, generate_maps=True):
    module = importlib.import_module("hex_qec.protocols.knill_online_offline")
    captured = []
    engine_type = module.modularised_circuit

    def capture(modules):
        engine = engine_type(modules)
        captured.append(engine)
        engine.simulate = lambda *args, **kwargs: (0, 0)
        if not generate_maps:
            engine.generate_correction_to_measurement_flip_map = lambda: None
        return engine

    monkeypatch.setattr(module, "modularised_circuit", capture)
    module.knill_online_offline(Code.rotated(point.d).matrices, point.d,
                               pymatching.Matching.from_check_matrix,
                               pymatching.Matching.from_check_matrix, True, point.p,
                               1, 1, "z", point.T_tel, surface_code=True,
                               create_codecapacity_dem=False)
    return captured[0]


def test_eight_stage_actual_sequence_depth_noise_and_readout(monkeypatch):
    point = ExperimentPoint("fig4d_reproduction", 3, .007, 3, 3, 8)
    model = HexFullKnill(point, seed=123)
    legacy = capture_legacy(point, monkeypatch, generate_maps=False)
    assert str(model.engine.circuit) == str(legacy.circuit)
    meta = model.metadata
    assert meta["T_tel"] == 8 and meta["r_0"] == meta["r_plus"] == [3] * 8
    assert meta["resource_measurements"] == [3 * (3**2 - 1)] * 16
    assert meta["module_roles"].count("bell_measure_and_correct") == 8
    assert meta["initial_data"] == "ideal_encoded_zero"
    assert meta["final_readout"] == "noisy_destructive_Z"
    assert meta["final_readout_error"] == point.p
    assert meta["prior_policy"] == "hex_legacy_hamming" and not meta["create_codecapacity_dem"]
    final = model.engine.circuit_modules[-1].circuit
    assert [op.name for op in final] == ["X_ERROR", "M"]
    assert final[0].gate_args_copy() == [point.p]
    assert all(not op.name.endswith("ERROR") and not op.name.startswith("DEPOLARIZE")
               for op in model.engine.circuit_modules[0].circuit)
    assert any(op.name == "DEPOLARIZE2" for op in model.engine.circuit)


@pytest.mark.parametrize("distance,r_0,r_plus", [(3, 3, 3), (5, 5, 5), (3, 1, 1)])
def test_zero_noise_t1_and_native_objects_reused(distance, r_0, r_plus, monkeypatch):
    point = ExperimentPoint("fig4d_reproduction", distance, 0., r_0, r_plus, 1)
    model = HexFullKnill(point, seed=4321)
    sampler = model.sampler
    transitions = tuple(id(t) for t in model.transitions)

    def no_construction(*args, **kwargs):
        raise AssertionError("sampling/decoding must reuse constructed native objects")

    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", no_construction)
    for count in (3, 8):
        raw = model.sample(count)
        original = raw.copy()
        decoded = model.decode_batch(raw)
        assert decoded.logical_error.dtype == np.bool_ and not decoded.logical_error.any()
        assert np.array_equal(raw, original)
    assert model.sampler is sampler and transitions == tuple(id(t) for t in model.transitions)


def test_adapter_rejects_other_protocols_and_invalid_raw_arrays():
    point = ExperimentPoint("fig4d_reproduction", 3, 0., 3, 3, 1)
    with pytest.raises(ValueError, match="full Knill requires"):
        HexFullKnill(replace(point, kind="logical_zero_factory"), seed=1)
    model = HexFullKnill(point, seed=1)
    columns = model.engine.circuit.num_measurements
    for raw in (np.zeros((2, columns), np.uint8), np.zeros((2, columns-1), bool),
                np.zeros((0, columns), bool), np.zeros(columns, bool)):
        with pytest.raises(ValueError, match="bool matrix"):
            model.decode_batch(raw)


def legacy_process(engine, raw):
    """Hex simulate's chronological global-map processing on supplied records."""
    records = raw.copy()
    offset, labels = 0, np.zeros(len(raw), bool)
    for module in engine.circuit_modules:
        local = records[:, offset:offset+module.num_measurements]
        if isinstance(module, logical_measurement_module):
            labels |= np.any(module.c_func(local) != module.c_func_expected_output, axis=1)
        elif isinstance(module, (css_detector_module, measurement_module)):
            result = normalize_module_decode_output(module.c_func(local))
            assert result.postselection is None or not np.asarray(result.postselection).any()
            updates = (csc_matrix(result.corrections) @ module.correction_to_measurement_flips).toarray() % 2
            records ^= updates.astype(bool)
        offset += module.num_measurements
    return labels, records


def test_manual_saved_measurement_arrays_bit_exact_against_hex(tmp_path, monkeypatch):
    point = ExperimentPoint("fig4d_reproduction", 3, .02, 3, 3, 2)
    model = HexFullKnill(point, seed=9)
    legacy = capture_legacy(point, monkeypatch)
    assert str(model.engine.circuit) == str(legacy.circuit)
    # Explicit raw patterns, no random sampling or aggregate-count comparison.
    indices = np.arange(model.engine.circuit.num_measurements)
    raw = np.array([indices < 0, indices % 3 == 0, indices % 7 < 3, indices >= 0], dtype=bool)
    np.save(tmp_path / "raw.npy", raw)
    saved = np.load(tmp_path / "raw.npy")
    expected_labels, expected_records = legacy_process(legacy, saved)
    actual = model.decode_batch(saved)
    assert np.array_equal(actual.corrected_measurements, expected_records)
    assert np.array_equal(actual.logical_error, expected_labels)
    assert set(actual.logical_error.tolist()) == {False, True}


@pytest.mark.parametrize("errors,shots,expected", [
    (0, 10, (0., .3208873057505457)),
    (1, 10, (0., .42596773739483207)),
    (5, 10, (.23659309051256405, .763406909487436)),
    (10, 10, (.6791126942494542, 1.)),
])
def test_agresti_coull_numerical_fixture(errors, shots, expected):
    assert agresti_coull(errors, shots) == pytest.approx(expected, abs=1e-14)


@pytest.mark.parametrize("errors,shots", [(-1, 2), (3, 2), (0, 0), (True, 3), (1, 2.)])
def test_agresti_coull_invalid_counts(errors, shots):
    with pytest.raises(ValueError):
        agresti_coull(errors, shots)


def test_streamed_run_counts_seed_reuse_resume_and_saved_plot(tmp_path, monkeypatch):
    import knill_bench.adapters.hex_full_knill as adapter
    doc = document(tmp_path)
    actual_model = adapter.HexFullKnill
    models = []

    def track(*args, **kwargs):
        model = actual_model(*args, **kwargs)
        models.append(model)
        return model

    monkeypatch.setattr(adapter, "HexFullKnill", track)
    path = dispatcher.dispatch(doc.source_path)
    assert len(models) == 1
    point = next(doc.config.points())
    file = path / point.filename("logical_error")
    parquet = pq.ParquetFile(file)
    labels = parquet.read()["logical_error"].to_numpy()
    assert parquet.metadata.num_rows == 7 and parquet.metadata.num_row_groups == 3
    assert parquet.read()["shot_id"].to_pylist() == list(range(7))
    assert parquet.schema_arrow.field("logical_error").type == pa.bool_()
    meta = json.loads((path / "metadata.json").read_text())
    info = meta["points"][point.case_id]
    assert meta["status"] == info["status"] == "complete"
    assert info["shots"] == 7 and info["logical_errors"] == int(labels.sum())
    assert info["seed"] == point_seed(doc.config.master_seed, point)
    assert info["execution"]["T_tel"] == 8 and info["execution"]["r_plus"] == [3] * 8
    assert info["wall_seconds"] > 0 and meta["wall_seconds"] >= info["wall_seconds"]
    assert (path / "config.yaml").read_bytes() == doc.contents
    assert {p.name for p in path.iterdir()} == {"config.yaml", "metadata.json", file.name}
    # Replaying the SAME seeded sampler with the SAME chunk partition is exact.
    replay = actual_model(point, seed=info["seed"])
    expected = np.concatenate([replay.decode_batch(replay.sample(n)).logical_error for n in (3, 3, 1)])
    assert np.array_equal(labels, expected)
    before = file.read_bytes()

    def no_simulation(*args, **kwargs):
        raise AssertionError("saved analysis/resume of complete run must not simulate")

    monkeypatch.setattr(adapter, "HexFullKnill", no_simulation)
    assert dispatcher.resume(path) == path and before == file.read_bytes()
    summary = summarize_saved(path)[0]
    assert summary["shots"] == 7 and summary["logical_errors"] == int(labels.sum())
    assert summary["conditional_ler"] == labels.mean()
    assert plot_saved(path, tmp_path / "fig.png").stat().st_size > 1000
    result = subprocess.run([sys.executable, "-m", "knill_bench.experiments.cli", "plot-fig4d",
                             str(path), "--output", str(tmp_path / "cli.png")],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert (tmp_path / "cli.png").is_file() and "cli.png" in result.stdout
    info["logical_errors"] = 1 + int(labels.sum())
    (path / "metadata.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="counts disagree"):
        summarize_saved(path)


def test_spawn_workers_match_serial_point_streams(tmp_path):
    settings = dict(sweep=dict(d=[3], p=[0., .02]), r_0="2*d", r_plus="2/3*d",
                    shots=5, batch_size=3)
    doc = document(tmp_path, **settings, workers=2)
    parallel = runner.run(doc)
    serial_doc = document(tmp_path, **settings, workers=1)
    serial = runner.run(serial_doc)
    for point in doc.config.points():
        a = pq.read_table(parallel / point.filename("logical_error"))
        b = pq.read_table(serial / point.filename("logical_error"))
        assert a.equals(b)


def test_round_multipliers_reach_all_eight_stages_and_saved_plot(tmp_path):
    doc = document(tmp_path, sweep=dict(d=[3], p=[0.]), r_0="2*d", r_plus="2/3*d", shots=3)
    path = runner.run(doc)
    case = next(doc.config.points())
    assert (case.r_0, case.r_plus) == (6, 2)
    metadata = json.loads((path / "metadata.json").read_text())
    execution = metadata["points"][case.case_id]["execution"]
    assert execution["r_0"] == [6] * 8 and execution["r_plus"] == [2] * 8
    assert execution["resource_measurements"] == [48, 16] * 8
    assert summarize_saved(path)[0]["logical_errors"] == 0
    assert "r_0=6,r_+=2" in case.filename("logical_error")
    output = plot_saved(path, tmp_path / "rounds.svg")
    assert "logical error rate" in output.read_text()
    assert "Conditional logical error rate" not in output.read_text()


def test_saved_reader_rejects_missing_rows_and_shuffled_ids(tmp_path):
    doc = document(tmp_path, shots=3)
    path = runner.run(doc)
    point = next(doc.config.points())
    file = path / point.filename("logical_error")
    original_bytes = file.read_bytes()
    table = pq.read_table(file)
    bad_ids = table.set_column(0, table.schema.field(0), pa.array([0, 2, 1], type=pa.uint64()))
    pq.write_table(bad_ids, file)
    with pytest.raises(ValueError, match="contiguous"):
        summarize_saved(path)
    pq.write_table(table.slice(0, 2), file)
    with pytest.raises(ValueError, match="row count"):
        summarize_saved(path)
    file.unlink()
    with pytest.raises(ValueError, match="missing"):
        summarize_saved(path)
    file.write_bytes(original_bytes)
    assert summarize_saved(path)[0]["shots"] == 3


def test_failed_worker_is_not_a_complete_point_and_can_restart(tmp_path, monkeypatch):
    doc = document(tmp_path, sweep=dict(d=[3], p=[0., .02]), shots=3)
    actual = runner._run_point
    calls = []

    def fail_second(*args):
        calls.append(args[1].p)
        if args[1].p == .02:
            raise RuntimeError("deliberate worker failure")
        return actual(*args)

    monkeypatch.setattr(runner, "_run_point", fail_second)
    with pytest.raises(RuntimeError, match="deliberate"):
        runner.run(doc)
    path = next((tmp_path / "runs").iterdir())
    points = list(doc.config.points())
    completed_bytes = (path / points[0].filename("logical_error")).read_bytes()
    meta = json.loads((path / "metadata.json").read_text())
    assert meta["status"] == "failed"
    assert meta["points"][points[0].case_id]["status"] == "complete"
    assert meta["points"][points[1].case_id]["shots"] == 0
    with pytest.raises(ValueError, match="complete"):
        summarize_saved(path)
    monkeypatch.setattr(runner, "_run_point", actual)
    assert dispatcher.resume(path) == path
    assert (path / points[0].filename("logical_error")).read_bytes() == completed_bytes
    assert json.loads((path / "metadata.json").read_text())["resume_count"] == 1
