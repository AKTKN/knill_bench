# Getting started: auxiliary-system experiments

This branch supplies two schema-v2 experiments and saved-data analysis:

| Experiment | Physical stages | Final readout | Saved point files |
| --- | --- | --- | --- |
| Fig.4(d) full Knill | Eight full Knill stages; configurable noisy SE preparation, default d rounds on each Bell resource | Noisy Z | logical_error |
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

Hex is pinned to factory-noise HEX-N2 `86c9495094801012b9912bd41935ae48b08d8f92`,
on the H5 lineage.
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

The simulation templates have d3/5, p0/.001, 64 shots per point, automatic
time-adaptive chunks and one worker. Edit only d and p as sweep axes. Round rules accept literal
`d`, a positive integer, or a quoted positive multiple such as `"2*d"`,
`"2/3*d"` or `"1.5*d"`. Exact rational arithmetic floors the result for each
distance: `"2/3*d"` gives 2 rounds at d=3 and 3 at d=5. A result below one
is rejected. General expressions such as d-2 are unsupported. T, decoder, prior,
workers, shots and seed are fixed per run. Unknown keys/duplicate YAML fail.

Use `batch_size: auto` (or omit it), `target_chunk_seconds: 1.0` and
`buffer_shot: 10000` to let measured sampling/decode time set chunk sizes while
writing result rows in bounded groups. Multiple workers can share a single
point. Integer batch_size keeps fixed partitioning for exact seeded replay;
auto partitions depend on timing. See [parallel execution](docs/parallel_execution.md).
For PBS, set `workers` in the YAML to match the single-node CPU allocation;
the launcher passes the config directly to `run`. Direct CLI use also supports
`knill-bench-v2 run my_factory.yaml --workers 8` as an explicit override.
PBS/Conda clone, setup and submission instructions are in
[cluster setup](docs/cluster_setup.md).

Factory T defaults to one; set T_tel=2 or 3 for fixed role-swapping stages.
r_0 applies once to initial zero preparation; r_plus applies to each initial/
refresh plus preparation. A trajectory produces one final survivor. Full Knill
requires T_tel=8, False priors and theta:null. The standard Fig.4(d)
configuration uses r_0=r_plus=d; changing the depths runs a preparation-depth
variant through the same eight-stage protocol.

For example, either simulation template can use:

```yaml
r_0: "2*d"
r_plus: "2/3*d"
```

Check resolved depths before sampling with `knill-bench-v2 validate-config
my_fig4d.yaml` (or my_factory.yaml). The printed points show integer r_0/r_plus.

Keep `create_codecapacity_dem:false` initially. False uses finite Hamming gaps
even at p0. True now uses module-local Stim DEMs with cached matching graphs.
Its prior EXCLUDES preparation and earlier-stage residual errors; the actual
noisy preparation and causal frames remain in the simulation. See the
[factory guide](docs/logical_zero_factory.md) for the input boundary and
analysis-only Pauli observable. p0 True remains unsupported; structural errors
raise without fallback. Historical projected, local and Hamming gaps are not
interchangeable. Start a new run after this model change; old saved data can
still be analyzed with their original policy labels.

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

`analyze-factory` reads the saved `config.yaml` and Parquet files inside
`$FACTORY_RUN`. Its `--settings` argument is the analysis/cost configuration,
not the simulation configuration. Repeating it recomputes the analysis and
rewrites the requested report; it does not start or resume a simulation.
Editing my_factory.yaml does not update `$FACTORY_RUN`. After changing a
simulation configuration, start a new experiment and update that variable:

```bash
FACTORY_RUN=$(knill-bench-v2 run my_factory.yaml)
echo "$FACTORY_RUN"
knill-bench-v2 analyze-factory "$FACTORY_RUN" --settings my_analysis.yaml --output "$FACTORY_RUN/factory_report.md"
```

Every `run` starts fresh, even with the same config. Use `resume RUN` only
when continuing an existing experiment.

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
agreement. Its vertical axis is labeled `logical error rate`; this is errors
per complete eight-stage shot. Existing saved runs can be replotted with the
same plot command without resimulation. The distinct large opt-in jobs are:

```bash
bash scripts/run_fig4d.sh configs/fig4d.yaml
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory.yaml
```

The Fig.4(d) job has d9/11/15/21, 100,000 shots per point and an explicitly
approximate p=.004..010 grid. The default factory job has 10,000 shots per
point. Neither job runs during bootstrap or unit tests.

## 5. Inspect outputs and resume safely

New v2 runs use `results/<YYYYMMDDHHMMSS>_<config_hash8>_<name>/`, relative to
the invocation working directory unless output_root is absolute. The timestamp
is Japan time (Asia/Tokyo); the eight hex digits are the prefix of the canonical
simulation-config SHA256. For example,
`results/20261016155547_2242fc7d_factory_v2_example/`. A name collision advances
the directory timestamp by one second; it never reuses completed data. Actual
start/end timestamps and the full hash remain in metadata. Legacy run names
remain usable. Each run contains exact config.yaml, one metadata.json and
one/two Parquet tables per completed d/p point.

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

For unexpectedly slow factory setup, see the measured
[wall-time report](docs/factory_performance_report.md). The opt-in diagnostic
profiles one selected point without running the config's full shot/worker
budget or changing existing results:

```bash
python scripts/profile_factory.py configs/logical_zero_factory_v2_example.yaml \
  --distance 3 --p .001 --shots 7 --output results/profile_factory_d3.json
```

Select d/p values present in your config and a new output filename. True mode
constructs a local DEM once per distinct canonical module and reuses it across
stages. `--repeat 2` measures a fresh-seeded warm-cache attempt in the same
process; `--prior legacy-projected` explicitly replays the old H5 inference for
diagnostic comparison only. JSON records partial timings at the wall limit.

Factory simulation YAML also accepts `skip_circuit_validation: true` to skip
the expensive full physical bundle check during compilation. The default is
`false` (one full check). This does not change the physical circuit, prior,
sampling or matching decisions; decoder/sign/model checks still run. It is
not a saved validated-circuit cache. Both factory prior modes use packed
preparation-frame arithmetic. See [the factory guide](docs/logical_zero_factory.md)
for the exact scope. Fig.4(d) does not accept the opt-out.

## Ordinary syndrome-extraction memory

Copy `configs/templates/se_memory.yaml` and run it through the same v2 CLI or
PBS script (`CONFIG_FILE=my_memory.yaml`). Use `kind: se_memory`, `rounds: d`
and optional `get_logicalgap: true`; Knill resource/teleportation/prior fields
are not accepted for this kind. Initial physical-zero reset and final Z are
noisy, and total noisy SE count is exactly rounds. Requested complementary
gaps require 0<p<0.5 and a supported positive-weight graphlike circuit DEM;
p0 works with the option false. The additional file uses the same shot IDs
and gap_t001 for the entire memory experiment. See [memory guide](docs/se_memory.md).




## Factory custom physical noise

Copy [the seven-shot custom template](configs/templates/logical_zero_factory_custom_noise.yaml)
and follow [the noise/timing guide](docs/factory_custom_noise.md). The ordinary
factory shell wrapper/CLI runs it in both fixed and auto chunk modes. Custom
noise is supported only by logical_zero_factory; Fig.4(d) and SE memory raise
before output. Schema-v1 explicit profiles are unchanged. The guide separates
physical idle exposure from the local inference window and documents resume.
