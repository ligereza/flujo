#!/usr/bin/env python3
"""Genera docs/CATALOGO_RD.md a partir de la fuente real de PACKS RD.

No hardcodea precios: todos los numeros del catalogo (precio, voluntarios,
m2, stands, proporciones del desglose) se derivan en tiempo de ejecucion de
src/flujo/plano/packs.py (via flujo.plano.costs). Los ejemplos de
cotizacion dual-audiencia (productora / interno-ONG) se generan llamando al
motor real projects/cotizaciones/engine.py; si ese motor no se puede
importar o ejecutar (bug conocido al momento de escribir este script:
flujo.brand no expone load_styles/get_color), el catalogo cae a un ejemplo
derivado directamente de flujo.plano.costs.resumen_costos (misma fuente de
precios, sin el envoltorio roto) y deja constancia del problema real.

Uso:
    py scripts/generar_catalogo_rd.py

Regenera docs/CATALOGO_RD.md. NO editar ese archivo a mano.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
_SRC = ROOT / "src"
# Corrido como `py scripts/generar_catalogo_rd.py`, sys.path[0] es scripts/,
# donde vive scripts/flujo.py -- que hace SOMBRA al paquete flujo. Se saca
# ese dir antes de fijar el src de esta checkout (mismo espiritu que
# tests/conftest.py: el catalogo refleja el codigo al lado del script).
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
sys.path[:] = [p for p in sys.path if p != _SCRIPTS_DIR]
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flujo.version import __version__ as FLUJO_VERSION  # noqa: E402
from flujo.plano.packs import ALL_PACKS, PACKS, desglose_pack, ev_desde_pack  # noqa: E402
from flujo.plano.costs import resumen_costos  # noqa: E402

OUTPUT = ROOT / "docs" / "CATALOGO_RD.md"
EVENTO_EJEMPLO = ROOT / "projects" / "plano" / "ejemplos" / "evento_ejemplo.json"
GENERATOR_PATH = "scripts/generar_catalogo_rd.py"

try:
    from projects.cotizaciones.engine import generar_cotizacion
except Exception as exc:  # motor satelite, puede estar roto sin bloquear el catalogo
    generar_cotizacion = None
    _ENGINE_IMPORT_ERROR = f"{type(exc).__name__}: {getattr(exc, 'name', None) or exc}"
else:
    _ENGINE_IMPORT_ERROR = ""


def _money(n: int) -> str:
    return f"${n:,.0f}"


def _packs_table() -> str:
    lines = [
        "| Pack | Nombre | Precio | Voluntarios | Stands | m2 | Desglose por proporciones |",
        "|---|---|---|---|---|---|---|",
    ]
    for pack_id in ALL_PACKS:
        pack = PACKS[pack_id]
        tiene_desglose = "si" if pack.get("proporciones") else "no (precio plano)"
        lines.append(
            f"| {pack_id} | {pack['nombre']} | {_money(pack['precio'])} | "
            f"{pack['voluntarios']} | {pack['stands']} | {pack['m2']} | {tiene_desglose} |"
        )
    return "\n".join(lines)


def _pack_detail(pack_id: str) -> str:
    pack = PACKS[pack_id]
    lines = [f"### {pack['label']} -- {pack['nombre']}", "", pack["desc"], ""]
    lines.append(f"Precio: {_money(pack['precio'])} (valor absoluto, unico editable en packs.py)")
    lines.append("")
    lines.append("Incluye:")
    for inc in pack["inclusiones"]:
        lines.append(f"- {inc}")
    lines.append("")

    desglose = desglose_pack(pack_id)
    if desglose:
        lines.append("Desglose (proporcion del precio, derivado siempre como precio*pct/100):")
        lines.append("")
        lines.append("| Item | % | Monto |")
        lines.append("|---|---|---|")
        for item in desglose:
            lines.append(f"| {item['label']} | {item['pct']}% | {_money(item['monto'])} |")
        total = sum(item["monto"] for item in desglose)
        lines.append("")
        lines.append(f"Suma del desglose: {_money(total)} (debe igualar el precio del pack).")
    else:
        lines.append("Sin desglose por proporciones: precio plano, ver inclusiones arriba.")
    lines.append("")
    return "\n".join(lines)


def _fallback_examples() -> Dict[str, str]:
    """Ejemplo derivado directo de resumen_costos, sin pasar por engine.py."""
    from flujo.plano.packs import DEFAULT_PACK

    ev = ev_desde_pack(DEFAULT_PACK, nombre="Evento Ejemplo RD")
    costos = resumen_costos(ev)
    productora = (
        "[FALLBACK: projects/cotizaciones/engine.py no disponible ahora mismo, "
        "ver seccion 'Estado del motor de cotizaciones' abajo. Este texto usa "
        "la misma fuente de precios (flujo.plano.costs.resumen_costos) que "
        "engine.py.]\n\n"
        f"COTIZACION -- {ev['nombre']} | Reduciendo Dano\n\n{costos}"
    )
    interno = (
        "[FALLBACK: projects/cotizaciones/engine.py no disponible ahora mismo, "
        "ver seccion 'Estado del motor de cotizaciones' abajo.]\n\n"
        f"COTIZACION INTERNA -- {ev['nombre']}\nPara: ONG / trabajador / empresa\n\n{costos}"
    )
    return {"productora": productora, "interno": interno}


def _worked_examples() -> Tuple[Dict[str, str], str]:
    """Devuelve (ejemplos por audiencia, nota de estado del motor real)."""
    if generar_cotizacion is None:
        nota = (
            "engine.py NO se pudo importar: "
            f"{_ENGINE_IMPORT_ERROR}. Los ejemplos abajo son fallback derivado "
            "de flujo.plano.costs (mismos precios, sin el motor de cotizaciones)."
        )
        return _fallback_examples(), nota

    if not EVENTO_EJEMPLO.exists():
        nota = (
            f"engine.py se importo pero falta el fixture {EVENTO_EJEMPLO.relative_to(ROOT)}; "
            "los ejemplos abajo son fallback derivado de flujo.plano.costs."
        )
        return _fallback_examples(), nota

    filas = {"productora": "cotizacion_productora.txt", "interno": "cotizacion_interno.txt"}
    ejemplos: Dict[str, str] = {}
    try:
        for audiencia, nombre_archivo in filas.items():
            with tempfile.TemporaryDirectory(prefix="catalogo_rd_") as tmp:
                out_dir = Path(tmp)
                generar_cotizacion(EVENTO_EJEMPLO, audiencia, out_dir)
                ejemplos[audiencia] = (out_dir / nombre_archivo).read_text(encoding="utf-8").strip()
    except Exception as exc:  # motor real presente pero fallo al ejecutar
        nota = (
            f"engine.py se importo pero la llamada real fallo ({type(exc).__name__}: "
            f"{exc}). Los ejemplos abajo son fallback derivado de flujo.plano.costs."
        )
        return _fallback_examples(), nota

    nota = "engine.py funciono: los ejemplos abajo son la salida real de generar_cotizacion()."
    return ejemplos, nota


def render_catalogo() -> str:
    ejemplos, nota_motor = _worked_examples()

    partes = [
        "# Catalogo RD -- Packs y Cotizaciones",
        "",
        f"Version flujo: {FLUJO_VERSION}",
        "",
        "## Fuente de verdad",
        "",
        "- Fuente canonica de precios: `data/rd_packs.json`, editable a mano "
        "(desde 2026-07-26; antes vivia cableada en dos copias que podian "
        "desincronizarse, `packs.py` y `web/src/rdBrand.ts`).",
        "- `src/flujo/plano/packs.py` LEE ese archivo; `costs.py` y `engine.py` "
        "consumen SOLO ese modulo, nunca un precio propio.",
        "- `precio` es el unico valor absoluto editable por pack; cualquier monto de "
        "desglose se recalcula siempre como `precio*pct/100` (nunca se guarda aparte).",
        "",
        "## Packs",
        "",
        _packs_table(),
        "",
    ]
    for pack_id in ALL_PACKS:
        partes.append(_pack_detail(pack_id))

    partes += [
        "## Cotizaciones (dual-audiencia)",
        "",
        "El comando `py -m flujo cotizaciones <evento.json> --para "
        "productora|interno` genera 2 versiones desde el mismo costeo "
        "(`flujo.plano.costs.resumen_costos`, derivado del pack del evento):",
        "",
        "- `productora`: version externa branded/infografica (para productoras).",
        "- `interno` (tambien acepta `empresa`): desglose detallado interno, para "
        "ONG/empresa/trabajador.",
        "",
        f"Nota sobre el motor real: {nota_motor}",
        "",
        "### Ejemplo -- audiencia productora",
        "",
        "```",
        ejemplos["productora"],
        "```",
        "",
        "### Ejemplo -- audiencia interno (ONG/empresa)",
        "",
        "```",
        ejemplos["interno"],
        "```",
        "",
    ]

    if _ENGINE_IMPORT_ERROR:
        partes += [
            "## Estado del motor de cotizaciones (issue real, no arreglado por este script)",
            "",
            "`projects/cotizaciones/engine.py` hace "
            "`from flujo.brand import load_styles, get_color` a nivel de modulo. "
            "Ese import falla ahora mismo:",
            "",
            "```",
            _ENGINE_IMPORT_ERROR,
            "```",
            "",
            "`src/flujo/brand.py` quedo vacio (solo el docstring "
            "\"Modulo de branding migrado a knowledge/logos.\") tras una migracion; "
            "nunca se actualizo `engine.py` para dejar de depender de esos simbolos. "
            "Consecuencia: `py -m flujo cotizaciones ...` esta roto para AMBAS "
            "audiencias (el import falla antes de que se elija la audiencia). "
            "Este generador no lo arregla (fuera de alcance); usa el fallback de "
            "arriba para no bloquear el catalogo.",
            "",
        ]

    partes += [
        "## Regenerar",
        "",
        f"Este archivo es generado por `{GENERATOR_PATH}` -- NO editar a mano, "
        f"regenerar con: `py {GENERATOR_PATH}`",
        "",
    ]
    return "\n".join(partes) + "\n"


def main() -> int:
    contenido = render_catalogo()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"OK: {OUTPUT.relative_to(ROOT)} generado ({len(contenido)} bytes).")
    if _ENGINE_IMPORT_ERROR:
        print("AVISO: projects/cotizaciones/engine.py roto (ver seccion del catalogo).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
