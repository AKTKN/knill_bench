"""Independent v2 CLI; the original knill-bench commands remain schema-v1."""

import argparse
import json

from .config_v2 import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(prog="knill-bench-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-config", "prepare", "run"):
        sub.add_parser(name).add_argument("config")
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
        else:
            from .dispatcher import dispatch
            print(dispatch(args.config))
    except (ValueError, RuntimeError, NotImplementedError) as error:
        parser.exit(2, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
