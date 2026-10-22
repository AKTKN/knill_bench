# Independent schema-v2 experiment infrastructure (B0)

- `config_v2.py`: strict SafeLoader, `ConfigDocument`, `ExperimentConfig`,
  `ExperimentPoint`, `load_config`/`parse_config`, canonical identities and
  exact literal-plus filenames. Only d/p sweep, all other values are fixed.
  Preparation rules accept positive integers, d, or positive constants times d
  (e.g. `"2*d"`, `"2/3*d"`, `"1.5*d"`), with exact rational flooring.
  Parsing rejects any resolved depth outside [1,2^63-1] over the entire d grid;
  no eval/general expressions or new sweep axes are allowed.
- `seeds.py`: deterministic uint64 `point_seed`/`chunk_seed`; prior, theta,
  workers and shot count do not change physical sampling identity.
- `provenance.py`: actual imported Git/source-resource/dependency/CPU info
  and read-only H5 factory export validation; no physical object construction.
- `run_v2.py`: parent-owned `RunStore.create/resume/start_point/record_complete/
  finish/fail/close`. Atomic single metadata file, collision-free run
  directories, exact YAML bytes, clean full-point restart and completion marker.
  New names are `YYYYMMDDHHMMSS_<config_hash8>_<name>` using Asia/Tokyo time.
  Hash prefixes come from the canonical simulation config; metadata keeps the
  full hash and actual ISO UTC timestamps. Collision retries add one second.
  Create always reserves a fresh directory; legacy names can still resume.
- `dispatcher.py`: lazy kind dispatch to `run(document)` for B1 Fig.4(d) and
  B2 factory. Missing dependencies within an installed runner propagate.
- `cli.py`: separate `knill-bench-v2 validate-config/prepare/run/resume/plot-fig4d/analyze-factory`;
  v1 CLI and schemas are unchanged. `prepare` writes pending infrastructure only.
  Help distinguishes `run CONFIG` (new experiment) from `resume RUN` and
  `analyze-factory RUN --settings ANALYSIS_YAML` (saved-data analysis only).

See [the complete B0 specification](../../../docs/auxiliary_v2.md) for YAML
fields/defaults, public shapes/equations/filenames, lock ownership, crash/rename
limits, metadata hashes, actual seed consumption versus derivation, required
commands and remaining B1-B3 work. `RunStore` is synchronous in one parent;
native handles and point writers stay local to their worker. No YAML eval,
per-shot constructors, oracle-driven selection or scientific claims are added.

## B1 execution

`fig4d_reproduction.run(document, resume_path=None)` enforces T=8,
no theta and False prior mode before output. Standard paper settings use
r_0=r_plus=d; positive integer/multiple depth variants are also supported.
It constructs a HexFullKnill per
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

## Conda and installed-wheel provenance

The active research interpreter is Conda knill_system (Python 3.12.15), not
.venv. `provenance.source_info` preserves checkout provenance and additionally
accepts the cluster builder's _build_info.json after hashing every installed
Python/matrix resource. Wheel mode records checkout:null and install_kind:wheel.
Hex wheel mode requires the exact pinned HEX-N2 commit and verified ancestor marker plus
existing API checks; ordinary unstamped wheels are not silently trusted.
Source resume hashes remain strict. See [cluster setup](../../../docs/cluster_setup.md).

## Current factory True revision

compile_point routes True through adapters.hex_factory's cached module-local
Stim DEMs. Hex physical construction and causal frame/decode methods remain.
The prior excludes preparation/earlier-stage residuals, with explicit metadata
identifiers and scope; the physical circuit retains those errors. Both factory
prior modes use equivalent packed preparation-frame arithmetic with unchanged
native matching decisions. Physical identities/seed inputs are unchanged, but
prior_policy now identifies module_local_stim_dem. RunStore refuses resume
across policy changes before incomplete-file cleanup. Saved-only analysis
accepts historical projected data with the original label. See
[factory guide](../../../docs/logical_zero_factory.md) and the adapter DOCS.

Factory `skip_circuit_validation` defaults to false (one full native check).
True skips full bundle validation, including signed prefix-flow checks, while
keeping runtime decoding/sign/model checks. The parser rejects non-booleans
and True for Fig.4(d). The scheduler forwards it to each worker; execution
metadata declares the choice and frame implementation. False is omitted from
canonical config JSON to preserve existing default hashes, True is included.

## Current adaptive v2 execution (supersedes whole-point defaults above)

`adaptive_execution.py` supplies ChunkSizer/ChunkTask/ChunkResult/run_chunk and
execute_adaptive. Omitted/auto batch_size selects measured-time scheduling;
integer batch_size selects unchanged legacy whole-point execution. Each process
caches one point's physical model/decoder; chunk-seeded fresh samplers provide
worker-independent assigned-task streams. The parent holds the sole paired
PointWriter plus PointBuffer and an at-most-workers outstanding/reorder window.
Buffer-sized row groups and final publication/restart rules are independent
of compute chunk sizes. Auto timing can change partitions and actual samples;
use fixed mode for exact replay or common-raw-record prior comparisons.
`_prepare_point`/`_decode_chunk` share factory metadata and strict frame/gap
validation between both paths. No quantum/decoder physics changes.

Strict config adds buffer_shot (default auto=10000; fixed=batch_size) and
positive finite target_chunk_seconds (default 1, auto only). Old explicit
integer batch configs keep their canonical hash without the new options.
load_config(path, workers=N), dispatch(path, workers=N) and the CLI
run/prepare/validate-config --workers save effective YAML with source-input
SHA256; no override preserves original bytes. Resume uses saved settings.
See [full specification](../../../docs/parallel_execution.md).

## Ordinary syndrome-extraction memory

config_v2 adds se_memory plus rounds/get_logicalgap. Existing canonical hashes
are preserved by omitting new defaults for old kinds/points. Memory points
carry resolved rounds and an output-only flag; physical identity excludes the
flag and Knill filename placeholders. T=1/r_0=r_+=0 preserve filename keys;
an extra rounds key identifies the actual duration. One optional gap_t001
covers the complete trajectory. Config.gap_units drives run metadata.

se_memory.run uses the same RunStore, execute_points and PointBuffer/PointWriter
contracts, with strict requested-score checks. adaptive_execution now compiles
HexMemory and accepts its optional gap table; no old runner physics changes.
Point labels and gaps are returned only after full physical sampling. See
[memory guide](../../../docs/se_memory.md) for CLI/config/output semantics.




## BENCH-N1 factory custom noise schema

noise_v2.py maps strict custom YAML to Hex's frozen FactoryNoiseModel and
canonical nested YAML form without circuit construction. config_v2 adds optional
noise_model to configs/points while keeping noise as the short filename label.
Uniform None is omitted from canonical config/physical identity, retaining old
hashes/seeds. Custom full parameters enter both identities and pickle safely
for spawn. Probability products/idle domains are checked at every resolved
point before output; only factory accepts custom. Threshold/prior/workers/shots
remain outside physical seeds. Provenance/bootstrap pin HEX-N2 86c9495 and
inspect the optional noise_model builder interface. See
[custom noise](../../../docs/factory_custom_noise.md). N1 explicitly refuses
custom physical execution pending N2, while validate/prepare remain available.




## BENCH-N2 custom factory execution/provenance

The temporary N1 execution guard is removed. compile_point forwards the native
noise object through adapters.hex_factory in both prior modes. Existing
execution/adaptive_execution point transport and frozen keys carry full noise
without new worker arguments or scheduling logic; theta remains absent.
_prepare_point records native hashes plus full noise_parameters, actual
operation/readout probabilities, normalized window durations/application
counts and explicit post-control-in/storage-out local-prior flags.
noise_v2.execution_noise/validate_noise_execution cross-check custom metadata
without backend construction. RunStore checks it before parent completion and
completed resume; saved analysis checks the same fields. Factory run rejects a
mismatched external resume document before any incomplete-file cleanup.
Uniform provenance/cache/identity semantics are preserved. See
[the guide](../../../docs/factory_custom_noise.md) for exact fields and examples.

## General Knill EC memory revision

knill_ec_memory.run accepts positive T (default 8), no theta and False priors.
Scalar noise supports hex_uniform/noiseless_bellpair/code_capacity_noise via
Hex-owned policies. It shares _run_point and fixed/adaptive bounded execution
with Fig.4(d), and checks an external resume document before cleanup. New
metadata is validated before completion/resume; legacy kind canonical hashes
are unchanged. CLI plot-knill has plot-fig4d as an alias. See
[noise and compatibility](../../../docs/knill_ec_noise_plan.md).

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.

## knill_sim and explicit inference scope

config_v2 accepts general kind knill_sim and existing knill_ec_memory with
True priors and codecapacity_prior=module_local/default or full_prefix.
The option is inference-only, omitted from canonical False/default configs
and never added to physical points/seeds. The common runner passes it to
both fixed/adaptive worker setup/cache keys. RunStore uses config's explicit
prior_policy/projected_approximation and validates per-stage scope/model
metadata before completion/resume. Legacy Fig.4(d), factory and SE contracts
are unchanged. See [Knill simulator](../../../docs/knill_sim.md).
