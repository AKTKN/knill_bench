#!/usr/bin/env bash
set -euo pipefail
if (( $# > 1 )); then
    echo "Usage: $0 [config.yaml]" >&2
    exit 2
fi
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$ROOT/scripts/python.sh" -m knill_bench.experiments.cli run "${1:-$ROOT/configs/fig4d.yaml}"
