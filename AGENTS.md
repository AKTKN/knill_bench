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
