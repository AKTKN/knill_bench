"""B0 strict configuration, identities and phase dispatch; no simulation."""

from dataclasses import replace
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from knill_bench.config import resolve as resolve_v1
from knill_bench.experiments import load_config, parse_config
from knill_bench.experiments import dispatcher
from knill_bench.experiments.seeds import chunk_seed, point_seed

ROOT = Path(__file__).resolve().parents[1]


def raw_config(**updates):
    return dict(schema_version=2, kind="logical_zero_factory", name="unit_test",
                sweep={"d": [3, 5], "p": [0., .001]}, r_0="d", r_plus=2, T_tel=3, **updates)


@pytest.mark.parametrize("filename,kind", [("fig4d_v2_example.yaml", "knill_ec_memory"),
                                         ("logical_zero_factory_v2_example.yaml", "logical_zero_factory")])
def test_examples_parse_without_v1_changes(filename, kind):
    doc = load_config(ROOT / "configs" / filename)
    assert doc.config.kind == kind
    assert len(list(doc.config.points())) == len(doc.config.distances) * len(doc.config.probabilities)
    assert parse_config(doc.config.as_dict()) == doc.config
    assert doc.contents == doc.source_path.read_bytes()
    with pytest.raises(ValueError, match="unknown fields|schema_version"):
        resolve_v1(yaml.safe_load(doc.contents))


@pytest.mark.parametrize("key,value", [
    ("basis", ["x", "z"]), ("T_tel", [1, 2]), ("r_0", [1, 2]),
    ("workers", [1, 2]), ("theta", [0., 1.]), ("create_codecapacity_dem", [False, True]),
])
def test_forbidden_sweep_axes(key, value):
    cfg = raw_config()
    cfg["sweep"][key] = value
    with pytest.raises(ValueError, match="unknown keys"):
        parse_config(cfg)


@pytest.mark.parametrize("key,value", [
    ("schema_version", True), ("schema_version", 1), ("kind", "other"),
    ("name", "../escape"), ("output_root", ""), ("code", "color"),
    ("noise", "other"), ("r_0", "d-2"), ("r_plus", "__import__('os').system('false')"),
    ("r_0", 0), ("T_tel", [1, 2]), ("T_tel", True), ("shots", 0),
    ("batch_size", False), ("workers", -1), ("master_seed", 2**64),
    ("master_seed", -1), ("theta", float("nan")), ("theta", float("inf")),
    ("theta", [1, 2]), ("create_codecapacity_dem", 1), ("decoder", ["mwpm"]),
    ("unknown", 5),
])
def test_invalid_fixed_fields(key, value):
    cfg = raw_config()
    cfg[key] = value
    with pytest.raises(ValueError):
        parse_config(cfg)


@pytest.mark.parametrize("kind", ["fig4d_reproduction", "logical_zero_factory"])
@pytest.mark.parametrize("rule,expected", [
    ("d", [3, 5]), (2, [2, 2]), ("2*d", [6, 10]), ("2/3*d", [2, 3]),
    ("1.5*d", [4, 7]), ("0.6*d", [1, 3]), (" 2 / 3 * d ", [2, 3]),
    ("999999999999999999/1000000000000000000*d", [2, 4]),
])
def test_round_multipliers_floor_exactly_for_both_experiments(kind, rule, expected):
    raw = raw_config()
    raw.update(kind=kind, r_0=rule, r_plus=rule, sweep={"d": [3, 5], "p": [.001]})
    config = parse_config(raw)
    points = list(config.points())
    assert config.name == raw["name"]
    assert [p.r_0 for p in points] == [p.r_plus for p in points] == expected
    assert config.r_0 == config.r_plus == rule
    assert parse_config(config.as_dict()) == config


@pytest.mark.parametrize("rule", [
    "0*d", "-2*d", "1/0*d", "2/-3*d", "2//3*d", "d*2", "2*d+1",
    "2**d", "nan*d", "inf*d", "2/3", "2", "", False, .5,
    "9223372036854775807*d",
])
def test_invalid_round_multipliers_rejected(rule):
    for name in ("r_0", "r_plus"):
        raw = raw_config()
        raw[name] = rule
        with pytest.raises(ValueError, match=name):
            parse_config(raw)


def test_round_multiplier_must_resolve_positive_at_every_distance():
    raw = raw_config()
    raw.update(r_0="1/4*d", sweep={"d": [5, 3], "p": [.001]})
    with pytest.raises(ValueError, match=r"r_0 resolved at d=3.*flooring"):
        parse_config(raw)


def test_equivalent_round_rules_keep_physical_identity_and_seed():
    raw = raw_config()
    raw.update(r_0="2/3*d", r_plus="2*d", sweep={"d": [3], "p": [.001]})
    multiple = parse_config(raw)
    literal = parse_config(dict(raw, r_0=2, r_plus=6))
    a, b = next(multiple.points()), next(literal.points())
    assert a == b and a.case_id == b.case_id
    assert point_seed(multiple.master_seed, a) == point_seed(literal.master_seed, b)
    assert multiple.config_hash != literal.config_hash


@pytest.mark.parametrize("sweep", [None, {}, {"d": [3]}, {"d": [], "p": [.001]},
                                  {"d": [4], "p": [0.]}, {"d": [True], "p": [0.]},
                                  {"d": [3, 3], "p": [0.]}, {"d": [3], "p": [0., -0.]},
                                  {"d": [3], "p": [-.1]}, {"d": [3], "p": [.6]},
                                  {"d": [3], "p": [float("nan")]}, {"d": [3], "p": [True]}])
def test_invalid_axes(sweep):
    cfg = raw_config()
    cfg["sweep"] = sweep
    with pytest.raises(ValueError):
        parse_config(cfg)


def test_duplicate_yaml_keys_and_unsafe_tags_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("schema_version: 2\nschema_version: 2\n")
    with pytest.raises(ValueError, match="unique"):
        load_config(path)
    path.write_text("!!python/object/apply:os.system ['false']")
    with pytest.raises(ValueError, match="invalid v2 YAML"):
        load_config(path)


def test_fig4d_convention_is_false():
    cfg = raw_config()
    cfg.update(kind="fig4d_reproduction", create_codecapacity_dem=True)
    with pytest.raises(ValueError, match="requires create_codecapacity_dem=False"):
        parse_config(cfg)


def test_filename_rules_precision_and_seed_independence():
    config = parse_config(raw_config())
    points = list(config.points())
    assert [p.r_0 for p in points] == [3, 3, 5, 5]
    filename = points[1].filename("logical_error")
    assert filename == "logical_error__code=rotated_surface,d=3,p=0.001,noisemodel=hex_uniform,T=3,r_0=3,r_+=2.parquet"
    assert re.fullmatch(re.escape(filename), filename)
    assert replace(points[1], p=float(np.nextafter(.001, 1.))).filename("logical_error") != filename
    baseline = {p.case_id: (point_seed(config.master_seed, p), chunk_seed(config.master_seed, p, 7)) for p in points}
    different_policy = replace(config, theta=4., create_codecapacity_dem=True, workers=4, shots=128)
    assert config.config_hash != different_policy.config_hash
    assert baseline == {p.case_id: (point_seed(config.master_seed, p), chunk_seed(config.master_seed, p, 7))
                        for p in reversed(list(different_policy.points()))}
    assert len({v[0] for v in baseline.values()}) == 4
    assert chunk_seed(8, points[0], 0) != chunk_seed(8, points[0], 1)
    assert chunk_seed(8, points[0], 0) != chunk_seed(9, points[0], 0)
    assert chunk_seed(8, points[0], 0, stream="retention") != chunk_seed(8, points[0], 0)
    assert all(0 <= v[0] < 2**64 for v in baseline.values())
    with pytest.raises(ValueError):
        chunk_seed(8, points[0], -1)
    with pytest.raises(ValueError):
        points[0].filename("other")


@pytest.mark.parametrize("filename", ["fig4d_v2_example.yaml", "logical_zero_factory_v2_example.yaml"])
def test_dispatch_selects_runner_without_changing_document(tmp_path, filename, monkeypatch):
    cfg = yaml.safe_load((ROOT / "configs" / filename).read_bytes())
    cfg["output_root"] = str(tmp_path / "output")
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(cfg))
    seen = []
    monkeypatch.setattr(dispatcher, "import_module", lambda name: SimpleNamespace(run=lambda doc: seen.append((name, doc))))
    dispatcher.dispatch(path)
    assert seen[0][0].endswith(cfg["kind"]) and seen[0][1].contents == path.read_bytes()
    assert not (tmp_path / "output").exists()


def test_dispatch_does_not_hide_a_runner_dependency_failure(monkeypatch):
    def unavailable(name):
        raise ModuleNotFoundError("real dependency missing", name="some_dependency")
    monkeypatch.setattr(dispatcher, "import_module", unavailable)
    with pytest.raises(ModuleNotFoundError, match="real dependency"):
        dispatcher.experiment_runner("logical_zero_factory")


def test_new_cli_works_outside_repository_and_preserves_legacy_validation(tmp_path):
    path = str(ROOT / "configs/logical_zero_factory_v2_example.yaml")
    result = subprocess.run([sys.executable, "-m", "knill_bench.experiments.cli", "validate-config", path],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["config"]["schema_version"] == 2
