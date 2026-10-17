"""Physical Hex factory, with optional cached module-local Stim inference."""

import numpy as np

from knill_bench.adapters.factory_frames import FRAME_IMPLEMENTATION
from knill_bench.data.storage_v2 import PointWriter
from .execution import execute_points
from .run_v2 import RunStore


def compile_point(point, *, seed, create_codecapacity_dem=False, skip_circuit_validation=False):
    """Build/compile once locally, with two reused supports and one final oracle.

    Full bundle validation runs unless explicitly skipped. Matching-model
    support and runtime frame checks remain active in either mode.
    True excludes preparation/earlier-stage residuals from the PRIOR ONLY.
    The physical circuit and native causal frame processing retain them.
    UnsupportedProjectedModel propagates; there is no null-gap/fallback mode.
    Theta is deliberately absent from this physical/decoder interface.
    """
    from knill_bench.adapters.hex_factory import compile_local_factory
    if point.kind != "logical_zero_factory":
        raise ValueError("factory compilation requires a logical_zero_factory point")
    if type(create_codecapacity_dem) is not bool:
        raise ValueError("create_codecapacity_dem must be bool")
    return compile_local_factory(point, seed=seed, create_codecapacity_dem=create_codecapacity_dem,
                                 skip_circuit_validation=skip_circuit_validation)


def _run_point(path, point, shots, batch_size, seed, *, create_codecapacity_dem=False,
               skip_circuit_validation=False):
    bundle, compiled = compile_point(point, seed=seed, create_codecapacity_dem=create_codecapacity_dem,
                                    skip_circuit_validation=skip_circuit_validation)
    units = "log_weight" if create_codecapacity_dem else "hamming_weight"
    local_policy = compiled.cache_key.decoder_policy == "factory_module_local_stim_v1"
    execution = dict(bundle.metadata)
    execution.update(
        memory_basis="z", final_readout=point.final_readout,
        teleportation_readout="noisy_destructive_Z", teleportation_readout_error=point.p,
        score_units=units, create_codecapacity_dem=create_codecapacity_dem,
        skip_circuit_validation=skip_circuit_validation,
        circuit_validation="skipped_by_configuration" if skip_circuit_validation else "full_native",
        preparation_frame_implementation=(FRAME_IMPLEMENTATION if compiled.cache_key.decoder_policy
                                          in {"factory_module_local_stim_v1", "factory_causal_hamming_v1"}
                                          else "hex_native"),
        decoder="pymatching_mwpm", decoder_policy=compiled.cache_key.decoder_policy,
        gap_policy=compiled.cache_key.gap_policy,
        projected_prior_sha256=[p.configuration_sha256 for p in compiled.projected_priors],
        projected_model_sha256=[p.model_sha256 for p in compiled.projected_priors],
        prior_policy=("module_local_stim_dem" if local_policy else
                      "circuit_informed_projected" if create_codecapacity_dem else "hex_legacy_hamming"),
        prior_scope=("post_preparation_native_coupling_and_noisy_readout" if local_policy else None),
        preparation_residual_errors_in_prior=False if local_policy else None,
        earlier_stage_residual_errors_in_prior=False if local_policy else None,
        boundary_noise="native_only_no_added_channel",
        local_module_sha256=[p.physical_module_sha256 for p in compiled.projected_priors] if local_policy else [],
        local_analysis_sha256=[p.analysis_circuit_sha256 for p in compiled.projected_priors] if local_policy else [],
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
                           create_codecapacity_dem=store.document.config.create_codecapacity_dem,
                           skip_circuit_validation=store.document.config.skip_circuit_validation)
        return store.path
