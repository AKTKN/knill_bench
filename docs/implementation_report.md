# Implementation report — 2026-09-21

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
