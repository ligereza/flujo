#!/usr/bin/env python3
"""Chequeo general rápido del repo flujo."""
from pathlib import Path
import json, subprocess, sys, yaml

errors = []
warnings = []

ROOT = Path(__file__).resolve().parents[1]


def check_jsons():
    for p in ROOT.rglob("*.json"):
        if any(part in p.parts for part in [".git", "salida_generada", "02_editables_svg", "03_final_vectorizado_svg", "04_preview", "05_exports"]):
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"JSON inválido {p}: {e}")


def check_yamls():
    for p in ROOT.rglob("*.yaml"):
        if ".git" in p.parts:
            continue
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"YAML inválido {p}: {e}")


def check_pycache():
    for p in ROOT.rglob("__pycache__"):
        if ".git" not in p.parts:
            warnings.append(f"Cache Python presente: {p}")
    for p in ROOT.rglob("*.pyc"):
        if ".git" not in p.parts:
            warnings.append(f"PYC presente: {p}")


def check_required_files():
    required = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        "scripts/flujo.py",
        "scripts/_common.py",
    ]
    for f in required:
        if not (ROOT / f).exists():
            errors.append(f"Archivo requerido no encontrado: {f}")


def check_scripts_executable():
    for p in ROOT.glob("scripts/*.sh"):
        if not p.stat().st_mode & 0o111:
            warnings.append(f"Script no ejecutable: {p}")


def check_large_files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.stat().st_size > 500_000:
            warnings.append(f"Archivo grande (>500KB): {p} ({p.stat().st_size / 1024:.1f} KB)")


def check_no_exes():
    for p in ROOT.rglob("*.exe"):
        if ".git" not in p.parts:
            errors.append(f"EXE encontrado en repo: {p}")


def run_optional(cmd):
    try:
        r = subprocess.run(cmd, text=True, capture_output=True, timeout=60, cwd=ROOT)
        if r.returncode != 0:
            errors.append(f"Falla comando {cmd}: {r.stderr or r.stdout}")
        else:
            print(r.stdout.strip())
    except Exception as e:
        errors.append(f"No se pudo ejecutar {cmd}: {e}")


print("# Flujo health check")
check_required_files()
check_jsons()
check_yamls()
check_pycache()
check_scripts_executable()
check_large_files()
check_no_exes()

if (ROOT / "scripts" / "piezas_validate_config.py").exists():
    run_optional([sys.executable, str(ROOT / "scripts" / "piezas_validate_config.py")])

if warnings:
    print("\nAVISOS:")
    for w in warnings:
        print("-", w)

if errors:
    print("\nERRORES:")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("\nOK: health check sin problemas críticos")
