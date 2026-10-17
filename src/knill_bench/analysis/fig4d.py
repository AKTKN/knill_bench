"""Saved-data Fig.4(d) LER and 95% Agresti-Coull intervals; no simulation."""

import json
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pyarrow.parquet as pq

from knill_bench.data.storage_v2 import validate_point_files
from knill_bench.experiments.config_v2 import load_saved_config


def agresti_coull(errors, shots):
    """Two-sided 95% adjusted-Wald interval, clipped to [0, 1]."""
    if type(shots) is not int or type(errors) is not int or not 0 <= errors <= shots or shots < 1:
        raise ValueError("require integer 0 <= errors <= shots and shots > 0")
    z = NormalDist().inv_cdf(.975)
    adjusted_n = shots + z*z
    adjusted_p = (errors + z*z/2) / adjusted_n
    radius = z * math.sqrt(adjusted_p * (1 - adjusted_p) / adjusted_n)
    return max(0., adjusted_p - radius), min(1., adjusted_p + radius)


def summarize_saved(run_path):
    """Stream saved labels and verify counts/IDs against compact metadata.

    Every trajectory is retained (acceptance = 1); conditional LER is the
    observed per-shot error fraction. No per-round rate transform is applied.
    Incomplete runs, mismatched counts and invalid IDs raise before plotting.
    """
    path = Path(run_path)
    document = load_saved_config(path)
    config = document.config
    metadata = json.loads((path / "metadata.json").read_text())
    if (config.kind != "fig4d_reproduction" or config.T_tel != 8
            or config.theta is not None or config.create_codecapacity_dem
            or metadata.get("kind") != config.kind
            or metadata.get("schema_version") != 2 or metadata.get("status") != "complete"
            or metadata.get("config_hash") != config.config_hash
            or metadata.get("input_sha256") != document.input_hash
            or metadata.get("config") != config.as_dict()):
        raise ValueError("require a complete, unchanged Fig.4(d) run")
    points = list(config.points())
    if set(metadata["points"]) != {p.case_id for p in points}:
        raise ValueError("saved point identities changed")
    summaries = []
    for point in points:
        info = metadata["points"][point.case_id]
        if (info["status"] != "complete" or info["files"] != [point.filename("logical_error")]
                or any(info.get(k) != v for k, v in point.sampling_identity.items())):
            raise ValueError("require complete aligned Fig.4(d) points")
        if not (path / point.filename("logical_error")).is_file():
            raise ValueError("missing logical_error file for a complete point")
        validate_point_files(path, point, config.shots)
        shots, errors = 0, 0
        for batch in pq.ParquetFile(path / point.filename("logical_error")).iter_batches(batch_size=65536):
            ids, labels = batch.column(0), batch.column(1)
            if ids.null_count or labels.null_count:
                raise ValueError("null IDs or logical_error labels")
            if not np.array_equal(ids.to_numpy(), np.arange(shots, shots + len(batch), dtype=np.uint64)):
                raise ValueError("shot IDs must be contiguous from zero")
            shots += len(batch)
            errors += int(np.count_nonzero(labels.to_numpy(zero_copy_only=False)))
        if shots != info["shots"] or errors != info["logical_errors"]:
            raise ValueError("saved label counts disagree with metadata")
        lower, upper = agresti_coull(errors, shots)
        summaries.append(dict(d=point.d, p=point.p, shots=shots, logical_errors=errors,
                              conditional_ler=errors/shots, lower=lower, upper=upper))
    return summaries


def plot_saved(run_path, output):
    """Write one optional figure from saved Parquet, without importing runners."""
    summaries = summarize_saved(run_path)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    figure = Figure(figsize=(6.4, 4.4))
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    for distance in sorted({s["d"] for s in summaries}):
        rows = sorted((s for s in summaries if s["d"] == distance), key=lambda s: s["p"])
        y = np.array([r["conditional_ler"] for r in rows])
        errors = np.array([[r["conditional_ler"] - r["lower"] for r in rows],
                           [r["upper"] - r["conditional_ler"] for r in rows]])
        axis.errorbar([r["p"] for r in rows], y, yerr=errors, marker="o", capsize=3, label=f"d={distance}")
    axis.set(xlabel="Physical error probability p", ylabel="logical error rate",
             title="Eight-cycle full Knill memory · 95% Agresti–Coull")
    axis.legend()
    axis.grid(alpha=.25)
    figure.tight_layout()
    destination = Path(output)
    figure.savefig(destination)
    return destination
