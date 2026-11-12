"""Stream validated saved deep labels; no circuit/decoder construction."""

import json
from pathlib import Path

from knill_bench.converter.artifacts import registered_files, validate_artifacts, validate_counts
from knill_bench.converter.deep_metadata import DEEP_POLICY, ERROR_DEFINITION, validate_deep_execution
from knill_bench.data.storage_v2 import validate_point_files
from knill_bench.experiments.config_v2 import load_saved_config
from knill_bench.experiments.seeds import point_seed
from .confidence import WilsonInterval


def summarize_saved(run_path):
    path = Path(run_path)
    document = load_saved_config(path)
    config = document.config
    metadata = json.loads((path/"metadata.json").read_text())
    if (config.kind != "converter_deep_clifford" or metadata.get("schema_version") != 2
            or metadata.get("kind") != config.kind or metadata.get("status") != "complete"
            or metadata.get("config_hash") != config.config_hash or metadata.get("config") != config.as_dict()
            or metadata.get("input_sha256") != document.input_hash or metadata.get("prior_policy") != DEEP_POLICY
            or metadata.get("final_readout") != next(config.points()).final_readout):
        raise ValueError("require a complete, unchanged converter deep Clifford scientific run")
    points = list(config.points())
    if set(metadata.get("points", ())) != {p.case_id for p in points}:
        raise ValueError("saved deep point identities changed")
    summaries = []
    for point in points:
        info = metadata["points"][point.case_id]
        if (info.get("status") != "complete" or info.get("shots") != config.shots
                or type(info.get("logical_errors")) is not int or not 0 <= info["logical_errors"] <= config.shots
                or info.get("seed") != point_seed(config.master_seed, point)
                or any(info.get(k) != v for k, v in point.sampling_identity.items())
                or info.get("files") != registered_files(point, info.get("artifacts"))):
            raise ValueError("saved deep point identity/files/counts changed")
        validate_deep_execution(point, info.get("execution"))
        validate_point_files(path, point, config.shots)
        validate_artifacts(path, point, info.get("artifacts"), execution=info["execution"])
        validate_counts(path, point, config.shots, info["logical_errors"])
        errors, shots = info["logical_errors"], info["shots"]
        lower, upper = WilsonInterval().bounds(errors, shots)
        summaries.append(dict(case_id=point.case_id, d=point.d, p=point.p, logical_qubits=point.logical_qubits,
            depth=point.depth, n_r=point.n_r, circuit_seed=point.circuit_seed,
            logical_instance_sha256=info["execution"]["logical_instance_sha256"],
            shots=shots, logical_errors=errors, logical_error_rate=errors/shots, lower=lower, upper=upper))
    return dict(summary_schema="converter_deep_summary_v1", error_definition=ERROR_DEFINITION,
        prior_policy=DEEP_POLICY, confidence=.95, interval="pointwise_Wilson_score",
        rate_units="full_circuit_failure_probability", points=summaries)
