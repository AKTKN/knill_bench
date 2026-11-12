# Converter workstation and cluster execution — Phase 5

All three converter experiments run independently through schema-v2 YAML and
`knill-bench-v2`: ordinary syndrome-extraction memory, sequential Knill memory,
and deep logical Clifford circuits with parallel Knill intervals. Work continues
on `feature/converter-simulations` after Phase 4 `68bb77d`. The final delivered
commit SHA is reported with this phase's delivery message. Converter and Hex
sources and numerical pins remain unchanged.

## Installation and commands

Use Conda `knill_system` (Python 3.12.15). Do not recreate `.venv`.

```bash
bash scripts/bootstrap.sh --with-converter
conda activate knill_system
python -m pip check

knill-bench-v2 validate-config configs/converter_se_memory_v2_example.yaml
knill-bench-v2 prepare configs/converter_se_memory_v2_example.yaml
knill-bench-v2 run configs/converter_se_memory_v2_example.yaml
knill-bench-v2 run configs/converter_knill_memory_v2_example.yaml
knill-bench-v2 run configs/converter_deep_clifford_v2_example.yaml
knill-bench-v2 resume results/<run>
knill-bench-v2 summarize-converter results/<run>
knill-bench-v2 summarize-converter results/<run> --output summary.json
# Retained deep-only summary API/format:
knill-bench-v2 summarize-deep results/<deep-run>
```

`run CONFIG` always starts fresh. `prepare` reserves pending points without
compilation/sampling; `resume` can execute such a prepared run. `--workers 2`
on validate-config/prepare/run saves effective YAML and the original input
SHA256, preserving the input file. Resume uses saved workers/configuration.
`compile CONFIG` remains a distinct generation-only deep bundle, with no labels
or scientific completion marker; such bundles cannot resume as simulations.

The existing [SE](../configs/templates/converter_se_memory.yaml),
[noisy Knill](../configs/templates/converter_knill_memory.yaml),
[ideal-post Knill](../configs/templates/converter_knill_memory_ideal_post.yaml),
and [deep](../configs/templates/converter_deep_clifford.yaml) templates remain
supported. Only d/p sweep. Fixed rounds accept integers, d and positive rational
multiples such as `2*d` with exact flooring. SE counts INIT's first round;
Knill/deep resource depths must resolve to d. T_tel, depth, n_r, circuit_seed,
preparation policies and channel multipliers are fixed settings, not new axes.
For example, a tiny ordinary memory run:

```yaml
schema_version: 2
kind: converter_se_memory
noise: converter_uniform
sweep:
  d: [3, 5]
  p: [0.0, 0.003]
rounds: 2*d
shots: 3
batch_size: 2
buffer_shot: 2
workers: 2
master_seed: 12345
```

Knill selects noisy_d_rounds or ideal_post_se_depolarizing, with T_tel>=1 and
noisy final Z. Deep has ideal plus-product input, four logical qubits by default,
seeded HXYZ/CNOT layers and n_r parallel Knill cycles per interval. Its resources
select noisy or ideal/M9; ideal resources allow p_st_multiplier (default zero).
The final SE and native stabilizer probes are ideal and evaluation-only. See
[SE physics](converter_se_memory.md), [Knill physics](converter_knill_memory.md),
[deep generation](converter_deep_clifford.md) and [deep decoding](converter_deep_decoding.md).

## Public consumer interfaces and decoder policies

`ConverterSEMemory`, `ConverterKnillMemory` and `ConverterDeepClifford` implement
`SimulationModel`: exact sampled circuit, original LSTIM, static decoder/frame
plan, metadata and `decode_batch(raw) -> DecodedBatch(bool_labels)`. Physical
circuit generation, geometry, stage requests, use epochs, sector/frame maps
and terminal lifting remain exclusively public converter APIs.

SE uses the public semantic Z-sector view and a complete undecomposed graphlike
DEM, with physical observable flip XOR MWPM prediction. Unsupported hyperedges
or correlated components raise. Knill/deep reuse local temporal-boundary MWPM,
independent CSS capacity matching and destructive-readout capacity matching.
All native decomposed graphlike components are retained as an explicitly
independent approximation. Distinct parallel alternatives retain separate
paths; detector-free target components use declared individual prior-MAP bits.
Capacity uses unit Hamming costs. Residual unsupported structures raise.
Every matching call disables correlations. Native frame/sector maps preserve
deterministic Clifford/CNOT transport without joint cross-block inference.

Knill evaluates corrected final Z parity. Deep samples probe.circuit, supplies
only its canonical prefix to causal replay, and evaluates public corrected_flips
after every stage correction. A shot fails if any intended signed output
stabilizer flips. Its rate is failure probability for the whole intended pure
stabilizer-state circuit, without per-layer/per-round normalization. Probe
outcomes or fault truth never select corrections. These noise/QEC/decoder
choices differ from Cain et al.'s correlated-decoding experiment; no published
numerical reproduction or threshold claim follows from this integration.

## Spawn, memory and deterministic replay

One spawn pool persists across each run's points. Each process caches one
point's native model and decoders, independent of sampler RNG. Every chunk
gets a fresh sampler with a scheduling-independent uint64 seed. Workers return
only bool labels, bounded timing scalars and a compact static descriptor on
first use. Circuits, graphs and raw records never cross IPC. The parent owns
all label/ledger writers, artifact publication and metadata.

Pending plus reordered chunks are bounded by workers. Per-worker automatic
shot caps use a 64 MiB heuristic for record/frame/decoder arrays; native static
graphs/circuits and Python/compiler overhead are outside that heuristic. This
is not an RSS guarantee. Storage buffers are bounded by buffer_shot; the
sampling ledger buffers at most 512 rows. Circuit/model storage necessarily
grows with distance/depth; no all-shot array or all-chunk list is retained.

Fixed integer batch_size retains converter_fixed_chunks_v1: identical seeds
and partitions give bitwise-identical labels under serial/spawn scheduling.
Auto batching uses time_adaptive_chunks_v1 and timing feedback. Different runs
or worker counts can choose different partitions and records; no general
worker-independent bitwise claim is made for auto mode.

Every actual partition and seed is saved in sampling_chunks.parquet. The public
reader supports exact replay of recorded auto or fixed partitions:

```python
from knill_bench.converter.runtime import iter_sampling_chunks
from knill_bench.experiments.adaptive_execution import ChunkTask, run_chunk
from knill_bench.experiments.config_v2 import load_saved_config

config = load_saved_config(run).config
point = next(config.points())
for row in iter_sampling_chunks(run, point):
    task = ChunkTask(point, **{k: row[k] for k in ("chunk_id", "start", "shots", "seed")})
    labels = run_chunk(task).labels  # compare to saved shot IDs start..start+shots
```

Validate the saved run with summarize-converter before replay. Keep the recorded
backend/source/version environment for bitwise replay. Timing fields naturally
change on replay and are not part of physical identity. A same-batch independent
projection path and recorded-auto replay are tested exactly.

## Output and publication

New scientific runs carry root converter_execution_contract=converter_execution_v2.
The root has exact effective YAML/config hash, resolved point identities, master/
point seeds, actual bench/converter/stimflow identities and package versions.
Each point has:

```text
points/<case_id>/circuit.lstim
points/<case_id>/circuit.stim              # exact sampled circuit, including deep MPPs
points/<case_id>/metadata.json             # native model export/sequence/probe once
points/<case_id>/logical_error.parquet     # uint64 shot_id, bool logical_error
points/<case_id>/sampling_chunks.parquet   # actual partition/seed/timing ledger
points/<case_id>/logical_stabilizers.json  # deep only, signed logical generators
```

The ledger schema is chunk_id/start/shots/seed uint64 and setup_seconds,
sampler_compile_seconds, sampling_seconds, decoding_seconds float64, all
non-null. Metadata binds schema/case ID. Root artifacts map hashes the ledger
and model sidecars; execution.logical_error_sha256 hashes the label file. The
model sidecar's content hashes bind its static source/stabilizer files only.
No per-instruction export is duplicated in compact root results.

Each execution descriptor adds exact native circuit_counts (qubits, detectors,
measurements, native observables, evaluated logical observable count), rate,
pointwise 95% two-sided Wilson score interval, chunk count/digest, and timing
statistics. A representative fragment is:

```json
{
  "execution_contract": "converter_execution_v2",
  "logical_error_rate": 0.0,
  "confidence_interval": {"method": "Wilson_score", "confidence": 0.95,
                          "lower": 0.0, "upper": 0.5614970317550454},
  "chunk_seed_stream": "converter_fixed_chunks_v1",
  "bitwise_replay_requires_fixed_partition": true
}
```

The interval shown is for E=0,N=3, not precision evidence. Worker timing sums
measure per-chunk model setup, sampler compilation, sampling and decoding;
parent_compile_seconds includes model/artifact construction, and
parent_io_seconds measures publication/writes/close/fsync/registration, excluding
validation reads. These sums are not elapsed wall time or disjoint parallel
critical-path costs. Point/run wall_seconds records elapsed duration.

Every writer closes, fsyncs and validates before its public rename. Multiple
renames are not jointly atomic: the parent's complete point marker commits
the entire group. Publication failure leaves an unfinished point; resume deletes
its known public/temp files and restarts at zero with the original point seed.
Completed points validate hashes, model/source/policy, schemas, IDs/counts,
ledger seeds/partition and rate/CI/timing consistency before any cleanup.
Completed resume never constructs a physical model or samples. Earlier converter
results retain their original artifact contract; Hex tables, identities, seeds
and inference policies receive no new converter requirements. Source/version
compatibility remains strict, including the recorded bench revision.

## Cluster packaging and platform boundary

```bash
bash scripts/python.sh scripts/build_cluster_bundle.py --with-converter --download-deps --output results/cluster_bundle_converter
# On a target with compatible Conda Python, copy the bundle, then:
python results/cluster_bundle_converter/install.py
```

Six source-tagged project wheels include the exact converter VCS revision and
pinned stimflow subdirectory, the converter grammar and all 72 Hex matrix
resources. Optional binary dependency wheels permit offline pip installation;
Conda Python is provisioned separately. Target runtime needs neither Git nor
a developer converter checkout. Portable POSIX resource names/order preserve
existing Linux hashes and allow wheel verification on Windows. Windows process
locks use non-destructive handle liveness queries and validation readers close
before rename. PBS remains single-node and takes worker count from YAML.

The Linux/Windows GitHub Actions matrix runs subprocess/spawn, scientific,
serialization, storage and packaging checks. Only executed platform results
may be called validated: local execution here is Linux; CI status is reported
separately. No Windows runner is available inside this Linux workspace.

## Numerical validation and limits

The opt-in script runs small scientific datasets and validates publication,
completed resume, E/N, Wilson intervals and zero-noise labels:

```bash
bash scripts/python.sh scripts/validate_converter_matrix.py --output results/converter_validation
# Expensive, one sampled shot at d3/depth32; separate explicit opt-in:
bash scripts/python.sh scripts/validate_converter_matrix.py --only-depth32 --output results/converter_depth32
```

The regular matrix contains 52 points/156 shots: SE d3/5, R=1/d/2d, p=0/.003;
Knill d3/5, T_tel=1/2/3, both preparation regimes, p=0/.003; deep four-qubit
depths2/3, n_r=1/2, both resource policies, p=0/.003 and circuit seeds19/41.
At least one nontrivial case per kind uses two workers. The separate depth-32
case is d3/noisy resources/n_r1/seed19/p=.003, one shot. Existing exact d3 pure-X
enumeration, d3/5 mapping and single-fault checks, independent local MWPM,
signed logical groups, causal/nonzero-sector and symplectic terminal tests
remain the primary correctness evidence. Small Monte Carlo counts do not test
published curves and are not compared with an arbitrary agreement tolerance.

See [the final evidence report](converter_phase5_report.md) and
[TEST.md](../TEST.md) for actual executed outcomes, failure disclosures and limits.

### Observed depth-32 memory boundary

The finite-p d3/depth32/noisy-resource one-shot run could not complete on this
7851 MiB RAM / 2 GiB swap VM. It was killed during static native stage/view
construction both alongside other gates and in isolation. The isolated attempt
reached 7,111,924 KiB peak RSS (~6.78 GiB), elapsed 8:02.20, with no sampled
labels or complete marker. Reducing shots/buffer sizes does not bound that
static allocation. The pinned public stage/view APIs retain full-circuit and
per-stage snapshots; this integration does not alter private representations
or physical/decoder policies to make the case fit. Finite-p depth32 needs more
static-model memory than this workstation provided and is not numerically
validated here. The separate declared p0/ideal-resource smoke is reported
independently in the evidence report.

The separately declared p0/ideal-resource depth32 one-shot attempt also reached
6,835,408 KiB peak RSS (~6.52 GiB) before sampling and was stopped at the
workstation boundary (10:40.78, exit143). Depth32 compilation/signed-group checks
pass, while **depth32 sampled numerical validation remains incomplete on this
VM**, including at p0. The regular 52-point matrix and all three kinds' smaller
multiworker numerical executions are complete. Use a machine with sufficient
native static-model memory for the depth32 numerical check; no successful
larger-memory execution is claimed here.
