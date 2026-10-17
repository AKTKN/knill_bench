# B1: eight-cycle full Knill Fig.4(d) experiment

`configs/fig4d.yaml` defines d = 9, 11, 15, 21, T = 8 and the explicit
approximate p grid 0.004, 0.005, ..., 0.010. These are chosen sample points,
not a claim to know unpublished exact paper points. The default 100,000 shots
per point is an editable fixed-shot budget, not a precision guarantee.
Tests parse that YAML but never construct/sample its large-distance circuits.

## Physical and decoding contract

`adapters.hex_full_knill.HexFullKnill(point, seed=...)` constructs the actual
Hex H5 fixed `knill_online_offline` module sequence for Z memory:

1. Ideal encoded initial data in logical zero.
2. Each stage prepares fresh zero and plus resources with r_0 and r_plus
   noisy X/Z SE rounds respectively, then `CX(plus, zero)` and Hex's Bell coupling,
   destructive X/Z measurement and survivor-frame correction.
3. After eight stages the survivor has a **noisy** destructive Z readout at p.

Hex supplies the rotated-surface matrices (including distance 21), physical
fragments, surface hook ordering and all native preparation, Bell and final
readout `c_func` callbacks. Uniform Hex noise retains its original reset/
measurement flips and two-qubit depolarization; no explicit idle or one-qubit
gate model is added. Offline and online decoders use PyMatching MWPM.
`create_codecapacity_dem=False` preserves original online unit/Hamming weights
and legacy preparation priors, without asserting optimal conditional weights.
No old `knill_hex_dminus2` builder participates.

The runner requires T=8, no theta and False prior mode before creating output.
The standard paper configuration keeps r_0=r_plus=d. Both depths also accept
positive integers and fixed positive multiples of d, such as `"2*d"` and
`"2/3*d"`; these run preparation-depth variants. Fractions and decimals use
exact rational arithmetic and floor the result at each distance. A result
below one or above signed int64 is rejected during config validation. The
resolved depths are passed to Hex and recorded for all eight stages; no depth
is silently replaced with d. See [round-rule syntax](auxiliary_v2.md).

The lower-level adapter also accepts T=1/2 for tiny
protocol fixtures. It exposes `sample(shots)` and `decode_batch(raw_bool)`;
the latter returns `FullKnillBatch(logical_error, corrected_measurements)`.
Raw input is never modified. All physical sampling precedes batch decoding.

Only supplied records enter Hex callbacks. Preparation repair, Bell frames
and terminal decoding follow chronological module order. Packed local Pauli
transitions from the existing bench native adapter replace Hex's much larger
global correction-to-measurement maps. Preparation converters, sparse maps,
decoder handles are cached once per point/worker; one canonical
preparation template per basis shares handles across stages. Local transition
construction precedes support remapping to bound temporary arrays to one block.
The inherited transition LRU holds at most 16 entries. Native objects never
cross process boundaries. Nonzero residual preparation detectors fail the
point; there is no selection or silent decoder fallback.

This is full memory, with no factory terminal oracle, ideal final measurement,
confidence cut or postselection. Every shot is retained. The per-shot error
bit is Hex's final corrected logical value differing from expected zero.

## Execution, outputs and resume

```bash
# Production sweep: deliberate and potentially expensive.
bash scripts/run_fig4d.sh configs/fig4d.yaml

# Editable eight-cycle example; inspect its current shot budget before running.
bash scripts/run_fig4d.sh configs/fig4d_v2_example.yaml

knill-bench-v2 resume results/<fig4d-run>
knill-bench-v2 plot-fig4d results/<fig4d-run> --output fig4d.png
```

The shell wrapper accepts one optional config path. Relative output_root is
relative to the invocation working directory. KNILL_PYTHON may override the
active `knill_system` Conda Python. No sweep is launched by bootstrap.

`experiments.fig4d_reproduction.run(document)` uses B0 RunStore/PointWriter
publication rules. Omitted/auto batch_size uses the shared time-adaptive spawn
scheduler: multiple workers share each point, cache native models locally and
return decoded labels to a parent-owned buffer/writer. buffer_shot controls
Parquet row groups independently of the measured-time chunk sizes. Integer
batch_size retains the historical whole-point, continuing point-seeded sampler
path. Fixed-partition replay remains exact under the same Stim/platform;
auto partitioning depends on timing and does not promise identical records.
See [parallel execution](parallel_execution.md) for caps, seeds, metadata and
resume details. There is no error-target stopping or discarded calibration.

Each completed point has exactly one B0 logical_error Parquet with non-null
contiguous uint64 shot_id and bool logical_error. One writer stays open over
all chunks. Only exact config.yaml, one metadata.json and point files are
required. No circuit, raw-array, log, timing or gap tables are mandatory.

The owning parent verifies completed files, records actual shots/errors and
wall time, and publishes point completion. `execution` in point metadata
records actual preparation depths/roles, noise/readout/prior/decoder settings,
circuit size and sampling policy. Point wall time includes setup, sampling,
decoding, I/O and coordinator wait; it is not decoder latency. Failed points
are not complete data. Resume validates the unchanged source/config/environment,
retains completed files, and restarts unfinished points from shot zero with
their original seeds. The CLI can also execute a B0 `prepare`d Fig.4(d) run
using `resume`. B2 now adds separate factory execution through the same CLI.

## Saved-data statistics and limits

`analysis.fig4d.summarize_saved(path)` streams the saved bool labels and checks
complete status, config/input hashes, schemas, row counts, contiguous IDs and
agreement with metadata error counts. No simulator/decoder is imported or run.
Each row returns d, p, shots, logical_errors, conditional_ler, lower and upper.
With acceptance one, conditional LER = errors/shots. This is failure over the
whole eight-stage experiment, without a per-cycle conversion.

`agresti_coull(k,n)` uses z=Phi^-1(0.975), n'=n+z²,
p'=(k+z²/2)/n', and p' ± z sqrt(p'(1-p')/n'), clipped to [0,1].
The plotted point is k/n; error bars are the two-sided 95% Agresti-Coull
interval. Zero observed errors retain a positive upper bound. The plot's
vertical label is `logical error rate`; the saved `conditional_ler` summary
key is retained for API compatibility, with every shot accepted.
`plot_saved(path, output)` writes only the requested optional figure, grouped
by distance, using a headless Matplotlib canvas. Saved runs can be plotted
without requiring their original simulation environment to match.

Tests compare the exact eight-stage physical module sequence with Hex at d=3,
manual saved raw arrays bit for bit against legacy global-map processing at
T=2, and zero-noise T=1 at d=3/5. Tiny serial/spawn runs verify exact shot
streams, publication/counts, restart and analysis. Numerical interval fixtures
and missing/truncated/shuffled/count-tampered files are covered.
See [TEST.md](../TEST.md) for results and any corrected failed checks.

These checks establish implementation fidelity at tested sizes. The production
sweep, large-distance runtime/memory and statistical agreement with the paper
have not been measured. They do not establish a threshold, general fault
tolerance, or new decoder accuracy/performance. Hex and v1 numerical sources
remain unchanged. See [B2](logical_zero_factory.md) for the separate factory;
[B3](factory_analysis.md) analyzes saved factory acceptance/costs separately.
