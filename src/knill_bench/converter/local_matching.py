"""Explicit component-independent local MWPM, retaining parallel alternatives.

This is a decoder approximation to native decomposed DEMs. It never edits the
physical circuit/model. Each graphlike component has its own zero-syndrome
subdivision node, so differently labelled parallel alternatives cannot merge.
"""

import math

import numpy as np

from .decoding import GraphlikeModelError


class LocalMatching:
    def __init__(self, detector_count, output_count, components):
        import pymatching
        import stim

        self.detector_count, self.output_count = detector_count, output_count
        self.detector_bias = np.zeros(detector_count, dtype=bool)
        self.output_bias = np.zeros(output_count, dtype=bool)
        skeleton = stim.DetectorErrorModel()
        if detector_count:
            skeleton.append("detector", [], [stim.target_relative_detector_id(detector_count-1)])
        self.matching = pymatching.Matching.from_detector_error_model(skeleton, enable_correlations=False)
        self.summary = dict(components=0, graph_components=0, prior_only_components=0, trivial_components=0,
                            zero_probability_components=0, complemented_components=0)
        self.auxiliary_count = 0
        for endpoints, labels, probability in components:
            self.summary["components"] += 1
            endpoints, labels = tuple(sorted(set(endpoints))), tuple(sorted(set(labels)))
            if (len(endpoints) > 2 or any(not 0 <= i < detector_count for i in endpoints)
                    or any(not 0 <= i < output_count for i in labels)
                    or not math.isfinite(probability) or not 0 <= probability <= 1):
                raise GraphlikeModelError("local matching requires graphlike components and valid target/probability bounds")
            if not endpoints and not labels:
                self.summary["trivial_components"] += 1
            if not endpoints and labels:
                self.summary["prior_only_components"] += 1
            if probability > .5:
                self.detector_bias[list(endpoints)] ^= True
                self.output_bias[list(labels)] ^= True
                probability = 1-probability
                self.summary["complemented_components"] += 1
            if probability == 0:
                self.summary["zero_probability_components"] += 1
                continue
            if not endpoints:
                continue  # Explicit independent component MAP hypothesis, recorded above.
            weight = math.log1p(-probability)-math.log(probability)
            node = detector_count + self.auxiliary_count
            self.matching.add_edge(endpoints[0], node, fault_ids=set(labels), weight=weight/2)
            if len(endpoints) == 2:
                self.matching.add_edge(node, endpoints[1], weight=weight/2)
            else:
                self.matching.add_boundary_edge(node, weight=weight/2)
            self.auxiliary_count += 1
            self.summary["graph_components"] += 1
        self.matching.ensure_num_fault_ids(output_count)
        if (self.matching.num_detectors != detector_count+self.auxiliary_count
                or self.matching.num_fault_ids != output_count):
            raise GraphlikeModelError("local matching graph changed declared input/output dimensions")

    @classmethod
    def temporal(cls, dem, *, output_count):
        """Keep every native ^ component; reject residual hyperedges, never trim.

        Correlation between components is explicitly ignored. Invisible target
        components use their individual prior-MAP bit (q>1/2); no probe is sampled.
        """
        components, errors, separated = [], 0, 0
        for instruction in dem.flattened():
            if instruction.type != "error":
                continue
            errors += 1
            probability, = instruction.args_copy()
            detectors, targets = set(), set()
            for item in instruction.targets_copy():
                if item.is_separator():
                    components.append((detectors, targets, probability))
                    detectors, targets = set(), set()
                    separated += 1
                elif item.is_relative_detector_id():
                    detectors.symmetric_difference_update((item.val,))
                elif item.is_logical_observable_id():
                    targets.symmetric_difference_update((item.val,))
                else:
                    raise GraphlikeModelError("unsupported temporal DEM target")
            components.append((detectors, targets, probability))
        if dem.num_observables > output_count:
            raise GraphlikeModelError("temporal DEM has unknown prediction targets")
        result = cls(dem.num_detectors, output_count, components)
        result.summary.update(source_events=errors, separators=separated)
        return result

    @classmethod
    def capacity(cls, check_matrix):
        matrix = np.asarray(check_matrix)
        if matrix.ndim != 2 or not np.isin(matrix, (0, 1)).all():
            raise GraphlikeModelError("capacity matching requires a binary check matrix")
        # q chosen only to encode unit Hamming edge cost, not a physical channel.
        components = [(np.flatnonzero(matrix[:, j]), (j,), 1/(1+math.e)) for j in range(matrix.shape[1])]
        if any(not len(c[0]) for c in components):
            raise GraphlikeModelError("unconstrained capacity columns are unsupported")
        return cls(matrix.shape[0], matrix.shape[1], components)

    def decode(self, events):
        events = np.asarray(events)
        if events.dtype != bool or events.ndim != 2 or events.shape[1] != self.detector_count:
            raise ValueError("local matching requires aligned bool syndrome batches")
        lifted = np.zeros((len(events), self.detector_count+self.auxiliary_count), dtype=bool)
        lifted[:, :self.detector_count] = events ^ self.detector_bias
        result = self.matching.decode_batch(lifted, enable_correlations=False).astype(bool)
        return result ^ self.output_bias
