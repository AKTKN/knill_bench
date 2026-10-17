

# Custom physical noise for the schema-v2 factory

BENCH-N1 adds strict parsing, native frozen noise objects, full configuration/
physical identities and pointwise probability validation. BENCH-N2 connects
physical execution. Hex is pinned to HEX-N2 86c9495; no dependency source is
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
No per-shot/table schema or extra mandatory simulation artifact is introduced.

The local prior starts at the coupling boundary: actual post-CNOT control
idle belongs inside the CNOT/readout model; earlier storage idle and preparation/
earlier-stage residuals stay outside that approximation. Physical trajectories
retain all sources. It is not a posterior conditioned on preparation repair,
and a survivor-only error can be invisible to the current target syndrome.
The terminal oracle remains noiseless and evaluation-only. Saved-data cuts do
not control physical sampling. Strict model restrictions still raise without
lossy graph decomposition or fallback.

During the N1 checkpoint execution is explicitly unavailable for custom noise;
N2 supplies the native bridge. Uniform execution remains available throughout.
