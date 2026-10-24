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

## User-requested saved-data notebook figures

The user authorized a schema-v2 lazy keyed dataset reader, six notebook figure
APIs and a shared plotting_lib APS style (300 dpi). See
[notebook plotting](docs/notebook_plotting.md) and notebooks/saved_figures.ipynb.
RunRegistry registration must not access files. Figure calls validate selected
published points and stream saved data only, without simulation/resume. A run
may still be running; selected unfinished points warn and are excluded.
Notebook cuts reject gap<=threshold, accepting strictly >; historical B3's
>= rule remains unchanged. Lifetime counts passed stages 0..T, factory only.
LER reduction is 1-selected/raw, undefined with zero baseline or no acceptance.
Factory labels retain their terminal evaluation-oracle meaning.

plotting_lib 0.1.0 is installed editable from the user's external/plotting_lib
checkout in knill_system. It is optional for notebooks, not a new simulation
runtime/cluster-wheel dependency. Preserve that checkout, existing data,
.gitignore edits and notebooks/basics.ipynb. No production sampling is
requested. Synthetic new tests use six rows; real-data checks are read-only.
Full gate: 465 passed, 1112 inherited-category warnings, 146.41 s. See TEST.md.

## User-requested reference typography, LaTeX and rounded gap analysis

The notebook style now uses plotting_lib APS as its base with 6x3.6 inch
figures, 14pt axis labels, 13pt ticks, 12pt legends and 300 dpi. FigureStyle
supports centralized label overrides, MathText mathrm/mathsf and optional
actual LaTeX with an explicit minimal preamble. Keep external plotting_lib
read-only. NotebookPlots round_digit defaults to None; integer values apply
Decimal ROUND_HALF_UP to all stage gaps before every statistic/cut and both
lifetime passes. Per-figure overrides include explicit None. Raw validation
must precede rounding; explicit thresholds and saved tables remain unchanged.
Optional gap-frequency return_unique adds per-group/per-stage sorted lists.
See docs/notebook_plotting.md. Full gate: 474 passed, 1112 inherited warnings,
147.57 s. Real saved-data notebook and actual LaTeX PNG/PDF smokes pass.

## User-requested lifetime fractions and capped mean

plot_lifetime now shows all-shot 100% stacked lifetime fractions (color=L,
group=hatch) and default dashed mean lifetime curves on an independently
scaled right axis. This supersedes the earlier notebook boxplot. All means
are empirical over 0..T, with T for full survivors; no unobserved long-time
lifetime is inferred. show_mean=False hides the second axis; return_summary=True
adds grouped thresholds/T/shots/counts/fractions/mean_lifetime. Strict cuts,
round_digit, bounded histograms and saved-data-only behavior are unchanged.
See docs/notebook_plotting.md. Keep user-chosen notebook thresholds intact.
Full gate: 478 passed, 1112 inherited warnings, 239.53 s. Real-data exports and
all notebook cells pass; only lifetime-related source outputs were refreshed.

## User-requested postselected-LER x tick spacing

The postselected-LER p axis now uses about five regular 1/2/5 intervals,
concise ScalarFormatter labels without additive offsets, and major-label
padding. Shared 13pt ticks and existing curves/cuts remain unchanged. The
notebook's user-selected settings/thresholds are preserved. Full gate:
478 passed, 1112 inherited warnings, 99.35 s. Actual PNG/PDF and notebook-cell
renders pass, with renderer-confirmed non-overlapping x labels.

## User-requested pointwise Wilson shades

WilsonInterval in analysis/confidence.py is the shared scalar/broadcast score
interval class, default confidence=.95. Five non-lifetime notebook figure types
now shade their intervals by default; the stacked lifetime figure, including
its mean, stays unshaded. Preserve point estimates, raw counts, strict cuts,
rounding, seeds and simulation/legacy CLI behavior. Conditional intervals use
accepted denominators; frequency count bounds are N times category-probability
bounds; per-round normalization transforms both endpoints. Undefined cases
stay NaN. Reduction is not binomial: use a=P(accept), b=P(accept|error), paired
ratio=b/a and a two-component Bonferroni Wilson envelope (97.5% each at the
default). State this is Wilson-derived/nominal, without independent-sample,
exact finite-sample or simultaneous/data-selected-cut coverage claims.
FigureStyle.shade_alpha defaults .18. See docs/notebook_plotting.md for the
formula and primary references. Full gate: 501 passed, 1112 inherited warnings,
109.71 s. Preserve user notebook parameters and unrelated/lifetime outputs.

## User-authorized general Knill EC and physical noise (2026-10-22)

The user authorized editing both Hex/bench, small tests/smokes, documentation
and commit/push on both auxiliary-system branches. This supersedes prior
read-only-Hex, T=8-only and mandatory-noisy-final rules for this scoped revision.
Read [plan/contract](docs/knill_ec_noise_plan.md). knill_ec_memory is canonical;
legacy fig4d_reproduction preserves its hashes and T=8/uniform contract.
Special noise models have ideal final readout and False inference option.
Preserve unrelated incoming notebook, plotting source and .gitignore changes;
no production sweep or other Hex worktree edits are authorized.

Latest scoped gate: 532 bench tests passed (1208 warnings, 151.11 s);
372 Hex tests passed (3 historical exclusions, 708 warnings, 68.49 s).
Hex is pinned to HEX-K1 8fa2200315cc4feaccf341a461f91739233de08a; native
sources are clean after their authorized commit. See TEST.md for the initial
dirty-fork integration failure, corrected tests and tiny fixed/auto smokes.

## User-authorized general Knill simulator and selectable priors

The user removed the general Knill False-only restriction and explicitly
selected support for both module-local Stim DEM and full-prefix projected
priors via codecapacity_prior. kind=knill_sim is general; knill_ec_memory
remains compatible. Local is default and includes current Bell assembly/
teleportation/readout, excluding prep/past residuals only from inference.
Full-prefix retains native Hex H5 causal replay and unsupported-graph errors.
Do not silently fall back between policies or erase physical residuals.
See [Knill simulator](docs/knill_sim.md). Hex/pins/v1 stay read-only; no
production sweep or edits to user notebooks/.gitignore are authorized.

Latest general-Knill gate: 581 passed, 1356 warnings, 182.02 s; targeted
read-only Hex gate: 41 passed, 188 warnings, 26.54 s. Tiny two-worker fixed/
auto runs and completed resume/saved plots pass for both prior modes. See
TEST.md; the supplied 200000-shot/d5..11 grid is parse-only validation.

## Fixed-R surface preparation: prompt 00 (2026-10-24)

The user requested committing/pushing incoming changes first: checkpoint
2e618b9 is on auxiliary-system. The supplied surface_timegap prompt/plan then
requires a child implementation branch and no implementation push. Work is
on surface-prep-fixed; retain this local diff unless later explicitly directed.
This supersedes the historical auxiliary-system-only rule for this task.
Read docs/temporal_preparation_theory.md before later preparation steps.

Prompt 00 adds theory, shared preparation contracts and the reviewed supplied
temporal DEM/matching seed with synthetic tests. The surface_prep_fixed
physical builder/config/CLI/worker/report is not yet implemented. Defaults
are z preparation, X sign gap, Z readout, prefix_frame_only and adaptive=false;
R is an explicit positive integer, not cycles/d/round-multiple syntax. Output
truth is after the final Z extraction. Both X/Z sign inference and deterministic
logical-Z labels are required; decoder inputs exclude evaluator truth.

BoundaryConstraintModel aliases TemporalDemModel; keep one H/P/F/S/B/column
authority. Preserve original completed term identities, all spatial open
columns including zero-online columns, p0 exclusions and common integer costs.
Unsupported proof/noise/graph conditions fail explicitly. Kernel graph tests
are not physical calibration at the current pin. Later integration reuses
the ordered chunk infrastructure in simulation/worker.py and runner.py via
new-protocol delegations, preserving every existing protocol/API/schema.
Hex remains clean/read-only at HEX-K1, all pins unchanged; use Conda and only
tiny d3/5 physical fixtures when their circuit step is implemented. Do not
run the supplied older-pin scripts' large sampling budgets or production runs.

Prompt 00 final gate: `bash scripts/python.sh -m pytest -q --disable-warnings`
— 666 passed, 1356 inherited-category warnings, 276.16 s. Focused kernels/
contracts: 85 passed. TEST.md records the initial source-edit-during-test
resume rejection and the clean-source rerun; no resume guard was weakened.

## Fixed-R surface preparation: prompt 01 (2026-10-24)

The user authorized committing/pushing prompt 00 before implementing prompt 01.
Bench e3de069 is pushed on surface-prep-fixed. Hex had no pending changes;
its auxiliary-system push was already up-to-date at HEX-K1. No artificial Hex
commit, pin change or other-worktree edit was made. Prompt 01 work remains a
local diff; further commit/push requires a later request.

Read docs/surface_preparation.md for the implemented circuit/config/truth API.
surface_prep_fixed is a protocol-only schema-v1 extension: fixed literal R,
z/x/z, prefix_frame_only, hex_legacy and fixed_shots. Legacy valid resolved
config/grid/circuit identities stay exact. Both Code/native instrument flows
and the unconditional native gate/noise/probability domain are checked;
undecomposed non-gauge DEM failures raise capability errors. Physical p and
optional nominal decoding_p stay separate; only the latter changes offline
inference circuits. Source/ref/map/model hashes are explicit.

The physical prefix contains exactly R full X/Z rounds and no evaluation.
Production adds ideal output X-MPP/destructive Z and evaluator-only labels;
offline completion adds hidden past X probes after noisy initialization.
Record/detector/observable namespaces are explicit. Only production sampler
arrays may enter split_preparation_samples; its detached observations expose
no raw readout or truth. The current runner rejects this protocol before
output creation; do not route it through legacy memory accounting. Decoder/
metric integration remains prompts 02/03; ordered workers/output remain 04.
Use Conda and <=7-shot d3/5 physical fixtures. No production sweep is authorized.

Prompt 01 full gate: `bash scripts/python.sh -m pytest -q --disable-warnings`
— 762 passed, 1496 existing-category warnings, 187.01 s. Focused circuit/
config/kernel/legacy gate: 216 passed. Installed config CLI, pip check,
compileall and a three-shot R1/zero-online-X boundary smoke pass. See TEST.md
for exact commands, the corrected placeholder assertion and unchanged scope.

## Fixed-R surface preparation: prompt 02 (2026-10-24)

The user authorized committing/pushing prompt 01 as 01, then implementing
surface_timegap/prompts/02_dem_boundary_constraints.md. Checkpoint 3cdc594
is pushed on surface-prep-fixed. Prompt 02 remains a local diff until a later
commit request. Hex and all dependency sources/pins stay read-only; no new
production sampling is authorized. Continue using Conda knill_system.

Read docs/temporal_boundary_model.md for setup/model/artifact interfaces.
TemporalDemModel remains the single boundary-column authority and the
supplied TemporalMatching core is unchanged. Keep full completed supports,
roles, duplicate/evaluation-only/inactive columns, feature order and original
float/common integer weights. p0 is excluded by matching_kwargs; active
rounded-zero costs stay zero without clipping. Every full-degree-one spatial
port is frozen, even future-only. No ordinary-DEM/gate-name boundary guesses,
separator splitting or online-signature inference merging is allowed.

compile_preparation_boundary_model certifies nominal production/completed
same-X online/all-evaluation parity models with exact independent XOR
aggregation (binary64 tolerance recorded), builder maps and source provenance.
The known initial-Z anchor stays separate. Version-1 model artifacts preserve
full column/label order and a canonical payload hash; loading validates
schema/ranges/derived policy and reconstructs sparse arrays without Stim DEM
parsing. The future runner owns artifact persistence/hash/publication; its
pre-output guard remains until prompt 04. High-level X/Z adapter/metrics are
prompt 03, not implemented here. Keep full-witness/compact adapter identity
separate from the static model hash when adding that adapter.

New tests use synthetic columns and d3/5 exact DEM fixtures, with three-row
zero-syndrome core decodes and no physical sampling. They independently
check R2 readout/data/two-qubit gate-Pauli responses, invisible labels,
future spatial ports, two-future cancellation, fixed zeros/ones and strict
artifact round-trips. Append all gate results/corrections to TEST.md.

Prompt 02 final source-frozen gate:
`bash scripts/python.sh -m pytest -q --disable-warnings` — 828 passed,
1628 existing-category warnings, 191.44 s. Focused: 247 passed. All 762
previous tests remain, plus 66 model/artifact cases. Three-shot artifact/core
smoke, pip check, compileall and documentation/whitespace/scope checks pass.
TEST.md records the corrected empty-target negative-control fixture.

## Fixed-R surface preparation: prompt 03 (2026-10-24)

The user authorized committing/pushing prompt 02 before implementing
surface_timegap/prompts/03_batch_decoder_and_metrics.md. Checkpoint 451e1f0
is pushed on surface-prep-fixed. Prompt 03 remains a local implementation
diff; stop before prompt 04 worker/storage integration unless requested.
Hex, other dependencies, pins, user configs/notebooks/.gitignore and existing
v1/v2 numerical paths remain unchanged. Use Conda knill_system and <=7-shot
d3/5 physical fixtures; no production sweep is authorized.

Read docs/preparation_decoder.md. TemporalGapDecoder accepts only static X
completed/Z-prefix models and two online bool detector arrays. Setup caches
the supplied TemporalMatching plus the same static multigraph kernel for Z,
whose known initial-zero anchor remains in the physical prefix. No terminal
probe/readout is decoder evidence. Full-witness mode prewarms optional
label graphs; no decode reparses DEMs, quantizes or constructs graphs.
Compact/full mode, tie/frame/source/model/backend identities are hashed.
The core has additive frozen-bit/P/F result fields and graph prewarming;
its objectives, topology, offsets and solver algorithm are not rewritten.

Prefix_frame_only means one software parity comparison, no physical
correction, pure-error LUT or terminal recovery. Unsupported terminal mode
raises. The evaluator alone joins truth with prediction, keeping per-sector,
code-space and logical-Z readout meanings separate. Independent validity
denominators preserve baselines with no complement. High-level acceptance
requires X baseline AND X complement AND Z validity AND gap>=g. NaN gaps are
unavailable; negative/inconsistent available costs/gaps raise. All error
placeholders require masks; code/joint counts require both baselines.
Source/debug witnesses belong to their selected same-solve baseline; never
attach a disagreeing full witness to compact output. Frozen diagnostics
include zeros and ones with original completed-DEM column IDs.

New synthetic tests cover hand-derived costs/masks/joint counts, controlled
alternate valid ties, static caching and explicit little-endian padding.
Native d3/5 R1/2/3 fixtures and single readout/Pauli faults use <=7 shots.
Measured illustrative setup/decode calls are documented, without throughput,
calibration, FT or posterior claims. Append all gate results to STATUS/TEST.

Prompt 03 final source-frozen gate:
`bash scripts/python.sh -m pytest -q --disable-warnings` — 883 passed,
1716 existing-category warnings, 268.78 s. All 828 earlier tests remain,
with 55 new adapter/metric cases. Focused: 312 passed. pip check, compileall,
documentation links/whitespace and unchanged dependency/user/legacy scope
checks pass. No failed unit gate or dependency patch was needed in this phase.

## Fixed-R surface preparation: prompt 04 (2026-10-24)

The user authorized committing/pushing prompt 03 as 03, then implementing
surface_timegap/prompts/04_monte_carlo_parallel.md. Checkpoint 6fa15c5 is
pushed on surface-prep-fixed. Keep prompt 04 as a local diff; do not push it,
start prompt 05 or launch production sweeps without a later request. Hex,
all dependency pins and other worktrees remain unchanged/read-only. Use
Conda knill_system, bounded d3 <=7-shot new physical fixtures and the tiny
installed CLI/shell smoke. The larger d3/5/7/9 YAML is parse-only in tests.

Read docs/preparation_execution.md. This phase delegates setup/sample/model/
evaluation to simulation/preparation.py while reusing the existing ordered
spawn/commit loop, worker CACHE and seed function. No second scheduler,
adaptive partitioning, terminal recovery or new quantum physics is introduced.
Static describe builds no Matching; workers load X/Z artifacts without DEM
parsing, cache graphs per bounded entry, and compile a fresh sampler for each
fixed chunk seed/call shape. Only the production circuit is sampled once per
chunk; every decoder receives the same online batch, never evaluator truth.

New preparation_result_version=1 tables keep sign/code/logical semantics
separate from legacy logical_failure/errors and v2. Invalid flags/costs/gaps
are nullable with independent masks. Aggregate/compact modes share the same
per-check/joint/gap-bin counters. All-shot syndrome retention is rejected;
uniform and first-failure examples are globally bounded under ordered commit.
Same-mode witnesses expand active columns to original DEM order. Canonical
sample hashes include bool dtype, names/shapes, row-padded little-endian bits
and serialization version. No singleton resampling is assumed to replay.

Preparation preflight verifies saved config/grid/environment, complete setup
artifacts and published part checksums/schema/count/seed/sample IDs BEFORE
staging/orphan cleanup. Checkpoints are publication markers, not jointly
atomic table renames. Parent fsyncs data directories before markers; unmarked
partial publications retry from original chunk seed. Missing published
markers and noncontiguous committed groups reject. Failed workers retain
assigned/unobserved history without fabricating scientific shot results.

Saved analyze is count/timing-only and never samples/resumes; calibration,
interval/figure reports remain prompt 05. Keep warmup/replay/setup/I/O out of
primary decode timers and state memory/latency/throughput measurement scopes.
The guide records tiny measured values/limits, not scaling or physics claims.
Retain minimal legacy decoder case dictionaries without a protocol key when
dispatching; use guarded lookups and support empty legacy protocol lists.

Prompt 04 final source-frozen gate:
`bash scripts/python.sh -m pytest -q --disable-warnings` — 902 passed,
1788 existing-category warnings, 234.42 s. All 883 earlier tests remain;
19 execution/artifact/recovery cases were added. The initial fixture tuple
mutation and legacy minimal-case guard regressions/fixes are recorded in
TEST.md. Tiny installed shell/CLI run/resume/analyze, pip check, compileall,
guide/whitespace and dependency/user/physics scope checks pass. No production
sweep or dependency source patch was run.
