"""
Tests de src/flujo/cotizaciones_base.py -- calculadora de dinero, cero tests
antes (gap #1 de la pasada de cobertura). Fija: que line-items agrega cada
condicion (testeo/masivo/horas>5), contingencia = 10% redondeado, total =
subtotal + contingencia, y el formato clp().
"""
from __future__ import annotations

from flujo.cotizaciones_base import clp, generar_cotizacion_base


def _codes(res) -> set[str]:
    return {i["code"] for i in res["items"]}


def test_clp_formatea_miles_con_punto():
    assert clp(100000) == "$100.000"
    assert clp(0) == "$0"
    assert clp(1234.6) == "$1.235"       # redondea


def test_contingencia_es_diez_por_ciento_redondeado():
    res = generar_cotizacion_base({"voluntarios": 4, "duracion_horas": 4})
    assert res["contingencia"] == round(res["subtotal"] * 0.10)


def test_total_es_subtotal_mas_contingencia():
    res = generar_cotizacion_base({"voluntarios": 6, "duracion_horas": 6})
    assert res["total"] == res["subtotal"] + res["contingencia"]
    assert res["total_clp"] == clp(res["total"])


def test_subtotal_es_suma_de_items():
    res = generar_cotizacion_base({"voluntarios": 5, "duracion_horas": 3})
    assert res["subtotal"] == sum(i["subtotal"] for i in res["items"])


def test_montos_literales_pinnean_los_precios():
    """Fija PESOS concretos por line-item (no solo la coherencia interna): un
    error en UNITARIOS[...] rompe esto. Sin este test un precio 12x pasaba verde
    (hallazgo del review adversarial 2026-07-17). Input controlado: 2 vol x 4h,
    con testeo, masivo y flyer impreso -> cada item tiene cantidad determinista."""
    res = generar_cotizacion_base(
        {"voluntarios": 2, "duracion_horas": 4, "incluye_testeo": True, "masivo": True},
        incluir_flyer_impreso=True,
    )
    montos = {i["code"]: i["subtotal"] for i in res["items"]}
    assert montos["equipo"] == 80_000          # 2 vol x 4h x 10.000
    assert montos["stand"] == 80_000
    assert montos["testeo"] == 120_000
    assert montos["contencion"] == 80_000
    assert montos["coordinacion"] == 90_000
    assert montos["rider_plano"] == 65_000
    assert montos["cartelera"] == 90_000
    assert montos["flyer_impreso"] == 75_000
    assert res["subtotal"] == 704_000
    assert res["contingencia"] == 70_400       # 10% exacto
    assert res["total"] == 774_400


def test_testeo_agrega_modulo():
    con = generar_cotizacion_base({"voluntarios": 4, "incluye_testeo": True, "duracion_horas": 4})
    sin = generar_cotizacion_base({"voluntarios": 4, "incluye_testeo": False, "duracion_horas": 4})
    assert "testeo" in _codes(con)
    assert "testeo" not in _codes(sin)


def test_masivo_agrega_contencion_y_coordinacion():
    res = generar_cotizacion_base({"voluntarios": 15, "masivo": True, "duracion_horas": 8})
    assert {"contencion", "coordinacion"} <= _codes(res)


def test_jornada_larga_agrega_alimentacion():
    larga = generar_cotizacion_base({"voluntarios": 4, "duracion_horas": 8})
    corta = generar_cotizacion_base({"voluntarios": 4, "duracion_horas": 4})
    assert "alimentacion" in _codes(larga)
    assert "alimentacion" not in _codes(corta)


def test_flags_de_diseno_controlan_items():
    con_flyer = generar_cotizacion_base({"voluntarios": 4}, incluir_flyer_impreso=True)
    sin_cartelera = generar_cotizacion_base({"voluntarios": 4}, incluir_cartelera=False)
    assert "flyer_impreso" in _codes(con_flyer)
    assert "cartelera" not in _codes(sin_cartelera)


def test_markdown_incluye_total_referencial():
    res = generar_cotizacion_base({"voluntarios": 4})
    assert "TOTAL REFERENCIAL" in res["markdown"]
    assert res["total_clp"] in res["markdown"]
