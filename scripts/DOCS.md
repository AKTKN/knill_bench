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
No B1/B2 shell runner is added yet, and its `run` command fails explicitly until
a scientific runner exists. See [the B0 guide](../docs/auxiliary_v2.md) for
commands, exact outputs and the phase boundary. Source-module documentation
lives in [experiments](../src/knill_bench/experiments/DOCS.md).
