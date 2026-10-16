# Scripts and entry points

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
to H5 4278d2900626f1d120d611f209340b20a9370f91; no dependency checkout is
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
