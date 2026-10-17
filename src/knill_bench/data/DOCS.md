# Versioned storage and provenance

`storage.py` and `provenance.py` retain all schema-v1 tables, archived
provenance, incremental worker parts/checkpoints and compatibility behavior.
They are unchanged in B0. Their specification is
[data_schema.md](../../../docs/data_schema.md).

`storage_v2.py` is independent: `schemas(point)`, `PointWriter`, `PointResult`
and parent-run helpers supply one `logical_error` table per d/p and one
aligned `logical_gaps` table for factory points. IDs are non-null uint64,
labels non-null bool, gaps nullable float64 `(shots,T)` with `gap_t001..` names.
Each writer validates bounded batches and uses one native ParquetWriter per
table for the entire point. Both footers close/fsync/validate before public
renames; metadata is the final pair-publication marker. No all-shot collection
or v1 table/transaction database is used.

Exact filenames retain literal `r_+`, use round-trippable p, and contain all
requested point keys. Incomplete appends/promotions abort both files. Hard
crashes are handled by `RunStore.resume`, restarting an unfinished point from
zero and preserving completed points. Locks enforce one writer/parent;
metadata updates reject non-owner PIDs. Contracts, nullable-gap semantics,
seed/policy identity, filesystem limits and public APIs are in
[the B0 guide](../../../docs/auxiliary_v2.md). B0 performs no science sampling.

## B2 use of paired storage

The factory runner now streams actual Hex final bool labels and per-stage
float64 gaps through these unchanged B0 writers. Both tables have identical
contiguous IDs and one writer per point/table across all chunks. B2 requires
all gaps to be finite/nonnegative/present, despite the nullable infrastructure
schema. Both files are removed on a chunk failure; the parent completion
marker and whole-point resume rules remain unchanged. No B3 analysis table
is introduced. See [the factory guide](../../../docs/logical_zero_factory.md).

B3 now validates/streams these unchanged paired schemas without simulation,
including differently partitioned row groups, non-null finite scores, exact
ID order and counts. Optional analysis reports are separate requested artifacts;
they do not alter point files or metadata. See
[B3](../../../docs/factory_analysis.md) for the conditional estimand and cost model.

## Installed distributions

`provenance.environment` retains v1 fields/archives for checkout execution and
now also records verified cluster-wheel source metadata when no Git checkout
is present. Patch capture remains checkout-only. B0/v1 table schemas and all
physical data semantics are unchanged. Shared source validation hashes Python/
matrix resources and rejects changed wheel content. See
[cluster setup](../../../docs/cluster_setup.md) for build/install/validation.

## V2 run-directory names

RunStore reserves `YYYYMMDDHHMMSS_<config_hash8>_<name>` in Asia/Tokyo time.
Same-name collisions advance one second without data reuse; full hashes and
actual ISO UTC timestamps remain in metadata. This changes only new directory
names, not table names/schemas or legacy run loading. `run` starts fresh while
`analyze-factory` reads only the specified saved run and its saved config.

## Bounded result coalescing

`PointBuffer(writer, buffer_shot)` validates contiguous uint64 IDs/bool labels
and float64 gaps, copies decoded results into fixed-size buffers, and writes
exactly buffer_shot rows per group except the final short group. commit flushes
the tail then delegates to PointWriter. Auto mode owns both in the parent;
fixed mode can use them inside its point worker. No raw histories are buffered.
PointWriter remains the single owner of paired close/fsync/check/rename/abort.
See [parallel execution](../../../docs/parallel_execution.md).

Ordinary memory uses these unchanged schemas/writers: optional logical_gaps
has exactly gap_t001 for the full trajectory. Its point.tables flag determines
whether a second writer exists. Both auto/fixed modes reject unavailable or
invalid requested memory scores; paired publication and buffer/restart rules
are unchanged. Filenames retain literal r_+ and add resolved rounds; see
[memory](../../../docs/se_memory.md).




BENCH-N2 custom factory noise uses exactly these paired schemas and bounded
writers. noisemodel=custom is the short filename label; full physical noise
parameters remain in config/point identity and compact metadata. Parent
publication and completed resume additionally reject inconsistent custom noise
provenance/scope. No table column, mandatory artifact, row-ID, buffering or
pair-publication boundary changes. See
[custom noise](../../../docs/factory_custom_noise.md).
