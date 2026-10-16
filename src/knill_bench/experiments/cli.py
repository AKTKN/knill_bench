"""Independent v2 CLI; the original knill-bench commands remain schema-v1."""

import argparse
import json

from .config_v2 import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(prog="knill-bench-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-config", "prepare", "run"):
        sub.add_parser(name).add_argument("config")
    sub.add_parser("resume").add_argument("run")
    plot = sub.add_parser("plot-fig4d")
    plot.add_argument("run")
    plot.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-config":
            config = load_config(args.config).config
            print(json.dumps(dict(config=config.as_dict(), config_hash=config.config_hash,
                                  points=[dict(p.sampling_identity, case_id=p.case_id) for p in config.points()]),
                             sort_keys=True, indent=2, allow_nan=False))
        elif args.command == "prepare":
            from .run_v2 import RunStore
            with RunStore.create(load_config(args.config)) as run:
                print(run.path)
        elif args.command == "run":
            from .dispatcher import dispatch
            print(dispatch(args.config))
        elif args.command == "resume":
            from .dispatcher import resume
            print(resume(args.run))
        else:
            from knill_bench.analysis.fig4d import plot_saved
            print(plot_saved(args.run, args.output))
    except (ValueError, RuntimeError, NotImplementedError) as error:
        parser.exit(2, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
