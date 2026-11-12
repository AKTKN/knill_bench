"""Parent-published point sidecars; the run complete marker commits the group."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from knill_bench.experiments.config_v2 import canonical


def relative_path(run, relative):
    """Accept one portable POSIX relative path and refuse symlink escapes."""
    if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative
            or "\0" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or any(p in {"", ".", ".."} for p in relative.split("/"))):
        raise ValueError("artifact path must be a safe POSIX relative path")
    root = Path(run).resolve()
    target = root
    for part in relative.split("/"):
        target = target / part
        if target.is_symlink():
            raise ValueError("artifact paths cannot contain symlinks")
    if not target.resolve().is_relative_to(root):
        raise ValueError("artifact path escapes run")
    return target


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


@dataclass(frozen=True)
class PointArtifacts:
    """Built by the parent, never returned through worker IPC.

    metadata must include converter export_metadata() in scientific phases:
    Stim's textual float formatting alone need not retain exact arguments.
    This contract deliberately performs no compilation or scientific decoding.
    """

    lstim_source: str
    stim_source: str
    metadata: dict
    logical_stabilizers: list | None = None


def publish_artifacts(run, point, artifacts):
    """Called only via the owning RunStore; all bytes fsync before renames."""
    import os

    if (not isinstance(artifacts, PointArtifacts) or not isinstance(artifacts.lstim_source, str)
            or not artifacts.lstim_source.strip() or not isinstance(artifacts.stim_source, str)
            or not artifacts.stim_source.strip() or not isinstance(artifacts.metadata, dict)):
        raise ValueError("converter artifacts require source strings and JSON metadata")
    if artifacts.logical_stabilizers is not None and (
            not point.optional_artifact_names or not isinstance(artifacts.logical_stabilizers, list)):
        raise ValueError("logical stabilizers are optional only for deep Clifford")
    contents = {"circuit.lstim": artifacts.lstim_source.encode("utf-8"),
                "circuit.stim": artifacts.stim_source.encode("utf-8")}
    if artifacts.logical_stabilizers is not None:
        contents["logical_stabilizers.json"] = canonical(artifacts.logical_stabilizers).encode("utf-8")
    meta = dict(artifact_schema="converter_point_v1", case_id=point.case_id,
                sampling_identity=point.sampling_identity, model=artifacts.metadata,
                content_sha256={n: hashlib.sha256(data).hexdigest() for n, data in contents.items()})
    contents["metadata.json"] = canonical(meta).encode("utf-8")
    paths = {n: relative_path(run, f"{point.directory}/{n}") for n in contents}
    if any(p.exists() or p.with_name("." + p.name + ".incomplete").exists() for p in paths.values()):
        raise FileExistsError("converter artifacts already exist; resume unfinished point first")
    staged, promoted = [], []
    try:
        for name, path in paths.items():
            temp = path.with_name("." + path.name + ".incomplete")
            staged.append(temp)
            with temp.open("xb") as output:
                output.write(contents[name])
                output.flush()
                os.fsync(output.fileno())
        for name, path in paths.items():
            os.replace(path.with_name("." + path.name + ".incomplete"), path)
            promoted.append(path)
    except BaseException:
        for path in staged + promoted:
            path.unlink(missing_ok=True)
        raise
    return {f"{point.directory}/{name}": hashlib.sha256(data).hexdigest() for name, data in contents.items()}


def registered_files(point, registry=None):
    required = {f"{point.directory}/{n}" for n in point.artifact_names}
    allowed = required | {f"{point.directory}/{n}" for n in point.optional_artifact_names}
    if registry is not None and (not isinstance(registry, dict) or not required <= registry.keys()
                                 or not registry.keys() <= allowed):
        raise ValueError("invalid converter artifact registration")
    optional = sorted(set(registry or ()) - required)
    return [*point.files, *optional]


def validate_artifacts(run, point, registry, *, execution=None):
    required = {f"{point.directory}/{n}" for n in point.artifact_names}
    allowed = required | {f"{point.directory}/{n}" for n in point.optional_artifact_names}
    if not isinstance(registry, dict) or not required <= registry.keys() or not registry.keys() <= allowed:
        raise ValueError("converter point is missing required artifact registration")
    for name, sha in registry.items():
        path = relative_path(run, name)
        if not path.is_file() or file_digest(path) != sha:
            raise ValueError("converter artifact content hash changed or is missing")
    meta = json.loads(relative_path(run, f"{point.directory}/metadata.json").read_text("utf-8"))
    expected = {PurePosixPath(name).name: sha for name, sha in registry.items() if not name.endswith("/metadata.json")}
    if (meta.get("artifact_schema") != "converter_point_v1" or meta.get("case_id") != point.case_id
            or meta.get("sampling_identity") != point.sampling_identity or meta.get("content_sha256") != expected):
        raise ValueError("converter point artifact identity changed")
    if point.kind == "converter_se_memory":
        from .metadata import validate_memory_artifacts
        validate_memory_artifacts(point, registry, meta.get("model"), execution)
    elif point.kind == "converter_knill_memory":
        from .metadata import validate_knill_artifacts
        validate_knill_artifacts(point, registry, meta.get("model"), execution)
    elif point.kind == "converter_deep_clifford" and execution is not None:
        from .deep_artifacts import validate_deep_model
        validate_deep_model(run, point, registry, scientific_execution=execution)


def validate_counts(run, point, shots, errors):
    """Bounded saved-data verification; no decoder or simulator construction."""
    import numpy as np
    import pyarrow.parquet as pq

    count = total = 0
    for batch in pq.ParquetFile(relative_path(run, point.filename("logical_error"))).iter_batches(batch_size=8192):
        ids, labels = (batch.column(i) for i in range(2))
        if (ids.null_count or labels.null_count
                or not np.array_equal(ids.to_numpy(), np.arange(count, count+len(batch), dtype=np.uint64))):
            raise ValueError("converter saved shot IDs/labels are invalid")
        count += len(batch)
        total += int(np.count_nonzero(labels.to_numpy(zero_copy_only=False)))
    if count != shots or total != errors:
        raise ValueError("converter saved shot/error counts changed")


def restart_artifacts(run, point):
    for name in (*point.artifact_names, *point.optional_artifact_names):
        path = relative_path(run, f"{point.directory}/{name}")
        path.unlink(missing_ok=True)
        path.with_name("." + path.name + ".incomplete").unlink(missing_ok=True)
