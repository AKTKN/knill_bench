"""Bounded whole-point execution shared by the independent v2 experiments."""

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import multiprocessing

from .seeds import point_seed


def execute_points(store, worker, **worker_options):
    """Run one compiled model per point; only the parent publishes metadata.

    A worker returns (PointResult, compact JSON execution metadata). Native
    objects and open point writers never leave that worker. Submission is
    bounded to workers tasks; each worker advances its sampler across chunks.
    """
    config = store.document.config
    completed_ids = {key for key, info in store.metadata["points"].items() if info["status"] == "complete"}
    pending = iter(p for p in config.points() if p.case_id not in completed_ids)

    def arguments(point):
        store.start_point(point)
        return store.path, point, config.shots, config.batch_size, point_seed(config.master_seed, point)

    if config.workers == 1:
        for point in pending:
            result, execution = worker(*arguments(point), **worker_options)
            store.record_complete(result, execution=execution)
    else:
        with ProcessPoolExecutor(max_workers=config.workers,
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            active = set()

            def submit_next():
                point = next(pending, None)
                if point is not None:
                    active.add(pool.submit(worker, *arguments(point), **worker_options))

            try:
                for _ in range(config.workers):
                    submit_next()
                while active:
                    completed, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in completed:
                        active.remove(future)
                        result, execution = future.result()
                        store.record_complete(result, execution=execution)
                        submit_next()
            except BaseException:
                for future in active:
                    future.cancel()
                raise
    store.finish()
