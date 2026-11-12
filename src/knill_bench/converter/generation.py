"""Explicit artifact-only compile command; no science run or error table."""

from datetime import timedelta
import os
from pathlib import Path

from knill_bench.data.storage_v2 import atomic_json
from knill_bench.experiments.provenance import collect_environment
from knill_bench.experiments.run_v2 import RUN_TIMEZONE, utc_now
from .artifacts import publish_artifacts
from .deep_artifacts import validate_deep_artifacts


def compile_config(document):
    config = document.config
    if config.kind != "converter_deep_clifford":
        raise ValueError("compile supports converter_deep_clifford generation only")
    environment = collect_environment(config.kind)
    from .deep_clifford import CompiledDeepClifford

    root = Path(config.output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    instant = utc_now().astimezone(RUN_TIMEZONE)
    while True:
        path = root / f"{instant.strftime('%Y%m%d%H%M%S')}_{config.config_hash[:8]}_{config.name}"
        try:
            path.mkdir()
            break
        except FileExistsError:
            instant += timedelta(seconds=1)
    metadata = dict(artifact_schema="converter_generation_v1", purpose="circuit_generation_only",
        status="generating", decoder_status="not_implemented_phase4", started_at=utc_now().isoformat(), ended_at=None,
        config_hash=config.config_hash, input_sha256=document.input_hash, config=config.as_dict(),
        environment=environment, points={})
    try:
        with (path / "config.yaml").open("xb") as output:
            output.write(document.contents)
            output.flush()
            os.fsync(output.fileno())
        atomic_json(path / "metadata.json", metadata)
        for point in config.points():
            (path / point.directory).mkdir(parents=True)
            model = CompiledDeepClifford(point)
            registry = publish_artifacts(path, point, model.artifacts())
            validate_deep_artifacts(path, point, registry)
            metadata["points"][point.case_id] = dict(sampling_identity=point.sampling_identity,
                status="generated", artifacts=registry, model=model.metadata,
                files=list(registry))
            atomic_json(path / "metadata.json", metadata)
            del model
        metadata.update(status="generated", ended_at=utc_now().isoformat())
        atomic_json(path / "metadata.json", metadata)
    except BaseException as error:
        metadata.update(status="failed", ended_at=utc_now().isoformat(), error=str(error))
        atomic_json(path / "metadata.json", metadata)
        raise
    return path
