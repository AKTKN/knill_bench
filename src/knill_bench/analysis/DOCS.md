# Saved-data analysis (schema v1)

`report.analyze` delegates surface_prep_fixed to `preparation.analyze`, which
validates saved artifacts/checkpoints/parts before streaming published chunk
counters. It writes a JSON/count/timing report with independent sign/code/
logical denominators, joint counts, bounded replay latency percentiles and
explicit memory/I/O timer scopes. It never simulates or resumes. Missing/
modified published parts reject; uncommitted failure attempts remain separate
from scientific denominators. Gap calibration/interval curves remain prompt
05. See [current saved-count API](../../../docs/preparation_execution.md).

## Notebook figures (schema v2)

`RunRegistry` (`saved_data.py`) registers keyed run paths without filesystem
access. At plot time, `select(filter_by)` validates saved config/metadata and
selects published complete points, warning on selected unfinished points.
`SavedPoint.batches` streams bounded, schema/ID/count-checked label/gap pairs,
including different row-group boundaries. Existing uniform/historical prior
labels and custom-noise execution checks are retained. It never resumes or
modifies a run. Each plot reloads data; no all-shot cache is kept.

`NotebookPlots` (`notebook_plotting.py`) returns editable Matplotlib `(fig, ax)`
for LER versus p, exact stage-gap frequencies, abort versus threshold,
first-rejection lifetime fractions/means, LER reduction, and postselected LER versus p.
Scalar/membership `filter_by` and scalar/list `group_by` accept key and resolved
experimental conditions. Ambiguous physical groups raise rather than pool.
`per_rounds=True` normalizes with `1-(1-LER)**(1/r)` using rounds or T.
`plot_logical_error_rate(rescale_p_keys=["ideal_bell"])` maps only selected
registered keys' horizontal coordinates to (23/10)*p-(8/5)*p**2, including their
Wilson shades. A scalar key or list/tuple/set/frozenset is supported; None/empty
keeps existing coordinates. Key validation uses the registry without IO; unknown
keys raise, while registered filtered-out paths remain unopened. Filters/groups
use original saved p; counts, LER/interval bounds and legend text stay unchanged.
The axis identifies the code-capacity scale when transformed points are present.
This display option composes with per_rounds and does not auto-detect physical
models or claim channel equivalence outside the documented logical-Z/T=1 scope.
See [the example and assumptions](../../../docs/notebook_plotting.md).
Reduction is `1-selected_LER/raw_LER`; no acceptance or zero baseline gives
undefined values. Default threshold grids contain all exact unique stage gaps;
automatic lifetime grids with >10 values raise and request `gap_threshold`.
Lifetime uses all shots and counts passed stages (0..T), factory only. It now
shows 100% stacked fractions by lifetime, grouped/hatch-coded bars per cut,
and default dashed means on an independently scaled right axis. These means
are capped at the saved T, with no extrapolation beyond the observation window.
`show_mean=False` hides that axis. Optional `return_summary=True` adds grouped
thresholds/T/shots/counts/fractions/mean_lifetime arrays. Legends are figure-level
(`fig.legends`); the primary returned axis shows fractions, `fig.axes[-1]` means
when show_mean=True.
Postselected p plots allow exactly one grouping field, color groups and use
both marker/dashes for up to 12 explicit thresholds, without per-round scaling.
Their physical-error x axis uses a sparse 1/2/5 regular locator (about five
intervals), concise ScalarFormatter labels without additive offsets and extra
major-label padding, retaining the shared tick font size. No data/curve changes.

`WilsonInterval` (`confidence.py`, also lazily exported from analysis) provides
default 95% two-sided, uncorrected Wilson score bounds for scalar/broadcast
integer counts. All five non-lifetime notebook plots now draw same-color
pointwise shades. Frequency uses category count/total shots, scaling bounds
back to expected-count units unless normalized; abort uses rejected/shots;
conditional LER uses accepted_errors/accepted. Per-round normalization applies
the same monotone transform to both endpoints. Zero successes retains a positive
upper bound; zero denominators remain NaN and receive no shade. FigureStyle's
shade_alpha defaults to .18. Default plot returns, counts and lines are unchanged.

Reduction is not binomial: let a=P(accept) and b=P(accept|error), so the paired
LER ratio is b/a. Two 97.5% Wilson intervals at default confidence yield the
Bonferroni rectangle [1-b_upper/a_lower, 1-b_lower/a_upper]. This avoids assuming
independence of overlapping samples. The band is Wilson-derived/conservative
relative to its component intervals, not an exact finite-sample 95% guarantee.
Zero acceptance or zero baseline errors is undefined; structural no-cut
(negative threshold, since scores are nonnegative) has exactly zero reduction
when defined. Observed all-pass at a finite cut is not treated as structural.
No simultaneous/adaptively selected-threshold coverage is claimed. No CI is
added to the stacked lifetime figure, including its mean curve. Legacy v1,
B3 and CLI adjusted-Wald/Wilson choices remain unchanged. See the notebook
guide for equations, sources and the optional NotebookPlots(interval=...) API.

These notebook cuts reject **gap <= threshold**, as requested, whereas the
historical B3 helper below accepts gap >= theta. Neither changes the other.
Factory labels remain terminal evaluation-oracle labels, never online LER.
Exact aggregate memory scales with distinct scores, not trajectory count;
lifetimes use a second bounded pass and integer histograms. No simulator or
native decoder is constructed. New lazy package exports preserve old imports.

`FigureStyle` (`figure_style.py`) calls the locally installed `plotting_lib`
APS style inside rc contexts, with reference-sized serif labels (14 pt),
ticks (13 pt), legends (12 pt) and 6x3.6 inch figures. Default display/export
dpi is 300. MathText defaults to Computer Modern; `labels` supports raw
mathsf/mathrm overrides for every axis/legend, while `usetex=True` and
`latex_preamble` provide actual LaTeX with a minimal amsmath preamble. It supports
figsize/rc overrides, existing axes and PDF/PNG export with `save`. Install the
optional package from `external/plotting_lib` in the notebook environment; the
simulation runtime locks and cluster wheels remain unchanged. See
[equations, all six APIs and examples](../../../docs/notebook_plotting.md).

`NotebookPlots(round_digit=None)` preserves exact scores; integers opt into
Decimal ROUND_HALF_UP before every gap frequency/unique/minimum/cut/lifetime/
selected-LER calculation. All gap plots accept per-call overrides, including
explicit None to disable the shared policy. `gap_processing.py` transforms
bounded batches using distinct scores and a 4096-entry scalar cache. Raw
validation runs first; explicit thresholds and saved files are unchanged.
Both lifetime passes use the same rounding. `plot_gap_frequency(return_unique=True)`
adds a third return `{group_tuple: {one_based_stage: sorted_gap_list}}` for all
stages, while the figure still displays only T_idx. Other/default returns stay
`(fig, ax)` and unselected LER is unaffected.

## Original v1 API

`report.py` aggregates existing v1 tables, Wilson intervals, timing and paired
statistics, then writes optional report/plots. `plotting.py` loads v1 LERs,
validates grouping/filter choices and plots saved summaries. It does not
resimulate data. The authoritative current v1 schema is
[data/storage.py](../data/storage.py) and [the schema guide](../../../docs/data_schema.md).

B0 changes no analysis Python. V2 has exactly one/two point tables and compact
metadata, described in [the v2 guide](../../../docs/auxiliary_v2.md). Fig.4(d)
Agresti-Coull plotting belongs to B1; factory acceptance/first-rejection/cost
analysis belongs to B3. No v1 Wilson result or old d-2 protocol is advertised
as a Fig.4(d) reproduction. Truth may label errors, never select confidence.

## B1 saved-data Fig.4(d)

`fig4d.agresti_coull(errors, shots)` returns clipped two-sided 95% bounds using
the adjusted-Wald formula. `summarize_saved(run)` checks complete metadata,
unchanged YAML/config hashes, physical identities, schemas, saved IDs and row/
error counts; it streams Parquet and returns d/p/count/LER/lower/upper mappings.
`plot_saved(run, output)` writes only an optional headless figure with grouped
distance curves. No simulator or runner is imported. Every Fig.4(d) shot is
retained, so conditional LER is errors/shots over eight stages, without a
per-round transform. The vertical label is `logical error rate`; the existing
`conditional_ler` summary key is unchanged. Valid saved preparation-depth
variants are accepted as well as standard d-round runs. No paper agreement
follows from tiny regression fixtures.
See [the B1 guide](../../../docs/fig4d.md) for equations and commands.

## B3 saved factory analysis

`factory.AnalysisSettings`, `load_settings(path)` and `threshold_grid` define
gap-only cuts, a read-batch bound and explicit FactoryCostModel/iid assumptions.
`analyze_saved(run, settings=None)` verifies complete metadata, exact config,
schema, IDs/counts and finite paired gaps, then streams one row per point/cut
with counts, acceptance/abort, conditional terminal factory-oracle error,
pointwise 95% Agresti-Coull intervals, first-rejection histogram and cost
statistics. No simulation package or native backend is imported. Read-batch
boundaries need not match Parquet row groups. All cut masks use gaps only.

`factory_cost.first_rejected_stage` returns 0 accepted or stage 1..T.
`FactoryCostModel.prefix_costs` declares initial serial/parallel overlap,
refresh prep/reset, teleport/readout and decode costs. `summarize_cost` computes
attempt moments and only under explicit iid restarts, mean cost/acceptance
with paired delta-method SE. One accepted T-stage trajectory yields one resource;
the evaluation oracle is excluded from operational cost. No accepted samples
leaves conditional LER and restart ratios null. Default costs are assumed
SE-equivalent work, not measured hardware latency.

`write_report(report, output)` writes optional .json/.csv/.md only on request;
CLI defaults to stdout JSON. Simulation files and v1 analysis remain unchanged.
See [B3 details](../../../docs/factory_analysis.md),
[getting started](../../../GETTING_STARTED.md) and the
[analysis template](../../../configs/templates/factory_analysis.yaml).

## Saved factory prior versions

factory.analyze_saved recognizes current module_local_stim_dem and historical
circuit_informed_projected for True runs, using the saved policy label in
report rows. It never reinterprets old projected gaps as new local gaps,
rebuilds a DEM or resumes a simulation. Current local priors exclude
preparation/earlier-stage residuals; see the factory guide for that model change.

Saved-data readers now use load_saved_config to preserve the historical
implicit batch_size=32 when an old archived YAML omitted the field. Canonical
metadata and original-input hashes disambiguate it from new auto-default runs;
all existing config/schema/ID/count checks still run. Auto/fixed table schemas
and scientific estimands are identical. No simulation or source-compatibility
check is added to saved-only analysis.




BENCH-N2 validates custom factory execution noise/configuration/finite-channel
hashes and declared local-prior scope before reading saved rows. Per-shot
schemas, conditional estimand and legacy uniform policy labels are unchanged.
No backend is constructed. Uniform settings load without Hex; custom settings
load native frozen noise classes for parameter/probability validation only.
See [custom noise](../../../docs/factory_custom_noise.md).

## General Knill saved-data analysis

fig4d.summarize_saved/plot_saved now also accept knill_ec_memory at positive
arbitrary T and check its noise execution metadata. plot-knill and the
plot-fig4d alias share this saved-only path, actual T/noise title, existing
summary keys and Agresti-Coull statistics. See
[noise contract](../../../docs/knill_ec_noise_plan.md).

## General Knill inference provenance

plot-knill/summarize_saved and RunRegistry now accept knill_sim/knill_ec_memory
True runs, preserving their local/full-prefix labels and validating inference
mode, scope, residual inclusion flags and per-stage sector hash structure.
Saved analysis never compiles a prior or changes logical-error labels. See
[metadata contract](../../../docs/knill_sim.md).
