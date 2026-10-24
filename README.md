# knill_bench

Reproducible physical Stim memory experiments comparing repeated surface-code syndrome extraction with three Knill strategies. The package uses the requested Hex checkout and user-owned LOM/surface-sim forks. It keeps circuit identity, decoder choice, classical work, and live hardware resources separate.

Fixed-R surface preparation is beginning on `surface-prep-fixed`. The
[theory and typed contract](docs/temporal_preparation_theory.md) fixes the
output-state labels, offline temporal boundaries and two-solve gap definition.
Only contracts and synthetic-tested decoder kernels are available at this
stage; `surface_prep_fixed` circuit/config/CLI execution is not yet integrated.

Saved v2 datasets can also be compared from notebooks with lazy keyed path
registration, six editable figure types and `plotting_lib` APS styling at
300 dpi. Five non-stacked figures include pointwise 95% Wilson shades
(paired Wilson-derived bounds for LER reduction). See [the notebook guide](docs/notebook_plotting.md) and
[the example notebook](notebooks/saved_figures.ipynb).

The research environment is now **Conda `knill_system`**. Run bootstrap below
or see [Conda/cluster setup](docs/cluster_setup.md) for environments.yaml,
locked notebook/analysis tools and resource-complete offline wheel bundles.

The `auxiliary-system` branch also supplies independent **schema-v2
experiments**: strict d/p-only configurations, compact provenance, streamed
point-level Parquet output, the **B1 eight-cycle Fig.4(d) runner** and the
**B2 two-block logical-zero factory runner**. See [the v2 contract](docs/auxiliary_v2.md),
[Fig.4(d) guide](docs/fig4d.md) and [factory guide](docs/logical_zero_factory.md).
**B3** adds saved-data acceptance, conditional oracle-error and explicitly
assumed attempt/restart-cost analysis. Start with [GETTING_STARTED.md](GETTING_STARTED.md)
and the runnable [factory](configs/templates/logical_zero_factory.yaml),
[Fig.4(d)](configs/templates/fig4d.yaml) and
[analysis](configs/templates/factory_analysis.yaml) templates.
Existing commands below retain schema-v1 behavior.

```bash
bash scripts/bootstrap.sh
conda activate knill_system
bash scripts/run_simulation.sh configs/smoke.yaml
python -m knill_bench.cli analyze results/<run-directory>
python -m knill_bench.cli benchmark-latency results/<run-directory> --workers 1
```

The smoke configuration has distances 3/5, X/Z memories, one/two cycles, 64 shots per physical point, two workers, and four timed individual calls per case. The larger benchmark is supplied but is never launched by bootstrap or tests.

| Stable protocol | Fresh A/B preparation | Post-CNOT SE | Intended decoder |
|---|---|---|---|
| `se_memory` | None | One ordinary X/Z SE round per memory cycle | Full-history PyMatching; selectable global BP-LSD |
| `knill_hex_dminus2` | Exactly d−2 rounds each | None | Native Hex preparation repair, Bell decoding, frame propagation, final decoding |
| `knill_aft_postgate` | One round each | One full X/Z round on **D, A, B after each CNOT** | LOM; selectable global BP-LSD |
| `knill_aft_prep_only` | One round each | None | LOM; selectable global BP-LSD |

Each Knill cycle executes `CX(B,A)`, optional SE, `CX(D,A)`, optional SE, then `MX(D)` and `MZ(A)`. B becomes the new memory. Ancilla preparation does not insert SE on D. The optional `gate_operands` scope is labeled separately in every case.

```bash
python -m knill_bench.cli validate-config configs/benchmark.yaml
python -m knill_bench.cli build configs/benchmark.yaml
python -m knill_bench.cli run configs/benchmark.yaml   # deliberate larger run
python -m knill_bench.cli resume results/<run-directory> --workers 2
python -m knill_bench.cli validate-references
python -m knill_bench.cli audit-faults results/<run-directory> --budget 12
python -m pytest -q
```

`build` writes circuit/model artifacts without sampling. `run` creates a new UTC timestamped directory. `resume` retains chunk identities and validates configuration, source, package, model, and environment compatibility. Worker count may change. Source changes require a new run. Analysis can be repeated; isolated timing replay appends separately labeled observations from retained uniform samples.

See [design](docs/design.md), [dependency provenance](docs/dependencies.md), [schemas](docs/data_schema.md), and [validation evidence](docs/validation.md). [Implementation report](docs/implementation_report.md) records the final smoke results and limitations.

Terminal full-history memory decoding does not by itself establish an online bounded-latency QEC architecture. The preparation length d−2 is an experimental choice, not a guarantee of gadget fault tolerance. Small smoke runs cannot establish thresholds or asymptotic exponents.


## Schema-v2 experiments

```bash
knill-bench-v2 validate-config configs/fig4d_v2_example.yaml
knill-bench-v2 validate-config configs/logical_zero_factory_v2_example.yaml
knill-bench-v2 prepare configs/logical_zero_factory_v2_example.yaml
# Deliberate production sweep; not a smoke test:
bash scripts/run_fig4d.sh configs/fig4d.yaml
knill-bench-v2 resume results/<fig4d-run>
knill-bench-v2 plot-fig4d results/<fig4d-run> --output fig4d.png
# Deliberate factory experiment; use the small v2 example for a smoke run:
bash scripts/run_logical_zero_factory.sh configs/logical_zero_factory.yaml
knill-bench-v2 resume results/<factory-run>
knill-bench-v2 analyze-factory results/<factory-run> --settings configs/templates/factory_analysis.yaml --output factory_report.md
```

`prepare` creates `{YYYYMMDDHHMMSS}_{config_hash8}_{experiment-name}/config.yaml`
(Japan time, with the simulation-config SHA256 prefix) and one
`metadata.json`, with pending points and no physical sampling. Fig.4(d) `run`
uses configurable preparation rounds on both resources (default d), eight full Knill stages and
noisy final readout. It streams one logical-error Parquet file per d/p and
records actual shot/error counts. The explicit production p grid is approximate;
the saved-data plot uses 95% Agresti-Coull intervals. Factory `run` uses Hex's
compiled one-bit stages with two reused supports and one terminal ideal
evaluation oracle. It writes aligned error/gap tables for all trajectories;
theta never controls sampling. Parent metadata marks complete points. Factory
acceptance and first-rejection costs are computed from saved files by
[the separate B3 helper](docs/factory_analysis.md), with no resimulation.

Both v2 experiments accept positive integers, `d`, and fixed round rules such
as `r_0: "2*d"` or `r_plus: "2/3*d"`. Multipliers use exact arithmetic and
floor to an integer at each distance; every resolved depth must be positive.
The standard Fig.4(d) configuration retains d rounds on both resources.
See [configuration syntax](docs/auxiliary_v2.md). The Fig.4(d) plot labels its
vertical axis `logical error rate` for the complete eight-stage experiment.

V2 `run CONFIG` always starts a new experiment directory. After editing a
simulation config, rerun it and update the saved run-path variable.
`analyze-factory RUN --settings ANALYSIS_YAML` only reanalyzes the data already
inside RUN; it does not execute a changed simulation config or resume sampling.

Hex is pinned to factory custom-noise HEX-N2 `86c9495` on the H5 lineage.
Dependency sources remain read-only during bench integration.
Factory `create_codecapacity_dem: true` now uses cached **module-local Stim
DEMs** in the bench adapter. Preparation/earlier-stage residual errors are
excluded from this prior only; noisy physical preparation and native frame
processing remain. This replaces the historical full-prefix projected policy.
Old runs can be analyzed with their original policy label, but require a fresh
run for this model change. See [factory model and cache](docs/logical_zero_factory.md)
and [measured wall times](docs/factory_performance_report.md).
Both factory prior modes now use equivalent packed preparation-frame arithmetic.
Factory YAML `skip_circuit_validation: true` skips the full construction-time
bundle check; omitted/false retains it. This option changes verification cost,
not physical sampling or decoding, and is not a validated-circuit disk cache.
Runtime sign and prior-model checks remain enabled. See the factory guide above.
The cluster builder adds matrix resources and build provenance in temporary
packaging copies; installed wheels can run without Git checkouts.
See [TEST.md](TEST.md) for regression results and
[the package map](src/knill_bench/DOCS.md) and [v2 contract](docs/auxiliary_v2.md)
for APIs, exact schemas, seeds, provenance, crash recovery and limits.

V2 defaults to time-adaptive parallel chunks: set `workers`, optional
`target_chunk_seconds` (default 1), and `buffer_shot` (default 10000).
Multiple workers can share one d/p point; results append in buffer-sized
Parquet groups. Integer `batch_size` retains the fixed execution/replay path.
The PBS launcher uses the YAML worker count directly. See
[parallel execution](docs/parallel_execution.md) for memory bounds, seeds
and [PBS / Anaconda clone instructions](docs/cluster_setup.md).

## Ordinary SE memory

V2 also supports `kind: se_memory`, using Hex's unmodified noisy physical-zero
initialization, d repeated X/Z syndrome-extraction rounds and noisy final Z.
`rounds` accepts d/integer/positive-multiple rules; `get_logicalgap: true`
adds a constrained opposite-observable-class MWPM decode and aligned
logical_gaps Parquet (one full-experiment gap_t001). Existing auto/fixed
execution, buffers, seed/provenance and restart rules are shared.
Start from [the template](configs/templates/se_memory.yaml), run
`bash scripts/run_se_memory.sh my_memory.yaml`, or set PBS CONFIG_FILE to it.
See [memory protocol, score definition and output](docs/se_memory.md).




Custom physical noise is factory-only: see
[noise/timing configuration](docs/factory_custom_noise.md) and the
[commented small template](configs/templates/logical_zero_factory_custom_noise.yaml).
Full Knill/Fig.4(d) and SE memory continue to require hex_uniform; v1 is unchanged.




The custom template executes through native Hex in both prior modes and both
bounded scheduling modes. Effective parameters/window durations and hashes
are saved with explicit local-prior scope and checked on resume/analysis.
Post-CNOT survivor idle is inside the local body; earlier storage idle stays
physical but outside that inference approximation.

## General Knill EC memory and physical noise

Use `kind: knill_ec_memory` for Hex-based full Knill EC, with positive T_tel
(default 8). `noise: noiseless_bellpair` idealizes both auxiliary preparations
and Bell-pair CNOT; `noise: code_capacity_noise` inserts only data
DEPOLARIZE1(p) before each teleportation. Both have ideal final readout.
hex_uniform retains noisy readout. See [the plan and implemented contract](docs/knill_ec_noise_plan.md)
and [tiny templates](configs/templates/knill_ec_memory.yaml). The old kind and
plot-fig4d command remain compatible; plot-knill is the general saved-data command.

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.

## General Knill EC and selectable inference

Use `kind: knill_sim` (or the existing knill_ec_memory) with any positive
T_tel. `create_codecapacity_dem: true` enables `codecapacity_prior:
module_local` (default, factory-style scope) or `full_prefix` (native causal
projection). False retains unit Hamming. Physical noise/readout is independent
of that choice. Full-prefix retains its structural limits and never falls
back. See [Knill simulation](docs/knill_sim.md) for exact scopes and tiny
[local](configs/templates/knill_sim.yaml)/[prefix](configs/templates/knill_sim_full_prefix.yaml) templates.
