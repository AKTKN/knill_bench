# Converter Phase 0 implementation report

Implemented the attached infrastructure phase on
`feature/converter-simulations`, based on requested bench
`auxiliary-system@2e618b9bbe66ce6d79f1a002183155a42954411d`.
The existing `surface-prep-fixed@00d3852` branch is preserved.

## Dependency and public API audit

Live remote branch checks confirmed the required converter
`457dc519adec6a11b38843a03e1c8fbbd6495f5a` on
`feature/parallel-knill-deep-clifford-api`, while main is `64e139d`.
The user's local clone remains clean on main. Installed exact converter/stimflow
VCS wheels in Conda knill_system, with no dependency source edits. Python is
3.12.15, converter 0.0.1, stimflow 1.17.dev0, Stim 1.16.0 and PyMatching 2.4.0.
Uniform noise, Knill/Pauli and typed preparation exports, stage requests, frame
plans, logical output stabilizers, terminal probes and metadata export are
checked through public APIs only. A small public d3 source compiles a strict
DEM and exports frame/stage/metadata objects without sampling.

## Delivered contracts

- Three strict converter kinds with d/p-only sweep, existing exact round
  resolution, matching resource depths, explicit preparation policies and
  physical identities covering circuit seeds/depth/counts.
- Separate consumer package with a stable sampled-circuit/LSTIM/static
  decoder/frame/batch-bool/metadata model interface. Scientific program
  generation, decoder adapters and models remain subsequent-phase work.
- Optional exact VCS pins, source/grammar verification, installed public API
  audit, version recording and converter-specific resume compatibility.
  Existing Hex-lineage provenance is retained for Hex kinds.
- Parent-owned point directories, staged sidecar registration/content hashes,
  unchanged v2 error Parquet schema, saved ID/count verification and whole-point
  recovery. Complete points validate before any unfinished cleanup.
- Shared bounded spawn/chunk/buffer infrastructure, explicit worker/artifact
  callbacks and compact numeric IPC. Converter fixed chunks use a distinct
  deterministic stream; auto retains timing-dependent partitions. Existing
  Hex execution semantics are unchanged.
- Optional six-project-wheel bundle support, staging-only source manifests
  including grammar and regenerated wheel RECORDs; ordinary bundles retain
  four project wheels. No user dependency checkout is switched or modified.
- Three small commented YAML templates and updated repository/package guides.

Public `validate-config` and `prepare` support the new kinds. Public `run`
and `resume`, plus default low-level compilation/whole-point execution,
raise explicit not-yet-implemented errors; converter cases cannot fall through
to a Hex factory runner or be reported as scientifically executed.

## Validation and limitations

The new contract suite passes **161 tests** (5.95 s). The full bench gate
passes **742 tests**, **1356 inherited-category warnings**, **132.90 s**.
It includes all three
schemas, strict invalid-field/sweep/YAML cases, exact depth flooring, frozen
spawn transport, point/chunk identity changes, installed versions/API/source
verification, blocked optional imports during real three-shot Hex execution,
seven-row synthetic fixed/auto serial/spawn execution, parent writer ownership,
artifact failure/corruption/recovery and portable Windows/POSIX path rules.
The golden fixture preserves all 14 pre-integration v2 configs' hashes, point
IDs and point seeds. Windows-specific paths are checked on Linux; a Windows
runtime/Conda installation is not claimed.

Full regression and installed-wheel/CLI results are recorded in
[TEST.md](../TEST.md). The six source wheels build successfully with dependency
repositories unchanged; wheel CLI/provenance smokes run with Git unavailable.
Numeric dependency resolution is retained from the current Conda environment
for that smoke; a new fully offline Python environment is not provisioned.

No converter physical shots, LER experiment, statistical agreement or production
sweep is implemented or claimed. The future scientific phases must supply the
actual generators/decoder models, retain exact exported instructions with the
sampled circuit, enforce truth isolation and validate their decoding physics.
