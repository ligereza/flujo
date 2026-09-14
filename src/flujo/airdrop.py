"""Motor de actualizaciones (airdrop) — sin carpeta de versión.

Soltar los archivos a aplicar dentro de `_airdrop/` respetando la estructura
del repo (ej. `_airdrop/src/flujo/cli.py`). Luego `flujo airdrop apply` los
copia a su destino, crea backup, y dispara checkpoint + push automáticamente.
"""

import hashlib
import hmac
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .paths import repo_root


def get_airdrop_dir() -> Path:
    return repo_root() / "_airdrop"


def get_backup_base_dir() -> Path:
    return repo_root() / "_airdrop_backups"


_MANIFEST_NAME = "_airdrop_manifest.json"
_PROTECTED_TOP_LEVEL_DIRS = {
    "src", "scripts", "tests", "docs", "projects", "jobs", "tools",
    "schemas", "context", ".github",
}


def _write_manifest(backup_dir: Path, changes: List[Dict]) -> None:
    """Guarda lo aplicado para que rollback también revierta archivos NEW."""
    manifest = [
        {"rel": c["rel"], "status": c["status"]}
        for c in changes
    ]
    (backup_dir / _MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_manifest(backup_dir: Path) -> List[Dict]:
    manifest_path = backup_dir / _MANIFEST_NAME
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("rel")]


def _cleanup_empty_parents(path: Path, repo: Path) -> None:
    """Elimina carpetas vacías creadas por archivos NEW, sin borrar raíces del repo."""
    current = path
    while current != repo and repo in current.parents:
        if current.parent == repo and current.name in _PROTECTED_TOP_LEVEL_DIRS:
            break
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


# --- Signed airdrops (VCD-09) --------------------------------------------
# The mail path used to authorize by comparing the forgeable `From:` header
# and then apply + push code. The real fix is a signed artifact plus a human
# approval. Convention follows cultura/mak_plataforma/mutaciones.py's style
# (plain-JSON artifacts, stdlib only); the crypto is HMAC-SHA256 with a shared
# key from the FLUJO_AIRDROP_HMAC_KEY environment variable.
#
# Artifacts, both living at the root of _airdrop/ and never applied as payload:
#   _airdrop_signed_manifest.json  {"version": 1, "algorithm": "hmac-sha256",
#                                   "files": {"rel/path": "<sha256 hex>", ...}}
#   _airdrop_signed_manifest.sig   hex HMAC-SHA256 of the manifest file bytes
#
# With no key configured, behavior is byte-for-byte the historical one.
SIGNED_MANIFEST_NAME = "_airdrop_signed_manifest.json"
SIGNATURE_NAME = "_airdrop_signed_manifest.sig"
SIGNING_KEY_ENV = "FLUJO_AIRDROP_HMAC_KEY"
_SIGNING_ALGORITHM = "hmac-sha256"


class AirdropSignatureError(RuntimeError):
    """A signed-airdrop policy refusal. Carries one reason per offending file."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        detail = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(
            "Firma del airdrop inválida; no se aplicó nada:\n" + detail +
            "\nSi un humano revisó el contenido y lo aprueba, puede aplicar con "
            "--allow-unsigned (nunca automatizado)."
        )


def get_signing_key() -> Optional[bytes]:
    """Key bytes from FLUJO_AIRDROP_HMAC_KEY, or None when unset/empty."""
    raw = os.getenv(SIGNING_KEY_ENV, "")
    return raw.encode("utf-8") if raw else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_signed_manifest() -> Dict:
    """Deterministic manifest of the current _airdrop/ payload.

    Same payload bytes -> same manifest bytes: no timestamps, sorted keys.
    """
    files = {c["rel"]: _sha256_file(c["src"]) for c in scan_airdrop()}
    return {"version": 1, "algorithm": _SIGNING_ALGORITHM, "files": files}


def manifest_to_bytes(manifest: Dict) -> bytes:
    """Canonical serialization: what gets written and what gets signed."""
    return json.dumps(
        manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sign_airdrop() -> Tuple[Path, Path]:
    """Write manifest + detached HMAC signature for the _airdrop/ payload."""
    key = get_signing_key()
    if key is None:
        raise RuntimeError(
            f"{SIGNING_KEY_ENV} no está configurada: no se puede firmar."
        )
    if not scan_airdrop():
        raise RuntimeError("No hay archivos en _airdrop/ para firmar.")
    data = manifest_to_bytes(build_signed_manifest())
    signature = hmac.new(key, data, hashlib.sha256).hexdigest()
    base = get_airdrop_dir()
    manifest_path = base / SIGNED_MANIFEST_NAME
    signature_path = base / SIGNATURE_NAME
    manifest_path.write_bytes(data)
    signature_path.write_text(signature + "\n", encoding="ascii")
    return manifest_path, signature_path


def verify_airdrop() -> List[str]:
    """Verify the signed manifest against the actual _airdrop/ payload.

    Returns a list of problems (empty = valid signature and intact payload).
    Every problem names the exact file and the reason, in operator Spanish.
    """
    key = get_signing_key()
    if key is None:
        return [
            f"{SIGNING_KEY_ENV} no está configurada: no se puede verificar la firma."
        ]
    base = get_airdrop_dir()
    manifest_path = base / SIGNED_MANIFEST_NAME
    signature_path = base / SIGNATURE_NAME
    problems: List[str] = []
    if not manifest_path.exists():
        problems.append(
            f"{SIGNED_MANIFEST_NAME}: falta el manifiesto firmado (payload sin firmar)"
        )
    if not signature_path.exists():
        problems.append(
            f"{SIGNATURE_NAME}: falta la firma separada (payload sin firmar)"
        )
    if problems:
        return problems

    data = manifest_path.read_bytes()
    expected = hmac.new(key, data, hashlib.sha256).hexdigest()
    actual = signature_path.read_text(encoding="ascii", errors="replace").strip()
    if not hmac.compare_digest(expected, actual):
        return [
            f"{SIGNED_MANIFEST_NAME}: la firma HMAC no corresponde al manifiesto "
            "(manifiesto adulterado o clave distinta)"
        ]

    try:
        manifest = json.loads(data)
    except json.JSONDecodeError:
        return [f"{SIGNED_MANIFEST_NAME}: no es JSON válido"]
    if not isinstance(manifest, dict) or manifest.get("algorithm") != _SIGNING_ALGORITHM:
        return [
            f"{SIGNED_MANIFEST_NAME}: algoritmo no soportado "
            f"(se espera {_SIGNING_ALGORITHM})"
        ]
    declared = manifest.get("files")
    if not isinstance(declared, dict):
        return [f"{SIGNED_MANIFEST_NAME}: falta el mapa 'files'"]

    present = {c["rel"]: c["src"] for c in scan_airdrop()}
    for rel in sorted(declared):
        if rel not in present:
            problems.append(
                f"{rel}: aparece en el manifiesto firmado pero falta en _airdrop/"
            )
        elif _sha256_file(present[rel]) != declared[rel]:
            problems.append(
                f"{rel}: el contenido no coincide con su hash SHA-256 del "
                "manifiesto (archivo adulterado)"
            )
    for rel in sorted(present):
        if rel not in declared:
            problems.append(
                f"{rel}: está en _airdrop/ pero no en el manifiesto firmado "
                "(archivo agregado sin firmar)"
            )
    return problems


# archivos que se ignoran al escanear _airdrop/
# .gitignore se permite explícitamente porque es un archivo legítimo de actualización
# The signature artifacts are metadata about the payload, never payload:
# they are ignored so apply can never copy them into the repo root.
_IGNORE = {".gitkeep", ".DS_Store", SIGNED_MANIFEST_NAME, SIGNATURE_NAME}


def _is_ignored(src: Path) -> bool:
    """Decide si un archivo de _airdrop/ debe ignorarse."""
    if src.name in _IGNORE:
        return True
    # Permitir .gitignore (archivo de configuración real del repo)
    if src.name == ".gitignore":
        return False
    if src.name.startswith("."):
        return True
    return False


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
        if _is_ignored(src):
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


def apply_airdrop(dry_run: bool = False, allow_unsigned: bool = False) -> List[Dict]:
    """Aplica todos los archivos de `_airdrop/` al repo.

    1. Crea backup de los archivos existentes (REPLACE) en `_airdrop_backups/`.
    2. Copia cada archivo a su destino (creando carpetas si hace falta).
    3. Da permiso de ejecución a los `.sh`.

    Signed-airdrop gate (VCD-09): when FLUJO_AIRDROP_HMAC_KEY is configured,
    an unsigned or tampered payload is refused with the exact file and reason.
    `allow_unsigned=True` is the documented HUMAN override (a person typing
    `--allow-unsigned` after reviewing the payload); automation never sets it.
    With no key configured, behavior is exactly the historical one.
    """
    changes = scan_airdrop()
    if not changes or dry_run:
        return changes

    if get_signing_key() is not None and not allow_unsigned:
        problems = verify_airdrop()
        if problems:
            raise AirdropSignatureError(problems)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = get_backup_base_dir() / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(backup_dir, changes)

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

    # Auto-compile any modified config.json projects!
    for c in changes:
        dest, rel = c["dest"], c["rel"]
        if dest.name == "config.json" and "projects/piezas_vectoriales/" in str(dest).replace("\\", "/"):
            try:
                from .render.piezas import render_config
                print(f"Auto-rendering modified project: {rel}")
                render_config(dest)
            except Exception as e:
                print(f"Warning: Failed to auto-render project {rel}: {e}")

    return changes


def _git(
    args: List[str],
    cwd: Path,
    timeout: int = 60,
    live: bool = False,
) -> "subprocess.CompletedProcess":
    """Ejecuta git directamente, con timeout para evitar cuelgues.

    Si live=True deja stdout/stderr conectados al terminal. Esto es importante
    para `git push`: en Windows puede abrir Git Credential Manager o pedir
    autenticacion, y con capture_output=True parecia que el runner estaba
    pegado sin explicar nada.
    """
    cmd = ["git", *args]
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "1")

    if live:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            timeout=timeout,
            env=env,
        )
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _write_checkpoint_file(repo: Path, msg: str) -> Path:
    """Crea checkpoints/<fecha>_<slug>.md (equivalente a checkpoint.sh, en Python)."""
    import re

    checkpoints = repo / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    slug = re.sub(r"[^a-z0-9]+", "-", msg.lower()).strip("-") or "avance"
    cp = checkpoints / f"{date}_{slug}.md"
    branch = _git(["branch", "--show-current"], repo).stdout.strip() or "(sin rama)"
    head = _git(["rev-parse", "--short", "HEAD"], repo).stdout.strip() or "(sin commit)"
    status = _git(["status", "--short"], repo).stdout.strip() or "(limpio)"
    estado = f"Rama: {branch}\nHEAD: {head}\nEstado git:\n{status}"
    cp.write_text(
        f"# Checkpoint — {msg}\n\nFecha: {date}\n\n## Estado\n\n{estado}\n\n"
        f"## Cambios realizados\n\n-\n\n## Próximo paso\n\n-\n",
        encoding="utf-8",
    )
    return cp


def run_auto_checkpoint(message: Optional[str] = None, push: bool = True) -> bool:
    """Crea checkpoint + commit + push usando git directamente (Python puro).

    No depende de `bash` ni de `scripts/checkpoint.sh`, por lo que funciona en
    Windows (Git Bash) sin chocar con el bash de WSL. Reintenta el commit si un
    pre-commit hook modifica archivos y aborta el primer intento.
    """
    repo = repo_root()
    if not (repo / ".git").exists():
        print("No es un repo git (.git no existe).")
        return False

    msg = message or f"airdrop aplicado {datetime.now().strftime('%Y-%m-%d_%H-%M')}"

    try:
        _write_checkpoint_file(repo, msg)

        # commit robusto frente a pre-commit hooks (hasta 3 intentos)
        committed = False
        for attempt in range(1, 4):
            print(f"Auto-checkpoint: git add -A (intento {attempt}/3)")
            _git(["add", "-A"], repo, timeout=120)
            staged = _git(["diff", "--cached", "--quiet"], repo, timeout=60)
            if staged.returncode == 0:
                print("No hay cambios para commitear.")
                committed = True
                break
            print(f"Auto-checkpoint: git commit (intento {attempt}/3)")
            res = _git(["commit", "-m", f"checkpoint: {msg}"], repo, timeout=180)
            if res.returncode == 0:
                committed = True
                break
            if res.stdout:
                print(res.stdout)
            if res.stderr:
                print(res.stderr)
            # un hook pudo modificar archivos: re-agregar y reintentar
        if not committed:
            print("No se pudo commitear tras 3 intentos (revisar hooks / git status).")
            return False

        if not push:
            print("Auto-checkpoint: commit local OK; push omitido por configuracion.")
            return True

        # push a la rama actual. Con salida en vivo y timeout para no quedar pegado.
        if _git(["remote", "get-url", "origin"], repo, timeout=20).returncode == 0:
            branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo, timeout=20).stdout.strip() or "main"
            print(f"Auto-checkpoint: git push -u origin {branch}")
            print("Si GitHub pide login, completa la ventana/prompt. Timeout: 180s.")
            push = _git(["push", "-u", "origin", branch], repo, timeout=180, live=True)
            if push.returncode != 0:
                print("git push fallo. El commit local puede haber quedado creado; ejecuta `git push` manual cuando autentiques.")
                return False
        return True
    except subprocess.TimeoutExpired as e:
        print(f"Timeout en git {' '.join(e.cmd if isinstance(e.cmd, list) else [str(e.cmd)])}.")
        print("El auto-checkpoint se detuvo para evitar quedarse pegado. Revisa `git status` y prueba `git push` manual.")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"Error en auto-checkpoint: {e}")
        return False


def rollback_last() -> Optional[Path]:
    """Restaura el último backup desde `_airdrop_backups/`.

    Desde v0.34.8 usa un manifest por backup: los archivos `REPLACE` se
    restauran y los archivos `NEW` se eliminan. Si el backup es legacy (sin
    manifest), mantiene el comportamiento anterior: solo restaura reemplazos.
    """
    repo = repo_root()
    base = get_backup_base_dir()
    if not base.exists():
        return None
    backups = sorted([d for d in base.iterdir() if d.is_dir()], reverse=True)
    if not backups:
        return None
    last = backups[0]

    manifest = _load_manifest(last)
    if manifest:
        # Primero restaurar reemplazos desde backup.
        for item in manifest:
            if item.get("status") != "REPLACE":
                continue
            rel = Path(str(item["rel"]))
            src = last / rel
            if not src.exists():
                continue
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            if dest.suffix == ".sh":
                dest.chmod(dest.stat().st_mode | 0o111)

        # Luego remover archivos que fueron NEW.
        for item in manifest:
            if item.get("status") != "NEW":
                continue
            rel = Path(str(item["rel"]))
            dest = repo / rel
            if dest.exists() and dest.is_file():
                dest.unlink()
                _cleanup_empty_parents(dest.parent, repo)
        return last

    # Backups antiguos sin manifest: comportamiento legacy.
    for src in last.rglob("*"):
        if src.is_dir() or src.name == _MANIFEST_NAME:
            continue
        rel = src.relative_to(last)
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if dest.suffix == ".sh":
            dest.chmod(dest.stat().st_mode | 0o111)
    return last
