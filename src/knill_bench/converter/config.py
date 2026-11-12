"""Strict converter-only schema, without importing the converter or Hex."""

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import re

from knill_bench.experiments.config_v2 import (
    CONVERTER_KINDS, _choice, _integer, _mapping, _number, _resolve_rounds, _rounds, digest,
)

COMMON = set("schema_version kind name output_root code noise sweep shots batch_size workers "
             "master_seed decoder buffer_shot target_chunk_seconds input_preparation".split())
SPECIFIC = {
    "converter_se_memory": {"rounds"},
    "converter_knill_memory": {"T_tel", "r_0", "r_plus", "resource_preparation", "post_rounds", "p_st_multiplier"},
    "converter_deep_clifford": {"logical_qubits", "depth", "circuit_seed", "n_r", "r_0", "r_plus",
                                "resource_preparation", "p_st_multiplier"},
}
KNILL_PREPARATIONS = {"ideal_post_se_depolarizing", "noisy_d_rounds"}


@dataclass(frozen=True)
class ConverterPoint:
    kind: str
    d: int
    p: float
    input_preparation: str
    rounds: int | None = None
    r_0: int = 0
    r_plus: int = 0
    T_tel: int = 1
    resource_preparation: str | None = None
    logical_qubits: int | None = None
    depth: int | None = None
    circuit_seed: int | None = None
    n_r: int | None = None
    code: str = "rotated_surface"
    noise: str = "converter_uniform"
    post_rounds: int = 0
    p_st_multiplier: float | None = None

    @property
    def sampling_identity(self):
        fields = COMMON | SPECIFIC[self.kind]
        result = {k: v for k, v in asdict(self).items() if k in fields or k in {"d", "p"}}
        contract = {"converter_knill_memory": "converter_knill_program_v1",
                    "converter_deep_clifford": "converter_deep_clifford_program_v1"}
        return dict(result, program_contract=contract.get(self.kind, "converter_program_v1"),
                    final_readout=self.final_readout)

    @property
    def final_readout(self):
        return ("ideal_terminal_stabilizer_probes_evaluation_only" if self.kind == "converter_deep_clifford"
                else "noisy_destructive_Z")

    @property
    def case_id(self):
        return digest(self.sampling_identity)

    @property
    def directory(self):
        # Persist POSIX relative paths; Path joins them portably on Windows too.
        return PurePosixPath("points", self.case_id).as_posix()

    @property
    def tables(self):
        return ("logical_error",)

    def filename(self, table):
        if table not in self.tables:
            raise ValueError("converter points contain only logical_error")
        return f"{self.directory}/{table}.parquet"

    @property
    def artifact_names(self):
        return ("circuit.lstim", "circuit.stim", "metadata.json")

    @property
    def optional_artifact_names(self):
        return ("logical_stabilizers.json",) if self.kind == "converter_deep_clifford" else ()

    @property
    def files(self):
        return (self.filename("logical_error"), *(f"{self.directory}/{n}" for n in self.artifact_names))


@dataclass(frozen=True)
class ConverterConfig:
    kind: str
    name: str
    distances: tuple[int, ...]
    probabilities: tuple[float, ...]
    output_root: str = "results"
    code: str = "rotated_surface"
    noise: str = "converter_uniform"
    decoder: str = "mwpm"
    shots: int = 64
    batch_size: int | str = "auto"
    workers: int = 1
    master_seed: int = 12345
    buffer_shot: int | None = None
    target_chunk_seconds: float = 1.0
    input_preparation: str = "noisy"
    rounds: int | str = "d"
    T_tel: int = 1
    r_0: int | str = "d"
    r_plus: int | str = "d"
    resource_preparation: str = "noisy"
    logical_qubits: int = 4
    depth: int = 32
    circuit_seed: int = 0
    n_r: int = 1
    post_rounds: int = 0
    p_st_multiplier: float | None = None

    # Shared RunStore interface; these are never converter YAML or identity fields.
    create_codecapacity_dem = False
    codecapacity_prior = "module_local"
    @property
    def prior_policy(self):
        if self.kind == "converter_deep_clifford":
            return "converter_deep_local_component_mwpm_css_capacity_v1"
        if self.kind == "converter_knill_memory":
            return "converter_knill_local_component_mwpm_css_capacity_v1"
        return ("converter_z_sector_undecomposed_dem_mwpm_v1" if self.kind == "converter_se_memory"
                else "converter_decoder_pending")
    projected_approximation = None
    gap_units = None

    @property
    def output_buffer_shots(self):
        return self.buffer_shot or (10_000 if self.batch_size == "auto" else self.batch_size)

    def as_dict(self):
        fields = COMMON | SPECIFIC[self.kind] | {"distances", "probabilities"}
        result = {k: v for k, v in asdict(self).items() if k in fields}
        if self.kind in {"converter_knill_memory", "converter_deep_clifford"} and self.p_st_multiplier is None:
            result.pop("p_st_multiplier")
        if self.buffer_shot is None:
            result.pop("buffer_shot")
        if self.target_chunk_seconds == 1.0:
            result.pop("target_chunk_seconds")
        result["schema_version"] = 2
        result["sweep"] = dict(d=list(result.pop("distances")), p=list(result.pop("probabilities")))
        return result

    @property
    def config_hash(self):
        return digest(self.as_dict())

    def points(self):
        for d in self.distances:
            for p in self.probabilities:
                options = {key: getattr(self, key) for key in SPECIFIC[self.kind]}
                for key in ("rounds", "r_0", "r_plus"):
                    if key in options:
                        options[key] = _resolve_rounds(options[key], d, key)
                yield ConverterPoint(self.kind, d, p, self.input_preparation,
                                     code=self.code, noise=self.noise, **options)


def parse_converter_config(raw):
    kind = _choice(raw.get("kind"), CONVERTER_KINDS, "kind")
    _mapping(raw, COMMON | SPECIFIC[kind], "converter root")
    if type(raw.get("schema_version")) is not int or raw["schema_version"] != 2:
        raise ValueError("schema_version must be 2")
    name = raw.get("name", kind)
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name):
        raise ValueError("name must be a safe 1-80 character experiment name")
    output = raw.get("output_root", "results")
    if not isinstance(output, str) or not output.strip() or "\0" in output:
        raise ValueError("output_root must be a nonempty path string")
    sweep = raw.get("sweep")
    _mapping(sweep, {"d", "p"}, "sweep (only d and p are permitted)")
    if set(sweep) != {"d", "p"} or any(not isinstance(sweep[k], list) or not sweep[k] for k in sweep):
        raise ValueError("sweep must contain nonempty d and p lists")
    ds = tuple(_integer(d, "sweep.d", 3) for d in sweep["d"])
    ps = tuple(_number(p, "sweep.p") for p in sweep["p"])
    if any(d % 2 != 1 for d in ds) or any(not 0 <= p <= .5 for p in ps):
        raise ValueError("sweep requires odd d>=3 and 0<=p<=0.5")
    if len(set(ds)) != len(ds) or len(set(ps)) != len(ps):
        raise ValueError("sweep axes must be unique")
    regime = (_choice(raw.get("resource_preparation", "noisy_d_rounds"), KNILL_PREPARATIONS,
                      "resource_preparation") if kind == "converter_knill_memory" else None)
    default_input = "ideal" if regime == "ideal_post_se_depolarizing" or kind == "converter_deep_clifford" else "noisy"
    options = dict(kind=kind, name=name, distances=ds, probabilities=ps, output_root=output,
                   code=_choice(raw.get("code", "rotated_surface"), {"rotated_surface"}, "code"),
                   noise=_choice(raw.get("noise"), {"converter_uniform"}, "noise"),
                   decoder=_choice(raw.get("decoder", "mwpm"), {"mwpm"}, "decoder"),
                   input_preparation=_choice(raw.get("input_preparation", default_input), {"noisy", "ideal"},
                                             "input_preparation"))
    for key, default in (("shots", 64), ("workers", 1), ("T_tel", 1), ("logical_qubits", 4),
                         ("depth", 32), ("n_r", 1)):
        if key in COMMON | SPECIFIC[kind]:
            options[key] = _integer(raw.get(key, default), key)
    for key, default in (("master_seed", 12345), ("circuit_seed", 0)):
        if key in COMMON | SPECIFIC[kind]:
            options[key] = _integer(raw.get(key, default), key, 0, 2**64-1)
    for key in ("rounds", "r_0", "r_plus"):
        if key in SPECIFIC[kind]:
            options[key] = _rounds(raw.get(key, "d"), key)
            for d in ds:
                _resolve_rounds(options[key], d, key)
    if "resource_preparation" in SPECIFIC[kind]:
        options["resource_preparation"] = (regime if regime is not None else
            _choice(raw.get("resource_preparation", "noisy"), {"noisy", "ideal"}, "resource_preparation"))
        if any(_resolve_rounds(options["r_0"], d, "r_0") != _resolve_rounds(options["r_plus"], d, "r_plus")
               for d in ds):
            raise ValueError("rotated-surface converter KNILL_EC requires resolved r_0 == r_plus at every d")
    if kind == "converter_knill_memory":
        if options["input_preparation"] != default_input:
            raise ValueError("input_preparation must agree with the named Knill preparation regime")
        if any(_resolve_rounds(options["r_0"], d, "r_0") != d for d in ds):
            raise ValueError("both named Knill regimes require r_0=r_plus=d; other resource depths are unsupported")
        options["post_rounds"] = _integer(raw.get("post_rounds", 0), "post_rounds", 0)
        if regime == "noisy_d_rounds":
            if "p_st_multiplier" in raw:
                raise ValueError("p_st_multiplier requires ideal_post_se_depolarizing")
        else:
            multiplier = _number(raw.get("p_st_multiplier", 1.), "p_st_multiplier")
            if multiplier < 0 or any(not 0 <= p*multiplier <= .75 for p in ps):
                raise ValueError("p_st_multiplier must be nonnegative with p_st in [0,0.75] at every p")
            options["p_st_multiplier"] = multiplier
    if kind == "converter_deep_clifford":
        if options["input_preparation"] != "ideal":
            raise ValueError("deep Clifford circuits require input_preparation: ideal")
        if options["logical_qubits"] < 2 or options["logical_qubits"] % 2:
            raise ValueError("logical_qubits must be even and >=2 for disjoint CNOT pairing")
        if any(_resolve_rounds(options["r_0"], d, "r_0") != d for d in ds):
            raise ValueError("deep Clifford resources require r_0=r_plus=d at every distance")
        if options["resource_preparation"] == "noisy":
            if "p_st_multiplier" in raw:
                raise ValueError("deep p_st_multiplier requires resource_preparation: ideal")
        else:
            multiplier = _number(raw.get("p_st_multiplier", 0.), "p_st_multiplier")
            if multiplier < 0 or any(not 0 <= p*multiplier <= .75 for p in ps):
                raise ValueError("p_st_multiplier must be nonnegative with p_st in [0,0.75] at every p")
            options["p_st_multiplier"] = multiplier
    batch = raw.get("batch_size", "auto")
    options["batch_size"] = batch if batch == "auto" else _integer(batch, "batch_size")
    if "buffer_shot" in raw:
        options["buffer_shot"] = _integer(raw["buffer_shot"], "buffer_shot")
    target = _number(raw.get("target_chunk_seconds", 1.), "target_chunk_seconds")
    if target <= 0 or (batch != "auto" and "target_chunk_seconds" in raw):
        raise ValueError("positive target_chunk_seconds requires batch_size: auto")
    options["target_chunk_seconds"] = target
    return ConverterConfig(**options)
