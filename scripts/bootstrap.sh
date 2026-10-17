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
checkout Hex https://github.com/AKTKN/Hex.git 86c9495094801012b9912bd41935ae48b08d8f92
checkout lomatching "${KNILL_LOMATCHING_URL:-https://github.com/AKTKN/lomatching.git}" b55a7a65969a106a547622287b620f0da2cb5e39
checkout surface-sim "${KNILL_SURFACE_SIM_URL:-https://github.com/AKTKN/surface-sim.git}" 493f800a3b4e9f80a6a569eb92d3c962dd6b09ad
# Conda owns Python/pip; all scientific and notebook packages use pip locks.
command -v conda >/dev/null || { echo "Install Anaconda/Miniconda first." >&2; exit 1; }
if conda run -n knill_system python -c 'import sys' >/dev/null 2>&1; then
    conda env update -n knill_system -f environments.yaml
else
    conda env create -f environments.yaml
fi
conda run --no-capture-output -n knill_system python -m pip install --no-deps --no-build-isolation \
    -e external/Hex -e external/lomatching -e external/surface-sim -e '.[research,dev]'
conda run --no-capture-output -n knill_system python -m pip check
conda run --no-capture-output -n knill_system python -m knill_bench.cli validate-config configs/smoke.yaml >/dev/null
