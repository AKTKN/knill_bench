# B2: batched logical-zero factory benchmark

The bench runs the tested Hex H5 physical factory through the independent v2
path. The current True policy builds module-local Stim priors in the bench
adapter; Hex still supplies all physical operations, causal Pauli-frame rules
and MWPM-sector construction. The original v1 experiments and B1 full Knill physical
adapter remain separate; full Knill keeps its noisy final readout.

## Commands and configuration

```bash
knill-bench-v2 validate-config configs/logical_zero_factory.yaml
# Deliberate 10,000-shot/point experiment, not run by tests/bootstrap:
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory.yaml

# Multi-stage example: inspect its YAML for the current depths and shot budget.
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory_v2_example.yaml
knill-bench-v2 resume results/<factory-run>
```

The wrapper accepts one optional config path, defaulting to the new factory
config. It uses the knill_system Conda environment, with KNILL_PYTHON override.
Relative output_root remains relative to the invocation working directory.
The default config uses d=3/5, p=.001/.003/.005, T_tel=1, r_0=r_plus=d,
uniform Hex noise, MWPM and create_codecapacity_dem=False. Only d/p sweep.
T_tel and round rules are run-wide fixed values. Round rules accept positive
integers, d, or quoted positive multiples such as `"2*d"`, `"2/3*d"` and
`"1.5*d"`. Each depth is computed exactly and floored at the point's distance;
all results must be at least one. Resolved depths reach Hex's PreparationPlan
and saved identities/metadata. See [syntax and bounds](auxiliary_v2.md).
The multi-stage example stores theta for later analysis; it never controls
which shots are sampled or retained.

## Physical factory and terminal labels

`experiments.logical_zero_factory.compile_point(point, seed=...,
create_codecapacity_dem=False, skip_circuit_validation=False)` returns the actual Hex FactoryCircuitBundle
and CompiledFactory. It calls:

- RotatedSurfaceCodeAdapter(d), PreparationPlan(r_0,r_plus);
- FactoryCircuitBuilder(..., physical_error=p, T_tel=T).build();
- Both prior modes use adapters.hex_factory.compile_local_factory, returning
  the native CompiledFactory with packed preparation arithmetic. True also
  selects the local-prior decoder described below.

By default Hex validates the signed check flows and causal frame boundaries. Exactly two
complete supports A/B are used for every T. Initially A is noisy zero-prepared
for r_0 SE rounds; B is noisy plus-prepared for r_plus rounds. Each stage has
transversal CNOT(fresh plus -> current memory), followed by **noisy** destructive
Z measurement of the consumed memory. Inferred logical X byproducts update
the survivor's software frame. The consumed support is reset/reprepared in X
for r_plus rounds and roles swap on the next stage. There is no third block,
extra r_0 zero preparation per stage, or post-CNOT SE.

Only the last survivor has a single **noiseless Z evaluation oracle**. Its
physical state still contains circuit faults. Hex evaluates that terminal
record using its separate Hamming code-capacity recovery and logical Z parity;
the result is logical_error:bool. No terminal label affects preparation repair,
online recovery, a stage gap, sampling or shot retention. Hex's chronological
decoder slices out the oracle and future records before earlier inference.
Altering saved oracle records changes labels but leaves all operational fields
and gaps unchanged; changing future-stage records leaves earlier gaps unchanged.

## Gap policies and validity

False selects Hex's baseline Hamming recovery and surface two-boundary MWPM
sector gap. Gaps are finite nonnegative float64 in **hamming_weight** units,
including p=0: the explicit zero-noise rule keeps finite unit edge weights
rather than constructing infinite likelihoods. A noiseless zero-syndrome
fixture has gap=d. Scores are min-sum sector weight differences, not posterior
probabilities or exact posterior log odds.

True now means **module_local_stim_dem**, replacing H5's complete-prefix
single-fault projection. Its explicit model assumption is
`preparation_and_earlier_stage_residual_errors_excluded_v1`:
**preparation and earlier-stage residual errors are excluded from the prior,
but remain in the noisy physical simulation and can cause logical errors.**
This is a change of inference model, not an equivalent faster implementation
of H5's projected prior or an exact preparation-conditioned posterior.

The adapter extracts the actual native coupling/readout fragments and maps
the consumed/fresh supports to canonical local IDs. DEM analysis adds an
ideal encoded |0> / |+> input with all CSS stabilizers +1, then the native
coupling/noise and noisy destructive Z readout. The boundary is immediately
after preparation and before coupling. H5 has no additional boundary/idle
channel there: none is invented, and the last SE gate's noise belongs to the
excluded preparation. All native coupling/readout channels are included.

Before that noise window, Pauli-target `OBSERVABLE_INCLUDE(0)` marks
Z_L(A) Z_L(B); after readout the same observable includes the logical Z
record parity. Stim 1.16 closes the input/output error sensitivity without
measuring the random byproduct or using an oracle. Z-check parities supply
the local detectors. Strict native `detector_error_model` uses no gauge,
disjoint-error approximation, or hyperedge-decomposition escape. Its complete
detector/logical events feed Hex's existing validated two-boundary gap lift.
No noiseless reference sample, preparation-decoder replay or Python growing-ID
event merge is performed. DEM row IDs are not physical-mechanism provenance.

The ideal encoder/annotations are **analysis-only**. The sampled circuit is
still the unmodified native concatenation of noisy preparation, coupling,
readout and refresh modules, with one terminal oracle. Actual shot records
use Hex's unchanged preparation resolution and `m_A XOR memory_x XOR plus_x`;
the local decoder selects the logical class and Hex updates the survivor's
X/Z frame. Global signed-flow detector annotations remain intact. A sum of
local DEMs is not claimed to be the joint full-circuit DEM.

Gaps use **log_weight** units; historical projected, local and Hamming scores
must not be treated as the same calibrated quantity. Configuration, local
physical-module, analysis-circuit and DEM hashes are saved per stage. Identical
stages share models. Tests cover d3/5, small depths/T, forward physical fault
propagation, analytic noise probabilities, exhaustive d3 sector minima and
actual multi-stage frame updates. This does not certify arbitrary settings.

UnsupportedProjectedModel propagates as a failed point/run, with no silent
Hamming fallback, omitted faults or null-gap substitute. In particular, True
at p=0 is unsupported; explicitly select False for finite Hamming scores.
Local models do not establish exact conditional decoding after preparation
repair, general fault tolerance or improved error rates.

## Bounded execution and output

`logical_zero_factory.run(document, resume_path=None)` uses the shared v2
scheduler. Omitted/auto batch_size selects time-adaptive chunks with multiple
workers sharing a point. Each worker caches one native physical model/decoder;
independently seeded chunk samplers draw complete T-stage trajectories. Parent
writers coalesce ordered label/gap results into buffer_shot row groups, with a
bounded reorder window. Integer batch_size retains the historical whole-point
worker, continuing point-seeded sampler path. See
[parallel execution](parallel_execution.md) for exact timing, memory, seed and
failure semantics. Workers=1 uses the same chunk code directly.

True additionally has a bounded 16-entry worker-local LRU for DEMs and native
gap graphs, keyed by the full canonical local circuit (including every noise
argument) and the complete code supports. An 8-entry LRU holds ideal input
encoder text. Identical local modules across stages/points reuse these objects;
T, preparation depths, seeds, shots and theta do not invalidate a local prior.
Different noise/code/module text does. Native versions and policy/boundary
conventions enter model configuration hashes. No disk/global/multiprocess cache
or sampler RNG reuse is introduced. Handles are synchronous, worker-local.

Both factory prior modes initialize the pinned H5 decoder slots immediately
after native physical construction, avoiding repeated full-bundle validation.
By default, full validation runs exactly once per compilation. The factory-only
fixed YAML option `skip_circuit_validation: true` omits that check; omitted or
`false` retains it. This skips the complete bundle check (signed prefix flows,
ledger/causal/oracle checks and operational-circuit DEM validation), not physical
operations or preparation decoding. Construction invariants, circuit hash,
local-prior structural checks, runtime repaired-sign checks, gap checks and
storage validation still run. The flag does not certify or persist a validated
circuit and does not load a physical circuit cache. Use full validation when
testing a changed circuit implementation. It is a simulator verification cost,
not an operation to repeat on quantum hardware for each shot.

H5 has no validation flag. `_build_without_full_validation` executes its exact
builder function with a private globals dictionary binding the bundle constructor
to a temporary subclass whose final validate call is empty. It returns an ordinary
native bundle with a working explicit `validate()` method; dependency sources and
module globals are not mutated. This and the decoder-slot binding must be
re-audited when upgrading Hex. V1 and B1 retain their existing numerical paths.

`factory_frames.FactoryPreparationPlan` preserves the native two circuit-level
and two code-capacity matching calls, including their weights, tie breaking and
pure-error convention. For circuit corrections c_x/c_z it precomposes the exit
X/Z maps with only the final stabilizer columns of the measurement-flip maps.
Byte lookup tables evaluate these GF(2) products using packed XOR; final X/Z
sign repair is XORed directly into the exit frames. No corrected full history,
large concatenated correction vector or per-batch sparse-to-dense conversion
is needed. Matching decisions still depend on the corrected final signs.
The native public PreparationFramePlan, with its diagnostic full-history return,
is unchanged and available on the bundle. Optimized plans are private to the
compiled factory. They share precomputed maps per native preparation template
(basis/support/depth) within the point, with synchronous native handles. Lookup
tables cost 256 * ceil(input_bits/8) * ceil(output_bits/8) bytes per map;
execution bounds each gather to 32 input bytes per shot. This is a memory/time
tradeoff, not a hardware real-time guarantee.

Each chunk samples a full fixed T trajectory, then calls decode on the saved
measurement array offline. It does not resample or stop when a gap is small.
`theta` is recorded only in the run config; it is absent from worker arguments
and compilation. All trajectories/gaps are saved, including ones below theta.
There is no retry/early-abort branch. Acceptance, first rejection and production
cost calculations are provided by [the separate B3 analysis](factory_analysis.md).

Physical seed derivation excludes prior policy, validation flag, theta, workers
and requested shots. Auto mode uses independently chunk-seeded samplers; its
wall-time feedback may change the partition across runs/policies. It does not
promise identical raw trajectories between auto Hamming/local runs. Use the
same integer batch_size and physical seed for paired physical-record studies.
Fixed mode retains the point-seeded continuing sampler and requires the same
Stim/platform/batch partition for exact replay. Theta never selects data.

Per point the output owner streams exactly these two B0 tables, using one writer
each across chunks and the exact partial final chunk:

| Table | Columns |
| --- | --- |
| logical_error | shot_id:uint64, logical_error:bool |
| logical_gaps | identical shot_id:uint64, gap_t001..gap_tT:float64 |

IDs are contiguous from zero and join exactly on shot_id. Although the B0
gap schema is nullable for infrastructure compatibility, B2 requires every
Hex stage gap to be present, finite and nonnegative; missing/NaN/Inf/negative
scores and unresolved frames fail the point and discard incomplete paired
output. No unavailable gap is silently converted to null.

Only exact config.yaml, one metadata.json and the two files per completed
point are required. The parent alone records actual shots/errors and publishes
completion after both closed footers validate. Metadata includes T/depths,
score units, oracle/readout conventions, two-support sizes and alternating
stage roles, decoder/gap policies, circuit/model hashes and sampling policy.
Execution also records `skip_circuit_validation`, `circuit_validation`
(`full_native` or `skipped_by_configuration`) and
`preparation_frame_implementation=factory_packed_preparation_frames_v1`.
Point wall time includes setup, simulation, decoding, I/O and coordinator wait;
it is not decoder latency. See [the v2 contract](auxiliary_v2.md) for exact
filenames, publication limits and lock/provenance rules.

Resume retains completed paired files and restarts an unfinished point at
shot zero with the same seed after checking unchanged config/source/environment.
Runs from the former True policy must start fresh under this code; resume
rejects changed policy/source before altering files. Saved-only analysis can
still read legacy `circuit_informed_projected` runs, retaining their old policy
label rather than relabeling their gaps. Late chunk failures remove both incomplete files. Fixed-mode tests replay the
same partition and compare both resumed tables exactly; auto restart can use
a different measured-time partition. No mandatory raw-array archive or log
is introduced. Large sweeps/resource costs were not measured in B2.

## Validation boundary

For setup versus sampling/decoding wall times and the current projected-prior
construction bottleneck, see the [measured performance report](factory_performance_report.md)
and the opt-in scripts/profile_factory.py selected-point diagnostic. Changing
physical shots/batch_size does not remove fixed model construction. The report
distinguishes completed measurements, bounded partial profiles and inference
policy comparisons.

Bench tests use d=3/5, T=1/2/3 and at most 7 shots per new physical fixture.
They cover real finite gaps, zero noise, two-support swapping, readout/oracle
conventions, repeatability, theta/prior-independent raw sampling, no oracle or
future leakage, cached native objects, aligned joins, exact counts, serial/
spawn equality, failure/restart and unsupported projected models. Existing
Hex tests separately validate signed parity/frame boundaries, native-map
equivalence, injected faults and exhaustive d3 sector weights. No physical
circuit or causal frame algorithm was copied into bench. See [TEST.md](../TEST.md) for commands,
results and any failures. B2 checks do not run production Monte Carlo; B3 now
adds separate saved-data analysis and a [getting-started guide](../GETTING_STARTED.md).




## Custom physical noise

The separate user-authorized BENCH-N1/N2 integration accepts factory-only
[custom-noise YAML](factory_custom_noise.md), using Hex HEX-N2 86c9495.
Legacy scalar hex_uniform behavior stays exact. The guide defines each
multiplier, normalized durations, the two disjoint windows, early validation,
physical/local-prior scope and short custom filenames. Start with the
[commented seven-shot template](../configs/templates/logical_zero_factory_custom_noise.yaml).
