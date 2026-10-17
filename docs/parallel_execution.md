# V2 adaptive parallel execution and buffered output

Both schema-v2 experiments use time-adaptive chunks by default. Schema-v1
execution and the Hex H5 sources are unchanged. The physical circuits, native
matching decisions, factory oracle isolation and full fixed-T trajectories
are unchanged; theta never enters scheduling or workers.

```yaml
shots: 100000
workers: 8
batch_size: auto          # Also the default when omitted.
target_chunk_seconds: 1.0 # Optional positive finite seconds, default 1.
buffer_shot: 10000        # Optional positive integer, default 10000 in auto mode.
```

Workers are processes on **one node**, using multiprocessing spawn. A pool
persists over the run. All workers can work on the same d/p point; points are
completed in configuration order. Each process holds at most one compiled
physical model/decoder, replacing it when the point changes. Factory local
DEM caches retain their existing bounded lifetime. Circuits, matching graphs,
frame maps and converters are built once per point per participating worker.
Native objects and raw measurement arrays never cross process boundaries.

The first chunks are one-shot calibration probes whose results are retained.
The coordinator estimates seconds/shot with an exponential moving average
(alpha 0.5) and chooses approximately target_chunk_seconds / seconds_per_shot
shots for the next assignment. Growth is limited to twice the preceding
observed chunk count. The remaining tail is shared across available worker
slots. Setup, queue/IPC and output time are excluded from throughput feedback;
sampling, fresh seeded sampler compilation and decoding are included. The
target is approximate, not a deadline or equal-duration guarantee. Cold setup,
small shot budgets, memory caps, variable decoder work and the final tail can
dominate elapsed time. No performance speedup claim is made from unit tests.

Each chunk is capped by buffer_shot, 65,536 shots, and an automatic raw-record/
decoder working-array estimate (64 MiB / [8 * (measurement_records +
4 * simulator_qubits + 8 * T)]). The one-shot probes discover the actual circuit
width before larger chunks are scheduled. The cap is a heuristic, not a total
RSS limit: native model/graph memory and interpreter processes are additional.
A large worker count duplicates those model costs.

The parent receives only bool labels and, for factory, finite nonnegative
float64 gaps. It validates task offsets/counts/shapes and writes contiguous
uint64 IDs. At most workers chunks are in flight **or** awaiting ordered
output combined; a delayed earlier chunk cannot create an unbounded reorder
queue. The writer copies results into one buffer of at most buffer_shot rows
per point. Every full buffer is appended as one Parquet row group to each
aligned table; only the final group can be short. This controls working memory
and write granularity, not the number of saved trajectories or total data size.
The parent retains no full-shot raw history.

There is still one Parquet file per point/table, not one file per buffer.
Appends go to hidden incomplete files; these are not public readable
checkpoints. Both footers close/fsync/validate before public renames and the
metadata completion marker. A failure removes the whole incomplete pair.
Resume preserves complete points, discards unfinished output, and restarts
that point at zero. It does not resume from the last buffer. Existing schema,
filenames, analysis and pair-publication semantics are preserved.

## Seeds and repeatability

Each assignment uses chunk_seed(master_seed, point, chunk_id,
stream="time_adaptive_chunks_v1"). Seeds depend on physical point/chunk IDs,
not PID, worker count, prior, theta or requested shots. A **fresh Stim sampler**
uses that seed for each assigned chunk; the expensive physical model and decoder
stay cached. No sampler RNG state leaks across points or chunks. Replaying an
identical task (point/start/count/seed), even on a different cached worker,
reproduces its records with the same Stim/platform.

Measured times change chunk sizes, so repeated auto runs, different workers,
and different inference policies can have different chunk partitions and
physical records despite identical master seeds. Automatic runs therefore do
not guarantee bitwise replay or paired raw trajectories across prior policies.
For a controlled common-record comparison or exact replay, use integer
batch_size with identical settings in both runs. Point metadata records the
actual sampling policy, chunk seed stream, ordered partition SHA256, number
and range of chunks/durations, aggregate sampling/decode and setup seconds,
number of workers used, target and cap. This compact summary is not a full
partition archive and cannot reconstruct a timing-dependent partition by itself.
The point seed remains a recorded physical identity; auto consumes chunk seeds.

```yaml
batch_size: 128 # Explicit integer selects the historical whole-point scheduler.
buffer_shot: 10000 # Optional independent output grouping in fixed mode too.
```

In fixed mode, one worker owns each whole point and advances the existing
point-seeded sampler with the exact fixed batch partition. Without buffer_shot,
its row-group behavior and canonical config hash remain unchanged. With the
buffer, only output grouping changes. target_chunk_seconds is accepted only
in auto mode. No extra sweep axes are added. New source revisions still require
fresh runs under the strict resume provenance rules.

## PBS / Anaconda

See [cluster setup](cluster_setup.md) and
[scripts/cluster_run_simualtion.sh](../scripts/cluster_run_simualtion.sh).
The script uses the allocated CPUs (or WORKERS up to that allocation) through
`knill-bench-v2 run CONFIG --workers N`. validate-config and prepare also accept
this override. The original file is never edited. With an override, the exact
**effective** YAML is saved in the run, prefixed by the original input SHA256;
metadata/config hashes describe the effective settings. With no override,
original input bytes, including comments, are preserved as before. Resume uses
the saved workers/config and checks the allocation can accommodate them.

## Reference and validation scope

The scheduling design follows the measured-throughput and separate-output-
buffer pattern in [color_code_softoutput scheduler](https://github.com/AKTKN/color_code_softoutput/blob/1e88fc4633beb8e2741e8a16cd3554ed5a106732/src/color_code_softoutput/simulation/scheduler.py)
and [its worker](https://github.com/AKTKN/color_code_softoutput/blob/1e88fc4633beb8e2741e8a16cd3554ed5a106732/src/color_code_softoutput/simulation/worker.py).
The installed sinter 1.16.0 collection and ramp-throttling code was also read;
sinter itself is not invoked because its aggregate collection interface does
not supply these per-shot paired factory tables. There is no new dependency.
Synthetic tests exercise timing feedback, bounds, out-of-order delivery and
failure handling. New physical fixtures use d3, at most seven shots, with
T=2 factory / T=8 full Knill. Existing d3/5 and fixed serial/spawn tests remain.
Production sweeps and cluster-host performance were not run.

Saved runs whose old YAML omitted batch_size retain their historical default
32 through load_saved_config, using the saved canonical metadata to identify
that default. They remain readable by saved-only analysis; new omitted-field
inputs select auto. Source/environment resume compatibility remains strict.

Ordinary `kind: se_memory` uses the same execution paths. HexMemory caches its
circuit/converter/unconstrained matching and optional opposite-class graph per
point/worker; only output labels/gaps cross processes. get_logicalgap is absent
from physical identity/seeds, although extra work can change auto partitions.
Fixed mode preserves exact common records and first labels with gap on/off.
One optional gap_t001 covers the entire trajectory. See [memory](se_memory.md).
