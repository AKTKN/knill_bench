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
