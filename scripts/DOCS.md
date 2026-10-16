# Scripts and entry points

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
The B1 shell runner is described below; factory execution still stops at B2.
See [the B0 guide](../docs/auxiliary_v2.md) for
commands, exact outputs and the phase boundary. Source-module documentation
lives in [experiments](../src/knill_bench/experiments/DOCS.md).

## B1

`run_fig4d.sh [CONFIG]` invokes the independent v2 `run` command using the
repository .venv, with KNILL_PYTHON override supported. Its default is the
deliberate production `configs/fig4d.yaml`; tests/bootstrap do not launch it.
One optional config path is accepted. Relative output_root follows invocation
working directory. Resume and optional saved-data plot commands are in
[the B1 guide](../docs/fig4d.md). Factory execution is still B2.
