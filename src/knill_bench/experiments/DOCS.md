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
- `dispatcher.py`: lazy kind dispatch to `run(document)` for B1 Fig.4(d) and
  B2 factory. Missing dependencies within an installed runner propagate.
- `cli.py`: separate `knill-bench-v2 validate-config/prepare/run/resume/plot-fig4d/analyze-factory`;
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

Dispatcher executes Fig.4(d), with factory execution added in B2 below.
`dispatcher.resume(path)` loads the saved document and uses B0 exact-environment
restart checks. CLI adds `resume RUN` and `plot-fig4d RUN --output FILE`.
Preparation still samples nothing. See [the B1 guide](../../../docs/fig4d.md)
for precise physical, seed, failure, metadata and unmeasured production limits.

## B2 execution

`logical_zero_factory.compile_point(point, seed=..., create_codecapacity_dem=False)`
returns the native Hex bundle and CompiledFactory. `run(document, resume_path=None)`
uses one model per point and B0's paired writer, stores every final error and
per-stage float64 gap, and records compact role/size/policy/model metadata.
No physics is reimplemented here. False uses finite unit-Hamming gaps even at
p0; supported True uses log_weight projected gaps. Hex support errors propagate;
missing/nonfinite/negative gaps or unresolved frames fail paired output.

`execution.execute_points(store, worker, **worker_options)` now supplies the
common B1/B2 bounded spawn scheduler, point-seeded arguments, parent-only
completion and resume skipping. Native objects remain local to a whole-point
task, not per chunk. Theta is absent from factory compilation/worker options;
all fixed-T trajectories are sampled and saved. No cuts/retries/costs are
computed. See [the B2 guide](../../../docs/logical_zero_factory.md) for exact
shapes, terminal/operational boundaries, policy restrictions and tested limits.

## B3 CLI

`analyze-factory RUN [--settings FILE] [--theta VALUE ... | --theta-grid START STOP COUNT]`
reads saved pairs only. `--iid-restarts` explicitly enables renewal accounting;
`--output FILE` optionally writes .json/.csv/.md, otherwise prints JSON. Cost
assumptions live in a separate strict analysis YAML, never new simulation
sweep axes. `--theta=-inf` provides the no-cut identity. The CLI also reports
filesystem errors clearly. Runners, seeds, samplers and paired storage are
unchanged. See [B3](../../../docs/factory_analysis.md) and
[getting started](../../../GETTING_STARTED.md) for exact reproduce commands.
