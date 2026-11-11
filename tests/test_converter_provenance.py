"""Installed public API/Stim compatibility; no scientific LER execution."""

import base64
import hashlib
import importlib.util
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import numpy as np
import pytest
import yaml

from knill_bench.converter import provenance
from knill_bench.converter.models import DecodedBatch
from knill_bench.experiments import dispatcher
from knill_bench.experiments.config_v2 import CONVERTER_KINDS, load_config
from knill_bench.experiments.provenance import collect_environment

ROOT = Path(__file__).resolve().parents[1]


def test_exact_installed_converter_stimflow_and_public_api():
    converter, flow = provenance.validate_converter()
    assert converter["commit"] == provenance.CONVERTER_REVISION
    assert flow["commit"] == provenance.STIMFLOW_REVISION
    assert converter["install_kind"] in {"vcs_wheel", "bundle_wheel"}
    assert metadata.version("stim") == "1.16.0" and metadata.version("pymatching") == "2.4.0"
    env = collect_environment("converter_se_memory")
    assert "hex" not in env and env["converter"] == converter and env["stimflow"] == flow


def test_public_compiler_works_with_pinned_stim_without_sampling():
    from logical_to_stim_converter import NoiseModel, parse_logical_circuit
    from logical_to_stim_converter.decoding import make_stage_requests
    source = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND Q0 P0
INIT_Z[initial](1) Q0
SE(1) Q0
MZ Q0
"""
    compiled = parse_logical_circuit(source).compile(noise_model=NoiseModel.uniform_depolarizing(.001))
    compiled.validate_metadata()
    assert compiled.circuit.detector_error_model().num_observables == 1
    assert compiled.export_metadata()["schema"] == "compiled-metadata-v1"
    assert compiled.make_frame_plan() is not None
    assert make_stage_requests(compiled) is not None


def test_wrong_installed_revision_rejected(monkeypatch):
    original = provenance.metadata.distribution
    def fake(name):
        dist = original(name)
        if name != "logical-to-stim-converter": return dist
        return SimpleNamespace(version=dist.version, files=dist.files, locate_file=dist.locate_file,
            read_text=lambda key: json.dumps(dict(url=provenance.CONVERTER_URL,
                vcs_info=dict(commit_id="f"*40, vcs="git"))) if key == "direct_url.json" else dist.read_text(key))
    monkeypatch.setattr(provenance.metadata, "distribution", fake)
    with pytest.raises(RuntimeError, match="exact Git revision"):
        provenance.validate_converter()


def test_missing_public_api_rejected(monkeypatch):
    import logical_to_stim_converter as api
    monkeypatch.setattr(api.CompiledCircuit, "make_frame_plan", None)
    # Contract validation must require callable methods, not just attribute names.
    with pytest.raises(RuntimeError, match="public Phase 0 API"):
        provenance.validate_converter()


def test_fake_installed_wheel_checks_resources_and_grammar(tmp_path, monkeypatch):
    package = tmp_path / "fake_converter"
    package.mkdir()
    (package / "__init__.py").write_text("value = 1\n")
    (package / "grammar.lark").write_text('start: "test"\n')
    module = SimpleNamespace(__file__=str(package / "__init__.py"))
    entries = []
    for path in package.iterdir():
        digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=").decode()
        entries.append(SimpleNamespace(path=path, hash=SimpleNamespace(mode="sha256", value=digest)))
    direct = dict(url="https://example.invalid/repo.git", vcs_info=dict(vcs="git", commit_id="a"*40))
    dist = SimpleNamespace(files=entries, locate_file=lambda e: e.path, version="1",
                           read_text=lambda n: json.dumps(direct))
    monkeypatch.setattr(provenance.metadata, "distribution", lambda n: dist)
    monkeypatch.setattr(provenance.importlib, "import_module", lambda n: module)
    info = provenance.installed_source("fake", "fake_converter", "a"*40, direct["url"])
    assert info["source_sha256"]
    (package / "grammar.lark").write_text("changed")
    with pytest.raises(RuntimeError, match="changed.*resource"):
        provenance.installed_source("fake", "fake_converter", "a"*40, direct["url"])
    (package / "grammar.lark").unlink()
    with pytest.raises(RuntimeError, match="missing.*resources"):
        provenance.installed_source("fake", "fake_converter", "a"*40, direct["url"])


@pytest.mark.parametrize("kind", sorted(CONVERTER_KINDS))
def test_dispatch_and_resume_refuse_unimplemented_runners_before_output(tmp_path, kind):
    source = tmp_path / "input.yaml"
    source.write_text(yaml.safe_dump(dict(schema_version=2, kind=kind, noise="converter_uniform",
        sweep=dict(d=[3], p=[.001]), output_root=str(tmp_path / "outputs"), shots=3)))
    with pytest.raises(NotImplementedError, match="scientific runner is not implemented"):
        dispatcher.dispatch(source)
    assert not (tmp_path / "outputs").exists()
    from knill_bench.experiments.run_v2 import RunStore
    with RunStore.create(load_config(source)) as store:
        run = store.path
        assert store.metadata["status"] == "running"
    before = (run / "metadata.json").read_bytes()
    with pytest.raises(NotImplementedError, match="scientific runner is not implemented"):
        dispatcher.resume(run)
    assert (run / "metadata.json").read_bytes() == before


def test_hex_run_has_no_converter_import_even_if_backend_unavailable(tmp_path):
    script = '''
import sys, importlib.abc
class BlockConverter(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"logical_to_stim_converter", "stimflow"}:
            raise AssertionError("Hex path imported optional converter")
sys.meta_path.insert(0, BlockConverter())
from knill_bench.experiments.config_v2 import parse_config
from knill_bench.experiments.dispatcher import dispatch
from pathlib import Path
import yaml
root = Path(sys.argv[1])
path = root / "hex.yaml"
path.write_text(yaml.safe_dump(dict(schema_version=2,kind="se_memory",shots=3,batch_size=3,
    rounds=1,sweep=dict(d=[3],p=[.001]),output_root=str(root/"runs"))))
result = dispatch(path)
assert (result / "metadata.json").is_file()
# Parsing converter config itself also does not import the optional backend.
parse_config(dict(schema_version=2,kind="converter_se_memory",noise="converter_uniform",
    sweep=dict(d=[3],p=[.001])))
assert "logical_to_stim_converter" not in sys.modules and "stimflow" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_decode_contract_rejects_nonboolean_or_multidimensional_labels():
    assert DecodedBatch(np.zeros(3, dtype=bool)).logical_error.shape == (3,)
    for value in ([False], np.zeros(3), np.zeros((3, 1), dtype=bool)):
        with pytest.raises(ValueError): DecodedBatch(value)


def test_cluster_converter_wheel_manifest_and_record(tmp_path):
    spec = importlib.util.spec_from_file_location("bundle_builder", ROOT / "scripts/build_cluster_bundle.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    wheel = tmp_path / "logical_to_stim_converter-0.0.1-py3-none-any.whl"
    files = {"logical_to_stim_converter/__init__.py": b"value=1\n",
             "logical_to_stim_converter/language/grammar.lark": b'start: "test"',
             "logical_to_stim_converter-0.0.1.dist-info/RECORD": b""}
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in files.items(): archive.writestr(name, data)
    info = builder.tag_vcs_wheel(wheel, "logical_to_stim_converter", provenance.CONVERTER_REVISION,
                                 provenance.CONVERTER_URL)
    with zipfile.ZipFile(wheel) as archive:
        import csv, io
        rows = list(csv.reader(io.StringIO(archive.read("logical_to_stim_converter-0.0.1.dist-info/RECORD").decode())))
        for name, digest, size in rows:
            if not digest: continue
            actual = base64.urlsafe_b64encode(hashlib.sha256(archive.read(name)).digest()).rstrip(b"=").decode()
            assert digest == "sha256=" + actual and int(size) == len(archive.read(name))
        manifest = json.loads(archive.read("logical_to_stim_converter/_build_info.json"))
        assert manifest["source_sha256"] == info["source_sha256"]
        archive.extractall(tmp_path / "installed")
    module = SimpleNamespace(__file__=str(tmp_path / "installed/logical_to_stim_converter/__init__.py"))
    from unittest.mock import patch
    with patch.object(provenance.importlib, "import_module", return_value=module), \
            patch.object(provenance.metadata, "distribution", return_value=SimpleNamespace(version="0.0.1")):
        assert provenance.installed_source("fake", "logical_to_stim_converter", provenance.CONVERTER_REVISION,
                                           provenance.CONVERTER_URL)["install_kind"] == "bundle_wheel"


def test_converter_sources_import_no_private_dependency_modules():
    import ast
    for path in (ROOT / "src/knill_bench/converter").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([node.module] if isinstance(node, ast.ImportFrom) else
                     [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if name and name.startswith("logical_to_stim_converter"):
                    assert all(not part.startswith("_") for part in name.split(".")), (path, name)
