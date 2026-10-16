"""Explicit counterfactual attempt accounting, separate from circuit sampling."""

from dataclasses import asdict, dataclass
import math

import numpy as np


@dataclass(frozen=True)
class FactoryCostModel:
    unit: str = "SE_equivalent"
    initial_preparation: str = "serial"
    se_round: float = 1.
    reset: float = 0.
    teleportation: float = 0.
    preparation_decode: float = 0.
    online_decode: float = 0.
    restart: float = 0.

    def __post_init__(self):
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("cost unit must be a nonempty string")
        if not isinstance(self.initial_preparation, str) or self.initial_preparation not in {"serial", "parallel"}:
            raise ValueError("initial_preparation must be serial or parallel")
        for name in ("se_round", "reset", "teleportation", "preparation_decode", "online_decode", "restart"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"cost {name} must be finite and nonnegative")
        if self.se_round <= 0:
            raise ValueError("cost se_round must be positive")

    def prefix_costs(self, point):
        """Cost through each stage's decision; terminal oracle is excluded.

        Reset is per block preparation; SE includes its own ancilla resets.
        Teleportation includes coupling/readout; prep/online decoding are
        additional critical-path delays. Parallel initial prep assumes enough
        quantum/classical capacity to overlap both full preparation paths.
        """
        initial = [self.reset + r*self.se_round + self.preparation_decode for r in (point.r_0, point.r_plus)]
        initial = sum(initial) if self.initial_preparation == "serial" else max(initial)
        refresh = self.reset + point.r_plus*self.se_round + self.preparation_decode
        stage = self.teleportation + self.online_decode
        costs = initial + np.arange(point.T_tel)*refresh + np.arange(1, point.T_tel+1)*stage
        if not np.isfinite(costs).all() or costs[-1] > np.finfo(float).max**.5:
            raise ValueError("cost schedule overflows finite moment accounting")
        return costs

    def as_dict(self):
        return asdict(self)


def first_rejected_stage(gaps, theta):
    """Return 0 for accepted, otherwise the first rejecting stage numbered 1..T.

    Decisions use gaps only; later gaps cannot move an earlier rejection.
    """
    values = np.asarray(gaps)
    if (values.ndim != 2 or not values.shape[1] or not np.isfinite(values).all()
            or (values < 0).any() or isinstance(theta, bool) or math.isnan(float(theta))):
        raise ValueError("require finite nonnegative stage gaps and a non-NaN cut")
    rejected = values < theta
    return np.where(rejected.any(axis=1), rejected.argmax(axis=1)+1, 0)


def summarize_cost(histogram, point, model, *, iid_restarts=False):
    """Histogram index 0 is acceptance, j>0 is rejection after stage j.

    E[C]/P(A) follows the renewal equation only for iid fresh attempts with
    the declared reset/restart schedule. Dependence of cost on success within
    an attempt is allowed. Ratio SE is a paired delta-method description.
    """
    hist = np.asarray(histogram)
    if (hist.dtype.kind not in "iu" or hist.shape != (point.T_tel+1,) or (hist < 0).any()
            or hist.sum() < 1 or type(iid_restarts) is not bool):
        raise ValueError("require a nonempty nonnegative acceptance/first-rejection histogram and boolean iid flag")
    n, accepted = int(hist.sum()), int(hist[0])
    prefix = model.prefix_costs(point)
    costs = np.r_[prefix[-1], prefix + model.restart]
    if not np.isfinite(costs).all() or costs.max() > np.finfo(float).max**.5:
        raise ValueError("cost schedule overflows finite moment accounting")
    weights = hist/n
    mean = float(weights @ costs)
    variance = float(weights @ (costs-mean)**2) * n/(n-1) if n > 1 else None
    ratio = mean/(accepted/n) if accepted and iid_restarts else None
    if ratio is not None and (not math.isfinite(ratio) or ratio > np.finfo(float).max**.5):
        raise ValueError("iid cost estimate overflows finite moment accounting")
    ratio_se = None
    if ratio is not None and n > 1:
        residual = costs.copy()
        residual[0] -= ratio
        ratio_se = math.sqrt(float(weights @ residual**2)/(n-1))/(accepted/n)
    return dict(cost_unit=model.unit, cost_schedule=model.initial_preparation,
                full_trajectory_cost=float(prefix[-1]), mean_attempt_cost=mean,
                attempt_cost_standard_error=math.sqrt(variance/n) if variance is not None else None,
                iid_restarts=iid_restarts, iid_expected_attempts=n/accepted if accepted and iid_restarts else None,
                iid_cost_to_first_accepted=ratio, iid_cost_standard_error=ratio_se,
                iid_estimate_status=("not_assumed" if not iid_restarts else
                                     "estimated" if accepted else "undefined_no_observed_acceptance"))
