# Bench regression tests

`test_notebook_plotting.py` uses only six-row synthetic v2 tables (no physical
sampling). It checks lazy keyed registration, scalar/membership/alias filters,
unambiguous grouping, all six editable figure APIs, APS/300-dpi context/export,
rounds/T normalization, exact frequencies, strict gap<=cut rejection,
label-independent selection, negative/undefined reduction, first-rejection
lifetimes, stacked fraction conservation and capped means, explicit threshold grids/automatic ten-cut
limit, color/marker/line-style mappings, incomplete-run complete-point reading,
and schema/paired-ID/null/nonfinite/negative/count/config/unit corruption.
The optional plotting_lib package must be installed for these rendering tests;
see [installation](../docs/notebook_plotting.md).
Additional cases cover optional per-group/all-stage unique returns, Decimal
half-up ties, shared/per-figure rounding and None overrides across every gap
plot, both lifetime passes, rounded automatic-grid limits, partition-invariant
summaries, unchanged raw data and validation of corrupt negative scores before
rounding. Actual TeX/PDF rendering is a separate environment smoke, not a unit
test dependency on a TeX installation.
Lifetime cases check exact all-shot counts/fractions/means at strict-equality
and infinite cuts, monotone mean versus threshold, grouped stack heights,
mean-axis opt-out/default returns, label and batch-partition independence,
and invalid options before I/O. No boxplot/outlier semantics remain in this API.
Wilson plot cases verify all five shade types, observed versus accepted
denominators, per-round endpoint transforms, frequency count units, omitted
undefined/zero-baseline bands, and exclusion of both lifetime axes. Observed
zero errors retain a positive Wilson upper bound on log plots.

`test_confidence.py` cross-checks Wilson against SciPy's independent score
implementation across 90/95/99% levels and analytic small integer counts.
It covers boundaries, broadcast shapes, empty denominators, count units,
per-round transforms, paired reduction/error-retention identity with Bonferroni
adjustment, structural no-cut versus observed all-pass, undefined estimates
and invalid counts/paired cells/options. No Monte Carlo or storage fixture.

The original `test_circuits`, `test_decoding`, `test_execution` and
`test_analysis_plotting` files exercise v1 signed circuit/DEM invariants,
native comparisons, bounded execution/resume/streaming, statistical summaries
and plots. They remain unchanged. Some inherited static Hex fixtures sample
256 shots; B0 adds no physical Monte Carlo or large sweep.

`test_v2_config.py` validates both examples, strict fields/rules/axes/SafeLoader,
full literal-plus filenames, float identity, schedule/policy-independent seeds,
phase dispatch and the separately installed CLI. `test_v2_storage.py` uses
synthetic <=7-row points to check typed nullable schemas, one streaming writer
per table, aligned IDs, footer/promotion order, append/rename/metadata failures,
clean restart, collisions, provenance, parent ownership and source/config
validation. Actual H5 API inspection is read-only and forbids scientific
construction. No test needs network access or benchmark data.

Run `.venv/bin/python -m pytest -q` after the normal editable/bootstrap setup.
[TEST.md](../TEST.md) records exact commands/results and setup corrections.
[The B0 guide](../docs/auxiliary_v2.md) documents new contracts and limits.

## B1 regression coverage

`test_fig4d.py` parses the production config without building its circuits;
checks runner protocol guards; compares the exact d=3 T=8 module sequence
with fixed Hex; compares manual saved raw arrays/corrected records/labels
bit for bit with legacy global maps at T=2; tests d=3/5 zero-noise T=1 and
native reuse; verifies tiny streamed output/counts/metadata, point-seeded
replay, serial versus spawn streams, worker failure and whole-point resume.
Saved-data plotting/CLI, numerical Agresti-Coull fixtures and invalid counts,
missing/truncated/shuffled/count-tampered files are covered. New physical
fixtures use <=11 shots, never d=21 or the production sweep. The B0 dispatcher
test was updated again in B2 to verify both available kind dispatches.

## B2 regression coverage

`test_logical_zero_factory.py` uses the real Hex API at d3/5, p0 and small
positive p, T1/2/3, with <=7-shot fixtures. It checks two reused supports and
roles, noisy teleportation/ideal terminal readouts, finite Hamming gaps at p0,
actual projected gaps/units/hashes, raw seed equality across theta/prior mode,
oracle/future isolation, streaming exact counts/partial chunks/paired joins,
serial/spawn equality, no native construction during chunks, unsupported and
invalid-gap failure, and restart after a late chunk failure preserving complete
pairs and reproducing the original seed stream. No B3 cuts or costs are added.
Existing read-only Hex circuit/batch/surface-gap tests separately validate
signed flows, parity/frame boundaries, legacy-map equivalence, injected faults
and exhaustive d3 sector costs. Commands/results are recorded in TEST.md.

## B3 analysis and integration

`test_factory_analysis.py` uses six-row synthetic paired data to check AND
cuts, monotone acceptance, -infinity/raw-LER identity, zero acceptance, equality
at the cut, gap-only first rejection and label-independent selection/costs.
It verifies serial/parallel/reset/decode/restart accounting, the iid renewal
gate, paired cost-ratio uncertainty, and one resource per full T trajectory.
It rejects broken IDs, missing/null/nonfinite/negative scores, changed counts,
incomplete status and unit mismatch. Templates/grid/strict YAML, optional reports,
installed CLI and no Hex/Stim/PyMatching import are checked. Tiny d3/5 three-shot
smokes run both complete v2 experiments and saved analysis. Existing B1/B2 and
read-only Hex constructor counters test cached inference without wall-time
assertions. No production sweep or new large-shot test is introduced.

## Conda / cluster package validation

Run `conda run --no-capture-output -n knill_system python -m pytest -q`.
`test_cluster_packaging.py` verifies wheel provenance without Git, resource/
source tamper rejection and retained H5 revision enforcement. Full existing
science/run/analysis regressions run in the new Conda interpreter. Separate
installed-wheel integration builds/installs all four packages and pip locks
into an isolated temporary target, removes Git/Conda from PATH, then runs
small v1/v2 experiments, analysis and resume. See TEST.md for exact results.

## V2 rational round rules and Fig.4(d) label

Config tests cover integer/decimal/fraction multiples, exact flooring near
integer boundaries, invalid syntax/denominators, zero-depth and int64 overflow
rejection, and seed equality for equivalent physical depths. Example parsing
checks the actual d/p Cartesian product instead of assuming four points,
allowing user edits without sampling those examples. Small physical fixtures
verify native factory propagation and all eight full-Knill stage depths,
measurement counts, saved metadata, custom-depth serial/spawn equality and
saved plotting with the `logical error rate` label. Existing d-round Hex circuit
and manual-array comparisons remain; no dependency source is changed.

V2 storage collision fixtures now check the compact Asia/Tokyo timestamp,
eight-digit config-hash prefix, midnight rollover, fresh pending state on an
identical-config creation, changed-config naming, preservation of completed
data and legacy-directory resume. They use synthetic seven-row tables only.

`test_factory_profiling.py` checks the optional diagnostic's inclusive versus
exclusive wall/CPU accounting with deterministic clocks and verifies that an
interrupted phase records its timing and restores runtime patches. Unit tests
do not execute a performance sweep or assert machine-specific speed thresholds.

## Factory module-local DEM checks

test_factory_local_dem.py compares strict Stim local DEMs with independent
forward fault propagation and analytic readout probabilities (d3/5), checks
Pauli logical boundaries and frame invariance, exhaustively enumerates d3
sector minima while manually replaying three stages of native preparation
frames, and verifies original physical samples. Cache checks cover stage/
depth/seed reuse, noise/body invalidation, bounded eviction and no legacy
projection calls or repeated bundle validation. Existing runner tests now
exercise True serial/spawn equality and failed-chunk restart as well as False.
Saved-data checks preserve historical policy labels and forbid mixed-policy
resume. Profiling tests verify cold/warm cache counters and identical seeded
outputs. New physical samples remain <=7 shots at d3/5.

test_factory_frames.py checks packed GF(2) against independent integer products
at byte/block boundaries and zero dimensions; d3/5 <=7-shot comparisons match
all native full-history exit frames and every decoded result field under both
prior modes, including nonzero faults and noiseless random stabilizer signs.
It verifies exact circuit/RNG/decode equality with validation enabled/skipped,
explicit validate() on returned native bundles, template sharing, strict flag
parsing and config-hash/physical-seed compatibility. Runner tests cover both
validation modes under serial/spawn and saved execution metadata; profiler
tests count the skipped/full checks and packed-map/frame calls.

## Adaptive parallel execution

`test_adaptive_execution.py` covers strict new config/default/hash behavior,
CLI worker overrides, deterministic synthetic throughput adaptation, bounded
out-of-order windows, exact buffer row groups/alignment, invalid-result abort,
whole-point restart/completed preservation, real d3 seven-shot serial/spawn
runs for full Knill and both factory priors, worker-cache reuse and explicit
chunk-seed replay. Existing fixed-mode serial/spawn equality is retained.
`test_cluster_script.py` exercises Conda activation, quoted config paths,
single-command run/resume and YAML worker preservation with stub executables.
PBS CPU environment variables and a one-entry nodefile cannot inject a worker
override. No production or throughput benchmarks run in tests.

## Ordinary memory and complementary gap

test_se_memory.py covers strict config/round rules and pre-extension golden
hashes; exact Hex physical circuits/noisy boundaries; d3/5 <=7-shot labels,
optional-gap first-decode and truth isolation; exhaustive tiny graph minima,
independent binary-integer sector costs on the d3 circuit DEM, constraint and
native-cost validation, cached graphs, optional paired schemas/IDs/buffers,
serial/spawn (auto and fixed), p0 plain decoding and failure/restart. Invalid
requested gaps and changed-option resume are rejected. No production sweep,
new large Monte Carlo, dependency edit or benchmark is included.




BENCH-N1 test_v2_factory_noise.py covers strict custom nesting/defaults,
finite numeric/domain checks at every point, explicit unsupported-kind errors
before output, duplicate YAML keys, native frozen/pickled objects, canonical
roundtrip, short filenames, complete noise/seed identity and legacy uniform
config/point/seed goldens. It constructs no physical circuit. Existing v1/
Fig.4(d)/memory/factory regression suites remain required at the new Hex pin.




BENCH-N2 test_factory_custom_noise.py adds small d3 physical cases (batches
<=7 shots): exact native circuit identity, both validation/prior modes, actual
alternating idle supports/probabilities, preparation frames versus native,
analytic gate/readout DEM weights, included post-control and excluded storage
regions, complete custom cache separation, paired physical logical faults,
no oracle influence, native reuse, zero multipliers, fixed/auto/spawn aligned
Parquet/counts/metadata, saved analysis, tamper rejection and failed-point
restart/replay. No production sweep or new large Monte Carlo fixture is added.

## General Knill memory noise tests

test_knill_ec_memory.py covers parsing/domain/protocol restrictions, config
round trips, physical IDs/seeds, exact native circuit/global-frame replay,
d3/5 p0 and cached decoding, fixed/auto bounded output, metadata tampering,
completed resume, saved plotting, fixed serial/spawn equality and failed-point
restart. New physical fixtures use <=7 shots; production configs parse only.
Existing legacy tests remain, with two expectations updated for shipped kind
renaming. See [plan/contract](../docs/knill_ec_noise_plan.md).
