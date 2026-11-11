"""Public consumer-side simulation contracts and reserved-kind guard."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    import stim


class SimulationModel(Protocol):
    """Worker-local static state; native graphs/circuits never enter IPC.

    circuit is the exact circuit sampled, including evaluation probes if any.
    Original program text, converter export metadata (exact instruction args),
    decoder and source-bound frame plan must describe that same model. Terminal
    evaluator records must be excluded from decoder/frame inputs.
    """

    circuit: "stim.Circuit"
    lstim_source: str
    decoder: object
    frame_plan: object
    metadata: dict

    def decode_batch(self, measurements: np.ndarray) -> "DecodedBatch": ...


@dataclass(frozen=True)
class DecodedBatch:
    logical_error: np.ndarray

    def __post_init__(self):
        if (not isinstance(self.logical_error, np.ndarray) or self.logical_error.dtype != bool
                or self.logical_error.ndim != 1):
            raise ValueError("converter batch decode must return a boolean per-shot vector")


def require_scientific_runner(kind):
    raise NotImplementedError(f"{kind}: scientific runner is not implemented yet")
