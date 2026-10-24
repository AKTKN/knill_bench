"""Strict protocol-only additions and exact legacy config/grid preservation."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from knill_bench.config import canonical, grid, load, resolve
from knill_bench.preparation import PreparationCapabilityError


TEMPLATE = Path(__file__).parents[1] / "configs/templates/surface_prep_fixed.yaml"


def raw():
    return yaml.safe_load(TEMPLATE.read_text())


def test_template_round_trip_and_fixed_r_grid_without_legacy_boundary_fields():
    cfg = load(TEMPLATE)
    assert resolve(cfg) == cfg
    cfg["experiment"].update(distances=[3, 5], physical_error_rates=[0, .003])
    points = list(grid(resolve(cfg)))
    assert {(p["distance"], p["p"]) for p in points} == {(3, 0.), (3, .003), (5, 0.), (5, .003)}
    assert all(p["rounds"] == 3 and not p["adaptive"] for p in points)
    for p in points:
        assert not {"cycles", "prep_rounds", "initial_boundary", "final_readout"} & p.keys()
        assert p["oracle_cut"] == "after_final_z_extraction"
        assert p["decoding_p"] == p["p"]
    assert len({p["sampling_case_id"] for p in points}) == 4


@pytest.mark.parametrize("name,value", [
    ("rounds", 0), ("rounds", -1), ("rounds", True), ("rounds", 2.), ("rounds", "d"),
    ("rounds", "2*d"), ("rounds", 2**63), ("rounds", [2, 3]),
    ("prep_basis", "x"), ("sign_sector", "z"), ("readout_basis", "x"),
    ("logical_evaluation", "terminal_recovery"), ("adaptive", True), ("adaptive", 0),
    ("decoding_p", .5), ("decoding_p", -.01), ("decoding_p", float("nan")),
    ("decoding_p", float("inf")), ("decoding_p", True), ("decoding_p", ".003"), ("decoding_p", 2**2048),
    ("prep_rounds", 3), ("post_gate_rounds", 0), ("unknown", "value"),
])
def test_protocol_fields_reject_unknown_ambiguous_and_unsupported_modes(name, value):
    cfg = raw()
    cfg["protocols"][0][name] = value
    with pytest.raises(ValueError):
        resolve(cfg)


@pytest.mark.parametrize("name,value", [
    ("cycles", [3]), ("cycles_per_distance", [1]), ("initial_boundary", {"kind": "noisy_preparation"}),
    ("final_readout", "noisy_destructive"), ("comparison", {"kind": "equal_cycles"}),
    ("bases", ["x"]), ("bases", ["x", "z"]), ("rounds", [3]), ("master_seed", 2**64),
])
def test_preparation_never_borrows_legacy_duration_boundary_or_basis_fields(name, value):
    cfg = raw()
    cfg["experiment"][name] = value
    with pytest.raises(ValueError):
        resolve(cfg)


@pytest.mark.parametrize("profile", ["explicit", "phenomenological", "hex_uniform"])
def test_unimplemented_noise_profile_is_explicitly_rejected(profile):
    cfg = raw()
    cfg["noise"] = {"profile": profile}
    with pytest.raises(ValueError, match="only noise"):
        resolve(cfg)


@pytest.mark.parametrize("scale", [0, -1, True, "1000", float("nan"), float("inf"), 2**2048])
def test_common_cost_scale_is_strict_numeric(scale):
    cfg = raw()
    cfg["decoders"]["temporal"]["weight_scale"] = scale
    with pytest.raises(ValueError, match="weight_scale"):
        resolve(cfg)


def test_nonphysical_settings_do_not_change_sampling_ids_or_existing_seed_streams():
    from knill_bench.simulation.seeds import seed
    original = load(TEMPLATE)
    altered = deepcopy(original)
    altered["protocols"][0]["decoding_p"] = .003
    altered["decoders"]["temporal"].update(weight_scale=2000, output_mode="full_witness")
    altered["sampling"].update(workers=2, shots_per_case=7)
    a, b = next(grid(original)), next(grid(resolve(altered)))
    assert a["sampling_case_id"] == b["sampling_case_id"]
    assert seed(617, a["sampling_case_id"], 0, 0) == seed(617, b["sampling_case_id"], 0, 0)
    for key, value in (("rounds", 4),):
        changed = deepcopy(original)
        changed["protocols"][0][key] = value
        assert next(grid(resolve(changed)))["sampling_case_id"] != a["sampling_case_id"]


def test_rejects_mixed_protocols_missing_rounds_bad_decoders_and_stopping_rules():
    cfg = raw()
    cfg["protocols"].append({"id": "se_memory", "decoders": ["temporal"]})
    with pytest.raises(ValueError, match="mixed"):
        resolve(cfg)
    cfg = raw()
    del cfg["protocols"][0]["rounds"]
    with pytest.raises(ValueError, match="rounds"):
        resolve(cfg)
    for decoders in ([], ["missing"], ["temporal", "temporal"]):
        cfg = raw()
        cfg["protocols"][0]["decoders"] = decoders
        with pytest.raises(ValueError):
            resolve(cfg)
    cfg = raw()
    cfg["decoders"]["temporal"] = {"kind": "pymatching"}
    with pytest.raises(ValueError, match="temporal_gap"):
        resolve(cfg)
    for rule in ("target_errors", "time_budget"):
        cfg = raw()
        cfg["sampling"]["stop_rule"] = rule
        with pytest.raises(ValueError, match="fixed_shots"):
            resolve(cfg)
    cfg = raw()
    cfg["decoders"]["temporal"]["output_mode"] = "other"
    with pytest.raises(ValueError, match="output_mode"):
        resolve(cfg)


@pytest.mark.parametrize("addition", ["rounds: 4", "rounds: 3", "adaptive: true"])
def test_duplicate_preparation_yaml_keys_are_not_silently_overwritten(tmp_path, addition):
    path = tmp_path / "duplicate.yaml"
    text = TEMPLATE.read_text()
    text = text.replace("    rounds: 3", "    rounds: 3\n    " + addition)
    path.write_text(text)
    with pytest.raises(ValueError, match="duplicate"):
        load(path)


def test_unsafe_tags_and_nonfinite_yaml_are_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(TEMPLATE.read_text().replace("rounds: 3", "rounds: !!python/object/apply:os.system ['false']"))
    with pytest.raises(yaml.constructor.ConstructorError):
        load(path)
    path.write_text(TEMPLATE.read_text().replace("physical_error_rates: [0.001]", "physical_error_rates: [.nan]"))
    with pytest.raises(ValueError, match="physical_error_rates"):
        load(path)


def test_default_model_probability_domain_is_checked_before_building():
    cfg = raw()
    cfg["experiment"]["physical_error_rates"] = [.5]
    with pytest.raises(ValueError, match="default decoding_p"):
        resolve(cfg)
    cfg["protocols"][0]["decoding_p"] = .003
    assert next(grid(resolve(cfg)))["decoding_p"] == .003
    cfg["experiment"]["physical_error_rates"] = [2**2048]
    with pytest.raises(ValueError, match="physical_error_rates"):
        resolve(cfg)


def test_config_validation_never_constructs_physics_and_runner_fails_before_output(tmp_path, monkeypatch, capsys):
    from knill_bench.cli import main
    from knill_bench.codes import Code
    from knill_bench.simulation.runner import prepare
    monkeypatch.setattr(Code, "rotated", lambda *args: pytest.fail("validation must not construct circuits"))
    cfg = raw()
    cfg["experiment"]["output_root"] = str(tmp_path / "must_not_exist")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    assert main(["validate-config", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["resolved_grid"][0]["rounds"] == 3
    with pytest.raises(PreparationCapabilityError, match="prompt 04"):
        prepare(path)
    assert not (tmp_path / "must_not_exist").exists()


def test_legacy_resolved_config_and_grid_goldens_are_unchanged():
    # Computed using config.py at prompt-00 commit e3de069.
    cfg = load(Path(__file__).parents[1] / "configs/smoke.yaml")
    assert hashlib.sha256(canonical(cfg).encode()).hexdigest() == "b18095133ef63d3c315c612e0748bfda8caa607e3bdc38d8a3db31a6943cd072"
    assert hashlib.sha256(canonical(list(grid(cfg))).encode()).hexdigest() == "8815093f14af3939de1a25718e3c6dfdb159eaf80cfb63444d6a8918179d75a9"
