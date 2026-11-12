"""Prefix-only local MWPM followed by public terminal evaluation."""

from dataclasses import dataclass

import numpy as np

from .knill_decoding import CausalDecoder


@dataclass(frozen=True)
class DeepReplay:
    frames: object
    sectors: np.ndarray
    stabilizer_flips: np.ndarray
    logical_error: np.ndarray
    stages: tuple


class DeepDecoder(CausalDecoder):
    def __init__(self, compiled, probe, *, frame_plan=None):
        super().__init__(compiled, frame_plan=frame_plan)
        self.probe = probe
        if (probe.source_fingerprint != self.frame_plan.source_fingerprint
                or probe.original_measurement_count != compiled.circuit.num_measurements):
            raise ValueError("deep probe/frame source or canonical prefix changed")
        original = probe.original_measurement_count
        if any(i >= original for request in (*self.boundaries.values(), *self.readouts.values())
               for i in request.view.measurement_map.global_ids):
            raise ValueError("terminal probe columns entered a canonical decoder view")

    def replay(self, samples, **options):
        raw, _ = self.probe.split_measurements(samples)
        replay = self.replay_prefix(raw, **options)
        flips = self.probe.corrected_flips(samples, replay.frames)
        if flips.dtype != bool or flips.shape != (len(raw), len(self.probe.observables)):
            raise ValueError("native deep terminal evaluator changed its bool stabilizer dimensions")
        return DeepReplay(replay.frames, replay.sectors, flips, np.any(flips, axis=1), replay.stages)
