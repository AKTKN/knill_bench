"""Pure streaming acceptance/terminal-oracle/cost analysis of saved v2 pairs."""

from dataclasses import dataclass, field
import csv
import json
import math
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import yaml

from knill_bench.data.storage_v2 import validate_point_files
from knill_bench.experiments.config_v2 import _UniqueSafeLoader, load_config
from knill_bench.experiments.seeds import point_seed
from .factory_cost import FactoryCostModel, first_rejected_stage, summarize_cost
from .fig4d import agresti_coull


def _cut(value):
    if type(value) not in (int, float) or math.isnan(value):
        raise ValueError("theta must be a number, with +/-infinity allowed and NaN forbidden")
    return float(value)


def threshold_grid(start, stop, count):
    if (type(count) is not int or not 1 <= count <= 10000
            or not math.isfinite(_cut(start)) or not math.isfinite(_cut(stop)) or start > stop):
        raise ValueError("threshold grid requires finite start <= stop and integer count in [1,10000]")
    return tuple(float(v) for v in np.linspace(start, stop, count))


@dataclass(frozen=True)
class AnalysisSettings:
    thresholds: tuple = (-math.inf, 0., 1., 2., 3., math.inf)
    cost: FactoryCostModel = field(default_factory=FactoryCostModel)
    iid_restarts: bool = False
    batch_size: int = 65536

    def __post_init__(self):
        cuts = tuple(_cut(t) for t in self.thresholds)
        if not cuts or len(cuts) > 10000 or len(set(cuts)) != len(cuts):
            raise ValueError("provide 1..10000 unique thresholds")
        if type(self.iid_restarts) is not bool or not isinstance(self.cost, FactoryCostModel):
            raise ValueError("require boolean iid_restarts and a FactoryCostModel")
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise ValueError("analysis batch_size must be positive")
        object.__setattr__(self, "thresholds", cuts)


def load_settings(path):
    """Strict separate analysis YAML, never a simulation sweep/config mutation."""
    try:
        raw = yaml.load(Path(path).read_text(), Loader=_UniqueSafeLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"invalid analysis YAML: {error}") from error
    allowed = {"analysis_version", "thresholds", "threshold_grid", "cost", "iid_restarts", "batch_size"}
    if not isinstance(raw, dict) or raw.keys()-allowed or type(raw.get("analysis_version")) is not int or raw["analysis_version"] != 1:
        raise ValueError("analysis YAML requires analysis_version: 1 and known fields")
    if "thresholds" in raw and "threshold_grid" in raw:
        raise ValueError("choose thresholds or threshold_grid")
    options = {k: raw[k] for k in ("thresholds", "iid_restarts", "batch_size") if k in raw}
    if "thresholds" in raw and not isinstance(raw["thresholds"], list):
        raise ValueError("thresholds must be a list")
    if "threshold_grid" in raw:
        grid = raw["threshold_grid"]
        if not isinstance(grid, dict) or set(grid) != {"start", "stop", "count"}:
            raise ValueError("threshold_grid requires start, stop, count")
        options["thresholds"] = threshold_grid(**grid)
    if "cost" in raw:
        if not isinstance(raw["cost"], dict) or raw["cost"].keys()-FactoryCostModel.__dataclass_fields__.keys():
            raise ValueError("unknown cost model fields")
        options["cost"] = FactoryCostModel(**raw["cost"])
    return AnalysisSettings(**options)


def _paired_batches(error_file, gap_file, batch_size):
    # Row-group boundaries need not coincide; consume aligned bounded slices.
    streams = [iter(pq.ParquetFile(p).iter_batches(batch_size=batch_size)) for p in (error_file, gap_file)]
    buffers = [None, None]
    while True:
        for j in range(2):
            if buffers[j] is None or len(buffers[j]) == 0:
                buffers[j] = next(streams[j], None)
        if buffers[0] is None or buffers[1] is None:
            if buffers[0] is not None or buffers[1] is not None:
                raise ValueError("paired tables have different row counts")
            return
        count = min(len(b) for b in buffers)
        yield tuple(b.slice(0, count) for b in buffers)
        buffers = [b.slice(count) for b in buffers]


def _rate(count, total):
    return (count/total, *agresti_coull(count, total)) if total else (None, None, None)


def _theta_json(theta):
    return theta if math.isfinite(theta) else "-inf" if theta < 0 else "inf"


def analyze_saved(run_path, settings=None):
    """Return compact rows; all cuts use gaps only and terminal labels only score.

    Complete source metadata is checked without importing Hex, constructing a
    circuit/decoder, or requiring the original simulation environment today.
    Unavailable scores, broken pairing and changed counts fail explicitly.
    """
    settings = AnalysisSettings() if settings is None else settings
    if not isinstance(settings, AnalysisSettings):
        raise ValueError("settings must be AnalysisSettings")
    path = Path(run_path).resolve()
    document = load_config(path / "config.yaml")
    config = document.config
    meta = json.loads((path / "metadata.json").read_text())
    units = "log_weight" if config.create_codecapacity_dem else "hamming_weight"
    if (config.kind != "logical_zero_factory" or meta.get("kind") != config.kind
            or meta.get("schema_version") != 2 or meta.get("status") != "complete"
            or meta.get("config_hash") != config.config_hash or meta.get("config") != config.as_dict()
            or meta.get("input_sha256") != document.input_hash
            or meta.get("gap_units") != units or meta.get("prior_policy") != config.prior_policy
            or meta.get("final_readout") != "noiseless_terminal_Z_factory_oracle"):
        raise ValueError("require a complete, unchanged factory run with declared score/oracle conventions")
    points = list(config.points())
    if set(meta["points"]) != {p.case_id for p in points}:
        raise ValueError("saved point identities changed")
    rows = []
    for point in points:
        info = meta["points"][point.case_id]
        if (info["status"] != "complete" or info["files"] != [point.filename(t) for t in point.tables]
                or type(info["shots"]) is not int or type(info["logical_errors"]) is not int
                or info.get("seed") != point_seed(config.master_seed, point)
                or any(info.get(k) != v for k, v in point.sampling_identity.items())):
            raise ValueError("require complete aligned factory points")
        files = [path / point.filename(t) for t in point.tables]
        if any(not file.is_file() for file in files):
            raise ValueError("missing paired factory file")
        validate_point_files(path, point, config.shots)
        hist = np.zeros((len(settings.thresholds), point.T_tel+1), np.int64)
        accepted_errors = np.zeros(len(settings.thresholds), np.int64)
        shots, errors = 0, 0
        for error_batch, gap_batch in _paired_batches(*files, settings.batch_size):
            if any(column.null_count for batch in (error_batch, gap_batch) for column in batch.columns):
                raise ValueError("factory analysis requires non-null IDs, labels and gaps")
            expected = np.arange(shots, shots+len(error_batch), dtype=np.uint64)
            if any(not np.array_equal(batch.column(0).to_numpy(), expected) for batch in (error_batch, gap_batch)):
                raise ValueError("paired shot IDs must align and be contiguous from zero")
            labels = error_batch.column(1).to_numpy(zero_copy_only=False)
            gaps = np.column_stack([gap_batch.column(j).to_numpy() for j in range(1, point.T_tel+1)])
            if not np.isfinite(gaps).all() or (gaps < 0).any():
                raise ValueError("factory gaps must be finite and nonnegative")
            shots += len(labels)
            errors += int(labels.sum())
            for index, theta in enumerate(settings.thresholds):
                first = first_rejected_stage(gaps, theta)
                hist[index] += np.bincount(first, minlength=point.T_tel+1)
                accepted_errors[index] += np.count_nonzero(labels & (first == 0))
        if shots != info["shots"] or errors != info["logical_errors"]:
            raise ValueError("saved row/error counts disagree with metadata")
        for index, theta in enumerate(settings.thresholds):
            accepted, bad = int(hist[index, 0]), int(accepted_errors[index])
            raw_rate, raw_lo, raw_hi = _rate(errors, shots)
            rate, lo, hi = _rate(bad, accepted)
            acceptance, a_lo, a_hi = _rate(accepted, shots)
            abort, b_lo, b_hi = _rate(shots-accepted, shots)
            rows.append(dict(case_id=point.case_id, d=point.d, p=point.p, r_0=point.r_0, r_plus=point.r_plus,
                             T_tel=point.T_tel, prior_policy=config.prior_policy, gap_units=units,
                             theta=_theta_json(theta), shots=shots, logical_errors=errors, accepted=accepted,
                             accepted_errors=bad, raw_ler=raw_rate, raw_ler_lower=raw_lo, raw_ler_upper=raw_hi,
                             acceptance=acceptance, acceptance_lower=a_lo, acceptance_upper=a_hi,
                             abort_rate=abort, abort_lower=b_lo, abort_upper=b_hi,
                             terminal_oracle_ler=rate, terminal_oracle_ler_lower=lo, terminal_oracle_ler_upper=hi,
                             terminal_oracle_ler_standard_error=math.sqrt(rate*(1-rate)/accepted) if accepted else None,
                             first_rejected_counts=hist[index, 1:].tolist(),
                             **summarize_cost(hist[index], point, settings.cost, iid_restarts=settings.iid_restarts)))
    return dict(analysis_version=1, run=str(path), estimand="conditional_terminal_factory_oracle_error",
                interval="95% pointwise Agresti-Coull; descriptive conditional on each fixed gap-only cut",
                uncertainty_note="No simultaneous/threshold-selection guarantee; cost SE uses an iid paired delta approximation.",
                cost_note="Counterfactual single-factory accounting; full trajectories were sampled. No queue, oracle latency or dynamic retry was simulated.",
                settings=dict(thresholds=[_theta_json(t) for t in settings.thresholds], cost=settings.cost.as_dict(),
                              iid_restarts=settings.iid_restarts, batch_size=settings.batch_size),
                provenance=dict(config_hash=config.config_hash, input_sha256=document.input_hash,
                                bench=meta["environment"]["bench"], hex=meta["environment"]["hex"]), rows=rows)


def write_report(report, output):
    """Write only an explicitly requested JSON/CSV/Markdown analysis artifact."""
    path = Path(output)
    if path.suffix == ".json":
        path.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    elif path.suffix == ".csv":
        rows = [dict(row, estimand=report["estimand"], interval=report["interval"],
                     cost_model=json.dumps(report["settings"]["cost"], sort_keys=True)) for row in report["rows"]]
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()} for row in rows)
    elif path.suffix == ".md":
        lines = ["# Saved factory acceptance and cost", "", report["estimand"], "", report["interval"], "",
                 report["uncertainty_note"], "", report["cost_note"], "", "Settings: `"+
                 json.dumps(report["settings"], sort_keys=True)+"`", "", "Simulation provenance: `"+
                 json.dumps(report["provenance"], sort_keys=True)+"`", "",
                 "| d | p | theta | accepted / shots | abort | terminal oracle LER [95% CI] | mean attempt cost | iid cost to first accepted |",
                 "|---|---|---|---|---|---|---|---|"]
        for row in report["rows"]:
            value = lambda name: "undefined" if row[name] is None else f"{row[name]:.6g}"
            lines.append(f"| {row['d']} | {row['p']} | {row['theta']} | {row['accepted']} / {row['shots']} | "
                         f"{value('abort_rate')} | {value('terminal_oracle_ler')} "
                         f"[{value('terminal_oracle_ler_lower')}, {value('terminal_oracle_ler_upper')}] | "
                         f"{value('mean_attempt_cost')} {row['cost_unit']} | {value('iid_cost_to_first_accepted')} |")
        path.write_text("\n".join(lines)+"\n")
    else:
        raise ValueError("analysis output must end in .json, .csv or .md")
    return path
