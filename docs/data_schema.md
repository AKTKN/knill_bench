# Output and schema version 1

B1 retains this v1 layout and the B0 v2 table types below. Its independent
[Fig.4(d) runner](fig4d.md) writes only one logical_error table per point,
actual shot/error counts and a nested execution descriptor in the existing
metadata.json. Saved-data analysis validates every shot ID and label count;
the optional Agresti-Coull plot requires no new analysis tables or simulation.

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
one/two Parquet files per completed point. Run names are unique UTC timestamps
plus safe experiment names. Both streamed file footers close/fsync/validate
before individual atomic renames; parent metadata marks pair completion.
An unfinished point is never treated as committed data, and clean restart
removes its public/temporary files and begins at shot zero with the same seed.

Metadata includes actual Git/import/resource/dependency provenance, run and
point status/times/counts, master/point seeds, derivation version, input/config
hashes, prior policy, final-readout convention and score units. Only d/p vary
within a run; prior/kind/theta differences get unique run directories. Read
[the B0 guide](auxiliary_v2.md) for exact schema, nullable-gap meaning, ownership,
crash windows and public APIs. B0 provides infrastructure, not science runners.
