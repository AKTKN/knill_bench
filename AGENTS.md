# Agent guide: auxiliary-system bench development

## Repository and phase boundary

This bench work is based on main b3cc72a7c643c326ea83bf7ece892e19bc7dc7ee.
All phase commits/pushes go to `auxiliary-system`, never main. B0 was explicitly
requested after Hex H0-H5. Stop after B0's scoped commit/push; do not start B1,
B2 or B3 without a later user request. There is no v2 science runner in B0.

Read README.md, docs/design.md, docs/data_schema.md and
[the B0 guide](docs/auxiliary_v2.md) before extending this branch. Package
DOCS.md files describe actual interfaces and tested limits; update every
relevant guide with source changes. Initial documentation covers all eight
Python package directories, tests and scripts. Append STATUS/TEST history.

## Git and dependency safety

- Preserve user changes. The incoming .gitignore edit adds AFT/implementation;
  do not stage, overwrite or stash it as part of this work. Incoming root
  AGENTS/STATUS files were empty; B0 supplies their initial content.
- Hex is a separate Git worktree/repository at external/Hex. It is clean at H5
  4278d2900626f1d120d611f209340b20a9370f91 on its own auxiliary-system branch.
  B0 pins/imports it read-only and changes no Hex source/version. Do not touch
  the user's other hex-parallel worktree. Other fork revisions remain fixed.
- Never force push/reset dependency checkouts. Bootstrap checks exact refs.
  Only intended bench code/tests/docs/configs and the dependency pin are staged.
  No experiment outputs, lock files, virtualenvs or caches are committed.

## V1/v2 contracts

- Preserve the original schema-v1 config/CLI/builders/decoders/simulation/
  analysis/storage APIs and tests. New modules are experiments/* and
  data/storage_v2.py, with separate knill-bench-v2 entry point.
- V2 has exactly d/p sweeps. Fixed settings and only literal d/positive-integer
  round rules are accepted. Reject unknown/duplicate keys, forbidden sweeps,
  arbitrary expressions and unsafe YAML tags. Fig.4(d) prior flag is False.
- Run directories are unique UTC timestamp plus safe name. Save exact YAML
  bytes and one compact metadata JSON. Actual imported bench/Hex Git refs,
  dirty flags, Python/matrix-resource hashes, versions, seeds and point counts/
  times are recorded, with no mandatory logs/archives/diagnostic tables.
- Each point has one error Parquet table, factory also one aligned gap table.
  Keep every required filename key including literal r_+. IDs are uint64,
  labels bool, gaps nullable float64. Stream bounded batches with one writer
  per table. No all-shot materialization or per-shot constructors.
- Both tables must close/fsync/validate before public renames; metadata's
  complete point marker is the pair-publication boundary. Two renames are not
  jointly atomic. Resume discards every unfinished point's pair/temp files and
  restarts at zero with the same point seed. Preserve completed data.
- Only the owning parent updates metadata, synchronously. Workers own their
  point writers and later will cache samplers/maps/graphs per point/worker.
  Derive stable point/chunk seeds independently of scheduling, prior/theta,
  workers and shot count. No B0 process pool or sampling is implemented.
- Full Knill's final readout stays noisy. Factory's sole terminal ideal oracle
  is evaluation-only. Never use truth to decode, score confidence or select
  trajectories. H5 projected priors have measured context/nonlinear limits;
  unsupported graphs must raise, with no lossy fallback or FT/MAP/gain claims.

## Validation

Use the isolated editable/bootstrap .venv and exact runtime lock. Required
full bench gate: `.venv/bin/python -m pytest -q`; B0 passed 139 tests (65 v1,
74 v2), with existing warnings. B0 adds only synthetic <=7-row storage cases
and read-only Hex export checks; inherited v1 256-shot fixtures are retained.
No new large Monte Carlo or benchmark is permitted in unit tests. Record all
failures/fixes and exact commands in TEST.md. Initial setup issues were resolved
inside .venv without dependency source patches; pip check passes.

## B1 handoff (supersedes the historical B0 stop above)

The user explicitly authorized B1 after B0. B1 adds the independent eight-cycle
Fig.4(d) runner and saved-data Agresti-Coull plot; stop here until B2 is requested.
Commit/push this phase only to bench auxiliary-system. Hex H5 stays read-only,
v1 numerical sources stay unchanged, and the user's .gitignore stays unstaged.

Read [the B1 guide](docs/fig4d.md) before changing the adapter/runner. Production
YAML has d=9/11/15/21, T=8 and an explicitly approximate p grid .004–.010.
Both Bell resources require d noisy SE rounds, ideal encoded initial data,
uniform Hex noise, MWPM and original Hamming online weights, noisy final Z.
Do not substitute the v1 d-2 builder or factory ideal oracle. The adapter uses
actual Hex callbacks and cached local Pauli transitions; do not introduce a
different protocol or mutate the dependency to gain per-shot labels.

Run small physical fixtures only (new batches <=128 shots, d=3/5); T=1 is a
separate adapter fixture, while scientific runner execution requires T=8.
Production configs are parsed in tests without constructing large circuits.
Cache native objects per point/worker, stream one B0 file, use the point seed
once with a continuing sampler/fixed batch partition. Parent alone publishes
counts and compact execution metadata. Resume restarts unfinished points;
analysis must validate saved IDs/counts and never simulate. No production
sweep or statistical paper-agreement claim is part of this phase.

B1 full gate: `.venv/bin/python -m pytest -q` — 161 passed, 488 inherited
warnings, 119.95 s. TEST.md records the corrected missing-file check, focused
results, installed CLI/shell smoke and unchanged v1/dependency/user-file scope.

## B2 handoff (supersedes the historical B1 stop above)

The user explicitly authorized B2. Implement/commit/push only this phase to
bench auxiliary-system; stop before B3. Read [the factory guide](docs/logical_zero_factory.md).
Use Hex's actual FactoryCircuitBuilder/CompiledFactory and gap interfaces,
with exactly two reused supports, CNOT(fresh plus -> memory), noisy consumed
Z readout and one noiseless terminal evaluation oracle. No new quantum physics
implementation or dependency edit belongs in bench. V1 and the B1 physical
adapter stay unchanged; B1/B2 share the bounded whole-point scheduler.

Build/cache one factory per case/worker, sample fixed full T trajectories in
chunks, decode offline and stream both B0 point files with identical IDs.
Theta never enters compilation, worker arguments, sampling or trajectory
selection. Hamming/projected policies use the same physical circuit/seed;
prior mode changes inference only. Save actual T/depths/units/oracle and
compact model hashes. Reject missing/nonfinite/negative gaps instead of
silently producing null. False at p0 uses finite unit-Hamming scores; True
must pass Hex's structural checks, and p0 True raises without fallback.

New physical tests use d3/5 and <=7-shot fixtures at T=1/2/3, not production
sweeps. Retain all existing tests. Validate paired joins/counts, two-support
reuse, oracle/future isolation, native caching, theta/prior seed independence,
serial/spawn equality and failed-chunk restart. Delegate stronger parity/frame
checks to existing read-only Hex tests; record results in TEST.md. B3 cuts,
first-rejection/retry costs and performance/threshold claims remain out of scope.

B2 final gates: 182 bench tests passed (592 inherited warnings, 138.24 s) and
112 existing Hex circuit/batch/gap tests passed read-only. TEST.md records
commands, coverage, tiny installed CLI/shell smoke and unchanged file scope.

## B3 handoff (supersedes the historical B2 stop above)

The user explicitly authorized B3 and a getting-started document/configuration
templates. All four bench phases are implemented after this scoped commit/push
on auxiliary-system. Do not launch production sweeps without a separate request.
See [getting started](GETTING_STARTED.md) and [B3 equations](docs/factory_analysis.md).

B3 is pure saved-data analysis: validate paired schemas/IDs/counts and finite
scores, select using AND of gap>=theta only, then score terminal factory-oracle
labels. Never call that conditional label online data-Knill LER. Negative
infinity is no cut; zero accepted shots means undefined/null conditional LER.
Pointwise 95% Agresti-Coull intervals are descriptive per fixed cut, with no
simultaneous/data-selected-threshold coverage claim.

Keep cost accounting separate from circuits. Declare serial/parallel initial
prep, per-refresh prep/reset/decode, teleport/readout/online-decode and rejection
cleanup assumptions. Default SE-equivalent costs are assumed, not measured.
One T-stage trajectory produces one final resource. E[attempt cost]/P(accept)
and its paired delta SE require explicit iid fresh restarts; zero acceptance
leaves ratios null. No dynamic retry, alternate timing/noise, queue or multi-
factory schedule is simulated. Simulation table schemas/runners are unchanged.

Use separate analysis YAML (analysis_version:1), never new simulation sweep
axes. Optional JSON/CSV/Markdown reports are requested outputs; no extra
mandatory simulation artifact. User templates in configs/templates are small
runnable examples for both experiments plus analysis settings. Keep the guide,
CLI/examples and strict parser consistent. Preserve user .gitignore/dependency
sources and existing v1 APIs/tests. Full bench gate: 203 passed, 608 warnings,
137.58 s; targeted read-only Hex gate: 128 passed, 320 warnings, 49.97 s.
TEST.md records the corrected float-test assertion and exact commands.
