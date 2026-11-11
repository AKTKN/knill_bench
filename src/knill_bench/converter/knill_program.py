"""Consumer-authored LSTIM and public typed preparation noise policies."""

from .se_memory import exact_stim_text

IDEAL_POST = "ideal_post_se_depolarizing"
NOISY_D = "noisy_d_rounds"


def knill_source(point):
    if point.kind != "converter_knill_memory" or point.resource_preparation not in {IDEAL_POST, NOISY_D}:
        raise ValueError("Knill memory requires a named Phase 2 preparation regime")
    if point.r_0 != point.d or point.r_plus != point.d:
        raise ValueError("Phase 2 Knill resources require exactly d preparation rounds")
    ideal = point.resource_preparation == IDEAL_POST
    if point.input_preparation != ("ideal" if ideal else "noisy"):
        raise ValueError("input preparation disagrees with the Knill regime")
    lines = ["FORMAT(1)", f"CODE sc ROTATED_SURFACE({point.d})",
             *(f"PATCH P{i} sc index={i}" for i in range(3)), "BIND D P0",
             f"INIT_Z[initial]({1 if ideal else point.d}) D" + (" noise=ideal" if ideal else "")]
    # Authored (current data, fresh A, surviving B) rotation; never rebind D.
    rotation = ((0, 1, 2), (2, 0, 1), (1, 2, 0))
    for cycle in range(point.T_tel):
        _, a, b = rotation[cycle % 3]
        lines.extend((f"BIND A{cycle} P{a}", f"BIND B{cycle} P{b}",
                      f"KNILL_EC[ec{cycle}]({point.d}) D A{cycle} B{cycle}"))
        if point.post_rounds:
            lines.append(f"SE[post{cycle}]({point.post_rounds}) D")
    lines.append("MZ[final] D")
    return "\n".join(lines) + "\n"


def compile_knill(point):
    from logical_to_stim_converter import NoiseModel, PostInitializationNoise, ResourcePreparationNoise, parse_logical_circuit

    source = knill_source(point)
    program = parse_logical_circuit(source)
    uniform = NoiseModel.uniform_depolarizing(point.p)
    discovered = None
    if point.resource_preparation == IDEAL_POST:
        # Compile lifecycle first; do not guess an epoch from patch/round numbers.
        lifecycle = program.compile(noise_model=NoiseModel())
        initial, = (p for p in lifecycle.preparations if p.logical_id == "D")
        use, = (u for u in lifecycle.block_uses if u.use_id == initial.block_use_id)
        if use.reset_module_id != initial.module_id:
            raise ValueError("input preparation is not the reset of the discovered physical use")
        discovered = initial.block_use_id
        noise = NoiseModel(uniform.default,
            resource_preparation=ResourcePreparationNoise(True, point.p*point.p_st_multiplier),
            post_initialization=(PostInitializationNoise("initial", discovered, point.p),))
        del lifecycle
    else:
        noise = uniform
    compiled = program.compile(noise_model=noise)
    compiled.validate_metadata()
    if discovered is not None:
        boundary, = compiled.post_initialization_boundaries
        if boundary.block_use_id != discovered or boundary.operation_id != "initial" or boundary.probability != point.p:
            raise ValueError("post-initialization policy resolved to a different use")
        if any(b.block_use_id == discovered for b in compiled.resource_preparation_boundaries):
            raise ValueError("input and M9 policies overlap a physical use")
    elif compiled.post_initialization_boundaries or compiled.resource_preparation_boundaries:
        raise ValueError("noisy_d_rounds must not insert additional preparation channels")
    return source, compiled, exact_stim_text(compiled.circuit)
