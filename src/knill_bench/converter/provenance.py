"""Exact installed VCS identities and resource verification for converter runs."""

import base64
import hashlib
import importlib
from importlib import metadata
import json
from pathlib import Path

CONVERTER_REVISION = "457dc519adec6a11b38843a03e1c8fbbd6495f5a"
STIMFLOW_REVISION = "ffe0d043598ed5df0851a3e6b4920359a23fafbd"
CONVERTER_URL = "https://github.com/AKTKN/logical_to_stim_converter.git"
STIMFLOW_URL = "https://github.com/quantumlib/Stim.git"
RESOURCE_SUFFIXES = {".py", ".lark"}


def resource_hash(files):
    """Portable, length-delimited package identity (includes the LSTIM grammar)."""
    sha = hashlib.sha256()
    for relative, data in sorted(files):
        name = relative.encode("utf-8")
        sha.update(len(name).to_bytes(8, "little") + name)
        sha.update(len(data).to_bytes(8, "little") + data)
    return sha.hexdigest()


def installed_source(distribution, module_name, revision, url, *, subdirectory=None):
    try:
        dist = metadata.distribution(distribution)
        module = importlib.import_module(module_name)
    except (metadata.PackageNotFoundError, ImportError) as error:
        raise RuntimeError("Converter support requires installation from requirements-converter.lock") from error
    root = Path(module.__file__).resolve().parent
    resources = {p.relative_to(root).as_posix(): p for p in root.rglob("*")
                 if p.is_file() and p.suffix in RESOURCE_SUFFIXES}
    source_hash = resource_hash((name, p.read_bytes()) for name, p in resources.items())
    manifest = root / "_build_info.json"
    if manifest.is_file():
        info = json.loads(manifest.read_text())
        if (info.get("format_version") != 1 or info.get("module") != module_name
                or info.get("commit") != revision or info.get("origin_url") != url
                or info.get("subdirectory") != subdirectory
                or info.get("source_sha256") != source_hash or info.get("dirty") is not False):
            raise RuntimeError(f"changed or unverified {distribution} wheel source/resources")
        install_kind = "bundle_wheel"
    else:
        direct = json.loads(dist.read_text("direct_url.json") or "{}")
        if (direct.get("url") != url or direct.get("vcs_info", {}).get("commit_id") != revision
                or direct.get("vcs_info", {}).get("vcs") != "git"
                or direct.get("subdirectory") != subdirectory):
            raise RuntimeError(f"{distribution} must be installed from exact Git revision {revision}")
        # A direct_url records origin; RECORD additionally detects changed/missing
        # installed scientific files and grammar. No source checkout is required.
        recorded = {}
        for entry in dist.files or ():
            path = Path(dist.locate_file(entry)).resolve()
            if path.is_relative_to(root) and path.suffix in RESOURCE_SUFFIXES:
                recorded[path.relative_to(root).as_posix()] = entry
        if set(recorded) != set(resources):
            raise RuntimeError(f"changed or missing {distribution} installed resources")
        for name, entry in recorded.items():
            digest = entry.hash
            actual = base64.urlsafe_b64encode(hashlib.sha256(resources[name].read_bytes()).digest()).rstrip(b"=").decode()
            if digest is None or digest.mode != "sha256" or digest.value != actual:
                raise RuntimeError(f"changed {distribution} installed resource: {name}")
        install_kind = "vcs_wheel"
    return dict(commit=revision, required_revision=revision, origin_url=url, subdirectory=subdirectory,
                import_path=str(root), source_sha256=source_hash, install_kind=install_kind,
                version=dist.version, dirty=False)


def validate_converter():
    """Use only exported APIs; never build/sample a scientific model here."""
    converter = installed_source("logical-to-stim-converter", "logical_to_stim_converter",
                                 CONVERTER_REVISION, CONVERTER_URL)
    flow = installed_source("stimflow", "stimflow", STIMFLOW_REVISION, STIMFLOW_URL,
                            subdirectory="glue/stimflow")
    import logical_to_stim_converter as api
    from logical_to_stim_converter import decoding
    required = ("parse_logical_circuit", "NoiseModel", "ResourcePreparationNoise", "PostInitializationNoise",
                "KnillEC", "LogicalPauli", "TerminalObservableProbe")
    if (any(not callable(getattr(api, n, None)) for n in required)
            or not callable(getattr(decoding, "make_stage_requests", None))
            or not hasattr(api.CompiledCircuit, "logical_output_stabilizers")
            or any(not callable(getattr(api.CompiledCircuit, n, None)) for n in (
                "make_frame_plan", "make_terminal_observable_probe", "export_metadata"))
            or not callable(getattr(api.NoiseModel, "uniform_depolarizing", None))):
        raise RuntimeError("installed converter lacks the required public Phase 0 API")
    for name, expected in (("stim", "1.16.0"), ("pymatching", "2.4.0")):
        if metadata.version(name) != expected:
            raise RuntimeError(f"converter integration requires {name}=={expected}; no downgrade is supported")
    return converter, flow
