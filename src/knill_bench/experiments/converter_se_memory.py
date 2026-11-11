"""Runnable converter-authored SE memory using parent-owned bounded output."""

from .config_v2 import load_saved_config
from .run_v2 import RunStore


def run(document, *, resume_path=None):
    if document.config.kind != "converter_se_memory":
        raise ValueError("converter memory runner requires kind converter_se_memory")
    # Reject mismatched caller documents before resume performs any cleanup.
    if resume_path is not None:
        saved = load_saved_config(resume_path)
        if saved.config != document.config or saved.contents != document.contents:
            raise ValueError("resume document must match saved converter memory configuration")
    from knill_bench.converter.execution import execute_converter_points
    from knill_bench.converter.se_memory import clear_memory_cache, memory_artifacts
    from .adaptive_execution import run_chunk

    clear_memory_cache()
    try:
        with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
            if store.metadata["status"] != "complete":
                execute_converter_points(store, worker=run_chunk, artifact_builder=memory_artifacts)
            return store.path
    finally:
        clear_memory_cache()
