"""B2: real Hex factory integration, causal gaps and aligned streamed output."""

from dataclasses import replace
import importlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pymatching
import pytest
import stim
import yaml

from hex_qec.decoders import UnsupportedProjectedModel
from hex_qec.simulation import CompiledFactory
from knill_bench.experiments import dispatcher, logical_zero_factory as runner
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config
from knill_bench.experiments.seeds import point_seed

ROOT = Path(__file__).resolve().parents[1]


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="logical_zero_factory", name="factory_test",
               output_root=str(tmp_path / "runs"), sweep=dict(d=[3], p=[.001]),
               r_0=2, r_plus=2, T_tel=1, shots=7, batch_size=3, workers=1, master_seed=711)
    raw.update(updates)
    path = tmp_path / "input.yaml"
    path.write_text("# Exact input bytes.\n" + yaml.safe_dump(raw))
    return load_config(path)


def point(T=1, p=.001, d=3):
    return ExperimentPoint("logical_zero_factory", d, p, 2, 2, T)


def tables(path, case):
    return tuple(pq.read_table(path / case.filename(name)) for name in case.tables)


def test_default_config_and_factory_kind_boundary(tmp_path):
    doc = load_config(ROOT / "configs/logical_zero_factory.yaml")
    assert doc.config.kind == "logical_zero_factory" and doc.config.T_tel == 1
    assert doc.config.r_0 == doc.config.r_plus == "d" and not doc.config.create_codecapacity_dem
    assert doc.config.decoder == "mwpm" and doc.config.noise == "hex_uniform"
    wrong = replace(point(), kind="fig4d_reproduction")
    with pytest.raises(ValueError, match="logical_zero_factory"):
        runner.compile_point(wrong, seed=7)
    invalid = document(tmp_path, kind="fig4d_reproduction")
    with pytest.raises(ValueError, match="logical_zero_factory"):
        runner.run(invalid)
    assert not (tmp_path / "runs").exists()


def test_round_multipliers_reach_native_factory_and_saved_metadata(tmp_path):
    doc = document(tmp_path, sweep=dict(d=[3], p=[0.]), r_0="2/3*d", r_plus="2*d",
                   T_tel=2, shots=3)
    path = runner.run(doc)
    case = next(doc.config.points())
    metadata = json.loads((path / "metadata.json").read_text())
    execution = metadata["points"][case.case_id]["execution"]
    assert execution["r_0"] == 2 and execution["r_plus"] == 6
    errors, gaps = tables(path, case)
    assert errors.num_rows == gaps.num_rows == 3
    assert not any(errors["logical_error"].to_pylist())
    assert all(np.all(gaps[name].to_numpy() == 3.) for name in ("gap_t001", "gap_t002"))


@pytest.mark.parametrize("d,T,p", [(3, T, p) for T in (1, 2, 3) for p in (0., .003)] + [(5, 2, 0.)])
def test_real_hex_shapes_two_reused_supports_and_finite_hamming(d, T, p):
    bundle, compiled = runner.compile_point(point(T, p, d), seed=471)
    assert len(bundle.blocks) == 2 and bundle.metadata["live_blocks"] == 2
    assert bundle.circuit.num_qubits == 2 * (2*d*d - 1)
    assert [s.consumed_block for s in bundle.stages] == ["A" if j % 2 == 0 else "B" for j in range(T)]
    assert [s.surviving_block for s in bundle.stages] == ["B" if j % 2 == 0 else "A" for j in range(T)]
    assert bundle.metadata["cnot_direction"] == "fresh_plus_to_memory"
    assert len(bundle.preparation_frames) == T + 1
    final = bundle.circuit[bundle.oracle.instructions.start:]
    assert len(final) == 1 and final[0].name == "M" and final[0].gate_args_copy() == []
    if p:
        for stage in bundle.stages:
            readout = bundle.circuit[stage.measurement.instructions.start:stage.measurement.instructions.stop]
            assert readout[0].name == "X_ERROR" and readout[0].gate_args_copy() == [p]
    for start, count in ((0, 3), (3, 4)):
        raw = compiled.sample_measurements(count)
        result = compiled.decode(raw, shot_id_start=start)
        assert result.stage_ids == tuple(range(T))
        assert result.logical_error.shape == (count,) and result.logical_error.dtype == bool
        assert result.gaps.shape == (count, T) and result.gaps.dtype == np.float64
        assert np.isfinite(result.gaps).all() and (result.gaps >= 0).all()
        assert result.gap_units == "hamming_weight" and result.frame_resolved.all()
        assert np.array_equal(result.shot_id, np.arange(start, start+count, dtype=np.uint64))
        if p == 0:
            assert not result.logical_error.any()
            assert np.all(result.gaps == d)  # Explicit finite unit-weight p0 rule.


@pytest.mark.parametrize("projected", [False, True])
def test_oracle_and_future_records_cannot_change_earlier_gaps(tmp_path, projected):
    bundle, compiled = runner.compile_point(point(2), seed=44, create_codecapacity_dem=projected)
    raw = compiled.sample_measurements(7)
    np.save(tmp_path / "raw.npy", raw)
    saved = np.load(tmp_path / "raw.npy")
    before = compiled.decode(saved)
    altered = saved.copy()
    # Flip a whole logical X support only in the terminal evaluation records.
    oracle_logical = [bundle.oracle.measurements.start + q for q in bundle.code.logical_x]
    altered[:, oracle_logical] ^= True
    after = compiled.decode(altered)
    assert np.array_equal(before.logical_error ^ True, after.logical_error)
    for name in vars(before).keys() - {"logical_error"}:
        assert np.array_equal(getattr(before, name), getattr(after, name)), name
    cutoff = bundle.stages[0].measurement.measurements.stop
    future_changed = saved.copy()
    future_changed[:, cutoff:] ^= True
    future = compiled.decode(future_changed)
    assert np.array_equal(before.gaps[:, :1], future.gaps[:, :1])
    assert np.array_equal(before.logical_byproducts[:, :1], future.logical_byproducts[:, :1])
    assert np.array_equal(raw, saved)


def test_streamed_pairs_repeatability_theta_independence_and_join(tmp_path, monkeypatch):
    doc = document(tmp_path, T_tel=3)
    original_compile, original_writer = runner.compile_point, pq.ParquetWriter
    raw_batches, compiled_points, writers = [], [], []

    def track_compile(*args, **kwargs):
        bundle, compiled = original_compile(*args, **kwargs)
        batches = []
        raw_batches.append(batches)
        compiled_points.append(compiled)

        class Tracked:
            cache_key, projected_priors = compiled.cache_key, compiled.projected_priors

            def sample_measurements(self, shots):
                raw = compiled.sample_measurements(shots)
                batches.append(raw.copy())
                return raw

            def decode(self, raw, **options):
                return compiled.decode(raw, **options)

        return bundle, Tracked()

    def track_writer(*args, **kwargs):
        writers.append(args[0])
        return original_writer(*args, **kwargs)

    monkeypatch.setattr(runner, "compile_point", track_compile)
    monkeypatch.setattr(pq, "ParquetWriter", track_writer)
    first = dispatcher.dispatch(doc.source_path)
    cut_doc = document(tmp_path, T_tel=3, theta=1e12)
    second = dispatcher.dispatch(cut_doc.source_path)
    case = next(doc.config.points())
    assert len(compiled_points) == 2 and len(writers) == 4
    assert len(raw_batches[0]) == len(raw_batches[1]) == 3
    for a, b in zip(raw_batches[0], raw_batches[1]):
        assert np.array_equal(a, b)
    for a, b in zip(tables(first, case), tables(second, case)):
        assert a.equals(b)
    errors, gaps = tables(first, case)
    assert errors["shot_id"].to_pylist() == gaps["shot_id"].to_pylist() == list(range(7))
    assert gaps.column_names == ["shot_id", "gap_t001", "gap_t002", "gap_t003"]
    assert errors.schema.field("shot_id").type == pa.uint64()
    assert errors.schema.field("logical_error").type == pa.bool_()
    assert all(gaps.schema.field(name).type == pa.float64() and gaps[name].null_count == 0
               for name in gaps.column_names[1:])
    assert errors.join(gaps, keys="shot_id", join_type="inner").num_rows == 7
    for name in case.tables:
        assert pq.ParquetFile(first / case.filename(name)).metadata.num_row_groups == 3
    assert (first / "config.yaml").read_bytes() == doc.contents
    assert {p.name for p in first.iterdir()} == {"config.yaml", "metadata.json", *[case.filename(t) for t in case.tables]}
    metadata = json.loads((first / "metadata.json").read_text())
    info = metadata["points"][case.case_id]
    assert metadata["status"] == info["status"] == "complete"
    assert info["shots"] == 7 and info["logical_errors"] == sum(errors["logical_error"].to_pylist())
    assert info["seed"] == point_seed(doc.config.master_seed, case)
    assert info["execution"]["live_blocks"] == 2 and info["execution"]["T_tel"] == 3
    assert info["execution"]["score_units"] == metadata["gap_units"] == "hamming_weight"
    assert info["execution"]["oracle"] == "terminal_ideal_Z_evaluation_only"
    assert info["execution"]["final_readout"] == metadata["final_readout"] == case.final_readout
    assert not info["execution"]["postselection"]


def test_caches_survive_all_batches_without_per_shot_construction(tmp_path, monkeypatch):
    implementation = importlib.import_module("hex_qec.simulation.factory")
    actual_sampler = implementation._compile_sampler
    actual_bundle = importlib.import_module("hex_qec.protocols.logical_zero_factory").FactoryCircuitBuilder.build
    counts = dict(bundle=0, sampler=0)

    def build(self):
        counts["bundle"] += 1
        return actual_bundle(self)

    def compile_sampler(*args, **kwargs):
        counts["sampler"] += 1
        return actual_sampler(*args, **kwargs)

    monkeypatch.setattr(implementation, "_compile_sampler", compile_sampler)
    monkeypatch.setattr(importlib.import_module("hex_qec.protocols.logical_zero_factory").FactoryCircuitBuilder, "build", build)
    bundle, compiled = runner.compile_point(point(3), seed=8)
    assert counts == dict(bundle=1, sampler=1)

    def forbidden(*args, **kwargs):
        raise AssertionError("batch processing must not construct native objects")

    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", forbidden)
    monkeypatch.setattr(implementation, "_compile_sampler", forbidden)
    monkeypatch.setattr(stim, "FlipSimulator", forbidden)
    monkeypatch.setattr(stim, "Circuit", forbidden)
    monkeypatch.setattr(runner, "compile_point", lambda *args, **kwargs: (bundle, compiled))
    case = point(3)
    result, _ = runner._run_point(tmp_path, case, 7, 3, 8)
    assert result.shots == 7 and counts == dict(bundle=1, sampler=1)


def test_projected_and_hamming_share_raw_sampler_and_seeds_but_keep_units(tmp_path, monkeypatch):
    baseline_doc = document(tmp_path, T_tel=2)
    projected_doc = document(tmp_path, T_tel=2, create_codecapacity_dem=True, theta=3.)
    baseline_point = next(baseline_doc.config.points())
    projected_point = next(projected_doc.config.points())
    assert baseline_point == projected_point
    seed = point_seed(baseline_doc.config.master_seed, baseline_point)
    bundle, hamming = runner.compile_point(baseline_point, seed=seed)
    _, projected = runner.compile_point(projected_point, seed=seed, create_codecapacity_dem=True)
    assert hamming.circuit == projected.circuit
    for count in (3, 4):
        a, b = hamming.sample_measurements(count), projected.sample_measurements(count)
        assert np.array_equal(a, b)
        result = projected.decode(b)
        assert result.gap_units == "log_weight" and np.isfinite(result.gaps).all() and (result.gaps >= 0).all()
    path = runner.run(projected_doc)
    meta = json.loads((path / "metadata.json").read_text())
    execution = meta["points"][baseline_point.case_id]["execution"]
    assert meta["gap_units"] == execution["score_units"] == "log_weight"
    assert len(execution["projected_prior_sha256"]) == len(execution["projected_model_sha256"]) == 2
    assert execution["projected_prior_sha256"] == [p.configuration_sha256 for p in projected.projected_priors]
    assert meta["projected_approximation"] == "preparation_and_earlier_stage_residual_errors_excluded_v1"
    assert meta["prior_policy"] == execution["prior_policy"] == "module_local_stim_dem"
    assert execution["preparation_residual_errors_in_prior"] is False


def test_unsupported_projected_model_fails_without_files_or_fallback(tmp_path):
    doc = document(tmp_path, sweep=dict(d=[3], p=[0.]), create_codecapacity_dem=True)
    with pytest.raises(UnsupportedProjectedModel, match="Hamming baseline"):
        runner.run(doc)
    path = next((tmp_path / "runs").iterdir())
    assert {p.name for p in path.iterdir()} == {"config.yaml", "metadata.json"}
    meta = json.loads((path / "metadata.json").read_text())
    info = next(iter(meta["points"].values()))
    assert meta["status"] == info["status"] == "failed" and info["shots"] == 0
    assert "UnsupportedProjectedModel" in info["error"]


@pytest.mark.parametrize("local_prior", [False, True])
@pytest.mark.parametrize("skip", [False, True])
def test_serial_and_spawn_streams_match_and_completed_resume_does_not_compile(tmp_path, monkeypatch, local_prior, skip):
    probabilities = [.002, .003] if local_prior else [0., .003]
    doc = document(tmp_path, sweep=dict(d=[3], p=probabilities), T_tel=2, shots=5, workers=2,
                   create_codecapacity_dem=local_prior, skip_circuit_validation=skip)
    parallel = runner.run(doc)
    serial_doc = document(tmp_path, sweep=dict(d=[3], p=probabilities), T_tel=2, shots=5,
                          create_codecapacity_dem=local_prior, skip_circuit_validation=skip)
    serial = runner.run(serial_doc)
    for case in doc.config.points():
        assert all(a.equals(b) for a, b in zip(tables(parallel, case), tables(serial, case)))
        meta = json.loads((parallel / "metadata.json").read_text())
        execution = meta["points"][case.case_id]["execution"]
        assert execution["skip_circuit_validation"] is skip
        assert execution["circuit_validation"] == ("skipped_by_configuration" if skip else "full_native")
        assert execution["preparation_frame_implementation"] == "factory_packed_preparation_frames_v1"
    before = {p.name: p.read_bytes() for p in parallel.glob("*.parquet")}

    def forbidden(*args, **kwargs):
        raise AssertionError("completed resume must not compile or sample")

    monkeypatch.setattr(runner, "compile_point", forbidden)
    assert dispatcher.resume(parallel) == parallel
    assert before == {p.name: p.read_bytes() for p in parallel.glob("*.parquet")}


@pytest.mark.parametrize("local_prior", [False, True])
def test_midpoint_failure_discards_both_files_and_resume_replays_seed(tmp_path, monkeypatch, local_prior):
    doc = document(tmp_path, sweep=dict(d=[3], p=[.002, .003] if local_prior else [0., .003]), T_tel=2,
                   create_codecapacity_dem=local_prior)
    original_compile = runner.compile_point

    def fail_midpoint(case, **options):
        bundle, compiled = original_compile(case, **options)
        if case.p != .003:
            return bundle, compiled

        class Failing:
            cache_key, projected_priors = compiled.cache_key, compiled.projected_priors
            sample_measurements = compiled.sample_measurements
            calls = 0

            def decode(self, raw, **kwargs):
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError("deliberate second-chunk failure")
                return compiled.decode(raw, **kwargs)

        return bundle, Failing()

    monkeypatch.setattr(runner, "compile_point", fail_midpoint)
    with pytest.raises(RuntimeError, match="second-chunk"):
        runner.run(doc)
    path = next((tmp_path / "runs").iterdir())
    cases = list(doc.config.points())
    preserved = {name: (path / cases[0].filename(name)).read_bytes() for name in cases[0].tables}
    assert all(not (path / cases[1].filename(name)).exists() for name in cases[1].tables)
    assert not list(path.glob(".*.incomplete")) and not list(path.glob("*.lock"))
    failed = json.loads((path / "metadata.json").read_text())
    assert failed["points"][cases[1].case_id]["shots"] == 0
    monkeypatch.setattr(runner, "compile_point", original_compile)
    assert dispatcher.resume(path) == path
    assert preserved == {name: (path / cases[0].filename(name)).read_bytes() for name in cases[0].tables}
    seed = point_seed(doc.config.master_seed, cases[1])
    _, reference = original_compile(cases[1], seed=seed, create_codecapacity_dem=local_prior)
    expected = [reference.decode(reference.sample_measurements(n), shot_id_start=start)
                for start, n in ((0, 3), (3, 3), (6, 1))]
    errors, gaps = tables(path, cases[1])
    assert np.array_equal(errors["logical_error"].to_numpy(), np.concatenate([r.logical_error for r in expected]))
    actual_gaps = np.column_stack([gaps[f"gap_t{j:03d}"].to_numpy() for j in (1, 2)])
    assert np.array_equal(actual_gaps, np.concatenate([r.gaps for r in expected]))
    meta = json.loads((path / "metadata.json").read_text())
    assert meta["status"] == "complete" and meta["resume_count"] == 1


@pytest.mark.parametrize("bad_gap", [None, np.nan, np.inf, -1.])
def test_missing_or_invalid_gap_is_not_silently_saved_as_null(tmp_path, monkeypatch, bad_gap):
    doc = document(tmp_path)
    original_compile = runner.compile_point

    def invalid(*args, **kwargs):
        bundle, compiled = original_compile(*args, **kwargs)

        class Invalid:
            cache_key, projected_priors = compiled.cache_key, compiled.projected_priors
            sample_measurements = compiled.sample_measurements

            def decode(self, raw, **options):
                result = compiled.decode(raw, **options)
                gaps = None if bad_gap is None else np.full_like(result.gaps, bad_gap)
                return replace(result, gaps=gaps)

        return bundle, Invalid()

    monkeypatch.setattr(runner, "compile_point", invalid)
    with pytest.raises(ValueError, match="finite nonnegative"):
        runner.run(doc)
    path = next((tmp_path / "runs").iterdir())
    assert {p.name for p in path.iterdir()} == {"config.yaml", "metadata.json"}
    assert json.loads((path / "metadata.json").read_text())["status"] == "failed"
