"""BENCH-N2: native custom channels, local scope, bounded output and resume."""

from dataclasses import fields, replace
import json

import numpy as np
import pyarrow.parquet as pq
import pymatching
import pytest
import stim
import yaml

from hex_qec.circuit_generation import FactoryNoiseModel, IdleWindow, PlusPreparationIdle
from hex_qec.circuit_generation.factory_noise import idle_depolarizing_probability
from hex_qec.decoders import UnsupportedProjectedModel
from hex_qec.modularisation import PreparationPlan
from hex_qec.protocols import FactoryCircuitBuilder, RotatedSurfaceCodeAdapter
from hex_qec.simulation.factory import FactoryBatchDecoder
from knill_bench.adapters import hex_factory as local
from knill_bench.analysis.factory import AnalysisSettings, analyze_saved
from knill_bench.experiments import adaptive_execution as adaptive
from knill_bench.experiments import logical_zero_factory as runner
from knill_bench.experiments.config_v2 import load_config
from knill_bench.experiments.run_v2 import RunStore
from knill_bench.experiments.seeds import point_seed
from test_v2_factory_noise import custom_noise


def document(tmp_path, **updates):
    raw = dict(schema_version=2, kind="logical_zero_factory", name="custom_test",
               output_root=str(tmp_path/"runs"), noise=custom_noise(),
               sweep=dict(d=[3],p=[.003]), r_0=2,r_plus=2,T_tel=2,shots=7,
               batch_size=3,workers=1,master_seed=773)
    raw.update(updates)
    path=tmp_path/"input.yaml"
    path.write_text("# Exact custom physical settings\n"+yaml.safe_dump(raw))
    return load_config(path)


def tables(path, point):
    return [pq.read_table(path/point.filename(t)) for t in point.tables]


@pytest.fixture(autouse=True)
def clear_models():
    local.clear_local_prior_cache()
    adaptive._MODEL=None
    yield
    local.clear_local_prior_cache()
    adaptive._MODEL=None


@pytest.mark.parametrize("prior", [False,True])
@pytest.mark.parametrize("skip", [False,True])
def test_native_builder_identity_idle_supports_and_packed_frames(tmp_path,prior,skip):
    doc=document(tmp_path)
    point=next(doc.config.points())
    bundle,compiled=runner.compile_point(point,seed=91,create_codecapacity_dem=prior,
                                         skip_circuit_validation=skip)
    expected=FactoryCircuitBuilder(RotatedSurfaceCodeAdapter(3),PreparationPlan(2,2),
                                   .003,T_tel=2,noise_model=point.noise_model).build()
    assert bundle.circuit==expected.circuit==compiled.circuit
    assert compiled.cache_key.noise_model_sha256==point.noise_model.configuration_sha256
    assert len(bundle.blocks)==2 and bundle.circuit.num_qubits==34
    for j,stage in enumerate(bundle.stages):
        consumed,survivor=bundle.blocks[j%2],bundle.blocks[(j+1)%2]
        assert (stage.consumed_block,stage.surviving_block)==(consumed.name,survivor.name)
        post=bundle.circuit[stage.post_cnot_control_idle.instructions.slice]
        assert len(post)==1 and post[0].name=="DEPOLARIZE1"
        assert tuple(t.value for t in post[0].targets_copy())==survivor.data_qubits
        assert post[0].gate_args_copy()[0]==idle_depolarizing_probability(.003,.2,2,5)
        assert stage.post_cnot_control_idle.instructions.stop==stage.coupling.instructions.stop
        if j==0:
            assert stage.storage_idle is None
        else:
            idle=bundle.circuit[stage.storage_idle.instructions.slice]
            assert tuple(t.value for t in idle[0].targets_copy())==consumed.data_qubits
            assert idle[0].gate_args_copy()[0]==idle_depolarizing_probability(.003,.2,2,1)
            assert stage.storage_idle.instructions.stop==stage.coupling.instructions.start
    oracle=bundle.circuit[bundle.oracle.instructions.slice]
    assert len(oracle)==1 and oracle[0].name=="M" and not oracle[0].gate_args_copy()
    raw=compiled.sample_measurements(7)
    reference=FactoryBatchDecoder(bundle)
    reference._projected_gaps=compiled._decoder._projected_gaps
    reference.projected_priors=compiled.projected_priors
    actual,expected=compiled.decode(raw),reference.decode(raw)
    for description in fields(expected):
        np.testing.assert_array_equal(getattr(actual,description.name),
                                      getattr(expected,description.name))


@pytest.mark.parametrize("window,field,value", [
    ("post_cnot_control","duration",.5),
    ("during_plus_preparation","se_round_duration",.25)])
def test_window_duration_changes_exact_native_physical_channel(tmp_path,window,field,value):
    point=next(document(tmp_path).config.points())
    before,_=runner.compile_point(point,seed=1)
    old=getattr(point.noise_model,window)
    new_model=replace(point.noise_model,**{window:replace(old,**{field:value})})
    changed=replace(point,noise_model=new_model)
    after,_=runner.compile_point(changed,seed=1)
    region_name="post_cnot_control_idle" if window=="post_cnot_control" else "storage_idle"
    stage=0 if window=="post_cnot_control" else 1
    a=before.circuit[getattr(before.stages[stage],region_name).instructions.start]
    b=after.circuit[getattr(after.stages[stage],region_name).instructions.start]
    assert a.gate_args_copy()!=b.gate_args_copy()
    duration=value if stage==0 else changed.r_plus*value
    rate=getattr(new_model,window).rate_multiplier
    assert b.gate_args_copy()[0]==idle_depolarizing_probability(point.p,new_model.idle,duration,rate)
    assert before.metadata["circuit_sha256"]!=after.metadata["circuit_sha256"]


def test_local_analysis_contains_post_idle_excludes_storage_and_has_analytic_weights(tmp_path):
    point=next(document(tmp_path).config.points())
    bundle,compiled=runner.compile_point(point,seed=19,create_codecapacity_dem=True)
    n=bundle.code.num_data_qubits
    bodies=[local._local_body(bundle,s) for s in bundle.stages]
    assert bodies[0]==bodies[1]  # storage is strictly before the local boundary
    assert compiled.projected_priors[0] is compiled.projected_priors[1]
    body=stim.Circuit(bodies[0])
    channels=[i for i in body if i.name=="DEPOLARIZE1"]
    assert len(channels)==1
    assert [t.value for t in channels[0].targets_copy()]==list(range(n,2*n))
    analysis=local._analysis_circuit(bundle.code,bodies[0])
    assert any(i==channels[0] for i in analysis)
    assert analysis.num_measurements==n
    assert str(local._stim_dem(analysis))==compiled.projected_priors[0].dem_text
    # Only target marginal errors affect the current Z readout. The included
    # post-CNOT control channel is physically present but invisible here.
    q_gate=8*point.p*point.noise_model.two_qubit/15
    q_readout=point.p*point.noise_model.measurement
    q=q_gate+q_readout-2*q_gate*q_readout
    analytic={}
    for qubit in range(n):
        signature=local.FaultSignature(tuple(j for j,r in enumerate(bundle.code.z_checks) if qubit in r),
                                      (0,) if qubit in bundle.code.logical_z else ())
        old=analytic.get(signature,0.)
        analytic[signature]=old*(1-q)+q*(1-old)
    actual={event.signature:event.probability for event in compiled.projected_priors[0].model.events}
    assert actual.keys()==analytic.keys()
    for signature,probability in actual.items():
        assert probability==pytest.approx(analytic[signature],abs=1e-14)


@pytest.mark.parametrize("parameter", ["one_qubit","post_duration","prep_duration","measurement","two_qubit"])
def test_complete_noise_configuration_separates_cached_prior_identities(tmp_path,parameter):
    point=next(document(tmp_path).config.points())
    a,first=runner.compile_point(point,seed=1,create_codecapacity_dem=True)
    model=point.noise_model
    if parameter in {"measurement","two_qubit"}:
        model=replace(model,**{parameter:getattr(model,parameter)*1.5})
    elif parameter=="one_qubit":model=replace(model,one_qubit=.3)
    elif parameter=="post_duration":model=replace(model,post_cnot_control=IdleWindow(.5,5))
    else:model=replace(model,during_plus_preparation=PlusPreparationIdle(True,.5,1))
    b,second=runner.compile_point(replace(point,noise_model=model),seed=1,create_codecapacity_dem=True)
    assert a.metadata["circuit_sha256"]!=b.metadata["circuit_sha256"]
    assert first.cache_key!=second.cache_key
    p,q=first.projected_priors[0],second.projected_priors[0]
    assert p is not q and p.configuration_sha256!=q.configuration_sha256
    assert local.local_prior_cache_info()["misses"]==2
    # Prep/storage are excluded, and post-control noise is invisible to this
    # stage's consumed-target readout. Distinct configuration is still kept.
    if parameter in {"measurement","two_qubit"}:
        assert p.dem_text!=q.dem_text and p.model_sha256!=q.model_sha256
    else:
        assert p.dem_text==q.dem_text
    if parameter in {"post_duration","measurement","two_qubit"}:
        assert p.physical_module_sha256!=q.physical_module_sha256
    else:
        assert p.physical_module_sha256==q.physical_module_sha256


@pytest.mark.parametrize("prior", [False,True])
def test_survivor_logical_fault_and_oracle_cannot_enter_operational_decoding(tmp_path,prior):
    point=next(document(tmp_path,T_tel=1).config.points())
    bundle,compiled=runner.compile_point(point,seed=91,create_codecapacity_dem=prior)
    offset=bundle.stages[0].post_cnot_control_idle.instructions.start
    sim=stim.FlipSimulator(batch_size=7,num_qubits=bundle.circuit.num_qubits,seed=73)
    sim.do(bundle.circuit[:offset].without_noise())
    faulty=sim.copy(copy_rng=True)
    fault=stim.Circuit()
    fault.append("X_ERROR",[bundle.blocks[1].data_qubits[q] for q in bundle.code.logical_x],1)
    faulty.do(fault)
    suffix=bundle.circuit[offset:].without_noise()
    sim.do(suffix);faulty.do(suffix)
    reference=bundle.circuit.without_noise().reference_sample()[None,:]
    raw=reference^sim.get_measurement_flips().T
    changed=reference^faulty.get_measurement_flips().T
    np.testing.assert_array_equal(raw[:,:bundle.oracle.measurements.start],
                                  changed[:,:bundle.oracle.measurements.start])
    before,after=compiled.decode(raw),compiled.decode(changed)
    assert not before.logical_error.any() and after.logical_error.all()
    for name in vars(before).keys()-{"logical_error"}:
        np.testing.assert_array_equal(getattr(before,name),getattr(after,name))


def test_custom_hamming_and_local_share_fixed_raw_samples_and_native_objects_are_cached(tmp_path,monkeypatch):
    point=next(document(tmp_path).config.points())
    _,hamming=runner.compile_point(point,seed=71)
    _,weighted=runner.compile_point(point,seed=71,create_codecapacity_dem=True)
    assert hamming.circuit==weighted.circuit
    for count in (3,4):
        raw=hamming.sample_measurements(count)
        np.testing.assert_array_equal(raw,weighted.sample_measurements(count))
        def forbidden(*args,**kwargs):raise AssertionError("batch constructed native model")
        with monkeypatch.context() as m:
            m.setattr(local,"_stim_dem",forbidden)
            m.setattr(FactoryCircuitBuilder,"build",forbidden)
            m.setattr(pymatching.Matching,"from_check_matrix",forbidden)
            for decoder in (hamming,weighted):
                decoded=decoder.decode(raw)
                assert np.isfinite(decoded.gaps).all()
                assert decoded.frame_resolved.all()


@pytest.mark.parametrize("prior", [False,True])
@pytest.mark.parametrize("batch", [3,"auto"])
def test_saved_pairs_exact_yaml_effective_noise_and_local_scope(tmp_path,prior,batch):
    doc=document(tmp_path,create_codecapacity_dem=prior,batch_size=batch,buffer_shot=3)
    path=runner.run(doc)
    point=next(doc.config.points())
    errors,gaps=tables(path,point)
    assert errors["shot_id"].to_pylist()==gaps["shot_id"].to_pylist()==list(range(7))
    assert errors.join(gaps,keys="shot_id",join_type="inner").num_rows==7
    assert gaps.column_names==["shot_id","gap_t001","gap_t002"]
    assert all(gaps[name].null_count==0 and np.isfinite(gaps[name].to_numpy()).all()
               for name in gaps.column_names[1:])
    assert (path/"config.yaml").read_bytes()==doc.contents
    assert set(p.name for p in path.iterdir())=={"config.yaml","metadata.json",
                                                *[point.filename(t) for t in point.tables]}
    metadata=json.loads((path/"metadata.json").read_text())
    info=metadata["points"][point.case_id];execution=info["execution"]
    assert metadata["status"]==info["status"]=="complete"
    assert info["logical_errors"]==sum(errors["logical_error"].to_pylist())
    assert execution["noise_parameters"]==doc.config.as_dict()["noise"]
    assert execution["noise_model_sha256"]==point.noise_model.configuration_sha256
    assert execution["teleportation_readout_error"]==point.p*2
    assert execution["idle_window_durations"]==dict(post_cnot_control=2.,during_plus_preparation=2.)
    assert execution["idle_window_application_counts"]==dict(post_cnot_control=2,during_plus_preparation=1)
    assert execution["oracle"]=="terminal_ideal_Z_evaluation_only"
    if prior:
        assert execution["post_cnot_control_idle_in_local_prior"] is True
        assert execution["storage_idle_errors_in_local_prior"] is False
        assert execution["preparation_residual_errors_in_prior"] is False
    report=analyze_saved(path,AnalysisSettings(thresholds=(-np.inf,)))
    assert report["rows"][0]["shots"]==7
    with RunStore.resume(path) as store:assert store.metadata["status"]=="complete"


@pytest.mark.parametrize("prior", [False,True])
def test_fixed_serial_spawn_and_theta_independence(tmp_path,prior):
    doc=document(tmp_path,shots=5,workers=2,create_codecapacity_dem=prior)
    parallel=runner.run(doc)
    other=document(tmp_path,shots=5,workers=1,theta=1e12,create_codecapacity_dem=prior)
    serial=runner.run(other)
    point=next(doc.config.points())
    assert next(other.config.points())==point
    assert point_seed(doc.config.master_seed,point)==point_seed(other.config.master_seed,point)
    assert all(a.equals(b) for a,b in zip(tables(parallel,point),tables(serial,point)))


def test_custom_adaptive_spawn_saves_aligned_tables_and_consistent_models(tmp_path):
    doc=document(tmp_path,shots=5,workers=2,batch_size="auto",buffer_shot=3,create_codecapacity_dem=True)
    path=runner.run(doc);point=next(doc.config.points())
    errors,gaps=tables(path,point)
    assert errors["shot_id"].to_pylist()==gaps["shot_id"].to_pylist()==list(range(5))
    meta=json.loads((path/"metadata.json").read_text())["points"][point.case_id]["execution"]
    assert meta["parallel_execution"]=="time_adaptive_chunks_v1"
    assert meta["noise_model_sha256"]==point.noise_model.configuration_sha256


@pytest.mark.parametrize("field,value", [
    ("noise_model_sha256","bad"),
    ("noise_model_json","{}"),
    ("physical_noise_sha256","bad"),
    ("noise_parameters",{}),
    ("post_cnot_control_idle_in_local_prior",False),
    ("storage_idle_errors_in_local_prior",True),
    ("prior_policy","hex_legacy_hamming"),
    ("prior_scope","includes_storage_and_preparation")])
def test_resume_and_saved_analysis_reject_tampered_noise_metadata(tmp_path,field,value):
    doc=document(tmp_path,shots=3,create_codecapacity_dem=True)
    path=runner.run(doc)
    metadata_path=path/"metadata.json"
    metadata=json.loads(metadata_path.read_text())
    next(iter(metadata["points"].values()))["execution"][field]=value
    metadata_path.write_text(json.dumps(metadata))
    point=next(doc.config.points())
    original={name:(path/point.filename(name)).read_bytes() for name in point.tables}
    for operation in (lambda:RunStore.resume(path),lambda:analyze_saved(path)):
        with pytest.raises(ValueError,match="custom noise"):operation()
    assert original=={name:(path/point.filename(name)).read_bytes() for name in point.tables}


def test_changed_noise_document_rejected_before_unfinished_data_cleanup(tmp_path):
    doc=document(tmp_path)
    with RunStore.create(doc) as store:path=store.path
    point=next(doc.config.points())
    partial=path/point.filename("logical_error");partial.write_bytes(b"unfinished")
    metadata=(path/"metadata.json").read_bytes()
    changed=custom_noise()
    changed["idle_windows"]["post_cnot_control"]["duration"]=.5
    other=document(tmp_path,noise=changed)
    with pytest.raises(ValueError,match="resume document"):runner.run(other,resume_path=path)
    assert partial.read_bytes()==b"unfinished"
    assert (path/"metadata.json").read_bytes()==metadata


def test_failed_custom_chunk_restarts_and_replays_fixed_tables(tmp_path,monkeypatch):
    doc=document(tmp_path,create_codecapacity_dem=True)
    real=runner._decode_chunk
    calls=[]
    def interrupted(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RuntimeError("synthetic custom chunk failure")
        return real(*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(runner,"_decode_chunk",interrupted)
        with pytest.raises(RuntimeError,match="custom chunk"):runner.run(doc)
    path=next((tmp_path/"runs").iterdir());point=next(doc.config.points())
    assert not any(path.glob("*.parquet"))
    runner.run(doc,resume_path=path)
    fresh=runner.run(doc)
    assert all(a.equals(b) for a,b in zip(tables(path,point),tables(fresh,point)))


def test_custom_zero_active_prior_rejects_without_fallback(tmp_path):
    doc=document(tmp_path,sweep=dict(d=[3],p=[0.]),shots=3,create_codecapacity_dem=True)
    with pytest.raises(UnsupportedProjectedModel,match="Hamming"):runner.run(doc)
    path=next((tmp_path/"runs").iterdir())
    assert not any(path.glob("*.parquet"))
    assert json.loads((path/"metadata.json").read_text())["status"]=="failed"


def test_custom_zero_multipliers_execute_noiseless_operations(tmp_path):
    model=FactoryNoiseModel(one_qubit=0,two_qubit=0,idle=0,measurement=0,reset=0)
    point=replace(next(document(tmp_path).config.points()),noise_model=model)
    bundle,compiled=runner.compile_point(point,seed=47)
    assert all(not i.gate_args_copy() or not any(i.gate_args_copy())
               for i in bundle.circuit if stim.gate_data(i.name).is_noisy_gate)
    result=compiled.sample(7)
    assert not result.logical_error.any() and not result.corrected_syndromes.any()
    np.testing.assert_array_equal(result.gaps,3.)

