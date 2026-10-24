"""Evaluator-only fixed-R sign/code/readout errors and bounded batch counts.

Only this layer joins sampled truth to predictions. Cuts use validity and
gap alone; sampled errors cannot affect acceptance. Undefined errors/rates
have explicit masks/null denominators, including valid baselines lacking a
complement. No sampler, correction, stopping policy or result writer is used.
"""

from dataclasses import dataclass
from numbers import Real

import numpy as np

from knill_bench.preparation import PreparationPrediction, PreparationTruth


def _threshold(value) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError("gap threshold must be a real number (infinities allowed), not NaN")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError("gap threshold cannot overflow float64") from error
    if np.isnan(result):
        raise ValueError("gap threshold cannot be NaN")
    return result


def preparation_acceptance(prediction: PreparationPrediction, threshold=-np.inf) -> np.ndarray:
    """AND of all three validity masks and inclusive gap>=g; no truth input."""
    prediction.__post_init__()
    cut = _threshold(threshold)
    return (prediction.baseline_valid & prediction.complementary_valid & prediction.z_decoder_valid
            & (prediction.gap >= cut))


@dataclass(frozen=True)
class PreparationEvaluation:
    """Batch-local labels and explicit masks; invalid error bits are placeholders.

    E_code requires both X/Z baselines, E_LZ only the Z baseline. A missing X
    complement never erases valid baseline statistics. joint_counts uses
    only code-valid rows and the bit index 4*E_sX + 2*E_sZ + E_LZ.
    """

    error_bits_x: np.ndarray
    error_bits_z: np.ndarray
    sign_miss_x: np.ndarray
    sign_miss_z: np.ndarray
    code_space_miss: np.ndarray
    logical_z_error: np.ndarray
    x_valid: np.ndarray
    z_valid: np.ndarray
    code_valid: np.ndarray
    logical_valid: np.ndarray
    complementary_valid: np.ndarray
    eligible: np.ndarray
    gap: np.ndarray
    status: np.ndarray

    def accepted(self, threshold=-np.inf):
        return self.eligible & (self.gap >= _threshold(threshold))


def evaluate_preparation(truth: PreparationTruth, prediction: PreparationPrediction) -> PreparationEvaluation:
    """Apply the prefix software parity frame exactly once, independently by CSS.

    tau truth XOR tau prediction gives sign errors, and logical_Z truth XOR
    Z-prefix prediction gives the declared readout failure. There is no pure-
    error LUT, physical correction or extra terminal syndrome recovery.
    """
    truth.__post_init__()
    prediction.__post_init__()
    for label, response in ((truth.tau_x, prediction.tau_x_prediction),
                            (truth.tau_z, prediction.tau_z_prediction),
                            (truth.logical_z, prediction.logical_z_prediction)):
        if label.shape != response.shape:
            raise ValueError("truth/prediction shot and check dimensions disagree")
    xvalid, zvalid = prediction.baseline_valid.copy(), prediction.z_decoder_valid.copy()
    xbits = (truth.tau_x ^ prediction.tau_x_prediction) & xvalid[:, None]
    zbits = (truth.tau_z ^ prediction.tau_z_prediction) & zvalid[:, None]
    sx, sz = xbits.any(axis=1), zbits.any(axis=1)
    code_valid = xvalid & zvalid
    code_miss = (sx | sz) & code_valid
    logical = (truth.logical_z ^ prediction.logical_z_prediction)[:, 0] & zvalid
    return PreparationEvaluation(
        xbits, zbits, sx, sz, code_miss, logical, xvalid, zvalid, code_valid, zvalid.copy(),
        prediction.complementary_valid.copy(), preparation_acceptance(prediction),
        prediction.gap.copy(), prediction.status.copy(),
    )


def summarize_preparation(evaluation: PreparationEvaluation, *, threshold=-np.inf) -> dict:
    """Compact integer counts and empirical rates, no confidence/calibration claim.

    Intended per bounded chunk; the later runner will combine counts. The
    selected statistics require all validity flags. Unconditional baselines
    keep their separate denominators, even if no gap was available.
    """
    cut = _threshold(threshold)
    accepted = evaluation.accepted(cut)
    count = len(evaluation.gap)

    def metric(errors, valid):
        n, k = int(np.count_nonzero(valid)), int(np.count_nonzero(errors & valid))
        return dict(shots=n, errors=k, rate=k / n if n else None)

    def table(mask):
        xv, zv = mask & evaluation.x_valid, mask & evaluation.z_valid
        cv = mask & evaluation.code_valid
        lv = mask & evaluation.logical_valid
        joint = 4 * evaluation.sign_miss_x.astype(np.uint8) + 2 * evaluation.sign_miss_z + evaluation.logical_z_error
        code_correct = cv & ~evaluation.code_space_miss
        return dict(
            sign_x=metric(evaluation.sign_miss_x, xv), sign_z=metric(evaluation.sign_miss_z, zv),
            code_space=metric(evaluation.code_space_miss, cv), logical_z=metric(evaluation.logical_z_error, lv),
            logical_z_given_code_correct=metric(evaluation.logical_z_error, code_correct),
            per_check_errors_x=np.count_nonzero(evaluation.error_bits_x[xv], axis=0).tolist(),
            per_check_errors_z=np.count_nonzero(evaluation.error_bits_z[zv], axis=0).tolist(),
            error_count_histogram_x=np.bincount(evaluation.error_bits_x[xv].sum(axis=1).astype(np.int64),
                minlength=evaluation.error_bits_x.shape[1] + 1).tolist(),
            error_count_histogram_z=np.bincount(evaluation.error_bits_z[zv].sum(axis=1).astype(np.int64),
                minlength=evaluation.error_bits_z.shape[1] + 1).tolist(),
            joint_denominator=int(np.count_nonzero(cv)),
            joint_counts=np.bincount(joint[cv], minlength=8).tolist(),
        )

    names, counts = np.unique(evaluation.status, return_counts=True)
    return dict(
        metric_version=1, logical_evaluation="prefix_frame_only", shots=count,
        threshold="-inf" if np.isneginf(cut) else "+inf" if np.isposinf(cut) else cut,
        eligible=int(np.count_nonzero(evaluation.eligible)), accepted=int(np.count_nonzero(accepted)),
        acceptance=int(np.count_nonzero(accepted)) / count if count else None,
        invalid_reasons=dict(
            x_baseline=int(np.count_nonzero(~evaluation.x_valid)),
            no_complement=int(np.count_nonzero(evaluation.x_valid & ~evaluation.complementary_valid)),
            z_decoder=int(np.count_nonzero(~evaluation.z_valid)),
        ),
        below_cut=int(np.count_nonzero(evaluation.eligible & ~accepted)),
        status_counts={str(name): int(n) for name, n in zip(names, counts)},
        unconditional=table(np.ones(count, dtype=bool)), selected=table(accepted),
    )
