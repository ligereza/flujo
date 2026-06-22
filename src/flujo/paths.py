from pathlib import Path
import os
import sys
from functools import lru_cache


def is_packaged() -> bool:
    """True when running inside a PyInstaller (or similar) standalone bundle .exe.
    Also honors FLUJO_PACKAGED=1 (set by desktop launcher for robustness).
    """
    if os.environ.get("FLUJO_PACKAGED") == "1":
        return True
    return bool(getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None))


def _is_frozen() -> bool:
    """Internal alias for backwards in module."""
    return is_packaged()


def _frozen_base() -> Path | None:
    """Return the base dir where --add-data files live (context/, svg/, projects/...).
    For onefile: inside temp _MEIPASS (assets only).
    For onedir: next to the .exe .
    """
    if not _is_frozen():
        return None
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        return Path(mp)
    # onedir case or direct
    return Path(sys.executable).parent


def _exe_dir() -> Path:
    """Directory containing the running .exe (persistent, even for onefile)."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path.cwd()


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Encuentra la raíz del repo subiendo hasta encontrar pyproject.toml o .git.
    En modo empaquetado (PyInstaller), devuelve el base de assets bundled.
    """
    fb = _frozen_base()
    if fb is not None:
        return fb
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


def asset_root() -> Path:
    """Root for read-only bundled assets (context/, svg/, projects/flujo for brand).
    Falls back to repo_root in dev.
    """
    fb = _frozen_base()
    if fb is not None:
        return fb
    return repo_root()


def workspace_root() -> Path:
    """Writable root for user data (jobs/, data/, inbox etc).
    In packaged .exe: always next to the .exe (flujo_workspace sibling) so it survives onefile extracts.
    Dev: falls back to repo root.
    Set FLUJO_WORKSPACE_ROOT=/path to override.
    """
    env = os.getenv("FLUJO_WORKSPACE_ROOT")
    if env:
        p = Path(env).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    if _is_frozen():
        p = _exe_dir() / "flujo_workspace"
        p.mkdir(parents=True, exist_ok=True)
        return p
    return repo_root()

def flyer_base() -> Path:
    env = os.getenv("FLYER_BASE")
    if env:
        return Path(env)
    # In packaged prefer workspace sibling for user flyers too
    if _is_frozen():
        return workspace_root() / "projects" / "flyer_eventos"
    return repo_root() / "projects" / "flyer_eventos"

def inbox_dir() -> Path:
    return workspace_root() / "inbox"

def jobs_dir() -> Path:
    return workspace_root() / "jobs"

def piezas_base() -> Path:
    # user render projects go to workspace in packaged
    if _is_frozen():
        p = workspace_root() / "projects" / "piezas_vectoriales"
        p.mkdir(parents=True, exist_ok=True)
        return p
    return repo_root() / "projects" / "piezas_vectoriales"

def plano_base() -> Path:
    if _is_frozen():
        p = workspace_root() / "projects" / "plano"
        p.mkdir(parents=True, exist_ok=True)
        return p
    return repo_root() / "projects" / "plano"

def context_dir() -> Path:
    """Always asset for HTML/JS/visualizers (bundled or source)."""
    return asset_root() / "context"

def data_dir() -> Path:
    p = workspace_root() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def datadrops_dir() -> Path:
    """Writable user dir for datadrops (inverse airdrop): uploaded real photos of finished work.
    Date-subdir structure inside. Used by hub UI + future AI review for styles/patterns.
    """
    p = workspace_root() / "datadrops"
    p.mkdir(parents=True, exist_ok=True)
    return p
