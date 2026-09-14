#!/usr/bin/env python3
"""Exporta una propuesta RD en PDF por pack de servicio (INFO/TESTEO/COMPLETO).

Cada PDF junta: brief institucional (texto exacto de la propuesta) + datos del
evento + plano SVG del stand + rider (necesidades logicas) + cotizacion, con
tablas alineadas. Vectorial via Edge headless (mismo motor que tools/svg/svg_to_pdf.py).

Uso:
    py scripts/export_propuesta_pdf.py                    # 3 packs x 2 temas = 6 PDFs
    py scripts/export_propuesta_pdf.py INFO TESTEO         # subconjunto de packs
    py scripts/export_propuesta_pdf.py dark                # solo un tema
    py scripts/export_propuesta_pdf.py --out C:/ruta       # carpeta de salida
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flujo.plano.costs import calcular_costos  # noqa: E402
from flujo.plano.engine import reglas_rider, render_svg, validate_evento  # noqa: E402
from flujo.plano.packs import ALL_PACKS, ev_desde_pack  # noqa: E402

_REPO = Path(__file__).resolve().parents[1]
_BRIEF_TXT = _REPO / "datadrops" / "Propuesta_Reduciendo_Dano.txt"
_EDGE_CANDS = [
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

PACK_IDS = ALL_PACKS


def _edge() -> str:
    for e in _EDGE_CANDS:
        if os.path.exists(e):
            return e
    raise SystemExit("Edge no encontrado (ajusta _EDGE_CANDS)")


def _brief_secciones() -> dict[str, str]:
    """Extrae 'Quienes Somos' y 'Objetivo del Servicio' del txt canonico (cp1252)."""
    txt = _BRIEF_TXT.read_text(encoding="cp1252")
    lineas = [l.strip() for l in txt.splitlines()]
    def bloque(desde: str, hasta: str) -> str:
        try:
            i = lineas.index(desde)
            j = lineas.index(hasta)
        except ValueError:
            return ""
        return " ".join(l for l in lineas[i + 1:j] if l)
    return {
        "quienes": bloque("Quiénes Somos", "Objetivo del Servicio"),
        "objetivo": bloque("Objetivo del Servicio", "Modalidades de Intervención"),
    }


def _clp(n: float) -> str:
    return "$" + format(int(n), ",d").replace(",", ".")


def _fila(k: str, v: str, num: bool = False) -> str:
    cls = ' class="num"' if num else ""
    return f'<tr><th>{escape(k)}</th><td{cls}>{escape(v)}</td></tr>'


# Temas de documento con paleta RD real (linea_editorial/v4.1.md):
# Negro #0A0A0A, Blanco ceramico #F2F2F2, Magenta #C800C8, Amarillo #FFD21F.
TEMAS_DOC = {
    "dark": {
        "bg": "#0a0a0a", "text": "#f2f2f2", "muted": "#8a8a80", "accent": "#c800c8",
        "panel": "#141414", "borde": "#2a2a2a", "th": "#181818", "total": "#ffd21f",
        "logo": "RD_logo_vector_blanco.svg",  # gota blanca -> fondo oscuro
    },
    "white": {
        "bg": "#ffffff", "text": "#141414", "muted": "#6b6b62", "accent": "#b100b8",
        "panel": "#f6f4f6", "borde": "#d8d5d8", "th": "#f0edf0", "total": "#b100b8",
        "logo": "RD_logo_vector_negro.svg",   # gota negra -> fondo blanco
    },
}


def _logo_inline(nombre_svg: str) -> str:
    """Devuelve el <svg> del logo RD vectorial listo para incrustar (crisp)."""
    p = _REPO / "assets" / "logo" / nombre_svg
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8")
    svg = txt[txt.index("<svg"):]
    # fijar tamano de masthead conservando el viewBox (ratio 1060x817.61)
    svg = svg.replace("<svg", '<svg height="40" width="52" preserveAspectRatio="xMidYMid meet"', 1)
    return svg


def _masthead(tema: dict, nombre: str) -> str:
    """Cabecera con logo RD vectorial + bloque ORGANIZACION RD (ref RIDER-01.svg)."""
    return f"""<div class="mh">
  <div class="mh-l">
    <span class="logo">{_logo_inline(tema['logo'])}</span>
    <div class="mh-tt">
      <div class="mh-t">PROPUESTA DE INTERVENCION RD</div>
      <div class="mh-s">Documentacion de intervencion en terreno &middot; {escape(nombre)}</div>
    </div>
  </div>
  <div class="org">
    <div class="org-t">ORGANIZACION RD</div>
    <div class="org-b">Reduciendo Dano Chile<br>reduciendo-dano.cl &middot; v4.1</div>
  </div>
</div>"""


def _html_pack(pack_id: str, brief: dict[str, str], tema_id: str = "dark") -> str:
    ev = ev_desde_pack(pack_id, layout_mode="grid_2x")
    nombre = str(ev.get("pack_label", pack_id))
    vol = int(ev.get("voluntarios", 0) or 0)
    testeo = bool(ev.get("incluye_testeo", False))

    t = TEMAS_DOC.get(tema_id, TEMAS_DOC["dark"])
    svg = render_svg(ev, tema=tema_id)
    costos = calcular_costos(ev)
    reqs = reglas_rider(ev)
    val = validate_evento(ev)

    datos = "".join([
        _fila("Pack", nombre),
        _fila("Precio", _clp(costos["precio"])),
        _fila("Voluntarios", str(vol)),
        _fila("Superficie", f"{costos['m2']} m² · {costos['stands']} stand(s)"),
        _fila("Incluye testeo", "Si" if testeo else "No"),
        _fila("Layout", str(ev.get("layout_mode"))),
    ])
    rider_rows = "".join(f"<li>{escape(r)}</li>" for r in reqs)
    if costos["desglose"]:
        costos_rows = "".join(
            _fila(f"{item['label']} ({item['pct']}%)", _clp(item["monto"]), num=True)
            for item in costos["desglose"]
        )
    else:
        costos_rows = _fila(nombre, _clp(costos["precio"]), num=True)
    val_html = ""
    if val["warnings"]:
        val_html = "<p class='warn'>Advertencias: " + "; ".join(escape(w) for w in val["warnings"]) + "</p>"

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:12mm 12mm; }}
* {{ box-sizing:border-box; }}
body {{ font-family:Inter,Arial,sans-serif; color:{t['text']}; background:{t['bg']}; font-size:11px; margin:0; }}
.mh {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:3px solid {t['accent']}; padding-bottom:8px; margin-bottom:12px; }}
.mh-l {{ display:flex; align-items:center; gap:12px; }}
.logo {{ display:inline-flex; align-items:center; }}
.mh-t {{ font-family:Bahnschrift,Arial; font-size:17px; font-weight:800; letter-spacing:.5px; }}
.mh-s {{ color:{t['muted']}; font-size:9.5px; }}
.org {{ border:1px solid {t['borde']}; border-radius:4px; padding:5px 9px; text-align:right; }}
.org-t {{ font-size:9px; font-weight:700; letter-spacing:1px; color:{t['accent']}; }}
.org-b {{ font-size:9px; color:{t['muted']}; line-height:1.35; }}
h2 {{ font-size:12.5px; margin:13px 0 6px; color:{t['accent']}; border-bottom:1px solid {t['borde']}; padding-bottom:2px; letter-spacing:.3px; }}
p {{ line-height:1.45; margin:0 0 6px; text-align:justify; }}
table {{ border-collapse:collapse; width:100%; margin:4px 0 8px; }}
th, td {{ border:1px solid {t['borde']}; padding:4px 8px; text-align:left; vertical-align:top; }}
th {{ background:{t['th']}; width:42%; font-weight:600; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.reqs {{ column-count:2; column-gap:20px; margin:4px 0 8px; padding:0; list-style:none; }}
.reqs li {{ break-inside:avoid; line-height:1.4; margin-bottom:5px; padding-left:18px; position:relative; }}
.reqs li::before {{ content:""; position:absolute; left:0; top:2px; width:11px; height:11px; border:1.5px solid {t['accent']}; border-radius:2px; }}
.total {{ font-size:14px; font-weight:800; color:{t['total']}; margin-top:4px; }}
.warn {{ color:{t['accent']}; font-size:9.5px; opacity:.85; }}
.map {{ border:1px solid {t['borde']}; border-radius:6px; padding:6px; text-align:center; background:{t['panel']}; }}
.map svg {{ max-width:100%; height:auto; }}
.foot {{ margin-top:10px; color:{t['muted']}; font-size:9px; border-top:1px solid {t['borde']}; padding-top:4px; }}
</style></head><body>
{_masthead(t, nombre)}

<h2>1. Quienes Somos</h2>
<p>{escape(brief['quienes'])}</p>
<h2>2. Objetivo del Servicio</h2>
<p>{escape(brief['objetivo'])}</p>

<h2>3. Datos del Evento</h2>
<table>{datos}</table>
{val_html}

<h2>4. Plano del Stand</h2>
<div class="map">{svg}</div>

<h2>5. Rider &mdash; Necesidades Operativas</h2>
<ul class="reqs">{rider_rows}</ul>

<h2>6. Cotizacion</h2>
<table>{costos_rows}</table>
<p class="total">TOTAL: {_clp(costos['total'])}</p>
<p class="warn">Precio plano por pack de servicio RD (no por hora/voluntario).</p>

<p class="foot">Generado por flujo.plano (motor unico). Fines preventivos, educativos y de reduccion de riesgos. Reduciendo Dano Chile.</p>
</body></html>"""


def _render_pdf(html: str, out_pdf: Path) -> bool:
    tmp = Path(tempfile.gettempdir()) / f"_propuesta_{out_pdf.stem}.html"
    tmp.write_text(html, encoding="utf-8")
    udd = Path(tempfile.gettempdir()) / "_propuesta_edge"
    subprocess.run(
        [_edge(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--print-to-pdf-no-header", f"--user-data-dir={udd}",
         f"--print-to-pdf={os.path.abspath(out_pdf)}", tmp.as_uri()],
        check=False,
    )
    return out_pdf.exists()


def main() -> None:
    args = [a for a in sys.argv[1:]]
    out_dir = _REPO / "_entregas"
    if "--out" in args:
        i = args.index("--out")
        out_dir = Path(args[i + 1])
        del args[i:i + 2]
    packs = [a.upper() for a in args if a.upper() in PACK_IDS] or PACK_IDS
    out_dir.mkdir(parents=True, exist_ok=True)

    brief = _brief_secciones()
    if not brief["quienes"] or not brief["objetivo"]:
        raise SystemExit(f"No pude extraer el brief de {_BRIEF_TXT}")

    temas = [a for a in args if a in TEMAS_DOC] or list(TEMAS_DOC)
    ok = 0
    total = len(packs) * len(temas)
    for tema in temas:
        for pack_id in packs:
            out_pdf = out_dir / f"propuesta_{pack_id.lower()}_{tema}.pdf"
            if _render_pdf(_html_pack(pack_id, brief, tema), out_pdf):
                print(f"OK  {out_pdf}")
                ok += 1
            else:
                print(f"FALLO  {out_pdf}")
    print(f"\n{ok}/{total} PDFs en {out_dir}")


if __name__ == "__main__":
    main()
