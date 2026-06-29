#!/usr/bin/env python3
"""
Generador maestro de flyers Suplementos RD.

Entrada:
  01_contenido/contenido_suplementos_rd.json

Salidas:
  02_editables_svg/           -> SVG con texto vivo/editable para Illustrator
  03_final_vectorizado_svg/   -> SVG con texto convertido a trazados/path
  04_preview/preview_flyers.html
  05_exports/*.zip

Formato: 2000 x 2800 px, equivalente proporcional a 10 x 14 cm (Vertical).
"""
from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath

from functools import lru_cache


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "01_contenido" / "contenido_suplementos_rd.json"
EDIT_DIR = ROOT / "02_editables_svg"
VEC_DIR = ROOT / "03_final_vectorizado_svg"
PREVIEW_DIR = ROOT / "04_preview"
EXPORT_DIR = ROOT / "05_exports"

W, H = 2000, 2800
FONT_REG = "arial.ttf"
FONT_BOLD = "arialbd.ttf"
FONT_FAMILY = "DejaVu Sans, Arial, Helvetica, sans-serif"


def load_data():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dirs():
    for d in [EDIT_DIR, VEC_DIR, PREVIEW_DIR, EXPORT_DIR]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=10)
def fp(weight="regular"):
    return FontProperties(family="DejaVu Sans", weight="bold" if weight=="bold" else "normal")


def text_width(s: str, size: float, weight="regular") -> float:
    if not s:
        return 0.0
    w = 0.0
    for char in s:
        if char.isupper():
            w += 0.85 * size if char in 'WM' else 0.72 * size
        elif char.islower():
            w += 0.77 * size if char in 'wm' else 0.33 * size if char in 'ijl' else 0.57 * size
        elif char.isdigit():
            w += 0.55 * size
        elif char in ' .,;:!?':
            w += 0.35 * size
        else:
            w += 0.55 * size
    return w


def wrap_line(text: str, max_width: float, size: float, weight="regular"):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = word if not cur else cur + " " + word
        if text_width(test, size, weight) <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}{op}{extra}/>'


def circle(cx, cy, r, fill, opacity=None, stroke=None, sw=1):
    op = f' opacity="{opacity}"' if opacity is not None else ""
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}{op}/>'


def line(x1, y1, x2, y2, stroke, sw=1, opacity=None):
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{op}/>'


def svg_open(metadata=""):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}px" height="{H}px" viewBox="0 0 {W} {H}">',
        f'<metadata>{html.escape(metadata)}</metadata>'
    ]


# -----------------------------
# Editable SVG text helpers
# -----------------------------
def add_edit_text(svg, text, x, y, size=40, fill="#161513", weight="regular", max_width=None, line_height=None, bullet=False, indent=0, cls="txt"):
    line_height = line_height or size * 1.28
    fw = "700" if weight == "bold" else "400"
    cy = y
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            cy += line_height * .55
            continue
        lines = wrap_line(para, max_width - indent, size, weight) if max_width else [para]
        for i, txt in enumerate(lines):
            tx = x + (indent if i > 0 else 0)
            if bullet and i == 0:
                svg.append(f'<text x="{x}" y="{cy + size}" fill="{fill}" font-family="{FONT_FAMILY}" font-size="{size}" font-weight="700">•</text>')
                tx = x + indent
            svg.append(
                f'<text class="{cls}" x="{tx}" y="{cy + size}" fill="{fill}" '
                f'font-family="{FONT_FAMILY}" font-size="{size}" font-weight="{fw}">{html.escape(txt)}</text>'
            )
            cy += line_height
    return cy


# -----------------------------
# Vectorized text helpers
# -----------------------------
@lru_cache(maxsize=10000)
def path_d_for_text(text, x, baseline_y, size, fill, weight="regular"):
    tp = TextPath((0, 0), text, size=size, prop=fp(weight))
    verts = tp.vertices
    codes = tp.codes
    if codes is None:
        return ""
    parts = []
    i = 0
    while i < len(codes):
        code = codes[i]
        vx, vy = verts[i]
        X, Y = x + vx, baseline_y - vy
        if code == MplPath.MOVETO:
            parts.append(f"M {X:.3f} {Y:.3f}")
        elif code == MplPath.LINETO:
            parts.append(f"L {X:.3f} {Y:.3f}")
        elif code == MplPath.CURVE3:
            if i + 1 < len(codes):
                vx2, vy2 = verts[i + 1]
                parts.append(f"Q {X:.3f} {Y:.3f} {x + vx2:.3f} {baseline_y - vy2:.3f}")
                i += 1
        elif code == MplPath.CURVE4:
            if i + 2 < len(codes):
                vx2, vy2 = verts[i + 1]
                vx3, vy3 = verts[i + 2]
                parts.append(f"C {X:.3f} {Y:.3f} {x + vx2:.3f} {baseline_y - vy2:.3f} {x + vx3:.3f} {baseline_y - vy3:.3f}")
                i += 2
        elif code == MplPath.CLOSEPOLY:
            parts.append("Z")
        i += 1
    return f'<path d="{" ".join(parts)}" fill="{fill}"/>'


def add_vec_text(svg, text, x, y, size=40, fill="#161513", weight="regular", max_width=None, line_height=None, bullet=False, indent=0):
    line_height = line_height or size * 1.28
    cy = y
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            cy += line_height * .55
            continue
        lines = wrap_line(para, max_width - indent, size, weight) if max_width else [para]
        for i, txt in enumerate(lines):
            tx = x + (indent if i > 0 else 0)
            if bullet and i == 0:
                svg.append(path_d_for_text("•", x, cy + size, size, fill, "bold"))
                tx = x + indent
            svg.append(path_d_for_text(txt, tx, cy + size, size, fill, weight))
            cy += line_height
    return cy


# -----------------------------
# Shared composition
# -----------------------------
def panel(x, y, w, h, colors, dark=False):
    fill = colors["green"] if dark else colors["white"]
    opacity = ".94" if dark else ".64"
    stroke = colors["white"] if dark else colors["line"]
    return rect(x, y, w, h, fill, rx=44, stroke=stroke, sw=3, opacity=opacity)


def add_background(svg, colors, accent):
    svg.append('<g id="fondo_editable">')
    svg.append(rect(0, 0, W, H, colors["cream"]))
    svg.append(circle(300, 300, 380, accent, opacity=".16"))
    svg.append(circle(1700, 200, 330, colors["blue"], opacity=".08"))
    svg.append(circle(1900, 2650, 410, "none", opacity=".14", stroke=colors["green"], sw=90))
    svg.append(circle(-40, 2400, 230, accent, opacity=".10"))
    svg.append('</g>')
    svg.append('<g id="marco_y_decoracion_editable">')
    svg.append(rect(70, 70, 1860, 2660, "none", rx=70, stroke="#CFC2B2", sw=4, opacity=".7"))
    svg.append(f'<rect x="1600" y="210" width="210" height="92" rx="46" fill="{accent}" stroke="{colors["ink"]}" stroke-width="6" transform="rotate(-14 1705 256)" opacity=".92"/>')
    svg.append(f'<rect x="1435" y="315" width="158" height="76" rx="38" fill="{colors["yellow"]}" stroke="{colors["ink"]}" stroke-width="5" transform="rotate(18 1514 353)" opacity=".86"/>')
    svg.append('</g>')


def add_header(svg, flyer, project, colors, accent, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg.append('<g id="header_marca">')
    svg.append(rect(120, 105, 74, 74, colors["green"], rx=24))
    add_text(svg, "RD", 136, 119, size=34, fill=colors["white"], weight="bold")
    add_text(svg, project["brand"], 215, 119, size=42, fill=colors["ink"], weight="bold")
    tag = flyer["tag"].upper()
    tag_w = max(360, text_width(tag, 24, "bold") + 70)
    svg.append(rect(W - 120 - tag_w, 116, tag_w, 60, colors["white"], rx=30, stroke=colors["line"], sw=2, opacity=".7"))
    add_text(svg, tag, W - 120 - tag_w + 35, 124, size=24, fill=accent, weight="bold")
    svg.append('</g>')


def add_title(svg, flyer, colors, accent, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg.append('<g id="titulo">')
    label = "LÍNEA" if flyer["type"] == "general" else "PRODUCTO"
    add_text(svg, label, 120, 260, size=27, fill=accent, weight="bold")
    ty = 305
    title_size = 85 if len(flyer["title"]) < 23 else 75
    for title_line in wrap_line(flyer["title"], 1760, title_size, "bold"):
        add_text(svg, title_line, 120, ty, size=title_size, fill=colors["ink"], weight="bold")
        ty += title_size * 1.05
    if flyer.get("subtitle"):
        add_text(svg, flyer["subtitle"], 120, max(510, ty + 10), size=54, fill=accent, weight="bold")
    svg.append('</g>')


def add_footer(svg, project, colors, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg.append('<g id="footer">')
    svg.append(line(120, 2640, 1880, 2640, colors["line"], sw=5))
    add_text(svg, project["website"], 120, 2670, size=46, fill=colors["green"], weight="bold")
    add_text(svg, project["footer"], 1060, 2676, size=22, fill=colors["muted"], weight="bold", max_width=820, line_height=28)
    svg.append('</g>')


def make_base(flyer, project, colors, mode):
    accent = colors[flyer["accent"]]
    svg = svg_open(f"{flyer['id']} / {mode} / 2000x2800 px")
    add_background(svg, colors, accent)
    add_header(svg, flyer, project, colors, accent, mode)
    add_title(svg, flyer, colors, accent, mode)
    return svg, accent


def finish(svg, project, colors, out_path, mode):
    add_footer(svg, project, colors, mode)
    svg.append("</svg>")
    out_path.write_text("\n".join(svg), encoding="utf-8")


def render_general(flyer, project, colors, out_dir, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg, accent = make_base(flyer, project, colors, mode)
    svg.append('<g id="cajas_editables">')
    svg.append(panel(120, 600, 1760, 500, colors, dark=True))
    svg.append(panel(120, 1160, 1760, 1360, colors, dark=False))
    svg.append('</g>')
    svg.append('<g id="contenido_texto">')
    add_text(svg, "Descripción", 175, 645, size=35, fill=colors["yellow"], weight="bold")
    y = 719
    for para in flyer["description"]:
        y = add_text(svg, para, 175, y, size=37, fill=colors["white"], weight="regular", max_width=1650, line_height=52)
        y += 42
    add_text(svg, flyer["section_title"], 175, 1210, size=38, fill=accent, weight="bold")
    y = 1280
    for item in flyer["items"]:
        y = add_text(svg, item, 175, y, size=30, fill=colors["ink"], weight="regular", max_width=1650, line_height=42, bullet=True, indent=34)
        y += 17
    svg.append('</g>')
    suffix = "editable" if mode == "editable" else "vectorizado"
    finish(svg, project, colors, out_dir / f"{flyer['id']}_{suffix}.svg", mode)


def render_product(flyer, project, colors, out_dir, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg, accent = make_base(flyer, project, colors, mode)
    svg.append('<g id="cajas_editables">')
    svg.append(panel(120, 660, 1760, 880, colors, dark=False))
    svg.append(panel(120, 1600, 1760, 920, colors, dark=False))
    svg.append('</g>')
    svg.append('<g id="contenido_texto">')
    add_text(svg, flyer.get("description_title", "Descripción"), 185, 715, size=38, fill=accent, weight="bold")
    desc_size = 32 if flyer["id"] == "06_creatina_monohidratada" else 37
    y = 785
    for para in flyer["description"]:
        y = add_text(svg, para, 185, y, size=desc_size, fill=colors["ink"], weight="regular", max_width=1630, line_height=desc_size * 1.38)
        y += 32
    add_text(svg, flyer["section_title"], 185, 1655, size=38, fill=accent, weight="bold")
    item_size = 33 if len(flyer["items"]) <= 3 else 30
    if flyer["id"] == "06_creatina_monohidratada":
        item_size = 30
    y = 1725
    for item in flyer["items"]:
        y = add_text(svg, item, 185, y, size=item_size, fill=colors["ink"], weight="regular", max_width=1630, line_height=item_size * 1.35, bullet=True, indent=42)
        y += 35
    svg.append('</g>')
    suffix = "editable" if mode == "editable" else "vectorizado"
    finish(svg, project, colors, out_dir / f"{flyer['id']}_{suffix}.svg", mode)


def render_protein(flyer, project, colors, out_dir, mode):
    add_text = add_edit_text if mode == "editable" else add_vec_text
    svg, accent = make_base(flyer, project, colors, mode)
    svg.append('<g id="cajas_editables">')
    svg.append(panel(120, 660, 1760, 480, colors, dark=False))
    svg.append(panel(120, 1200, 1760, 580, colors, dark=False))
    svg.append(panel(120, 1840, 1760, 580, colors, dark=False))
    svg.append(rect(120, 2480, 1760, 100, colors["green"], rx=34, opacity=".96"))
    svg.append('</g>')
    svg.append('<g id="contenido_texto">')
    add_text(svg, flyer.get("description_title", "Descripción"), 185, 710, size=34, fill=accent, weight="bold")
    y = 770
    for para in flyer["description"]:
        y = add_text(svg, para, 185, y, size=31, fill=colors["ink"], weight="regular", max_width=1630, line_height=41)
        y += 20
    add_text(svg, flyer["versions"][0]["title"], 185, 1250, size=34, fill=accent, weight="bold")
    add_text(svg, flyer["versions"][0]["body"], 185, 1310, size=29, fill=colors["ink"], weight="regular", max_width=1630, line_height=39)
    add_text(svg, flyer["versions"][1]["title"], 185, 1890, size=34, fill=accent, weight="bold")
    add_text(svg, flyer["versions"][1]["body"], 185, 1950, size=29, fill=colors["ink"], weight="regular", max_width=1630, line_height=39)
    add_text(svg, flyer["usage_title"], 170, 2515, size=28, fill=colors["yellow"], weight="bold")
    add_text(svg, flyer["usage"], 490, 2515, size=24, fill=colors["white"], weight="regular", max_width=1350, line_height=29)
    svg.append('</g>')
    suffix = "editable" if mode == "editable" else "vectorizado"
    finish(svg, project, colors, out_dir / f"{flyer['id']}_{suffix}.svg", mode)


def render_all(data):
    project, colors = data["project"], data["palette"]
    for mode, out_dir in [("editable", EDIT_DIR), ("vector", VEC_DIR)]:
        for flyer in data["flyers"]:
            if flyer["type"] == "general":
                render_general(flyer, project, colors, out_dir, mode)
            elif flyer["type"] == "protein":
                render_protein(flyer, project, colors, out_dir, mode)
            else:
                render_product(flyer, project, colors, out_dir, mode)


def write_preview(data):
    cards = []
    for flyer in data["flyers"]:
        edit_name = f"../02_editables_svg/{flyer['id']}_editable.svg"
        vec_name = f"../03_final_vectorizado_svg/{flyer['id']}_vectorizado.svg"
        cards.append(f"""
        <article class="card">
          <h2>{html.escape(flyer['title'])}</h2>
          <iframe src="{edit_name}" title="{html.escape(flyer['title'])}"></iframe>
          <div class="links">
            <a href="{edit_name}">SVG editable</a>
            <a href="{vec_name}">SVG vectorizado</a>
          </div>
        </article>""")
    preview = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preview Flyers Suplementos RD</title>
<style>
  body {{ margin:0; font-family:Arial, sans-serif; background:#e2d7c8; color:#161513; }}
  header {{ position:sticky; top:0; z-index:10; background:#161513; color:#fff; padding:18px 24px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header p {{ margin:6px 0 0; color:#d8cec2; }}
  main {{ max-width:1280px; margin:28px auto; padding:0 18px; display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:28px; }}
  .card {{ background:#fff8ed; border-radius:18px; padding:16px; box-shadow:0 18px 50px rgba(0,0,0,.18); }}
  .card h2 {{ margin:0 0 12px; font-size:20px; }}
  iframe {{ width:100%; aspect-ratio:1/1.4; border:1px solid #d9cec0; border-radius:12px; background:white; }}
  .links {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
  a {{ background:#161513; color:white; text-decoration:none; padding:10px 13px; border-radius:999px; font-weight:700; font-size:14px; }}
</style>
</head>
<body>
<header>
  <h1>Preview Flyers Suplementos RD · 2000×2800 px</h1>
  <p>Vista editable. Los archivos finales vectorizados están enlazados en cada tarjeta.</p>
</header>
<main>
{''.join(cards)}
</main>
</body>
</html>"""
    (PREVIEW_DIR / "preview_flyers.html").write_text(preview, encoding="utf-8")


def write_readme(data):
    readme = f"""# Flujo optimizado · Suplementos RD

Formato de trabajo: **2000 × 2800 px**, proporción equivalente a **10 × 14 cm**.

## Carpetas

- `01_contenido/`: texto maestro aprobado en JSON.
- `02_editables_svg/`: SVG con texto vivo/editable para Illustrator.
- `03_final_vectorizado_svg/`: SVG con texto convertido a trazados/path. Ideal para entrega final o imprenta.
- `04_preview/`: HTML para revisar visualmente todos los flyers.
- `05_exports/`: ZIPs listos para compartir.
- `scripts/`: generador automático.

## Cómo editar el flujo

1. Cambia textos, títulos o colores en:
   `01_contenido/contenido_suplementos_rd.json`
2. Regenera todo ejecutando:
   `python3 scripts/generar_flyers.py`
3. Abre en Illustrator los archivos de:
   `02_editables_svg/`
4. Cuando el diseño esté aprobado, usa los archivos de:
   `03_final_vectorizado_svg/`

## Illustrator

- Para cambiar fondos o colores: edita los grupos `fondo_editable`, `marco_y_decoracion_editable` y `cajas_editables`.
- Para editar textos: usa los SVG de `02_editables_svg`.
- Para evitar problemas de fuentes en la entrega: usa los SVG de `03_final_vectorizado_svg`.

## Nota

Post Fiesta está incluido en el flyer general, pero todavía no existe ficha individual porque falta su texto completo.
"""
    (ROOT / "README_FLUJO_OPTIMIZADO.md").write_text(readme, encoding="utf-8")


import zipfile


def zip_dir(src: Path, zip_name: str):
    zip_path = EXPORT_DIR / zip_name
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in src.rglob('*'):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(src))


def make_exports():
    zip_dir(EDIT_DIR, "suplementos_rd_editables_svg_2000x2800.zip")
    zip_dir(VEC_DIR, "suplementos_rd_vectorizados_svg_2000x2800.zip")
    # ZIP completo ordenado
    full = EXPORT_DIR / "suplementos_rd_flujo_completo_2000x2800.zip"
    if full.exists():
        full.unlink()
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in ["01_contenido", "02_editables_svg", "03_final_vectorizado_svg", "04_preview"]:
            for file_path in (ROOT / folder).rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(ROOT))
        readme_file = ROOT / "README_FLUJO_OPTIMIZADO.md"
        if readme_file.exists():
            zipf.write(readme_file, "README_FLUJO_OPTIMIZADO.md")


def main():
    data = load_data()
    ensure_dirs()
    render_all(data)
    write_preview(data)
    write_readme(data)
    make_exports()
    print("OK: flujo optimizado generado")
    print(f"- Editables: {len(list(EDIT_DIR.glob('*.svg')))} SVG")
    print(f"- Vectorizados: {len(list(VEC_DIR.glob('*.svg')))} SVG")
    print(f"- Preview: {PREVIEW_DIR / 'preview_flyers.html'}")
    print(f"- Exports: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
