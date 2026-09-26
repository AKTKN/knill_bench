# Dependencies and reproducible installation

The workspace originally contained only the implementation prompt. Existing clean checkouts were found in `../temporal_confidence/external_libs`. Their working branches were preserved. Three local `knill-bench-integration` worktrees were created under this project's `external/` directory.

| Package | Upstream | User fork | Exact base revision |
|---|---|---|---|
| Hex | https://github.com/ewanmurphy/Hex | https://github.com/AKTKN/Hex | `5de58f2f80791054411ad3c0885a4fe3671ed56a` (`hex-adaptive`) |
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
