"""Read-only notebook analysis: <=6 synthetic rows, no physical sampling."""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from matplotlib.collections import FillBetweenPolyCollection

from knill_bench.analysis.saved_data import RunRegistry
from knill_bench.analysis.confidence import WilsonInterval
from knill_bench.analysis.figure_style import FigureStyle
from knill_bench.analysis.gap_processing import round_gaps
from knill_bench.analysis.notebook_plotting import NotebookPlots, cut_statistics, summarize_point
from knill_bench.data.storage_v2 import PointWriter
from knill_bench.experiments import run_v2
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.run_v2 import RunStore

GAPS = np.array([[3, 3, 3], [1, 4, 4], [4, 1, 5], [5, 5, 1], [2, 2, 2], [0, 0, 0]], float)
LABELS = np.array([1, 0, 1, 0, 0, 1], bool)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def make_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(run_v2, "collect_environment", lambda: {})
    count = 0

    def make(kind="logical_zero_factory", *, probabilities=(.001,), distances=(3,),
             gap_values=GAPS, labels=LABELS, unfinished=False, memory_gaps=False):
        nonlocal count
        count += 1
        raw = dict(schema_version=2, kind=kind, name=f"plot{count}",
                   output_root=str(tmp_path / "runs"), sweep=dict(d=list(distances), p=list(probabilities)),
                   shots=len(labels), batch_size=2)
        if kind == "se_memory":
            raw.update(rounds="2*d", get_logicalgap=memory_gaps)
        else:
            raw.update(T_tel=8 if kind == "fig4d_reproduction" else gap_values.shape[1])
        source = tmp_path / f"{count}.yaml"
        source.write_text(yaml.safe_dump(raw))
        doc = load_config(source)
        with RunStore.create(doc) as store:
            for i, point in enumerate(doc.config.points()):
                if unfinished and i:
                    continue
                store.start_point(point)
                scores = gap_values if "logical_gaps" in point.tables else None
                if kind == "se_memory" and scores is not None:
                    scores = scores[:, :1]
                with PointWriter(store.path, point, expected_shots=len(labels)) as writer:
                    writer.write_batch(np.arange(len(labels), dtype=np.uint64), labels, scores)
                    result = writer.commit()
                store.record_complete(result)
            if not unfinished:
                store.finish()
            return store.path
    return make


def test_registration_is_lazy_and_key_filter_avoids_other_files(make_saved, tmp_path, monkeypatch):
    path = make_saved()
    data = RunRegistry({"factory": path, "unavailable": tmp_path / "absent"})
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", lambda *a, **k: pytest.fail("registration performed IO"))
        RunRegistry({"arbitrary": tmp_path / "absent"}).register("another", "also_absent")
    assert len(data.select({"key": "factory", "distance": [3]})) == 1
    with pytest.raises(ValueError, match="duplicate"):
        data.register("factory", path)
    with pytest.raises(ValueError, match="unknown dataset"):
        data.select({"key": "missing"})
    with pytest.raises(ValueError, match="unknown filter"):
        data.select({"key": "factory", "typo": 1})


def test_exact_strict_cuts_and_stream_partitions(make_saved):
    path = make_saved()
    point, = RunRegistry({"f": path}).select()
    a = summarize_point(point, gaps=True, batch_size=2)
    b = summarize_point(point, gaps=True, batch_size=5)
    assert a == b
    assert a["frequency"] == {0.: 1, 1.: 1, 2.: 1, 3.: 1, 4.: 1, 5.: 1}
    stats = cut_statistics(a, [-math.inf, 0, 1, 2, 3, math.inf])
    assert stats["accepted"].tolist() == [6, 5, 2, 1, 0, 0]
    assert stats["accepted_errors"].tolist() == [3, 2, 1, 1, 0, 0]
    np.testing.assert_allclose(stats["abort"], [0, 1/6, 4/6, 5/6, 1, 1])
    np.testing.assert_allclose(stats["reduction"][:4], [0, .2, 0, -1])
    assert np.isnan(stats["ler"][-1])
    # Selection is invariant under changing truth labels.
    swapped = dict(a, errors=0, minimum_errors={v: 0 for v in a["minimum_counts"]})
    assert np.array_equal(stats["accepted"], cut_statistics(swapped, stats["threshold"])["accepted"])
    assert np.isnan(cut_statistics(swapped, [0])["reduction"]).all()


def test_all_six_figures_return_editable_matplotlib_objects(make_saved, tmp_path):
    path = make_saved(probabilities=(.001, .002))
    data = RunRegistry({"f": path})
    plots = NotebookPlots(data, batch_size=2)
    fig, ax = plots.plot_logical_error_rate(filter_by={"key": "f"}, group_by="d")
    assert ax.get_yscale() == "log" and not ax.get_title()
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [.5, .5])
    assert fig.dpi == 300
    fig, ax = plots.plot_logical_error_rate(group_by="d", per_rounds=True)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1 - .5**(1/3)] * 2)
    f = {"p": .001}
    fig, ax = plots.plot_gap_frequency(filter_by=f, group_by="d", T_idx=2)
    assert ax.collections[0].get_offsets()[:, 1].sum() == 6
    fig, ax = plots.plot_gap_frequency(filter_by=f, group_by="d", normalize=True)
    assert ax.collections[0].get_offsets()[:, 1].sum() == pytest.approx(1)
    fig, ax = plots.plot_abort(filter_by=f, group_by="d")
    np.testing.assert_allclose(ax.lines[0].get_xdata(), [0, 1, 2, 3, 4, 5])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1/6, 4/6, 5/6, 1, 1, 1])
    fig, ax, summary = plots.plot_lifetime(filter_by=f, group_by="d", gap_threshold=[1], return_summary=True)
    # Lifetimes [3,0,1,2,3,0]: all-shot mean=1.5, fractions sum to one.
    np.testing.assert_array_equal(summary[(3,)]["counts"], [[2, 1, 1, 2]])
    np.testing.assert_allclose(summary[(3,)]["fractions"].sum(axis=1), [1])
    np.testing.assert_allclose(fig.axes[1].lines[0].get_ydata(), [1.5])
    fig, ax = plots.plot_ler_reduction(filter_by=f, group_by="d")
    np.testing.assert_allclose(ax.lines[0].get_ydata()[:3], [.2, 0, -1])
    fig, ax = plots.plot_postselected_logical_error_rate(gap_threshold=[-math.inf, 1], group_by="d")
    assert ax.lines[0].get_color() == ax.lines[1].get_color()
    assert ax.lines[0].get_marker() != ax.lines[1].get_marker()
    assert ax.lines[0].get_linestyle() != ax.lines[1].get_linestyle()
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [.5, .5])
    ax.set_ylabel("Edited in notebook")
    plots.style.save(fig, tmp_path / "test.pdf")
    plots.style.save(fig, tmp_path / "test.png")
    assert (tmp_path / "test.pdf").stat().st_size > 1000


def test_memory_and_fig4d_normalization_and_missing_gap(make_saved):
    memory = make_saved("se_memory")
    fig4d = make_saved("fig4d_reproduction")
    plots = NotebookPlots({"memory": memory, "fig4d": fig4d})
    _, ax = plots.plot_logical_error_rate(per_rounds=True)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1 - .5**(1/6)])
    np.testing.assert_allclose(ax.lines[1].get_ydata(), [1 - .5**(1/8)])
    with pytest.raises(ValueError, match="no logical_gaps"):
        plots.plot_gap_frequency(filter_by={"key": "memory"})
    memory = make_saved("se_memory", memory_gaps=True)
    plots = NotebookPlots({"m": memory})
    plots.plot_gap_frequency()
    plots.plot_abort()
    with pytest.raises(ValueError, match="requires logical_zero_factory"):
        plots.plot_lifetime()


def test_groups_filters_and_single_p_or_d_constraints(make_saved):
    a = make_saved(probabilities=(.001, .002), distances=(3, 5))
    b = make_saved()
    plots = NotebookPlots({"a": a, "b": b})
    with pytest.raises(ValueError, match="multiple physical"):
        plots.plot_abort(group_by="d")
    with pytest.raises(ValueError, match="mixes key"):
        plots.plot_logical_error_rate(group_by="d")
    with pytest.raises(ValueError, match="mixes d"):
        plots.plot_logical_error_rate(filter_by={"key": "a"}, group_by="key")
    with pytest.raises(ValueError, match="at least one"):
        plots.plot_ler_reduction(filter_by={"key": "a"})
    with pytest.raises(ValueError, match="at least one"):
        plots.plot_ler_reduction(filter_by={"key": "a", "d": [3, 5], "p": [.001, .002]})
    plots.plot_ler_reduction(filter_by={"key": "a", "distance": 3})
    with pytest.raises(ValueError, match="exactly one"):
        plots.plot_postselected_logical_error_rate(gap_threshold=[0], group_by=("key", "d"))
    _, ax = plots.plot_postselected_logical_error_rate(filter_by={"key": "a"}, gap_threshold=[0, 1])
    assert ax.lines[0].get_color() != ax.lines[2].get_color()
    with pytest.raises(ValueError, match="unknown group"):
        plots.plot_gap_frequency(group_by="typo")


@pytest.mark.parametrize("thresholds", [[], [True], [float("nan")], [1, 1], ["1"], 1])
def test_invalid_thresholds(make_saved, thresholds):
    plots = NotebookPlots({"f": make_saved()})
    with pytest.raises(ValueError, match="gap_threshold"):
        plots.plot_abort(gap_threshold=thresholds)


def test_lifetime_unique_limit_and_explicit_thresholds(make_saved):
    scores = np.arange(18, dtype=float).reshape(6, 3)
    plots = NotebookPlots({"f": make_saved(gap_values=scores)})
    with pytest.raises(ValueError, match="11 or more"):
        plots.plot_lifetime()
    plots.plot_lifetime(gap_threshold={0, 10, 20})


def test_complete_points_in_incomplete_run_and_count_tamper(make_saved):
    path = make_saved(probabilities=(.001, .002), unfinished=True)
    plots = NotebookPlots({"f": path})
    with pytest.warns(UserWarning, match="Skipped 1"):
        _, ax = plots.plot_logical_error_rate()
    assert len(ax.lines[0].get_xdata()) == 1
    meta_path = path / "metadata.json"
    meta = json.loads(meta_path.read_text())
    for info in meta["points"].values():
        if info["status"] == "complete":
            info["logical_errors"] -= 1
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="counts disagree"), pytest.warns(UserWarning):
        plots.plot_logical_error_rate()


@pytest.mark.parametrize("damage", ["ids", "null", "nan", "negative", "missing", "schema", "config", "units"])
def test_corruption_raises_before_figure(make_saved, damage):
    path = make_saved()
    file = next(path.glob("logical_gaps__*"))
    if damage == "missing":
        file.unlink()
    elif damage in {"config", "units"}:
        meta_path = path / "metadata.json"
        meta = json.loads(meta_path.read_text())
        meta["gap_units" if damage == "units" else "config_hash"] = "changed"
        meta_path.write_text(json.dumps(meta))
    else:
        table = pq.read_table(file)
        if damage == "ids":
            table = table.set_column(0, table.schema.field(0), pa.array([0, 2, 1, 3, 4, 5], type=pa.uint64()))
        elif damage == "schema":
            table = table.set_column(1, pa.field("bad", pa.float64()), table.column(1))
        else:
            value = {"null": None, "nan": math.nan, "negative": -1}[damage]
            table = table.set_column(1, table.schema.field(1), pa.array([value, *GAPS[1:, 0]], type=pa.float64()))
        pq.write_table(table, file, row_group_size=3)
    with pytest.raises(ValueError):
        NotebookPlots({"f": path}).plot_abort()
    assert not plt.get_fignums()


def test_aps_style_is_local_and_overrideable():
    original = matplotlib.rcParams.copy()
    style = FigureStyle(settings={"font.size": 11})
    with style.context():
        assert matplotlib.rcParams["pdf.fonttype"] == 42
        assert matplotlib.rcParams["font.size"] == 11
        assert matplotlib.rcParams["axes.labelsize"] == 14
        assert matplotlib.rcParams["xtick.labelsize"] == 13
        assert matplotlib.rcParams["mathtext.fontset"] == "cm"
        assert matplotlib.rcParams["savefig.dpi"] == 300
        fig, ax = style.axes()
        np.testing.assert_allclose(fig.get_size_inches(), [6, 3.6])
    assert matplotlib.rcParams["font.size"] == original["font.size"]
    assert matplotlib.rcParams["figure.figsize"] == original["figure.figsize"]


def test_unique_return_is_grouped_and_contains_every_stage(make_saved):
    plots = NotebookPlots({"f": make_saved(distances=(3, 5))})
    fig, ax, unique = plots.plot_gap_frequency(group_by="d", T_idx=2, return_unique=True)
    assert set(unique) == {(3,), (5,)}
    for group in unique.values():
        assert group == {j: sorted(set(GAPS[:, j - 1])) for j in (1, 2, 3)}
    np.testing.assert_array_equal(ax.collections[0].get_offsets()[:, 0], unique[(3,)][2])
    assert len(plots.plot_gap_frequency(group_by="d")) == 2
    with pytest.raises(ValueError, match="return_unique"):
        plots.plot_gap_frequency(return_unique="yes")


def test_decimal_rounding_uses_half_up_without_mutating_scores():
    values = np.array([[1.25, 1.35, 2.675, 0.005], [1.249999999, 1.250000001, 15., 25.]])
    original = values.copy()
    np.testing.assert_array_equal(round_gaps(values, 1), [[1.3, 1.4, 2.7, 0.], [1.2, 1.3, 15., 25.]])
    assert round_gaps(np.array([2.675, .005]), 2).tolist() == [2.68, .01]
    assert round_gaps(np.array([15., 25.]), -1).tolist() == [20., 30.]
    assert round_gaps(values, None) is values
    np.testing.assert_array_equal(values, original)


def test_rounding_is_consistent_across_all_gap_figures_and_both_lifetime_passes(make_saved):
    scores = np.array([[1.04, 1.2, 3.], [1.05, 4., 4.], [4., 1.04, 5.],
                       [5., 5., 1.05], [2.675, 2.6749999999999994, 2.675], [.04, .05, .06]])
    path = make_saved(gap_values=scores)
    plots = NotebookPlots({"f": path}, round_digit=1, batch_size=2)
    _, ax, unique = plots.plot_gap_frequency(group_by="d", return_unique=True)
    assert unique[(3,)][1] == [0., 1., 1.1, 2.7, 4., 5.]
    _, raw_ax = plots.plot_gap_frequency(round_digit=None)
    assert scores[0, 0] in raw_ax.collections[0].get_offsets()[:, 0]
    _, merged_ax = plots.plot_gap_frequency(round_digit=0)
    assert 2 in merged_ax.collections[0].get_offsets()[:, 1]
    _, ax = plots.plot_abort(gap_threshold=[1.])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [3/6])
    _, ax = plots.plot_abort(gap_threshold=[1.], round_digit=None)
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1/6])
    _, ax = plots.plot_ler_reduction(filter_by={"d": 3}, gap_threshold=[1.])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [1.])
    _, ax = plots.plot_postselected_logical_error_rate(gap_threshold=[1.])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [0.])
    fig, ax = plots.plot_lifetime(gap_threshold=[1.])
    np.testing.assert_allclose(fig.axes[1].lines[0].get_ydata(), [10/6])
    fig, ax = plots.plot_lifetime(gap_threshold=[1.], round_digit=None)
    np.testing.assert_allclose(fig.axes[1].lines[0].get_ydata(), [15/6])
    point, = plots.data.select()
    a = summarize_point(point, gaps=True, round_digit=1, unique_by_stage=True, batch_size=2)
    b = summarize_point(point, gaps=True, round_digit=1, unique_by_stage=True, batch_size=5)
    assert a == b
    # Unselected labels/normalization do not depend on rounding.
    _, ax = plots.plot_logical_error_rate()
    np.testing.assert_allclose(ax.lines[0].get_ydata(), [.5])


def test_rounding_precedes_unique_grid_limit_and_does_not_hide_invalid_raw_scores(make_saved):
    scores = 1. + np.arange(18, dtype=float).reshape(6, 3) * .001
    plots = NotebookPlots({"f": make_saved(gap_values=scores)}, round_digit=0)
    _, ax = plots.plot_lifetime()
    assert [t.get_text() for t in ax.get_xticklabels()] == ["1"]
    path = make_saved(gap_values=scores)
    file = next(path.glob("logical_gaps__*"))
    table = pq.read_table(file)
    table = table.set_column(1, table.schema.field(1), pa.array([-.01, *scores[1:, 0]], type=pa.float64()))
    pq.write_table(table, file)
    plots = NotebookPlots({"f": path}, round_digit=0)
    with pytest.raises(ValueError, match="finite and nonnegative"):
        plots.plot_abort()


@pytest.mark.parametrize("digits", [True, 1.5, "2", 309, -309])
def test_invalid_rounding_rejected_before_io(digits):
    with pytest.raises(ValueError, match="round_digit"):
        NotebookPlots({"missing": "/nonexistent"}, round_digit=digits)
    with pytest.raises(ValueError, match="round_digit"):
        NotebookPlots({"missing": "/nonexistent"}).plot_abort(round_digit=digits)


def test_lifetime_stacked_fractions_means_and_first_failure(make_saved):
    plots = NotebookPlots({"f": make_saved(distances=(3, 5))}, batch_size=2)
    cuts = [-math.inf, 0, 1, 2, math.inf]
    fig, ax, summaries = plots.plot_lifetime(group_by="d", gap_threshold=cuts, return_summary=True)
    assert len(fig.axes) == 2
    assert ax.get_ylabel() == "Shot fraction"
    expected = np.array([[0, 0, 0, 6], [1, 0, 0, 5], [2, 1, 1, 2], [3, 1, 1, 1], [6, 0, 0, 0]])
    for summary in summaries.values():
        np.testing.assert_array_equal(summary["counts"], expected)
        np.testing.assert_allclose(summary["fractions"], expected / 6)
        np.testing.assert_allclose(summary["mean_lifetime"], [3, 2.5, 1.5, 1, 0])
        assert (np.diff(summary["mean_lifetime"]) <= 0).all()
    # Every grouped stack conserves one full population, even at -/+infinity.
    for group_index in range(2):
        height = sum(np.array([bar.get_height() for bar in container])
                     for container in ax.containers[group_index * 4:(group_index + 1) * 4])
        np.testing.assert_allclose(height, np.ones(5))
    assert len(fig.axes[1].lines) == 2
    fig, ax = plots.plot_lifetime(group_by="d", gap_threshold=[1], show_mean=False)
    assert len(fig.axes) == 1
    assert len(fig.legends) == 2  # both stage and group legends remain
    assert not ax.lines  # no former outlier/median markers


def test_lifetime_summary_is_partition_and_label_independent(make_saved):
    path = make_saved()
    plots = NotebookPlots({"f": path}, batch_size=2)
    options = dict(gap_threshold=[0, 1, 2], group_by="d", return_summary=True)
    _, _, before = plots.plot_lifetime(**options)
    plots.batch_size = 5
    _, _, repartitioned = plots.plot_lifetime(**options)
    error_file = next(path.glob("logical_error__*"))
    table = pq.read_table(error_file)
    pq.write_table(table.set_column(1, table.schema.field(1), pa.array(~LABELS)), error_file, row_group_size=3)
    _, _, relabeled = plots.plot_lifetime(**options)
    for after in (repartitioned, relabeled):
        for field in ("thresholds", "counts", "fractions", "mean_lifetime"):
            np.testing.assert_array_equal(before[(3,)][field], after[(3,)][field])


@pytest.mark.parametrize("options", [dict(show_mean="yes"), dict(return_summary=1)])
def test_lifetime_invalid_options_rejected_before_io(options):
    with pytest.raises(ValueError, match="must be bool"):
        NotebookPlots({"missing": "/nonexistent"}).plot_lifetime(**options)


def _bands(ax):
    return [artist for artist in ax.collections if isinstance(artist, FillBetweenPolyCollection)]


def test_wilson_shade_on_every_nonstacked_plot_and_accepted_denominator(make_saved):
    plots = NotebookPlots({"f": make_saved(probabilities=(.001, .002))})
    _, ax = plots.plot_logical_error_rate()
    assert len(_bands(ax)) == 1
    expected = plots.interval.bounds(3, 6)
    vertices = _bands(ax)[0].get_paths()[0].vertices
    np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()], expected)
    _, ax = plots.plot_logical_error_rate(per_rounds=True)
    vertices = _bands(ax)[0].get_paths()[0].vertices
    np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()], plots.interval.per_round(3, 6, 3))
    for normalize in (False, True):
        _, ax = plots.plot_gap_frequency(filter_by={"p": .001}, normalize=normalize)
        assert len(_bands(ax)) == 1
        vertices = _bands(ax)[0].get_paths()[0].vertices
        np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()],
                                   plots.interval.frequency(1, 6, normalize=normalize))
    _, ax = plots.plot_abort(filter_by={"p": .001})
    assert len(_bands(ax)) == 1
    _, ax = plots.plot_ler_reduction(filter_by={"p": .001})
    assert len(_bands(ax)) == 1
    _, ax = plots.plot_postselected_logical_error_rate(gap_threshold=[1, 99])
    # Cut=1 retains two shots, one error. Cut=99 retains none: no made-up band.
    assert len(_bands(ax)) == 1
    vertices = _bands(ax)[0].get_paths()[0].vertices
    np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()], plots.interval.bounds(1, 2))
    fig, ax = plots.plot_lifetime(filter_by={"p": .001}, gap_threshold=[1, 2])
    assert not any(_bands(axis) for axis in fig.axes)


def test_undefined_reduction_has_no_shade_and_shared_interval_configuration(make_saved):
    plots = NotebookPlots({"f": make_saved(labels=np.zeros(6, bool))}, interval=WilsonInterval(.99))
    _, ax = plots.plot_ler_reduction(filter_by={"p": .001})
    assert not _bands(ax)
    assert np.isnan(ax.lines[0].get_ydata()).all()
    _, ax = plots.plot_logical_error_rate()
    assert len(_bands(ax)) == 1  # zero observed errors still have a nonzero upper bound
    with pytest.raises(ValueError, match="interval"):
        NotebookPlots({"missing": "/nonexistent"}, interval="wilson")
