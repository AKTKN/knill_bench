# DEM conversion and physical fault audits (schema v1)

## Fixed-R completed DEM model (prompts 00/02)

`temporal_dem.completed_dem_to_temporal_model(dem, detector_roles=...,
num_observables=..., weight_scale=1000)` requires an explicitly completed
selected-CSS model. It retains original DEM term columns and full individual
supports, rejects separators/hyperedges/missing roles, freezes every spatial
open column and records source DEM SHA256, strictness and ties-to-even
rounding. `TemporalDemModel` is also the high-level `BoundaryConstraintModel`;
there is no duplicate container. Positive-probability variables enter
`matching_kwargs()`; p=0 terms stay in full provenance/labels. `expand_errors`
restores solver witnesses to that full order.

Prompt 02 adds optional ordered `feature_observable_ids`/`feature_ids` and
finite JSON `model_provenance`, full_detector_support, original float costs,
unidentifiable evaluation-only columns and complete quantization policy
metadata. `to_artifact`/`from_artifact` and `temporal_artifact` exclusive
fsynced JSON I/O preserve original terms, labels, inactive columns and their
canonical payload hash. Loading validates schema/ranges/derived costs and
does not parse Stim DEM text.

`preparation_model.compile_preparation_boundary_model(compiled, weight_scale)`
certifies actual-pin nominal production/completed X-online/all-evaluation
outputs and supplies explicit map/source/Hex provenance. It uses
`temporal_validation`'s validation-only independent XOR parity aggregation,
never an aggregated inference graph. Missing/changed map/label/probability
models fail. See [model API and artifact policy](../../../docs/temporal_boundary_model.md).

`temporal_matching.TemporalMatching(**model.matching_kwargs())` caches two
static graphs. `decode_batch(unpacked_binary_syndromes, return_errors=False)`
returns baseline/complement features/costs, gaps and status. Common integral
costs preserve fixed-zero/one and temporal/cost offsets; private subdivision
nodes preserve parallel mechanisms. Unavailable gaps are NaN, not confidence.
Optional debug uses same-solve full witnesses and reports compact tie
disagreement; solver-input and original DEM column orders remain distinct.

These kernels have synthetic exhaustive-optimum tests. Current-pin native
model certification, R2 readout/data/two-qubit Pauli responses and strict
artifact round-trips are now tested. Prompt 03 adds a high-level X/Z adapter;
prompt 04 now supplies ordered workers/persistence. See
[proofs, units, assumptions and scientific gates](../../../docs/temporal_preparation_theory.md).

`preparation_model.compile_preparation_prefix_model` selects the production
Z rows, verifies their known initial-zero/SE record expressions, and produces
`preparation_prefix.PrefixDemModel` with tau_Z/logical_Z response maps. It
retains original production DEM columns, preserves parallel/invisible terms,
rejects separators and selected-sector hyperedges, quantizes once and removes
p0 only from solver inputs. It is one ordinary prefix model, with no inferred
temporal boundaries or competing H/P/F/S type. The shared `_StaticMatcher`
provides exact unmerged graph handling; no new matching optimizer is written.
`TemporalMatchingResult` now also exposes the selected baseline's frozen bits
and P/F labels, masked by baseline validity. `prepare_full_witness` prewarms
the existing optional debug graphs. Objectives/RHS/costs/tie handling are
unchanged. See [adapter and metrics](../../../docs/preparation_decoder.md).
Prompt 04 adds strict Z-prefix to_artifact/from_artifact reconstruction from
original supports/probabilities/row maps, without Stim parsing. The adapter's
static descriptor and live constructor share one definition/hash function.
The unchanged core solves now expose separate baseline/complement wall
timers, including their respective bookkeeping. Worker phase/replay times
are separate in [the execution guide](../../../docs/preparation_execution.md).

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
