#!/usr/bin/env python3
from knill_bench.cli import main
import sys

if __name__ == '__main__':
    raise SystemExit(main(['run', *sys.argv[1:]]))
