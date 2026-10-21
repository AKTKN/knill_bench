"""Six editable saved-data figures; strict gap<=threshold rejection.

Every call rereads selected data. No simulator, decoder or native circuit is
constructed. Factory LER always labels the terminal evaluation oracle.
"""

from collections import Counter, defaultdict

import matplotlib as mpl
import numpy as np
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, PercentFormatter, ScalarFormatter

from .confidence import WilsonInterval
from .figure_style import FigureStyle
from .gap_processing import round_gaps, validate_round_digit
from .saved_data import RunRegistry, choices, field_name

_INHERIT = object()


def _add_counts(counter, values):
    unique, counts = np.unique(values, return_counts=True)
    counter.update(dict(zip(unique.tolist(), counts.tolist())))


def summarize_point(saved, *, gaps=False, T_idx=1, batch_size=65536,
                    round_digit=None, unique_by_stage=False):
    """Stream sufficient statistics, with memory O(unique gap values).

    Return labels/counts only in aggregate. Full trajectories are never retained.
    ``gap_counts`` includes every stage, ``frequency`` only the chosen stage,
    ``minimum_counts/errors`` describe each full trajectory's minimum gap.
    round_digit transforms every gap before all statistics; unique_by_stage
    additionally returns sorted unique lists for every one-based stage.
    """
    validate_round_digit(round_digit)
    if gaps and (type(T_idx) is not int or not 1 <= T_idx <= saved.point.T_tel):
        raise ValueError(f"T_idx must be in 1..{saved.point.T_tel}")
    result = dict(conditions=saved.conditions, shots=0, errors=0,
                  gap_counts=Counter(), frequency=Counter(),
                  minimum_counts=Counter(), minimum_errors=Counter())
    stages = {t: set() for t in range(1, saved.point.T_tel + 1)} if unique_by_stage else None
    for labels, scores in saved.batches(gaps=gaps, batch_size=batch_size):
        result["shots"] += len(labels)
        result["errors"] += int(labels.sum())
        if gaps:
            scores = round_gaps(scores, round_digit)
            _add_counts(result["gap_counts"], scores.ravel())
            _add_counts(result["frequency"], scores[:, T_idx - 1])
            minima = scores.min(axis=1)
            _add_counts(result["minimum_counts"], minima)
            _add_counts(result["minimum_errors"], minima[labels])
            if stages is not None:
                for t, values in stages.items():
                    values.update(np.unique(scores[:, t - 1]).tolist())
    if stages is not None:
        result["unique_by_stage"] = {t: sorted(values) for t, values in stages.items()}
    return result


def _thresholds(value, summaries):
    if value is None:
        return np.array(sorted(set().union(*(s["gap_counts"] for s in summaries))), float)
    try:
        raw = list(value)
        if not raw or any(isinstance(v, (bool, str)) for v in raw):
            raise ValueError
        values = np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("gap_threshold must be a nonempty list/set of numeric thresholds") from error
    if values.ndim != 1 or np.isnan(values).any() or len(set(values)) != len(values):
        raise ValueError("gap_threshold must contain unique numbers without NaN; +/-inf are allowed")
    return np.sort(values)


def cut_statistics(summary, thresholds):
    """Exact AND(gap>threshold); undefined LER/reduction are NaN for plotting."""
    x = np.array(sorted(summary["minimum_counts"]), float)
    counts = np.array([summary["minimum_counts"][v] for v in x], np.int64)
    errors = np.array([summary["minimum_errors"][v] for v in x], np.int64)
    index = np.searchsorted(x, thresholds, side="right")
    rejected = np.r_[0, counts.cumsum()][index]
    rejected_errors = np.r_[0, errors.cumsum()][index]
    accepted = summary["shots"] - rejected
    accepted_errors = summary["errors"] - rejected_errors
    ler = np.divide(accepted_errors, accepted, out=np.full(len(accepted), np.nan), where=accepted > 0)
    baseline = summary["errors"] / summary["shots"]
    reduction = 1 - ler / baseline if baseline else np.full(len(accepted), np.nan)
    return dict(threshold=np.asarray(thresholds), accepted=accepted, accepted_errors=accepted_errors,
                abort=rejected / summary["shots"], ler=ler, reduction=reduction)


class NotebookPlots:
    """Notebook API: register paths, then call plot_* with filter_by/group_by.

    Plots return ``(matplotlib.figure.Figure, matplotlib.axes.Axes)``; frequency
    optionally adds a per-group, per-stage unique-values dictionary. Lifetime
    optionally adds per-group counts, fractions and capped means.
    Scalar filters mean equality; list/set/tuple filters mean membership.
    Ambiguous groups raise instead of pooling distinct physical conditions.
    round_digit defaults to exact scores; each gap plot can override the
    shared setting, with explicit None disabling rounding for that figure.
    """

    def __init__(self, data, *, style=None, batch_size=65536, round_digit=None, interval=None):
        self.data = data if isinstance(data, RunRegistry) else RunRegistry(data)
        self.style = FigureStyle() if style is None else style
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.batch_size = batch_size
        self.round_digit = validate_round_digit(round_digit)
        self.interval = WilsonInterval() if interval is None else interval
        if not isinstance(self.interval, WilsonInterval):
            raise ValueError("interval must be WilsonInterval")

    def _round_digit(self, value):
        return validate_round_digit(self.round_digit if value is _INHERIT else value)

    def _prepare(self, filter_by, group_by, *, gaps=False, T_idx=1, curves=False,
                 round_digit=_INHERIT, unique_by_stage=False):
        digits = self._round_digit(round_digit)
        fields = (group_by,) if isinstance(group_by, str) else tuple(group_by)
        fields = tuple(field_name(f) for f in fields)
        if len(set(fields)) != len(fields):
            raise ValueError("duplicate group_by fields")
        points = self.data.select(filter_by)
        if any(f not in p.conditions for p in points for f in fields):
            raise ValueError("unknown group_by field")
        grouped = defaultdict(list)
        for point in points:
            key = tuple(point.conditions[f] for f in fields)
            try:
                grouped[key].append(point)
            except TypeError as error:
                raise ValueError("group_by fields must be scalar") from error
        invariants = ("key", "kind", "d", "T", "r_0", "r_plus", "rounds", "noise_parameters",
                      "prior_policy", "gap_units", "final_readout", "decoder")
        for key, items in grouped.items():
            if not curves and len(items) != 1:
                raise ValueError(f"group {key} contains multiple physical points; add filter_by/group_by (e.g. key, d, p)")
            if curves:
                for name in invariants:
                    if len({p.conditions[name] for p in items}) != 1:
                        raise ValueError(f"group {key} mixes {name}; add filter_by/group_by")
                ps = [p.point.p for p in items]
                if len(set(ps)) != len(ps):
                    raise ValueError("multiple points at the same p; add key/conditions to filter_by/group_by")
        rows = {key: [summarize_point(p, gaps=gaps, T_idx=T_idx, batch_size=self.batch_size,
                                      round_digit=digits, unique_by_stage=unique_by_stage)
                      for p in sorted(items, key=lambda p: p.point.p)]
                for key, items in grouped.items()}
        return fields, rows, grouped

    def _label(self, fields, key):
        text = ", ".join(f"{f}={v}" for f, v in zip(fields, key)) or "Selected data"
        return self.style.label(text)

    def _finish(self, ax, xlabel, ylabel, *, log=False):
        self.style.axis_labels(ax, xlabel, ylabel)
        if log:
            ax.set_yscale("log")
        ax.legend()
        return ax.figure, ax

    def _shade(self, ax, x, lower, upper, color):
        """Draw only defined pointwise bounds, behind the existing curve/points."""
        x, lower, upper = np.broadcast_arrays(np.asarray(x, float), lower, upper)
        valid = np.isfinite(x) & np.isfinite(lower) & np.isfinite(upper)
        if np.any(valid):
            return ax.fill_between(x, lower, upper, where=valid, color=color,
                                   alpha=self.style.shade_alpha, linewidth=0,
                                   zorder=.5, label="_nolegend_")

    def plot_logical_error_rate(self, *, filter_by=None, group_by=("key", "d"),
                                per_rounds=False, ax=None):
        """LER vs p; optionally 1-(1-LER)**(1/rounds_or_T).

        The transform is a normalization convention, not an independent-round
        noise estimate. Zero observed errors remain zero (invisible on log y).
        """
        if type(per_rounds) is not bool:
            raise ValueError("per_rounds must be bool")
        fields, groups, _ = self._prepare(filter_by, group_by, curves=True)
        with self.style.context():
            _, ax = self.style.axes(ax)
            for key, rows in groups.items():
                errors = np.array([r["errors"] for r in rows], np.int64)
                shots = np.array([r["shots"] for r in rows], np.int64)
                y = errors / shots
                lower, upper = self.interval.bounds(errors, shots)
                if per_rounds:
                    rounds = np.array([r["conditions"]["rounds"] or r["conditions"]["T"] for r in rows])
                    with np.errstate(divide="ignore"):
                        y = -np.expm1(np.log1p(-y) / rounds)
                    lower, upper = self.interval.per_round(errors, shots, rounds)
                x = [r["conditions"]["p"] for r in rows]
                line, = ax.plot(x, y, marker="o", label=self._label(fields, key))
                self._shade(ax, x, lower, upper, line.get_color())
            ylabel = "logical error rate per round" if per_rounds else "logical error rate"
            return self._finish(ax, "Physical error rate", ylabel, log=True)

    def plot_gap_frequency(self, *, filter_by=None, group_by=("key", "d", "p"),
                           T_idx=1, normalize=False, return_unique=False,
                           round_digit=_INHERIT, ax=None):
        """Stage-gap counts; optional third return is {group_tuple: {stage: [gaps]}}.

        T_idx is one-based. return_unique includes all stages per group, while
        the figure displays only T_idx. Values reflect the selected rounding.
        """
        if type(return_unique) is not bool:
            raise ValueError("return_unique must be bool")
        fields, groups, _ = self._prepare(filter_by, group_by, gaps=True, T_idx=T_idx,
                                          round_digit=round_digit, unique_by_stage=return_unique)
        with self.style.context():
            _, ax = self.style.axes(ax)
            for key, (row,) in groups.items():
                x = sorted(row["frequency"])
                counts = np.array([row["frequency"][v] for v in x], np.int64)
                scale = row["shots"] if normalize else 1
                scatter = ax.scatter(x, counts / scale, label=self._label(fields, key))
                lower, upper = self.interval.frequency(counts, row["shots"], normalize=normalize)
                self._shade(ax, x, lower, upper, scatter.get_facecolor()[0])
            result = self._finish(ax, "Logical gap", "Relative frequency" if normalize else "Frequency")
            if return_unique:
                return (*result, {key: rows[0]["unique_by_stage"] for key, rows in groups.items()})
            return result

    def _threshold_plot(self, statistic, filter_by, group_by, gap_threshold, ax, round_digit):
        fields, groups, _ = self._prepare(filter_by, group_by, gaps=True, round_digit=round_digit)
        thresholds = _thresholds(gap_threshold, [r for rows in groups.values() for r in rows])
        with self.style.context():
            _, ax = self.style.axes(ax)
            for key, (row,) in groups.items():
                values = cut_statistics(row, thresholds)
                if statistic == "abort":
                    lower, upper = self.interval.bounds(row["shots"] - values["accepted"], row["shots"])
                else:
                    lower, upper = self.interval.reduction(values["accepted_errors"], values["accepted"],
                                                          row["errors"], row["shots"], no_cut=thresholds < 0)
                line, = ax.plot(thresholds, values[statistic], marker="o", label=self._label(fields, key))
                self._shade(ax, thresholds, lower, upper, line.get_color())
            ylabel = "Abort probability" if statistic == "abort" else "Logical error rate reduction"
            return self._finish(ax, "Logical gap threshold", ylabel)

    def plot_abort(self, *, filter_by=None, group_by=("key", "d", "p"), gap_threshold=None,
                   round_digit=_INHERIT, ax=None):
        """Probability of any stage gap<=cut; default grid is all unique gaps."""
        return self._threshold_plot("abort", filter_by, group_by, gap_threshold, ax, round_digit)

    def plot_lifetime(self, *, filter_by=None, group_by=("key", "d", "p"), gap_threshold=None,
                      round_digit=_INHERIT, show_mean=True, return_summary=False, ax=None):
        """Stacked fractions of passed stages (0..T), with capped mean on the right.

        All shots enter the distribution, including rejected shots and survivors
        censored at T. Colors identify lifetime; hatches identify groups. The
        optional third return maps groups to thresholds/counts/fractions/means.
        More than ten automatic cuts requires an explicit list.
        """
        if type(show_mean) is not bool or type(return_summary) is not bool:
            raise ValueError("show_mean and return_summary must be bool")
        digits = self._round_digit(round_digit)
        fields, groups, points = self._prepare(filter_by, group_by, gaps=True, round_digit=digits)
        thresholds = _thresholds(gap_threshold, [r for rows in groups.values() for r in rows])
        if gap_threshold is None and len(thresholds) > 10:
            raise ValueError("11 or more unique thresholds: specify gap_threshold=[...] explicitly")
        # A second bounded pass counts integer lifetimes; no all-shot arrays.
        stats = {}
        for key, (point,) in points.items():
            if point.point.kind != "logical_zero_factory":
                raise ValueError("teleportation lifetime requires logical_zero_factory")
            T = point.point.T_tel
            hist = np.zeros((len(thresholds), T + 1), np.int64)
            for _, scores in point.batches(gaps=True, batch_size=self.batch_size):
                scores = round_gaps(scores, digits)
                prefix = np.minimum.accumulate(scores, axis=1)
                for i, cut in enumerate(thresholds):
                    lifetime = np.count_nonzero(prefix > cut, axis=1)
                    hist[i] += np.bincount(lifetime, minlength=T + 1)
            fractions = hist / point.info["shots"]
            stats[key] = dict(thresholds=thresholds.copy(), T=T, shots=point.info["shots"],
                              counts=hist, fractions=fractions,
                              mean_lifetime=fractions @ np.arange(T + 1))
        with self.style.context():
            fig, ax = self.style.axes(ax)
            palette = mpl.rcParams["axes.prop_cycle"].by_key()["color"]
            max_T = max(s["T"] for s in stats.values())
            observed = sorted({int(t) for s in stats.values()
                               for t in np.flatnonzero(s["counts"].sum(axis=0))})
            stage_colors = {t: mpl.colormaps["viridis"](t / max_T) for t in observed}
            hatches = ("", "///", "\\\\\\", "xxx", "...", "+++", "ooo", "***")
            markers = ("o", "s", "^", "D", "v", "P", "X", "h")
            group_handles, group_labels = [], []
            mean_ax = ax.twinx() if show_mean else None
            width = .8 / len(groups)
            for index, (key, summary) in enumerate(stats.items()):
                color = palette[index % len(palette)]
                positions = np.arange(len(thresholds)) + (index - (len(groups) - 1) / 2) * width
                bottom = np.zeros(len(thresholds))
                hatch = hatches[index % len(hatches)]
                for t in observed:
                    if t > summary["T"]:
                        continue
                    fraction = summary["fractions"][:, t]
                    ax.bar(positions, fraction, bottom=bottom, width=width * .9,
                           color=stage_colors[t], edgecolor=".25", linewidth=.45, hatch=hatch)
                    bottom += fraction
                handle = Patch(facecolor="white", edgecolor=".25", hatch=hatch)
                if mean_ax is not None:
                    line, = mean_ax.plot(positions, summary["mean_lifetime"],
                                         color=color, marker=markers[index % len(markers)],
                                         linestyle="--", markeredgecolor="white", markeredgewidth=.5)
                    handle = (handle, line)
                group_handles.append(handle)
                group_labels.append(self._label(fields, key))
            ax.set_xticks(np.arange(len(thresholds)), [f"{t:g}" for t in thresholds])
            self.style.axis_labels(ax, "Logical gap threshold", "Shot fraction")
            ax.set_ylim(0, 1.05)
            ax.set_yticks(np.linspace(0, 1, 6))
            ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
            stage_handles = [Patch(facecolor=stage_colors[t], label=f"L={t}") for t in observed]
            fig.legend(handles=stage_handles, ncol=min(5, len(observed)), loc="outside upper center")
            if mean_ax is not None:
                mean_ax.set_ylabel(self.style.label("Mean lifetime"))
                # Independent automatic limits expose changes such as 8 ->
                # 7.99 that a full 0..T mean scale would conceal.
                mean_ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
                mean_ax.ticklabel_format(axis="y", useOffset=False)
                # Keep the primary percent ticks on the left and mean ticks on
                # the right; pyplot's shared style otherwise mirrors both.
                ax.tick_params(axis="y", which="both", right=False)
                mean_ax.tick_params(axis="y", which="both", left=False)
            fig.legend(group_handles, group_labels, handler_map={tuple: HandlerTuple(ndivide=None)},
                       loc="outside lower center", ncol=min(3, len(groups)))
            result = ax.figure, ax
            return (*result, stats) if return_summary else result

    def plot_ler_reduction(self, *, filter_by=None, group_by=("key", "d", "p"),
                           gap_threshold=None, round_digit=_INHERIT, ax=None):
        """1 - selected LER / unselected LER; negative means worse quality.

        At least p or d must be explicitly filtered to one value. Zero baseline
        errors or no survivors leaves the corresponding reduction undefined.
        """
        filters = {field_name(k): v for k, v in (filter_by or {}).items()}
        if not any(name in filters and len(choices(filters[name])) == 1 for name in ("p", "d")):
            raise ValueError("filter_by must fix at least one of p or d to one value")
        return self._threshold_plot("reduction", filter_by, group_by, gap_threshold, ax, round_digit)

    def plot_postselected_logical_error_rate(self, *, gap_threshold, filter_by=None,
                                             group_by="d", round_digit=_INHERIT, ax=None):
        """LER vs p: group=color, threshold=marker AND line style; no per-round transform.

        Use a sparse regular x grid and precision derived from the tick spacing
        to keep physical-error labels readable at the default publication size.
        """
        fields = (group_by,) if isinstance(group_by, str) else tuple(group_by)
        if len(fields) != 1:
            raise ValueError("postselected LER requires exactly one group_by field")
        if gap_threshold is None:
            raise ValueError("provide gap_threshold=[...] explicitly")
        thresholds = _thresholds(gap_threshold, [])
        fields, groups, _ = self._prepare(filter_by, fields, gaps=True, curves=True, round_digit=round_digit)
        # Each threshold has both a distinct marker and a distinct dash pattern.
        markers = ("o", "s", "^", "D", "v", "P", "X", "<", ">", "*", "h", "+")
        if len(thresholds) > len(markers):
            raise ValueError("at most 12 thresholds can be distinguished in one plot")
        styles = ["-", "--", "-.", ":"] + [(0, (i, 1, 1, 1)) for i in range(2, 10)]
        with self.style.context():
            _, ax = self.style.axes(ax)
            palette = mpl.rcParams["axes.prop_cycle"].by_key()["color"]
            handles = []
            for index, (key, rows) in enumerate(groups.items()):
                color = palette[index % len(palette)]
                handles.append(Line2D([], [], color=color, label=self._label(fields, key)))
                stats = [cut_statistics(row, thresholds) for row in rows]
                x = [r["conditions"]["p"] for r in rows]
                for i, cut in enumerate(thresholds):
                    ax.plot(x, [v["ler"][i] for v in stats],
                            color=color, marker=markers[i], linestyle=styles[i])
                    lower, upper = self.interval.bounds(
                        np.array([v["accepted_errors"][i] for v in stats], np.int64),
                        np.array([v["accepted"][i] for v in stats], np.int64))
                    self._shade(ax, x, lower, upper, color)
            handles += [Line2D([], [], color="black", marker=markers[i], linestyle=styles[i],
                               label=f"threshold={t:g}") for i, t in enumerate(thresholds)]
            self.style.axis_labels(ax, "Physical error rate", "Post-selected logical error rate")
            ax.set_yscale("log")
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))
            formatter = ScalarFormatter(useOffset=False, useMathText=True)
            formatter.set_powerlimits((-4, 4))
            ax.xaxis.set_major_formatter(formatter)
            ax.tick_params(axis="x", which="major", pad=5)
            ax.legend(handles=handles)
            return ax.figure, ax
