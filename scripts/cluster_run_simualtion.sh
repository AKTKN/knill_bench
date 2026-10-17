#!/usr/bin/env bash
#PBS -N knill_factory
#PBS -l select=1:ncpus=96:mpiprocs=96
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

# This is a single-node process pool. Use the CPUs allocated by PBS.
knill_allocated_cpus="${PBS_NCPUS:-}"
if [[ -z "$knill_allocated_cpus" && -n "${PBS_NODEFILE:-}" ]]; then
    knill_allocated_cpus="$(wc -l < "$PBS_NODEFILE")"
    knill_allocated_cpus="${knill_allocated_cpus//[[:space:]]/}"
fi
knill_allocated_cpus="${knill_allocated_cpus:-1}"
knill_workers="${WORKERS:-$knill_allocated_cpus}"
if [[ ! "$knill_workers" =~ ^[1-9][0-9]*$ || ! "$knill_allocated_cpus" =~ ^[1-9][0-9]*$ ]]; then
    printf '%s\n' 'WORKERS and the PBS CPU count must be positive integers.' >&2
    exit 2
fi
if (( knill_workers > knill_allocated_cpus )); then
    printf '%s\n' 'WORKERS exceeds the PBS CPU allocation.' >&2
    exit 2
fi
if [[ -n "${PBS_NODEFILE:-}" ]]; then
    knill_node_count="$(sort -u -- "$PBS_NODEFILE" | wc -l)"
    if (( knill_node_count > 1 )); then
        printf '%s\n' 'Request select=1: the runner supports one node per job.' >&2
        exit 2
    fi
fi

# RESUME_RUN continues the saved configuration, including its saved workers.
if [[ -n "${RESUME_RUN:-}" ]]; then
    knill_saved_workers="$(python -c 'import sys; from knill_bench.experiments.config_v2 import load_saved_config; print(load_saved_config(sys.argv[1]).config.workers)' "$RESUME_RUN")"
    if (( knill_saved_workers > knill_allocated_cpus )); then
        printf '%s\n' 'The saved run requires more workers than this PBS allocation.' >&2
        exit 2
    fi
    python -m knill_bench.experiments.cli resume "$RESUME_RUN"
else
    knill_config_file="${CONFIG_FILE:-configs/templates/logical_zero_factory.yaml}"
    python -m knill_bench.experiments.cli validate-config "$knill_config_file" --workers "$knill_workers"
    python -m knill_bench.experiments.cli run "$knill_config_file" --workers "$knill_workers"
fi
