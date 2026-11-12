"""Noisy deep Clifford runner with bounded parent-owned labels/artifacts."""

import json
from pathlib import Path

from .config_v2 import load_saved_config
from .run_v2 import RunStore


def run(document, *, resume_path=None):
    if document.config.kind != "converter_deep_clifford":
        raise ValueError("deep runner requires kind converter_deep_clifford")
    if resume_path is not None:
        if json.loads((Path(resume_path)/"metadata.json").read_text()).get("artifact_schema") == "converter_generation_v1":
            raise ValueError("generation-only artifacts cannot resume as a scientific run; use run CONFIG")
        saved = load_saved_config(resume_path)
        if saved.config != document.config or saved.contents != document.contents:
            raise ValueError("resume document must match saved deep Clifford configuration")
    from knill_bench.converter.deep_simulation import clear_deep_cache, deep_artifacts
    from knill_bench.converter.execution import execute_converter_points
    from .adaptive_execution import run_chunk

    clear_deep_cache()
    try:
        with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
            if store.metadata["status"] != "complete":
                execute_converter_points(store, worker=run_chunk, artifact_builder=deep_artifacts)
            return store.path
    finally:
        clear_deep_cache()
