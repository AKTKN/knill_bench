"""Validated saved-only summaries for all three converter experiment kinds."""

import json
from pathlib import Path

from knill_bench.converter.artifacts import registered_files, validate_artifacts, validate_counts
from knill_bench.converter.runtime import CONTRACT, binomial_result, validate_runtime
from knill_bench.data.storage_v2 import validate_point_files
from knill_bench.experiments.config_v2 import CONVERTER_KINDS, load_saved_config
from knill_bench.experiments.noise_v2 import validate_noise_execution
from knill_bench.experiments.seeds import point_seed


def summarize_saved(run_path):
    path=Path(run_path);document=load_saved_config(path);config=document.config
    metadata=json.loads((path/"metadata.json").read_text())
    if (config.kind not in CONVERTER_KINDS or metadata.get("schema_version") != 2
            or metadata.get("kind") != config.kind or metadata.get("status") != "complete"
            or metadata.get("config_hash") != config.config_hash or metadata.get("config") != config.as_dict()
            or metadata.get("input_sha256") != document.input_hash or metadata.get("prior_policy") != config.prior_policy
            or metadata.get("final_readout") != next(config.points()).final_readout
            or metadata.get("converter_execution_contract",CONTRACT) != CONTRACT):
        raise ValueError("require a complete, unchanged converter scientific run")
    points=list(config.points())
    if set(metadata.get("points",())) != {p.case_id for p in points}:raise ValueError("saved converter point identities changed")
    rows=[]
    for point in points:
        info=metadata["points"][point.case_id]
        if (info.get("status") != "complete" or info.get("shots") != config.shots
                or type(info.get("logical_errors")) is not int or not 0 <= info["logical_errors"] <= config.shots
                or info.get("seed") != point_seed(config.master_seed,point)
                or any(info.get(k) != v for k,v in point.sampling_identity.items())
                or info.get("files") != registered_files(point,info.get("artifacts"))):
            raise ValueError("saved converter point identity/files/counts changed")
        validate_noise_execution(point,info.get("execution"),create_codecapacity_dem=False)
        validate_point_files(path,point,config.shots)
        validate_artifacts(path,point,info.get("artifacts"),execution=info["execution"])
        validate_counts(path,point,config.shots,info["logical_errors"])
        validate_runtime(path,config,point,info,required="converter_execution_contract" in metadata)
        result=binomial_result(info["logical_errors"],info["shots"])
        rows.append(dict(case_id=point.case_id,parameters=point.sampling_identity,
            shots=info["shots"],logical_errors=info["logical_errors"],**result))
    return dict(summary_schema="converter_summary_v1",kind=config.kind,prior_policy=config.prior_policy,
                rate_units="full_experiment_failure_probability",points=rows)
