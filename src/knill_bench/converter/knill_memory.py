"""Static converter Knill memory model with causal local MWPM replay."""

from dataclasses import asdict

from knill_bench.experiments.config_v2 import digest
from .artifacts import PointArtifacts
from .knill_decoding import KnillDecoder
from .knill_program import IDEAL_POST, compile_knill
from .metadata import KNILL_MODEL, KNILL_POLICY, KNILL_LIMITS
from .models import DecodedBatch
from .se_memory import text_hash

_CACHED = None


class ConverterKnillMemory:
    def __init__(self, point):
        self.point = point
        self.lstim_source, self.compiled, self.stim_source = compile_knill(point)
        self.circuit = self.compiled.circuit
        self.decoder = KnillDecoder(self.compiled)
        self.frame_plan = self.decoder.frame_plan
        if len({bid for bid, _ in self.compiled.physical_qubit_map}) != 3 or len(self.compiled.relocation_history) != point.T_tel:
            raise ValueError("Knill physical patch or teleportation count changed")
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
        ideal = point.resource_preparation == IDEAL_POST
        initial, = (p for p in self.compiled.preparations if p.logical_id == "D")
        self.metadata = dict(
            physical_model=KNILL_MODEL, prior_policy=KNILL_POLICY, memory_basis="Z", physical_patch_count=3,
            distance=point.d, physical_error=point.p, T_tel=point.T_tel, teleportations=len(self.compiled.relocation_history),
            r_0=point.r_0, r_plus=point.r_plus, post_rounds=point.post_rounds,
            input_preparation=point.input_preparation, input_rounds=1 if ideal else point.d,
            resource_preparation=point.resource_preparation, resource_rounds=point.d,
            m9_enabled=ideal, p_st_multiplier=point.p_st_multiplier,
            input_post_initialization_probability=point.p if ideal else 0.,
            resource_post_se_probability=point.p*point.p_st_multiplier if ideal else 0.,
            input_use=asdict(initial.block_use_id), final_readout=point.final_readout, noise="converter_uniform",
            enable_correlations=False, joint_cross_block_matching=False, terminal_ideal_oracle=False,
            temporal_policy="native_decomposed_components_independent_explicit_parallel_paths",
            prior_only_policy="independent_component_MAP_bias", capacity_policy="unit_hamming_per_patch_css",
            decoder_limits=list(KNILL_LIMITS), measurements=self.circuit.num_measurements, qubits=self.circuit.num_qubits,
            physical_detectors=self.circuit.num_detectors, observables=1,
            stage_count=len(stages), boundary_count=len(self.decoder.boundaries), readout_count=len(self.decoder.readouts),
            source_fingerprint=self.frame_plan.source_fingerprint, lstim_sha256=text_hash(self.lstim_source),
            stim_sha256=text_hash(self.stim_source), decoder_model_sha256=digest(stages),
            temporal_source_events=sum(a.temporal.summary["source_events"] for a in self.decoder.boundary_decoders.values()),
            temporal_components=sum(a.temporal.summary["components"] for a in self.decoder.boundary_decoders.values()),
            temporal_prior_only_components=sum(a.temporal.summary["prior_only_components"] for a in self.decoder.boundary_decoders.values()),
            temporal_separators=sum(a.temporal.summary["separators"] for a in self.decoder.boundary_decoders.values()),
        )

        from .runtime import circuit_counts
        self.metadata["circuit_counts"] = circuit_counts(self.circuit, 1)

    def decode_batch(self, measurements):
        return DecodedBatch(self.decoder.replay(measurements).logical_error)

    def artifacts(self):
        return PointArtifacts(self.lstim_source, self.stim_source, dict(execution=self.metadata,
            decoder_stages=self.decoder_stages, converter_export=self.compiled.export_metadata()))


def knill_model(point):
    global _CACHED
    if _CACHED is None or _CACHED[0] != point:
        _CACHED = None
        _CACHED = (point, ConverterKnillMemory(point))
    return _CACHED[1]


def clear_knill_cache():
    global _CACHED
    _CACHED = None


def knill_artifacts(point):
    return knill_model(point).artifacts()
