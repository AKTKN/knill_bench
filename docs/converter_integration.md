# Converter integration — Phases 0–4

This phase adds infrastructure for `converter_se_memory`,
`converter_knill_memory` and `converter_deep_clifford`. Phase 1 implements
[ordinary converter SE memory](converter_se_memory.md); Phase 2 adds
[three-patch Knill EC memory](converter_knill_memory.md). Phase 3 adds
[deep Clifford circuit generation](converter_deep_clifford.md), through the
artifact-only `compile` command. Phase 4 adds [noisy deep decoding](converter_deep_decoding.md). `validate-config` parses all
three without importing converter, stimflow or Hex. `prepare` verifies the
installed converter and reserves pending point directories. `run` and `resume`
execute all three converter kinds; `summarize-deep` validates saved deep labels
and reports full-circuit LER with pointwise Wilson intervals.
Its `compile` output is a separate generated-artifact manifest, with no sampled
labels/Parquet table or scientific completion marker.
Existing Hex configurations, hashes, seeds, filenames, directories and table
schemas are unchanged. V1 numerical sources and dependency sources are unchanged.

## Installation and branches

The implementation branch `feature/converter-simulations` starts at bench
`auxiliary-system@2e618b9bbe66ce6d79f1a002183155a42954411d`, as requested.
The independent `surface-prep-fixed` branch is preserved. At inspection the
user's converter checkout was clean on `main@64e139d`; required commit
`457dc519adec6a11b38843a03e1c8fbbd6495f5a` was on
`origin/feature/parallel-knill-deep-clifford-api`. Neither source nor checkout
branch is changed by installation. Never install a floating converter branch.

```bash
conda activate knill_system
python -m pip install -c requirements.lock -c requirements-research.lock -r requirements-converter.lock
python -m pip check
# Complete fresh setup, including the optional backend:
bash scripts/bootstrap.sh --with-converter
```

`pyproject.toml` offers the optional `converter` extra with exact Git URLs.
The separate optional lock also pins converter-only transitive dependencies.
stimflow is pinned to Stim repository commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`, subdirectory `glue/stimflow`.
Tested installed versions are converter 0.0.1, stimflow 1.17.dev0, Python
3.12.15, Stim **1.16.0**, PyMatching **2.4.0**. No Stim downgrade is allowed.
The ordinary Hex bootstrap and four-wheel bundle do not require this backend.

Optional converter cluster wheels are built from exact VCS requirements, with
source manifests added only to staging wheels. Both Python source and the
LSTIM grammar are hashed. The wheel RECORD is regenerated after tagging.

```bash
bash scripts/python.sh scripts/build_cluster_bundle.py --with-converter --download-deps --output results/converter_bundle
```

This produces six project wheels plus platform-specific dependency wheels.
The target installer uses numeric converter-runtime pins and `--no-deps` for
the source wheels; it never resolves Git URLs in offline mode. Conda Python
is still provisioned separately. The original source lock is included for audit.

## YAML contract

Use the [SE](../configs/templates/converter_se_memory.yaml),
[Knill](../configs/templates/converter_knill_memory.yaml), and
[deep Clifford](../configs/templates/converter_deep_clifford.yaml) templates.

```bash
knill-bench-v2 validate-config configs/templates/converter_knill_memory.yaml
knill-bench-v2 prepare configs/templates/converter_knill_memory.yaml
knill-bench-v2 compile configs/converter_deep_clifford_v2_example.yaml
```

All retain `schema_version: 2`, `sweep.d`, `sweep.p`, `shots`, `batch_size`,
`workers`, `master_seed`, `output_root`, `name`, `code: rotated_surface`,
`decoder: mwpm`, `buffer_shot` and `target_chunk_seconds`. Only d/p sweep.
Distances are odd integers >=3; probabilities are finite in [0,.5].
`noise: converter_uniform` is required and reserves exactly the public
`NoiseModel.uniform_depolarizing(p)` policy. Hex noise profiles are rejected.
The SE runner delegates its entire physical schedule to the converter.

| Kind | Additional fields and defaults |
| --- | --- |
| All converter kinds | `input_preparation: noisy` or `ideal` (must agree with Knill regime) |
| SE memory | `rounds: d` |
| Knill memory | `T_tel: 1`, `r_0: d`, `r_plus: d`, `post_rounds: 0`, `resource_preparation: noisy_d_rounds` or `ideal_post_se_depolarizing`; ideal-post `p_st_multiplier: 1` |
| Deep Clifford | `logical_qubits: 4`, `depth: 32`, `circuit_seed: 0`, `n_r: 1`, `r_0: d`, `r_plus: d`, `resource_preparation: noisy` or `ideal`; ideal resources allow `p_st_multiplier: 0` |

SE/deep policy names are consumer-owned contracts: `noisy` retains uniform preparation
noise; `ideal` requests ideal input initialization or ideal Bell-owned resource
preparation without an added post-preparation channel. Future runners must use
public typed preparation policies/primitive overrides. These names do not
idealize subsequent gates or erase residual errors. `n_r` reserves the number
of parallel Knill EC rounds per Clifford layer; `circuit_seed` identifies the
generated logical gate schedule separately from `master_seed` sampling.
Knill uses the two explicit Phase 2 regimes: noisy d-round input/resources,
or ideal input/resources plus public post-initialization/M9 data channels.
The ideal-post multiplier sets p_st=p*multiplier; ordinary CNOT/readout noise
remains active. Conflicting input settings and legacy placeholder Knill names
are rejected. Deep requires ideal plus-state input; noisy resources use d rounds,
and ideal resources use typed M9 with optional p_st=p*multiplier (default zero).
Its seeded single-qubit/CNOT sequence is independent of d/p/n_r/workers. Native
parallel Knill groups and terminal probes retain the Phase 3 generator; Phase 4
reuses the local temporal/CSS/readout adapters and native causal frame replay.
SE memory now uses exactly R total rounds and Z-sector MWPM, with noisy Z
readout. Deep Clifford reserves ideal
terminal stabilizer probes exclusively for evaluation.

Depth rules share existing exact rational flooring: positive integer, `d`,
`2*d`, `2/3*d`, `.6*d`, etc. Every resolved result must fit positive int64.
Knill and deep require **resolved r_0 == r_plus == d at every swept d**.
post_rounds is Knill-only and must be a nonnegative integer. Deep logical_qubits
must be even and >=2 for disjoint perfect CNOT pairing. Unknown/duplicate keys, arbitrary
expressions, unsafe YAML, irrelevant kind fields and new sweep axes fail before
output. Hex-only priors/theta/gaps/validation switches are rejected.

Physical identities include kind, d, p, resolved depths/rounds, preparation
policies, logical qubit count, depth, circuit seed, n_r/T_tel, Knill post_rounds/
p_st multiplier and the program
contract version. Execution settings and requested shots are excluded.
Equivalent round rules resolve to identical physical IDs/point seeds even
when their YAML config hashes differ. The existing point/chunk derivation
algorithm is reused, in a distinct physical kind namespace.

## Consumer architecture and execution

`knill_bench.converter` imports no backend at package import time.
`config.py` supplies frozen/pickleable configs and points. `models.py` defines
the stable `SimulationModel` protocol: exact sampled `circuit`, original
`lstim_source`, worker-local static `decoder` and `frame_plan`, compact
`metadata`, and `decode_batch(measurements) -> DecodedBatch` containing a
one-dimensional bool logical-error array. Truth/probe columns must never
enter decoder inputs. Phase 1 adds se_memory.py, decoding.py and metadata.py
for ordinary memory. Phase 2 adds knill_program.py, knill_memory.py,
knill_decoding.py and local_matching.py for public native stage/frame replay
with independent temporal-component/CSS matching. Correlation loss, invisible
components and local-prior limits are explicit in metadata; residual hyperedges
raise. Phase 3 adds deep_program.py/deep_clifford.py for seeded abstract gates,
public parallel compilation and native signed probes, plus generation.py and
deep_artifacts.py for artifact-only publication. Phase 4 adds deep_decoding.py,
deep_simulation.py and deep_metadata.py for local replay, native terminal
evaluation and strict saved scientific identity. No
private converter import or copied converter implementation is permitted.

`execution.execute_converter_points` requires explicit worker/artifact-builder
callbacks, supplied by all three converter runners. It reuses shared ChunkTask/ChunkResult,
spawn pools, bounded outstanding/reordered batches, ChunkSizer, PointBuffer,
PointWriter, chunk seeds and RunStore. The artifact builder runs in the parent;
workers return bool vectors, timing/caps and <=64 KiB JSON execution descriptors.
Native samplers, circuits, graphs and frames stay local to their process.

Converter fixed mode uses independent chunk seeds under
`converter_fixed_chunks_v1`, with exactly the supplied batch partition;
serial/spawn results match for identical tasks. Auto uses existing
`time_adaptive_chunks_v1`: timing may change partitions/results across runs or
worker counts. Existing Hex fixed mode retains its continuing point sampler.
Only the parent opens converter point writers or publishes sidecars/metadata.
Synthetic seven-row workers and tiny real SE/Knill runs verify this path.

## Saved artifacts and recovery

Run names retain Japan time `YYYYMMDDHHMMSS_<config_hash8>_<name>` and exact
input YAML. Converter layout is point-relative, using the full physical ID:

```text
config.yaml
metadata.json                         # existing RunStore, publication markers
points/<case_id>/
    circuit.lstim
    circuit.stim                     # exact sampled model, including probes
    logical_error.parquet            # unchanged v2 uint64 shot_id / bool label
    metadata.json                    # converter_point_v1 identity/model/content hashes
    logical_stabilizers.json          # optional, deep Clifford only
```

`prepare` creates empty point directories and pending metadata only. Scientific
artifacts retain public `compiled.export_metadata()` inside the model sidecar.
The SE serializer round-trips every numeric argument and verifies full equality
to the sampled circuit. Exported selected instructions additionally preserve
exact reconstruction. The model's
sampled circuit must be the same circuit whose artifacts are published.
`PointArtifacts` carries parent-owned source strings and JSON model metadata.
For both deep `compile` and scientific runs, circuit.stim is the **extended probe.circuit**. The original
native circuit export remains the canonical prefix; terminal probe metadata
retains its original measurement count, indices, signed supports and fingerprint.
Signed logical definitions are mandatory for both generated and scientific deep artifacts.
The root `converter_generation_v1` manifest has generated/failed status and
does not use the simulation table or completion contract shown above.

Run point `files` lists the required table/sidecars and any optional stabilizer
file; `artifacts` maps sidecar paths to SHA256. All sidecars fsync before the
first rename, and publication failures roll back promoted sidecars. Tables
retain atomic close/fsync/schema/count verification. The run point's
`status: complete` is the group publication boundary; filesystem renames are
not jointly atomic. Before completion/resume, sidecar contents/identities and
streamed table IDs/error counts are verified. Optional artifacts are registered
under the same rule. Fixed file allowlists and safe POSIX relative paths reject
traversal, Windows drive/UNC paths and symlink escapes.

Only the owner updates metadata. Incomplete-point recovery removes all of that
point's known table/sidecar/temp files and restarts at zero with the same seed;
complete files stay intact. Config/source/version compatibility and all complete
points are checked before cleanup. No unfinished scientific kind is marked as
success by public CLI. All converter scientific runs support resume. Generated
bundles remain artifact-only and cannot be resumed as scientific datasets.
Memory checks cross-check execution,
artifact hashes/export and physical/readout identities before publication/resume.
Knill additionally binds preparation probabilities, decoder approximation and
per-stage model digest to its saved sidecar.

## Provenance

Converter runs record actual installed converter and stimflow revisions,
versions, origin/subdirectory, resource hashes and import paths, plus Stim,
PyMatching, Python and other relevant versions. Exact pip VCS direct_url and
installed RECORD hashes, or verified bundle manifests, are required. Plain
unverified PyPI wheels/editable checkouts are rejected explicitly. Source
checkouts/Git are unnecessary at wheel runtime. Resume compares both backend
source identities and versions. Hex experiments continue to use their existing
Hex-lineage API/source/matrix checks and never import this optional backend.

See [the Phase 0 report](converter_phase0_report.md),
[the SE-memory guide](converter_se_memory.md), [Phase 1 report](converter_se_memory_report.md),
[the Knill guide](converter_knill_memory.md), [Phase 2 report](converter_knill_memory_report.md),
[the generation guide](converter_deep_clifford.md), [Phase 3 report](converter_deep_clifford_report.md),
[deep decoding](converter_deep_decoding.md), [Phase 4 report](converter_deep_decoding_report.md) and
[TEST.md](../TEST.md) for verification and remaining phase boundaries.
