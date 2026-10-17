"""Ordinary noisy-Z memory using Hex's unmodified repeated-SE circuit."""

from dataclasses import dataclass
import hashlib

import numpy as np

from hex_qec.circuit_generation import get_parity_check_matrices, stabilizer_measurement_circuit
from knill_bench.decoding.dem import convert_dem
from knill_bench.decoding.observable_gap import ObservableMWPM


@dataclass(frozen=True)
class MemoryBatch:
    logical_error: np.ndarray
    gaps: np.ndarray | None


class HexMemory:
    def __init__(self, point, *, seed):
        if point.kind != "se_memory":
            raise ValueError("HexMemory requires an se_memory point")
        self.point = point
        self.circuit = stabilizer_measurement_circuit(
            get_parity_check_matrices("surface", point.d), pauli="z",
            syndrome_repetitions=point.rounds, prob=point.p, surface_code=True,
            disable_final_detectors=False,
        )
        if self.circuit.num_observables != 1:
            raise ValueError("ordinary Z memory requires exactly one logical observable")
        # Keep complete independent events, including their full observable
        # signatures. No separator splitting or lost correlated mechanisms.
        dem = self.circuit.detector_error_model(allow_gauge_detectors=False, approximate_disjoint_errors=False)
        model = convert_dem(dem)
        if np.any((model.q <= 0) | (model.q >= 1)):
            raise ValueError("memory DEM requires stochastic probabilities strictly between zero and one")
        weights = np.log1p(-model.q) - np.log(model.q)
        self.decoder = ObservableMWPM(model.h, model.l, weights, get_logicalgap=point.get_logicalgap)
        self.converter = self.circuit.compile_m2d_converter()
        self.sampler = self.circuit.compile_sampler(seed=seed)
        self.metadata = dict(
            protocol="hex_repeated_se_memory", memory_basis="z", rounds=point.rounds,
            noisy_se_rounds=point.rounds, initial_boundary="noisy_physical_zero",
            initial_data="physical_zero_reset_with_X_error", physical_error=point.p, noise=point.noise,
            teleportations=0, separate_preparation_rounds=0, live_blocks=1,
            final_readout=point.final_readout, final_readout_error=point.p, terminal_ideal_oracle=False,
            decoder="pymatching_mwpm", decoder_policy="full_circuit_graphlike_dem_mwpm_v1",
            detector_sector="Z_check_history_and_noisy_final_Z",
            prior_policy="full_circuit_stim_dem", graph_model="complete_independent_dem_events",
            get_logicalgap=point.get_logicalgap,
            gap_policy="opposite_observable_class_spacetime_mwpm_v1" if point.get_logicalgap else None,
            gap_scope="whole_memory_experiment" if point.get_logicalgap else None,
            score_units="log_weight" if point.get_logicalgap else None,
            circuit_sha256=hashlib.sha256(str(self.circuit).encode()).hexdigest(),
            dem_sha256=hashlib.sha256(str(dem).encode()).hexdigest(),
            decoder_model_sha256=self.decoder.model_sha256,
            measurement_records=self.circuit.num_measurements, simulator_qubits=self.circuit.num_qubits,
            detectors=self.circuit.num_detectors, observables=1, dem_events=model.h.shape[1],
            postselection=False, sampling="one_point_seeded_stim_sampler_advanced_in_fixed_batches",
        )

    def sample(self, shots):
        return self.sampler.sample(shots=shots)

    def decode_detectors(self, detectors):
        """Inference receives detector events only, never observed logical truth."""
        return self.decoder.decode_batch(detectors)

    def decode_batch(self, measurements):
        raw = np.asarray(measurements)
        if (raw.dtype != bool or raw.ndim != 2 or not len(raw)
                or raw.shape[1] != self.circuit.num_measurements):
            raise ValueError("require a nonempty aligned bool measurement batch")
        detectors, actual = self.converter.convert(measurements=raw, separate_observables=True)
        decoded = self.decode_detectors(detectors)
        # Evaluate truth only after inference and complementary scoring finish.
        error = decoded.prediction ^ actual[:, 0]
        gaps = None if decoded.gap is None else decoded.gap[:, None]
        if self.point.get_logicalgap and (gaps is None or gaps.dtype != np.float64
                                         or gaps.shape != (len(raw), 1) or not np.isfinite(gaps).all()
                                         or (gaps < 0).any()):
            raise ValueError("memory complementary gap must be finite nonnegative float64")
        return MemoryBatch(error, gaps)
