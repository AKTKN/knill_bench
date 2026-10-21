# Dependencies and reproducible installation

## Current Conda/cluster workflow

The user requested migration to **knill_system**, replacing the project .venv.
`bash scripts/bootstrap.sh` now creates/updates environments.yaml and installs
the pinned forks/bench editable. All numerical versions in requirements.lock
are preserved; requirements-research.lock adds pinned notebook, analysis,
plotting, parallel-work and build tools. pyproject.toml supplies research/dev
extras and exact fork-source records under tool.knill-bench.sources. Numeric
wheel dependency metadata enables offline resolution; runtime provenance still
rejects an unverified Hex installation. See [the cluster guide](cluster_setup.md).

The cluster builder stages copies without modifying dependency repositories,
includes Hex's 72 .mtx resources, tags four wheels with source commit/hash/
dirty information and verifies Python/matrix hashes after building. Installed
v1/v2 provenance accepts those verified wheel manifests without Git. The
separate numerical circuit/decoder implementations are unchanged.

## Historical source-checkout setup

The following records the original v1/B0 setup; current commands use Conda.

The workspace originally contained only the implementation prompt. Existing clean checkouts were found in `../temporal_confidence/external_libs`. Their working branches were preserved. Three local `knill-bench-integration` worktrees were created under this project's `external/` directory.

| Package | Upstream | User fork | Integration revision |
|---|---|---|---|
| Hex | https://github.com/ewanmurphy/Hex | https://github.com/AKTKN/Hex | `86c9495094801012b9912bd41935ae48b08d8f92` (`auxiliary-system`, HEX-N2) |
| lomatching | https://github.com/MarcSerraPeralta/lomatching | https://github.com/AKTKN/lomatching | `b55a7a65969a106a547622287b620f0da2cb5e39` |
| surface-sim | https://github.com/MarcSerraPeralta/surface-sim | https://github.com/AKTKN/surface-sim | `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` |

The latter two user forks were created as requested on 2026-09-21. Existing origin/upstream remotes were preserved; `knill-bench-fork` points to each user fork. Local integration branches are not pushed. No dependency source changes were necessary. In particular the user's newer `hex-parallel` worktree remains on its original branch and is not used as the implementation base.

`bash scripts/bootstrap.sh` checks exact base revisions, creates missing integration checkouts, installs locked dependencies and the three editable checkouts into `.venv`, then installs this package editable with `--no-deps`. That last step avoids a resolver conflict between exact Git URL metadata for reproducible non-development installation and the deliberately selected editable paths. The script never resets an existing checkout. `KNILL_LOMATCHING_URL` and `KNILL_SURFACE_SIM_URL` can override clone URLs explicitly. CLI commands require the research dependencies to import from Git checkouts, and save the actual module paths.

`requirements.lock` pins the installed transitive environment. Direct requirements include Python 3.12, Stim 1.16.0, PyMatching 2.4.0, ldpc 2.4.1, NumPy 2.5.3, SciPy 1.18.1, PyYAML 6.0.3, PyArrow 25.0.1, and Matplotlib 3.11.2. Matplotlib is justified by required analysis plots and is already a dependency of the research packages. Pytest is a development dependency. Exact Git URLs in `pyproject.toml` prevent silently substituting PyPI Hex in non-development installations; the validated research workflow is the editable bootstrap, not a wheel-only deployment.

Each run stores distribution versions, imported paths, branches, SHAs, dirty status, Python/platform/CPU/thread information, source hash, invocation, and a package-source archive. Dependency dirty tracked patches and untracked source/config archives are captured when needed. The environment allowlist excludes credentials and unrelated environment variables. Native thread limits are set before scientific imports and inherited by workers. An explicit conflicting user setting is rejected rather than overwritten.

Source APIs inspected: Hex's circuit_generation, module_generation, modularised_circuit, decoder adapters, and fixed Knill entry point; lomatching's decoder/util implementations; surface-sim's logical schedule and reference example; installed BP-LSD's decode, convergence, iteration and statistics interfaces. The designated Hex revision exposes its experiment runner through the separate Experiments project. This package uses an independent bounded spawn pool instead of assuming a Hex internal pool exists.

## Licenses and references

Dependency repositories retain their license files unchanged. Copies are in `docs/licenses/` for review. No third-party paper text is redistributed.

* Murphy, Sahu, Vasmer, [Simplified circuit-level decoding using Knill error correction](https://arxiv.org/abs/2603.05320), and the [Hex source](https://github.com/AKTKN/Hex).
* Serra-Peralta, Shaw, Terhal, [Decoding across transversal Clifford gates in the surface code](https://arxiv.org/abs/2505.13599), PRX Quantum 7, 010335 (2026), DOI [10.1103/sk5y-25b1](https://doi.org/10.1103/sk5y-25b1). The local published PDF was inspected; later arXiv revisions are not assumed identical.
* Cain et al., [Fast correlated decoding of transversal logical algorithms](https://arxiv.org/abs/2505.13587). The local PDF is the June 2025 version.
* Zhou et al., [Low-Overhead Transversal Fault Tolerance for Universal Quantum Computation](https://arxiv.org/abs/2406.17653), originally titled Algorithmic Fault Tolerance for Fast Quantum Computing.
* [BP-LSD API documentation](https://software.roffe.eu/ldpc/ldpc/bplsd_decoder.html); actual installed API is checked by the reference command.
* Gidney, Stim; Higgott and Gidney, PyMatching; Roffe et al., LDPC/BP-LSD. Consult each installed project's citation guidance for publications using generated data.

The papers motivate the comparison and decoding choices; they do not certify the particular circuit, detector projection, approximate decoder, or schedule implemented here.


## Auxiliary-system B0 dependency update

The earlier worktree setup is historical. The active Hex checkout completed
H0-H5 on its own auxiliary-system branch; bench now pins H5 `4278d29` in
pyproject.toml and bootstrap.sh. Its historical hex-adaptive base remains
5de58f2f80791054411ad3c0885a4fe3671ed56a. B0 modifies no dependency source,
version or working branch. Both other dependency refs and requirements.lock
remain unchanged. The bootstrap still refuses to reset an existing checkout.

B0 validation uses an isolated `.venv` containing the exact runtime lock,
plus the three editable forks and bench. `pip check` passes. Initial attempts
to share the base Anaconda environment exposed old setuptools/packaging,
missing galois and NumPy-1.x/LOM incompatibility. Those setup problems were
resolved within `.venv`; no compatibility shim or dependency-source patch was
introduced. [TEST.md](../TEST.md) records commands and versions.

V2 stores a compact allowlist of relevant dependency versions and actual bench/
Hex source provenance in one metadata file. It does not reuse v1 environment
archives, source tarballs or extra tables; see [the B0 guide](auxiliary_v2.md).




## BENCH-N1 factory-noise dependency audit

The user-authorized integration updates only the bench pin/bootstrap/API check
to existing Hex HEX-N2 86c9495094801012b9912bd41935ae48b08d8f92. This is a
clean auxiliary-system descendant of H5, supplying frozen FactoryNoiseModel,
IdleWindow/PlusPreparationIdle and optional builder noise_model. Uniform
circuits/decoding were retained in Hex with golden tests. Private builder type
binding and decoder slots retain their interfaces; bench regression gates
re-audit them. Wheel manifests now require the new pinned revision/ancestor
marker and resource hashes. Numeric locks, package versions, other fork refs
and all dependency source checkouts are unchanged by bench. Old saved data
remain analyzable; strict source/environment rules require fresh runs for
simulation after upgrading. Bootstrap still refuses to reset any checkout.

Current Knill-noise dependency pin: Hex HEX-K1 `8fa2200315cc4feaccf341a461f91739233de08a` on
`auxiliary-system`, descending from HEX-N2/H5. This supersedes the earlier
HEX-N2 pin. Bootstrap/bundles require that clean exact checkout; runtime
checks the new native policy and fixed Knill API, with strict source/resource
hashes for installed wheels.
