# Fixed-R preparation Monte Carlo (prompt 04)

`surface_prep_fixed` now runs through the existing schema-v1 CLI and ordered
spawn scheduler. It uses the [native circuit](surface_preparation.md),
[completed boundary model](temporal_boundary_model.md) and
[X/Z adapter/evaluator](preparation_decoder.md). Prompt 03 was pushed as
`6fa15c5` on `surface-prep-fixed`; prompt 04 is pushed as `70074e6`.
Hex and its HEX-K1 pin are unchanged. No production sweep was launched.

## Commands and budgets

The [tiny template](../configs/templates/surface_prep_fixed.yaml) runs three
d3/R3 shots, one chunk, one worker. Use Conda knill_system:

```bash
bash scripts/python.sh -m knill_bench.cli validate-config configs/templates/surface_prep_fixed.yaml
bash scripts/python.sh -m knill_bench.cli build configs/templates/surface_prep_fixed.yaml
bash scripts/run_simulation.sh configs/templates/surface_prep_fixed.yaml
bash scripts/python.sh -m knill_bench.cli resume RUN --workers 2
bash scripts/python.sh -m knill_bench.cli analyze RUN
```

`build` creates a fresh prepared run without sampling or live graph
construction. `run` creates another fresh run and executes it. `resume`
continues the saved partition; changing workers is allowed. `analyze` reads
published saved data only and now writes reports, typed gap/risk tables and
figures to a newly created analysis subdirectory. It never simulates or resumes.
See [prompt-05 analysis](preparation_reports.md) and the
[getting-started commands](preparation_getting_started.md). Legacy `audit-faults`
and `benchmark-latency` reject preparation runs; the worker already saves
explicit, bounded replay timings in `preparation_calls`.

The [larger template](../configs/templates/surface_prep_fixed_sweep.yaml) is
**parse-only validation in this phase**: d=3/5/7/9, p=.001/.003/.005, fixed
R=3, 10,000 shots per point, chunk_size=256, workers=4, aggregate-only output.
It has not been run. Review its time/storage budget before an explicit run.
Other R values need separate configs; d/p remain the only sweep axes.
Preparation still requires fixed_shots, z/x/z, prefix_frame_only and the
native hex_legacy profile. `save_all_syndromes: true` is rejected for this
protocol; select bounded retention instead. Existing memory/Knill configs,
numerical builders and logical-error table meanings remain unchanged.

CLI thread setup precedes native imports. OMP_NUM_THREADS,
OPENBLAS_NUM_THREADS and MKL_NUM_THREADS must agree with
native_threads_per_worker (default one). The existing wrapper uses the saved
YAML worker count; no cluster allocation inference is added here.

## Setup, cached models and sampling

`runner.prepare` delegates preparation setup to `simulation/preparation.py`.
It saves the exact input YAML, resolved parameters/grid, environment/source/
dependency provenance, actual bench Git state, production/nominal/completed
circuits and strict DEMs, record/detector/evaluation maps, cost policies and
decoder descriptors. The maps include the actual after-final-Z output cut,
physical/evaluation/offline resource counts and physical versus nominal p.

`adapters.decoders.describe` delegates this protocol to static preparation
model compilation. It builds/certifies no live Matching objects. Each
descriptor saves X and Z original-column artifacts, active/mechanism ID maps,
scale/rounding, complete output/tie/frame identity and model hashes.
The X artifact preserves individual completed boundary supports. The Z
artifact directly reconstructs its ordinary known-zero prefix model. Neither
worker load nor decode reparses a Stim DEM. `construct` verifies the loaded
models and creates the three compact native topologies once (or their optional
full-witness label graphs). Empty/noiseless models can have zero live graphs.

`worker.model` uses its existing bounded OrderedDict cache for preparation
runtime bundles: production circuit, minimal `PreparationSampleMap`, all
decoder models/graphs and static label maps. The key includes run/model and
decoder identity. Hits enforce the current cache bound; eviction releases
the bundle, and rebuilding preserves the same inference. Graph-construction
counts, setup wall time, visible sparse-buffer bytes and RSS deltas are
recorded for cold entries. No sampler RNG state is cached between chunks.

One task is `(sampling_case_id, replicate, chunk_id, shot_start, shots)`.
Its worker compiles a production detector sampler with that chunk's seed,
then makes one sample call for exactly the assigned count, returning online
detectors and evaluation-only observable labels. The shared splitter copies
the two bool online blocks into observation buffers separate from truth.
Every decoder sees only those two online arrays. X baseline/complement and
Z-prefix solves use that same physical batch. The evaluator alone compares
predictions to truth. A changed oracle cannot change either decoder output.

Compact shot columns are built using Arrow arrays and validity masks, without
per-shot Python objects. Ordinary inference is batch/vectorized; the only
intentional single-shot decode loop is the bounded latency replay sample.
Retained-example serialization loops over bounded selected rows only.
Memory scales with chunk size, configured decoder count and cache bound,
not all shots in a point/run. Optional full-witness mode computes witnesses
for that chunk; only bounded retained chains are persisted.

## Seeds, sample hashes and publication

The inherited seed derivation is unchanged: SHA256 of canonical
`[1, master_seed, sampling_case_id, replicate, chunk_id, "physical"]`, first
eight bytes interpreted little-endian. Physical identity includes distance,
explicit R, bases, native noise, schedule, cut/probe and sampler semantics.
Decoder scale/mode/nominal p, workers, retention and execution order do not
enter that identity. Uniform retention and latency selections reuse their
separate deterministic streams over global replicate/shot indices.

Reproducibility requires the saved circuit, code/dependency/environment,
seed, partition and sampling call shape. Stim is not assumed to replay the
same records across arbitrary versions, hardware or call subdivisions.
Changing chunk_size/config/source/model/map/graph rejects resume. Workers
may change because they do not change chunk seeds or sampling call shapes.

`sample_hash_version=preparation_bool_rows_little_endian_v1` hashes the ordered
online_X, online_Z, truth_tau_X, truth_tau_Z, truth_logical_Z matrices. A
length-prefixed canonical JSON descriptor includes names, bool dtype, shapes,
little-endian bit order and zero row-padding convention. Each matrix then
contributes its byte length and row-wise packed bytes. Empty R1 X blocks are
unambiguous because their shape remains in the descriptor. This hash is
independent of decoder results and is saved in batches/checkpoints/retention.

The existing parent schedules a bounded number of spawned tasks and commits
in case/replicate/chunk order. Workers send only small staged-file manifests;
sample arrays never cross process queues. The parent checks schemas, hashes,
row counts, event totals and retained identities, applies the global failure
quota, then renames all parts. Each file closes/fsyncs before promotion;
preparation data directories fsync before the checkpoint. The checkpoint is
the publication marker; multiple table renames are **not jointly atomic**.

Resume checks the saved config/grid/environment plus the complete setup-file
registry and every published table's hash/schema/count/identity **before**
deleting staging/orphan files. Missing published checkpoints or gaps in a
group's committed chunk prefix reject. A checkpoint ahead of the manifest
after a crash is recovered as authoritative. Unmarked partial promotions and
staged outputs are discarded and retried from the original chunk seed and
shot zero of that chunk; completed checkpoints/data remain intact.

A failed worker writes explicit assigned-but-unobserved rows and failure
history, never a complete checkpoint. Retry replaces its unfinished parts.
Failure history remains separate from observed scientific denominators.
Runtime structural/numerical inference errors fail the chunk rather than
silently clipping costs, swapping decoders or discarding individual shots.
Mathematically infeasible shots instead retain their masks/status and valid
baseline statistics.

## Result schema and bounded examples

New preparation tables have `preparation_result_version=1` Arrow metadata
in addition to schema-v1 storage metadata. All result fields are nullable;
unavailable scalar errors/costs/gaps use null with explicit masks/status.
Existing `shots.logical_failure`, `decoder_batches.errors` and v2 files are
not reused for sign inference.

| Table | Saved meaning |
|---|---|
| `preparation_cases` | Physical d/R/p and nominal p, decoder, circuit/model hashes, full case/map/policy metadata |
| `batches` | Existing protocol-neutral chunk identity, seed, assigned/observed count, sampling/splitting time and canonical sample hash |
| `preparation_chunks` | Assigned/observed counts, X baseline/complement/Z validity, sign/code/logical counters, per-check/joint summaries, gap-bin counters, phase timings |
| `preparation_shots` | Optional compact per-shot validity, nullable sign/code/logical flags/counts, original integer costs, score gap and status |
| `preparation_retained` | Bounded production online/truth rows, predictions/weights/status, model IDs and optional same-mode diagnostic chains |
| `preparation_calls` | Separate primary phase, warmup and bounded single-shot replay wall times |
| `preparation_stopping` | Assigned fixed-shot group's actual published count, state and elapsed time |

Gap bins are fixed [0,1), [1,2), [2,4), [4,8), [8,16), [16,32),
[32,64), [64,+infinity); index -1 is unavailable. No binning sweep axis is
introduced. Each bin includes attempt count, all metric validity denominators,
sign/code/logical errors and eight-bin joint counts. The joint index is
`4*E_sX+2*E_sZ+E_LZ`; it separates X-sign-correct conditions from the stronger
code-correct condition. Aggregate-only and compact-shot modes have identical
counter and bin semantics. Exact arbitrary threshold curves require the
optional compact table; later saved analysis must not invent them from bins.

Uniform examples are fixed without replacement across all replicates. Failure
candidates include code/readout misses and unavailable high-level inference;
workers keep only their first configured local candidates, and the ordered
parent enforces the global per-case cap. Uniform and failure reasons can
overlap. Completion order cannot choose which examples survive.

Retained rows store the original production sample plus decoder predictions,
validity, gap/cost/status and frozen-bit/P/F diagnostics. Full-mode chains
are expanded through each model's active-column map before saving; the
model artifacts preserve original mechanism IDs. They are estimates, never
called actual sampled faults. A false debug_matches_compact flag is kept and
never attached to a separate compact correction. Diagnostic replay uses
saved rows directly or regenerates the original entire chunk with the same
call shape and checks its sample hash. Singleton resampling is not replay.

## Timing boundaries and small measured smoke

Setup includes circuit/DEM/model validation/hash work, artifact loading and
cached graph construction. Worker timings separate sampler compilation,
sampling, splitting, X baseline, X complement, Z decode, adapter overhead,
evaluation/bin aggregation, warmup, latency replay and staging I/O. Parent
commit I/O is checkpointed separately. Baseline time includes input checking/
baseline bookkeeping; complement time includes fixed RHS/parity/cost work.
Warmup and replay do not enter primary decode throughput. Model caching and
sampler compilation have deliberately different lifetimes.
The phase timers are not an exhaustive worker CPU accounting: canonical
sample hashing, Arrow column assembly and retained-row encoding are worker
bookkeeping visible in execution wall time, but have no separate timer.
Task elapsed time also includes queue/ordered-wait overhead. Consequently
the phase sums must not be presented as end-to-end throughput.

A real shell/installed-CLI smoke used d3/R2/p=.003, seed617, seven shots,
chunk_size=3 (3/3/1), two workers, native threads one, compact output,
warmup one per chunk and three in-batch latency calls. Run, completed
resume with one worker and saved-only analyze all passed. Temporary outputs
were removed; `/tmp/knill_prep_04_smoke_metrics.json` records the measurements.

| Measurement | Observed value |
|---|---:|
| Full shell invocation, including setup/Conda/imports | 6.510 s |
| Execution wall, including pool/import/I/O/warmup/replay | 2.740 s |
| Physical shots / execution second | 2.555 |
| Batch X baseline amortized time | 73,508 ns/shot |
| Batch X complement amortized time | 186,298 ns/shot |
| Sum of primary X/X-complement/Z decode times | 2.064 ms |
| Primary decode-only shots/second | 3,392 |
| Three single-call latency p50 / p95 / p99 | 1.140 / 1.637 / 1.682 ms |
| Cold worker artifact+decoder setup sum | 61.098 ms |
| Three sampler compile / sample time sums | .123 / .687 ms |
| Maximum worker process peak RSS | 358,871,040 bytes |
| Selected Python model sparse buffers | 5,264 bytes |
| Maximum detector+observable sample arrays | 63 bytes |
| Published table bytes per physical shot | 14,681 bytes |

These are tiny-run observations under concurrent local load, not throughput
or scaling benchmarks. Pool/import and Parquet/JSON overhead dominate this
size; the output ratio includes fixed per-part headers. Sparse-buffer counts
exclude opaque native graph allocations, and sample-array bytes exclude
split/prediction/Arrow buffers; RSS includes interpreter/imports and native
memory. Three latency calls cannot characterize tail latency. Seven zero
observed errors are not evidence for a rare-error rate or threshold.

## Validation boundary

Tests use only d3 and <=7-shot new physical fixtures. They compare one/two
workers, interrupted resume and repeated completed resume, aggregate-only
versus compact counts/bins, same-mode retained replay, source/model/map/
partition/table tampering, worker and parent-promotion failure recovery,
truth isolation, cache eviction, graph reuse, p0/null/R1 behavior and two
decoders sharing one physical sample. Legacy memory/Knill execution tests
are retained. The larger template is parsed with circuit construction
forbidden. Exact commands, fixture correction and full gates are in
[TEST.md](../TEST.md).

Prompt 05 adds empirical gap/error curves, interval/plot/report validation
and broader scientific acceptance; see [the report guide](preparation_reports.md). New physical/protocol claims
need their own evidence; no FT, posterior, threshold or rare-event agreement
is inferred from these software/structural tests.
