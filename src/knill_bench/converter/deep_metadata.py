"""Strict saved deep-decoder identity, without native construction/sampling."""

import re

from .metadata import KNILL_LIMITS

DEEP_POLICY = "converter_deep_local_component_mwpm_css_capacity_v1"
ERROR_DEFINITION = "any_corrected_terminal_stabilizer_flip_full_circuit"
DEEP_LIMITS = (*KNILL_LIMITS,
    "Deterministic Clifford frame/sector transport is retained without probabilistic cross-block inference.",
    "Terminal ideal probes are evaluation-only; full-circuit failure is any corrected stabilizer flip.")


def validate_deep_execution(point, execution):
    n, cycles = point.logical_qubits, point.depth*point.n_r
    expected = dict(physical_model="converter_deep_clifford_parallel_knill_v1", generation_only=False,
        decoder_status="local_mwpm", prior_policy=DEEP_POLICY, decoder_limits=list(DEEP_LIMITS),
        error_definition=ERROR_DEFINITION, logical_qubits=n, depth=point.depth, n_r=point.n_r,
        circuit_seed=point.circuit_seed, physical_patch_count=3*n, teleportations=n*cycles,
        qec_intervals=point.depth, parallel_knill_groups=cycles, parallel_resource_overlap_min=n,
        distance=point.d, physical_error=point.p, input_preparation="ideal", input_state="plus_product",
        input_rounds=1, resource_preparation=point.resource_preparation, resource_rounds=point.d,
        p_st_multiplier=point.p_st_multiplier,
        resource_post_se_probability=point.p*point.p_st_multiplier if point.resource_preparation == "ideal" else 0.,
        noise="converter_uniform", final_readout=point.final_readout, final_ideal_se_rounds=1,
        terminal_probe_count=n, boundary_count=2*n*(1+cycles), readout_count=2*n*cycles,
        stage_count=2*n+4*n*cycles,
        temporal_policy="native_decomposed_components_independent_explicit_parallel_paths",
        prior_only_policy="independent_component_MAP_bias", capacity_policy="unit_hamming_per_patch_css")
    if (not isinstance(execution, dict) or any(execution.get(k) != v for k, v in expected.items())
            or execution.get("m9_enabled") is not (point.resource_preparation == "ideal")
            or any(execution.get(k) is not False for k in (
                "generation_only", "enable_correlations", "joint_cross_block_matching", "terminal_decoder_inputs"))
            or any(not isinstance(execution.get(k), str) or re.fullmatch(r"[0-9a-f]{64}", execution[k]) is None
                   for k in ("source_fingerprint", "lstim_sha256", "stim_sha256", "decoder_model_sha256",
                             "logical_instance_sha256", "logical_stabilizers_sha256", "terminal_probe_sha256"))
            or any(type(execution.get(k)) is not int or execution[k] < minimum for k, minimum in (
                ("original_measurement_count", 1), ("measurements", 1), ("qubits", 1), ("physical_time_layers", 1),
                ("temporal_source_events", 0), ("temporal_components", 0), ("temporal_prior_only_components", 0),
                ("temporal_separators", 0)))):
        raise ValueError("saved deep Clifford execution identity/policy/model changed or is missing")
    if execution["measurements"] != execution["original_measurement_count"]+n:
        raise ValueError("saved deep terminal/canonical measurement partition changed")
