"""Batched logical-zero factory using only the tested Hex factory interfaces."""

import numpy as np

from knill_bench.data.storage_v2 import PointWriter
from .execution import execute_points
from .run_v2 import RunStore


def compile_point(point, *, seed, create_codecapacity_dem=False):
    """Build/compile once locally, with two reused supports and one final oracle.

    Hex validates signed frames/causal boundaries and projected-model support.
    UnsupportedProjectedModel propagates; there is no null-gap/fallback mode.
    Theta is deliberately absent from this physical/decoder interface.
    """
    from hex_qec.modularisation import PreparationPlan
    from hex_qec.protocols import FactoryCircuitBuilder, RotatedSurfaceCodeAdapter
    from hex_qec.simulation import CompiledFactory
    if point.kind != "logical_zero_factory":
        raise ValueError("factory compilation requires a logical_zero_factory point")
    bundle = FactoryCircuitBuilder(
        RotatedSurfaceCodeAdapter(point.d), PreparationPlan(point.r_0, point.r_plus),
        point.p, T_tel=point.T_tel,
    ).build()
    compiled = CompiledFactory.from_bundle(bundle, seed=seed,
                                           create_codecapacity_dem=create_codecapacity_dem)
    return bundle, compiled


def _run_point(path, point, shots, batch_size, seed, *, create_codecapacity_dem=False):
    bundle, compiled = compile_point(point, seed=seed, create_codecapacity_dem=create_codecapacity_dem)
    units = "log_weight" if create_codecapacity_dem else "hamming_weight"
    execution = dict(bundle.metadata)
    execution.update(
        memory_basis="z", final_readout=point.final_readout,
        teleportation_readout="noisy_destructive_Z", teleportation_readout_error=point.p,
        score_units=units, create_codecapacity_dem=create_codecapacity_dem,
        decoder="pymatching_mwpm", decoder_policy=compiled.cache_key.decoder_policy,
        gap_policy=compiled.cache_key.gap_policy,
        projected_prior_sha256=[p.configuration_sha256 for p in compiled.projected_priors],
        projected_model_sha256=[p.model_sha256 for p in compiled.projected_priors],
        blocks=[dict(name=b.name, data_qubits=len(b.data_qubits), qubits=len(b.qubits)) for b in bundle.blocks],
        stage_roles=[dict(stage=s.index, consumed=s.consumed_block, surviving=s.surviving_block)
                     for s in bundle.stages],
        measurement_records=bundle.circuit.num_measurements, simulator_qubits=bundle.circuit.num_qubits,
        oracle_record_start=bundle.oracle.measurements.start,
        postselection=False, trajectory="full_fixed_T_no_retries_or_early_abort",
        sampling="one_point_seeded_stim_sampler_advanced_in_fixed_batches",
        zero_noise_gap_policy="finite_unit_hamming" if not create_codecapacity_dem else "unsupported",
    )
    with PointWriter(path, point, expected_shots=shots) as writer:
        for start in range(0, shots, batch_size):
            count = min(batch_size, shots - start)
            raw = compiled.sample_measurements(count)
            decoded = compiled.decode(raw, shot_id_start=start)  # Offline, after sampling.
            gaps = decoded.gaps
            if (decoded.gap_units != units or gaps is None or gaps.dtype != np.float64
                    or gaps.shape != (count, point.T_tel) or not np.isfinite(gaps).all()
                    or (gaps < 0).any()):
                raise ValueError("Hex factory must return finite nonnegative per-stage gaps in declared units")
            if not decoded.frame_resolved.all():
                raise RuntimeError("Hex factory did not resolve every stage frame")
            writer.write_batch(decoded.shot_id, decoded.logical_error, gaps)
        result = writer.commit()
    return result, execution


def run(document, *, resume_path=None):
    if document.config.kind != "logical_zero_factory":
        raise ValueError("factory runner requires kind logical_zero_factory")
    with (RunStore.create(document) if resume_path is None else RunStore.resume(resume_path)) as store:
        if store.document.config != document.config:
            raise ValueError("resume document must match the saved run configuration")
        if store.metadata["status"] != "complete":
            execute_points(store, _run_point,
                           create_codecapacity_dem=store.document.config.create_codecapacity_dem)
        return store.path
