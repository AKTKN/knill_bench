# knill_bench package map

`preparation.py` defines the independent fixed-R preparation contracts:
compiled physical/evaluation/offline circuits, explicit ledgers/cut/maps,
separate online observations and evaluator truth, predictions and a decoder
Protocol. `BoundaryConstraintModel` aliases the reviewed temporal DEM type;
legacy `models.py` remains unchanged. Prompt 01 adds a circuit/config builder,
explicit observable expressions and production batch splitting. See
[theory, exact integration sites and remaining gates](../../docs/temporal_preparation_theory.md).
The [preparation guide](../../docs/surface_preparation.md) documents actual
native round/flow/noise checks, physical/nominal model roles and the tiny
Python usage. CLI simulation build/run remains guarded pending step 04.
Prompt 02's [boundary model API](../../docs/temporal_boundary_model.md) compiles
and certifies static X models, preserves float/integer costs and original
columns/features in hashed JSON artifacts, and loads without DEM parsing.
The native builder and matching objectives remain unchanged in that step.
Prompt 03 adds strict prediction/diagnostic contracts,
`adapters.temporal_gap.TemporalGapDecoder`, the independent known-zero
`decoding.preparation_prefix` model and evaluator-only
`simulation.preparation_metrics`. Their [API guide](../../docs/preparation_decoder.md)
documents cached batch/single/packed decoding, same-mode witnesses, validity
denominators and inclusive gap cuts. No simulation table or runner is added.

`analysis.RunRegistry`, `NotebookPlots` and `FigureStyle` provide saved-only
v2 notebook comparisons with deferred keyed loading, six editable Matplotlib
figures and optional local plotting_lib APS/300-dpi style. See
[the notebook guide](../../docs/notebook_plotting.md) and
[analysis interfaces](analysis/DOCS.md). Simulation/CLI/B3 schemas are unchanged.
The shared style supplies reference-sized serif/LaTeX labels and ticks;
round_digit optionally applies decimal half-up rounding before all gap
analysis, and gap frequency can return per-group/per-stage unique lists.
Lifetime uses all-shot stacked fractions and capped means on a separate axis,
with optional returned numerical summaries of both.
WilsonInterval supplies pointwise 95% score shades on the other five notebook
figures, including transformed per-round and paired reduction bounds. This
saved-analysis extension changes neither simulation nor legacy CLI estimands.

The original schema-v1 path remains `config.py` -> `cli.py` ->
`simulation.runner`; its dataclasses in `models.py` describe compiled physical
experiments, raw samples and predictions. `codes.py` loads/validates the
single-logical-qubit rotated-surface CSS matrices from the imported Hex.
No v1 API/schema or numerical implementation is changed by B0.

The independent [experiments](experiments/DOCS.md) package adds schema-v2
config/dispatch/run ownership, with [data](data/DOCS.md) supplying streamed
point tables. See [the v2 guide](../../docs/auxiliary_v2.md) for every field,
filename, seed, metadata, shape, crash policy and phase boundary. Other packages:
[adapters](adapters/DOCS.md), [analysis](analysis/DOCS.md),
[circuits](circuits/DOCS.md), [decoding](decoding/DOCS.md) and
[simulation](simulation/DOCS.md).

Hex is pinned to HEX-N2 86c9495094801012b9912bd41935ae48b08d8f92 (H5 lineage).
B0 verifies actual exported interfaces and Git lineage read-only; it does not
build a sampler/decoder or implement science runners. Fig.4(d) full Knill and
the ideal terminal factory oracle remain distinct experiments. No oracle truth
may enter decoding, confidence, cuts or selection of physical trajectories.
Testing commands/results live in [TEST.md](../../TEST.md). All package
subdirectories containing Python modules maintain DOCS.md.

## B1 Fig.4(d)

`adapters.hex_full_knill` now supplies per-shot full Knill labels from actual
Hex modules, separate from the old d-2 builder. `experiments.fig4d_reproduction`
enforces eight stages/d resource prep/noisy final readout and streams B0 data
with bounded point workers and parent-owned completion. `analysis.fig4d`
validates saved labels/counts and plots 95% Agresti-Coull intervals without
resimulation. V1 numerical sources and Hex remain unchanged. See
[the B1 guide](../../docs/fig4d.md) for APIs/commands/cache/seed semantics and
tested versus unmeasured production limits. Factory execution is documented below.

## B2 logical-zero factory

`experiments.logical_zero_factory` builds the actual Hex H5 factory/compiled
decoder once per point and streams aligned logical_error/logical_gaps tables.
It preserves noisy teleportation readout and the sole terminal ideal oracle,
two-block role swapping, finite Hamming or supported projected gaps and fixed
full trajectories independent of theta. `experiments.execution` now shares
the bounded whole-point scheduler with B1. Existing simulation/circuit/decoder/
storage numerical implementations and all dependencies remain unchanged.
See [the B2 guide](../../docs/logical_zero_factory.md) for APIs, commands,
score units, zero-noise policy and causal tests.

## B3 completion and user entry points

`analysis.factory` streams saved pairs for gap-only acceptance, pointwise
conditional oracle-error intervals, first rejection and explicitly assumed
costs. `analysis.factory_cost` isolates the timing/renewal assumptions. CLI
adds analyze-factory with optional JSON/CSV/Markdown output and separate
analysis settings. No circuit/decoder/worker/storage implementation changes.
User entry points are [GETTING_STARTED.md](../../GETTING_STARTED.md), the
[templates](../../configs/templates/factory_analysis.yaml) and
[B3 equations/limits](../../docs/factory_analysis.md). Production agreement,
queues, runtime/speedup and general fault-tolerance claims remain unestablished.

## Research environment and distribution

Conda knill_system replaces .venv. pyproject.toml now exposes pinned research/
dev extras, numeric wheel dependencies and an explicit table of pinned fork
sources. The staging-only cluster builder includes all Hex matrices and source
manifests, without modifying fork source. Both provenance implementations
support checksum-verified installed wheels as well as source checkouts.
Scientific builders/decoders/storage remain unchanged. See
[cluster setup](../../docs/cluster_setup.md) and [getting started](../../GETTING_STARTED.md).

## Configurable v2 preparation depths

Both experiments accept fixed integer/d/positive-multiple round rules, such as
`"2*d"` or `"2/3*d"`. Resolution uses exact rational arithmetic and floors at
each distance; all depths must be positive signed-int64 values. The full Knill
adapter passes these resolved depths to Hex for every resource preparation,
while the factory uses its existing PreparationPlan interface. Standard
Fig.4(d) settings retain d rounds. The saved-data Fig.4(d) vertical axis now
reads `logical error rate`; summary keys and table schemas are unchanged.

New v2 directories are `YYYYMMDDHHMMSS_<config_hash8>_<name>` (Asia/Tokyo),
with exclusive creation and one-second collision increments. Metadata retains
actual UTC times and the full simulation-config hash. `run CONFIG` always
creates fresh data; `analyze-factory RUN` reanalyzes saved data/config only.
Legacy run paths and v1 directory/schema contracts remain supported.

## Module-local factory DEM revision

adapters.hex_factory now builds strict local Stim DEMs for v2 factory True.
The prior excludes preparation/earlier-stage residuals; physical sampling and
Hex frame logic retain them. Bounded per-worker DEM/gap caching and one full
validation by default per freshly built True factory remove legacy projection and repeated
validation. Experiments save explicit policy/scope/hashes; old saved analysis
keeps its original labels. No fork/v1/B1 source changes. See
[factory guide](../../docs/logical_zero_factory.md) and
[measured report](../../docs/factory_performance_report.md).

Both factory prior modes now use adapters.factory_frames for equivalent packed
GF(2) exit-frame/final-check computation, retaining the four native matching
calls. ExperimentConfig.skip_circuit_validation defaults to false and can skip
the full construction-time bundle check for factory only. Runtime checks and
physical/seed/model semantics remain unchanged; execution metadata declares
the validation mode and frame implementation. V1/B1 and Hex stay unchanged.

Current v2 execution defaults to adaptive_execution's time-adaptive chunks,
with per-worker native model caches and parent-owned buffered paired output.
Integer batch_size retains the legacy fixed path. See
[parallel execution](../../docs/parallel_execution.md) for exact seed/partition,
memory and restart limits. CLI --workers supports PBS allocations; saved
config.yaml describes the effective setting without editing the source input.
V1, native adapters and Hex source remain unchanged in this revision.

## Ordinary memory extension

adapters.hex_memory and experiments.se_memory connect Hex's native repeated-SE
Z memory to existing v2 auto/fixed runners and paired buffered output. Optional
get_logicalgap adds one cached opposite-observable-class graph via
[decoding.observable_gap](decoding/DOCS.md), without changing the first decode
or exposing truth to inference. All original v1/B1/B2 numerical sources and
Hex remain unchanged. [Memory guide](../../docs/se_memory.md) defines noisy
boundaries, rounds, scores, compatibility filename keys and validation limits.




BENCH-N1 adds factory-only custom physical-noise YAML, native immutable
parameters and strict pre-output validation. Uniform identities remain exact;
Fig.4(d)/SE memory reject the custom mapping explicitly. See
[custom noise](../../docs/factory_custom_noise.md) for channels/timing,
configuration, inference boundaries and the two-stage integration contract.




BENCH-N2 forwards custom factory noise to native Hex preparation/circuit APIs,
retaining cached causal/packed decoding and the existing local prior boundary.
The parent validates effective parameters/hashes/scope on publish/resume;
saved analysis validates the same noise metadata. Fixed/adaptive output remains
paired and bounded. Full Knill/Fig.4(d), SE memory and v1 numerical paths are
unchanged. See [custom noise](../../docs/factory_custom_noise.md).

## General Knill EC memory

experiments.knill_ec_memory is the canonical full-Knill runner, sharing the
bounded worker/adapter path with legacy fig4d_reproduction. Hex exports the
physical policy; adapters.hex_full_knill records actual rates/boundaries.
See [noise revision](../../docs/knill_ec_noise_plan.md) for supported kinds,
models, arbitrary positive T, compatibility and saved-only plot-knill.

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.

## Key-specific physical-error plotting coordinate

NotebookPlots.plot_logical_error_rate now accepts rescale_p_keys, applying
(23/10)*p-(8/5)*p**2 only to those dataset keys' plotted x values and Wilson
shades. Saved files/filter coordinates and all LER statistics stay unchanged.
See [notebook usage and analytic scope](../../docs/notebook_plotting.md).

## General Knill simulation with two prior scopes

experiments.knill_sim dispatches the general memory runner. True enables
module-local Stim or native full-prefix inference through adapters.knill_priors.
Existing kinds/default hashes remain supported. See
[Knill simulation](../../docs/knill_sim.md) for syntax, physical independence,
scopes, metadata, cache lifetime and unsupported models.
