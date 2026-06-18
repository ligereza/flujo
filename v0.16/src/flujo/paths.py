from pathlib import Path
import os

def repo_root() -> Path:
    """Encuentra la raíz del repo subiendo hasta encontrar pyproject.toml o .git"""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists() or (parent / "scripts" / "flujo.py").exists():
            if "site-packages" in str(parent):
                continue
            return parent
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "tools" / "flyer_eventos").exists():
            return parent
    return cwd

def flyer_base() -> Path:
    env = os.getenv("FLYER_BASE")
    if env:
        return Path(env)
    return repo_root() / "projects" / "flyer_eventos"

def inbox_dir() -> Path:
    return repo_root() / "inbox"

def jobs_dir() -> Path:
    return repo_root() / "jobs"

def piezas_base() -> Path:
    return repo_root() / "projects" / "piezas_vectoriales"

def context_dir() -> Path:
    return repo_root() / "context"

def data_dir() -> Path:
    p = repo_root() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p
