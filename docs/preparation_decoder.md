# Fixed-R batch decoding and metrics (prompt 03)

The Python API now combines the supplied two-solve X temporal matching core
with one cached Z-prefix MWPM model. The evaluator separately joins their
predictions with sampled truth. Prompt 04 now provides
[ordered worker/storage integration](preparation_execution.md). No production
run is included.

Start with the [circuit/config guide](surface_preparation.md),
[completed model/artifact guide](temporal_boundary_model.md) and
[theory/frame contract](temporal_preparation_theory.md). Hex and all pins stay
unchanged. Prompt 02 is committed/pushed as `451e1f0` on `surface-prep-fixed`;
prompt 03 is pushed as `6fa15c5`; prompt 04 is a local implementation diff.

## Python API and truth boundary

```python
from knill_bench.circuits.preparation import build_preparation
from knill_bench.adapters.temporal_gap import prepare_preparation_decoder
from knill_bench.preparation import split_preparation_samples
from knill_bench.simulation.preparation_metrics import (
    evaluate_preparation, summarize_preparation,
)

compiled = build_preparation(dict(
    protocol="surface_prep_fixed", distance=3, rounds=2,
    p=0, decoding_p=.003,
))
decoder = prepare_preparation_decoder(compiled, weight_scale=1000,
                                      output_mode="compact")
det, labels = compiled.circuit.compile_detector_sampler(seed=617).sample(
    3, separate_observables=True,
)
batch = split_preparation_samples(compiled, det, labels)
prediction = decoder.decode_batch(
    batch.observations.online_x_detectors,
    batch.observations.online_z_detectors,
)
evaluation = evaluate_preparation(batch.truth, prediction)
summary = summarize_preparation(evaluation, threshold=0)
```

Setup compiles/certifies static models and returns an adapter with no reference
to the compiled evaluator, circuit, sampled truth or raw record buffers. The
direct constructor is `TemporalGapDecoder(x_model, z_model, output_mode=...,
logical_evaluation="prefix_frame_only")`. It accepts only static models.
Both must describe the same nominal production experiment and common scale.
Only `tau_x:<check>` feature rows enter the X core; Z supplies
`tau_z:<check>` and the single `logical_z` response. Check identities must be
unique/contiguous and are mapped explicitly, independent of feature row order.

`decode_batch(online_x_detectors, online_z_detectors)` accepts unpacked
bool[shots,detectors] arrays; `decode_one` accepts two one-dimensional bool
arrays and returns a one-row batch. Neither accepts truth or last absolute
signs. `decode_packed_batch` is the explicit uint8 alternative: little-endian
bit order, exactly ceil(detectors/8) bytes per row, zero padding required.
It unpacks each sector once, including an empty R1 X detector block.

## Three cached solves and one frame convention

The X core is the supplied `TemporalMatching(**model.matching_kwargs())`.
Its baseline/complementary problems, all-zero/all-one spatial frozen bits,
P/F offsets, fixed cost and private parallel-edge subdivisions are retained.
This step adds diagnostic outputs and an optional graph-prewarm method; it
does not replace the optimizer or alter either objective.

`compile_preparation_prefix_model(compiled, weight_scale=1000)` builds a
separate `PrefixDemModel` from the nominal production-shaped DEM. It selects
all Z SE rows, including each first-round known-zero comparison. Compilation
checks that every selected row uses the expected physical SE records; ideal
output probes/destructive readout cannot become its detectors. Static DEM L
responses describe tau_Z and logical_Z without supplying their sampled values.
The model retains every original production DEM term, including parallel,
zero-detector and p0 terms. It projects onto explicitly selected Z rows before
checking degree<=2; combined X/Z events may have larger full support.
Separators, selected hyperedges and probabilities outside [0,.5) raise.

The Z model reuses the supplied `_StaticMatcher` multigraph implementation
for one ordinary prefix solve. It has no P/F classification or complementary
Z optimization. The original completed X model remains the sole H/P/F/S
authority. Both models use `rint(scale*(log1p(-p)-log(p)))`, preserve active
rounded zeros, exclude p0 from matching and retain original-column maps.
The Z model hash includes original supports/probabilities/costs, selected
detector/feature order, known-zero scope and provenance. `expand_errors`
restores full-mode Z witnesses to original production-DEM columns.

The declared recovery is **prefix_frame_only**. One software parity prediction
is compared with truth exactly once. No physical correction, pure-error LUT,
ideal-final-syndrome decoding or extra terminal recovery is applied. A physical
sign that is correctly inferred counts as success. Terminal recovery would
need a distinct protocol/identity; explicitly requesting it raises here.

## Predictions, validity and ties

`PreparationPrediction` returns bool tau_X/tau_Z/logical_Z predictions,
baseline/complementary costs, gap, independent validity masks and status.
Costs are float64 representations of the shared integer costs. Gap is
`(W1-W0)/weight_scale`, a quantized natural-log **score**, not posterior odds.
Unavailable costs are +infinity and unavailable gaps are NaN. Available
negative/nonfinite/inconsistent costs or gaps raise; no clipping occurs.

| Mask/status | Meaning |
|---|---|
| `baseline_valid` (`x_baseline_valid` alias) | X prefix baseline exists |
| `complementary_valid` | X constrained comparison exists; requires a baseline |
| `z_decoder_valid` | Independent known-zero Z-prefix solve exists |
| `invalid_syndrome` | No X baseline, regardless of Z validity |
| `no_complementary_solution` | X baseline exists but its comparison does not |
| `z_decoder_invalid` | Both X solves exist but Z is invalid |
| `ok` | All three masks are true |

Masks preserve multiple simultaneous obstructions, even though status has
the precedence above. At nominal p=0 a clean baseline can be valid with no
temporal path; its errors still count in baseline statistics, its gap remains
NaN and it is never accepted. There is no artificial epsilon path.

`prediction.diagnostics` includes baseline frozen assignments (both zeros and
ones), original completed-DEM frozen column IDs, the selected baseline's P/F
parities and Z cost. These labels are masked by their validity flags. Normal
compact output has no full mechanism vectors. `output_mode="full_witness"`
prewarms the optional X/Z original-column label graphs during setup, then
returns `prediction.debug` for X and optional Z witnesses/agreement flags
inside diagnostics. No decode call constructs graphs, reparses a DEM or
requantizes weights.

The selected output mode is immutable for an adapter and is included in its
model definition/hash with source hashes, backend version, tie policy,
feature/column identities, scale and frame convention. Native equal-cost
solutions may differ between compact/full outputs. Full witnesses and their
predictions always come from the **same solve**; `debug_matches_compact=False`
identifies a different optimum, never a witness for a prior compact result.
The frozen assignments/P/F diagnostics describe that same returned baseline.

## Evaluator counts and selection

`evaluate_preparation(truth, prediction)` alone combines the two interfaces:

```text
error_bits_X = tau_X XOR tau_hat_X      error_bits_Z = tau_Z XOR tau_hat_Z
E_sX = any(error_bits_X)                E_sZ = any(error_bits_Z)
E_code = E_sX OR E_sZ                  E_LZ = logical_Z XOR logical_Z_hat
accepted(g) = baseline_valid AND complementary_valid AND z_decoder_valid
              AND gap >= g
```

Per-check bits, per-shot error counts, any-check and code/logical errors
remain distinct. Invalid errors have zero placeholders with explicit masks:
X errors require X baseline, Z/readout errors require Z baseline, code/joint
errors require both. A missing complement does not erase these valid baseline
statistics. This logical error is the stated software-frame readout failure;
it is not a state-fidelity or fault-tolerance certificate.

`preparation_acceptance(prediction, threshold)` accepts no truth.
`summarize_preparation(evaluation, threshold=...)` returns compact counts,
per-check totals, error-count histograms, empirical rates, independent invalid
reason counts, status counts, and selected/unconditional eight-bin joint
counts indexed by `4*E_sX+2*E_sZ+E_LZ`. It also reports logical error conditional
on code-correct rows. Each statistic carries its own denominator. Empty
denominators yield null rates; zero acceptance yields no conditional estimate.
Cuts are inclusive; +/-infinity are explicit no-cut/reject-all options, NaN
and malformed thresholds fail. JSON summaries label infinities as strings.
Invalid-reason counts can overlap and should not be summed as a partition.
Pointwise intervals, calibration curves, saved reports and result tables
remain later prompts.

## Validation and measured example

Synthetic tests retain the seed's exhaustive optima and independently check
adapter costs, fixed zeros/ones, full-column constraints, feature reordering,
status masks, six-row denominators/joint counts and software-frame double-
application controls. A valid alternate tied optimum supplied through a test
backend verifies the disagreement flag and same-solve witness semantics.
Graph construction and quantization are forbidden during repeated batch/
single decodes. Explicit packed padding/empty-sector paths are tested.

Native fixtures use d3/5, R1/2/3 and <=7 shots, with p0/noisy-model and actual
noisy batches. Intermediate readout faults have hand-derived adjacent temporal
responses. X/Z/Y faults after the actual output cut independently exercise
both sign metrics and deterministic logical-Z readout, including invisible
endpoint errors. Changing all evaluator truth leaves predictions/gaps intact.
Initial-Z anchor and terminal-record negative controls reject bad model scope.
No production sweep, statistical calibration or backend speed claim is made.

One local compact-mode timing call per setting used R=2, p=.003, seven shots,
seed 617, Conda knill_system. Values below are milliseconds; the first builder
call includes cold provenance/resource work. Model/setup includes validation,
hashing and bookkeeping; graph sub-timers do not sum to the total.

| d | Circuit build | Decoder setup total | Model compilation | X graphs | Z graph | X comparative decode | Z prefix decode | Decode total | Evaluation/summary |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 301.592 | 49.031 | 26.491 | 6.955 | 3.819 | 1.708 | .677 | 2.816 | 1.291 |
| 5 | 338.468 | 289.407 | 159.619 | 8.768 | 12.284 | 2.266 | 1.679 | 4.346 | .758 |

Sampler compile/sample/split took .997/.485 ms respectively. X completed
models retained 92/289 original columns, Z prefix models 199/743. All seven
statuses were ok in each illustrative batch; these counts are not a rare-error
estimate. `decoder.setup_timings_ns` and `last_decode_timings_ns` expose the
same wall-time boundaries. Raw JSON was `/tmp/knill_prep_03_timings.json`;
commands/gates are recorded in [TEST.md](../TEST.md). These isolated timings
are descriptive single calls, with no throughput/scaling inference.


## Saved-data validation and figures (prompt 05)

[Report validation](preparation_reports.md) now independently checks original-
column same-mode witnesses, common integer costs and P–F difference paths,
and writes pointwise Wilson gap/risk figures with separate validity masks.
Bounded paired event counters compare decoder variants on the same samples.
See [getting started](preparation_getting_started.md) for simulation/report
commands; this adds no physical correction, posterior or FT claim.
