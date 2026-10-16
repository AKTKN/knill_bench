# knill_bench package map

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

Hex is pinned to H5 4278d2900626f1d120d611f209340b20a9370f91.
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
