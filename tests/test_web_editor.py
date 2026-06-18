"""Tests del editor web (lógica pura, sin levantar Gradio)."""

import copy

import pytest

from flujo.web.svg_preview import render_svg, _wrap
from flujo.web import editor


def sample_config():
    return {
        "project": {"slug": "demo", "name": "Demo"},
        "canvas": {
            "width": 1080, "height": 1920,
            "real_size_cm": {"width": 10.8, "height": 19.2},
            "safe_margin_px": 60,
        },
        "palette": {"paper": "#FFF8ED", "ink": "#161513", "accent": "#173F2F"},
        "background": "paper",
        "global_elements": [
            {"type": "rect", "x": 10, "y": 10, "w": 1060, "h": 1900, "stroke": "ink", "stroke_width": 4, "fill": "none"},
        ],
        "documents": [
            {
                "id": "01_demo",
                "elements": [
                    {"type": "image", "src": "", "x": 80, "y": 80, "w": 920, "h": 800},
                    {"type": "text", "content": "TÍTULO", "x": 80, "y": 1000, "size": 90, "fill": "ink", "weight": "bold"},
                    {"type": "paragraph", "content": "Subtítulo demo.", "x": 80, "y": 1150, "size": 40, "fill": "ink", "max_width": 900},
                ],
            }
        ],
    }


# --- svg_preview ----------------------------------------------------------

def test_render_svg_basico():
    svg = render_svg(sample_config())
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'width="1080px"' in svg
    assert "TÍTULO" in svg


def test_render_svg_escapa_texto():
    cfg = sample_config()
    cfg["documents"][0]["elements"][1]["content"] = "A & B <x>"
    svg = render_svg(cfg)
    assert "&amp;" in svg
    assert "<x>" not in svg  # debe estar escapado


def test_render_svg_image_placeholder_sin_src():
    svg = render_svg(sample_config())
    # imagen sin src => placeholder
    assert "IMAGEN" in svg


def test_render_svg_image_con_src():
    cfg = sample_config()
    cfg["documents"][0]["elements"][0]["src"] = "input/foto.jpg"
    svg = render_svg(cfg)
    assert "<image" in svg
    assert "input/foto.jpg" in svg


def test_render_svg_safe_area():
    svg = render_svg(sample_config(), show_safe_area=True)
    assert "stroke-dasharray" in svg


def test_render_svg_sin_documentos():
    svg = render_svg({"canvas": {"width": 100, "height": 100}, "documents": []})
    assert "sin documentos" in svg


def test_wrap_respeta_ancho():
    lines = _wrap("una frase larga que deberia partirse en varias lineas", 200, 40)
    assert len(lines) > 1


def test_wrap_sin_maxwidth():
    lines = _wrap("linea1\nlinea2", None, 40)
    assert lines == ["linea1", "linea2"]


# --- editor: catálogo y estado --------------------------------------------

def test_catalog_choices_no_vacio():
    ch = editor.catalog_choices()
    assert len(ch) >= 12
    # cada item es (label, id)
    assert all(isinstance(c, tuple) and len(c) == 2 for c in ch)


def test_catalog_choices_filtra_area():
    sup = editor.catalog_choices(area="suplementos")
    assert sup
    assert all("sup_" in cid or "suplement" in label.lower() for label, cid in sup)


def test_load_format_state_etiqueta():
    cfg, svg, fields = editor.load_format_state("sup_etiqueta_165x65")
    assert cfg["canvas"]["width"] > 0
    assert svg.startswith("<svg")
    assert "titulo" in fields


def test_load_format_state_sin_plantilla_genera_base():
    # cartelera no tiene template => debe generar base con image + textos
    cfg, svg, fields = editor.load_format_state("evt_cartelera_individual_1080x1920")
    assert cfg["canvas"]["width"] == 1080
    assert cfg["canvas"]["height"] == 1920
    tipos = [e.get("type") for d in cfg["documents"] for e in d["elements"]]
    assert "image" in tipos
    assert "text" in tipos


def test_apply_text_fields():
    cfg = sample_config()
    new = editor._apply_text_fields(cfg, "NUEVO", "SUB", "CUERPO")
    contenidos = [e.get("content") for e in new["documents"][0]["elements"] if e.get("type") in ("text", "paragraph")]
    assert "NUEVO" in contenidos
    assert "SUB" in contenidos


def test_update_state_dpi():
    cfg = sample_config()
    new_cfg, svg, msg = editor.update_state(cfg, "T", "", "", dpi=300, width_cm=None, height_cm=None)
    # 10.8 cm a 300 dpi
    assert new_cfg["canvas"]["width"] == round(10.8 / 2.54 * 300)
    assert "DPI" in msg
    assert svg.startswith("<svg")


def test_update_state_proporcion_avisa():
    cfg = sample_config()
    new_cfg, svg, msg = editor.update_state(cfg, "T", "", "", dpi=None, width_cm=14, height_cm=10)
    assert new_cfg["canvas"]["real_size_cm"]["width"] == 14
    assert "Proporción" in msg


def test_update_state_no_muta_original():
    cfg = sample_config()
    snap = copy.deepcopy(cfg)
    editor.update_state(cfg, "OTRO", "", "", dpi=300, width_cm=None, height_cm=None)
    assert cfg == snap  # update_state trabaja sobre copia


def test_export_files(tmp_path, monkeypatch):
    monkeypatch.setattr(editor, "repo_root", lambda: tmp_path)
    cfg = sample_config()
    svg_path, cfg_path = editor.export_files(cfg, slug="mi_pieza")
    from pathlib import Path
    assert Path(cfg_path).exists()
    assert Path(svg_path).exists()
    assert "mi_pieza" in cfg_path
