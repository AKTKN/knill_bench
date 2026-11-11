"""Strict independent-event MWPM and public semantic memory views."""

import math

import numpy as np


class GraphlikeModelError(ValueError):
    """The exact selected DEM cannot be consumed without dropping information."""


def checked_matching(dem):
    """Reject unsupported events before calling PyMatching (correlations off).

    Keep complete undecomposed events. Parallel events may merge only when
    their detector endpoints AND logical labels agree. Logical-only events,
    hyperedges and separator components cannot silently disappear in matching.
    """
    import pymatching

    edges = {}
    for instruction in dem.flattened():
        if instruction.type != "error":
            continue
        probability, = instruction.args_copy()
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise GraphlikeModelError("DEM event probability must be finite and in [0,1]")
        detectors, logicals = set(), set()
        for target in instruction.targets_copy():
            if target.is_separator():
                raise GraphlikeModelError("correlated separator components are unsupported by independent-event MWPM")
            if target.is_relative_detector_id():
                support = detectors
            elif target.is_logical_observable_id():
                support = logicals
            else:
                raise GraphlikeModelError("unsupported DEM error target")
            support.symmetric_difference_update((target.val,))
        if len(detectors) > 2:
            raise GraphlikeModelError("DEM contains a hyperedge; no graphlike fallback is permitted")
        if probability == 0:
            continue
        if not detectors and logicals:
            raise GraphlikeModelError("detector-free logical events are unsupported by this MWPM adapter")
        if not detectors:
            continue  # A complete trivial event changes neither syndrome nor truth.
        endpoints, labels = tuple(sorted(detectors)), tuple(sorted(logicals))
        if endpoints in edges and edges[endpoints] != labels:
            raise GraphlikeModelError("parallel DEM edges have different logical labels")
        edges[endpoints] = labels
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=False)
    if (matching.num_detectors != dem.num_detectors or matching.num_fault_ids != dem.num_observables
            or matching.num_edges != len(edges)):
        raise GraphlikeModelError("PyMatching did not retain the exact selected DEM graph dimensions/edges")
    return matching


class MemoryDecoder:
    """One static public decoder view, reference parity maps and MWPM graph.

    No evaluator truth is passed to matching. X is supported here for dual-basis
    validation; the registered schema-v2 memory experiment is Z memory only.
    """

    def __init__(self, compiled, *, basis="Z"):
        from logical_to_stim_converter import make_decoder_view, DetectorSelector, DEMOptions

        if basis not in {"X", "Z"}:
            raise ValueError("memory decoder basis must be X or Z")
        selected = tuple(o.index for o in compiled.observables if o.basis == basis and o.logical_id == "D")
        if len(selected) != 1 or len(compiled.observables) != 1:
            raise ValueError("memory decoder requires one reliable memory observable")
        self.view = make_decoder_view(
            compiled, detector_selector=DetectorSelector(block_ids=("P0",), basis=basis),
            observable_selector=selected, cross_region_policy="retain",
            dem_options=DEMOptions(decompose_errors=False, flatten_loops=True),
        )
        self.dem = self.view.detector_error_model
        self.matching = checked_matching(self.dem)

    def predict(self, events):
        events = np.asarray(events)
        if events.dtype != bool or events.ndim != 2 or events.shape[1] != self.dem.num_detectors:
            raise ValueError("memory decoder requires an aligned bool detector-event batch")
        result = self.matching.decode_batch(events, enable_correlations=False)
        if result.shape != (len(events), 1):
            raise ValueError("memory MWPM returned an invalid observable prediction shape")
        return result.astype(bool, copy=False)

    def decode_batch(self, raw):
        from .models import DecodedBatch

        # Both arrays derive from the SAME caller-owned physical measurement batch.
        events = self.view.events_from_raw(raw)
        prediction = self.predict(events)
        actual = self.view.observable_flips_from_raw(raw)
        return DecodedBatch((actual ^ prediction)[:, 0])
