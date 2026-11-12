"""Consumer-owned causal, per-patch temporal/CSS MWPM adapters."""

from dataclasses import dataclass

import numpy as np

from .local_matching import LocalMatching


def parity(values, matrix):
    return (np.asarray(values, dtype=np.uint8) @ np.asarray(matrix, dtype=np.uint8).T % 2).astype(bool)


class BoundaryDecoder:
    def __init__(self, request, frame_boundary):
        self.request, self.frame_boundary = request, frame_boundary
        self.temporal = LocalMatching.temporal(request.detector_error_model, output_count=len(request.target_ids))
        if self.temporal.detector_count != len(request.view.detectors):
            raise ValueError("boundary temporal model/view detector order changed")
        self.hx, self.hz = request.check_matrix("X"), request.check_matrix("Z")
        self.x_decoder, self.z_decoder = LocalMatching.capacity(self.hz), LocalMatching.capacity(self.hx)
        self.x_rows = np.array([i for i, check in enumerate(request.checks) if check.basis == "X"], dtype=int)
        self.z_rows = np.array([i for i, check in enumerate(request.checks) if check.basis == "Z"], dtype=int)
        self.last_columns = tuple(request.view.measurement_map.global_to_local[i] for i in request.last_record_ids)
        self.prepared_support = self.logical_toggle = self.prepared_target = None
        if request.preparation is not None:
            prep = request.preparation
            indices = {name: i for i, name in enumerate(request.data_ids)}
            support = prep.logical_z if prep.basis == "Z" else prep.logical_x
            opposite = prep.logical_x if prep.basis == "Z" else prep.logical_z
            self.prepared_support = np.array([indices[q] for q in support], dtype=int)
            self.logical_toggle = np.array([q in opposite for q in request.data_ids], dtype=bool)
            self.prepared_target = request.target_ids.index("prepared_logical_error")
            matrix = self.hz if prep.basis == "Z" else self.hx
            if parity(self.logical_toggle[None, :], matrix).any() or not np.logical_xor.reduce(self.logical_toggle[self.prepared_support]):
                raise ValueError("prepared logical constraint is not a check-preserving logical toggle")
        expected_ids = tuple(f"{axis}:{q}" for axis in ("X", "Z") for q in request.data_ids)
        if frame_boundary.input_ids != expected_ids or frame_boundary.block_use_id != request.block_use_id:
            raise ValueError("boundary frame/input physical X/Z ordering or use changed")

    def _bind(self, request, inputs):
        if (request is not self.request or inputs.source_fingerprint != request.view.source_fingerprint
                or inputs.expected_sector is not None):
            raise ValueError("boundary decoder request/source contract changed")

    def effect(self, bits):
        n = len(self.request.data_ids)
        effect = np.zeros((len(bits), len(self.request.checks)), dtype=bool)
        effect[:, self.z_rows] = parity(bits[:, :n], self.hz)
        effect[:, self.x_rows] = parity(bits[:, n:], self.hx)
        return effect

    def validate_result(self, inputs, result):
        bits = result.correction.bits
        if bits.shape != (len(inputs.records), 2*len(self.request.data_ids)):
            raise ValueError("boundary correction has the wrong physical X/Z width")
        errors = result.predicted_record_errors
        if errors is None or errors.shape != (len(bits), len(self.request.checks)):
            raise ValueError("boundary decoder must return last-record error predictions")
        sector = inputs.records[:, self.last_columns] ^ errors
        if result.net_sector is None or not np.array_equal(result.net_sector, sector ^ self.effect(bits)):
            raise ValueError("boundary net-sector equation disagrees with the applied physical correction")

    def decode_batch(self, request, inputs):
        from logical_to_stim_converter.decoding import CorrectionBatch, StageResult

        self._bind(request, inputs)
        target_predictions = self.temporal.decode(inputs.events)
        errors = target_predictions[:, :len(request.checks)]
        inferred = inputs.records[:, self.last_columns] ^ errors
        x = self.x_decoder.decode(inferred[:, self.z_rows])
        z = self.z_decoder.decode(inferred[:, self.x_rows])
        if self.prepared_target is not None:
            vector = x if request.preparation.basis == "Z" else z
            current = np.logical_xor.reduce(vector[:, self.prepared_support], axis=1)
            change = current ^ target_predictions[:, self.prepared_target]
            vector ^= change[:, None] & self.logical_toggle
        bits = np.concatenate((x, z), axis=1)
        result = StageResult(CorrectionBatch(inputs.source_fingerprint, request.module_id, bits,
            request.block_use_id, self.frame_boundary.input_ids), errors, inferred ^ self.effect(bits))
        self.validate_result(inputs, result)
        return result


class ReadoutDecoder:
    def __init__(self, request, frame_boundary):
        self.request, self.frame_boundary = request, frame_boundary
        self.checks = request.check_matrix
        self.matching = LocalMatching.capacity(self.checks)
        if (frame_boundary.block_use_id != request.block_use_id
                or len(frame_boundary.input_ids) != self.checks.shape[1]):
            raise ValueError("readout frame/use/record width changed")

    def decode_batch(self, request, inputs):
        from logical_to_stim_converter.decoding import CorrectionBatch, StageResult

        if (request is not self.request or request.readout.basis != self.request.readout.basis
                or inputs.source_fingerprint != request.view.source_fingerprint
                or inputs.expected_sector is None or inputs.expected_sector.shape != (len(inputs.records), len(self.checks))):
            raise ValueError("readout decoder request/basis/source/sector changed")
        difference = parity(inputs.records, self.checks) ^ inputs.expected_sector
        correction = self.matching.decode(difference)
        result = StageResult(CorrectionBatch(inputs.source_fingerprint, request.readout.module_id,
            correction, request.block_use_id, self.frame_boundary.input_ids))
        self.validate_result(inputs, result)
        return result

    def validate_result(self, inputs, result):
        if (result.correction.bits.shape != inputs.records.shape
                or not np.array_equal(parity(result.correction.bits, self.checks),
                                      parity(inputs.records, self.checks) ^ inputs.expected_sector)):
            raise ValueError("readout capacity correction does not satisfy the current sector/syndrome equation")


@dataclass(frozen=True)
class StageTrace:
    kind: str
    module_id: str
    inputs: object
    result: object
    before: np.ndarray
    after: np.ndarray


@dataclass(frozen=True)
class KnillReplay:
    frames: object
    sectors: np.ndarray
    logical_error: np.ndarray
    stages: tuple[StageTrace, ...]


@dataclass(frozen=True)
class CausalReplay:
    frames: object
    sectors: np.ndarray
    stages: tuple[StageTrace, ...]


class CausalDecoder:
    """Shared Phase 2 adapters and native causal replay, with no terminal truth."""

    def __init__(self, compiled, *, frame_plan=None):
        from logical_to_stim_converter.decoding import make_stage_requests

        self.compiled = compiled
        self.frame_plan = compiled.make_frame_plan() if frame_plan is None else frame_plan
        self.requests = make_stage_requests(compiled)
        self.boundaries = {r.module_id: r for r in self.requests.boundaries}
        self.readouts = {r.readout.module_id: r for r in self.requests.readouts}
        modules = [module for _, module in self.requests.order]
        physical_order = [f.module_id for f in compiled.fragments if f.module_id in modules]
        if (modules != physical_order or len(set(modules)) != len(modules)
                or set(modules) != self.boundaries.keys() | self.readouts.keys()):
            raise ValueError("stage requests must cover each native boundary/readout in causal order")
        self.sector_slots = {module: np.array([self.requests.sector_input_ids.index((module, c.check_id)) for c in r.checks])
                             for module, r in self.boundaries.items()}
        seen = set()
        for kind, module in self.requests.order:
            if kind == "boundary":
                seen.add(module)
            else:
                used = {i for support in self.readouts[module].sector_map.supports for i in support}
                if any(self.requests.sector_input_ids[i][0] not in seen for i in used):
                    raise ValueError("readout sector map references a future boundary")
        self.boundary_decoders = {module: BoundaryDecoder(r, self.frame_plan.boundary_by_id[module])
                                 for module, r in self.boundaries.items()}
        self.readout_decoders = {module: ReadoutDecoder(r, self.frame_plan.boundary_by_id[module])
                                for module, r in self.readouts.items()}
        self._order = tuple(self.requests.order)

    def replay_prefix(self, raw, *, trace=False, boundary_decoders=None, readout_decoders=None):
        from logical_to_stim_converter.decoding import CorrectionBatch, StageInputs, StageResult

        if tuple(self.requests.order) != self._order:
            raise ValueError("causal correction order changed or omitted a boundary/readout")
        frames = self.frame_plan.start(raw, source_fingerprint=self.frame_plan.source_fingerprint)
        sectors = np.zeros((len(raw), len(self.requests.sector_input_ids)), dtype=bool)
        traces = []
        boundary_decoders = self.boundary_decoders if boundary_decoders is None else boundary_decoders
        readout_decoders = self.readout_decoders if readout_decoders is None else readout_decoders
        current = frames.interpreted_measurements
        for kind, module in self.requests.order:
            request = self.boundaries[module] if kind == "boundary" else self.readouts[module]
            expected = (request.sector_map.apply(sectors) ^ request.sector_constant) if kind == "readout" else None
            inputs = StageInputs(self.frame_plan.source_fingerprint, frames.events(request.view),
                                 request.view.project_raw_measurements(current), expected)
            adapter = boundary_decoders[module] if kind == "boundary" else readout_decoders[module]
            result = adapter.decode_batch(request, inputs)
            if not isinstance(result, StageResult) or not isinstance(result.correction, CorrectionBatch):
                raise ValueError("every causal stage must return its correction; readout omission is unsupported")
            if result.correction.boundary_id != module:
                raise ValueError("decoder correction returned for a different causal stage")
            boundary = self.frame_plan.boundary_by_id[module]
            if (result.correction.source_fingerprint != self.frame_plan.source_fingerprint
                    or result.correction.block_use_id != boundary.block_use_id
                    or result.correction.input_ids != boundary.input_ids):
                raise ValueError("causal correction source/use/input ordering changed")
            if kind == "boundary":
                self.boundary_decoders[module].validate_result(inputs, result)
            else:
                self.readout_decoders[module].validate_result(inputs, result)
            frames.apply(result.correction)
            updated = frames.interpreted_measurements
            if kind == "boundary":
                sectors[:, self.sector_slots[module]] = result.net_sector
            elif not np.array_equal(parity(request.view.project_raw_measurements(updated),
                                           self.readout_decoders[module].checks), expected):
                raise ValueError("readout correction was omitted or its applied sector is stale")
            if trace:
                traces.append(StageTrace(kind, module, inputs, result, current, updated))
            current = updated
        return CausalReplay(frames, sectors, tuple(traces))


class KnillDecoder(CausalDecoder):
    def __init__(self, compiled):
        super().__init__(compiled)
        observable, = compiled.observables
        if observable.basis != "Z" or observable.logical_id != "D":
            raise ValueError("Knill memory needs one deterministic terminal D/Z observable")
        self.observable = observable

    def replay(self, raw, **options):
        replay = self.replay_prefix(raw, **options)
        corrected = replay.frames.interpreted_measurements
        value = np.logical_xor.reduce(corrected[:, self.observable.readout_measurement_indices], axis=1)
        return KnillReplay(replay.frames, replay.sectors, value ^ bool(self.observable.expected_value), replay.stages)
