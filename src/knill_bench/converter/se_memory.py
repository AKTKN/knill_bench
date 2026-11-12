"""Converter-authored ordinary Z memory; no bench physical circuit builder."""

import hashlib

from knill_bench.experiments.config_v2 import _integer, digest
from .artifacts import PointArtifacts
from .decoding import MemoryDecoder
from .metadata import MEMORY_MODEL, MEMORY_POLICY

_CACHED = None


def memory_source(distance, rounds, *, basis="Z", input_preparation="noisy"):
    """INIT includes round one; emit exactly R-1 further SE rounds."""
    _integer(distance, "distance", 3)
    _integer(rounds, "rounds")
    if distance % 2 != 1 or basis not in {"X", "Z"} or input_preparation not in {"noisy", "ideal"}:
        raise ValueError("memory requires odd distance, X/Z basis and noisy/ideal initialization")
    lines = ["FORMAT(1)", f"CODE sc ROTATED_SURFACE({distance})", "PATCH P0 sc index=0", "BIND D P0",
             f"INIT_{basis}[initial](1) D" + (" noise=ideal" if input_preparation == "ideal" else "")]
    if rounds > 1:
        lines.append(f"SE[storage]({rounds-1}) D")
    lines.append(f"M{basis}[readout] D")
    return "\n".join(lines) + "\n"


def exact_stim_text(circuit):
    """Retain public Stim target/tag spellings and round-trip every float arg.

    Stim display formatting can shorten probabilities. Replace only numeric
    argument text with round-trip Python floats, then verify full equality.
    """
    import stim

    def lines(body):
        for index, instruction in enumerate(body):
            text = str(instruction)
            if isinstance(instruction, stim.CircuitRepeatBlock):
                yield str(body[index:index+1]).splitlines()[0]
                yield from ("    " + line for line in lines(instruction.body_copy()))
                yield "}"
            elif instruction.gate_args_copy():
                end = text.rfind(")")
                start = text.rfind("(", 0, end)
                yield text[:start+1] + ", ".join(repr(v) for v in instruction.gate_args_copy()) + text[end:]
            else:
                yield text
    text = "\n".join(lines(circuit)) + "\n"
    if stim.Circuit(text) != circuit:
        raise ValueError("cannot serialize the exact sampled Stim circuit without changing instructions")
    return text


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ConverterSEMemory:
    """A point's compiled physical circuit, public maps/frame and cached MWPM."""

    def __init__(self, point):
        from logical_to_stim_converter import NoiseModel, parse_logical_circuit

        if point.kind != "converter_se_memory" or point.noise != "converter_uniform":
            raise ValueError("ConverterSEMemory requires converter_se_memory/converter_uniform")
        self.point = point
        self.lstim_source = memory_source(point.d, point.rounds, input_preparation=point.input_preparation)
        self.compiled = parse_logical_circuit(self.lstim_source).compile(
            noise_model=NoiseModel.uniform_depolarizing(point.p))
        self.compiled.validate_metadata()
        self.circuit = self.compiled.circuit
        self.stim_source = exact_stim_text(self.circuit)
        self.decoder = MemoryDecoder(self.compiled)
        self.frame_plan = self.compiled.make_frame_plan()
        view = self.decoder.view
        self.metadata = dict(
            physical_model=MEMORY_MODEL, prior_policy=MEMORY_POLICY, memory_basis="Z",
            distance=point.d, physical_error=point.p, rounds=point.rounds,
            initialization_se_rounds=1, additional_se_rounds=point.rounds-1,
            input_preparation=point.input_preparation, final_readout=point.final_readout,
            noise="converter_uniform", noise_api="NoiseModel.uniform_depolarizing",
            detector_sector="Z", enable_correlations=False, decompose_errors=False,
            correlated_components="rejected", terminal_ideal_oracle=False,
            measurements=self.circuit.num_measurements, qubits=self.circuit.num_qubits,
            physical_detectors=self.circuit.num_detectors, decoding_detectors=self.decoder.dem.num_detectors,
            observables=1, matching_edges=self.decoder.matching.num_edges,
            source_fingerprint=view.source_fingerprint,
            lstim_sha256=text_hash(self.lstim_source), stim_sha256=text_hash(self.stim_source),
            dem_sha256=text_hash(str(self.decoder.dem)),
            detector_map_sha256=digest(view.detector_map.local_to_global),
            observable_map_sha256=digest(view.observable_map.local_to_global),
        )
        from .runtime import circuit_counts
        self.metadata["circuit_counts"] = circuit_counts(self.circuit, 1)

    def decode_batch(self, measurements):
        return self.decoder.decode_batch(measurements)

    def artifacts(self):
        return PointArtifacts(self.lstim_source, self.stim_source, dict(
            execution=self.metadata, converter_export=self.compiled.export_metadata()))


def memory_model(point):
    """Bounded one-point process-local cache, excluding sampler/RNG state."""
    global _CACHED
    if _CACHED is None or _CACHED[0] != point:
        _CACHED = None
        _CACHED = (point, ConverterSEMemory(point))
    return _CACHED[1]


def clear_memory_cache():
    global _CACHED
    _CACHED = None


def memory_artifacts(point):
    return memory_model(point).artifacts()
