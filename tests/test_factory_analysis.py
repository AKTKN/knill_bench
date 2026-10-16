"""B3 saved-file identities, gap-only decisions, iid accounting and v2 smoke."""

from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from knill_bench.analysis.factory import AnalysisSettings, analyze_saved, load_settings, threshold_grid, write_report
from knill_bench.analysis.factory_cost import FactoryCostModel, first_rejected_stage, summarize_cost
from knill_bench.data.storage_v2 import PointWriter
from knill_bench.experiments import run_v2
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.run_v2 import RunStore

ROOT = Path(__file__).resolve().parents[1]
GAPS = np.array([[3, 3, 3], [1, 4, 4], [4, 1, 5], [5, 5, 1], [2, 2, 2], [0, 0, 0]], np.float64)
LABELS = np.array([1, 0, 1, 0, 0, 1], bool)


@pytest.fixture
def saved(tmp_path, monkeypatch):
    env = dict(bench=dict(commit="bench", source_sha256="b"), hex=dict(commit="hex", source_sha256="h"))
    monkeypatch.setattr(run_v2, "collect_environment", lambda: env)
    source = tmp_path / "input.yaml"
    source.write_text(yaml.safe_dump(dict(schema_version=2, kind="logical_zero_factory", name="analysis",
        output_root=str(tmp_path / "runs"), sweep=dict(d=[3], p=[.001]), r_0=2, r_plus=3,
        T_tel=3, shots=6, batch_size=2)))
    doc = load_config(source)
    point = next(doc.config.points())
    with RunStore.create(doc) as store:
        store.start_point(point)
        with PointWriter(store.path, point, expected_shots=6) as writer:
            for start in (0, 2, 4):
                writer.write_batch(np.arange(start, start+2, dtype=np.uint64), LABELS[start:start+2], GAPS[start:start+2])
            result = writer.commit()
        store.record_complete(result)
        store.finish()
        return store.path, point


def test_exact_gap_only_acceptance_identities_and_zero_acceptance(saved):
    path, _ = saved
    settings = AnalysisSettings(thresholds=(-math.inf, 0., 1., 2., 3., math.inf), batch_size=2, iid_restarts=True)
    report = analyze_saved(path, settings)
    rows = report["rows"]
    assert [r["accepted"] for r in rows] == [6, 6, 5, 2, 1, 0]
    assert rows[0]["abort_rate"] == 0 and rows[0]["terminal_oracle_ler"] == LABELS.mean()
    assert rows[3]["accepted_errors"] == 1 and rows[3]["terminal_oracle_ler"] == .5
    assert rows[3]["abort_rate"] == pytest.approx(2/3)
    assert rows[3]["first_rejected_counts"] == [2, 1, 1]
    assert rows[3]["mean_attempt_cost"] == 8.5 and rows[3]["iid_cost_to_first_accepted"] == 25.5
    assert rows[3]["iid_expected_attempts"] == 3
    assert rows[-1]["terminal_oracle_ler"] is rows[-1]["terminal_oracle_ler_lower"] is None
    assert rows[-1]["iid_cost_to_first_accepted"] is None
    assert rows[-1]["iid_estimate_status"] == "undefined_no_observed_acceptance"
    assert rows[-1]["acceptance_upper"] > 0 and rows[-1]["abort_upper"] == 1.
    assert all(sum(r["first_rejected_counts"])+r["accepted"] == 6 for r in rows)
    assert report["estimand"] == "conditional_terminal_factory_oracle_error"
    assert "pointwise" in report["interval"]
    json.dumps(report, allow_nan=False)
    # Chunk partition affects neither statistics nor paired cost uncertainty.
    assert rows == analyze_saved(path, replace(settings, batch_size=5))["rows"]


def test_first_rejection_ignores_later_gaps_and_labels_do_not_select(saved):
    path, point = saved
    first = first_rejected_stage(GAPS, 2.)
    assert first.tolist() == [0, 1, 2, 3, 0, 1]
    later = GAPS.copy()
    later[1, 1:] = [0, 100]
    later[2, 2] = 0
    assert np.array_equal(first, first_rejected_stage(later, 2.))
    before = analyze_saved(path)
    file = path / point.filename("logical_error")
    table = pq.read_table(file)
    pq.write_table(table.set_column(1, table.schema.field(1), pa.array(~LABELS)), file, row_group_size=3)
    # Complement keeps the total error count equal in this six-row fixture.
    after = analyze_saved(path)
    for a, b in zip(before["rows"], after["rows"]):
        for key in ("accepted", "first_rejected_counts", "mean_attempt_cost", "abort_rate", "iid_cost_to_first_accepted"):
            assert a[key] == b[key]
    assert before["rows"][-2]["terminal_oracle_ler"] != after["rows"][-2]["terminal_oracle_ler"]


def test_cost_schedule_reset_decoding_overlap_and_iid_gate(saved):
    _, point = saved
    serial = FactoryCostModel(unit="microsecond", initial_preparation="serial", se_round=2., reset=1.,
                              preparation_decode=3., teleportation=4., online_decode=5., restart=7.)
    # Initial (1+4+3)+(1+6+3)=18; each teleport=9, refresh=10.
    assert np.array_equal(serial.prefix_costs(point), [27, 46, 65])
    parallel = replace(serial, initial_preparation="parallel")
    assert np.array_equal(parallel.prefix_costs(point), [19, 38, 57])
    hist = np.array([2, 2, 1, 1])
    result = summarize_cost(hist, point, serial, iid_restarts=True)
    costs = np.array([65, 34, 53, 72, 65, 34], float)
    accept = np.array([1, 0, 0, 0, 1, 0], bool)
    expected = costs.mean()/accept.mean()
    assert result["mean_attempt_cost"] == pytest.approx(costs.mean())
    assert result["iid_cost_to_first_accepted"] == pytest.approx(expected)
    assert result["attempt_cost_standard_error"] == pytest.approx(costs.std(ddof=1)/math.sqrt(6))
    residual = costs - expected*accept
    assert result["iid_cost_standard_error"] == pytest.approx(residual.std(ddof=1)/math.sqrt(6)/accept.mean())
    no_iid = summarize_cost(hist, point, serial)
    assert no_iid["iid_cost_to_first_accepted"] is None and no_iid["iid_estimate_status"] == "not_assumed"
    # One survivor per full T attempt, rather than T produced resources.
    all_accepted = summarize_cost([6, 0, 0, 0], point, serial, iid_restarts=True)
    assert all_accepted["iid_expected_attempts"] == 1 and all_accepted["iid_cost_to_first_accepted"] == 65
    single = summarize_cost([1, 0, 0, 0], point, serial, iid_restarts=True)
    assert single["attempt_cost_standard_error"] is single["iid_cost_standard_error"] is None


@pytest.mark.parametrize("damage", ["ids", "null", "nan", "negative", "missing", "counts", "unfinished", "units"])
def test_saved_pair_integrity_errors_are_not_silent_filters(saved, damage):
    path, point = saved
    file = path / point.filename("logical_gaps")
    meta_file = path / "metadata.json"
    meta = json.loads(meta_file.read_text())
    if damage in {"ids", "null", "nan", "negative"}:
        table = pq.read_table(file)
        if damage == "ids":
            table = table.set_column(0, table.schema.field(0), pa.array([0, 2, 1, 3, 4, 5], type=pa.uint64()))
        else:
            values = [None if damage == "null" else float("nan") if damage == "nan" else -1., *GAPS[1:, 0]]
            table = table.set_column(1, table.schema.field(1), pa.array(values, type=pa.float64()))
        pq.write_table(table, file)
    elif damage == "missing":
        file.unlink()
    elif damage == "counts":
        meta["points"][point.case_id]["logical_errors"] += 1
    elif damage == "unfinished":
        meta["status"] = "running"
    elif damage == "units":
        meta["gap_units"] = "log_weight"
    meta_file.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        analyze_saved(path)


@pytest.mark.parametrize("cost", [dict(se_round=0), dict(reset=-1), dict(online_decode=float("nan")),
                                 dict(teleportation=True), dict(unit=""), dict(initial_preparation="guessed")])
def test_cost_validation(cost):
    with pytest.raises(ValueError):
        FactoryCostModel(**cost)


def test_analysis_templates_lists_grid_and_strict_settings(tmp_path):
    for name in ("fig4d", "logical_zero_factory"):
        doc = load_config(ROOT / f"configs/templates/{name}.yaml")
        assert doc.config.shots <= 128 and doc.config.workers == 1
    settings = load_settings(ROOT / "configs/templates/factory_analysis.yaml")
    assert settings.thresholds[0] == -math.inf and not settings.iid_restarts
    assert threshold_grid(0., 3., 4) == (0., 1., 2., 3.)
    path = tmp_path / "analysis.yaml"
    path.write_text("analysis_version: 1\nthreshold_grid: {start: 0.0, stop: 3.0, count: 4}\n")
    assert load_settings(path).thresholds == (0., 1., 2., 3.)
    for text in ("analysis_version: 1\nunknown: 2", "analysis_version: 1\nanalysis_version: 1",
                 "analysis_version: 1\nthresholds: [.nan]", "analysis_version: 1\ncost: {unknown: 1}",
                 "analysis_version: 1\nthresholds: [1]\nthreshold_grid: {start: 0, stop: 1, count: 2}"):
        path.write_text(text)
        with pytest.raises(ValueError):
            load_settings(path)


def test_optional_reports_cli_and_no_simulation_imports(saved, tmp_path):
    path, _ = saved
    before = {f.name: f.read_bytes() for f in path.iterdir()}
    report = analyze_saved(path)
    for suffix in ("json", "csv", "md"):
        assert write_report(report, tmp_path / f"report.{suffix}").stat().st_size > 100
    result = subprocess.run([sys.executable, "-m", "knill_bench.experiments.cli", "analyze-factory", str(path),
                             "--theta=-inf", "--theta=2", "--theta=inf", "--iid-restarts"],
                            cwd=tmp_path, text=True, capture_output=True, check=True)
    rows = json.loads(result.stdout)["rows"]
    assert [r["accepted"] for r in rows] == [6, 2, 0]
    assert rows[1]["iid_cost_to_first_accepted"] == 25.5
    code = "import sys; import knill_bench.analysis.factory; assert not any(m in sys.modules for m in ('stim','pymatching','hex_qec'))"
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True)
    assert before == {f.name: f.read_bytes() for f in path.iterdir()}


@pytest.mark.parametrize("kind", ["logical_zero_factory", "fig4d_reproduction"])
def test_complete_tiny_v2_smoke_each_experiment(tmp_path, kind):
    from knill_bench.experiments.dispatcher import dispatch
    from knill_bench.analysis.fig4d import summarize_saved
    source = tmp_path / "smoke.yaml"
    source.write_text(yaml.safe_dump(dict(schema_version=2, kind=kind, name="b3_smoke",
        output_root=str(tmp_path / "runs"), sweep=dict(d=[3, 5], p=[0.]), T_tel=3 if kind == "logical_zero_factory" else 8,
        r_0="d", r_plus="d", shots=3, batch_size=2)))
    path = dispatch(source)
    rows = analyze_saved(path)["rows"] if kind == "logical_zero_factory" else summarize_saved(path)
    assert rows and {r["d"] for r in rows} == {3, 5}
    assert all(r["shots"] == 3 and r["logical_errors"] == 0 for r in rows)
