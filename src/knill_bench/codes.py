"""The authoritative geometry and row ordering are the requested Hex matrices."""
from dataclasses import dataclass
import numpy as np
from hex_qec.circuit_generation.circuit_generation import (
    get_parity_check_matrices, create_stabilizers_and_block_template, generate_blocks,
)


def gf2_rank(a):
    a = np.asarray(a, dtype=np.uint8).copy()
    rank = 0
    for col in range(a.shape[1]):
        candidates = np.flatnonzero(a[rank:, col])
        if not len(candidates):
            continue
        pivot = rank + candidates[0]
        a[[rank, pivot]] = a[[pivot, rank]]
        for row in np.flatnonzero(a[:, col]):
            if row != rank:
                a[row] ^= a[rank]
        rank += 1
        if rank == len(a):
            break
    return rank


@dataclass
class Code:
    distance: int
    matrices: tuple
    template: dict
    stabilizers: tuple

    @classmethod
    def rotated(cls, distance):
        if type(distance) is not int or distance < 3 or distance % 2 != 1:
            raise ValueError("distance must be an odd integer >= 3")
        try:
            matrices = tuple(m.tocsr().astype(np.uint8) for m in get_parity_check_matrices("surface", distance))
        except IndexError as exc:
            raise ValueError(f"Hex checkout has no rotated surface matrices for d={distance}") from exc
        hx, hz, lx, lz = (m.toarray() for m in matrices)
        assert hx.shape[1] == distance**2
        assert not np.any(hx @ hz.T % 2)
        assert not np.any(hx @ lz.T % 2) and not np.any(hz @ lx.T % 2)
        assert lx.shape[0] == lz.shape[0] == 1 and (lx @ lz.T % 2)[0, 0] == 1
        assert distance**2 - gf2_rank(hx) - gf2_rank(hz) == 1
        template, stabs, _, _ = create_stabilizers_and_block_template(*matrices)
        return cls(distance, matrices, template, stabs)

    def blocks(self, count):
        return generate_blocks(count, self.template)

    def coordinates(self):
        return [(i % self.distance, i // self.distance) for i in range(self.distance**2)]
