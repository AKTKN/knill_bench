

# Custom physical noise for the schema-v2 factory

BENCH-N1 adds strict parsing, native frozen noise objects, full configuration/
physical identities and pointwise probability validation. BENCH-N2 implements
physical execution through the native factory builder and causal decoder. Hex is pinned to HEX-N2 86c9495; no dependency source is
edited by bench. See [the commented example](../configs/templates/logical_zero_factory_custom_noise.yaml).
Legacy `noise: hex_uniform` is unchanged. Only kind logical_zero_factory
accepts the mapping below. Fig.4(d) and SE memory raise exactly:
`Custom noise is currently supported only for kind=logical_zero_factory.`
Schema-v1 and its explicit profile remain separate and unchanged.

```yaml
noise:
  model: custom
  multipliers:
    one_qubit: 0.1
    two_qubit: 1.0
    idle: 0.2
    measurement: 2.0
    reset: 1.0
  idle_windows:
    post_cnot_control: {duration: 2.0, rate_multiplier: 5.0}
    during_plus_preparation:
      enabled: true
      se_round_duration: 1.0
      rate_multiplier: 1.0
```

Each multiplier scales p. Native one-/two-qubit gates get DEPOLARIZE1/2;
readout gets the basis-complementary Pauli before measurement, resets get it
after reset. One-qubit noise covers actual native gates, without inventing a
noisy H for the RX reset primitive. All-one custom multipliers define a new
model, since legacy uniform Hex has no one-qubit depolarizing gate noise.

For idle base probability q=p*idle*window.rate_multiplier and normalized
duration tau, Hex computes p_eff=3/4*[1-(1-4*q/3)**tau], using its shared stable
utility. A duration changes exposure time; a rate multiplier changes q.
Fractional durations require q<=3/4; all resolved probabilities must lie in
[0,1], without clipping. Zero duration adds no channel. Only d/p sweep;
no expression (including d or 2*d) is accepted as an idle duration. r_plus
retains the existing separate exact integer/d/multiple round syntax.

Post-CNOT idle affects precisely the surviving fresh-plus control data after
the complete transversal CNOT and before destructive noisy target Z readout.
Inter-stage storage idle affects the current logical-zero memory while the
other support resets/prepares plus: tau=resolved r_plus*se_round_duration.
It is aggregated at refresh end because memory has no intervening interactions.
Initial zero/plus preparations are scheduled in parallel, with no stage-0
storage wait. These are disjoint windows, with no generic idle layer, hardware
schedule or additional_wait field. Neither special channel affects ancillas.

model: custom is required; omitted operation multipliers default to 1,
post duration defaults 0 with rate 1, and preparation idle defaults disabled
with SE duration/rate 1. Canonical metadata expands defaults. Unknown or duplicate
keys, booleans as numbers, nonfinite/negative values, unsafe tags and malformed
nested mappings fail. All operation products and idle domains/durations are
checked at every d/p point before output, even for inactive windows.

Config/physical identities contain all custom parameters. Uniform canonical
hashes and seeds omit the new None field and retain their old values. Threshold,
prior mode, workers and requested shots do not change sampling identity.
Filenames use noisemodel=custom and retain all existing point keys including
literal r_+; full parameters belong in exact saved YAML/compact metadata.
Different run hashes/directories separate configurations with equal basenames.
Normalized durations parameterize noise exposure. The separate B3 assumed-cost
model is unchanged and does not infer hardware timing/costs from this noise YAML.
No per-shot/table schema or extra mandatory simulation artifact is introduced.

The local prior starts at the coupling boundary: actual post-CNOT control
idle belongs inside the CNOT/readout model; earlier storage idle and preparation/
earlier-stage residuals stay outside that approximation. Physical trajectories
retain all sources. It is not a posterior conditioned on preparation repair,
and a survivor-only error can be invisible to the current target syndrome.
The terminal oracle remains noiseless and evaluation-only. Saved-data cuts do
not control physical sampling. Strict model restrictions still raise without
lossy graph decomposition or fallback.

At the historical N1 checkpoint custom execution was explicitly unavailable
to prevent uniform fallback. N2 supplies the native bridge; current custom
examples run through both existing fixed/adaptive bounded schedulers.


## Run and analyze

```bash
bash scripts/python.sh -m knill_bench.experiments.cli validate-config configs/templates/logical_zero_factory_custom_noise.yaml
bash scripts/run_logical_zero_factory.sh configs/templates/logical_zero_factory_custom_noise.yaml
# Use the printed run path for these commands:
bash scripts/python.sh -m knill_bench.experiments.cli resume results/RUN
bash scripts/python.sh -m knill_bench.experiments.cli analyze-factory results/RUN --theta=-inf
```

The template is seven d3 shots, two teleportations and auto chunks, with
bounded three-row result groups. Integer batch_size retains fixed partition
replay. No threshold enters compilation, worker arguments or sampling. Both
prior modes draw the same physical circuit and point seed; auto timing can
change actual partitions, so use equal integer batch_size for paired records.
No production sweep or dynamic quantum retry is part of this feature.

## Physical construction and decoder consistency

Bench passes the frozen validated object as noise_model to Hex's actual
FactoryCircuitBuilder. Hex prepares the noisy native modules and derives their
own DEM priors/correction maps before compilation. Bench's packed preparation
plans consume those exact maps and all four matching decisions, including
joint Pauli representatives supported in HEX-N2. It does not strip noise from
compiled preparations or duplicate a quantum gate sequence. The private
construction-type binding used for skip_circuit_validation and the causal
decoder-slot binding were re-audited at the new pin; the default still performs
one full signed/ledger/strict-DEM validation. Runtime gap/frame/model checks
remain active when that full construction check is skipped.

False retains finite unit-Hamming online recovery/gaps, including zero noise.
True retains the existing bench module-local Stim DEM and strict Hex graph/
weight checks. _local_body extracts every actual coupling/readout instruction,
including native post_cnot_control_idle; storage_idle is before that boundary
and is excluded along with preparation/earlier-stage residuals. The analysis
input/Pauli logical boundary has all +1 CSS stabilizers and never uses sampled
preparation records, future records or oracle labels. Unsupported graphs,
zero-active-noise True and other existing restrictions raise without fallback.
This is not native Hex H5's full-prefix projected policy.

A post-CNOT control error does not propagate backwards into the consumed
target's readout. That channel is present in the local analysis circuit, but
Stim may give it no current detector/logical effect. Analytic target-bit
marginals are q_gate=8*p*two_qubit/15 and q_readout=p*measurement, combined by
XOR q_gate+q_readout-2*q_gate*q_readout. A survivor logical X can change the final
oracle label with identical operational records/gaps. Including a channel in
the analyzed window therefore does not make the gap a complete posterior or
survivor-quality certificate. Storage noise still affects later physical
records and terminal labels although the local prior excludes it.

## Caches, metadata and resume

The worker caches one compiled native factory/decoder per full physical point;
fresh independently seeded samplers in auto mode retain the existing RNG policy.
The bounded 16-entry local-prior LRU additionally keys the **complete native
noise configuration hash** for custom models. Identical stages with alternating
A/B IDs share canonical local models. Changing even excluded preparation/
storage parameters keeps configuration entries separate. Their DEM text may
be equal because those sources are outside the prior; post-control duration
changes the local body/analysis hashes even when its current DEM effect is
invisible. Gate/readout changes alter the corresponding DEM probabilities.
Uniform cache calls/model hashes keep their previous form. No sampler RNG
state is shared across points, and no model/graph/map is built per shot.

Exact executed YAML, one metadata.json and the two existing Parquet tables
remain the only mandatory outputs. Effective metadata records full normalized
noise_parameters, native noise_model_json/sha256, physical_noise_sha256,
operation probabilities, both resolved idle probabilities, normalized durations
and application counts. The native circuit SHA256 still hashes actual Stim
text. Local module/analysis/DEM/configuration hashes and explicit flags
post_cnot_control_idle_in_local_prior=true and
storage_idle_errors_in_local_prior=false identify True's scope. Effective
teleportation_readout_error is p*measurement; the terminal oracle is noiseless.

The parent cross-checks custom configuration/probability/hash/scope metadata
before publishing a complete point, on completed resume, and during saved
analysis. Changed config YAML, physical identity/seeds, noise provenance or
local scope is rejected. A mismatched external resume document is rejected
before touching unfinished data. Ordinary source/dependency compatibility
checks remain strict. Completed files are preserved; unfinished paired files
restart from shot zero under the existing fixed/auto replay limits.

Saved-only analysis constructs no circuit, matching graph, sampler or decoder.
Uniform settings remain import-independent of Hex; custom settings load Hex's
native frozen parameter classes and idle-probability validation only. Old
uniform saved data retain their original policy labels and per-shot schemas.
No circuit dumps, detector tables or large provenance archives are required.
