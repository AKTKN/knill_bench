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
