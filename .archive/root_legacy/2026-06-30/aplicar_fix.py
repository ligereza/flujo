#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_fix.py  -  Repara el dispatcher: restaura tu __main__.py original
y registra los addons (hub serve/index/route) dentro de tu cli.py Typer,
SIN pisar tus comandos (health/doctor/job/eventos...).

Uso (desde la raiz del repo, C:\\IA\\flujo):
    py aplicar_fix.py
    py aplicar_fix.py --dry-run   (solo muestra que haria)

Es idempotente: si ya esta aplicado, no duplica nada.
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
# si se ejecuta desde el zip extraido, permitir --repo
def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd(),
                    help="raiz del repo flujo (default: carpeta actual)")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


MAIN_ORIGINAL = 'from .cli import app\n\nif __name__ == "__main__":\n    app()\n'
IMPORT_LINE = "from flujo.cli_addons import register_addons"
CALL_LINE = "register_addons(app)"


def main():
    a = parse()
    repo = os.path.abspath(a.repo)
    cli = os.path.join(repo, "src", "flujo", "cli.py")
    main_py = os.path.join(repo, "src", "flujo", "__main__.py")
    addons = os.path.join(repo, "src", "flujo", "cli_addons.py")

    print("Reparando dispatcher en:", repo)
    if not os.path.isfile(cli):
        print("ERROR: no encuentro src/flujo/cli.py. Pasa --repo C:\\IA\\flujo")
        return 2
    if not os.path.isfile(addons):
        print("ERROR: falta src/flujo/cli_addons.py (debe venir en este fix).")
        return 2

    # 1) restaurar __main__.py original (delegar a cli:app)
    cur = open(main_py, encoding="utf-8").read() if os.path.isfile(main_py) else ""
    if "register_addons" in cur or "from .cli import app" in cur and "subcomando" not in cur and len(cur) < 200:
        print("  __main__.py ya delega a cli:app (ok)")
    else:
        print("  __main__.py: restaurando version que delega a cli:app")
        if not a.dry_run:
            open(main_py, "w", encoding="utf-8").write(MAIN_ORIGINAL)

    # 2) inyectar las 2 lineas en cli.py (idempotente)
    src = open(cli, encoding="utf-8").read()
    changed = False

    if CALL_LINE in src:
        print("  cli.py ya tiene register_addons(app) (ok)")
    else:
        # localizar la definicion de la app principal: 'app = typer.Typer('
        m = re.search(r"^app\s*=\s*typer\.Typer\(", src, re.M)
        if not m:
            print("  AVISO: no encontre 'app = typer.Typer(' en cli.py.")
            print("  Agrega manualmente al final de cli.py:")
            print("    " + IMPORT_LINE)
            print("    " + CALL_LINE)
            return 1
        # insertar import al inicio (tras el primer bloque de imports) y la llamada al final
        if IMPORT_LINE not in src:
            src = IMPORT_LINE + "\n" + src
        src = src.rstrip() + "\n\n# --- addons del airdrop hub (serve/index/route) ---\n" + CALL_LINE + "\n"
        changed = True

    if changed:
        print("  cli.py: insertando import + register_addons(app) al final")
        if not a.dry_run:
            # backup por seguridad
            open(cli + ".bak", "w", encoding="utf-8").write(open(cli, encoding="utf-8").read())
            open(cli, "w", encoding="utf-8").write(src)
            print("  (backup: cli.py.bak)")

    print("\nListo." + ("  [DRY-RUN: no se escribio nada]" if a.dry_run else ""))
    print("Verifica con:")
    print("  py -m flujo health        (tus comandos siguen vivos)")
    print("  py -m flujo hub serve --open")
    print("  py -m flujo hub route where --area eventos --pieza flyer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
