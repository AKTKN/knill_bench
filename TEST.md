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

## 2026-10-17 — Simple PBS launcher

The user requested a Conda/CLI launcher whose worker count comes from YAML.
Removed PBS_NCPUS/PBS_NODEFILE inference, WORKERS handling, automatic --workers,
allocation/node guards, saved-worker helper and redundant validate-config
invocation. run still validates configs through the existing strict parser.
The example keeps select=1:ncpus=96, without mpiprocs. Resume calls the existing
CLI directly and preserves saved settings. No Python runtime/physics source,
simulation config, dependency, environment or result schema was changed.

- `bash scripts/python.sh -m pytest -q tests/test_cluster_script.py`
  — **8 passed**, **0.81 s**. Stub-executable cases verify Conda/quoting/threads,
  one-command run/resume, absence of worker overrides under conflicting/missing
  CPU environment variables and a one-entry nodefile with YAML workers=96.
- `bash -n scripts/cluster_run_simualtion.sh` and `git diff --check` pass.
- An actual local smoke harness via `bash scripts/python.sh -` used a
  TemporaryDirectory and a spaced config path copied from the factory template:
  d3/p=.001/T1/three shots, workers=2, buffer_shot=3, auto batches. It invoked
  `bash scripts/cluster_run_simualtion.sh` with PBS_O_WORKDIR set to the checkout,
  CONFIG_FILE set to that YAML, PBS_NCPUS unset, a one-entry PBS_NODEFILE and
  WORKERS=1. The completed metadata retained workers=2 and three shots; input
  and saved config bytes matched exactly. A second identical shell invocation
  with RESUME_RUN set and PBS_NCPUS=not-used completed successfully. All smoke
  files were temporary; no production sweep or real cluster submission ran.
- `bash scripts/python.sh -m pytest -q`
  — **443 passed**, **1112 inherited-category warnings**, **221.51 s**, no
  exclusions or failures. All existing science, saved-analysis and resume tests
  remain green. Hex checkout remains clean; final `git diff --check` passes.

## 2026-10-21 — Lazy saved-data notebook plots

Scope: new analysis/saved_data.py, notebook_plotting.py and figure_style.py,
lazy public exports, six-row synthetic tests, the new saved_figures notebook,
and documentation. No circuit, decoder, runner, schema, dependency pin,
numerical lock, original experiment data or v1/B3 numerical source changed.
Incoming .gitignore and untracked notebooks/basics.ipynb remain untouched.

- `bash scripts/python.sh -m pip install --no-deps --no-build-isolation -e external/plotting_lib`
  installed plotting_lib 0.1.0 in Conda knill_system from the user's existing
  clean checkout f0837a9d2f7f20268ebf705a00731a10c648ad3c. No dependency upgrade.
- `bash scripts/python.sh -m pytest -q tests/test_notebook_plotting.py`
  initially produced 3 failures / 19 passes. Two assertions incorrectly treated
  the sole gap>2 survivor as error-free; its label is True, so accepted_errors=1
  and reduction=-1. The third expected default key/d/p groups to be ambiguous,
  though those groups each contain one point. Corrected the expected values
  and made the ambiguity test explicitly group_by=d. No selection rule changed.
  Rerun: **22 passed, 5.51 s**. The tests validate lazy/no-IO registration and
  key exclusion, aliases/membership, all six editable figures, exact strict
  cuts/abort and label-independent acceptance, unequal batch/row-group bounds,
  rounds/T normalization, frequency, lifetime quartiles, >10 unique-cut error,
  negative/undefined reductions, group/threshold style mapping, incomplete-run
  publication and missing/null/nonfinite/negative/schema/ID/count/config/unit
  rejection. Synthetic points contain six rows; no physical sampling added.
- `bash scripts/python.sh -m pytest -q`
  — **465 passed**, **1112 inherited-category warnings**, **146.41 s**.
  No failures, exclusions or new warning category.
- `bash scripts/python.sh -m pip check` — no broken requirements.
- A `bash scripts/python.sh -` saved-only import check verifies that importing
  NotebookPlots/RunRegistry/FigureStyle loads no stim, hex_qec, pymatching or
  experiments.run_v2. No source/environment compatibility check or native
  constructor is invoked by saved-only plotting.
- A read-only `bash scripts/python.sh -` rendering harness validated the new
  notebook with nbformat and generated all six figures as PNG/PDF under
  ignored results/notebook_plotting_smoke. It used the supplied saved fig4d/
  memory d9 data for the per-round comparison and factory d5/p=.001 (plus d5's
  p sweep for the sixth figure). Factory d5/p=.001 contains 1,000,000 shots,
  609 labels, 20 exact unique all-stage scores and 17 first-stage scores.
  Tested strict-cut curves, T_idx frequency, explicit lifetime cuts [0,2,4],
  unnormalized selected LER, editable axes and 300-dpi exports. Viewed rendered
  lifetime/postselection images. Exact near-equal floating gaps remain distinct.
- `bash scripts/python.sh -m jupyter kernelspec list --json` confirmed the
  existing knill_system kernel uses the intended Conda interpreter.
- Exploratory JSON inspection of the pre-existing basics.ipynb failed because
  that user file is empty; it was preserved and a separate valid notebook was
  created. `git diff --check` initially caught a documentation EOF blank line;
  removed it. Final checks and notebook execution are recorded below.
- Executed every cell against supplied saved data, using the intended kernel:

  ```bash
  bash scripts/python.sh - <<'PY'
  from pathlib import Path
  import nbformat
  from nbclient import NotebookClient
  notebook = nbformat.read('notebooks/saved_figures.ipynb', as_version=4)
  nbformat.validate(notebook)
  NotebookClient(notebook, timeout=120, kernel_name='knill_system').execute()
  nbformat.write(notebook, Path('results/notebook_plotting_smoke/saved_figures.executed.ipynb'))
  PY
  ```

  All cells passed, including all distances in the notebook's factory figures
  and [0,6,8] explicit lifetime/postselection thresholds. Only saved data was
  read. The executed notebook is ignored; the source notebook retains no output.
- Final `bash scripts/python.sh -m compileall -q src`, `git diff --check`, local
  Markdown-link checks and dependency `git status --short` checks pass. Hex and
  plotting_lib checkouts remain clean. No new sweep or physical timing run.

## 2026-10-21 — Reference typography / LaTeX / round_digit

- `bash scripts/python.sh -m pytest -q tests/test_notebook_plotting.py`
  first ran **30 passed / 1 failed**. The new raw-negative validation fixture
  attempted to save -.01 through PointWriter, whose existing writer correctly
  rejects negative scores. Changed the fixture to corrupt the Parquet column
  after a valid publication, as in existing corruption cases. The selected-LER
  zero-error fixture explicitly captures the expected log-axis warning.
  Rerun: **31 passed, 7.21 s**, no uncaptured warnings.
  Added cases cover per-group/per-stage unique-list return/old tuple arity,
  half-up ties (1.25, 2.675, .005), negative digits, raw-array preservation,
  shared/per-plot/None rounding overrides for every gap figure, both lifetime
  passes, rounded automatic-grid limits, partition-invariant summaries,
  invalid options before I/O and raw-negative validation before rounding.
- `bash scripts/python.sh -m pytest -q` — **474 passed**, **1112 inherited-
  category warnings**, **147.57 s**. No failures or exclusions. No new physical
  fixtures or Monte Carlo runs; new cases use six-row synthetic saved data.
- `bash scripts/python.sh -m pip check` — no broken requirements.
- A read-only `bash scripts/python.sh -` render harness used FigureStyle with
  reference typography and labels mapping Physical error rate to a mathrm
  label and logical error rate to p_L. Actual Fig.4(d) saved data rendered to
  results/notebook_plotting_refinement/reference_style.png/.pdf; separately
  `FigureStyle(usetex=True, labels=...)` rendered mathrm/mathsf labels to
  latex_style.png/.pdf using the system latex/dvipng and minimal amsmath
  preamble. Viewed both images. No TeX/package/dependency sources were edited.
- The same harness used factory d5/p=.001 with NotebookPlots(round_digit=6)
  and gap-frequency return_unique=True. Each of eight stages has nine rounded
  unique values; the original first stage has seventeen exact values. Saved
  rounded_gap_frequency.png as a read-only data smoke, not a simulation.
- Executed the updated notebook with:

  ```bash
  bash scripts/python.sh - <<'PY'
  from pathlib import Path
  import nbformat
  from nbclient import NotebookClient
  notebook = nbformat.read('notebooks/saved_figures.ipynb', as_version=4)
  nbformat.validate(notebook)
  NotebookClient(notebook, timeout=120, kernel_name='knill_system').execute()
  nbformat.write(notebook, Path('results/notebook_plotting_refinement/saved_figures.executed.ipynb'))
  PY
  ```

  All cells pass with round_digit=6 and per-group/all-stage unique-list output.
  Existing notebook source outputs were preserved; the new executed copy is
  ignored. Local kernel transport and existing font metadata messages are
  environment diagnostics, not failed tests. No input data was modified.
- Final `bash scripts/python.sh -m compileall -q src`, `git diff --check`, local
  Markdown-link checks and dependency `git status --short` checks pass.
  Incoming .gitignore/basics.ipynb, dependency source and numerical locks remain
  untouched. No production sampling, new scientific model or cluster job.

## 2026-10-21 — Stacked lifetime fractions / mean

- `bash scripts/python.sh -m pytest -q tests/test_notebook_plotting.py`
  — **35 passed, 9.89 s** initially; after legend layout refinement,
  **35 passed, 9.62 s**. No test failures. Replaced private quartile assertions
  with exact all-shot counts/fractions/means, including strict equality,
  -/+infinity (all T/all zero), monotone mean, per-group stack height=100%,
  opt-out of the mean axis, default/optional return arity, row-batch/row-group
  and truth-label independence, both rounding passes and invalid flags before
  I/O. New fixtures remain synthetic six-row data; no physical sampling.
- `bash scripts/python.sh -m pytest -q` — **478 passed**, **1112 inherited-
  category warnings**, **239.53 s**. No failures or exclusions. No v1/B3,
  simulator, decoder, dependency or simulation-config changes.
- A read-only `bash scripts/python.sh -` render used the supplied factory data,
  p=.001, group_by=d, round_digit=6 and thresholds [0,6,8]. Exact means were
  d5 [8,7.972604,7.881825], d7 [8,7.99548,7.977105], d11
  [8,7.99978,7.998529]. The first external-axis legend layout emitted a
  constrained_layout collapse warning. Replaced it with figure-level outside
  upper/lower legends and shortened the right-axis label. PNG/PDF exports
  then pass with layout warnings treated as errors. Viewed the final plot.
  Independent automatic right-axis limits expose small mean changes; raw
  fractions stay on a full 0..100% left axis.
- The first full `NotebookClient(...).execute()` smoke failed on the example's
  new three-variable return: the keyword insertion assumed the old literal
  [0,6,8] cut list, while the user's latest cell had [0,10,30]. Added
  return_summary=True independently of the cut values, preserving the user's
  list. No package numerical/source fix was needed. Rerunning all cells passes.
- Full notebook smoke via `bash scripts/python.sh -` used
  nbformat.read/validate('notebooks/saved_figures.ipynb') and
  `NotebookClient(notebook, timeout=120, kernel_name='knill_system').execute()`.
  An in-memory export-check cell saved the current lifetime Figure to
  results/notebook_lifetime_stacked/lifetime.png and lifetime.pdf; the entire
  executed copy is results/notebook_lifetime_stacked/saved_figures.executed.ipynb.
  Only source cells saved-figures-09 and saved-figures-lifetime-means received
  refreshed execution counts/outputs, after checking that their sources still
  matched. All unrelated source cells/outputs were preserved. Every cell passes
  against saved data, with the user's [0,10,30] thresholds unchanged.
- `bash scripts/python.sh -m pip check` reports no broken requirements.
  `bash scripts/python.sh -m compileall -q src`, `git diff --check`, local
  Markdown-link checks and clean Hex/plotting_lib Git checks pass. New outputs
  are ignored; incoming .gitignore/basics.ipynb and dependency sources remain
  untouched. No production sampling or cluster execution was performed.
- A separate `bash scripts/python.sh -` saved-data smoke used
  FigureStyle(usetex=True), d5/p=.001, round_digit=6 and [0,10,30] cuts, saving
  results/notebook_lifetime_stacked/lifetime_tex.pdf. Actual LaTeX percent ticks,
  dual axes, hatches and figure legends render successfully with layout
  warnings treated as errors.

## 2026-10-21 — Postselected-LER horizontal tick spacing

This is a presentation-only change in analysis/notebook_plotting.py. Existing
common font sizes, saved-data reading, cut masks, rates and all other plots
remain unchanged. No new unit fixture, sampling, dependency or config edit.

- `bash scripts/python.sh -m pytest -q` — **478 passed**, **1112 inherited-
  category warnings**, **99.35 s**. No failures or exclusions.
- Read-only `bash scripts/python.sh -` rendering used the user's supplied
  factory run, round_digit=0 and exact call
  `plot_postselected_logical_error_rate(filter_by={"key":"factory"}, group_by="d", gap_threshold=[0,5,10])`.
  Before: half-step labels 0.0010, 0.0015, etc. After: five visible labels
  0.001, 0.002, 0.003, 0.004, 0.005. After fig.canvas.draw(), renderer bounds
  confirm every adjacent label has >8 pixels separation (actual minimum
  200.36 pixels at 300 dpi), while all retain fontsize=13. Saved/viewed
  results/notebook_postselected_ticks/postselected_ler.png and .pdf.
- A `bash scripts/python.sh -` NotebookClient smoke executed a temporary
  notebook containing the existing saved-figures-01 initialization and
  saved-figures-13 postselected plot plus an in-memory export-check cell,
  with timeout=120 and kernel_name=knill_system. It passes and saves the
  ignored postselected.executed.ipynb. Only saved-figures-13 output/execution
  count was refreshed in the source notebook after a source-equality guard;
  parameters, initialization and every other cell remain unchanged.
- `bash scripts/python.sh -m compileall -q src`, `git diff --check`, local
  Markdown-link checks and clean Hex/plotting_lib status checks pass. No
  dependency source or incoming .gitignore/basics.ipynb change.

## 2026-10-21 — Shared Wilson intervals and notebook shades

- `bash scripts/python.sh -m pytest -q tests/test_confidence.py tests/test_notebook_plotting.py`
  — **58 passed, 7.43 s**. No failures or uncaptured warnings. The independent
  SciPy binomtest(...).proportion_ci(method="wilson") implementation agrees
  across 90/95/99% confidence and analytic integer counts. Checks cover zero/
  full successes, zero trials, broadcasting, count units, per-round endpoint
  transforms, invalid counts/shapes/options, paired 2x2 conservation, the
  error-retention/acceptance ratio identity, Bonferroni-adjusted bounds,
  structural no-cut versus finite-cut observed all-pass and undefined cases.
  Plot tests verify every included shade and both excluded lifetime axes,
  selected denominators and undefined-band omission. Removed the former
  expected zero-positive-data log warning: zero observed errors now have a
  positive Wilson upper band. No pseudocount changes the plotted estimate.
- `bash scripts/python.sh -m pytest -q` — **501 passed**, **1112 inherited-
  category warnings**, **109.71 s**, no failures/exclusions. New storage/plot
  cases retain six synthetic rows; statistical count checks do not sample.
- A read-only `bash scripts/python.sh -` harness ran all six notebook APIs
  against the supplied factory data, round_digit=0, p=.001 for gap/abort/
  reduction/lifetime, [0,5,10] selected-LER cuts and [0,10,30] lifetime cuts.
  Saved PNG/PDF files under ignored results/notebook_wilson_intervals.
  FillBetweenPolyCollection counts were raw LER=3, frequency=3, abort=3,
  reduction=3, selected LER=9, lifetime=0. Viewed selected-LER/reduction renders.
- Full notebook smoke via `bash scripts/python.sh -` used nbformat.read/validate
  and NotebookClient(notebook, timeout=120, kernel_name='knill_system').execute().
  In-memory export cells after each non-lifetime plot saved its current
  Figure (including user semilogy changes) as PNG/PDF. Every cell passed;
  the executed copy is results/notebook_wilson_intervals/saved_figures.executed.ipynb.
  Only saved-figures-03/05/07/11/13 output/execution counts were copied back,
  after checking source equality. Their source code and user parameters,
  plus every other/lifetime cell and output, were preserved. A short Markdown
  note documents default shades; no simulation config was edited.
- `bash scripts/python.sh -m pip check` — no broken requirements.
  `bash scripts/python.sh -m compileall -q src`, `git diff --check`, local
  Markdown-link checks and clean Hex/plotting_lib checks pass. A documentation
  patch initially rejected a stale context; reapplied it against current text.
  No test/science failure or source fallback resulted.

Statistical definitions follow NIST's Wilson score description, with the
paired reduction algebra/Bonferroni construction derived and documented in
[the notebook guide](docs/notebook_plotting.md). These are pointwise nominal
intervals, without simultaneous or selected-cut coverage claims. V1/B3/CLI
Wilson/adjusted-Wald contracts, all simulation schemas, physical adapters and
fork pins are unchanged. No resampling, new experiment or production sweep.

## General Knill EC memory and physical-noise revision (2026-10-22)

Implemented `kind: knill_ec_memory` with positive T_tel (default 8), while
retaining legacy fig4d_reproduction input/saved identities and T=8/uniform
semantics. Both new physical models use the native Hex policy and ideal
terminal destructive readout. Capacity inserts exactly current-data
DEPOLARIZE1(p) before every teleportation; it is not a projected-prior option.
See docs/knill_ec_noise_plan.md for the plan, region table and limitations.

Commands and corrected checks:

- `bash scripts/python.sh -m pytest -q tests/test_fig4d.py tests/test_v2_config.py --disable-warnings`
  initially 2 failed, 105 passed, 64 warnings, 11.57 s: two shipped-config
  expectations still used the old kind after migration. Updated only those
  expectations; all legacy protocol/identity tests remain.
- The first combined new/native run had 2 failed, 124 passed: the new target
  assertion assumed native Stim CX instructions were coalesced despite
  intervening noise(0). Collecting every native CX control fixed the test;
  no physical construction changed for this correction.
- `bash scripts/python.sh -m pytest -q tests/test_knill_ec_memory.py external/Hex/tests/test_knill_noise.py --disable-warnings`
  — 56 passed, 168 warnings, 12.33 s. New physical fixtures are d3/5,
  <=7 shots, T=1/2/3. Coverage includes actual native circuit/raw/global-frame
  decode parity, cached native handles, p0 labels, noise identities/seeds,
  protocol/parser rejection, fixed/auto output, metadata checks, complete
  resume, fixed serial/spawn equality and failed-point restart.
- Native capacity validation compares direct MWPM with all 512 d3 masks in
  each pure X/Y/Z pattern family and each X/Z memory basis, using synthetic
  records in <=7-row batches, not Monte Carlo or all 4^9 mixed patterns.
- `bash scripts/python.sh -m pytest -q --disable-warnings`
  before the Hex dependency commit: 11 failed, 521 passed, 1180 warnings,
  118.32 s. Ten inherited v1 execution cases hit its pre-existing dirty-fork
  provenance mismatch (prepare attaches a patch field, execute does not);
  the remaining check explicitly required clean Hex. A focused
  `bash scripts/python.sh -m pytest -q tests/test_execution.py -x --disable-warnings`
  reproduced the same mismatch (1 failed, 16 warnings, 3.11 s).
  Fixed integration order: commit tested Hex, update exact pin/API audit,
  and rerun with clean dependency; no v1 code or test behavior was weakened.
- **Final full gate:** `bash scripts/python.sh -m pytest -q --disable-warnings`
  — **532 passed**, 1208 existing-category/new-call-site SciPy warnings,
  **151.11 s**. Includes all incoming notebook/Wilson tests unchanged.
- Hex gate: `bash scripts/python.sh -m pytest -q external/Hex/tests -k 'not ler_is_statistically_compatible and not test_real_cluster_llr_threshold_produces_mixed_short_long_batch' --disable-warnings`
  — **372 passed**, **3 deselected**, 708 warnings, **68.49 s**. Excludes the
  same two 2048-shot statistical cases and previously reproduced adaptive
  BP-LSD seed assertion as N2. Native old tests were not edited.

Installed CLI/shell smoke: `bash scripts/python.sh /tmp/smoke_knill_noise.py`
(with final output captured as results/knill_ec_noise_smoke/final_smoke_output.json).
For each new model: d3, p=0/.02, r=(1,2), T=2, three shots per point,
fixed batch=3/workers=1 and auto/workers=2. Four runs, 24 trajectories total,
completed resume with byte-identical Parquet, exact IDs [0,1,2], complete
metadata with ideal boundary, saved counts and `plot-knill` PNGs all pass.
Final Hex was clean at 8fa2200315cc4feaccf341a461f91739233de08a.
Raw outputs/configs/figures/summary remain ignored under
results/knill_ec_noise_smoke. All eight tiny points observed zero errors;
these observations provide no threshold or statistical accuracy evidence.
Use the committed three-shot templates and run/resume/plot-knill commands in
the guide to reproduce the checks without the temporary orchestration script.

`bash scripts/python.sh -m pip check` passes. Shell syntax passes for bootstrap,
run_knill_ec_memory, run_fig4d and the unchanged PBS wrapper. `bash scripts/python.sh -m compileall -q src external/Hex/src`, local new-guide links and both
`git diff --check` gates pass. Incoming unrelated .gitignore, notebooks,
plotting sources/tests and guide are byte-identical to their initial contents;
shared guide updates are append-only and their incoming portions remain unstaged.
Other dependencies and the hex-parallel worktree are untouched. No production
sweep, statistical paper-agreement, performance or threshold claim is made.

## 2026-10-22 — Selected-key ideal-Bell/capacity x conversion

Implemented per-figure rescale_p_keys on plot_logical_error_rate only, using
the user's supplied x=(23/10)*p-(8/5)*p**2 for the named registry keys. This
is a coordinate view of saved statistics, with no inferred model selection,
new sampling, fitting, pooling or LER/interval recomputation. See
[notebook plotting](docs/notebook_plotting.md) for usage and the supplied
logical-Z/T=1 channel-equivalence assumptions.

- `bash scripts/python.sh -m pytest -q tests/test_notebook_plotting.py --disable-warnings`
  — **57 passed**, **12.58 s**. Twenty new synthetic cases check .01/.03/.05/.07
  map to .02284/.06756/.11100/.15316 for only the requested key, both distance
  groups and both per_rounds modes. They verify band/line coordinates, unchanged
  LER/interval y values/legends/files, raw-p filtering, grouping without key,
  zero/no clipping, no-op defaults/empty inputs, early unknown/type rejection,
  and no IO for filtered-out paths. Fixtures remain six saved rows, no sampling.
- `bash scripts/python.sh -m pytest -q --disable-warnings`
  — **552 passed**, **1208 warnings**, **167.91 s**. No failed checks.
- `bash scripts/python.sh /tmp/smoke_ler_p_rescale.py`
  — passes using the actual notebook's saved ideal_bell and code_capacity
  runs (20261022100223_0522ba07_ideal_bell and
  20261022095055_e051a690_code_capacity). Both declare logical-Z Knill, T=1,
  ideal final readout; only ideal_bell's p is transformed. Eight curves from
  52 published points/52 million saved rows render in the requested log-x flow.
  Every x coordinate matches the saved p or supplied polynomial; every y
  matches saved error/shot counts. All config/metadata/Parquet hashes are
  identical before and after. compile_sampler, compile_detector_sampler and
  Matching.from_check_matrix were patched to raise throughout figure/export,
  proving the smoke did not sample or construct a decoder.
  PNG/PDF exports remain ignored at
  results/notebook_p_rescale/code_capacity_vs_ideal_bell.{png,pdf}; the PNG was
  visually inspected. No curve-agreement hypothesis test is asserted.
- `git diff --check` passes. Initial SHA256 values confirm the user's existing
  notebooks/saved_figures.ipynb and .gitignore edits remain untouched. Hex is
  still clean at the existing pin; no simulation schema/config/runner, physical
  code or other notebook outputs were modified.

## 2026-10-22 — General Knill simulation and selectable True priors

User reported the general-Knill True guard blocking d-round preparation and
requested kind=knill_sim. Clarified existing Hex full-prefix versus local DEM
scope; user explicitly selected both as configurable options. Added fixed
codecapacity_prior=module_local/default or full_prefix for general True Knill.
False retains Hamming, physical noise/records/seeds and existing valid config
hashes. New scope metadata and cache keys distinguish inference models; no
unsupported model silently falls back. See [contract](docs/knill_sim.md).

Commands/results, from bench root in Conda knill_system:

- `bash scripts/python.sh -m pytest -q tests/test_knill_ec_memory.py tests/test_fig4d.py tests/test_v2_config.py --disable-warnings`
  — 137 passed, 160 warnings, 17.95 s after independent alias/guard plumbing.
- Tiny direct native-boundary smoke constructed local d3/r3 and d5/r5, and
  prefix d3/r1, T=1/p=.001, then sampled/decoded three shots each: all pass.
- `bash scripts/python.sh -m pytest -q tests/test_knill_sim.py --disable-warnings`
  — **30 passed**, 148 warnings, **18.20 s**. Covers the user's full grid
  parsing with sampler construction forbidden; both general names/options;
  strict irrelevant/unknown-field rejection; False hash compatibility;
  prior-independent case IDs/seeds/raw seven-shot arrays; both new physical
  models; actual d3/5 d-round preparation; cache reuse and no per-shot model/
  sampler/graph construction; prep/past exclusion hashes; noisy terminal
  boundary; exact local ideal-Bell/capacity sector DEM probabilities under
  p_cap=2.3*p-1.6*p**2; native full-prefix/global-map decode parity for all
  three physical models; unsupported/p0 rejection before sampler compilation;
  fixed/auto run/resume/CLI and notebook saved readers; inference-scope
  tamper rejection; fixed serial/spawn equality.
  Removed only the obsolete knill_ec_memory True-rejection parameter from
  the previous test. Legacy False/factory/SE/v1/native expectations remain.
- `bash scripts/python.sh -m pytest -q external/Hex/tests/test_codecapacity_public.py external/Hex/tests/test_knill_noise.py --disable-warnings`
  — **41 passed**, 188 warnings, **26.54 s**, read-only. Confirms native
  prefix causal/context/unsupported-model and existing physical-noise tests.
- **Full gate:** `bash scripts/python.sh -m pytest -q --disable-warnings`
  — **581 passed**, **1356 warnings**, **182.02 s**. No failed checks.
- `bash scripts/python.sh /tmp/smoke_knill_sim.py > results/knill_sim_smoke_output.json`
  — four actual CLI/wrapper runs with workers=2, three shots per point,
  p=.001/T=1, each True mode under fixed batch=3 and auto. Local uses d3/5,
  r_0=r_plus=d; prefix uses d3/r=(1,1). All 18 saved trajectories are
  published with IDs [0,1,2], the selected prior label/scope and complete
  metadata. Installed knill-bench-v2 completed resume leaves Parquet bytes
  unchanged; plot-knill/summarize_saved work for both modes. Every tiny point
  observed zero errors; no statistical agreement is inferred. Configs, runs,
  summaries and PNGs stay ignored under results/knill_sim_smoke.
- `bash scripts/python.sh -m pip check` passes, as do
  `bash scripts/python.sh -m compileall -q src` and `git diff --check`.

New physical fixtures are d3/5 and <=7 shots. No user production configuration
or sweep was run. Full-prefix still rejects its known d3 2/3-round unsupported
X-sector structure; local resolves that scope issue by explicitly changing
inference assumptions, without erasing physical prep/past residuals. Hex and
all dependency source/pins are unchanged/clean. Incoming and ongoing user
notebook/.gitignore edits, earlier plotting source changes and existing saved
data are preserved. No benchmark, threshold or exact posterior claim.

## 2026-10-24 — Fixed-R preparation prompt 00

First reviewed the existing two-file diff, parsed both notebook versions as
JSON and ran `git diff --check`. Checkpoint command:
`git add -- .gitignore notebooks/saved_figures.ipynb && git commit -m "chore: checkpoint notebook updates and local timegap workspace ignore" && git push origin auxiliary-system`.
Commit 2e618b9 was pushed successfully. `git switch -c surface-prep-fixed`
then created the requested child branch. No implementation commit/push ran.

Audited the actual AGENTS/guides, legacy compiled types/decoder and ordered
worker/runner/storage interfaces plus v2 scheduler differences. Actual Hex
remains clean at 8fa2200315cc4feaccf341a461f91739233de08a; LOM/surface-sim
are clean at their unchanged pins. The supplied validation's older Hex pin
and larger physical shot counts were not substituted for current evidence.
The initial attempted external/refs.lock.yaml read found no such file;
the authoritative pins were read from pyproject.toml and actual dependency HEADs.

Seed review/application:

- `git apply --stat surface_timegap/seed_knill_bench.patch` and
  `git apply --check surface_timegap/seed_knill_bench.patch` pass. Reviewed
  full original DEM/matching code and synthetic tests before
  `git apply surface_timegap/seed_knill_bench.patch`.
- Input patch SHA256:
  170de7a2a95ece2eacb57aa30a0b8f164566d42992b263d3f661b22b51aec20e.
  A reconstruction comparison confirms temporal_matching.py and both seed
  test files are byte-identical; temporal_dem.py only adds source SHA256,
  strictness and rounding metadata. No competing H/P/F/S/B dataclass exists.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_dem.py tests/test_temporal_matching.py --disable-warnings`
  — **67 passed**, **1.13 s**, in the actual Conda interpreter.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_contract.py tests/test_temporal_dem.py tests/test_temporal_matching.py --disable-warnings`
  — initially **84 passed**, **2.06 s**; after adding the one-shot disjoint-
  buffer back-reference regression, **85 passed**, **1.32 s**. All new cases
  are synthetic. They check the supplied exhaustive optimum/path/constraint
  gates, explicit integer R/defaults, dtype/count validation, separate truth
  interface/storage and source metadata. They do not certify the later
  physical adapter, its oracle isolation or physical calibration.

Full validation correction:

- `bash scripts/python.sh -m pytest -q --disable-warnings > /tmp/knill_surface_prep_gate.log 2>&1`
  — **1 failed, 665 passed**, **1348 warnings**, **244.78 s**. I added the
  completed-label map field in preparation.py while this gate was running.
  The existing test_streaming_aggregate_only_matches_full_shot_run then
  correctly rejected resume with a source/environment mismatch. Comparing
  its archived knill_bench-source.tar.gz to current source identifies only
  preparation.py as changed. No decoder or resume rule was weakened.
- `bash scripts/python.sh -m pytest -q tests/test_execution.py::test_streaming_aggregate_only_matches_full_shot_run --disable-warnings > /tmp/knill_surface_prep_failure_check.log 2>&1`
  — **1 passed**, **16 warnings**, **22.47 s**, with source edits finished.
  A fresh full gate was started with Python source held fixed.
- `bash scripts/python.sh -m pytest -q --disable-warnings > /tmp/knill_surface_prep_gate_final.log 2>&1`
  — **666 passed**, **1356 inherited-category warnings**, **276.16 s**.
  All existing tests are retained; 85 new synthetic cases were added.
  This is the complete gate against the final Python source. No new physical
  sampling test, Hex modification or production sweep is part of prompt 00.

`bash scripts/python.sh -m pip check` reports no broken requirements;
`bash scripts/python.sh -m compileall -q src` passes. A local-link audit
resolves README/theory/package/decoder/test guide targets. Documentation patch
context errors were corrected using the actual file headings/endings, without
partial file edits. `git diff --check` passes. The checkpoint notebook and
.gitignore have no subsequent diff; dependency repositories remain clean.

## 2026-10-24 — Fixed-R preparation prompt 01

The user explicitly requested the prompt-00 commit/push first, then prompt 01.
`git commit -m "00: define fixed-R preparation theory and contracts"` created
e3de069 (16 files), and `git push -u origin surface-prep-fixed` succeeded.
Hex status was clean at 8fa2200315cc4feaccf341a461f91739233de08a;
`git -C external/Hex push origin auxiliary-system` returned Everything up-to-date.
No Hex commit/source/pin or other dependency/worktree change was made.

Read prompt 01, its shared implementation plan/00 contract, actual Code,
native primitives, config/grid/CLI and legacy builder/runner interfaces.
Implemented only native circuits/config/truth splitting and a pre-output
runner guard; no high-level decoder, metric, Monte Carlo worker or report is
claimed here. All new sampling fixtures are d3/5 and <=7 shots; no supplied
older-pin large validation script or production sweep was executed.

Commands/results from Conda knill_system:

- Three-shot direct builds at d3/R2/p0 and d3/R3/p=.001 pass. Strict completed
  DEMs connect to the unchanged seed core, with no dependency patches. The
  p0 circuit has 16 physical measurements and 13 ideal evaluation measurements;
  tau_X/tau_Z/logical_Z all zero. These are fixtures, not statistical estimates.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_circuits.py --disable-warnings > /tmp/knill_prep_01_circuits.log 2>&1`
  — initial **1 failed, 34 passed**, 120 warnings, 4.46 s. The only failure
  was an unfilled expected legacy circuit SHA placeholder in the test. The
  measured SHA was already available; replaced the placeholder with
  1c5706d386c7089b0fbe71a9949e32a77244cce99c77772f9df801eeb6c74a9d.
  No physics, assertion convention or decoder rule changed to address it.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_config.py tests/test_preparation_contract.py --disable-warnings > /tmp/knill_prep_01_config.log 2>&1`
  — **68 passed**, 3.92 s, before extra numeric/domain edge cases were added.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_config.py tests/test_preparation_circuits.py tests/test_preparation_contract.py tests/test_temporal_dem.py tests/test_temporal_matching.py tests/test_circuits.py --disable-warnings > /tmp/knill_prep_01_focused_gate.log 2>&1`
  — final **216 passed**, **288 existing-category warnings**, **16.62 s**.
  Earlier focused refinements passed 213/214 cases. Current coverage includes
  exact native physical prefixes at d3/5 R2/3/4/5; noisy-first/last readout,
  intermediate/late/corner data injections; unknown first-X negative controls;
  ideal tau/logical-Z and known-Z anchor; output/evaluation/offline counts;
  instrument/signed flows, strict DEM options/failure, changed noise/probability
  domain capability errors, no sampler/matcher in compilation, exact marginal
  DEM parity probabilities at four current-pin d/R settings; physical versus
  nominal noise hashes/samples/seeds; real sampler/core truth isolation;
  fixed defaults/axes, duplicate/unsafe/unknown/overflowed inputs and pre-output
  runner rejection. Existing circuit tests and all prompt-00 tests are retained.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_circuits.py tests/test_preparation_config.py --disable-warnings > /tmp/knill_prep_01_science_final.log 2>&1`
  — 95 passed, 136 warnings, 5.97 s, before the final native-rate audit case.
- Reconstructed config.py from `git show e3de069:src/knill_bench/config.py`
  in an isolated module and checked exact canonical config/grid hashes:
  b18095133ef63d3c315c612e0748bfda8caa607e3bdc38d8a3db31a6943cd072 and
  8815093f14af3939de1a25718e3c6dfdb159eaf80cfb63444d6a8918179d75a9.
  The new regression tests retain these pre-extension goldens.
- Reconstructed the legacy builder directly from
  `git show e3de069:src/knill_bench/circuits/builders.py` in an isolated module:
  its d3/Z/noisy-preparation/R-independent two-cycle circuit **and DEM** match
  the current legacy branch exactly. No sampling is needed for this comparison.
- `conda run --no-capture-output -n knill_system knill-bench validate-config configs/templates/surface_prep_fixed.yaml > /tmp/knill_prep_01_cli.json`
  — installed CLI passes, one d3/R3 point, no physics/sampling/output creation.
- `bash scripts/python.sh -m pip check` — no broken requirements;
  `bash scripts/python.sh -m compileall -q src` passes. README/theory/preparation/
  package/circuit/simulation/decoder/test guide links resolve, new-file
  whitespace checks and `git diff --check` pass.
- `bash scripts/python.sh -m pytest -q --disable-warnings > /tmp/knill_prep_01_full_gate.log 2>&1`
  — **762 passed**, **1496 existing-category warnings**, **187.01 s**.
  All 666 previous tests remain; 96 circuit/config cases were added. Python
  source/tests were held fixed throughout this successful first full gate.
- Three-shot d3/R1/p0 direct builder/sampler/split smoke (seed=9) also passes:
  online X shape (3,0), online Z shape (3,4), all noiseless evaluator labels
  zero. This checks the advertised positive-R/empty-sector boundary without
  constructing a runner, output directory or terminal decoder.

Full gate was started after all Python source/tests were finalized; subsequent
edits are documentation only. Prompt 01 remains a local diff, preserving the
user's notebooks/configs/.gitignore, all saved data and clean dependency sources.

## 2026-10-24 — Prompt 02 completed DEM and boundary constraints

The user authorized checkpointing prompt 01 before implementing prompt 02.
`git diff --check` passed; staged only the 21 prompt-01 files and ran
`git commit -m '01: implement fixed-R preparation and isolated truth'`, then
`git push origin surface-prep-fixed`. Commit **3cdc594** is on the remote.
Hex remains clean on auxiliary-system at HEX-K1; no artificial dependency
commit, source edit, pin update or other-worktree change was made.

Reused the supplied TemporalDemModel/TemporalMatching; only the model layer
was extended. New setup certification and artifact I/O do not construct a
sampler/matcher. Native injected-fault tests use exact one-fault DEMs, not
sampling. New restored-core fixtures use three zero syndromes; one separate
manual physical smoke uses three d3/R2 shots. No production sweep was run.

- `bash scripts/python.sh -m pytest -q tests/test_temporal_dem.py tests/test_temporal_matching.py tests/test_preparation_contract.py --disable-warnings > /tmp/knill_prep_02_seed.log 2>&1`
  — **85 passed**, 0.86 s after the parser/model refactor.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_model_artifact.py --disable-warnings > /tmp/knill_prep_02_artifact.log 2>&1`
  — **32 passed**, 0.70 s for the initial artifact/cost cases.
- `bash scripts/python.sh -m pytest -q tests/test_preparation_boundary_model.py tests/test_temporal_model_artifact.py --disable-warnings > /tmp/knill_prep_02_models.log 2>&1`
  — initial **1 failed, 52 passed**, 124 warnings, 4.73 s. The sole failure
  was the stripped-evaluation negative-control fixture: Stim's append helper
  rejected an empty target list on an error term after removing its labels.
  Constructed that test instruction with explicit `stim.DemInstruction`;
  no scientific condition, parser rule or expected response was relaxed.
  The corrected 53-case gate passes before the additional edge cases below.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_dem.py tests/test_temporal_matching.py tests/test_temporal_model_artifact.py tests/test_preparation_boundary_model.py tests/test_preparation_contract.py tests/test_preparation_circuits.py tests/test_preparation_config.py --disable-warnings > /tmp/knill_prep_02_focused.log 2>&1`
  — **244 passed**, 272 warnings, 10.35 s. Later additions cover active-zero
  cost paths, dropped invisible labels and malformed artifact provenance.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_model_artifact.py tests/test_preparation_boundary_model.py tests/test_temporal_dem.py tests/test_temporal_matching.py tests/test_preparation_contract.py tests/test_preparation_circuits.py tests/test_preparation_config.py --disable-warnings > /tmp/knill_prep_02_focused_final.log 2>&1`
  — final **247 passed**, **272 existing-category warnings**, **10.74 s**.
  Native d3/5 R1/2/3/5 noiseless/.003 models certify same-X online and all
  evaluation signatures/probabilities. Distinct physical/nominal p is checked.
  Explicit R2 first/final readout, corner/interior data and correlated
  two-qubit Pauli injections give independently predicted full detector,
  temporal parity and tau responses. Tests retain future-only spatial ports,
  two-future contracted-zero labels, invisible logical events and parallel/
  inactive mechanisms. Hand-derived .1 XOR .2 = .26 prevents probability
  summation. Source coordinates do not affect classification. Synthetic
  fixed-one/zero solver costs and active quantized-zero paths are verified.
  Artifact tests preserve original columns/feature order, forbid DEM parsing
  during load/decode, reject invalid ranges/roles/schema/derived costs even
  after rehashing, reject duplicate JSON keys and check owning-run hashes.
- `bash scripts/python.sh -m compileall -q src tests` — passes;
  `bash scripts/python.sh -m pip check` — no broken requirements.
- Three-shot d3/R2/p=.003 production sampler (seed=617), split, certified
  artifact write/read, matching decode and full-column witness expansion:
  actual original-column syndrome and feature products agree with the
  restored-core predictions. JSON summary is `/tmp/knill_prep_02_smoke.json`.
  Artifacts were written only in a temporary directory and removed afterward.
- Smoke results: all three statuses are ok, integer gaps are 9372, original
  and active mechanism counts are both 92; maximum marginalized probability
  difference is 3.469446951953614e-18. The persisted/reloaded payload SHA256 is
  b1a7f21fdaa41dfaf5e93d2ce8446986463ced6631e9d13f258e0fb7183c4672.
- `bash scripts/python.sh -m pytest -q --disable-warnings > /tmp/knill_prep_02_full_gate.log 2>&1`
  — **828 passed**, **1628 existing-category warnings**, **191.44 s**.
  All 762 previous tests remain, with 66 new model/artifact cases. No Python
  source or tests changed during this successful first full gate.
- Changed/new guide link targets and new-file whitespace pass, as does
  `git diff --check`. Git scope checks confirm no changes to existing configs,
  notebooks, .gitignore or dependency/environment pins. Hex, lomatching,
  surface-sim and external plotting_lib source checkouts stay clean.

All Python source/tests were finalized before the full suite. Only repository
documentation was edited while that source-frozen validation ran. The
high-level adapter/metrics, runner-owned artifact publication and saved-data
analysis are still their later prompts; the existing pre-output guard remains.
Prompt 02 is left as the requested local implementation diff; only the
explicitly requested prompt-01 checkpoint was committed/pushed this turn.

## 2026-10-24 — Prompt 03 batch decoder and preparation metrics

At the user's request, checked `git diff --check`, staged the 19 prompt-02
source/test/docs files and ran
`git commit -m '02: certify completed DEM boundary models and artifacts'`
and `git push origin surface-prep-fixed`. Commit **451e1f0** is pushed.
This phase preserves Hex/source pins, all existing configs/notebooks/data
and .gitignore. Prompt 03 is kept as a local implementation diff.

TemporalGapDecoder reuses the supplied two-solve core, with additive result
diagnostics and full-witness prewarming, and its static multigraph engine
for independent known-zero Z-prefix inference. New model/evaluator modules
stay separate from legacy builders/decoders/simulation tables. No optimizer
or circuit physics is duplicated. New physical fixtures use d3/5 and <=7 shots.

- `bash scripts/python.sh -m pytest -q tests/test_temporal_matching.py tests/test_temporal_dem.py tests/test_preparation_contract.py --disable-warnings > /tmp/knill_prep_03_seed.log 2>&1`
  — **85 passed**, **1.17 s**, after the additive core result/prewarm changes.
- Initial direct Python d3/R2 physical-p0/nominal-.003 smoke, three shots,
  seed 9: both sign/logical predictions and errors zero, finite gaps 9.372,
  three ok/accepted rows; no runner/output construction.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_gap.py --disable-warnings > /tmp/knill_prep_03_adapter.log 2>&1`
  — initial **22 passed**, **72 existing-category warnings**, **8.60 s**.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_gap.py tests/test_preparation_metrics.py tests/test_temporal_matching.py tests/test_preparation_contract.py --disable-warnings > /tmp/knill_prep_03_focused.log 2>&1`
  — **90 passed**, 72 warnings, 7.77 s; after the additional native readout/
  noisy-witness/scope/padding cases, **95 passed**, 88 warnings, 8.89 s.
  There were no failed unit checks in these gates.
- `bash scripts/python.sh -m pytest -q tests/test_temporal_gap.py tests/test_preparation_metrics.py tests/test_temporal_matching.py tests/test_temporal_dem.py tests/test_temporal_model_artifact.py tests/test_preparation_boundary_model.py tests/test_preparation_contract.py tests/test_preparation_circuits.py tests/test_preparation_config.py tests/test_decoding.py --disable-warnings > /tmp/knill_prep_03_focused_final.log 2>&1`
  — **312 passed**, **432 existing-category warnings**, **28.65 s**.
  New gates independently verify fixed zeros/ones, P/F/cost offsets, original-
  column restoration and features, same-solve witnesses, controlled alternate
  equal-cost ties, fixed mode hashes, cached batch/single/packed APIs and
  no DEM parsing/quantization/graph building during decode. Six-row metric
  fixtures verify X/Z/code/logical denominators, error counts/joint bins,
  code-correct conditional readout error, inclusive truth-independent cuts,
  invalid/empty cases and software-frame double-application controls.
  Native d3/5 R1/2/3 tests use <=7 shots: actual nominal/noiseless and noisy
  full-column models, known middle X/Z readout faults, invisible endpoint
  X/Z/Y faults, oracle changes, invalid initial/terminal Z scopes and empty
  R1 X input. Existing legacy decoder and all earlier preparation tests stay.
- `bash scripts/python.sh -m compileall -q src tests` — passes;
  `bash scripts/python.sh -m pip check` — no broken requirements.
- Standalone direct Python timing/smoke wrote only
  `/tmp/knill_prep_03_timings.json`: d3/5, R2, p=.003, seven shots, seed 617,
  compact mode. One call per setting: build 301.592/338.468 ms; decoder setup
  49.031/289.407 ms (model compilation 26.491/159.619 ms); X graphs
  6.955/8.768 ms and Z graph 3.819/12.284 ms. X comparative batch decode
  1.708/2.266 ms, Z prefix .677/1.679 ms, decode total 2.816/4.346 ms;
  evaluator/summary 1.291/.758 ms. Both illustrative batches have seven ok
  statuses, gap 9.372 and X/Z original-column counts 92/199 and 289/743.
  The guide records timer boundaries; these are single-call descriptions,
  not production throughput, calibration, speed/scaling or rare-error claims.
- `bash scripts/python.sh -m pytest -q --disable-warnings > /tmp/knill_prep_03_full_gate.log 2>&1`
  — **883 passed**, **1716 existing-category warnings**, **268.78 s**.
  All 828 previous tests remain, with 55 new adapter/metric cases. This is
  the first successful full gate with source/tests held fixed throughout.
  No failed unit check or dependency source patch was needed for prompt 03.
- Changed/new Markdown links, untracked-source whitespace and
  `git diff --check` pass. Hex, lomatching, surface-sim and external plotting_lib
  checkouts are clean. Hex remains at HEX-K1
  8fa2200315cc4feaccf341a461f91739233de08a. Diff scope confirms existing user
  configs/notebooks/.gitignore, pins/environment files, legacy decoder
  dispatch, config/circuit builders and simulation runner are unchanged.

All Python source and tests were frozen before the full gate; documentation
only was edited while that validation ran. This phase adds no ordered worker,
result storage or CLI simulation integration; the prompt-04 guard remains.
