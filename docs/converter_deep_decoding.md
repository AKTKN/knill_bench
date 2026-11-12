# Noisy deep Clifford simulation — Phase 4

Phase 5 completes the shared workstation/cluster execution contract: all three
converter kinds record actual chunk partitions/seeds in a bounded parent-owned
ledger, save label checksums and E/N/Wilson/timing statistics, and support the
saved-only summarize-converter command. Scientific policies and identities stay
unchanged. See [the final integration guide](converter_phase5.md) and
[validation evidence](converter_phase5_report.md).

`kind: converter_deep_clifford` supports `run`, `resume` and saved-label
`summarize-deep`. Its seeded gate generator, twelve-patch parallel Knill
schedule, ideal input, final ideal SE and converter terminal probes retain
[the Phase 3 physical contract](converter_deep_clifford.md). The physical
substitution of Knill cycles for Cain et al.'s SE intervals and the local
decoder differ from the published experiment. No correlated decoding or
paper-curve agreement is claimed.

## Commands and configuration

Use Conda `knill_system` with the unchanged exact optional
[converter installation](converter_integration.md).

```bash
conda activate knill_system
knill-bench-v2 validate-config configs/converter_deep_clifford_v2_example.yaml
knill-bench-v2 run configs/converter_deep_clifford_v2_example.yaml
knill-bench-v2 resume results/<scientific-run>
knill-bench-v2 summarize-deep results/<scientific-run>
knill-bench-v2 summarize-deep results/<scientific-run> --output summary.json
# Independent generation-only export remains available:
knill-bench-v2 compile configs/converter_deep_clifford_v2_example.yaml
```

The example uses seven shots at d3/depth 2 with ideal resource preparation
and p_st=p. The noisy-resource [template](../configs/templates/converter_deep_clifford.yaml)
uses d3/5, seven shots and two layers. These budgets are smoke examples, not
statistically precise LER estimates. The depth-32 template has been validated
by compilation at d3; it has not been sampled as part of this implementation.
Only d/p sweep. N, depth, circuit_seed and n_r are fixed; the ideal instance
is independent of distance, noise, repetition count, sample seed and workers.

```yaml
schema_version: 2
kind: converter_deep_clifford
noise: converter_uniform
sweep:
  d: [3]
  p: [0.01]
logical_qubits: 4
depth: 1
circuit_seed: 19
n_r: 1
resource_preparation: noisy
shots: 7
batch_size: 3
buffer_shot: 3
workers: 2
master_seed: 12345
```

`resource_preparation: noisy` uses d noisy resource rounds. `ideal` uses native
M9 ideal resource preparation with optional p_st_multiplier (default zero).
Only resource preparation is idealized: logical/entangling/teleportation gates
and destructive Bell readouts retain uniform converter noise. No production
noise, geometry, MPP or signed-frame implementation is copied into bench.

## Static models and causal inference

Each point/process caches one compiled circuit, terminal probe, public
`make_stage_requests(compiled)`, `compiled.make_frame_plan()`, boundary temporal
DEMs and local PyMatching graphs. The parent uses its own cached model for
artifacts. Each chunk creates a fresh Stim sampler with its chunk seed and a
fresh `OfflineFrameBatch`; no RNG state is cached between points/chunks.

Deep decoding reuses Phase 2's boundary and readout adapters in a common
`CausalDecoder`. Each boundary temporal DEM predicts last-check record errors
and any prepared-logical target. Independent CSS capacity matching produces
X-then-Z physical corrections. Prepared eigenvalue constraints use the native
logical supports. The predicted net check sector is verified against the
record-error/correction equation and stored at `StageRequests.sector_input_ids`.

Replay follows `StageRequests.order`. Each stage uses current interpreted
records and events after all earlier corrections. Readouts obtain expected
sectors from the native `ReadoutRequest.sector_map` and constant, then solve
H*correction = H*records XOR expected. Their corrections must actually produce
the expected interpreted sector. Source fingerprints, module, use epoch and
input IDs bind every correction. Missing stages, reordered replay, omitted
corrections and mismatched net-sector equations raise.

The native frame plan carries Pauli frames through CNOTs, Hadamards and
teleportations. Native sector maps retain deterministic cross-block Clifford
propagation. Frames are never reset at a logical CNOT. This deterministic
transport does not introduce joint probabilistic inference: all graphs are
local to a physical patch/window, and every matching call uses
`enable_correlations=False`.

The decoder policy is `converter_deep_local_component_mwpm_css_capacity_v1`.
As in Phase 2, every native graphlike DEM separator component is retained but
components are treated independently. Separate degree-two graph paths preserve
differently labelled parallel alternatives. Detector-free target components
use individual prior-MAP hypotheses; probabilities above one half have explicit
biases. Residual hyperedges and unsupported structures raise. Readout/CSS
capacity uses unit Hamming costs. These priors omit historical residuals from
local inference, while those residuals remain in physical simulation. This is
neither correlated decoding nor exact maximum-likelihood decoding. Metadata
records approximation limits and component/stage model hashes.

## Terminal evaluation and rate definition

The sampler uses **probe.circuit**, including the final N ideal MPP results.
`probe.split_measurements(samples)` supplies the unchanged canonical prefix to
the frame replay. No terminal result enters any stage input, matching graph,
sector prediction or correction. After replay,
`probe.corrected_flips(samples, frames)` evaluates the native signed logical
stabilizers. For four generators,

```
logical_error[shot] = any(corrected_flips[shot, i] for i in range(4))
LER = sum(logical_error) / shots
```

This is full-circuit failure probability for the intended pure stabilizer
state, rather than a per-qubit, per-layer or per-round rate. It is invariant
under a change of independent generating basis. Individual terminal bits and
simulated faults are evaluation data only. The error-definition identifier is
`any_corrected_terminal_stabilizer_flip_full_circuit`.

## Saved data, reproducibility and resume

Each scientific point publishes the unchanged uint64 shot_id/bool logical_error
Parquet schema plus exact circuit.lstim, sampled circuit.stim, metadata.json
and logical_stabilizers.json under points/<case_id>/. The sidecar retains the
full logical gate sequence, RNG convention, native export, signed stabilizers,
terminal supports/indices/original measurement count and decoder stage digest.
Source/artifact hashes, point identity, policy and streamed IDs/counts validate
before publication and resume. Parent-owned bounded writers and metadata use
[the shared converter scheduler](parallel_execution.md).

Fixed integer batches replay bitwise with identical seeds/partitions, including
serial versus spawn workers. Auto timing can change partitions and records;
use fixed batching for paired record comparisons. Unfinished points restart at
zero with the same point seed; completed files are preserved. Completed resume
validates saved artifacts without constructing a circuit or sampling.

`compile` remains a distinct converter_generation_v1 artifact-only manifest.
A generated bundle has no labels or scientific completion marker and cannot
be resumed as a simulation. Use `run CONFIG` to create a fresh scientific run.
Historical Phase 3 generation bundles still validate under their original label.

`summarize-deep` streams and validates saved complete points only. It checks
identity, Parquet schemas/contiguous IDs, row/error counts, circuit/probe and
stage hashes, then reports counts, LER and pointwise two-sided 95% Wilson score
intervals. It neither samples nor resumes and does not require current source
compatibility to analyze saved data. The interval describes the fixed full-
circuit binomial estimand; no simultaneous or adaptively selected coverage is
claimed. Reports are optional requested JSON outputs, not mandatory run files.

See [the validation report](converter_deep_decoding_report.md) and
[TEST.md](../TEST.md) for ideal branches, known physical/logical Pauli faults,
independent PyMatching/projection/symplectic checks and end-to-end output.
