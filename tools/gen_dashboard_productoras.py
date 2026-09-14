"""Genera el tablero HTML db_productoras.html a partir de:

- data/productoras/*.json (fuente de verdad, editable a mano)
- eventos.jsonl triangulados (tools/triangular_fichas.py), top-N por n_fichas

Uso:
    py tools/gen_dashboard_productoras.py --eventos <eventos.jsonl> --out <db_productoras.html> [--top 20]
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>DB Productoras RD</title>
<style>
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; margin: 2rem; background:#0b0d10; color:#e8e8ec; }
h1 { font-size: 1.4rem; }
h2 { margin-top: 2.5rem; border-bottom: 1px solid #333; padding-bottom: .3rem; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin-top: 1rem; }
th, td { border: 1px solid #2a2d33; padding: .4rem .6rem; text-align: left; vertical-align: top; }
th { background: #16181c; position: sticky; top: 0; }
tr:nth-child(even) { background: #101215; }
.pendiente { color: #ff8a8a; font-weight: 600; }
.ok { color: #7ee787; }
.spot { color: #ffd479; }
.logo-thumb { width: 40px; height: 40px; object-fit: contain; background:#fff; border-radius:4px; }
.small { color:#9aa0a6; font-size:.75rem; }
.tag { display:inline-block; padding:.1rem .4rem; border-radius:3px; background:#22262c; margin:.1rem; font-size:.72rem; }
</style>
</head>
<body>
<h1>DB Productoras RD -- estado (generado __FECHA__)</h1>
<p class="small">Fuente productoras: data/productoras/*.json. Fuente eventos: triangulacion de fichas de curatoria (mak), top __N_EVENTOS__ por cantidad de fichas relacionadas. Logos: PENDIENTE = intento fallido (bloqueo de red al fetch), no hay dato inventado.</p>

<h2>Productoras / spots (__N_PROD__)</h2>
<table>
<tr><th>Logo</th><th>Nombre</th><th>Tipo</th><th>IG</th><th>Logo estado</th><th>Venues</th><th>Eventos</th><th>Relaciones</th></tr>
__PROD_ROWS__
</table>

<h2>Eventos triangulados (top __N_EVENTOS__ por evidencia)</h2>
<p class="small">Cluster por fecha (+-1 dia) + venue o solape de lineup. Ruido conocido: fichas de material_rd (suplementos) contaminan algunos clusters de fecha antigua/invalida. Clusters de N fichas muy alto pueden fusionar varias ediciones reales de una misma serie (ej. Sundeck/Espacio Riesco encadenado por solape de lineup) -- no usar como fuente de un evento puntual sin revisar las fichas. Ver docs/rd/DB_PRODUCTORAS_ESTADO.md seccion "Entrega 2026-07-23".</p>
<table>
<tr><th>Fecha</th><th>Venues (candidatos)</th><th>Productoras (candidatas)</th><th>Lineup</th><th>N fichas</th></tr>
__EV_ROWS__
</table>

</body>
</html>
"""


def logo_cell(slug: str, estado: str, raster: str | None) -> str:
    # raster viene del campo logos[0]["raster"] del json (nombre real del
    # archivo descargado, no siempre == slug, ver PR #254: club_freedom.png
    # para freedom.json, street_machine.png para streetmachine.json, etc.)
    if raster and Path(raster).exists():
        return f'<img class="logo-thumb" src="{Path(raster).as_posix()}">'
    png = Path("knowledge/logos/descargas") / f"{slug}.png"
    if png.exists():
        return f'<img class="logo-thumb" src="{png.as_posix()}">'
    cls = "pendiente" if estado in ("no_encontrado", "PENDIENTE", "sin_logo_field") else "ok"
    return f'<span class="{cls}">{estado}</span>'


def build(eventos_path: Path, out_path: Path, top: int) -> None:
    prod_rows = []
    for f in sorted(glob.glob("data/productoras/*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        slug = Path(f).stem
        logos = d.get("logos", [])
        logo_estado = logos[0]["estado"] if logos else "sin_logo_field"
        logo_raster = logos[0].get("raster") if logos else None
        tipo = d.get("tipo", "productora")
        tipo_cls = "spot" if tipo == "spot" else ""
        relaciones = d.get("relaciones", [])
        rel_txt = "".join(
            f'<span class="tag">{r.get("tipo")} {r.get("objetivo")}</span>'
            for r in relaciones
        ) or "-"
        prod_rows.append(
            f"<tr><td>{logo_cell(slug, logo_estado, logo_raster)}</td>"
            f"<td>{d.get('name', slug)}</td>"
            f'<td class="{tipo_cls}">{tipo}</td>'
            f"<td>{d.get('instagram', '') or '-'}</td>"
            f"<td>{logo_estado}</td>"
            f"<td>{len(d.get('venues', []))}</td>"
            f"<td>{len(d.get('eventos', []))}</td>"
            f"<td>{rel_txt}</td></tr>"
        )

    eventos = []
    if eventos_path.exists():
        for line in eventos_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                eventos.append(json.loads(line))
    eventos.sort(key=lambda e: -e["n_fichas"])
    eventos = eventos[:top]

    ev_rows = []
    for e in eventos:
        venues = ", ".join(e["venues"][:4]) or "-"
        prods = ", ".join(p for p in e["productoras"][:4] if "ción" not in p.lower()) or "-"
        lineup = ", ".join(e["lineup"][:6]) or "-"
        ev_rows.append(
            f"<tr><td>{e.get('fecha_min') or 'sin fecha'}</td>"
            f"<td>{venues}</td><td>{prods}</td><td>{lineup}</td>"
            f"<td>{e['n_fichas']}</td></tr>"
        )

    import datetime

    html = (
        HTML_TEMPLATE
        .replace("__FECHA__", datetime.date.today().isoformat())
        .replace("__N_PROD__", str(len(prod_rows)))
        .replace("__N_EVENTOS__", str(len(ev_rows)))
        .replace("__PROD_ROWS__", "\n".join(prod_rows))
        .replace("__EV_ROWS__", "\n".join(ev_rows))
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"OK -> {out_path} ({len(prod_rows)} productoras, {len(ev_rows)} eventos)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eventos", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    build(args.eventos, args.out, args.top)


if __name__ == "__main__":
    main()
