"""Installed wheel provenance must preserve revision/resource checks without Git."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from knill_bench.experiments import provenance


def source_manifest(tmp_path):
    package = tmp_path / "example_package"
    package.mkdir()
    source = package / "__init__.py"
    source.write_text("value = 1\n")
    relative = b"__init__.py"
    data = source.read_bytes()
    digest = hashlib.sha256(len(relative).to_bytes(8, "little")+relative+
                            len(data).to_bytes(8, "little")+data).hexdigest()
    manifest = dict(format_version=1, module="example_package", commit="a"*40,
                    branch="auxiliary-system", dirty=False, source_sha256=digest,
                    origin_url="https://example.invalid/repository.git")
    (package / "_build_info.json").write_text(json.dumps(manifest))
    return SimpleNamespace(__name__="example_package", __file__=str(source)), manifest


def test_wheel_source_info_without_git(tmp_path, monkeypatch):
    module, manifest = source_manifest(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("wheel provenance must not need Git")
    monkeypatch.setattr(provenance, "_git", forbidden)
    info = provenance.source_info(module)
    assert info["checkout"] is None and info["install_kind"] == "wheel"
    assert info["commit"] == manifest["commit"] and info["source_sha256"] == manifest["source_sha256"]


@pytest.mark.parametrize("change", ["python", "matrix"])
def test_wheel_rejects_changed_or_missing_scientific_resources(tmp_path, change):
    module, _ = source_manifest(tmp_path)
    from pathlib import Path
    root = Path(module.__file__).parent
    if change == "python":
        Path(module.__file__).write_text("value = 2\n")
    else:
        (root / "checks.mtx").write_text("a changed matrix resource")
    with pytest.raises(RuntimeError, match="changed Python/matrix"):
        provenance.source_info(module)


def test_installed_hex_still_requires_pinned_hex_n2_provenance(monkeypatch):
    info = dict(checkout=None, commit=provenance.HEX_REVISION,
                verified_ancestor=provenance.HEX_REVISION, install_kind="wheel")
    monkeypatch.setattr(provenance, "source_info", lambda module: info.copy())
    assert provenance.validate_hex()["required_revision"] == provenance.HEX_REVISION
    info["commit"] = "a"*40
    with pytest.raises(RuntimeError, match="must descend from HEX-N2"):
        provenance.validate_hex()
