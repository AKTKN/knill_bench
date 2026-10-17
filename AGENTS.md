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

## Current research environment: Conda knill_system

The user explicitly requested a post-B3 migration to Anaconda/Conda, package
distribution for clusters and deletion of .venv. This supersedes historical
.venv commands above. Use `conda run --no-capture-output -n knill_system python`
or activate knill_system. Python is 3.12.15; numerical pins remain unchanged.
Do not recreate .venv. environments.yaml plus requirements.lock and
requirements-research.lock define the environment; bootstrap verifies the same
fork refs and installs four editable packages. Shell wrappers use python.sh.

Cluster packaging is staging-only: scripts/build_cluster_bundle.py makes four
wheels with source manifests and all Hex matrix resources without changing
dependency repositories. Optional dependency wheels enable offline pip setup;
Conda Python itself is provisioned separately. V1/v2 provenance must support
verified installed wheels without requiring Git, retaining strict Python/
matrix hashes and pinned H5 checks. Do not change circuit/decoder physics.

See [cluster setup](docs/cluster_setup.md) for the tested target and reproduce
commands. Installed artifacts belong under ignored results/cluster_bundle,
not Git. Preserve the existing user .gitignore edit. This environment task
does not authorize production experiments or changes to other Conda envs.

Migration gate after removing .venv: 207 passed, 608 inherited warnings,
147.48 s. Offline installed-wheel smoke also passed v1/v2 experiments, saved
analysis and resume with Git absent. TEST.md records the missing-sinter-wheel
build correction and resource audit. All fork source checkouts remain clean.

## User-requested v2 round multiples and Fig.4(d) label

The user explicitly authorized preparation-depth multiples in both v2
experiments, superseding the literal-d/integer-only and mandatory r_0=r_plus=d
constraints above. Accept fixed positive coefficients times d, including
"2*d", "2/3*d" and decimal coefficients, with exact rational flooring.
Require a positive signed-int64 result at every distance before creating a run;
reject arbitrary expressions and zero denominators. Only d/p are sweep axes.
Standard Fig.4(d) paper config stays at d rounds; variants must pass actual
resolved r_0/r_plus to Hex and retain accurate metadata/identities. T=8,
False priors, no theta and noisy final readout remain required for full Knill.
The plot's vertical label is exactly "logical error rate"; saved summary keys
and per-shot schemas remain unchanged. Preserve incoming edits to both
configs/*_v2_example.yaml as well as .gitignore. Use small isolated fixtures,
never these user-edited experiment budgets, for validation.

Current full gate: `bash scripts/python.sh -m pytest -q` — 242 passed,
620 existing-category warnings, 136.34 s. TEST.md records the corrected
config-name loop-variable collision and the final validation.

## User-requested v2 directory names and command clarification

New v2 run names use YYYYMMDDHHMMSS_<config_hash8>_<name> in Asia/Tokyo time,
superseding the historical UTC/microsecond directory format. The short hash
is the first eight hex digits of config.config_hash; metadata retains the full
hash and actual ISO UTC timestamps. Exclusive mkdir collisions advance the
directory timestamp one second, never reuse a previous run. Existing directory
names still load/resume; do not rename existing outputs. `run CONFIG` always
starts fresh. `analyze-factory RUN --settings ANALYSIS_YAML` reads RUN's saved
simulation config/data only and does not simulate or automatically resume.

Latest full gate: 243 passed, 620 inherited warnings, 169.15 s. Legacy-path,
collision/midnight rollover and fresh pending-state checks pass; see TEST.md.

## User-requested factory wall-time diagnosis

The user explicitly requested measured wall times and bottleneck identification
for the edited factory example. Read existing run/process status without
interrupting user jobs. Isolated selected-point diagnostic runs (including d7)
are authorized for this investigation; do not launch the full production sweep.
Keep Hex and other dependency source read-only. scripts/profile_factory.py
instruments real worker/native boundaries in its own process, with temporary
physical files and bounded wall time. Runtime patches are diagnostics only.
Do not change decoder policies in the user's config or apply an optimization
to the pinned fork as part of a report-only request. Keep raw timing artifacts
under ignored results/ and document measurements/limits in the repo report.

The measured root cause is projected merge_independent_events growing-ID
validation, with repeated bundle signed-flow validation secondary. See
docs/factory_performance_report.md. Latest full gate: 245 passed, 620 inherited
warnings, 163.25 s; explicit bounded-profile timeouts are not failed unit tests.

## User-requested module-local factory DEM revision

The user authorized replacing factory True inference with module-local Stim
DEMs, cache/redundancy optimization and measured wall-time comparison. This
supersedes the historical full-prefix projected-prior/report-only constraints.
Hex H5 remains read-only. Bench adapters.hex_factory uses native physical
modules and inherits native causal frame/decode methods; v1 and B1 stay unchanged.
The DEM-only input has all +1 CSS stabilizers, a Pauli logical input boundary,
native coupling/readout noise and a logical measurement output boundary.
Preparation/earlier-stage residuals are EXCLUDED FROM THE PRIOR, not removed
from physical simulation. No added boundary noise, ideal physical reset or
oracle information is permitted. Strict Stim/Hex structural checks remain.

Cache local DEM/gap models by complete canonical body/code, bounded per worker;
never cache/reuse sampler RNG state across points. Full native physical bundle
validation still runs once on each fresh True factory before the private H5
initialization binding. Save explicit new model/scope/hash identifiers. Analyze
old saved models under their original labels; refuse mixed-policy resume.
Use Conda, <=7-shot d3/5 unit fixtures, and isolated selected-point wall-time
profiles (d7 authorized). No production sweep. Preserve incoming user config
and .gitignore edits and append STATUS/TEST results. See factory guide/report.

Latest gates for this revision: 255 bench tests passed (688 warnings, 164.62 s),
128 read-only Hex tests passed (320 warnings, 55.76 s). Selected-point True
profiles complete at d3/5/7; legacy projection/merge calls are zero, local DEM
cache miss=1/hit=3 across two T=2 attempts. See TEST.md and the performance
report for exact commands, timings, and unchanged user/dependency scope.

## User-requested factory validation option and packed frames

The user authorized skip_circuit_validation and preparation-frame arithmetic
optimization. Their clarification specifies True=skip, False/default=validate.
This supersedes the mandatory full validation for fresh True factories above
only when explicitly opted out. Both factory prior modes now use bench's
packed final-check/exit-frame computation with all four original matching
decisions retained. V1/B1 and Hex H5 source remain unchanged. Full checks run
once by default; runtime sign/model/gap checks remain in skip mode. This is
not a persisted validated-circuit cache. Private H5 builder/decoder bindings
must be re-audited on upgrades. See docs/factory_frame_optimization.md and
the updated factory guide. Keep unit fixtures <=7 shots at d3/5; selected d7
timing comparisons remain separate opt-in diagnostics under ignored results.

Latest gates: 272 bench tests passed (744 warnings, 168.27 s) and 128 existing
Hex tests passed read-only (320 warnings, 55.43 s). See TEST.md for commands
and corrected test assumptions; docs/factory_frame_optimization.md reports
exact-output comparison and measured setup/frame speed changes at d7/T3.

## User-requested adaptive v2 execution and PBS launch

The user explicitly authorized committing all incoming work (including the
previously protected config/.gitignore edits) as a clean checkpoint before
this revision. Checkpoint 4e1d684 was pushed to auxiliary-system. Subsequent
changes implement time-adaptive v2 chunks, buffer_shot output and the supplied
scripts/cluster_run_simualtion.sh PBS wrapper; this supersedes historical
whole-point-only, fixed-batch and worker-owned-writer requirements in auto mode.
Both v2 experiments default to auto; integer batch_size retains legacy exact
fixed-partition execution. Hex H5 and v1 physics/execution remain unchanged.

Auto workers cache physical models/decoders and use independent chunk-seeded
samplers. Parent owns one ordered buffered writer per table plus metadata;
outstanding and reordered chunks together are bounded by workers. Timing-
dependent partitions can change actual records across runs/priors/workers;
use fixed mode for paired-record comparisons and bitwise replay. buffer_shot
sets result row groups, not checkpoints; unfinished points restart at zero.
Old omitted-batch saved runs retain implicit 32 when loading saved data.
CLI --workers saves effective YAML plus original-input SHA256, without editing
source configs. PBS stays single-node and uses allocated CPUs with BLAS=1.
See docs/parallel_execution.md and docs/cluster_setup.md. New physical tests
stay d3 and <=7 shots. Production sweeps/real cluster submission remain outside
this implementation request.

Latest adaptive revision gates: 312 bench tests passed (772 warnings,
173.96 s); 128 read-only Hex tests passed (320 warnings, 50.71 s). PBS shell
unit/syntax checks, pip check and the real local Conda wrapper's three-shot
run/resume/analysis pass. See TEST.md for exact commands and corrected checks.

## User-requested ordinary memory and complementary gap

The user authorized a v2 ordinary syndrome-extraction |0> memory adapter,
runner and output, using the actual Hex implementation, with optional
get_logicalgap. kind=se_memory uses noisy physical-zero initialization,
exactly rounds (default d) X/Z SE rounds and noisy final Z, with no Knill
resources/teleportations/ideal oracle. Hex H5 and v1/B1/B2 physics stay read-only.
rounds is a fixed integer/d/multiple rule; only d/p sweep. Knill-only options
are rejected, and memory-specific fields do not change old canonical hashes.

Full-circuit complete independent DEM events and their observable matrix feed
cached MWPM. get_logicalgap adds a constrained opposite-class decode using a
validated two-boundary spacetime lift, preserving the first prediction. This
is a min-weight cost difference in log_weight units, not posterior log odds.
No truth enters inference/scoring. Unsupported graph/logical/weight structure
raises; get_logicalgap requires 0<p<0.5, while plain memory supports p0.
No spatial-planarity check in Hex is bypassed: bench's new graph construction
has its own algebra/constraint validation and works on spacetime graphs.

Output shares v2 error schema and optional aligned gap_t001 for the whole
memory experiment. Required filename keys are retained with T=1 (one score),
r_0=r_+=0 (no Knill resources), plus resolved rounds; physical identity excludes
these compatibility keys and the gap flag. Metadata explicitly records zero
teleportations and noisy boundaries. Both adaptive/fixed execution, bounded
buffers, paired publication and whole-point resume are shared. Keep new
physical fixtures d3/5 and <=7 shots; no production sweep is authorized.
See docs/se_memory.md and TEST.md for math, tests and usage.

Latest memory revision gates: 369 bench tests passed (928 warnings,
183.80 s), and 128 read-only Hex tests passed (320 warnings, 51.62 s).
Three-shot direct/PBS-wrapper run and completed resume, shell syntax and
pip check pass. TEST.md records the corrected native-method monkeypatch
assumption, exact commands and unchanged user/dependency scope.




## BENCH-N1 / BENCH-N2 factory custom physical noise

The user authorized these two scoped commits/pushes on auxiliary-system after
Hex HEX-N1/N2. This supersedes the historical H5 pin for this integration:
require HEX-N2 86c9495094801012b9912bd41935ae48b08d8f92; all dependency sources
remain read-only. N1 supplies strict factory-only YAML parsing, frozen native
noise parameters, identities, validation and pin/API audit. N2 supplies actual
native factory execution, local-DEM noise scope, metadata and small physical
checks. Never duplicate Hex physical circuit construction. Only d/p sweep;
reject custom noise for Fig.4(d)/SE memory before output with the specified
explicit error. Preserve all uniform hashes/seeds and v1 explicit profiles.

Read docs/factory_custom_noise.md. Multipliers/durations are fixed finite
nonnegative numerics, never arbitrary expressions. Validate operation and
resolved idle probabilities at every swept point before creating a run.
Physical identities include full parameters; theta/prior/workers/shots remain
nonphysical. Include post-CNOT control idle inside local body; exclude earlier
storage/preparation residuals only from the local prior, never simulation.
Do not invent a generic hardware schedule, extra idle channel or retry path.
Use Conda and d3/5 <=7-shot physical fixtures; retain paired bounded output,
strict metadata/resume and worker-local native caching. Update STATUS/TEST and
all affected guides each stage; stop after N2 commit/push. No production sweep.




BENCH-N2 now implements native noise forwarding and both-prior/fixed/adaptive
execution. The local body includes post-control idle and excludes pre-coupling
storage; a control fault may be invisible to that stage's target gap. Custom
LRU keys include the full native parameter hash, even for excluded sources.
Parent publication/resume/saved analysis cross-check custom noise/probability/
hash/scope metadata. External mismatched resume docs fail before cleanup.
Uniform hashes, seeds, caches, model labels and v1 physics remain unchanged.


BENCH-N2 final gates: `bash scripts/python.sh -m pytest -q` — 443 passed,
1112 existing-category warnings, 214.21 s. Read-only Hex factory/noise/frame/
gap gate: 199 passed, 348 warnings, 36.91 s. Three-shot custom True shell/CLI
run/completed-resume/saved-analysis, pip check and compile/link integrity pass.
TEST.md records exact commands and the N1 provenance-message assertion fixes.
Both bench stages are complete after the N2 commit/push; no production runs.

## User-requested simple PBS launcher

The user explicitly requested removing PBS CPU inference and worker overrides.
scripts/cluster_run_simualtion.sh now activates Conda and calls run CONFIG or
resume RUN directly. Workers come from input/saved YAML. PBS_NCPUS,
PBS_NODEFILE and WORKERS are not read; mpiprocs is not required by the wrapper.
Keep select=1 and choose YAML workers to match the requested CPU allocation.
This supersedes the historical PBS allocation/node guards and automatic
--workers behavior above. BLAS/OpenMP threads remain one. Direct CLI --workers
is still available explicitly; scheduler/physics/resume contracts are unchanged.

Latest gate: `bash scripts/python.sh -m pytest -q` — 443 passed, 1112 existing-
category warnings, 221.51 s. Eight shell-interface cases and an actual local
three-shot run/completed-resume verify exact YAML and worker preservation with
a one-entry nodefile. No production sweep or real cluster submission ran.
