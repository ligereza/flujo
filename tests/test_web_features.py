"""Tests de las features nuevas del editor: avisos IG, acuse de recibo, autofit."""

import pytest

from flujo.web import editor
from flujo.web.svg_preview import render_svg


# --- Instagram ----------------------------------------------------------

def test_analizar_ig_vacio():
    out = editor.analizar_instagram("")
    assert "Pega" in out


def test_analizar_ig_detecta_links():
    txt = "mira esto https://www.instagram.com/p/ABC123/ para el flyer"
    out = editor.analizar_instagram(txt)
    assert "Links de Instagram detectados: 1" in out


def test_analizar_ig_aviso_privado():
    txt = "el perfil es privado, link https://www.instagram.com/p/ABC123/"
    out = editor.analizar_instagram(txt)
    assert "PRIVAD" in out.upper()


def test_analizar_ig_aviso_video():
    txt = "la primera imagen es video https://www.instagram.com/p/ABC123/"
    out = editor.analizar_instagram(txt)
    assert "VIDEO" in out.upper()


def test_analizar_ig_sin_links():
    out = editor.analizar_instagram("hola, hazme un flyer por favor")
    assert "SIN LINKS" in out.upper()


# --- Acuse de recibo ----------------------------------------------------

def _cfg():
    return {
        "project": {"name": "Etiqueta Miel", "slug": "miel-organica"},
        "canvas": {"real_size_cm": {"width": 16.5, "height": 6.5}},
    }


def test_acuse_estructura():
    ac = editor.construir_acuse(_cfg(), solicitante="Juan")
    assert set(ac) == {"asunto", "cuerpo", "mailto", "gmail"}


def test_acuse_incluye_nombre_y_folio():
    ac = editor.construir_acuse(_cfg(), solicitante="Juan")
    assert "Etiqueta Miel" in ac["asunto"]
    assert "miel-organica" in ac["asunto"]
    assert "Juan" in ac["cuerpo"]
    assert "16.5x6.5 cm" in ac["cuerpo"]


def test_acuse_links_validos():
    ac = editor.construir_acuse(_cfg())
    assert ac["mailto"].startswith("mailto:?")
    assert ac["gmail"].startswith("https://mail.google.com/")
    # el asunto va url-encoded
    assert "subject=" in ac["mailto"]
    assert "su=" in ac["gmail"]


def test_acuse_folio_explicito():
    ac = editor.construir_acuse(_cfg(), folio="WA-001")
    assert "WA-001" in ac["asunto"]


# --- autofit en el editor ----------------------------------------------

def test_mark_autofit_activa_en_texto_con_maxwidth():
    cfg = {"documents": [{"elements": [
        {"type": "text", "content": "x", "max_width": 500},
        {"type": "rect", "x": 0},
    ]}]}
    out = editor._mark_autofit(cfg, True)
    els = out["documents"][0]["elements"]
    assert els[0]["autofit"] is True
    assert "autofit" not in els[1]  # el rect no se toca


def test_mark_autofit_respeta_locked():
    cfg = {"documents": [{"elements": [
        {"type": "text", "content": "lote 123", "max_width": 500, "locked": True},
    ]}]}
    out = editor._mark_autofit(cfg, True)
    assert out["documents"][0]["elements"][0]["autofit"] is False


def test_update_state_con_autofit():
    cfg, _, _ = editor.load_format_state("sup_etiqueta_165x65")
    new_cfg, svg, msg = editor.update_state(cfg, "TITULO LARGO " * 5, "", "",
                                            dpi=None, width_cm=None, height_cm=None, autofit=True)
    assert "autofit" in msg
    assert svg.startswith("<svg")


def test_preview_aplica_autofit():
    # un texto enorme con autofit debe renderizar con size reducido
    cfg = {
        "canvas": {"width": 600, "height": 300},
        "palette": {"ink": "#000"},
        "documents": [{"id": "d", "elements": [
            {"type": "text", "content": "PALABRA " * 30, "x": 20, "y": 20,
             "size": 90, "max_width": 560, "max_height": 200, "autofit": True, "fill": "ink"},
        ]}],
    }
    svg = render_svg(cfg)
    assert svg.startswith("<svg")
    # debió generar varias líneas <text>
    assert svg.count("<text") >= 2
