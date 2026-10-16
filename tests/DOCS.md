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

## B1 regression coverage

`test_fig4d.py` parses the production config without building its circuits;
checks runner protocol guards; compares the exact d=3 T=8 module sequence
with fixed Hex; compares manual saved raw arrays/corrected records/labels
bit for bit with legacy global maps at T=2; tests d=3/5 zero-noise T=1 and
native reuse; verifies tiny streamed output/counts/metadata, point-seeded
replay, serial versus spawn streams, worker failure and whole-point resume.
Saved-data plotting/CLI, numerical Agresti-Coull fixtures and invalid counts,
missing/truncated/shuffled/count-tampered files are covered. New physical
fixtures use <=11 shots, never d=21 or the production sweep. The B0 dispatcher
test was updated again in B2 to verify both available kind dispatches.

## B2 regression coverage

`test_logical_zero_factory.py` uses the real Hex API at d3/5, p0 and small
positive p, T1/2/3, with <=7-shot fixtures. It checks two reused supports and
roles, noisy teleportation/ideal terminal readouts, finite Hamming gaps at p0,
actual projected gaps/units/hashes, raw seed equality across theta/prior mode,
oracle/future isolation, streaming exact counts/partial chunks/paired joins,
serial/spawn equality, no native construction during chunks, unsupported and
invalid-gap failure, and restart after a late chunk failure preserving complete
pairs and reproducing the original seed stream. No B3 cuts or costs are added.
Existing read-only Hex circuit/batch/surface-gap tests separately validate
signed flows, parity/frame boundaries, legacy-map equivalence, injected faults
and exhaustive d3 sector costs. Commands/results are recorded in TEST.md.
