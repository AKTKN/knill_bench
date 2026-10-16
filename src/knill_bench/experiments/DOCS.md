# Independent schema-v2 experiment infrastructure (B0)

- `config_v2.py`: strict SafeLoader, `ConfigDocument`, `ExperimentConfig`,
  `ExperimentPoint`, `load_config`/`parse_config`, canonical identities and
  exact literal-plus filenames. Only d/p sweep, all other values are fixed.
- `seeds.py`: deterministic uint64 `point_seed`/`chunk_seed`; prior, theta,
  workers and shot count do not change physical sampling identity.
- `provenance.py`: actual imported Git/source-resource/dependency/CPU info
  and read-only H5 factory export validation; no physical object construction.
- `run_v2.py`: parent-owned `RunStore.create/resume/start_point/record_complete/
  finish/fail/close`. Atomic single metadata file, collision-free UTC run
  directories, exact YAML bytes, clean full-point restart and completion marker.
- `dispatcher.py`: lazy kind dispatch to future B1/B2 `run(document)`; currently
  raises explicitly before output creation. Does not hide missing dependencies
  within a later installed runner.
- `cli.py`: separate `knill-bench-v2 validate-config/prepare/run`; v1 CLI and
  schemas are unchanged. `prepare` writes pending infrastructure only.

See [the complete B0 specification](../../../docs/auxiliary_v2.md) for YAML
fields/defaults, public shapes/equations/filenames, lock ownership, crash/rename
limits, metadata hashes, actual seed consumption versus derivation, required
commands and remaining B1-B3 work. `RunStore` is synchronous in one parent;
native handles and point writers stay local to their worker. No YAML eval,
per-shot constructors, oracle-driven selection or scientific claims are added.
