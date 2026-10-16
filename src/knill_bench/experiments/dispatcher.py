"""Lazy dispatch for independent v2 scientific runners."""

from importlib import import_module
from pathlib import Path

from .config_v2 import KINDS, load_config


def experiment_runner(kind):
    if kind not in KINDS:
        raise ValueError("unknown v2 experiment kind")
    module_name = f"knill_bench.experiments.{kind}"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        phase = "B1" if kind == "fig4d_reproduction" else "B2"
        raise NotImplementedError(f"{kind} scientific runner belongs to {phase}; it is not implemented yet") from error
    return module.run


def dispatch(config_path):
    document = load_config(config_path)
    # Resolve before creating a run, so unavailable runners leave no outputs.
    return experiment_runner(document.config.kind)(document)


def resume(run_path):
    path = Path(run_path).resolve()
    document = load_config(path / "config.yaml")
    return experiment_runner(document.config.kind)(document, resume_path=path)
