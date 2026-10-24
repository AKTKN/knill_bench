# Simulation and replay (schema v1)

For prompt 01, runner.prepare explicitly rejects surface_prep_fixed after
config parsing and before directory creation. Its circuit and truth APIs
are available through Python, but the existing memory/Knill accounting must
not be used as a preparation worker. Ordered chunk integration is step 04;
see [current preparation capabilities](../../../docs/surface_preparation.md).

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
