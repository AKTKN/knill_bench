"""General fixed-depth Hex Knill EC memory; physical policy is a point field."""

from .fig4d_reproduction import _run_point
from .execution import execute_points
from .run_v2 import RunStore


def validate_experiment(config):
    if config.kind != "knill_ec_memory" or config.T_tel < 1:
        raise ValueError("Knill EC requires kind knill_ec_memory and positive T_tel")
    if config.theta is not None or config.create_codecapacity_dem:
        raise ValueError("Knill EC requires no theta and create_codecapacity_dem=False")


def run(document, *, resume_path=None):
    validate_experiment(document.config)
    # Reject an external mismatched document before resume can clean files.
    if resume_path is not None:
        from .config_v2 import load_saved_config
        if load_saved_config(resume_path).config != document.config:
            raise ValueError("resume document must match the saved run configuration")
    with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
        validate_experiment(store.document.config)
        if store.metadata["status"] != "complete":
            execute_points(store, _run_point)
        return store.path
