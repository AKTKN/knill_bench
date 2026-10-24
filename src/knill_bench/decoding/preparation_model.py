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
