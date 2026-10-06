# Validation record

## High-throughput refactor validation (2026-09-26)

The refactor was checked against the original public commit `265062f` with `scripts/verify_refactor.py` (8 fixed-seed raw shots per case). Sampling case IDs, circuit hashes, DEM hashes, detector bits, logical truth, decoder prediction bits, valid flags, residuals, logical error counts, and fallback identity matched exactly for `se_memory` d=5/N=2, native Hex d=5/N=2 and d=7/N=3, AFT post-gate d=5/N=2 and d=7/N=3, and AFT preparation-only d=5/N=2. Larger fixed-record profiles also matched for native Hex d=7/N=7 and AFT post-gate d=7/N=21 at 16 shots. The existing native same-raw-sample regression against Hex remains in the suite. Preparation constructs no live decoder backend; workers load saved matching graphs, and resume rejects a changed graph hash.

`scripts/verify_run_identity.py` also ran one worker through interruption and resume in both the baseline and refactored checkouts. Across SE, Native Hex, and AFT post-gate d=5/N=2, its six committed chunks matched exactly on checkpoint IDs/seeds/status, decoder counts, per-shot predictions/validity/residuals, and six retained sample identities, reasons, detector bits, logical truth, and Native Hex raw bits. AFT/SE raw retained records are intentionally null in the refactored detector-only path; their detector and observable bits match. This checks the retention and transaction policy beyond fixed-record decoder inference.

For tested SE and AFT circuits, Stim `compile_detector_sampler` with the same seed and shot count produced detector and observable arrays identical to `compile_sampler` plus `compile_m2d_converter`. Tests now cover SE d=5/N=2, AFT post-gate d=5/N=2 and d=7/N=3, and AFT preparation-only d=5/N=2. This is an observed property of the pinned Stim 1.16.0 environment, not a cross-version RNG guarantee. The one/two-worker resume test compares exact shot rows and chunk seeds. Aggregate-only tests compare full-shot and aggregate-only runs on the same fixed physical chunks, including exact sample hashes, decoder counts, paired counts, and retained samples. Other tests verify bounded retained samples, interrupted resume, empty shot parts, successful analysis, and bounded parent filtering with `save_all_syndromes=true`.

The benchmark scripts are `scripts/benchmark_refactor.py`, `scripts/compare_performance.py`, `scripts/verify_refactor.py`, `scripts/verify_run_identity.py`, and `scripts/stress_memory.py`. RSS uses Linux `/proc/self/status` for current process, a 20 ms `/proc` poll for concurrent parent-plus-child RSS, and `resource.getrusage(...).ru_maxrss` for peak process RSS. No `psutil` dependency was added. Setup and throughput numbers are single-run measurements; model construction, sampling, raw conversion, decoder time, staged bytes, and IPC bytes are separated. `chunk_size` remains user-controlled.

To reproduce the baseline comparisons from the repository root with the installed environment: `git worktree add --detach /tmp/knill-baseline-validation 265062f`, then `.venv/bin/python scripts/verify_refactor.py /tmp/knill-baseline-validation`, `.venv/bin/python scripts/verify_run_identity.py /tmp/knill-baseline-validation`, and `.venv/bin/python scripts/compare_performance.py /tmp/knill-baseline-validation`. Run `.venv/bin/python scripts/stress_memory.py` for the bounded interrupted/resumed memory case. Remove the temporary worktree with `git worktree remove /tmp/knill-baseline-validation` afterward. `benchmark_refactor.py --mode sampling` compares raw-plus-converter and direct-detector samplers on a chosen case without constructing decoders.

The updated d=7/N=7 two-worker stress run used 12 shots per protocol, chunk size four, Native Hex and AFT post-gate, aggregate-only storage, nonzero uniform/failure retention, and interruption after one committed chunk followed by resume. Six checkpoint IDs were unique and complete; staging was empty afterward and analysis produced three summary rows. The largest worker IPC payload was 2,596 bytes and staged chunk 35,901 bytes. Sampled simultaneous RSS peaked at 1,195,016,192 bytes for parent plus child processes, with parent 409,346,048 and highest worker 396,746,752 bytes. Parent current RSS rose from 380,850,176 after preparation to 389,955,584 after resume. Two worker PIDs processed both protocols; their current RSS was 347–349 MB on Native Hex and 395–397 MB on AFT. This tests cache turnover and bounded growth over six chunks, not long-run allocator behavior. Eight workers were not run on this host. Native chunks used 16,380 raw bytes, while AFT chunks used zero. Checkpoints record model construction RSS deltas, Python-visible sparse buffer bytes, sampled active-chunk RSS increase, staging time, and parent commit time; see the schema note for what those counters omit.

After the final instrumentation changes, `.venv/bin/python -m pytest -q --disable-warnings -x` passed 64 tests in 99.83 seconds. The six-case fixed-record baseline comparison and the interrupted/resumed run-identity comparison also passed. The first full-suite attempt during development was interrupted by its resume compatibility check because source files were edited while it was running; the final run used a stable tree.

For the native record-copy audit, a d=7/N=7, 16-shot circuit had 4,095 Boolean measurements (65,520 bytes). The current full-copy-and-convert path had a 1.414 ms median over 100 repetitions. An equivalent packed local-delta path applied the same correction to the input, converted it, and restored the input in `finally`; its packed deltas used 8,288 bytes, but its median was 1.482 ms. The two paths produced identical residual arrays and restored input bits. This isolated microbenchmark supports retaining the faster, non-mutating full copy at this chunk size; it does not establish the best choice for every chunk size. Native d=7/N=7 fixed-record predictions, valid flags, and residual hashes were unchanged after template sharing. Tests verify repeated-cycle matrix identity, bounded transitions, fixed BP-LSD q=0/1 offsets, and native callback owner release.

In single d=7/N=7, 16-shot profiles immediately before and after sharing one local state-preparation template per basis, Native Hex decoder construction changed from 4.280 to 4.181 seconds and model RSS increase from 14,888,960 to 12,210,176 bytes; process peak RSS changed from 312,131,584 to 310,353,920 bytes. These are single-run observations, not stable performance estimates. Raw, detector, observable, prediction, validity, and residual SHA-256 fingerprints matched exactly. The full suite passed 61 tests after the template and owner-reference changes; focused checks cover the subsequent cache-key cleanup and cache-resize behavior.

Validated on 2026-09-21 with Python 3.12.7 and the exact dependency revisions/versions in `dependencies.md` and `requirements.lock`. This record reports executed checks; it makes no fault-tolerance or threshold claim.

## A — dependency/reference checks

* `bash scripts/bootstrap.sh` passed. All three research imports resolve inside `external/`, on clean `knill-bench-integration` branches.
* `.venv/bin/python -m knill_bench.cli validate-references` passed. Native Hex d=3, Z, one teleportation, one preparation round, p=0.001, seed=321 produced **1 logical error / 256 shots**. Legacy native batch overshoot is avoided by using exactly 256 shots for this reference.
* The documented surface-sim/LOM unrotated d=3 two-block example decoded **0/32** physical samples, with 36 detectors. Its single logical `TICK` generated exactly **one SE round per block** (12 check measurements each), while the physical circuit contains 20 `TICK`s. This establishes the logical/physical TICK distinction; it is not the rotated comparison arm.
* BP-LSD satisfied all four syndromes of H=[[1,1,0],[0,1,1]], using installed public convergence and iteration properties. API version is ldpc 2.4.1; no native batch decode is claimed.

## B/C — circuits, models, native regression

`.venv/bin/python -m pytest -q` passed **49 tests** (40.93 seconds in the final recorded run). The 252 warnings are dependency SciPy `mmread` future-default warnings, not failed checks. Checks include:

* All 32 combinations of four protocols × d=3/5 × X/Z × N=1/2: strict DEM extraction, exact SE counts, ledger completeness, signed Stim detector/observable flows, and zero-noise detector/observable parity.
* Expected random Bell outcomes remain random; no gauge allowance, postselection, extra terminal SE, or sampled-error boundary selection is used.
* Actual surface-specific X/Z hook interaction ordering and legacy noise operation classes.
* Explicit scheduled noise, noisy initial boundaries, equal-time residuals, and bounded cross-replicate sample retention.
* DEM repeat/shift expansion, separators, repeated-target cancellation, duplicate supports with different logical labels, XOR probability merging, detector-free logical terms, fixed priors and no-fault models. Trusted Stim DEM sampling verifies the binary event effects.
* Same-circuit PyMatching agreement and local/global LOM detector mapping.
* Native Hex d=5, N=2, X and Z: exact error-count regression against the original pipeline on identical 256-shot raw records. All 21 internal matching calls per two-cycle native decode are instrumented (eight preparation calls plus two Bell calls per cycle, and one final call).
* Controlled nonmatchability triggers only the configured case-level fallback, with one effective decoder instance; a nondeterministic circuit still raises.
* Physical Pauli insertion agrees with original-circuit measurement-to-detector conversion; native noisy-boundary zero-noise replay returns no failures.

The post-gate detector basis was changed from forward output comparisons to the paper-compatible pre-gate row frame by an invertible CNOT row transform. No quantum gate, noise location, preparation length, or readout was altered by that change. Counterexamples from preliminary forward-frame diagnostics remain in the earlier development output. The final frame still has approximate-decoder single-fault failures; they are not suppressed or relabeled as computational success.

## D — processes, persistence, timing and storage

The test suite ran fixed tasks with one and two spawned workers and compared physical sample hashes, exact predictions and all counts; they agree. An intentionally interrupted run resumed without duplicate/missing committed chunks, and a second resume added no work. Config/grid changes were rejected. Time-budget and target-error stopping were exercised.

A controlled worker exception generated an explicit failed status, zero confirmed physical shots, preserved assigned-shot counts/seed, and computational-failure rows. Retrying with the real process pool replaced the failed transaction with the same task identity, without double counting. Every generated test Parquet table was read back against its explicit Arrow schema.

Decoder timing separates batched work from actual individual calls. Sampling, m2d conversion, warm-up, model construction, file writing, and diagnostic replay are outside primary decoder-call timers. Nested native backend events are retained separately from inclusive callback totals. Uniform and failure retention are bounded; bit lengths and little-endian packing were checked. Outside-repository execution of the installed CLI passed.

## E — end-to-end runs

Authoritative final smoke output:

`results/20260921T101344.588286Z_ce674202f6/`

Executed through the required shell → thin Python launcher → installed package path. It contains 32 physical cases, 64 committed chunks, **2,048 physical shots**, 56 decoder cases, and **3,584 decoder-shot results**. All four protocols and global BP-LSD were exercised. All selected LOM subgraphs constructed without fallback in this small grid; fallback was separately validated by the controlled test. There were zero computational failures.

The isolated replay command uses one worker and retained uniform samples. Analysis generates normalized Parquet summaries plus LER, timing, native-cost, BP/LSD/cluster, model-cost, and resource figures. The final implementation report gives locations, exact measured counts and fault-audit evidence. No production benchmark was launched.

The additional `configs/explicit_smoke.yaml` runs all four protocols with noisy initial preparation, serial waiting/idle noise, and a requested elapsed-time budget of 400 gate units. SE fits three cycles at 377 units; the legacy and preparation-only arms fit one cycle at 361 units; the post-gate arm requires 733 units for even one cycle. The residuals −23, −39 and +333 are explicitly recorded. Those points must not be described as exactly time matched.

## Limits of the evidence

Single-fault auditing enumerates all relevant d=3 physical-Pauli **detector/logical equivalence classes**, counts all represented physical locations, and injects one raw-record representative per class. It does not exhaust every intrinsic random measurement frame of the native pipeline. d=5 diagnostics are restricted to 12 single-fault classes and 12 sampled two-fault witnesses per case in the recorded audit. No decomposed matching graph distance is presented as a circuit-distance proof.

Both matching projection/decomposition and BP-LSD are approximate. LOM uses a documented complete selected-sector observing-region superset rather than claiming the paper's minimal automatic region on this custom geometry. Native Hex's legacy prior is retained even in the explicit-noise example and is labeled accordingly. Timing from the two-worker smoke is concurrent-load timing; isolated replay has its own observations and strata. There is no streaming/windowed decoder or realtime feedforward implementation.

Final data verification read all authoritative-run Parquet datasets, including 14,168 physical-fault audit rows and the supplemental CPU/diagnostic/native/model summary tables; schemas and checkpoint row counts matched. The authoritative source and environment compatibility checks passed with the recorded native thread limits. The fault audit was reused from the immediately preceding run only after checking byte-identical circuit/DEM and scientific-source artifacts; its explicit evidence-reuse record is `logs/fault_audit_reuse.json`. See the implementation report for exact counterexample counts.
