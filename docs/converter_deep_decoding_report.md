# Phase 4 implementation and validation report

The feature/converter-simulations branch extends Phase 3 commit edee43a with
noisy deep-circuit execution. The logical generator and converter-authored
physical schedule remain unchanged. Converter 457dc519adec6a11b38843a03e1c8fbbd6495f5a,
stimflow ffe0d043598ed5df0851a3e6b4920359a23fafbd, Stim 1.16.0 and
PyMatching 2.4.0 remain pinned. Dependency checkouts are untouched.

## Implementation

Phase 2's preparation-boundary temporal/CSS MWPM and destructive-readout
capacity adapters now share CausalDecoder. It binds every stage to native
source/module/use/input ordering, validates the current record-error/net-sector
equations, requires causal order and checks applied readout syndromes. The
Phase 2 memory wrapper retains its final corrected Z-parity evaluation.

DeepDecoder splits native probe samples and sends only the canonical prefix
through this shared replay. Prior inferred boundary sectors feed native
readout sector maps, and native OfflineFrameBatch applies/propagates every
correction. Terminal signed-state evaluation calls the public
probe.corrected_flips only after inference finishes. One bool label is the OR
of all N corrected terminal flips, with full-circuit rather than per-round
units. Local graphs retain enable_correlations=False and the documented
component-independent approximation; no joint cross-block graph is built.

ConverterDeepClifford caches static physical/probe/frame/stage/matching models
per point/process. The shared scheduler samples fresh chunk-seeded probe
circuits, streams parent-owned Parquet labels and publishes the four exact
sidecars. Stage digests, source/probe/canonical linkage, policies and streamed
IDs/counts validate before completion/resume. Failed points restart from zero;
completed resume constructs no physical model. The old compile command remains
generation-only, including compatibility with its historical status label.
Generation bundles cannot resume as scientific datasets.

The optional summarize-deep command streams validated saved labels, checks
metadata/error counts and reports the shared pointwise 95% Wilson score bounds.
It never samples, decodes, resumes or imposes current-source compatibility on
saved analysis. The small example now explicitly requests seven shots and
fixed batches instead of relying on the default shot budget. Its execution
config hash changes intentionally; all 22 pre-change configurations retain
physical point identities and point seeds, including all deep instances.
The other 21 canonical config hashes are unchanged.

## Independent checks

New tests sample at most seven shots per batch at d3. Ideal cases cover three
logical seeds, depths 1/2/3 and n_r 1/2, checking every corrected signed output
stabilizer for every sampled Bell branch. Existing Phase 3 signed-group tests
continue to compare U Xq U dagger using an independent four-qubit Stim circuit,
including phases and equivalent generating bases. Its d5 and depth-32 checks
remain compilation-only.

Test-only deterministic Pauli circuits remove stochastic channels and insert
known faults into converter-authored circuits. Logical and single-data-qubit
X/Z faults are placed before/after user CNOTs, before/after teleportation and
on Bell resources. X control-to-target and Z target-to-control propagation is
checked by independent logical Pauli conjugation through the remaining gates.
Physical X/Y/Z faults immediately before terminal measurement are checked by
explicit support anticommutation. An independent symplectic frame calculation
agrees with every representative corrected terminal result.

Actual native DEM components and identical local syndromes are decoded using
independently assembled sparse-check-matrix PyMatching graphs. Separate paths
retain differently labelled parallel alternatives; direct DEM import would
merge some of these and is not a valid labelled reference. Both temporal
predictions and CSS/readout capacity solutions agree. Independent public view
projection and explicit GF(2) sector replay give exactly the same terminal
bits/labels on the same finite-p samples. Changing only terminal columns
changes evaluation but leaves all matching inputs/corrections/sectors intact.
Appending the probe preserves the full canonical prefix and identical-seed
raw-prefix samples.

Negative tests detect reversed/omitted stages, missing or unapplied readout
corrections, source/use/input-ID changes, swapped numeric X/Z halves and stale
expected sectors. A valid test-only alternative leaves nonzero boundary
sectors uncorrected, exercising sector maps across user CNOTs rather than
passing by assuming zero sectors. Production still uses the original Phase 2
CSS correction policy.

Execution checks cover both resource policies, fixed/auto batching, two-worker
spawn, static-model caching without sampler reuse, fixed serial/spawn equality,
failed-chunk restart, completed-byte preservation and identity/artifact/count
corruption. Saved rate/Wilson calculations are compared to counts read directly
from Parquet and the independent Wilson formula, with sampling forbidden.

The first dedicated gates found two fixture issues: a preparation-time thin
logical support was stale after Hadamard orientation changes, and an artifact
test named terminal_stabilizers.json instead of logical_stabilizers.json.
The controlled logical fault now uses all-data X/Z on the odd rotated CSS
patch, valid in either orientation. Corrected fault/artifact checks pass.
These fixes do not change production physical construction or inference.

Installed CLI smoke runs at d3/depth 1/p=.03 produce validated per-shot labels
for noisy resources (fixed batching) and ideal/M9 resources (auto batching),
three shots each. Completed resume preserves every byte and summarize-deep
reproduces the saved counts. These intentionally tiny runs exercise software;
their rates provide no precision, threshold or paper-comparison evidence.
Exact commands and the final regression/install gates are in [TEST.md](../TEST.md).

See [the decoder assumptions and usage](converter_deep_decoding.md). No noisy
depth-32 run, production sweep, correlated decoder or subsequent phase was run.

Final complete gate: **940 passed, 1356 inherited warnings, 800.07 s** with no
exclusions. This includes all 38 new deep decoder/execution cases and every
existing converter SE/Knill, Hex-adapter, v1 and deep generation/depth-32 test.
The separate read-only Hex gate passes **41 tests**, 188 warnings, 15.60 s.
Six resource-complete wheels build/install; verified installed imports with
Git unavailable run/resume/summarize both resource policies. pip check,
compileall, public-import audit, diff integrity and clean dependency-source
checks pass. Detailed commands, first-gate fixture failures and corrections
are retained in TEST.md.
