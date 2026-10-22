# Knill EC memory noise revision plan (2026-10-22)

1. Hex owns a frozen, validated Knill noise policy and the data-only depolarizing
   module. Extend fixed Knill with a keyword-only noise option; retain the exact
   omitted/uniform circuit, callbacks and frame decisions. Adaptive Hex and
   factory/SE protocols remain unchanged.
2. Bench adds canonical `kind: knill_ec_memory`, positive arbitrary T_tel
   (default 8), and scalar noise names `hex_uniform`, `noiseless_bellpair`,
   `code_capacity_noise`. Keep `fig4d_reproduction` as a legacy kind with its
   original T=8/uniform contract, hashes and saved data. Reuse the bounded
   fixed/adaptive execution and error-only schema. No new sweep axes.
3. noiseless_bellpair: zero preparation and auxiliary CX noise, native noisy
   data-to-zero CX and consumed X/Z readout, ideal terminal readout.
   code_capacity_noise: exactly one DEPOLARIZE1(p) on the current data block
   immediately before each Bell coupling; every other channel has probability
   zero. p is total one-qubit depolarization (each X/Y/Z p/3).
   Both retain native preparation records/repair, causal frame/byproducts and
   terminal logical decoding. No truth in inference; no postselection.
4. Check complete noise locations/targets/probabilities, p=0, exhaustive d3
   capacity Pauli patterns, native/bench circuit and raw-record decode parity,
   caching, identities, strict parsing, fixed/spawn/auto, restart and saved-only
   analysis. Use d3/5 and <=7 new physical shots; no production sweep.
5. Run focused and full Conda tests, tiny CLI run/resume/plot smokes, pip check.
   Update guides and STATUS/TEST with commands/failures/limits, commit/push Hex
   auxiliary-system, pin the resulting commit in bench, then commit/push bench
   auxiliary-system. Preserve unrelated incoming notebook/.gitignore changes.

The user's request explicitly authorizes editing Hex and ideal final readout
for the two new models, superseding historical read-only/noisy-boundary rules
for this scoped revision. Small smoke checks do not establish a threshold or
paper agreement. `code_capacity_noise` is a physical noise option, distinct
from factory `create_codecapacity_dem` inference.

## Implemented configuration and execution

`kind: knill_ec_memory` replaces the old user-facing Fig.4(d) kind. It denotes
Hex-based full Knill EC memory in logical Z, with positive integer `T_tel`
(default 8), fixed r_0/r_plus rules and only d/p sweep axes. The old
`fig4d_reproduction` kind remains accepted for existing inputs/saved data with
its original T=8, hex_uniform-only contract; it is not normalized when loading,
so its canonical config hashes, point IDs, seeds and saved filenames stay
unchanged. New kind identities intentionally differ; create a fresh run when
migrating a YAML. Legacy directories/data are never renamed. Existing
configs/fig4d*.yaml and configs/templates/fig4d.yaml now use the new name with
their prior budgets, T=8 and physical model unchanged.

Set scalar `noise` to one of the following:

| Region | hex_uniform | noiseless_bellpair | code_capacity_noise |
|---|---|---|---|
| Initial encoded data | ideal | ideal | ideal |
| Both auxiliary preparations, including all SE | native p | ideal | ideal |
| Auxiliary transversal CX(plus,zero) | native p | ideal | ideal |
| Data before each teleportation CX | no extra channel | no extra channel | DEPOLARIZE1(p), data only |
| CX(data,zero), consumed X/Z readout | native p | native p | ideal |
| Terminal destructive Z readout | native p | ideal | ideal |

The first special model idealizes Bell construction **through its CNOT**,
including SE-based preparation. The second has no other nonzero gate, reset,
measurement or idle channel. p is total one-qubit depolarization probability
(each X/Y/Z branch p/3, each CSS marginal 2p/3). Native p=0 fragments may retain
inert noise(0) instructions. Preparation remains the native SE protocol with
its random stabilizer signs/repair and configured depths, not a different
ideal encoder. Data errors are not erased by a reset between EC cycles.
Both use actual Hex callbacks and causal software byproducts, independent
CSS-sector unit-Hamming MWPM and one terminal logical readout decode. Capacity
decoding here does not exploit X/Z correlations or claim exact logical ML.
Final ideal readout is the memory boundary, not a factory oracle protocol.

Special models are accepted only for knill_ec_memory; factory custom mappings
remain factory-only. `create_codecapacity_dem` must be false and theta null.
The physical noise option is distinct from the factory's similarly named
inference option. r_0/r_plus, T and physical model enter identities/seeds;
workers/shots/decoder-analysis parameters do not. No new simulation axes,
Parquet columns or mandatory files are introduced. Native model/decoder caches
and bounded fixed/adaptive scheduling stay shared. Fixed batch_size supports
exact seeded partition replay; auto partitions remain timing dependent.

Metadata stores the noise name, resolved region probabilities, actual T/depths,
noise_scope_version=knill_ec_physical_noise_v1, ideal/noisy final boundary and
terminal_ideal_oracle=false. Parent completion, resume and saved analysis
cross-check the new execution fields. A mismatched external resume document
is rejected before cleanup. Source revision hashes continue to prevent resume
across code changes, including the Hex upgrade. Historical saved data still
supports saved-only analysis without matching the current simulation source.

```bash
# Each template uses d3, three shots per point, T=2; no production sweep.
bash scripts/run_knill_ec_memory.sh configs/templates/knill_ec_memory_noiseless_bellpair.yaml
bash scripts/run_knill_ec_memory.sh configs/templates/knill_ec_memory_code_capacity_noise.yaml
knill-bench-v2 resume results/<saved-run>
knill-bench-v2 plot-knill results/<saved-run> --output knill.png
```

`plot-knill` is the canonical saved-data command; `plot-fig4d` remains an alias.
Both accept old and new kinds, validate saved counts/IDs and never simulate.
The plot identifies actual T and noise, with the existing `logical error rate`
label, conditional_ler summary key and 95% Agresti-Coull intervals retained.
The lazy notebook reader accepts the new kind through existing generic fields.
No production run, threshold, paper agreement or speed claim is part of this
revision. See TEST.md for test and smoke evidence.

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.

## General Knill inference update

The later [knill_sim contract](knill_sim.md) supersedes the general kinds'
mandatory False flag above: True explicitly selects module_local/default or
full_prefix. Both preserve all physical noise boundaries in this guide.
Legacy reproduction settings and earlier saved hashes stay unchanged.
