"""Small, strict schema-v2 configuration with exactly two sweep axes."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re

import yaml


KINDS = {"fig4d_reproduction", "logical_zero_factory"}


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


def _rounds(value, where):
    return value if value == "d" else _integer(value, where)


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

    def __post_init__(self):
        _choice(self.kind, KINDS, "kind")
        _choice(self.code, {"rotated_surface"}, "code")
        _choice(self.noise, {"hex_uniform"}, "noise")
        _integer(self.d, "d", 3)
        if self.d % 2 != 1:
            raise ValueError("d must be odd")
        p = _number(self.p, "p")
        if not 0 <= p <= .5:
            raise ValueError("p must be in [0, 0.5]")
        object.__setattr__(self, "p", p)
        for name in ("r_0", "r_plus", "T_tel"):
            _integer(getattr(self, name), name)

    @property
    def final_readout(self):
        return ("noiseless_terminal_Z_factory_oracle" if self.kind == "logical_zero_factory"
                else "noisy_destructive_Z")

    @property
    def sampling_identity(self):
        # Decoder policy, theta, workers and requested shots cannot change the
        # identity of the physical circuit or its sampling seed.
        return dict(asdict(self), final_readout=self.final_readout, memory_basis="z")

    @property
    def case_id(self):
        return digest(self.sampling_identity)

    def filename(self, table: str) -> str:
        if table not in {"logical_error", "logical_gaps"}:
            raise ValueError("unknown v2 point table")
        if table == "logical_gaps" and self.kind != "logical_zero_factory":
            raise ValueError("Fig.4(d) has no logical_gaps table")
        # The literal '+' is valid in a filename. Never use these names as
        # unescaped regular expressions or interpolate them into shell code.
        return (f"{table}__code={self.code},d={self.d},p={self.p!r},noisemodel={self.noise},"
                f"T={self.T_tel},r_0={self.r_0},r_+={self.r_plus}.parquet")

    @property
    def tables(self):
        return ("logical_error", "logical_gaps") if self.kind == "logical_zero_factory" else ("logical_error",)


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
    batch_size: int = 32
    workers: int = 1
    master_seed: int = 12345

    def as_dict(self):
        result = asdict(self)
        result["schema_version"] = 2
        result["sweep"] = {"d": list(result.pop("distances")), "p": list(result.pop("probabilities"))}
        return result

    @property
    def config_hash(self):
        return digest(self.as_dict())

    @property
    def prior_policy(self):
        return "circuit_informed_projected" if self.create_codecapacity_dem else "hex_legacy_hamming"

    def points(self):
        for d in self.distances:
            for p in self.probabilities:
                yield ExperimentPoint(self.kind, d, p, d if self.r_0 == "d" else self.r_0,
                                      d if self.r_plus == "d" else self.r_plus, self.T_tel,
                                      self.code, self.noise)


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
             "create_codecapacity_dem decoder shots batch_size workers master_seed".split(), "root")
    if type(raw.get("schema_version")) is not int or raw["schema_version"] != 2:
        raise ValueError("schema_version must be 2")
    kind = _choice(raw.get("kind"), KINDS, "kind")
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
    policy = raw.get("create_codecapacity_dem", False)
    if type(policy) is not bool:
        raise ValueError("create_codecapacity_dem must be bool")
    if kind == "fig4d_reproduction" and policy:
        raise ValueError("Fig.4(d) reproduction requires create_codecapacity_dem=False")
    theta = raw.get("theta")
    if theta is not None:
        theta = _number(theta, "theta")
    return ExperimentConfig(
        kind, name, ds, ps, output,
        _choice(raw.get("code", "rotated_surface"), {"rotated_surface"}, "code"),
        _choice(raw.get("noise", "hex_uniform"), {"hex_uniform"}, "noise"),
        _rounds(raw.get("r_0", "d"), "r_0"), _rounds(raw.get("r_plus", "d"), "r_plus"),
        _integer(raw.get("T_tel", 8 if kind == "fig4d_reproduction" else 1), "T_tel"),
        theta, policy, _choice(raw.get("decoder", "mwpm"), {"mwpm"}, "decoder"),
        _integer(raw.get("shots", 64), "shots"), _integer(raw.get("batch_size", 32), "batch_size"),
        _integer(raw.get("workers", 1), "workers"),
        _integer(raw.get("master_seed", 12345), "master_seed", 0, 2**64 - 1),
    )


def load_config(path) -> ConfigDocument:
    source = Path(path).resolve()
    contents = source.read_bytes()
    try:
        raw = yaml.load(contents.decode("utf-8"), Loader=_UniqueSafeLoader)
    except (yaml.YAMLError, UnicodeError) as error:
        raise ValueError(f"invalid v2 YAML: {error}") from error
    return ConfigDocument(parse_config(raw), contents, source)
