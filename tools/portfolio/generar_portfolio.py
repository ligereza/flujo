"""Genera los JSON del portfolio publico (ligereza/portfolio-auto).

El repo flujo actua como interfaz de administracion del sitio: editar
tools/portfolio/proyectos.json (curado a mano) y correr esto (o dejar que lo
corra .github/workflows/portfolio.yml) produce:

  out/flujo-projects.json  -- proyectos vivos del repo, con version/fecha reales
  out/basurero.json        -- archivo de archivos borrados minado del historial
                              git (el "basurero/fungi": lo que el repo digirio)

Uso:
    py tools/portfolio/generar_portfolio.py [--out DIR] [--max N]

Sin red, sin APIs: solo git local y archivos del repo. El publish al sitio lo
hace el workflow (necesita el secret PORTFOLIO_TOKEN); este script nunca pushea.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from catalog_contract import load_catalog

_REPO = Path(__file__).resolve().parents[2]
_CURADO = Path(__file__).resolve().parent / "proyectos.json"

# Nunca publicar rutas de estos tipos (nombres sensibles o ruido generado).
_NO_PUBLICABLE = re.compile(
    r"(^|/)(\.env|2\.txt|config\.json|credentials?|secret|token|password"
    r"|id_rsa|.*\.(pem|p12|key|db|sqlite3?|zip|pyc|bak)"
    r"|__pycache__|\.pytest_cache|node_modules|dist|build"
    r"|_airdrop[^/]*|_logs|\.archive|_archive"
    r"|sub-.*-resource-providers-.*\.csv)",
    re.IGNORECASE,
)
# Generados que se borran/regeneran todo el tiempo: compost sin historia real.
_RUIDO = re.compile(r"^(context/.*\.html|.*package-lock\.json)$")


def es_publicable(ruta: str) -> bool:
    """True si la ruta de un archivo borrado puede aparecer en el sitio publico."""
    ruta = ruta.replace("\\", "/")
    if _NO_PUBLICABLE.search(ruta):
        return False
    if _RUIDO.match(ruta):
        return False
    return True


def compactar_borrados(eventos: list[dict]) -> list[dict]:
    """Deduplica por ruta quedandose con el borrado MAS RECIENTE.

    eventos viene ordenado del mas nuevo al mas viejo (orden de git log).
    """
    vistos: set[str] = set()
    salida: list[dict] = []
    for ev in eventos:
        if ev["ruta"] in vistos:
            continue
        vistos.add(ev["ruta"])
        salida.append(ev)
    return salida


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(_REPO), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=True,
    ).stdout


def minar_borrados(max_entradas: int = 400) -> list[dict]:
    """Archivos borrados en la historia de git (mas recientes primero)."""
    crudo = _git(
        "log", "--diff-filter=D", "--name-only",
        "--format=%x01%h%x02%cs", "--no-renames",
    )
    eventos: list[dict] = []
    commit, fecha = "", ""
    for linea in crudo.splitlines():
        if linea.startswith("\x01"):
            commit, _, fecha = linea[1:].partition("\x02")
            continue
        ruta = linea.strip()
        if not ruta or not es_publicable(ruta):
            continue
        eventos.append({
            "ruta": ruta.replace("\\", "/"),
            "borrado": fecha,
            "commit": commit,
            "ext": (Path(ruta).suffix.lstrip(".").lower() or "sin-ext"),
        })
    return compactar_borrados(eventos)[:max_entradas]


def leer_version() -> str:
    texto = (_REPO / "src" / "flujo" / "version.py").read_text(encoding="utf-8")
    m = re.search(r'__version__ = "([^"]+)"', texto)
    return m.group(1) if m else "0.0.0"


def construir_proyectos() -> dict:
    curado = load_catalog(_CURADO, source_label="tools/portfolio/proyectos.json")
    return {
        "titulo": curado.get("titulo", "flujo"),
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "version_flujo": leer_version(),
        "contrato": curado["contract"],
        "proyectos": curado["proyectos"],
    }


def construir_basurero(max_entradas: int = 400) -> dict:
    entradas = minar_borrados(max_entradas)
    return {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fuente": "historial git de ligereza/vibecodeine (archivos borrados)",
        "total": len(entradas),
        "entradas": entradas,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(_REPO / "out"), help="directorio de salida")
    ap.add_argument("--max", type=int, default=400, help="tope de entradas del basurero")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    proyectos = construir_proyectos()
    basurero = construir_basurero(args.max)
    (out / "flujo-projects.json").write_text(
        json.dumps(proyectos, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "basurero.json").write_text(
        json.dumps(basurero, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {out / 'flujo-projects.json'} ({len(proyectos['proyectos'])} proyectos)")
    print(f"OK {out / 'basurero.json'} ({basurero['total']} archivos digeridos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
