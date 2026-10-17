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
if sys.argv[1] == "-c":
    print(os.environ.get("SAVED_WORKERS", "2"))
''')
    python.chmod(0o755)
    env = dict(os.environ, CONDA_BASE=str(base), PBS_O_WORKDIR=str(tmp_path), PBS_NCPUS="4",
               PATH=str(bin_path) + os.pathsep + os.environ["PATH"],
               ACTIVATION_LOG=str(tmp_path / "activation"), PYTHON_LOG=str(tmp_path / "python.log"))
    for name in ("WORKERS", "RESUME_RUN", "CONFIG_FILE", "PBS_NODEFILE", "KNILL_CONDA_ENV"):
        env.pop(name, None)
    return tmp_path, env


def invoke(pbs, **updates):
    path, env = pbs
    env.update(updates)
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in (path / "python.log").read_text().splitlines()] if (path / "python.log").exists() else []
    return result, calls


def test_pbs_allocated_workers_conda_threads_and_quoted_config(pbs):
    path, _ = pbs
    result, calls = invoke(pbs, CONFIG_FILE="configs/my factory.yaml", KNILL_CONDA_ENV="my_knill_cluster")
    assert result.returncode == 0, result.stderr
    assert (path / "activation").read_text().strip() == "activate my_knill_cluster"
    assert calls[0]["args"] == ["-m", "knill_bench.experiments.cli", "validate-config", "configs/my factory.yaml", "--workers", "4"]
    assert calls[1]["args"][2] == "run"
    assert all(call["cwd"] == str(path) and call["threads"] == "1" for call in calls)


def test_worker_limit_and_resume_use_saved_setting(pbs):
    result, calls = invoke(pbs, WORKERS="2", RESUME_RUN="results/saved run")
    assert result.returncode == 0
    assert calls[-1]["args"] == ["-m", "knill_bench.experiments.cli", "resume", "results/saved run"]
    assert len(calls) == 2  # Read saved workers, then resume. No simulation config override.


@pytest.mark.parametrize("updates,message", [
    ({"WORKERS": "5"}, "exceeds"), ({"WORKERS": "0"}, "positive integers"),
    ({"WORKERS": "-2"}, "positive integers"), ({"PBS_NCPUS": "bad"}, "positive integers"),
    ({"RESUME_RUN": "results/saved", "SAVED_WORKERS": "8"}, "saved run requires"),
])
def test_invalid_allocation_fails_without_launch(pbs, updates, message):
    result, calls = invoke(pbs, **updates)
    assert result.returncode == 2 and message in result.stderr
    assert not any(c["args"][:3] == ["-m", "knill_bench.experiments.cli", "run"] for c in calls)


def test_nodefile_cpu_count_and_single_node_guard(pbs):
    path, env = pbs
    env.pop("PBS_NCPUS")
    nodes = path / "nodes"
    nodes.write_text("node01\nnode01\n")
    result, calls = invoke(pbs, PBS_NODEFILE=str(nodes))
    assert result.returncode == 0 and calls[-1]["args"][-1] == "2"
    nodes.write_text("node01\nnode02\n")
    result, _ = invoke(pbs, PBS_NODEFILE=str(nodes))
    assert result.returncode == 2 and "select=1" in result.stderr
