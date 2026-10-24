# Completed DEM boundary model (prompt 02)

The fixed-R preparation setup now certifies and serializes its X-sector
boundary model using the supplied `TemporalDemModel` and matching core.
`BoundaryConstraintModel` remains an alias of that same type. This step
adds no simulation table or runner. The subsequent
[prompt-03 X/Z decoder and metrics](preparation_decoder.md) now consume these
static models; prompt 04 now supplies
[ordered workers and persistence](preparation_execution.md).

See [circuit/record contracts](surface_preparation.md) and
[theory and assumptions](temporal_preparation_theory.md). Hex remains
read-only at HEX-K1. All circuit comparisons use the current imported pin.

## Setup and persistence API

```python
from knill_bench.circuits.preparation import build_preparation
from knill_bench.decoding.preparation_model import compile_preparation_boundary_model
from knill_bench.decoding.temporal_artifact import write_temporal_model, read_temporal_model
from knill_bench.decoding.temporal_matching import TemporalMatching

compiled = build_preparation(dict(
    protocol="surface_prep_fixed", distance=3, rounds=2, p=.003,
))
model = compile_preparation_boundary_model(compiled, weight_scale=1000)
digest = write_temporal_model("boundary_X.json", model)
restored = read_temporal_model("boundary_X.json", expected_sha256=digest)
core = TemporalMatching(**restored.matching_kwargs())
```

This explicitly writes one setup artifact in the chosen working directory;
it never starts a run or samples any circuit. The file is exclusively
created and fsynced. Prompt 04's runner owns its destination, saved hash
and publication/resume checks. Loading rebuilds sparse arrays directly from
validated columns/roles; it does not parse a DEM or compile a circuit.
Matching graphs are constructed once by the adapter, outside decode calls.

`compile_preparation_boundary_model` receives only the builder's static setup.
It checks complete detector/evaluation namespaces, ordered online identities
and evaluation metric/check identities, then compares the nominal
production-shaped and completed models. It retains all tau_X, tau_Z and
logical_Z features, in the builder's order. The adapter selects its X prediction
rows. This X boundary model does not implement Z-prefix inference; prompt 03's
separate `PrefixDemModel` does so without a P/F completion.

When physical p and decoding_p differ, both sides of certification use
decoding_p. Physical sampling remains on the original production circuit.
Provenance records actual builder/source/resource/model hashes, the Hex
revision/dirty state, explicit row/evaluation maps, boundary compiler/parser/
comparison source hashes and the marginal comparison certificate. It has no
sampled boundary outcomes or actual fault locations.

## Low-level completed-model API

`completed_dem_to_temporal_model(dem, detector_roles=..., num_observables=...,
weight_scale=1000, feature_observable_ids=None, feature_ids=None,
model_provenance=None)` retains one column per flattened DEM error term.
The role sequence is indexed by absolute detector ID; an integer-key mapping
must cover every detector ID exactly. Missing/invalid roles are rejected.
Roles never come from coordinates, gate names or guesses about readout faults.
An ordinary open-window DEM lacks sufficient boundary information. The
low-level parser cannot prove a caller's completion assumptions; its default
provenance explicitly says `completion_certified: false`.

DEM L targets provide the static evaluation-response map. Optional unique
`feature_observable_ids` selects/reorders rows, and `feature_ids` names them;
the default selects every declared observable in ascending ID order. Original
observable signatures remain in `terms`, even for unselected feature rows.
Feature names and observable IDs are distinct from mechanism IDs.

| Field | Meaning in original DEM column order |
|---|---|
| `h_completed`, `full_detector_support`, `terms` | Individual completed endpoints and original flattened term/instruction indices |
| `h_online`, `past`, `future` | Online rows and XOR parities of explicitly typed past/future rows |
| `frozen_columns` | Every individual full-degree-one spatial open port, including future-only ports |
| `feature_map`, `feature_ids`, `feature_observable_ids` | Ordered evaluation response rows and their explicit IDs |
| `probabilities`, `float_weights`, `weights` | Original independent probabilities, log odds and common integer costs |
| `active_columns`, `inactive_columns` | Ordered p>0 solver projection and retained p=0 columns |
| `zero_online_columns`, `invisible_columns`, `unidentifiable_columns` | No online response; no completed response; no completed response with retained evaluation labels |

The full support is checked **before** temporal XOR contraction. Separators
and full support above two are rejected. Unfrozen nonzero augmented columns
must have degree two; degree one means missing boundary scope. Two endpoints
within the same past/future slice can contract to zero; their labels and
probabilities remain. Duplicates and parallel mechanisms remain separate;
the existing matching core uses private subdivision nodes to preserve them.
`provenance_kind=completed_dem_term` never claims a unique physical gate origin.

All p must be finite in [0,.5). Negative/NaN/out-of-range values and p>=.5
fail; no epsilon or correlated-component splitting is used. The builder
already enforces strict Stim extraction with `decompose_errors=False`,
`approximate_disjoint_errors=False`, `allow_gauge_detectors=False` and signed
detector/evaluation flows; unsupported noise or nondeterminism raises a
concrete capability error.

## Weights and artifacts

For p>0, float cost is `log1p(-p)-log(p)`. One model-wide scale gives
`numpy.rint(scale*cost)` (ties to even), shared by both solves. Quantized
edge costs must lie in [0,2^24-1], with total at most 2^53-1. Active costs
that round to zero stay zero without clipping; visible ties remain solver
ties and invisible baseline variables are chosen zero. An active zero-cost
P–F path can therefore give gap zero. These are representative minimum
costs, not posterior odds.

p=0 float costs are +infinity; stored integer zero is only an inactive
placeholder. JSON metadata uses null for this explicitly documented infinity.
`matching_kwargs()` excludes these columns and remaps frozen indices.
`expand_errors()` restores witnesses to the full original column order with
zeros in inactive positions. Do not pass full placeholder weights directly
to a solver.

`to_artifact()` / `TemporalDemModel.from_artifact()` use version 1 JSON with
a canonical payload SHA256. The payload stores roles, original term supports,
probabilities, integer weights, feature order, active IDs, original float
costs, accepted bounds, rounding/inactive/zero policies and provenance.
Loading verifies ranges, column ordering, schema and all derived metadata/
costs, including after a file is rehashed. The owning-run hash is an additional
identity check. JSON duplicate keys are rejected. A checksum detects changes;
it is not authentication or a replacement for the builder's scientific proof.
Setup owns model arrays and must not mutate them after construction.

The artifact identifies the boundary model and its cost policy. Prompt 03
additionally identifies the selected compact/full-witness and tie policy
in its adapter definition; a static model hash alone does not select that mode.

## Equivalence and independent checks

`temporal_validation.marginal_parity_probabilities` and
`compare_marginal_models` are validation-only APIs. They project explicit
ordered online/evaluation IDs and aggregate identical independent parity
signatures with `(1-product(1-2*p))/2`, evaluated stably using log1p/expm1
and compensated summation. They drop only empty-output or p=0 events from
this **comparison**. They never replace or merge the inference columns.

Certification compares the same X online outputs and **all** evaluation
labels, marginalizing hidden past/future and unselected Z detectors. The
known initial-Z anchor remains in its separate production-shaped model;
there is no invented unknown-past Z boundary. Signature supports must match
and probabilities must agree within atol=1e-14, rtol=1e-12 (recorded with
the actual maximum difference). This is algebraic equality up to binary64
arithmetic, not a statistical agreement claim or a new instrument proof.
Removing evaluation declarations loses invisible endpoint effects and is
explicitly rejected by the comparison tests.

Tests use d3/5, R=1/2/3/5, noiseless and .003 models, including a distinct
physical/nominal p fixture. R2 single readout/data faults independently
predict past/online/future/tau signatures, including a future-only frozen
port and two-future contraction to zero with labels retained. A single
correlated two-qubit Pauli event after a native CNOT checks readout/data
cancellation without splitting. Coordinate changes leave classifications
unchanged. Synthetic tests cover hand-derived XOR probabilities, fixed-one
and fixed-zero costs, inactive/active-zero terms, original-column/feature
round-trips and invalid/tampered artifacts. No production sweep or new large
physical sampling is used. Exact gates and corrections are in [TEST.md](../TEST.md).
