"""One bounded-memory writer per point; metadata is the publication marker."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import socket
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from knill_bench.experiments.config_v2 import ExperimentPoint


def schemas(point: ExperimentPoint):
    common = [pa.field("shot_id", pa.uint64(), nullable=False)]
    result = {"logical_error": pa.schema(common + [pa.field("logical_error", pa.bool_(), nullable=False)])}
    if "logical_gaps" in point.tables:
        result["logical_gaps"] = pa.schema(common + [pa.field(f"gap_t{j:03d}", pa.float64(), nullable=True)
                                                     for j in range(1, point.T_tel + 1)])
    return {name: schema.with_metadata({b"knill_bench_schema_version": b"2", b"table": name.encode()})
            for name, schema in result.items()}


def atomic_json(path: Path, value):
    temp = path.with_name("." + path.name + ".tmp")
    try:
        with temp.open("w") as output:
            json.dump(value, output, sort_keys=True, indent=2, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def acquire_lock(path: Path):
    """Exclusive local-process guard; stale locks are removed only on resume."""
    with path.open("x") as output:
        json.dump(dict(pid=os.getpid(), host=socket.gethostname()), output)


def clear_stale_lock(path: Path):
    if not path.exists():
        return
    try:
        info = json.loads(path.read_text())
        if info["host"] != socket.gethostname() or type(info["pid"]) is not int or info["pid"] <= 0:
            raise ValueError("foreign host or invalid PID")
        try:
            os.kill(info["pid"], 0)
        except ProcessLookupError:
            path.unlink()
            return
    except (ValueError, KeyError, PermissionError) as error:
        raise RuntimeError(f"cannot establish stale lock ownership: {path}") from error
    raise RuntimeError(f"another live process owns {path}")


@dataclass(frozen=True)
class PointResult:
    case_id: str
    shots: int
    logical_errors: int
    wall_seconds: float
    files: tuple[str, ...]


class PointWriter:
    """Stream aligned contiguous IDs, close BOTH tables, then rename each.

    Two filesystem renames cannot be jointly atomic. A reader must consult
    the parent-owned metadata complete marker. Resume discards all outputs
    from an unfinished point, including a crash between those renames.
    """

    def __init__(self, run, point: ExperimentPoint, *, expected_shots: int):
        if type(expected_shots) is not int or not 1 <= expected_shots < 2**63:
            raise ValueError("expected_shots must be positive and fit int64")
        self.run, self.point = Path(run), point
        self.expected_shots = expected_shots
        self._lock = self.run / f".point-{point.case_id}.lock"
        self._schemas = schemas(point)
        self._writers, self._opened, self._promoted = {}, [], []
        self.rows = self.errors = 0
        self._closed = self._committed = False
        self._started = time.monotonic()
        acquire_lock(self._lock)
        try:
            for name in point.tables:
                if self._public(name).exists() or self._temp(name).exists():
                    raise FileExistsError("point output already exists; resume unfinished points before writing")
            for name in point.tables:
                self._writers[name] = pq.ParquetWriter(self._temp(name), self._schemas[name], compression="zstd")
                self._opened.append(self._temp(name))
        except BaseException:
            self.abort()
            raise

    def _public(self, table):
        return self.run / self.point.filename(table)

    def _temp(self, table):
        return self.run / ("." + self.point.filename(table) + ".incomplete")

    def write_batch(self, shot_id, logical_error, gaps=None):
        if self._closed:
            raise RuntimeError("point writer is closed")
        ids, labels = np.asarray(shot_id), np.asarray(logical_error)
        if ids.ndim != 1 or ids.dtype != np.uint64 or not len(ids):
            raise ValueError("shot_id must be a nonempty uint64 vector")
        if labels.shape != ids.shape or labels.dtype != bool:
            raise ValueError("logical_error must be an aligned non-null boolean vector")
        if self.rows + len(ids) > self.expected_shots:
            raise ValueError("batch exceeds expected point shot count")
        expected = np.arange(len(ids), dtype=np.uint64) + np.uint64(self.rows)
        if not np.array_equal(ids, expected):
            raise ValueError("shot_id must be contiguous from zero with no duplicates or reordering")
        shot_ids = pa.array(ids, type=pa.uint64())
        tables = {"logical_error": pa.Table.from_arrays([shot_ids, pa.array(labels)], schema=self._schemas["logical_error"])}
        if "logical_gaps" in self._schemas:
            if gaps is None:
                columns = [pa.nulls(len(ids), type=pa.float64()) for _ in range(self.point.T_tel)]
            else:
                values = np.asarray(gaps)
                if values.dtype != np.float64 or values.shape != (len(ids), self.point.T_tel):
                    raise ValueError("gaps must be aligned float64 (shots,T_tel) values")
                if np.isinf(values).any() or (values < 0).any():
                    raise ValueError("gaps must be nonnegative finite values or NaN for unavailable")
                columns = [pa.array(values[:, j], type=pa.float64(), from_pandas=True) for j in range(self.point.T_tel)]
            tables["logical_gaps"] = pa.Table.from_arrays([shot_ids, *columns], schema=self._schemas["logical_gaps"])
        elif gaps is not None:
            raise ValueError("Fig.4(d) does not have a gaps table")
        # Validate both tables before either append; retain only this batch.
        for name, table in tables.items():
            self._writers[name].write_table(table)
        self.rows += len(ids)
        self.errors += int(np.count_nonzero(labels))

    def _close(self):
        failure = None
        for writer in self._writers.values():
            try:
                writer.close()
            except BaseException as error:
                failure = failure or error
        self._writers.clear()
        self._closed = True
        if failure is not None:
            raise failure

    def commit(self) -> PointResult:
        if self._closed:
            raise RuntimeError("point writer is closed")
        try:
            if self.rows != self.expected_shots:
                raise ValueError("incomplete point: shot count does not match expected_shots")
            self._close()
            for name in self.point.tables:
                with self._temp(name).open("rb") as source:
                    os.fsync(source.fileno())
                info = pq.ParquetFile(self._temp(name))
                if (info.metadata.num_rows != self.rows
                        or not info.schema_arrow.equals(self._schemas[name], check_metadata=True)):
                    raise ValueError("staged Parquet schema/count mismatch")
            # Every footer is closed and checked before the first promotion.
            for name in self.point.tables:
                if self._public(name).exists():
                    raise FileExistsError("refusing to overwrite public point output")
                os.replace(self._temp(name), self._public(name))
                self._promoted.append(self._public(name))
            self._committed = True
            self._lock.unlink()
            return PointResult(self.point.case_id, self.rows, self.errors, time.monotonic() - self._started,
                               tuple(self.point.filename(name) for name in self.point.tables))
        except BaseException:
            self.abort()
            raise

    def abort(self):
        try:
            self._close()
        finally:
            if not self._committed:
                for path in (*self._opened, *self._promoted):
                    path.unlink(missing_ok=True)
            self._lock.unlink(missing_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        if not self._committed:
            self.abort()


def validate_point_files(run: Path, point: ExperimentPoint, expected_shots: int):
    for name, schema in schemas(point).items():
        info = pq.ParquetFile(run / point.filename(name))
        if info.metadata.num_rows != expected_shots or not info.schema_arrow.equals(schema, check_metadata=True):
            raise ValueError("public point file has incorrect schema or row count")


def restart_incomplete_point(run: Path, point: ExperimentPoint):
    """Parent-only call, after acquiring the run lock; never for complete points."""
    clear_stale_lock(run / f".point-{point.case_id}.lock")
    for table in point.tables:
        (run / point.filename(table)).unlink(missing_ok=True)
        (run / ("." + point.filename(table) + ".incomplete")).unlink(missing_ok=True)
