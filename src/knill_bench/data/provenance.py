import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from knill_bench.config import digest
from knill_bench.data.storage import atomic_json


def utc(): return datetime.now(timezone.utc).isoformat()

def sha(text): return hashlib.sha256(text.encode()).hexdigest()

def git(path,*args):
    r=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True)
    return r.stdout.strip() if r.returncode==0 else None


def source_files():
    import knill_bench
    root=Path(knill_bench.__file__).parent
    return root, sorted(root.rglob('*.py'))


def source_hash():
    root,files=source_files()
    return digest({str(p.relative_to(root)):sha(p.read_text()) for p in files})


def environment(run=None):
    packages={x.metadata['Name']:x.version for x in importlib.metadata.distributions()}
    deps=[]
    for name,upstream in [('hex_qec','https://github.com/ewanmurphy/Hex'),('lomatching','https://github.com/MarcSerraPeralta/lomatching'),('surface_sim','https://github.com/MarcSerraPeralta/surface-sim')]:
        module=importlib.import_module(name);path=Path(module.__file__).resolve()
        root=git(path.parent,'rev-parse','--show-toplevel')
        if root is None: raise RuntimeError(f'{name} must import from a development checkout, got {path}')
        status=git(root,'status','--porcelain')
        dep=dict(module=name,import_path=str(path),checkout=root,upstream_url=upstream,
                 origin_url=git(root,'remote','get-url','origin'),branch=git(root,'branch','--show-current'),
                 commit=git(root,'rev-parse','HEAD'),dirty=bool(status))
        dep['fork_url']=dep['origin_url'] if name=='hex_qec' else (git(root,'remote','get-url','knill-bench-fork') or (dep['origin_url'] if 'AKTKN' in dep['origin_url'] else None))
        if status and run:
            patch=git(root,'diff','--binary','HEAD') or ''
            target=Path(run)/'provenance'/f'{name}.patch';target.parent.mkdir(exist_ok=True)
            target.write_text(patch);dep['patch']=str(target.relative_to(run))
            # Only source/config untracked files from the dependency, never environment files.
            untracked=(git(root,'ls-files','--others','--exclude-standard') or '').splitlines()
            with tarfile.open(Path(run)/'provenance'/f'{name}-untracked.tar.gz','w:gz') as tar:
                for f in untracked:
                    if Path(f).suffix in {'.py','.toml','.yaml','.md','.mtx'}: tar.add(Path(root)/f,arcname=f)
        deps.append(dep)
    info=dict(python=sys.version,platform=platform.platform(),machine=platform.machine(),processor=platform.processor(),
              cpu_count=os.cpu_count(),packages=packages,dependencies=deps,source_hash=source_hash(),
              threads={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
              invocation=sys.argv,seed_derivation_version=1)
    if run:
        root,files=source_files();dest=Path(run)/'provenance';dest.mkdir(exist_ok=True)
        with tarfile.open(dest/'knill_bench-source.tar.gz','w:gz') as tar:
            for p in files: tar.add(p,arcname=str(p.relative_to(root.parent)))
        info['source_snapshot']='provenance/knill_bench-source.tar.gz'
    return info


def compatibility(env):
    return digest({k:env[k] for k in ('python','platform','machine','packages','source_hash','dependencies','threads')})
