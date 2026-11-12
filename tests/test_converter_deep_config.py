"""Abstract gate distribution, repeatable RNG and strict Phase 3 settings."""

from dataclasses import replace
import json
import random
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

import pytest

from knill_bench.converter.deep_program import GENERATOR, deep_source, generate_logical_circuit
from knill_bench.experiments.config_v2 import parse_config


def raw(**updates):
    value = dict(schema_version=2, kind="converter_deep_clifford", noise="converter_uniform",
                 sweep=dict(d=[3, 5], p=[0., .001]), circuit_seed=19)
    value.update(updates)
    return value


def generated(seed):
    return generate_logical_circuit(depth=3, circuit_seed=seed).as_dict()


def test_defaults_roundtrip_and_generation_contract():
    c = parse_config(raw())
    assert c.logical_qubits == 4 and c.depth == 32 and c.n_r == 1
    assert c.input_preparation == "ideal" and c.r_0 == c.r_plus == "d"
    assert parse_config(c.as_dict()) == c
    assert next(c.points()).sampling_identity["program_contract"] == "converter_deep_clifford_program_v1"


@pytest.mark.parametrize("updates", [dict(input_preparation="noisy"), dict(logical_qubits=1),
    dict(logical_qubits=3), dict(logical_qubits=True), dict(depth=0), dict(n_r=0), dict(n_r="2"),
    dict(r_0=2,r_plus=2), dict(r_0="2*d",r_plus="2*d"), dict(p_st_multiplier=1.),
    dict(resource_preparation="ideal",p_st_multiplier=-1.),
    dict(resource_preparation="ideal",p_st_multiplier=float("nan")),
    dict(resource_preparation="ideal",p_st_multiplier=True),
    dict(resource_preparation="ideal",p_st_multiplier=1000.),
    dict(resource_preparation="noisy_d_rounds"), dict(post_rounds=1)])
def test_unsupported_deep_settings_fail_before_generation(updates):
    with pytest.raises(ValueError):
        parse_config(raw(**updates))


def test_ideal_resource_policy_default_and_resolved_probability():
    c = parse_config(raw(resource_preparation="ideal"))
    assert c.p_st_multiplier == 0. and parse_config(c.as_dict()) == c
    assert parse_config(raw(resource_preparation="ideal",p_st_multiplier=3.)).p_st_multiplier == 3.
    with pytest.raises(ValueError, match="every p"):
        parse_config(raw(resource_preparation="ideal",p_st_multiplier=2.,sweep=dict(d=[3],p=[.001,.5])))


def test_sequence_is_independent_of_all_physical_and_execution_controls():
    c = parse_config(raw(depth=3))
    reference = generated(19)
    state = random.getstate()
    for count in (1,2,3):
        changed = replace(c,n_r=count,workers=count,shots=7,master_seed=count)
        for point in changed.points():
            logical = generate_logical_circuit(logical_qubits=point.logical_qubits,
                depth=point.depth,circuit_seed=point.circuit_seed)
            assert logical.as_dict() == reference
            source = deep_source(point,logical)
            assert source.count("KNILL_EC[") == 4*3*count
            assert source.count("PATCH ") == 12
            assert source.count("SE[final_se") == 4
            labels = [line.split("[",1)[1].split("]",1)[0] for line in source.splitlines() if "[" in line]
            assert len(labels) == len(set(labels))
    assert random.getstate() == state


def test_seeded_call_order_golden_instance_and_depth_prefix():
    logical = generate_logical_circuit(depth=2,circuit_seed=19)
    assert logical.instance_hash == "d456a8d7614c37fffe6bf608e5a99e18a8c74fd6c0d5f765a842dc11b244d2d1"
    assert logical.as_dict()["generator"] == GENERATOR
    assert logical.layers == generate_logical_circuit(depth=32,circuit_seed=19).layers[:2]
    assert generated(20) == generated(20) and generated(19) != generated(20)
    assert len({json.dumps(generated(seed),sort_keys=True) for seed in range(16)}) == 16


def test_every_layer_has_one_hxyz_gate_per_qubit_and_uniform_perfect_pairing_convention():
    # Check the exact documented random draws, without a frequency/Monte Carlo criterion.
    rng = random.Random(123)
    logical = generate_logical_circuit(depth=32,circuit_seed=123)
    for layer in logical.layers:
        assert layer.single_qubit == tuple("HXYZ"[rng.randrange(4)] for _ in range(4))
        permutation = list(range(4));rng.shuffle(permutation)
        expected = []
        for i in (0,2):
            pair = tuple(permutation[i:i+2])
            expected.append(pair[::-1] if rng.getrandbits(1) else pair)
        assert layer.cnots == tuple(expected)
        assert sorted(q for pair in layer.cnots for q in pair) == list(range(4))


def test_seeded_logical_instances_match_under_spawn():
    with ProcessPoolExecutor(2,mp_context=multiprocessing.get_context("spawn")) as pool:
        assert list(pool.map(generated,[19,20,19])) == [generated(19),generated(20),generated(19)]


@pytest.mark.parametrize("count",[2,4,6])
def test_even_logical_qubit_generalization_is_explicit(count):
    c = parse_config(raw(logical_qubits=count,depth=2))
    logical = generate_logical_circuit(logical_qubits=count,depth=2,circuit_seed=19)
    assert all(len(layer.cnots) == count//2 for layer in logical.layers)
    assert deep_source(next(c.points()),logical).count("PATCH ") == 3*count
