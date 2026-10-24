# Fixed-R surface preparation: theory and implementation contract

Contract date: 2026-10-24, `surface_prep_fixed_v1`. This is prompt 00: theory,
shared types and the reviewed decoder seed. Circuit/config integration,
the X/Z adapter, metrics, workers and reports are subsequent steps, not
implemented capabilities of this change. No production experiment is run.

## Checkout and scope

The user-requested checkpoint is bench `2e618b9`, pushed on `auxiliary-system`.
Implementation starts from it on child branch `surface-prep-fixed`; this work
remains a local diff. Hex is clean at the existing HEX-K1 pin
`8fa2200315cc4feaccf341a461f91739233de08a`, LOM at `b55a7a6`, surface-sim at
`493f800`. No dependency source or pin is changed. The handoff's Hex `5de58f2`
and bench `b3cc72a` are audit references, not the actual execution environment.
Its physical validation numbers are not evidence for this pinned checkout.
Conda `knill_system` supplies Python 3.12.15, Stim 1.16.0, PyMatching 2.4.0,
NumPy 2.5.3 and SciPy 1.18.1.

Adopt exactly one patch, noisy transversal physical-zero initialization,
exactly **R full X-then-Z SE rounds**, then the output cut. There is no
teleportation, retry or stopping decision. Defaults are `prep_basis=z`,
`sign_sector=x`, `readout_basis=z`, `logical_evaluation=prefix_frame_only`,
`adaptive=false`. R is an explicit positive signed-int64 integer, fixed within
a run; d/p are the only intended sweep axes. Different R values use separate
configs. Neither `cycles`, preparation d rounds, nor a coefficient of d means R.
The first implementation uses native `hex_legacy` circuit noise; another
profile requires its own validated builder/scope and cannot share its label.
Physical p and positive nominal decoder probabilities must be distinct in
metadata when testing noiseless samples with a noisy inference model.

These choices retain a deterministic logical-Z target and an unknown initial
X-sign sector. They also let fixed chunk identities reproduce samples. Physical
adaptive stopping and timing-dependent chunk resizing are both excluded here.
Other bases, terminal recovery, gauge circuits and random logical-X comparison
raise `PreparationCapabilityError` until separately specified and validated.

## State, records, frame and truth

The output is **after the last Z extraction**, later than the last X readout.
An endpoint data fault during that Z extraction can change the X sign without
changing an online X detector. Keep it in output-state truth.

For check j in either sector a, let m_R,a be its last noisy record. An ideal
X-stabilizer probe after the cut gives s_out,X. Ideal destructive data-Z records
r_Z give s_out,Z = H_Z r_Z and ell_Z = L_Z r_Z, using Hex matrix row order.
Define, over GF(2),

```text
tau_X = m_R,X XOR s_out,X        tau_Z = m_R,Z XOR H_Z r_Z
tau_hat_a = B_a e0,a             sign_hat_out,a = m_R,a XOR tau_hat_a
sign_error_bits_a = tau_a XOR tau_hat_a
E_sX = any(sign_error_bits_X)    E_sZ = any(sign_error_bits_Z)
E_code = E_sX OR E_sZ            E_LZ = ell_Z XOR ell_hat_Z
```

Record per-check errors, their count and any-check error separately. A changed
physical sign that is correctly inferred is a success. E_sX=0 alone does not
certify all stabilizer signs. E_LZ is the specified corrected measurement
failure flag; report its joint counts with E_sX/E_sZ and its rate conditional
on E_code=0. This is not a proof of fault tolerance or a state fidelity.

The Z-prefix decoder retains the known initial-Z anchor and predicts both
tau_Z and ell_hat_Z. It sees no ideal terminal syndrome/readout. The X-gap
decoder alone cannot supply logical-Z recovery. Initially no physical
correction is applied: one software parity prediction is compared once with
the evaluator label. A future actual Pauli frame must declare its symplectic
sign/logical maps and physical-versus-software application. A pure-error
repair with logical action must include that action exactly once; no
exponential all-syndrome recovery lookup table is needed for these metrics.

Canonical reference samples are not shot-paired ideal histories. The absolute
first X signs and logical-X outcomes are random; comparing them with a fixed
reference does not define an error rate. A future `coupled_frame_flip`
diagnostic requires shared ideal randomness/Pauli-frame coupling and separate
labels. It is not a prerequisite for this baseline.

## Three circuits and an explicit offline completion

1. `physical_prefix`: native transversal initialization and exactly R full SE
   rounds. Unknown first X signs emit no standalone detector; known first Z
   signs retain their comparison with zero. Later detectors are successive
   same-check readout differences.
2. `circuit`: that prefix plus ideal output X probes and ideal destructive Z.
   Only prefix detectors are public. `OBSERVABLE_INCLUDE` records tau_X,
   tau_Z and ell_Z in explicit order (all X checks, all Z checks, logical Z).
   These parities are deterministic in the noiseless circuit. The suffix is
   evaluation-only and contributes no physical resource cost.
3. `completed_circuit`: an offline selected-X model with an ideal past probe
   **after noisy initialization and before SE**, and ideal output probes.
   It declares individual rows `past = m_1 XOR s_past`, `online = m_t XOR
   m_(t+1)`, `future = m_R XOR s_out`. Past/future outcomes are never sampled
   for a production decoder. Z inference is separately anchored at initialization;
   do not replace its known initial signs by an unknown past boundary.

A circuit builder must prove the declared signed/noiseless flows and verify
strict DEM extraction (`decompose_errors=False`, `allow_gauge_detectors=False`,
`approximate_disjoint_errors=False`). A capability error is required if a
noise/channel/measurement schedule cannot establish these properties.

### Why the hidden past probe is permissible under these assumptions

Assume a full commuting stabilizer set, a nondemolition Clifford extraction
instrument, ancilla preparation/reset as prescribed, and stochastic Pauli
faults/classical readout flips independent of measurement outcomes. For each
fixed fault trajectory, propagate Pauli faults through the ideal Clifford
instrument to obtain K_m = E Pi_(m XOR q), where Pi_b is the joint stabilizer
projector. The discarded ideal premeasurement is D(rho)=sum_a Pi_a rho Pi_a.
Orthogonal projectors satisfy

```text
Pi_b D(rho) Pi_b = sum_a Pi_b Pi_a rho Pi_a Pi_b = Pi_b rho Pi_b.
```

Thus K_m D(rho) K_m† = K_m rho K_m†: both each first-full-SE outcome
probability and its conditional output state agree. All subsequent joint
statistics agree by applying the same later instruments. For an X-only past
probe, each full X/Z projector refines an X eigenspace, giving the same
identity. Average over fault trajectories afterwards. The probe sits after
the same noisy initialization, so it does not erase initialization noise.

This argument requires the full instrument to have the stated form; it is
not implied merely by a circuit being Clifford. Partial/noncommuting gauge
extraction, leakage, non-Pauli channels or outcome-dependent circuit rewrites
need a new proof and capability checks. It does not justify inserting a past
probe into the physical experiment.

Validate completion by projecting production and completed DEMs onto the
**same** online X rows and evaluation features and marginalizing hidden rows.
For that validation only, aggregate independent identical parity signatures
by p_odd=(1-product_i(1-2p_i))/2. Compare Z-prefix inference separately.
Never feed this aggregated validation model back into boundary classification.

## Completed graph and the two optimizations

Retain each flattened completed DEM error instruction in original column
order. Its source is a `completed_dem_term`, not necessarily a unique physical
gate fault. Individual detector rows must have explicit, exhaustive roles.
Reject separators and completed detector support greater than two **before**
contracting boundary rows; coordinates/online degree alone cannot classify a
spatial versus temporal endpoint.

Let H be online incidence, P/F the XOR of individual past/future rows, B the
static requested feature map. S contains **all** full-support-one columns:
each has an unrepresented spatial endpoint, including a future-only column
whose online incidence is zero. Full-support-two terms can become zero after
contraction; full-support-zero terms can still flip evaluation labels. Keep
both in the truth/provenance model. Before solving, check every unfrozen
nonzero augmented column [H;P;F] has exactly two endpoints.

For one shot y, use a common nonnegative integer objective W(e)=sum_j q_j e_j:

```text
e0 minimizes W(e) with H e = y
e1 minimizes W(e) with H e = y, e[S] = e0[S],
                       P e = P e0 XOR 1, F e = F e0 XOR 1
Delta_integer = W(e1) - W(e0)
```

Fix both zeros and ones. With A the complement of S and z=e0[S], construct
K_A=[H_A;P_A;F_A] once. Its per-shot RHS is

```text
(y XOR H_S z, P e0 XOR 1 XOR P_S z, F e0 XOR 1 XOR F_S z).
W1 = W_A + q_S dot z.
```

The fixed cost and both boundary offsets are mandatory. The reviewed seed
uses two cached native matchers, no per-shot graph mutations or penalties.
Parallel mechanisms use private degree-two subdivision nodes, costs (q,0),
zero subdivision syndrome and labels on the q edge. This preserves original
variables even when online columns coincide (especially R=2).

### Graph-parity proof

For gamma=e0 XOR e1, the constraints give H gamma=0, gamma[S]=0 and
P gamma=F gamma=1. Fixed spatial-open edges cancel. Each remaining nonzero
column is an ordinary two-endpoint graph edge. Therefore the selected
difference subgraph has exactly two odd-degree vertices, P and F; all online
vertices have even degree. Every connected component has an even number of
odd-degree vertices (the degree sum equals twice its edge count). P and F
must be in the same component, which contains a P–F path. Additional cycles
and parity-invisible zero columns do not alter this conclusion.

This is a statement about two hypotheses on the validated completed graph.
It does not identify the sampled physical fault, imply sign correctness at
large gap, sum over degeneracies, or give posterior odds. Model assumptions,
this graph proof and Monte Carlo calibration are three separate claims.

## Weights, statuses and witnesses

For independent DEM probability 0<p<1/2, w=log1p(-p)-log(p). Quantize once:
q=rint(lambda*w), default lambda=1000, ties to even. Active terms that round
to zero remain zero-cost variables; zero-online baseline ties choose zero.
p=0 columns remain in provenance/B/truth but are removed by
`matching_kwargs()`; placeholder zero costs must not make them selectable.
p>=1/2, nonfinite/negative probabilities and invalid scales fail strictly.

Both graphs use the same integer q values, bounded by 2**24-1 per edge and
2**53-1 summed cost. PyMatching 2.4.0's integral-weight path uses normalization
one, including when the largest frozen weight disappears from the second
graph. See [the pinned backend implementation](https://github.com/oscarhiggott/PyMatching/blob/v2.4.0/src/pymatching/sparse_blossom/driver/user_graph.cc#L444).
Core weights/gaps are integer-cost units represented as float64; the high-level
gap is Delta_integer/lambda, a quantized natural-log score. Record original
probabilities, scale, rounding, source DEM hash, row/feature maps, strictness
and output mode in the inference identity. Changing these requires a new hash.

`invalid_syndrome` means no baseline; `no_complementary_solution` leaves a
valid baseline but no gap. Core unavailable weights are infinity and gaps
NaN; persistence must use null and explicit validity/status, never infinity
as confidence. High-level `ok` additionally requires Z validity;
`z_decoder_invalid` cannot pass a gap cut. Status precedence is invalid X
baseline, absent X complement, invalid Z, then ok; independent masks preserve
all simultaneous failure reasons. Preserve separately available baseline
statistics. Structural/numerical failures raise (adapter capability
error or invariant exception); never clamp a negative gap or drop bad shots.

Compact and full-witness matchers can choose different tied optima, including
different frozen assignments and hence different constrained gaps. Fix the
output mode for a calibration run. Debug features and errors must come from
the same solve. `debug_matches_compact=False` forbids attaching that witness
to a compact result. Use `model.expand_errors` to restore full DEM order:
`TemporalDemModel.active_columns` means p>0, whereas the core's
`active_columns` means unfrozen solver columns. They are different maps.

## Shared types and exact integration sites

[`preparation.py`](../src/knill_bench/preparation.py) is the single high-level
contract module. It does not subclass or change `models.CompiledExperiment`,
`RawSamples` or `Predictions`: these describe legacy full-memory logical
observables and would conflate sign labels and terminal decoding.

| Contract | Owner and contents |
|---|---|
| `PreparationSettings` | Explicit R and the fixed supported scientific defaults; not another YAML loader |
| `CompiledPreparationExperiment` | Builder output: physical prefix, production evaluation circuit, offline X completion, separate ledgers/detector namespaces, explicit production `labels`/offline `completed_labels`, exclusive output cut, named source/model hashes |
| `PreparationObservations` | Only bool[shots,D_X] and bool[shots,D_Z]; no raw records or evaluator back-reference |
| `PreparationTruth` / `PreparationBatch` | Evaluator labels tau_X/tau_Z/logical_Z and separate online object; shared NumPy storage is rejected |
| `PreparationPrediction` | Both sign predictions, Z logical prediction, three validity masks, status, costs/scale/gap and optional seed debug result |
| `BoundaryConstraintModel` | Alias of seed `TemporalDemModel`, retaining H/P/F/S/B, probabilities, full supports, stable term IDs, p>0 mapping, scale, strictness and source hash |
| `PreparationDecoder` | `decode_batch(online_x_detectors, online_z_detectors)`; constructed only with static models/maps, never a compiled evaluator |

Arrays are unpacked bool at this boundary. Frozen dataclasses do not freeze
borrowed arrays or mutable Stim objects; setup owns compiled objects and
decoders must not mutate input buffers. Raw record IDs, production detector
IDs, completed detector IDs, feature IDs and mechanism columns are separate
named fields, never interchangeable positional guesses.
Sign prediction arrays match the truth arrays' [shots,checks] shapes; logical
prediction is [shots,1]. Costs, gaps, masks and status are [shots]. Settings
and batch constructors validate their narrow input contracts now; full
circuit/ledger/label coverage and adapter-output validation belong to steps
01–03, rather than being implied by constructing a typed container.

Reuse the existing **ordered chunk** infrastructure requested in prompt 04,
not schema-v2 auto scheduling. Preserve all old protocols/CLI calls/hashes:

| Step | Concrete input, output and connection |
|---|---|
| 01 circuit/config | Extend `config.resolve/grid` for a separate `protocols[].id=surface_prep_fixed` case, then `circuits/preparation.py` builds the compiled contract from `Code.rotated` and native initialization/X/Z primitives. Never call `Builder.initialize(...noisy_preparation)` or reinterpret cycles. A preparation-only config omits cycles and legacy initial/final boundary settings; mixed legacy/preparation configs are initially rejected. Old config paths remain exact. |
| 02 model | `completed_dem_to_temporal_model(completed_dem, detector_roles=..., num_observables=..., weight_scale=...)` returns `BoundaryConstraintModel`. Add production/completed marginal equivalence and injected-fault certification at the actual pin. Z model retains the production initial anchor; it has its own feature/row maps. |
| 03 adapter/evaluator | `adapters/temporal_gap.py` constructs `TemporalMatching(**model.matching_kwargs())` plus a cached Z-prefix matcher. `decode_batch` returns `PreparationPrediction`. Only `simulation/preparation_metrics.py` joins it with truth, forming per-sector/code/logical/joint counts. No alternate decoder core or terminal recovery. |
| 04 setup | Add a preparation delegation in `simulation.runner.prepare` before its legacy `build/describe/convert_dem` path. Store circuits, completed DEM, row/feature maps, column order/probabilities and hashes. `adapters.decoders.describe/construct` delegate the new protocol to its descriptor/adapter, leaving old branches unchanged. |
| 04 execution | `simulation.worker.model` retains its bounded cache and delegates preparation compilation/loading to `simulation/preparation.py`; `execute` delegates this task before legacy logical-flip accounting. Cache both X graphs, Z graph and maps under physical+decoder identity. Sampler compiles per fixed chunk seed/call shape; only production circuit is sampled. |
| 04 commit/resume | Reuse `runner.execute_run`'s bounded spawn, ordered staged commits, seed derivation and manifest verification. Add a protocol-specific table-set/schema selection in `data/storage.py`/runner, not reinterpretation of existing `logical_failure`/`errors` or v2 point files. Preparation tables carry their own version tag. Workers stage bounded outputs; parent alone commits small manifests/counts. |
| 05 saved analysis | `analysis/preparation.py` reads versioned preparation counts/optional compact rows, validates identities and reports gap calibration, acceptance/unconditional-miss/conditional-risk curves, intervals and measured timing. It never simulates or automatically resumes. |

No new config, command or result schema is executable in step 00. The later
CLI uses the existing `knill-bench validate-config/build/run/resume/analyze`
dispatch, thin shell wrapper and existing config loader. It must reject
irrelevant legacy fields instead of silently borrowing their meaning. R is
not an extra simulation sweep axis. No new standalone scheduler/seed system
or mandatory simulation logs/archives is needed.

## Scientific acceptance checklist and evidence boundary

The 67 supplied synthetic decoder tests are imported after patch review.
They independently enumerate small optima, frozen-zero/one assignments,
costs/offsets, original-column P–F connectivity, parallel mechanisms,
zero-online/evaluation-only terms, inactive p=0, malformed roles, separators,
hyperedges, quantization/range and infeasibility. Contract tests add strict
defaults/R, buffer isolation and a truth-independent low-level score.
These do not certify a physical builder or the future high-level adapter.

Remaining gates, to complete in their owning steps:

- [ ] 01: d3/5, R=2/3/4/5 has exactly R full rounds; small <=7-shot p0
  fixtures have zero tau/logical-Z flips while first X signs remain random.
  Deterministic flows and negative reference-comparison controls are checked.
- [ ] 01/02: actual output-cut faults after last X are visible to truth;
  independently injected first/final readout, intermediate and corner faults
  match online/past/future/tau/logical responses without gate-name inference.
- [ ] 02: production/completed **same-sector** marginalized models agree at
  the current Hex pin, including zero-online labels; Z-anchor comparison is
  separate. Row/feature/column serialization preserves identities.
- [ ] 03: actual X/Z adapter never receives truth; changing only all oracle
  buffers leaves predictions/gaps unchanged. Sector-swapped Pauli faults,
  sign/logical correction convention and no double correction are tested.
- [ ] 03: batch/single validity, costs/features and tie/output-mode semantics
  agree; debug witnesses satisfy original-column constraints and paths.
- [ ] 04: one/two spawned workers, failed-chunk restart and uninterrupted run
  have the same fixed-chunk sample hashes/counts; changed chunk shape, graph,
  label/source/environment hashes reject resume before output mutation.
- [ ] 04: aggregate-only and compact-shot results agree; all invalid reasons
  and assigned/unobserved shots are counted; bounded retention/staging/cache
  construction is independent of shot count. Packed/unpacked/padding and
  retained replay use a versioned canonical sample hash.
- [ ] 05: acceptance requires all validity flags and gap>=g. Report A, joint
  miss U and conditional risk Q=U/A separately for X/code/logical metrics,
  denominators/pointwise intervals, null empty bins and conditional E_LZ.
- [ ] 05: separate setup/sample/X baseline/X complement/Z/evaluation/I/O
  timings and diagnostic replay; claim speed or scientific calibration only
  from new measured evidence, never the supplied older-pin validation.

No large Monte Carlo, production sweep, FT/threshold/posterior claim, adaptive
continuation, concatenated color-code decoder or Knill handoff is certified
by this phase. Test commands/failures/results are appended to `TEST.md`.

The supplied seed is reused, with source-hash/strictness/rounding metadata
added rather than a duplicate constraint container. Primary semantics are
audited against [Stim observable declarations](https://github.com/quantumlib/Stim/blob/v1.16.0/doc/gates.md#the-observable_include-instruction)
and the PyMatching source above; mathematical conclusions follow from the
explicit assumptions and parity proof here.
