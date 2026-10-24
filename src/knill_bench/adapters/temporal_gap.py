"""Fixed-R batch X temporal gap plus independent known-zero Z-prefix MWPM.

The constructor accepts static response models only. Neither it nor decoding
accepts a compiled evaluator, measurement records, sampled truth or boundary
outcomes. One software parity frame is predicted; physical data is untouched.
"""

import hashlib
import json
from pathlib import Path
from time import perf_counter_ns

import numpy as np
import pymatching

from knill_bench.decoding.preparation_prefix import PrefixDemModel
from knill_bench.decoding.temporal_dem import TemporalDemModel, _canonical_json
from knill_bench.decoding.temporal_matching import TemporalMatching, TemporalStatus, _StaticMatcher
from knill_bench.preparation import (
    PreparationCapabilityError, PreparationDiagnostics, PreparationObservations,
    PreparationPrediction, PreparationStatus,
)


def _check_rows(names, metric):
    by_index = {}
    for row, name in enumerate(names):
        if name.startswith(metric + ":"):
            text = name[len(metric) + 1:]
            if not text.isdigit() or str(int(text)) != text or int(text) in by_index:
                raise ValueError(f"invalid {metric} feature identity")
            by_index[int(text)] = row
    if not by_index or set(by_index) != set(range(len(by_index))):
        raise ValueError(f"missing/noncontiguous {metric} feature identities")
    return tuple(by_index[i] for i in range(len(by_index)))


class TemporalGapDecoder:
    """Cache the supplied two-solve core and one ordinary Z-prefix topology.

    output_mode is part of the definition/hash and fixed for this instance.
    Full witnesses are prewarmed and always come from the same solve as their
    features; debug agreement flags never authorize attaching them to a
    different compact result. Model active_columns and frozen original IDs
    remain separate in the definition and returned diagnostics.
    """

    def __init__(self, x_model: TemporalDemModel, z_model: PrefixDemModel, *,
                 output_mode="compact", logical_evaluation="prefix_frame_only"):
        started = perf_counter_ns()
        if logical_evaluation != "prefix_frame_only" or z_model.logical_evaluation != logical_evaluation:
            raise PreparationCapabilityError("temporal_gap supports prefix_frame_only; terminal_recovery needs a separate protocol")
        if output_mode not in {"compact", "full_witness"}:
            raise ValueError("output_mode must be compact or full_witness")
        if z_model.scope != "known_zero_Z_prefix_v1":
            raise PreparationCapabilityError("Z inference requires the known-initial-zero prefix scope")
        if x_model.weight_scale != z_model.weight_scale:
            raise ValueError("X and Z models must declare the same common weight_scale")
        x_origin = x_model.metadata["provenance"].get("model_hashes", {}).get("model_circuit")
        z_origin = z_model.metadata["provenance"].get("model_hashes", {}).get("model_circuit")
        if x_origin != z_origin:
            raise ValueError("X and Z models refer to different nominal experiments")
        self.x_model, self.z_model = x_model, z_model
        self._output_mode, self._weight_scale = output_mode, x_model.weight_scale
        self.x_rows = _check_rows(x_model.feature_ids, "tau_x")
        self.z_rows = _check_rows(z_model.feature_ids, "tau_z")
        if z_model.feature_ids.count("logical_z") != 1:
            raise ValueError("Z model requires exactly one logical_z feature")
        self.logical_row = z_model.feature_ids.index("logical_z")
        kwargs = x_model.matching_kwargs()
        kwargs["feature_map"] = kwargs["feature_map"][list(self.x_rows), :]
        begin = perf_counter_ns()
        self.x_core = TemporalMatching(**kwargs)
        if output_mode == "full_witness":
            self.x_core.prepare_full_witness()
        x_ns = perf_counter_ns() - begin
        begin = perf_counter_ns()
        active = z_model.active_columns
        self.z_matcher = _StaticMatcher(z_model.h[:, active], z_model.weights[active], z_model.feature_map[:, active])
        if output_mode == "full_witness":
            self.z_matcher.prepare_full_witness()
        z_ns = perf_counter_ns() - begin
        self.frozen_original_columns = tuple(int(x_model.active_columns[j]) for j in self.x_core.frozen_columns)
        import knill_bench.decoding.temporal_matching as kernel
        import knill_bench.decoding.preparation_prefix as prefix
        definition = dict(
            kind="temporal_gap", definition_version=1, output_mode=output_mode,
            logical_evaluation=logical_evaluation, physical_correction_applied=False,
            terminal_recovery=False, x_model_sha256=x_model.artifact_sha256, z_model_sha256=z_model.model_sha256,
            weight_scale=self.weight_scale, gap_unit="quantized_natural_log_score",
            weight_rounding=x_model.weight_rounding, pymatching_version=pymatching.__version__,
            tie_policy="native_same_solve_fixed_output_mode_invisible_zero_v1",
            parallel_policy="private_degree_two_subdivision_v1",
            x_feature_ids=[x_model.feature_ids[i] for i in self.x_rows], z_feature_ids=list(z_model.feature_ids),
            x_active_columns=x_model.active_columns.tolist(), z_active_columns=active.tolist(),
            x_mechanism_ids=list(kwargs["mechanism_ids"]),
            z_mechanism_ids=[z_model.mechanism_ids[j] for j in active],
            frozen_original_columns=list(self.frozen_original_columns),
            z_scope=z_model.scope, z_detector_ids=list(z_model.detector_ids),
            accepted_input="unpacked_bool_or_explicit_little_endian_packed_method",
            source_hashes={name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in
                           (("adapter", __file__), ("matching_core", kernel.__file__), ("prefix_model", prefix.__file__))},
        )
        self._definition_json = _canonical_json(definition)
        self.model_sha256 = hashlib.sha256(self._definition_json.encode()).hexdigest()
        self.setup_timings_ns = dict(x_graphs=x_ns, z_graph=z_ns, total=perf_counter_ns() - started)
        self.last_decode_timings_ns = None

    @property
    def metadata(self):
        return dict(definition=json.loads(self._definition_json), model_sha256=self.model_sha256)

    @property
    def output_mode(self):
        return self._output_mode

    @property
    def weight_scale(self):
        return self._weight_scale

    def decode_batch(self, online_x_detectors, online_z_detectors) -> PreparationPrediction:
        started = perf_counter_ns()
        observations = PreparationObservations(online_x_detectors, online_z_detectors)
        x, z = observations.online_x_detectors, observations.online_z_detectors
        if x.shape[1] != self.x_core.num_detectors or z.shape[1] != self.z_matcher.num_rows:
            raise ValueError("online detector dimensions disagree with static X/Z models")
        full = self.output_mode == "full_witness"
        begin = perf_counter_ns()
        result = self.x_core.decode_batch(x, return_errors=full)
        x_ns = perf_counter_ns() - begin
        begin = perf_counter_ns()
        zvalid = self.z_matcher.feasible(z)
        ids = np.flatnonzero(zvalid)
        features, weights, errors, agrees = self.z_matcher.decode_batch(z[ids], return_errors=full)
        if (not np.isfinite(weights).all() or (weights < 0).any() or (weights > 2**53 - 1).any()
                or not np.equal(weights, np.rint(weights)).all()):
            raise RuntimeError("Z-prefix backend returned an invalid common integer cost")
        z_features = np.zeros((len(z), self.z_matcher.num_features), dtype=bool)
        z_features[ids] = features
        z_weight = np.full(len(z), np.inf)
        z_weight[ids] = weights
        z_errors = np.zeros((len(z), self.z_matcher.num_columns), dtype=np.uint8) if full else None
        z_agrees = np.zeros(len(z), dtype=bool) if full else None
        if full:
            z_errors[ids], z_agrees[ids] = errors, agrees
        z_ns = perf_counter_ns() - begin
        baseline_valid = result.status != TemporalStatus.INVALID_SYNDROME.value
        complementary_valid = result.status == TemporalStatus.OK.value
        status = result.status.copy()
        status[complementary_valid & ~zvalid] = PreparationStatus.Z_DECODER_INVALID.value
        diagnostics = PreparationDiagnostics(
            self.frozen_original_columns, result.baseline_frozen.astype(bool),
            result.baseline_past.astype(bool), result.baseline_future.astype(bool),
            z_weight, z_errors, z_agrees,
        )
        prediction = PreparationPrediction(
            result.baseline_features.astype(bool), z_features[:, self.z_rows].copy(),
            z_features[:, self.logical_row:self.logical_row + 1].copy(),
            result.baseline_weights, result.complementary_weights, result.gaps / self.weight_scale,
            baseline_valid, complementary_valid, zvalid, status, self.weight_scale,
            result if full else None, diagnostics,
        )
        self.last_decode_timings_ns = dict(x_comparative=x_ns, z_prefix=z_ns, total=perf_counter_ns() - started)
        return prediction

    def decode_one(self, online_x_detectors, online_z_detectors) -> PreparationPrediction:
        x, z = np.asarray(online_x_detectors), np.asarray(online_z_detectors)
        if x.ndim != 1 or z.ndim != 1:
            raise ValueError("decode_one requires one-dimensional bool detector arrays")
        return self.decode_batch(x[None, :], z[None, :])

    def decode_packed_batch(self, online_x_detectors, online_z_detectors) -> PreparationPrediction:
        """Explicit little-endian uint8 input; reject nonzero padding bits."""
        def unpack(value, count):
            if (not isinstance(value, np.ndarray) or value.dtype != np.uint8 or value.ndim != 2
                    or value.shape[1] != (count + 7) // 8):
                raise ValueError("packed detectors must be uint8[shots, ceil(detectors/8)]")
            if count % 8 and (value[:, -1] >> (count % 8)).any():
                raise ValueError("packed detector padding bits must be zero")
            return np.unpackbits(value, axis=1, count=count, bitorder="little").astype(bool)
        return self.decode_batch(unpack(online_x_detectors, self.x_core.num_detectors),
                                 unpack(online_z_detectors, self.z_matcher.num_rows))


def prepare_preparation_decoder(compiled, *, weight_scale=1000, output_mode="compact") -> TemporalGapDecoder:
    """Setup convenience; return an adapter with no compiled-evaluator reference."""
    from knill_bench.decoding.preparation_model import compile_preparation_boundary_model, compile_preparation_prefix_model
    begin = perf_counter_ns()
    x_model = compile_preparation_boundary_model(compiled, weight_scale=weight_scale)
    z_model = compile_preparation_prefix_model(compiled, weight_scale=weight_scale)
    models_ns = perf_counter_ns() - begin
    decoder = TemporalGapDecoder(x_model, z_model, output_mode=output_mode,
        logical_evaluation=compiled.settings.logical_evaluation)
    decoder.setup_timings_ns["models"] = models_ns
    decoder.setup_timings_ns["total"] += models_ns
    return decoder
