"""Ordinary Hex memory and opposite-class costs; physical batches <=7 shots."""

from dataclasses import replace
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pymatching
import pytest
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp
import yaml

from hex_qec.circuit_generation import get_parity_check_matrices, stabilizer_measurement_circuit
from knill_bench.adapters.hex_memory import HexMemory
from knill_bench.decoding.observable_gap import ObservableMWPM
from knill_bench.experiments import adaptive_execution, dispatcher, se_memory as runner
from knill_bench.experiments.config_v2 import load_config, parse_config
from knill_bench.experiments.seeds import chunk_seed, point_seed

ROOT = Path(__file__).resolve().parents[1]


def raw_config(**updates):
    raw = dict(schema_version=2, kind="se_memory", name="memory_test",
               sweep=dict(d=[3], p=[.003]), rounds="d", shots=7,
               batch_size=3, buffer_shot=3, workers=1, master_seed=317)
    return dict(raw, **updates)


def document(tmp_path, **updates):
    path = tmp_path / "memory.yaml"
    path.write_text("# Exact memory input.\n" + yaml.safe_dump(raw_config(output_root=str(tmp_path / "runs"), **updates)))
    return load_config(path)


def tables(run, point):
    return tuple(pq.read_table(run / point.filename(name)) for name in point.tables)


@pytest.mark.parametrize("rounds,expected", [("d", (3, 5)), ("2/3*d", (2, 3)), (2, (2, 2))])
def test_memory_config_rounds_identity_filename_and_optional_tables(rounds, expected):
    config = parse_config(raw_config(sweep=dict(d=[3, 5], p=[.003]), rounds=rounds))
    assert parse_config(config.as_dict()) == config
    assert tuple(point.rounds for point in config.points()) == expected
    assert config.gap_units is None and config.prior_policy == "full_circuit_stim_dem"
    for point in config.points():
        assert point.tables == ("logical_error",) and point.r_0 == point.r_plus == 0
        assert f",rounds={point.rounds}.parquet" in point.filename("logical_error")
        gap_point = replace(point, get_logicalgap=True)
        assert gap_point.case_id == point.case_id and gap_point.sampling_identity == point.sampling_identity
        assert gap_point.tables == ("logical_error", "logical_gaps")
        assert point_seed(config.master_seed, point) == point_seed(config.master_seed, gap_point)
        assert chunk_seed(config.master_seed, point, 3) == chunk_seed(config.master_seed, gap_point, 3)
        assert "T_tel" not in point.sampling_identity and "r_plus" not in point.sampling_identity
        assert point.sampling_identity["initial_boundary"] == "noisy_physical_zero"
    old_fields = {"T_tel", "r_0", "r_plus", "create_codecapacity_dem", "theta"}
    assert not old_fields & config.as_dict().keys()


@pytest.mark.parametrize("updates", [
    dict(rounds="d-1"), dict(rounds="1/4*d"), dict(rounds=0), dict(rounds=True),
    dict(get_logicalgap=1), dict(get_logicalgap="true"), dict(get_logicalgap=[True]),
    dict(T_tel=1), dict(r_0="d"), dict(r_plus="d"), dict(theta=None),
    dict(create_codecapacity_dem=False), dict(skip_circuit_validation=True),
    dict(get_logicalgap=True, sweep=dict(d=[3], p=[0.])),
    dict(get_logicalgap=True, sweep=dict(d=[3], p=[.5])),
    dict(sweep=dict(d=[3], p=[.003], rounds=[1, 2])),
])
def test_invalid_memory_options_rejected_before_output(updates):
    with pytest.raises(ValueError):
        parse_config(raw_config(**updates))


@pytest.mark.parametrize("kind", ["fig4d_reproduction", "logical_zero_factory"])
def test_memory_options_do_not_leak_to_existing_kinds(kind):
    for option in (dict(rounds="d"), dict(get_logicalgap=False)):
        raw = dict(schema_version=2, kind=kind, sweep=dict(d=[3], p=[.003]), **option)
        with pytest.raises(ValueError, match="only for se_memory"):
            parse_config(raw)


@pytest.mark.parametrize("d,rounds", [(3, 1), (3, 3), (5, 5)])
def test_native_circuit_exact_rounds_full_noisy_boundaries_and_labels(d, rounds):
    point = next(parse_config(raw_config(sweep=dict(d=[d], p=[.003]), rounds=rounds)).points())
    model = HexMemory(point, seed=81)
    direct = stabilizer_measurement_circuit(get_parity_check_matrices("surface", d), "z", rounds, .003,
                                           disable_final_detectors=False, surface_code=True)
    assert model.circuit == direct and direct.num_observables == 1
    assert direct.num_measurements == rounds * (d*d - 1) + d*d
    assert direct.num_qubits == 2*d*d - 1
    assert direct[0].name == "R" and direct[1].name == "X_ERROR"
    assert direct[1].gate_args_copy() == [.003]
    measurements = [instruction for instruction in direct if instruction.name == "M"]
    assert len(measurements) == 1 and len(measurements[0].targets_copy()) == d*d
    assert model.metadata["final_readout_error"] == .003
    assert not model.metadata["terminal_ideal_oracle"]
    raw = model.sample(7)
    untouched = raw.copy()
    result = model.decode_batch(raw)
    detectors, actual = model.converter.convert(measurements=raw, separate_observables=True)
    dem = direct.detector_error_model()
    matching = pymatching.Matching.from_detector_error_model(dem)
    expected = matching.decode_batch(detectors).ravel().astype(bool) ^ actual[:, 0]
    assert np.array_equal(result.logical_error, expected)
    assert result.gaps is None and np.array_equal(raw, untouched)


@pytest.mark.parametrize("d", [3, 5])
def test_optional_gap_preserves_first_decode_and_truth_isolation(d):
    point = next(parse_config(raw_config(sweep=dict(d=[d], p=[.003]))).points())
    plain, scored = HexMemory(point, seed=81), HexMemory(replace(point, get_logicalgap=True), seed=81)
    raw = plain.sample(7)
    assert np.array_equal(raw, scored.sample(7)) and plain.circuit == scored.circuit
    a, b = plain.decode_batch(raw), scored.decode_batch(raw)
    assert np.array_equal(a.logical_error, b.logical_error)
    assert b.gaps.shape == (7, 1) and b.gaps.dtype == np.float64
    assert np.isfinite(b.gaps).all() and (b.gaps >= 0).all()
    altered = raw.copy()
    logical_x = get_parity_check_matrices("surface", d)[2].nonzero()[1]
    altered[:, raw.shape[1] - d*d + logical_x] ^= True
    det, actual = scored.converter.convert(measurements=raw, separate_observables=True)
    det_changed, actual_changed = scored.converter.convert(measurements=altered, separate_observables=True)
    assert np.array_equal(det, det_changed) and np.all(actual ^ actual_changed)
    changed = scored.decode_batch(altered)
    assert np.array_equal(changed.logical_error, ~b.logical_error)
    assert np.array_equal(changed.gaps, b.gaps)
    decoded = scored.decode_detectors(det)
    assert np.all((decoded.correction @ scored.decoder.h.T % 2) == det)
    assert np.all((decoded.opposite_correction @ scored.decoder.h.T % 2) == det)
    first_class = (decoded.correction @ scored.decoder.l.T % 2).ravel()
    opposite_class = (decoded.opposite_correction @ scored.decoder.l.T % 2).ravel()
    assert np.all(first_class ^ opposite_class)
    assert np.allclose(decoded.gap, decoded.opposite_weight - decoded.weight)


def test_spacetime_gap_independent_binary_integer_optimization():
    point = next(parse_config(raw_config(get_logicalgap=True, rounds=1)).points())
    model = HexMemory(point, seed=91)
    decoder = model.decoder
    n, m = decoder.h.shape[1], decoder.h.shape[0]
    faults = np.zeros((3, n), dtype=np.uint8)
    faults[1, 0] = 1
    faults[2, [n//3, n//2]] = 1
    syndromes = faults @ decoder.h.T % 2
    result = decoder.decode_batch(syndromes)
    constraint = sparse.vstack((decoder.h, decoder.l), format="csc")
    matrix = sparse.hstack((constraint, -2 * sparse.eye(m + 1)), format="csc")
    objective = np.r_[decoder.weights, np.zeros(m + 1)]
    bounds = Bounds(np.zeros(n + m + 1), np.r_[np.ones(n), np.full(m + 1, n)])
    for row, s in enumerate(syndromes):
        sector_costs = []
        for sector in (0, 1):
            rhs = np.r_[s, sector].astype(float)
            exact = milp(objective, integrality=np.ones(len(objective)), bounds=bounds,
                         constraints=LinearConstraint(matrix, rhs, rhs),
                         options=dict(mip_rel_gap=0., time_limit=5.))
            assert exact.success, exact.message
            sector_costs.append(exact.fun)
        assert result.weight[row] == pytest.approx(min(sector_costs), abs=1e-9)
        assert result.opposite_weight[row] == pytest.approx(sector_costs[1 ^ int(result.prediction[row])], abs=1e-9)
        assert result.gap[row] == pytest.approx(abs(sector_costs[1] - sector_costs[0]), abs=1e-9)


def test_small_graph_exhaustive_minima_ties_and_first_class_preserved():
    h = sparse.csc_matrix([[1, 1, 0, 1], [0, 1, 1, 0]], dtype=np.uint8)
    l = sparse.csc_matrix([[0, 0, 1, 1]], dtype=np.uint8)
    weights = np.array([1., 2., 1., 1.])
    scored = ObservableMWPM(h, l, weights, get_logicalgap=True)
    plain = ObservableMWPM(h, l, weights)
    faults = np.array(list(product((0, 1), repeat=4)), dtype=np.uint8)
    syndromes = np.array(list(product((0, 1), repeat=2)), dtype=np.uint8)
    decoded = scored.decode_batch(syndromes)
    assert np.array_equal(decoded.correction, plain.decode_batch(syndromes).correction)
    for row, s in enumerate(syndromes):
        feasible = faults[np.all(faults @ h.T % 2 == s, axis=1)]
        classes = (feasible @ l.T % 2).ravel()
        costs = [np.min((feasible @ weights)[classes == sector]) for sector in (0, 1)]
        assert decoded.weight[row] == min(costs)
        assert decoded.opposite_weight[row] == costs[1 ^ int(decoded.prediction[row])]
        assert decoded.gap[row] == abs(costs[1] - costs[0])
    assert (decoded.gap == 0).any()
    assert np.all(np.diff(scored.extended.indptr) == 2)  # No degree-three row append.


@pytest.mark.parametrize("h,l,w", [
    ([[1], [1], [1]], [[0]], [1.]),  # Hyperedge.
    ([[0]], [[1]], [1.]),           # Unobservable detector-free logical event.
    ([[1]], [[1]], [0.]),           # Nonpositive gap prior.
    ([[1]], [[0]], [1.]),           # Unreachable opposite class.
    ([[1, 1], [1, 1]], [[0, 1]], [1., 1.]),  # Inconsistent internal observable cycle.
])
def test_unsupported_gap_models_raise_without_fallback(h, l, w):
    with pytest.raises(ValueError):
        ObservableMWPM(h, l, w, get_logicalgap=True)


def test_decoding_reuses_both_matching_graphs(tmp_path, monkeypatch):
    point = next(document(tmp_path, get_logicalgap=True).config.points())
    model = HexMemory(point, seed=9)
    raw = model.sample(7)

    def forbidden(*args, **kwargs):
        raise AssertionError("decode rebuilt native graph/circuit/sampler")

    monkeypatch.setattr(pymatching.Matching, "from_check_matrix", forbidden)
    for part in (raw[:3], raw[3:]):
        assert model.decode_batch(part).gaps.shape == (len(part), 1)


@pytest.mark.parametrize("gap", [False, True])
@pytest.mark.parametrize("batch", [3, "auto"])
def test_runner_streams_optional_aligned_files_and_resume(tmp_path, gap, batch, monkeypatch):
    doc = document(tmp_path, get_logicalgap=gap, batch_size=batch)
    path = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    saved = tables(path, point)
    assert saved[0]["shot_id"].to_pylist() == list(range(7))
    assert saved[0].schema.field("logical_error").type == pa.bool_()
    assert len(saved) == 1 + gap
    if gap:
        assert saved[1].column_names == ["shot_id", "gap_t001"]
        assert saved[1]["shot_id"].equals(saved[0]["shot_id"])
        assert saved[1]["gap_t001"].null_count == 0
    for name in point.tables:
        file = pq.ParquetFile(path / point.filename(name))
        assert [file.metadata.row_group(i).num_rows for i in range(3)] == [3, 3, 1]
    assert {p.name for p in path.iterdir()} == {"metadata.json", "config.yaml", *[point.filename(t) for t in point.tables]}
    assert (path / "config.yaml").read_bytes() == doc.contents
    metadata = json.loads((path / "metadata.json").read_text())
    info = metadata["points"][point.case_id]
    assert info["status"] == metadata["status"] == "complete" and info["shots"] == 7
    assert info["logical_errors"] == sum(saved[0]["logical_error"].to_pylist())
    assert metadata["gap_units"] == ("log_weight" if gap else None)
    assert info["execution"]["rounds"] == 3 and info["execution"]["teleportations"] == 0
    assert info["execution"]["get_logicalgap"] is gap
    before = {p.name: p.read_bytes() for p in path.glob("*.parquet")}
    monkeypatch.setattr(HexMemory, "__init__", lambda *a, **kw: pytest.fail("completed resume compiled"))
    assert dispatcher.resume(path) == path
    assert before == {p.name: p.read_bytes() for p in path.glob("*.parquet")}


@pytest.mark.parametrize("gap", [False, True])
def test_fixed_serial_spawn_and_gap_option_preserve_physical_stream(tmp_path, gap):
    updates = dict(get_logicalgap=gap, sweep=dict(d=[3], p=[.001, .003]))
    doc = document(tmp_path, workers=2, **updates)
    parallel = dispatcher.dispatch(doc.source_path)
    serial_doc = document(tmp_path, workers=1, **updates)
    serial = dispatcher.dispatch(serial_doc.source_path)
    for point in doc.config.points():
        assert all(a.equals(b) for a, b in zip(tables(parallel, point), tables(serial, point)))


def test_fixed_gap_toggle_keeps_raw_data_labels_and_seeds(tmp_path):
    doc = document(tmp_path, get_logicalgap=False)
    plain = dispatcher.dispatch(doc.source_path)
    gap_doc = document(tmp_path, get_logicalgap=True)
    scored = dispatcher.dispatch(gap_doc.source_path)
    a, b = next(doc.config.points()), next(gap_doc.config.points())
    assert a.case_id == b.case_id
    assert tables(plain, a)[0].equals(tables(scored, b)[0])


@pytest.mark.parametrize("gap", [False, True])
def test_auto_spawn_works_for_one_memory_point(tmp_path, gap):
    doc = document(tmp_path, get_logicalgap=gap, batch_size="auto", workers=2)
    path = dispatcher.dispatch(doc.source_path)
    point = next(doc.config.points())
    assert tables(path, point)[0].num_rows == 7
    execution = json.loads((path / "metadata.json").read_text())["points"][point.case_id]["execution"]
    assert execution["parallel_execution"] == adaptive_execution.POLICY
    assert execution["chunk_count"] >= 3


def test_zero_noise_memory_without_gap_is_supported(tmp_path):
    doc = document(tmp_path, sweep=dict(d=[3, 5], p=[0.]), get_logicalgap=False)
    path = dispatcher.dispatch(doc.source_path)
    for point in doc.config.points():
        assert not any(tables(path, point)[0]["logical_error"].to_pylist())


def test_second_chunk_failure_aborts_pair_and_restarts_from_zero(tmp_path, monkeypatch):
    doc = document(tmp_path, get_logicalgap=True, sweep=dict(d=[3], p=[.001, .003]))
    original = HexMemory.decode_batch
    calls = {}

    def failing(self, raw):
        calls[self.point.p] = calls.get(self.point.p, 0) + 1
        if self.point.p == .003 and calls[self.point.p] == 2:
            raise RuntimeError("deliberate memory second-chunk failure")
        return original(self, raw)

    monkeypatch.setattr(HexMemory, "decode_batch", failing)
    with pytest.raises(RuntimeError, match="second-chunk"):
        dispatcher.dispatch(doc.source_path)
    path = next((tmp_path / "runs").iterdir())
    points = list(doc.config.points())
    before = {name: (path / points[0].filename(name)).read_bytes() for name in points[0].tables}
    assert all(not (path / points[1].filename(name)).exists() for name in points[1].tables)
    assert not list(path.glob(".*.incomplete"))
    monkeypatch.setattr(HexMemory, "decode_batch", original)
    assert dispatcher.resume(path) == path
    assert before == {name: (path / points[0].filename(name)).read_bytes() for name in points[0].tables}
    model = HexMemory(points[1], seed=point_seed(doc.config.master_seed, points[1]))
    expected = [model.decode_batch(model.sample(count)) for count in (3, 3, 1)]
    errors, gaps = tables(path, points[1])
    assert np.array_equal(errors["logical_error"].to_numpy(), np.concatenate([x.logical_error for x in expected]))
    assert np.allclose(gaps["gap_t001"].to_numpy(), np.concatenate([x.gaps[:, 0] for x in expected]))


def test_example_and_cli_validate_outside_checkout(tmp_path):
    example = ROOT / "configs/se_memory_v2_example.yaml"
    assert load_config(example).config.kind == "se_memory"
    result = subprocess.run([sys.executable, "-m", "knill_bench.experiments.cli", "validate-config", str(example)],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["config"]["get_logicalgap"] is True


@pytest.mark.parametrize("kind,config_hash,case_id", [
    ("fig4d_reproduction", "4a42559ab68f9f7baf89fa0a61f5dd6d11bbfbd94259111bb88538541d7f144a",
     "9970e8c9ab9c3968a5a1b6fc992e90c0b9bf07a9befe41f8f6879ba7fd574e66"),
    ("logical_zero_factory", "0f501388970d49333b195abb402243d52844600e5b55ac1cee50922298109679",
     "70d3ecf399ce2397d0f67f3304e97d5ccc9d228da8a4989f90b68a35668e8108"),
])
def test_existing_kind_hashes_match_pre_memory_commit(kind, config_hash, case_id):
    # Golden values obtained from config_v2.py at de21bfc, not recomputed here.
    config = parse_config(dict(schema_version=2, kind=kind, sweep=dict(d=[3], p=[.003])))
    assert config.config_hash == config_hash
    assert next(config.points()).case_id == case_id


@pytest.mark.parametrize("bad", [None, np.nan, np.inf, -1.])
@pytest.mark.parametrize("batch", [3, "auto"])
def test_invalid_requested_memory_gap_aborts_in_both_execution_modes(tmp_path, monkeypatch, bad, batch):
    doc = document(tmp_path, get_logicalgap=True, batch_size=batch)
    original = HexMemory.decode_batch

    def broken(self, raw):
        result = original(self, raw)
        return replace(result, gaps=None if bad is None else np.full_like(result.gaps, bad))

    monkeypatch.setattr(HexMemory, "decode_batch", broken)
    with pytest.raises(ValueError, match="gap"):
        dispatcher.dispatch(doc.source_path)
    path = next((tmp_path / "runs").iterdir())
    assert {p.name for p in path.iterdir()} == {"config.yaml", "metadata.json"}
    assert json.loads((path / "metadata.json").read_text())["status"] == "failed"


def test_resume_rejects_changed_gap_option_without_deleting_completed_files(tmp_path):
    doc = document(tmp_path, get_logicalgap=True)
    path = dispatcher.dispatch(doc.source_path)
    before = {p.name: p.read_bytes() for p in path.glob("*.parquet")}
    raw = yaml.safe_load((path / "config.yaml").read_bytes())
    raw["get_logicalgap"] = False
    (path / "config.yaml").write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="config changed"):
        dispatcher.resume(path)
    assert before == {p.name: p.read_bytes() for p in path.glob("*.parquet")}
