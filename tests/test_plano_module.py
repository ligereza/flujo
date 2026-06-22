"""Tests directos para el módulo flujo.plano (engine + costs)."""
from pathlib import Path

import pytest

from flujo.plano import (
    load_evento,
    render_svg,
    render_rider,
    modulos_desde_evento,
    solve_layout,
    calcular_costos,
    resumen_costos,
)


@pytest.fixture
def evento_masivo():
    return {
        "nombre": "Festival Ejemplo 2026",
        "duracion_horas": 6,
        "voluntarios": 7,
        "asistentes_estimados": 2500,
        "incluye_testeo": True,
        "masivo": True,
    }


@pytest.fixture
def evento_pequeno():
    return {
        "nombre": "Evento pequeño",
        "duracion_horas": 3,
        "voluntarios": 3,
        "asistentes_estimados": 100,
        "incluye_testeo": False,
        "masivo": False,
    }


def test_modulos_masivo(evento_masivo):
    mods = modulos_desde_evento(evento_masivo)
    assert len(mods) == 3
    assert mods[0]["nombre"] == "Stand Informativo"
    assert mods[1]["nombre"] == "Stand Testeo"
    assert mods[2]["nombre"] == "Contención / Descanso"


def test_modulos_pequeno(evento_pequeno):
    mods = modulos_desde_evento(evento_pequeno)
    assert len(mods) == 1
    assert mods[0]["nombre"] == "Stand Informativo"


def test_solve_layout_masivo(evento_masivo):
    cajas, ancho, alto = solve_layout(evento_masivo)
    assert len(cajas) == 3
    assert ancho > 0
    assert alto > 0
    # 3 stands de 3x3 + 2 pasillos de 1.2 = 9 + 2.4 = 11.4
    assert ancho == pytest.approx(11.4)


def test_render_svg(evento_masivo):
    svg = render_svg(evento_masivo)
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Festival Ejemplo 2026" in svg
    assert "Stand Informativo" in svg
    assert "Stand Testeo" in svg


def test_render_rider(evento_masivo):
    rider = render_rider(evento_masivo)
    assert "RIDER TÉCNICO" in rider
    assert "ALIMENTACIÓN" in rider
    assert "2 mesa(s)" in rider
    assert "testeo" in rider.lower()
    assert "ZONA DE CONTENCIÓN" in rider


def test_render_rider_pequeno(evento_pequeno):
    rider = render_rider(evento_pequeno)
    assert "1 mesa(s)" in rider
    assert "colación" not in rider.lower()
    assert "alimentación" not in rider.lower()
    assert "contención" not in rider.lower()


def test_costos_masivo(evento_masivo):
    c = calcular_costos(evento_masivo)
    assert c["personal"] > 0
    assert c["alimentacion"] > 0
    assert c["extras"] > 0
    assert c["total"] > 0
    assert c["detalle"]["mesas"] == 3  # 2 base + 1 testeo
    assert c["detalle"]["stands"] == 3


def test_costos_pequeno(evento_pequeno):
    c = calcular_costos(evento_pequeno)
    assert c["alimentacion"] == 0
    assert c["extras"] == 0
    assert c["detalle"]["mesas"] == 1
    assert c["detalle"]["stands"] == 1


def test_resumen_costos(evento_masivo):
    texto = resumen_costos(evento_masivo)
    assert "COTIZACIÓN REFERENCIAL" in texto
    assert "TOTAL REFERENCIAL" in texto
    assert "$" in texto


def test_load_evento(tmp_path):
    ev = tmp_path / "ev.json"
    ev.write_text('{"nombre": "x", "voluntarios": 2}', encoding="utf-8")
    data = load_evento(ev)
    assert data["nombre"] == "x"


def test_load_evento_rechaza_no_objeto(tmp_path):
    ev = tmp_path / "ev.json"
    ev.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_evento(ev)
