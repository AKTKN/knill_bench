"""Optional decimal half-up rounding before any notebook gap statistics."""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from functools import lru_cache
import math

import numpy as np


def validate_round_digit(value):
    if value is not None and (type(value) is not int or not -308 <= value <= 308):
        raise ValueError("round_digit must be None or an integer in [-308, 308]")
    return value


@lru_cache(maxsize=4096)
def _rounded_value(value, digits):
    # Decimal(str(float)) makes conventional decimal ties explicit (2.675 ->
    # 2.68). Cache only distinct values, never trajectories or all-shot arrays.
    with localcontext() as context:
        context.prec = 650
        result = float(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))
    if not math.isfinite(result):
        raise ValueError("round_digit produces a nonfinite logical gap")
    return result


def round_gaps(scores, round_digit):
    """Return rounded bounded-batch scores, leaving raw input unchanged.

    Raw finite/nonnegative score validation belongs to SavedPoint.batches and
    always precedes this transformation. None returns the original array.
    """
    validate_round_digit(round_digit)
    if round_digit is None:
        return scores
    unique, inverse = np.unique(scores, return_inverse=True)
    rounded = np.array([_rounded_value(float(v), round_digit) for v in unique])
    return rounded[inverse].reshape(scores.shape)
