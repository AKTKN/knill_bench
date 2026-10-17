#!/usr/bin/env python3
"""Opt-in wall-time profile of one real v2 factory point, without editing Hex."""

import argparse
from collections import Counter
from contextlib import ExitStack
import cProfile
import ctypes
from functools import wraps
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import platform
import pstats
import resource
import signal
import sys
import tempfile
import time
from unittest.mock import patch


class Timings:
    """Inclusive and exclusive wall/CPU seconds for nested synchronous calls."""

    def __init__(self):
        self.rows = {}
        self.stack = []

    def wrap(self, function, label):
        @wraps(function)
        def measured(*args, **kwargs):
            name = label(*args, **kwargs) if callable(label) else label
            frame = dict(wall=time.perf_counter(), cpu=time.process_time(), child_wall=0., child_cpu=0.)
            self.stack.append(frame)
            try:
                return function(*args, **kwargs)
            finally:
                wall, cpu = time.perf_counter()-frame["wall"], time.process_time()-frame["cpu"]
                self.stack.pop()
                row = self.rows.setdefault(name, dict(calls=0, wall_s=0., self_wall_s=0., cpu_s=0., self_cpu_s=0.))
                row["calls"] += 1
                row["wall_s"] += wall
                row["cpu_s"] += cpu
                row["self_wall_s"] += wall-frame["child_wall"]
                row["self_cpu_s"] += cpu-frame["child_cpu"]
                if self.stack:
                    self.stack[-1]["child_wall"] += wall
                    self.stack[-1]["child_cpu"] += cpu
        return measured

    def instrument(self, scope, owner, name, label):
        scope.enter_context(patch.object(owner, name, self.wrap(getattr(owner, name), label)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--p", type=float, required=True)
    parser.add_argument("--prior", choices=("configured", "hamming", "projected", "local", "legacy-projected"),
                        default="configured", help="projected/local mean current True; legacy-projected replays pinned H5")
    parser.add_argument("--repeat", type=int, default=1, help="Fresh seeded point attempts in one worker; expose warm DEM cache")
    parser.add_argument("--shots", type=int, default=7, help="Bounded diagnostic shots, independent of config budget")
    parser.add_argument("--batch-size", type=int, default=7)
    parser.add_argument("--max-wall-seconds", type=float, default=180.)
    parser.add_argument("--cprofile", action="store_true", help="Also save function-level wall-time stats (adds overhead)")
    parser.add_argument("--trace-validation", action="store_true", help="Measure each Python line of bundle.validate")
    parser.add_argument("--output", required=True, help="New .json output; refuses to overwrite")
    args = parser.parse_args(argv)
    if (args.shots < 1 or args.batch_size < 1 or args.repeat < 1
            or not math.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0):
        parser.error("shots, batch size and max wall seconds must be positive")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error(f"output already exists: {output}")

    started = time.perf_counter()
    from knill_bench.experiments.config_v2 import load_config
    from knill_bench.experiments import logical_zero_factory as runner
    from knill_bench.adapters import hex_factory as local
    from knill_bench.experiments.seeds import point_seed
    from knill_bench.data import storage_v2 as storage
    import numpy as np
    import psutil
    import pymatching
    import stim
    from hex_qec.protocols import RotatedSurfaceCodeAdapter, FactoryCircuitBuilder
    from hex_qec.protocols.logical_zero_factory import FactoryCircuitBundle
    from hex_qec.simulation.factory import FactoryBatchDecoder, CompiledFactory
    from hex_qec.modularisation.factory import PreparationFramePlan
    from knill_bench.adapters.factory_frames import FactoryPreparationPlan
    from hex_qec.decoders.surface_gap import SurfaceMWPMHomologyGap
    from hex_qec.decoders.codecapacity_dem import EffectivePriorBuilder, ProjectedDEMBuilder
    projection = importlib.import_module("hex_qec.decoders.codecapacity_dem")
    simulation = importlib.import_module("hex_qec.simulation.factory")
    imports_s = time.perf_counter()-started

    begin = time.perf_counter()
    document = load_config(args.config)
    config_load_s = time.perf_counter()-begin
    if document.config.kind != "logical_zero_factory":
        parser.error("requires a logical_zero_factory config")
    point = next((p for p in document.config.points() if p.d == args.distance and p.p == args.p), None)
    if point is None:
        parser.error("distance/p must select a point present in the config")
    projected = (document.config.create_codecapacity_dem if args.prior == "configured" else args.prior != "hamming")
    if args.prior == "legacy-projected" and document.config.skip_circuit_validation:
        parser.error("legacy-projected diagnostics require full circuit validation")
    from knill_bench.experiments.provenance import collect_environment
    begin = time.perf_counter()
    environment = collect_environment()
    provenance_s = time.perf_counter()-begin
    blas_pools = []
    for library in sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                           if 'openblas' in line and '/' in line}):
        handle = ctypes.CDLL(library)
        for name in ('scipy_openblas_get_num_threads64_', 'scipy_openblas_get_num_threads',
                     'openblas_get_num_threads64_', 'openblas_get_num_threads'):
            function = getattr(handle, name, None)
            if function is not None:
                function.restype = ctypes.c_int
                blas_pools.append(dict(library=library, threads=function()))
                break
    timer, stages, merge_groups, attempts = Timings(), [], [], []
    local.clear_local_prior_cache()
    report = dict(format_version=1, config_path=str(document.source_path), config_hash=document.config.config_hash,
                  input_sha256=document.input_hash, point=point.sampling_identity,
                  seed=point_seed(document.config.master_seed, point), create_codecapacity_dem=projected,
                  skip_circuit_validation=document.config.skip_circuit_validation,
                  shots=args.shots, batch_size=args.batch_size, imports_s=imports_s,
                  config_load_s=config_load_s, provenance_s=provenance_s,
                  source={name:environment[name] for name in ('bench','hex')}, blas_pools=blas_pools,
                  configured_shots=document.config.shots, configured_workers=document.config.workers,
                  measurement_mode="one_isolated_worker_point_not_a_parallel_sweep",
                  python=sys.version, platform=platform.platform(), pid=os.getpid(),
                  versions=dict(numpy=np.__version__, stim=stim.__version__, pymatching=pymatching.__version__),
                  thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                  cpu_logical=psutil.cpu_count(), cpu_physical=psutil.cpu_count(logical=False),
                  available_memory_bytes=psutil.virtual_memory().available,
                  cprofile=args.cprofile, trace_validation=args.trace_validation, max_wall_seconds=args.max_wall_seconds)
    report.update(prior_requested=args.prior, repeat=args.repeat)
    original_inspect = EffectivePriorBuilder.inspect
    original_merge = projection.merge_independent_events

    def merge(events):
        events = list(events)
        sizes = sorted(Counter(event.signature for event in events).values(), reverse=True)
        merge_groups.append(dict(inputs=len(events), groups=len(sizes), largest_groups=sizes[:10],
                                 repeated_id_validation_terms=sum(n*(n+1)//2 for n in sizes)))
        return original_merge(events)

    def inspect(service):
        fresh = service._result is None
        if fresh:
            stage = dict(stage=service.context.stage_id, mechanisms=len(service.context.mechanisms),
                         prefix_instructions=len(service.context.circuit),
                         prefix_measurements=service.context.circuit.num_measurements)
            stages.append(stage)
            print(f"[profile] start projected stage={stage['stage']} mechanisms={stage['mechanisms']}", file=sys.stderr, flush=True)
        result = original_inspect(service)
        if fresh:
            stage.update(events=len(result.model.events), active_events=len(result.model.active_events))
            print(f"[profile] finished projected stage={stage['stage']}", file=sys.stderr, flush=True)
        return result

    profile = cProfile.Profile(timer=time.perf_counter) if args.cprofile else None
    validation_code = FactoryCircuitBundle.validate.__code__
    validation_lines, trace_frames = {}, {}
    previous_trace = sys.gettrace()

    def trace_validation(frame, event, arg):
        if frame.f_code is not validation_code:
            return None
        now = time.perf_counter()
        key = id(frame)
        if key in trace_frames:
            line, begin = trace_frames[key]
            row = validation_lines.setdefault(line, dict(visits=0, wall_s=0.))
            row["visits"] += 1
            row["wall_s"] += now-begin
        if event == "return":
            trace_frames.pop(key, None)
        else:
            trace_frames[key] = frame.f_lineno, now
        return trace_validation

    def timeout(signum, frame):
        raise TimeoutError(f"diagnostic point exceeded {args.max_wall_seconds} wall seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout)
    measured_start = time.perf_counter()
    try:
        with ExitStack() as scope, tempfile.TemporaryDirectory(prefix="knill-factory-profile-") as directory:
            if args.prior == "legacy-projected":
                # Diagnostic replay only: restore the original pinned H5 setup
                # while retaining identical physical point/seed/writer handling.
                from hex_qec.modularisation import PreparationPlan

                def legacy_compile(case, *, seed, create_codecapacity_dem, skip_circuit_validation=False):
                    bundle = FactoryCircuitBuilder(RotatedSurfaceCodeAdapter(case.d),
                        PreparationPlan(case.r_0, case.r_plus), case.p, T_tel=case.T_tel).build()
                    return bundle, CompiledFactory.from_bundle(bundle, seed=seed,
                                                               create_codecapacity_dem=create_codecapacity_dem)

                scope.enter_context(patch.object(runner, "compile_point", legacy_compile))
            scope.enter_context(patch.object(EffectivePriorBuilder, "inspect", inspect))
            scope.enter_context(patch.object(projection, "merge_independent_events", merge))
            targets = [
                (runner, "_run_point", "point.total"),
                (RotatedSurfaceCodeAdapter, "__init__", "setup.geometry"),
                (FactoryCircuitBuilder, "build", "setup.circuit_and_preparation"),
                (local, "_build_without_full_validation", "setup.circuit_and_preparation"),
                (FactoryCircuitBundle, "validate", "setup.bundle_validation"),
                (PreparationFramePlan, "__init__", "setup.preparation_frame_maps"),
                (FactoryPreparationPlan, "__init__", "setup.packed_frame_maps"),
                (FactoryBatchDecoder, "__init__", "setup.factory_decoder"),
                (ProjectedDEMBuilder, "__init__", "setup.projected_source"),
                (ProjectedDEMBuilder, "context", "setup.projected_context"),
                (EffectivePriorBuilder, "inspect", lambda service: f"prior.stage_{service.context.stage_id}.inspect"),
                (projection, "_enumerate_prefix_faults", "prior.enumerate_faults"),
                (projection, "_propagate_faults", "prior.propagate_faults"),
                (projection, "_signatures", "prior.signatures"),
                (projection, "merge_independent_events", "prior.merge_events"),
                (local, "_build_local_prior", "prior.local_build"),
                (local, "_stim_dem", "prior.local_stim_dem"),
                (local, "_analysis_circuit", "prior.local_analysis_circuit"),
                (local._LocalFactoryDecoder, "__init__", "setup.local_factory_decoder"),
                (PreparationFramePlan, "resolve", "decode.preparation_frames"),
                (FactoryPreparationPlan, "resolve", "decode.preparation_frames"),
                (SurfaceMWPMHomologyGap, "__init__", "setup.gap_graph"),
                (SurfaceMWPMHomologyGap, "decode_batch", "decode.homology_gap"),
                (pymatching.Matching, "decode_batch", "decode.native_pymatching"),
                (simulation, "_compile_sampler", "setup.stim_sampler"),
                (CompiledFactory, "sample_measurements", "sampling.physical_shots"),
                (CompiledFactory, "decode", "decode.physical_shots"),
                (storage.PointWriter, "__init__", "io.writer_open"),
                (storage.PointWriter, "write_batch", "io.write_batch"),
                (storage.PointWriter, "commit", "io.commit_and_validate"),
            ]
            for owner, name, label in targets:
                timer.instrument(scope, owner, name, label)
            signal.setitimer(signal.ITIMER_REAL, args.max_wall_seconds)
            if args.trace_validation:
                sys.settrace(trace_validation)
            if profile:
                profile.enable()
            for index in range(args.repeat):
                destination = Path(directory) / str(index)
                destination.mkdir()
                before = json.loads(json.dumps(timer.rows))
                started_attempt = time.perf_counter()
                result, execution = runner._run_point(destination, point, args.shots, args.batch_size,
                                                      report["seed"], create_codecapacity_dem=projected,
                                                      skip_circuit_validation=document.config.skip_circuit_validation)
                delta = {label:{key:value-before.get(label,{}).get(key,0) for key,value in row.items()}
                         for label,row in timer.rows.items()}
                attempts.append(dict(index=index, wall_s=time.perf_counter()-started_attempt,
                                     timings=delta, cache=local.local_prior_cache_info(),
                                     logical_errors=result.logical_errors,
                                     output_sha256={name:hashlib.sha256((destination/name).read_bytes()).hexdigest()
                                                    for name in result.files}))
            report.update(status="complete", logical_errors=result.logical_errors,
                          measurement_records=execution["measurement_records"], simulator_qubits=execution["simulator_qubits"],
                          circuit_sha256=execution["circuit_sha256"],
                          prior_policy=execution["prior_policy"], decoder_policy=execution["decoder_policy"],
                          projected_prior_sha256=execution["projected_prior_sha256"],
                          output_sha256=attempts[-1]["output_sha256"])
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="timeout" if isinstance(error, TimeoutError) else "failed",
                      error=f"{type(error).__name__}: {error}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if args.trace_validation:
            sys.settrace(previous_trace)
        if profile:
            profile.disable()
        report.update(measured_wall_s=time.perf_counter()-measured_start, timings=timer.rows, stages=stages,
                      merge_groups=merge_groups,
                      attempts=attempts, local_cache=local.local_prior_cache_info(),
                      validation_lines=validation_lines,
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      native_threads_end=psutil.Process().num_threads())
        output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
        if profile:
            profile.dump_stats(str(output.with_suffix(".pstats")))
            with output.with_suffix(".pstats.txt").open("w") as stream:
                pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(45)
    print(output)
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
