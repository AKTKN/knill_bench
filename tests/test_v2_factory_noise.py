"""BENCH-N1: factory-only custom noise schema, identities and early rejection."""

from dataclasses import FrozenInstanceError, replace
import pickle
from pathlib import Path

import pytest
import yaml

from hex_qec.circuit_generation import FactoryNoiseModel
from knill_bench.experiments import dispatcher
from knill_bench.experiments.config_v2 import ExperimentPoint, load_config, parse_config
from knill_bench.experiments.noise_v2 import CUSTOM_KIND_ERROR
from knill_bench.experiments.seeds import chunk_seed, point_seed


def custom_noise():
    return dict(model="custom", multipliers=dict(one_qubit=.1,two_qubit=1.,idle=.2,measurement=2.,reset=1.),
                idle_windows=dict(post_cnot_control=dict(duration=2.,rate_multiplier=5.),
                    during_plus_preparation=dict(enabled=True,se_round_duration=1.,rate_multiplier=1.)))


def raw_config(**updates):
    raw=dict(schema_version=2,kind="logical_zero_factory",name="custom_test",noise=custom_noise(),
             sweep=dict(d=[3,5],p=[.001,.003]),r_0="d",r_plus="d",T_tel=2,
             theta=None,create_codecapacity_dem=False,decoder="mwpm",shots=7,
             batch_size="auto",workers=1,master_seed=12345)
    return dict(raw,**updates)


def test_native_frozen_noise_parse_roundtrip_and_short_filenames(tmp_path):
    raw=raw_config()
    cfg=parse_config(raw)
    assert cfg.noise == "custom" and isinstance(cfg.noise_model,FactoryNoiseModel)
    assert cfg.noise_model.one_qubit == .1 and cfg.noise_model.idle == .2
    assert cfg.noise_model.post_cnot_control.duration == 2
    assert cfg.noise_model.during_plus_preparation.enabled
    assert parse_config(cfg.as_dict()) == cfg
    assert cfg.as_dict()["noise"] == raw["noise"]
    assert "noise_model" not in cfg.as_dict()
    points=list(cfg.points())
    assert len(points)==4
    assert [p.r_plus for p in points]==[3,3,5,5]
    assert all(p.noise_model is cfg.noise_model for p in points)
    assert pickle.loads(pickle.dumps(points[0]))==points[0]
    assert "noisemodel=custom,T=2,r_0=3,r_+=3.parquet" in points[0].filename("logical_gaps")
    assert "multipliers" not in points[0].filename("logical_error")
    with pytest.raises(FrozenInstanceError):
        cfg.noise_model.reset=2
    path=tmp_path/"custom.yaml"
    contents=("# Preserve original bytes\n"+yaml.safe_dump(raw)).encode()
    path.write_bytes(contents)
    document=load_config(path)
    assert document.contents == contents
    assert document.config==cfg
    override=load_config(path,workers=2)
    assert override.config.noise_model==cfg.noise_model and path.read_bytes()==contents


def test_custom_defaults_are_explicitly_canonical():
    cfg=parse_config(raw_config(noise=dict(model="custom")))
    assert cfg.noise_model==FactoryNoiseModel()
    assert cfg.as_dict()["noise"]["idle_windows"]["post_cnot_control"]["duration"]==0
    assert parse_config(cfg.as_dict()).config_hash==cfg.config_hash


@pytest.mark.parametrize("path,value", [
    (("noise",),"custom"), (("noise",),None), (("noise",),[]),
    (("noise",),{}), (("noise","model"),"other"),
    (("noise","additional_wait"),2), (("noise","multipliers"),None),
    (("noise","multipliers","bogus"),1), (("noise","multipliers","idle"),-.1),
    (("noise","multipliers","one_qubit"),True), (("noise","multipliers","reset"),"1"),
    (("noise","multipliers","measurement"),float("inf")),
    (("noise","multipliers","two_qubit"),float("nan")),
    (("noise","idle_windows"),[]), (("noise","idle_windows","additional_wait"),1),
    (("noise","idle_windows","post_cnot_control"),3),
    (("noise","idle_windows","post_cnot_control","duration"),"d"),
    (("noise","idle_windows","post_cnot_control","duration"),"2*d"),
    (("noise","idle_windows","post_cnot_control","duration"),-1),
    (("noise","idle_windows","post_cnot_control","rate_multiplier"),False),
    (("noise","idle_windows","during_plus_preparation","enabled"),1),
    (("noise","idle_windows","during_plus_preparation","enabled"),"true"),
    (("noise","idle_windows","during_plus_preparation","se_round_duration"),"d"),
    (("noise","idle_windows","during_plus_preparation","se_round_duration"),float("inf")),
    (("noise","idle_windows","during_plus_preparation","rate_multiplier"),-1),
    (("noise","idle_windows","during_plus_preparation","duration"),2),
])
def test_unknown_or_malformed_noise_fails_before_output(tmp_path,path,value):
    raw=raw_config(output_root=str(tmp_path/"runs"))
    dest=raw
    for part in path[:-1]: dest=dest[part]
    dest[path[-1]]=value
    file=tmp_path/"bad.yaml"
    file.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError): dispatcher.dispatch(file)
    assert not (tmp_path/"runs").exists()


@pytest.mark.parametrize("kind", ["fig4d_reproduction","se_memory"])
def test_other_protocols_custom_noise_raise_explicit_error_before_output(tmp_path,kind):
    raw=raw_config(kind=kind,output_root=str(tmp_path/"runs"))
    file=tmp_path/"unsupported.yaml"
    file.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError) as exc:dispatcher.dispatch(file)
    assert str(exc.value)==CUSTOM_KIND_ERROR
    assert not (tmp_path/"runs").exists()
    config=parse_config(raw_config())
    with pytest.raises(ValueError,match="supported only"):
        replace(config,kind=kind)
    with pytest.raises(ValueError,match="supported only"):
        replace(next(config.points()),kind=kind)


@pytest.mark.parametrize("which", ["operation","post","prep","overflow"])
def test_all_probabilities_and_resolved_durations_validated_before_output(tmp_path,which):
    raw=raw_config(output_root=str(tmp_path/"runs"),sweep=dict(d=[3,5],p=[.001,.5]))
    noise=raw["noise"]
    if which=="operation":noise["multipliers"]["reset"]=3
    if which in {"post","prep"}:
        noise["multipliers"]["measurement"]=1
        noise["multipliers"]["idle"]=2
        for window in noise["idle_windows"].values():window["rate_multiplier"]=1
        if which=="post":noise["idle_windows"]["post_cnot_control"]["duration"]=.5
        else:noise["idle_windows"]["during_plus_preparation"]["se_round_duration"]=.5
    if which=="overflow":noise["idle_windows"]["during_plus_preparation"]["se_round_duration"]=1e308
    file=tmp_path/"bad.yaml";file.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):load_config(file)
    assert not (tmp_path/"runs").exists()


def test_duplicate_keys_rejected_at_every_noise_nesting(tmp_path):
    for text in ("noise: {model: custom, model: custom}",
                 "noise: {model: custom, multipliers: {idle: 1, idle: 2}}",
                 "noise: {model: custom, idle_windows: {post_cnot_control: {duration: 1, duration: 2}}}"):
        path=tmp_path/"duplicate.yaml"
        path.write_text("schema_version: 2\nkind: logical_zero_factory\nsweep: {d: [3], p: [0.001]}\n"+text)
        with pytest.raises(ValueError,match="unique"):load_config(path)


def test_noise_parameters_change_config_physical_identity_and_seeds_only_when_physical():
    base=parse_config(raw_config())
    point=next(base.points())
    paths=[("multipliers",field) for field in ("one_qubit","two_qubit","idle","measurement","reset")]
    for path in paths:
        raw=raw_config();raw["noise"][path[0]][path[1]]*=1.5
        changed=parse_config(raw);other=next(changed.points())
        assert base.config_hash!=changed.config_hash and point.case_id!=other.case_id
        assert point_seed(base.master_seed,point)!=point_seed(base.master_seed,other)
    for window,field in (("post_cnot_control","duration"),("post_cnot_control","rate_multiplier"),
                         ("during_plus_preparation","se_round_duration"),("during_plus_preparation","rate_multiplier"),
                         ("during_plus_preparation","enabled")):
        raw=raw_config();value=raw["noise"]["idle_windows"][window][field]
        raw["noise"]["idle_windows"][window][field]=False if field=="enabled" else value*2
        changed=parse_config(raw)
        assert changed.config_hash!=base.config_hash
        assert next(changed.points()).case_id!=point.case_id
    options=replace(base,theta=4.,create_codecapacity_dem=True,workers=2,shots=3)
    assert next(options.points())==point and options.config_hash!=base.config_hash
    assert chunk_seed(12345,point,3)==chunk_seed(12345,next(options.points()),3)
    assert "noise" not in base.as_dict()["sweep"]


@pytest.mark.parametrize("kind,cfg_hash,case_id,seed", [
    ("logical_zero_factory","6368fba3d4d9decc575aa35c02db30148e19ee1d126e93b4bd5c0eb0ec869c71",
     "6a9ac3a46e5cab8a66a4459bb92eed630cd4765c7896106d4a3bed3f74c26558",14440836524900115690),
    ("fig4d_reproduction","84ee41763b9fdd4bfe50f2b375a6eb5924cf28b18b4086d12c1518bc043aac5c",
     "81ff41b1cc35c4a698b8412b0f6915683e4dc3eb4b57a1773447f2fd2416966a",14779664108244039017),
    ("se_memory","51267b999103db297a0a5c8ea74a893a05432d3318d8506f1f02966e8090911a",
     "271136aa395d7e1c09814857e6730ee23bef48e0bae1d9cf36118811a107b76b",16050205909297673157),
])
def test_uniform_config_hashes_physical_ids_and_seeds_unchanged(kind,cfg_hash,case_id,seed):
    cfg=parse_config(dict(schema_version=2,kind=kind,sweep=dict(d=[3],p=[.001]),batch_size=3))
    point=next(cfg.points())
    assert cfg.config_hash==cfg_hash and point.case_id==case_id
    assert point_seed(cfg.master_seed,point)==seed
    assert "noise_model" not in cfg.as_dict() and "noise_model" not in point.sampling_identity


def test_custom_example_parses_without_building_circuits():
    root=Path(__file__).resolve().parents[1]
    cfg=load_config(root/"configs/templates/logical_zero_factory_custom_noise.yaml").config
    assert cfg.noise=="custom" and cfg.shots==7
