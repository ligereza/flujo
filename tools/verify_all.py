#!/usr/bin/env python3
"""Verificacion del repo en un comando, con reporte limpio.

Uso: py tools/verify_all.py [--web]
Corre: compileall src/flujo, pytest tests/ -q, flujo verify.
Con --web agrega: npm run typecheck (en web/).
Exit != 0 si algo falla.
"""
import subprocess, sys

def run(name, cmd, cwd=None):
    print(f"\n=== {name}: {' '.join(cmd)} ===")
    try:
        r = subprocess.run(cmd, cwd=cwd)
        ok = r.returncode == 0
    except FileNotFoundError as e:
        print(f"  (no ejecutable: {e})"); ok = False
    print(f"--> {'OK' if ok else 'FALLO'} ({name})")
    return ok

def main():
    py = sys.executable
    res = []
    res.append(("compileall", run("compileall", [py, "-m", "compileall", "-q", "src/flujo"])))
    res.append(("pytest", run("pytest", [py, "-m", "pytest", "tests/", "-q"])))
    res.append(("flujo verify", run("flujo verify", [py, "-m", "flujo", "verify"])))
    if "--web" in sys.argv:
        res.append(("web typecheck", run("web typecheck", ["npm", "run", "typecheck"], cwd="web")))
    print("\n===== RESUMEN =====")
    for n, ok in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    sys.exit(0 if all(ok for _, ok in res) else 1)

if __name__ == "__main__":
    main()
