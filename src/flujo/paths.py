from pathlib import Path

def repo_root() -> Path:
    """Encuentra la raíz del repo subiendo hasta encontrar pyproject.toml o .git"""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists() or (parent / "scripts" / "flujo.py").exists():
            # heurstic: if we're in site-packages, walk up from cwd
            if "site-packages" in str(parent):
                continue
            return parent
    # fallback: cwd, walk up looking for tools/flyer_eventos
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "tools" / "flyer_eventos").exists():
            return parent
    return cwd

import os

def flyer_base() -> Path:
    env = os.getenv("FLYER_BASE")
    if env:
        return Path(env)
    return repo_root() / "projects" / "flyer_eventos"

def inbox_dir() -> Path:
    return repo_root() / "inbox"
