"""Lazy, read-only schema-v2 datasets for notebook figures (no simulation)."""

from dataclasses import dataclass
import json
from pathlib import Path
import warnings

import numpy as np
import pyarrow.parquet as pq

from knill_bench.data.storage_v2 import validate_point_files
from knill_bench.experiments.config_v2 import load_saved_config, LEGACY_PRIOR_POLICY
from knill_bench.experiments.noise_v2 import validate_noise_execution
from knill_bench.experiments.seeds import point_seed
from .factory import _paired_batches

ALIASES = {"distance": "d", "T_tel": "T", "r_+": "r_plus", "noisemodel": "noise"}


def field_name(name):
    return ALIASES.get(name, name)


def choices(value):
    return value if isinstance(value, (list, tuple, set, frozenset)) else (value,)


@dataclass(frozen=True)
class SavedPoint:
    path: Path
    point: object
    info: dict
    conditions: dict
    expected_shots: int

    def batches(self, *, gaps=False, batch_size=65536):
        """Validate schemas, contiguous paired IDs, scores and metadata counts.

        Exhaust this iterator to validate totals. Row groups may differ between
        tables. Only one bounded paired batch is materialized at a time.
        """
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        point = self.point
        if gaps and "logical_gaps" not in point.tables:
            raise ValueError(f"{self.conditions['key']}: this experiment has no logical_gaps file")
        files = [self.path / point.filename(t) for t in point.tables]
        if any(not f.is_file() for f in files):
            raise ValueError(f"missing published point file: {self.path}, d={point.d}, p={point.p}")
        validate_point_files(self.path, point, self.expected_shots)
        # Even LER-only plots validate an existing gap pair before using its labels.
        if len(files) == 2:
            stream = _paired_batches(*files, batch_size)
        else:
            stream = ((b,) for b in pq.ParquetFile(files[0]).iter_batches(batch_size=batch_size))
        shots = errors = 0
        for batches in stream:
            expected = np.arange(shots, shots + len(batches[0]), dtype=np.uint64)
            for batch in batches:
                if any(c.null_count for c in batch.columns):
                    raise ValueError("null IDs, labels or logical gaps")
                if not np.array_equal(batch.column(0).to_numpy(), expected):
                    raise ValueError("paired shot IDs must be contiguous from zero and aligned")
            labels = batches[0].column(1).to_numpy(zero_copy_only=False)
            scores = None
            if len(batches) == 2:
                scores = np.column_stack([c.to_numpy() for c in batches[1].columns[1:]])
                if not np.isfinite(scores).all() or (scores < 0).any():
                    raise ValueError("logical gaps must be finite and nonnegative")
            shots += len(labels)
            errors += int(labels.sum())
            yield labels, scores if gaps else None
        if shots != self.info["shots"] or errors != self.info["logical_errors"]:
            raise ValueError("saved shot/error counts disagree with metadata")


class RunRegistry:
    """Register ``{key: run_directory}`` without accessing the filesystem.

    Selection reads config/metadata only when requested. Complete points in an
    unfinished run can be plotted; selected unpublished points are skipped with
    a warning. Corrupt complete points always raise. No persistent data cache.
    """

    def __init__(self, paths=None):
        self._paths = {}
        for key, path in (paths or {}).items():
            self.register(key, path)

    def register(self, key, path):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("dataset key must be a nonempty string")
        if key in self._paths:
            raise ValueError(f"duplicate dataset key: {key}")
        self._paths[key] = Path(path).expanduser()
        return self

    @property
    def paths(self):
        return dict(self._paths)

    def select(self, filter_by=None):
        filters = {}
        for name, value in (filter_by or {}).items():
            name = field_name(name)
            if name in filters:
                raise ValueError(f"duplicate filter alias: {name}")
            filters[name] = value
        keys = choices(filters["key"]) if "key" in filters else tuple(self._paths)
        if any(key not in self._paths for key in keys):
            raise ValueError("unknown dataset key")
        selected, skipped = [], 0
        known = {"key"}
        for key in keys:
            path = self._paths[key]
            document = load_saved_config(path)
            config = document.config
            meta = json.loads((path / "metadata.json").read_text())
            policies = {config.prior_policy}
            if config.kind == "logical_zero_factory" and config.create_codecapacity_dem:
                policies.add(LEGACY_PRIOR_POLICY)
            if (meta.get("schema_version") != 2 or meta.get("kind") != config.kind
                    or meta.get("config_hash") != config.config_hash
                    or meta.get("input_sha256") != document.input_hash
                    or meta.get("config") != config.as_dict()
                    or meta.get("gap_units") != config.gap_units
                    or meta.get("prior_policy") not in policies
                    or meta.get("final_readout") != next(config.points()).final_readout):
                raise ValueError(f"unchanged schema-v2 config/score/readout metadata required: {path}")
            points = list(config.points())
            if set(meta["points"]) != {p.case_id for p in points}:
                raise ValueError("saved point identities changed")
            for point in points:
                info = meta["points"][point.case_id]
                conditions = {**config.as_dict(), "key": key, "d": point.d, "p": point.p,
                              "T": point.T_tel, "r_0": point.r_0, "r_plus": point.r_plus,
                              "rounds": point.rounds, "noise": point.noise,
                              "noise_parameters": json.dumps(config.as_dict()["noise"], sort_keys=True),
                              "prior_policy": meta["prior_policy"], "gap_units": meta["gap_units"],
                              "final_readout": point.final_readout, "case_id": point.case_id,
                              "config_hash": config.config_hash}
                for name in ("sweep", "T_tel", "schema_version"):
                    conditions.pop(name, None)
                known.update(conditions)
                if not all(name in conditions and conditions[name] in choices(value)
                           for name, value in filters.items()):
                    continue
                if info.get("status") != "complete":
                    skipped += 1
                    continue
                if (info.get("files") != [point.filename(t) for t in point.tables]
                        or type(info.get("shots")) is not int or info["shots"] != config.shots
                        or type(info.get("logical_errors")) is not int
                        or not 0 <= info["logical_errors"] <= info["shots"]
                        or info.get("seed") != point_seed(config.master_seed, point)
                        or any(info.get(k) != v for k, v in point.sampling_identity.items())):
                    raise ValueError("complete point identity/count/publication metadata mismatch")
                if config.kind in {"logical_zero_factory", "knill_sim", "knill_ec_memory"}:
                    validate_noise_execution(point, info.get("execution"),
                                             create_codecapacity_dem=config.create_codecapacity_dem, codecapacity_prior=config.codecapacity_prior)
                selected.append(SavedPoint(path, point, info, conditions, config.shots))
        if set(filters) - known:
            raise ValueError(f"unknown filter fields: {sorted(set(filters) - known)}")
        if skipped:
            warnings.warn(f"Skipped {skipped} selected unfinished point(s); only published complete points are plotted",
                          UserWarning, stacklevel=2)
        if not selected:
            raise ValueError("no complete points match filter_by")
        return selected
