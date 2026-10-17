"""Per-shot adapter for Hex's fixed full Knill protocol, with noisy readout.

Module construction follows protocols/knill_online_offline.py at pinned H5.
The existing bench local-frame machinery replaces Hex's much larger global
correction maps. Hex itself supplies every physical fragment and c_func.
"""

import copy
from dataclasses import dataclass

import numpy as np
import pymatching
from scipy.sparse import csc_matrix

from hex_qec.circuit_generation import noiseless_unitary_state_prep
from hex_qec.modularisation import (
    css_detector_module, logical_measurement_module, modularised_circuit,
    no_measurement_module, generate_state_prep_modules,
    generate_transversal_cnot_module, generate_bell_measurement_and_correction_module,
    generate_logical_measurement_module,
)
from knill_bench.codes import Code
from knill_bench.experiments.config_v2 import ExperimentPoint
from .hex_native import PackedFrame, _transition


@dataclass(frozen=True)
class FullKnillBatch:
    logical_error: np.ndarray
    corrected_measurements: np.ndarray


class HexFullKnill:
    """Compile once, sample raw batches, then decode those batches offline.

    T=1 is supported here for small protocol tests; the Fig.4(d) runner requires
    T=8. No postselection, terminal ideal oracle, or code-capacity reweighting.
    Native handles and templates belong to this point in this process only.
    """

    def __init__(self, point: ExperimentPoint, *, seed: int):
        if point.kind != "fig4d_reproduction":
            raise ValueError("full Knill requires Fig.4(d) points")
        code = Code.rotated(point.d)
        pcm, blocks = code.matrices, code.blocks(2 * point.T_tel + 1)
        matching = pymatching.Matching.from_check_matrix  # Legacy Hamming online weights.
        modules, supports, roles, transitions = [], [], [], []

        def append(module, support, role, transition=None):
            modules.append(module)
            supports.append(support)
            roles.append(role)
            transitions.append(_transition(module, support) if transition is None else transition)

        data = blocks[0]["data_qubits"]
        append(no_measurement_module(noiseless_unitary_state_prep(pcm, "z", eigenvalue=0), data),
               data, "ideal_encoded_data")
        families = {}
        for basis, offset, rounds in (("z", 1, point.r_0), ("x", 2, point.r_plus)):
            resource_supports = [sum((blocks[2 * j + offset][key]
                                      for key in ("data_qubits", "x_ancillas", "z_ancillas")), [])
                                 for j in range(point.T_tel)]
            canonical = list(range(len(resource_supports[0])))
            template = generate_state_prep_modules(pcm, rounds, basis, point.p,
                                                  [canonical], matching, matchable=True,
                                                  surface_code=True)[0]
            # The callback closes over local circuits, maps and decoder handles.
            # set_support only replaces the instance's physical circuit/support.
            template.cache_m2d_converters()
            # Build local maps before support remapping, keeping temporary
            # frame arrays to one resource block even for large distances.
            transition = _transition(template, canonical)
            family = []
            for support in resource_supports:
                instance = copy.copy(template)
                instance.set_support(support)
                family.append((instance, support, transition))
            families[basis] = family

        for j in range(point.T_tel):
            for basis in ("z", "x"):
                module, support, transition = families[basis][j]
                append(module, support, "prepare_zero" if basis == "z" else "prepare_plus", transition)
            previous, zero, plus = (blocks[q]["data_qubits"] for q in (2*j, 2*j+1, 2*j+2))
            append(generate_transversal_cnot_module(point.p, plus, zero), plus + zero, "bell_entangle")
            append(generate_bell_measurement_and_correction_module(pcm, point.p, previous, zero, plus,
                                                                   decoder_generator=matching),
                   previous + zero + plus, "bell_measure_and_correct")
        final = blocks[-1]["data_qubits"]
        append(generate_logical_measurement_module(pcm, point.p, "z", final, matching),
               final, "noisy_final_Z")
        self.engine = modularised_circuit(modules)
        self.supports, self.roles = supports, roles
        self.transitions = transitions
        self.converter = self.engine.circuit.compile_m2d_converter()
        self.sampler = self.engine.circuit.compile_sampler(seed=seed)
        self.metadata = dict(
            protocol="hex_fixed_full_knill", T_tel=point.T_tel,
            r_0=[point.r_0] * point.T_tel, r_plus=[point.r_plus] * point.T_tel,
            initial_data="ideal_encoded_zero", memory_basis="z",
            noise="hex_uniform", physical_error=point.p,
            final_readout="noisy_destructive_Z", final_readout_error=point.p,
            create_codecapacity_dem=False, prior_policy="hex_legacy_hamming",
            offline_decoder="pymatching_mwpm", online_decoder="pymatching_mwpm",
            postselection=False, frame_processing="cached_local_pauli_transitions",
            measurement_records=self.engine.circuit.num_measurements,
            simulator_qubits=self.engine.circuit.num_qubits,
            module_roles=roles,
            resource_measurements=[m.num_measurements for m in modules if isinstance(m, css_detector_module)],
            sampling="one_point_seeded_stim_sampler_advanced_in_fixed_batches",
        )

    def sample(self, shots):
        return self.sampler.sample(shots=shots)

    def decode_batch(self, measurements):
        """Use only supplied raw records; return error labels and repaired records.

        Residual detector failures raise for the whole point. They are never
        silently discarded or counted as successful/accepted trajectories.
        """
        raw = np.asarray(measurements)
        if (raw.dtype != np.bool_ or raw.ndim != 2 or raw.shape[0] == 0
                or raw.shape[1] != self.engine.circuit.num_measurements):
            raise ValueError("raw measurements must be a nonempty aligned bool matrix")
        records = raw.copy()
        frame = PackedFrame(self.engine.circuit.num_qubits, len(raw))
        offset, logical_error = 0, None
        for module, support, transition in zip(self.engine.circuit_modules, self.supports, self.transitions):
            n = module.num_measurements
            flips = frame.advance(module.circuit)
            local = raw[:, offset:offset+n] ^ flips
            records[:, offset:offset+n] = local
            if isinstance(module, logical_measurement_module):
                values = np.asarray(module.c_func(local))
                logical_error = np.any(values != module.c_func_expected_output, axis=1)
            elif transition is not None:
                corrections = np.asarray(module.c_func(local), dtype=np.uint8)
                frame.apply(corrections, transition, support)
                if isinstance(module, css_detector_module):
                    nx, nz = module.x_dem_check_matrix.shape[1], module.z_dem_check_matrix.shape[1]
                    updates = (csc_matrix(corrections[:, :nx]) @ module.x_dem_correction_to_local_measurement_flips
                               + csc_matrix(corrections[:, nx:nx+nz]) @ module.z_dem_correction_to_local_measurement_flips)
                    records[:, offset:offset+n] ^= (updates.toarray() % 2).astype(bool)
            offset += n
        detectors, _ = self.converter.convert(measurements=records, separate_observables=True)
        if detectors.any():
            raise RuntimeError("Hex full Knill decoding left nonzero preparation detectors")
        return FullKnillBatch(logical_error, records)
