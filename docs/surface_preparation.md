# Fixed-R surface preparation: circuit and truth (prompt 01)

`surface_prep_fixed` now has a strict schema-v1 config branch, a Python circuit
builder and production sample splitting. It uses native Hex primitives on
one rotated-surface patch: noisy transversal physical-zero initialization,
exactly R full X-then-Z rounds, then ideal evaluation. Decoder/metric/worker
and saved-report integration are later prompts. `knill-bench build/run`
currently rejects this protocol before creating output; it does not fall
through to the ordinary memory runner.

See [theory, proofs and interfaces](temporal_preparation_theory.md) for the
scientific contract. Hex remains unchanged at HEX-K1
`8fa2200315cc4feaccf341a461f91739233de08a`. The prompt 00 bench checkpoint
`e3de069` is pushed on `surface-prep-fixed`; prompt 01 is a local diff.

## Small example

Use the [three-shot template](../configs/templates/surface_prep_fixed.yaml).
Only distance/physical-p are sweep axes; R is a fixed literal integer.

```bash
bash scripts/python.sh -m knill_bench.cli validate-config configs/templates/surface_prep_fixed.yaml
```

The Python API builds without writing output or constructing a sampler/decoder:

```python
from knill_bench.config import load, grid
from knill_bench.circuits.builders import build
from knill_bench.preparation import split_preparation_samples

config = load("configs/templates/surface_prep_fixed.yaml")
point = next(grid(config))
compiled = build(point)
sampler = compiled.circuit.compile_detector_sampler(seed=617)
detectors, labels = sampler.sample(3, separate_observables=True)
batch = split_preparation_samples(compiled, detectors, labels)
online_x = batch.observations.online_x_detectors
online_z = batch.observations.online_z_detectors
# batch.truth belongs only to the evaluator; no decoder receives it.
print(compiled.metadata["output_cut"])
```

Later workers cache compiled models and advance assigned fixed chunk streams;
this small example is not a new execution framework. No production sweep was
used to validate this step.

## Configuration

Keep the existing schema-v1 `experiment/noise/decoders/protocols/sampling`
structure. A preparation config has one protocol and cannot mix legacy
memory/Knill protocols. `experiment.distances` and `physical_error_rates` are
nonempty unique grids; `bases` is `[z]` (default). `cycles`,
`cycles_per_distance`, `initial_boundary`, `final_readout` and `comparison`
are rejected for this protocol, including explicit legacy defaults.

| Protocol field | Accepted value |
|---|---|
| `id` | `surface_prep_fixed` |
| `rounds` | Required literal positive signed-int64 integer; no d rules, list or expression |
| `prep_basis`, `sign_sector`, `readout_basis` | z, x, z |
| `logical_evaluation` | `prefix_frame_only` |
| `adaptive` | false boolean; integer zero is rejected |
| `decoding_p` | Optional fixed finite number in [0,.5); omitted means the point's physical p |
| `decoders` | Nonempty unique names whose kind is `temporal_gap` |

Only `noise: {profile: hex_legacy}` is implemented. Native data initialization,
ancilla preparation/readout flips and two-qubit depolarization use p; no new
idle/one-qubit channel or generic schedule is added. Explicit/phenomenological
profiles and Knill options fail. Physical p may be in [0,.5], but its default
nominal decoder p must be below .5; supply a distinct nominal value if needed.
The temporal descriptor accepts positive finite `weight_scale` (1000) and
`output_mode: compact|full_witness`; this step validates the descriptor without
constructing its future adapter. Only `sampling.stop_rule: fixed_shots` is
accepted. Worker counts and fixed chunk sizes keep their existing meanings.

Unknown/duplicate preparation YAML keys, unsafe tags, nonfinite/overflowed
numerics and unsupported scientific modes fail before run output. Existing
valid legacy config/grid hashes and numerical builders remain unchanged.

`decoding_p`, cost scale/output mode, workers and shots do not change the
physical sampling case ID. The identity includes R, bases, native noise,
X-then-Z schedule, actual output cut, probe specification and sampler semantics.
Physical and nominal probabilities are both explicit in compiled metadata.
For p_phys=0/p_decode>0, only offline inference models are noisy; physical
sampling stays noiseless. No epsilon is injected into a p_decode=0 model.

## Circuit and index namespaces

`circuits.preparation.build_preparation(case)` and the existing `build(case)`
dispatch return `CompiledPreparationExperiment`:

| Field | Meaning |
|---|---|
| `physical_prefix` | Actual initialization plus exactly R full rounds, all online detectors |
| `circuit`, `dem` | Physical prefix plus ideal X MPP and ideal destructive Z; actual physical p |
| `model_circuit`, `model_dem` | Production-shaped nominal inference circuit/DEM, with the same known-Z anchor and record/label order |
| `completed_circuit`, `completed_dem` | Offline nominal X completion, with ideal past probes after noisy initialization and past/online/future X rows |
| `ledger`, `completed_ledger` | Separate absolute zero-based measurement indices, sources, sector/check/round or data-qubit index |
| `detectors`, `completed_detectors` | Separate detector indices, family/check/round, explicit row role and absolute record expression |
| `observables`, `completed_observables` | Explicit observable-to-metric/check/record parity expressions |
| `labels`, `completed_labels` | Separate grouped observable IDs: all tau_X, all tau_Z, one logical Z |
| `output_cut` | Exclusive physical-prefix instruction/measurement limits, after the final Z extraction |

Round numbers are one-based. No position/coordinate heuristic assigns row
roles or mechanism provenance. The completed circuit has only X detectors;
it does not replace the known initial-Z comparison in the production-shaped
Z-prefix inference model. No standalone random first-X detector is present.

The final destructive Z is ideal. Z truth is H_Z r_Z and logical truth is
L_Z r_Z, without a Z-MPP or terminal recovery. X truth uses the ideal X probes
at the actual output cut. Deterministic labels are tau_X, tau_Z and logical-Z
flip, not absolute random X signs. Sampled truth is never decoder evidence.

`split_preparation_samples` accepts only unpacked bool production detector and
observable arrays with exact dimensions. Its caller owns the production
namespace; shape alone cannot certify an array's origin. Use only the physical
`compiled.circuit` sampler above. It detaches online buffers from raw sampler
and truth storage, including when an input buffer combined both. Do not sample
the completed model and pass its hidden boundary rows as online observations.

## Validation, metadata and limits

Before completion, the builder checks the native ideal full-SE instrument:
each independent CSS check has its signed input-to-measurement flow and is
preserved; both logical Paulis are preserved. Together with the validated
one-logical-qubit CSS ranks, these certify the commuting projective instrument
up to branch phase within this Clifford/Pauli model. The actual native prefix
also has a strict unconditional-operation/noise whitelist. Changed gate/noise
or outcome-feedback structure raises a capability error, even if its ideal
flows happened to remain valid.

Every production/completed detector and evaluation parity passes signed flow
checks. Stim DEM extraction always uses `decompose_errors=False`,
`allow_gauge_detectors=False`, `approximate_disjoint_errors=False`; failures
are surfaced as `PreparationCapabilityError`, with no gauge/approximation
fallback. Compilation constructs no live decoder or sampler.

Metadata separates physical SE/qubit/measurement counts from ideal evaluation
and offline probe counts. Hex legacy has no hardware time model; elapsed time
and spacetime volume remain null. Source hashes cover builder/contracts,
actual imported Hex Python/matrix resources and ordered code-matrix rows.
Model hashes cover prefix/three circuit roles/DEMs, both record/detector/
observable maps and probability/settings semantics. Actual Hex ref/dirty state
is recorded through the existing verified-checkout/wheel provenance path.
The later adapter adds its own quantized-weight/output-mode identity; these
builder hashes describe circuits, DEMs and maps, not a compiled decoder.

Physical tests use d3/5, R=2/3/4/5 and at most seven shots per batch. They
compare native prefix circuits exactly; check random first-X versus zero
noiseless evaluation labels; inject first/final readout, intermediate,
space-time-corner and detector-invisible post-X faults; validate single
software-frame versus double-correction semantics; and isolate oracle buffers
from an actual seed-core decode. Four current-pin d/R combinations also check
production/completed **same-X-sector** marginalized DEM parity probabilities,
including all evaluation labels, using exact independent XOR aggregation.

These are structural tests, not logical-error calibration or a confidence/FT
claim. Full Z inference, comparative-model certification/serialization,
metrics, worker/restart/output and reports remain the later prompts. Exact
commands/results and corrections are recorded in [TEST.md](../TEST.md).
