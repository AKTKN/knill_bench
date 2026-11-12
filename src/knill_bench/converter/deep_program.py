"""Seeded abstract Clifford layers and converter-native parallel Knill LSTIM."""

from dataclasses import dataclass
import random

from knill_bench.experiments.config_v2 import _integer, digest

GENERATOR = "python_random_MT19937_HXYZ_shuffle_orientation_v1"
RNG_CONVENTION = (
    "Private random.Random(circuit_seed); per layer draw randrange(4) for each qubit in Q order "
    "using HXYZ, shuffle list(range(logical_qubits)), then getrandbits(1) for each adjacent pair; "
    "bit 1 reverses control/target. No physical or execution parameter consumes this stream."
)


@dataclass(frozen=True)
class CliffordLayer:
    single_qubit: tuple[str, ...]
    cnots: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class LogicalCircuit:
    logical_qubits: int
    circuit_seed: int
    layers: tuple[CliffordLayer, ...]

    def as_dict(self):
        return dict(generator=GENERATOR, rng_convention=RNG_CONVENTION,
            logical_qubits=self.logical_qubits, circuit_seed=self.circuit_seed,
            initial_state="plus_product", gate_order="single_qubit_then_disjoint_CNOTs",
            single_qubit_probabilities={gate: .25 for gate in "HXYZ"},
            layers=[dict(index=i, single_qubit=list(layer.single_qubit),
                         cnots=[list(pair) for pair in layer.cnots]) for i, layer in enumerate(self.layers)])

    @property
    def instance_hash(self):
        return digest(self.as_dict())


def generate_logical_circuit(*, logical_qubits=4, depth=32, circuit_seed=0):
    """Abstract gates only: d, p, n_r, master_seed and workers are not inputs."""
    _integer(logical_qubits, "logical_qubits", 2)
    _integer(depth, "depth")
    _integer(circuit_seed, "circuit_seed", 0, 2**64-1)
    if logical_qubits % 2:
        raise ValueError("logical_qubits must be even for a perfect CNOT pairing")
    rng, layers = random.Random(circuit_seed), []
    for _ in range(depth):
        singles = tuple("HXYZ"[rng.randrange(4)] for _ in range(logical_qubits))
        permutation = list(range(logical_qubits))
        rng.shuffle(permutation)
        pairs = []
        for i in range(0, logical_qubits, 2):
            a, b = permutation[i:i+2]
            pairs.append((b, a) if rng.getrandbits(1) else (a, b))
        layers.append(CliffordLayer(singles, tuple(pairs)))
    return LogicalCircuit(logical_qubits, circuit_seed, tuple(layers))


def deep_source(point, logical):
    """Fresh handles/labels, three-patch rotation and full group barriers."""
    if (point.kind != "converter_deep_clifford" or point.input_preparation != "ideal"
            or point.r_0 != point.d or point.r_plus != point.d
            or logical.logical_qubits != point.logical_qubits or len(logical.layers) != point.depth
            or logical.circuit_seed != point.circuit_seed):
        raise ValueError("deep program requires ideal input, d-round resources and its seeded logical instance")
    n = point.logical_qubits
    lines = ["FORMAT(1)", f"CODE sc ROTATED_SURFACE({point.d})"]
    lines.extend(f"PATCH P{q}_{p} sc index={3*q+p}" for q in range(n) for p in range(3))
    lines.extend(f"BIND Q{q} P{q}_0" for q in range(n))
    lines.extend(("PARALLEL {", *(f"INIT_X[initial_q{q}](1) Q{q} noise=ideal" for q in range(n)), "}"))
    rotation = ((0, 1, 2), (2, 0, 1), (1, 2, 0))
    for index, layer in enumerate(logical.layers):
        lines.append("PARALLEL {")
        for q, gate in enumerate(layer.single_qubit):
            lines.append(f"{gate}[layer{index}_q{q}] Q{q}" + (" mode=transversal" if gate != "H" else ""))
        lines.extend(("}", "PARALLEL {",
                      *(f"CX[layer{index}_cx{j}] Q{c} Q{t}" for j, (c, t) in enumerate(layer.cnots)), "}"))
        for repetition in range(point.n_r):
            cycle = index*point.n_r + repetition
            _, a, b = rotation[cycle % 3]
            for q in range(n):
                lines.extend((f"BIND A{cycle}_{q} P{q}_{a}", f"BIND B{cycle}_{q} P{q}_{b}"))
            lines.extend(("PARALLEL {",
                *(f"KNILL_EC[ec{cycle}_q{q}]({point.d}) Q{q} A{cycle}_{q} B{cycle}_{q}" for q in range(n)), "}"))
    lines.extend(("PARALLEL {", *(f"SE[final_se_q{q}](1) Q{q} noise=ideal" for q in range(n)), "}"))
    return "\n".join(lines) + "\n"


def compile_deep(point, source):
    from logical_to_stim_converter import NoiseModel, ResourcePreparationNoise, parse_logical_circuit

    uniform = NoiseModel.uniform_depolarizing(point.p)
    if point.resource_preparation == "ideal":
        noise = NoiseModel(uniform.default,
            resource_preparation=ResourcePreparationNoise(True, point.p*point.p_st_multiplier))
    elif point.resource_preparation == "noisy" and point.p_st_multiplier is None:
        noise = uniform
    else:
        raise ValueError("deep preparation requires noisy resources or typed ideal/M9 resources")
    compiled = parse_logical_circuit(source).compile(noise_model=noise, allow_open_outputs=True)
    compiled.validate_metadata()
    return compiled
