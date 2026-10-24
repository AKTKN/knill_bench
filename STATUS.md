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

The requested PBS simplification removes CPU/nodefile inference, WORKERS and
automatic --workers overrides, allocation guards and the separate preflight
CLI invocation. The wrapper activates Conda and invokes one run/resume command.
Workers come from input/saved YAML; the PBS example requests one 96-CPU node
without mpiprocs. BLAS/OpenMP threads remain one. Cluster/getting-started and
parallel-execution guides now describe this contract. Python CLI, schedulers,
simulation configuration/data schemas and dependency sources are unchanged.

All eight updated shell-interface regressions pass. An actual local Conda
wrapper smoke used d3/T1/three shots and YAML workers=2 with a one-entry
nodefile and WORKERS=1; exact saved YAML, workers=2 and completed resume pass.
TEST.md records commands and the full regression result.
Full gate: `bash scripts/python.sh -m pytest -q` — **443 passed**, 1112
inherited-category warnings, **221.51 s**. No failures or exclusions.

## 2026-10-21 — Saved-data notebook figures / APS style

Implemented lazy RunRegistry path/key registration and validated schema-v2
streaming reads, NotebookPlots' six requested editable Matplotlib figure APIs,
and FigureStyle using the user-owned plotting_lib APS package at 300 dpi.
Notebook cuts follow the requested strict acceptance gap>threshold; historical
B3/CLI remains unchanged. Exact unique-score grids/frequencies, per-round
normalization, abort, passed-stage lifetimes, undefined/negative LER reduction,
and color/marker/dash threshold comparisons are documented. Unfinished runs
expose only published complete points with warnings; corrupt complete points
raise. No all-shot arrays, simulation, decoder construction or data mutation.

Added notebooks/saved_figures.ipynb and docs/notebook_plotting.md, updated all
relevant package/test/schema/getting-started guides. Installed plotting_lib
0.1.0 editable in knill_system without changing numerical locks, simulation
wheel bundles or dependency source. Existing .gitignore and basics.ipynb are
preserved. Full regression: 465 passed, 1112 inherited-category warnings,
146.41 s. All six figures render/export from actual saved data; artifacts are
ignored under results/notebook_plotting_smoke. TEST.md records checks/fixes.
The full example notebook also executed successfully under the existing
knill_system kernel against the supplied saved runs; its executed copy stays
under ignored results/. No new simulation or experiment was launched.

## 2026-10-21 — Reference typography, LaTeX and gap rounding

Adjusted all notebook figures through FigureStyle: APS base, 6x3.6 inch,
14pt axis labels, 13pt ticks, 12pt framed legends, serif/Computer Modern math,
300 dpi and marker-safe x margins. labels mappings support mathrm/mathsf;
actual usetex=True uses a minimal customizable amsmath preamble. Verified
actual TeX and MathText PNG/PDF exports in the current Conda environment.

Added optional return_unique to gap frequency, returning sorted unique values
for every group and one-based stage. Added shared/per-figure round_digit:
decimal half-up rounding precedes all gap statistics, cuts and both lifetime
passes, with raw validation first. None preserves exact behavior. Bounded
batch transforms and a 4096-entry distinct-value cache retain streaming; no
saved data, simulation physics or B3 convention is changed. Updated notebook
sources while preserving incoming outputs, and updated the analysis/schema
and user guides. Full gate: 474 passed, 1112 inherited warnings, 147.57 s.
The full updated example executes with round_digit=6 and all-stage unique
returns. New rendered/executed artifacts stay under ignored results/.

## 2026-10-21 — Stacked lifetime distribution and mean

Replaced the notebook lifetime boxplot with per-threshold/group 100% stacked
fractions for L=0..T. Colors identify L, hatches identify groups; dashed grouped
mean curves use a separate automatically scaled right axis so small changes
near T are visible. Means include every shot and remain capped by the saved
T-stage observation window. show_mean=False hides them; return_summary=True
returns exact histogram counts, fractions and means. Default (fig, ax), strict
cuts, shared/per-figure rounding, grid limits and bounded read-only processing
are retained. Removed unused private quartile/outlier helper.

Updated guides and notebook lifetime cells. Preserved the latest user-selected
[0,10,30] thresholds and unrelated notebook sources/outputs. Executed all cells
and refreshed only the lifetime plot/mean output; optional PNG/PDF artifacts
remain under ignored results/notebook_lifetime_stacked. Full gate: 478 passed,
1112 inherited-category warnings, 239.53 s. No new physical simulation or
science/dependency/config change. TEST.md records the layout and notebook
keyword corrections and the read-only rendering checks.

## 2026-10-21 — Readable postselected-LER horizontal ticks

Reduced postselected-LER physical-error x ticks to a regular 1/2/5 grid of
about five intervals, with concise spacing-derived precision, no additive
offset and additional label padding. The supplied .001..005 range displays
.001/.002/.003/.004/.005, keeping the common 13pt font. Other figures and all
numerical/group/threshold behavior remain unchanged. Updated guides and
refreshed only the notebook's postselected plot output, preserving its
[0,5,10] thresholds, round_digit=0 and other cells. Actual PNG/PDF renders and
label-bounds verification pass; full gate: 478 passed, 1112 inherited warnings,
99.35 s. Artifacts stay under ignored results/notebook_postselected_ticks.

## 2026-10-21 — Wilson interval class and five notebook shades

Added analysis.WilsonInterval with vector/scalar score bounds, frequency-count
units, monotone per-round transforms and paired Wilson-derived reduction
bounds. Default 95% pointwise shades now appear on raw LER, stage-gap frequency,
abort, LER reduction and postselected LER; the stacked lifetime figure and
its mean remain unshaded. Selected LER uses accepted shot counts. Zero observed
errors retain positive upper bounds, while undefined denominators/reductions
receive no invented band. Reduction uses error-retention/acceptance with two
Bonferroni-adjusted component Wilson intervals, without assuming independent
samples. Coverage interpretation/equations/primary sources are documented.
FigureStyle adds shade_alpha=.18; existing calls/point estimates are retained.

Updated the example and affected package/schema/user/test guides. All notebook
cells execute against saved data; only the five CI figure outputs were refreshed.
User round_digit, threshold and semilogy settings plus lifetime/other outputs
are preserved. All six read-only PNG/PDF renders pass (bands 3/3/3/3/9/0).
Full gate: 501 passed, 1112 inherited-category warnings, 109.71 s. New numeric
checks cross-validate SciPy score intervals; no new physical sampling, dependency
source edits, simulation fields or production run. TEST.md records commands.

## General Knill EC memory and physical-noise revision (2026-10-22)

Canonical v2 kind is knill_ec_memory with positive T_tel (default 8); old
fig4d_reproduction remains compatible with its original IDs/hashes and
T=8/uniform contract. Shipped Fig.4(d) YAMLs now use the new name with the
same budgets/physics. Hex-owned noiseless_bellpair idealizes preparations and
auxiliary CX; code_capacity_noise inserts only current-data DEPOLARIZE1(p)
before each teleportation. Both have ideal final measurement. Uniform, v1,
factory and SE physics remain unchanged. New kinds use shared fixed/auto
bounded execution, explicit validated noise metadata and saved-only plot-knill
(with plot-fig4d alias). Tiny templates and docs/knill_ec_noise_plan.md added.

Hex 8fa2200315cc4feaccf341a461f91739233de08a was committed/pushed to its
auxiliary-system; bench bootstrap/package/runtime pins and API audit updated.
Final Conda gate: 532 passed, 1208 warnings, 151.11 s. Hex broad gate:
372 passed, 3 historical exclusions, 708 warnings, 68.49 s. Four tiny CLI/shell
smokes cover both new models, fixed/auto and complete resume/PNG analysis.
TEST.md records exact commands, corrected assumptions and the initial
dirty-dependency gate failures resolved by committing Hex before bench's final
gate. No v1 provenance or numerical behavior changed. Incoming unrelated
notebook/.gitignore work is preserved and excluded from this scoped commit.
No production sweep or other worktree edit ran.

## 2026-10-22 — Key-specific ideal-Bell/capacity LER coordinates

NotebookPlots.plot_logical_error_rate adds rescale_p_keys (default None).
Only specified registered dataset keys use x=(23/10)*p-(8/5)*p**2; their Wilson
shades follow the same coordinates. Original-p filtering/grouping, all LER
counts/interval endpoints, legend labels, defaults and other figures remain
unchanged. Nonempty string keys or list/tuple/set/frozenset are accepted,
unknown/invalid keys fail before IO, and filtered-out registered paths stay
lazy. Transformed figures identify the code-capacity x scale. The option
composes with per_rounds without changing its existing y normalization.

Documented the supplied channel correspondence and logical-Z/T=1 assumptions,
with the requested code_capacity/ideal_bell example. Added 20 synthetic cases;
focused notebook gate: 57 passed, 12.58 s. Full Conda gate: 552 passed,
1208 inherited-category warnings, 167.91 s. Real saved-data-only PNG/PDF smoke
passes for eight curves/52 published points, with all input hashes unchanged
and sampler/decoder constructors forbidden. Artifacts are ignored under
results/notebook_p_rescale. User notebook/.gitignore are byte-identical to
initial contents; no simulation, Hex/dependency, configuration or data edits.

## 2026-10-22 — General knill_sim and two explicit prior scopes

Removed the general-Knill False-only guard and added kind=knill_sim while
retaining knill_ec_memory. After explaining the difference, the user explicitly
chose support for both codecapacity_prior=module_local (default) and full_prefix.
Local builds strict two-sector Stim DEMs from the actual current native
Bell-resource CX, optional data noise, data coupling and readouts; +1 CSS/
Pauli analysis boundaries never enter physical sampling. Prep/earlier-stage
residuals are excluded only from its prior. Full-prefix uses native Hex causal
projection/global maps and retains unsupported graph/no-active-event errors.
There is no fallback or physical-noise change. Both scopes retain native prep
repair, packed runtime frames and bounded fixed/adaptive execution.

Explicit scope/approximation/residual flags and per-stage sector hashes are
saved and checked by parent publication/resume/CLI/notebook readers. Existing
valid False hashes and physical IDs/seeds are preserved; mode is inference
only. Tiny templates and docs/knill_sim.md explain both scopes and limits.
The supplied 24-point/200000-shot grid was parsed without circuit construction;
no production sweep ran. Focused: 30 new tests passed, 148 warnings, 18.20 s;
full gate: 581 passed, 1356 warnings, 182.02 s. Read-only Hex: 41 passed,
188 warnings, 26.54 s. Two-worker fixed/auto CLI smokes, complete resume and
saved plots pass for both modes (local d3/5 d-rounds; prefix d3 one-round).
Hex/pins/v1 and user .gitignore/notebook/previous plotting work are preserved.

## 2026-10-24 — Fixed-R preparation theory and contracts (prompt 00)

Committed/pushed the user's incoming notebook/.gitignore changes as checkpoint
2e618b9 on auxiliary-system, then created surface-prep-fixed as requested by
the supplied implementation plan. New implementation remains a local diff.
docs/temporal_preparation_theory.md fixes the actual post-Z output cut,
X/Z sign and deterministic logical-Z labels, hidden-probe assumptions,
P–F graph-parity proof, common objective/frozen constraints, capability errors
and step-by-step integration/acceptance gates against the actual checkout.

preparation.py supplies separate compiled/online/truth/prediction contracts,
strict explicit integer R and supported defaults, and an online/truth shared-
buffer guard. BoundaryConstraintModel aliases the supplied TemporalDemModel.
Reviewed/applied the four-file decoder seed; its solver/tests remain exact,
with source DEM SHA256, strictness and rounding metadata added to the model.
No physical builder/config/CLI/worker/report is claimed at this stage.
Hex remains clean at HEX-K1; other pins/sources, existing v1/v2 numerical
paths, all user notebooks/configs and saved data are unchanged by this phase.
No supplied large validation script or production sampling was executed.

Focused gate: 85 passed, 1.32 s. Full-gate commands, an initial validation
source-edit/resume rejection and its correction are recorded in TEST.md.
Final source-frozen full gate: 666 passed, 1356 inherited-category warnings,
276.16 s. pip check, compileall, documentation links and whitespace pass.

## 2026-10-24 — Fixed-R native circuits and truth (prompt 01)

At the user's request, committed/pushed prompt 00 as e3de069 on
surface-prep-fixed. Hex's auxiliary-system was clean and already pushed at
8fa2200; no dependency source/pin change or artificial empty commit was needed.
Prompt 01 adds native one-patch physical-zero preparation with exactly R full
X/Z SE rounds, ideal evaluation after the final Z extraction and a separate
offline completed X model. Compiled ledgers/detector roles/observable expressions,
cut/resource accounting, actual imported provenance and hashes are explicit.
Signed instrument/logical/label flows, strict DEM extraction and the audited
unconditional uniform-noise domain are checked without sampling or decoding.

The existing config/grid accept a strict protocol-only branch and the tiny
schema-v1 template. Explicit nominal decoding_p changes only inference models,
not physical circuit/point seeds. Detached production sample splitting keeps
all truth/readout buffers out of online observations. Native injected-fault
and current-pin marginal tests cover the output tail, both sign sectors,
deterministic logical Z, single software-frame semantics and oracle isolation.
Legacy config/grid/memory-circuit goldens stay exact. The runner has an explicit
pre-output guard pending step 04; adapters/metrics remain steps 02/03.

Focused final gate: 216 passed, 288 existing-category warnings, 16.62 s.
Installed CLI validation, pip check, compileall and guide/whitespace audits
pass. The full gate and exact commands/corrections are recorded in TEST.md.
No production sampling, existing data/config/notebook edits or dependency
changes are part of this phase. Prompt 01 remains an uncommitted local diff.
Final source-frozen full gate: 762 passed, 1496 existing-category warnings,
187.01 s. The R1 empty-online-X boundary also passes a three-shot p0 smoke.

## 2026-10-24 — Completed DEM boundary models (prompt 02)

Committed/pushed prompt 01 as 3cdc594 (`01: implement fixed-R preparation
and isolated truth`) on surface-prep-fixed, then implemented the requested
boundary-model phase as a local diff. The supplied matching core is unchanged.
TemporalDemModel now preserves named/ordered feature maps, full detector
supports, unidentifiable evaluation terms, original float costs, common
quantization policy and static provenance. Existing positive-probability
projection/inactive restoration and all spatial frozen ports remain exact.

Setup certification compares nominal production/completed same-X online
and all evaluation outputs using independent XOR parity probabilities, with
explicit maps/source/Hex hashes and recorded binary64 bounds. It rejects
changed maps/probabilities or missing evaluation responses. Version-1 JSON
artifacts preserve original columns/features, metadata and a canonical hash;
loading validates the model without parsing a Stim DEM. Exclusive/fsynced
artifact I/O is available to the future runner. No existing simulation table,
runner, circuit builder, config hash, matching core or dependency source was
changed; high-level X/Z inference/metrics and ordered execution remain 03/04.

Focused final gate: 247 passed, 272 existing-category warnings, 10.74 s.
New tests use hand-derived synthetic models and tiny d3/5 DEMs, including R2
readout/data/two-qubit Pauli responses, future-only ports, two-future
cancellation, fixed-zero/one offsets, active-zero costs and strict portable
artifact round-trips. pip check, compileall and a three-shot production/core
artifact smoke pass. Full-gate results and exact commands are in TEST.md.
No production sweep, user notebook/config/.gitignore edits, saved-data change,
Hex edit or dependency-pin change is part of this phase.
Final source-frozen full gate: 828 passed, 1628 existing-category warnings,
191.44 s. All 762 previous tests are retained; 66 model/artifact cases were
added. Documentation links, new-file whitespace and git diff checks pass.
