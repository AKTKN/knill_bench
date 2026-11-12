"""Bounded parent-owned sampling ledger and saved scientific result checks."""

import hashlib
import math
import os

from knill_bench.experiments.config_v2 import canonical
from knill_bench.experiments.seeds import chunk_seed
from .artifacts import file_digest, relative_path

CONTRACT = "converter_execution_v2"
LEDGER = "sampling_chunks.parquet"
TIMINGS = ("sampler_compile_seconds", "sampling_seconds", "decoding_seconds")


def circuit_counts(circuit, evaluated_observables):
    return dict(qubits=circuit.num_qubits, detectors=circuit.num_detectors,
                measurements=circuit.num_measurements, observables=circuit.num_observables,
                evaluated_logical_observables=evaluated_observables)


def binomial_result(errors, shots):
    from knill_bench.analysis.confidence import WilsonInterval
    lower, upper = WilsonInterval().bounds(errors, shots)
    return dict(logical_error_rate=errors/shots,
                confidence_interval=dict(method="Wilson_score", confidence=.95, lower=lower, upper=upper))


def ledger_schema(point):
    import pyarrow as pa
    return pa.schema([pa.field(k, pa.uint64(), nullable=False) for k in ("chunk_id", "start", "shots", "seed")]
        + [pa.field(k, pa.float64(), nullable=False) for k in ("setup_seconds", *TIMINGS)],
        metadata={b"sampling_ledger": b"1", b"case_id": point.case_id.encode()})


class SamplingLedger:
    """One parent writer, <=512 buffered rows, with ordered chunk identities.

    A point's complete marker commits this file together with its label table
    and model sidecars. Closing/fsync/schema checks precede its public rename.
    """
    def __init__(self, run, point, master_seed, stream):
        import pyarrow.parquet as pq
        self.point, self.master_seed, self.stream = point, master_seed, stream
        self.path = relative_path(run, f"{point.directory}/{LEDGER}")
        self.temp = self.path.with_name("."+self.path.name+".incomplete")
        if self.path.exists() or self.temp.exists():
            raise FileExistsError("sampling ledger exists; resume the unfinished point first")
        self.schema = ledger_schema(point)
        self.writer = pq.ParquetWriter(self.temp, self.schema, compression="zstd")
        self.rows, self.count, self.shots = [], 0, 0
        self.totals = dict.fromkeys(("setup_seconds", *TIMINGS), 0.)
        self.closed = False

    def append(self, result):
        if result.chunk_id != self.count or result.start != self.shots:
            raise ValueError("sampling ledger requires contiguous ordered chunks/shots")
        values = dict(result.timings or dict.fromkeys(TIMINGS, 0.))
        row = dict(chunk_id=result.chunk_id, start=result.start, shots=result.shots,
                   seed=chunk_seed(self.master_seed,self.point,result.chunk_id,stream=self.stream),
                   setup_seconds=result.setup_seconds, **values)
        if set(values) != set(TIMINGS) or any(not math.isfinite(row[k]) or row[k] < 0 for k in self.totals):
            raise ValueError("sampling ledger requires finite nonnegative worker timings")
        for k in self.totals:self.totals[k] += row[k]
        self.rows.append(row);self.count += 1;self.shots += result.shots
        if len(self.rows) == 512:self.flush()

    def flush(self):
        import pyarrow as pa
        if self.rows:
            self.writer.write_table(pa.Table.from_pylist(self.rows,schema=self.schema))
            self.rows.clear()

    def publish(self):
        import pyarrow.parquet as pq
        self.flush();self.writer.close();self.closed = True
        with self.temp.open("r+b") as source:os.fsync(source.fileno())
        file=pq.ParquetFile(self.temp)
        if file.metadata.num_rows != self.count or not file.schema_arrow.equals(self.schema,check_metadata=True):
            file.close()
            raise ValueError("sampling ledger schema/count changed before publication")
        file.close()
        if self.path.exists():raise FileExistsError("refusing to overwrite a public sampling ledger")
        os.replace(self.temp,self.path)
        return file_digest(self.path)

    def close(self):
        if not self.closed:self.writer.close();self.closed=True
        self.temp.unlink(missing_ok=True)


def iter_sampling_chunks(run, point):
    """Public bounded reader of recorded partitions/seeds, not a simulator."""
    import pyarrow.parquet as pq
    file=pq.ParquetFile(relative_path(run,f"{point.directory}/{LEDGER}"))
    try:
        if not file.schema_arrow.equals(ledger_schema(point),check_metadata=True):
            raise ValueError("sampling ledger schema or case identity changed")
        for batch in file.iter_batches(batch_size=512):
            if any(c.null_count for c in batch.columns):raise ValueError("sampling ledger contains nulls")
            yield from batch.to_pylist()
    finally:file.close()


def validate_runtime(run, config, point, info, *, required=False):
    """Check new execution records; old converter files retain their old contract."""
    execution=info.get("execution") or {}
    if not required and execution.get("execution_contract") is None and "circuit_counts" not in execution:return
    if execution.get("execution_contract") != CONTRACT:
        raise ValueError("converter execution contract is missing or changed")
    if (type(info.get("shots")) is not int or info["shots"] != config.shots
            or type(info.get("logical_errors")) is not int or not 0 <= info["logical_errors"] <= info["shots"]):
        raise ValueError("converter saved shot/error counts changed")
    expected=binomial_result(info["logical_errors"],info["shots"])
    if any(execution.get(k) != v for k,v in expected.items()):
        raise ValueError("saved converter logical error rate/confidence interval changed")
    if execution.get("logical_error_sha256") != file_digest(relative_path(run,point.filename("logical_error"))):
        raise ValueError("converter logical-error Parquet checksum changed")
    relative=f"{point.directory}/{LEDGER}"
    if relative not in info.get("artifacts",{}) or file_digest(relative_path(run,relative)) != info["artifacts"][relative]:
        raise ValueError("converter sampling ledger checksum is missing or changed")
    stream=execution.get("chunk_seed_stream")
    if stream not in {"converter_fixed_chunks_v1","time_adaptive_chunks_v1"} or stream != execution.get("parallel_execution"):
        raise ValueError("converter sampling stream changed")
    count=shots=0;partition=hashlib.sha256();totals=dict.fromkeys(("setup_seconds",*TIMINGS),0.)
    minimum=config.shots;maximum=0
    for row in iter_sampling_chunks(run,point):
        if (row["chunk_id"] != count or row["start"] != shots or row["shots"] < 1
                or row["seed"] != chunk_seed(config.master_seed,point,count,stream=stream)
                or any(not math.isfinite(row[k]) or row[k]<0 for k in totals)
                or (config.batch_size != "auto" and row["shots"] != min(config.batch_size,config.shots-shots))):
            raise ValueError("converter sampling chunk identity/partition/seed/timing changed")
        partition.update(canonical([row[k] for k in ("chunk_id","start","shots","seed")]).encode()+b"\n")
        for k in totals:totals[k] += row[k]
        minimum=min(minimum,row["shots"]);maximum=max(maximum,row["shots"])
        count+=1;shots+=row["shots"]
    if (shots != config.shots or count != execution.get("chunk_count")
            or partition.hexdigest() != execution.get("chunk_partition_sha256")
            or minimum != execution.get("chunk_shots_min") or maximum != execution.get("chunk_shots_max")):
        raise ValueError("converter sampling ledger count/digest disagrees with execution metadata")
    timing=execution.get("timing_statistics")
    if (not isinstance(timing,dict) or any(not isinstance(timing.get(k),(int,float)) or
            not math.isfinite(timing[k]) or timing[k]<0 for k in (*totals,"parent_compile_seconds","parent_io_seconds"))
            or any(not math.isclose(timing[k],v,rel_tol=1e-12,abs_tol=1e-12) for k,v in totals.items())):
        raise ValueError("converter timing statistics changed or are missing")
