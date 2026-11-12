"""Independent logical/fault/MWPM/causal tests, d3 and <=7 shots per batch."""

from dataclasses import replace
import math

import numpy as np
import pymatching
import pytest
from scipy.sparse import csc_matrix
import stim

from logical_to_stim_converter.decoding import StageInputs
from knill_bench.converter.deep_simulation import ConverterDeepClifford
from knill_bench.experiments.config_v2 import parse_config


def point(**updates):
    raw = dict(schema_version=2, kind="converter_deep_clifford", noise="converter_uniform",
               sweep=dict(d=[3], p=[.01]), depth=2, circuit_seed=19)
    raw.update(updates)
    return next(parse_config(raw).points())


@pytest.fixture(scope="module")
def model():
    return ConverterDeepClifford(point())


@pytest.fixture(scope="module")
def m9():
    return ConverterDeepClifford(point(depth=1, resource_preparation="ideal", p_st_multiplier=2.))


def sample_fault(model, cut, wires, axis):
    # Test-only deterministic injection; converter owns every remaining operation.
    fault = stim.Circuit(); fault.append(axis, wires)
    physical = model.circuit[:cut].without_noise() + fault + model.circuit[cut:].without_noise()
    return physical.compile_sampler(seed=917).sample(3)


def independent_terminal(model, samples, frames):
    """Explicit symplectic pairing using public supports, never for inference."""
    columns = []
    for info in model.probe.observables:
        xz = np.logical_xor.reduce(frames.final_x[:, info.physical_z], axis=1)
        zx = np.logical_xor.reduce(frames.final_z[:, info.physical_x], axis=1)
        columns.append(samples[:, info.measurement_index] ^ xz ^ zx ^ bool(info.expected_value))
    return np.column_stack(columns)


@pytest.mark.parametrize("seed,depth,n_r", [(19,1,1), (41,2,1), (11,3,2)])
def test_ideal_all_signed_generators_all_branches(seed, depth, n_r):
    ideal = ConverterDeepClifford(point(sweep=dict(d=[3],p=[0.]), circuit_seed=seed, depth=depth,n_r=n_r))
    samples = ideal.circuit.compile_sampler(seed=281).sample(7)
    before = samples.copy()
    result = ideal.decoder.replay(samples)
    assert result.stabilizer_flips.shape == (7,4) and result.stabilizer_flips.dtype == bool
    assert not result.stabilizer_flips.any() and not result.logical_error.any()
    assert np.array_equal(before,samples)
    assert np.array_equal(independent_terminal(ideal,samples,result.frames), result.stabilizer_flips)
    assert set(samples[:,ideal.probe.measurement_indices].ravel()) == {False,True}


def reference_components(detectors, outputs, components, events):
    """Independent sparse-check-matrix PyMatching construction.

    Subdivide each component to preserve differently labelled parallel edges;
    direct DEM import would merge those alternatives. No bench graph is used.
    """
    active, db, ob = [], np.zeros(detectors,bool), np.zeros(outputs,bool)
    for ends, labels, q in components:
        if q > .5:
            db[list(ends)] ^= True; ob[list(labels)] ^= True; q = 1-q
        if ends and q:
            active.append((tuple(sorted(ends)), tuple(sorted(labels)), math.log((1-q)/q)))
    h = np.zeros((detectors+len(active),2*len(active)),dtype=np.uint8)
    f = np.zeros((outputs,2*len(active)),dtype=np.uint8)
    weights = []
    for i,(ends,labels,w) in enumerate(active):
        h[ends[0],2*i] = h[detectors+i,2*i] = h[detectors+i,2*i+1] = 1
        if len(ends)==2: h[ends[1],2*i+1] = 1
        f[list(labels),2*i] = 1
        weights.extend([w/2,w/2])
    if not active:
        assert not (events ^ db).any()
        return np.broadcast_to(ob,(len(events),outputs)).copy()
    graph = pymatching.Matching.from_check_matrix(csc_matrix(h), weights=weights,
                                                  faults_matrix=csc_matrix(f))
    lifted = np.column_stack((events ^ db,np.zeros((len(events),len(active)),bool)))
    return graph.decode_batch(lifted,enable_correlations=False).astype(bool) ^ ob


def dem_components(dem):
    parts = []
    for inst in dem.flattened():
        if inst.type != "error":continue
        ends, labels = set(), set()
        for t in inst.targets_copy():
            if t.is_separator():
                parts.append((ends,labels,inst.args_copy()[0])); ends,labels=set(),set()
            elif t.is_relative_detector_id():ends.symmetric_difference_update([t.val])
            else:
                assert t.is_logical_observable_id(); labels.symmetric_difference_update([t.val])
        parts.append((ends,labels,inst.args_copy()[0]))
    return parts


def capacity_reference(h, syndrome):
    return reference_components(len(h),h.shape[1],
        [(set(np.flatnonzero(h[:,j])),{j},1/(1+math.e)) for j in range(h.shape[1])],syndrome)


def test_actual_local_predictions_against_independent_sparse_pymatching(model):
    samples=model.circuit.compile_sampler(seed=921).sample(7)
    replay=model.decoder.replay(samples,trace=True)
    for trace in replay.stages:
        if trace.kind == "boundary":
            a=model.decoder.boundary_decoders[trace.module_id]; r=a.request
            predicted=reference_components(r.detector_error_model.num_detectors,len(r.target_ids),
                dem_components(r.detector_error_model),trace.inputs.events)
            assert np.array_equal(predicted,a.temporal.decode(trace.inputs.events))
            # Check both CSS capacity solves, before the prepared-logical toggle.
            inferred=trace.inputs.records[:,a.last_columns] ^ predicted[:,:len(r.checks)]
            for h, rows, adapter in ((a.hz,a.z_rows,a.x_decoder),(a.hx,a.x_rows,a.z_decoder)):
                assert np.array_equal(capacity_reference(h,inferred[:,rows]),adapter.decode(inferred[:,rows]))
        else:
            a=model.decoder.readout_decoders[trace.module_id]
            syndrome=(trace.inputs.records.astype(np.uint8)@a.checks.T%2).astype(bool)^trace.inputs.expected_sector
            assert np.array_equal(capacity_reference(a.checks,syndrome),trace.result.correction.bits)


def manual_replay(model,samples):
    """Independent projection path: recompute current records/events via view."""
    d=model.decoder; raw,_=model.probe.split_measurements(samples)
    frames=model.frame_plan.start(raw,source_fingerprint=model.probe.source_fingerprint)
    sectors=np.zeros((len(raw),len(d.requests.sector_input_ids)),bool)
    for kind,module in d.requests.order:
        a=(d.boundary_decoders if kind=="boundary" else d.readout_decoders)[module]
        r=a.request; current=frames.interpreted_measurements
        expected=None
        if kind=="readout":
            expected=np.column_stack([np.logical_xor.reduce(sectors[:,s],axis=1) if s else np.zeros(len(raw),bool)
                for s in r.sector_map.supports]) ^ r.sector_constant
        inputs=StageInputs(model.probe.source_fingerprint,r.view.events_from_raw(current),
                           current[:,r.view.measurement_map.global_ids],expected)
        result=a.decode_batch(r,inputs);frames.apply(result.correction)
        if kind=="boundary":
            for i,c in enumerate(r.checks):
                sectors[:,d.requests.sector_input_ids.index((module,c.check_id))]=result.net_sector[:,i]
    return independent_terminal(model,samples,frames)


@pytest.mark.parametrize("fixture",["model","m9"])
def test_identical_finite_noise_batch_independent_projection_and_probe_isolation(request,fixture):
    model=request.getfixturevalue(fixture)
    samples=model.circuit.compile_sampler(seed=923).sample(7)
    first=model.decoder.replay(samples,trace=True)
    assert np.array_equal(first.stabilizer_flips,manual_replay(model,samples))
    assert np.array_equal(first.logical_error,model.decode_batch(samples).logical_error)
    assert first.logical_error.shape==(7,) and first.logical_error.dtype==bool
    changed=samples.copy();changed[:,model.probe.measurement_indices]^=True
    other=model.decoder.replay(changed,trace=True)
    assert np.array_equal(first.stabilizer_flips ^ True,other.stabilizer_flips)
    for a,b in zip(first.stages,other.stages,strict=True):
        assert np.array_equal(a.result.correction.bits,b.result.correction.bits)
        assert np.array_equal(a.result.net_sector,b.result.net_sector)
        assert np.array_equal(a.inputs.events,b.inputs.events)
    prefix=model.compiled.circuit
    assert model.probe.circuit[:len(prefix)]==prefix
    assert np.array_equal(prefix.compile_sampler(seed=923).sample(7),
                          samples[:,:model.probe.original_measurement_count])


def logical_rows(model):
    rows=[]
    for product in model.logical_stabilizers:
        row=stim.PauliString(4);row.sign=product.sign
        for q,axis in product.factors:row[int(q[1:])]=axis
        rows.append(row)
    return rows


def gate_tail(model,layer,*,include_cnot=None):
    tail=stim.Circuit()
    if include_cnot is not None:
        for c,t in model.logical_circuit.layers[layer].cnots[include_cnot:]:tail.append("CX",[c,t])
    for later in model.logical_circuit.layers[layer+1:]:
        for q,g in enumerate(later.single_qubit):tail.append(g,[q])
        for c,t in later.cnots:tail.append("CX",[c,t])
    return tail


def assert_fault(model,cut,prep,axis,error,tail,*,logical=True):
    # On an odd rotated CSS patch, all-data X/Z is the logical Pauli in
    # either orientation. A preparation-time thin support can be stale after H.
    support=prep.data_ids if logical else prep.data_ids[:1]
    wires=[model.compiled.physical_qubit_map[prep.block_id,q] for q in support]
    samples=sample_fault(model,cut,wires,axis)
    replay=model.decoder.replay(samples)
    propagated=error.after(tail)
    expected=np.array([not propagated.commutes(row) for row in logical_rows(model)])
    assert np.array_equal(replay.stabilizer_flips,np.broadcast_to(expected,(3,4)))
    assert np.array_equal(replay.stabilizer_flips,independent_terminal(model,samples,replay.frames))
    return propagated


@pytest.mark.parametrize("axis",["X","Z"])
def test_logical_and_single_physical_fault_before_after_logical_cnot(model,axis):
    c=model.compiled
    for index,(control,target) in enumerate(model.logical_circuit.layers[0].cnots):
        gate=next(f for f in c.fragments if f.operation_id==f"layer0_cx{index}")
        instructions=[i for i,inst in enumerate(c.circuit) if inst.tag==gate.module_id]
        q=control if axis=="X" else target
        prep=next(p for p in c.preparations if p.logical_id==f"Q{q}")
        error=stim.PauliString(4);error[q]=axis
        for before,cut in ((True,min(instructions)),(False,max(instructions)+1)):
            tail=gate_tail(model,0,include_cnot=index if before else index+1)
            assert_fault(model,cut,prep,axis,error,tail)
            assert_fault(model,cut,prep,axis,stim.PauliString(4),tail,logical=False)
        # Explicit independent CNOT rule, before any subsequent layers.
        one=stim.Circuit();one.append("CX",[control,target])
        propagated=error.after(one)
        assert propagated[control]==propagated[target]==(1 if axis=="X" else 3)


@pytest.mark.parametrize("axis",["X","Z"])
def test_fault_before_after_teleportation_and_on_bell_resource(m9,axis):
    c=m9.compiled
    for bell,relocation in zip(c.bell_measurements,c.relocation_history,strict=True):
        q=int(relocation.logical_id[1:]);error=stim.PauliString(4);error[q]=axis
        gate=next(f for f in c.fragments if f.operation_type=="TransversalCNOT"
                  and f"ec0_q{q}" in f.composite_ids and f"Q{q}" in f.logical_ids)
        before=min(i for i,inst in enumerate(c.circuit) if inst.tag==gate.module_id)
        after=max(i for i,inst in enumerate(c.circuit)
                  if inst.tag in (bell.x_readout.module_id,bell.z_readout.module_id))+1
        for cut,use in ((before,relocation.source_use_id),(after,relocation.output_use_id)):
            prep=next(p for p in c.preparations if p.block_use_id==use)
            assert_fault(m9,cut,prep,axis,error,stim.Circuit())
            assert_fault(m9,cut,prep,axis,stim.PauliString(4),stim.Circuit(),logical=False)
    for resource in c.resource_preparation_boundaries:
        wire=c.physical_qubit_map[resource.data_sites[0]]
        samples=sample_fault(m9,resource.ideal_boundary_instruction,[wire],axis)
        result=m9.decoder.replay(samples)
        assert not result.stabilizer_flips.any()
        assert np.array_equal(result.stabilizer_flips,independent_terminal(m9,samples,result.frames))


@pytest.mark.parametrize("axis",["X","Z","Y"])
def test_terminal_single_physical_fault_exact_symplectic_flips(model,axis):
    c=model.compiled;cut=len(c.circuit)
    for q in range(4):
        block=c.open_logical_outputs[f"Q{q}"]
        prep=next(p for p in reversed(c.preparations) if p.block_id==block)
        wire=c.physical_qubit_map[block,prep.data_ids[0]]
        samples=sample_fault(model,cut,[wire],axis)
        result=model.decoder.replay(samples)
        expected=[((axis in "XY" and wire in o.physical_z) ^ (axis in "ZY" and wire in o.physical_x))
                  for o in model.probe.observables]
        assert np.array_equal(result.stabilizer_flips,np.broadcast_to(expected,(3,4)))
        assert np.array_equal(result.stabilizer_flips,independent_terminal(model,samples,result.frames))


def test_wrong_order_omitted_readout_identity_and_xz_order_detected(model,monkeypatch):
    d=model.decoder;samples=model.circuit.compile_sampler(seed=929).sample(7)
    for order in (tuple(reversed(d.requests.order)),d.requests.order[:-1]):
        with monkeypatch.context() as patch:
            patch.setattr(d,"requests",replace(d.requests,order=order))
            with pytest.raises(ValueError,match="order"):d.replay(samples)
    class Omitted:
        def decode_batch(self,*args):return None
    first=next(iter(d.readout_decoders))
    with pytest.raises(ValueError,match="omission"):
        d.replay(samples,readout_decoders={**d.readout_decoders,first:Omitted()})
    replay=d.replay(samples,trace=True)
    trace=next(t for t in replay.stages if t.kind=="boundary" and t.result.correction.bits.any())
    correction=trace.result.correction
    mutations=[dict(source_fingerprint="0"*64),dict(block_use_id=replace(correction.block_use_id,epoch=999)),
               dict(input_ids=tuple(reversed(correction.input_ids)))]
    class Bad:
        def decode_batch(self,*args):return bad
    for mutation in mutations:
        bad=replace(trace.result,correction=replace(correction,**mutation))
        with pytest.raises(ValueError,match="source/use/input"):
            d.replay(samples,boundary_decoders={**d.boundary_decoders,trace.module_id:Bad()})
    swapped=np.concatenate(np.split(correction.bits,2,axis=1)[::-1],axis=1)
    bad=replace(trace.result,correction=replace(correction,bits=swapped))
    with pytest.raises(ValueError,match="net-sector"):
        d.replay(samples,boundary_decoders={**d.boundary_decoders,trace.module_id:Bad()})


def test_nonzero_prior_sectors_and_stale_sector_are_detected(model):
    d=model.decoder;samples=model.circuit.without_noise().compile_sampler(seed=931).sample(7)
    # Valid alternative: infer the same record errors but leave the preparation
    # Pauli in its native nonzero sector instead of applying a CSS correction.
    class SectorOnly:
        def __init__(self,adapter):self.adapter=adapter
        def decode_batch(self,r,inputs):
            result=self.adapter.decode_batch(r,inputs)
            bits=np.zeros_like(result.correction.bits)
            sector=inputs.records[:,self.adapter.last_columns]^result.predicted_record_errors
            return replace(result,correction=replace(result.correction,bits=bits),net_sector=sector)
    adapters={k:SectorOnly(a) for k,a in d.boundary_decoders.items()}
    replay=d.replay(samples,boundary_decoders=adapters,trace=True)
    assert replay.sectors.any() and not replay.stabilizer_flips.any()
    seen=set();nonzero=False;multi_owner=False
    for t in replay.stages:
        if t.kind=="boundary":seen.add(t.module_id);continue
        r=d.readouts[t.module_id]
        expected=np.column_stack([np.logical_xor.reduce(replay.sectors[:,s],axis=1) if s else np.zeros(7,bool)
            for s in r.sector_map.supports])^r.sector_constant
        assert np.array_equal(expected,t.inputs.expected_sector)
        assert all(d.requests.sector_input_ids[i][0] in seen for s in r.sector_map.supports for i in s)
        nonzero |= expected.any()
        multi_owner |= any(len({d.requests.sector_input_ids[i][0] for i in s})>3 for s in r.sector_map.supports)
    assert nonzero and multi_owner  # includes transport across logical CNOTs.
    class Stale:
        def __init__(self,adapter):self.adapter=adapter
        def decode_batch(self,r,inputs):
            return self.adapter.decode_batch(r,replace(inputs,expected_sector=np.zeros_like(inputs.expected_sector)))
    with pytest.raises(ValueError,match="sector/syndrome"):
        d.replay(samples,boundary_decoders=adapters,
                 readout_decoders={k:Stale(a) for k,a in d.readout_decoders.items()})


def test_readout_correction_must_actually_be_applied(model,monkeypatch):
    from logical_to_stim_converter.decoding import OfflineFrameBatch
    samples=model.circuit.without_noise().compile_sampler(seed=933).sample(3)
    first=next(iter(model.decoder.readouts.values()))
    samples[:,first.record_ids[0]]^=True  # force a nonzero capacity correction.
    apply=OfflineFrameBatch.apply
    def skip(self,correction):
        if correction.boundary_id not in model.decoder.readouts:apply(self,correction)
    monkeypatch.setattr(OfflineFrameBatch,"apply",skip)
    with pytest.raises(ValueError,match="omitted|stale"):model.decoder.replay(samples)
