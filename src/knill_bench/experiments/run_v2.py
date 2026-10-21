"""Parent-owned compact run metadata and clean restart of unfinished points."""

import copy
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import time

from knill_bench.data.storage_v2 import (
    PointResult, acquire_lock, atomic_json, clear_stale_lock,
    restart_incomplete_point, validate_point_files,
)
from .config_v2 import ConfigDocument, load_saved_config, LOCAL_PRIOR_APPROXIMATION
from .provenance import collect_environment
from .seeds import SEED_DERIVATION, point_seed
from .noise_v2 import validate_noise_execution


RUN_TIMEZONE = timezone(timedelta(hours=9), "Asia/Tokyo")


def utc_now():
    return datetime.now(timezone.utc)


def _compatibility(environment):
    return {"python": environment["python"], "os": environment["os"],
            "dependencies": environment["dependencies"],
            **{name: {key: environment[name][key] for key in ("commit", "source_sha256")}
               for name in ("bench", "hex")}}


class RunStore:
    """A single parent owns metadata; the scheduler assigns point-writer ownership.

    create/prepare never simulate. Point runners own physical execution.
    Metadata 'complete' for a point is its publication marker. A context exit
    releases ownership; callers explicitly finish after all points complete.
    """

    @classmethod
    def create(cls, document: ConfigDocument):
        env = collect_environment()  # Validate actual imported Hex before output.
        config = document.config
        root = Path(config.output_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        instant = utc_now().astimezone(RUN_TIMEZONE)
        suffix = f"{config.config_hash[:8]}_{config.name}"
        while True:
            path = root / f"{instant.strftime('%Y%m%d%H%M%S')}_{suffix}"
            try:
                path.mkdir()
                break
            except FileExistsError:
                # Reserve a fresh directory even for identical configs in one
                # second, preserving the requested format without reuse.
                instant += timedelta(seconds=1)
        try:
            with (path / "config.yaml").open("xb") as output:
                output.write(document.contents)
                output.flush()
                os.fsync(output.fileno())
            store = cls(path, document)
            store._metadata = dict(
                schema_version=2, kind=config.kind, name=config.name,
                started_at=utc_now().isoformat(), ended_at=None, status="running",
                wall_seconds=0., resume_count=0,
                config_hash=config.config_hash, input_sha256=document.input_hash,
                config=config.as_dict(), environment=env,
                master_seed=config.master_seed, seed_derivation=SEED_DERIVATION,
                prior_policy=config.prior_policy,
                final_readout=next(config.points()).final_readout,
                gap_units=config.gap_units,
                projected_approximation=(LOCAL_PRIOR_APPROXIMATION
                                         if config.create_codecapacity_dem else None),
                points={p.case_id: dict(p.sampling_identity, status="pending", seed=point_seed(config.master_seed, p),
                                       shots=0, logical_errors=0, wall_seconds=0., started_at=None,
                                       ended_at=None, files=[p.filename(t) for t in p.tables])
                        for p in config.points()},
            )
            store._save()
            return store
        except BaseException:
            if "store" in locals():
                store.close()
            raise

    def __init__(self, path, document):
        self.path, self.document = Path(path), document
        self._owner = os.getpid()
        self._closed = False
        self._started = time.monotonic()
        self._previous_wall = 0.
        self._point_starts = {}
        self._lock = self.path / ".run.lock"
        acquire_lock(self._lock)

    @classmethod
    def resume(cls, path):
        path = Path(path).resolve()
        document = load_saved_config(path)
        clear_stale_lock(path / ".run.lock")
        store = cls(path, document)
        try:
            value = json.loads((path / "metadata.json").read_text())
            config = document.config
            if (value.get("schema_version") != 2 or value.get("config_hash") != config.config_hash
                    or value.get("input_sha256") != document.input_hash or value.get("config") != config.as_dict()):
                raise ValueError("saved v2 config changed; resume rejected")
            if (config.kind == "knill_ec_memory"
                    and value.get("final_readout") != next(config.points()).final_readout):
                raise ValueError("saved Knill final readout changed")
            if (value.get("prior_policy") != config.prior_policy
                    or (config.create_codecapacity_dem
                        and value.get("projected_approximation") != LOCAL_PRIOR_APPROXIMATION)):
                raise ValueError("saved prior policy changed; create a new run")
            env = collect_environment()
            if _compatibility(value["environment"]) != _compatibility(env):
                raise ValueError("source/dependency environment changed; create a new run")
            points = {p.case_id: p for p in config.points()}
            if set(value["points"]) != points.keys() or value["status"] not in {"running", "failed", "complete"}:
                raise ValueError("invalid saved v2 point identities/status")
            # Validate completed files before deleting any incomplete output.
            for key, point in points.items():
                info = value["points"][key]
                if (any(info.get(name) != setting for name, setting in point.sampling_identity.items())
                        or info.get("seed") != point_seed(config.master_seed, point)):
                    raise ValueError("saved physical point identity/seed changed")
                if info["files"] != [point.filename(t) for t in point.tables]:
                    raise ValueError("saved point filenames changed")
                if info["status"] == "complete":
                    validate_noise_execution(point, info.get("execution"),
                                             create_codecapacity_dem=config.create_codecapacity_dem)
                    validate_point_files(path, point, config.shots)
                    if (type(info["shots"]) is not int or info["shots"] != config.shots
                            or type(info["logical_errors"]) is not int
                            or not 0 <= info["logical_errors"] <= info["shots"]):
                        raise ValueError("saved complete point count changed")
                elif info["status"] not in {"pending", "running", "failed"}:
                    raise ValueError("invalid saved point status")
            if value["status"] == "complete" and any(p["status"] != "complete" for p in value["points"].values()):
                raise ValueError("complete run has unfinished point metadata")
            (path / ".metadata.json.tmp").unlink(missing_ok=True)
            for key, point in points.items():
                if value["points"][key]["status"] != "complete":
                    restart_incomplete_point(path, point)
                    value["points"][key].update(status="pending", shots=0, logical_errors=0,
                                               started_at=None, ended_at=None, wall_seconds=0.)
                    value["points"][key].pop("error", None)
            store._metadata = value
            store._previous_wall = value["wall_seconds"]
            if value["status"] != "complete":
                value.update(status="running", ended_at=None, resume_count=value["resume_count"] + 1)
                value.pop("error", None)
                store._save()
            return store
        except BaseException:
            store.close()
            raise

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)

    def _check_owner(self):
        if self._closed or os.getpid() != self._owner:
            raise RuntimeError("only the owning parent process may update run metadata")

    def _save(self):
        self._check_owner()
        self._metadata["wall_seconds"] = self._previous_wall + time.monotonic() - self._started
        atomic_json(self.path / "metadata.json", self._metadata)

    def start_point(self, point):
        self._check_owner()
        expected = {p.case_id: p for p in self.document.config.points()}
        if point.case_id not in expected or point != expected[point.case_id]:
            raise ValueError("point does not belong to this run")
        value = self._metadata["points"][point.case_id]
        if self._metadata["status"] != "running" or value["status"] != "pending":
            raise ValueError("point must be pending in a running run")
        value.update(status="running", started_at=utc_now().isoformat())
        self._point_starts[point.case_id] = time.monotonic()
        self._save()

    def record_complete(self, result: PointResult, *, execution=None):
        self._check_owner()
        config = self.document.config
        point = next((p for p in config.points() if p.case_id == result.case_id), None)
        if point is None or self._metadata["points"][point.case_id]["status"] != "running":
            raise ValueError("result must belong to a running point")
        if (type(result.shots) is not int or result.shots != config.shots or type(result.logical_errors) is not int
                or not 0 <= result.logical_errors <= result.shots
                or not math.isfinite(result.wall_seconds) or result.wall_seconds < 0
                or result.files != tuple(point.filename(t) for t in point.tables)):
            raise ValueError("invalid point result identity/counts")
        validate_point_files(self.path, point, config.shots)
        validate_noise_execution(point, execution, create_codecapacity_dem=config.create_codecapacity_dem)
        if execution is not None:
            if not isinstance(execution, dict):
                raise ValueError("execution metadata must be a JSON mapping")
            # Validate/copy before mutating the completion marker; keep runner
            # details nested so they cannot overwrite identities/counts/status.
            execution = json.loads(json.dumps(execution, allow_nan=False))
        value = self._metadata["points"][point.case_id]
        if execution is not None:
            value["execution"] = execution
        value.update(status="complete", shots=result.shots, logical_errors=result.logical_errors,
                     wall_seconds=time.monotonic() - self._point_starts[point.case_id],
                     ended_at=utc_now().isoformat())
        self._save()

    def finish(self):
        self._check_owner()
        if not all(p["status"] == "complete" for p in self._metadata["points"].values()):
            raise ValueError("cannot complete a run with unfinished points")
        self._metadata.update(status="complete", ended_at=utc_now().isoformat())
        self._save()

    def fail(self, error):
        self._check_owner()
        ended = utc_now().isoformat()
        for key, info in self._metadata["points"].items():
            if info["status"] == "running":
                info.update(status="failed", ended_at=ended, error=f"{type(error).__name__}: {error}",
                            wall_seconds=time.monotonic() - self._point_starts[key])
        self._metadata.update(status="failed", ended_at=ended, error=f"{type(error).__name__}: {error}")
        self._save()

    def close(self):
        if not self._closed:
            self._check_owner()
            self._lock.unlink(missing_ok=True)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind is not None and self._metadata["status"] != "complete":
                self.fail(value)
        finally:
            self.close()
