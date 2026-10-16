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
The future B1 adapter must preserve noisy final readout and use d preparation
rounds, rather than repurposing `knill_hex_dminus2`. New v2 interface/provenance
checks live in [experiments](../experiments/DOCS.md); no Hex source is modified.
