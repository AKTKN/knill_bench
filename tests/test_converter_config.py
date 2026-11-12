"""Phase 0 YAML/identity contracts; never build scientific circuits."""

from dataclasses import replace
import json
from pathlib import Path
import pickle

import pytest
import yaml

from knill_bench.experiments.config_v2 import CONVERTER_KINDS, load_config, parse_config
from knill_bench.experiments.seeds import chunk_seed, point_seed

ROOT = Path(__file__).resolve().parents[1]


def raw(kind="converter_knill_memory", **updates):
    return dict(schema_version=2, kind=kind, noise="converter_uniform",
                sweep=dict(d=[3, 5], p=[0., .001]), **updates)


@pytest.mark.parametrize("kind", sorted(CONVERTER_KINDS))
def test_schema_roundtrip_pickle_and_portable_points(kind, tmp_path):
    path = tmp_path / "source.yaml"
    path.write_text("# preserve bytes\n" + yaml.safe_dump(raw(kind)))
    doc = load_config(path)
    assert doc.contents == path.read_bytes()
    c = doc.config
    assert parse_config(c.as_dict()) == c
    assert pickle.loads(pickle.dumps(c)) == c
    assert len(list(c.points())) == 4
    for point in c.points():
        assert pickle.loads(pickle.dumps(point)) == point
        assert point.filename("logical_error") == f"points/{point.case_id}/logical_error.parquet"
        assert "\\" not in point.directory and ":" not in point.directory
        assert point.tables == ("logical_error",)
        with pytest.raises(ValueError): point.filename("logical_gaps")


@pytest.mark.parametrize("kind", sorted(CONVERTER_KINDS))
@pytest.mark.parametrize("key,value", [
    ("schema_version", True), ("schema_version", 1), ("noise", "hex_uniform"), ("noise", {"model": "custom"}),
    ("noise", "other"), ("code", "color"), ("decoder", "bplsd"), ("name", "../bad"),
    ("output_root", ""), ("shots", 0), ("workers", True), ("batch_size", False),
    ("master_seed", -1), ("master_seed", 2**64), ("buffer_shot", 0),
    ("input_preparation", "magic"), ("input_preparation", False), ("theta", 0),
    ("create_codecapacity_dem", False), ("get_logicalgap", False), ("skip_circuit_validation", False),
    ("codecapacity_prior", "module_local"), ("target_chunk_seconds", float("nan")), ("unknown", 1),
])
def test_invalid_fields(kind, key, value):
    document = raw(kind)
    document[key] = value
    with pytest.raises(ValueError): parse_config(document)


@pytest.mark.parametrize("sweep", [None, {}, {"d": [3]}, {"d": [], "p": [0.]},
    {"d": [4], "p": [0.]}, {"d": [True], "p": [0.]}, {"d": [3, 3], "p": [0.]},
    {"d": [3], "p": [0., -0.]}, {"d": [3], "p": [float("inf")]}, {"d": [3], "p": [True]},
    {"d": [3], "p": [.51]}, {"d": [3], "p": [-.001]}, {"d": [3], "p": [.001], "depth": [1, 2]},
])
def test_only_valid_d_p_sweeps(sweep):
    document = raw()
    document["sweep"] = sweep
    with pytest.raises(ValueError): parse_config(document)


@pytest.mark.parametrize("kind,key", [("converter_se_memory", "r_0"), ("converter_se_memory", "T_tel"),
    ("converter_se_memory", "resource_preparation"), ("converter_knill_memory", "rounds"),
    ("converter_knill_memory", "logical_qubits"), ("converter_deep_clifford", "T_tel"),
    ("converter_deep_clifford", "rounds")])
def test_irrelevant_kind_options_rejected(kind, key):
    with pytest.raises(ValueError, match="unknown keys"): parse_config(raw(kind, **{key: 1}))


@pytest.mark.parametrize("rule,expected", [("d", [3, 5]), (2, [2, 2]), ("2*d", [6, 10]),
    ("2/3*d", [2, 3]), (".6*d", [1, 3]), ("1.5*d", [4, 7])])
def test_depth_resolution(rule, expected):
    memory = parse_config(raw("converter_se_memory", rounds=rule))
    assert [p.rounds for p in memory.points() if p.p == 0.] == expected
    for kind in CONVERTER_KINDS - {"converter_se_memory"}:
        if rule != "d":
            with pytest.raises(ValueError, match="require r_0=r_plus=d"):
                parse_config(raw(kind, r_0=rule, r_plus=rule))
            continue
        config = parse_config(raw(kind, r_0=rule, r_plus=rule))
        assert [p.r_0 for p in config.points() if p.p == 0.] == expected
        assert all(p.r_0 == p.r_plus for p in config.points())


@pytest.mark.parametrize("rule", [False, 0, "d-2", "1/0*d", "0*d", "1/9*d", "2**d", "9e99*d", "2*d+1"])
def test_invalid_rounds(rule):
    with pytest.raises(ValueError): parse_config(raw("converter_se_memory", rounds=rule))
    with pytest.raises(ValueError): parse_config(raw(r_0=rule, r_plus=rule))


def test_shared_resource_depth_compares_resolved_values_at_every_distance():
    assert next(parse_config(dict(raw(r_0="d", r_plus=3), sweep=dict(d=[3], p=[.001]))).points()).r_0 == 3
    with pytest.raises(ValueError, match="r_0 == r_plus"):
        parse_config(raw(r_0="d", r_plus=3))


@pytest.mark.parametrize("key,value", [("logical_qubits", 0), ("depth", True), ("circuit_seed", -1),
    ("circuit_seed", 2**64), ("n_r", 0), ("resource_preparation", "unknown")])
def test_deep_options_validate(key, value):
    with pytest.raises(ValueError): parse_config(raw("converter_deep_clifford", **{key: value}))


def test_physical_identity_and_seeds_exclude_execution_controls():
    c = parse_config(raw("converter_deep_clifford"))
    a = next(c.points())
    changed = replace(c, shots=7, workers=2, batch_size=3, buffer_shot=2, name="different", decoder="mwpm")
    assert a == next(changed.points())
    assert point_seed(c.master_seed, a) == point_seed(changed.master_seed, a)
    for key, value in (("logical_qubits", 2), ("depth", 2), ("n_r", 2), ("circuit_seed", 9),
                       ("resource_preparation", "ideal")):
        b = next(replace(c, **{key: value}).points())
        assert a.case_id != b.case_id and point_seed(123, a) != point_seed(123, b)
    for b in (replace(a, d=5), replace(a, p=.002), replace(a, r_0=2, r_plus=2)):
        assert a.case_id != b.case_id and chunk_seed(123, a, 0) != chunk_seed(123, b, 0)
    knill = parse_config(raw())
    assert next(knill.points()).case_id != next(replace(knill, T_tel=2).points()).case_id
    memory = parse_config(raw("converter_se_memory"))
    assert next(memory.points()).case_id != next(replace(memory, rounds=2).points()).case_id


def test_all_legacy_hex_hashes_and_seeds_match_prechange_snapshot():
    snapshots = json.loads((ROOT / "tests/fixtures/hex_v2_identities.json").read_text())
    assert len(snapshots) == 14
    for path, expected in snapshots.items():
        c = load_config(ROOT / path).config
        assert c.config_hash == expected["config_hash"], path
        assert [[p.case_id, point_seed(c.master_seed, p)] for p in c.points()] == expected["points"], path


@pytest.mark.parametrize("suffix", ["shots: 1\nshots: 2\n", "shots: !!python/object/apply:os.system ['false']\n"])
def test_duplicate_and_unsafe_yaml(tmp_path, suffix):
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw()) + suffix)
    with pytest.raises(ValueError): load_config(path)


def test_fixed_target_and_cli_override(tmp_path):
    with pytest.raises(ValueError): parse_config(raw(batch_size=2, target_chunk_seconds=1))
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(raw(shots=7)))
    before = path.read_bytes()
    document = load_config(path, workers=2)
    assert document.config.workers == 2 and path.read_bytes() == before
    assert b"original input SHA256" in document.contents
