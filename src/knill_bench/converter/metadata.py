"""Saved converter-memory contract checks, with no compiler or sampler imports."""

import re

MEMORY_MODEL = "converter_se_memory_v1"
MEMORY_POLICY = "converter_z_sector_undecomposed_dem_mwpm_v1"
KNILL_MODEL = "converter_knill_three_patch_memory_v1"
KNILL_POLICY = "converter_knill_local_component_mwpm_css_capacity_v1"
KNILL_LIMITS = (
    "Native temporal DEM decomposition components are inferred independently; correlations are ignored.",
    "Parallel component alternatives retain separate graph paths; detector-free components use prior-MAP bits.",
    "Capacity matching uses unit Hamming weights independently per patch, not joint circuit-noise inference.",
    "Native local windows cannot infer all incoming residual errors; one-round windows may have no temporal evidence.",
    "Prepared logical constraints and deterministic sector propagation do not imply exact maximum-likelihood decoding.",
)


def validate_memory_execution(point, execution):
    expected = dict(physical_model=MEMORY_MODEL, prior_policy=MEMORY_POLICY, memory_basis="Z",
                    distance=point.d, physical_error=point.p, rounds=point.rounds,
                    initialization_se_rounds=1, additional_se_rounds=point.rounds-1,
                    input_preparation=point.input_preparation, final_readout=point.final_readout,
                    noise="converter_uniform", noise_api="NoiseModel.uniform_depolarizing",
                    detector_sector="Z", correlated_components="rejected", observables=1)
    if (not isinstance(execution, dict) or any(execution.get(k) != v for k, v in expected.items())
            or any(execution.get(k) is not False for k in ("enable_correlations", "decompose_errors", "terminal_ideal_oracle"))
            or any(not isinstance(execution.get(k), str) or re.fullmatch(r"[0-9a-f]{64}", execution[k]) is None
                   for k in ("source_fingerprint", "lstim_sha256", "stim_sha256", "dem_sha256",
                             "detector_map_sha256", "observable_map_sha256"))
            or any(type(execution.get(k)) is not int or execution[k] < minimum for k, minimum in (
                ("measurements", 1), ("qubits", 1), ("physical_detectors", 1),
                ("decoding_detectors", 1), ("matching_edges", 0)))):
        raise ValueError("saved converter memory execution identity/policy/model changed or is missing")


def validate_memory_artifacts(point, registry, model, execution):
    if not isinstance(model, dict):
        raise ValueError("missing converter memory artifact model")
    saved = model.get("execution")
    validate_memory_execution(point, saved)
    validate_memory_execution(point, execution)
    export = model.get("converter_export")
    if (any(execution.get(k) != v for k, v in saved.items())
            or registry[f"{point.directory}/circuit.lstim"] != saved["lstim_sha256"]
            or registry[f"{point.directory}/circuit.stim"] != saved["stim_sha256"]
            or not isinstance(export, dict) or export.get("schema") != "compiled-metadata-v1"
            or export.get("source_fingerprint") != saved["source_fingerprint"]
            or not isinstance(export.get("selected_instructions"), list)):
        raise ValueError("converter memory artifact/source/execution linkage changed")


def validate_knill_execution(point, execution):
    ideal = point.resource_preparation == "ideal_post_se_depolarizing"
    expected = dict(physical_model=KNILL_MODEL, prior_policy=KNILL_POLICY, memory_basis="Z", physical_patch_count=3,
        distance=point.d, physical_error=point.p, T_tel=point.T_tel, teleportations=point.T_tel,
        r_0=point.r_0, r_plus=point.r_plus, post_rounds=point.post_rounds,
        input_preparation=point.input_preparation, input_rounds=1 if ideal else point.d,
        resource_preparation=point.resource_preparation, resource_rounds=point.d, p_st_multiplier=point.p_st_multiplier,
        input_post_initialization_probability=point.p if ideal else 0.,
        resource_post_se_probability=point.p*point.p_st_multiplier if ideal else 0.,
        noise="converter_uniform", final_readout=point.final_readout, decoder_limits=list(KNILL_LIMITS), observables=1,
        temporal_policy="native_decomposed_components_independent_explicit_parallel_paths",
        prior_only_policy="independent_component_MAP_bias", capacity_policy="unit_hamming_per_patch_css")
    if (not isinstance(execution, dict) or any(execution.get(k) != v for k, v in expected.items())
            or execution.get("m9_enabled") is not ideal
            or any(execution.get(k) is not False for k in ("enable_correlations", "joint_cross_block_matching", "terminal_ideal_oracle"))
            or any(not isinstance(execution.get(k), str) or re.fullmatch(r"[0-9a-f]{64}", execution[k]) is None
                   for k in ("source_fingerprint", "lstim_sha256", "stim_sha256", "decoder_model_sha256"))
            or any(type(execution.get(k)) is not int or execution[k] < 0 for k in (
                "measurements", "qubits", "physical_detectors", "stage_count", "boundary_count", "readout_count",
                "temporal_source_events", "temporal_components", "temporal_prior_only_components", "temporal_separators"))):
        raise ValueError("saved converter Knill memory execution identity/policy changed or is missing")


def validate_knill_artifacts(point, registry, model, execution):
    from knill_bench.experiments.config_v2 import digest
    if not isinstance(model, dict):
        raise ValueError("missing converter Knill model artifacts")
    saved, export, stages = model.get("execution"), model.get("converter_export"), model.get("decoder_stages")
    validate_knill_execution(point, saved)
    validate_knill_execution(point, execution)
    if (any(execution.get(k) != v for k, v in saved.items())
            or registry[f"{point.directory}/circuit.lstim"] != saved["lstim_sha256"]
            or registry[f"{point.directory}/circuit.stim"] != saved["stim_sha256"]
            or not isinstance(export, dict) or export.get("schema") != "compiled-metadata-v1"
            or export.get("source_fingerprint") != saved["source_fingerprint"]
            or not isinstance(export.get("selected_instructions"), list)
            or not isinstance(stages, list) or digest(stages) != saved["decoder_model_sha256"]
            or len(stages) != saved["stage_count"]):
        raise ValueError("converter Knill artifact/source/execution linkage changed")
