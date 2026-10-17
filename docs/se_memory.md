# Ordinary syndrome-extraction Z memory

`kind: se_memory` runs Hex H5's actual
`stabilizer_measurement_circuit(..., pauli="z", surface_code=True,
disable_final_detectors=False)`. Hex sources are read-only. This is a single
rotated-surface-code block, with noisy physical |0> reset, exactly `rounds`
noisy X/Z syndrome-extraction rounds and noisy destructive final Z readout.
There is no teleportation, additional preparation-SE prefix, ideal terminal
oracle, postselection or retry. Only Z-check detector history and final-Z
closure enter the standard logical-Z memory decoder; X checks are physically
measured by Hex as usual. Initial opposite-basis signs are not assumed known.

The experiment is distinct from full Knill's ideal encoded initial boundary
and from the factory's evaluation-only ideal oracle. Comparisons must retain
these labels and specify the respective round/time/resource conventions.
No per-round LER conversion, hardware-duration equivalence or threshold claim
is inferred from this implementation.

## Configuration and launch

```bash
cp configs/templates/se_memory.yaml my_memory.yaml
knill-bench-v2 validate-config my_memory.yaml
knill-bench-v2 run my_memory.yaml --workers 4
# Equivalent shell wrapper:
bash scripts/run_se_memory.sh my_memory.yaml
knill-bench-v2 resume results/RUN_DIRECTORY
```

Minimal fixed experiment settings:

```yaml
schema_version: 2
kind: se_memory
name: my_memory
output_root: results
sweep:
  d: [3, 5]
  p: [0.001, 0.003]
rounds: d
get_logicalgap: true
shots: 64
batch_size: auto
buffer_shot: 10000
target_chunk_seconds: 1.0
workers: 4
master_seed: 12345
```

Only d/p sweep. `rounds` defaults to d and accepts the same positive integer/
d/multiple rules as v2 preparation depths (e.g. `"2*d"`, `"2/3*d"`), floored
exactly and positive at every distance. It is the **total** number of noisy SE
rounds, including the first one. `get_logicalgap` is a strict boolean, default
false. Decoder is MWPM; code/noise retain rotated_surface/hex_uniform defaults.
Knill-only r_0/r_plus/T_tel/theta/create_codecapacity_dem keys are rejected,
as is skip_circuit_validation:true. These memory options cannot be supplied
to the old kinds. V1 numerical APIs and both existing v2 protocols are unchanged.

With gap disabled, p=0 works with its empty DEM and zero detector/observable
predictions. With gap enabled, require 0<p<0.5 and positive finite representable
DEM log weights at model setup. At p=0 the opposite-class log cost has infinite
support cost; it is rejected rather than replaced with a finite Hamming prior,
null or a fabricated gap. Non-graphlike/unsupported models fail explicitly.

For PBS, use the same [cluster launcher](cluster_setup.md):

```bash
mkdir -p logs
qsub -v CONFIG_FILE=my_memory.yaml,KNILL_CONDA_ENV=knill_system \
  scripts/cluster_run_simualtion.sh
```

## Decoding and complementary gap

The adapter extracts the full circuit DEM with strict Stim checks, without
splitting separator components or approximate disjoint errors. Each complete
independent event retains its entire detector/observable signature. Identical
full signatures merge with XOR probability. For the supported memory graphs,
H has one/two detector endpoints per event and L has one logical-observable
row. No full error mechanism, hyperedge or logical-only event is silently
omitted. Weights are w_j=log((1-q_j)/q_j), not factory Hamming weights.

One cached unconstrained PyMatching graph supplies the initial correction e0:

```
H e0 = s (mod 2)
b0 = L e0 (mod 2)
W0 = sum_j w_j e0_j
```

When requested, a second cached graph decodes the **same** detector vector
under the opposite logical constraint:

```
e1 = argmin_e sum_j w_j e_j
     subject to H e = s, L e = 1 XOR b0 (mod 2)
gap = W1 - W0
```

The first prediction and error label are identical with the option on/off.
The cost difference is nonnegative (zero on a class tie). Both H constraints,
the changed L class and native/recomputed weights are checked. A materially
negative difference raises rather than taking abs or switching the first label.
Only tiny floating summation negatives up to 1e-10 are clipped to zero.
Native matching discretizes float weights; unsupported dynamic range or
unresolved ordering raises. This is a **minimum-weight complementary gap**, not
a marginal posterior log-odds or a sum over all errors in a logical class.

Appending L directly to H could make degree-three columns. The decoder instead
finds a binary vertex potential u with L_e=u_a XOR u_b on internal edges.
A one-endpoint edge at a attaches to constrained B_(L_e XOR u_a). The lifted
matrix H_ext=[H;B0;B1] has exactly two endpoints per column and satisfies
L=u^T H XOR B1. For target class b, the extra syndrome bits are
`t1=b XOR u.s`, `t0=parity(s) XOR t1`. These are constrained vertices, not free
matching boundaries. Binary dimensions, degrees, potential, logical identity
and connectedness to both boundaries are validated once. General spacetime
graphs need not be planar; this algebra does not require the spatial planarity
restriction of Hex's separate factory-only SurfaceMWPMHomologyGap class.
No dependency check is bypassed or monkeypatched.

The adapter converts raw measurements to detectors and the actual observable,
then passes **only detectors** to inference/gap scoring. Only afterward is
`logical_error = predicted_observable XOR actual_observable` evaluated.
Altering a terminal logical measurement without changing detectors changes
the label, never the gap. No truth, oracle or success label enters the decoder.

## Parquet and metadata

Output retains exact YAML (or effective CLI-override YAML), one metadata.json,
one error table and, only when requested, one aligned gap table per d/p:

| Table | Columns |
| --- | --- |
| logical_error | shot_id:uint64, logical_error:bool |
| logical_gaps | identical shot_id:uint64, gap_t001:float64 |

`gap_t001` is the score for the **whole memory trajectory**, not an intermediate
round or factory stage. The nullable v2 schema is retained, but every requested
memory gap must be present, finite and nonnegative. IDs are contiguous from
zero. Every shot is saved regardless of score.

Example filename (existing required keys, including literal r_+, are retained):

```
logical_gaps__code=rotated_surface,d=3,p=0.003,noisemodel=hex_uniform,T=1,r_0=0,r_+=0,rounds=3.parquet
```

For memory, T=1 identifies the single saved trajectory score. r_0=r_+=0 state
that no Knill resource preparation is performed. Physical round count is the
explicit rounds key; metadata says teleportations=0. These compatibility keys
do not add operations and are excluded from memory's physical seed identity.
Resolved rounds do enter physical identity. get_logicalgap changes the run
configuration and output tables but never physical identity or point/chunk
seeds. Existing kinds retain their original canonical config/point hashes.

Execution metadata records actual rounds, noisy boundaries/noise, selected
sector, full-circuit DEM policy, graph and circuit/DEM hashes, optional gap
policy/units/scope, and the shared scheduler's actual sampling/partition details.
It does not relabel these scores as factory gap units or terminal-oracle LER.

Both auto and fixed execution share [bounded output](parallel_execution.md).
Models/converters/matching graphs stay cached per point/worker; there is no
per-shot constructor. Auto chunks use the existing chunk-seed stream and
buffer_shot-sized row groups; fixed mode advances its point-seeded sampler.
For exact common-record gap-on/off comparisons, use the same fixed batch_size.
Auto timing can change partitions/records when extra decoding changes runtime.
Both tables close/fsync/validate before public renames and parent completion.
Unfinished points restart at zero; completed points remain untouched. RunStore
rejects changed config/source/environment before resume cleanup.

Tests use d3/5 and <=7-shot physical batches. They compare the exact Hex circuit,
ordinary decoder labels, first/opposite constraints and truth isolation, tiny
exhaustive sector minima and independent MILP costs on the d3 circuit DEM.
Serial/spawn, optional-file schemas/IDs, buffer grouping, caching and restart
are exercised. Production sweeps and performance/threshold claims are excluded.
