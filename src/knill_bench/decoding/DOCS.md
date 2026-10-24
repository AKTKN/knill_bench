# DEM conversion and physical fault audits (schema v1)

## Fixed-R temporal decoder seed (prompt 00)

`temporal_dem.completed_dem_to_temporal_model(dem, detector_roles=...,
num_observables=..., weight_scale=1000)` requires an explicitly completed
selected-CSS model. It retains original DEM term columns and full individual
supports, rejects separators/hyperedges/missing roles, freezes every spatial
open column and records source DEM SHA256, strictness and ties-to-even
rounding. `TemporalDemModel` is also the high-level `BoundaryConstraintModel`;
there is no duplicate container. Positive-probability variables enter
`matching_kwargs()`; p=0 terms stay in full provenance/labels. `expand_errors`
restores solver witnesses to that full order.

`temporal_matching.TemporalMatching(**model.matching_kwargs())` caches two
static graphs. `decode_batch(unpacked_binary_syndromes, return_errors=False)`
returns baseline/complement features/costs, gaps and status. Common integral
costs preserve fixed-zero/one and temporal/cost offsets; private subdivision
nodes preserve parallel mechanisms. Unavailable gaps are NaN, not confidence.
Optional debug uses same-solve full witnesses and reports compact tie
disagreement; solver-input and original DEM column orders remain distinct.

These kernels have synthetic exhaustive-optimum tests; there is no fixed-R
physical circuit/adapter/worker yet. See
[proofs, units, assumptions and scientific gates](../../../docs/temporal_preparation_theory.md).

## Existing conversion and audits

`dem.py` converts Stim events into complete detector/logical signatures,
XOR-merges identical supports, preserves logical-only effects and handles
fixed probabilities. `audit.py` inserts bounded controlled physical faults
and audits saved v1 circuits/models. No decoding Python is changed in B0.
See [design](../../../docs/design.md) and [validation](../../../docs/validation.md).

V2 decoding remains a later-runner concern using Hex's validated native APIs.
`create_codecapacity_dem=True` names a fixed-reference independent-superposition
approximation with real context/nonlinear limits, not exact conditional MAP.
Unsupported hyperedges/logical mechanisms must raise; never drop them or use
oracle truth to improve apparent confidence. B0's provenance interface checks
construct no decoder/graph/sampler. See [v2](../../../docs/auxiliary_v2.md).

## Observable-constrained spacetime MWPM

`observable_gap.ObservableMWPM(H,L,weights,get_logicalgap=False)` validates a
complete independent-event graphlike model with exactly one observable row.
It caches ordinary MWPM; when enabled it also caches a two-constrained-boundary
lift derived from L's internal XOR potential. decode_batch returns the first
prediction/correction/cost and optional opposite-class correction/cost/gap.
It verifies both syndrome constraints, opposite observable parity, native
costs and nonnegative cost difference, preserving the first prediction.
Connected spacetime lifts need not be planar. It never appends a degree-three
row, rebuilds graphs per shot, splits/drop events or accepts truth labels.
Unsupported degrees, logical-only events, inconsistent potentials, nonpositive
gap weights and unresolved cost ordering raise. n=0 supports zero-noise plain
memory. This minimum-chain cost difference is not posterior log odds.
See [algebra and numerical limits](../../../docs/se_memory.md).
