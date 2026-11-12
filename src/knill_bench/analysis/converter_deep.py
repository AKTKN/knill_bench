"""Backward-compatible deep summary using common saved converter validation."""

import json
from pathlib import Path

from knill_bench.converter.deep_metadata import DEEP_POLICY, ERROR_DEFINITION
from knill_bench.experiments.config_v2 import load_saved_config
from .converter import summarize_saved as summarize_converter


def summarize_saved(run_path):
    path=Path(run_path)
    report=summarize_converter(path)
    if report["kind"] != "converter_deep_clifford":
        raise ValueError("require a converter deep Clifford scientific run")
    config=load_saved_config(path).config
    metadata=json.loads((path/"metadata.json").read_text())
    rows=[]
    for point,row in zip(config.points(),report["points"],strict=True):
        ci=row["confidence_interval"]
        rows.append(dict(case_id=point.case_id,d=point.d,p=point.p,logical_qubits=point.logical_qubits,
            depth=point.depth,n_r=point.n_r,circuit_seed=point.circuit_seed,
            logical_instance_sha256=metadata["points"][point.case_id]["execution"]["logical_instance_sha256"],
            shots=row["shots"],logical_errors=row["logical_errors"],logical_error_rate=row["logical_error_rate"],
            lower=ci["lower"],upper=ci["upper"]))
    return dict(summary_schema="converter_deep_summary_v1",error_definition=ERROR_DEFINITION,
        prior_policy=DEEP_POLICY,confidence=.95,interval="pointwise_Wilson_score",
        rate_units="full_circuit_failure_probability",points=rows)
