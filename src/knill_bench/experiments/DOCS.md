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
- `dispatcher.py`: lazy kind dispatch to `run(document)`; Fig.4(d) is B1,
  factory still raises before output creation until B2. Missing dependencies
  within an installed runner propagate.
- `cli.py`: separate `knill-bench-v2 validate-config/prepare/run/resume/plot-fig4d`;
  v1 CLI and schemas are unchanged. `prepare` writes pending infrastructure only.

See [the complete B0 specification](../../../docs/auxiliary_v2.md) for YAML
fields/defaults, public shapes/equations/filenames, lock ownership, crash/rename
limits, metadata hashes, actual seed consumption versus derivation, required
commands and remaining B1-B3 work. `RunStore` is synchronous in one parent;
native handles and point writers stay local to their worker. No YAML eval,
per-shot constructors, oracle-driven selection or scientific claims are added.

## B1 execution

`fig4d_reproduction.run(document, resume_path=None)` enforces T=8, r_0=r_plus=d,
no theta and False prior mode before output. It constructs a HexFullKnill per
point, advances one sampler seeded with point_seed, and streams bounded batches
including the exact final partial batch. Workers > 1 use spawn and at most
workers pending whole-point tasks. Native objects stay in workers; only small
PointResult/execution descriptors return to the parent. `record_complete`
accepts optional nested JSON execution metadata, copied/validated before the
completion marker. No B0 schema/filename or v1 numerical API changes.

Dispatcher now executes Fig.4(d), while factory remains an explicit B2 error.
`dispatcher.resume(path)` loads the saved document and uses B0 exact-environment
restart checks. CLI adds `resume RUN` and `plot-fig4d RUN --output FILE`.
Preparation still samples nothing. See [the B1 guide](../../../docs/fig4d.md)
for precise physical, seed, failure, metadata and unmeasured production limits.
