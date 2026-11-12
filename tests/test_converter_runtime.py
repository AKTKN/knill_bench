"""Exact bounded ledger, statistics, identity, integrity and replay contracts."""

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from knill_bench.converter.artifacts import file_digest
from knill_bench.converter.runtime import (
    CONTRACT, LEDGER, SamplingLedger, binomial_result, iter_sampling_chunks, validate_runtime,
)
from knill_bench.experiments import adaptive_execution as adaptive, dispatcher
from knill_bench.experiments.config_v2 import load_config, parse_config
from knill_bench.experiments.seeds import chunk_seed
from knill_bench.analysis.converter import summarize_saved


def config(tmp_path,**updates):
    raw=dict(schema_version=2,kind="converter_se_memory",noise="converter_uniform",
        sweep=dict(d=[3],p=[.02]),shots=7,batch_size="auto",buffer_shot=3,
        workers=1,output_root=str(tmp_path/"runs"))
    raw.update(updates);path=tmp_path/"input.yaml";path.write_text(yaml.safe_dump(raw))
    return load_config(path)


@pytest.fixture(scope="module")
def actual(tmp_path_factory):
    tmp_path=tmp_path_factory.mktemp("runtime")
    doc=config(tmp_path);path=dispatcher.dispatch(doc.source_path)
    return path,doc


def test_actual_adaptive_recorded_partition_replay_and_saved_stats(actual):
    path,doc=actual;point=next(doc.config.points())
    info=json.loads((path/"metadata.json").read_text())["points"][point.case_id]
    chunks=list(iter_sampling_chunks(path,point));assert len(chunks)==info["execution"]["chunk_count"]
    expected=pq.read_table(path/point.filename("logical_error"))["logical_error"].to_numpy()
    adaptive._MODEL=None
    try:
        for row in reversed(chunks):  # Recorded identities survive arbitrary replay order.
            result=adaptive.run_chunk(adaptive.ChunkTask(point,**{k:row[k] for k in ("chunk_id","start","shots","seed")}))
            assert np.array_equal(result.labels,expected[row["start"]:row["start"]+row["shots"]])
    finally:adaptive._MODEL=None
    report=summarize_saved(path)["points"][0]
    assert report["logical_error_rate"]==int(expected.sum())/len(expected)
    assert report["confidence_interval"]==binomial_result(int(expected.sum()),len(expected))["confidence_interval"]
    assert info["execution"]["logical_error_sha256"]==file_digest(path/point.filename("logical_error"))
    assert info["execution"]["circuit_counts"]["measurements"]>0
    for key in ("sampler_compile_seconds","sampling_seconds","decoding_seconds","setup_seconds"):
        assert info["execution"]["timing_statistics"][key]==pytest.approx(sum(c[key] for c in chunks))


def ledger_fixture(tmp_path,shots=7):
    doc=config(tmp_path,shots=shots,batch_size=1);p=next(doc.config.points())
    (tmp_path/p.directory).mkdir(parents=True)
    stream="converter_fixed_chunks_v1";ledger=SamplingLedger(tmp_path,p,doc.config.master_seed,stream)
    digest=hashlib.sha256()
    from knill_bench.experiments.config_v2 import canonical
    for i in range(shots):
        result=adaptive.ChunkResult(i,i,1,np.zeros(1,bool),None,.3,.4,7,os.getpid(),None,
            dict(sampler_compile_seconds=.1,sampling_seconds=.1,decoding_seconds=.1))
        ledger.append(result)
        digest.update(canonical([i,i,1,chunk_seed(doc.config.master_seed,p,i,stream=stream)]).encode()+b"\n")
        assert len(ledger.rows)<512
    sha=ledger.publish()
    # Logical data are separately checksummed; exact count/schema checks belong
    # to RunStore, and do not need a physical model in this ledger unit fixture.
    label=tmp_path/p.filename("logical_error");label.write_bytes(b"synthetic labels")
    info=dict(shots=shots,logical_errors=0,artifacts={f"{p.directory}/{LEDGER}":sha},execution=dict(
        execution_contract=CONTRACT,**binomial_result(0,shots),logical_error_sha256=file_digest(label),
        chunk_seed_stream=stream,parallel_execution=stream,chunk_count=shots,
        chunk_shots_min=1,chunk_shots_max=1,chunk_partition_sha256=digest.hexdigest(),
        timing_statistics=dict(ledger.totals,parent_compile_seconds=.2,parent_io_seconds=.2)))
    return doc,p,info


def test_ledger_buffer_bound_multiple_flushes_and_unit_wilson(tmp_path):
    # Synthetic chunks only; no >7-shot physical sampling.
    doc,p,info=ledger_fixture(tmp_path,1025)
    assert len(list(iter_sampling_chunks(tmp_path,p)))==1025
    assert pq.ParquetFile(tmp_path/p.directory/LEDGER).metadata.num_row_groups==3
    validate_runtime(tmp_path,doc.config,p,info,required=True)
    zero=binomial_result(0,7);full=binomial_result(7,7)
    assert zero["confidence_interval"]["lower"]==0 and zero["confidence_interval"]["upper"]>0
    assert full["confidence_interval"]["upper"]==1 and full["confidence_interval"]["lower"]<1


@pytest.mark.parametrize("field",["seed","start","chunk_id","shots","sampling_seconds"])
def test_even_rehashed_ledger_corruption_fails_semantic_checks(tmp_path,field):
    doc,p,info=ledger_fixture(tmp_path)
    path=tmp_path/p.directory/LEDGER;table=pq.read_table(path);rows=table.to_pylist()
    rows[1][field]=-1. if field.endswith("seconds") else rows[1][field]+1
    pq.write_table(pa.Table.from_pylist(rows,schema=table.schema),path)
    info["artifacts"][f"{p.directory}/{LEDGER}"]=file_digest(path)
    with pytest.raises(ValueError,match="chunk identity|count/digest|statistics"):
        validate_runtime(tmp_path,doc.config,p,info,required=True)


@pytest.mark.parametrize("damage",["rate","interval","label_checksum","ledger_checksum","timing","contract"])
def test_runtime_rejects_changed_summary_or_missing_manifest(tmp_path,damage):
    doc,p,info=ledger_fixture(tmp_path)
    e=info["execution"]
    if damage=="rate":e["logical_error_rate"]=.5
    elif damage=="interval":e["confidence_interval"]["upper"]=0.
    elif damage=="label_checksum":(tmp_path/p.filename("logical_error")).write_bytes(b"corrupt")
    elif damage=="ledger_checksum":(tmp_path/p.directory/LEDGER).write_bytes(b"corrupt")
    elif damage=="timing":e["timing_statistics"]["sampling_seconds"]=float("nan")
    else:e.pop("execution_contract")
    with pytest.raises(ValueError):validate_runtime(tmp_path,doc.config,p,info,required=True)


def test_ledger_refuses_duplicate_and_unordered_chunks_and_cleans_temp(tmp_path,monkeypatch):
    doc=config(tmp_path);p=next(doc.config.points());(tmp_path/p.directory).mkdir(parents=True)
    ledger=SamplingLedger(tmp_path,p,123,"time_adaptive_chunks_v1")
    result=adaptive.ChunkResult(1,0,1,np.zeros(1,bool),None,1.,0.,7,1,None)
    with pytest.raises(ValueError,match="ordered"):ledger.append(result)
    ledger.close();assert not ledger.temp.exists()


def test_posix_pid_probe_preserves_live_process_and_dead_process(tmp_path):
    from knill_bench.data.storage_v2 import _pid_alive, clear_stale_lock
    import socket
    assert _pid_alive(os.getpid())
    path=tmp_path/"lock";path.write_text(json.dumps(dict(host=socket.gethostname(),pid=os.getpid())))
    with pytest.raises(RuntimeError,match="live process"):clear_stale_lock(path)
    assert path.exists()


def test_validation_matrix_configurations_are_small_and_cover_requested_axes():
    import importlib.util
    file=Path(__file__).parents[1]/"scripts/validate_converter_matrix.py"
    spec=importlib.util.spec_from_file_location("validation_matrix",file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    docs=list(module.configurations(include_depth32=True))
    points=[p for raw in docs for p in parse_config(raw).points()]
    assert len(docs)==18 and len(points)==53
    assert {p.rounds for p in points if p.kind=="converter_se_memory"}=={1,3,5,6,10}
    assert {p.T_tel for p in points if p.kind=="converter_knill_memory"}=={1,2,3}
    assert {p.depth for p in points if p.kind=="converter_deep_clifford"}=={2,3,32}
    assert all(parse_config(raw).shots<=3 for raw in docs)


@pytest.mark.parametrize("handle,status,error,expected",[(123,258,0,True),(123,0,0,False),(0,0,87,False),(0,0,5,None)])
def test_windows_pid_handle_probe_never_sends_a_signal(monkeypatch,handle,status,error,expected):
    import ctypes
    import sys
    from knill_bench.data.storage_v2 import _pid_alive
    closed=[]
    class Function:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*args):return self.fn(*args)
    kernel=SimpleNamespace(OpenProcess=Function(lambda *a:handle),
        WaitForSingleObject=Function(lambda *a:status),CloseHandle=Function(lambda h:closed.append(h)))
    monkeypatch.setattr(ctypes,"WinDLL",lambda *a,**kw:kernel,raising=False)
    monkeypatch.setattr(ctypes,"get_last_error",lambda:error,raising=False)
    monkeypatch.setattr(sys,"platform","win32")
    monkeypatch.setattr(os,"kill",lambda *a:pytest.fail("Windows process probe sent a signal"))
    if expected is None:
        with pytest.raises(PermissionError):_pid_alive(1234)
    else:assert _pid_alive(1234) is expected
    assert closed==([handle] if handle else [])
