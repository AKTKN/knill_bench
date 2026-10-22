# Schema-v2 auxiliary experiments: B0–B3

B1 now implements the Fig.4(d) runner, bounded point workers, resume and
saved-data Agresti-Coull plotting. See [the B1 guide](fig4d.md) for scientific
constraints, commands, actual seed use and validation. The foundation below
records the B0 contract. B2 adds the [two-block factory runner](logical_zero_factory.md)
with aligned per-shot error/gap output. B3 now supplies
[saved factory acceptance/oracle-quality/cost analysis](factory_analysis.md).
See [getting started](../GETTING_STARTED.md) and [configuration templates](../configs/templates/factory_analysis.yaml).

B0 supplies schema-v2 configuration, point identities/seeds, run directories,
compact provenance/metadata and streamed point-level Parquet storage.
Scientific Fig. 4(d), factory and acceptance/cost runners belong to B1, B2
and B3 respectively. B0 does not simulate either experiment, plot a paper
figure, or implement a worker pool. The dispatcher raises an explicit
`NotImplementedError` before creating outputs for an unavailable runner.

The existing schema-v1 CLI, configurations, scientific builders, decoder
adapters, table schemas and resume engine remain separate and unchanged.
Hex is imported read-only from the H5 `auxiliary-system` lineage, pinned in
bench to HEX-N2 `86c9495094801012b9912bd41935ae48b08d8f92` after the
separately requested factory-noise extension. B0 itself changed no Hex source. Export/signature/lineage validation never constructs a
physical circuit, sampler, decoder or matching graph.

## Configuration and commands

```bash
bash scripts/bootstrap.sh
conda activate knill_system
knill-bench-v2 validate-config configs/fig4d_v2_example.yaml
knill-bench-v2 validate-config configs/logical_zero_factory_v2_example.yaml
knill-bench-v2 prepare configs/logical_zero_factory_v2_example.yaml
```

`prepare` writes `config.yaml` and `metadata.json` and leaves an incomplete
run with pending points and `status="running"`. It samples nothing. `run`
executes Fig.4(d) or the logical-zero factory; `resume` executes prepared or
unfinished runs under the same source/config/environment checks.
The equivalent module command is `python -m knill_bench.experiments.cli`.
The old `knill-bench` / `knill_bench.cli` continue to accept schema 1 only.

Both checked-in v2 examples use small distances, not a Fig. 4(d) production
grid. Only `sweep.d` and `sweep.p` are axes. Distances are nonempty, unique,
odd integers >=3; probabilities are unique finite numbers in [0,.5].
All other fields are fixed for a run:

| Field | Allowed values / default |
| --- | --- |
| `schema_version` | Exactly integer 2 |
| `kind` | `fig4d_reproduction` or `logical_zero_factory` |
| `name` | Safe ASCII name, 1–80 letters/digits/underscore/hyphen; defaults to kind |
| `output_root` | Nonempty path, defaults to `results`; relative to invocation working directory |
| `code`, `noise` | `rotated_surface`, `hex_uniform` |
| `r_0`, `r_plus` | Positive integer, `d`, or a positive multiple such as `"2*d"`, `"2/3*d"`, `"1.5*d"`; default `d` |
| `T_tel` | Positive integer; default 8 for Fig. 4(d), 1 for factory |
| `create_codecapacity_dem` | Boolean, default false; Fig. 4(d) requires false |
| `skip_circuit_validation` | Boolean, default false; true skips full physical bundle validation for factory only |
| `decoder` | `mwpm` |
| `theta` | Optional finite analysis cut; default null, never a sampling/selection rule |
| `shots`, `workers` | Positive integers, defaults 64/1 |
| `batch_size` | `auto` (default) or positive integer for legacy fixed whole-point execution |
| `buffer_shot` | Positive output-buffer row count; default 10000 in auto, batch_size in fixed mode |
| `target_chunk_seconds` | Positive finite sampling/decode time target, default 1.0; auto mode only |
| `master_seed` | uint64 integer, default 12345 |

Positive integer settings fit signed int64; seeds fit uint64. Booleans are
not accepted as numbers. Unknown root/nested keys, repeated YAML keys,
forbidden sweeps, nonfinite values, expression strings such as `d-2`, and
Python object tags fail. Only a duplicate-checking SafeLoader is used; no
expression evaluation or environment interpolation occurs. Parsing alone
does not certify that Hex supplies matrices/graphs for every requested case.
The Fig.4(d) runner additionally requires T=8, no theta and False prior mode,
before creating any output. Its standard paper configuration uses both depths
equal to d; other positive depths run preparation-depth variants.

`skip_circuit_validation` changes verification work only: physical identities,
seeds and decoding results are unchanged. True is rejected for Fig.4(d); v1 is
unchanged. For old config-hash compatibility, false is omitted from canonical
config JSON (the exact YAML is always preserved). True is included in the hash.
See [factory validation and frame arithmetic](logical_zero_factory.md).

Round multipliers use the restricted syntax `constant*d` or
`numerator/denominator*d`, with positive integer/decimal constants and optional
spaces around operators. The `*` separates the coefficient from `d`, and `/`
denotes division within that coefficient. They are parsed as exact rational
numbers, multiplied by each distance, and floored to an integer. For example:

```yaml
r_0: "2*d"
r_plus: "2/3*d"
```

At d=3 these resolve to (6,2); at d=5 they resolve to (10,3). `"0.6*d"`
resolves to 3 at d=5 without floating-point rounding. The resulting depth must
be in [1, 2^63-1] at **every** swept distance; zero after flooring is an error,
not clamped to one. Zero denominators, negative coefficients and other
expressions are rejected before run creation. This applies to both experiments.
Multipliers remain fixed round rules, not extra sweep axes. Resolved integer
depths enter the physical identity, seeds, filenames and execution metadata;
equivalent rules therefore retain the same physical point seeds.

`load_config(path)` returns frozen `ConfigDocument(config,contents,source_path)`.
`parse_config(mapping)` returns frozen `ExperimentConfig`; `as_dict()` gives
resolved JSON-compatible defaults and `config_hash` is its full SHA256.
`points()` yields frozen `ExperimentPoint` objects with resolved integer
preparation depths. The exact original bytes, including comments and formatting,
become the run's `config.yaml`; `input_sha256` identifies those bytes separately.

## Run identity, seeds and provenance

Each new run is `{YYYYMMDDHHMMSS}_{config_hash8}_{experiment-name}` below
`output_root`. The timestamp uses Japan time (Asia/Tokyo, UTC+09:00), without
punctuation or fractional seconds. `config_hash8` is the first eight lowercase
hex digits of the canonical simulation config's SHA256 (`config.config_hash`);
metadata retains the full hash. Comments/YAML formatting do not change this
hash, while configuration fields do. For example:

```text
20261016155547_2242fc7d_factory_v2_example/
```

An exclusive directory creation reserves each name. If that name already
exists, the timestamp advances by one second until a fresh name is reserved;
this also handles collisions in the short hash without reusing data. The
directory timestamp can therefore be ahead of the actual start on collision;
metadata retains the actual start/end times in ISO UTC. `run CONFIG` always
starts a fresh experiment, including repeated identical configs. Only
`resume RUN` continues saved execution. Existing directories/files are never
reused or overwritten by preparation. Legacy directory names still load and
resume; existing output directories are not renamed.

A point's canonical physical identity includes kind, code, noise, d, p,
resolved r_0/r_plus, T and the final-readout/basis convention. SHA256 gives its
case ID. The initial v2 memories are Z basis. Factory terminal readout is
`noiseless_terminal_Z_factory_oracle`; full Knill is `noisy_destructive_Z`.
The consumed one-bit measurement remains noisy in factory execution.

`point_seed(master,point)` and `chunk_seed(master,point,j,stream="chunk")`
derive uint64 from the first eight SHA256 bytes, little endian, over canonical
JSON `[derivation_version,master,physical_identity,stream,chunk_or_null]`.
The version is `sha256_auxiliary_v2_uint64_little_endian_v1`.
No Python hash, PID, process scheduling or worker number enters a seed.
Prior choice, theta, requested shots and worker count do not change the physical
identity. Different prior choices can therefore compare shared physical records.

Metadata stores master/per-point seeds and derivation version. Current auto
execution consumes chunk_seed with stream=time_adaptive_chunks_v1, caching
physical models/decoders but using a fresh sampler per assigned chunk. Actual
partitioning depends on measured timing; stable seeds alone do not guarantee
identical raw records across workers, runs or prior modes. Compact execution
metadata includes the partition hash and chunk/timing summary. Integer
batch_size retains the original continuing point-seeded sampler and fixed
partition, with old explicit-integer config hashes preserved. Use fixed mode
for bitwise replay and shared-raw-record prior comparisons. See
[adaptive parallel execution](parallel_execution.md) for exact limits.

In auto mode the parent owns the paired PointWriter and bounded PointBuffer;
workers return only labels/gaps, never native objects or measurement histories.
Each full buffer_shot result group is appended to both tables, with a short
final group. At most workers chunks can be outstanding/reordered. Fixed mode
keeps worker-owned writers and can also set an independent buffer_shot.
Publication/restart rules are unchanged: unfinished points restart at zero,
not from a saved buffer. No extra mandatory files or simulation axes are added.

The run/prepare/validate-config CLI accepts --workers N. An override saves
exact effective YAML with the original source-input SHA256 in a comment;
without an override the original YAML bytes remain exact. Source files are
never modified. See [cluster usage](cluster_setup.md).

`provenance.collect_environment()` stores actual Python/OS/CPU info, relevant
dependency versions, and Git commit/branch/dirty/import path/source-resource
hash for the imported bench and Hex packages. Hashes cover Python and checked-
in Matrix Market resources. H5 ancestry and exported factory interfaces are
verified against the imported module path, not an assumed `external/` path.
No source archives, patches, circuit/DEM archives, full environment-variable
dump or mandatory logs are created. This is descriptive provenance for a dirty
checkout, not an archive capable of reconstructing arbitrary uncommitted work.

## Tables and streaming contract

The public point basename is:

```text
logical_error__code=rotated_surface,d=3,p=0.001,noisemodel=hex_uniform,T=2,r_0=3,r_+=3.parquet
logical_gaps__code=rotated_surface,d=3,p=0.001,noisemodel=hex_uniform,T=2,r_0=3,r_+=3.parquet
```

Fig. 4(d) produces the first table only; factory produces exactly both.
The `r_+` key contains a literal plus. Use path APIs, quoted shell arguments
and `re.escape` for regex use. Numeric p is a round-trippable Python float
representation, preserving distinct binary64 values without rounded-name
collisions. Kind/prior/theta/code revision/readout are run-wide metadata,
so they cannot collide across distinct directories.

| Table | Columns |
| --- | --- |
| `logical_error` | `shot_id:uint64` non-null, `logical_error:bool` non-null |
| `logical_gaps` | Same `shot_id`, `gap_t001` through `gap_tT`: nullable float64 |

Each file tags schema version 2 and its table name. Shot IDs are contiguous
from zero and match row-for-row in both tables. `PointWriter.write_batch`
accepts only aligned uint64 IDs, bool labels and float64 `(batch,T)` gaps.
It validates both tables before either append, then writes just that batch
through one `pyarrow.ParquetWriter` per table. It retains counters, not all
shot arrays. Gap NaNs map to null; `gaps=None` explicitly means all unavailable.
Negative/infinite gaps fail. Unavailable is not zero. Later scientific runners
must not convert an unsupported Hex model/error into null gaps silently.
True gaps use `log_weight`, False factory gaps use `hamming_weight`; neither
is an exact posterior probability. Full Knill has no gap table in this schema.

B2 requires present, finite, nonnegative gaps at every stage and raises for
unavailable/nonfinite results rather than storing null. False at p=0 uses
Hex's explicit finite unit-Hamming rule; True at p=0 is unsupported. The
nullable Arrow schema remains unchanged for infrastructure compatibility.

Example infrastructure use (labels/gaps must come from real decoding):

```python
from knill_bench.experiments import load_config
from knill_bench.experiments.run_v2 import RunStore
from knill_bench.data.storage_v2 import PointWriter

with RunStore.create(load_config(config_path)) as run:
    for point in run.document.config.points():
        run.start_point(point)                 # parent only
        with PointWriter(run.path, point, expected_shots=run.document.config.shots) as out:
            for ids, labels, gaps in real_decoded_batches(point):
                out.write_batch(ids, labels, gaps)
            result = out.commit()             # worker returns small counters/paths
        run.record_complete(result)           # parent validates schema/counts
    run.finish()                              # only after every point completed
```

The B0 dispatcher did not implement `real_decoded_batches` or invoke this
example. B1's Fig.4(d) worker supplies real sampled/decoded batches and a
bounded spawn pool when workers > 1.

## Metadata ownership, publication and crashes

Exactly one `metadata.json` holds run start/end ISO UTC timestamps,
running/complete/failed state, active wall time, config/input hashes, resolved
fixed settings, provenance, seeds and per-point state/counts/times/filenames.
Only its owning parent PID may update it. Metadata is written via fsynced
`.metadata.json.tmp` and `os.replace`. There are no per-chunk public files or
transaction databases. Per-point counts represent committed output, not
partially attempted or unobserved shots.

B1 adds a compact nested `points[case_id].execution` descriptor at completion:
actual module roles, preparation counts, physical/readout noise, prior/decoder
conventions, circuit record/qubit counts and actual sampling-stream policy.
`RunStore.record_complete(result, execution=JSON_mapping)` validates and
copies this optional descriptor before updating the completion marker.

B2 uses that same nested descriptor for two-block sizes/alternating roles,
T/depths, noisy teleportation readout and terminal ideal-oracle convention,
actual gap units/policy, circuit and stage projected-model/configuration hashes.
It adds no mandatory artifacts or per-chunk metadata. Both scientific runners
share experiments/execution.py, which selects time-adaptive chunks by default
or the historical whole-point scheduler for integer batch_size.

Point files stay hidden as `.<public-name>.incomplete` until their full
expected shot counts are reached. BOTH writers close, fsync and pass schema/
footer-count checks before the first rename. Each rename is atomic individually;
the filesystem cannot make two file renames jointly atomic. Consumers must
consult the point's `metadata.json` complete marker. The parent publishes that
marker only after both files validate. A Python exception aborts both outputs;
an abrupt crash can leave one public file with incomplete metadata.

`RunStore.resume(path)` acquires exclusive parent ownership, checks exact
input/config identities plus imported source/resource/dependency versions,
validates completed point footers, then removes BOTH public/temporary outputs
for every unfinished point. Those points restart from zero with the original
point seed; completed points are preserved. A malformed completed file or
changed config/environment causes rejection before deleting point data.
Partial chunk progress is deliberately not resumed. Run wall time accumulates
measured active sessions; time lost between the last metadata update and a
hard crash cannot be recovered.

Local PID/host lock files guard a run and each point. Normal close removes
them. Resume may remove locks whose same-host owner no longer exists; live,
foreign-host or unverifiable owners are refused. Keep one coordinator per run;
this is local filesystem/process coordination, not a distributed scheduler.
A crash before the initial metadata file is established requires a fresh run;
unvalidated temporary JSON is not treated as committed provenance. No process
constructs a second writer for an owned point or appends to completed files.

## Validation and phase boundary

See [TEST.md](../TEST.md) for actual commands, setup issues and results.
Tests use synthetic <=7-row chunks for storage/failure boundaries and read-only
Hex API inspection; no new physical Monte Carlo is performed in B0. Existing
v1 regressions remain in the suite. No data-oracle selection, scientific gain,
threshold, latency, speedup or paper-agreement claim is made by infrastructure
tests. Historical H5 projected limits describe old runs. Current factory True
uses the module-local model documented below and retains H5's gap-lift checks.

## Current factory True policy

`create_codecapacity_dem:true` now records `prior_policy:module_local_stim_dem`
and `projected_approximation:preparation_and_earlier_stage_residual_errors_excluded_v1`.
The prior covers only native coupling/noisy destructive readout after an ideal
+1 stabilizer boundary; noisy preparation and propagated frames remain physical.
No extra boundary noise is inserted. Pauli observable input/output annotations
are used only for DEM analysis. Local DEM/matching caches are bounded and
worker-local; sampler state is never shared across points. See [the factory guide](logical_zero_factory.md).

Existing `projected_prior_sha256`/`projected_model_sha256` execution keys now
identify local configuration/DEM content, with additional local physical-module
and analysis-circuit hashes plus explicit scope/exclusion fields. Stage hashes
can repeat because identical modules share priors. Filenames/shot schemas/seeds
are unchanged. Old projected runs remain readable by saved-only analysis with
their original labels; resume refuses the old policy/source before any cleanup.

## Additional kind: ordinary SE memory

`kind: se_memory` is now available through run/prepare/resume and the shared
adaptive/fixed schedulers. New fixed fields are `rounds` (default d; same exact
positive integer/d/multiple grammar) and `get_logicalgap` (boolean, default
false). Both are forbidden on existing kinds. Memory rejects Knill-only
r_0/r_plus/T_tel/theta/create_codecapacity_dem and skip_circuit_validation:true.
Only d/p sweep. get_logicalgap requires 0<p<0.5 and supported positive DEM
weights; without it p0 is supported. Native physics, boundary conventions,
first/opposite-class inference and exact table/filename meaning are in
[the memory guide](se_memory.md). New default fields are omitted from old
canonical configs/point identities, preserving prior hashes and seeds.




Factory custom-noise YAML is added in BENCH-N1/N2, documented in
[the custom-noise guide](factory_custom_noise.md). The scalar hex_uniform form
retains all canonical identities; custom is factory-only, with full fixed
parameters in config/physical hashes and pre-output probability/domain checks.
Only d/p sweep. Result schemas/publication rules are unchanged, with the short
noisemodel=custom filename label. v1 explicit profiles are unaffected.

## General Knill EC memory (supersedes B1 kind/T restriction)

Use kind=knill_ec_memory with positive T_tel (default 8); fig4d_reproduction
is retained as the legacy T=8/uniform kind. noise accepts hex_uniform or the
Knill-only noiseless_bellpair/code_capacity_noise policies, both with ideal
final readout. Prior mode must remain False and theta null. Only d/p sweeps
and fixed prep-depth rules remain. See [full API/noise/metadata contract](knill_ec_noise_plan.md).

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.

## General Knill simulator (supersedes general-Knill False-only restriction)

kind=knill_sim and existing knill_ec_memory accept True priors with fixed
codecapacity_prior=module_local/default or full_prefix. Fig.4(d) is the
standard T8/d-round/uniform/False choice; the legacy reproduction kind retains
its prior contract. False hashes and all old physical IDs/seeds are preserved.
See [strict syntax, native/local scopes and tests](knill_sim.md).
