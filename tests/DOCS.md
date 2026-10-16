# Bench regression tests

The original `test_circuits`, `test_decoding`, `test_execution` and
`test_analysis_plotting` files exercise v1 signed circuit/DEM invariants,
native comparisons, bounded execution/resume/streaming, statistical summaries
and plots. They remain unchanged. Some inherited static Hex fixtures sample
256 shots; B0 adds no physical Monte Carlo or large sweep.

`test_v2_config.py` validates both examples, strict fields/rules/axes/SafeLoader,
full literal-plus filenames, float identity, schedule/policy-independent seeds,
phase dispatch and the separately installed CLI. `test_v2_storage.py` uses
synthetic <=7-row points to check typed nullable schemas, one streaming writer
per table, aligned IDs, footer/promotion order, append/rename/metadata failures,
clean restart, collisions, provenance, parent ownership and source/config
validation. Actual H5 API inspection is read-only and forbids scientific
construction. No test needs network access or benchmark data.

Run `.venv/bin/python -m pytest -q` after the normal editable/bootstrap setup.
[TEST.md](../TEST.md) records exact commands/results and setup corrections.
[The B0 guide](../docs/auxiliary_v2.md) documents new contracts and limits.
