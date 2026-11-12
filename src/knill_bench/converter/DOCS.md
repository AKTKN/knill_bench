# Optional converter consumer package — Phases 0–5

Phase 3 adds `deep_program.py`: frozen abstract gate layers, a private seeded
HXYZ/shuffle/orientation RNG and explicit barrier-separated parallel LSTIM.
`deep_clifford.py` compiles through public typed noise policies, checks patch/
relocation/overlap allocation and validates native logical stabilizers before
requesting a native terminal probe. Its circuit is probe.circuit; no physical
lifting, MPP construction or signed frame correction is implemented here.
The model has a lazy public frame plan and deliberately has no decode_batch.
`generation.py` owns artifact-only fresh output; `deep_artifacts.py` verifies
full logical sequence, signed state, probe-prefix/count/support metadata and
hashes. No scientific run marker, samples or error tables are produced.
See [the deep guide](../../../docs/converter_deep_clifford.md).

Phase 2 adds `knill_program.py` (three-patch LSTIM, actual-use discovery and
public typed M9/post-initialization noise), `knill_memory.py` (cached static
model/artifacts), `knill_decoding.py` (public boundary/readout requests and
causal frame replay) and `local_matching.py` (explicit component-independent
temporal matching plus unit-Hamming CSS capacity). Every parallel alternative
has a separate graph path; invisible components have a declared prior rule;
residual hyperedges raise. Prepared logical constraints and native sector maps
are retained. Final corrected interpreted parity supplies labels, with no
oracle/probe inputs. Metadata binds policies, limits and stage hashes. See
[the Knill guide](../../../docs/converter_knill_memory.md).

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
Phase 4 adds deep_simulation.py (static point cache), deep_decoding.py
(prefix-only causal replay plus public terminal evaluation), and deep_metadata.py
(strict scientific policy/source/stage identity). CausalDecoder shares Phase 2
adapters and enforces stage order, source/use/input IDs and applied readout
syndromes. deep_artifacts.py validates both scientific sidecars and historical
generation bundles. All three kinds support run/resume; compile stays artifact-only.
See [deep decoding](../../../docs/converter_deep_decoding.md).

## Phase 5 integration

runtime.py owns a <=512-row parent sampling ledger with exact chunk IDs,
shot ranges, uint64 seeds and split timings. Public iter_sampling_chunks streams
recorded replay tasks. validate_runtime binds chunk streams/digests, Parquet
checksums, E/N/Wilson summaries and timing aggregates without sampling. New runs
use converter_execution_v2; historical artifacts retain their old contract.
All models expose native circuit_counts without changing physical identities.
Static model sidecars exclude runtime ledgers from their static content map;
root registration hashes the entire publication group.

See [final converter integration](../../../docs/converter_phase5.md).
