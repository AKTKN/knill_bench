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
B1's separate adapter preserves noisy final readout and uses configurable
preparation rounds (default d); its implementation is documented below. V2 interface/provenance
checks live in [experiments](../experiments/DOCS.md); no Hex source is modified.

## B1 per-shot full Knill adapter

`hex_full_knill.HexFullKnill(point, seed=...)` builds the actual fixed Hex
sequence for Z memory and the point's resolved r_0/r_plus rounds on the zero/
plus Bell resources at every stage. The standard paper settings use d for both.
T=8 is enforced by
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
An eight-stage d3 fixture with depths (6,2) also checks actual preparation
measurement counts, labels, saved metadata and analysis.

## Factory local Stim DEM adapter

hex_factory.compile_local_factory(point, seed=..., create_codecapacity_dem=True,
skip_circuit_validation=False) returns a native Hex bundle
and CompiledFactory, using native physical construction and inherited causal
decode methods. True now excludes preparation/earlier-stage residual errors
from the PRIOR ONLY. _local_body extracts native coupling/readout with canonical
support IDs; _analysis_circuit adds ideal encoded +1 input stabilizers and
Pauli-target logical boundaries. _stim_dem uses strict Stim conversion; Hex
ProjectedErrorModel supplies the existing graph/lift checks and gap backend.
No ideal analysis operations enter the physical circuit, and no oracle or
preparation-decoder replay enters the prior.

_cached_local_prior is a 16-entry synchronous worker-local LRU keyed by frozen
code supports and complete canonical body text; _ideal_input caches at most
eight encoder strings. T/depth/seed/shot/theta are intentionally excluded.
local_prior_cache_info and clear_local_prior_cache support diagnostics/tests.
The _LocalFactoryDecoder initialization binds the pinned H5 private slots
after native construction, avoiding duplicate validation. Full bundle validation
runs once unless skip_circuit_validation=True. The opt-out uses the exact H5
builder code with a private construction-type binding, without modifying Hex
or its globals; the returned normal bundle still has validate(). Re-audit both
bindings when upgrading Hex. Both factory prior modes use this adapter; B1/v1
retain their existing paths.

factory_frames.FactoryPreparationPlan retains all four native matching calls
but computes only final check values and exit frames. PackedGF2Map precomposes
the two DEM-sector correction maps into packed outputs, avoiding corrected full
histories, correction concatenations and runtime CSR/dense-history conversion.
Capacity repairs still use corrected signs and are XORed into exit frames.
Maps/handles are shared per native support/basis/depth template within a point;
gathers are bounded to 32 input bytes, and lookup tables use 256 combinations
per group of 8 input bits. ExitFrame is private; native diagnostic return APIs
are unchanged. Runtime sign consistency checks remain enabled in skip mode.
See [factory guide](../../../docs/logical_zero_factory.md) for hashes and limits.

## Hex ordinary SE memory

`hex_memory.HexMemory(point, seed=...)` owns the exact native
stabilizer_measurement_circuit(z, rounds, p, surface_code=True,
disable_final_detectors=False), a converter, sampler, full-event DEM and
ObservableMWPM. `sample` advances the fixed-mode sampler; adaptive execution
uses its circuit with assigned chunk seeds. `decode_detectors` accepts only
detectors; `decode_batch` converts raw records, decodes/scores, then compares
the predicted and actual logical observable. MemoryBatch has bool
logical_error and optional float64 (shots,1) gaps. Physical initialization,
SE and final readout are noisy; no ideal oracle/correction module is added.
Metadata declares actual boundaries/rounds, selected detector sector and
circuit/DEM/model hashes. See [protocol](../../../docs/se_memory.md).
