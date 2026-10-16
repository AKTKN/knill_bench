# Getting started: auxiliary-system experiments

This branch supplies two schema-v2 experiments and saved-data analysis:

| Experiment | Physical stages | Final readout | Saved point files |
| --- | --- | --- | --- |
| Fig.4(d) full Knill | Eight full Knill stages; d noisy SE rounds on each Bell resource | Noisy Z | logical_error |
| Logical-zero factory | Fixed T>=1 one-bit stages on two reused supports | One ideal Z evaluation oracle | logical_error + logical_gaps |

Factory conditional error rates describe the terminal **factory oracle**;
they are not online data-Knill error rates. Production paper agreement has not
been established. Start with the small templates below.

## 1. Set up the pinned environment

From the repository root, create/update the Conda research environment:

```bash
bash scripts/bootstrap.sh
conda activate knill_system
python -m pip check
```

The environment uses Python 3.12.15 and pip-installed locked numerical,
analysis, plotting and notebook tools. Bootstrap preserves existing fork
checkouts, verifies exact revisions, and installs the forks/bench editable.
`.venv` is no longer used. In batch jobs use `conda run --no-capture-output -n
knill_system ...`; the shell wrappers select this environment automatically.
See [the cluster/Conda guide](docs/cluster_setup.md) for `environments.yaml`,
research locks, resource-complete wheels and offline cluster installation.

Hex is pinned to H5 `4278d2900626f1d120d611f209340b20a9370f91`.
LOM is pinned to `b55a7a65969a106a547622287b620f0da2cb5e39`, surface-sim to
`493f800a3b4e9f80a6a569eb92d3c962dd6b09ad`. Do not reset the user's other
dependency worktrees. Bench phase history is B0 `4446bc2`, B1 `58cff21`,
B2 `034e711`; B3's final commit is reported in the implementation handoff.
Use `git rev-parse HEAD` for the current bench revision.

## 2. Copy a runnable configuration template

```bash
cp configs/templates/logical_zero_factory.yaml my_factory.yaml
cp configs/templates/fig4d.yaml my_fig4d.yaml
cp configs/templates/factory_analysis.yaml my_analysis.yaml
knill-bench-v2 validate-config my_factory.yaml
knill-bench-v2 validate-config my_fig4d.yaml
```

The simulation templates have d3/5, p0/.001, 64 shots per point, batches of 32
and one worker. Edit only d and p as sweep axes. Round rules accept literal
`d` or a positive integer, not expressions such as d-2. T, decoder, prior,
workers, shots and seed are fixed per run. Unknown keys/duplicate YAML fail.

Factory T defaults to one; set T_tel=2 or 3 for fixed role-swapping stages.
r_0 applies once to initial zero preparation; r_plus applies to each initial/
refresh plus preparation. A trajectory produces one final survivor. Full Knill
requires T_tel=8, r_0=r_plus=d, False priors and theta:null.

Keep `create_codecapacity_dem:false` initially. False uses finite Hamming gaps
even at p0. True is a projected approximation with structural restrictions;
p0 True is unsupported. A tested small positive-p True factory configuration
is d3, p=.001, r_0=r_plus=2, T=1/2. Unsupported models raise without fallback.
Hamming and log-weight gap cuts use different units.

## 3. Run the small factory and analyze saved data

```bash
FACTORY_RUN=$(knill-bench-v2 run my_factory.yaml)
echo "$FACTORY_RUN"
knill-bench-v2 analyze-factory "$FACTORY_RUN" --settings my_analysis.yaml
```

The last command prints JSON only. Optional output can be requested as JSON,
CSV or Markdown without resimulation:

```bash
knill-bench-v2 analyze-factory "$FACTORY_RUN" --settings my_analysis.yaml --output factory_report.md
knill-bench-v2 analyze-factory "$FACTORY_RUN" --theta=-inf --theta=1 --theta=2 --theta=inf --output factory_report.csv
knill-bench-v2 analyze-factory "$FACTORY_RUN" --theta-grid 0 5 11 --iid-restarts --output factory_cost.json
```

Acceptance requires every stage gap>=theta. Negative infinity retains all
shots; positive infinity rejects all finite gaps. No accepted shots means
conditional LER is undefined/null. All simulation shots remain saved regardless
of theta. Terminal labels score accepted shots; they never choose them.

The analysis template explicitly sets an assumed cost schedule. Defaults count
SE-equivalent work with serial initial preparation and zero assumed extra
overheads, not measured hardware durations. Specify reset, prep-decode,
teleport/readout, online-decode and restart costs in a consistent unit when
available. Parallel initial preparation is an explicit alternative assumption.
The ideal oracle has no operational latency charge.

`--iid-restarts` explicitly assumes fresh independent identically distributed
attempts and enables estimated E[attempt cost]/P(accept), with descriptive
paired uncertainty. Without that assumption, only attempt costs are reported.
No accepted samples leaves the ratio undefined. This is a single-factory
accounting model; no retry, queue or dynamic schedule was simulated. See
[the B3 equations and statistical limits](docs/factory_analysis.md).

## 4. Run and plot the small full-Knill experiment

```bash
FIG4D_RUN=$(knill-bench-v2 run my_fig4d.yaml)
knill-bench-v2 plot-fig4d "$FIG4D_RUN" --output fig4d_smoke.png
```

This checks the eight-stage execution path at small distances. The plot reads
saved labels and uses 95% Agresti-Coull intervals; it does not establish paper
agreement. The distinct large opt-in jobs are:

```bash
bash scripts/run_fig4d.sh configs/fig4d.yaml
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory.yaml
```

The Fig.4(d) job has d9/11/15/21, 100,000 shots per point and an explicitly
approximate p=.004..010 grid. The default factory job has 10,000 shots per
point. Neither job runs during bootstrap or unit tests.

## 5. Inspect outputs and resume safely

Every run is `results/<UTC-timestamp>_<name>/`, relative to the invocation
working directory unless output_root is absolute. It contains exact config.yaml,
one metadata.json and one/two Parquet tables per completed d/p point.

```text
logical_error__code=rotated_surface,d=3,p=0.001,noisemodel=hex_uniform,T=1,r_0=3,r_+=3.parquet
logical_gaps__code=rotated_surface,d=3,p=0.001,noisemodel=hex_uniform,T=1,r_0=3,r_+=3.parquet
```

Error tables have uint64 shot_id and bool logical_error. Factory gap tables
have identical IDs and float64 gap_t001..gap_tT. B2 requires finite, present
gaps. Metadata records counts, times, seeds, noise/readout/policy, actual Git
and imported source hashes. Completed metadata is the publication marker.
Analysis verifies schemas, IDs and actual counts before producing a report.

```bash
knill-bench-v2 resume "$FACTORY_RUN"
# Alternatively: prepare without sampling, then execute that prepared run.
PREPARED_RUN=$(knill-bench-v2 prepare my_factory.yaml)
knill-bench-v2 resume "$PREPARED_RUN"
```

Resume retains completed point files and restarts unfinished points at zero
with original seeds. It requires unchanged config/source/dependencies; start
a new run after changing those. Exact random replay also needs the same
batch partition, library version and platform. Saved-data analysis does not
require today's environment to match the simulation environment.

## Public interfaces and checks

- `experiments.config_v2.load_config(path)` -> ConfigDocument.
- `experiments.dispatcher.dispatch(config_path)` / `resume(run_path)` -> run path.
- `experiments.logical_zero_factory.compile_point(...)` -> native Hex bundle/compiled factory.
- `analysis.factory.analyze_saved(path, AnalysisSettings(...))` -> compact report mapping.
- `analysis.factory_cost.first_rejected_stage(gaps, theta)` -> 0 accepted or first rejected stage 1..T.
- `analysis.factory.write_report(report, output)` -> optional artifact path.
- `analysis.fig4d.summarize_saved(path)` / `plot_saved(path, output)` -> saved full-Knill statistics/figure.

```bash
python -m pytest -q
```

[TEST.md](TEST.md) records actual results, corrected failures and read-only Hex
integration tests. Existing schema-v1 commands remain `knill-bench` or
`python -m knill_bench.cli`; v2 commands are deliberately separate. Detailed
references: [v2 schema](docs/auxiliary_v2.md), [Fig.4(d)](docs/fig4d.md),
[factory](docs/logical_zero_factory.md), [B3 analysis](docs/factory_analysis.md).
