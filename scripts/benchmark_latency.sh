#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec "${KNILL_PYTHON:-$ROOT/.venv/bin/python}" -m knill_bench.cli benchmark-latency "$@"
