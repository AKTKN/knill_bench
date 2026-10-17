"""Module-local Stim priors attached to the pinned Hex factory decoder.

MODEL CHANGE: preparation and earlier-stage residual errors are EXCLUDED from
this prior, although they remain in the physical simulation. Ideal +1 input
stabilizers and Pauli observable boundaries are analysis-only. No preparation
decoder, physical shot, future measurement or terminal oracle enters the DEM.

Hex supplies every physical operation and causal stage/frame algorithm. H5
bindings below optionally omit full construction-time bundle validation and
replace preparation-frame arithmetic while retaining all matching decisions.
"""

from dataclasses import asdict, dataclass, fields
from functools import lru_cache
import hashlib
from types import FunctionType, MappingProxyType

import pymatching
import stim

from hex_qec.decoders.codecapacity_dem import (
    FaultSignature, ProjectedErrorModel, ProjectedEvent, UnsupportedProjectedModel,
)
from hex_qec.decoders.factory_surface import SurfaceFactoryReadout
from hex_qec.modularisation import PreparationPlan
from hex_qec.modularisation.factory import FACTORY_FRAME_CONVENTION
from hex_qec.protocols import FactoryCircuitBuilder, RotatedSurfaceCodeAdapter
from hex_qec.protocols.logical_zero_factory import FactoryCircuitBundle
from hex_qec.simulation import factory as native
from knill_bench.experiments.config_v2 import LOCAL_PRIOR_APPROXIMATION, digest
from .factory_frames import FactoryPreparationPlan


POLICY = "factory_module_local_stim_v1"
BOUNDARY = "after_preparation_before_native_coupling; no_added_noise"


@dataclass(frozen=True)
class LocalPrior:
    """Immutable descriptions; native matching handles are kept separately."""

    model: ProjectedErrorModel
    dem_text: str
    configuration_sha256: str
    model_sha256: str
    physical_module_sha256: str
    analysis_circuit_sha256: str
    approximation: str = LOCAL_PRIOR_APPROXIMATION
    boundary: str = BOUNDARY


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@lru_cache(maxsize=8)
def _ideal_input(code):
    """Analysis-only encoded |0>_A |+>_B, all CSS stabilizers +1.

    Return text, not a mutable Circuit shared with a physical caller. This
    encoder is never concatenated into the sampled circuit.
    """
    n = code.num_data_qubits

    def pauli(basis, indices):
        value = stim.PauliString(2*n)
        for index in indices:
            value[index] = basis
        return value

    stabilizers = [pauli(basis, [offset+i for i in row])
                   for offset in (0, n)
                   for basis, rows in (("X", code.x_checks), ("Z", code.z_checks))
                   for row in rows]
    stabilizers += [pauli("Z", code.logical_z), pauli("X", [n+i for i in code.logical_x])]
    circuit = stim.Circuit()
    circuit.append("R", range(2*n))
    circuit += stim.Tableau.from_stabilizers(stabilizers).to_circuit()
    return str(circuit)


def _local_body(bundle, stage):
    """Extract the actual module, canonicalizing consumed/fresh support IDs.

    Include every actual coupling/readout channel, including native post-CNOT
    control idle. Native storage_idle is before coupling and excluded along
    with preparation residuals. No boundary channel is invented.
    """
    blocks = {b.name: b for b in bundle.blocks}
    support = (blocks[stage.consumed_block].data_qubits
               + blocks[stage.surviving_block].data_qubits)
    mapping = {q: i for i, q in enumerate(support)}
    body = stim.Circuit()
    for region in (stage.coupling, stage.measurement):
        for instruction in bundle.circuit[region.instructions.start:region.instructions.stop]:
            if instruction.name in {"DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"}:
                continue
            targets = instruction.targets_copy()
            if any(not t.is_qubit_target or t.value not in mapping for t in targets):
                raise UnsupportedProjectedModel("local factory module needs data-only quantum targets")
            body.append(instruction.name,
                        [stim.target_inv(mapping[t.value]) if t.is_inverted_result_target
                         else mapping[t.value] for t in targets], instruction.gate_args_copy())
    n = bundle.code.num_data_qubits
    measured = [t.value for i in body if i.name == "M" for t in i.targets_copy()]
    if measured != list(range(n)) or body.num_measurements != n:
        raise UnsupportedProjectedModel("local factory module requires ordered destructive Z readout")
    return str(body)


def _analysis_circuit(code, body_text):
    n = code.num_data_qubits
    circuit = stim.Circuit(_ideal_input(code))
    # Z_L(A) at the output pulls back through CX(B,A) to Z_L(A) Z_L(B).
    # Pauli OBSERVABLE_INCLUDE targets (Stim >=1.16) close that sensitivity
    # without measuring or fixing the intrinsically random logical byproduct.
    # Place this BEFORE the first included noise channel.
    circuit.append("OBSERVABLE_INCLUDE",
                   [stim.target_z(i) for i in code.logical_z]
                   + [stim.target_z(n+i) for i in code.logical_z], 0)
    circuit += stim.Circuit(body_text)
    for row in code.z_checks:
        circuit.append("DETECTOR", [stim.target_rec(i-n) for i in row])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(i-n) for i in code.logical_z], 0)
    return circuit


def _stim_dem(circuit):
    """Instrumentable strict native DEM boundary; no Monte Carlo/reference shot."""
    return circuit.detector_error_model(decompose_errors=False,
                                       allow_gauge_detectors=False,
                                       approximate_disjoint_errors=False)


def _event_model(dem):
    events = []
    for instruction in dem.flattened():
        if instruction.type != "error":
            continue
        targets = instruction.targets_copy()
        if any(not (t.is_relative_detector_id() or t.is_logical_observable_id()) for t in targets):
            raise UnsupportedProjectedModel("local DEM must retain undecomposed complete signatures")
        signature = FaultSignature(tuple(t.val for t in targets if t.is_relative_detector_id()),
                                   tuple(t.val for t in targets if t.is_logical_observable_id()))
        # Stim already merges complete signatures. IDs here identify DEM rows,
        # not original physical mechanisms; do not invent mechanism provenance.
        events.append(ProjectedEvent(signature, instruction.args_copy()[0], (len(events),)))
    return ProjectedErrorModel(dem.num_detectors, tuple(events))


def _build_local_prior(code, body_text, noise_model_sha256=""):
    circuit = _analysis_circuit(code, body_text)
    dem = _stim_dem(circuit)
    model = _event_model(dem)
    gap = model.compile_gap()  # Retains H5's graph/lift/q/p0 checks; no fallback.
    description = dict(policy=POLICY, approximation=LOCAL_PRIOR_APPROXIMATION,
                       boundary=BOUNDARY, code=asdict(code), physical_module=body_text,
                       analysis_circuit=str(circuit), stim=stim.__version__, pymatching=pymatching.__version__)
    if noise_model_sha256:
        description["noise_model_sha256"] = noise_model_sha256
    prior = LocalPrior(model, str(dem), digest(description), _sha(str(dem)),
                       _sha(body_text), _sha(str(circuit)))
    return prior, gap


@lru_cache(maxsize=16)
def _cached_local_prior(code, body_text, noise_model_sha256=""):
    """Bounded synchronous worker-local cache; no samplers/RNG state cached.

    Complete canonical physical module text includes every in-window channel.
    Custom mode also keys the complete native noise configuration, keeping
    excluded prep/storage parameter changes separately identified. T, depths,
    seeds, shots, theta and physical support labels do not affect this local
    model. Native versions are process-fixed
    and recorded in the configuration hash. Spawn workers have separate caches.
    """
    return (_build_local_prior(code, body_text, noise_model_sha256) if noise_model_sha256
            else _build_local_prior(code, body_text))


def clear_local_prior_cache():
    _cached_local_prior.cache_clear()
    _ideal_input.cache_clear()


def local_prior_cache_info():
    return _cached_local_prior.cache_info()._asdict()


class _LocalFactoryDecoder(native.FactoryBatchDecoder):
    def __init__(self, bundle, *, create_codecapacity_dem=True):
        # Private immediate handoff from our builder boundary. Full validation
        # is controlled there; native decoder construction must not repeat it.
        if bundle.metadata["frame_convention"] != FACTORY_FRAME_CONVENTION:
            raise ValueError("unsupported factory frame convention")
        self._stages = bundle.stages
        self._oracle = bundle.oracle.measurements
        self._width = bundle.circuit.num_measurements
        templates, plans = {}, {}
        for plan in bundle.preparation_frames:
            key = id(plan.module)
            if key not in templates:
                templates[key] = FactoryPreparationPlan(plan)
            plans[plan.region.measurements.start] = templates[key].bind(plan.region)
        self._plans = MappingProxyType(plans)
        if len(self._plans) != len(self._stages)+1:
            raise ValueError("factory must have one zero prep and one plus prep per stage")
        self._initial = self._plans[self._stages[0].preparations[0].measurements.start]
        self._readout = SurfaceFactoryReadout(bundle.code, self._initial.module.z_pcm)
        noise_hash = bundle.metadata.get("noise_model_sha256", "")
        models = ([_cached_local_prior(bundle.code, _local_body(bundle, stage), noise_hash)
                   if noise_hash else _cached_local_prior(bundle.code, _local_body(bundle, stage))
                   for stage in self._stages] if create_codecapacity_dem else [])
        self.projected_priors = tuple(prior for prior, _ in models)
        self._projected_gaps = tuple(gap for _, gap in models)
        # Native stage methods retain causal readout/frame/gap/oracle behavior.
        # Only the preparation plans' equivalent arithmetic is replaced.


class _ConstructionBundle(FactoryCircuitBundle):
    """Private construction-only bundle; never returned to a caller."""

    def validate(self):
        pass


_H5_BUILD = FactoryCircuitBuilder.build


def _build_without_full_validation(builder):
    """Run H5's exact build code with a private construction type binding.

    H5 has no validate=False argument. Rebind only its bundle constructor in
    a private globals dictionary: no dependency edit, global monkeypatch,
    rewritten bytecode or copied circuit-building algorithm. Its final
    bundle.validate() is a no-op ONLY during this opted-out construction.
    Return a normal native bundle whose explicit validate() still works.
    This narrow H5 binding must be re-audited on dependency upgrades.
    """
    build = FunctionType(_H5_BUILD.__code__,
                         dict(_H5_BUILD.__globals__, FactoryCircuitBundle=_ConstructionBundle),
                         _H5_BUILD.__name__, _H5_BUILD.__defaults__, _H5_BUILD.__closure__)
    result = build(builder)
    return FactoryCircuitBundle(**{f.name: getattr(result, f.name) for f in fields(FactoryCircuitBundle)})


def compile_local_factory(point, *, seed, create_codecapacity_dem=True,
                          skip_circuit_validation=False):
    """Fresh native physical factory with opt-out validation and packed frames."""
    if type(skip_circuit_validation) is not bool or type(create_codecapacity_dem) is not bool:
        raise ValueError("factory validation/prior options must be bool")
    if seed is not None:
        native._validate_shot_ids(seed, 1)
        seed = int(seed)
    noise_options = {} if point.noise_model is None else {"noise_model": point.noise_model}
    builder = FactoryCircuitBuilder(
        RotatedSurfaceCodeAdapter(point.d), PreparationPlan(point.r_0, point.r_plus),
        point.p, T_tel=point.T_tel, **noise_options,
    )
    bundle = (_build_without_full_validation(builder) if skip_circuit_validation else builder.build())
    if _sha(str(bundle.circuit)) != bundle.metadata["circuit_sha256"]:
        raise ValueError("factory circuit changed since its metadata hash was built")
    decoder = _LocalFactoryDecoder(bundle, create_codecapacity_dem=create_codecapacity_dem)
    metadata = bundle.metadata
    key = native.FactoryCacheKey(
        _sha(repr(bundle.code)), bundle.code.distance, metadata["physical_error"], metadata["noise"],
        bundle.preparation.r_0, bundle.preparation.r_plus, len(bundle.stages), metadata["circuit_sha256"],
        metadata["frame_convention"], metadata["preparation_prior"], metadata["terminal_label_convention"], seed,
        decoder_policy=POLICY if create_codecapacity_dem else "factory_causal_hamming_v1",
        gap_policy=("surface_two_boundary_module_local_stim_v1" if create_codecapacity_dem
                    else "surface_two_boundary_hamming_v1"),
        create_codecapacity_dem=create_codecapacity_dem,
        projected_prior_sha256=tuple(p.configuration_sha256 for p in decoder.projected_priors),
        noise_model_sha256=metadata.get("noise_model_sha256", ""),
    )
    # Keep the physical circuit independent of the caller's returned bundle.
    circuit = bundle.circuit.copy()
    return bundle, native.CompiledFactory(key, circuit, decoder, native._compile_sampler(circuit, seed))
