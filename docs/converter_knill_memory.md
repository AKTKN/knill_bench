# Converter Knill EC memory — Phase 2

Phase 5 completes the shared workstation/cluster execution contract: all three
converter kinds record actual chunk partitions/seeds in a bounded parent-owned
ledger, save label checksums and E/N/Wilson/timing statistics, and support the
saved-only summarize-converter command. Scientific policies and identities stay
unchanged. See [the final integration guide](converter_phase5.md) and
[validation evidence](converter_phase5_report.md).

`kind: converter_knill_memory` runs one logical Z memory through `T_tel >= 1`
successive converter-native Knill EC teleportations. The converter owns all
physical gates, geometry, detector metadata, patch lifetimes, relocations and
Clifford frame propagation. Bench supplies LSTIM, public typed noise policies,
local PyMatching adapters and bounded execution. Existing Hex runners and the
Phase 1 converter SE model retain their physics and identities.

Use Conda `knill_system` with the exact optional backend installation in
[the integration guide](converter_integration.md). Converter and stimflow pins,
Stim 1.16.0 and PyMatching 2.4.0 are unchanged. No private converter modules or
dependency source edits are used.

## Run and resume

```bash
conda activate knill_system
knill-bench-v2 validate-config configs/converter_knill_memory_v2_example.yaml
knill-bench-v2 run configs/converter_knill_memory_v2_example.yaml
knill-bench-v2 resume results/<saved-run>
```

The [small example](../configs/converter_knill_memory_v2_example.yaml) uses
d3/5, two teleportations and seven shots per point. The templates for
[noisy preparation](../configs/templates/converter_knill_memory.yaml) and
[ideal preparation with post-SE channels](../configs/templates/converter_knill_memory_ideal_post.yaml)
are also runnable. For example:

```yaml
schema_version: 2
kind: converter_knill_memory
name: converter_knill
code: rotated_surface
noise: converter_uniform
decoder: mwpm
sweep:
  d: [3]
  p: [0.001]
T_tel: 2
r_0: d
r_plus: d
resource_preparation: ideal_post_se_depolarizing
input_preparation: ideal
p_st_multiplier: 1.0
post_rounds: 0
shots: 3
batch_size: auto
workers: 2
master_seed: 12345
```

Only d/p are sweep axes. `T_tel` is a fixed positive integer, independent of
preparation depth. Both resource depths must resolve to exactly d at every
distance. The common integer/d/multiplier parser remains available, but a rule
resolving to another depth is rejected for these Phase 2 regimes. `post_rounds`
is a nonnegative integer, default 0; when positive it adds that many noisy SE
rounds after **each** teleportation, including the last. No extra SE is inserted
by default. Final destructive Z readout is noisy and mandatory.

The Phase 0 placeholder Knill values `resource_preparation: noisy` and `ideal`
are replaced by the two explicit names below. Contradictory input settings,
Knill-inapplicable fields, Hex priors/gaps and arbitrary expressions are
rejected before creating a run. `converter_deep_clifford` has a separate [generator](converter_deep_clifford.md)
and [local decoder](converter_deep_decoding.md).

## Three-patch physical program

The source declares exactly P0/P1/P2. Persistent handle D starts on P0, then
the `(D,A,B)` physical roles cycle through `(0,1,2)`, `(2,0,1)`, `(1,2,0)`.
Each cycle binds fresh A/B handles to the two available patches and invokes
`KNILL_EC[ec<i>](d) D A<i> B<i>`. The native compiler relocates D onto B;
bench never rebinds or resets the surviving D use. Resource handles and
composite IDs are unique. The model checks three physical patches and exactly
T_tel relocations. Terminal `MZ[final] D` retains the native deterministic
observable and frame metadata.

## Physical preparation regimes

| Policy | Input | Bell resources | Extra channels |
| --- | --- | --- | --- |
| `noisy_d_rounds` (default) | INIT_Z(d), noisy | d noisy SE rounds per resource | None; M9 disabled |
| `ideal_post_se_depolarizing` | INIT_Z(1), noise=ideal | d ideal SE rounds per resource through M9 | Input DEPOLARIZE1(p); resource DEPOLARIZE1(p_st) after ideal preparation |

Both use `NoiseModel.uniform_depolarizing(p)` for resource-entangling and
teleportation CNOTs, destructive readouts, optional post-rounds and subsequent
operations. Ideal preparation does not idealize those operations.

For the ideal-post regime, bench first compiles a noiseless lifecycle and
finds the actual input preparation/reset `BlockUseId`. It then attaches
`PostInitializationNoise("initial", actual_use, p)` and recompiles with
`ResourcePreparationNoise(enabled=True, p_st_transversal=p*p_st_multiplier)`.
The multiplier defaults to 1 and is finite/nonnegative. Every resolved p_st
must lie in the converter's [0,.75] range. The policy is rejected in the noisy
regime. The final metadata checks that input and M9 channels refer to disjoint
uses; physical tests verify their exact data-qubit targets and probabilities.
No epoch is assumed, and no extra channel is applied to an M9 resource use.

## Causal local decoding

Each worker builds the physical circuit, native frame plan/stage requests,
local DEMs, check matrices and matching graphs once per point. It samples raw
measurements with Stim and starts a fresh `OfflineFrameBatch` for each chunk.
Native `StageRequests.order` defines the replay order. Each stage recomputes
its view/events from **current interpreted records** after preceding
corrections; stale original detection arrays are never reused.

For a preparation or SE boundary:

1. Decode the native `BoundaryRequest.detector_error_model` to predict errors
   in the last check records and, where present, the prepared logical target.
2. Infer the check sector as interpreted last records XOR predicted errors.
3. Apply independent CSS capacity matching using native check matrices:
   H_Z determines physical X correction and H_X determines physical Z.
4. Enforce the prepared logical eigenvalue constraint by a check-preserving
   opposite logical operator when needed. Return X-then-Z `CorrectionBatch`
   plus the predicted residual/net sector. Verify its GF(2) equation.

For a destructive readout, with interpreted records m, check matrix H and
expected sector s from `ReadoutRequest.sector_map` applied to preceding net
sectors, decode `H m XOR s`. Check `H correction == H m XOR s`, then apply the
record correction through `OfflineFrameBatch.apply()`. The native frame plan
propagates corrections and deterministic sectors across both CNOTs and later
teleportations. Requests, source fingerprints, physical input ordering, basis
and use epochs are bound explicitly. The native frame also rejects reuse of
an already applied correction.

All matching calls use `enable_correlations=False`. Each patch has its own
temporal and capacity graphs. Deterministic cross-patch Clifford propagation
uses converter sector maps; no joint cross-block matching graph is built.

## Explicit approximation and unsupported models

Boundary DEMs supplied by the pinned converter are decomposed. Bench retains
**every graphlike separator component** and treats components independently.
Correlation between components of one physical event is therefore ignored.
Each graphlike component gets a separate degree-two subdivision node with
zero syndrome. Its two edge costs sum to log((1-q)/q), preserving differently
labelled parallel alternatives instead of letting a library merge them.

Detector-free target components use their individual independent prior-MAP
bit (q>1/2); they are counted in metadata. This is a component hypothesis, not
an exact marginal-MAP target prediction. Probabilities above 1/2 are complemented
with explicit syndrome/target offsets; zero-probability and fully trivial
components are counted. Residual components touching more than two detectors,
unknown targets and unsupported check-matrix columns raise explicitly. Faults
and measurements are never silently trimmed to make a graph.

Capacity graphs use unit Hamming weights per physical data qubit; these are
decoder costs, not another physical noise probability. Native local windows
exclude earlier residuals from their prior and cannot infer every incoming
error. In particular ideal single-round preparation may supply no temporal
evidence; post-initialization/M9 faults remain in physical simulation and are
handled by subsequent syndrome/readout information where observable.
Prepared logical constraints and sector propagation do not make this correlated
decoding or exact maximum-likelihood inference. Metadata records these limits,
source/component/separator/invisible counts, policies and stage-model hashes.

## Error labels, artifacts and reproducibility

After all stages, bench evaluates the native terminal logical-Z parity on
corrected interpreted records and XORs its deterministic expected bit. This
yields one boolean `logical_error` per shot. No simulated fault truth,
directly sampled logical-observable labels or ideal MPP probes enter decoding.
The production circuit has no evaluation oracle or added probe.

Fixed integer `batch_size` uses independently chunk-seeded samplers and the
existing `converter_fixed_chunks_v1` stream. Identical seeds and partitions
give identical labels under serial/spawn execution. Auto batching can change
partitions and sampled records with timing or worker count. Native static
objects stay local; RNG state is never cached across chunks/points.

The parent streams contiguous uint64 shot IDs and boolean labels to the
unchanged error Parquet schema under `points/<case_id>/`. Exact `circuit.lstim`,
round-trip-equal sampled `circuit.stim` and one model metadata sidecar accompany
the table. The sidecar contains the public converter export, per-stage hashes
and compact decoder summaries. `post_rounds`, both preparation policies and
p_st multiplier enter physical identities/seeds. The new Knill program/policy
contract prevents confusion with the unimplemented Phase 0 placeholder.
Existing SE/deep/Hex identities are preserved.

Artifact hashes, model digest, provenance, IDs and counts validate before
completion/resume. Only the parent publishes metadata; unfinished points
restart at zero with the same seeds and completed points stay intact. A
completed resume neither builds circuits nor samples. See
[execution](parallel_execution.md), [artifacts](converter_integration.md) and
[the validation report](converter_knill_memory_report.md).
