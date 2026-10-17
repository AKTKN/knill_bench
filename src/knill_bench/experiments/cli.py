"""Independent v2 CLI; the original knill-bench commands remain schema-v1."""

import argparse
from dataclasses import replace
import json

from .config_v2 import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(prog="knill-bench-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate-config", "Validate a simulation config without sampling."),
        ("prepare", "Create a new run directory without sampling."),
        ("run", "Create a new run directory and simulate the supplied config."),
    ):
        command = sub.add_parser(name, help=help_text, description=help_text)
        command.add_argument("config")
        command.add_argument("--workers", type=int, help="Override process count; save the effective YAML in the run.")
    sub.add_parser("resume", help="Continue an existing run directory.").add_argument("run")
    plot = sub.add_parser("plot-fig4d")
    plot.add_argument("run")
    plot.add_argument("--output", required=True)
    analysis_text = ("Analyze saved data in RUN using analysis settings. This does not simulate; "
                     "after editing a simulation config, use 'run CONFIG' to create a new experiment.")
    analysis = sub.add_parser("analyze-factory", help="Analyze a saved factory run without simulation.",
                              description=analysis_text)
    analysis.add_argument("run")
    analysis.add_argument("--settings")
    cuts = analysis.add_mutually_exclusive_group()
    cuts.add_argument("--theta", action="append", type=float, help="Repeat for a list; use --theta=-inf for no cut")
    cuts.add_argument("--theta-grid", nargs=3, metavar=("START", "STOP", "COUNT"))
    analysis.add_argument("--iid-restarts", action="store_true", default=None)
    analysis.add_argument("--output", help="Optional .json, .csv or .md; default prints JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-config":
            config = load_config(args.config, workers=args.workers).config
            print(json.dumps(dict(config=config.as_dict(), config_hash=config.config_hash,
                                  points=[dict(p.sampling_identity, case_id=p.case_id) for p in config.points()]),
                             sort_keys=True, indent=2, allow_nan=False))
        elif args.command == "prepare":
            from .run_v2 import RunStore
            with RunStore.create(load_config(args.config, workers=args.workers)) as run:
                print(run.path)
        elif args.command == "run":
            from .dispatcher import dispatch
            print(dispatch(args.config, workers=args.workers))
        elif args.command == "resume":
            from .dispatcher import resume
            print(resume(args.run))
        elif args.command == "plot-fig4d":
            from knill_bench.analysis.fig4d import plot_saved
            print(plot_saved(args.run, args.output))
        else:
            from knill_bench.analysis.factory import (
                AnalysisSettings, analyze_saved, load_settings, threshold_grid, write_report,
            )
            settings = load_settings(args.settings) if args.settings else AnalysisSettings()
            if args.theta is not None:
                settings = replace(settings, thresholds=tuple(args.theta))
            elif args.theta_grid is not None:
                start, stop, count = args.theta_grid
                settings = replace(settings, thresholds=threshold_grid(float(start), float(stop), int(count)))
            if args.iid_restarts:
                settings = replace(settings, iid_restarts=True)
            report = analyze_saved(args.run, settings)
            if args.output:
                print(write_report(report, args.output))
            else:
                print(json.dumps(report, indent=2, allow_nan=False))
    except (ValueError, RuntimeError, NotImplementedError, OSError) as error:
        parser.exit(2, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
