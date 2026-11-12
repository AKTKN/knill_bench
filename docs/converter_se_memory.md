# Converter syndrome-extraction memory — Phase 1

Phase 5 completes the shared workstation/cluster execution contract: all three
converter kinds record actual chunk partitions/seeds in a bounded parent-owned
ledger, save label checksums and E/N/Wilson/timing statistics, and support the
saved-only summarize-converter command. Scientific policies and identities stay
unchanged. See [the final integration guide](converter_phase5.md) and
[validation evidence](converter_phase5_report.md).

`kind: converter_se_memory` is runnable ordinary Z memory. The pinned converter
generates every physical operation, detector and observable. PyMatching supplies
independent-event MWPM. Existing Hex `se_memory` and v1 are unchanged; the other
two converter scientific kinds remain unimplemented.

## Run and configuration

Use Conda `knill_system` and the exact optional dependencies in
[the integration guide](converter_integration.md). Stim stays 1.16.0 and
PyMatching stays 2.4.0. The [small adaptive example](../configs/converter_se_memory_v2_example.yaml)
uses d3/5, seven shots per point and two workers. The
[fixed template](../configs/templates/converter_se_memory.yaml) uses three-shot
chunks and one worker.

```bash
conda activate knill_system
knill-bench-v2 validate-config configs/converter_se_memory_v2_example.yaml
knill-bench-v2 run configs/converter_se_memory_v2_example.yaml
knill-bench-v2 resume results/<saved-run>
```

Only d/p sweep. `rounds` accepts a positive integer, `d` or an exact positive
distance multiple such as `2/3*d`, floored before output. The supplied
100000-shot d3/5/7 configuration is parse-only validation, never a unit-test run.
`run` creates a fresh run. `prepare` reserves pending directories without
compilation/sampling; resume can execute a prepared run. Completed resume checks
saved data/provenance without constructing a circuit, decoder or sampler.
Unfinished points restart from zero with the same seeds; complete files remain.
Source/environment changes require a fresh run.

## Physical and decoder contracts

The authored LSTIM is:

```text
FORMAT(1)
CODE sc ROTATED_SURFACE(d)
PATCH P0 sc index=0
BIND D P0
INIT_Z[initial](1) D
SE[storage](R-1) D
MZ[readout] D
```

Omit SE when R=1. INIT includes the first complete X/Z extraction: the total
is **R**, rather than R+1. Both check sectors remain physical. The converter
alone owns geometry, schedules, timing/noise and readout; bench adds no physical
schedule, encoded-state boundary or ideal evaluation oracle.

`noise: converter_uniform` calls `NoiseModel.uniform_depolarizing(p)`.
Default `input_preparation: noisy` retains noisy initialization and its first
extraction. The existing `ideal` option adds `noise=ideal` to INIT only;
subsequent SE and final destructive Z retain native uniform noise. YAML is
Z memory; the source helper/decoder support an X variant for dual-basis
validation only, with no new YAML field or sweep.

The adapter calls public `make_decoder_view` with semantic
`DetectorSelector(block_ids=("P0",), basis="Z")`, selecting the sole reliable
D/Z observable from public metadata. No independent detector coordinates,
detector numbering or physical stabilizer geometry is reconstructed. It uses
the exact physical-sector marginal with
`DEMOptions(decompose_errors=False, flatten_loops=True)`.

The ordinary Z-sector DEM is graphlike without decomposition. The adapter
inspects every complete event and rejects hyperedges, correlated separator
components, detector-free logical faults and parallel edges with different
logical labels. Graph dimensions/edge counts are checked after construction.
Identical-endpoint/identical-label independent events may combine through
PyMatching's independent probability rule; complete trivial events have no
syndrome or logical effect. There is no lossy fallback. Both construction and
batch decode use `enable_correlations=False`; p=0's empty graph is supported.

One raw physical Stim batch supplies both `view.events_from_raw(raw)` and
`view.observable_flips_from_raw(raw)`. Matching receives events only, before
the evaluator label is read. Per-shot output is
`logical_error = physical_observable_flip XOR MWPM_prediction`. No truth
selects a correction or trajectory. MWPM is minimum-weight inference, with
no logical-coset posterior/maximum-likelihood guarantee.

## Execution, artifacts and resume

`ConverterSEMemory` implements SimulationModel: exact circuit, original LSTIM,
static MemoryDecoder and public frame plan, boolean DecodedBatch and compact
metadata. A bounded one-point process-local cache holds the circuit/view/DEM/
graph. The parent builds artifacts once and reuses its model for serial chunks;
spawned workers each build their own model once per point. Sampler RNG state is
never cached across chunks/points. Model caches clear at run exit.

The shared bounded scheduler, numeric ChunkResult, spawn pool and buffered
PointWriter handle both modes. Parent owns sidecars and Parquet. Integer
batch_size uses `converter_fixed_chunks_v1`: identical fixed partitions/seeds
replay across serial/spawn workers. Auto uses `time_adaptive_chunks_v1`;
timing may change partitions and records. Row groups are not partial checkpoints.

Each point retains the Phase 0 layout:

```text
points/<physical-case-id>/circuit.lstim
points/<physical-case-id>/circuit.stim
points/<physical-case-id>/logical_error.parquet
points/<physical-case-id>/metadata.json
```

Parquet remains non-null uint64 shot_id plus bool logical_error, contiguous
from zero. The Stim serializer uses round-trip floats and verifies full equality
to the sampled circuit, including tags/repeats. The sidecar also retains public
`export_metadata()` with exact selected instructions and source fingerprint.

Compact execution metadata records total/init/additional rounds, boundaries,
noise API, sector/MWPM policy, dimensions, edge count and source/circuit/DEM/
projection hashes. Existing run metadata adds installed source/version identities,
chunk partition/counts/times and actual shot/error counts. Parent completion
and saved resume cross-check point/execution/artifact linkage and streamed IDs/
counts. All complete points validate before unfinished cleanup. Mismatched
caller documents are rejected before resume cleanup.

## Validation

Tests use d3/5 and at most seven physical shots per batch. They check p=0 for
X/Z with retained random gauges; exact R=1/2/3 counts; identical-batch agreement
with full Stim m2d, public projections, selected-circuit m2d and separately built
MWPM; all single physical X faults including boundary sites; caching, fixed/
adaptive one/two-worker output, replay, restart and strict saved metadata.

Perfect-syndrome references use the converter's public initialization boundary
and wire map, adding controlled faults only in tests. All **512** d3 pure-X
patterns are enumerated classically: independent CSS H_Z/L_Z syndromes/parity
and exhaustive minimum-pattern-weight classes agree with projected pure-X Stim
DEM matching and a separate CSS matching graph. The explicit iid X probability
is q=.1, not depolarizing p. This is exhaustive classical validation, not 512
Monte Carlo shots or an exact logical-coset posterior claim.

Existing Hex memory tests remain unchanged. See [TEST.md](../TEST.md) and
[the report](converter_se_memory_report.md). No production LER, threshold or
performance claim follows from the small fixtures.
