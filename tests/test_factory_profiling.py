"""Diagnostic wall-time accounting must not double-count nested phases."""

from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "factory_profile_diagnostic", Path(__file__).resolve().parents[1] / "scripts/profile_factory.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def test_nested_wall_and_cpu_times_have_exclusive_accounting(monkeypatch):
    wall, cpu = iter([0., 1., 3., 5.]), iter([0., 1., 2., 4.])
    monkeypatch.setattr(profile, "time", SimpleNamespace(perf_counter=lambda: next(wall),
                                                        process_time=lambda: next(cpu)))
    timer = profile.Timings()
    inner = timer.wrap(lambda: "value", "inner")
    assert timer.wrap(inner, "outer")() == "value"
    assert timer.rows["outer"] == dict(calls=1, wall_s=5., self_wall_s=3., cpu_s=4., self_cpu_s=3.)
    assert timer.rows["inner"] == dict(calls=1, wall_s=2., self_wall_s=2., cpu_s=1., self_cpu_s=1.)
    assert not timer.stack


def test_interrupted_phase_still_records_elapsed_time_and_restores_patches():
    timer = profile.Timings()

    def interrupted():
        raise TimeoutError("bounded profile")

    owner = SimpleNamespace(work=interrupted)
    with ExitStack() as scope:
        timer.instrument(scope, owner, "work", "interrupted")
        assert owner.work is not interrupted
        with pytest.raises(TimeoutError, match="bounded profile"):
            owner.work()
    assert owner.work is interrupted and not timer.stack
    assert timer.rows["interrupted"]["calls"] == 1
    assert timer.rows["interrupted"]["wall_s"] >= 0


@pytest.mark.parametrize("skip", [False, True])
def test_local_profile_reports_warm_cache_and_absent_legacy_projection(tmp_path, skip):
    config = tmp_path / "tiny.yaml"
    config.write_text(f"skip_circuit_validation: {str(skip).lower()}\n" + """schema_version: 2
kind: logical_zero_factory
name: profile_test
output_root: unused
sweep: {d: [3], p: [0.003]}
r_0: 1
r_plus: 1
T_tel: 2
create_codecapacity_dem: true
shots: 3
batch_size: 3
""")
    output = tmp_path / "profile.json"
    assert profile.main([str(config), "--distance", "3", "--p", ".003", "--shots", "3",
                         "--batch-size", "3", "--repeat", "2", "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["status"] == "complete" and report["prior_policy"] == "module_local_stim_dem"
    assert report["timings"]["prior.local_stim_dem"]["calls"] == 1
    assert report["skip_circuit_validation"] is skip
    assert report["timings"].get("setup.bundle_validation", {}).get("calls", 0) == (0 if skip else 2)
    assert report["timings"]["decode.preparation_frames"]["calls"] == 6
    assert report["timings"]["setup.packed_frame_maps"]["calls"] == 6
    assert "prior.merge_events" not in report["timings"]
    assert "prior.propagate_faults" not in report["timings"]
    assert report["stages"] == report["merge_groups"] == []
    assert report["local_cache"]["misses"] == 1 and report["local_cache"]["hits"] == 3
    first, second = report["attempts"]
    assert first["output_sha256"] == second["output_sha256"]
    assert second["timings"]["prior.local_stim_dem"]["calls"] == 0
