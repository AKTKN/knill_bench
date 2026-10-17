"""Packed preparation arithmetic and opt-out validation retain native physics."""

from dataclasses import fields

import numpy as np
import pytest
from scipy import sparse

from hex_qec.protocols.logical_zero_factory import FactoryCircuitBundle
from hex_qec.simulation.factory import FactoryBatchDecoder
from knill_bench.adapters import hex_factory as local
from knill_bench.adapters.factory_frames import FactoryPreparationPlan, PackedGF2Map
from knill_bench.experiments import logical_zero_factory as runner
from knill_bench.experiments.config_v2 import ExperimentPoint, digest, parse_config
from knill_bench.experiments.seeds import point_seed


@pytest.mark.parametrize("inputs,outputs", [(0, 9), (9, 0), (1, 1), (7, 8), (8, 7), (9, 17), (263, 25)])
def test_packed_gf2_matches_independent_integer_product(inputs, outputs):
    rng = np.random.default_rng(18)
    matrix = rng.integers(0, 4, (inputs, outputs), dtype=np.int64)
    bits = rng.integers(0, 2, (7, inputs), dtype=np.uint8)
    for representation in (matrix, sparse.csc_matrix(matrix)):
        mapping = PackedGF2Map(representation)
        np.testing.assert_array_equal(mapping.apply(bits), (bits @ matrix % 2).astype(bool))
        assert mapping.apply(bits[:0]).shape == (0, outputs)
    with pytest.raises(ValueError, match="width"):
        mapping.apply(np.zeros((7, inputs+1), bool))


@pytest.mark.parametrize("d,T,p,prior", [(3, 1, 0., False), (3, 3, .003, False),
                                        (3, 3, .03, True), (5, 2, .003, True)])
def test_native_and_optimized_frames_and_all_decode_fields_match(d, T, p, prior):
    case = ExperimentPoint("logical_zero_factory", d, p, 2, 3, T)
    bundle, compiled = runner.compile_point(case, seed=73, create_codecapacity_dem=prior)
    raw = compiled.sample_measurements(7)
    original = raw.copy()
    # Reference uses original full-history correction, with exactly the same
    # local teleportation models; do not build the old projected prior.
    reference = FactoryBatchDecoder(bundle)
    reference._projected_gaps = compiled._decoder._projected_gaps
    reference.projected_priors = compiled.projected_priors
    for plan in bundle.preparation_frames:
        records = raw[:, plan.region.measurements.slice]
        expected = plan.resolve(records)
        fast = compiled._decoder._plans[plan.region.measurements.start]
        actual = fast.resolve(records)
        np.testing.assert_array_equal(actual.x, expected.x)
        np.testing.assert_array_equal(actual.z, expected.z)
        assert isinstance(fast, FactoryPreparationPlan)
    expected = reference.decode(raw, shot_id_start=19)
    actual = compiled.decode(raw, shot_id_start=19)
    for field in fields(expected):
        np.testing.assert_array_equal(getattr(actual, field.name), getattr(expected, field.name))
    np.testing.assert_array_equal(raw, original)
    plus = [compiled._decoder._plans[s.preparations[-1].measurements.start] for s in bundle.stages]
    # H5 has distinct templates for A and B; repeated resets of one support
    # reuse maps, while decoder ordering on different supports stays separate.
    for left in plus:
        for right in plus:
            if left.module is right.module:
                assert left._x_map is right._x_map and left._z_map is right._z_map


@pytest.mark.parametrize("prior", [False, True])
def test_skip_validation_is_opt_in_and_preserves_circuit_sampling_decoding(monkeypatch, prior):
    case = ExperimentPoint("logical_zero_factory", 3, .003, 1, 2, 2)
    validations = []
    validate = FactoryCircuitBundle.validate

    def counted(bundle):
        validations.append(bundle)
        return validate(bundle)

    monkeypatch.setattr(FactoryCircuitBundle, "validate", counted)
    bundle, checked = runner.compile_point(case, seed=21, create_codecapacity_dem=prior)
    assert len(validations) == 1
    skipped_bundle, skipped = runner.compile_point(case, seed=21, create_codecapacity_dem=prior,
                                                   skip_circuit_validation=True)
    assert len(validations) == 1
    assert type(skipped_bundle) is FactoryCircuitBundle
    assert local._H5_BUILD.__globals__["FactoryCircuitBundle"] is FactoryCircuitBundle
    assert checked.cache_key == skipped.cache_key
    assert bundle.circuit == skipped_bundle.circuit == skipped.circuit
    raw = checked.sample_measurements(7)
    np.testing.assert_array_equal(raw, skipped.sample_measurements(7))
    a, b = checked.decode(raw), skipped.decode(raw)
    for field in fields(a):
        np.testing.assert_array_equal(getattr(a, field.name), getattr(b, field.name))
    # The returned ordinary bundle still supports explicit full validation.
    skipped_bundle.validate()
    assert len(validations) == 2
    for invalid in (0, 1, "true", None):
        with pytest.raises(ValueError, match="bool"):
            runner.compile_point(case, seed=21, skip_circuit_validation=invalid)


def test_validation_option_config_hash_compatibility_and_physical_seed_independence():
    raw = dict(schema_version=2, kind="logical_zero_factory", name="validation",
               sweep=dict(d=[3], p=[.003]))
    default = parse_config(raw)
    full = parse_config(dict(raw, skip_circuit_validation=False))
    skipped = parse_config(dict(raw, skip_circuit_validation=True))
    assert default == full and not default.skip_circuit_validation
    old_canonical = default.as_dict()
    assert "skip_circuit_validation" not in old_canonical
    assert default.config_hash == digest(old_canonical)
    assert skipped.config_hash != full.config_hash
    assert parse_config(skipped.as_dict()) == skipped
    a, b = next(full.points()), next(skipped.points())
    assert a == b and a.case_id == b.case_id
    assert point_seed(full.master_seed, a) == point_seed(skipped.master_seed, b)
    for invalid in (0, 1, "true", None):
        with pytest.raises(ValueError, match="must be bool"):
            parse_config(dict(raw, skip_circuit_validation=invalid))
    with pytest.raises(ValueError, match="only for logical_zero_factory"):
        parse_config(dict(raw, kind="fig4d_reproduction", skip_circuit_validation=True))
