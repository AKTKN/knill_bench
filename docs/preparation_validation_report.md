# Prompt-05 validation results

The prompt-04 checkpoint is pushed as `70074e6` on `surface-prep-fixed`.
Prompt-05 implementation is kept local. Hex remains clean at HEX-K1
`8fa2200315cc4feaccf341a461f91739233de08a`; other dependency checkouts, user
notebooks, .gitignore and source pins are unchanged.

The [simulation getting-started guide](preparation_getting_started.md) gives
small runnable commands. The [report contract](preparation_reports.md)
defines the typed tables, figures, masks, cuts, intervals and measured scopes.

## Established graph statement

For the supported unmerged, graphlike completed independent DEM, freezing
every spatial degree-one port to its baseline assignment and flipping both
P/F parities gives Hδ=0, δ_S=0, Pδ=Fδ=1. The difference support contains a
past-to-future path. An independent BFS checks retained original-column
supports, including original active/mechanism mappings. This allows cycles
and multiple paths and does not identify the actual sampled fault, sum
posterior hypotheses, or prove fault tolerance.

The four-edge synthetic counterexample enumerates 16 assignments. Without
freezing, disconnected P/spatial and F/spatial ports cost 2; freezing forces
the P–online–F path of cost 12. The readout-only syndrome-one optimum costs
are 5 and 7, gap 2. The independent unit fixture checks every spatial assignment
and P/F/syndrome RHS, including infeasibility, against the native static kernel.

## Deterministic/software checks

The acceptance subset passed 101 tests at its recorded revision. Final report
fixtures passed **19 tests, 92 warnings, 35.69 s** after adding interior-qubit
Pauli/tableau comparisons and preserving execution status/failure accounting.
Actual exact commands and all initial failures/fixes are in [TEST.md](../TEST.md).

These fixtures and retained earlier tests cover unknown/random first-X signs,
known-zero Z anchors, exact native R-round prefix/noise/cut, evaluator-only
suffix, X/Z sector separation, first/last/interior/continuous readout faults,
boundary/interior Pauli signs and direct tableau expectations, ideal Z MPP
versus H_Z destructive bits, nominal/production X/all-label marginal equality,
truth isolation, exact small-graph costs, compact/full tie identity,
original-column constraints/paths, nullable metrics, batch/single decode,
1/2-worker and interrupted-resume sample replay, compact/aggregate equality,
paired events, zero-event Wilson bounds and corrupted input/output rejection.
New physical unit-test batches use d3/5 with at most seven shots. No large
Monte Carlo is hidden in the unit suite. Analysis tests explicitly forbid
sampler and live matcher construction and check source files unchanged.

## Actual end-to-end smoke

The final external driver passed on 2026-10-24. It ran the shell wrapper,
module API and installed `knill-bench` console entry point in Conda
knill_system. Artifacts are retained under ignored
`results/preparation_prompt05_smoke/20261024T104907.373089Z/`:

- `compact.yaml`, `aggregate.yaml`: exact actual inputs.
- `smoke_results.json`: assertions, paths, config hash, counts, timing and
  embedded validation/source identities.
- `analysis/report.md`: primary report with PNG/PDF/SVG figures, typed tables,
  paired/joint counts and retained examples.
- `aggregate_analysis/report.md`: interrupted/restarted aggregate replay.
- `reproduce_smoke.py` and per-command stdout/stderr logs.

Run the saved-data report again without sampling, choosing a new directory:

```bash
bash scripts/python.sh -m knill_bench.cli analyze \
  results/preparation_prompt05_smoke/20261024T104907.373089Z/runs/20261024T104908.855921Z_ccecb96dbe \
  --output results/preparation_prompt05_smoke/20261024T104907.373089Z/reanalysis
```

The independent physical budget was **d=3, R=2, p=0/.02, seven attempts at each
p (14 total)**, seed617, chunks 3/3/1, two workers, native threads one, warmup
one per chunk and two replay latency samples per point. Both modes used a
positive nominal inference p=.02, so the p0 check has finite model scores
without artificial physical noise. p=.02 is a deliberately explicit bounded
stress-smoke choice to exercise misses, not a paper/agreement parameter.

Compact and full-witness variants share each physical sample. The driver
repeated the same 14 fixed-seed records with aggregate-only output, interrupting
after one chunk and resuming from one to two workers. These are replay records,
not 14 additional independent samples. Initial smoke-harness diagnostics also
sampled the same fixed-seed points before its metadata assertion correction;
those records are not pooled into scientific denominators. No standard
production sweep was launched.

| physical p | mode | X miss/valid | Z miss/valid | code miss/valid | logical-Z error/valid |
|---|---|---|---|---|---|
| 0 | compact | 0/7 | 0/7 | 0/7 | 0/7 |
| 0 | full_witness | 0/7 | 0/7 | 0/7 | 0/7 |
| .02 | compact | 2/7 | 1/7 | 2/7 | 0/7 |
| .02 | full_witness | 3/7 | 1/7 | 3/7 | 0/7 |

All three masks were valid for all primary shots; invalid/unpublished failed
scientific counts were zero. The modes' X/code event cells on the seven noisy
samples were [3,2,1,1] in order 00,01,10,11: **three discordant paired events**,
not an independent-sample comparison. Z/logical event decisions agreed across
modes. Both modes had identical objective definitions but can select different
minimum-cost ties, as their saved identities declare; the report does not
attach a debug witness to a compact correction.

The saved analyzer checked **14 retained decoder examples**: seven available
same-solve full witnesses passed all algebra/cost/feature checks and the
independent original-column P–F traversal; seven compact witnesses were
explicitly unavailable. Source/artifact hashes and the nominal X/all-label
marginal plus independent known-zero Z map checks passed. Published parts,
checkpoints and static artifacts were unchanged by completed resume. Analysis
left input simulation files unchanged. The derived stopping timing/status table
is legitimately refreshed by resume and is not a scientific sample table.
Compact versus aggregate replay produced identical canonical sample hashes,
all typed bin/threshold counters and paired tables.

## Observed gap/risk and statistical resolution

In this single seven-shot noisy point, all observed X/code misses were in
[0,1). At g=1, both modes accepted 3/7 and had 0/3 X/code misses. This is an
exploratory observation, not a resolved performance trend: the pointwise 95%
Wilson interval for 0/3 extends to **.5615**. At g=4, acceptance is 2/7 with
0/2 misses and upper endpoint **.6576**. Logical-Z errors are 0/7 at no cut,
with upper endpoint **.3543**, not evidence for probability zero. Noiseless
0/7 rates have the same descriptive finite-sample upper endpoint.

The no-cut noisy X-sign estimates are 2/7 with Wilson [.0822,.6411] for
compact and 3/7 with [.1582,.7495] for full witnesses. These broad, paired
observations do not rank the modes scientifically. X-gap mainly concerns
Z-type faults; logical-Z readout mainly depends on the separate X-type fault
sector. No logical gap–risk correlation is resolved here. All intervals are
pointwise approximate fixed-shot intervals; the report's multiple cuts do not
provide simultaneous or data-selected-threshold coverage.

## Measured cost and remaining experiments

The complete shell invocation for 14 physical shots and both decoder modes
took **7.383 s**, including Conda/imports/setup/pool/warmup/replay/I/O. Completed
resume took **3.298 s**; installed-CLI scientific export took **13.523 s**.
The aggregate interruption/resume invocations took **6.434/6.718 s**, dominated
by their separate process/import setup; aggregate saved-data export took
**10.155 s**. These are tiny local smoke observations, not scaling benchmarks.

| p | mode | primary decode shots/s | X baseline ns/shot | X complement ns/shot |
|---|---|---|---|---|
| 0 | compact | 2542 | 129164 | 228577 |
| 0 | full_witness | 1333 | 194901 | 339815 |
| .02 | compact | 4727 | 53068 | 130191 |
| .02 | full_witness | 1802 | 150728 | 228080 |

Primary decode includes X baseline/complement and Z, excluding setup, warmup,
latency replay, sampling, evaluation and I/O. Worker process peak RSS was
**363,663,360 bytes**; selected Python sparse buffers for both decoder bundles
were **10,528 bytes**, and the largest raw detector/observable arrays were
**63 bytes**. RSS includes interpreter/native imports; selected buffers omit
opaque native graph/prediction/Arrow allocations. Sampler compile/sample sums
were .158/.678 ms at p0 and .120/.170 ms at p=.02. Staging-write phase sums
were 195.0/180.7 ms, parent-commit sums 222.4/231.7 ms. Phase timers can overlap
across workers and some I/O scopes; they are not additive elapsed wall time.

The standard d5/7/9, R2/3/4/5 rare-error study remains unexecuted. It needs an
explicit production budget and scientifically chosen noise/threshold settings.
Adaptive extension of the same trajectory and factory timing/efficiency require
new physical execution/cost experiments. Neither was simulated or inferred
from this fixed-R report.

## Final regression and scope gate

`bash scripts/python.sh -m pytest -q --disable-warnings` passed **921 tests**,
with **1880 inherited-category warnings**, in **281.47 s**. This retains all
902 previous cases plus 19 new validation/report cases. Source/tests were
frozen for the successful final smoke and complete regression; later edits
only record results. `compileall`, guide-link/whitespace checks and pip check
pass. The exact final test log is retained beside the smoke artifacts as
full_pytest.log. TEST.md records initial incorrect fixtures/API/harness
assumptions and the explicit interrupted render-correction gate.

No dependency source/version, user notebook, .gitignore or environment lock
changed. Legacy simulation numerics and physical seed derivation are unchanged.
Prompt 05 remains local and unpushed, with no production or later-phase run.
