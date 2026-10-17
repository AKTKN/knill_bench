# Test record

## B0 auxiliary-system infrastructure

Date: 2026-10-16. New v2 modules add no physical Monte Carlo. Synthetic storage
points use seven rows in batches of at most three. Actual H5 exports/lineage
are inspected with scientific constructors forbidden. Original v1 tests remain
unchanged, including their inherited 256-shot native fixtures.

Initial environment diagnostics: base Anaconda Python had NumPy 1.26.4,
SciPy 1.13.1, Stim 1.15.0, PyMatching 2.3.1, PyArrow 16.1.0, PyYAML 6.0.1 and
pytest 7.4.4. No bench/fork editable installs or .venv existed. A first editable
surface-sim install failed on its SPDX license metadata with old setuptools;
a subsequent attempt required newer packaging. V1 collection then exposed
missing galois and LOM's NumPy-1.x np.bool incompatibility. These were environment
issues, not changed/suppressed v1 assertions. No dependency source was patched.

Before the final lock setup:

```bash
.venv/bin/python -m pytest -q tests/test_v2_config.py tests/test_v2_storage.py
```

Initial **1 failed, 68 passed, 8 warnings, 4.50 s**: the float-identity test
passed numpy.float64 into the plain Python/YAML-number API. Converting that
test fixture to float preserves strict parser validation. Rerun **69 passed,
8 warnings, 3.52 s**. Further append/metadata failure and identity-corruption
checks subsequently increased the new test count to 74.

Final isolated environment setup (local editable repos, no source changes):

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock wheel
.venv/bin/python -m pip install --no-deps --no-build-isolation -e . -e external/Hex -e external/lomatching -e external/surface-sim
```

Editable installs had also installed local setuptools 84.0.0 and packaging
26.3 to resolve the earlier build-tool metadata errors. The final environment
matches every runtime lock entry: NumPy 2.5.3, SciPy 1.18.1, Stim 1.16.0,
PyMatching 2.4.0, LDPC 2.4.1, PyArrow 25.0.1, PyYAML 6.0.3, pytest 9.1.1,
Matplotlib 3.11.2. Fork distribution versions: Hex 0.1.0, LOM 0.3.0,
surface-sim 0.11.0. `.venv/bin/python -m pip check` reports no broken requirements.
The bootstrap Hex pin and project Git dependency both name H5 4278d29.

Full validation command:

```bash
.venv/bin/python -m pytest -q
```

**139 passed, 432 warnings, 115.21 s**: all 65 original v1 tests and 74 new
v2 cases. Warnings are inherited SciPy Matrix Market sparse-matrix migration
notices in Hex and four empty-legend warnings in existing aggregate plotting.
No tests were skipped/deselected, and no full benchmark or paper sweep ran.

V2 cases cover strict parsing, both checked-in examples, unchanged v1 schema
rejection of v2, all forbidden sweeps, duplicate YAML/unsafe tags, named round
rules, exact full filenames including literal r_+, adjacent-float p identity,
uint64 stable seeds, scheduling/prior/theta/worker independence, installed
outside-repo CLI, future phase dispatch, one writer per table across chunks,
nullable gap schema, contiguous aligned IDs, footers complete before either
rename, append/incomplete/second-rename/metadata failures, collision-safe
run directories, exact YAML preservation, exclusive owners, parent-only
metadata, unchanged completed files, restart of unfinished pairs, source/
config/point identity guards and actual read-only H5 provenance.

This is B0 storage/config/metadata validity and v1 regression evidence. It
makes no physical-prior, LER/threshold, confidence/calibration, speedup,
paper-reproduction or general fault-tolerance claim. See
[the B0 guide](docs/auxiliary_v2.md) for exact public contracts and limits.


Final integrity/smoke checks also pass: compilation (`.venv/bin/python -m
compileall -q src tests`), `bash -n scripts/bootstrap.sh`, `git diff --check`,
and pip check. The installed knill-bench-v2 console validates both examples;
a temporary outside-repository CLI prepare preserves input bytes and writes
only config/metadata with real clean H5 provenance and pending points. CLI run
then exits with the explicit B2 boundary and creates no second directory.
All temporary smoke artifacts were removed. All ten Python-package/tests/
scripts directories have DOCS.md and all 47 local Markdown links resolve.
All previously tracked v1 Python sources/tests and requirements.lock are
byte-identical to the base. Main still points at b3cc72a, all dependency
worktrees are clean, and the incoming user .gitignore bytes remain unchanged.
The B0 diff contains 33 intended code/tests/docs/config/packaging files;
.gitignore is deliberately excluded from staging. No experiment output is
committed. The complete exact-lock editable installation command above was
also rerun successfully after environment setup, with no version/source changes.

## B1 — eight-cycle Fig.4(d) runner (2026-10-16)

Used the same isolated exact-lock .venv and editable H5/fork checkouts as B0.
No dependency install/update or source modification was needed.

Initial focused command:

```bash
.venv/bin/python -m pytest -q tests/test_fig4d.py tests/test_v2_config.py tests/test_v2_storage.py
```

**94 passed, 48 warnings, 13.63 s** (21 initial B1 cases plus the 73 remaining
B0 cases; the now-available Fig.4(d) dispatch boundary case was replaced by
real execution coverage). Two additional adapter/file-integrity cases brought
B1 to 23 cases. The next focused `pytest -q tests/test_fig4d.py` had **1 failed,
22 passed, 56 warnings, 11.93 s**: a deliberately missing complete-point file
raised PyArrow's FileNotFoundError instead of the reader's clear ValueError.
Added an explicit missing-file check in saved analysis; no storage/Hex source
change or test suppression was used. The full gate below includes that case.

```bash
.venv/bin/python -m pytest -q
```

**161 passed, 488 warnings, 119.95 s**: all 65 original v1 tests, 73 B0 cases
and 23 B1 cases. No skips/deselections. Warnings are 484 inherited Hex/SciPy
Matrix Market migration notices and four existing v1 empty-legend warnings.

B1 validates exact eight-stage physical circuit equality against Hex at d=3,
exact d-prep measurement counts on both resources, ideal initial data, uniform
Hex noise and noisy final readout; manual supplied/saved bool records at T=2
match legacy global correction-map processing bit for bit, including final
labels and all corrected records. T=1 zero-noise fixtures use d=3/5, with
3/8-shot batches and cached native handles. New physical test fixtures have
at most 11 shots, not the inherited 256-shot legacy fixtures. No d21 circuit
or production sweep was run; only production YAML axes/constraints are parsed.

Tiny d3/T8 execution tests validate exact final partial chunks, one writer/
file per point, schema/IDs/row/error counts, exact input bytes, compact circuit
metadata, deterministic same-partition replay, serial/spawn equality, failed
worker status and restart preserving completed data. Saved-data plot/CLI
tests forbid simulation, verify Agresti-Coull numerical fixtures and reject
invalid counts, incomplete runs, missing/truncated/shuffled-ID/count-tampered
files. No paper agreement, threshold or performance claim is made.

Additional completed checks:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests
bash -n scripts/run_fig4d.sh scripts/bootstrap.sh
git diff --check
```

All pass. Installed console/shell smoke from a temporary directory parsed all
28 production cases without constructing them, ran two separate **3-shot,
d3, T8, p0** cases (B0 prepare followed by CLI resume; shell run), and plotted
saved labels via installed CLI. Both runs had exactly 3 shots, zero errors,
real imported H5 provenance and only config/metadata/one point file. Factory
run still exited 2 at the B2 boundary without a new output directory. Temporary
smoke artifacts were removed. The production wrapper itself was not launched
with the production YAML.

All 53 local Markdown links in the checked guides/package docs resolve.
All original v1 Python/test bytes remain identical to the base, all three
dependency worktrees are clean, Hex is still H5 4278d29, main remains b3cc72a,
and requirements.lock, dependency pins/bootstrap and incoming .gitignore bytes
are unchanged. Only intended B1 bench files are staged; .gitignore is excluded.

## B2 — batched logical-zero factory runner (2026-10-16)

Same isolated exact-lock .venv and read-only editable H5/fork checkouts.
No dependency install/update or source changes were needed. Initial focused gate:

```bash
.venv/bin/python -m pytest -q tests/test_logical_zero_factory.py tests/test_fig4d.py tests/test_v2_config.py tests/test_v2_storage.py
```

**115 passed, 144 warnings, 35.76 s.** This covered the initial 18 B2 cases
and existing v2 regressions, including both now-available kind dispatches.
Added two further B2 cases for default-config/kind guards and real mid-chunk
paired restart, and strengthened the cache check to forbid Stim Circuit
construction during chunks. Final full bench gate:

```bash
.venv/bin/python -m pytest -q
```

**182 passed, 592 warnings, 138.24 s**: all 65 v1 cases, 74 B0 cases, 23 B1
cases and 20 B2 cases. No skips/deselections. Warnings are 588 inherited
Hex/SciPy Matrix Market migration notices and four existing v1 empty-legend
warnings. No test command failed in B2; expected failure-injection/unsupported
model tests passed without suppressing actual runtime errors.

B2 tests use real Hex factories at d3/5, T1/2/3, p0 and small positive p,
with <=7-shot fixtures. They cover finite unit-Hamming p0 gaps, projected
log-weight gaps/model hashes, exactly two supports with alternating roles,
noisy consumed-block measurement and single terminal noiseless oracle,
per-stage shapes/units/finite scores, exact paired IDs/types/counts/join,
one writer per table across exact partial chunks, same-seed repeatability,
theta-independent raw records, identical Hamming/projected physical samples,
oracle-label and future-record isolation, cached samplers/maps/matchings,
serial/spawn equivalence, invalid-gap cleanup and late-chunk restart that
preserves completed pairs and exactly reproduces the original seed stream.
No B3 cuts, abort probabilities or cost analysis are implemented/tested.

Existing Hex parity/frame/sector validation was rerun read-only:

```bash
.venv/bin/python -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py
```

**112 passed, 204 warnings, 14.50 s.** This delegates signed flows, random
preparation signs, two-support reset/frame boundaries, legacy correction-map
equivalence, injected fault persistence, terminal label isolation and exhaustive
d3 both-sector minimum weights to their source tests. These inherited physical
fixtures use d3/5 and <=128-shot batches; exhaustive 512-pattern d3 enumeration
is a deterministic classical oracle, not a large Monte Carlo experiment.

Additional checks passed:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests
bash -n scripts/run_logical_zero_factory.sh scripts/run_fig4d.sh scripts/bootstrap.sh
git diff --check
```

Installed CLI/shell smoke ran from a temporary outside-repository directory.
It parsed six default config cases without simulating the default sweep, then
ran two separate 3-shot d3 cases: T3 p0 Hamming via the new shell wrapper and
T2 p=.001 projected via prepare/resume. Both produced only config/metadata/
two aligned files, with exact IDs/counts/join, correct T/units/readout/oracle,
two live blocks and actual imported H5 provenance. All temporary artifacts
were removed. No production sweep, d21 construction or performance test ran.

All 66 local Markdown links in checked guides/package docs resolve. Original
v1 Python/test bytes are identical to the historical base; B0 storage, B1's
physical adapter, dependency pins/bootstrap/lock and incoming .gitignore bytes
are unchanged. B1 only delegates its existing point scheduling to a shared
v2 helper. All three dependency worktrees are clean, Hex remains H5 4278d29,
main remains b3cc72a and user .gitignore stays excluded from the B2 commit.

## B3 — saved factory acceptance/cost and starter documentation (2026-10-16)

Used the unchanged isolated exact-lock .venv and read-only editable forks.
Initial targeted command:

```bash
.venv/bin/python -m pytest -q tests/test_factory_analysis.py
```

**1 failed, 20 passed, 16 warnings, 10.40 s.** A test compared two equivalent
floating-point cost means with exact equality: histogram-weighted aggregation
gave 53.83333333333333, direct per-shot mean gave 53.833333333333336. Corrected
mean/ratio assertions to use numerical tolerance; exact counts/IDs/masks remain
exact comparisons. Added single-sample SE coverage and strict integer-histogram
validation. No physical/decoder behavior or test selection was changed.

```bash
.venv/bin/python -m pytest -q
```

**203 passed, 608 warnings, 137.58 s**: all 65 original v1, 74 B0, 23 B1,
20 B2 and 21 B3 cases. No skips/deselections. Warnings are 604 inherited Hex/
SciPy Matrix Market migration notices and four existing v1 empty-legend notices.

B3 synthetic six-row fixtures validate exact AND cuts, equality at threshold,
-infinity/no-abort/raw-LER identity, monotone accepted counts, zero acceptance,
first-rejection prefix isolation, label-independent selection/costs, serial/
parallel initial overlap, prep/reset/decode/teleport/restart costs, one final
resource per T-stage attempt, explicit iid renewal gate and paired delta
uncertainty. They check streaming independent of read/row-group partitions,
schema/ID/null/nonfinite/negative/count/status/unit failures, strict analysis
YAML/list/grid, all three runnable templates, optional JSON/CSV/Markdown and
installed CLI. A separate process verifies saved analysis imports none of
Hex/Stim/PyMatching. Analysis leaves simulation bytes untouched.

Complete new v2 smokes use d3/5, p0 and three shots per point for both factory
T3 and full Knill T8, followed by saved analysis. Existing B1/B2 constructor
counters and forbidden-construction guards still pass, verifying cached
sampling/graphs/maps/inference across chunks without timing assertions. No new
large shots or d21 construction, benchmark/production sweep or queue is run.

Targeted Hex integration command, read-only:

```bash
.venv/bin/python -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py external/Hex/tests/test_codecapacity_public.py
```

**128 passed, 320 warnings, 49.97 s.** Includes prior circuit/frame/sector
checks, public False/True preservation, causal projected contexts, oracle/
future isolation, structural unsupported cases and cached native objects.
Exhaustive d3 error-pattern checks are deterministic, not Monte Carlo.

Also passed pip check, compileall, bash -n for bootstrap/both wrappers and
git diff --check. Installed outside-repository CLI smoke validated the starter
templates, ran separate three-shot d3 factory T3 and full Knill T8 cases,
checked no/zero acceptance and iid SE-equivalent cost, list/grid/settings,
all report formats and Fig.4(d) plot. Simulation bytes remained identical
after analysis; all temporary artifacts were removed.

The getting-started guide documents pinned setup, template copy/edit/run,
resume, plotting, saved analysis, public APIs, optional outputs, current Git
refs and statistical/cost/projected-model limits. Local documentation links
resolve. All original v1 Python/test bytes, B0 storage, B1/B2 scientific runners/
worker scheduler, dependency refs/lock/bootstrap and incoming .gitignore bytes
are unchanged. All dependency worktrees are clean, Hex remains H5 4278d29,
and main remains b3cc72a. Only intended B3 code/tests/docs/templates are staged;
the user .gitignore is excluded. Full paper agreement, production performance,
calibrated optimal cuts, queue costs and general fault tolerance are unmeasured.

## Conda knill_system / cluster packaging migration (2026-10-16)

The user requested a new named Anaconda environment, pip-installed research
tools, reproducible cluster packaging/configuration, and deletion of .venv.
Created /home/quantum_teresheys/anaconda3/envs/knill_system with Conda-forge
Python 3.12.15 and pip 26.2.1. Existing numerical requirements.lock is unchanged.
Installed its 34 pins plus 120 pinned research/build/transitive distributions
and the four editable project/fork packages. Jupyter kernel knill_system is
registered inside this environment. Base and other Conda environments were
not modified. environments.yaml, requirements-research.lock and the Linux
Conda explicit lock now describe the setup without a personal env prefix.

Installation/bootstrap commands exercised:

```bash
conda create -n knill_system python=3.12 pip -y --override-channels -c conda-forge
# Initial research install was resolved against the unchanged requirements.lock;
# its exact resolved versions are now requirements-research.lock.
conda run --no-capture-output -n knill_system python -m pip install --no-deps --no-build-isolation -e external/Hex -e external/lomatching -e external/surface-sim -e '.[research,dev]'
bash scripts/bootstrap.sh
conda run --no-capture-output -n knill_system python -m pip check
```

Bootstrap successfully reapplied environments.yaml to the new environment,
verified source pins, reinstalled editable packages and validated v1 config.
All 154 pip lock entries match installed versions; pip check passes.
Key versions: Stim 1.16.0, LDPC 2.4.1, PyMatching 2.4.0, NumPy 2.5.3,
SciPy 1.18.1, JupyterLab 4.6.4, ipykernel 7.4.0, seaborn 0.13.2 and Plotly 7.1.0.

The new Conda interpreter first passed all existing tests: **203 passed,
608 warnings, 162.27 s**. New installed-wheel provenance tests separately
passed **4 tests, 1.48 s**, including no-Git operation, resource/source tamper
rejection and H5 revision enforcement. After offline validation succeeded,
deleted the requested project .venv and ran the complete gate through the new
Conda-selecting launcher:

```bash
bash scripts/python.sh -m pytest -q
```

**207 passed, 608 warnings, 147.48 s**. No skips/deselections. Warnings are
the same inherited SciPy Matrix Market notices and old v1 legend warnings.
No unit test failed during this migration. Scripts' bash syntax, Python
compilation, YAML/TOML, local documentation links and diff whitespace pass.

Packaging audit: building unmodified Hex H5 with pip produced 28 Python files
and **zero matrix resources**. The cluster builder now stages packaging-only
overlays (without editing forks), includes **all 72 .mtx resources**, adds
source manifests and verifies every packaged Python/matrix hash. Numeric
wheel dependencies replace Git URL requirements in distribution metadata;
exact fork refs remain in tool.knill-bench.sources and runtime validation.

```bash
conda run --no-capture-output -n knill_system python scripts/build_cluster_bundle.py --download-deps
```

The initial binary-only dependency download failed because sinter 1.16.0 has
no published binary wheel in the index. Changed the build-side collection to
pip wheel (sdists are built on the build machine); no version was downgraded
or omitted. The final bundle succeeds: **158 wheels, approximately 315 MB**,
including the four projects and all 154 locked pip packages. All dependency
wheel hashes and scientific source hashes match the validated bundle after
the final docs/packaging refresh. The bundle includes install.py, checksums,
locks, configs and guides under ignored results/cluster_bundle.

Independent deployment test: created a temporary isolated Python environment,
installed the bundle with --no-index using local wheels only, and passed pip
check. With Git and Conda removed from PATH, verified v1/v2 provenance, Hex
resource loading, two three-shot d3 v2 protocols (factory T2/full Knill T8),
saved analysis and resume. A separate three-shot v1 SE-memory run committed
both chunks successfully. No source checkout was imported in this test, and
the temporary validation environment was removed. This is a local cluster-
style deployment check, not an experiment on a real cluster or a production sweep.

Hex/lomatching/surface-sim source repositories remain clean at their original
pins. Circuit, decoder, sampler, seed and table semantics are unchanged; only
bench packaging/provenance and launch/setup paths changed. The incoming user
.gitignore bytes are preserved. The project .venv is absent. Full setup and
platform limits (Linux x86_64, CPython 3.12, glibc >=2.28 for this wheel set)
are documented in docs/cluster_setup.md.

## Pre-commit verification and local experiment handoff (2026-10-16)

At the user's request to commit/push the environment and packaging work,
reran `bash scripts/python.sh -m pytest -q`: **207 passed, 608 inherited
warnings, 160.63 s**, with no skips or deselections. `bash scripts/python.sh
-m pip check` reports no broken requirements. Both v2 example YAML files pass
the installed CLI's validate-config command; shell syntax and
`git diff --check` pass. The three dependency repositories remain clean and
.venv remains absent. The existing numerical requirements.lock is unchanged.

The local handoff uses configs/fig4d_v2_example.yaml (eight full Knill stages)
and configs/logical_zero_factory_v2_example.yaml (two factory stages). Both
have d3/5, p0/.001, 64 shots per point, batch size 32 and one worker. Commands
cover sampling, saved Fig.4(d) plotting and factory acceptance/error analysis.
No additional production experiment was launched. The incoming user .gitignore
edit and ignored experiment/bundle artifacts are excluded from the commit.

## V2 round multipliers and Fig.4(d) label (2026-10-16)

The user requested the plot label `logical error rate` and constant multiples
of d for r_0/r_plus. Both experiments now resolve positive integer, fraction
and decimal coefficients with Fraction and integer flooring, never eval or
floating-point products. All resolved depths must fit positive signed int64.
Tests cover exact behavior just below an integer boundary, zero/negative or
invalid denominators, unsupported arithmetic, zero after flooring at a later
swept distance, int64 overflow and unchanged seeds for equivalent depths.

Focused command:

```bash
bash scripts/python.sh -m pytest -q tests/test_v2_config.py tests/test_fig4d.py tests/test_logical_zero_factory.py
```

**127 passed, 168 existing-category Matrix Market warnings, 46.33 s**. Small
physical checks confirm d3 depths (6,2) reach all eight full-Knill stages with
measurement counts (48,16), saved identities/metadata, noiseless labels and a
saved SVG carrying the requested label. A d3 two-stage factory passes (2,6)
through native Hex and saves aligned finite-gap/error tables. Custom-depth
serial/spawn results agree. The standard d-round circuit/manual-array Hex
comparisons are retained. Added a minimum-depth (1,1) adapter fixture for the
full regression gate. No test or implementation failure occurred in the
focused run.

Example config validation now checks the actual Cartesian product rather than
assuming four points. The user's incoming example changes are neither reverted
nor sampled. Direct installed-config resolution gives (d,r_0,r_plus) values
(3,6,2), (5,10,3), (7,14,4) for the requested rules; local documentation links
resolve. Incoming .gitignore and both v2-example bytes are preserved.

First full gate: `bash scripts/python.sh -m pytest -q` — **1 failed, 241 passed,
620 warnings, 160.66 s**. The existing run-collision test caught the new round
validation loop reusing the experiment-name variable, changing every parsed
name to r_plus. Renamed that loop variable to round_name and added an explicit
name-preservation assertion across both kinds and all valid round-rule cases.
The failure did not concern a circuit or decoder; all physical fixtures passed.

After the fix, `bash scripts/python.sh -m pytest -q tests/test_v2_config.py
tests/test_v2_storage.py::test_exact_config_minimal_metadata_run_collision_and_complete`
passed **85 tests, 1.60 s**.

Final full gate: `bash scripts/python.sh -m pytest -q` — **242 passed,
620 warnings, 136.34 s**, with no skips/deselections. Warnings are inherited
SciPy Matrix Market notices (12 additional instances from the three new
physical fixtures) and four existing v1 legend warnings. The minimum-depth
adapter fixture passes. `git diff --check` passes, local documentation links
resolve, both locks are unchanged and all three dependency repositories are
clean. SHA256 checks confirm the three incoming user-edited files remain
byte-identical. Only isolated tiny fixtures were sampled; no production sweep
or user-edited experiment configuration was run.

## V2 directory names and saved-analysis clarification (2026-10-16)

Read the reported run metadata without modifying experiment outputs:
results/20261016T065547.915842Z_factory_v2_example is complete with
resume_count=0. Code inspection confirms analyze-factory loads config.yaml
inside RUN, streams saved Parquet and rewrites the requested report. It does
not dispatch a simulation. `run CONFIG` always creates fresh pending metadata;
only explicit resume loads existing execution. Updated CLI help and docs to
explain updating FACTORY_RUN after editing a simulation config.

New directory format: YYYYMMDDHHMMSS_<config_hash[:8]>_<name>, Asia/Tokyo.
Synthetic storage tests check exact timestamps/hash prefixes, same-config
collision to the next second, midnight date rollover, changed-config hashes,
fresh pending state despite a complete earlier run, preservation of all earlier
run bytes, actual ISO UTC metadata times and legacy-name resume.

```bash
bash scripts/python.sh -m pytest -q tests/test_v2_storage.py tests/test_v2_config.py
```

**109 passed, 3.86 s**. No test failures. Installed analyze-factory --help
explains saved analysis versus `run CONFIG`; local documentation links resolve
and `git diff --check` passes. No user experiment config or production sweep
was sampled for this update.

Full gate: `bash scripts/python.sh -m pytest -q` — **243 passed, 620 inherited
warnings, 169.15 s**, no skips/deselections or failures. Existing actual
Fig.4(d)/factory execution, saved analysis and explicit resume tests all pass
with the new naming code. Incoming .gitignore and both v2 example SHA256s
remain unchanged. All three dependency repositories remain clean.

## Factory wall-time diagnosis (2026-10-16)

The user explicitly requested bottleneck profiling for the current edited
factory example. Read-only inspection found its last job failed by
KeyboardInterrupt after 1373.85 s; no simulation was active when investigated.
Added scripts/profile_factory.py and deterministic tests for nested inclusive/
exclusive clocks, exception accounting and restored runtime patches. Profiling
patches only the diagnostic process, calls the actual _run_point, writes physical
tables to temporary directories and keeps raw timings in results/factory_wall_profile.

Common commands (run serially to avoid measuring our own concurrent profiles):

```bash
# Default-thread baseline with and without --cprofile; d3 only.
bash scripts/python.sh scripts/profile_factory.py configs/logical_zero_factory_v2_example.yaml --distance 3 --p .003 --shots 7 --batch-size 7 --output NEW.json
# Set OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1 before these:
bash scripts/python.sh scripts/profile_factory.py configs/logical_zero_factory_v2_example.yaml --distance 3 --p .003 --shots 100 --batch-size 100 --output NEW.json
bash scripts/python.sh scripts/profile_factory.py configs/logical_zero_factory_v2_example.yaml --distance 5 --p .003 --shots 7 --batch-size 7 --max-wall-seconds 240 --output NEW.json
bash scripts/python.sh scripts/profile_factory.py configs/logical_zero_factory_v2_example.yaml --distance 7 --p .003 --shots 7 --batch-size 7 --max-wall-seconds 60 --output NEW.json
# Comparison: --prior hamming, d3/5/7; extra d7 --trace-validation / --cprofile.
```

The d5/d7 True runs deliberately time out and return exit code 2, saving partial
timings. These are measurement limits, not implementation/test failures or
completed-shot results. d3 True wall=9.517–9.738 s at 7 shots, 9.651 s at 100;
100-shot sampling=.000242 s, decoding=.008989 s, projected models=8.535 s and
merge_independent_events=8.021 s. d5's 240 s cap includes 230.594 s of merging
and .0946 s of PyMatching calls before physical sampling. Per-signature growing
ID tuple validation/sorting is quadratic; cProfile shows ~7.17 million ID-check
generator calls even at d3. cProfile increases d3 point wall to ~40 s, so the
report's primary values use direct perf_counter timers, not profiler totals.

Hamming comparisons d3/5/7 take .937/3.738/16.539 s. d7 validation takes
13.412 s in the ordinary run. Separate line tracing assigns 6.383/6.982 s
to has_all_flows (1972 calls over two validations); absolute times vary across
instrumented runs and are not an optimization result. Default OpenBLAS uses
20 threads; forcing one gives no material d3 improvement. Full details,
measurement exclusions and partial-profile limits are in
docs/factory_performance_report.md; JSON, pstats, snapshot and phase CSV remain
under ignored results/factory_wall_profile. Completed d3 policy comparisons
retain identical physical circuit hashes/seeds.

An initial optional threadpoolctl inventory probe found that package absent;
used stdlib ctypes to query the loaded OpenBLAS library instead, without
installing anything or changing the environment. No scientific/test failure
occurred in this investigation. Full gate:

```bash
bash scripts/python.sh -m pytest -q
```

**245 passed, 620 inherited warnings, 163.25 s**. No skips/deselections.
All prior numerical regressions remain. The earlier round-rule, naming and
axis-label edits are preserved. No fork source/config, numerical lock, or
existing experimental data was modified. No full production sweep was run.

## Module-local Stim factory prior revision (2026-10-16)

User-authorized model change: True excludes preparation/earlier-stage residuals
from its prior only, keeps the native physical circuit and inherited H5 causal
frames, and uses strict local Stim DEMs. No dependency source changes. New
fixtures are d3/5 and at most seven physical shots; fault enumeration is
deterministic model analysis, not Monte Carlo.

Focused commands/results during implementation:

```bash
bash scripts/python.sh -m pytest -q tests/test_logical_zero_factory.py tests/test_v2_storage.py
# 46 passed, 108 warnings, 20.46 s
bash scripts/python.sh -m pytest -q tests/test_factory_local_dem.py
# 7 passed, 36 warnings, 5.67 s
bash scripts/python.sh -m pytest -q tests/test_factory_local_dem.py tests/test_logical_zero_factory.py tests/test_factory_profiling.py tests/test_factory_analysis.py tests/test_v2_storage.py
# 78 passed, 184 warnings, 39.41 s (before adding the cold/warm profile test)
bash scripts/python.sh -m pytest -q tests/test_factory_profiling.py
# 3 passed, 8 warnings, 2.76 s
```

Coverage: independent forward fault/analytic probability equivalence; Pauli
logical boundary and known-frame invariance; exhaustive d3 sector costs with
manual three-stage native frame replay; unchanged sampled physical records;
cache reuse across depths/stages/seeds, invalidation and bounded eviction;
legacy projection/merge forbidden; one full native validation per fresh True
bundle; True/False serial-spawn equivalence, oracle/future isolation, paired
output and failed-chunk restart; old-data labeling and mixed-policy resume
rejection. Profile cold/warm attempts retain identical seed/output hashes.
No numerical test failures occurred in these focused gates. Several documentation
patches initially missed their exact context and were reapplied after reading
the current text; no source/test failure was hidden.

Full bench gate after all source/test changes:

```bash
bash scripts/python.sh -m pytest -q
```

**255 passed, 688 warnings, 164.62 s**. No failures/skips/deselections.
Warnings are the existing SciPy sparse-matrix, Stim measurement-reference, and
plot-legend categories exercised by the inherited suite and additional fixtures.
Full command output was captured in /tmp/knill-local-dem-full-test.log.

Read-only pinned Hex gate (no dependency edits):

```bash
bash scripts/python.sh -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py external/Hex/tests/test_codecapacity_public.py
```

**128 passed, 320 warnings, 55.76 s**. Output: /tmp/knill-local-dem-hex-test.log.

Selected-point timing commands, run sequentially after the bench gate, before
the Hex gate, with no concurrent investigation profiles/tests:

```bash
# Prefix EVERY command below with:
# OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
bash scripts/python.sh scripts/profile_factory.py results/factory_local_dem_profile/config.snapshot.yaml --distance 3 --p .003 --shots 7 --batch-size 7 --prior legacy-projected --max-wall-seconds 60 --output results/factory_local_dem_profile/d3_legacy_7.json
bash scripts/python.sh scripts/profile_factory.py results/factory_local_dem_profile/config.snapshot.yaml --distance 3 --p .003 --shots 7 --batch-size 7 --repeat 2 --max-wall-seconds 120 --output results/factory_local_dem_profile/d3_local_7.json
bash scripts/python.sh scripts/profile_factory.py results/factory_local_dem_profile/config.snapshot.yaml --distance 5 --p .003 --shots 7 --batch-size 7 --repeat 2 --max-wall-seconds 120 --output results/factory_local_dem_profile/d5_local_7.json
bash scripts/python.sh scripts/profile_factory.py results/factory_local_dem_profile/config.snapshot.yaml --distance 7 --p .003 --shots 7 --batch-size 7 --repeat 2 --max-wall-seconds 120 --output results/factory_local_dem_profile/d7_local_7.json
bash scripts/python.sh scripts/profile_factory.py results/factory_local_dem_profile/config.snapshot.yaml --distance 3 --p .003 --shots 100 --batch-size 100 --max-wall-seconds 60 --output results/factory_local_dem_profile/d3_local_100.json
```

All five diagnostics completed without timeout/failure. The 100-shot case is
an explicitly requested opt-in timing diagnostic, never a unit-test fixture.
Current d3/5/7 cold point times: .874790 / 2.507117 / 10.830310 s; warm attempts
.394060 / 2.045403 / 10.088741 s. d3/100 shots: .896075 s. Legacy d3/7 shots
replay: 10.480277 s, including 8.883106 s in two growing-ID merges. New True
has zero legacy projection/merge calls, one local DEM build for T=2 and zero
rebuilds on the second attempt (cache miss=1/hit=3). Full native bundle
validation is one per True compilation, versus three for legacy True.
Current d7 validation remains 7.522175 s of 10.830310 s, the major remaining
cost. Differences in model and first-write lazy imports are explicitly noted
in docs/factory_performance_report.md; historical d5/d7 timeouts are not
completed-time speedup estimates.

Every current diagnostic matches the historical configuration hash and seed.
Physical circuit hashes match historical completed Hamming profiles at all
three distances and historical True d3. Repeated local attempts have identical
paired file hashes. Raw timing artifacts and summary CSV are ignored under
results/factory_local_dem_profile. No full production sweep or existing-run
resume occurred. User .gitignore and both v2 example YAML diffs match their
pre-task byte-for-byte snapshot; Hex remains clean at pinned H5. V1/B1
numerical source was not edited in this task. git diff --check passes.

## 2026-10-16: fixed-d factory T-scaling wall-time report

User-requested opt-in timing experiment after the local DEM revision. Fixed
d=7, p=.003, r0=rplus=7, True local priors, master seed 12345; T=1/2/4/8
each has its own snapshot YAML. No new simulation sweep axis or numerical
source change. Each point uses 1,024 shots, batch 128, one first attempt and
three warm repeats in one process. These are diagnostics, not unit tests.
Each T runs in a separate process, sequentially with no concurrent bench tests.

Exact commands (the loop is also saved as results/factory_T_scaling_d7/measure.sh):

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for T in 1 2 4 8; do
  bash scripts/python.sh scripts/profile_factory.py \
    "results/factory_T_scaling_d7/T${T}.yaml" --distance 7 --p .003 \
    --shots 1024 --batch-size 128 --repeat 4 --max-wall-seconds 600 \
    --output "results/factory_T_scaling_d7/T${T}.json"
done
bash scripts/python.sh results/factory_T_scaling_d7/summarize.py
git diff --check
git -C external/Hex status --short
```

All four bounded diagnostics and all **16 attempts completed**, with no
timeouts/failures. Saved-profile assertions verify fixed settings, eight
sampling/decode batches per attempt, one bundle validation per attempt,
one local DEM build per process and zero warm rebuilds/legacy projection or
event-merge calls. Cache miss=1 and hit=3/7/15/31 for T=1/2/4/8. The local
prior configuration hash agrees across every T/stage, and paired output
hashes agree across all four same-seed attempts at each T.

Warm medians, T=1/2/4/8: sampling+decode **.192585 / .288639 / .510293 /
.893249 ms/shot**; full point amortization **5.860925 / 10.008451 /
18.474526 / 43.290427 ms/shot**. Bundle validation medians **3.696050 /
7.028790 / 15.288759 / 39.269553 s**. Error bars show the observed range
of the three warm repeats, not confidence intervals. First attempts are
reported separately. Summarizer emitted per-attempt CSV, summary JSON and
two figures in PNG/SVG/PDF; PNGs were inspected for layout and labels.

Report: docs/factory_T_scaling_report.md, linked from the existing performance
report. Raw artifacts, exact configs, host details and reproduction scripts
stay under ignored results/factory_T_scaling_d7. No simulation implementation
or unit tests changed, so the preceding 255-test bench / 128-test Hex gates
were not rerun for this documentation-and-measurement task. User .gitignore
and both example config diffs still match the pre-revision snapshot; Hex
remains clean. No production sweep, existing-run resume, staging or push.

## 2026-10-17: user-requested T=3 distance timing through d11

The explicit follow-up extends selected diagnostic distances to d=3/5/7/9/11.
Fixed p=.003, T=3, r0=rplus=d, True local prior, master seed 12345. Each
distance uses a fresh process; four attempts of 1,024 shots/batch 128 measure
one first attempt plus three warm repeats. These remain opt-in measurements,
not large unit-test fixtures or a production-budget sweep. Runtime and pinned
dependency sources were not edited. Measurement spanned October 16–17 JST.

Exact commands (also saved in results/factory_distance_scaling_T3/measure.sh):

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for d in 3 5 7 9 11; do
  bash scripts/python.sh scripts/profile_factory.py \
    results/factory_distance_scaling_T3/config.snapshot.yaml --distance "${d}" --p .003 \
    --shots 1024 --batch-size 128 --repeat 4 --max-wall-seconds 2400 \
    --output "results/factory_distance_scaling_T3/d${d}.json"
done
bash scripts/python.sh results/factory_distance_scaling_T3/summarize.py
git diff --check
git -C external/Hex status --short
```

All **20 attempts completed**, no diagnostic timeout/failure. Saved-profile
assertions validate the fixed settings, shot/batch counts, eight sample/decode
calls and one full validation per attempt, one local Stim DEM per distance,
zero warm regeneration and zero legacy fault propagation/event merging.
Each process finishes at cache miss=1/hit=11/currsize=1. Models share one
configuration hash across three stages and differ across all five distances.
All four attempts have identical paired output hashes at each distance.
Recorded qubits/records agree with 4*d*d-2 and 4*(d*(d*d-1)+d*d).

Warm processing medians are .130245/.213445/.396107/.757258/1.387510 ms/shot.
Full-point amortized medians are .607912/2.968308/14.185958/48.493113/
145.194036 ms/shot. d11 validation is 127.266977 s versus first local prior
.383694 s, including .00149954 s of Stim extraction. d7 warm processing
varies .155776–.429290 ms/shot despite identical output hashes; CPU time also
changes. Its cause is not established, no sample is dropped, and the report
explicitly avoids a fitted complexity claim. Observed min/max ranges are
not confidence intervals.

Summarizer passed and emitted attempts.csv, summary.json and two graphs in
PNG/SVG/PDF. Both PNGs were visually inspected. A documentation-only patch
initially failed to match a redundant context hunk; the hunk was removed and
the patch applied successfully, with no simulation/artifact change. No unit
or numerical tests were changed; previous 255-test bench / 128-test Hex gates
were not rerun for this report-only task. Protected user diffs were checked
against the snapshot saved before this follow-up; Hex stays clean and the
index empty. No existing run was resumed or production sweep launched.

## 2026-10-17: opt-out factory validation and equivalent packed preparation frames

The user clarified skip_circuit_validation=True means skip; False/default
retains one complete native bundle validation. Both factory prior modes now
use packed final-check/exit-frame maps with the same four native matching
calls. Hex/v1/B1 sources are unchanged. Full validation uses the native builder;
opt-out uses its exact function with a private construction-type binding,
returning a normal native bundle whose explicit validate() still works.

Initial integration check:

```bash
bash scripts/python.sh -m pytest -q tests/test_factory_local_dem.py tests/test_logical_zero_factory.py tests/test_factory_profiling.py
```

33 passed, 176 warnings, 26.65 s (before the new test cases were added).
The first new frame-test run had 11 passes and 3 failures: all numerical
comparisons passed, but a cache assertion incorrectly assumed plus plans
shared one template across A/B. H5 templates are per support/basis/depth.
The test now asserts sharing only for the same native module; the profiling
expectation was likewise corrected from two to three templates at T=2.
No numerical workaround or matching change was made. A combined source patch
and a later documentation patch each initially failed context verification;
both were reapplied with correct context, without partial changes.

Focused gate after corrections:

```bash
bash scripts/python.sh -m pytest -q tests/test_factory_frames.py tests/test_factory_profiling.py tests/test_logical_zero_factory.py tests/test_v2_config.py
```

127 passed, 196 warnings, 32.34 s. New physical fixtures remain d3/5 and
<=7 shots. Independent GF(2) products cover byte/chunk boundaries and zero
dimensions. Native full-history comparisons cover every exit frame and
decoded result field; skip/full modes preserve exact physical circuits,
seeds/raw arrays, cache keys and decoded outputs. Both prior and validation
modes pass serial/spawn equality, metadata checks and completed resume.
Runtime sign repair and strict local prior checks remain active.

Separate authorized d7 selected-point diagnostic (not a unit-test workload):

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  bash scripts/python.sh results/factory_frame_optimization/compare.py \
  > results/factory_frame_optimization/compare.log 2>&1
```

T=3, p=.003, r0=rplus=7, seed=917, 1,024 shots, batch 128, with an explicit
300 s wall bound. Full and skipped setup each ran three times with cold local
prior caches, alternating order. Native/packed arithmetic used identical
physical records/models, checking every result field exactly before seven
alternating warm repeats. No tests were run concurrently with measurement.
Setup medians: full 14.179799 s, skipped 3.212478 s. Preparation medians:
native .280835 s, packed .222392 s; whole decode .348699 versus .289702 s.
Packed lookup tables total 2.614502 MiB. Full ranges/host/source hashes and
the reproducible script remain in ignored results/factory_frame_optimization;
docs/factory_frame_optimization.md explains scope and throughput/latency limits.

Full bench gate:

```bash
bash scripts/python.sh -m pytest -q > /tmp/knill-frame-opt-full-tests.log 2>&1
```

**272 passed, 744 existing-category warnings, 168.27 s**. This includes all
v1/B1 tests, strict configs, both factory prior/validation modes, persistence,
serial/spawn and local DEM/cache/causality comparisons. No full-gate failures.

Read-only pinned Hex regression gate:

```bash
bash scripts/python.sh -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py external/Hex/tests/test_codecapacity_public.py > /tmp/knill-frame-opt-hex-tests.log 2>&1
git diff --check
git diff -- .gitignore configs/fig4d_v2_example.yaml configs/logical_zero_factory_v2_example.yaml | cmp - /tmp/knill-frame-opt-protected.diff
git -C external/Hex status --short
git diff --cached --stat
```

**128 passed, 320 inherited warnings, 55.43 s**. Diff checks pass, protected
user edits match the pre-task snapshot, Hex stays clean at H5, and the index
is empty. No user job/run was interrupted, production sweep launched, or
dependency source patched. All final code changes preceded the full gates.

## 2026-10-17: adaptive v2 chunks, buffer_shot and PBS cluster launch

First, all incoming bench changes (including the explicitly authorized user
config/.gitignore edits and supplied cluster script) were committed and pushed
as checkpoint 4e1d684 on auxiliary-system. Reference source was read at
AKTKN/color_code_softoutput 1e88fc4633beb8e2741e8a16cd3554ed5a106732,
plus the installed sinter 1.16.0 ramp-throttled sampler/collection worker.
No dependency checkout was modified or new dependency installed.

An initial full-suite attempt ran concurrently with package source edits:

```bash
bash scripts/python.sh -m pytest -q > /tmp/knill_baseline_tests.log 2>&1
```

271 passed and one v1 resume test rejected the changing source hash (736
warnings, 137.96 s). This was an invalid baseline because edits were in flight;
no compatibility check was relaxed and no v1 source was changed. The final
full gate below runs after package source is frozen. Initial focused legacy
gate passed: 132 tests, 212 warnings, 33.82 s:

```bash
bash scripts/python.sh -m pytest -q tests/test_v2_config.py tests/test_logical_zero_factory.py tests/test_fig4d.py > /tmp/knill_focused_tests.log 2>&1
bash scripts/python.sh -m pytest -q tests/test_adaptive_execution.py > /tmp/knill_adaptive_tests.log 2>&1
```

The first adaptive gate passed 30 tests, 28 warnings, 11.20 s. After adding
legacy omitted-default and PBS cases, a focused run had 39 passes and one
incorrect test assertion using factory report key points rather than rows
(28 warnings, 12.44 s). The assertion was corrected; analysis numerics were
unchanged. All added physical fixtures are d3, <=7 shots, factory T=2/full
Knill T=8. Synthetic timing/data tests do not benchmark physics.

Coverage includes EMA chunk sizing/ramp/caps/tails, useful one-shot probes,
bounded out-of-order windows, exact buffer-sized row groups, paired IDs/gaps,
invalid worker results, failure/restart with complete-point preservation,
worker-local model reuse and explicit chunk-seed replay. Auto partitions can
change actual samples with timing; existing fixed-mode serial/spawn equality
and theta/prior-independent raw-record tests are retained. Legacy saved YAML
with omitted batch_size continues to analyze using its old implicit 32.
CLI worker overrides save effective input/hash without changing source YAML.

PBS tests stub the Conda hook/Python executable and check quoted paths,
environment activation, one-thread libraries, allocated/default/limited CPU
counts, oversubscription, single-node nodefiles and saved-run worker checks.
The supplied filename cluster_run_simualtion.sh is retained, now executable;
PBS mpiprocs equals ncpus in its editable example so nodefile slot fallback
matches the allocation. Logs target the ignored logs directory, which must
exist before qsub.

```bash
bash -n scripts/cluster_run_simualtion.sh
bash scripts/python.sh -m pytest -q tests/test_cluster_script.py > /tmp/knill_pbs_script_final_tests.log 2>&1
bash scripts/python.sh -m pip check
git diff --check
```

Shell syntax passed; final PBS unit gate: 8 passed, 0.56 s. pip check reports
No broken requirements found. Local real-script smoke used a temporary YAML
at /tmp/knill_pbs_smoke_p2tc8ual/input.yaml: d3, p=.002, r0=rplus=2, T=1,
True local prior, 3 shots, buffer_shot=2, initial YAML workers=1. Its output
root was temporary; the edited user examples and production sweeps were not run.

```bash
PBS_O_WORKDIR="$PWD" PBS_NCPUS=2 CONFIG_FILE="$(cat /tmp/knill_pbs_smoke_path)/input.yaml" bash scripts/cluster_run_simualtion.sh > /tmp/knill_pbs_smoke.log 2>&1
knill_smoke_run=$(tail -n 1 /tmp/knill_pbs_smoke.log)
PBS_O_WORKDIR="$PWD" PBS_NCPUS=2 RESUME_RUN="$knill_smoke_run" bash scripts/cluster_run_simualtion.sh > /tmp/knill_pbs_resume.log 2>&1
bash scripts/python.sh -m knill_bench.experiments.cli analyze-factory "$knill_smoke_run" --settings configs/templates/factory_analysis.yaml --output /tmp/knill_pbs_analysis.json
```

Run, completed resume and saved analysis passed. Metadata reports complete,
3 shots, effective workers=2, workers_used=2 and time_adaptive_chunks_v1.
This validates the installed editable CLI and actual Conda/PBS wrapper locally;
no real qsub/cluster-host execution or production performance measurement was
performed. Source/hash resume checks remain strict.

Extended focused command (including the corrected assertion described above):

```bash
bash scripts/python.sh -m pytest -q tests/test_adaptive_execution.py tests/test_cluster_script.py > /tmp/knill_adaptive_cluster_tests.log 2>&1
```

Final full bench gate (all package source changes completed before starting):

```bash
bash scripts/python.sh -m pytest -q > /tmp/knill_full_adaptive_tests.log 2>&1
```

**312 passed, 772 existing-category warnings, 173.96 s**. This retains every
272 pre-existing test plus 40 adaptive/PBS cases. Warnings are inherited SciPy
sparse migration / plotting categories; no decoder fallback was added.

Read-only H5 regression gate:

```bash
bash scripts/python.sh -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py external/Hex/tests/test_codecapacity_public.py > /tmp/knill_adaptive_hex_tests.log 2>&1
git -C external/Hex status --short
git -C external/lomatching status --short
git -C external/surface-sim status --short
git diff --name-only -- src/knill_bench/adapters src/knill_bench/circuits src/knill_bench/decoding src/knill_bench/simulation
git diff --check
```

**128 passed, 320 inherited warnings, 50.71 s**. All three dependency checkouts
remain clean at their exact pinned refs; adapters/circuits/decoding/v1 simulation
have no diff from checkpoint 4e1d684. The original user experiment budgets,
d/p/depth/T/prior settings and .gitignore content are preserved; v2 configs
change only batch policy/output buffer/target settings and explanatory comments.
Package source is unchanged since the final full gate began. Only documentation
and PBS directives changed afterward; the final shell unit/syntax gate above
covers those final directives. No simulation outputs/caches/virtualenvs are staged.

## 2026-10-17: Hex ordinary SE memory and optional complementary gap

Added v2 kind se_memory with Hex's exact native noisy reset / repeated X/Z SE /
noisy final Z circuit. get_logicalgap adds an opposite-observable-class MWPM
solve and optional aligned Parquet. No Hex source, v1 numerical source, B1
physical adapter or factory policy/frame implementation was modified.

Read-only native inspection and a <=7-shot diagnostic at d3/5 checked circuit
round counts and complete DEM columns. d3/5 full circuit DEMs have degree 1/2
columns. Native SurfaceMWPMHomologyGap rejects these graphs at its spatial
planarity restriction; no check was bypassed. A new bench decoder validates
the observable-potential/two-boundary lift algebra on general spacetime graphs.
Complete event signatures are retained; there is no separator splitting,
hyperedge drop, truth/oracle inference or approximation-disjoint escape.

Initial focused gate:

```bash
bash scripts/python.sh -m pytest -q tests/test_se_memory.py tests/test_v2_config.py > /tmp/knill_memory_focused.log 2>&1
```

129 passed and one test failed (120 warnings, 14.63 s). The failed cache test
tried to monkeypatch compile_sampler on a read-only native Stim Circuit
instance. The invalid test patch was removed; cached matching-construction
checks remain. No simulator behavior was changed to accommodate the test.

Integration gate after correcting the test:

```bash
bash scripts/python.sh -m pytest -q tests/test_se_memory.py tests/test_v2_config.py tests/test_v2_storage.py tests/test_adaptive_execution.py > /tmp/knill_memory_integration.log 2>&1
```

**187 passed, 148 warnings, 24.42 s**. After adding invalid-gap and saved-option
cases plus pre-extension golden hashes:

```bash
bash scripts/python.sh -m pytest -q tests/test_se_memory.py > /tmp/knill_memory_final_focused.log 2>&1
```

**57 passed, 156 warnings, 19.46 s**. New physical fixtures remain d3/5,
<=7 shots. Tests cover exact Hex circuits and round/noise boundaries, ordinary
PyMatching labels, unchanged first decode when enabling gap, both H constraints
and opposite L parity, pure-truth-flip isolation, exhaustive tiny-graph class
minima/ties, and independent SciPy binary-integer optimization of both classes
on the d3 circuit DEM. Tiny MILP calls are deterministic verification, not
Monte Carlo or production performance benchmarks. Cached graphs and full-event
model semantics are checked. Hyperedges, detector-free logical mechanisms,
inconsistent potentials and unsupported weights fail without fallback.

Storage/runner tests cover optional-file presence, gap_t001 meaning/dtype,
paired uint64 IDs/counts, bool labels, 3/3/1 output groups, actual metadata,
fixed serial/spawn equality, adaptive spawn, gap-toggle fixed stream/labels,
p0 plain memory, completed resume, failed second-chunk full-point restart,
invalid requested gap rejection and changed-option resume before deletion.
Golden config/point hashes from de21bfc confirm existing kinds are unchanged.

Installed editable CLI/shell/PBS smoke uses only a temporary d3, p=.003,
rounds=d, get_logicalgap=true, 3-shot configuration at
/tmp/knill_memory_smoke_jdqu7rml/memory.yaml, buffer_shot=2 and two workers.
No checked-in example budget or production sweep was executed:

```bash
bash scripts/run_se_memory.sh "$(cat /tmp/knill_memory_smoke_path)/memory.yaml" > /tmp/knill_memory_smoke.log 2>&1
PBS_O_WORKDIR="$PWD" PBS_NCPUS=2 CONFIG_FILE="$(cat /tmp/knill_memory_smoke_path)/memory.yaml" bash scripts/cluster_run_simualtion.sh > /tmp/knill_memory_pbs_smoke.log 2>&1
knill_memory_smoke_run=$(tail -n 1 /tmp/knill_memory_pbs_smoke.log)
PBS_O_WORKDIR="$PWD" PBS_NCPUS=2 RESUME_RUN="$knill_memory_smoke_run" bash scripts/cluster_run_simualtion.sh > /tmp/knill_memory_resume_smoke.log 2>&1
bash -n scripts/run_se_memory.sh scripts/cluster_run_simualtion.sh
bash scripts/python.sh -m pip check
```

Direct wrapper run, real local Conda/PBS-wrapper run and completed resume all
passed. Shell syntax passed and pip check reports no broken requirements.
This is local wrapper validation, not an actual cluster qsub invocation.
The original user configs/.gitignore and all dependency pins/sources remain
unchanged; no new package dependency was introduced.

Final full bench gate (all package source frozen before starting):

```bash
bash scripts/python.sh -m pytest -q > /tmp/knill_memory_full.log 2>&1
```

**369 passed, 928 existing-category warnings, 183.80 s**. All previous 312
cases remain and 57 memory cases are added. Warnings are the existing SciPy
sparse-migration / plotting categories. No full-gate failures.

Read-only pinned Hex gate:

```bash
bash scripts/python.sh -m pytest -q external/Hex/tests/test_factory_circuit.py external/Hex/tests/test_factory_batch.py external/Hex/tests/test_surface_gap.py external/Hex/tests/test_codecapacity_public.py > /tmp/knill_memory_hex.log 2>&1
git -C external/Hex status --short
git -C external/lomatching status --short
git -C external/surface-sim status --short
git diff --name-only -- src/knill_bench/circuits src/knill_bench/simulation src/knill_bench/adapters/hex_factory.py src/knill_bench/adapters/hex_full_knill.py
git diff -- .gitignore configs/fig4d_v2_example.yaml configs/logical_zero_factory_v2_example.yaml
git diff --check
```

**128 passed, 320 inherited warnings, 51.62 s**. All dependency checkouts are
clean at their pinned refs. Scope/diff checks pass: the original user configs,
.gitignore and existing numerical/physical modules have no diff. Actual smoke
outputs contain complete metadata, rounds=3, gap_units=log_weight, and exactly
three joined rows in both tables. Test/output artifacts are temporary or
ignored; no production simulation or cluster submission was launched.


## BENCH-N1 factory custom noise schema (2026-10-17)

Starting bench checkout: clean auxiliary-system e0a5481, matching origin after
fetch. Existing Hex worktree is clean at separately committed/pushed HEX-N2
86c9495094801012b9912bd41935ae48b08d8f92. Updated the bench's exact pin,
bootstrap and provenance/API audit to that existing revision. No dependency
source/version, other fork ref, numerical lock or unrelated protocol changed.

noise_v2 maps strict YAML to native frozen FactoryNoiseModel/idle-window
objects without a physical backend. Added optional typed parameters to v2
config/points and complete custom physical/config identities. Uniform None
is omitted from canonical forms, retaining all old hashes/IDs/seeds (golden
checks for factory/Fig.4(d)/memory). Unknown/duplicate keys, unsafe/malformed
noise, bool/expression/nonfinite/negative numerics and invalid resolved
probabilities/domains at every d/p point fail before output. Fig.4(d)/SE memory
raise the exact required factory-only custom-noise error. Only d/p sweep.
Threshold/prior/workers/shots remain outside physical seed identity. Custom
filenames use noisemodel=custom; paired table schemas are unchanged.

Added a commented seven-shot template and noise/timing/inference guide. N1
explicitly refuses custom physical run/compile pending N2, preventing silent
uniform execution at this checkpoint; validate/prepare support the new schema.
N2 is the next authorized stage, with no production sweep authorized.

Validation so far:
- `bash scripts/python.sh -m pytest -q tests/test_v2_factory_noise.py tests/test_v2_config.py`
  — 124 passed, 1.52 s.
- Initial `bash scripts/python.sh -m pytest -q` — 407 passed, 2 failed,
  928 inherited-category warnings, 193.22 s. Both failures were old test regexes
  expecting 'must descend from H5' after the deliberately updated provenance
  message identifies HEX-N2. The actual rejection behavior was correct.
  Updated only the two pin/audit test names/messages; no physics assertion or
  production algorithm was weakened. The isolated old cluster test similarly
  gave 3 passed/1 failed in 1.26 s before correction.
- `bash scripts/python.sh -m pytest -q tests/test_cluster_packaging.py tests/test_v2_factory_noise.py tests/test_v2_config.py`
  — 128 passed, 2.20 s after the first regex fix.
- `bash scripts/python.sh -m pytest -q tests/test_cluster_packaging.py tests/test_v2_storage.py tests/test_v2_factory_noise.py tests/test_v2_config.py`
  — 153 passed, 4.12 s after both regex fixes.
- `bash scripts/python.sh -m knill_bench.experiments.cli validate-config configs/templates/logical_zero_factory_custom_noise.yaml`
  passes, showing canonical full noise/defaults and compact custom filenames.
- `bash -n scripts/bootstrap.sh` and `git diff --check` pass.

Full clean rerun result will be appended before the N1 commit. All original
v1/Fig.4(d)/memory/factory physical tests and user example budgets remain;
new N1 cases construct no physical circuit. No .venv, source reset, dependency
edit, production run or cluster submission was performed.

Final BENCH-N1 full gate: `bash scripts/python.sh -m pytest -q` — **409 passed**,
928 existing-category warnings, **185.19 s**. This includes all 369 inherited
bench cases plus 40 new schema cases, with uniform physics/seed and pin/API
binding checks. Both obsolete error-message assertions are fixed and no test
is deselected. N1 is complete; N2 integration is next. All dependency source
checkouts remain unchanged by bench.


## BENCH-N2 native factory custom-noise integration (2026-10-17)

BENCH-N1 was committed/pushed as e3e3e8d on auxiliary-system. N2 removes
its temporary execution guard and forwards the fully validated frozen native
noise object directly to Hex FactoryCircuitBuilder. No physical quantum
construction or decoder policy was copied into bench. Hex remains clean and
read-only at 86c9495; v1, full Knill/Fig.4(d), SE-memory numerical adapters,
shared scheduling/seed algorithms, locks and per-shot schemas are unchanged.
The existing user examples/.gitignore and numerical locks are unchanged.

The actual native coupling/readout body, including post-CNOT control idle,
is fed to strict module-local Stim DEM construction. Native pre-coupling
storage idle and preparation/earlier-stage residuals remain physical but are
excluded from this approximation. Analytic target-bit probabilities agree
with DEM weights. The included control-only post-CNOT channel can have no
current target detector/logical effect: a paired physical survivor logical X
flips the terminal label with identical operational records/frames/gaps. This
is explicitly tested/documented, without a posterior or quality-certificate
claim. Terminal readout remains noiseless and evaluation-only.

Both prior/validation modes reuse native custom preparation priors/maps and
all four matching decisions through the existing packed frame plans, including
joint Pauli representatives. Fixed/auto/spawn execution transports frozen
point settings through its existing cache/key. Custom local LRU keys additionally
include the entire native noise hash, conservatively separating even changed
excluded parameters whose actual DEM text can remain identical. The cache
stays bounded; no sampler RNG leaks across points or per-shot model rebuild
is introduced. Uniform cache calls/config/model/physical/seed hashes retain
the previous form.

Compact execution metadata now records the complete noise mapping, canonical
native parameter JSON/hash, physical-noise/circuit/model hashes, actual
operation/readout probabilities, normalized window durations/application
counts and explicit local-prior scope flags. Parent completion, completed
resume and saved analysis cross-check these against the config/point. Altered
noise/hash/scope/inner-policy metadata is rejected; a changed external resume
document fails before unfinished-file cleanup. Saved tables remain exactly
aligned bool labels/float64 gaps with contiguous uint64 IDs and short
noisemodel=custom basenames. No extra mandatory artifact is added. B3's
separate assumed-cost model does not infer timing/costs from noise durations.

Validation commands/results:

- `bash scripts/python.sh -m pytest -q tests/test_factory_custom_noise.py`
  — initial 29 physical/integration cases passed, 156 existing-category warnings,
  24.57 s. No new failing physical test preceded this result.
- `bash scripts/python.sh -m pytest -q tests/test_factory_custom_noise.py tests/test_v2_factory_noise.py`
  — 72 passed, 176 warnings, 25.87 s after adding gate/readout cache separation
  and noiseless zero-multiplier cases. Two further scope/policy tamper cases
  were then added and are included in the full gate below.
- `bash scripts/python.sh -m pytest -q`
  — **443 passed**, 1112 existing-category warnings, **214.21 s**, no exclusions.
  Includes all inherited v1/Fig.4(d)/memory/factory/analysis/provenance cases,
  40 new schema tests and 34 new d3 <=7-shot integration cases. No new large
  physical fixture/production sweep was run.
- Read-only Hex worktree:
  `conda run --no-capture-output -n knill_system python -m pytest -q tests/test_factory_noise_model.py tests/test_factory_custom_noise.py tests/test_factory_circuit.py tests/test_factory_batch.py tests/test_surface_gap.py`
  — **199 passed**, 348 inherited warnings, **36.91 s**. Retains original native
  fixtures; no dependency source change or general adaptive regression run.
- Actual shell/installed-CLI smoke via `bash scripts/python.sh -` used a
  TemporaryDirectory and copied the commented template to a spaced YAML path,
  overriding only output_root, shots=3, create_codecapacity_dem=True and
  batch_size=2. Subprocess commands were
  `bash scripts/run_logical_zero_factory.sh TEMP_CONFIG`,
  `python -m knill_bench.experiments.cli resume TEMP_RUN`, and
  `python -m knill_bench.experiments.cli analyze-factory TEMP_RUN --theta=-inf`.
  All pass; exactly three saved rows and correct noise/prior metadata were
  checked. No smoke output was left in Git.
- `bash scripts/python.sh -m pip check` passes (no broken requirements).
  `bash scripts/python.sh -m compileall -q src`, `git diff --check` and 128
  existing local Markdown link targets pass. Hex status remains clean.

Coverage includes native circuit identity/channel placement, both validation/
prior modes, d3 role swaps/window probabilities, native versus packed frames,
exact analytic local event weights, full custom cache identities, control/oracle
causality, no native constructors in batch decode, zero multipliers, fixed/
auto/spawn aligned tables/counts, theta independence, completed resume,
metadata tamper refusal, early mismatched-doc rejection, failed-chunk restart
and exact fixed replay, and explicit unsupported zero-active-noise True.

N2 changes are scoped to adapters/hex_factory.py; experiments/noise_v2.py,
logical_zero_factory.py and run_v2.py; analysis/factory.py; the new integration
tests; AGENTS/STATUS/TEST; affected package DOCS and user-facing noise/factory/
schema/parallel/getting-started guides. The commented config was added in N1.
There are no known failing bench tests. Model/graph restrictions and the
specified local preparation/storage approximation remain. Stop after N2
commit/push; no production sweep or further protocol extension is authorized.
