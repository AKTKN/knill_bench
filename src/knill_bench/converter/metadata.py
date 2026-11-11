"""Saved converter-memory contract checks, with no compiler or sampler imports."""

import re

MEMORY_MODEL = "converter_se_memory_v1"
MEMORY_POLICY = "converter_z_sector_undecomposed_dem_mwpm_v1"


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
