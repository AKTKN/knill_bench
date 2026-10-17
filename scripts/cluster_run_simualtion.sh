#!/usr/bin/env bash
#PBS -N knill_factory
#PBS -l select=1:ncpus=96
#PBS -l walltime=24:00:00
#PBS -o logs/knill_simulation.o
#PBS -e logs/knill_simulation.e

# Submit from the cloned repository root after mkdir -p logs. Edit PBS resources for your cluster.
# Example: qsub -v CONFIG_FILE=configs/cluster_factory.yaml,KNILL_CONDA_ENV=knill_system scripts/cluster_run_simualtion.sh
# Setup is done on the login node with bash scripts/bootstrap.sh, not in jobs.
set -euo pipefail
ulimit -s unlimited
cd -- "${PBS_O_WORKDIR:?Submit this script with qsub from the repository root}"

if [[ -n "${CONDA_BASE:-}" ]]; then
    knill_conda_base="$CONDA_BASE"
elif command -v conda >/dev/null 2>&1; then
    knill_conda_base="$(conda info --base)"
else
    printf '%s\n' 'Load the site Anaconda module or pass CONDA_BASE with qsub -v.' >&2
    exit 1
fi
source "$knill_conda_base/etc/profile.d/conda.sh"
conda activate "${KNILL_CONDA_ENV:-knill_system}"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# Worker count comes from the YAML, or the saved YAML when resuming.
if [[ -n "${RESUME_RUN:-}" ]]; then
    python -m knill_bench.experiments.cli resume "$RESUME_RUN"
else
    knill_config_file="${CONFIG_FILE:-configs/templates/logical_zero_factory.yaml}"
    python -m knill_bench.experiments.cli run "$knill_config_file"
fi
