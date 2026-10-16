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
