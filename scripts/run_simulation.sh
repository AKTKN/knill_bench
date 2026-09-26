#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec "${KNILL_PYTHON:-$ROOT/.venv/bin/python}" "$ROOT/scripts/run_simulation.py" "$@"
