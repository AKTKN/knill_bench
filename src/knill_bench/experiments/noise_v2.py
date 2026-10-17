"""Strict factory-only YAML boundary for Hex's immutable noise configuration.

Hex owns channel mathematics and physical construction. This module validates
YAML structure/types and translates it to the native object, without circuits.
"""

CUSTOM_KIND_ERROR = "Custom noise is currently supported only for kind=logical_zero_factory."


def noise_as_dict(model):
    parameters = model.as_dict()
    return dict(model="custom",
                multipliers={k: parameters[k] for k in
                             ("one_qubit", "two_qubit", "idle", "measurement", "reset")},
                idle_windows={k: parameters[k] for k in
                              ("post_cnot_control", "during_plus_preparation")})


def validate_noise(kind, name, model, *, p=None, r_plus=None):
    if name == "hex_uniform" and model is None:
        return
    if name == "custom":
        if kind != "logical_zero_factory":
            raise ValueError(CUSTOM_KIND_ERROR)
        from hex_qec.circuit_generation import FactoryNoiseModel
        if not isinstance(model, FactoryNoiseModel):
            raise ValueError("custom noise requires a validated Hex FactoryNoiseModel")
        if p is not None:
            model.operation_probabilities(p)
            model.idle_probabilities(p, r_plus)
        return
    raise ValueError("noise must be hex_uniform or a custom noise mapping")


def parse_noise(value, kind):
    from .config_v2 import _mapping, _number

    if isinstance(value, str) and value == "hex_uniform":
        return value, None
    if isinstance(value, dict) and kind != "logical_zero_factory":
        raise ValueError(CUSTOM_KIND_ERROR)
    _mapping(value, {"model", "multipliers", "idle_windows"}, "noise")
    if value.get("model") != "custom":
        raise ValueError("noise.model must be custom (legacy noise uses scalar hex_uniform)")

    def numbers(raw, allowed, where):
        _mapping(raw, allowed, where)
        result = {k: _number(v, f"{where}.{k}") for k, v in raw.items()}
        if any(v < 0 for v in result.values()):
            raise ValueError(f"{where} values must be nonnegative")
        return result

    multipliers = numbers(value.get("multipliers", {}),
                          {"one_qubit", "two_qubit", "idle", "measurement", "reset"},
                          "noise.multipliers")
    windows = value.get("idle_windows", {})
    _mapping(windows, {"post_cnot_control", "during_plus_preparation"}, "noise.idle_windows")
    post = numbers(windows.get("post_cnot_control", {}), {"duration", "rate_multiplier"},
                   "noise.idle_windows.post_cnot_control")
    prep = windows.get("during_plus_preparation", {})
    where = "noise.idle_windows.during_plus_preparation"
    _mapping(prep, {"enabled", "se_round_duration", "rate_multiplier"}, where)
    enabled = prep.get("enabled", False)
    if type(enabled) is not bool:
        raise ValueError(f"{where}.enabled must be bool")
    prep = numbers({k: v for k, v in prep.items() if k != "enabled"},
                   {"se_round_duration", "rate_multiplier"}, where)
    from hex_qec.circuit_generation import FactoryNoiseModel, IdleWindow, PlusPreparationIdle
    return "custom", FactoryNoiseModel(**multipliers, post_cnot_control=IdleWindow(**post),
                                       during_plus_preparation=PlusPreparationIdle(enabled=enabled, **prep))


def execution_noise(point):
    """Compact expected noise provenance; no circuit/decoder construction.

    The native physical_noise_sha256 convention is audited at the pinned Hex
    revision. It hashes p plus canonical native parameters, not circuit text.
    """
    if point.noise_model is None:
        return {}
    import hashlib
    from .config_v2 import canonical

    model = point.noise_model
    text = canonical(model.as_dict())
    post, prep = model.idle_probabilities(point.p, point.r_plus)
    return dict(
        noise="factory_operation_specific_v1", noise_parameters=noise_as_dict(model),
        noise_model_json=text, noise_model_sha256=model.configuration_sha256,
        physical_noise_sha256=hashlib.sha256(repr((point.p, text)).encode()).hexdigest(),
        noise_operation_probabilities=model.operation_probabilities(point.p),
        post_cnot_control_idle_probability=post, storage_idle_probability=prep,
        idle_window_durations=dict(post_cnot_control=model.post_cnot_control.duration,
            during_plus_preparation=(point.r_plus*model.during_plus_preparation.se_round_duration
                                     if model.during_plus_preparation.enabled else 0.)),
        idle_window_application_counts=dict(post_cnot_control=point.T_tel if post else 0,
            during_plus_preparation=point.T_tel-1 if prep else 0),
    )


def validate_noise_execution(point, execution, *, create_codecapacity_dem):
    """Cross-check custom saved provenance before publication/resume/analysis."""
    if point.noise_model is None:
        return
    expected = execution_noise(point)
    policy = "module_local_stim_dem" if create_codecapacity_dem else "hex_legacy_hamming"
    if (not isinstance(execution, dict)
            or any(execution.get(k) != v for k, v in expected.items())
            or execution.get("prior_policy") != policy
            or execution.get("teleportation_readout_error") != expected["noise_operation_probabilities"]["measurement"]):
        raise ValueError("saved custom noise execution metadata changed or is missing")
    if execution.get("prior_policy") == "module_local_stim_dem":
        if (execution.get("post_cnot_control_idle_in_local_prior") is not True
                or execution.get("storage_idle_errors_in_local_prior") is not False
                or execution.get("preparation_residual_errors_in_prior") is not False
                or execution.get("earlier_stage_residual_errors_in_prior") is not False
                or execution.get("prior_scope") != "post_preparation_native_coupling_and_noisy_readout"):
            raise ValueError("saved custom noise local-prior scope changed")
