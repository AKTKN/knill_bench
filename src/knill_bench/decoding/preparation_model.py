"""Setup-time certified X boundary model for the native fixed-R experiment.

Only explicit builder maps establish roles and output identities. No gate-name,
coordinate or fault-type heuristic is used. This is not the prompt-03 decoder:
it constructs no matching graphs and accepts no observations or evaluator data.
"""

from dataclasses import asdict
import hashlib
from pathlib import Path

from knill_bench.preparation import (
    CompiledPreparationExperiment, DetectorRole, PreparationCapabilityError,
)
from .temporal_dem import TemporalDemModel, completed_dem_to_temporal_model
from .temporal_validation import compare_marginal_models
from .preparation_prefix import PrefixDemModel, prefix_dem_to_model


def compile_preparation_boundary_model(compiled: CompiledPreparationExperiment, *,
                                        weight_scale=1000) -> TemporalDemModel:
    """Validate nominal production/completed outputs, then compile one artifact.

    Nominal decoding_p, rather than physical p, defines both comparison models.
    Every evaluation label (tau_X, tau_Z, logical_Z) is retained in original
    order; the later adapter selects its required rows. No truth is sampled.
    Save with temporal_artifact.write_temporal_model at runner setup; reload
    with read_temporal_model to avoid DEM parsing on the decode path.
    """
    def row_key(row):
        return row.sector, row.round_index, row.check_index

    def label_key(row):
        return row.metric, row.check_index

    try:
        prod_rows, complete_rows = compiled.detectors, compiled.completed_detectors
        if (tuple(r.detector_id for r in prod_rows) != tuple(range(compiled.model_dem.num_detectors))
                or tuple(r.detector_id for r in complete_rows) != tuple(range(compiled.completed_dem.num_detectors))
                or any(r.role != DetectorRole.ONLINE for r in prod_rows)
                or any(r.sector != "x" for r in complete_rows)):
            raise ValueError("detector namespace/role map disagrees with declared DEM rows")
        prod_online = [r for r in prod_rows if r.sector == "x"]
        complete_online = [r for r in complete_rows if r.role == DetectorRole.ONLINE]
        prod_keys, complete_keys = [row_key(r) for r in prod_online], [row_key(r) for r in complete_online]
        if (prod_keys != complete_keys or len(set(prod_keys)) != len(prod_keys)):
            raise ValueError("production/completed online row identities/order differ")
        prod_labels, complete_labels = compiled.observables, compiled.completed_observables
        if (tuple(r.observable_id for r in prod_labels) != tuple(range(compiled.model_circuit.num_observables))
                or tuple(r.observable_id for r in complete_labels) != tuple(range(compiled.completed_circuit.num_observables))
                or [label_key(r) for r in prod_labels] != [label_key(r) for r in complete_labels]
                or len({label_key(r) for r in prod_labels}) != len(prod_labels)):
            raise ValueError("production/completed evaluation identities/order differ")
        certificate = compare_marginal_models(
            compiled.model_dem, compiled.completed_dem,
            production_detector_ids=[r.detector_id for r in prod_online],
            completed_detector_ids=[r.detector_id for r in complete_online],
            production_observable_ids=[r.observable_id for r in prod_labels],
            completed_observable_ids=[r.observable_id for r in complete_labels],
        )
        names = [r.metric if r.check_index is None else f"{r.metric}:{r.check_index}" for r in complete_labels]
        return completed_dem_to_temporal_model(
            compiled.completed_dem, detector_roles=[r.role for r in complete_rows],
            num_observables=len(complete_labels), feature_ids=names, weight_scale=weight_scale,
            model_provenance=dict(
                source="native_fixed_R_X_shadow_completion", completion_certified=True,
                instrument_validation="signed_CSS_and_logical_flows", sector="x",
                rounds=compiled.settings.rounds, decoding_p=compiled.decoding_probability,
                source_hashes=dict(compiled.source_hashes), model_hashes=dict(compiled.model_hashes),
                boundary_source_hashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in ("preparation_model.py", "temporal_dem.py", "temporal_validation.py")},
                hex_revision=compiled.hex_revision, hex_dirty=compiled.hex_dirty,
                detector_map=[asdict(r) for r in complete_rows],
                evaluation_map=[asdict(r) for r in complete_labels],
                production_online_ids=[r.detector_id for r in prod_online],
                marginal_certificate=certificate,
            ),
        )
    except ValueError as error:
        raise PreparationCapabilityError(f"preparation boundary model certification failed: {error}") from error


def compile_preparation_prefix_model(compiled: CompiledPreparationExperiment, *,
                                      weight_scale=1000) -> PrefixDemModel:
    """Compile known-initial-zero Z rows, with evaluator-only response maps.

    The selected detectors consist solely of physical-prefix SE comparisons.
    In particular no terminal ideal probe/readout detector closes this model.
    """
    try:
        rows = [r for r in compiled.detectors if r.sector == "z"]
        labels = [r for r in compiled.observables if r.metric in {"tau_z", "logical_z"}]
        tau = [r for r in labels if r.metric == "tau_z"]
        logical = [r for r in labels if r.metric == "logical_z"]
        count = len(tau)
        if (not count or len(logical) != 1 or logical[0].check_index is not None
                or [r.check_index for r in tau] != list(range(count))
                or len(rows) != count * compiled.settings.rounds
                or any(r.role != DetectorRole.ONLINE for r in rows)
                or [(r.round_index, r.check_index) for r in rows] !=
                   [(r, j) for r in range(1, compiled.settings.rounds + 1) for j in range(count)]):
            raise ValueError("Z-prefix must retain every known-zero initial anchor and ordered SE row")
        ledger = {r.record_id: r for r in compiled.ledger}
        for row in rows:
            records = [ledger[i] for i in row.record_ids]
            expected_rounds = [1] if row.round_index == 1 else [row.round_index - 1, row.round_index]
            if ([r.round_index for r in records] != expected_rounds
                    or any(r.source != "se" or r.sector != "z" or r.check_index != row.check_index for r in records)):
                raise ValueError("Z decoder detector contains a non-prefix record or lacks its initial anchor")
        return prefix_dem_to_model(
            compiled.model_dem, detector_ids=[r.detector_id for r in rows],
            observable_ids=[r.observable_id for r in labels],
            feature_ids=[r.metric if r.check_index is None else f"{r.metric}:{r.check_index}" for r in labels],
            weight_scale=weight_scale,
            model_provenance=dict(
                source="native_fixed_R_known_zero_Z_prefix", decoding_p=compiled.decoding_probability,
                rounds=compiled.settings.rounds, model_hashes=dict(compiled.model_hashes),
                source_hashes=dict(compiled.source_hashes), hex_revision=compiled.hex_revision,
                detector_map=[asdict(r) for r in rows], evaluation_map=[asdict(r) for r in labels],
            ),
        )
    except (ValueError, KeyError) as error:
        raise PreparationCapabilityError(f"preparation Z-prefix model compilation failed: {error}") from error
