# Status

## B0 auxiliary-system configuration, metadata and storage

Date: 2026-10-16. Authorized scope: B0 only, after completed Hex H5, no B1/B2/B3.
Started from clean tracked main b3cc72a except the existing user .gitignore
edit and empty untracked AGENTS/STATUS files. Created bench auxiliary-system
from that exact lineage; main is preserved. Hex remains separately clean at
4278d2900626f1d120d611f209340b20a9370f91, with its source/version untouched.

Implemented independent schema-v2 modules: strict config/document/point
contracts and d/p grid, safe YAML parsing and defaults, complete literal-plus
filenames, deterministic point/chunk seed helpers, actual H5 export/lineage
validation, compact imported-source/resource/environment provenance, parent-
owned RunStore and streamed PointWriter/PointResult. A separate CLI supports
validate-config/prepare and kind dispatch. Unavailable scientific runners raise
before creating outputs. V1 source and public behavior are unchanged; the
Hex pin in pyproject/bootstrap advances to H5 and console entry point is added.
Other dependency refs and requirements.lock stay fixed.

Every run has unique UTC timestamp/name directory, exact config.yaml and one
metadata.json with state/times/counts/seeds/config/input/source hashes, versions,
prior/readout conventions. One public logical_error file per point and one
factory logical_gaps file use aligned contiguous uint64 shot IDs. Writers retain
one batch, close/check both tables before renames, and publish via the parent's
metadata marker. Normal failures abort paired output; resume removes unfinished
pairs/temp files, retains completed points and restarts point sampling identity
at shot zero. Local owner guards reject duplicate/live/foreign ownership.

Added small v2 examples and initial DOCS.md in every Python package, tests and
scripts. Updated README/design/schema/dependency/validation docs; the detailed
contract and current limitations are in docs/auxiliary_v2.md.

Validation: full bench suite **139 passed**, **432 warnings**, **115.21 s**;
65 original v1 tests plus 74 v2 cases. New tests use synthetic <=7-row batches,
not physical Monte Carlo. They cover both YAML examples, invalid sweeps/rules/
keys/types/tags, float filename identity, r_+ quoting, deterministic seeds,
unavailable dispatch, typed schemas/ID alignment, native writer count,
close-before-rename, append/rename/metadata failure, clean restart, collisions,
provenance and parent ownership. Existing v1 science/run/analysis tests all pass.
Pip check reports no broken requirements in the isolated exact-lock .venv.

Initial shared-environment setup exposed old setuptools/packaging, missing
galois and LOM's NumPy-1.x incompatibility. Installed the existing runtime lock
in isolated .venv and editable forks; no source shim or dependency edit was
needed. The first v2 subset had 1 failed / 68 passed due to a NumPy-scalar test
fixture passed to a plain-YAML-number API; the fixture was corrected and
69 passed before further failure-boundary cases brought the final v2 count to
74. Exact commands/results and integrity checks are recorded in TEST.md.

Limits: B0 has no science runners, worker pool, plots, acceptance/cost estimates
or thresholds. Workers/batch controls are recorded contracts for B1/B2. Config
parsing does not certify all Hex distances/prior models. Point/JSON publication
uses local filesystem atomic renames plus metadata markers, not a jointly
atomic two-file transaction or distributed scheduler. Resume requires exact
config/code/resources/runtime versions and restarts whole unfinished points;
it cannot recover wall time lost before a hard crash metadata update. No paper
agreement, physical-prior accuracy, performance improvement or FT claim follows.
The final commit/push result belongs to the B0 handoff.


Final integrity and installed CLI smoke checks passed as detailed in TEST.md:
exact config bytes, real imported H5 provenance, pending-only preparation,
explicit B2 dispatch stop, compilation/shell syntax/links, pip check and scope.
All tracked v1 Python/tests and lock bytes remain unchanged; all three
read-only dependency worktrees are clean. The user .gitignore edit is preserved
and excluded from the 33-file B0 commit.

## B1 — eight-cycle Fig.4(d) implementation (2026-10-16)

The user authorized B1 after B0. Added the dedicated production config and
shell runner, bench-side per-shot Hex full Knill adapter, bounded point-worker
execution/resume, compact execution metadata and optional saved-data plot.
Production settings are d=9/11/15/21, eight stages, d noisy SE rounds on EACH
zero/plus resource, ideal encoded initial data, original Hex uniform noise,
offline/online PyMatching MWPM with create_codecapacity_dem=False and noisy
final Z. The explicit .004–.010 p grid is approximate, not unpublished exact
paper points. The old d-2 protocol is untouched.

Actual Hex physical fragments/callbacks and existing bench cached local Pauli
transitions provide the protocol and frame semantics. A point seeds/compiles
one sampler, then samples/decodes/streams exact bounded chunks including the
last partial batch. Canonical preparation templates share cached native
maps/converters/decoders across stages. A bounded spawn pool handles workers>1;
only the parent publishes metadata. One B0 boolean-error file per point and
actual shot/error counts are saved. No new mandatory data/diagnostic artifacts.

Saved analysis validates complete metadata, exact config, schema, IDs and
label counts, then plots conditional errors/shots with 95% Agresti-Coull
intervals without simulation. All shots are retained and rates cover the full
eight-stage experiment. Resume preserves completed files and restarts whole
unfinished points with original seeds under B0 provenance checks.

Validation: **161 passed, 488 warnings, 119.95 s**, including 65 unchanged v1
tests and 23 B1 cases. Exact d3/T8 circuit equality and manual T2 record/label
equality against legacy Hex passed, as did d3/5 T1 zero-noise checks, exact
counts, deterministic serial/spawn streams, failure/restart, interval fixtures
and saved-file integrity/plots. An added missing-file case initially exposed
a raw FileNotFoundError; saved analysis now raises a clear ValueError and the
full gate passes. TEST.md records both focused runs and the final gate.

Installed CLI/shell temporary smoke also passed: production config parse only,
two tiny d3/T8/3-shot zero-noise cases, prepare/resume, saved plot and B2 stop.
Pip check, compilation, shell syntax, diff whitespace, documentation links and
source/dependency scope checks pass. Hex/other dependencies are clean and
unchanged, all original v1 numerical/test bytes are intact, main is unchanged,
and the user's .gitignore is preserved and excluded from staging.

Limits: production sweep and large-distance memory/runtime were not measured;
statistical agreement with Fig.4(d), thresholds and general fault tolerance
are not established. No factory execution or acceptance/cost analysis is
implemented in B1. See docs/fig4d.md for exact APIs, conventions and commands.
This phase ends with the single scoped B1 commit/push on auxiliary-system;
the final handoff reports its actual SHA and push result. Do not start B2.

## B2 — batched logical-zero factory (2026-10-16)

The user authorized B2 after B1. Added configs/logical_zero_factory.yaml,
scripts/run_logical_zero_factory.sh and experiments/logical_zero_factory.py.
The default experiment is T1, d3/5, depths d/d, p=.001/.003/.005 and False
Hamming priors; the existing small example now executes T2. Positive T>1
uses Hex's existing two-support swapping, without any bench physics rewrite.

Each whole-point worker builds the actual Hex bundle/CompiledFactory once,
samples fixed full trajectories in chunks and decodes recorded arrays offline.
The new experiments/execution.py shares B1's bounded spawn scheduler; native
objects stay local and processes are not initialized per chunk. Factory uses
noisy CNOT(plus -> zero)/consumed-block Z readout and a single terminal ideal
evaluation oracle. Terminal truth/future records do not affect earlier gaps.

Both B0 point-level tables stream aligned contiguous uint64 IDs, bool errors
and per-stage float64 gaps, with one writer each. Every shot is saved regardless
of theta; prior/theta/workers do not affect physical seed identity. Metadata
records T/depths, two-block roles/sizes, readout/oracle, units/policy, circuit
and projected model/configuration hashes. False retains finite unit-Hamming
scores at p0; supported True uses Hex's causal projected log-weight gaps.
UnsupportedProjectedModel propagates with no fallback/null-score substitution;
True at p0 fails explicitly. Invalid/missing gaps or unresolved frames fail
paired output. Resume restarts an unfinished pair with the original seed and
preserves complete pairs.

Validation: **182 passed, 592 warnings, 138.24 s** full bench; all v1/B0/B1
regressions plus 20 B2 cases pass. The initial focused gate had **115 passed**.
Existing read-only Hex circuit/batch/surface-gap gate had **112 passed,
204 warnings, 14.50 s**, including signed flows, legacy-map frame equivalence,
fault boundaries and exhaustive d3 sector costs. No B2 test command failed.
New physical fixtures are d3/5 and <=7 shots at T1/2/3; no production sweep.
Pip check, compilation, shell syntax, whitespace, 66 local links and source/
dependency/user-file preservation checks pass. Installed outside-repository
CLI/shell smoke also passed tiny T3 Hamming and T2 projected prepare/resume
runs with exact paired files/units/counts and real H5 provenance.

Limits: no production resource/runtime measurement, calibration, threshold,
fault-tolerance or projected-prior improvement claim. Projected scores retain
Hex's fixed-reference first-order/context restrictions and are not posterior
probabilities; Hamming/log-weight cuts are not interchangeable. No B3
acceptance/first-rejection/retry-cost analysis is implemented. See
docs/logical_zero_factory.md for exact APIs, conventions and commands.

Hex/other dependency sources remain clean/unchanged, main and all v1 numerical
sources/tests remain intact, B0 table schemas are unchanged, and the incoming
user .gitignore is preserved and excluded from staging. This phase ends with
one scoped B2 commit/push to auxiliary-system; final handoff reports actual
SHA/push status. Stop before B3 until explicitly requested.

## B3 — saved acceptance/quality/cost analysis and getting started (2026-10-16)

The user authorized B3 plus a getting-started document and configuration
templates. Added analysis/factory.py and factory_cost.py, analyze-factory CLI,
GETTING_STARTED.md, docs/factory_analysis.md and three runnable commented
templates in configs/templates for factory, Fig.4(d) and separate analysis.
Public APIs, outputs, pinned refs and reproduction commands are documented.

Saved analysis streams/validates unchanged paired tables, complete metadata,
exact config/IDs/counts/units and finite scores. Gap-only AND cuts yield
acceptance/abort, accepted counts, conditional terminal factory-oracle LER,
pointwise 95% Agresti-Coull intervals and descriptive uncertainty. Empty
acceptance gives null conditional values; no shot is selected by true error.
First rejection uses causal gap prefixes. Report formats JSON/CSV/Markdown
are optional; no mandatory simulation storage or resimulation is introduced.

Explicit cost models cover serial/parallel initial preparation, refresh prep,
reset, preparation/online decoding, teleport/readout and rejected-attempt
cleanup. Defaults count assumed SE-equivalent work. One full T attempt yields
one final resource. Cost-to-first-accepted and expected attempts require
explicit iid fresh restarts, use mean attempt cost/P(accept), and retain paired
delta-method uncertainty. Zero observed acceptance leaves ratios undefined.
No dynamic retry, actual alternate timing/noise, multi-factory queue, hardware
latency or production scheduling is simulated.

Validation: **203 bench tests passed, 608 inherited warnings, 137.58 s**,
including all v1/B0/B1/B2 tests and 21 B3 cases. Initial targeted run had one
overly strict float-equality assertion (one rounding bit); corrected it to
numerical tolerance and retained exact discrete checks. Targeted read-only
Hex circuit/batch/gap/public-policy suite: **128 passed, 320 warnings,
49.97 s**. New v2 smoke covers both experiments at d3/5 with three shots per
point. Existing constructor counters confirm cached inference across chunks.
TEST.md records exact commands, coverage and the corrected failed assertion.

Installed outside-repository CLI smoke passed template validation, both tiny
experiments, saved plots, settings/list/grid cuts, optional report formats,
iid/zero-acceptance handling and unchanged simulation bytes. Pip check,
compilation, shell syntax, whitespace and documentation/source scope checks
pass. All dependencies are clean/unchanged; v1 numerical/test bytes, B0 schemas,
B1/B2 scientific runners/scheduler, lock/pins/bootstrap and user .gitignore are
preserved. The B3 commit excludes .gitignore and includes no run artifacts.

Limits: no full Fig.4(d) agreement, production runtime/speedup, optimal-cut
calibration, general fault-tolerance or projected-prior accuracy claim. All
four bench phases are now implemented with the documented assumptions and
tested sizes. One scoped B3 commit/push goes to auxiliary-system; the final
handoff reports its actual SHA and push status. No production jobs are launched.

## Conda research environment and cluster distribution (2026-10-16)

Created the user-requested Anaconda environment **knill_system**, Python
3.12.15/pip 26.2.1, and installed all numerical requirements plus notebook,
analysis, plotting, data/parallel-work and development tools through pip.
Registered its environment-local Jupyter kernel. New environments.yaml,
requirements-research.lock and conda-linux-64.explicit.txt reproduce the
environment; pyproject.toml adds research/dev extras and explicit pinned fork
source records. Existing numerical requirements.lock stays byte-identical.
Bootstrap and all shell launchers now select Conda. The requested .venv
directory was deleted after new-environment and isolated-wheel validation.

Hex's ordinary H5 wheel omitted its matrices. Added a bench-owned staging
builder that creates resource-complete Hex/LOM/surface-sim/bench wheels without
editing dependency repositories, records source SHA/dirty/hash provenance and
checks packaged code/resources. V1/v2 provenance supports these verified wheels
without Git while preserving H5 and resource-integrity checks. No physics,
decoder or data-schema changes were made. Numeric wheel requirements support
offline pip; source provenance remains pinned and validated separately.

The cluster distribution in results/cluster_bundle has **158 wheels (~315 MB)**,
including 72 Hex .mtx resources, a checksum-verifying installer, both pip locks,
Conda definitions, configs and guides. An initial binary-only download could
not find a sinter 1.16.0 wheel; building that wheel on the build machine fixed
the issue without changing versions. The target only consumes wheels.

Validation: all 154 pip lock entries match installed versions; pip check and
bootstrap recreation/update pass. Initial Conda regression gate: 203 passed;
new wheel-provenance cases: 4 passed. Complete post-.venv-deletion gate:
**207 passed, 608 inherited warnings, 147.48 s**. Fully offline installation
into an isolated target passed both small v2 protocols, analysis/resume and a
small v1 run with Git/Conda absent from PATH. Temporary test environments were
removed. Syntax/config/link/whitespace and user-file preservation checks pass.

Updated getting-started/package/script/test guides; docs/cluster_setup.md
provides Japanese local/cluster setup and batch-job commands. This wheel set
targets Linux x86_64/CPython 3.12 (glibc >=2.28); Conda Python is provisioned
separately and other platforms require matching builds. Real cluster resource
performance and production experiments were not run. Dependency source refs
remain unchanged/clean and the user's .gitignore edit is preserved.

## Environment/packaging commit handoff (2026-10-16)

The user explicitly requested commit/push of the current environment and
cluster-packaging changes to auxiliary-system, plus local Fig.4(d)/factory
execution instructions. Pre-commit regression: **207 passed, 608 inherited
warnings, 160.63 s**; pip check and both small example config checks pass.
The source/dependency scope and production-experiment boundary are unchanged.
The existing user .gitignore edit remains outside this commit. The handoff
reports the resulting commit SHA and remote push status.

## V2 round multipliers and Fig.4(d) axis label (2026-10-16)

Implemented the user's requested `logical error rate` vertical label and
positive d-multiple preparation rules for both v2 experiments. Integer/d rules
remain supported; `"2*d"`, `"2/3*d"` and decimal coefficients use exact rational
arithmetic, flooring independently at each distance. Config validation rejects
zero denominators, arbitrary expressions, and resolved depths outside positive
signed int64 before run creation. Physical identities/seeds/filenames continue
to use resolved integer depths, preserving equivalent-rule point seeds.

The full Knill adapter now passes actual r_0/r_plus to Hex for every Bell
resource and records those depths. Its runner and saved reader accept depth
variants; standard paper settings still use d/d, with T=8, False priors, no
theta and noisy final readout. Factory uses its existing native PreparationPlan.
No dependency source, v1 numerical implementation or table schema changes.

Updated schema, getting-started, scientific/package guides and template comments.
Existing edits to both v2 example YAML files and .gitignore are preserved;
no user experiment budget or production sweep was run. Tests include exact
fractional flooring, invalid/zero/overflow rules, equivalent seeds, actual
full-Knill/factory depths and metadata, and saved plotting.

Final regression gate: **242 passed, 620 existing-category warnings, 136.34 s**.
The first full gate exposed a new config-loop variable collision overwriting
the experiment name; it was fixed and name preservation is covered explicitly.
All dependency repositories and both locks remain unchanged; incoming user
files match their initial hashes. TEST.md records focused/failure/final checks.

## V2 directory naming and run/analysis clarification (2026-10-16)

The reported commands both invoke saved-data analyze-factory, not simulation.
Read-only inspection of the referenced run confirms complete status and
resume_count=0. Analysis reads that run's saved config/data and overwrites the
explicit report output; an edited external simulation config only takes effect
after `run CONFIG` creates a new run and the shell run-path variable is updated.
No automatic run deduplication or implicit resume exists.

New v2 directories use YYYYMMDDHHMMSS_<config_hash8>_<name> in Asia/Tokyo time.
The hash is the canonical simulation config SHA256 prefix. Atomic exclusive
directory creation and one-second collision increments preserve fresh-run
behavior, including identical configs in the same second. Metadata retains
actual UTC timestamps/full hashes; existing output directories are not renamed
and legacy names remain loadable under the usual resume checks. CLI help and
getting-started/schema/package guides clarify simulation versus analysis.
No circuit, decoder, physical seed, table schema, dependency source or v1 API
changes belong to this naming update.

Validation: focused config/storage gate **109 passed, 3.86 s**; complete gate
**243 passed, 620 inherited warnings, 169.15 s**. No test failures. CLI help,
local documentation links, diff whitespace and incoming-user-file integrity
checks pass. No production experiment was launched.

## Factory wall-time bottleneck investigation (2026-10-16)

The user requested measured phase wall times for the edited True-prior example.
The latest recorded job was already interrupted: 1373.85 seconds overall,
d3 points ~15.7 seconds, d5 ~303–309 seconds, d7 ~1358 seconds without committed
shots. No user process was stopped or resumed. Added an opt-in, bounded
single-point profile script with nested wall/CPU timers, fault/group counts,
source/BLAS/RSS records, optional cProfile and validation-line tracing. Only
temporary physical files are sampled; timing artifacts live in ignored results/.

Measured the real unchanged worker at p=.003: d3 True/100 shots takes 9.651 s,
including 8.535 s in projected models and 8.021 s in repeated event-ID merging;
physical sampling is .000242 s and decoding .008989 s. d5 True hits its 240 s
limit with 230.594 s in merging before sampling. d7 True was bounded at 60 s
in stage0 setup. The duplicate signature groups cause repeated growing-tuple
sort/set/type validation, approximately quadratic in group size. Hamming-only
comparison points d3/5/7 take .937/3.738/16.539 s, with d7 bundle validation
13.412 s; separate line tracing attributes ~91.4% of validation to repeated
has_all_flows. Thread limiting did not materially improve d3, and 7 versus
100 physical shots leaves total runtime almost unchanged.

docs/factory_performance_report.md records methods, raw artifacts, censoring,
profiling overhead, policy/parallelism limits and suggested fixes. No numerical
or dependency source optimization was applied. Two deterministic timing tests
verify exclusive accounting and patch restoration. Full gate: **245 passed,
620 inherited warnings, 163.25 s**. Both example configs and .gitignore are
preserved; fork checkouts stay clean. No production sweep was launched.

## 2026-10-16: module-local Stim factory prior and timing revision

Implemented the user-requested True policy as module_local_stim_dem in the
bench adapter, with ideal +1 analysis input and Pauli logical boundaries around
native coupling/readout only. Preparation/earlier-stage residual errors are
explicitly excluded from the PRIOR, retained in physical simulation. Actual
Hex frame/decode methods, two supports, noisy readout and oracle isolation are
unchanged; Hex H5 stays read-only. Local DEM/gap caching is bounded per worker,
reuses identical stages/configurations, and never shares sampler RNG state.
Complete native bundle validation runs once per fresh True compilation.
Saved metadata records new scope/hashes; old saved analysis retains its label
and mixed-policy/source resume is rejected.

255 bench tests passed (688 warnings, 164.62 s); 128 read-only Hex tests passed
(320 warnings, 55.76 s). Isolated p=.003, T=2, r0=rplus=d, seven-shot cold
points completed in .875 / 2.507 / 10.830 s at d3/5/7. Legacy d3 replay took
10.480 s; new code calls the old single-fault projection/merge zero times.
Same-process second attempts rebuild no local DEM. Remaining d7 cost is native
validation (7.522 s). Model change and measurement limits are explicit in
docs/factory_performance_report.md; full evidence/commands in TEST.md.
No production sweep, dependency patch, user config edit, staging or push.

## 2026-10-16: fixed-distance runtime versus T

Completed the requested d=7, p=.003, r0=rplus=7, True-prior timing experiment
at T=1/2/4/8: 1,024 shots with batch 128 per attempt, four attempts per T,
separate serial processes, one native/BLAS thread. All 16 attempts completed.
Warm sampling+decode medians are .193/.289/.510/.893 ms/shot; setup/I/O-inclusive
amortized medians are 5.861/10.008/18.475/43.290 ms/shot. T8 bundle validation
is 39.270 s (~89% of point time). DEM is generated once per process, never on
warm repeats; prior hash agrees across T, and legacy projection/merge remain
absent. Repeated output hashes agree within each T.

Added docs/factory_T_scaling_report.md with two graphs, first/warm timing
distinctions, ranges, measured setup costs and reproducibility/interpretation
limits. CSV/JSON, exact YAMLs, scripts and PNG/SVG/PDF figures are ignored
under results/factory_T_scaling_d7. Simulation/dependency sources and user
configs were unchanged for this follow-up; previous test gates retained.

## 2026-10-17: T=3 runtime versus code distance through d11

Completed the later user-authorized diagnostic at d=3/5/7/9/11, T=3,
p=.003, r0=rplus=d and True local priors. Each distance used a separate
serial process with 1,024 shots/batch 128, first attempt plus three warm
repeats. All 20 attempts completed within the explicit per-distance bounds.
Warm processing medians are .130/.213/.396/.757/1.388 ms/shot; full-point
amortized medians are .608/2.968/14.186/48.493/145.194 ms/shot. d11 bundle
validation takes 127.267 s (~86% of the point), versus .384 s for the first
local prior including .00150 s of Stim extraction. The d7 processing range
is unusually wide (.156–.429 ms/shot); it is retained and not causally
attributed to caching or used to fit a complexity exponent.

All distances build one local DEM, with zero warm rebuilds or legacy
projection/merge calls; cache miss=1/hit=11. Repeated paired file hashes
match within each distance. Added docs/factory_distance_scaling_report.md
with graphs, phase tables, preparation-depth/record-size interpretation and
separate startup/steady-processing conclusions. Raw JSON/CSV, exact config,
host details, measurement/plot scripts and PNG/SVG/PDF exports remain ignored
under results/factory_distance_scaling_T3. No simulation/dependency source,
user config, existing run, unit-test budget, staging or push was changed.

## 2026-10-17: factory validation option and packed preparation arithmetic

Implemented skip_circuit_validation with the user's clarified semantics:
True skips full bundle validation, False/default runs it once. The flag is
factory-only, fixed per run, propagated through serial/spawn workers and
recorded in execution metadata. Physical point identity/seeds are independent;
default canonical config hashes remain compatible. No validated-circuit disk
cache is implied. Construction/runtime/model/gap/storage checks remain.

Both factory prior modes now compute only final stabilizer corrections and
exit X/Z frames using precomposed packed GF(2) lookup maps. Removed runtime
whole-history correction, large correction concatenation and CSR/dense-history
conversion. All four native matching decisions, pure-error representatives,
causal stage updates and the prior model are retained. Native public full-history
plans stay available; private optimized plans share maps per support template.
H5's exact physical builder is invoked with a private temporary bundle-type
binding when validation is skipped; returned bundles retain explicit validate().
No Hex source/global monkeypatch or copied physical protocol was introduced.

Full bench gate: 272 passed, 744 existing-category warnings, 168.27 s. d3/5
<=7-shot tests match every native frame/decode field and both validation modes'
circuit/raw data, with serial/spawn and metadata coverage. In an isolated d7,
T=3, p=.003, r=d, 1,024-shot comparison, all decoded fields match exactly.
Median setup falls 14.179799 to 3.212478 s when full validation is skipped.
Packed arithmetic reduces preparation decode/frame .280835 to .222392 s
(20.8%) and whole decode .348699 to .289702 s (16.9%); tables cost 2.615 MiB.
These are batch throughput measurements, not hardware real-time guarantees.
Report: docs/factory_frame_optimization.md; raw diagnostics remain ignored.
User .gitignore/example config edits and the clean pinned Hex checkout are
preserved. No production sweep, existing-run mutation, staging or push.
Read-only Hex gate: 128 passed, 320 inherited warnings, 55.43 s. Exact commands
and the corrected template-sharing test assumption are recorded in TEST.md.

## 2026-10-17: adaptive v2 parallel execution and PBS/Conda launch

User-requested clean checkpoint 4e1d684 committed/pushed all incoming work to
auxiliary-system first. Current v2 defaults now use measured sampling/decode
seconds per shot to adapt chunk sizes toward a configurable target (default
1 s). All workers can share one d/p point; each caches its native model/decoder.
Assigned chunks get stable independent seeds and fresh samplers. Timing-driven
partitions need not produce identical records across runs/policies; explicit
integer batch_size retains the original fixed path for bitwise/paired replay.

buffer_shot independently groups decoded output into bounded, aligned Parquet
row groups with an exact final tail. The parent owns auto-mode writers and
metadata; outstanding/reordered results share a worker-count bound. Existing
paired publication and whole-point restart rules remain. Old omitted-batch
saved configs still analyze with their historical default 32. No physics,
per-shot schema, theta-selection, v1 execution or dependency source changed.

The supplied scripts/cluster_run_simualtion.sh is now a single-node PBS v2
launcher with editable resources, Conda activation, BLAS/OpenMP=1, allocated
worker counts, allocation/node guards and resume support. CLI --workers saves
an effective configuration without modifying source YAML. Clone/bootstrap/
qsub instructions and automatic-chunk limits live in docs/cluster_setup.md
and docs/parallel_execution.md. Example budgets and physical settings remain;
only execution/output settings select the requested new mode.

Validation: **312 bench tests passed (772 warnings, 173.96 s)**;
**128 read-only Hex tests passed (320 warnings, 50.71 s)**. PBS unit tests,
shell syntax, pip check, and actual local Conda/PBS-wrapper run/resume/saved
analysis also pass. The local smoke used d3/T1/3 shots and both allocated
workers. TEST.md records all commands, the invalid overlapping-source baseline
attempt and corrected report-key assertion. No production sweep, real cluster
qsub, dependency edit or other Conda environment change was performed.

## 2026-10-17: ordinary Hex SE memory with optional complementary gap

Implemented v2 kind se_memory through the actual pinned Hex repeated-SE Z
memory circuit: noisy physical-zero reset, exactly rounds (default d) noisy
X/Z SE rounds, noisy final Z. No Knill teleportation/resource preparation or
terminal ideal factory oracle is added. rounds accepts the fixed exact
integer/d/multiple rules; only d/p sweep. get_logicalgap defaults false and
is restricted to this new kind. Existing config/physical identity hashes are
preserved, with golden checks against de21bfc.

The full independent-event circuit DEM supplies H/L and log weights. One
cached MWPM graph determines the first correction and label; optional scoring
uses a second cached observable-preserving two-boundary spacetime lift to
force the opposite logical class. Both H constraints and opposite L parity,
original/native weights and nonnegative cost difference are verified. This is
a min-weight complementary gap, not a posterior sum or exact logical MAP.
Detector-only inference never sees actual logical truth. Unsupported graph/
logical/weight structures raise. p0 plain decoding works; complementary
log-weight scoring requires 0<p<0.5 with positive representable model weights.
No lossy fallback or native spatial-planarity bypass is used.

The shared fixed/adaptive execution and buffers write the existing error
schema and optional joined logical_gaps with one whole-memory gap_t001 per
shot. Required filename keys remain (T=1 score, r_0=r_+=0 no resources), with
resolved rounds added. Metadata explicitly records zero teleportations,
actual noisy boundaries/rounds, hashes and policies. Pair publication, full-
point restart, strict resume checks and parent ownership are unchanged.

User-facing template/example, run_se_memory.sh and docs/se_memory.md provide
local/PBS usage. Existing cluster launcher accepts memory YAML through
CONFIG_FILE without changes or new dependencies. Hex/v1/B1/factory physics,
protected user configs/.gitignore and all fork sources remain untouched.

Validation: **369 bench tests passed (928 warnings, 183.80 s)**, including
57 new memory cases; **128 read-only Hex tests passed (320 warnings, 51.62 s)**.
Independent exhaustive/MILP class-cost checks, truth isolation, first-decode
preservation, optional schemas, serial/spawn, buffering, invalid gaps and
failure/restart pass. Real local three-shot direct/PBS wrappers and completed
resume, shell syntax and pip check pass. TEST.md records exact commands and
the corrected invalid monkeypatch test. No production sweep, performance
claim or real cluster qsub was performed.


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
