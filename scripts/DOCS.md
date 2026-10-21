# Scripts and entry points

## Factory wall-time diagnosis

`profile_factory.py CONFIG --distance D --p P --output NEW.json` measures one
selected real v2 factory point. It uses seven diagnostic shots by default,
independently of the config's shot/worker budget, and runs one process. Optional
`--prior configured|hamming|projected` changes only the selected inference mode
for an explicit comparison. Sampling/decoding/writing call the actual bench
worker with original seed and bounded batches; physical temporary tables are
removed afterward. It never dispatches the config's full sweep or resumes data.

Runtime-only wrappers on unchanged Hex/bench functions record nested inclusive
and exclusive wall/CPU times, projected fault/group counts, native BLAS thread
counts, source hashes and peak RSS. Wrappers are restored on exit. A Linux
SIGALRM bounds the point (default 180 seconds), saving partial timings and a
timeout status if needed; timeouts are not completed simulation results.
`--cprofile` adds .pstats/.pstats.txt for call-site diagnosis and can substantially
increase Python-loop timings. Use the default wrapper-only mode for primary
wall-time comparisons. `--trace-validation` records per-line elapsed time in
FactoryCircuitBundle.validate, including native child calls; compare its line
proportions within that run. Existing output JSON is refused. Results belong under
ignored results/, not committed experiment artifacts. See
[the measured report](../docs/factory_performance_report.md).

The fixed-distance T diagnostic uses separate fixed-T configuration snapshots;
it does not add a simulation sweep axis. See the
[d7 T-scaling report](../docs/factory_T_scaling_report.md) and ignored
`results/factory_T_scaling_d7/measure.sh` / `summarize.py` for the exact run and
saved-profile plotting commands. Per-shot sampling/decode throughput and full
point time divided by the shot count are reported separately. First attempts
are separated from same-process warm repeats; error bars are observed ranges,
not statistical confidence intervals. Timing experiments are opt-in and are
never part of the unit-test suite.

The follow-up [distance-scaling report](../docs/factory_distance_scaling_report.md)
fixes T=3 and measures d=3/5/7/9/11 with preparation depths equal to d. Exact
configs, serial measurement commands and saved-only plotting code live in
ignored `results/factory_distance_scaling_T3/`. Its 1,024-shot timing attempts
are explicitly requested diagnostics, not new unit-test fixtures. It retains
the same cold/warm and sampling/decode versus full-point timing definitions.

## Current Conda and cluster commands

`bootstrap.sh` now uses environments.yaml to create/update Conda knill_system,
checks the same fork revisions and installs all four packages editable. Numeric
dependencies remain pinned; requirements-research.lock adds the research and
build environment. Existing checkout mismatches are preserved/refused.
`python.sh` selects KNILL_PYTHON when supplied, otherwise the active named
Conda environment or `conda run -n knill_system`. Both experiment wrappers,
v1 simulation and latency wrapper use it; no wrapper depends on .venv.

`build_cluster_bundle.py [--download-deps] [--output NEW_DIRECTORY]` builds
four wheels from temporary copies. It verifies exact clean dependency pins,
includes Hex matrices and source manifests, checks resource hashes in the
wheels and optionally builds/downloads all pip dependencies as wheels. The
bundle's install.py verifies checksums and supports offline pip installation;
Conda Python itself is provisioned separately. Fork repositories are unchanged.
The source-checkout development bootstrap and target installed-wheel workflow
are documented in [cluster setup](../docs/cluster_setup.md). Historical .venv
notes below describe the earlier B0-B3 setup.

`bootstrap.sh` safely verifies the designated dependency worktree revisions,
installs `requirements.lock` plus the three editable forks and bench into
`.venv`, then validates the original smoke config. B0 updates only the Hex pin
to HEX-N2 86c9495094801012b9912bd41935ae48b08d8f92; no dependency checkout is
reset or modified. `run_simulation.py/.sh` and `benchmark_latency.sh` retain
v1 behavior. Existing `verify_*`, `benchmark_refactor.py`, `compare_performance.py`
and `stress_memory.py` remain opt-in v1 diagnostic/performance utilities;
unit tests do not launch benchmark sweeps.

The separate new `knill-bench-v2` console script (or
`python -m knill_bench.experiments.cli`) validates/prepares B0 configurations.
The B1/B2 shell runners are described below.
See [the B0 guide](../docs/auxiliary_v2.md) for
commands, exact outputs and the phase boundary. Source-module documentation
lives in [experiments](../src/knill_bench/experiments/DOCS.md).

## B1

`run_fig4d.sh [CONFIG]` invokes the independent v2 `run` command using the
repository .venv, with KNILL_PYTHON override supported. Its default is the
deliberate production `configs/fig4d.yaml`; tests/bootstrap do not launch it.
One optional config path is accepted. Relative output_root follows invocation
working directory. Resume and optional saved-data plot commands are in
[the B1 guide](../docs/fig4d.md).

## B2

`run_logical_zero_factory.sh [CONFIG]` mirrors the B1 wrapper for the new native
Hex factory runner. Default configs/logical_zero_factory.yaml has T=1, d=3/5,
10,000 shots/point and False priors; the separate small example exercises T=2.
Tests/bootstrap do not launch the default sweep. KNILL_PYTHON, optional path
and relative output behavior match run_fig4d.sh. See
[the B2 guide](../docs/logical_zero_factory.md) for resume, physical and gap
conventions and the B3 analysis boundary.

## B3 commands and starter templates

The installed v2 CLI adds saved-only analyze-factory; no new shell/performance
sweep is run automatically. Optional report settings and both small simulation
templates are in configs/templates. [Getting started](../GETTING_STARTED.md)
provides setup/copy/run/resume/plot/analyze commands, public APIs and exact
dependency refs. Large Fig.4(d)/factory jobs remain the explicit wrappers above.

## Local versus historical factory profiling

profile_factory.py now treats configured/projected/local True as the current
module_local_stim_dem policy. --prior legacy-projected is a diagnostic-only
replay of pinned Hex H5's original full-prefix setup; no config/source edits
are made. --repeat N creates N independently seeded attempts in temporary
subdirectories in one process, retaining only DEM/graph cache state. Timings
include per-attempt deltas, local cache counts, strict Stim extraction and
legacy projection/merge counters. A fresh process/cache is used by default.
All ideal analysis boundaries and inference model differences are explicit
in the report; speed comparisons do not establish equal inference quality.

The profiler honors factory config skip_circuit_validation and records it.
It times both native and packed preparation-frame resolution, packed-map setup,
and the private H5 construction path that omits full validation. Opt-out means
zero setup.bundle_validation calls. legacy-projected diagnostics require full
validation and reject a config opting out. Runtime instrumentation is confined
to the diagnostic process and is restored on exit, including timeout.

## PBS cluster execution

`cluster_run_simualtion.sh` (user's original spelling retained) now invokes the
v2 CLI for either experiment after activating KNILL_CONDA_ENV (default
knill_system). CONFIG_FILE defaults to the small factory template; RESUME_RUN
selects saved-run continuation. Worker count comes directly from the input
YAML (or saved YAML on resume); set it to match the single-node PBS allocation.
The wrapper runs one CLI command without --workers, allocation inference or
nodefile checks. PBS_NCPUS/PBS_NODEFILE/WORKERS do not affect its invocation;
mpiprocs is not required. BLAS/OpenMP threads are 1. Setup stays on the login
node, via the exact-ref Conda bootstrap. See
[clone/setup/qsub instructions](../docs/cluster_setup.md).

## Ordinary SE memory launcher

run_se_memory.sh [CONFIG] invokes the v2 run command through python.sh; default
is configs/se_memory_v2_example.yaml (small d3/5 example, not launched by tests).
PBS cluster_run_simualtion.sh already accepts this kind via CONFIG_FILE.
Same Conda selection/YAML worker settings apply; no extra dependencies or cluster
script changes are required. See [memory guide](../docs/se_memory.md).




BENCH-N1 advances only Hex's exact source pin to existing HEX-N2 86c9495;
bootstrap still preserves/refuses mismatched checkouts. Both other fork refs,
Conda/numeric locks and package versions are unchanged. Custom factory example
validation uses the existing v2 CLI/wrappers; no production job is launched.

## General Knill EC wrapper

run_knill_ec_memory.sh [CONFIG] uses python.sh and the v2 run command; its
default is the tiny configs/templates/knill_ec_memory.yaml. The legacy
run_fig4d.sh retains its filename/default config and uses the new kind in that
config. plot-knill is the saved-data plotting CLI, with plot-fig4d alias.
See [noise revision](../docs/knill_ec_noise_plan.md). PBS remains unchanged.

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.
