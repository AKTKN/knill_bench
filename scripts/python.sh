#!/usr/bin/env bash
# One launcher for local development and noninteractive cluster jobs.
set -euo pipefail
if [[ -n "${KNILL_PYTHON:-}" ]]; then
    exec "$KNILL_PYTHON" "$@"
elif [[ "${CONDA_DEFAULT_ENV:-}" == "${KNILL_CONDA_ENV:-knill_system}" ]]; then
    exec python "$@"
else
    exec conda run --no-capture-output -n "${KNILL_CONDA_ENV:-knill_system}" python "$@"
fi
