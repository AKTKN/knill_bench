"""Fixed-R physical-zero preparation from native Hex surface primitives.

Production has only prefix detectors and ideal evaluator-only observables.
The separate completed X circuit inserts ideal probes only for offline model
construction. No decoder, sampler, Pauli correction or stopping policy is built.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path

import stim

from hex_qec.circuit_generation.circuit_generation import (
    qubit_initialisation, measure_X_stabilizers_surface_code, measure_Z_stabilizers_surface_code,
)
from knill_bench.codes import Code
from knill_bench.preparation import (
    PREPARATION_SEMANTICS, CompiledPreparationExperiment, DetectorRole,
    PreparationCapabilityError, PreparationDetector, PreparationLabels,
    PreparationObservable, PreparationOutputCut, PreparationRecord, PreparationSettings,
)


def _sha(value) -> str:
    data = value if isinstance(value, bytes) else str(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _probability(value, name: str, *, model=False) -> float:
    upper = .5
    try:
        finite = math.isfinite(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else False
    except OverflowError:
        finite = False
    if not finite or value < 0 or (value >= upper if model else value > upper):
        raise ValueError(f"{name} must be finite in [0, {'0.5)' if model else '0.5]'}")
    return float(value)


def _data_pauli(row, basis, data, size):
    pauli = stim.PauliString(size)
    for col in row.indices:
        pauli[data[int(col)]] = basis.upper()
    return pauli


def _validate_instrument(code, block):
    """Certify the native ideal full commuting instrument before shadow probes.

    All independent CSS checks are measured nondestructively with their signed
    input eigenvalues. Both logical Paulis are preserved. Together with the
    checked one-logical-qubit CSS rank, these certify the joint projective
    instrument up to an irrelevant branch phase, under the Pauli-noise model.
    """
    circuit = stim.Circuit()
    measure_X_stabilizers_surface_code(circuit, code.stabilizers[0], block, 0)
    measure_Z_stabilizers_surface_code(circuit, code.stabilizers[1], block, 0)
    flows = []
    record = 0
    for matrix, basis in zip(code.matrices[:2], ("x", "z")):
        for j in range(matrix.shape[0]):
            pauli = _data_pauli(matrix.getrow(j), basis, block["data_qubits"], circuit.num_qubits)
            flows.extend((stim.Flow(input=pauli, output=pauli),
                          stim.Flow(input=pauli, measurements=[record])))
            record += 1
    for matrix, basis in zip(code.matrices[2:], ("x", "z")):
        pauli = _data_pauli(matrix.getrow(0), basis, block["data_qubits"], circuit.num_qubits)
        flows.append(stim.Flow(input=pauli, output=pauli))
    if circuit.num_measurements != record or not circuit.without_noise().has_all_flows(flows):
        raise PreparationCapabilityError("native full SE cannot certify a signed commuting nondemolition instrument")


def _validate_native_prefix(circuit, p):
    """Keep the audited unconditional Clifford/Pauli-noise proof domain exact."""
    allowed = {"R", "H", "CX", "CZ", "MR", "X_ERROR", "Z_ERROR", "DEPOLARIZE2", "DETECTOR"}
    for op in circuit:
        if op.name not in allowed:
            raise PreparationCapabilityError(f"unsupported native physical-prefix operation/noise: {op.name}")
        if op.name in {"X_ERROR", "Z_ERROR", "DEPOLARIZE2"} and op.gate_args_copy() != [p]:
            raise PreparationCapabilityError("native hex_legacy noise probability differs from the declared p")
        if op.name == "MR" and any(op.gate_args_copy()):
            raise PreparationCapabilityError("native hex_legacy readout noise must use the audited separate Pauli channel")
        if op.name != "DETECTOR" and any(t.is_measurement_record_target or t.is_sweep_bit_target for t in op.targets_copy()):
            raise PreparationCapabilityError("outcome-dependent physical gates are outside the shadow-probe proof")


class _CircuitPlan:
    def __init__(self, code, block, settings, p, *, completed):
        self.circuit = stim.Circuit()
        self.code, self.block, self.settings = code, block, settings
        self.ledger, self.detectors, self.observables = [], [], []
        self.last = {}
        qubit_initialisation(self.circuit, "z", block, p)
        past = self.probes("past_x_probe") if completed else None
        for r in range(1, settings.rounds + 1):
            for sector, function, stabs in zip(
                    ("x", "z"), (measure_X_stabilizers_surface_code, measure_Z_stabilizers_surface_code),
                    code.stabilizers[:2]):
                start = self.circuit.num_measurements
                function(self.circuit, stabs, block, p)
                count = code.matrices[0 if sector == "x" else 1].shape[0]
                records = tuple(range(start, start + count))
                if self.circuit.num_measurements != start + count:
                    raise PreparationCapabilityError("native SE measurement count differs from explicit check map")
                self.ledger.extend(PreparationRecord(m, "se", sector, r, j, None) for j, m in enumerate(records))
                if r > 1:
                    if not completed or sector == "x":
                        for j, (a, b) in enumerate(zip(self.last[sector], records)):
                            self.detector(sector, r, j, DetectorRole.ONLINE, (a, b))
                elif sector == "x" and completed:
                    for j, (a, b) in enumerate(zip(past, records)):
                        self.detector("x", r, j, DetectorRole.PAST, (a, b))
                elif sector == "z" and not completed:
                    for j, m in enumerate(records):
                        self.detector("z", r, j, DetectorRole.ONLINE, (m,))
                self.last[sector] = records
        self.cut = PreparationOutputCut(len(self.circuit), self.circuit.num_measurements, settings.rounds)
        self.prefix = self.circuit.copy()
        output_x = self.probes("output_x_probe")
        if completed:
            for j, (a, b) in enumerate(zip(self.last["x"], output_x)):
                self.detector("x", settings.rounds, j, DetectorRole.FUTURE, (a, b))
        start = self.circuit.num_measurements
        self.circuit.append("M", block["data_qubits"])
        self.ledger.extend(PreparationRecord(start + j, "destructive_z", "z", None, None, int(q))
                           for j, q in enumerate(block["data_qubits"]))
        tau_x, tau_z = [], []
        for j, (a, b) in enumerate(zip(self.last["x"], output_x)):
            tau_x.append(self.observable("tau_x", j, (a, b)))
        for j, a in enumerate(self.last["z"]):
            z_records = tuple(start + int(q) for q in code.matrices[1].getrow(j).indices)
            tau_z.append(self.observable("tau_z", j, (a, *z_records)))
        logical_records = tuple(start + int(q) for q in code.matrices[3].getrow(0).indices)
        logical_z = self.observable("logical_z", None, logical_records)
        self.labels = PreparationLabels(tuple(tau_x), tuple(tau_z), (logical_z,))

    def targets(self, records):
        return [stim.target_rec(m - self.circuit.num_measurements) for m in records]

    def detector(self, sector, r, j, role, records):
        index = len(self.detectors)
        self.circuit.append("DETECTOR", self.targets(records), [0 if sector == "x" else 1, j, r])
        self.detectors.append(PreparationDetector(index, sector, r, j, role, tuple(records)))

    def observable(self, metric, j, records):
        index = len(self.observables)
        self.circuit.append("OBSERVABLE_INCLUDE", self.targets(records), index)
        self.observables.append(PreparationObservable(index, metric, j, tuple(records)))
        return index

    def probes(self, source):
        records = []
        for j in range(self.code.matrices[0].shape[0]):
            targets = []
            for q in self.code.matrices[0].getrow(j).indices:
                if targets:
                    targets.append(stim.target_combiner())
                targets.append(stim.target_x(int(self.block["data_qubits"][int(q)])))
            record = self.circuit.num_measurements
            self.circuit.append("MPP", targets)
            records.append(record)
            self.ledger.append(PreparationRecord(record, source, "x", None, j, None))
        return tuple(records)

    def strict_dem(self):
        flows = [stim.Flow(measurements=row.record_ids) for row in (*self.detectors, *self.observables)]
        if not self.circuit.without_noise().has_all_flows(flows):
            raise PreparationCapabilityError("preparation detector/evaluation signed flows are not deterministic")
        if (tuple(row.record_id for row in self.ledger) != tuple(range(self.circuit.num_measurements))
                or len(self.detectors) != self.circuit.num_detectors
                or len(self.observables) != self.circuit.num_observables):
            raise PreparationCapabilityError("incomplete preparation record/detector/observable ledger")
        try:
            return self.circuit.detector_error_model(
                decompose_errors=False, allow_gauge_detectors=False, approximate_disjoint_errors=False)
        except ValueError as error:
            raise PreparationCapabilityError(f"strict preparation DEM extraction failed: {error}") from error


def build_preparation(case) -> CompiledPreparationExperiment:
    """Build/validate three circuit roles without sampling or decoding.

    ``p`` is physical native Hex noise. Optional ``decoding_p`` changes only
    the offline completed model and production-shaped nominal model. R is a
    literal full-round count, never a memory cycle or an initialization depth.
    """
    if case.get("protocol") != "surface_prep_fixed":
        raise ValueError("preparation builder requires protocol=surface_prep_fixed")
    if case.get("code", "rotated_surface") != "rotated_surface" or case.get("basis", "z") != "z":
        raise PreparationCapabilityError("surface_prep_fixed requires rotated_surface and z basis")
    if case.get("noise", {"profile": "hex_legacy"}) != {"profile": "hex_legacy"}:
        raise PreparationCapabilityError("surface_prep_fixed supports only the native hex_legacy noise profile")
    forbidden = {"cycles", "cycles_per_distance", "prep_rounds", "post_gate_rounds", "initial_boundary", "final_readout"} & case.keys()
    if forbidden:
        raise ValueError(f"preparation cannot reinterpret legacy fields {sorted(forbidden)}")
    allowed = {"protocol", "code", "basis", "distance", "p", "noise", "rounds", "prep_basis", "sign_sector",
               "readout_basis", "logical_evaluation", "adaptive", "decoding_p", "decoders", "decoder_specs",
               "sampling_case_id", "schedule_id", "oracle_cut", "probe_spec", "sampler_semantics"}
    if set(case) - allowed:
        raise ValueError(f"unknown preparation case fields: {sorted(set(case) - allowed)}")
    for key, value in dict(schedule_id="hex_surface_x_then_z_v1", oracle_cut="after_final_z_extraction",
                           probe_spec="ideal_X_MPP_then_ideal_destructive_Z", sampler_semantics=PREPARATION_SEMANTICS).items():
        if key in case and case[key] != value:
            raise PreparationCapabilityError(f"surface_prep_fixed requires {key}={value}")
    settings = PreparationSettings(case.get("rounds"), **{
        name: case[name] for name in ("prep_basis", "sign_sector", "readout_basis", "logical_evaluation", "adaptive") if name in case})
    p = _probability(case["p"], "physical p")
    nominal = _probability(case.get("decoding_p", p), "decoding_p", model=True)
    # Audit the actual imported dependency before invoking its physical builders.
    from knill_bench.experiments.provenance import validate_hex
    import knill_bench.preparation as contracts
    provenance = validate_hex()
    code = Code.rotated(case["distance"])
    block = code.blocks(1)[0]
    _validate_instrument(code, block)
    production = _CircuitPlan(code, block, settings, p, completed=False)
    model = production if nominal == p else _CircuitPlan(code, block, settings, nominal, completed=False)
    completed = _CircuitPlan(code, block, settings, nominal, completed=True)
    _validate_native_prefix(production.prefix, p)
    if model is not production:
        _validate_native_prefix(model.prefix, nominal)
    dem = production.strict_dem()
    model_dem = dem if model is production else model.strict_dem()
    completed_dem = completed.strict_dem()

    # Actual imported package provenance supports the existing verified-wheel path.
    matrices = [[list(map(int, matrix.getrow(j).indices)) for j in range(matrix.shape[0])] for matrix in code.matrices]
    sources = (("builder_python", _sha(Path(__file__).read_bytes())),
               ("contracts_python", _sha(Path(contracts.__file__).read_bytes())),
               ("hex_python_and_matrices", provenance["source_sha256"]),
               ("code_matrix_rows", _sha(_json(matrices))))
    hashes = tuple((name, _sha(value)) for name, value in (
        ("physical_prefix", production.prefix), ("production_circuit", production.circuit),
        ("model_circuit", model.circuit), ("completed_circuit", completed.circuit),
        ("production_dem", dem), ("model_dem", model_dem), ("completed_dem", completed_dem),
        ("record_maps", _json([[asdict(r) for r in plan.ledger] for plan in (production, completed)])),
        ("detector_maps", _json([[asdict(d) for d in plan.detectors] for plan in (production, completed)])),
        ("observable_maps", _json([[asdict(o) for o in plan.observables] for plan in (production, completed)])),
        ("semantics", _json(dict(version=PREPARATION_SEMANTICS, settings=asdict(settings),
                                  physical_p=p, decoding_p=nominal, matrices=matrices))),
    ))
    return CompiledPreparationExperiment(
        settings=settings, distance=code.distance, physical_probability=p, decoding_probability=nominal,
        data_qubits=tuple(map(int, block["data_qubits"])),
        physical_prefix=production.prefix, circuit=production.circuit, model_circuit=model.circuit,
        completed_circuit=completed.circuit, dem=dem, model_dem=model_dem, completed_dem=completed_dem,
        ledger=tuple(production.ledger), completed_ledger=tuple(completed.ledger),
        detectors=tuple(production.detectors), completed_detectors=tuple(completed.detectors),
        labels=production.labels, completed_labels=completed.labels,
        observables=tuple(production.observables), completed_observables=tuple(completed.observables),
        output_cut=production.cut, source_hashes=sources, model_hashes=hashes,
        hex_revision=provenance["commit"], hex_dirty=provenance["dirty"],
    )
