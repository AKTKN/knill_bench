# Output and schema version 1

`src/knill_bench/data/storage.py` is the authoritative Arrow schema. Every table has schema-version and table-name metadata, explicit scalar types, and nullable fields. Counts/times/indices use int64, physical seeds uint64, rates/statistics float64, flags bool, packed bits binary, and IDs string. Bits are little-endian within each byte. Unknown diagnostics are null, not zero.

| Table | Observation and key | Semantics |
|---|---|---|
| cases | `(sampling_case_id, requested_decoder)` | Protocol, geometry, basis, distance, p, cycles, rates, boundaries/schedule, requested/effective decoder, parameters, fallback reason, hashes, validation and resources |
| batches | `(sampling_case_id, replicate, chunk_id)` | Physical seed, shot range, confirmed/requested count, sampling/conversion times, worker/load, sample hash and status |
| decoder_batches | effective decoder case on chunk | Logical errors among valid predictions; valid/failed/task counts; batch wall/CPU work; history scope |
| shots | effective decoder case and shot | Packed actual/predicted logical bits, nullable logical failure, validity/residual, BP counters; no per-shot fault vector |
| decoder_calls | actual invocation | Throughput, single-shot latency, or diagnostic profiling; nested Hex phase, batch/input size, wall/CPU ns, nullable preprocessing/postprocessing, load/replay flags |
| diagnostics | model or sampled decode | DEM dimensions/nnz/hyperedges; residual and BP/LSD counters; explicitly available cluster diagnostics |
| retained_samples | sampling case, replicate, shot | Packed detector/raw measurement/logical records with bit lengths; uniform/failure/all reason; circuit/model hashes |
| summary | requested decoder case | Count-weighted LER and Wilson interval, failure rate, work/throughput, actual latency statistics, exposure/resources |
| paired_disagreements | two effective decoders on same circuit | Paired valid count, differing predictions, first-only and second-only logical errors |
| stopping | sampling case and replicate | Declared rule, actual counts, reference task errors, overshoot, cumulative run wall time and status |
| fault_audit | physical-fault class/witness and decoder | Sparse syndrome packed as bits, predicted/actual logical effects, physical location multiplicity, decoder/circuit ambiguity flags and witness text |

Main layout:

```
config.original.yaml   parameters.json   environment.json   manifest.json
circuits/<sampling-case-id>.stim
models/<sampling-case-id>.dem
models/<sampling-case-id>.metadata.json
data/cases.parquet
data/<table>/part-<case>-r<replicate>-c<chunk>.parquet
checkpoints/<case>-r<replicate>-c<chunk>.json
summary.parquet   report.md   plots/   logs/   provenance/
```

Circuit IDs and DEM content hashes are distinct. Resolved decoder parameters enter decoder-case identity but never physical seeds. A fallback alias's `metadata_json.effective_case_id` points to the sole execution/timing rows. Aggregate through that relation; summing aliased summary rows would double-count actual work. Numeric experiment results are Parquet. Small structured model details are normalized into model metadata; a few compact diagnostic/metadata columns contain JSON strings for variable sparse distributions.

Parts are written to a temporary file and atomically replaced, then a checkpoint is finalized. That checkpoint is the transaction marker. Resume validates config/grid and source/environment hashes plus every saved circuit/DEM hash; removes orphan transaction parts; and never counts an existing checkpoint twice. No worker appends to a shared Parquet file. Parent commits bound retained failures across chunks/replicates. Disabled tables retain an empty part with the correct schema.

`residual_weight` means the full H_det equation for BP-LSD, the legacy preparation-detector check for native Hex, and null for matching adapters that expose only logical predictions. `logical_failure` is null for invalid predictions. `total_task_failure_rate=(logical_errors+computational_failures)/assigned_decodes`. On worker failure, assigned but unobserved tasks are explicitly marked, while confirmed physical shots remain zero. Incomplete/failed run status must accompany any analysis. Wilson intervals concern valid predictions and do not hide computational failures. Zero observed errors have a nonzero upper bound. Sequential-stopping intervals are descriptive, not advertised as exact coverage.

Latency statistics use only actual terminal single-shot invocations, excluding warm-up, sampling, I/O and model initialization. Batch time/shot is named amortized work. Concurrent and isolated replay timing distributions are separate. Native child-backend events are nested under module and terminal timings; sum only one chosen hierarchy level.

Analysis also writes `latency_statistics` (per effective case, replay/load stratum and wall/CPU clock), `decoder_diagnostics_summary` (split by logical success/failure), `native_cost_summary` (explicit timing hierarchy), and `model_cost` (fault/hyperedge/selected-subgraph sizes against amortized work). These are normalized Parquet tables, not values read off plots. Figures include BP convergence, LSD use, sampled cluster counts, hyperedge/subgraph cost, and elapsed-time/spacetime comparisons when time is defined.
