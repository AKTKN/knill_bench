# Implementation report — 2026-09-21

## High-throughput refactor (2026-09-26)

Changed code: decoder descriptors/backends, Native Hex cache/template sharing, circuit timing, worker/runner transport, storage schemas, aggregate analysis, replay, config validation, and tests. New reproducible scripts are `scripts/benchmark_refactor.py`, `scripts/verify_refactor.py`, and `scripts/stress_memory.py`. `prepare()` now performs structural fallback resolution without constructing live decoders. Strict decomposed matching graphs are saved as hashed artifacts and loaded by workers without repeating subgraph extraction. Workers stage one chunk at a time in Parquet and send small manifests; checkpoint JSON remains the final commit marker. AFT/SE use direct detector sampling, and aggregate-only runs keep paired decoder counters. Model caches default to one per worker and Hex transitions are bounded to 16 entries. Repeated Native Hex preparation modules share immutable local matrices and decoder handles. A weak callback reference lets an evicted native decoder be released. Global BP-LSD avoids retaining the full fault model or copying its CSC matrices when all columns are active, and matching no longer stores a text copy of the selected DEM. The full corrected Native Hex measurement record remains a memory hotspot because its residual check consumes a complete corrected record.

Single-run measurements on the same machine and Python environment, comparing commit `265062f` with this refactor (lower is better for setup/RSS):

| Case | `prepare()` before → after | Prepare peak RSS before → after | Fixed-record decoder time before → after, 16 shots |
|---|---:|---:|---:|
| Native Hex d=7, z, N=7 | 16.15 → 8.54 s | 403.6 → 386.5 MB | 321.9 → 291.2 ms |
| AFT post-gate d=7, z, N=21 | 29.72 → 26.03 s | 507.3 → 452.0 MB | LOM 23.5 → 23.0 ms; BP-LSD 23.12 → 23.08 s |

These decoder timings use identical raw records to isolate inference; the production AFT path now avoids raw measurement allocation. They are single runs with normal timing variation, so the small decoder-time differences are not evidence of a reliable throughput change. The larger setup reductions reflect removal of duplicate live decoder construction. Fixed raw records, detectors, logical truth, predictions, validity, residuals, error counts, and fallback identities matched the original commit on six representative cases (see `validation.md`). The fixed-record profiles separated build, model construction, sampling, raw conversion, and terminal decoder work. Native Hex build was 4.94 → 5.01 s and worker-style decoder construction 8.05 → 8.07 s; AFT build was 16.92 → 16.86 s and decoder construction 7.03 → 6.71 s. Native model RSS increase was 14.9 → 13.4 MB, with profile peak RSS 312.6 → 310.9 MB. AFT model RSS increase was 67.5 → 61.9 MB, with profile peak RSS 404.8 → 395.2 MB. The profile's raw-sampling and conversion paths are held constant for exact scientific comparison; direct detector sampling is measured separately for production.

At 16 shots, Native Hex physical raw sampling was 95.17 → 95.35 ms, raw-to-detector conversion 93.21 → 91.05 ms, and nested frame-propagation work 100.43 → 88.53 ms. The AFT fixed-record comparison measured raw sampling at 1.885 → 1.862 s and conversion at 1.866 → 1.929 s. A separate current-code sampling check on the same d=7/N=21 AFT circuit and seed measured direct detector sampling at 8.28 ms; it produced exactly the same detector and observable bits as raw sampling plus conversion, while omitting the 162,736-byte raw array. The time comparisons are single runs and include API compilation overhead. Native frame time is nested inside terminal decode time.

The d=7/N=7 two-worker interrupted/resumed aggregate-only stress run completed six unique chunks (12 shots per case, chunk size four) and produced an analyzable report. A 20 ms Linux `/proc` poll measured a 1,195.0 MB concurrent parent-plus-child RSS peak, 409.3 MB parent peak, and 396.7 MB highest child RSS; `resource` measured a 407.9 MB parent process peak and 395.9 MB worker peak. The largest worker IPC payload was 2,596 bytes, largest staged Parquet chunk 35,901 bytes, longest staging write 575 ms, and longest parent commit 44 ms. Workers sampled zero raw bytes for AFT and 16,380 raw bytes for Native Hex per four-shot chunk. The largest observed active-chunk RSS increase was 43.8 MB; first-model RSS increases were 41.9–47.2 MB. Python-visible sparse matrix buffers occupied about 0.12 MB for Native Hex and 1.19 MB for AFT, excluding opaque backend allocations. Parent current RSS was 380.9 MB after preparation and 390.0 MB after resume/commit; both continuing workers processed both protocols, with current RSS around 347–349 MB on Native Hex and 395–397 MB on the larger AFT model. These measurements show bounded behavior in this six-chunk run, not a proven bound for arbitrary sweeps.

A separate four-chunk two-worker run recorded first-worker decoder construction at 7.85 and 8.95 s for Native Hex d=7/N=7 and 1.44 s for AFT post-gate d=7/N=7. These timings exclude artifact preparation, physical sampling, decoding, staging, and parent commit. The parent commit timer covers validation and file promotion; checkpoint and manifest JSON writes follow it. The sampled concurrent RSS poll can miss sub-20 ms peaks, so per-process `resource` peaks are reported alongside it.

Eight workers were not run because the host had about 2.2 GiB available before the test; eight times the observed worker RSS plus parent RSS would exceed that. For an eight-worker host with adequate RAM, start with `workers: 8`, `model_cache_size: 1`, `max_pending_chunks_per_worker: 1`, `native_threads_per_worker: 1`, `save_shot_results: false`, `save_all_syndromes: false`, and small retained-sample limits. Choose `chunk_size` explicitly after measuring target cases on the host; chunk arrays scale approximately linearly with it. The d=7/N=7 Native Hex raw, detector, and corrected-record arrays alone need about 23.7 MB at chunk size 2,048 or 47.4 MB at 4,096, before decoder scratch and Arrow buffers. This is an advisory calculation, not an automatic setting or an eight-worker capacity result.

`knill_bench` is installed and executable. All four required quantum circuits run with their specified decoder pipelines. The production benchmark configuration was validated but **not run**.

## Delivered package and commands

The `src/knill_bench` package contains strict configuration/grid resolution, authoritative Hex geometry, shared circuit/noise/schedule builders, a measurement ledger and signed CSS-flow detectors, native Hex/LOM/PyMatching/global BP-LSD adapters, lossless sparse DEM conversion, process workers, deterministic seeds, atomic checkpoints/Parquet tables, retained-sample timing replay, physical-fault auditing, and analysis.

Implemented commands: `validate-config`, `build`, `run`, `resume`, `benchmark-latency`, `analyze`, `validate-references`, and `audit-faults`. Bootstrap and launch scripts are executable thin wrappers. The installed CLI was tested outside the repository.

| Protocol | Ancilla SE | Additional SE | Decoder |
|---|---|---|---|
| `se_memory` | None | One ordinary full X/Z round per cycle | Full-history MWPM or global BP-LSD |
| `knill_hex_dminus2` | Exactly d−2 on each fresh A/B | None | Existing Hex preparation repair → Bell code-capacity decoding → propagated frame → final-readout decoding |
| `knill_aft_postgate` | Exactly one on each fresh A/B | One full X/Z round on **all live D/A/B blocks after each of two CNOTs** | LOM or global BP-LSD |
| `knill_aft_prep_only` | Exactly one on each fresh A/B | None | LOM or global BP-LSD |

Knill orientation is CX(B,A), CX(D,A), MX(D), MZ(A), with B becoming the next D. X/Z memories are separate. There is no postselection or adaptive preparation. Native Hex uses its original callbacks, maps and prior policy. AFT uses raw history without independent preparation-sign repair. LOM uses an explicitly recorded selected-sector observing-region superset and pre-gate detector comparisons. It does not enable edge-correlation reweighting. Unsupported graph decomposition can select one explicitly named global BP-LSD fallback for the entire case; aliases share inference and timings. Nondeterministic circuits cannot fall back.

## Dependencies

Clean, separate `knill-bench-integration` worktrees are based on:

* Modified Hex `hex-adaptive`: `5de58f2f80791054411ad3c0885a4fe3671ed56a`.
* lomatching: `b55a7a65969a106a547622287b620f0da2cb5e39`.
* surface-sim: `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad`.

The requested [AKTKN/lomatching](https://github.com/AKTKN/lomatching) and [AKTKN/surface-sim](https://github.com/AKTKN/surface-sim) forks were created and verified. Original remotes and the unrelated `hex-parallel` worktree were preserved. No dependency source patch was needed, and integration branches were not pushed. Editable imported paths, complete versions, licenses, exact Git revisions and source snapshots are recorded. See [dependencies](dependencies.md).

## Verification and measured smoke output

**49 tests passed**, including all 32 d=3/5, X/Z, N=1/2 circuit combinations; signed detector/observable flows; zero-noise checks; exact preparation/post-gate counts; hook/noise checks; native same-record regression; DEM edge cases; LOM mapping and controlled fallback; one-/two-worker identity; interruption/resume; worker failure/retry; bounded retention; time/error stopping; explicit noisy boundaries; and outside-repository imports. See the [validation record](validation.md).

Authoritative smoke run:

[`results/20260921T101344.588286Z_ce674202f6`](../results/20260921T101344.588286Z_ce674202f6/)

It has 32 physical cases, 64 chunks, **2,048 physical shots**, 56 decoder cases, and **3,584 decoder-shot results**. Each individual physical point has 64 shots at p=0.001. All selected LOM subgraphs constructed successfully. There were **zero computational failures**.

The following are validation totals pooled across d, basis and cycle count; they are not estimates for a single homogeneous experiment. The per-point LERs, denominators and Wilson intervals are in [report.md](../results/20260921T101344.588286Z_ce674202f6/report.md) and `summary.parquet`.

| Pipeline | Logical errors / decoder shots |
|---|---:|
| SE + MWPM | 1 / 512 |
| SE + global BP-LSD | 1 / 512 |
| Native Hex | 0 / 512 |
| AFT post-gate + LOM | 2 / 512 |
| AFT post-gate + global BP-LSD | 1 / 512 |
| AFT preparation-only + LOM | 0 / 512 |
| AFT preparation-only + global BP-LSD | 0 / 512 |

There are 224 actual sampled terminal single-shot timings and 224 additional isolated one-worker replay timings. Wall and CPU quantiles, production/replay and concurrent/isolated strata are separate in `data/latency_statistics.parquet`. The 1,904 raw call records also include real batch calls, nested native backend/module/frame calls and separate diagnostic replays. No amortized batch time is called single-shot latency. The latency figure legend tuples mean `(backend, replay, concurrent_load)`.

All final Parquet datasets were read back with exact Arrow schemas. Checkpoint row counts match their parts, and current package/dependency/thread compatibility matches the authoritative run. Source archives, circuit/DEM hashes and packed-record lengths were checked. There are 131 bounded retained samples, 24 paired decoder comparisons, and 14,168 fault-audit rows. Analysis emits LER, throughput/latency, native-cost, BP/LSD/cluster, model/subgraph/hyperedge-cost, and resource plots/tables.

## Fault-audit findings

The audit enumerated **7,208 relevant single-Pauli detector/logical equivalence classes at d=3**, representing **31,380 physical locations**, with one injected raw-record witness per class. Across d=3/5 it checked 7,400 single-fault witnesses, plus 192 bounded d=5 two-fault witnesses. It found no detector-free logical single-fault term or pair of single-fault classes with identical complete detector support but different logical labels in these circuits.

Approximate decoders nevertheless failed on some d=3 witnesses:

| Decoder/pipeline | Failing class witnesses / tested classes |
|---|---:|
| Native Hex | 9 / 920 |
| SE MWPM | 0 / 512 |
| SE global BP-LSD | 14 / 512 |
| AFT post-gate LOM | 186 / 4,856 |
| AFT post-gate global BP-LSD | 273 / 4,856 |
| AFT preparation-only LOM | 0 / 920 |
| AFT preparation-only global BP-LSD | 31 / 920 |

These are diagnostic counts, not Monte Carlo error probabilities. No decoder-call failures were recorded in those counts; the failures were wrong logical predictions. BP-LSD checks its full detector equation. Native residuals check its legacy preparation detectors, while matching adapters return logical predictions without claiming a full-fault residual. Witnesses, Pauli locations, predicted/actual bits and ambiguity flags are saved in `data/fault_audit/`. Their existence is not hidden by modifying the quantum protocol, postselecting, discarding hyperedges, or changing decoder after observing a shot.

The independent fault audit was executed in `results/20260921T100730.998531Z_ec66930ca2`. Its evidence was reused in the authoritative run **after verifying byte-identical circuit/DEM files and all scientific configuration, builder, adapter, and audit source files**. Only subsequent analysis tables/schema additions differed. `logs/fault_audit_reuse.json` records this explicit compatibility decision, source run and verified source hashes. The authoritative run's physical sampling and isolated timing were performed afresh under its own recorded source snapshot.

## Explicit-time example and limitations

The additional all-four-protocol example is [configs/explicit_smoke.yaml](../configs/explicit_smoke.yaml), with output in [`results/20260921T100946.147337Z_4ebc22603d`](../results/20260921T100946.147337Z_4ebc22603d/). It ran 128 physical shots and 224 decoder-shot evaluations, with noisy initial preparation and explicit serial waiting/idle noise. For a requested 400-unit exposure, actual whole-cycle exposures are 377 (SE, three cycles), 361 (native/preparation-only, one cycle), and 733 (post-gate, one cycle). The signed residual mismatch is recorded. The last point cannot fit even one cycle within the requested budget and is not presented as exactly time matched.

The legacy profile has no declared duration, idle noise or one-qubit-gate noise; its elapsed time and spacetime are null. The explicit schedule is deliberately conservative and serial for two-qubit pairs. No overlapping/free factory is assumed. Native decoding retains the legacy p-based prior even in the explicit-noise experiment, labeled in metadata; it has not been retuned to the new rates. LOM's complete-sector projection is not claimed to equal a minimal paper observing region, and graph decomposition is not correlation reweighting. BP-LSD parameters are starting values, not optimal settings. Sequential-stopping intervals are explicitly descriptive.

The audit does not exhaust every native intrinsic random record frame or establish all-distance circuit/gadget fault tolerance. No threshold or asymptotic exponent follows from these small samples. **Terminal full-history memory decoding does not by itself establish an online bounded-latency QEC architecture.**

## Larger runs and replay

```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
python -m knill_bench.cli validate-config configs/benchmark.yaml
python -m knill_bench.cli build configs/benchmark.yaml
# Start this deliberately; it was not run during implementation:
bash scripts/run_simulation.sh configs/benchmark.yaml
python -m knill_bench.cli resume results/<run-directory> --workers 8
python -m knill_bench.cli benchmark-latency results/<run-directory> --workers 1
python -m knill_bench.cli analyze results/<run-directory>
python -m knill_bench.cli audit-faults results/<run-directory> --budget 12
```

Changing scientific code, dependencies, configuration/grid or stored models requires a new run; changing only worker count is permitted. Existing completed chunks retain their task identities and seeds. The original YAML, resolved grid, batch partition and source/environment snapshots accompany every run.
