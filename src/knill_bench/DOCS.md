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
