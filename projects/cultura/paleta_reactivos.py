#!/usr/bin/env python3
"""
Paleta madre de Reduciendo Dano: la identidad visual de la ONG derivada de los
colores de los reactivos de analisis de sustancias -- el unico sistema cromatico
donde el color, literalmente, salva vidas (MANIFIESTO Omega #10). Cada color de
marca CITA su origen: que reactivo, que reaccion. La estetica y la etica son el
mismo pigmento.

LIMITE / RESPONSABILIDAD (capa descriptiva de reduccion de dano, permitida):
  - Los colores son referencia ESTETICA tomada de cartas de reactivos publicas
    (consenso DanceSafe / Energy Control). No es una guia de dosis, sintesis ni
    obtencion: nada de eso aparece aca.
  - El test de reactivo es PRESUNTIVO, no identifica con certeza: solo indica la
    posible presencia de una familia de sustancias, nunca pureza ni ausencia de
    adulterantes. Un color NO confirma que algo sea seguro.
  - Este archivo genera una PALETA de diseno, no reemplaza un kit real ni el
    criterio de un servicio de analisis.

Salidas (en --out):
  - reactivos.json     : el sistema de color (reactivo, reaccion, hex)
  - identidad_rd.html  : hoja de identidad -- swatches por reactivo + paleta de marca

    py projects/cultura/paleta_reactivos.py --out projects/cultura/identidad
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path

# Reacciones de reactivo bien establecidas y publicas (consenso de reduccion de
# dano). "reaccion" describe el viraje; "hex" aproxima ese color para diseno.
# Presuntivo: indica familia posible, no identifica con certeza.
REACCIONES = [
    # Marquis
    {"reactivo": "Marquis", "familia": "MDMA / MDA", "reaccion": "violeta a negro", "hex": "#3b1a4a"},
    {"reactivo": "Marquis", "familia": "anfetamina", "reaccion": "naranja a marron", "hex": "#b5651d"},
    {"reactivo": "Marquis", "familia": "opiaceos", "reaccion": "violeta", "hex": "#5b2a6b"},
    {"reactivo": "Marquis", "familia": "2C-B", "reaccion": "verde amarillento", "hex": "#6b8e23"},
    {"reactivo": "Marquis", "familia": "DXM", "reaccion": "gris a negro", "hex": "#3a3a3a"},
    {"reactivo": "Marquis", "familia": "cocaina", "reaccion": "rosa a durazno (actualizacion DanceSafe 2023)", "hex": "#e0a48c"},
    {"reactivo": "Marquis", "familia": "sin reaccion (blanco)", "reaccion": "sin cambio", "hex": "#efe9dd"},
    # Mecke
    {"reactivo": "Mecke", "familia": "MDMA", "reaccion": "azul a verde a negro", "hex": "#16302a"},
    {"reactivo": "Mecke", "familia": "opiaceos", "reaccion": "verde a azul", "hex": "#1f5a5a"},
    {"reactivo": "Mecke", "familia": "2C-B", "reaccion": "verde", "hex": "#4a7c3a"},
    # Mandelin
    {"reactivo": "Mandelin", "familia": "ketamina", "reaccion": "naranja", "hex": "#d47a1a"},
    {"reactivo": "Mandelin", "familia": "MDMA", "reaccion": "azul a negro", "hex": "#14213a"},
    {"reactivo": "Mandelin", "familia": "anfetamina", "reaccion": "verde", "hex": "#3a6b3a"},
    {"reactivo": "Mandelin", "familia": "cocaina", "reaccion": "naranja a marron", "hex": "#a8541a"},
    # Simon (distingue amina secundaria)
    {"reactivo": "Simon", "familia": "MDMA (amina 2a)", "reaccion": "azul", "hex": "#1b3a6b"},
    {"reactivo": "Simon", "familia": "MDA (amina 1a)", "reaccion": "gris a verde oscuro (actualizacion DanceSafe 2023; Simon distingue MDMA azul de MDA)", "hex": "#3a4a3a"},
    # Froehde
    {"reactivo": "Froehde", "familia": "opiaceos", "reaccion": "violeta a verde", "hex": "#3a4a2a"},
    {"reactivo": "Froehde", "familia": "2C-x", "reaccion": "verde oliva", "hex": "#5b6b2a"},
    # Ehrlich (indoles)
    {"reactivo": "Ehrlich", "familia": "LSD / indoles", "reaccion": "purpura a magenta", "hex": "#7a1f5a"},
    {"reactivo": "Ehrlich", "familia": "triptaminas", "reaccion": "purpura", "hex": "#6b2a5a"},
    # Liebermann
    {"reactivo": "Liebermann", "familia": "MDMA", "reaccion": "negro", "hex": "#1a1a1a"},
    {"reactivo": "Liebermann", "familia": "cocaina", "reaccion": "amarillo", "hex": "#d4b81a"},
    {"reactivo": "Liebermann", "familia": "cocaina cortada (levamisol / lidocaina)", "reaccion": "rojo oxido (DanceSafe: alerta de corte comun)", "hex": "#a0442a"},
]

# Paleta de marca derivada: las reacciones mas iconicas -> roles de identidad.
MARCA = [
    {"rol": "primario", "hex": "#3b1a4a", "origen": "Marquis / MDMA (violeta a negro)"},
    {"rol": "secundario", "hex": "#7a1f5a", "origen": "Ehrlich / LSD (purpura a magenta)"},
    {"rol": "acento", "hex": "#d47a1a", "origen": "Mandelin / ketamina (naranja)"},
    {"rol": "alerta", "hex": "#b5651d", "origen": "Marquis / anfetamina (naranja a marron)"},
    {"rol": "vida", "hex": "#4a7c3a", "origen": "Mecke / 2C-B (verde)"},
    {"rol": "papel", "hex": "#efe9dd", "origen": "sin reaccion (el blanco que no confirma nada)"},
]

DISCLAIMER = (
    "Colores de referencia estetica de cartas de reactivos publicas. El test de "
    "reactivo es PRESUNTIVO: indica la posible presencia de una familia de "
    "sustancias, no la identifica con certeza ni mide pureza. Un color no vuelve "
    "segura una sustancia. Esta paleta es diseno, no un kit de analisis."
)

FUENTE = (
    "Cartas publicas de harm-reduction, verificado contra DanceSafe "
    "(dancesafe.org/testing-kit-instructions, actualizaciones 2023). PRESUNTIVO: "
    "reaccion valida solo los primeros ~40s (excepto Ehrlich/Morris). El color es "
    "referencia, no diagnostico."
)


def _reactivos_agrupados():
    grupos: dict[str, list] = {}
    for r in REACCIONES:
        grupos.setdefault(r["reactivo"], []).append(r)
    return grupos


def build(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reactivos.json").write_text(
        json.dumps({"disclaimer": DISCLAIMER, "fuente": FUENTE, "reacciones": REACCIONES, "marca": MARCA},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def swatch(hexv, label, sub):
        # texto oscuro sobre claros, claro sobre oscuros
        light = int(hexv[1:3], 16) + int(hexv[3:5], 16) + int(hexv[5:7], 16) > 360
        fg = "#1a1a1a" if light else "#f2ece0"
        return (f'<div class="sw" style="background:{hexv};color:{fg}">'
                f'<b>{html.escape(label)}</b><span>{html.escape(sub)}</span>'
                f'<code>{hexv}</code></div>')

    # paleta de marca
    marca_html = "".join(swatch(m["hex"], m["rol"], m["origen"]) for m in MARCA)
    # swatches por reactivo
    bloques = []
    for reactivo, items in _reactivos_agrupados().items():
        cells = "".join(swatch(r["hex"], r["familia"], r["reaccion"]) for r in items)
        bloques.append(f'<h3>{html.escape(reactivo)}</h3><div class="row">{cells}</div>')

    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reduciendo Dano - paleta madre de reactivos</title>
<style>
  body{{margin:0;background:#0f0c09;color:#e8e0d2;font-family:system-ui,sans-serif;padding:28px}}
  .wrap{{max-width:1100px;margin:0 auto}}
  h1{{font-weight:600;margin:0 0 6px}}
  h2{{margin:34px 0 10px;font-size:16px;letter-spacing:.08em;text-transform:uppercase;color:#c9bfae}}
  h3{{margin:20px 0 8px;font:600 13px/1 monospace;color:#a99f8e;letter-spacing:.08em}}
  p.note{{color:#c98a5a;line-height:1.5;background:#1a120c;border:1px solid #3a2418;
          border-radius:8px;padding:12px 14px;max-width:900px}}
  .row{{display:flex;flex-wrap:wrap;gap:10px}}
  .sw{{width:150px;min-height:96px;border-radius:8px;padding:10px 12px;
       display:flex;flex-direction:column;gap:3px;justify-content:flex-end;
       border:1px solid rgba(255,255,255,.06)}}
  .sw b{{font-size:13px}} .sw span{{font-size:11px;opacity:.85;line-height:1.3}}
  .sw code{{font-size:11px;opacity:.7}}
</style></head><body><div class="wrap">
<h1>Reduciendo Dano &mdash; paleta madre</h1>
<p class="note">{html.escape(DISCLAIMER)}</p>
<h2>Paleta de marca</h2>
<div class="row">{marca_html}</div>
<h2>Origen: reacciones de reactivo</h2>
{''.join(bloques)}
</div></body></html>"""
    (out_dir / "identidad_rd.html").write_text(page, encoding="utf-8")
    return len(REACCIONES)


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera la paleta madre de reactivos para Reduciendo Dano.")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "identidad"),
                    help="Directorio de salida")
    args = ap.parse_args()
    n = build(Path(args.out))
    print(f"paleta: {n} reacciones + {len(MARCA)} colores de marca -> {args.out}/identidad_rd.html",
          file=sys.stderr)


if __name__ == "__main__":
    main()
