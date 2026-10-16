# Simulation and replay (schema v1)

`runner.py` retains v1 prepare/execute/resume, bounded spawn scheduling,
parent commits and count/stopping behavior. `worker.py` caches compiled
physical models, samplers and numerical backends per process and streams
staged chunk parts. `seeds.py` separates physical, retention and timing
streams; `replay.py` handles optional saved-record latency replay. None of
these Python modules is changed by B0. See [design](../../../docs/design.md)
for pipeline/memory/timing assumptions and [the v1 schema](../../../docs/data_schema.md).

V2 infrastructure instead lives in [experiments](../experiments/DOCS.md).
B0 deliberately supplies no v2 worker pool, batch sampler, Fig.4(d) adapter or
factory inference runner; unavailable dispatch raises before creating output.
B1/B2 will own those point-level tasks, construct each sampler/graph once per
case/worker and decode recorded batches offline. Workers will own point
ParquetWriters and return small results; only the parent owns metadata.
All shot trajectories stay fixed independently of analysis theta/oracle labels.
