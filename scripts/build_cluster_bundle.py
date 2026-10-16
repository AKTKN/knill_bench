#!/usr/bin/env python3
"""Build resource-complete, provenance-tagged wheels without editing forks."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def source_hash(files):
    digest = hashlib.sha256()
    # Match runtime pathlib ordering, including a.py versus a/... siblings.
    for name, data in sorted(files, key=lambda item: Path(item[0])):
        relative = name.encode()
        digest.update(len(relative).to_bytes(8, "little") + relative)
        digest.update(len(data).to_bytes(8, "little") + data)
    return digest.hexdigest()


def build_project(spec, output):
    root = ROOT / spec["path"]
    commit = git(root, "rev-parse", "HEAD")
    dirty = bool(git(root, "status", "--porcelain"))
    if "revision" in spec and (commit != spec["revision"] or dirty):
        raise ValueError(f"preserving {root}: require clean pinned {spec['revision']}, found {commit}, dirty={dirty}")
    module = spec["module"]
    with tempfile.TemporaryDirectory(prefix="knill-package-") as directory:
        stage = Path(directory)
        package = stage / spec["package-dir"]
        shutil.copytree(root / spec["package-dir"], package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
        for name in ("pyproject.toml", "README.md", "LICENSE", "LICENCE", "LICENSE.txt"):
            if (root / name).is_file():
                shutil.copy2(root / name, stage / name)
        scientific = [(str(p.relative_to(package)), p.read_bytes()) for p in package.rglob("*")
                      if p.is_file() and p.suffix in {".py", ".mtx"}]
        info = dict(format_version=1, module=module, commit=commit,
                    branch=git(root, "branch", "--show-current"), dirty=dirty,
                    source_sha256=source_hash(scientific), origin_url=git(root, "remote", "get-url", "origin"))
        if module == "hex_qec":
            info["verified_ancestor"] = spec["revision"]
        (package / "_build_info.json").write_text(json.dumps(info, sort_keys=True, indent=2)+"\n")
        project = stage / "pyproject.toml"
        text = project.read_text()
        if module == "hex_qec":
            # H5's original wheel omits every .mtx. Add packaging configuration
            # only in this staging directory; scientific source stays exact.
            text += ('\n[tool.setuptools.packages.find]\nwhere = ["src"]\n'
                     'include = ["hex_qec*"]\nnamespaces = false\n')
        if module != "knill_bench":
            patterns = ["_build_info.json"]
            if module == "hex_qec":
                patterns.append("circuit_generation/parity_check_matrices/*/*.mtx")
            text += f"\n[tool.setuptools.package-data]\n{module} = {json.dumps(patterns)}\n"
        project.write_text(text)
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(output), str(stage)], check=True)
        wheel = next(output.glob(spec["distribution"].replace("-", "_")+"-*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            prefix = module+"/"
            contents = [(name[len(prefix):], archive.read(name)) for name in archive.namelist()
                        if name.startswith(prefix) and Path(name).suffix in {".py", ".mtx"}]
            if source_hash(contents) != info["source_sha256"]:
                raise ValueError(f"wheel omitted or changed Python/matrix resources: {wheel}")
        return dict(info, wheel=wheel.name, matrix_resources=sum(name.endswith(".mtx") for name, _ in contents))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "results/cluster_bundle"))
    parser.add_argument("--download-deps", action="store_true", help="Include binary pip dependencies for this Python/platform")
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    wheels = output / "wheels"
    wheels.mkdir()
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    specs = list(config["tool"]["knill-bench"]["sources"].values())
    specs.append(dict(distribution="knill-bench", module="knill_bench", path=".", **{"package-dir": "src/knill_bench"}))
    projects = [build_project(spec, wheels) for spec in specs]
    for name in ("requirements.lock", "requirements-research.lock", "environments.yaml",
                 "conda-linux-64.explicit.txt", "GETTING_STARTED.md", "README.md", "TEST.md"):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / "configs", output / "configs")
    shutil.copytree(ROOT / "docs", output / "docs")
    if args.download_deps:
        # Some pinned packages (notably sinter 1.16) are published as sdists.
        # Build their wheels here, where build tools/network are available;
        # the target installs only the resulting wheels, never an sdist.
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheels),
                        "-r", str(ROOT / "requirements.lock"), "-r", str(ROOT / "requirements-research.lock")], check=True)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wheels.glob("*.whl"))}
    manifest = dict(bundle_version=1, python=sys.version, platform=sys.platform, projects=projects,
                    binary_dependencies_included=args.download_deps, wheels_sha256=hashes)
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2)+"\n")
    # The target already has Conda Python 3.12.15 and pip. No Git or source
    # checkout is required. SHA verification precedes any pip installation.
    installer = '''#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
import subprocess, sys
root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text())
for name, expected in manifest["wheels_sha256"].items():
    if hashlib.sha256((root / "wheels" / name).read_bytes()).hexdigest() != expected:
        raise SystemExit("wheel checksum mismatch: " + name)
options = ["--no-index", "--find-links", str(root / "wheels")] if manifest["binary_dependencies_included"] else []
subprocess.run([sys.executable, "-m", "pip", "install", *options, "-r", str(root / "requirements.lock"),
                "-r", str(root / "requirements-research.lock")], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps",
                *[str(root / "wheels" / p["wheel"]) for p in manifest["projects"]]], check=True)
subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
'''
    (output / "install.py").write_text(installer)
    print(output)


if __name__ == "__main__":
    main()
