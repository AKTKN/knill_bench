# Getting started: fixed-R surface preparation

Use `knill-bench` (schema v1) for `surface_prep_fixed`. This prepares a single
rotated surface-code patch in logical zero, performs exactly R full noisy X-
then-Z extraction rounds, and evaluates the state after the final Z extraction.
It reports X/Z output-sign misses, their OR (code-space sign miss), a
prefix-frame-corrected logical-Z readout error, and an X-sector comparative
gap. The ideal terminal probes/readout supply evaluation labels only.

## Environment and first simulation

From this repository root:

```bash
bash scripts/bootstrap.sh
bash scripts/python.sh -m pip check
cp configs/templates/surface_prep_fixed.yaml my_prep.yaml
bash scripts/python.sh -m knill_bench.cli validate-config my_prep.yaml
bash scripts/run_simulation.sh my_prep.yaml
```

The wrapper selects Conda `knill_system`; do not create a `.venv`. Bootstrap
checks the pinned forks rather than resetting them. Alternatively activate
`knill_system` and use `knill-bench run my_prep.yaml` directly. The tiny
example runs **three shots at d=3, R=3, physical p=.001, one worker**. It is a
software smoke budget, not a statistical error-rate experiment. The final
printed line is the run directory; copy it as RUN below. Setup/commit progress
also goes to stdout, so do not capture the entire output as a path.

```bash
RUN=results/REPLACE_WITH_THE_PRINTED_DIRECTORY
bash scripts/python.sh -m knill_bench.cli analyze "$RUN" --output "$RUN/analysis/first_report"
```

Choose a new analysis directory for each invocation. Omitting `--output`
creates a unique `RUN/analysis/<UTC timestamp>_<suffix>/`. Existing directories
are never overwritten. Analysis reads published saved data, checks hashes,
counts and model boundaries, and writes figures and tables; it does not sample,
resume or change simulation/config/checkpoint files. Run and analysis directory
names differ from the separate schema-v2 experiment format.

Open `analysis/first_report/report.md`. It links the PNG figures; the same
figures are available as PDF and SVG. Inspect `validation_summary.json` for
which witnesses were available, rather than assuming compact runs have full
chains. The three-shot template retains no examples; the synthetic exhaustive
spatial-freezing counterexample is still included.

## A bounded validation run with retained witnesses

[The validation template](../configs/templates/surface_prep_fixed_validation.yaml)
uses d=3, R=2, physical p=0/.02, seven shots at each p (14 total), two workers,
chunk_size=3, and matched positive nominal decoding_p=.02. At p0 this explicitly
keeps a positive inference model without inventing physical noise. The noisy
point is an explicit stress-smoke choice to exercise failure counters, not a
paper parameter or a rare-error study. Compact and full-witness decoders share
exactly the same physical samples. Their tie policies may differ; both model
identities and paired event counts are saved. Only bounded retained rows carry
full original-column chains.

```bash
cp configs/templates/surface_prep_fixed_validation.yaml my_validation.yaml
bash scripts/python.sh -m knill_bench.cli validate-config my_validation.yaml
bash scripts/run_simulation.sh my_validation.yaml
# Set RUN to this new run's final printed path.
bash scripts/python.sh -m knill_bench.cli analyze "$RUN" --output "$RUN/analysis/validation"
bash scripts/python.sh -m knill_bench.cli resume "$RUN" --workers 1
```

A completed resume preserves published chunks. Resume requires the saved
config, fixed partition, source and dependency identity to match. Keep source
files unchanged between build/run/resume; start a fresh run after editing
code or settings. Worker count may change via resume's explicit override;
seeds do not depend on worker count. Failed/unpublished chunks restart with
the original chunk seed and sampling call shape. Completed chunks stay intact.

To prepare without sampling, use `knill-bench build CONFIG`, then `knill-bench
resume RUN`. Every build/run creates a fresh directory. There is no automatic
resume based on a config name. Do not pass a simulation YAML as RUN to analyze.

## Changing simulation settings

Edit your copied YAML, then validate it before running:

| Setting | Meaning |
|---|---|
| `experiment.distances` | Supported odd rotated-surface distances, at least 3; d sweep |
| `experiment.physical_error_rates` | Native Hex uniform circuit-noise probabilities; p sweep |
| `protocols[0].rounds` | **Literal positive integer R**, independent of distance |
| `protocols[0].decoding_p` | Optional fixed nominal inference p; omitted means physical p |
| `sampling.shots_per_case` | Fixed attempts per physical d/p case and replicate |
| `sampling.chunk_size` | Fixed seeded partition and memory bound; keep fixed for replay |
| `sampling.workers` | Spawned worker processes; start small and measure memory |
| `sampling.native_threads_per_worker` | Native threads, default 1; environment thread vars must agree |
| `decoders.NAME.weight_scale` | Common integer objective quantization; changes decoder identity |
| `decoders.NAME.output_mode` | `compact` or `full_witness`, with distinct tie identities |
| `storage.save_shot_results` | Save nullable compact rows for arbitrary exact reanalysis cuts |
| `storage.retained_uniform_samples_per_case` | Bounded unbiased diagnostic row selection |
| `storage.retained_failure_samples_per_case` | Bounded failure examples; biased, not a rate estimator |
| `timing.warmup_shots` | Per-chunk warmup using already sampled rows |
| `timing.latency_sample_count_per_case` | Bounded replay calls, separate from primary throughput |

Only d and p are sweep axes. Use separate configs for R=2/3/4/5; `d`, `2*d`
and v2 round-rule expressions are not accepted here. Keep z preparation,
X sign sector, Z readout, `prefix_frame_only`, `adaptive: false`,
`stop_rule: fixed_shots`, `noise: {profile: hex_legacy}`. This phase has no
adaptive stopping, teleportation, factory or color-code runner.

The [larger sweep template](../configs/templates/surface_prep_fixed_sweep.yaml)
is an **unexecuted opt-in example**, with d3/5/7/9 and 10,000 shots per point.
Check its entire grid and measure selected-point time/memory before launching
it. Nothing in bootstrap, tests or analysis launches it. User experiment YAMLs
and existing outputs are not changed by these examples.

## Cuts, confidence intervals and saved outputs

```bash
bash scripts/python.sh -m knill_bench.cli analyze "$RUN" \
  --output "$RUN/analysis/custom_cuts" \
  --gap-threshold=-inf --gap-threshold=0 --gap-threshold=2.5 --gap-threshold=inf
```

Acceptance is **X baseline valid AND X complement valid AND Z decoder valid
AND gap>=g**. This is an offline cut on fixed-R data. Thresholds never change
sampling or select which trajectories are simulated. The default grid is
-inf,0,1,2,4,8,16,32,64,+inf. Arbitrary cuts require saved compact shot rows;
aggregate-only runs support exactly saved bin edges and +/-inf, without
interpolating counts. Cuts are inclusive, unlike the separate notebook strict
`>` policy. Empty accepted sets have null conditional rates.

| Analysis output | Content |
|---|---|
| `report.md` | Counts, graph premises, limits, cost table, figures and exact reanalysis command |
| `validation_summary.json` | Pass/fail and reasons, saved source/graph/file hashes, individual model/witness checks |
| `conditional_rates.parquet` | Gap bins, occupancy, per-metric and common-valid denominators/events, Wilson endpoints |
| `threshold_curve.parquet` | Attempts/accepted/invalid/valid rejects, events, A/U/Q and Wilson endpoints |
| `joint_counts.json` | Eight cells indexed 4*E_X+2*E_Z+E_LZ overall, per bin and cut |
| `paired_comparisons.json` | Same-sample decoder event cells 00,01,10,11 and disagreements, or explicit unavailability |
| `preparation_summary.json` | Saved independent baseline counts, replay timings and measured resource scopes |
| `figures/` | Sign-gap, logical-gap, acceptance-risk and synthetic spatial-freezing figures; 300 dpi PNG/PDF/SVG |
| `retained_examples/` | Original chunk/sample identity, packed rows, same-solve constraints/paths and the synthetic graph example |

A=accepted/all attempts, U=accepted errors/all attempts, Q=accepted errors/
accepted. X/Z/code/logical unconditional metrics retain separate validity
masks; bin tables also provide a common gap-valid comparison. Code-correct
conditional logical risk is P(E_LZ | E_code=0,accept), not an X-only condition.
Every zero-error point has a positive 95% Wilson upper bound, and zero
observations give null. The intervals are approximate, pointwise fixed-shot
intervals. Curves are exploratory, without simultaneous or data-selected-cut
coverage claims. A tiny smoke cannot resolve rare errors or prove a risk trend.

Gap is the cost difference of two independent-DEM minimum representatives,
with all spatial ports frozen and both temporal parities flipped. Its units
are integer cost divided by weight_scale. It is not posterior log odds.
The checked graph statement is that the XOR support contains a past-to-future
path; it does not identify a sampled physical fault or prove fault tolerance.
See [report definitions](preparation_reports.md), [execution](preparation_execution.md),
[decoder/metrics](preparation_decoder.md), [theory](temporal_preparation_theory.md)
and [recorded test/smoke results](../TEST.md).

Actual prompt-05 final results: [921-test gate and bounded end-to-end smoke](preparation_validation_report.md).
