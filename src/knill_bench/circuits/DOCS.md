# Circuit builders (schema v1)

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
