"""Tests para flujo.rd.datos -- ingesta privacy-first de datos de campo RD.

El test critico (`test_rut_valido_rechazado_y_nunca_llega_a_la_db`) es el que
justifica todo el modulo: una fila con un RUT chileno VALIDO (digito
verificador correcto, no solo el formato) debe ser rechazada Y el contenido
de ese RUT no debe aparecer en NINGUN lado de la DB resultante -- ni una fila
sanitizada a medias, ni un log, ni un dump completo via `sqlite3 iterdump`.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from flujo.rd.datos import (
    DEFAULT_DB_PATH,
    IngestResult,
    conectar,
    ingest_csv,
    validar_fila,
)

_REPO = Path(__file__).resolve().parents[1]
_DEMO_DIR = _REPO / "data" / "rd_datos_demo"

# RUT chileno con digito verificador REAL (modulo 11 de 12345678 -> 5), no un
# placeholder de formato: si el scan solo detectara formato esto igual pasa,
# pero usar el digito correcto deja el test a salvo de cualquier futura
# validacion de digito verificador que se agregue a flujo.privacy.
RUT_VALIDO = "12.345.678-5"


def _escribir_csv(path: Path, campos: list[str], filas: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for f in filas:
            w.writerow(f)


# ---------------------------------------------------------------------------
# conectar / schema
# ---------------------------------------------------------------------------

def test_conectar_crea_schema_no_destructivo(tmp_path: Path):
    db = tmp_path / "rd_datos.db"
    conn = conectar(db)
    tablas = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert {"registros_testeo", "atenciones", "encuestas"} <= tablas

    # Conectar de nuevo con datos ya insertados no debe borrar nada.
    conn = conectar(db)
    conn.execute(
        "INSERT INTO atenciones(fecha, evento, tipo) VALUES ('2026-05-01', 'ev', 'escucha')"
    )
    conn.commit()
    conn.close()
    conn = conectar(db)
    n = conn.execute("SELECT COUNT(*) FROM atenciones").fetchone()[0]
    conn.close()
    assert n == 1


def test_los_datos_de_terreno_van_a_la_unica_base():
    """Una sola base, por orden del operador el 2026-09-05.

    Antes esto exigia `rd_datos.db`, hermana de `rd.db`. La separacion existia
    porque `build_rd_db()` borra el archivo y lo reescribe, asi que un rebuild
    habria destruido registros de terreno. Eso se resolvio en el rebuild --ver
    `test_un_rebuild_no_destruye_los_datos_de_terreno`-- y no ya con dos
    archivos.
    """
    from flujo.rd.datos import LEGACY_DB_PATH, TABLAS_ACUMULATIVAS

    assert DEFAULT_DB_PATH.name == "rd.db"
    assert DEFAULT_DB_PATH.parent.name == "data"
    # La base previa se conserva: es la fuente de la migracion y no se borra.
    assert LEGACY_DB_PATH.name == "rd_datos.db"
    assert DEFAULT_DB_PATH != LEGACY_DB_PATH
    assert set(TABLAS_ACUMULATIVAS) == {"registros_testeo", "atenciones", "encuestas"}


# ---------------------------------------------------------------------------
# validar_fila
# ---------------------------------------------------------------------------

def test_validar_fila_testeo_ok():
    row = {"fecha": "2026-05-10", "sustancia_declarada": "MDMA", "reactivo": "Marquis"}
    assert validar_fila(row, "testeo") == []


def test_validar_fila_fecha_invalida():
    row = {"fecha": "10-05-2026", "sustancia_declarada": "MDMA", "reactivo": "Marquis"}
    errores = validar_fila(row, "testeo")
    assert any("ISO" in e for e in errores)


def test_validar_fila_fecha_vacia():
    row = {"fecha": "", "sustancia_declarada": "MDMA", "reactivo": "Marquis"}
    errores = validar_fila(row, "testeo")
    assert any("fecha vacia" in e for e in errores)


def test_validar_fila_campo_obligatorio_vacio():
    row = {"fecha": "2026-05-10", "sustancia_declarada": "", "reactivo": "Marquis"}
    errores = validar_fila(row, "testeo")
    assert any("sustancia_declarada" in e for e in errores)


def test_validar_fila_atencion_tipo_invalido():
    row = {"fecha": "2026-05-10", "tipo": "masaje"}
    errores = validar_fila(row, "atencion")
    assert any("tipo de atencion invalido" in e for e in errores)


def test_validar_fila_atencion_tipo_valido():
    row = {"fecha": "2026-05-10", "tipo": "hidratacion"}
    assert validar_fila(row, "atencion") == []


def test_validar_fila_encuesta_ok():
    row = {"fecha": "2026-05-10", "pregunta_id": "Q1", "respuesta": "si"}
    assert validar_fila(row, "encuesta") == []


def test_validar_fila_tipo_csv_desconocido():
    errores = validar_fila({"fecha": "2026-05-10"}, "otro")
    assert errores and "tipo de CSV desconocido" in errores[0]


# ---------------------------------------------------------------------------
# ingest_csv -- demo completo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre,tipo,esperadas",
    [
        ("testeos_demo.csv", "testeo", 30),
        ("atenciones_demo.csv", "atencion", 15),
        ("encuestas_demo.csv", "encuesta", 15),
    ],
)
def test_ingest_demo_completo(tmp_path: Path, nombre: str, tipo: str, esperadas: int):
    csv_path = _DEMO_DIR / nombre
    assert csv_path.exists(), f"falta {csv_path}"
    db = tmp_path / "rd_datos.db"
    res = ingest_csv(csv_path, tipo, db=db)
    assert isinstance(res, IngestResult)
    assert res.insertadas == esperadas
    assert res.rechazadas_pii == 0
    assert res.invalidas == 0

    conn = sqlite3.connect(db)
    tabla = {"testeo": "registros_testeo", "atencion": "atenciones", "encuesta": "encuestas"}[tipo]
    n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    conn.close()
    assert n == esperadas


def test_ingest_demo_insertadas_mas_rechazadas_igual_filas(tmp_path: Path):
    db = tmp_path / "rd_datos.db"
    res = ingest_csv(_DEMO_DIR / "testeos_demo.csv", "testeo", db=db)
    total_filas = 30
    assert res.insertadas + res.rechazadas_pii + res.invalidas == total_filas


# ---------------------------------------------------------------------------
# EL TEST CRITICO: RUT valido inyectado -> rechazo total, jamas persiste
# ---------------------------------------------------------------------------

def test_rut_valido_rechazado_y_nunca_llega_a_la_db(tmp_path: Path):
    csv_path = tmp_path / "con_rut.csv"
    campos = [
        "fecha", "evento", "sustancia_declarada", "reactivo", "resultado_color",
        "familia_detectada", "coincide", "adulterante_sospechado", "descartada", "notas",
    ]
    filas = [
        {
            "fecha": "2026-06-01", "evento": "Festival Rio Verde",
            "sustancia_declarada": "MDMA", "reactivo": "Marquis",
            "resultado_color": "negro-violeta", "familia_detectada": "MDMA",
            "coincide": 1, "adulterante_sospechado": "", "descartada": 0,
            "notas": f"contactar a esta persona, RUT {RUT_VALIDO}",
        },
        {
            "fecha": "2026-06-02", "evento": "Festival Rio Verde",
            "sustancia_declarada": "ketamina", "reactivo": "Froehde",
            "resultado_color": "amarillo palido", "familia_detectada": "ketamina",
            "coincide": 1, "adulterante_sospechado": "", "descartada": 0,
            "notas": "fila limpia sin PII",
        },
    ]
    _escribir_csv(csv_path, campos, filas)

    db = tmp_path / "rd_datos.db"
    # Incluso en modo sanitize, RUT/tarjeta se rechazan SIEMPRE.
    res = ingest_csv(csv_path, "testeo", db=db, policy="sanitize")

    assert res.insertadas == 1          # solo la fila limpia
    assert res.rechazadas_pii == 1      # la fila con RUT
    assert res.invalidas == 0

    # Dump completo de la DB: el RUT no puede aparecer en NINGUNA forma.
    conn = sqlite3.connect(db)
    dump = "\n".join(conn.iterdump())
    conn.close()
    assert RUT_VALIDO not in dump
    assert "12345678" not in dump.replace(".", "").replace("-", "")
    assert "contactar a esta persona" not in dump  # la fila entera, no solo el RUT


# ---------------------------------------------------------------------------
# policy strict vs sanitize (otro PII: email/telefono, sin RUT/tarjeta)
# ---------------------------------------------------------------------------

def _csv_con_email(path: Path) -> None:
    campos = ["fecha", "evento", "sustancia_declarada", "reactivo", "notas"]
    _escribir_csv(path, campos, [
        {
            "fecha": "2026-06-01", "evento": "Under Bosque",
            "sustancia_declarada": "MDMA", "reactivo": "Marquis",
            "notas": "escribir a juan@ejemplo.cl para seguimiento",
        },
    ])


def test_policy_strict_rechaza_email(tmp_path: Path):
    csv_path = tmp_path / "con_email.csv"
    _csv_con_email(csv_path)
    db = tmp_path / "rd_datos.db"
    res = ingest_csv(csv_path, "testeo", db=db, policy="strict")
    assert res.insertadas == 0
    assert res.rechazadas_pii == 1


def test_policy_sanitize_persiste_con_placeholder(tmp_path: Path):
    csv_path = tmp_path / "con_email.csv"
    _csv_con_email(csv_path)
    db = tmp_path / "rd_datos.db"
    res = ingest_csv(csv_path, "testeo", db=db, policy="sanitize")
    assert res.insertadas == 1
    assert res.rechazadas_pii == 0

    conn = sqlite3.connect(db)
    notas = conn.execute("SELECT notas FROM registros_testeo").fetchone()[0]
    conn.close()
    assert "[EMAIL]" in notas
    assert "juan@ejemplo.cl" not in notas


def test_policy_sanitize_cubre_campo_evento_no_solo_notas(tmp_path: Path):
    """Regresion: el PII puede aparecer en CUALQUIER columna de texto libre
    tipeada por un operador (no solo `notas`) -- ej. `evento`. El scan corre
    sobre la fila completa; la sanitizacion debe cubrir la fila completa
    tambien, o un email en `evento` se coló crudo a la DB."""
    csv_path = tmp_path / "con_email_en_evento.csv"
    campos = ["fecha", "evento", "sustancia_declarada", "reactivo", "notas"]
    _escribir_csv(csv_path, campos, [
        {
            "fecha": "2026-06-01",
            "evento": "contactar organizador a juan@ejemplo.cl",
            "sustancia_declarada": "MDMA", "reactivo": "Marquis",
            "notas": "fila sin PII en notas",
        },
    ])
    db = tmp_path / "rd_datos.db"
    res = ingest_csv(csv_path, "testeo", db=db, policy="sanitize")
    assert res.insertadas == 1
    assert res.rechazadas_pii == 0

    conn = sqlite3.connect(db)
    evento = conn.execute("SELECT evento FROM registros_testeo").fetchone()[0]
    conn.close()
    assert "[EMAIL]" in evento
    assert "juan@ejemplo.cl" not in evento


# ---------------------------------------------------------------------------
# filas invalidas: detalle truncado a 5, cuentan sin insertarse
# ---------------------------------------------------------------------------

def test_filas_invalidas_detalle_truncado_a_5(tmp_path: Path):
    csv_path = tmp_path / "invalidas.csv"
    campos = ["fecha", "sustancia_declarada", "reactivo"]
    filas = [{"fecha": "fecha-mala", "sustancia_declarada": "", "reactivo": ""} for _ in range(8)]
    _escribir_csv(csv_path, campos, filas)

    db = tmp_path / "rd_datos.db"
    res = ingest_csv(csv_path, "testeo", db=db)
    assert res.insertadas == 0
    assert res.invalidas == 8
    assert len(res.detalle_invalidas) == 5


def test_ingest_csv_tipo_invalido_lanza(tmp_path: Path):
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("fecha\n2026-05-01\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_csv(csv_path, "no-existe", db=tmp_path / "x.db")


def test_ingest_csv_policy_invalida_lanza(tmp_path: Path):
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("fecha\n2026-05-01\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_csv(csv_path, "testeo", db=tmp_path / "x.db", policy="permisivo")
