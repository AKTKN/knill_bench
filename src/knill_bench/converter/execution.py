"""Reserved parent-owned execution path, exercised with synthetic workers only."""

from knill_bench.experiments.config_v2 import CONVERTER_KINDS


def execute_converter_points(store, *, worker, artifact_builder):
    """Reuse bounded spawn tasks, numeric ChunkResult and paired publication.

    worker must be a module-level spawn-pickleable callable taking ChunkTask;
    return only bool labels, timing/caps and compact JSON execution metadata.
    artifact_builder runs exclusively in the parent, returning PointArtifacts.
    Neither circuits nor decoder/frame/native objects cross the worker boundary.
    Integer batch_size uses fixed chunk seeds; auto retains timing-dependent
    partitions. This helper provides infrastructure, not a scientific runner.
    """
    if store.document.config.kind not in CONVERTER_KINDS:
        raise ValueError("converter execution requires a converter experiment")
    if not callable(worker) or not callable(artifact_builder):
        raise ValueError("converter execution requires explicit worker and parent artifact builder")
    from knill_bench.experiments.adaptive_execution import execute_adaptive
    return execute_adaptive(store, worker=worker, prepare_point=artifact_builder)
