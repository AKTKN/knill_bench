# Converter Knill-memory Phase 2 report

Implemented on feature/converter-simulations after Phase 1 commit 61f4769.
Converter/stimflow revisions, numerical pins, dependency checkouts and existing
Hex runners remain unchanged. The model consumes public LSTIM, typed noise,
stage requests, CSS matrices and frame APIs. Bench implements no physical
geometry or copied converter decoder.

## Result and limits

`converter_knill_memory` now runs/resumes fixed/adaptive multi-worker points
using exactly three recycled patches, persistent D and T_tel native
teleportations. Resource depths are d, independently of T_tel; post_rounds
defaults to zero. The final readout is deterministic noisy Z. Both named
regimes are implemented: noisy d-round input/resources, and ideal input/
resources with typed post-initialization/M9 depolarizing channels. A lifecycle
compile resolves the actual input use before applying the named channel.

Local boundary adapters infer temporal readout errors, perform independent
CSS capacity matching and enforce prepared logical constraints. Readout
adapters match measured syndrome minus the native transported net sector.
Every stage reads the updated interpreted record and applies a native
CorrectionBatch in causal order. The final corrected native Z parity gives
the label. No ideal MPP probe, fault truth or directly sampled observable
label is passed into a decoder.

This decoder is explicitly approximate: native separator components are
independent, graph paths preserve parallel alternatives, detector-free target
components use individual prior hypotheses, and capacity costs are unit
Hamming weights per patch. Residual hyperedges raise. There is no joint
cross-block inference, correlated decoding or exact maximum-likelihood claim.
The metadata stores these limits and hashes/counts for every stage.

An illustrative d3, p=.001, T_tel=2 CLI model has 51 qubits and 10 stages
(5 boundaries, 5 readouts) in either regime. The noisy regime has 1851 native
temporal source events decomposed into 3202 components, including 135
detector-free target components and 1351 separators. All are accounted for.
The ideal-post regime has no noisy temporal preparation events in these local
windows. Its added physical channels remain in the sampled circuit and are
decoded from later syndrome/readout information where observable. These counts
explain a local-model limitation; zero temporal events do not mean zero noise.

Parent-owned streaming, exact sampled Stim/LSTIM, native export, compact
execution descriptors and whole-point restart reuse the Phase 0/1 path. The
Knill-specific program and policy identity prevents accidental reuse of the
Phase 0 placeholder. All 17 snapshotted non-Knill configuration hashes, point
IDs and point seeds remain identical.

## Correctness evidence

The baseline Phase 0/1 converter gate passed 200 tests. New focused gates pass
151 config/local-model tests (including existing strict config tests), 28
physical tests and 13 execution tests. They cover:

- Noiseless T_tel=1/2/3/4 in both regimes with nonconstant Bell branches,
  three physical patches, unique epochs and exact relocation/order checks.
- Physical data targets/probabilities for typed input/M9 channels, noisy
  gate/readout retention, explicit optional post-rounds and regime rejection.
- Single preparation/resource Pauli faults, destructive-readout flips and
  faults before/after teleportation CNOTs; known logical X/Z propagation
  through successive teleportations, including open-output frame transport.
- Direct GF(2) syndrome/correction and nonzero sector-map equations, including
  first-cycle CNOT propagation; exact frame-record deltas and refreshed events.
- Negative tests for omitted/swapped corrections, X/Z input ordering, epochs,
  readout basis and double application.
- Independent small PyMatching references, exhaustive component-pattern
  costs for parallel labels, separator/invisible rules and hyperedge rejection.
- Same-batch determinism, fixed serial/spawn equality, cached native objects,
  Parquet IDs/counts/row groups, artifact reconstruction, failed-point restart,
  unchanged completed bytes and metadata/config rejection before cleanup.

Finite-p fixtures use d3/5, both regimes and multiple teleportation depths;
all new physical batches have at most seven shots. The full regression gate
passes **850 tests**, with **1356 inherited warnings**, in **239.42 s**.
Existing Hex and converter SE tests remain in that gate.

Installed CLI checks pass both regimes at d3, p=.001, T_tel=1/2, three shots
and two workers, covering fixed/auto execution and prepared/completed resume.
Six project wheels build with all 72 Hex matrix resources and the converter
grammar. With PATH empty and all three consumer/backend imports verified from
the installed wheel target, both regimes run through prepared and completed
resume at three shots/two workers. These wheel checks use the existing Conda
numerical dependencies; they do not provision a new offline Python environment.
pip check, compileall and diff checks pass. See [TEST.md](../TEST.md) for commands
and the corrected diagnostic-script metadata-key assumption.

The fixtures establish implementation checks, not a statistical LER, threshold
or speed claim. No production sweep or deep-Clifford scientific phase ran.
See [the runnable guide](converter_knill_memory.md).
