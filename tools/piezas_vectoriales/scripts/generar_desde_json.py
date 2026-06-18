#!/usr/bin/env python3
"""
Generador genérico de piezas gráficas desde JSON.

Sirve para crear flyers, etiquetas, tarjetas, stickers o cualquier formato rectangular.
Genera dos salidas:
  1) SVG editable con texto vivo
  2) SVG final con textos vectorizados como paths

Uso:
  python3 00_sistema_generico/scripts/generar_desde_json.py 00_sistema_generico/proyectos/etiquetas_ejemplo/config.json
"""
from __future__ import annotations

import html
import json
import shutil
import sys
import zipfile
from pathlib import Path

from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath

ROOT = Path.cwd()
FONT_FAMILY = "DejaVu Sans, Arial, Helvetica, sans-serif"


def _find_font(weight_hint="regular"):
    """Busca una fuente sans-serif del sistema. Prefiere fuentes probadas con TextPath."""
    preferred = [
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("DejaVu Sans", "DejaVu Sans Bold"),
        ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
        ("Arial.ttf", "Arial Bold.ttf"),
        ("FreeSans.ttf", "FreeSansBold.ttf"),
    ]

    for reg_name, bold_name in preferred:
        target = bold_name if weight_hint == "bold" else reg_name
        for font in fontManager.ttflist:
            fname = font.fname
            if not fname.lower().endswith(".ttf"):
                continue
            if target.lower() in fname.lower() or target.lower() in font.name.lower():
                return fname

    # fallback: primera fuente sans-serif que no parezca display/símbolos
    for font in fontManager.ttflist:
        fname = font.fname.lower()
        if fname.endswith(".ttf") and "sans" in font.name.lower() and "display" not in fname and "math" not in fname:
            return font.fname

    raise RuntimeError("No se encontró ninguna fuente TTF sans-serif en el sistema.")


FONT_REG = _find_font("regular")
FONT_BOLD = _find_font("bold") if any("bold" in f.name.lower() for f in fontManager.ttflist) else FONT_REG


def fp(weight="regular"):
    return FontProperties(fname=FONT_BOLD if weight == "bold" else FONT_REG)


def text_width(s: str, size: float, weight="regular") -> float:
    if not s:
        return 0
    tp = TextPath((0, 0), s, size=size, prop=fp(weight))
    return max(0, tp.get_extents().width)


def wrap_line(text: str, max_width: float, size: float, weight="regular"):
    words = str(text).split()
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


def path_d_for_text(text, x, baseline_y, size, fill, weight="regular"):
    import numpy as np
    tp = TextPath((0, 0), str(text), size=size, prop=fp(weight))
    verts = np.asarray(tp.vertices)
    codes = np.asarray(tp.codes) if tp.codes is not None else None
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
        elif code == MplPath.CURVE3 and i + 1 < len(codes):
            vx2, vy2 = verts[i + 1]
            parts.append(f"Q {X:.3f} {Y:.3f} {x + vx2:.3f} {baseline_y - vy2:.3f}")
            i += 1
        elif code == MplPath.CURVE4 and i + 2 < len(codes):
            vx2, vy2 = verts[i + 1]
            vx3, vy3 = verts[i + 2]
            parts.append(f"C {X:.3f} {Y:.3f} {x + vx2:.3f} {baseline_y - vy2:.3f} {x + vx3:.3f} {baseline_y - vy3:.3f}")
            i += 2
        elif code == MplPath.CLOSEPOLY:
            parts.append("Z")
        i += 1
    return f'<path d="{" ".join(parts)}" fill="{fill}"/>'


def esc(s):
    return html.escape(str(s), quote=True)


def color(value, palette):
    if value is None:
        return "none"
    return palette.get(value, value)


def _autofit_size(el):
    """Ajusta el tamaño de fuente para que el texto entre en la caja.

    Solo si el elemento pide autofit y no está locked. Usa la medición real
    (text_width / TextPath) para decidir. Respeta min_size y max_height.
    """
    if el.get("locked") or not el.get("autofit"):
        return el
    max_width = el.get("max_width")
    if not max_width:
        return el
    size = float(el.get("size", 40))
    weight = el.get("weight", "regular")
    lh_ratio = (el["line_height"] / size) if el.get("line_height") and size else 1.28
    min_size = float(el.get("min_size") or max(8.0, size * 0.5))
    max_height = el.get("max_height")
    content = str(el.get("content", ""))
    cur = size
    step = 2.0

    def longest_word_fits(s):
        for word in content.replace("\n", " ").split():
            if max_width and text_width(word, s, weight) > max_width:
                return False
        return True

    while cur > min_size and not longest_word_fits(cur):
        cur -= step

    if max_height and max_height > 0:
        while cur > min_size:
            # alto envuelto a tamaño cur
            total = 0.0
            for para in content.split("\n"):
                para = para.strip()
                if not para:
                    total += cur * lh_ratio * 0.55
                    continue
                lines = wrap_line(para, max_width, cur, weight) if max_width else [para]
                total += len(lines) * cur * lh_ratio
            if total <= max_height:
                break
            cur -= step
        cur = max(cur, min_size)

    if cur != size:
        el = dict(el)
        el["size"] = round(cur, 2)
        el["line_height"] = round(cur * lh_ratio, 2)
    return el


def add_text(svg, el, palette, mode):
    el = _autofit_size(el)
    fill = color(el.get("fill", "ink"), palette)
    size = el.get("size", 40)
    weight = el.get("weight", "regular")
    line_height = el.get("line_height", size * 1.28)
    max_width = el.get("max_width")
    x = el.get("x", 0)
    y = el.get("y", 0)
    content = el.get("content", "")
    indent = el.get("indent", 0)
    bullet = el.get("bullet", False)
    cls = el.get("class", "txt")

    paragraphs = str(content).split("\n")
    cy = y
    fw = "700" if weight == "bold" else "400"
    for para in paragraphs:
        para = para.strip()
        if not para:
            cy += line_height * .55
            continue
        lines = wrap_line(para, max_width - indent, size, weight) if max_width else [para]
        for idx, line in enumerate(lines):
            tx = x + (indent if idx > 0 else 0)
            if bullet and idx == 0:
                if mode == "editable":
                    svg.append(f'<text x="{x}" y="{cy + size}" fill="{fill}" font-family="{FONT_FAMILY}" font-size="{size}" font-weight="700">•</text>')
                else:
                    svg.append(path_d_for_text("•", x, cy + size, size, fill, "bold"))
                tx = x + indent
            if mode == "editable":
                svg.append(f'<text class="{esc(cls)}" x="{tx}" y="{cy + size}" fill="{fill}" font-family="{FONT_FAMILY}" font-size="{size}" font-weight="{fw}">{esc(line)}</text>')
            else:
                svg.append(path_d_for_text(line, tx, cy + size, size, fill, weight))
            cy += line_height
    return cy


def render_element(svg, el, palette, mode):
    t = el.get("type")
    opacity = f' opacity="{el["opacity"]}"' if "opacity" in el else ""
    if t == "rect" or t == "panel":
        fill = color(el.get("fill", "none"), palette)
        stroke = el.get("stroke")
        stroke_attr = f' stroke="{color(stroke, palette)}" stroke-width="{el.get("stroke_width", 1)}"' if stroke else ""
        svg.append(f'<rect x="{el.get("x",0)}" y="{el.get("y",0)}" width="{el.get("w",100)}" height="{el.get("h",100)}" rx="{el.get("radius",0)}" fill="{fill}"{stroke_attr}{opacity}/>' )
    elif t == "circle":
        fill = color(el.get("fill", "none"), palette)
        stroke = el.get("stroke")
        stroke_attr = f' stroke="{color(stroke, palette)}" stroke-width="{el.get("stroke_width", 1)}"' if stroke else ""
        svg.append(f'<circle cx="{el.get("cx",0)}" cy="{el.get("cy",0)}" r="{el.get("r",50)}" fill="{fill}"{stroke_attr}{opacity}/>' )
    elif t == "line":
        svg.append(f'<line x1="{el.get("x1",0)}" y1="{el.get("y1",0)}" x2="{el.get("x2",0)}" y2="{el.get("y2",0)}" stroke="{color(el.get("stroke", "ink"), palette)}" stroke-width="{el.get("stroke_width", 1)}"{opacity}/>' )
    elif t == "text" or t == "paragraph":
        add_text(svg, el, palette, mode)
    elif t == "list":
        y = el.get("y", 0)
        gap = el.get("gap", 18)
        for item in el.get("items", []):
            item_el = dict(el)
            item_el["type"] = "paragraph"
            item_el["content"] = item
            item_el["y"] = y
            item_el["bullet"] = True
            y = add_text(svg, item_el, palette, mode) + gap
    elif t == "group_label":
        svg.append(f'<!-- {esc(el.get("label", "grupo"))} -->')
    else:
        svg.append(f'<!-- elemento no reconocido: {esc(t)} -->')


def render_document(doc, cfg, out_dir: Path, mode: str):
    palette = cfg.get("palette", {})
    canvas = cfg.get("canvas", {})
    w, h = canvas.get("width", 1000), canvas.get("height", 1000)
    suffix = "editable" if mode == "editable" else "vectorizado"
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}px" height="{h}px" viewBox="0 0 {w} {h}">',
        f'<metadata>{esc(cfg.get("project", {}).get("name", "Proyecto"))} / {esc(doc.get("id", "documento"))} / {suffix}</metadata>'
    ]

    # Fondo por defecto
    bg = doc.get("background", cfg.get("background", "cream"))
    svg.append(f'<g id="fondo_editable"><rect x="0" y="0" width="{w}" height="{h}" fill="{color(bg, palette)}"/></g>')

    # Elementos globales + documento
    layers = [
        ("elementos_globales", cfg.get("global_elements", [])),
        ("elementos_documento", doc.get("elements", []))
    ]
    for layer_name, elements in layers:
        svg.append(f'<g id="{esc(layer_name)}">')
        for el in elements:
            # variables simples por documento
            el = json.loads(json.dumps(el))
            for key, val in list(el.items()):
                if isinstance(val, str):
                    el[key] = val.format(**doc, **cfg.get("project", {}))
            render_element(svg, el, palette, mode)
        svg.append('</g>')
    svg.append('</svg>')
    out = out_dir / f'{doc.get("id", "documento")}_{suffix}.svg'
    out.write_text("\n".join(svg), encoding="utf-8")


def write_preview(cfg, edit_dir, vec_dir, preview_dir):
    cards = []
    for doc in cfg.get("documents", []):
        did = doc.get("id", "documento")
        title = doc.get("title", did)
        cards.append(f'''
        <article class="card">
          <h2>{esc(title)}</h2>
          <iframe src="../01_editables_svg/{did}_editable.svg"></iframe>
          <p><a href="../01_editables_svg/{did}_editable.svg">Editable</a> <a href="../02_vectorizados_svg/{did}_vectorizado.svg">Vectorizado</a></p>
        </article>''')
    html_doc = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Preview</title>
<style>body{{margin:0;background:#ddd2c3;font-family:Arial,sans-serif;color:#161513}}header{{background:#161513;color:white;padding:18px 24px}}main{{max-width:1200px;margin:24px auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px;padding:0 16px}}.card{{background:#fff8ed;border-radius:18px;padding:16px;box-shadow:0 14px 40px rgba(0,0,0,.16)}}iframe{{width:100%;aspect-ratio:{cfg.get("canvas",{}).get("width",1)}/{cfg.get("canvas",{}).get("height",1)};border:1px solid #ccc;border-radius:10px;background:white}}a{{display:inline-block;background:#161513;color:white;text-decoration:none;padding:8px 12px;border-radius:999px;font-weight:700}}</style></head><body><header><h1>{esc(cfg.get("project",{}).get("name","Preview"))}</h1><p>Editable + vectorizado</p></header><main>{''.join(cards)}</main></body></html>'''
    (preview_dir / "preview.html").write_text(html_doc, encoding="utf-8")


def zip_folder(folder: Path, zip_path: Path):
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in folder.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(folder))


def zip_files(base_dir: Path, zip_path: Path, relative_paths: list):
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for rel in relative_paths:
            p = base_dir / rel
            if p.is_file():
                zf.write(p, rel)
            elif p.is_dir():
                for item in p.rglob("*"):
                    if item.is_file() and item.suffix.lower() != ".zip":
                        zf.write(item, item.relative_to(base_dir))


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 generar_desde_json.py ruta/config.json")
        sys.exit(1)
    config_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    project_slug = cfg.get("project", {}).get("slug", config_path.parent.name)
    out_root = config_path.parent / "salida_generada"
    if out_root.exists():
        shutil.rmtree(out_root)
    edit_dir = out_root / "01_editables_svg"
    vec_dir = out_root / "02_vectorizados_svg"
    preview_dir = out_root / "03_preview"
    export_dir = out_root / "04_exports"
    for d in [edit_dir, vec_dir, preview_dir, export_dir]:
        d.mkdir(parents=True, exist_ok=True)

    for doc in cfg.get("documents", []):
        render_document(doc, cfg, edit_dir, "editable")
        render_document(doc, cfg, vec_dir, "vector")
    write_preview(cfg, edit_dir, vec_dir, preview_dir)
    zip_folder(edit_dir, export_dir / f"{project_slug}_editables_svg.zip")
    zip_folder(vec_dir, export_dir / f"{project_slug}_vectorizados_svg.zip")
    zip_files(config_path.parent, export_dir / f"{project_slug}_flujo_completo.zip", ["config.json", "salida_generada"])
    print(f"OK: generado en {out_root}")


if __name__ == "__main__":
    main()
