"""Phase 3 CLI/manifest/export integrity; never sample noisy deep circuits."""

import hashlib
import json
from pathlib import Path

import pytest
import stim
import yaml

from knill_bench.converter.artifacts import file_digest
from knill_bench.converter.deep_artifacts import validate_deep_artifacts
from knill_bench.converter.generation import compile_config
from knill_bench.converter.se_memory import exact_stim_text
from knill_bench.experiments.cli import main
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.config_v2 import digest
from knill_bench.experiments.dispatcher import dispatch, resume


def document(tmp_path,**updates):
    raw = dict(schema_version=2,kind="converter_deep_clifford",noise="converter_uniform",
        name="deep_test",sweep=dict(d=[3],p=[.001]),depth=1,circuit_seed=19,
        output_root=str(tmp_path/"artifacts"),workers=2,shots=3)
    raw.update(updates)
    path = tmp_path/"input.yaml";path.write_text("# retain exact Phase 3 input\n"+yaml.safe_dump(raw))
    return load_config(path)


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("deep_artifact")
    doc = document(tmp)
    path = compile_config(doc)
    return path,doc


def test_compile_cli_exports_probe_and_signed_state_without_sampling_or_decoder(tmp_path,monkeypatch,capsys):
    import logical_to_stim_converter.decoding as api
    import pymatching
    doc = document(tmp_path,resource_preparation="ideal",p_st_multiplier=2.)
    def forbidden(*args,**kwargs):raise AssertionError("Phase 3 attempted sampling or decoder construction")
    monkeypatch.setattr(stim.Circuit,"compile_sampler",forbidden)
    monkeypatch.setattr(stim.Circuit,"compile_detector_sampler",forbidden)
    monkeypatch.setattr(api,"make_stage_requests",forbidden)
    monkeypatch.setattr(pymatching.Matching,"__init__",forbidden)
    assert main(["compile",str(doc.source_path),"--workers","1"]) == 0
    path = Path(capsys.readouterr().out.strip())
    meta = json.loads((path/"metadata.json").read_text())
    assert meta["artifact_schema"] == "converter_generation_v1" and meta["status"] == "generated"
    assert meta["purpose"] == "circuit_generation_only" and meta["decoder_status"] == "not_constructed_generation_only"
    assert meta["config"]["workers"] == 1 and b"original input SHA256" in (path/"config.yaml").read_bytes()
    assert not list(path.rglob("*.parquet"))
    assert "logical_errors" not in json.dumps(meta)
    assert "hex" not in meta["environment"]
    assert meta["environment"]["converter"]["commit"] == "457dc519adec6a11b38843a03e1c8fbbd6495f5a"


def test_exact_native_probe_artifacts_full_gate_sequence_and_physical_support(generated):
    path,doc = generated
    assert (path/"config.yaml").read_bytes() == doc.contents
    meta = json.loads((path/"metadata.json").read_text())
    point = next(doc.config.points());entry = meta["points"][point.case_id]
    assert entry["status"] == "generated" and entry["sampling_identity"] == point.sampling_identity
    assert len(entry["files"]) == 4 and set(entry["files"]) == set(entry["artifacts"])
    model = validate_deep_artifacts(path,point,entry["artifacts"])
    for relative,sha in entry["artifacts"].items():assert file_digest(path/relative) == sha
    sampled = stim.Circuit((path/point.directory/"circuit.stim").read_text())
    original = stim.Circuit()
    for inst in model["converter_export"]["selected_instructions"]:
        original.append(inst["name"],[stim.GateTarget(t) for t in inst["targets"]],inst["arguments"],tag=inst["tag"])
    assert sampled[:len(original)] == original
    assert sampled.num_measurements == original.num_measurements+4
    assert sampled[len(original):][0].name == "MPP"
    assert exact_stim_text(sampled) == (path/point.directory/"circuit.stim").read_text()
    assert model["terminal_probe"]["measurement_indices"] == list(range(original.num_measurements,sampled.num_measurements))
    definitions = json.loads((path/point.directory/"logical_stabilizers.json").read_text())
    assert definitions == model["converter_export"]["logical_output_stabilizers"]
    assert len(model["logical_circuit"]["layers"]) == 1
    assert all(key in model["logical_circuit"] for key in ("generator","rng_convention","single_qubit_probabilities"))
    assert entry["model"] == model["execution"]


def test_generation_bundle_cannot_resume_as_scientific_data(generated):
    path,_ = generated
    before = {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError,match="generation-only"):resume(path)
    after = {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob("*") if p.is_file()}
    assert before == after


def test_compile_rejects_other_kinds_before_creating_output(tmp_path):
    for kind in ("converter_se_memory","converter_knill_memory","se_memory"):
        raw = dict(schema_version=2,kind=kind,noise="converter_uniform" if kind.startswith("converter") else "hex_uniform",
            sweep=dict(d=[3],p=[.001]),output_root=str(tmp_path/"absent"))
        path=tmp_path/"other.yaml";path.write_text(yaml.safe_dump(raw))
        with pytest.raises(ValueError,match="generation only"):compile_config(load_config(path))
    assert not (tmp_path/"absent").exists()


def test_corrupt_probe_or_stabilizer_artifact_is_rejected(generated,tmp_path):
    import shutil
    path,doc = generated;target=tmp_path/"copy";shutil.copytree(path,target)
    point=next(doc.config.points())
    meta=json.loads((target/"metadata.json").read_text())
    registry=meta["points"][point.case_id]["artifacts"]
    (target/point.directory/"logical_stabilizers.json").write_text("[]")
    with pytest.raises(ValueError,match="content hash"):
        validate_deep_artifacts(target,point,registry)


@pytest.mark.parametrize("change",["prefix","indices","sequence","fingerprint"])
def test_model_linkage_rejects_changed_probe_sequence_and_source(generated,tmp_path,change):
    import shutil
    path,doc = generated;target=tmp_path/"copy";shutil.copytree(path,target)
    point=next(doc.config.points())
    meta=json.loads((target/"metadata.json").read_text())
    registry=meta["points"][point.case_id]["artifacts"]
    relative=f"{point.directory}/metadata.json";sidecar=target/relative
    content=json.loads(sidecar.read_text());model=content["model"]
    if change == "prefix":model["execution"]["original_measurement_count"] += 4
    if change == "indices":
        model["terminal_probe"]["measurement_indices"][0] -= 1
        model["execution"]["terminal_probe_sha256"] = digest(model["terminal_probe"])
    if change == "sequence":model["logical_circuit"]["layers"][0]["single_qubit"][0] = "Y"
    if change == "fingerprint":model["converter_export"]["source_fingerprint"] = "0"*64
    sidecar.write_text(json.dumps(content));registry[relative] = file_digest(sidecar)
    with pytest.raises(ValueError,match="identity|prefix"):
        validate_deep_artifacts(target,point,registry)


def test_failed_compilation_is_never_marked_generated(tmp_path,monkeypatch):
    from knill_bench.converter import deep_clifford
    doc=document(tmp_path)
    def broken(*args,**kwargs):raise ValueError("injected physical compile failure")
    monkeypatch.setattr(deep_clifford.CompiledDeepClifford,"__init__",broken)
    with pytest.raises(ValueError,match="injected"):compile_config(doc)
    path,=(tmp_path/"artifacts").iterdir()
    meta=json.loads((path/"metadata.json").read_text())
    assert meta["status"] == "failed" and meta["points"] == {}
    assert not list(path.rglob("*.parquet"))
