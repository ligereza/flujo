"""Tests del auto-fit de texto (render.autofit)."""

import pytest

from flujo.render import autofit as af


def test_approx_measure_crece_con_tamano():
    assert af.approx_measure("hola", 40) < af.approx_measure("hola", 80)


def test_wrap_respeta_max_width():
    lines = af.wrap_text("una frase bastante larga para varias lineas", 120, 40, "regular", af.approx_measure)
    assert len(lines) > 1


def test_wrap_respeta_saltos():
    lines = af.wrap_text("a\nb", None, 40, "regular", af.approx_measure)
    assert lines == ["a", "b"]


def test_fit_reduce_si_no_cabe_por_alto():
    texto = "ingredientes: a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r"
    size, lines = af.fit_font_size(texto, size=80, max_width=600, max_height=200,
                                   measure=af.approx_measure)
    assert size < 80  # tuvo que reducir
    assert size >= 8


def test_fit_no_reduce_si_cabe():
    size, lines = af.fit_font_size("corto", size=40, max_width=2000, max_height=2000,
                                   measure=af.approx_measure)
    assert size == 40


def test_fit_respeta_min_size():
    texto = " ".join(["palabra"] * 200)
    size, _ = af.fit_font_size(texto, size=100, max_width=300, max_height=120,
                              min_size=30, measure=af.approx_measure)
    assert size == 30  # no baja del mínimo


def test_fit_reduce_si_palabra_no_cabe_en_ancho():
    size, _ = af.fit_font_size("supercalifragilisticoexpialidoso", size=120, max_width=200,
                              measure=af.approx_measure)
    assert size < 120


def test_autofit_element_solo_si_flag():
    el = {"type": "text", "content": "x" * 100, "size": 80, "max_width": 200, "max_height": 100}
    # sin flag => no cambia
    assert af.autofit_element(el)["size"] == 80
    el2 = dict(el, autofit=True)
    assert af.autofit_element(el2)["size"] < 80


def test_autofit_element_respeta_locked():
    el = {"type": "text", "content": "x" * 100, "size": 80, "max_width": 200,
          "max_height": 100, "autofit": True, "locked": True}
    assert af.autofit_element(el)["size"] == 80  # locked nunca se toca


def test_autofit_element_ignora_no_texto():
    el = {"type": "rect", "x": 0, "y": 0, "w": 10, "h": 10, "autofit": True}
    assert af.autofit_element(el) == el


def test_autofit_config_no_muta_original():
    import copy
    cfg = {"documents": [{"elements": [
        {"type": "text", "content": "x" * 100, "size": 80, "max_width": 200, "max_height": 80, "autofit": True}
    ]}]}
    snap = copy.deepcopy(cfg)
    out = af.autofit_config(cfg)
    assert cfg == snap
    assert out["documents"][0]["elements"][0]["size"] < 80
