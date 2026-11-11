"""Small physical circuits, causal equations and controlled faults (<=7 shots)."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import BlockUseId, NoiseModel, parse_logical_circuit
from logical_to_stim_converter.decoding import CorrectionBatch
from knill_bench.converter.knill_decoding import KnillDecoder
from knill_bench.converter.knill_memory import ConverterKnillMemory
from knill_bench.converter.knill_program import IDEAL_POST, NOISY_D, knill_source
from knill_bench.experiments.config_v2 import parse_config


def point(regime=IDEAL_POST, *, d=3, p=0., depth=2, **options):
    return next(parse_config(dict(schema_version=2,kind="converter_knill_memory",noise="converter_uniform",
        sweep=dict(d=[d],p=[p]),resource_preparation=regime,T_tel=depth,**options)).points())


@pytest.fixture(scope="module")
def clean():
    return ConverterKnillMemory(point(depth=3))


@pytest.fixture(scope="module")
def noisy():
    return ConverterKnillMemory(point(NOISY_D,p=.001,depth=2))


@pytest.mark.parametrize("regime", [IDEAL_POST,NOISY_D])
@pytest.mark.parametrize("depth", [1,2,3,4])
def test_noiseless_successive_knill_random_branches_and_three_patch_recycling(regime,depth):
    model=ConverterKnillMemory(point(regime,depth=depth))
    c=model.compiled
    raw=model.circuit.compile_sampler(seed=126).sample(7)
    before=raw.copy()
    assert not model.decode_batch(raw).logical_error.any()
    assert np.array_equal(raw,before)
    branches=[]
    for bell in c.bell_measurements:
        for readout in (bell.x_readout,bell.z_readout):
            ids=[c.measurement_index_by_key[k] for k in readout.logical_parity.terms]
            branches.extend(np.logical_xor.reduce(raw[:,ids],axis=1).tolist())
    assert set(branches)=={False,True}
    assert len(c.relocation_history)==depth
    assert {bid for bid,_ in c.physical_qubit_map}=={"P0","P1","P2"}
    assert len(c.block_uses)==1+2*depth
    assert len({u.use_id for u in c.block_uses})==len(c.block_uses)
    previous=next(p.block_use_id for p in c.preparations if p.logical_id=="D")
    for i,r in enumerate(c.relocation_history):
        assert r.composite_id==f"ec{i}" and r.source_use_id==previous
        resource=[p for p in c.preparations if p.logical_id in {f"A{i}",f"B{i}"}]
        assert len(resource)==2 and all(p.block_use_id!=previous for p in resource)
        assert {p.block_id for p in resource}=={"P0","P1","P2"}-{previous.block_id}
        previous=r.output_use_id
    for bid in ("P0","P1","P2"):
        epochs=sorted(u.use_id.epoch for u in c.block_uses if u.use_id.block_id==bid)
        assert epochs==list(range(len(epochs)))
    assert model.lstim_source.count("KNILL_EC[")==depth
    assert "SE[post" not in model.lstim_source
    assert c.observables[0].basis=="Z" and c.readouts[-1].mode=="deterministic"


@pytest.mark.parametrize("regime", [IDEAL_POST,NOISY_D])
def test_optional_post_rounds_are_explicit_independent_of_teleportation_count(regime):
    model=ConverterKnillMemory(point(regime,depth=2,post_rounds=1))
    assert len(model.compiled.relocation_history)==2
    assert sum(f.operation_type=="SyndromeExtraction" for f in model.compiled.fragments)==2
    assert model.lstim_source.count("SE[post")==2
    assert not model.decode_batch(model.circuit.compile_sampler(seed=127).sample(3)).logical_error.any()


@pytest.mark.parametrize("regime", [IDEAL_POST,NOISY_D])
@pytest.mark.parametrize("depth", [1,2])
def test_finite_probability_d3_d5_models_and_both_preparation_regimes(regime,depth):
    # d5 is the larger finite-p fixture; other tests exercise d3 and T=3/4.
    model=ConverterKnillMemory(point(regime,d=5,p=.001,depth=depth))
    raw=model.circuit.compile_sampler(seed=128).sample(3)
    decoded=model.decode_batch(raw)
    assert decoded.logical_error.dtype==bool and decoded.logical_error.shape==(3,)
    assert model.metadata["joint_cross_block_matching"] is False
    assert model.metadata["enable_correlations"] is False and model.metadata["decoder_limits"]
    assert np.array_equal(decoded.logical_error,model.decode_batch(raw).logical_error)


def test_typed_noise_targets_actual_use_and_probabilities_with_no_double_channel():
    model=ConverterKnillMemory(point(p=.002,depth=2,p_st_multiplier=1.5))
    c=model.compiled
    initial,=c.post_initialization_boundaries
    native_initial,=(p for p in c.preparations if p.logical_id=="D")
    assert initial.block_use_id==native_initial.block_use_id
    assert initial.operation_id=="initial" and initial.probability==.002
    channel=c.circuit[initial.channel_instruction]
    assert channel.name=="DEPOLARIZE1" and channel.gate_args_copy()==[.002]
    assert [t.value for t in channel.targets_copy()]==[c.physical_qubit_map[q] for q in initial.data_sites]
    resources=c.resource_preparation_boundaries
    assert len(resources)==4 and initial.block_use_id not in {b.block_use_id for b in resources}
    assert len({b.block_use_id for b in resources})==4
    for boundary in resources:
        ch=c.circuit[boundary.channel_instruction]
        assert ch.name=="DEPOLARIZE1" and ch.gate_args_copy()==[.003]
        assert [t.value for t in ch.targets_copy()]==[c.physical_qubit_map[q] for q in boundary.data_sites]
        assert boundary.ideal_boundary_instruction<=boundary.channel_instruction
    for prep in c.preparations:
        assert prep.rounds==(1 if prep.logical_id=="D" else 3)
    # CNOT and destructive-readout noise remains ordinary in regime A.
    assert any(i.name=="DEPOLARIZE2" and i.gate_args_copy()==[.002] for i in c.circuit)
    assert any(i.name in {"M","MX"} and i.gate_args_copy()==[.002] for i in c.circuit)


def test_noisy_regime_retains_d_rounds_and_no_m9_or_input_post_channels(noisy):
    c=noisy.compiled
    assert all(p.rounds==3 for p in c.preparations)
    assert not c.resource_preparation_boundaries and not c.post_initialization_boundaries
    assert noisy.metadata["temporal_components"]>0 and noisy.metadata["temporal_separators"]>0
    assert noisy.metadata["temporal_prior_only_components"]>0


def test_frame_replay_deltas_and_current_events_are_exact_not_stale(clean):
    raw=clean.circuit.compile_sampler(seed=129).sample(7)
    replay=clean.decoder.replay(raw,trace=True)
    changed=False
    for trace in replay.stages:
        boundary=clean.frame_plan.boundary_by_id[trace.module_id]
        assert np.array_equal(trace.before ^ trace.after,boundary.record_map.apply(trace.result.correction.bits))
        request=(clean.decoder.boundaries if trace.kind=="boundary" else clean.decoder.readouts)[trace.module_id]
        assert np.array_equal(trace.inputs.events,request.view.events_from_raw(trace.before))
        changed |= not np.array_equal(trace.inputs.events,request.view.events_from_raw(raw))
    assert changed
    assert not replay.logical_error.any()


def test_readout_syndrome_equations_and_nonzero_sector_map_gf2(clean):
    raw=clean.circuit.compile_sampler(seed=130).sample(7)
    replay=clean.decoder.replay(raw,trace=True)
    for trace in replay.stages:
        if trace.kind!="readout":continue
        r=clean.decoder.readouts[trace.module_id]
        measured=np.column_stack([np.logical_xor.reduce(trace.inputs.records[:,np.flatnonzero(row)],axis=1)
                                  for row in r.check_matrix])
        effect=np.column_stack([np.logical_xor.reduce(trace.result.correction.bits[:,np.flatnonzero(row)],axis=1)
                                for row in r.check_matrix])
        assert np.array_equal(measured ^ effect,trace.inputs.expected_sector)
    # Feed arbitrary nonzero sectors: this cannot pass by assuming all are zero.
    rng=np.random.default_rng(131)
    sectors=rng.integers(0,2,(7,len(clean.decoder.requests.sector_input_ids))).astype(bool)
    for r in clean.decoder.requests.readouts:
        expected=np.column_stack([np.logical_xor.reduce(sectors[:,s],axis=1) if s else np.zeros(7,bool)
                                  for s in r.sector_map.supports]) ^ r.sector_constant
        assert np.array_equal(expected,r.sector_map.apply(sectors)^r.sector_constant)
    # Explicit first-cycle Clifford equations: CX(A,B), CX(D,A).
    first=clean.compiled.bell_measurements[0]
    prep={p.logical_id:p for p in clean.compiled.preparations if p.logical_id in {"D","A0","B0"}}
    ids=clean.decoder.requests.sector_input_ids
    for readout,owners in ((first.x_readout,("D","A0","B0")),(first.z_readout,("D","A0"))):
        r=clean.decoder.readouts[readout.module_id]
        rows=[c for c in readout.checks if c.basis==readout.basis]
        manual=np.column_stack([np.logical_xor.reduce(sectors[:,[ids.index((prep[name].module_id,c.check_id))
            for name in owners]],axis=1) for c in rows])
        assert np.array_equal(manual,r.sector_map.apply(sectors)^r.sector_constant)


def test_bad_corrections_epoch_order_double_apply_and_wrong_readout_are_detected(clean):
    raw=clean.circuit.compile_sampler(seed=132).sample(3)
    replay=clean.decoder.replay(raw,trace=True)
    trace=next(t for t in replay.stages if t.kind=="boundary" and t.result.correction.bits.any())
    correction=trace.result.correction
    for bad in (replace(correction,block_use_id=BlockUseId(correction.block_use_id.block_id,999)),
                replace(correction,input_ids=tuple(reversed(correction.input_ids)))):
        frame=clean.frame_plan.start(raw,source_fingerprint=clean.frame_plan.source_fingerprint)
        with pytest.raises(ValueError):frame.apply(bad)
    frame=clean.frame_plan.start(raw,source_fingerprint=clean.frame_plan.source_fingerprint)
    frame.apply(correction)
    with pytest.raises(ValueError):frame.apply(correction)
    adapter=clean.decoder.boundary_decoders[trace.module_id]
    for bits in (np.zeros_like(correction.bits),np.concatenate(np.split(correction.bits,2,axis=1)[::-1],axis=1)):
        bad_result=replace(trace.result,correction=replace(correction,bits=bits))
        with pytest.raises(ValueError,match="net-sector"):
            adapter.validate_result(trace.inputs,bad_result)
    x=next(r for r in clean.decoder.readouts.values() if r.readout.basis=="X")
    z=next(r for r in clean.decoder.readouts.values() if r.readout.basis=="Z")
    xtrace=next(t for t in replay.stages if t.module_id==x.readout.module_id)
    with pytest.raises(ValueError,match="basis"):
        clean.decoder.readout_decoders[x.readout.module_id].decode_batch(z,xtrace.inputs)


def sample_fault(model,cut,wires,axis="X",shots=3):
    fault=stim.Circuit()
    fault.append(axis,wires)
    # Controlled fault fixture: retain the exact converter-authored operations,
    # remove stochastic channels only here, and insert the declared Pauli.
    physical=model.circuit[:cut].without_noise()+fault+model.circuit[cut:].without_noise()
    return physical.compile_sampler(seed=133).sample(shots)


@pytest.mark.parametrize("axis",["X","Z"])
def test_single_resource_data_and_bell_final_readout_faults(clean,axis):
    c=clean.compiled
    for resource in c.resource_preparation_boundaries:
        wire=c.physical_qubit_map[resource.data_sites[0]]
        raw=sample_fault(clean,resource.ideal_boundary_instruction,[wire],axis)
        assert not clean.decode_batch(raw).logical_error.any()
    raw=clean.circuit.compile_sampler(seed=134).sample(3)
    for r in clean.decoder.readouts.values():
        changed=raw.copy()
        changed[:,r.record_ids[r.logical_indices[0]]]^=True
        assert not clean.decode_batch(changed).logical_error.any()


@pytest.mark.parametrize("axis",["X","Z"])
def test_input_preparation_data_fault_in_noisy_round_window(noisy,axis):
    prep=next(p for p in noisy.compiled.preparations if p.logical_id=="D")
    last_round0=max(m.index for m in noisy.compiled.measurements if m.module_id==prep.module_id and m.key.round_index==0)
    cut=next(i for i in range(1,len(noisy.circuit)) if noisy.circuit[:i].num_measurements>last_round0)
    wire=noisy.compiled.physical_qubit_map[prep.block_id,prep.data_ids[0]]
    raw=sample_fault(noisy,cut,[wire],axis)
    assert not noisy.decode_batch(raw).logical_error.any()


@pytest.mark.parametrize("axis",["X","Z"])
def test_single_fault_before_and_after_data_teleportation_cnot(clean,axis):
    c=clean.compiled
    gates=[f for f in c.fragments if f.operation_type=="TransversalCNOT" and "D" in f.logical_ids]
    assert len(gates)==3
    for gate,relocation in zip(gates,c.relocation_history,strict=True):
        indices=[i for i,inst in enumerate(c.circuit) if inst.tag==gate.module_id]
        source=next(p for p in c.preparations if p.block_use_id==relocation.source_use_id)
        wire=c.physical_qubit_map[source.block_id,source.data_ids[0]]
        for cut in (min(indices),max(indices)+1):
            assert not clean.decode_batch(sample_fault(clean,cut,[wire],axis)).logical_error.any()


@pytest.mark.parametrize("axis,expected",[("X",True),("Z",False)])
def test_known_logical_fault_before_and_after_successive_teleportations(clean,axis,expected):
    c=clean.compiled
    cuts=[(c.post_initialization_boundaries[0].ideal_boundary_instruction,
           next(p for p in c.preparations if p.logical_id=="D"))]
    for bell in c.bell_measurements:
        readout_ids=[bell.x_readout.module_id,bell.z_readout.module_id]
        cut=max(i for i,inst in enumerate(c.circuit) if inst.tag in readout_ids)+1
        prep=next(p for p in c.preparations if p.block_use_id==bell.output_use_id)
        cuts.append((cut,prep))
    for cut,prep in cuts:
        support=prep.logical_x if axis=="X" else prep.logical_z
        wires=[c.physical_qubit_map[prep.block_id,q] for q in support]
        labels=clean.decode_batch(sample_fault(clean,cut,wires,axis)).logical_error
        assert (labels==expected).all()


def test_open_output_logical_x_z_frame_transport_to_surviving_use(clean):
    source=knill_source(clean.point).rsplit("MZ[final] D",1)[0]
    c=parse_logical_circuit(source).compile(noise_model=NoiseModel(),allow_open_outputs=True)
    plan=c.make_frame_plan()
    raw=c.circuit.compile_sampler(seed=135).sample(3)
    initial=next(p for p in c.preparations if p.logical_id=="D")
    output=next(p for p in c.preparations if p.block_use_id==c.relocation_history[-1].output_use_id)
    boundary=plan.boundary_by_id[initial.module_id]
    for axis in ("X","Z"):
        before=plan.start(raw,source_fingerprint=plan.source_fingerprint)
        after=plan.start(raw,source_fingerprint=plan.source_fingerprint)
        bits=np.zeros((3,2*len(initial.data_ids)),dtype=bool)
        support=initial.logical_x if axis=="X" else initial.logical_z
        for q in support:bits[:,initial.data_ids.index(q)+(0 if axis=="X" else len(initial.data_ids))]=True
        after.apply(CorrectionBatch(plan.source_fingerprint,initial.module_id,bits,initial.block_use_id,boundary.input_ids))
        dx=before.final_x ^ after.final_x
        dz=before.final_z ^ after.final_z
        z_wires=[c.physical_qubit_map[output.block_id,q] for q in output.logical_z]
        x_wires=[c.physical_qubit_map[output.block_id,q] for q in output.logical_x]
        assert (np.logical_xor.reduce(dx[:,z_wires],axis=1)==(axis=="X")).all()
        assert (np.logical_xor.reduce(dz[:,x_wires],axis=1)==(axis=="Z")).all()
