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
