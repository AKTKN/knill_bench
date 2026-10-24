# Simulation and replay (schema v1)

For prompt 01, runner.prepare explicitly rejects surface_prep_fixed after
config parsing and before directory creation. Its circuit and truth APIs
are available through Python, but the existing memory/Knill accounting must
not be used as a preparation worker. Ordered chunk integration is step 04;
see [current preparation capabilities](../../../docs/surface_preparation.md).
Prompt 02 provides setup-time boundary certification and exclusive/fsynced
artifact I/O in decoding; the step-04 delegation will save its hash and load
that validated model rather than parsing a DEM during decode. No worker or
runner source changes are part of prompt 02.

Prompt 03 adds evaluator-only `preparation_metrics.evaluate_preparation`:
join strict predictions with truth once to obtain per-check/any-check X/Z
sign errors, their code-space OR, and logical-Z readout error. Independent
baseline validity masks retain valid statistics when gaps are unavailable.
`preparation_acceptance` takes predictions only and requires all three
validities plus inclusive gap>=threshold. `summarize_preparation` produces
compact per-check/error-count/joint counters, denominators, selected/baseline
rates and invalid reasons, using null for undefined rates. No physical
correction, terminal recovery, sampler, writer or runner is constructed.
See [API and numerical semantics](../../../docs/preparation_decoder.md).

`runner.py` retains v1 prepare/execute/resume, bounded spawn scheduling,
parent commits and count/stopping behavior. `worker.py` caches compiled
physical models, samplers and numerical backends per process and streams
staged chunk parts. `seeds.py` separates physical, retention and timing
streams; `replay.py` handles optional saved-record latency replay. None of
these Python modules is changed by B0. See [design](../../../docs/design.md)
for pipeline/memory/timing assumptions and [the v1 schema](../../../docs/data_schema.md).

V2 execution instead lives in [experiments](../experiments/DOCS.md).
B1 and B2 share bounded whole-point workers, construct each sampler/graph once
per case/worker and decode recorded batches offline. Workers own point
ParquetWriters and return small results; only the parent owns metadata.
All shot trajectories stay fixed independently of analysis theta/oracle labels.
The B2 factory delegates circuit/decoder/gap work to Hex CompiledFactory;
no simulation Python in this directory is changed. See
[the B2 guide](../../../docs/logical_zero_factory.md) for two-support reuse,
units, evaluation-only oracle, exact paired outputs and supported-model limits.
