"""Public-only Clifford/group, allocation, parallelism and terminal checks.

Only noiseless validation batches are sampled here (<=7 shots). Noisy decoding
has separate Phase 4 tests. Depth 32 is compilation/validation only.
"""

from dataclasses import replace
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pytest
import stim

from logical_to_stim_converter import NoiseModel, parse_logical_circuit
from logical_to_stim_converter.decoding import CorrectionBatch, make_stage_requests
from knill_bench.converter.deep_clifford import CompiledDeepClifford, validate_stabilizers
from knill_bench.experiments.config_v2 import load_config, parse_config

FIXTURES = Path(__file__).parent / "fixtures"


def point(**updates):
    raw = dict(schema_version=2,kind="converter_deep_clifford",noise="converter_uniform",
        sweep=dict(d=[3],p=[0.]),depth=2,circuit_seed=19)
    raw.update(updates)
    return next(parse_config(raw).points())


@pytest.fixture(scope="module")
def small():
    return CompiledDeepClifford(point())


@pytest.fixture(scope="module")
def repeated():
    return CompiledDeepClifford(point(depth=3,n_r=2,circuit_seed=41))


@pytest.fixture(scope="module")
def m9():
    return CompiledDeepClifford(point(resource_preparation="ideal",p_st_multiplier=3.,
        sweep=dict(d=[3],p=[.001])))


def logical_stim(logical):
    reference = stim.Circuit()
    for layer in logical.layers:
        for q, gate in enumerate(layer.single_qubit):
            reference.append(gate,[q])
        for control,target in layer.cnots:
            reference.append("CX",[control,target])
    return reference


def paulis(products,n=4):
    rows = []
    for product in products:
        row = stim.PauliString(n)
        row.sign = product.sign
        for name,axis in product.factors:
            row[int(name[1:])] = axis
        rows.append(row)
    return rows


def group(rows):
    result = {str(stim.PauliString(len(rows[0])))}
    for row in rows:
        result.update(str(stim.PauliString(element)*row) for element in tuple(result))
    return result


def assert_signed_group(compiled, logical):
    reference = logical_stim(logical)
    expected = []
    for q in range(logical.logical_qubits):
        initial = stim.PauliString(logical.logical_qubits);initial[q] = "X"
        expected.append(initial.after(reference))  # G_i = U X_i U dagger, including signs.
    actual = paulis(compiled.logical_output_stabilizers,logical.logical_qubits)
    assert group(actual) == group(expected)
    assert len(group(actual)) == 2**logical.logical_qubits
    assert all(a.commutes(b) for a,b in itertools.combinations(actual,2))
    assert all(row.sign in (1,-1) for row in actual)
    stim.Tableau.from_stabilizers(actual,allow_redundant=False,allow_underconstrained=False)


@pytest.mark.parametrize("fixture",["small","repeated","m9"])
def test_independent_ideal_clifford_signed_group_including_pauli_phases(request,fixture):
    model = request.getfixturevalue(fixture)
    assert_signed_group(model.compiled,model.logical_circuit)
    gates = {gate for layer in model.logical_circuit.layers for gate in layer.single_qubit}
    assert "Y" in gates
    assert any(row.sign == -1 for row in paulis(model.logical_stabilizers))


def test_stabilizer_validator_rejects_dependent_noncommuting_and_retired_products(small):
    from logical_to_stim_converter import LogicalPauliProduct
    ids = tuple(f"Q{q}" for q in range(4))
    for products in (small.logical_stabilizers[:-1],
        (small.logical_stabilizers[0],)*4,
        (LogicalPauliProduct({"Q0":"X"}),LogicalPauliProduct({"Q0":"Z"}),
         LogicalPauliProduct({"Q1":"X"}),LogicalPauliProduct({"Q2":"X"})),
        (*small.logical_stabilizers[:3],LogicalPauliProduct({"retired":"X"}))):
        with pytest.raises(ValueError):validate_stabilizers(products,ids)


def test_three_patches_each_recycling_epochs_and_every_teleportation_output(repeated):
    c = repeated.compiled
    c.validate_metadata()
    assert len({bid for bid,_ in c.physical_qubit_map}) == 12
    assert len(c.relocation_history) == 4*3*2
    assert len(c.block_uses) == 4*(1+2*3*2)
    uses = {u.use_id:u for u in c.block_uses}
    assert len(uses) == len(c.block_uses)
    for q in range(4):
        previous = next(p.block_use_id for p in c.preparations if p.logical_id == f"Q{q}")
        for cycle in range(6):
            relocation, = (r for r in c.relocation_history if r.composite_id == f"ec{cycle}_q{q}")
            current,a,b = ((0,1,2),(2,0,1),(1,2,0))[cycle%3]
            assert relocation.source_use_id == previous
            assert relocation.source_block_id == f"P{q}_{current}"
            assert relocation.output_block_id == f"P{q}_{b}"
            resources = [p for p in c.preparations if p.logical_id in {f"A{cycle}_{q}",f"B{cycle}_{q}"}]
            assert {p.block_id for p in resources} == {f"P{q}_{a}",f"P{q}_{b}"}
            assert all(p.rounds == 3 and p.block_use_id != previous for p in resources)
            previous = relocation.output_use_id
        assert c.open_logical_outputs[f"Q{q}"] == previous.block_id
        assert c.orientations[f"Q{q}"] == 0
    for patch in {u.block_id for u in uses}:
        ordered = sorted((u for u in c.block_uses if u.use_id.block_id == patch),key=lambda u:u.use_id.epoch)
        assert [u.use_id.epoch for u in ordered] == list(range(len(ordered)))
        for previous,current in zip(ordered,ordered[1:]):
            assert previous.terminal_module_id is not None
            assert previous.time_layer_stop <= current.time_layer_start
            assert current.reset_module_id != previous.reset_module_id


def module_layers(compiled, select):
    names = {f.module_id for f in compiled.fragments if select(f)}
    return {layer.index for layer in compiled.time_layers if names & set(layer.operation_by_block.values())}


def test_full_native_barriers_and_parallel_factory_overlap(repeated):
    c = repeated.compiled
    previous = module_layers(c,lambda f:f.operation_id is not None and f.operation_id.startswith("initial_q"))
    by_module = {f.module_id:f for f in c.fragments}
    for index in range(3):
        singles = module_layers(c,lambda f:f.operation_id is not None and f.operation_id.startswith(f"layer{index}_q"))
        cnots = module_layers(c,lambda f:f.operation_id is not None and f.operation_id.startswith(f"layer{index}_cx"))
        assert max(previous) < min(singles) and max(singles) < min(cnots)
        assert len(cnots) == 1
        previous = cnots
        for repetition in range(2):
            cycle = index*2+repetition
            names = {f"ec{cycle}_q{q}" for q in range(4)}
            interval = module_layers(c,lambda f:bool(set(f.composite_ids) & names))
            assert max(previous) < min(interval)
            stages = []
            for layer in c.time_layers:
                owners = {cid for mid in set(layer.operation_by_block.values())
                    if by_module[mid].operation_type == "LogicalInit"
                    for cid in by_module[mid].composite_ids if cid in names}
                stages.append(len(owners))
            assert max(stages) == 4
            previous = interval
    final = module_layers(c,lambda f:f.operation_id is not None and f.operation_id.startswith("final_se_q"))
    assert max(previous) < min(final)


def test_parallel_circuit_is_shorter_than_explicitly_serialized_factories(small):
    lines, output = small.lstim_source.splitlines(), []
    index = 0
    while index < len(lines):
        if lines[index] == "PARALLEL {" and lines[index+1].startswith("KNILL_EC["):
            index += 1
            while lines[index] != "}":
                output.append(lines[index]);index += 1
        else:output.append(lines[index])
        index += 1
    serial = parse_logical_circuit("\n".join(output)+"\n").compile(allow_open_outputs=True)
    serial.validate_metadata()
    assert len(small.compiled.time_layers) < len(serial.time_layers)
    assert group(paulis(serial.logical_output_stabilizers)) == group(paulis(small.logical_stabilizers))


def test_native_prefix_binding_and_orientation_after_every_cycle(small):
    lines = small.lstim_source.splitlines()
    cycle = 0
    for index,line in enumerate(lines):
        if line != "PARALLEL {" or not lines[index+1].startswith("KNILL_EC["):continue
        stop = lines.index("}",index)
        prefix = parse_logical_circuit("\n".join(lines[:stop+1])+"\n").compile(allow_open_outputs=True)
        prefix.validate_metadata()
        assert len(prefix.relocation_history) == 4*(cycle+1)
        output = (2,1,0)[cycle%3]
        assert prefix.open_logical_outputs == {f"Q{q}":f"P{q}_{output}" for q in range(4)}
        assert all(prefix.orientations[f"Q{q}"] == 0 for q in range(4))
        partial = replace(small.logical_circuit,layers=small.logical_circuit.layers[:cycle+1])
        assert_signed_group(prefix,partial)
        cycle += 1
    assert cycle == 2


def test_native_parallel_overlap_and_missing_reset_conflicts_are_rejected(small):
    overlap = small.lstim_source.replace("KNILL_EC[ec0_q1](3) Q1 A0_1 B0_1",
                                       "KNILL_EC[ec0_q1](3) Q0 A0_1 B0_1")
    surviving_reset = small.lstim_source.replace("BIND A1_0 P0_0","BIND A1_0 P0_2")
    for source in (overlap,surviving_reset):
        with pytest.raises(ValueError):parse_logical_circuit(source).compile(allow_open_outputs=True)


def test_typed_resource_noise_and_ideal_initial_final_boundaries(m9):
    c = m9.compiled
    assert len(c.resource_preparation_boundaries) == 2*4*2
    assert not c.post_initialization_boundaries
    initial_uses = {p.block_use_id for p in c.preparations if p.logical_id.startswith("Q")}
    assert not initial_uses & {b.block_use_id for b in c.resource_preparation_boundaries}
    for boundary in c.resource_preparation_boundaries:
        channel = c.circuit[boundary.channel_instruction]
        assert channel.name == "DEPOLARIZE1" and channel.gate_args_copy() == [.003]
        assert [t.value for t in channel.targets_copy()] == [c.physical_qubit_map[q] for q in boundary.data_sites]
    initial = {f.module_id for f in c.fragments if f.operation_id and f.operation_id.startswith("initial_q")}
    final = {f.module_id for f in c.fragments if f.operation_id and f.operation_id.startswith("final_se_q")}
    assert len(initial) == len(final) == 4
    for module in initial | final:
        body = stim.Circuit()
        for instruction in c.circuit:
            if instruction.tag == module:body.append(instruction)
        assert body == body.without_noise()
    assert any(i.name == "DEPOLARIZE2" and i.gate_args_copy() == [.001] for i in c.circuit)
    assert m9.metadata["generation_only"] and m9.metadata["decoder_status"] == "not_constructed_generation_only"


def perfect_recorded_sector_frames(model,samples):
    """Test-only exact d3 representatives from all 512 physical X/Z patterns.

    Perfect measurements only. No terminal record affects correction selection.
    This is a finite algebraic preparation check, not a noisy decoder.
    """
    raw,_ = model.probe.split_measurements(samples)
    frames = model.frame_plan.start(raw,source_fingerprint=model.probe.source_fingerprint)
    requests = make_stage_requests(model.compiled)
    boundaries = {r.module_id:r for r in requests.boundaries}
    patterns = np.array(list(itertools.product([0,1],repeat=9)),dtype=np.uint8)
    for kind,module in requests.order:
        if kind != "boundary":continue
        request = boundaries[module]
        assert all(i < model.probe.original_measurement_count for i in request.last_record_ids)
        current = frames.interpreted_measurements[:,request.last_record_ids]
        parts = []
        for basis in ("Z","X"):
            h = request.check_matrix(basis)
            syndrome = current[:,[i for i,c in enumerate(request.checks) if c.basis == basis]]
            prep = request.preparation
            if prep is not None and prep.basis == basis:
                support = prep.logical_x if basis == "X" else prep.logical_z
                h = np.vstack((h,[q in support for q in request.data_ids]))
                syndrome = np.column_stack((syndrome,np.zeros(len(raw),dtype=bool)))
            possible = (patterns @ h.T % 2).astype(bool)
            selected = []
            for target in syndrome:
                matches = np.flatnonzero(np.all(possible == target,axis=1))
                assert len(matches)
                selected.append(patterns[matches[0]])
            parts.append(np.asarray(selected,dtype=bool))
        frame_boundary = model.frame_plan.boundary_by_id[module]
        frames.apply(CorrectionBatch(model.probe.source_fingerprint,module,np.concatenate(parts,axis=1),
            request.block_use_id,frame_boundary.input_ids))
    return frames


@pytest.mark.parametrize("fixture",["small","repeated"])
def test_noiseless_signed_terminal_state_after_native_frame_correction(request,fixture):
    model = request.getfixturevalue(fixture)
    samples = model.circuit.compile_sampler(seed=331).sample(7)
    raw,terminal = model.probe.split_measurements(samples)
    assert raw.shape[1] == model.compiled.circuit.num_measurements
    assert samples.shape == (7,raw.shape[1]+4)
    assert set(terminal.ravel()) == {False,True}
    frames = perfect_recorded_sector_frames(model,samples)
    assert not model.probe.corrected_flips(samples,frames).any()
    changed = samples.copy();changed[:,model.probe.measurement_indices] ^= True
    other = perfect_recorded_sector_frames(model,changed)
    assert np.array_equal(frames.final_x,other.final_x) and np.array_equal(frames.final_z,other.final_z)
    assert model.probe.corrected_flips(changed,other).all()


def test_probe_circuit_and_metadata_preserve_canonical_prefix_and_signed_support(small):
    probe,c = small.probe,small.compiled
    assert small.circuit == probe.circuit and small.circuit != c.circuit
    assert small.circuit[:len(c.circuit)] == c.circuit
    assert probe.original_measurement_count == len(c.measurements)
    assert probe.measurement_indices == tuple(range(len(c.measurements),len(c.measurements)+4))
    assert all(obs.expected_value == 0 for obs in probe.observables)
    assert probe.source_fingerprint == small.frame_plan.source_fingerprint
    assert len([i for i in small.circuit if i.name == "MPP"]) == 1
    assert not any(i.name == "MPP" for i in c.circuit)
    for info in probe.observables:
        assert info.physical_x or info.physical_z
        assert info.physical_sign in (-1,1)
        assert all(c.open_logical_outputs[name] == use.block_id
            for (name,_),use in zip(info.logical_observable.factors,info.block_use_ids,strict=True))
    final = [f for f in c.fragments if f.operation_id and f.operation_id.startswith("final_se_q")]
    assert len(final) == 4 and all(f.operation_type == "SyndromeExtraction" for f in final)
    for fragment in final:
        records = [m for m in c.measurements if m.module_id == fragment.module_id]
        # Native round indices continue across a patch use, rather than restarting at zero.
        assert len({m.key.round_index for m in records}) == 1
        assert len(records) == small.point.d**2-1


@pytest.mark.parametrize("depth",[2,3])
def test_structural_and_signed_invariants_against_pinned_public_examples(depth,request):
    model = request.getfixturevalue("small" if depth == 2 else "repeated")
    manifest = json.loads((FIXTURES/"converter_deep_references.json").read_text())
    path = FIXTURES/f"converter_deep_reference_d3_depth{depth}.lstim"
    source = path.read_text()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[path.name]["source_sha256"]
    c = parse_logical_circuit(source).compile(allow_open_outputs=True,noise_model=NoiseModel())
    c.validate_metadata()
    assert len({bid for bid,_ in c.physical_qubit_map}) == model.metadata["physical_patch_count"] == 12
    assert len(c.relocation_history) == 4*depth
    assert len(model.compiled.relocation_history) == 4*depth*model.point.n_r
    assert len(c.logical_output_stabilizers) == len(model.logical_stabilizers) == 4
    assert all(c.orientations[f"Q{q}"] == model.compiled.orientations[f"Q{q}"] == 0 for q in range(4))
    # The public example has extra post-CNOT Paulis. Check its own signed group;
    # its logical gate instance is intentionally different from the paper ordering.
    reference = stim.Circuit()
    for layer in range(depth):
        reference.append("H",[1,3] if layer%2 == 0 else [0,2])
        reference.append("CX",[0,1,2,3] if layer%2 == 0 else [1,2,3,0])
        for q,axis in enumerate("XYZY"):reference.append(axis,[q])
    expected = []
    for q in range(4):
        initial = stim.PauliString(4);initial[q] = "X";expected.append(initial.after(reference))
    assert group(paulis(c.logical_output_stabilizers)) == group(expected)


def test_d5_compilation_preserves_logical_instance_across_distance_probability_and_nr(small):
    model = CompiledDeepClifford(replace(small.point,d=5,r_0=5,r_plus=5,p=.002))
    assert model.logical_circuit == small.logical_circuit
    assert model.metadata["logical_instance_sha256"] == small.metadata["logical_instance_sha256"]
    assert group(paulis(model.logical_stabilizers)) == group(paulis(small.logical_stabilizers))
    assert len({bid for bid,_ in model.compiled.physical_qubit_map}) == 12
    assert_signed_group(model.compiled,model.logical_circuit)


def test_depth_32_d3_compiles_validates_and_keeps_twelve_patches():
    # Explicit user-requested compilation envelope. Never sample this circuit.
    config = load_config(FIXTURES.parents[1]/"configs/templates/converter_deep_clifford_depth32.yaml").config
    model = CompiledDeepClifford(next(config.points()))
    model.compiled.validate_metadata()
    assert model.point.depth == 32 and len(model.compiled.relocation_history) == 128
    assert len({bid for bid,_ in model.compiled.physical_qubit_map}) == 12
    assert model.circuit.num_measurements == model.probe.original_measurement_count+4
    assert model.metadata["parallel_resource_overlap_min"] == 4
    assert_signed_group(model.compiled,model.logical_circuit)
