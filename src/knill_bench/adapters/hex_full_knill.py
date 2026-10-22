"""Per-shot adapter for Hex fixed full Knill with explicit physical noise policy.

Module construction follows protocols/knill_online_offline.py on the pinned H5 lineage.
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
    KnillNoiseModel, css_detector_module, logical_measurement_module, modularised_circuit,
    no_measurement_module, generate_state_prep_modules,
    generate_transversal_cnot_module, generate_bell_measurement_and_correction_module,
    generate_logical_measurement_module,
)
from knill_bench.codes import Code
from knill_bench.experiments.config_v2 import (ExperimentPoint, KNILL_KINDS, GENERAL_KNILL_KINDS,
    KNILL_PRIOR_POLICIES, LOCAL_PRIOR_APPROXIMATION, KNILL_PREFIX_APPROXIMATION)
from .hex_native import PackedFrame, _transition


@dataclass(frozen=True)
class FullKnillBatch:
    logical_error: np.ndarray
    corrected_measurements: np.ndarray


class HexFullKnill:
    """Compile once, sample raw batches, then decode those batches offline.

    T=1 is supported here for small protocol tests; the Fig.4(d) runner requires
    T=8. knill_ec_memory accepts arbitrary positive T and native noise models.
    Optional local/full-prefix inference retains all physical noise.
    No postselection or terminal factory oracle.
    Native handles and templates belong to this point in this process only.
    """

    def __init__(self, point: ExperimentPoint, *, seed: int,
                 create_codecapacity_dem=False, codecapacity_prior="module_local"):
        if type(create_codecapacity_dem) is not bool:
            raise ValueError("create_codecapacity_dem must be bool")
        if not isinstance(codecapacity_prior, str) or codecapacity_prior not in KNILL_PRIOR_POLICIES:
            raise ValueError("codecapacity_prior must be module_local or full_prefix")
        if point.kind == "fig4d_reproduction" and create_codecapacity_dem:
            raise ValueError("legacy Fig.4(d) requires create_codecapacity_dem=False")
        if point.kind not in KNILL_KINDS:
            raise ValueError("full Knill requires knill_sim / knill_ec_memory / Fig.4(d) points")
        noise = KnillNoiseModel(point.noise)
        rates = noise.probabilities(point.p)
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
            template = generate_state_prep_modules(pcm, rounds, basis, rates["preparation"],
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
            append(generate_transversal_cnot_module(rates["bell_pair_cnot"], plus, zero), plus + zero, "bell_entangle")
            data_noise = noise.data_noise_module(point.p, previous)
            if data_noise is not None:
                append(data_noise, previous, "data_code_capacity_noise")
            append(generate_bell_measurement_and_correction_module(pcm, rates["teleportation"], previous, zero, plus,
                                                                   decoder_generator=matching),
                   previous + zero + plus, "bell_measure_and_correct")
        final = blocks[-1]["data_qubits"]
        append(generate_logical_measurement_module(pcm, rates["final_readout"], "z", final, matching),
               final, "noisy_final_Z" if point.noise == "hex_uniform" else "ideal_final_Z")
        self.engine = modularised_circuit(modules)
        self.supports, self.roles = supports, roles
        self.transitions = transitions
        self.metadata = dict(
            protocol="hex_fixed_full_knill", T_tel=point.T_tel,
            r_0=[point.r_0] * point.T_tel, r_plus=[point.r_plus] * point.T_tel,
            initial_data="ideal_encoded_zero", memory_basis="z",
            noise=point.noise, physical_error=point.p,
            final_readout=point.final_readout, final_readout_error=rates["final_readout"],
            create_codecapacity_dem=False, prior_policy="hex_legacy_hamming",
            offline_decoder="pymatching_mwpm", online_decoder="pymatching_mwpm",
            postselection=False, frame_processing="cached_local_pauli_transitions",
            measurement_records=self.engine.circuit.num_measurements,
            simulator_qubits=self.engine.circuit.num_qubits,
            module_roles=roles,
            resource_measurements=[m.num_measurements for m in modules if isinstance(m, css_detector_module)],
            sampling="one_point_seeded_stim_sampler_advanced_in_fixed_batches",
        )

        if point.kind in GENERAL_KNILL_KINDS:
            self.metadata.update(noise_probabilities=rates, terminal_ideal_oracle=False,
                noise_scope_version="knill_ec_physical_noise_v1")

        if create_codecapacity_dem:
            from .knill_priors import configure_local_priors, configure_full_prefix_priors, SCOPE
            local = codecapacity_prior == "module_local"
            descriptions = (configure_local_priors(self, code) if local
                            else configure_full_prefix_priors(self, code))
            self.metadata.update(
                create_codecapacity_dem=True, codecapacity_prior=codecapacity_prior,
                prior_policy=KNILL_PRIOR_POLICIES[codecapacity_prior],
                projected_approximation=LOCAL_PRIOR_APPROXIMATION if local else KNILL_PREFIX_APPROXIMATION,
                prior_scope=SCOPE if local else "initialization_to_current_bell_readout_prefix",
                preparation_residual_errors_in_prior=not local,
                earlier_stage_residual_errors_in_prior=not local,
                boundary_noise="native_only_no_added_channel", projected_priors=descriptions,
            )
        self.converter = self.engine.circuit.compile_m2d_converter()
        self.sampler = self.engine.circuit.compile_sampler(seed=seed)

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
