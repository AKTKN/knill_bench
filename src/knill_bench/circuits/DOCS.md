# Circuit builders (schema v1)

`preparation.build_preparation(case)` (also the new-protocol branch in
`builders.build`) returns CompiledPreparationExperiment for surface_prep_fixed.
It reuses Code.rotated and actual native initialization/X/Z extraction, with
exactly explicit rounds and no legacy initialization/cycle builder. Production
has online-only detectors plus ideal tau_X/tau_Z/logical-Z evaluation. A
separate nominal completed X circuit has ideal hidden past/output probes.
Compiled record/detector/observable namespaces and hashes are explicit.
Native ideal signed CSS/logical instrument flows, the audited unconditional
Clifford/Pauli prefix and strict non-gauge/undecomposed DEMs are checked once
at compilation. No sampler, decoder, physical correction or terminal recovery
is constructed. See [API/config/evidence](../../../docs/surface_preparation.md).

`builders.py` builds SE memory and the three named v1 Knill variants with
absolute measurement ledgers, signed CSS check propagation, observable
closure, Hex noise and optional explicit schedules. The native variant uses
exactly d-2 SE preparation rounds and remains different from paper Fig.4(d).
See [design](../../../docs/design.md) for each boundary, hook order, physical
resource/schedule convention and strict Stim flow/DEM checks.

B0 changes no circuit Python and builds no v2 physical circuits. V2 stores
fixed code/noise/depth/T/readout conventions through
[experiments](../experiments/DOCS.md). Later B1/B2 runners must use the tested
Hex public interfaces: full Knill retains noisy final readout; factory alone
has a final ideal Z evaluation oracle. No oracle/future records enter stage
inference, and no scientific support is implied by config parsing alone.
