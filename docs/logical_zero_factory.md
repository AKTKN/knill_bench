# B2: batched logical-zero factory benchmark

The bench now runs the tested Hex H5 factory through the independent v2 path.
No new circuit, Pauli-frame rule, MWPM-sector construction or prior model is
implemented in bench. The original v1 experiments and B1 full Knill physical
adapter remain separate; full Knill keeps its noisy final readout.

## Commands and configuration

```bash
.venv/bin/knill-bench-v2 validate-config configs/logical_zero_factory.yaml
# Deliberate 10,000-shot/point experiment, not run by tests/bootstrap:
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory.yaml

# Smaller multi-stage example: d=3/5, T=2, 64 shots per point.
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory_v2_example.yaml
.venv/bin/knill-bench-v2 resume results/<factory-run>
```

The wrapper accepts one optional config path, defaulting to the new factory
config. It uses repository .venv/bin/python, with KNILL_PYTHON override.
Relative output_root remains relative to the invocation working directory.
The default config uses d=3/5, p=.001/.003/.005, T_tel=1, r_0=r_plus=d,
uniform Hex noise, MWPM and create_codecapacity_dem=False. Only d/p sweep.
T_tel and integer/d round rules are run-wide fixed values. The existing
small example uses depths (2,2), T=2 and a stored theta for later analysis.

## Physical factory and terminal labels

`experiments.logical_zero_factory.compile_point(point, seed=...,
create_codecapacity_dem=False)` returns the actual Hex FactoryCircuitBundle
and CompiledFactory. It calls:

- RotatedSurfaceCodeAdapter(d), PreparationPlan(r_0,r_plus);
- FactoryCircuitBuilder(..., physical_error=p, T_tel=T).build();
- CompiledFactory.from_bundle(bundle, seed=point_seed, create_codecapacity_dem=flag).

Hex validates the signed check flows and causal frame boundaries. Exactly two
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

True delegates all model construction and structural checks to Hex. It uses
stage-specific complete causal-prefix projected models with the actual earlier
projected policy. Gaps use **log_weight** units; cuts are not interchangeable
with Hamming units. The approximation remains
single_fault_at_noiseless_reference_independent_superposition_v1. Configuration
and model hashes for each stage are retained in compact execution metadata.
Tests cover d3, p=.001, depths (2,2), T=2. This does not certify arbitrary
distances, depths or probabilities.

UnsupportedProjectedModel propagates as a failed point/run, with no silent
Hamming fallback, omitted faults or null-gap substitute. In particular, True
at p=0 is unsupported; explicitly select False for finite Hamming scores.
Projected models do not establish exact conditional decoding after nonlinear
preparation repair, general fault tolerance or improved error rates.

## Bounded execution and output

`logical_zero_factory.run(document, resume_path=None)` uses the shared
`experiments.execution.execute_points` scheduler also used by B1. A point
worker builds one Hex bundle/compiled factory and caches all samplers, graphs,
converters and correction maps there. One process handles an entire point,
advancing one point-seeded sampler through bounded chunks. Workers > 1 use
spawn with at most workers point tasks pending; no native object is pickled
and no process is initialized per chunk. Workers=1 runs directly in the parent.

Each chunk samples a full fixed T trajectory, then calls decode on the saved
measurement array offline. It does not resample or stop when a gap is small.
`theta` is recorded only in the run config; it is absent from worker arguments
and compilation. All trajectories/gaps are saved, including ones below theta.
There is no retry/early-abort branch. Acceptance, first rejection and production
cost calculations are provided by [the separate B3 analysis](factory_analysis.md).

Physical seeds exclude prior policy, theta, workers and requested shots.
Hamming and projected modes on the same physical point use identical circuits
and raw records for a fixed seed/chunk partition. Their inferred frames, gaps
and final labels may differ. Reproduction requires the same library/platform
and batch partition. B0 chunk seeds are unused; one continuing sampler consumes
the point seed once.

Per point the worker streams exactly these two B0 tables, using one writer
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
Point wall time includes setup, simulation, decoding, I/O and coordinator wait;
it is not decoder latency. See [the v2 contract](auxiliary_v2.md) for exact
filenames, publication limits and lock/provenance rules.

Resume retains completed paired files and restarts an unfinished point at
shot zero with the same seed after checking unchanged config/source/environment.
Late chunk failures remove both incomplete files; tests replay that seed and
compare both resumed tables exactly. No mandatory raw-array archive or log
is introduced. Large sweeps/resource costs were not measured in B2.

## Validation boundary

Bench tests use d=3/5, T=1/2/3 and at most 7 shots per new physical fixture.
They cover real finite gaps, zero noise, two-support swapping, readout/oracle
conventions, repeatability, theta/prior-independent raw sampling, no oracle or
future leakage, cached native objects, aligned joins, exact counts, serial/
spawn equality, failure/restart and unsupported projected models. Existing
Hex tests separately validate signed parity/frame boundaries, native-map
equivalence, injected faults and exhaustive d3 sector weights. No physics
implementation was copied into bench. See [TEST.md](../TEST.md) for commands,
results and any failures. B2 checks do not run production Monte Carlo; B3 now
adds separate saved-data analysis and a [getting-started guide](../GETTING_STARTED.md).
