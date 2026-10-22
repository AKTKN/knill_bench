# General Knill EC simulation

`kind: knill_sim` runs the existing native Hex full-Knill logical-Z memory.
`knill_ec_memory` remains supported with identical options. Fig.4(d) is a
choice of parameters: T_tel=8, r_0=r_plus=d, hex_uniform and False priors.
The legacy fig4d_reproduction kind keeps its old compatibility contract.

## Configuration

To use the user's d-round preparation settings with circuit-informed local
inference, change/add these fields; the other supplied settings can remain:

```yaml
kind: knill_sim
create_codecapacity_dem: true
codecapacity_prior: module_local
```

Only d/p sweep axes remain. T_tel is any positive integer (default 8),
r_0/r_plus accept the existing positive integer/d/multiple rules. theta is
still null because this memory runner produces no postselection score.
Physical noise remains hex_uniform, noiseless_bellpair or code_capacity_noise.
Uniform final readout is noisy; the two special physical models keep ideal
final readout. `codecapacity_prior` changes inference only, never these channels.

`create_codecapacity_dem: false` retains the original native unit-Hamming
online decisions. True enables one of two explicitly selectable policies:

| codecapacity_prior | Sources included in current prior | Method / limit |
|---|---|---|
| module_local (default) | Current auxiliary CX(plus,zero), data CX(data,zero), Bell X/Z readouts; data-only capacity injection when configured | Strict Stim DEM with ideal +1 CSS input stabilizers and Pauli logical input boundary; excludes preparation/earlier-stage residuals from the prior |
| full_prefix | All physical operations from ideal initial data through the current Bell readout, including preparation and earlier-stage faults | Existing Hex H5 causal fault projection, replaying preparation and previous Bell recoveries at a fixed reference; may reject models outside its supported graph class |

The local analysis starts after both SE preparations but **before Bell-pair
assembly CX**. It includes assembly faults, unlike a prior starting only at
the later data-coupling CX. It canonicalizes the actual native three-block
body; it does not rebuild physical gates or add a boundary noise channel.
Pauli OBSERVABLE_INCLUDE input/output boundaries cancel random Bell byproducts
without using physical fault truth, final labels or future records. Each
sector uses only its operational corrected Bell syndrome for inference.

Module-local excludes preparation/previous-stage residuals **from inference
only**. The physical circuit retains all configured noisy SE preparation,
assembly, coupling, readout and propagation; no physical reset/encoder is
inserted to realize the analysis boundary. Changing preparation depths can
change sampled labels while leaving this deliberately local prior unchanged.
The local X/Z DEMs use complete error signatures and native Hex log-weight
MWPM class selection. They retain two separate marginal sectors, without a
joint X/Z decoder or exact preparation-conditioned posterior claim.

Full-prefix uses Hex's configure_knill_projected_priors with its native global
correction maps and the actual earlier configured full-prefix recoveries.
No final readout/oracle enters a prior. Its fixed-reference independent-event
superposition is also an approximation after nonlinear preparation decoding.
The adapter's packed runtime frames preserve those native causal decisions.
This mode can be expensive as distance/depth/T grow. Existing d3 preparation
2/3-round X-sector cases retain detector-free logical events and raise
UnsupportedProjectedModel. Selecting this mode does not silently fall back to
local or Hamming. Both True policies retain strict finite-weight/graph/lift
checks; p=0 True raises, while False supports p=0.

`codecapacity_prior` accepts only module_local/full_prefix and only for the
general Knill kinds with create_codecapacity_dem=True. Omitted selects local.
It is a fixed inference setting, not a sweep axis. A tiny full-prefix example:

```yaml
schema_version: 2
kind: knill_sim
name: knill_full_prefix_smoke
output_root: results
noise: hex_uniform
sweep: {d: [3], p: [0.001]}
r_0: 1
r_plus: 1
T_tel: 1
create_codecapacity_dem: true
codecapacity_prior: full_prefix
shots: 3
batch_size: 3
workers: 1
```

The [local template](../configs/templates/knill_sim.yaml) uses d3, d-round
preparation and three shots. [The full-prefix template](../configs/templates/knill_sim_full_prefix.yaml)
uses the supported one-round fixture. Run either with the existing wrapper:

```bash
bash scripts/run_knill_ec_memory.sh configs/templates/knill_sim.yaml
knill-bench-v2 resume results/<run>
knill-bench-v2 plot-knill results/<run> --output knill.png
```

The user's 200000-shot, d5/7/9/11 sweep is parsed in tests only; it is not
launched as validation. auto is time-adaptive, not fixed-partition replay;
use integer batch_size when comparing identical physical records across
prior modes. No production runtime, threshold or paper-agreement claim follows
from the tiny test/smoke cases.

## Caching, identities and saved data

Local model/graph cache: 16 entries per worker, keyed by complete canonical
native body, immutable code and sector; ideal analysis-input encoders have an
8-entry cache. No sampler RNG is stored in these caches. Sampling/decoding do
not rebuild DEMs/graphs/converters. Full-prefix native graphs/maps are compiled
once per point/worker. Both paths reuse the existing bounded fixed/adaptive
scheduler and error-only Parquet output. No per-shot constructors or gap table
is added.

Inference selection does not enter ExperimentPoint, case_id or point seed.
For the same kind/physical settings, False/local/prefix share the exact
physical circuit and fixed-partition raw sampler stream. Auto timing can
change partitions across models. New kind names intentionally have their
own identity; existing knill_ec_memory/legacy identities and all previously
valid canonical config hashes are unchanged. False/default configs omit the
new field; True configs save it in canonical metadata and exact input YAML.

Prior policies are knill_module_local_stim_dem and
knill_full_prefix_projected, separate from factory labels. Execution metadata
records selected mode, scope, approximation, included/excluded residual flags,
and two sector configuration/model hashes per stage (local additionally
records physical-body and analysis-circuit hashes). Parent completion, resume,
plot-knill and the lazy notebook reader validate mode/scope/hash structure.
Resume refuses changed inference/config/source before discarding unfinished
outputs; switching mode requires a fresh run. Saved statistics never simulate.
