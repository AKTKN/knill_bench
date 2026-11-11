"""Phase 2 named physical regimes and fixed d-round policy, no simulation."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from knill_bench.experiments.config_v2 import parse_config, load_config
from knill_bench.experiments.seeds import point_seed


def raw(regime="noisy_d_rounds", **options):
    config = dict(schema_version=2, kind="converter_knill_memory", noise="converter_uniform",
                  resource_preparation=regime, sweep=dict(d=[3, 5], p=[0., .001]), T_tel=2)
    config.update(options)
    return config


@pytest.mark.parametrize("regime", ["noisy_d_rounds", "ideal_post_se_depolarizing"])
def test_named_regimes_roundtrip_physical_settings_and_depth_independence(regime):
    c = parse_config(raw(regime))
    assert parse_config(c.as_dict()) == c
    assert c.post_rounds == 0
    assert c.input_preparation == ("ideal" if regime.startswith("ideal") else "noisy")
    for p in c.points():
        assert p.r_0 == p.r_plus == p.d and p.T_tel == 2
        assert p.p_st_multiplier == (1. if regime.startswith("ideal") else None)
        assert p.sampling_identity["program_contract"] == "converter_knill_program_v1"


@pytest.mark.parametrize("options", [dict(post_rounds=-1), dict(post_rounds=True), dict(post_rounds="d"),
    dict(r_0=1, r_plus=1), dict(r_0="2*d", r_plus="2*d"), dict(p_st_multiplier=1.),
    dict(input_preparation="ideal"), dict(resource_preparation="noisy"), dict(resource_preparation="ideal")])
def test_noisy_regime_rejects_unrequested_channels_depths_and_contradictory_policy(options):
    with pytest.raises(ValueError): parse_config(raw(**options))


@pytest.mark.parametrize("multiplier", [-1, float("inf"), float("nan"), True, "2", None, 1000])
def test_bad_post_se_multiplier_rejected_before_output(multiplier):
    with pytest.raises(ValueError): parse_config(raw("ideal_post_se_depolarizing", p_st_multiplier=multiplier))


def test_multiplier_validates_every_probability_and_only_bell_resource_channel_changes():
    a = parse_config(raw("ideal_post_se_depolarizing", p_st_multiplier=2., post_rounds=1))
    b = replace(a, p_st_multiplier=3.)
    assert next(a.points()).case_id != next(b.points()).case_id
    assert next(a.points()).p == next(b.points()).p  # Input post probability remains p.
    with pytest.raises(ValueError, match="every p"):
        parse_config(raw("ideal_post_se_depolarizing", p_st_multiplier=2., sweep=dict(d=[3], p=[.001,.5])))
    with pytest.raises(ValueError, match="input_preparation"):
        parse_config(raw("ideal_post_se_depolarizing", input_preparation="noisy"))


def test_all_new_physical_settings_enter_identity_but_execution_controls_do_not():
    c = parse_config(raw("ideal_post_se_depolarizing"))
    p = next(c.points())
    for update in (dict(post_rounds=1), dict(T_tel=3), dict(p_st_multiplier=2.)):
        other = next(replace(c, **update).points())
        assert p.case_id != other.case_id and point_seed(123,p) != point_seed(123,other)
    assert p == next(replace(c, shots=7, workers=2, batch_size=3, name="other").points())
    assert p.case_id != next(parse_config(raw()).points()).case_id


def test_se_and_deep_do_not_accept_knill_only_extensions():
    for kind in ("converter_se_memory", "converter_deep_clifford"):
        for field in ("post_rounds", "p_st_multiplier"):
            with pytest.raises(ValueError, match="unknown keys"):
                parse_config(dict(schema_version=2, kind=kind, noise="converter_uniform",
                                  sweep=dict(d=[3],p=[.001]), **{field:1}))


def test_existing_non_knill_converter_and_hex_configs_stay_unchanged():
    # Supplement the committed Hex golden fixture with explicit SE identity
    # independence from new dataclass fields; no new defaults enter old kinds.
    c = load_config(Path(__file__).resolve().parents[1]/"configs/converter_se_memory_v2_example.yaml").config
    point = next(c.points())
    assert c.config_hash == replace(c, post_rounds=1, p_st_multiplier=2.).config_hash
    assert point.case_id == replace(point, post_rounds=1, p_st_multiplier=2.).case_id
