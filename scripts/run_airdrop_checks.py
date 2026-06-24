#!/usr/bin/env python3
"""Aplica un airdrop con checks y log de error reproducible.

Uso:
    py scripts/run_airdrop_checks.py "vX.Y.Z - mensaje"
    py scripts/run_airdrop_checks.py --resume "vX.Y.Z - mensaje"

Diseñado para Windows/Git Bash: no invoca `bash` desde Python. Usa el motor
Python de `flujo.airdrop` para scan/apply/checkpoint y deja logs UTF-8 en
`_logs/` si algo falla.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path.cwd().resolve()
SRC = ROOT / "src"


def _ensure_src_first() -> None:
    """Mantiene src/ antes que scripts/ para no importar scripts/flujo.py.

    En Windows/Git Bash el runner se ejecuta como `py scripts/run_airdrop_checks.py`;
    Python agrega `scripts/` a sys.path. Si luego `scripts/` queda antes de `src/`,
    `import flujo.airdrop` puede resolver `scripts/flujo.py` como módulo `flujo` y
    fallar con: `'flujo' is not a package`.
    """
    if not SRC.exists():
        return
    src = str(SRC)
    sys.path[:] = [p for p in sys.path if p != src]
    sys.path.insert(0, src)


_ensure_src_first()

LOG_DIR = ROOT / "_logs"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _write(log, text: str = "") -> None:
    print(text)
    log.write(text + "\n")
    log.flush()


def _copy_to_clipboard(text: str) -> bool:
    clip = shutil.which("clip")
    if not clip:
        return False
    try:
        subprocess.run([clip], input=text, text=True, encoding="utf-8", errors="replace", check=True)
        return True
    except Exception:
        return False


def _run_subprocess(log, cmd: list[str]) -> int:
    _write(log, "")
    _write(log, "> " + " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        log.write(line)
    proc.wait()
    log.flush()
    if proc.returncode != 0:
        _write(log, f"\nERROR: comando falló con código {proc.returncode}: {' '.join(cmd)}")
    return proc.returncode


def _run_step(log, name: str, func: Callable[[], None]) -> int:
    _write(log, "")
    _write(log, f"> {name}")
    try:
        func()
    except Exception as exc:  # noqa: BLE001 - script operativo: log completo y parar
        _write(log, f"ERROR: {name} falló: {exc}")
        return 1
    return 0


def _validate_airdrop(log, allow_airdrop_engine: bool = False) -> None:
    _ensure_src_first()
    script = ROOT / "scripts" / "validate_airdrop.py"
    spec = importlib.util.spec_from_file_location("flujo_validate_airdrop_script", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar validador: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    argv = ["--allow-airdrop-engine"] if allow_airdrop_engine else []
    rc = module.main(argv)
    _ensure_src_first()
    if rc != 0:
        raise RuntimeError(f"validate_airdrop terminó con código {rc}")
    _write(log, "VALIDACIÓN OK")


def _airdrop_dry_run(log) -> None:
    _ensure_src_first()
    from flujo.airdrop import scan_airdrop

    changes = scan_airdrop()
    if not changes:
        raise RuntimeError("No hay archivos pendientes en _airdrop/")
    _write(log, "Simulación de airdrop:")
    for change in changes:
        _write(log, f"  {change['status']:<8} {change['rel']}")
    _write(log, f"Total: {len(changes)} archivos serían afectados.")


def _airdrop_apply(log) -> None:
    _ensure_src_first()
    from flujo.airdrop import apply_airdrop

    changes = apply_airdrop()
    if not changes:
        raise RuntimeError("No hay archivos pendientes en _airdrop/")
    _write(log, "Airdrop aplicado:")
    for change in changes:
        _write(log, f"  OK {change['rel']}")


def _checkpoint(log, message: str) -> None:
    _ensure_src_first()
    from flujo.airdrop import run_auto_checkpoint

    ok = run_auto_checkpoint(message)
    if not ok:
        raise RuntimeError("run_auto_checkpoint devolvió False")
    _write(log, "Checkpoint + push OK")



def _capture(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return (proc.stdout or proc.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001 - summary best effort
        return f"? ({exc})"


def _write_success_summary(log, message: str) -> None:
    _ensure_src_first()
    version = _capture([sys.executable, "-c", "from flujo.version import get_version; print(get_version())"])
    commit = _capture(["git", "rev-parse", "--short", "HEAD"])
    branch = _capture(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = _capture(["git", "status", "--short"]) or "limpio"
    _write(log, "")
    _write(log, "### RESUMEN FINAL")
    _write(log, f"Versión: {version}")
    _write(log, f"Rama: {branch}")
    _write(log, f"Commit: {commit}")
    _write(log, f"Mensaje: {message}")
    _write(log, "Checks: pip install, compileall, pytest, health, version, changelog" + (", hub_smoke" if (ROOT / "scripts" / "hub_smoke.py").exists() else ""))
    _write(log, f"Git status: {status}")
    _write(log, "Próximo recomendado: py -m flujo app  (o py -m flujo doctor si es una máquina nueva)")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runner seguro de airdrop con log")
    parser.add_argument("message", help="Mensaje del checkpoint")
    parser.add_argument("--resume", action="store_true", help="Reanuda después de un apply ya realizado: salta validate/dry-run/apply y corre checks/checkpoint")
    parser.add_argument("--skip-hub-smoke", action="store_true", help="omite scripts/hub_smoke.py")
    parser.add_argument("--skip-checkpoint", action="store_true", help="Ejecuta checks pero no commitea/pushea")
    parser.add_argument(
        "--allow-airdrop-engine",
        action="store_true",
        help="Permite airdrops que modifican src/flujo/airdrop.py tras revisión explícita",
    )
    args = parser.parse_args(argv)

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"airdrop_run_{_timestamp()}.txt"

    failed = False
    with log_path.open("w", encoding="utf-8") as log:
        _write(log, f"### START {datetime.now().isoformat(timespec='seconds')}")
        _write(log, f"### PWD {ROOT}")
        _write(log, f"### MESSAGE {args.message}")
        _write(log, "### RUNNER Python-only (sin bash interno)")
        if args.resume:
            _write(log, "### RESUME: saltando validate/dry-run/apply; continuando checks/checkpoint")

        _ensure_src_first()
        steps: list[tuple[str, Callable[[], int]]] = []
        if not args.resume:
            steps.extend([
                (
                    "validar _airdrop",
                    lambda: _run_step(
                        log,
                        "py scripts/validate_airdrop.py"
                        + (" --allow-airdrop-engine" if args.allow_airdrop_engine else ""),
                        lambda: _validate_airdrop(log, args.allow_airdrop_engine),
                    ),
                ),
                ("airdrop dry-run", lambda: _run_step(log, "flujo.airdrop.scan_airdrop()", lambda: _airdrop_dry_run(log))),
                ("airdrop apply", lambda: _run_step(log, "flujo.airdrop.apply_airdrop()", lambda: _airdrop_apply(log))),
            ])

        compile_targets = ["src", "scripts", "tests"]
        generator = ROOT / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py"
        if generator.exists():
            compile_targets.append(str(generator.relative_to(ROOT)))

        steps.extend([
            ("pip install", lambda: _run_subprocess(log, [sys.executable, "-m", "pip", "install", "-e", ".[dev]"])),
            ("compileall", lambda: _run_subprocess(log, [sys.executable, "-m", "compileall", "-q", *compile_targets])),
            ("pytest", lambda: _run_subprocess(log, [sys.executable, "-m", "pytest", "tests/", "-q"])),
            ("health", lambda: _run_subprocess(log, [sys.executable, "-m", "flujo", "health"])),
            ("version", lambda: _run_subprocess(log, [sys.executable, "-m", "flujo", "version"])),
            (
                "changelog check",
                lambda: _run_subprocess(
                    log,
                    [
                        sys.executable,
                        "-c",
                        "from flujo.version import get_version, get_changelog; v=get_version(); "
                        "assert v in get_changelog(), v; print(v, True)",
                    ],
                ),
            ),
        ])
        smoke = ROOT / "scripts" / "hub_smoke.py"
        if smoke.exists() and not args.skip_hub_smoke:
            steps.append(("hub smoke", lambda: _run_subprocess(log, [sys.executable, str(smoke)])))
        if not args.skip_checkpoint:
            steps.append(("checkpoint", lambda: _run_step(log, "flujo.airdrop.run_auto_checkpoint()", lambda: _checkpoint(log, args.message))))

        for _name, step in steps:
            rc = step()
            if rc != 0:
                failed = True
                break

        if not failed:
            _write_success_summary(log, args.message)
        _write(log, "")
        _write(log, f"### END {datetime.now().isoformat(timespec='seconds')}")
        _write(log, f"### RESULT {'FAILED' if failed else 'OK'}")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    copied = _copy_to_clipboard(text)
    if failed:
        error_path = LOG_DIR / f"airdrop_error_{_timestamp()}.txt"
        error_path.write_text(text, encoding="utf-8")
        print(f"\nERROR: airdrop detenido. Log: {error_path}")
        if copied:
            print("Log copiado al portapapeles.")
        return 1

    print(f"\nOK: airdrop/checks completados. Log: {log_path}")
    if copied:
        print("Log copiado al portapapeles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
