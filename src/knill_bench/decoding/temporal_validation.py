"""Validation-only marginal parity models; never matching/inference inputs.

Hidden past/future detector outputs are discarded, retaining all requested
online/evaluation outputs. Independent events with identical projected
signatures XOR-compose, not probability-sum. Terms in the actual boundary
model remain separate, even when this comparison aggregates them.
"""

import hashlib
import json
import math

import numpy as np
import stim

from .temporal_dem import _ordered_ids


def marginal_parity_probabilities(dem: stim.DetectorErrorModel, *, detector_ids,
                                  observable_ids) -> dict:
    """Project onto explicit ordered outputs and aggregate independent parity.

    Complete production evaluation declarations must be retained. An ordinary
    observable-stripped prefix DEM cannot validate output-state truth.
    Empty-output and p0 terms have no effect on this marginal distribution.
    """
    detectors = _ordered_ids(detector_ids, dem.num_detectors, "detector_ids")
    observables = _ordered_ids(observable_ids, dem.num_observables, "observable_ids")
    dmap, omap = ({j: i for i, j in enumerate(ids)} for ids in (detectors, observables))
    logs = {}
    for op in dem.flattened():
        if op.type in {"detector", "logical_observable"}:
            continue
        if op.type != "error":
            raise ValueError(f"Unsupported flattened DEM instruction: {op.type}")
        p = op.args_copy()[0]
        # Validate probability only; no quantization/weight range is relevant.
        if not math.isfinite(p) or not 0 <= p < .5:
            raise ValueError("Marginal DEM probabilities must satisfy 0 <= p < 0.5")
        ds, ls = set(), set()
        for target in op.targets_copy():
            if target.is_separator():
                raise ValueError("Marginal comparison rejects correlated DEM separators")
            if target.is_relative_detector_id():
                if not 0 <= target.val < dem.num_detectors:
                    raise ValueError("Marginal detector ID out of range")
                if target.val in dmap:
                    ds.symmetric_difference_update([dmap[target.val]])
            elif target.is_logical_observable_id():
                if not 0 <= target.val < dem.num_observables:
                    raise ValueError("Marginal observable ID out of range")
                if target.val in omap:
                    ls.symmetric_difference_update([omap[target.val]])
            else:
                raise ValueError(f"Unsupported marginal DEM target: {target}")
        key = (tuple(sorted(ds)), tuple(sorted(ls)))
        if any(key) and p > 0:
            logs.setdefault(key, []).append(math.log1p(-2 * p))
    # Stable form of (1-product(1-2*p))/2, including tiny probabilities.
    return {key: -.5 * math.expm1(math.fsum(values)) for key, values in sorted(logs.items())}


def compare_marginal_models(production_dem, completed_dem, *, production_detector_ids,
                            completed_detector_ids, production_observable_ids,
                            completed_observable_ids, atol=1e-14, rtol=1e-12) -> dict:
    """Certify the same projected parity model within explicit binary64 bounds.

    This is an algebraic factor/signature comparison, not statistical sampling
    or a proof of the shadow-probe instrument. The circuit builder certifies
    that instrument separately. Returned provenance contains no merged graph.
    """
    if (not np.isfinite([atol, rtol]).all() or atol < 0 or rtol < 0):
        raise ValueError("Marginal comparison tolerances must be finite and nonnegative")
    if (len(production_detector_ids) != len(completed_detector_ids)
            or len(production_observable_ids) != len(completed_observable_ids)):
        raise ValueError("Marginal output dimensions do not match")
    a = marginal_parity_probabilities(production_dem, detector_ids=production_detector_ids,
                                     observable_ids=production_observable_ids)
    b = marginal_parity_probabilities(completed_dem, detector_ids=completed_detector_ids,
                                     observable_ids=completed_observable_ids)
    if a.keys() != b.keys():
        raise ValueError("Production/completed marginal signature supports differ")
    max_difference = max((abs(a[key] - b[key]) for key in a), default=0.)
    if any(not math.isclose(a[key], b[key], abs_tol=atol, rel_tol=rtol) for key in a):
        raise ValueError(f"Production/completed marginal probabilities differ (max={max_difference})")

    def digest(values):
        rows = [[list(key[0]), list(key[1]), p] for key, p in values.items()]
        return hashlib.sha256(json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    return dict(validation="same_online_and_evaluation_independent_parity_v1",
                signatures=len(a), max_probability_difference=max_difference,
                atol=float(atol), rtol=float(rtol),
                production_marginal_sha256=digest(a), completed_marginal_sha256=digest(b))
