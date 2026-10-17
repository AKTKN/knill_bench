"""Factory-only preparation frames with unchanged Hex matching decisions.

Only final check values and exit X/Z frames are materialized. Native Hex's
public PreparationFramePlan (including its full-history result) stays intact.
All four native decoders and their tie-breaking/logical conventions are reused.
"""

from dataclasses import dataclass

import numpy as np
from scipy import sparse


FRAME_IMPLEMENTATION = "factory_packed_preparation_frames_v1"


class PackedGF2Map:
    """Row-vector GF(2) product using byte lookup tables and bounded gathers.

    Eight input bits select the XOR of eight packed matrix rows. Tables are
    built once per preparation template; execution never constructs CSR or
    dense full-history correction arrays. At most 32 input bytes are gathered
    at once, bounding scratch by batch_size * 32 * packed_output_width.
    """

    def __init__(self, matrix):
        matrix = matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)
        if matrix.ndim != 2:
            raise ValueError("GF(2) map must be a matrix")
        self.inputs, self.outputs = matrix.shape
        groups = (self.inputs + 7) // 8
        width = (self.outputs + 7) // 8
        rows = np.zeros((groups * 8, width), dtype=np.uint8)
        rows[:self.inputs] = np.packbits(np.asarray(matrix % 2, dtype=np.uint8),
                                        axis=1, bitorder="little")
        rows = rows.reshape(groups, 8, width)
        self._table = np.zeros((groups, 256, width), dtype=np.uint8)
        for bit in range(8):
            stop = 1 << bit
            self._table[:, stop:2*stop] = self._table[:, :stop] ^ rows[:, bit:bit+1]
        self._indices = np.arange(groups)
        self._table.flags.writeable = False

    def packed(self, bits):
        bits = np.asarray(bits)
        if bits.ndim != 2 or bits.shape[1] != self.inputs:
            raise ValueError("GF(2) input has wrong width")
        codes = np.packbits(bits, axis=1, bitorder="little")
        output = np.zeros((len(bits), (self.outputs + 7)//8), dtype=np.uint8)
        for start in range(0, len(self._indices), 32):
            stop = start + 32
            selected = self._table[self._indices[None, start:stop], codes[:, start:stop]]
            output ^= np.bitwise_xor.reduce(selected, axis=1)
        return output

    def apply(self, bits):
        return np.unpackbits(self.packed(bits), axis=1, count=self.outputs,
                             bitorder="little").astype(bool)


@dataclass(frozen=True)
class ExitFrame:
    x: np.ndarray
    z: np.ndarray


class FactoryPreparationPlan:
    """Narrow H5 binding consumed only by native FactoryBatchDecoder.

    This intentionally returns only ExitFrame; callers needing corrected
    histories/sign diagnostics continue to use the original native plan.
    """

    def __init__(self, plan):
        self.module, self.region = plan.module, plan.region
        self._x_converter, self._z_converter = plan._x_converter, plan._z_converter
        module = self.module
        self._n = module.num_data_qubits
        self._mx, self._mz = module.num_x_stabilizers, module.num_z_stabilizers
        self._checks = self._mx + self._mz
        x_history = module.x_dem_correction_to_local_measurement_flips
        z_history = module.z_dem_correction_to_local_measurement_flips
        nx, nz = x_history.shape[0], z_history.shape[0]
        # Fuse exit-frame maps with ONLY the final check columns. Both sectors
        # map to the same packed output, so combine them by XOR before unpacking.
        final = sparse.vstack((x_history[:, -self._checks:], z_history[:, -self._checks:]), format="csc")
        combined = sparse.hstack((plan.x_map[:nx+nz], plan.z_map[:nx+nz], final), format="csr")
        self._x_map = PackedGF2Map(combined[:nx])
        self._z_map = PackedGF2Map(combined[nx:])
        self._x_checks = PackedGF2Map(module.x_pcm.T)
        self._z_checks = PackedGF2Map(module.z_pcm.T)

    def bind(self, region):
        from copy import copy
        if region.measurements.stop - region.measurements.start != self.module.num_measurements:
            raise ValueError("preparation region has the wrong measurement width")
        result = copy(self)
        result.region = region
        return result

    def resolve(self, measurements):
        batch = np.asarray(measurements)
        module = self.module
        if batch.ndim != 2 or batch.shape[1] != module.num_measurements:
            raise ValueError("expected exactly the local preparation measurement batch")
        if not np.all((batch == 0) | (batch == 1)):
            raise ValueError("preparation measurements must be binary")
        batch = batch.astype(bool, copy=False)
        x_syndromes = self._x_converter.convert(measurements=batch, separate_observables=True)[0]
        z_syndromes = self._z_converter.convert(measurements=batch, separate_observables=True)[0]
        x_dem = module.x_dem_decoder.decode_batch(x_syndromes).correction
        z_dem = module.z_dem_decoder.decode_batch(z_syndromes).correction
        packed = self._x_map.packed(x_dem) ^ self._z_map.packed(z_dem)
        combined = np.unpackbits(packed, axis=1, count=2*self._n+self._checks,
                                 bitorder="little").astype(bool)
        final = batch[:, -self._checks:] ^ combined[:, 2*self._n:]
        last_x, last_z = final[:, :self._mx], final[:, self._mx:]
        # Keep the SAME native capacity decoders: no new pure-error convention,
        # representative selection, weight policy or logical-class assumption.
        z_repair = module.x_decoder.decode_batch(last_x).correction
        x_repair = module.z_decoder.decode_batch(last_z).correction
        if (np.any(last_x ^ self._x_checks.apply(z_repair))
                or np.any(last_z ^ self._z_checks.apply(x_repair))):
            raise ValueError("preparation decoder did not resolve all stabilizer signs")
        return ExitFrame(combined[:, :self._n] ^ np.asarray(x_repair, dtype=bool),
                         combined[:, self._n:2*self._n] ^ np.asarray(z_repair, dtype=bool))
