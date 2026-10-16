# Decoder and reference adapters (schema v1)

`decoders.py` supplies global BP-LSD, PyMatching and LOM construction/
description, supported named fallback and result conversion. `hex_native.py`
uses the actual Hex CSS/Bell/final callbacks with cached local correction
transitions and packed Pauli-frame propagation. `references.py` provides
independent small native/LOM/BP reference checks. Existing source is unchanged
in B0; these remain the old v1 pipeline, not a B0 Fig.4(d) runner.

See [design](../../../docs/design.md) for noise, signed frames, decoder
assumptions and cache lifetime. Native objects are synchronous and worker-local;
they must not be constructed per shot or transported through process pickling.
B1's separate adapter preserves noisy final readout and uses d preparation
rounds; its implementation is documented below. V2 interface/provenance
checks live in [experiments](../experiments/DOCS.md); no Hex source is modified.

## B1 per-shot full Knill adapter

`hex_full_knill.HexFullKnill(point, seed=...)` builds the actual fixed Hex
sequence for Z memory and d rounds on both Bell resources. T=8 is enforced by
the experiment runner; this adapter also supports small T=1/2 test fixtures.
`sample(shots)` returns raw bool records; `decode_batch(raw)` returns
`FullKnillBatch(logical_error:bool[S], corrected_measurements:bool[S,M])`.
Native CSS/Bell/final callbacks use MWPM and default Hamming online priors.
Final readout is noisy. No code-capacity reweighting or factory oracle is added.

The unchanged `hex_native.PackedFrame/_transition` helpers supply cached local
maps and packed frame propagation. Canonical preparation templates share native
handles/maps/converters across stages. Sample once per chunk, decode offline,
check repaired detector residuals, and fail rather than discard bad shots.
Exact circuit and manual-array global-map comparisons against Hex are tested
at d=3, with zero-noise T=1 d=3/5. See [B1 details](../../../docs/fig4d.md).
