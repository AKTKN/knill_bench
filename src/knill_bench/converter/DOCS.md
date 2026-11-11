# Optional converter consumer package — Phases 0/1

Phase 1 implements `se_memory.py`: authored INIT_Z(1), optional SE(R-1),
noisy MZ through the converter, exact Stim serialization and one cached model
per point/process. `decoding.py` selects the public semantic Z view, checks
complete undecomposed DEM graph compatibility and caches independent MWPM.
One raw batch yields reference-relative truth XOR prediction labels; truth is
never supplied to matching. `metadata.py` checks physical/policy/hash identity
and artifact/export linkage without importing a compiler or sampler. See
[the SE guide](../../../docs/converter_se_memory.md).

`config.py` supplies ConverterConfig/ConverterPoint and strict parse routing
from schema-v2. Only d/p sweep; fixed integer/multiplier rules resolve before
output. Kind-specific options never enter existing Hex configs/physical IDs.
`models.py` defines SimulationModel/DecodedBatch and the reserved-kind guard.

`execution.py` reuses shared bounded ChunkTask/ChunkResult spawn execution and
buffered PointWriter, requiring explicit numerical worker and parent artifact
callbacks. Integer batches have a converter-specific fixed chunk seed stream;
auto uses existing timing feedback. Native graphs/circuits/frames stay local.

`artifacts.py` supplies PointArtifacts, safe portable path resolution, parent
sidecar staging/hashing/registration, streamed saved ID/count verification and
incomplete-point cleanup. RunStore owns the publication marker and all writes.
No artifact is reader-visible as complete before its point marker is published.

`provenance.py` verifies actual exact VCS-wheel or bundle-wheel converter and
stimflow identities, RECORD/scientific-resource hashes (including grammar),
public API availability and unchanged Stim/PyMatching pins. It is loaded only
for converter infrastructure operations. No private converter module imports.

See [configuration, policies, artifact format and limits](../../../docs/converter_integration.md).
Future Knill/deep generators, decoder adapters and scientific models belong
here; those two scientific kinds remain unsupported. SE run/resume is available.
