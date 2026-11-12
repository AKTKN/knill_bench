"""Generation-side artifact validation without physical compilation or sampling."""

import json
import re

from knill_bench.experiments.config_v2 import digest
from .artifacts import relative_path, validate_artifacts
from .deep_program import GENERATOR, generate_logical_circuit


def validate_deep_artifacts(run, point, registry):
    validate_artifacts(run, point, registry)
    if f"{point.directory}/logical_stabilizers.json" not in registry:
        raise ValueError("deep generation requires signed logical stabilizer registration")
    model = json.loads(relative_path(run, f"{point.directory}/metadata.json").read_text())["model"]
    if not isinstance(model, dict):
        raise ValueError("deep generation requires a model metadata object")
    logical = generate_logical_circuit(logical_qubits=point.logical_qubits,
        depth=point.depth, circuit_seed=point.circuit_seed).as_dict()
    execution, probe, export = (model.get(k) for k in ("execution", "terminal_probe", "converter_export"))
    stabilizers = json.loads(relative_path(run, f"{point.directory}/logical_stabilizers.json").read_text())
    expected = dict(physical_model="converter_deep_clifford_parallel_knill_v1", generation_only=True,
        decoder_status="not_implemented_phase4", logical_qubits=point.logical_qubits,
        depth=point.depth, circuit_seed=point.circuit_seed, n_r=point.n_r, qec_intervals=point.depth,
        parallel_knill_groups=point.depth*point.n_r, teleportations=point.logical_qubits*point.depth*point.n_r,
        physical_patch_count=3*point.logical_qubits, parallel_resource_overlap_min=point.logical_qubits,
        distance=point.d, physical_error=point.p, input_preparation="ideal", input_state="plus_product",
        input_rounds=1, resource_preparation=point.resource_preparation, resource_rounds=point.d,
        m9_enabled=point.resource_preparation == "ideal", p_st_multiplier=point.p_st_multiplier,
        resource_post_se_probability=point.p*point.p_st_multiplier if point.resource_preparation == "ideal" else 0.,
        noise="converter_uniform", final_readout=point.final_readout, final_ideal_se_rounds=1,
        terminal_probe_count=point.logical_qubits, generator=GENERATOR,
        logical_instance_sha256=digest(logical), logical_stabilizers_sha256=digest(stabilizers),
        terminal_probe_sha256=digest(probe), lstim_sha256=registry[f"{point.directory}/circuit.lstim"],
        stim_sha256=registry[f"{point.directory}/circuit.stim"])
    if (not isinstance(execution, dict) or any(execution.get(k) != v for k, v in expected.items())
            or execution.get("generation_only") is not True
            or execution.get("m9_enabled") is not (point.resource_preparation == "ideal")
            or model.get("logical_circuit") != logical or not isinstance(probe, dict) or not isinstance(export, dict)
            or export.get("schema") != "compiled-metadata-v1"
            or any(execution.get(k) != probe.get(k) for k in ("source_fingerprint", "original_measurement_count"))
            or export.get("source_fingerprint") != probe.get("source_fingerprint")
            or export.get("logical_output_stabilizers") != stabilizers
            or not isinstance(stabilizers, list) or len(stabilizers) != point.logical_qubits
            or not isinstance(execution.get("source_fingerprint"), str)
            or re.fullmatch(r"[0-9a-f]{64}", execution["source_fingerprint"]) is None
            or any(type(execution.get(k)) is not int or execution[k] < 1 for k in (
                "original_measurement_count", "measurements", "qubits", "physical_time_layers"))):
        raise ValueError("deep generation artifact/model/logical/source identity changed")
    original, n = execution["original_measurement_count"], point.logical_qubits
    if (execution["measurements"] != original+n or probe.get("measurement_indices") != list(range(original, original+n))
            or probe.get("original_qubit_count") != execution["qubits"]
            or len(probe.get("observables", ())) != n or len(export.get("measurements", ())) != original):
        raise ValueError("terminal probe prefix/count metadata changed")
    for index, observable in enumerate(probe["observables"]):
        if (observable.get("logical_observable") != stabilizers[index]
                or observable.get("measurement_index") != original+index
                or observable.get("expected_value") != 0 or observable.get("physical_sign") not in (-1, 1)
                or any(type(q) is not int or not 0 <= q < execution["qubits"]
                       for axis in ("physical_x", "physical_z") for q in observable.get(axis, ()))):
            raise ValueError("terminal signed support metadata changed")
    return model
