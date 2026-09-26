# Implementation prompt: `knill_bench`

Implement a working, reproducible research simulation package named `knill_bench`. Follow the specification below, inspect the actual dependency APIs, and complete the implementation through small validated end-to-end experiments. Do not stop after producing a plan or scaffolding. Do not run a production-scale sweep during implementation.

The purpose is to compare logical error rates (LER), decoder execution times, and decoding workload for conventional syndrome-extraction memory and three Knill-memory strategies. The comparison must distinguish changes in the quantum circuit from changes in the decoder and from differences in computational resources.

## 1. Repository and dependency policy

Use these projects:

- The user's modified Hex: <https://github.com/AKTKN/Hex>. Start from the user's designated implementation branch, create a separate integration branch/worktree for this project, and preserve existing workflows.
- A user-owned fork of `lomatching`: <https://github.com/MarcSerraPeralta/lomatching>.
- A user-owned fork of `surface-sim`: <https://github.com/MarcSerraPeralta/surface-sim>.
- `stim`, `pymatching`, `ldpc` with BP-LSD, `numpy`, `scipy`, `PyYAML`, and `pyarrow` for Parquet. Use a lightweight validated configuration model; add dependencies only when justified.

Inspect applicable `AGENTS.md` files, repository status, documentation, and APIs before modifying repositories. Use existing forks when present. Keep dependency changes minimal and isolated in their integration branches. Do not replace the user's Hex implementation with upstream Hex or silently use a PyPI package instead of the requested checkout. If remote fork operations are unavailable, continue with local integration branches and document the exact remaining remote setup; do not claim that a fork exists.

Install development checkouts as editable dependencies using a documented bootstrap script. Record upstream URL, fork URL when available, branch, commit SHA, dirty status, and actual imported module path. Pin reproducible non-development installations to exact revisions/versions. Preserve relevant licenses and citations.

Source observations to recheck, not assumptions about every future revision:

- Hex's inspected branch was `hex-adaptive`, commit `5de58f2f80791054411ad3c0885a4fe3671ed56a`.
- Inspected `lomatching` commit: `b55a7a65969a106a547622287b620f0da2cb5e39`; its project version was `0.3.0`.
- Inspected `surface-sim` commit: `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad`; its project version was `0.11.0`.
- Hex's README exposes parallel experiments through the separate `ewanmurphy/Experiments` project (`experiment local-run ... --parallel ...`). Inspect that implementation if useful. Reuse its process-isolation/parameter-sweep pattern where appropriate, but do not assume Hex has a reusable internal process-pool API.

This request authorizes implementing the package and necessary local dependency changes. Continue between verification stages without repeatedly requesting confirmation. Preserve unrelated local changes. Report substantive blockers and do not silently change the scientific experiment to bypass them.

## 2. Mandatory experiment matrix

Implement the following four protocols as distinct, stable identifiers:

| Protocol ID | Ancilla preparation | Additional SE after transversal gates | Decoding strategy |
|---|---|---|---|
| `se_memory` | No Knill Bell ancillas | Ordinary repeated SE on the memory patch | Full-history MWPM and, explicitly selectable, global BP-LSD |
| `knill_hex_dminus2` | Exactly `d - 2` SE rounds per fresh zero/plus ancilla | None beyond the chosen legacy Hex protocol | Existing Hex-style offline preparation decoding followed by online code-capacity Bell-measurement decoding and final readout decoding |
| `knill_aft_postgate` | Exactly one SE round per fresh zero/plus ancilla | Exactly one full X/Z SE round after each of the two transversal CNOT layers | Correlated observable decoding using LOM, or explicitly selected global BP-LSD |
| `knill_aft_prep_only` | Exactly one SE round per fresh zero/plus ancilla | Zero | Correlated observable decoding using LOM, or explicitly selected global BP-LSD |

Requirements:

1. Implement all four; do not substitute one for another.
2. Start with the same rotated surface-code family and matching physical-qubit/check/logical-operator ordering across protocols. Odd distances `d >= 3` make `d - 2` positive. Validate unsupported distances rather than silently rounding.
3. Run separate X-memory and Z-memory experiments. They are complementary experiments, not simultaneous destructive measurements of the same output patch.
4. No postselection and no adaptive preparation length in the mandatory experiments.
5. `d - 2` is an experimental preparation length. Do not claim that it guarantees gadget-level fault tolerance for the implemented circuit, noise model, or approximate decoder.
6. In `knill_aft_postgate`, the default post-gate SE scope is **all currently live code blocks** after each transversal CNOT layer. Thus, with live blocks D, A, B, both post-gate rounds act on D, A, B, including blocks about to be destructively measured. Record this scope. An optional `gate_operands` variant must be distinctly labeled and must not replace the default.
7. During fresh-ancilla preparation, the preparation rounds apply to A and B. Do not silently insert preparation-time SE on D. Waiting noise, when enabled, is a separate explicit schedule choice.
8. The AFT variants use the entire available measurement history through the final memory readout. Initially implement terminal, full-history decoding. This is not a demonstration of bounded-memory streaming or real-time feedforward.
9. Retain the native Hex decoder pipeline for `knill_hex_dminus2`. A global BP-LSD/LOM decoding of its raw quantum circuit can be added as a clearly labeled decoder ablation; it is not the native legacy pipeline.

The default analysis must support both (a) the four intended protocol/decoder pipelines and (b) decoder-controlled comparisons, particularly global BP-LSD on the identical SE/AFT circuits. Record decoder identity separately from protocol identity.

## 3. Quantum-circuit definition and shared primitives

Create a common code description containing the binary matrices `H_X`, `H_Z`, logical representatives, qubit/check ordering, coordinates, and boundary conventions. Verify `H_X H_Z^T = 0`, logical commutation, and the one-logical-qubit assumption. If using a `surface-sim` layout, explicitly map it to the Hex ordering and verify equivalence. The unrotated-code example in the LOM README is a reference test, not a replacement for the rotated-code comparison.

Use common low-level SE, reset, destructive measurement, and transversal-CNOT primitives wherever possible. Relevant Hex functions include:

- `get_parity_check_matrices("surface", d)`;
- `create_stabilizers_and_block_template` and `generate_blocks`;
- `measure_X_stabilizers_surface_code`, `measure_Z_stabilizers_surface_code`;
- `transversal_cnot`, `qubit_initialisation`, and `qubit_measurement`;
- `stabilizer_measurement_circuit_both_detectors` as a reference for preparation.

Verify their signatures and hook-error ordering in the checked-out revision. Set the surface-code-specific option where required. Do not copy a convenient complete memory generator with different boundary, hook, or noise conventions into only one arm of the comparison.

For cycle j, use the Hex circuit orientation:

1. Input block `D_j`; prepare fresh `A_j` from physical `|0>^n` and `B_j` from physical `|+>^n` with the protocol's preparation length.
2. Apply transversal `CX(B_j, A_j)` to form the Bell resource.
3. Insert the configured post-gate SE, if any.
4. Apply transversal `CX(D_j, A_j)`.
5. Insert the configured post-gate SE, if any.
6. Destructively measure D_j in X and A_j in Z.
7. The output B_j becomes D_{j+1}.

Fresh physical block IDs per cycle are acceptable initially. Resource accounting must use block lifetimes; the largest simulator qubit index is not the peak physical-qubit requirement.

For the native Hex pipeline, retain its preparation repair, decoded Bell outcomes, and propagation of inferred corrections. Instrument existing functions or add backward-compatible hooks rather than approximating the pipeline by a different decoder. Regress against the legacy implementation on the same raw records whenever possible. Preserve the legacy decoder-prior policy as the default; any revised prior is a separately labeled ablation.

For both AFT variants, preserve raw preparation and Bell measurement records, do not independently decode/commit the preparation signs, and do not run an extra code-capacity decoder before correlated decoding. Do not apply a Pauli correction both physically and by flipping records. A static Clifford circuit with final Pauli-frame interpretation is sufficient for these nonadaptive memory experiments.

### Boundaries and noise

Implement a common initial boundary policy:

- Default `ideal_encoded`: exact initial logical zero/plus with known stabilizer signs, used consistently for all protocols.
- A configurable common noisy preparation boundary, including `d` SE rounds, as an additional experiment. Record how its frame is interpreted. Do not treat noisy initial signs as exact or choose a boundary using the unknown sampled error.

Use the same final destructive-readout noise convention in all protocols. Do not append an undeclared perfect SE round or extra `d` rounds to the AFT variants.

Implement and name a `hex_legacy` noise profile reproducing the inspected Hex locations and probabilities. Its low-level code includes two-qubit depolarization and preparation/measurement flips, but no explicit idle noise; verify this against the selected branch. Record every included/omitted operation class. Do not label it a fully uniform gate/idle noise model.

Also support a shared explicit circuit-noise configuration (`p1`, `p2`, reset, measurement, idle per declared time unit) with a documented layer schedule. Derive named rates from the sweep parameter p through validated multipliers, not arbitrary Python expressions. Apply noise once, including when a fork's generator already inserts noise. Physical sampling must use the actual Stim circuit.

Treat equal cycle counts and equal elapsed time as different comparisons. Implement equal-cycle comparison first. For equal-time mode, specify preparation overlap/waiting and gate durations, build and save the actual schedule, and match actual exposure or report the residual mismatch. Do not divide by a guessed constant, assume a factory is free, or infer physical time from unscheduled instruction count. If elapsed time is undefined in `hex_legacy`, store null rather than an invented duration.

## 4. Measurement ledger, detectors, and observables

Maintain a measurement ledger mapping `(cycle, block, operation, check_or_data_index)` to absolute measurement-record indices, with qubit IDs and basis. Maintain separate logical-layer, SE-round, and physical-time indices. Generate Stim record offsets from this ledger.

Build circuit-wide deterministic detectors. Include preparation boundaries, cross-block relations under CNOT, and destructive-measurement closure. A first opposite-basis stabilizer outcome during preparation is generally random and is not a standalone deterministic detector.

Use verified Pauli-flow/stabilizer propagation or the forked `surface-sim` detector machinery. For CNOT, track

`X_c -> X_c X_t`, `X_t -> X_t`, `Z_c -> Z_c`, `Z_t -> Z_c Z_t`.

Ensure that detector relations cancel random preparation signs rather than setting them to zero. Use the LOM paper's pre-gate detector frame as the initial compatibility target, or demonstrate and document an equivalent supported basis. Do not assume any arbitrary detector basis supports the same automatic observing-region extraction.

For N Knill cycles, let each `m_X`/`m_Z` be the raw physical measurement parity on the fixed corresponding logical representative. With no explicitly applied byproduct corrections, define the terminal reliable observables:

`o_Z = m_Z(D_N) XOR XOR_{j=0}^{N-1} m_Z(A_j)`;

`o_X = m_X(D_N) XOR XOR_{j=0}^{N-1} m_X(D_j)`.

Use one selected-basis observable `L0` per memory circuit. Verify the convention by backpropagating through the circuit and checking the known initial states. Intermediate Bell outcomes are individually random; do not declare each a deterministic observable. For a circuit with explicit feedback/corrections, derive the equivalent observable consistently instead of adding the byproduct twice.

Use `allow_gauge_detectors=False` for production models and validation. Nondeterministic detectors/observables are circuit-construction failures; do not hide them using gauge-detector allowance, removed records, extra ideal rounds, or a decoder fallback.

Important `surface-sim` behavior: in its logical `schedule_from_circuit` interface, `TICK` requests a QEC round on active layouts. It is not merely a timing separator. Separate this logical meaning from physical Stim `TICK` instructions. Inspect iterator/decorator behavior and assert actual SE counts on every block so the `prep_only` arm contains no hidden extra SE.

## 5. Decoder adapters

Place all external-package imports and integration logic under `src/knill_bench/`. Define typed interfaces for compiled experiments, raw samples, decoder predictions, timing records, and optional diagnostics. Decoder outputs must state whether they are physical/fault corrections or logical-observable flip predictions.

### 5.1 MWPM and LOM

Use PyMatching for supported SE/code-capacity problems and `lomatching.MoMatching` for observing-region decoding. Inspect the actual APIs:

```python
MoMatching.from_circuit(encoded_circuit, stab_coords, allow_gauge_detectors=False)
MoMatching(dem=full_dem,
           dem_subgraphs=[observable_dem],
           det_inds_subgraphs=[global_detector_indices])
```

`from_circuit` expects detectors and reliable observables to already exist. Detector coordinates must identify the correct block/check type, with time in the last coordinate. The manual constructor is appropriate when explicit observing-region extraction is more reliable for the Hex circuit.

Use `lomatching.util.get_circuit_subgraph` where appropriate. Preserve mappings between local and global detector IDs, and between observable IDs. Test extraction on a documented surface-sim/LOM example before custom Knill circuits. Handle zero-noise validation without relying on nonzero DEM boundary-error terms to discover an observing region.

Validate selected subgraphs before claiming MWPM support. Save graphlike/decomposable/nondecomposable diagnostics and exception details. Graph decomposition and correlated matching are not synonymous; record whether edge correlations are actually used by the installed implementation. Never silently discard a hyperedge or use `ignore_decomposition_failures=True` as a repair.

Implement an explicit configuration policy `on_nonmatchable: error | bplsd_global`. The fallback is a **case-level decoder-construction choice**, recorded as requested/effective decoder and reason. A full DEM containing hyperedges does not by itself make LOM unusable: inspect the relevant subgraphs first. Do not catch arbitrary exceptions, nondeterministic-observable errors, or indexing bugs and reinterpret them as nonmatchability.

### 5.2 Global BP-LSD without X/Z separation

This is a mandatory selectable decoder, not merely a last-resort placeholder. Apply it to SE and both AFT variants. It uses all deterministic detector rows from both stabilizer sectors in one model.

Extract an undecomposed DEM, construct sparse binary matrices

`H_det in F_2^(n_detectors x n_faults)` and
`L_obs in F_2^(n_observables x n_faults)`,

and a fault-probability vector `q`. Each column represents one DEM error mechanism, including its complete detector support and observable support. For observed detector vector s:

`e_hat = BP_LSD(H_det, q, s)`;
`predicted_observable_flips = L_obs @ e_hat mod 2`.

The approximate optimization target is a likely fault vector with `H_det @ e_hat = s`, using priors q. This is not guaranteed logical maximum-likelihood decoding.

Verify the installed import/signature, for example:

```python
from ldpc.bplsd_decoder import BpLsdDecoder
decoder = BpLsdDecoder(
    H_det,
    error_channel=q.tolist(),
    max_iter=max_iter,
    bp_method="minimum_sum",
    ms_scaling_factor=ms_scaling_factor,
    schedule="parallel",
    lsd_method="LSD_0",
    lsd_order=0,
)
```

Expose supported BP/LSD parameters in YAML and reject unsupported combinations explicitly. The BP update schedule named `parallel` is not a promise of multi-core execution. Verify actual support for batch decoding; if absent, loop over shots within worker processes and time that implementation honestly.

DEM conversion rules:

- Preserve multi-detector hyperedges and shared X/Z-sector fault variables. Do not split them into independent columns or separate decoders.
- Expand repeat/shift instructions correctly; use sparse storage and avoid quadratic intermediate structures.
- If an imported DEM has `^` separators, they are components of the **same** error event. Reconstruct its XOR support, including repeated-target cancellation. Do not treat components as independent errors.
- Distinguish columns with identical detector support but different logical support. If merging identical full `(H_det column, L_obs column)` supports for independent DEM events, use `q_merged = (1 - product_i(1 - 2*q_i))/2`, not a sum.
- Preserve undetectable logical-error terms. If a backend cannot accept zero-detector columns, treat their prior explicitly with a documented prediction convention; never discard their contribution from truth/error accounting. Ignore fully trivial terms only with a recorded justification.
- Validate dimensions, binary parity, zero/no-fault cases, probability limits, and `H_det @ e_hat == s`. Record residual-syndrome weight and decoder failures.
- Do not feed a uniform p as every circuit-fault prior.
- Default to strict DEM extraction. Any required approximation of disjoint/exclusive noise must be opt-in, documented, and recorded. Retaining joint DEM columns does not make BP-LSD exact inference for arbitrary correlated noise.

The `lomatching` DEM utilities may be reused only after checking their assumptions. The inspected `dem_to_hpl_list` rejects decomposed terms with separators; do not assume it implements all conversion cases above.

For decoder-comparison experiments on the same circuit, sample once and pass the same syndromes to each decoder. Never let actual logical flips or injected-error ground truth enter decoder inference or parameter selection.

## 6. Timing: distinguish latency, throughput, and workload

Implement two measurement modes:

1. `throughput`: batched physical sampling and batched decoding when supported. Report batch wall time, batch CPU time, shots/s, and amortized time/shot.
2. `latency`: sample first, then time individual decode invocations on a representative, deterministically selected subset using `perf_counter_ns` and `process_time_ns`. Exclude sampling, disk I/O, compilation, and initialization from the decoder-call timer. Include and separately identify necessary adapter preprocessing/postprocessing.

Do not call `batch_time / batch_size` single-shot latency or manufacture per-shot latency values from a batch. Warm up each decoder, exclude warm-up from reported steady-state timings, and record warm-up policy. Use fixed per-process thread limits to prevent oversubscription. Provide an isolated one-worker timing/replay command for comparable latency measurements; timings from simultaneous production workers must be labeled as concurrent-load measurements.

For native Hex, instrument separately:

- preparation/offline decoding, including both ancilla types and all actual calls;
- Bell/code-capacity decoding;
- final readout decoding;
- frame propagation and adapter/classical postprocessing;
- decoder construction/model setup, outside steady-state call time.

For SE and AFT, report terminal full-history decoder invocation time and the history size. Also report total classical decoding work per memory shot and per declared protocol cycle, with units. Do not compare a single Hex Bell call directly against an entire AFT history and label the difference a real-time latency advantage. Summed service times are not an actual parallel critical-path latency. Streaming/windowed decoding can be an extension, but is not required here and must not be implied by the initial results.

Collect mean, standard deviation, median, p90, p95, p99, maximum, and timing sample count from actual call observations. Do not average worker percentiles. Keep raw timing events or sufficient retained observations so quantiles are calculated correctly. Label wall time and process CPU time separately; process CPU measurements may include internal threads.

Optional expensive BP/LSD diagnostics must be configurable and disabled for the primary uninstrumented timing measurement, or their overhead must be measured and labeled. Supported diagnostics include BP iterations/convergence, LSD use, cluster counts/sizes, residual syndrome, and recovery weight. Check actual public properties and reset per-shot statistics; unavailable fields are null with an availability indicator, not zero.

## 7. Parallel execution and deterministic work allocation

Parallelize independent simulation work using processes, following the operational pattern of Hex's existing experiment runner. A bounded process pool with a spawn-safe worker initializer is sufficient; no distributed task framework is needed.

- Support parallel parameter points and splitting one parameter point into independent shot chunks. Avoid nested pools.
- Construct/cache Stim samplers and decoder objects inside each worker; do not repeatedly pickle live native objects or rebuild decoders per shot.
- Bound chunk size, pending work, model caches, and in-flight sample memory.
- Derive independent sampling seeds from a master seed plus stable sampling-case, replicate, and chunk IDs using a stable digest/SeedSequence. A sampling-case ID identifies the physical circuit and boundary/noise parameters and excludes decoder settings and worker count. Never use Python's randomized `hash`, PID, current time, or worker completion order. Separate decoder randomness and timing-subset randomness from physical sampling seeds.
- Decoders evaluating the same circuit/chunk use the same physical samples. Different protocols sharing a numeric seed are not automatically paired trials.
- Fixed case/chunk IDs must produce the same sample workload for one-worker and multi-worker runs under the same pinned environment and batch partition. Do not promise bit-identical Stim samples across versions, SIMD platforms, or changed sampling call sizes.
- Support fixed-shot stopping as the primary statistical mode, plus explicit max-shot/target-error/time-budget limits. Record the stopping rule, actual counts, and overshoot. For error-based stopping, use a declared reference decoder or a documented all-decoder policy; do not silently choose whichever decoder finishes first.
- For reproducible error-based stopping, commit chunk results in deterministic chunk order and declare treatment of already-running excess chunks. Fixed-shot binomial intervals are not automatically exact under sequential stopping; label intervals accordingly.
- Save completed chunks atomically, support resume without duplicate counting, and validate config/model/environment compatibility. Different worker counts can be permitted if work IDs and model/seed settings are unchanged. Code/model changes must create a new run or require an explicit, recorded compatibility decision.
- Decoder diagnostics and retained samples must remain bounded. With per-shot result storage enabled, write incremental Parquet parts rather than accumulating the full experiment in memory.
- Worker failures must have an explicit status and must not disappear from denominators. A killed/retried chunk must retain the same task identity and seeds.

Use `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` consistently in launch scripts, without overriding an explicit compatible user setting. Record effective values. Provide a simple PBS launch example only if it fits the user's available environment; local shell execution is mandatory.

## 8. Package organization and commands

Use a standard `src` layout. The following is a suggested organization; combine small files where sensible without removing responsibilities:

```text
pyproject.toml
README.md
src/knill_bench/
    __init__.py
    cli.py
    config.py
    models.py
    codes.py
    circuits/       # shared primitives, four builders, schedules, ledger/flows
    adapters/       # Hex, surface-sim, LOM, PyMatching, BP-LSD integration
    decoding/       # DEM conversion and common result/timing interfaces
    simulation/     # sampling, workers, runner, seeds, checkpoints
    data/           # typed Arrow schemas, atomic writers, manifests
    analysis/       # aggregation, comparisons, plots
configs/
    smoke.yaml
    benchmark.yaml
scripts/
    bootstrap.sh
    run_simulation.sh
    run_simulation.py
    benchmark_latency.sh
tests/
docs/
    design.md
    validation.md
    data_schema.md
    dependencies.md
```

Shell scripts must invoke thin Python launchers or the installed module. All scientific/simulation logic and external-package integration belongs under `src/knill_bench`, not in scripts/notebooks. The package must import and run outside the repository directory after installation; avoid `sys.path` hacks.

Provide commands equivalent to:

```bash
bash scripts/bootstrap.sh
bash scripts/run_simulation.sh configs/smoke.yaml
python -m knill_bench.cli validate-config configs/benchmark.yaml
python -m knill_bench.cli build configs/benchmark.yaml
python -m knill_bench.cli run configs/benchmark.yaml
python -m knill_bench.cli resume results/<run-directory>
python -m knill_bench.cli benchmark-latency results/<run-directory> --workers 1
python -m knill_bench.cli analyze results/<run-directory>
```

Implement the commands rather than merely documenting them. Use quoted shell arguments, propagate exit codes, and use `set -euo pipefail` where appropriate.

## 9. YAML configuration

Use safe YAML loading, strict validation, canonical resolved JSON, and explicit units. Do not use `eval`. Implement named rules such as `d_minus_2`, and structured lengths such as `cycles_per_distance`, resolving them to integers before execution. Reject unknown fields and incompatible decoder/protocol combinations with actionable errors.

The following expresses the required configuration capabilities. You may refine the schema, but ship working YAML files matching the implementation and document any change:

```yaml
schema_version: 1
experiment:
  name: four_protocol_surface_memory
  master_seed: 12345
  output_root: results
  code: rotated_surface
  distances: [3, 5, 7]
  bases: [x, z]
  physical_error_rates: [0.0005, 0.001, 0.002]
  cycles_per_distance: [1, 3, 10]
  replicates: 1
  initial_boundary: {kind: ideal_encoded}
  final_readout: noisy_destructive
  comparison: {kind: equal_cycles}

noise:
  profile: hex_legacy

decoders:
  mwpm: {kind: pymatching}
  lom:
    kind: lomatching
    on_nonmatchable: bplsd_global
    fallback_decoder: global_lsd
  global_lsd:
    kind: bplsd_global
    bp_method: minimum_sum
    max_iter: 100
    ms_scaling_factor: 0.75
    schedule: parallel
    lsd_method: LSD_0
    lsd_order: 0
  hex_native:
    kind: hex_native_pipeline
    offline_decoder: pymatching
    online_decoder: pymatching
    final_readout_decoder: pymatching
    prior_policy: legacy

protocols:
  - id: se_memory
    decoders: [mwpm, global_lsd]
  - id: knill_hex_dminus2
    prep_rounds: {rule: d_minus_2}
    decoders: [hex_native]
  - id: knill_aft_postgate
    prep_rounds: 1
    post_gate_rounds: 1
    post_gate_scope: all_active
    decoders: [lom, global_lsd]
  - id: knill_aft_prep_only
    prep_rounds: 1
    post_gate_rounds: 0
    decoders: [lom, global_lsd]

sampling:
  workers: 8
  shots_per_case: 100000
  chunk_size: 4096
  stop_rule: fixed_shots
  max_pending_chunks_per_worker: 2
  native_threads_per_worker: 1

timing:
  collect_batch_times: true
  latency_sample_count_per_case: 1000
  latency_sampling: deterministic_uniform
  warmup_shots: 32
  isolated_replay_workers: 1

storage:
  format: parquet
  compression: zstd
  save_shot_results: true
  save_decoder_calls: true
  save_all_syndromes: false
  retained_failure_samples_per_case: 100
  retained_uniform_samples_per_case: 100

diagnostics:
  bp_lsd_stats: sampled
  structural_metrics: true
```

Explicitly record requested and effective decoders. If `lom` falls back to the already selected `global_lsd`, avoid redundant decoding/timing on that chunk while preserving a clear alias/fallback record. The example BP parameters are a starting configuration, not a performance-optimal claim.

The smoke configuration must be small: distances 3 and 5, both bases, a few cycles, all four protocols, both global BP-LSD and matching paths where valid, at most a few hundred shots per point, and two workers. Use a correspondingly small timing subset. Run it during implementation; do not launch the benchmark YAML automatically. At d=3, `d - 2 = 1`, so include d=5 to exercise the actual difference in preparation lengths.

## 10. Output layout, Parquet schema, and reproducibility

Create one timestamped run directory using UTC and a collision-resistant suffix, for example:

```text
results/20260921T134500.123456Z_<run-id>/
    config.original.yaml
    parameters.json
    environment.json
    manifest.json
    circuits/<circuit-id>.stim
    models/<model-id>.dem
    models/<model-id>.metadata.json
    data/cases.parquet
    data/batches/part-*.parquet
    data/decoder_batches/part-*.parquet
    data/shots/part-*.parquet
    data/decoder_calls/part-*.parquet
    data/diagnostics/part-*.parquet
    data/retained_samples/part-*.parquet
    summary.parquet
    plots/
    logs/
```

Directories of Parquet parts are valid Parquet datasets; do not force workers to append to a shared file. Use explicit versioned Arrow schemas, stable column types, typed nulls, and atomic finalization. JSON is for configuration/provenance/manifest, while numeric/tabular experiment results are Parquet. Model and circuit artifacts may use their native text/sparse formats.

Required information, organized into normalized tables rather than repeated large blobs:

| Table | Unit of observation | Required fields |
|---|---|---|
| `cases` | Circuit and decoder case | Stable IDs/hashes, protocol, distance, basis, p, rates, cycles, preparation/post-gate rounds and scope, geometry, boundary/noise/schedule IDs, requested/effective decoder, parameters, fallback status/reason, validation status |
| `batches` | Physical sampling chunk | Circuit/replicate/chunk IDs, seed, shot range, actual shot count, sampling wall/CPU times, worker/load metadata, completion/error status |
| `decoder_batches` | Decoder on a sampling chunk | Decoder case ID, chunk ID, errors, valid/failed decode counts, batch decode wall/CPU times, postprocessing time, observable count, scope/history size |
| `shots` | Shot and decoder result | IDs, shot index, actual/predicted logical flips, logical failure, decoder status, syndrome weight, residual weight when defined, nullable BP/LSD diagnostics |
| `decoder_calls` | Actual timed invocation | Shot or batch ID, phase, cycle/block/sector if applicable, input size, decoder/backend, batch size, timing mode, wall/CPU ns, preprocessing/postprocessing ns when measured, warm-up/profiling/load flags |
| `diagnostics` | Structural or sampled diagnostic | Detector/fault/observable counts, sparse nnz, column-weight/hyperedge distributions, selected-subgraph sizes, decoder diagnostic availability and model-validation results |
| `retained_samples` | Bounded replayable sample | IDs, packed syndrome and optionally raw measurements, actual observable bits, logical record lengths, bit order, retention reason and sampling policy, circuit/model hashes |
| `summary` | Aggregated case | Counts, LER/intervals, computational-failure rate, timing counts/statistics/quantiles, throughput, total decoding work, resource/exposure metrics |

Do not allocate full-fault error vectors for every shot unless explicitly requested. Store compact logical bits and use bit-packed binary fields for retained syndromes/measurements, with explicit lengths and bit order. Retain a bounded uniform subset in addition to a bounded failure subset so replay/latency analysis is not restricted to difficult shots. For native Hex replay, detector syndromes alone may be insufficient: retain the raw module measurement records required by its pipeline.

Record BP convergence separately from final LSD correction validity. A decoding exception or inconsistent recovery is a computational failure, not a shot to discard. Report logical failure among valid predictions together with failure count and a conservative total task-failure rate counting computational failures; if all predictions are valid these agree. Do not silently replace missing predictions with ground truth.

Include resource diagnostics: number of data/check qubits per block, peak live blocks/qubits, total block preparations, SE counts by block and phase, reset/measurement/one-/two-qubit gate counts, noise-location counts, detector/matrix sizes, and modeled spacetime volume only when the schedule defines time. Preserve the distinction between allocated simulation IDs and live hardware resources.

`parameters.json` must contain the fully resolved parameter grid and stopping/timing/storage policies, not only the original YAML. Save configuration hashes, seed derivation version, batch partition, package versions, Python/platform/CPU/thread information, dependency revisions, actual import paths, circuit/DEM hashes and extraction options, invocation arguments, and start/end times. For dirty source trees, retain a reproducible patch/snapshot reference; a dirty flag alone is insufficient. Do not collect unrelated secrets or the entire environment.

## 11. Analysis outputs

Provide an analysis command that reads the Parquet datasets and generates:

- Per-experiment LER with denominators and binomial intervals, including a nonzero upper bound when no failures are observed.
- LER versus p and distance for the four intended pipelines.
- LER versus decoder wall-time/work, with timing scope and history length explicit.
- Latency distributions/quantiles for actual individual invocations, and separate batched-throughput plots.
- Native Hex offline, Bell, final-readout, and frame-processing cost breakdowns.
- BP convergence/LSD-use/iteration and available cluster statistics, split by successful/failed logical prediction where sample sizes permit.
- Hyperedge/subgraph/model-size diagnostics against decoding cost.
- Paired decoder-disagreement statistics on identical circuit shots, without presenting different-protocol trials as paired merely because seeds match.
- Equal-cycle results and, when configured with an explicit schedule, equal-time and resource-cost comparisons.

For fixed-shot cases use documented Wilson or exact binomial intervals. Label sequential-stopping intervals appropriately. Aggregate counts, not averages of per-worker LERs. The optional conversion `p_cycle = (1 - (1 - 2*P_fail)^(1/N))/2` assumes identical independent per-cycle binary flips and negligible/handled boundary effects; do not use it as the primary metric or apply it silently. Do not claim a threshold or an asymptotic exponent from a small smoke experiment.

## 12. Verification stages and acceptance criteria

Work through these stages, report findings briefly, and continue automatically once each stage passes. Keep `docs/validation.md` updated with commands, results, and remaining limitations.

### Stage A: dependency and reference checks

- Reproduce a small native Hex run using the designated branch.
- Reproduce the documented surface-sim/LOM example and inspect the actual emitted SE count.
- Verify BP-LSD decoding and diagnostics on a small known binary model.
- Confirm imports resolve to the intended forks/checkouts.

### Stage B: circuits and boundaries

- Build all four protocols for d=3,5, both bases, and N=1,2.
- Assert exact preparation/post-gate SE counts, measurement ledger validity, common geometry/logical convention, and noise placement.
- At p=0, verify deterministic detector and observable parities and zero failures, while allowing the expected random individual preparation/Bell outcomes.
- Use strict Stim DEM extraction and flow checks where supported. No hidden ideal measurements or gauge-detector allowances.
- Ensure adding measurement-producing operations preserves/recomputes all record offsets correctly.

### Stage C: decoder/model validation

- Check DEM-column syndrome/observable effects against injected faults or a trusted small-model sampler, including joint X/Z faults, separator terms, repeated targets, duplicate supports with different logical labels, and detector-free logical terms.
- Compare the SE matching adapter with a trusted matching result on the same circuit and shots.
- Check native Hex integration against its original pipeline on the same raw samples, including correction propagation and final readout.
- Check LOM detector-index/observable mapping on tiny circuits; verify known observing regions before relying on automatic extraction.
- At d=3, enumerate relevant single physical Pauli faults, distinguish circuit distance failures from approximate-decoder failures, and save any counterexamples. Examine higher-weight faults at d=5 only within a bounded diagnostic budget.
- Do not treat the graphlike distance of a decomposed matching model as a proof of the original circuit's distance. Do not rewrite a failing research arm into a different circuit solely to pass a desired FT assertion.

### Stage D: parallelism, storage, and timing

- For fixed shots/chunks and pinned environment, one-worker and two-worker sampling must agree on task IDs, sampled results, predictions, and counts; timing values need not agree.
- Resume an intentionally interrupted run without missing/duplicate completed chunks.
- Read every produced Parquet dataset back and verify schema, counts, null semantics, and manifest consistency.
- Verify no warm-up, simulation, or file-writing time is included in the decoder-only timer; distinguish batch amortization from per-call latency.
- Verify bounded sample retention, actual stopping behavior, and explicit handling of worker/decoder failures.

### Stage E: end-to-end research smoke run

- Run the small YAML through the required shell -> Python entry point.
- Exercise all four protocols and explicitly exercise global BP-LSD, even when LOM works.
- Exercise nonmatchable-model fallback using a controlled test, without weakening invalid-circuit checks.
- Generate timestamped outputs, JSON provenance, Parquet results, and analysis plots/tables.
- Produce a short report stating what was validated, what remains a scientific question, and exactly how to run a larger sweep.

Acceptance requires executable implementations rather than placeholder classes or fabricated diagnostics. If a dependency limitation prevents one path from working, retain a minimal reproducible case and clearly identify the blocker. Complete the remaining authorized paths and do not report the four-way experiment as complete until all four circuits run with at least one specified decoder. A LOM limitation may legitimately be handled by the explicitly configured global BP-LSD fallback; a nondeterministic or incorrectly specified circuit may not.

## 13. References and expected final implementation report

Consult the actual sources and the locally provided papers where relevant:

- [User's Hex](https://github.com/AKTKN/Hex), especially `src/hex_qec/protocols/knill_online_offline.py`, `modularisation/module_generation.py`, and `circuit_generation/circuit_generation.py`.
- [Hex experiment runner](https://github.com/ewanmurphy/Experiments).
- [LOM implementation](https://github.com/MarcSerraPeralta/lomatching), especially `decoder.py`, `util.py`, and README tests.
- [surface-sim](https://github.com/MarcSerraPeralta/surface-sim), especially `experiments/arbitrary_experiment.py`, detector handling, and rotated-code iterators.
- [BP-LSD API](https://software.roffe.eu/ldpc/ldpc/bplsd_decoder.html). Check the installed version; documentation and code can differ.
- [Serra-Peralta, Shaw, and Terhal, Decoding across transversal Clifford gates in the surface code](https://arxiv.org/abs/2505.13599).
- [Cain et al., Fast correlated decoding of transversal logical algorithms](https://arxiv.org/abs/2505.13587).
- [Algorithmic Fault Tolerance for Fast Quantum Computing](https://arxiv.org/abs/2406.17653), subsequently published under the low-overhead transversal fault-tolerance title.
- [Murphy, Sahu, and Vasmer, Simplified circuit-level decoding using Knill error correction](https://arxiv.org/abs/2603.05320).

At completion, report: implemented modules/commands, dependency changes and revisions, the exact four protocol definitions, decoder support/fallbacks, verification evidence, smoke-run location and measured results, known limitations, and production run/replay commands. State explicitly that terminal full-history memory decoding does not by itself establish an online bounded-latency QEC architecture.
