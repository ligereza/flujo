"""Motor de actualizaciones (airdrop) — sin carpeta de versión.

Soltar los archivos a aplicar dentro de `_airdrop/` respetando la estructura
del repo (ej. `_airdrop/src/flujo/cli.py`). Luego `flujo airdrop apply` los
copia a su destino, crea backup, y dispara checkpoint + push automáticamente.
"""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .paths import repo_root


def get_airdrop_dir() -> Path:
    return repo_root() / "_airdrop"


def get_backup_base_dir() -> Path:
    return repo_root() / "_airdrop_backups"


# archivos que se ignoran al escanear _airdrop/
_IGNORE = {".gitkeep", ".DS_Store"}


def scan_airdrop() -> List[Dict]:
    """Escanea `_airdrop/` y devuelve la lista de cambios a aplicar.

    Cada cambio mapea un archivo de `_airdrop/` a su destino en la raíz del repo
    según su ruta relativa.
    """
    base = get_airdrop_dir()
    if not base.exists():
        return []
    changes: List[Dict] = []
    for src in sorted(base.rglob("*")):
        if src.is_dir():
            continue
        if src.name in _IGNORE or src.name.startswith("."):
            continue
        rel = src.relative_to(base)
        dest = repo_root() / rel
        status = "REPLACE" if dest.exists() else "NEW"
        # rel.as_posix() => siempre con "/" (consistente en Windows y Linux/macOS)
        changes.append({"src": src, "dest": dest, "rel": rel.as_posix(), "status": status})
    return changes


def list_airdrop_files() -> List[str]:
    """Lista las rutas relativas pendientes de aplicar en `_airdrop/`."""
    return [c["rel"] for c in scan_airdrop()]


def apply_airdrop(dry_run: bool = False) -> List[Dict]:
    """Aplica todos los archivos de `_airdrop/` al repo.

    1. Crea backup de los archivos existentes (REPLACE) en `_airdrop_backups/`.
    2. Copia cada archivo a su destino (creando carpetas si hace falta).
    3. Da permiso de ejecución a los `.sh`.
    """
    changes = scan_airdrop()
    if not changes or dry_run:
        return changes

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = get_backup_base_dir() / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for c in changes:
        src, dest, rel = c["src"], c["dest"], c["rel"]
        if c["status"] == "REPLACE":
            bpath = backup_dir / rel
            bpath.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, bpath)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if dest.suffix == ".sh":
            dest.chmod(dest.stat().st_mode | 0o111)
    return changes


def run_auto_checkpoint(message: Optional[str] = None) -> bool:
    """Ejecuta `scripts/checkpoint.sh` (genera checkpoint + commit + push)."""
    script = repo_root() / "scripts" / "checkpoint.sh"
    if not script.exists():
        return False
    msg = message or f"airdrop aplicado {datetime.now().strftime('%Y-%m-%d_%H-%M')}"
    try:
        subprocess.run(
            ["bash", str(script), msg],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(e.stderr or e.stdout)
        return False


def rollback_last() -> Optional[Path]:
    """Restaura el último backup desde `_airdrop_backups/`."""
    base = get_backup_base_dir()
    if not base.exists():
        return None
    backups = sorted([d for d in base.iterdir() if d.is_dir()], reverse=True)
    if not backups:
        return None
    last = backups[0]
    for src in last.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(last)
        dest = repo_root() / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if dest.suffix == ".sh":
            dest.chmod(dest.stat().st_mode | 0o111)
    return last
