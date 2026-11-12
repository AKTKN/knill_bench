# Deep logical Clifford generation — Phase 3

`converter_deep_clifford` now generates and compiles logical Clifford circuits
with parallel Knill EC, validates their logical stabilizers and appends native
terminal probes. No noisy deep-circuit decoder or logical error rate is
implemented by this generation model. Phase 4 now adds a separate
[scientific runner and local decoder](converter_deep_decoding.md). Existing converter SE/Knill memory and Hex runners
are unchanged.

The circuit family uses ideal plus-state input, single-qubit H/X/Y/Z gates,
then randomly paired/oriented CNOTs, following Cain et al., PRL 133, 240602
(2024), Fig. 3 and supplemental Sec. 2.C.
[Paper and supplement](https://arxiv.org/pdf/2403.03272),
[published article](https://doi.org/10.1103/PhysRevLett.133.240602).
Here each SE interval is explicitly replaced by n_r parallel Knill cycles.
This substitution changes the physical experiment; no paper performance or
correlated-decoder result is reproduced or claimed.

## Installation and commands

Use Conda `knill_system` and the unchanged exact converter/stimflow pins in
[the integration guide](converter_integration.md). All physical compilation,
CSS layouts, lifecycle/orientation metadata, logical state tracking and
terminal lifting use the converter's public API.

```bash
conda activate knill_system
knill-bench-v2 validate-config configs/converter_deep_clifford_v2_example.yaml
knill-bench-v2 compile configs/converter_deep_clifford_v2_example.yaml
```

`compile` creates a fresh artifact-only directory and prints its path. It
does not sample, create a matching decoder, write an error Parquet table or
mark a scientific run complete. Phase 4 `run` and `resume` use a separate
scientific dataset; see [deep decoding](converter_deep_decoding.md).
`prepare` retains the Phase 0 empty-run contract.
A generated bundle is inspected through its files; it is not a resumable
simulation dataset. Repeating `compile` always creates a new directory.

The [small example](../configs/converter_deep_clifford_v2_example.yaml) uses
d3, two layers and ideal/M9 resources with p_st=p. The
[noisy-resource template](../configs/templates/converter_deep_clifford.yaml)
uses depth 2 and d3/5. The explicitly tested
[depth-32 template](../configs/templates/converter_deep_clifford_depth32.yaml)
compiles at d3 without sampling.

## Configuration and logical random instance

Defaults are four logical qubits, depth 32, circuit_seed 0 and n_r 1.
Only d/p sweep; depth, n_r and circuit_seed are fixed settings. Positive
integer n_r counts Knill cycles per interval, independently of the d rounds
used to prepare each resource. Both r_0/r_plus must resolve to d at every
distance. The strict common round-rule syntax remains available, but a rule
resolving to another depth is rejected. Initial input must be ideal.
Even logical_qubits>=2 are supported explicitly; four gives two disjoint
CNOTs per layer and twelve physical patches.

```yaml
schema_version: 2
kind: converter_deep_clifford
name: deep_example
code: rotated_surface
noise: converter_uniform
decoder: mwpm
sweep:
  d: [3]
  p: [0.001]
logical_qubits: 4
depth: 32
circuit_seed: 19
n_r: 1
r_0: d
r_plus: d
input_preparation: ideal
resource_preparation: noisy
output_root: results
```

`generate_logical_circuit(logical_qubits, depth, circuit_seed)` uses a private
`random.Random` MT19937 stream and never touches global RNG state. The versioned
convention is `python_random_MT19937_HXYZ_shuffle_orientation_v1`. In each layer:

1. In Q index order, draw one randrange(4) gate using HXYZ, with probability
   1/4 each. Identity is not an option.
2. Shuffle list(range(logical_qubits)) and pair adjacent entries. This gives
   a uniform perfect pairing.
3. Draw one getrandbits(1) coin per pair; bit 1 reverses control and target.

All single-qubit gates precede both CNOTs; both CNOTs precede the QEC interval.
There are no extra Pauli gates after the CNOTs. Uniform gate probabilities and
this exact seeded call order are explicit consumer conventions; they do not
recover the paper's unreleased random seed/particular gate instance. The full
sequence, convention, probabilities and logical-instance hash are exported;
runtime Python/version provenance is retained.

d, p, n_r, resource noise, master_seed, shots and workers never enter the logical
RNG. Changing them preserves the entire ideal gate instance for a fixed depth,
qubit count and circuit seed. Increasing depth preserves the shorter gate
prefix. Worker count cannot alter generation. Physical point identities still
include d/p/n_r and preparation policies, under the new deep program contract;
the existing SE/Knill/Hex identities are unchanged.

## Physical resource allocation and barriers

Each Qq has its own Pq_0/Pq_1/Pq_2 set. All Q handles are initialized with
INIT_X(1), noise=ideal, in one parallel group. Per-qubit roles rotate through
(data,A,B)=(0,1,2),(2,0,1),(1,2,0), using the global Knill-cycle index across
layer boundaries. Persistent Qq is never rebound or reset while surviving.
Every resource handle and primitive/composite label is fresh.

Single-qubit gates form one parallel group. Paulis use mode=transversal;
Hadamards use the converter's H semantics. The CNOT perfect matching forms
another parallel group. For each of the n_r cycles, fresh A/B bindings precede
a group containing all four KNILL_EC[tag](d) operations. Full group barriers
separate gates, CNOTs, successive Knill cycles and the next logical layer.
Factories are physically parallel, rather than sequentially emitted circuits.
The model checks native time layers for simultaneous resource initialization.

After the last interval, every surviving Q output receives exactly one
SE[final_se_q](1), noise=ideal, in a final parallel group. No destructive logical
readout is added. Native metadata validates physical overlap conflicts, resets,
use epochs, relocations and orientation. The consumer checks 3N patches,
N*depth*n_r relocations, N*(1+2*depth*n_r) uses and final active bindings.
Width stays fixed; circuit, record and metadata size grow with depth and n_r.

## Noise policy

Input initialization and terminal SE/probes are ideal. The remainder uses
the public NoiseModel.uniform_depolarizing(p) contract, including physical
logical gates and the native Knill operations. This is the existing converter
uniform model, without replacing its probabilities with the paper's separate
physical noise conventions.

resource_preparation: noisy (default) uses d noisy resource-preparation rounds
and no M9/post-initialization channels. resource_preparation: ideal uses public
ResourcePreparationNoise(enabled=True, p_st_transversal=p*p_st_multiplier).
The multiplier defaults to 0, retaining Phase 0's meaning of ideal resource
preparation without an added channel; setting it to 1 selects p_st=p. It must
be fixed, finite and nonnegative, with every resolved p_st in [0,.75]. It is
rejected for noisy resources. M9 idealizes resource preparation only; resource
entangling CNOTs and teleportation/readout operations retain ordinary noise.
There is no added input post-initialization channel in this phase.

## Signed stabilizers and terminal probe

Production obtains its signed output generators exclusively from
compiled.logical_output_stabilizers. Abstract logical validation requires N
independent commuting Hermitian generators on active Q handles, using Stim's
public tableau validator. Independent test circuits propagate each initial Xq
through the sampled logical gates as U Xq U dagger and compare the complete
signed stabilizer groups, allowing equivalent generating bases and row order.

compiled.make_terminal_observable_probe(generators) owns physical Pauli lifting,
MPP targets, relocation, orientation and signs. The exported/sampler-ready
circuit is **probe.circuit**, including N noiseless terminal measurements.
The canonical compiled.circuit remains the unchanged prefix, and frame plans
consume only that prefix. Bench preserves original_measurement_count, terminal
indices, source fingerprint, logical definitions, physical X/Z supports,
physical signs and block-use IDs from the native probe.

Phase 3 exposes the compiled model and its lazy native frame plan for later
consumers, with no decode_batch method. Tests use an independent exact finite
recorded-sector representative for perfect syndrome bits, apply only native
CorrectionBatch values and call probe.corrected_flips for noiseless validation.
Terminal columns never select a correction. This limited test oracle is not
a noisy decoding policy and is not part of production generation.

## Generated bundle and validation boundary

The directory uses the existing Japan-time timestamp/config-hash/name format.
It stores exact effective config.yaml and a metadata.json with
artifact_schema=converter_generation_v1, purpose=circuit_generation_only and
status=generated or failed. It has no simulation complete marker or shot/error
counts. Each physical point contains:

```text
points/<case_id>/circuit.lstim
points/<case_id>/circuit.stim                # includes the native terminal MPP
points/<case_id>/logical_stabilizers.json    # signed logical definitions
points/<case_id>/metadata.json              # native export, full logical sequence, probe metadata
```

The parent owns publication. Files are fsynced and hashed; failed sidecar
publication rolls back that point. Generation validates point identities,
full logical-instance reconstruction, source/probe linkage, exact circuit text,
measurement partition and stabilizer hashes before marking a point generated.
Failed compilation is recorded explicitly. Regeneration starts fresh; Phase 3
adds no resume protocol or Parquet schema. Compilation currently happens in
the parent; workers remains a saved future-execution setting, independently of
the native physical PARALLEL operations.

See [the implementation report](converter_deep_clifford_report.md) and
[TEST.md](../TEST.md) for deterministic, signed-state, parallel/resource,
probe-isolation and depth-32 checks. All sampled fixtures are noiseless d3
with at most seven shots. These generation-only tests compile finite-p models without decoding. Phase 4
[scientific validation](converter_deep_decoding_report.md) separately exercises
finite-p labels; no noisy depth-32 run is included.
