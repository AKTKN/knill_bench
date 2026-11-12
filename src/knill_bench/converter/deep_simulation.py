"""One static deep circuit/probe/local decoder per point and process."""

from dataclasses import asdict

from knill_bench.experiments.config_v2 import digest
from .deep_clifford import CompiledDeepClifford
from .deep_decoding import DeepDecoder
from .deep_metadata import DEEP_POLICY, DEEP_LIMITS, ERROR_DEFINITION
from .models import DecodedBatch
from .se_memory import text_hash

_CACHED = None


class ConverterDeepClifford(CompiledDeepClifford):
    def __init__(self, point):
        super().__init__(point)
        self.decoder = DeepDecoder(self.compiled, self.probe, frame_plan=self.frame_plan)
        stages = []
        for kind, module in self.decoder.requests.order:
            if kind == "boundary":
                adapter = self.decoder.boundary_decoders[module]
                request = adapter.request
                stages.append(dict(kind=kind, module_id=module, block_use_id=asdict(request.block_use_id),
                    temporal_dem_sha256=text_hash(str(request.detector_error_model)),
                    target_ids=list(request.target_ids), temporal=adapter.temporal.summary,
                    x_checks_sha256=digest(adapter.hx.tolist()), z_checks_sha256=digest(adapter.hz.tolist())))
            else:
                request = self.decoder.readouts[module]
                stages.append(dict(kind=kind, module_id=module, block_use_id=asdict(request.block_use_id),
                    basis=request.readout.basis, checks_sha256=digest(request.check_matrix.tolist()),
                    sector_map_sha256=digest([request.sector_map.input_size, request.sector_map.supports,
                                              list(map(bool, request.sector_constant))])))
        self.decoder_stages = stages
        self.metadata = dict(self.metadata, generation_only=False, decoder_status="local_mwpm",
            prior_policy=DEEP_POLICY, decoder_limits=list(DEEP_LIMITS), error_definition=ERROR_DEFINITION,
            enable_correlations=False, joint_cross_block_matching=False, terminal_decoder_inputs=False,
            temporal_policy="native_decomposed_components_independent_explicit_parallel_paths",
            prior_only_policy="independent_component_MAP_bias", capacity_policy="unit_hamming_per_patch_css",
            stage_count=len(stages), boundary_count=len(self.decoder.boundaries),
            readout_count=len(self.decoder.readouts), decoder_model_sha256=digest(stages),
            temporal_source_events=sum(a.temporal.summary["source_events"] for a in self.decoder.boundary_decoders.values()),
            temporal_components=sum(a.temporal.summary["components"] for a in self.decoder.boundary_decoders.values()),
            temporal_prior_only_components=sum(a.temporal.summary["prior_only_components"] for a in self.decoder.boundary_decoders.values()),
            temporal_separators=sum(a.temporal.summary["separators"] for a in self.decoder.boundary_decoders.values()))

    def decode_batch(self, measurements):
        return DecodedBatch(self.decoder.replay(measurements).logical_error)

    def artifacts(self):
        artifacts = super().artifacts()
        artifacts.metadata["decoder_stages"] = self.decoder_stages
        return artifacts


def deep_model(point):
    global _CACHED
    if _CACHED is None or _CACHED[0] != point:
        _CACHED = None
        _CACHED = (point, ConverterDeepClifford(point))
    return _CACHED[1]


def clear_deep_cache():
    global _CACHED
    _CACHED = None


def deep_artifacts(point):
    return deep_model(point).artifacts()
