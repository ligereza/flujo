"""The floor-plan symbol catalogue must be editable by the events manager.

Acceptance criterion, the user's own words (2026-07-26): "puede la jefa de
eventos agregar un icono? si no, no es configurable". So these tests do exactly
what she would do -- drop an .svg in a folder, declare it in a JSON -- and then
check the symbol reaches the rendered plan. Nothing here mocks the renderer.
"""
from __future__ import annotations

import json

import pytest

from flujo.plano import iconos as mod

SVG_DISENADORA = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!-- Generator: Adobe Illustrator -->\n'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">\n'
    '  <path d="M 10 10 H 230 V 110 H 10 Z" fill="none" stroke="currentColor"/>\n'
    '</svg>\n'
)


@pytest.fixture()
def repo(tmp_path):
    """A throwaway repo root with the two paths the catalogue reads."""
    (tmp_path / "data" / "plano_simbolos").mkdir(parents=True)

    def cargar(simbolos, svgs=None):
        (tmp_path / "data" / "plano_simbolos.json").write_text(
            json.dumps({"simbolos": simbolos}), encoding="utf-8")
        for nombre, contenido in (svgs or {}).items():
            (tmp_path / "data" / "plano_simbolos" / nombre).write_text(
                contenido, encoding="utf-8")
        mod.recargar_catalogo(tmp_path)
        return mod

    yield cargar
    mod._RAIZ_FIJA = None       # otros tests siguen viendo el catalogo real
    mod.recargar_catalogo()


def _evento(**extra):
    ev = {"nombre": "Evento Test", "voluntarios": 6, "duracion_horas": 8,
          "incluye_testeo": True, "layout_mode": "grid_2x"}
    ev.update(extra)
    return ev


def test_agregar_un_simbolo_llega_al_plano(repo):
    """El caso completo: suelta un SVG, lo declara, y aparece en el plano."""
    repo(
        [{"id": "hidratacion", "etiqueta": "Punto de hidratación",
          "color": "#38bdf8", "svg": "hidratacion.svg",
          "zona": "INFRAESTRUCTURA", "cuando": "siempre"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    assert "hidratacion" in mod.simbolos_de_evento(_evento())
    assert mod.ETIQUETAS["hidratacion"] == "Punto de hidratación"

    from flujo.plano import engine
    svg = engine.render_svg(_evento())
    assert "Punto de hidratación" in svg          # la etiqueta se imprime
    assert "M 10 10 H 230 V 110 H 10 Z" in svg    # y el dibujo de ella tambien


def test_currentcolor_toma_el_color_declarado(repo):
    mod = repo(
        [{"id": "hidratacion", "color": "#38bdf8", "svg": "hidratacion.svg"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    marca = mod.icono("hidratacion", 100, 100, 1.0)
    assert "#38bdf8" in marca and "currentColor" not in marca


def test_el_svg_se_centra_y_conserva_proporcion(repo):
    """240x120 en una caja de 160: factor 160/240, y centrado en el punto."""
    mod = repo(
        [{"id": "hidratacion", "svg": "hidratacion.svg"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    marca = mod.icono("hidratacion", 100.0, 100.0, 1.0)
    assert "scale(0.6667)" in marca
    assert "translate(20.00 60.00)" in marca


def test_no_viaja_script_ni_manejadores_al_plano(repo):
    """Un plano se entrega a un venue: no lleva script adentro."""
    mod = repo(
        [{"id": "sucio", "svg": "sucio.svg"}],
        {"sucio.svg": '<svg viewBox="0 0 10 10"><script>alert(1)</script>'
                      '<rect width="10" height="10" onload="x()"/></svg>'},
    )
    marca = mod.icono("sucio", 0, 0, 1.0)
    assert "script" not in marca and "onload" not in marca
    assert "<rect" in marca


def test_zona_invalida_avisa_y_no_desaparece(repo, capsys):
    """El defecto que existia: una clave fuera de zona se perdia en silencio."""
    mod = repo(
        [{"id": "hidratacion", "svg": "hidratacion.svg", "zona": "INVENTADA"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    assert "no existe" in capsys.readouterr().err
    zonas = dict(mod.zonas_de_iconos())
    assert "hidratacion" in zonas[mod.ZONA_POR_DEFECTO]


def test_archivo_faltante_avisa_y_no_rompe_el_plano(repo, capsys):
    mod = repo([{"id": "fantasma", "svg": "no_existe.svg"}])
    assert "falta el archivo" in capsys.readouterr().err
    assert "fantasma" not in mod.CATALOGO
    assert mod.simbolos_de_evento(_evento())  # el resto del plano sigue


def test_json_roto_avisa_y_deja_los_iconos_base(repo, tmp_path, capsys):
    repo([])
    (tmp_path / "data" / "plano_simbolos.json").write_text("{roto", encoding="utf-8")
    mod.recargar_catalogo(tmp_path)
    assert "no se pudo leer" in capsys.readouterr().err
    assert "tent" in mod.simbolos_de_evento(_evento())


def test_puede_reetiquetar_un_icono_base_sin_tocar_codigo(repo):
    mod = repo([{"id": "water", "etiqueta": "Agua potable", "color": "#00ffcc"}])
    assert mod.ETIQUETAS["water"] == "Agua potable"
    assert mod.COLORES["water"] == "#00ffcc"
    # sigue dibujandose con su glyph de siempre, no como un aporte externo
    assert "<g transform" not in mod.icono("water", 0, 0, 1.0)


def test_cuando_manual_solo_aparece_si_el_evento_lo_pide(repo):
    mod = repo(
        [{"id": "hidratacion", "svg": "hidratacion.svg", "cuando": "manual"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    assert "hidratacion" not in mod.simbolos_de_evento(_evento())
    pedido = mod.simbolos_de_evento(_evento(simbolos_extra=["hidratacion"]))
    assert "hidratacion" in pedido


def test_cuando_condicional_respeta_el_tipo_de_evento(repo):
    mod = repo(
        [{"id": "hidratacion", "svg": "hidratacion.svg", "cuando": "jornada_larga"}],
        {"hidratacion.svg": SVG_DISENADORA},
    )
    assert "hidratacion" in mod.simbolos_de_evento(_evento(duracion_horas=8))
    assert "hidratacion" not in mod.simbolos_de_evento(_evento(duracion_horas=3))
