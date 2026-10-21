"""Compact actual imported-source provenance; no archives or environment dump."""

import hashlib
import importlib
from importlib import metadata
import inspect
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

HEX_REVISION = "8fa2200315cc4feaccf341a461f91739233de08a"


def _git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Git provenance unavailable for {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def source_info(module):
    path = Path(module.__file__).resolve()
    sha = hashlib.sha256()
    sources = (p for p in path.parent.rglob("*") if p.is_file() and p.suffix in {".py", ".mtx"})
    for source in sorted(sources):
        relative = str(source.relative_to(path.parent)).encode()
        data = source.read_bytes()
        sha.update(len(relative).to_bytes(8, "little") + relative)
        sha.update(len(data).to_bytes(8, "little") + data)
    source_hash = sha.hexdigest()
    manifest = path.parent / "_build_info.json"
    if manifest.exists():
        info = json.loads(manifest.read_text())
        if (info.get("format_version") != 1 or info.get("module") != module.__name__
                or not re.fullmatch(r"[0-9a-f]{40}", info.get("commit", ""))
                or info.get("source_sha256") != source_hash or type(info.get("dirty")) is not bool):
            raise RuntimeError(f"invalid wheel build provenance or changed Python/matrix resources: {manifest}")
        return dict(import_path=str(path), checkout=None, commit=info["commit"], branch=info.get("branch"),
                    dirty=info["dirty"], source_sha256=source_hash, install_kind="wheel",
                    origin_url=info.get("origin_url"), verified_ancestor=info.get("verified_ancestor"))
    root = Path(_git(path.parent, "rev-parse", "--show-toplevel"))
    # Do not mistake an untracked site-packages directory inside another Git
    # repository for the source checkout of the installed distribution.
    _git(root, "ls-files", "--error-unmatch", str(path.relative_to(root)))
    return dict(import_path=str(path), checkout=str(root), commit=_git(root, "rev-parse", "HEAD"),
                branch=_git(root, "branch", "--show-current"),
                dirty=bool(_git(root, "status", "--porcelain")), source_sha256=source_hash)


def validate_hex():
    """Require actual Knill-noise-lineage checkout and inspect the exported interfaces."""
    module = importlib.import_module("hex_qec")
    info = source_info(module)
    if info["checkout"] is None:
        valid = info["commit"] == HEX_REVISION and info.get("verified_ancestor") == HEX_REVISION
    else:
        valid = subprocess.run(["git", "-C", info["checkout"], "merge-base", "--is-ancestor",
                                HEX_REVISION, info["commit"]], capture_output=True).returncode == 0
    if not valid:
        raise RuntimeError(f"imported Hex must descend from HEX-K1 {HEX_REVISION}; got {info['commit']}")
    from hex_qec.protocols import FactoryCircuitBuilder, FactoryCircuitBundle, RotatedSurfaceCodeAdapter, knill_online_offline
    from hex_qec.modularisation import PreparationPlan, KnillNoiseModel
    from hex_qec.simulation import CompiledFactory, FactoryBatchResult
    from hex_qec.decoders import EffectivePriorBuilder, ProjectedDEMBuilder
    required = {
        FactoryCircuitBuilder: {"adapter", "preparation", "T_tel", "noise_model"},
        PreparationPlan: {"r_0", "r_plus"},
        KnillNoiseModel: {"name"},
        knill_online_offline: {"noise_model", "create_codecapacity_dem"},
        CompiledFactory.from_bundle: {"bundle", "seed", "create_codecapacity_dem"},
    }
    for function, names in required.items():
        if not names <= inspect.signature(function).parameters.keys():
            raise RuntimeError(f"imported Hex has an incompatible {function.__name__} interface")
    for name in ("sample_measurements", "decode", "decode_operational"):
        if not callable(getattr(CompiledFactory, name, None)):
            raise RuntimeError(f"imported Hex lacks CompiledFactory.{name}")
    # Import the remaining stable types above too; do not construct a physical
    # circuit, decoder, sampler or matching graph during infrastructure setup.
    info["required_revision"] = HEX_REVISION
    return info


def collect_environment():
    import knill_bench
    versions = {}
    for name in ("knill-bench", "hex-qec", "numpy", "scipy", "stim", "pymatching", "ldpc",
                 "PyYAML", "pyarrow", "networkx", "stimbposd"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return dict(python=sys.version, os=platform.platform(),
                cpu=dict(machine=platform.machine(), processor=platform.processor(), count=os.cpu_count()),
                dependencies=versions, bench=source_info(knill_bench), hex=validate_hex())
