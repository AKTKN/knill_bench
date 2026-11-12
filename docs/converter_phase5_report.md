# Phase 5 integration and numerical validation report

Branch: feature/converter-simulations, continuing from Phase 4
68bb77de86863ae27c7695c9b718fcf2c83d4edd. The final Phase 5 commit SHA is
reported in the delivery message; Git identifies the revision containing this
report. Runtime is Conda knill_system/Python 3.12.15, Stim 1.16.0,
PyMatching 2.4.0, converter 457dc519adec6a11b38843a03e1c8fbbd6495f5a and
stimflow ffe0d043598ed5df0851a3e6b4920359a23fafbd. No dependency sources,
physical builders, scientific decoder policies, numerical pins or user configs
are changed.

## Implemented interfaces

The existing three SimulationModel implementations and v2 runners remain the
physical/scientific interfaces: ConverterSEMemory, ConverterKnillMemory and
ConverterDeepClifford expose circuit, lstim_source, decoder, frame_plan,
metadata and decode_batch(raw)->DecodedBatch. All circuit generation, native
views/stages/sectors/frames and deep terminal lifting remain public converter
operations. Cached static objects are reused per point/process; samplers are
fresh and independently chunk-seeded.

New converter.runtime provides SamplingLedger, bounded iter_sampling_chunks,
native circuit_counts, Wilson binomial_result and validate_runtime. Shared
adaptive_execution records split worker timings and parent compile/write times,
publishes ordered chunk/seed records, and checksums labels. RunStore registers
runtime artifacts and validates their contract before completion or incomplete
cleanup. New analysis.converter.summarize_saved serves all three experiments;
the prior deep summary format delegates to it without changing its public keys.
CLI adds summarize-converter. The opt-in scripts/validate_converter_matrix.py
creates small, reproducible validated datasets outside the unit suite.

The new converter_execution_v2 marker requires a complete sampling ledger,
label checksum, exact rate/Wilson interval and consistent timing/partition
metadata. Older converter metadata retains its own original contract; Hex
receives no new converter files or fields. Portable POSIX source-name ordering
preserves the existing Linux Hex source/matrix SHA256
(e16c17466d43d42369c8e53b2f45e5500e5dc5874c0d64484759f52b363e8f9e).
Windows lock liveness uses a non-destructive handle query instead of a kill
signal, and staged Parquet validation readers close before public renames.

## Configuration, commands and scientific meaning

Only d/p sweep. SE rounds support fixed integers/d/multiples, counting INIT's
included first round. Knill supports T_tel>=1, both noisy_d_rounds and
ideal_post_se_depolarizing, with d resource rounds and noisy final Z. Deep
supports four logical qubits by default, depth/circuit_seed/n_r, noisy or typed
ideal/M9 resources, ideal input/final SE/probes and the unchanged seeded gate
schedule. Existing small examples/templates and all 22 config/point/seed
snapshots are unchanged.

```bash
conda activate knill_system
knill-bench-v2 run configs/converter_se_memory_v2_example.yaml
knill-bench-v2 run configs/converter_knill_memory_v2_example.yaml
knill-bench-v2 run configs/converter_deep_clifford_v2_example.yaml
knill-bench-v2 resume results/<run>
knill-bench-v2 summarize-converter results/<run>
```

SE uses semantic Z-sector undecomposed graphlike DEM MWPM. Knill/deep use
local independent temporal-component/CSS/readout capacity MWPM with native
causal frame/sector propagation. Correlations are disabled, parallel alternatives
retained, detector-free hypotheses explicit, and unsupported hyperedges raise.
No joint cross-block graph is introduced. Terminal probe/fault truth never
selects corrections. Deep failure means any corrected signed output generator
flips for the whole intended stabilizer-state circuit; memory labels retain
their original logical-Z meanings. E/N and pointwise 95% Wilson score intervals
are checked against saved labels. Small counts do not validate paper curves,
thresholds or per-round/per-layer rates.

## Output and execution guarantees

The [integration guide](converter_phase5.md) gives the full output schema,
representative rate/CI metadata, exact CLI/cluster commands and replay API.
Each point has LSTIM, exact sampled Stim, bool error Parquet, one native model
metadata sidecar, an actual partition/seed/timing Parquet ledger and signed
logical definitions for deep circuits. Deep Stim includes terminal MPPs.
Root metadata records real source/version identities, resolved conditions,
counts/rates/intervals, native circuit counts, policies, hashes and timing sums;
no instruction export is duplicated there.

Only the parent writes/publishes. Pending/reordered results remain bounded by
workers; shot arrays/buffers are bounded and the ledger buffers <=512 rows.
Native static model growth is outside the heuristic raw-array budget. All files
close/fsync/validate before promotion; the complete marker commits their group.
Incomplete points restart from zero with original seeds. Completed points are
verified but never resampled or overwritten. Fixed partition replay is exact
under serial/spawn; time-adaptive partitions can differ across runs/workers.
Recorded auto partitions replay exactly in the dedicated test.

## Executed checks and disclosed failures

- Unfiltered read-only Hex suite: **374 passed, 1 failed, 720 warnings, 40.95 s**.
  The failure is test_real_cluster_llr_threshold_produces_mixed_short_long_batch
  in test_phase5_confidence_adaptive.py, historically documented before converter
  integration. Its eight fixed-seed samples all select the long path. Running
  that test alone on the unchanged dependency reproduces the failure in .57 s.
  It is not hidden by deselection, a tolerance change or a dependency edit.
- Runtime/storage/synthetic-contract gate: **68 passed, 4.96 s**. Dedicated
  contract/config/generation gate including Windows handle mocks: **152 passed,
  9.67 s**. Real subprocess CLI gate: **15 passed, 65.49 s**. Fixed/auto execution,
  original Hex adaptive behavior and completed resume gate: **80 passed,
  28 inherited warnings, 171.71 s**.
- The first focused invocation named nonexistent test_storage_v2.py and collected
  no tests. The corrected invocation found old artifact-count assertions and
  synthetic manually published points lacking the new scientific runtime marker:
  18 failed/76 passed. Existing output tests now expect the required extra ledger;
  storage-only fixtures explicitly mock runtime science validation, while new
  runtime and native CLI tests exercise that validation without mocks.
- Six project/backend wheels built/installed with the pinned converter and
  stimflow, grammar and all 72 Hex matrices. Verified installed imports with
  PATH empty and Git unavailable run/prepare/resume/summarize all three kinds,
  using three shots and two workers. Exact completed bytes are preserved.
- pip check, compileall, whitespace/diff checks and the public converter import
  audit pass. All 22 existing canonical config hashes, physical point IDs and
  point seeds match the pre-phase snapshot. Dependency source checkouts stay
  clean. Linux is the locally executed platform; Linux/Windows CI is configured
  and its actual status must be distinguished from local validation.

The complete bench gate passes **975 tests**, with **1356 inherited warnings**,
in **914.45 s**. No tests are excluded and no warning policy changes. This
includes all 35 new runtime/subprocess cases and the existing scientific
fault-injection, independent-reference, storage, spawn and depth32 compilation
checks. The separate full Hex dependency suite retains its one disclosed
historical failure. Exact commands and logs are in [TEST.md](../TEST.md).

## Completed numerical matrix

The regular opt-in matrix completes **52 points / 156 shots in 710.33 s**.
Every point has validated circuit/Parquet/ledger artifacts and completed resume.
All 26 p0 points have zero failures (0/78 shots). Each individual point has
N=3 and a checked Wilson interval; the table below aggregates raw counts only
within each named configuration for compact reporting, not a pooled LER
estimate across distances. SE and Knill rows each include d3 and d5 at both
p0 and p=.003. Deep rows use d3, with seed19 for n_r1 and seed41 for n_r2.


| Configuration | Points | p0 E/N | p=.003 E/N |
| --- | ---: | ---: | ---: |
| se_1 | 4 | 0/6 | 0/6 |
| se_d | 4 | 0/6 | 0/6 |
| se_2d | 4 | 0/6 | 0/6 |
| knill_noisy_d_rounds_1 | 4 | 0/6 | 0/6 |
| knill_noisy_d_rounds_2 | 4 | 0/6 | 0/6 |
| knill_noisy_d_rounds_3 | 4 | 0/6 | 0/6 |
| knill_ideal_post_se_depolarizing_1 | 4 | 0/6 | 0/6 |
| knill_ideal_post_se_depolarizing_2 | 4 | 0/6 | 0/6 |
| knill_ideal_post_se_depolarizing_3 | 4 | 0/6 | 0/6 |
| deep_2_1_noisy | 2 | 0/3 | 2/3 |
| deep_2_1_ideal | 2 | 0/3 | 1/3 |
| deep_2_2_noisy | 2 | 0/3 | 1/3 |
| deep_2_2_ideal | 2 | 0/3 | 3/3 |
| deep_3_1_noisy | 2 | 0/3 | 2/3 |
| deep_3_1_ideal | 2 | 0/3 | 0/3 |
| deep_3_2_noisy | 2 | 0/3 | 3/3 |
| deep_3_2_ideal | 2 | 0/3 | 3/3 |

Each kind includes nontrivial two-worker execution. Per-point rates, intervals,
physical identities, sampling seeds/partitions and exact artifact registrations
remain in ignored results/converter_phase5_matrix/validation.json and the
corresponding datasets; no raw experiment outputs are committed.

The initial depth32 finite-p attempt was killed during static model construction
with an OOM recorded by the host while the other gates ran. It published no
labels or complete scientific marker. An isolated retry is measured separately;
its outcome is recorded below, without counting an attempted run as validated.

The finite-p depth32 retry also failed in isolation: **exit137 / host OOM kill**,
**8:02.20 elapsed**, **7,111,924 KiB peak RSS (~6.78 GiB)**, before sampling.
The VM has 7851 MiB RAM and 2 GiB swap. It has no completed labels or scientific
marker. The planned bounded stop arrived after the host had killed the child.
This large static native stage/view construction is outside the shot-array
heuristic and directly limits finite-p depth32 execution on this workstation.
The pinned APIs retain full source/per-stage snapshots; no private mutation,
trimming, changed physical noise or decoder fallback was used to fit memory.
A separate p0/ideal-resource depth32 smoke is recorded independently.

A separate d3/depth32/n_r1/seed19 **p0, ideal/M9-resource** one-shot run was
bounded and stopped before sampling at **6,835,408 KiB peak RSS (~6.52 GiB)**,
**10:40.78 elapsed**, exit143. It also produced no labels or complete marker;
the host OOM counter remained 2. Both diagnostic runs were safely reopened
without construction and marked failed through RunStore, clearing dead locks
and unfinished files while preserving identities/seeds. Thus **52 points are
numerically validated**; depth32 has compile/signed-group validation only.
Its sampled numerical smoke is an explicit remaining resource limitation,
including at p0 on this VM. No extra decoder approximation or private API
mutation is used to turn an incomplete check into a pass.

Remaining limits directly affecting execution are the large native static
stage/view memory for deep circuits, strict source/version resume compatibility,
timing-dependent auto partitions, the documented local/non-correlated decoder
approximations, and the distinction between verified Linux checks and pending
remote Windows CI. All requested independent references/fault checks in the
bench pass; the existing Hex dependency suite still has its disclosed fixed-
seed adaptive-confidence failure. No published numerical reproduction is claimed.
