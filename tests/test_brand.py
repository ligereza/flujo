"""
Tests de src/flujo/brand.py -- loader de identidad, sitio del bug "cotizaciones
roto" (brand.py vaciado -> ImportError). Cero regresion antes (gap #2). Fija el
contrato que engine.py y piezas.py importan: load_styles/get_color no lanzan,
caen a defaults si falta el JSON, y devuelven default para clave desconocida.
"""
from __future__ import annotations

import json

import flujo.brand as brand


def test_load_styles_devuelve_colores():
    brand.load_styles.cache_clear()
    styles = brand.load_styles()
    assert isinstance(styles, dict)
    for clave in ("ink", "accent", "paper"):
        assert clave in styles
        assert styles[clave].startswith("#")


def test_get_color_conocido_y_desconocido():
    brand.load_styles.cache_clear()
    assert brand.get_color("ink").startswith("#")
    assert brand.get_color("no_existe") == "#000000"
    assert brand.get_color("no_existe", "#abcdef") == "#abcdef"


def test_load_styles_cae_a_defaults_si_falta_json(tmp_path, monkeypatch):
    """Si projects/flujo/flujo.json no esta (paquete instalado fuera del repo),
    no revienta: usa los defaults espejo."""
    brand.load_styles.cache_clear()
    monkeypatch.setattr(brand, "_FLUJO_JSON", tmp_path / "no_existe.json")
    styles = brand.load_styles()
    assert styles == brand._DEFAULT_COLORS
    brand.load_styles.cache_clear()


def test_load_styles_cae_a_defaults_si_json_corrupto(tmp_path, monkeypatch):
    brand.load_styles.cache_clear()
    malo = tmp_path / "malo.json"
    malo.write_text("{ esto no es json", encoding="utf-8")
    monkeypatch.setattr(brand, "_FLUJO_JSON", malo)
    assert brand.load_styles() == brand._DEFAULT_COLORS
    brand.load_styles.cache_clear()


def test_lee_colores_del_json_real(tmp_path, monkeypatch):
    brand.load_styles.cache_clear()
    j = tmp_path / "flujo.json"
    j.write_text(json.dumps({"colors": {"ink": "#111111", "accent": "#222222"}}), encoding="utf-8")
    monkeypatch.setattr(brand, "_FLUJO_JSON", j)
    styles = brand.load_styles()
    assert styles["ink"] == "#111111"
    assert styles["accent"] == "#222222"
    brand.load_styles.cache_clear()


def test_symbols_que_importan_sus_consumidores_existen():
    """Direct regression of the bug: these names MUST exist. The module was once
    emptied while its callers still imported them, and `flujo cotizaciones` died
    with ImportError while render/piezas.py swallowed it in a silent except.

    Today the only importer is projects/cotizaciones/engine.py (load_styles), as
    the DEFAULT palette a caller or an event's own `estilo` block may override.
    piezas.py stopped importing it on 2026-07-26: it printed "flujo aplicado
    automaticamente" and applied nothing. get_color stays public because it is
    the read path for a single colour and removing it is how this bug happened."""
    assert callable(brand.load_styles)
    assert callable(brand.get_color)
