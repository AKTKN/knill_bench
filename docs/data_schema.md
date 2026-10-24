# Output and schema version 1

The [fixed-R preparation contract](temporal_preparation_theory.md) defines
in-memory online/truth/prediction types at prompt 00; prompt 01 adds explicit
circuit record/observable maps and detached production batch splitting.
Prompt 02 adds an explicitly requested setup artifact through
`temporal_artifact.write_temporal_model`: version-1 JSON, canonical payload
SHA256, original ordered term supports/probabilities, typed detector rows,
feature order, float/integer costs/policies and model provenance. Loading
strictly reconstructs sparse arrays without a DEM parser; the future runner
will persist/verify the owning hash. See [artifact details](temporal_boundary_model.md).
It changes no persisted shot table. Future preparation results require a separate versioned
sign/code/logical schema; existing `logical_failure`/`errors` columns and v2
point files must retain their meanings.

B1 retains this v1 layout and the B0 v2 table types below. Its independent
[Fig.4(d) runner](fig4d.md) writes only one logical_error table per point,
actual shot/error counts and a nested execution descriptor in the existing
metadata.json. Saved-data analysis validates every shot ID and label count;
the optional Agresti-Coull plot requires no new analysis tables or simulation.

B2's [factory runner](logical_zero_factory.md) streams both B0 tables with
identical contiguous shot IDs. Every stage has a finite nonnegative float64
gap (hamming_weight for False, log_weight for supported True). Nullable types
are retained, but B2 rejects unavailable/nonfinite scores. T/depths, oracle,
roles, policies and compact model hashes enter the existing execution metadata;
there are no mandatory additional tables or first-rejection/cost outputs.

B3 reads those same files and optionally emits a separate JSON/CSV/Markdown
report on request. Per-cut rows include counts, acceptance/abort and 95%
pointwise Agresti-Coull intervals, terminal factory-oracle LER/conditional
uncertainty, first-rejection counts, assumed attempt costs and explicitly
enabled iid restart estimates. Undefined conditional/ratio values are null
(blank CSV). No mandatory simulation storage/schema is added. See
[the B3 guide](factory_analysis.md) for fields, equations and limitations.

`src/knill_bench/data/storage.py` is the authoritative Arrow schema. Every table has schema-version and table-name metadata, explicit scalar types, and nullable fields. Counts/times/indices use int64, physical seeds uint64, rates/statistics float64, flags bool, packed bits binary, and IDs string. Bits are little-endian within each byte. Unknown diagnostics are null, not zero.

| Table | Observation and key | Semantics |
|---|---|---|
| cases | `(sampling_case_id, requested_decoder)` | Protocol, geometry, basis, distance, p, cycles, rates, boundaries/schedule, requested/effective decoder, parameters, fallback reason, hashes, validation and resources |
| batches | `(sampling_case_id, replicate, chunk_id)` | Physical seed, shot range, confirmed/requested count, sampling/conversion times, worker/load, sample hash and status |
| decoder_batches | effective decoder case on chunk | Logical errors among valid predictions; valid/failed/task counts; batch wall/CPU work; history scope |
| shots | effective decoder case and shot | Packed actual/predicted logical bits, nullable logical failure, validity/residual, BP counters; no per-shot fault vector |
| decoder_calls | actual invocation | Throughput, single-shot latency, or diagnostic profiling; nested Hex phase, batch/input size, wall/CPU ns, nullable preprocessing/postprocessing, load/replay flags |
| diagnostics | model or sampled decode | DEM dimensions/nnz/hyperedges; residual and BP/LSD counters; explicitly available cluster diagnostics |
| retained_samples | sampling case, replicate, shot | Packed detector/logical records and nullable raw measurements, with bit lengths; uniform/failure/all reason; circuit/model hashes |
| paired_chunks | sampling case, replicate, chunk, decoder pair | Online paired valid, disagreement, and one-sided error counts, including aggregate-only runs |
| summary | requested decoder case | Count-weighted LER and Wilson interval, failure rate, work/throughput, actual latency statistics, exposure/resources |
| paired_disagreements | two effective decoders on same circuit | Paired valid count, differing predictions, first-only and second-only logical errors |
| stopping | sampling case and replicate | Declared rule, actual counts, reference task errors, overshoot, cumulative run wall time and status |
| fault_audit | physical-fault class/witness and decoder | Sparse syndrome packed as bits, predicted/actual logical effects, physical location multiplicity, decoder/circuit ambiguity flags and witness text |

Main layout:

```
config.original.yaml   parameters.json   environment.json   manifest.json
circuits/<sampling-case-id>.stim
models/<sampling-case-id>.dem
models/<sampling-case-id>-<decoder-hash>.graph.dem
models/<sampling-case-id>.metadata.json
data/cases.parquet
data/<table>/part-<case>-r<replicate>-c<chunk>.parquet
checkpoints/<case>-r<replicate>-c<chunk>.json
staging/<case>-r<replicate>-c<chunk>/<table>.parquet  # only while a chunk is running
summary.parquet   report.md   plots/   logs/   provenance/
```

Circuit IDs and DEM content hashes are distinct. Resolved decoder parameters enter decoder-case identity but never physical seeds. A fallback alias's `metadata_json.effective_case_id` points to the sole execution/timing rows. Aggregate through that relation; summing aliased summary rows would double-count actual work. Numeric experiment results are Parquet. Small structured model details are normalized into model metadata; a few compact diagnostic/metadata columns contain JSON strings for variable sparse distributions.

Workers write per-chunk staged parts and return path, row count, SHA-256, status, and small aggregate counters. The parent validates identity, schema, row count, and checksum; filters retained samples in bounded Arrow batches; promotes files atomically; and finalizes the checkpoint last. This bounded filter also applies when `save_all_syndromes=true`. That checkpoint is the transaction marker. Resume validates config/grid and source/environment hashes plus every saved circuit, DEM, and matching graph hash; removes orphan transaction parts; and never counts an existing checkpoint twice. No worker appends to a shared Parquet file. Parent commits bound retained failures across chunks/replicates. Disabled tables retain an empty part with the correct schema. Checkpoints also record setup timing, current/peak worker RSS, observed active-chunk RSS increase, sampled array bytes, staged bytes, IPC payload bytes, staging time, and parent commit time when available. `setup_timing.decoder_sparse_matrix_bytes` counts distinct underlying NumPy buffers of Python-visible sparse matrices in decoder objects; it excludes opaque native backend allocations and is a lower bound on decoder memory. `active_chunk_rss_delta_bytes` is the maximum of RSS snapshots after sampling/conversion, each decode, and staging minus RSS after model construction; it can miss a transient peak between snapshots. `parent_commit_ns` ends after validating and promoting Parquet parts, before the checkpoint and manifest JSON writes. Model metadata names each decomposed graph artifact and its SHA-256. This replaces embedding the full graph text in metadata.

`sample_hash` hashes raw measurements, detectors, and observables for Native Hex. Detector-only cases hash detectors and observables because no raw measurement matrix is sampled. Fixed-seed detector/observable arrays were compared directly with the previous raw-sampling path. In aggregate-only mode, `shots` is empty and `paired_chunks` supplies the paired statistics used by analysis.

`residual_weight` means the full H_det equation for BP-LSD, the legacy preparation-detector check for native Hex, and null for matching adapters that expose only logical predictions. `logical_failure` is null for invalid predictions. `total_task_failure_rate=(logical_errors+computational_failures)/assigned_decodes`. On worker failure, assigned but unobserved tasks are explicitly marked, while confirmed physical shots remain zero. Incomplete/failed run status must accompany any analysis. Wilson intervals concern valid predictions and do not hide computational failures. Zero observed errors have a nonzero upper bound. Sequential-stopping intervals are descriptive, not advertised as exact coverage.

Latency statistics use only actual terminal single-shot invocations, excluding warm-up, sampling, I/O and model initialization. Batch time/shot is named amortized work. Concurrent and isolated replay timing distributions are separate. Native child-backend events are nested under module and terminal timings; sum only one chosen hierarchy level.

Analysis also writes `latency_statistics` (per effective case, replay/load stratum and wall/CPU clock), `decoder_diagnostics_summary` (split by logical success/failure), `native_cost_summary` (explicit timing hierarchy), and `model_cost` (fault/hyperedge/selected-subgraph sizes against amortized work). These are normalized Parquet tables, not values read off plots. Figures include BP convergence, LSD use, sampled cluster counts, hyperedge/subgraph cost, and elapsed-time/spacetime comparisons when time is defined.


## Independent schema version 2 (B0)

V1 schemas/layout and APIs above remain unchanged. New `storage_v2.py`
creates exactly one `logical_error__code=...,d=...,p=...,noisemodel=...,T=...,r_0=...,r_+=....parquet`
per point, containing non-null shot_id:uint64 and logical_error:bool. Factory
also has `logical_gaps__...parquet` with identical row IDs and nullable float64
`gap_t001..gap_tT`. Float p retains full binary64 identity and the literal plus
in `r_+` is preserved. No v1 diagnostics/timing/checkpoint tables are required.

Run root: exact original `config.yaml`, ONE compact `metadata.json`, and the
one/two Parquet files per completed point. New v2 run names are
`YYYYMMDDHHMMSS_<config_hash8>_<safe-experiment-name>` using Asia/Tokyo time
and the first eight hex digits of the canonical simulation-config SHA256.
Collisions advance the directory timestamp one second; metadata keeps the
actual ISO UTC times and full config hash. Old directory names still load.
Both streamed file footers close/fsync/validate
before individual atomic renames; parent metadata marks pair completion.
An unfinished point is never treated as committed data, and clean restart
removes its public/temporary files and begins at shot zero with the same seed.

Metadata includes actual Git/import/resource/dependency provenance, run and
point status/times/counts, master/point seeds, derivation version, input/config
hashes, prior policy, final-readout convention and score units. Only d/p vary
within a run; prior/kind/theta differences get unique run directories. Read
[the B0 guide](auxiliary_v2.md) for exact schema, nullable-gap meaning, ownership,
crash windows and public APIs. B0 provides infrastructure, not science runners.

## Factory local-prior metadata revision

Current True runs declare prior_policy=module_local_stim_dem and
projected_approximation=preparation_and_earlier_stage_residual_errors_excluded_v1.
The existing per-stage projected_prior_sha256/projected_model_sha256 fields
identify local model configuration and Stim DEM text. Execution adds
local_module_sha256, local_analysis_sha256, prior_scope, boundary_noise and
preparation_residual_errors_in_prior/earlier_stage_residual_errors_in_prior=false.
Hashes may repeat across stages. Point tables, seeds and filenames are unchanged.
Old projected data remain analyzable with their saved policy label; changed
policy/source cannot be resumed. See [factory guide](logical_zero_factory.md).

Factory execution now also records skip_circuit_validation (boolean),
circuit_validation (full_native/skipped_by_configuration), and
preparation_frame_implementation (factory_packed_preparation_frames_v1).
Missing fields in historical results do not imply skipped validation. The
default false flag is omitted from canonical config JSON to preserve old
config hashes; true is included. Neither setting changes point IDs/seeds or
per-shot table schemas. Exact input YAML remains archived without modification.

## Adaptive v2 execution metadata and row groups

Auto mode retains these exact table schemas/files and publication boundaries.
The parent buffers ordered labels/gaps and appends buffer_shot rows to each
aligned table per row group (last group may be short). No chunk files or logs
are mandatory. Integer batch_size retains worker-owned writers; buffer_shot
can independently coalesce their results too. Unfinished points restart at zero.
Execution records parallel_execution=time_adaptive_chunks_v1, the actual
sampling/seed stream, partition SHA256, chunk count/shot/duration ranges,
aggregate worker setup/sampling-decode seconds, workers used, target and cap.
Auto consumes chunk seeds; the saved point seed remains an identity. Config
hashes describe the effective --workers override when present; saved YAML
includes the original input SHA256 comment. See [execution](parallel_execution.md).

## Ordinary v2 memory output

se_memory reuses logical_error's shot_id:uint64/logical_error:bool and, when
get_logicalgap is true, logical_gaps with aligned shot_id and gap_t001:float64.
The one score covers the whole memory trajectory; requested scores are finite,
nonnegative and non-null. Standard filename keys remain, with T=1 for one
trajectory score, r_0=r_+=0 for no Knill resources, and an added rounds key.
Physical identity records actual rounds/noisy initial and terminal boundaries,
not those compatibility placeholders. Metadata declares teleportations=0,
full-circuit DEM/decoder/model hashes and complementary log-weight score scope.
Same buffer, paired-publication and full-point restart rules apply. Existing
schemas/filenames/hashes are unchanged. See [memory output](se_memory.md).




Schema-v2 custom factory noise preserves both existing point tables, types,
shot IDs and publication rules. Filenames use noisemodel=custom; the complete
fixed noise mapping enters canonical config/physical identity and compact
metadata with effective probabilities, idle durations/application counts,
native hashes and the local prior's explicit included/excluded sources.
See [custom noise](factory_custom_noise.md). V1 profiles/schemas are unchanged.

## Notebook saved-data views

The [notebook plotting API](notebook_plotting.md) adds no saved schema or
mandatory output. Keyed run paths are loaded at figure time. Only complete
point markers permit reading; schemas, paired contiguous IDs and metadata
counts are verified. Notebook threshold cuts accept strictly gap > threshold
(reject <=), independently of the existing B3 >= convention. Factory selected
LER still describes terminal oracle labels. Unique gap aggregates (exact by
default, or after optional round_digit half-up rounding) and integer lifetime
histograms are in-memory analysis products only. Rounding and optional unique
lists never rewrite the per-shot tables or change B3's original convention.
Notebook lifetime figures normalize each all-shot histogram to a 100% stack
and compute its mean over 0..T. Optional returned summaries are transient
analysis products, with no new mandatory file or simulation schema.
Notebook 95% Wilson shades also use saved aggregate counts only; conditional
LER intervals use accepted denominators and reduction uses paired
acceptance/error-retention bounds. Legacy CLI/B3 intervals and table schemas
remain unchanged. See the notebook guide for the pointwise interpretation.

## General Knill EC memory

The v2 kind knill_ec_memory has only the existing logical_error table and all
existing filename keys. The noise filename label is hex_uniform,
noiseless_bellpair or code_capacity_noise. Special models declare
final_readout=ideal_destructive_Z; uniform remains noisy_destructive_Z.
Execution metadata includes noise_probabilities and
noise_scope_version=knill_ec_physical_noise_v1 with actual T/depths. Complete
publication/resume/saved analysis validate these fields. Legacy kind hashes
and schemas stay unchanged. See [contract](knill_ec_noise_plan.md).

## General Knill prior selection

knill_sim and knill_ec_memory retain the error-only point schema. True
configs save codecapacity_prior (module_local/default or full_prefix) and
distinct prior_policy/approximation plus per-stage two-sector model hashes.
Local execution declares preparation/past residuals excluded from inference;
prefix declares their inclusion. Publication/resume/saved readers validate
the selected scope. Neither prior changes physical point IDs or seeds. See
[metadata and scopes](knill_sim.md).
