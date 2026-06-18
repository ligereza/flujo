"""Editor visual de piezas (Gradio) — parte del paquete flujo.

Reemplaza al script legacy `scripts/app.py` con un editor propio que:
  - Lista el catálogo de formatos (filtrable por área/medio/herramienta).
  - Carga un config.json (de una plantilla del catálogo o de un proyecto).
  - Permite editar datos básicos (título/subtítulo/cuerpo) y la PROPORCIÓN/DPI.
  - Muestra un PREVIEW SVG en vivo.
  - Exporta el SVG y/o guarda el nuevo config.json.

Diseñado para correr local (`flujo serve`). Toda la lógica pesada se reutiliza
de módulos ya testeados: render.formats, render.rescale, web.svg_preview.

Las funciones de estado son puras y testeables (no dependen de Gradio); la UI
solo las orquesta. Por eso `import gradio` es perezoso dentro de `build_app`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..paths import repo_root
from ..render.formats import list_formats, FormatInfo
from ..render.rescale import set_dpi, set_real_size, current_dpi
from .svg_preview import render_svg


# ============================================================
# Lógica pura (testeable sin Gradio)
# ============================================================

def catalog_choices(area: str = "", medio: str = "", herramienta: str = "") -> List[Tuple[str, str]]:
    """Devuelve [(label, id)] de formatos para un dropdown, con filtros."""
    out = []
    for f in list_formats(area, medio, herramienta):
        tag = " · ".join(x for x in (f.area, f.medio, f.herramienta) if x)
        size = "paramétrico" if f.parametrico else f"{f.width_cm:g}x{f.height_cm:g}cm"
        out.append((f"{f.id}  ({size})  [{tag}]", f.id))
    return out


def _format_by_id(fmt_id: str) -> Optional[FormatInfo]:
    for f in list_formats():
        if f.id == fmt_id:
            return f
    return None


def _load_template_config(fmt: FormatInfo) -> Dict:
    """Carga el config.json de plantilla del formato, o genera uno base."""
    repo = repo_root()
    if fmt.has_template:
        tpath = fmt.template if fmt.template.is_absolute() else repo / fmt.template
        if tpath.exists():
            try:
                return json.loads(tpath.read_text(encoding="utf-8"))
            except Exception:
                pass
    # Base mínima si no hay plantilla (formatos digitales nuevos / paramétricos)
    w = fmt.canvas_width or int(round(fmt.width_cm / 2.54 * 150))
    h = fmt.canvas_height or int(round(fmt.height_cm / 2.54 * 150))
    return {
        "project": {"name": fmt.id, "slug": fmt.id, "brand": "Marca"},
        "canvas": {
            "width": w, "height": h,
            "real_size_cm": {"width": fmt.width_cm, "height": fmt.height_cm},
            "safe_margin_px": max(40, int(min(w, h) * 0.04)),
        },
        "palette": {
            "paper": "#FFF8ED", "ink": "#161513", "muted": "#675F55",
            "line": "#D9CEC0", "accent": "#173F2F", "white": "#FFFFFF",
        },
        "background": "paper",
        "global_elements": [],
        "documents": [
            {
                "id": f"01_{fmt.id}",
                "title": fmt.id,
                "elements": [
                    {"type": "image", "src": "", "x": int(w*0.08), "y": int(h*0.08),
                     "w": int(w*0.84), "h": int(h*0.45)},
                    {"type": "text", "content": "TÍTULO", "x": int(w*0.08), "y": int(h*0.58),
                     "size": max(40, int(h*0.06)), "fill": "ink", "weight": "bold",
                     "max_width": int(w*0.84)},
                    {"type": "paragraph", "content": "Subtítulo / descripción.",
                     "x": int(w*0.08), "y": int(h*0.70), "size": max(24, int(h*0.03)),
                     "fill": "muted", "max_width": int(w*0.84)},
                ],
            }
        ],
    }


def _first_text_fields(config: Dict) -> Dict[str, str]:
    """Extrae los primeros text/paragraph como título/subtítulo/cuerpo editables."""
    fields = {"titulo": "", "subtitulo": "", "cuerpo": ""}
    keys = ["titulo", "subtitulo", "cuerpo"]
    i = 0
    for doc in config.get("documents", []):
        for el in doc.get("elements", []):
            if el.get("type") in ("text", "paragraph") and i < len(keys):
                fields[keys[i]] = str(el.get("content", ""))
                i += 1
    return fields


def _apply_text_fields(config: Dict, titulo: str, subtitulo: str, cuerpo: str) -> Dict:
    """Escribe título/subtítulo/cuerpo de vuelta en los primeros text/paragraph."""
    cfg = copy.deepcopy(config)
    vals = [titulo, subtitulo, cuerpo]
    i = 0
    for doc in cfg.get("documents", []):
        for el in doc.get("elements", []):
            if el.get("type") in ("text", "paragraph") and i < len(vals):
                if vals[i] != "":
                    el["content"] = vals[i]
                i += 1
    return cfg


def load_format_state(fmt_id: str) -> Tuple[Dict, str, Dict[str, str]]:
    """Carga un formato: devuelve (config, svg_preview, campos_texto)."""
    fmt = _format_by_id(fmt_id)
    if not fmt:
        empty = {"canvas": {"width": 800, "height": 600}, "documents": []}
        return empty, render_svg(empty), {"titulo": "", "subtitulo": "", "cuerpo": ""}
    cfg = _load_template_config(fmt)
    return cfg, render_svg(cfg, show_safe_area=True), _first_text_fields(cfg)


def _mark_autofit(config: Dict, enable: bool) -> Dict:
    """Activa/desactiva la bandera `autofit` en los text/paragraph que tengan max_width.

    Respeta `locked` (datos exactos nunca se reescalan). Añade un max_height
    estimado si falta, para que el autofit pueda limitar por alto.
    """
    cfg = copy.deepcopy(config)
    for doc in cfg.get("documents", []) or []:
        for el in doc.get("elements", []) or []:
            if not isinstance(el, dict) or el.get("type") not in ("text", "paragraph"):
                continue
            if el.get("locked"):
                el["autofit"] = False
                continue
            if el.get("max_width"):
                el["autofit"] = bool(enable)
    return cfg


def update_state(
    config: Dict,
    titulo: str,
    subtitulo: str,
    cuerpo: str,
    dpi: Optional[float],
    width_cm: Optional[float],
    height_cm: Optional[float],
    autofit: bool = True,
) -> Tuple[Dict, str, str]:
    """Aplica ediciones de texto + proporción/DPI + autofit. Devuelve (config, svg, info_msg)."""
    cfg = _apply_text_fields(config, titulo, subtitulo, cuerpo)
    msgs = []
    try:
        if width_cm and height_cm:
            cfg, info = set_real_size(cfg, float(width_cm), float(height_cm), dpi=dpi or None)
            msgs.append(f"Proporción → {width_cm:g}x{height_cm:g}cm @ {info['dpi_usado']:.0f}dpi")
            if info.get("aviso"):
                msgs.append("⚠ " + info["aviso"])
        elif dpi:
            cfg, info = set_dpi(cfg, float(dpi))
            msgs.append(f"DPI → {info['dpi_despues']:.0f} (canvas {info['canvas_despues'][0]}x{info['canvas_despues'][1]}px)")
    except ValueError as e:
        msgs.append(f"Error: {e}")
    cfg = _mark_autofit(cfg, autofit)
    if autofit:
        msgs.append("autofit activo")
    return cfg, render_svg(cfg, show_safe_area=True), "  ·  ".join(msgs) or "Actualizado."


def export_files(config: Dict, slug: str = "") -> Tuple[str, str]:
    """Guarda el SVG de preview y el config.json en projects/piezas_vectoriales/<slug>/.

    Devuelve (ruta_svg, ruta_config). El SVG de producción se obtiene luego con
    `flujo render run`; este export sirve para abrir/editar rápido en Illustrator.
    """
    slug = slug or config.get("project", {}).get("slug", "pieza")
    out_dir = repo_root() / "projects" / "piezas_vectoriales" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = out_dir / "config.json"
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    svg_path = out_dir / "preview.svg"
    svg_path.write_text(render_svg(config), encoding="utf-8")
    return str(svg_path), str(cfg_path)


# ============================================================
# Avisos de Instagram (reusa intake.email_parser)
# ============================================================

def analizar_instagram(texto: str) -> str:
    """Analiza un correo/texto con links de IG y devuelve un resumen con avisos.

    Reutiliza la detección ya existente en intake.email_parser:
    perfil privado, video en carrusel, sin links.
    """
    from ..intake.email_parser import parse_email_content, generate_warnings

    if not texto or not texto.strip():
        return "Pega el correo/texto con los links de Instagram."

    parsed = parse_email_content(texto)
    parsed["warnings"] = generate_warnings(parsed)

    lines: List[str] = []
    links = parsed.get("instagram_links", [])
    lines.append(f"Links de Instagram detectados: {len(links)}")
    for l in links:
        lines.append(f"  · {l}")
    lines.append(f"Tipo de pieza inferido: {parsed.get('project_type', '?')}")

    warnings = parsed.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("AVISOS:")
        for w in warnings:
            lines.append(f"  {w}")
    else:
        lines.append("")
        lines.append("✓ Sin avisos: parece descargable.")

    secciones = parsed.get("sections", {})
    if secciones:
        lines.append("")
        lines.append("Datos detectados:")
        for k, v in secciones.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ============================================================
# Acuse de recibo (mailto / Gmail prellenado)
# ============================================================

def construir_acuse(config: Dict, solicitante: str = "", canal: str = "correo",
                    folio: str = "") -> Dict[str, str]:
    """Construye el texto + enlaces (mailto y Gmail web) para acusar recibo.

    Semiautomático: el dueño da un clic y se abre el correo prellenado con el
    folio y el resumen de lo entendido. Devuelve dict con: asunto, cuerpo,
    mailto, gmail.
    """
    import urllib.parse

    proj = config.get("project", {}) if config else {}
    canvas = config.get("canvas", {}) if config else {}
    real = canvas.get("real_size_cm", {})
    nombre = proj.get("name", "tu pedido")
    folio = folio or proj.get("slug", "")

    medida = ""
    if real.get("width") and real.get("height"):
        medida = f"{real['width']}x{real['height']} cm"

    asunto = f"Pedido recibido: {nombre}" + (f" (folio {folio})" if folio else "")
    cuerpo_lineas = [
        f"Hola{(' ' + solicitante) if solicitante else ''},",
        "",
        "Confirmo la recepción de tu pedido. Esto es lo que entendí:",
        f"  · Pieza: {nombre}",
    ]
    if folio:
        cuerpo_lineas.append(f"  · Folio: {folio}")
    if medida:
        cuerpo_lineas.append(f"  · Medida: {medida}")
    cuerpo_lineas += [
        "",
        "Si algo no coincide, respóndeme este correo.",
        "Quedo trabajando en ello.",
        "",
        "Saludos.",
    ]
    cuerpo = "\n".join(cuerpo_lineas)

    qs = urllib.parse.urlencode({"subject": asunto, "body": cuerpo})
    mailto = f"mailto:?{qs}"
    gmail = f"https://mail.google.com/mail/?view=cm&fs=1&{urllib.parse.urlencode({'su': asunto, 'body': cuerpo})}"
    return {"asunto": asunto, "cuerpo": cuerpo, "mailto": mailto, "gmail": gmail}


# ============================================================
# UI (Gradio) — import perezoso
# ============================================================

_CSS = """
:root { --bg:#0a0a0a; --panel:#111; --border:#222; --text:#e0e0e0; --cyan:#00f0ff; }
body, .gradio-container { background:var(--bg)!important; color:var(--text)!important; }
h1,h2,h3 { color:#fff!important; }
button.primary { background:linear-gradient(135deg,var(--cyan),#7000ff)!important; color:#000!important; font-weight:700!important; }
.block { background:var(--panel)!important; border:1px solid var(--border)!important; }
"""


def build_app():
    import gradio as gr

    def _svg_html(svg: str) -> str:
        # Encajar el SVG en un contenedor responsivo
        return f'<div style="max-width:100%;border:1px solid #333;background:#fff;padding:8px">{svg}</div>'

    with gr.Blocks(title="flujo · editor") as demo:
        gr.HTML(f"<style>{_CSS}</style>")
        gr.Markdown("# FLUJO // Editor de piezas")

        state = gr.State({})

        with gr.Tab("EDITOR"):
            gr.Markdown("Catálogo de la ONG → editar datos y proporción → preview SVG → exportar.")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Elegir formato")
                    f_area = gr.Dropdown(["", "eventos", "suplementos"], value="", label="Área")
                    f_medio = gr.Dropdown(["", "impresion", "digital"], value="", label="Medio")
                    fmt = gr.Dropdown(choices=catalog_choices(), label="Formato", value=None)

                    gr.Markdown("### 2. Datos")
                    titulo = gr.Textbox(label="Título")
                    subtitulo = gr.Textbox(label="Subtítulo")
                    cuerpo = gr.Textbox(label="Cuerpo", lines=3)
                    autofit = gr.Checkbox(label="Auto-ajustar texto a la caja (autofit)", value=True)

                    gr.Markdown("### 3. Proporción / Resolución")
                    with gr.Row():
                        width_cm = gr.Number(label="Ancho cm", value=None)
                        height_cm = gr.Number(label="Alto cm", value=None)
                    dpi = gr.Number(label="DPI (anti-pixelado)", value=None)

                    with gr.Row():
                        btn_update = gr.Button("Actualizar preview", variant="primary")
                        btn_export = gr.Button("Exportar SVG + config", variant="secondary")
                    info = gr.Textbox(label="Estado", interactive=False)

                with gr.Column(scale=2):
                    gr.Markdown("### Preview")
                    preview = gr.HTML()

        with gr.Tab("INSTAGRAM"):
            gr.Markdown("## Analizar links de Instagram")
            gr.Markdown("Pega el correo/mensaje con links. Detecta perfil privado, "
                        "video en carrusel y datos del pedido **antes** de descargar.")
            ig_in = gr.Textbox(label="Correo / texto con links", lines=8)
            ig_btn = gr.Button("Analizar", variant="primary")
            ig_out = gr.Textbox(label="Resultado", lines=12, interactive=False)
            ig_btn.click(analizar_instagram, ig_in, ig_out)

        with gr.Tab("ACUSE DE RECIBO"):
            gr.Markdown("## Acusar recibo (semiautomático)")
            gr.Markdown("Genera un correo prellenado con folio + resumen. Un clic y se abre tu correo.")
            ac_solic = gr.Textbox(label="Nombre del solicitante (opcional)")
            ac_folio = gr.Textbox(label="Folio (opcional; por defecto el slug)")
            ac_btn = gr.Button("Generar acuse", variant="primary")
            ac_cuerpo = gr.Textbox(label="Mensaje", lines=10, interactive=False)
            ac_links = gr.HTML()

        # --- callbacks EDITOR ---
        def on_filter(area, medio):
            return gr.Dropdown(choices=catalog_choices(area, medio))

        f_area.change(on_filter, [f_area, f_medio], fmt)
        f_medio.change(on_filter, [f_area, f_medio], fmt)

        def on_select(fmt_id):
            if not fmt_id:
                return {}, "", "", "", "", ""
            cfg, svg, fields = load_format_state(fmt_id)
            return cfg, _svg_html(svg), fields["titulo"], fields["subtitulo"], fields["cuerpo"], "Formato cargado."

        fmt.change(on_select, fmt, [state, preview, titulo, subtitulo, cuerpo, info])

        def on_update(cfg, t, s, c, af, d, w, h):
            if not cfg:
                return {}, "", "Primero elige un formato."
            new_cfg, svg, msg = update_state(cfg, t, s, c, d, w, h, autofit=af)
            return new_cfg, _svg_html(svg), msg

        btn_update.click(on_update, [state, titulo, subtitulo, cuerpo, autofit, dpi, width_cm, height_cm],
                         [state, preview, info])

        def on_export(cfg):
            if not cfg:
                return "Primero elige un formato."
            svg_path, cfg_path = export_files(cfg)
            return f"Exportado:\n  {cfg_path}\n  {svg_path}\n\nLuego: flujo render run {cfg_path}"

        btn_export.click(on_export, state, info)

        # --- callbacks ACUSE ---
        def on_acuse(cfg, solic, folio):
            if not cfg:
                return "Primero elige un formato en la pestaña EDITOR.", ""
            ac = construir_acuse(cfg, solicitante=solic or "", folio=folio or "")
            links = (
                f'<div style="display:flex;gap:12px">'
                f'<a href="{ac["mailto"]}" style="color:#00f0ff">📧 Abrir en tu correo (mailto)</a>'
                f'<a href="{ac["gmail"]}" target="_blank" style="color:#00f0ff">✉️ Abrir en Gmail</a>'
                f'</div>'
            )
            return ac["cuerpo"], links

        ac_btn.click(on_acuse, [state, ac_solic, ac_folio], [ac_cuerpo, ac_links])

    return demo


def launch(server_name: str = "127.0.0.1", server_port: int = 7860, share: bool = False):
    demo = build_app()
    demo.launch(server_name=server_name, server_port=server_port, share=share, show_error=True)
