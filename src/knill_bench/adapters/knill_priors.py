"""Full Knill inference only: local Stim DEM or native causal full-prefix.

No analysis boundary enters physical sampling. Local priors exclude noisy
preparation/earlier-stage residuals, retain both current native CX gadgets and
readout noise, and use independent X/Z sectors. They are not conditional ML.
"""

from dataclasses import asdict
from functools import lru_cache
import hashlib

import numpy as np
import pymatching
import stim

from hex_qec.modularisation import measurement_module
from hex_qec.modularisation.factory import CodeSpec
from hex_qec.decoders.codecapacity_dem import UnsupportedProjectedModel
from knill_bench.experiments.config_v2 import digest, LOCAL_PRIOR_APPROXIMATION
from .hex_factory import _event_model, _stim_dem

POLICY = "knill_module_local_stim_v1"
SCOPE = "current_bell_resource_cnot_data_coupling_and_readouts"


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _code_spec(code):
    def rows(matrix):
        return tuple(tuple(map(int, matrix.getrow(i).nonzero()[1])) for i in range(matrix.shape[0]))
    hx, hz, lx, lz = code.matrices
    return CodeSpec("rotated_surface", hx.shape[1], rows(hx), rows(hz), rows(lx)[0], rows(lz)[0], code.distance)


@lru_cache(maxsize=8)
def _ideal_input(code):
    n = code.num_data_qubits
    def pauli(basis, indices):
        value = stim.PauliString(3*n)
        for index in indices:
            value[index] = basis
        return value
    stabilizers = [pauli(basis, [offset+i for i in row])
                   for offset in (0, n, 2*n)
                   for basis, rows in (("X", code.x_checks), ("Z", code.z_checks))
                   for row in rows]
    stabilizers += [pauli("Z", code.logical_z), pauli("Z", [n+i for i in code.logical_z]),
                    pauli("X", [2*n+i for i in code.logical_x])]
    circuit = stim.Circuit()
    circuit.append("R", range(3*n))
    circuit += stim.Tableau.from_stabilizers(stabilizers).to_circuit()
    return str(circuit)


def _analysis_circuit(code, body, sector):
    """Pauli logical input closes random Bell byproducts without truth/oracle."""
    n = code.num_data_qubits
    source = stim.Circuit(body)
    checks, logical = ((code.x_checks, code.logical_x) if sector == "x"
                       else (code.z_checks, code.logical_z))
    readouts = [(op.name, t.value) for op in source
                if op.name in {"MRX", "MR", "MX", "M"} for t in op.targets_copy()]
    if readouts != [("MRX", i) for i in range(n)] + [("MR", n+i) for i in range(n)]:
        raise UnsupportedProjectedModel("local Knill prior needs native ordered destructive X/Z Bell readout")
    gates = stim.Circuit()
    for op in source.without_noise():
        if op.name in {"MRX", "MR", "MX", "M"}:
            break
        gates.append(op)
    output = stim.PauliString(3*n)
    for i in logical:
        output[(0 if sector == "x" else n)+i] = "X" if sector == "x" else "Z"
    input_pauli = output.before(gates)
    if input_pauli.sign != 1:
        raise UnsupportedProjectedModel("local Knill logical boundary must have positive signed flow")
    targets = []
    for i in range(3*n):
        kind = input_pauli[i]
        if kind:
            targets.append({1: stim.target_x, 2: stim.target_y, 3: stim.target_z}[kind](i))
    circuit = stim.Circuit(_ideal_input(code))
    circuit.append("OBSERVABLE_INCLUDE", targets, 0)
    circuit += source
    shift = -2*n if sector == "x" else -n
    for row in checks:
        circuit.append("DETECTOR", [stim.target_rec(shift+i) for i in row])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(shift+i) for i in logical], 0)
    return circuit


@lru_cache(maxsize=16)
def _cached_local_prior(code, body, sector):
    circuit = _analysis_circuit(code, body, sector)
    dem = _stim_dem(circuit)
    model = _event_model(dem)  # Complete signatures; no lossy decomposition.
    gap = model.compile_gap()  # Native strict finite-weight/lift checks.
    configuration = dict(policy=POLICY, scope=SCOPE, approximation=LOCAL_PRIOR_APPROXIMATION,
                         code=asdict(code), sector=sector, body=body, circuit=str(circuit),
                         stim=stim.__version__, pymatching=pymatching.__version__)
    description = dict(configuration_sha256=digest(configuration), model_sha256=_sha(str(dem)),
                       physical_module_sha256=_sha(body), analysis_circuit_sha256=_sha(str(circuit)))
    return gap, description


def clear_knill_prior_cache():
    _cached_local_prior.cache_clear()
    _ideal_input.cache_clear()


def knill_prior_cache_info():
    return _cached_local_prior.cache_info()._asdict()


def _local_body(pieces, support):
    """Canonical current-stage native gates/noise only, no prep/past/final."""
    mapping = {q: i for i, q in enumerate(support)}
    body = stim.Circuit()
    for piece in pieces:
        for op in piece.circuit:
            targets = op.targets_copy()
            if any(not t.is_qubit_target or t.value not in mapping for t in targets):
                raise UnsupportedProjectedModel("local Knill body must have data-only quantum targets")
            body.append(op.name, [mapping[t.value] for t in targets], op.gate_args_copy())
    return str(body)


def configure_local_priors(model, code):
    """Extract each actual native stage, canonicalize data/zero/plus supports."""
    spec = _code_spec(code)
    n = spec.num_data_qubits
    descriptions, current = [], []
    for module, role, support in zip(model.engine.circuit_modules, model.roles, model.supports):
        if role == "bell_entangle":
            current = [module]
        elif role == "data_code_capacity_noise":
            current.append(module)
        elif role == "bell_measure_and_correct":
            current.append(module)
            body = _local_body(current, support)
            compiled = tuple(_cached_local_prior(spec, body, sector) for sector in ("x", "z"))
            gaps = tuple(pair[0] for pair in compiled)
            logicals = (code.matrices[2], code.matrices[3])
            checks = (code.matrices[0], code.matrices[1])
            def decode(records, *, gaps=gaps, logicals=logicals, checks=checks):
                records = np.asarray(records)
                if records.ndim != 2 or records.shape[1] != 2*n or not np.all((records == 0) | (records == 1)):
                    raise ValueError("Bell readout needs binary (shots,2*n) records")
                values = []
                for index, (gap, check, logical) in enumerate(zip(gaps, checks, logicals)):
                    readout = records[:, index*n:(index+1)*n]
                    syndrome = (readout @ check.T % 2).astype(bool)
                    best = gap.decode_batch(syndrome).best_class
                    values.append(((readout @ logical.T % 2).ravel().astype(bool) ^ best.astype(bool))[:, None])
                return np.hstack(values).astype(np.int8)
            module.c_func = decode
            descriptions.append([dict(pair[1]) for pair in compiled])
    if len(descriptions) != model.metadata["T_tel"]:
        raise ValueError("local Knill prior stage count mismatch")
    return descriptions


def configure_full_prefix_priors(model, code):
    """Use native H5 causal replay and structural guards without changing circuits."""
    from hex_qec.modularisation.online_context import configure_knill_projected_priors
    model.engine.generate_correction_to_measurement_flip_map()
    configure_knill_projected_priors(model.engine, code.matrices)
    return [[dict(configuration_sha256=p.configuration_sha256, model_sha256=p.model_sha256)
             for p in module.projected_priors]
            for module in model.engine.circuit_modules if isinstance(module, measurement_module)]
