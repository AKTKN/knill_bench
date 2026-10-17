"""Test the PBS wrapper without a scheduler, environment changes or simulation."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/cluster_run_simualtion.sh"


@pytest.fixture
def pbs(tmp_path):
    base = tmp_path / "anaconda test"
    hooks = base / "etc/profile.d"
    hooks.mkdir(parents=True)
    (hooks / "conda.sh").write_text('conda() { printf "%s\\n" "$*" > "$ACTIVATION_LOG"; }\n')
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    python = bin_path / "python"
    python.write_text(f'''#!{sys.executable}
import json, os, sys
with open(os.environ["PYTHON_LOG"], "a") as out:
    out.write(json.dumps(dict(args=sys.argv[1:], cwd=os.getcwd(), threads=os.environ["OMP_NUM_THREADS"])) + "\\n")
''')
    python.chmod(0o755)
    env = dict(os.environ, CONDA_BASE=str(base), PBS_O_WORKDIR=str(tmp_path),
               PATH=str(bin_path) + os.pathsep + os.environ["PATH"],
               ACTIVATION_LOG=str(tmp_path / "activation"), PYTHON_LOG=str(tmp_path / "python.log"))
    for name in ("WORKERS", "RESUME_RUN", "CONFIG_FILE", "PBS_NCPUS", "PBS_NODEFILE", "KNILL_CONDA_ENV"):
        env.pop(name, None)
    return tmp_path, env


def invoke(pbs, **updates):
    path, env = pbs
    env.update(updates)
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in (path / "python.log").read_text().splitlines()] if (path / "python.log").exists() else []
    return result, calls


def test_pbs_conda_threads_and_quoted_config(pbs):
    path, _ = pbs
    result, calls = invoke(pbs, CONFIG_FILE="configs/my factory.yaml", KNILL_CONDA_ENV="my_knill_cluster")
    assert result.returncode == 0, result.stderr
    assert (path / "activation").read_text().strip() == "activate my_knill_cluster"
    assert len(calls) == 1
    assert calls[0]["args"] == ["-m", "knill_bench.experiments.cli", "run", "configs/my factory.yaml"]
    assert all(call["cwd"] == str(path) and call["threads"] == "1" for call in calls)


def test_resume_uses_saved_settings_without_cpu_checks(pbs):
    result, calls = invoke(pbs, PBS_NCPUS="1", RESUME_RUN="results/saved run")
    assert result.returncode == 0
    assert calls[-1]["args"] == ["-m", "knill_bench.experiments.cli", "resume", "results/saved run"]
    assert len(calls) == 1


@pytest.mark.parametrize("updates", [
    {},
    {"WORKERS": "1"},
    {"WORKERS": "96", "PBS_NCPUS": "1"},
    {"PBS_NCPUS": "bad"},
    {"PBS_NODEFILE": "/not-read-by-the-launcher"},
])
def test_cpu_environment_does_not_override_yaml(pbs, updates):
    result, calls = invoke(pbs, **updates)
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert calls[0]["args"] == [
        "-m", "knill_bench.experiments.cli", "run", "configs/templates/logical_zero_factory.yaml",
    ]


def test_single_nodefile_entry_does_not_replace_yaml_workers(pbs):
    path, _ = pbs
    config = path / "config.yaml"
    contents = "schema_version: 2\nkind: fig4d_reproduction\nworkers: 96\n"
    config.write_text(contents)
    nodes = path / "nodes"
    nodes.write_text("node01\n")
    result, calls = invoke(pbs, PBS_NODEFILE=str(nodes), CONFIG_FILE=str(config))
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert calls[0]["args"] == ["-m", "knill_bench.experiments.cli", "run", str(config)]
    assert config.read_text() == contents
