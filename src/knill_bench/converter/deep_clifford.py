"""Generation-only deep Clifford model with native signed terminal probes."""

from dataclasses import asdict
from functools import cached_property

from knill_bench.experiments.config_v2 import digest
from .artifacts import PointArtifacts
from .deep_program import GENERATOR, compile_deep, deep_source, generate_logical_circuit
from .se_memory import exact_stim_text, text_hash

DEEP_MODEL = "converter_deep_clifford_parallel_knill_v1"


def logical_definitions(products):
    return [dict(factors=[list(pair) for pair in product.factors], sign=product.sign, label=product.label)
            for product in products]


def validate_stabilizers(products, logical_ids):
    """Validate only abstract logical algebra; native APIs own physical lifting."""
    import stim

    if len(products) != len(logical_ids):
        raise ValueError("deep output needs one independent stabilizer per logical qubit")
    slots = {q: i for i, q in enumerate(logical_ids)}
    rows = []
    for product in products:
        row = stim.PauliString(len(slots))
        row.sign = product.sign
        for q, axis in product.factors:
            if q not in slots:
                raise ValueError("output stabilizer refers to a retired logical resource")
            row[slots[q]] = axis
        rows.append(row)
    # Reject dependence, noncommutation, imaginary phases and inconsistent signs.
    stim.Tableau.from_stabilizers(rows, allow_redundant=False, allow_underconstrained=False)


def _allocation(compiled, point):
    n, cycles = point.logical_qubits, point.depth*point.n_r
    patches = {f"P{q}_{p}" for q in range(n) for p in range(3)}
    if ({bid for bid, _ in compiled.physical_qubit_map} != patches
            or set(compiled.open_logical_outputs) != {f"Q{q}" for q in range(n)}
            or len(compiled.relocation_history) != n*cycles
            or len(compiled.block_uses) != n*(1+2*cycles)):
        raise ValueError("deep patch, output, reset-use or teleportation allocation changed")
    rotation = ((0, 1, 2), (2, 0, 1), (1, 2, 0))
    for q in range(n):
        relocations = [r for r in compiled.relocation_history if r.logical_id == f"Q{q}"]
        previous = next(p.block_use_id for p in compiled.preparations if p.logical_id == f"Q{q}")
        for cycle, relocation in enumerate(relocations):
            data, _, output = rotation[cycle % 3]
            if (relocation.composite_id != f"ec{cycle}_q{q}" or relocation.source_use_id != previous
                    or relocation.source_block_id != f"P{q}_{data}" or relocation.output_block_id != f"P{q}_{output}"):
                raise ValueError("deep recycling reset a surviving state or changed native relocation")
            previous = relocation.output_use_id
        if compiled.open_logical_outputs[f"Q{q}"] != previous.block_id or compiled.orientations[f"Q{q}"] != 0:
            raise ValueError("deep final binding/orientation changed")
    # Certify actual native layer overlap, rather than counting PARALLEL text.
    modules = {f.module_id: f for f in compiled.fragments}
    overlaps = []
    for cycle in range(cycles):
        names = {f"ec{cycle}_q{q}" for q in range(n)}
        largest = 0
        for layer in compiled.time_layers:
            owners = {composite for module in set(layer.operation_by_block.values())
                      if modules[module].operation_type == "LogicalInit"
                      for composite in modules[module].composite_ids if composite in names}
            largest = max(largest, len(owners))
        if largest != n:
            raise ValueError("independent Knill resource preparations failed to overlap physically")
        overlaps.append(largest)
    return min(overlaps)


class CompiledDeepClifford:
    """No noisy decoder or per-shot error API is supplied in Phase 3.

    circuit is probe.circuit. Frame plans consume the native canonical prefix;
    terminal columns remain evaluation-only. Physical lifting/signs are native.
    """

    def __init__(self, point):
        if point.kind != "converter_deep_clifford" or point.noise != "converter_uniform":
            raise ValueError("deep generation requires converter_deep_clifford/converter_uniform")
        self.point = point
        self.logical_circuit = generate_logical_circuit(logical_qubits=point.logical_qubits,
            depth=point.depth, circuit_seed=point.circuit_seed)
        self.lstim_source = deep_source(point, self.logical_circuit)
        self.compiled = compile_deep(point, self.lstim_source)
        overlap = _allocation(self.compiled, point)
        self.logical_stabilizers = self.compiled.logical_output_stabilizers
        validate_stabilizers(self.logical_stabilizers, tuple(f"Q{q}" for q in range(point.logical_qubits)))
        self.probe = self.compiled.make_terminal_observable_probe(self.logical_stabilizers)
        self.circuit = self.probe.circuit
        self.stim_source = exact_stim_text(self.circuit)
        if (self.probe.original_measurement_count != self.compiled.circuit.num_measurements
                or self.probe.measurement_indices != tuple(range(self.probe.original_measurement_count, self.circuit.num_measurements))
                or len(self.probe.observables) != point.logical_qubits
                or self.circuit[:len(self.compiled.circuit)] != self.compiled.circuit):
            raise ValueError("native terminal probe changed its canonical prefix or terminal measurement count")
        self.terminal_metadata = dict(source_fingerprint=self.probe.source_fingerprint,
            original_measurement_count=self.probe.original_measurement_count,
            original_qubit_count=self.probe.original_qubit_count,
            measurement_indices=list(self.probe.measurement_indices),
            observables=[asdict(observable) for observable in self.probe.observables])
        self.metadata = dict(physical_model=DEEP_MODEL, generation_only=True, decoder_status="not_implemented_phase4",
            logical_qubits=point.logical_qubits, depth=point.depth, circuit_seed=point.circuit_seed,
            n_r=point.n_r, qec_intervals=point.depth, parallel_knill_groups=point.depth*point.n_r,
            teleportations=len(self.compiled.relocation_history), physical_patch_count=3*point.logical_qubits,
            parallel_resource_overlap_min=overlap, distance=point.d, physical_error=point.p,
            input_preparation="ideal", input_state="plus_product", input_rounds=1,
            resource_preparation=point.resource_preparation, resource_rounds=point.d,
            m9_enabled=point.resource_preparation == "ideal", p_st_multiplier=point.p_st_multiplier,
            resource_post_se_probability=point.p*point.p_st_multiplier if point.resource_preparation == "ideal" else 0.,
            noise="converter_uniform", final_readout=point.final_readout, final_ideal_se_rounds=1,
            terminal_probe_count=point.logical_qubits, original_measurement_count=self.probe.original_measurement_count,
            measurements=self.circuit.num_measurements, qubits=self.circuit.num_qubits,
            physical_time_layers=len(self.compiled.time_layers), generator=GENERATOR,
            logical_instance_sha256=self.logical_circuit.instance_hash,
            logical_stabilizers_sha256=digest(logical_definitions(self.logical_stabilizers)),
            terminal_probe_sha256=digest(self.terminal_metadata), source_fingerprint=self.probe.source_fingerprint,
            lstim_sha256=text_hash(self.lstim_source), stim_sha256=text_hash(self.stim_source))

    @cached_property
    def frame_plan(self):
        """Public source-bound native plan, constructed only when requested."""
        return self.compiled.make_frame_plan()

    def artifacts(self):
        return PointArtifacts(self.lstim_source, self.stim_source,
            dict(execution=self.metadata, logical_circuit=self.logical_circuit.as_dict(),
                 terminal_probe=self.terminal_metadata, converter_export=self.compiled.export_metadata()),
            logical_definitions(self.logical_stabilizers))
