# DEM conversion and physical fault audits (schema v1)

`dem.py` converts Stim events into complete detector/logical signatures,
XOR-merges identical supports, preserves logical-only effects and handles
fixed probabilities. `audit.py` inserts bounded controlled physical faults
and audits saved v1 circuits/models. No decoding Python is changed in B0.
See [design](../../../docs/design.md) and [validation](../../../docs/validation.md).

V2 decoding remains a later-runner concern using Hex's validated native APIs.
`create_codecapacity_dem=True` names a fixed-reference independent-superposition
approximation with real context/nonlinear limits, not exact conditional MAP.
Unsupported hyperedges/logical mechanisms must raise; never drop them or use
oracle truth to improve apparent confidence. B0's provenance interface checks
construct no decoder/graph/sampler. See [v2](../../../docs/auxiliary_v2.md).
