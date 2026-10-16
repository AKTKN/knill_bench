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
