# Saved-data analysis (schema v1)

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
