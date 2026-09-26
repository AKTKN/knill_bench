#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$ROOT"
mkdir -p external
# Existing checkouts/worktrees are never reset. Exact base revisions are checked.
checkout() {
    local name=$1 url=$2 revision=$3
    if [[ ! -e "external/$name/.git" ]]; then
        git clone -- "$url" "external/$name"
        git -C "external/$name" checkout -b knill-bench-integration "$revision"
    fi
    local actual
    actual=$(git -C "external/$name" rev-parse HEAD)
    if [[ "$actual" != "$revision" ]]; then
        echo "external/$name is at $actual, expected $revision; preserving it. Review docs/dependencies.md." >&2
        exit 1
    fi
}
checkout Hex https://github.com/AKTKN/Hex.git 5de58f2f80791054411ad3c0885a4fe3671ed56a
checkout lomatching "${KNILL_LOMATCHING_URL:-https://github.com/AKTKN/lomatching.git}" b55a7a65969a106a547622287b620f0da2cb5e39
checkout surface-sim "${KNILL_SURFACE_SIM_URL:-https://github.com/AKTKN/surface-sim.git}" 493f800a3b4e9f80a6a569eb92d3c962dd6b09ad
if command -v uv >/dev/null 2>&1; then
    [[ -d .venv ]] || uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python -r requirements.lock -e external/Hex -e external/lomatching -e external/surface-sim
    uv pip install --python .venv/bin/python --no-deps -e .
else
    [[ -d .venv ]] || python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.lock -e external/Hex -e external/lomatching -e external/surface-sim
    .venv/bin/python -m pip install --no-deps -e .
fi
.venv/bin/python -m knill_bench.cli validate-config configs/smoke.yaml >/dev/null
