"""Tests para flujo.jobs.brief."""

from pathlib import Path
import pytest

from flujo.jobs.brief import (
    Brief,
    EstadoJob,
    Medidas,
    Entrega,
    Contenido,
    Restricciones,
    load_brief,
    save_brief,
    parse_yaml_simple,
    dump_yaml_simple,
    brief_from_text,
)


def test_estado_enum():
    assert EstadoJob.BORRADOR.value == "borrador"
    assert EstadoJob.LISTO_PARA_DISENAR.value == "listo_para_disenar"
    assert EstadoJob.ENTREGADO.value == "entregado"


def test_brief_tiene_datos_criticos():
    b = Brief(tipo_pieza="etiqueta", medidas=Medidas(ancho_cm=10, alto_cm=5))
    assert b.tiene_datos_criticos()
    b2 = Brief()
    assert not b2.tiene_datos_criticos()


def test_brief_puede_transicionar():
    b = Brief(estado=EstadoJob.LISTO_PARA_DISENAR)
    assert b.puede_transicionar(EstadoJob.EN_DISENO)
    assert not b.puede_transicionar(EstadoJob.ENTREGADO)


def test_parse_yaml_simple_basic():
    text = """
id: 2026-06-17_test
estado: borrador
cliente: Acme
medidas:
  ancho_cm: 10
  alto_cm: 5
"""
    data = parse_yaml_simple(text)
    assert data["id"] == "2026-06-17_test"
    assert data["estado"] == "borrador"
    assert data["cliente"] == "Acme"
    assert data["medidas"]["ancho_cm"] == 10


def test_dump_yaml_simple_roundtrip():
    original = {
        "id": "test",
        "estado": "borrador",
        "productos": ["uno", "dos"],
        "medidas": {"ancho_cm": 10.5, "alto_cm": 5.0},
    }
    text = dump_yaml_simple(original)
    parsed = parse_yaml_simple(text)
    assert parsed["id"] == "test"
    assert parsed["estado"] == "borrador"
    assert parsed["medidas"]["ancho_cm"] == 10.5


def test_load_save_brief(tmp_path: Path):
    brief = Brief(
        id="2026-06-17_test",
        estado=EstadoJob.LISTO_PARA_DISENAR,
        cliente="Acme",
        proyecto="Etiquetas Test",
        tipo_pieza="etiqueta",
        medidas=Medidas(ancho_cm=16.5, alto_cm=6.5, orientacion="horizontal"),
        productos=["Impulso", "Magnesio"],
    )
    path = tmp_path / "brief.yaml"
    save_brief(path, brief)
    loaded = load_brief(path)
    assert loaded.id == "2026-06-17_test"
    assert loaded.estado == EstadoJob.LISTO_PARA_DISENAR
    assert loaded.cliente == "Acme"
    assert loaded.tipo_pieza == "etiqueta"
    assert loaded.medidas.ancho_cm == 16.5
    assert "Impulso" in loaded.productos


def test_brief_from_text_detecta_tipo_y_medidas():
    text = """
Necesito una etiqueta de 16.5x6.5 cm con productos como Impulso y Magnesio.
"""
    b = brief_from_text(text, job_id="2026-06-17_etiquetas")
    assert b.tipo_pieza == "etiqueta"
    assert b.medidas.ancho_cm == 16.5
    assert b.medidas.alto_cm == 6.5
    assert "Impulso" in b.productos or "Magnesio" in b.productos
    assert b.estado == EstadoJob.BRIEF_EXTRAIDO


def test_brief_from_text_genera_pendientes_si_faltan_datos():
    text = "Hola, necesito algo."
    b = brief_from_text(text, job_id="test")
    assert len(b.pendientes) > 0
    assert any("medida" in p.lower() for p in b.pendientes)


def test_parse_yaml_simple_supports_scalar_lists_without_pyyaml():
    from flujo.jobs.brief import parse_yaml_simple

    data = parse_yaml_simple('''productos:\n  - Impulso\n  - Creatina\npendientes:\n  - Confirmar medida\nmedidas:\n  ancho_cm: 16.5\n  alto_cm: 6.5\n''')
    assert data["productos"] == ["Impulso", "Creatina"]
    assert data["pendientes"] == ["Confirmar medida"]
    assert data["medidas"]["ancho_cm"] == 16.5
