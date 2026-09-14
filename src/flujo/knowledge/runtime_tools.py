"""Resolve optional local runtimes without installing or executing them.

The MAK machine keeps Blender outside ``PATH`` on purpose.  Consumers must
still agree on the same executable, otherwise one audit says "missing" while
the render tools use a real binary.  This module only checks paths; it never
starts a process or changes the environment.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def resolve_blender(repo_root: str | Path | None = None) -> Path | None:
    """Return the first executable Blender candidate visible to this MAK.

    ``repo_root`` is used to locate the sibling ``/home/mak/blender`` install
    while keeping tests and other checkouts isolated.  The explicit env var
    remains the highest-priority override and is never printed by this helper.
    """
    candidates: list[Path] = []
    # BLENDER_EXE is the name MAPA.md documents. MAK_BLENDER was used by
    # cultura/mak_curatoria/diagnostico_proyectos.py and by nothing else, so
    # anyone who set the documented variable got Blender resolved here and NOT
    # there. Both are honoured in both places; the documented one wins.
    configured = (os.environ.get("BLENDER_EXE", "").strip()
                  or os.environ.get("MAK_BLENDER", "").strip())
    if configured:
        candidates.append(Path(configured).expanduser())
    found = shutil.which("blender")
    if found:
        candidates.append(Path(found))
    if repo_root is not None:
        root = Path(repo_root).expanduser().resolve()
        home_root = root.parent if root.name == "flujo" else root
        candidates.extend((
            home_root / "blender" / "blender",
            home_root / "blender-4.5.3-viejo" / "blender",
        ))
    else:
        candidates.extend((
            Path("/home/mak/blender/blender"),
            Path("/home/mak/blender-4.5.3-viejo/blender"),
        ))
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()
        except OSError:
            continue
    return None


def declared_node_minimum(repo_root: str | Path | None = None) -> str:
    """Return the Node minimum the web surface declares, or an empty string.

    The requirement has exactly one home, ``web/package.json``; reading it here
    keeps a second copy of the number from drifting away from the build.
    """
    root = Path(repo_root).expanduser() if repo_root is not None else Path("/home/mak/flujo")
    manifest = root / "web" / "package.json"
    try:
        import json

        engines = json.loads(manifest.read_text(encoding="utf-8")).get("engines") or {}
    except (OSError, ValueError):
        return ""
    return str(engines.get("node") or "").strip()


def node_candidates(repo_root: str | Path | None = None) -> list[Path]:
    """Every Node binary this MAK can reach, most explicit first.

    Measured on 2026-08-21: ``PATH`` resolves Node 18.20.4 while the web
    surface declares ``>=20.19.0``, and Node 20.20.2 and 24.18.0 are installed
    under the local GitHub Actions runner. A resolver that only looked at
    ``PATH`` reported "node available" for a version the build warns about, so
    the candidates below include the installs that actually satisfy it. Later
    entries are newer on purpose: a caller that needs the declared minimum can
    walk this list instead of guessing a path.

    Paths only. This never runs ``node`` and never changes the environment.
    """
    root = Path(repo_root).expanduser().resolve() if repo_root is not None else Path("/home/mak/flujo")
    home_root = root.parent if root.name == "flujo" else root
    candidates: list[Path] = []
    configured = os.environ.get("NODE_EXE", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    found = shutil.which("node")
    if found:
        candidates.append(Path(found))
    candidates.extend((
        home_root / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node",
        home_root / "actions-runner" / "externals" / "node24" / "bin" / "node",
        home_root / "actions-runner" / "externals" / "node20" / "bin" / "node",
    ))
    resolved: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                resolved.append(candidate)
        except OSError:
            continue
    return resolved


def resolve_node(repo_root: str | Path | None = None) -> Path | None:
    """Return the first reachable Node binary, or ``None``."""
    found = node_candidates(repo_root)
    return found[0] if found else None


def resolve_console_script(name: str, *, env_var: str | None = None) -> Path | None:
    """Find a console script that a declared Python dependency installs.

    ``shutil.which`` alone is not enough here. pip puts console scripts next to
    the interpreter that installed them -- ``.venv/bin/<name>`` -- and that
    directory is NOT on ``PATH`` unless the venv is activated. Running the suite
    as ``./.venv/bin/python -m pytest`` therefore reported a declared dependency
    as missing.

    Measured on 2026-08-21: ``vpype`` is declared in ``pyproject.toml`` under the
    ``dev`` extra, ``.venv/bin/vpype`` exists and ``import vpype`` works, yet
    ``laser.verificar()`` returned ``{"vpype": False}`` and
    ``test_estado_reporta_la_cadena_real`` skipped with "vpype not installed".
    A gate that never fires where the dependency IS installed is not a gate.

    Order: explicit env override, then PATH, then the running interpreter's own
    bin directory. Paths only -- nothing is executed here.

    One trap measured while writing this: ``Path(sys.executable).resolve()``
    walks OUT of the venv, because ``.venv/bin/python`` is a symlink to
    ``/usr/bin/python3``. The unresolved dirname is the one that holds the
    console scripts.
    """
    candidates: list[Path] = []
    if env_var:
        configured = os.environ.get(env_var, "").strip()
        if configured:
            candidates.append(Path(configured).expanduser())
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    # NOT resolve(): .venv/bin/python is a symlink to /usr/bin/python3, so
    # resolving it walks out of the venv and the console script is missed. The
    # unresolved dirname is the venv bin; sys.prefix covers the case where the
    # interpreter was invoked through another link.
    for base in (Path(sys.executable).parent, Path(sys.prefix) / "bin",
                 Path(sys.prefix) / "Scripts"):
        candidates.append(base / name)
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                # Keep the spelling of the interpreter's own bin directory.
                # In this MAK layout ``.venv`` is a compatibility symlink to
                # the archived environment; resolving it would hide the
                # operational path callers were asked to diagnose.
                if candidate.parent in {
                    Path(sys.executable).parent,
                    Path(sys.prefix) / "bin",
                    Path(sys.prefix) / "Scripts",
                }:
                    return candidate
                return candidate.resolve()
        except OSError:
            continue
    return None
