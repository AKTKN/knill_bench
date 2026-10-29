# Fixed-R preparation validation and reports (prompt 05)

[Getting started](preparation_getting_started.md) gives executable commands and
small simulation budgets. `analysis.preparation_report.analyze_saved(run,
output=None, thresholds=None)` returns `(case_summaries, analysis_directory)`.
`analysis.preparation.analyze` and `report.analyze` retain the list return type.
The CLI prints the actual analysis report path. Existing legacy analysis keeps
its output behavior; new output/threshold flags are preparation-only.

## Immutable saved-data analysis

The output is a newly created directory, explicit via `--output`, or unique
under RUN/analysis. Reusing an existing directory raises. Writing into the run
root or simulation data/model/circuit/checkpoint/staging/log directories raises.
No sampler, live matching graph, simulation or resume is constructed. Static
Stim circuit/DEM parsing is used for an independent saved-map/marginal audit.
A failure writes validation_summary.json with status=fail, its reason and an
analysis failure report before raising. A pass records exactly which checks
ran; it does not claim that repository tests ran inside the analyzer.

Only checkpoint-published parts are read. Source artifact registry and part
hashes/schemas/counts/seed identities are checked before analysis. Failed
assigned-but-unobserved chunks remain outside observed denominators. Setup
circuits, maps, config and checkpoints are unchanged, including when a run is
incomplete; the published prefix can be analyzed. Resume compatibility with
today's source is separate from saved-only analysis.

Saved records are checked for exactly R physical extraction rounds, omitted
unknown first-X anchor, ordered known-zero first-Z anchor, online-only SE
record references, no terminal noise/idling and the after-final-Z cut. Nominal
production and completed DEMs are projected onto the same X online rows and
all evaluation labels, then compared by independent parity signatures. They
are not compared as full CSS versus X-only vectors. The separate Z-prefix
model's selector/scope/hash is verified. Earlier deterministic tests establish
the native instrument, actual noise schedule, truth isolation and Pauli-fault
responses; source hashes identify those checks' implementation.

The analyzer streams one saved chunk at a time. It validates summary metric
and joint counts, bin partition totals and compact row identities/null masks/
status/scores. When compact rows are saved, all event/bin counters are
independently recomputed and retained rows are joined against their original
compact correction/events. Analysis retains only case/bin/cut counters,
configured bounded diagnostics and static models; it never materializes all
shot tables across a run.

## Probability and interval schema

`conditional_rates.parquet` has analysis_version=1 metadata and typed
case_id/d/R/p/decoder, bin, left/right, occupancy, scope, metric, denominator,
events, rate/lower/upper. Bins are [0,1),[1,2),[2,4),[4,8),[8,16),[16,32),
[32,64),[64,inf), plus bin=-1 for unavailable scores. Null right on the last
bin means unbounded. Unavailable scores have null left/right. `metric_valid`
uses each metric's own mask; `common_gap_valid` requires valid X baseline,
X complement and Z baseline. Joint/code statistics require both baselines.
A missing complement does not erase otherwise valid unconditional metrics.

`threshold_curve.parquet` has threshold (float64, infinities permitted), metric,
attempts, accepted, invalid, rejected_valid, events, conditional_denominator,
A/A_lower/A_upper, U/U_lower/U_upper, Q/Q_lower/Q_upper, plus case identity.
For the four primary metrics, N is all observed physical attempts, n is all
three masks AND gap>=g, and k is accepted errors. A=n/N, U=k/N, Q=k/n.
The additional logical_z_given_code_correct metric has denominator equal to
accepted code-correct shots; its Q is P(E_LZ | E_code=0,accept). Its A still
reports total accepted fraction; the distinct conditional_denominator is
explicit. Invalid and valid-but-below-cut fractions are separate.

Default cuts are fixed bin edges with +/-infinity. Compact rows support exact
arbitrary cuts. Aggregate-only data support saved edges and infinities; other
cuts raise instead of interpolating. All comparisons are inclusive >= and
use the saved unrounded gap. Analysis never chooses trajectories or changes
simulation thresholds. No new simulation sweep axis is introduced.

Intervals use the shared `WilsonInterval` at fixed .95, two-sided, without
continuity correction. They apply separately to each integer numerator and
its explicit denominator. Zero events have a positive upper bound; zero
trials give null point/interval values. Curves are exploratory, fixed-shot,
pointwise summaries; no simultaneous or data-selected-threshold coverage
claim is made. Gap is not posterior log odds; exp(-gap) is not calibrated.

`joint_counts.json` uses index 4*E_X+2*E_Z+E_LZ overall, per bin and accepted
cut. Per-check error counts and error-count histograms remain in unchanged
saved chunk summaries; shot-level any-check event rates are not per-check
rates. `paired_comparisons.json` preserves same-physical-chunk event cells
00,01,10,11 for each jointly valid metric and decoder pair, with disagreement
count 01+10. New runs save these bounded counters inside the first decoder's
summary_json; no physical/table schema or sampling identity changes. Older
multi-decoder data without those counters explicitly report unavailable;
no independent-sample variance is substituted. Different physical cases are
not paired, even with equal seeds.

## Independent retained-witness audit

Original completed DEM columns include p0 terms. Full witnesses were expanded
through active_columns before persistence. The analyzer verifies inactive
columns zero, all original spatial IDs/fixed bits, H e0=H e1=y, both P/F flips,
the same integer objective including fixed costs, nonnegative gap and the
scaled score. X feature predictions and separate Z syndrome/feature predictions
are checked directly by GF(2) multiplication. It independently traverses the
original selected difference edges to find a P–F path, recording original
column and mechanism IDs. Parallel edges are never merged for this check.

All results must have the saved mode/model identity. Full-witness chains are
from their own solve; debug_matches_compact=False does not invalidate that
solve or attach it to a compact correction. Compact mode has no full witness
and is explicitly unavailable for path validation. Null complements keep their
status and null score; they do not become infinite confidence. These checks
verify feasibility/cost/features, not optimality on every large saved graph;
independent exhaustive finite graph tests establish the solver's objective
contract separately.

Given graphlikeness of the unmerged completed model, frozen spatial ports,
Hδ=0, δ_S=0 and Pδ=Fδ=1, the only odd augmented vertices are P/F. They lie in
the same connected component and the difference support contains a P–F path.
Cycles and multiple paths are allowed. This does not prove that a physical
sample had a time-spanning fault or that independent DEM terms map one-to-one
to physical gate faults. Unsupported hyperedges/separators raise earlier;
there is no physical likelihood lift, posterior or fault-tolerance claim.

The reproducible synthetic counterexample enumerates all 16 four-edge
assignments: two disconnected spatial ports cost 2 if left unfrozen, whereas
freezing them forces the valid P–online–F path of cost 12. For the readout-only
syndrome-one example, baseline/complement costs are 5/7 and gap=2. Tests also
compare every spatial assignment and temporal RHS against an independent
enumeration, including infeasible RHSs. The figure is labeled synthetic;
actual retained X misses, when present, get a separate diagnostic plot. Biased
retained examples cannot supply frequency estimates.

## Figures, performance and scope

Matplotlib writes 300 dpi PNG plus PDF/SVG for sign-gap risk (X/Z/code with
occupancy and counts), logical-Z gap risk (own/common denominators), acceptance
versus risk (with U and separate rejection/invalid panels), and the spatial
escape counterexample. Numerical source data are the typed tables/JSON files.
Legends/captions identify d/R/p/decoder/attempts, objective, freezing and the
evaluation-only suffix. All-zero rates retain visible upper interval bars.

The report's throughput/memory table gives d/R/p/shots, saved YAML worker count,
chunk size, sampling, X baseline/complement, Z, staging I/O, parent commit,
process peak RSS and primary decode shots/s. These are observed phase sums;
concurrent phases overlap. Pool/imports, warmup/replay, setup and I/O are excluded
from decode-only throughput. RSS includes process imports/native allocations;
sparse buffer bytes omit opaque native graphs. Tiny-part overhead dominates
small output-byte ratios. A separate end-to-end smoke measures actual elapsed
wall time and records its exact config/results in TEST.md and the smoke report.

Deterministic physical fixtures use d3/5 and <=7 shots. The final gate retains
all prior tests and adds ideal diagnostic Z MPP versus destructive H_Z readout,
direct terminal tableau/Pauli signs, first/last/continuous readout ambiguity,
independent graph optima and report corruption/null/output tests. The authorized
end-to-end smoke uses d3 and explicit small budgets only. d5/7/9, R2/3/4/5
statistical sweeps, adaptive continuation and factory efficiency remain future
experiments requiring an explicit production request. Non-observation in a
smoke run leaves rare error rates unresolved.

Actual prompt-05 final results: [921-test gate and bounded end-to-end smoke](preparation_validation_report.md).
