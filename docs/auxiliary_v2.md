# Schema-v2 auxiliary experiments: B0 foundation, B1 Fig.4(d), B2 factory

B1 now implements the Fig.4(d) runner, bounded point workers, resume and
saved-data Agresti-Coull plotting. See [the B1 guide](fig4d.md) for scientific
constraints, commands, actual seed use and validation. The foundation below
records the B0 contract. B2 adds the [two-block factory runner](logical_zero_factory.md)
with aligned per-shot error/gap output. Acceptance/cost analysis remains B3.

B0 supplies schema-v2 configuration, point identities/seeds, run directories,
compact provenance/metadata and streamed point-level Parquet storage.
Scientific Fig. 4(d), factory and acceptance/cost runners belong to B1, B2
and B3 respectively. B0 does not simulate either experiment, plot a paper
figure, or implement a worker pool. The dispatcher raises an explicit
`NotImplementedError` before creating outputs for an unavailable runner.

The existing schema-v1 CLI, configurations, scientific builders, decoder
adapters, table schemas and resume engine remain separate and unchanged.
Hex is imported read-only from the H5 `auxiliary-system` lineage, pinned in
bench to `4278d2900626f1d120d611f209340b20a9370f91`; B0 changes no Hex
version/source. Export/signature/lineage validation never constructs a
physical circuit, sampler, decoder or matching graph.

## Configuration and commands

```bash
bash scripts/bootstrap.sh
.venv/bin/knill-bench-v2 validate-config configs/fig4d_v2_example.yaml
.venv/bin/knill-bench-v2 validate-config configs/logical_zero_factory_v2_example.yaml
.venv/bin/knill-bench-v2 prepare configs/logical_zero_factory_v2_example.yaml
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
| `r_0`, `r_plus` | Literal `d` or positive integer; default `d` |
| `T_tel` | Positive integer; default 8 for Fig. 4(d), 1 for factory |
| `create_codecapacity_dem` | Boolean, default false; Fig. 4(d) requires false |
| `decoder` | `mwpm` |
| `theta` | Optional finite analysis cut; default null, never a sampling/selection rule |
| `shots`, `batch_size`, `workers` | Positive integers, defaults 64/32/1 |
| `master_seed` | uint64 integer, default 12345 |

Positive integer settings fit signed int64; seeds fit uint64. Booleans are
not accepted as numbers. Unknown root/nested keys, repeated YAML keys,
forbidden sweeps, nonfinite values, expression strings such as `d-2`, and
Python object tags fail. Only a duplicate-checking SafeLoader is used; no
expression evaluation or environment interpolation occurs. Parsing alone
does not certify that Hex supplies matrices/graphs for every requested case.
The Fig.4(d) runner additionally requires T=8, both resolved preparation depths
equal d, no theta and False prior mode, before creating any output.

`load_config(path)` returns frozen `ConfigDocument(config,contents,source_path)`.
`parse_config(mapping)` returns frozen `ExperimentConfig`; `as_dict()` gives
resolved JSON-compatible defaults and `config_hash` is its full SHA256.
`points()` yields frozen `ExperimentPoint` objects with resolved integer
preparation depths. The exact original bytes, including comments and formatting,
become the run's `config.yaml`; `input_sha256` identifies those bytes separately.

## Run identity, seeds and provenance

Each run is exactly `{UTC-timestamp}_{experiment-name}` below `output_root`,
using `%Y%m%dT%H%M%S.%fZ`. An exclusive directory creation reserves its name;
a timestamp collision advances by one microsecond. Different run-wide configs
always receive distinct directories even when names/point filenames match.
Existing directories/files are never reused or overwritten by preparation.

A point's canonical physical identity includes kind, code, noise, d, p,
resolved r_0/r_plus, T and the final-readout/basis convention. SHA256 gives its
case ID. The initial v2 memories are Z basis. Factory terminal readout is
`noiseless_terminal_Z_factory_oracle`; full Knill is `noisy_destructive_Z`.
The consumed one-bit measurement remains noisy in future factory execution.

`point_seed(master,point)` and `chunk_seed(master,point,j,stream="chunk")`
derive uint64 from the first eight SHA256 bytes, little endian, over canonical
JSON `[derivation_version,master,physical_identity,stream,chunk_or_null]`.
The version is `sha256_auxiliary_v2_uint64_little_endian_v1`.
No Python hash, PID, process scheduling or worker number enters a seed.
Prior choice, theta, requested shots and worker count do not change the physical
identity. Different prior choices can therefore compare shared physical records.

Metadata stores master and per-point seeds, fixed batch size and derivation
version; chunk seeds can be reconstructed without storing a long chunk list.
B0 does not claim to have consumed either seed stream. B1 uses the point seed
once to compile its continuing sampler, with fixed batch partition and no
chunk-seed consumption. Other runners must
record/use their actual stream and keep samplers/graphs cached once per case/
worker. A continuing Stim sampler normally uses the point seed once and
advances over batches; reproducibility requires the same library/platform and
chunk partition. Deriving chunk seeds does not authorize recompiling a sampler
or decoder per chunk/shot.

B2 consumes the same continuing point-seeded sampler policy. Prior mode and
theta do not enter the physical seed/circuit, and no chunks are skipped when
scores fall below a cut. Actual full-trajectory data are saved in both tables.

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
use the bounded whole-point scheduler in experiments/execution.py.

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
tests. H5's projected-prior restrictions and approximation limits still apply.
