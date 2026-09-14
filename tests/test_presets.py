"""
Tests de src/flujo/eventos/presets.py -- alimenta la calculadora de cotizaciones
y el dimensionamiento de plano/rider. Cero tests antes (gap #3). Fija: preset
desconocido cae a 'base' sin error, apply no pisa valores explicitos, e inferencia
por keywords.
"""
from __future__ import annotations

from flujo.eventos import presets


def test_normalize_alias_y_desconocido():
    assert presets.normalize_preset_id("underground") == "under"
    assert presets.normalize_preset_id("festival") == "mainstream"
    assert presets.normalize_preset_id("evento_under") == "under"   # prefijo evento_
    # desconocido/garbage -> base, no error
    assert presets.normalize_preset_id("xyz-inexistente") == "base"
    assert presets.normalize_preset_id(None) == "base"
    assert presets.normalize_preset_id("") == "base"


def test_infer_por_keywords():
    assert presets.infer_event_preset("Festival masivo en Espacio Riesco") == "mainstream"
    assert presets.infer_event_preset("fiesta underground en un club") == "under"
    assert presets.infer_event_preset("evento normal sin pistas") == "base"


def test_apply_no_pisa_valores_explicitos():
    """Los campos que trae el evento ganan al preset; solo se rellenan los
    None/'' (semantica de override parcial)."""
    ev = presets.apply_event_preset({"preset": "mainstream", "voluntarios": 3})
    assert ev["voluntarios"] == 3            # explicito, no el del preset
    assert ev["preset"] == "mainstream"
    assert ev["preset_label"]                # rellenado del preset
    assert "preset_operativo" in ev


def test_apply_rellena_campos_faltantes_del_preset():
    ev = presets.apply_event_preset({"preset": "under"})
    preset = presets.get_event_preset("under")
    for k in ("duracion_horas", "voluntarios", "asistentes_estimados", "incluye_testeo", "masivo"):
        assert ev[k] == preset[k]


def test_apply_vacio_usa_base():
    ev = presets.apply_event_preset({})
    assert ev["preset"] == "base"
    assert ev["preset_operativo"]["label"] == ev["preset_label"]


def test_valor_vacio_string_se_trata_como_faltante():
    ev = presets.apply_event_preset({"preset": "base", "voluntarios": ""})
    assert isinstance(ev["voluntarios"], int)   # se relleno del preset, no quedo ''
