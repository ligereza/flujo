"""Tests del modelo de PACKS RD (espejo Python de web/src/rdBrand.ts)."""
from flujo.plano.packs import (
    ALL_PACKS,
    PACKS,
    desglose_pack,
    ev_desde_pack,
    get_pack,
    normalize_pack_id,
    proporcion_monto,
)


def test_packs_precios_y_voluntarios():
    assert PACKS["INFO"]["precio"] == 250_000
    assert PACKS["INFO"]["voluntarios"] == 6
    assert PACKS["TESTEO"]["precio"] == 300_000
    assert PACKS["TESTEO"]["voluntarios"] == 6
    assert PACKS["COMPLETO"]["precio"] == 500_000
    assert PACKS["COMPLETO"]["voluntarios"] == 15
    assert ALL_PACKS == ["INFO", "TESTEO", "COMPLETO"]


def test_proporciones_completo_suman_100():
    props = PACKS["COMPLETO"]["proporciones"]
    assert sum(p["pct"] for p in props) == 100


def test_proporcion_monto_es_derivado_no_guardado():
    # 60% de 500.000 = 300.000; si el precio cambia, el monto se recalcula
    assert proporcion_monto(500_000, 60) == 300_000
    assert proporcion_monto(1_000_000, 60) == 600_000


def test_desglose_pack_completo():
    desglose = desglose_pack("COMPLETO")
    assert len(desglose) == 5
    assert sum(item["monto"] for item in desglose) == PACKS["COMPLETO"]["precio"]


def test_desglose_pack_sin_proporciones():
    assert desglose_pack("INFO") == []
    assert desglose_pack("TESTEO") == []


def test_normalize_pack_id_alias_legacy():
    assert normalize_pack_id("under") == "INFO"
    assert normalize_pack_id("base") == "TESTEO"
    assert normalize_pack_id("mainstream") == "COMPLETO"
    assert normalize_pack_id("completo") == "COMPLETO"
    assert normalize_pack_id(None) == "TESTEO"
    assert normalize_pack_id("algo-desconocido") == "TESTEO"


def test_get_pack_no_muta_registro():
    pack = get_pack("INFO")
    pack["precio"] = 1
    assert PACKS["INFO"]["precio"] == 250_000


def test_ev_desde_pack_deriva_flags_operativos():
    ev_info = ev_desde_pack("INFO")
    assert ev_info["voluntarios"] == 6
    assert ev_info["incluye_testeo"] is False
    assert ev_info["masivo"] is False

    ev_testeo = ev_desde_pack("TESTEO")
    assert ev_testeo["voluntarios"] == 6
    assert ev_testeo["incluye_testeo"] is True
    assert ev_testeo["masivo"] is False

    ev_completo = ev_desde_pack("COMPLETO", nombre="Festival X", duracion_horas=8)
    assert ev_completo["voluntarios"] == 15
    assert ev_completo["incluye_testeo"] is True
    assert ev_completo["masivo"] is True
    assert ev_completo["nombre"] == "Festival X"
    assert ev_completo["duracion_horas"] == 8
