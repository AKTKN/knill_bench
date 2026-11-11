# Converter SE-memory Phase 1 report

Implemented on feature/converter-simulations after Phase 0 commit 3cc1974.
The converter/stimflow pins, Conda knill_system numerical versions and all
dependency source checkouts remain unchanged. No other feature branch or
Hex physical/decoder implementation is modified.

## Result

The registered converter_se_memory runner now executes/resumes fixed and
adaptive d/p points with multiple workers. The consumer authors one-round
native INIT_Z, R-1 further SE rounds when needed, and native noisy destructive
Z readout. Default initialization is noisy; the existing explicit ideal INIT
policy is supported without idealizing later operations. No physical circuit
or stabilizer geometry is implemented in bench.

The decoder uses public semantic Z-sector views and the exact undecomposed
sector DEM. It explicitly rejects unsupported graph/correlated/logical-label
structures, and builds PyMatching with correlations disabled. The physical
circuit retains both check sectors. Actual flips and predictions derive from
the same raw measurement batch; only events enter inference.

One static circuit/view/DEM/graph/frame model is cached per point/process.
Parent owns sidecars/Parquet; workers return compact numeric ChunkResult.
Fixed chunk seeds/partitions replay across serial/spawn, while auto retains
timing-dependent partitions. Whole-point restart and completed-byte preservation
are shared with Phase 0. Exact round-trip Stim text and native exported
instructions retain the sampled circuit; parent verifies point/execution/
artifact/source linkage. The other two converter scientific kinds stay guarded.

## Correctness evidence

Phase 0's 161 tests passed before implementation. The focused Phase 1/Phase 0/
unchanged Hex-memory gate passed 257 tests with 156 existing-category warnings
in 31.64 s. New scientific tests include:

- p=0 X/Z variants at d3/5, noisy/ideal INIT policies, retained random gauges,
  and exact R=1/2/3 extraction counts.
- Direct full-circuit Stim m2d, semantic record maps, selected-circuit m2d and
  independently built MWPM agreement on the same raw batches.
- Every single physical X at d3/5, including boundary wires, using the public
  preparation cut/wire map and an otherwise perfect syndrome circuit.
- All 512 d3 pure-X patterns, enumerated algebraically using CSS H_Z/L_Z,
  compared with exact minimum-pattern-weight classes, projected pure-X Stim
  DEM matching and independent CSS matching. Explicit iid X q=.1 differs
  from the experiment's depolarizing p. This validates minimum-weight class
  inference and does not claim exact logical-coset MAP.
- Parent publication, exact saved circuit/export reconstruction, bounded row
  groups, IDs/counts, fixed serial/spawn replay, native caching, failed-chunk
  restart and metadata rejection before cleanup.

The initial scientific gate exposed test-only assumptions about selected-view
annotation ordering and Stim repeat-block string representation. The reference
fixture now projects a faulted native DEM through public maps; the artifact
serializer uses a proper public circuit representation and verifies full
round-trip equality. No dependency patch or quantum schedule change was needed.

The full regression gate passes **781 tests**, with **1356 inherited-category
warnings**, in **148.48 s**. Installed fixed/auto two-worker CLI runs and
completed resumes pass at three shots per d3/5 point. A six-wheel bundle also
executes a prepared run and completed resume with Git unavailable, using a
three-shot d3/two-worker fixture. Current Conda packages supply numerical
dependencies in that wheel smoke; no new offline Python environment is created.
Full commands and installed CLI/wheel results are recorded in
[TEST.md](../TEST.md). New physical batches are d3/5 and <=7 shots. The 512
patterns are classical enumeration, and the supplied 100000-shot d3/5/7 grid
is parse-only. No production sweep, LER agreement, threshold or performance
claim follows from these fixtures. See [the runnable guide](converter_se_memory.md).
