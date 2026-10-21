"""Small, strict schema-v2 configuration with exactly two sweep axes."""

from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING

import yaml

from .noise_v2 import noise_as_dict, parse_noise, validate_noise

if TYPE_CHECKING:
    from hex_qec.circuit_generation import FactoryNoiseModel


KNILL_KINDS = {"knill_ec_memory", "fig4d_reproduction"}
KINDS = KNILL_KINDS | {"logical_zero_factory", "se_memory"}
LOCAL_PRIOR_POLICY = "module_local_stim_dem"
LOCAL_PRIOR_APPROXIMATION = "preparation_and_earlier_stage_residual_errors_excluded_v1"
LEGACY_PRIOR_POLICY = "circuit_informed_projected"


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _mapping(value, allowed, where):
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{where} must be a mapping with string keys")
    unknown = value.keys() - set(allowed)
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")


def _integer(value, where, minimum=1, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{where} must be an integer in [{minimum}, {maximum}]")
    return value


def _number(value, where):
    if type(value) not in (int, float):
        raise ValueError(f"{where} must be a finite number")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{where} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{where} must be finite")
    return 0.0 if result == 0 else result


def _choice(value, choices, where):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{where} must be one of {sorted(choices)}")
    return value


def _round_multiplier(value, where):
    """Parse only a positive constant times d, using exact rational arithmetic."""
    if value == "d":
        return Fraction(1)
    number = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
    match = (re.fullmatch(rf"\s*({number})(?:\s*/\s*({number}))?\s*\*\s*d\s*", value)
             if isinstance(value, str) else None)
    if match is None:
        raise ValueError(f"{where} must be a positive integer, 'd', or a multiple such as '2*d' or '2/3*d'")
    numerator = Fraction(match[1])
    denominator = Fraction(match[2]) if match[2] is not None else Fraction(1)
    if numerator <= 0 or denominator <= 0:
        raise ValueError(f"{where} multiplier and denominator must be positive")
    return numerator / denominator


def _rounds(value, where):
    if type(value) is int:
        return _integer(value, where)
    _round_multiplier(value, where)
    return value


def _resolve_rounds(value, d, where):
    if type(value) is int:
        return _integer(value, where)
    multiplier = _round_multiplier(value, where)
    rounds = multiplier.numerator * d // multiplier.denominator
    return _integer(rounds, f"{where} resolved at d={d} (after flooring)")


class _UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("YAML mapping keys must be unique strings")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


@dataclass(frozen=True)
class ExperimentPoint:
    kind: str
    d: int
    p: float
    r_0: int
    r_plus: int
    T_tel: int
    code: str = "rotated_surface"
    noise: str = "hex_uniform"
    rounds: int | None = None
    get_logicalgap: bool = False
    noise_model: "FactoryNoiseModel | None" = None

    def __post_init__(self):
        _choice(self.kind, KINDS, "kind")
        _choice(self.code, {"rotated_surface"}, "code")
        validate_noise(self.kind, self.noise, self.noise_model)
        _integer(self.d, "d", 3)
        if self.d % 2 != 1:
            raise ValueError("d must be odd")
        p = _number(self.p, "p")
        if not 0 <= p <= .5:
            raise ValueError("p must be in [0, 0.5]")
        object.__setattr__(self, "p", p)
        if type(self.get_logicalgap) is not bool:
            raise ValueError("get_logicalgap must be bool")
        if self.kind == "se_memory":
            _integer(self.rounds, "rounds")
            _integer(self.r_0, "se_memory r_0 (no separate preparation)", 0, 0)
            _integer(self.r_plus, "se_memory r_plus (no separate preparation)", 0, 0)
            _integer(self.T_tel, "se_memory single trajectory", 1, 1)
        else:
            for name in ("r_0", "r_plus", "T_tel"):
                _integer(getattr(self, name), name)
            if self.rounds is not None or self.get_logicalgap:
                raise ValueError("rounds/get_logicalgap are supported only for se_memory")
        validate_noise(self.kind, self.noise, self.noise_model, p=p, r_plus=self.r_plus)

    @property
    def final_readout(self):
        if self.kind == "knill_ec_memory" and self.noise != "hex_uniform":
            return "ideal_destructive_Z"
        return ("noiseless_terminal_Z_factory_oracle" if self.kind == "logical_zero_factory"
                else "noisy_destructive_Z")

    @property
    def sampling_identity(self):
        # Decoder policy, theta, workers and requested shots cannot change the
        # identity of the physical circuit or its sampling seed.
        result = asdict(self)
        if self.noise_model is None:
            result.pop("noise_model")  # Preserve every uniform physical ID/seed.
        result.pop("get_logicalgap")  # An output/inference option, never physical identity.
        if self.kind == "se_memory":
            for name in ("r_0", "r_plus", "T_tel"):
                result.pop(name)
            result["initial_boundary"] = "noisy_physical_zero"
        else:
            result.pop("rounds")  # Preserve every existing physical ID/seed.
        return dict(result, final_readout=self.final_readout, memory_basis="z")

    @property
    def case_id(self):
        return digest(self.sampling_identity)

    def filename(self, table: str) -> str:
        if table not in {"logical_error", "logical_gaps"}:
            raise ValueError("unknown v2 point table")
        if table not in self.tables:
            raise ValueError("this point has no logical_gaps table")
        # The literal '+' is valid in a filename. Never use these names as
        # unescaped regular expressions or interpolate them into shell code.
        return (f"{table}__code={self.code},d={self.d},p={self.p!r},noisemodel={self.noise},"
                f"T={self.T_tel},r_0={self.r_0},r_+={self.r_plus}"
                + (f",rounds={self.rounds}" if self.kind == "se_memory" else "") + ".parquet")

    @property
    def tables(self):
        return (("logical_error", "logical_gaps") if self.kind == "logical_zero_factory" or self.get_logicalgap
                else ("logical_error",))


@dataclass(frozen=True)
class ExperimentConfig:
    kind: str
    name: str
    distances: tuple[int, ...]
    probabilities: tuple[float, ...]
    output_root: str = "results"
    code: str = "rotated_surface"
    noise: str = "hex_uniform"
    r_0: int | str = "d"
    r_plus: int | str = "d"
    T_tel: int = 1
    theta: float | None = None
    create_codecapacity_dem: bool = False
    decoder: str = "mwpm"
    shots: int = 64
    batch_size: int | str = "auto"
    workers: int = 1
    master_seed: int = 12345
    skip_circuit_validation: bool = False
    buffer_shot: int | None = None
    target_chunk_seconds: float = 1.0
    rounds: int | str = "d"
    get_logicalgap: bool = False
    noise_model: "FactoryNoiseModel | None" = None

    def __post_init__(self):
        validate_noise(self.kind, self.noise, self.noise_model)
        if self.noise_model is not None:
            for d in self.distances:
                r_plus = _resolve_rounds(self.r_plus, d, "r_plus")
                for p in self.probabilities:
                    validate_noise(self.kind, self.noise, self.noise_model, p=p, r_plus=r_plus)

    @property
    def output_buffer_shots(self):
        return self.buffer_shot or (10_000 if self.batch_size == "auto" else self.batch_size)

    def as_dict(self):
        result = asdict(self)
        result.pop("noise_model")
        if self.noise_model is not None:
            result["noise"] = noise_as_dict(self.noise_model)
        # Preserve canonical hashes of existing configurations with full validation.
        if not result["skip_circuit_validation"]:
            result.pop("skip_circuit_validation")
        # Explicit fixed-batch legacy documents retain their canonical hashes.
        if self.buffer_shot is None:
            result.pop("buffer_shot")
        if self.target_chunk_seconds == 1.0:
            result.pop("target_chunk_seconds")
        if self.kind == "se_memory":
            for name in ("r_0", "r_plus", "T_tel", "theta", "create_codecapacity_dem"):
                result.pop(name)
        else:
            result.pop("rounds")
            result.pop("get_logicalgap")
        result["schema_version"] = 2
        result["sweep"] = {"d": list(result.pop("distances")), "p": list(result.pop("probabilities"))}
        return result

    @property
    def config_hash(self):
        return digest(self.as_dict())

    @property
    def prior_policy(self):
        if self.kind == "se_memory":
            return "full_circuit_stim_dem"
        return LOCAL_PRIOR_POLICY if self.create_codecapacity_dem else "hex_legacy_hamming"

    @property
    def gap_units(self):
        if self.kind == "se_memory":
            return "log_weight" if self.get_logicalgap else None
        if self.kind == "logical_zero_factory":
            return "log_weight" if self.create_codecapacity_dem else "hamming_weight"
        return None

    def points(self):
        for d in self.distances:
            for p in self.probabilities:
                if self.kind == "se_memory":
                    yield ExperimentPoint(self.kind, d, p, 0, 0, 1, self.code, self.noise,
                                          _resolve_rounds(self.rounds, d, "rounds"), self.get_logicalgap)
                    continue
                yield ExperimentPoint(self.kind, d, p, _resolve_rounds(self.r_0, d, "r_0"),
                                      _resolve_rounds(self.r_plus, d, "r_plus"), self.T_tel,
                                      self.code, self.noise, noise_model=self.noise_model)


@dataclass(frozen=True)
class ConfigDocument:
    config: ExperimentConfig
    contents: bytes
    source_path: Path

    @property
    def input_hash(self):
        return hashlib.sha256(self.contents).hexdigest()


def parse_config(raw) -> ExperimentConfig:
    _mapping(raw, "schema_version kind name output_root code noise sweep r_0 r_plus T_tel theta "
             "create_codecapacity_dem decoder shots batch_size workers master_seed skip_circuit_validation "
             "buffer_shot target_chunk_seconds rounds get_logicalgap".split(), "root")
    if type(raw.get("schema_version")) is not int or raw["schema_version"] != 2:
        raise ValueError("schema_version must be 2")
    kind = _choice(raw.get("kind"), KINDS, "kind")
    noise, noise_model = parse_noise(raw.get("noise", "hex_uniform"), kind)
    if kind != "se_memory" and {"rounds", "get_logicalgap"} & raw.keys():
        raise ValueError("rounds/get_logicalgap are supported only for se_memory")
    if kind == "se_memory" and {"r_0", "r_plus", "T_tel", "theta", "create_codecapacity_dem"} & raw.keys():
        raise ValueError("se_memory accepts rounds/get_logicalgap, not Knill resource/teleportation/prior options")
    name = raw.get("name", kind)
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name):
        raise ValueError("name must be a safe 1-80 character experiment name")
    output = raw.get("output_root", "results")
    if not isinstance(output, str) or not output.strip() or "\0" in output:
        raise ValueError("output_root must be a nonempty path string")
    sweep = raw.get("sweep")
    _mapping(sweep, {"d", "p"}, "sweep (only d and p are permitted)")
    if set(sweep) != {"d", "p"}:
        raise ValueError("sweep must contain d and p")
    for axis in ("d", "p"):
        if not isinstance(sweep[axis], list) or not sweep[axis]:
            raise ValueError(f"sweep.{axis} must be a nonempty list")
    ds = tuple(_integer(d, "sweep.d", 3) for d in sweep["d"])
    if any(d % 2 != 1 for d in ds):
        raise ValueError("sweep.d must contain odd distances")
    ps = tuple(_number(p, "sweep.p") for p in sweep["p"])
    if any(not 0 <= p <= .5 for p in ps):
        raise ValueError("sweep.p must be in [0, 0.5]")
    if len(set(ds)) != len(ds) or len(set(ps)) != len(ps):
        raise ValueError("sweep axes must be unique")
    memory_rounds = _rounds(raw.get("rounds", "d"), "rounds")
    for d in ds:
        _resolve_rounds(memory_rounds, d, "rounds")
    get_gap = raw.get("get_logicalgap", False)
    if type(get_gap) is not bool:
        raise ValueError("get_logicalgap must be bool")
    if get_gap and any(not 0 < p < .5 for p in ps):
        raise ValueError("get_logicalgap log-weight scoring requires 0 < p < 0.5")
    policy = raw.get("create_codecapacity_dem", False)
    if type(policy) is not bool:
        raise ValueError("create_codecapacity_dem must be bool")
    if kind in KNILL_KINDS and policy:
        raise ValueError("Knill EC / Fig.4(d) reproduction requires create_codecapacity_dem=False")
    skip_validation = raw.get("skip_circuit_validation", False)
    if type(skip_validation) is not bool:
        raise ValueError("skip_circuit_validation must be bool")
    if skip_validation and kind != "logical_zero_factory":
        raise ValueError("skip_circuit_validation=True is supported only for logical_zero_factory")
    theta = raw.get("theta")
    if theta is not None:
        theta = _number(theta, "theta")
    rounds = {}
    for round_name in ("r_0", "r_plus"):
        rounds[round_name] = _rounds(raw.get(round_name, "d"), round_name)
        # Validate every distance now, before prepare/run creates any output.
        for d in ds:
            _resolve_rounds(rounds[round_name], d, round_name)
    batch = raw.get("batch_size", "auto")
    if batch != "auto":
        batch = _integer(batch, "batch_size")
    buffer = _integer(raw["buffer_shot"], "buffer_shot") if "buffer_shot" in raw else None
    target = _number(raw.get("target_chunk_seconds", 1.0), "target_chunk_seconds")
    if target <= 0:
        raise ValueError("target_chunk_seconds must be positive")
    if batch != "auto" and "target_chunk_seconds" in raw:
        raise ValueError("target_chunk_seconds requires batch_size: auto")
    return ExperimentConfig(
        kind, name, ds, ps, output,
        _choice(raw.get("code", "rotated_surface"), {"rotated_surface"}, "code"),
        noise,
        rounds["r_0"], rounds["r_plus"],
        _integer(raw.get("T_tel", 8 if kind in KNILL_KINDS else 1), "T_tel"),
        theta, policy, _choice(raw.get("decoder", "mwpm"), {"mwpm"}, "decoder"),
        _integer(raw.get("shots", 64), "shots"), batch,
        _integer(raw.get("workers", 1), "workers"),
        _integer(raw.get("master_seed", 12345), "master_seed", 0, 2**64 - 1),
        skip_validation, buffer, target, memory_rounds, get_gap, noise_model,
    )


def load_config(path, *, workers=None) -> ConfigDocument:
    source = Path(path).resolve()
    contents = source.read_bytes()
    try:
        raw = yaml.load(contents.decode("utf-8"), Loader=_UniqueSafeLoader)
    except (yaml.YAMLError, UnicodeError) as error:
        raise ValueError(f"invalid v2 YAML: {error}") from error
    # Validate the original even when applying a CLI resource override.
    parse_config(raw)
    if workers is not None:
        _integer(workers, "workers")
        original_hash = hashlib.sha256(contents).hexdigest()
        raw = dict(raw, workers=workers)
        contents = (f"# CLI workers override; original input SHA256: {original_hash}\n"
                    + yaml.safe_dump(raw, sort_keys=False)).encode("utf-8")
    return ConfigDocument(parse_config(raw), contents, source)


def load_saved_config(run_path) -> ConfigDocument:
    """Retain the old implicit batch_size=32 for already saved legacy runs.

    New input defaults to auto. Saved canonical metadata disambiguates old
    omitted defaults; callers still enforce full hash/config/provenance checks.
    """
    path = Path(run_path)
    document = load_config(path / "config.yaml")
    metadata = json.loads((path / "metadata.json").read_text())
    if (document.config.batch_size == "auto"
            and metadata.get("input_sha256") == document.input_hash
            and metadata.get("config", {}).get("batch_size") == 32
            and "batch_size" not in yaml.load(document.contents, Loader=_UniqueSafeLoader)):
        document = replace(document, config=replace(document.config, batch_size=32))
    return document
