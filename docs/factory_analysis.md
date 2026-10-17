# B3: saved factory acceptance, oracle quality and attempt cost

`analysis.factory.analyze_saved(run_path, settings=AnalysisSettings(...))`
streams paired B2 tables without importing Hex/Stim/PyMatching or simulating.
It checks complete run/point metadata, exact YAML/config hashes, physical
identities/seeds, declared prior/gap/oracle conventions, schemas/counts,
contiguous identical uint64 IDs, non-null labels/gaps and finite nonnegative
scores. Different Parquet row-group boundaries are consumed in aligned bounded
slices. Invalid scores are errors, never an implicit selection policy.
Read memory scales with analysis batch_size times stage count, not total shots;
counters scale with points, cuts and stages. B0/B1/B2 sampling/storage is unchanged.

## Gap cuts and descriptive uncertainty

For each user-specified theta, accept A=AND_j(gap_j>=theta). Selection and first
rejection depend only on gaps. Terminal logical_error labels enter only the
numerator of raw and accepted error rates. No shot is split/resampled using
its true error and no automatically optimized cut is chosen.

The report has one row per point/cut with total shots/errors, accepted count/
errors, acceptance, abort rate, raw LER, conditional terminal-oracle LER and
their two-sided 95% pointwise Agresti-Coull intervals. Conditional LER is the
final **factory evaluation oracle** error, not an online data-Knill EC LER.
No acceptance makes conditional LER/interval/SE null. Zero observed errors
still has a positive binomial upper bound; a plug-in SE of zero is not proof
of zero uncertainty. Thresholds chosen after inspecting many cuts have no
simultaneous or selection-adjusted coverage guarantee.

The exact identities checked in deterministic fixtures are: theta=-infinity
retains every shot and recovers raw LER; larger cuts cannot increase accepted
count; equality at theta is accepted; and acceptance plus the first-rejection
histogram totals the shot count. Altering terminal labels cannot alter accepted
counts, first rejection or costs. Altering gaps after an already-realized first
rejection cannot move that rejection.

`first_rejected_stage(gaps,theta)` returns 0 for accepted, otherwise the first
rejected stage numbered 1..T. Full T-stage trajectories remain in saved data.
Only counterfactual accounting stops at the first rejected stage.

## Explicit cost model

`FactoryCostModel` parameters are nonnegative durations/costs in one declared
unit, with positive `se_round`. Defaults are SE_equivalent, serial initial
preparation, se_round=1 and all other overheads zero. These are assumptions,
not measured hardware/decoder latencies. B2 process wall time is not substituted
as a quantum critical-path latency.

Let S=se_round, R=reset, D=preparation_decode, H=teleportation+online_decode,
and F=R+r_plus*S+D. Initial preparation cost is

```text
I_serial   = (R+r_0*S+D) + (R+r_plus*S+D)
I_parallel = max(R+r_0*S+D, R+r_plus*S+D)
C_j        = I + (j-1)*F + j*H,      j=1..T
```

Parallel initial preparation assumes enough quantum/classical capacity to
overlap both full preparation/decode paths. Refresh preparation is serial
before the next teleportation; future refreshes are never prepared speculatively.
Reset is per data-block preparation, while check-ancilla resets are included
in SE cost. Teleportation includes coupling and noisy consumed-block readout;
online_decode is the stage decision latency. Preparation decoding lies on the
assumed preparation critical path. The sole terminal ideal oracle is evaluation
only and contributes no operational latency.

An accepted attempt costs C_T and yields **one** final resource. A rejected
attempt first rejected at j costs C_j+restart; restart is cleanup beyond the
next attempt's already-counted preparation resets. It is charged only after
rejection. Cost assumptions do not modify the sampled circuit or insert noise
for alternate overlap/waiting schedules. This is not a simulated adaptive
trajectory, multi-factory queue, hardware schedule or memory-noise model.

Mean attempt cost and its sample-mean SE come from the empirical first-rejection
histogram. `full_trajectory_cost=C_T` separately describes the fixed sampled
trajectory. Under explicit **iid fresh-restart** assumptions, the renewal
equation gives estimated cost-to-first-accepted = mean(C)/P(A), and expected
attempts = 1/P(A). Within-attempt cost may correlate with acceptance. No ratio
is reported unless iid_restarts is explicitly true. No observed acceptance
leaves the ratio undefined/null; it does not prove the true acceptance is zero.

The ratio's descriptive SE uses paired residuals C_i-ratio*A_i:
SE = sample_std(residual)/sqrt(N)/mean(A). It is a delta approximation under
iid attempts, not a calibrated small-acceptance confidence interval or guaranteed
runtime bound. For N=1, empirical cost/ratio SE is unavailable/null. Scalar
costs omit unmodeled overheads, queues and inter-attempt correlations.

## Settings and optional reports

[The analysis template](../configs/templates/factory_analysis.yaml) is a
separate strict YAML with analysis_version:1. It accepts a list of thresholds
(including -.inf/.inf) or a finite inclusive threshold_grid with start/stop/count,
cost-model fields, boolean iid_restarts and a read batch_size. It is not a
simulation schema or new sweep axis. Duplicate/unknown keys, NaN cuts,
unsupported fields or invalid durations fail.

```bash
knill-bench-v2 analyze-factory "$FACTORY_RUN" --settings configs/templates/factory_analysis.yaml
knill-bench-v2 analyze-factory "$FACTORY_RUN" --theta=-inf --theta=2 --theta=inf --iid-restarts --output report.json
knill-bench-v2 analyze-factory "$FACTORY_RUN" --theta-grid 0 5 11 --output report.csv
knill-bench-v2 analyze-factory "$FACTORY_RUN" --settings my_analysis.yaml --output report.md
```

Without output, CLI prints JSON. JSON/CSV/Markdown are optional analysis
artifacts; no simulation table/log/archive is added. `write_report` includes
declared cost assumptions and the conditional-estimand/interval labels. JSON
and Markdown also include compact simulation source provenance. Infinity cuts
are serialized as strings '-inf'/'inf', undefined quantities as null or blank
CSV cells. Readers can work with old saved data without matching today's source
environment; resume retains stricter source/environment compatibility rules.

This command always reads the simulation config saved inside RUN. Changing
an external simulation YAML does not select new data. To simulate changed
parameters, first use `FACTORY_RUN=$(knill-bench-v2 run SIMULATION_YAML)` and
then analyze that new path. `--settings` controls only cuts/cost assumptions.
Repeated analysis recomputes the report and overwrites the explicitly requested
output file; it never resumes or skips a simulation because another run exists.

The reported costs do not certify exact posterior confidence, fault tolerance,
an improved projected prior, threshold scaling or Fig.4(d) agreement. Hamming
and log-weight cuts are not interchangeable. See [getting started](../GETTING_STARTED.md)
for setup/templates/reproduce commands and [TEST.md](../TEST.md) for tiny v2
end-to-end smoke, existing constructor-counter checks, read-only Hex integration
and full v1 regression results. No production sweep or large performance job
is run by unit tests.

Current True runs use module_local_stim_dem, excluding preparation/earlier-stage
residuals from the prior while retaining noisy physical preparation. Historical
circuit_informed_projected data remain readable, and report rows retain their
saved policy label. Even though both use log_weight units, their gaps/cuts are
not interchangeable calibrations. Source/policy changes require a fresh
simulation run, not resume. See [the model definition](logical_zero_factory.md).
