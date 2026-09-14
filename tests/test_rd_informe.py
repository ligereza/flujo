"""Tests para flujo.rd.informe -- informe trimestral, resumen JSON del hub
y export CSV de agregados (F3b, sobre F3a #157).

Cubre:
  - informe demo (>=3 tablas + disclaimer presente).
  - tasa_adulteracion / tendencias / atenciones_por_tipo con fixture
    conocida (numeros exactos, no solo "no esta vacio").
  - rango_trimestre: formato valido/invalido.
  - resumen_json: DB inexistente -> {"disponible": False} (nunca lanza);
    DB con datos -> totales correctos.
  - endpoint del hub GET /api/rd-datos-summary (patron del hub smoke
    existente: instanciar HubRequestHandler via __new__, llamar el metodo
    privado directo -- sin socket real, ver tests/test_hotfix_03411.py).
  - exportar_csv_agregados: RUT inyectado en un agregado sintetico ->
    fila rechazada (defensa en profundidad, mismo scan de rd/datos.py).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from flujo.rd.datos import atenciones_por_tipo, conectar, rango_trimestre, tasa_adulteracion, tendencias
from flujo.rd.informe import (
    exportar_csv_agregados,
    informe_trimestral,
    resumen_json,
)
from flujo.web.hub import HubRequestHandler

_REPO = Path(__file__).resolve().parents[1]
_DEMO_DIR = _REPO / "data" / "rd_datos_demo"


def _db_demo_completa(tmp_path: Path) -> Path:
    """Ingesta los 3 CSV demo (30/15/15 filas, ver test_rd_datos.py) a una
    DB temporal y la retorna."""
    from flujo.rd.datos import ingest_csv

    db = tmp_path / "rd_datos.db"
    ingest_csv(_DEMO_DIR / "testeos_demo.csv", "testeo", db=db)
    ingest_csv(_DEMO_DIR / "atenciones_demo.csv", "atencion", db=db)
    ingest_csv(_DEMO_DIR / "encuestas_demo.csv", "encuesta", db=db)
    return db


# ---------------------------------------------------------------------------
# rango_trimestre
# ---------------------------------------------------------------------------

def test_rango_trimestre_q1_a_q4():
    assert rango_trimestre("2026-Q1") == ("2026-01-01", "2026-03-31")
    assert rango_trimestre("2026-Q2") == ("2026-04-01", "2026-06-30")
    assert rango_trimestre("2026-Q3") == ("2026-07-01", "2026-09-30")
    assert rango_trimestre("2026-Q4") == ("2026-10-01", "2026-12-31")


def test_rango_trimestre_bisiesto_q1():
    # 2028 es bisiesto: febrero tiene 29 dias, pero Q1 termina en marzo 31
    # (no depende de febrero); confirma que no se rompe con anio bisiesto.
    assert rango_trimestre("2028-Q1") == ("2028-01-01", "2028-03-31")


def test_rango_trimestre_formato_invalido_lanza():
    with pytest.raises(ValueError):
        rango_trimestre("2026-T3")
    with pytest.raises(ValueError):
        rango_trimestre("Q3-2026")
    with pytest.raises(ValueError):
        rango_trimestre("2026-Q5")


# ---------------------------------------------------------------------------
# tendencias / tasa_adulteracion / atenciones_por_tipo -- fixture conocida
# ---------------------------------------------------------------------------

def _db_fixture_conocida(tmp_path: Path) -> Path:
    """DB minima con numeros exactos y conocidos (no el demo grande) para
    poder assertar valores precisos de tasa/conteo."""
    db = tmp_path / "fixture.db"
    conn = conectar(db)
    conn.executemany(
        "INSERT INTO registros_testeo(fecha, sustancia_declarada, reactivo, coincide) "
        "VALUES (?,?,?,?)",
        [
            ("2026-07-01", "MDMA", "Marquis", 1),
            ("2026-07-15", "MDMA", "Marquis", 1),
            ("2026-08-01", "MDMA", "Marquis", 0),
            ("2026-08-10", "cocaina", "Simon", 0),
            ("2026-09-05", "cocaina", "Simon", 0),
            ("2026-09-06", "cocaina", "Simon", 1),
            ("2026-04-01", "ketamina", "Froehde", 1),  # fuera de Q3 -- filtro
        ],
    )
    conn.executemany(
        "INSERT INTO atenciones(fecha, tipo) VALUES (?,?)",
        [
            ("2026-07-01", "hidratacion"),
            ("2026-07-02", "hidratacion"),
            ("2026-08-01", "escucha"),
            ("2026-04-01", "derivacion"),  # fuera de Q3 -- filtro
        ],
    )
    conn.commit()
    conn.close()
    return db


def test_tendencias_conteo_exacto_sin_filtro(tmp_path):
    db = _db_fixture_conocida(tmp_path)
    conn = conectar(db)
    filas = {(r["mes"], r["sustancia_declarada"]): r["conteo"] for r in tendencias(conn)}
    conn.close()
    assert filas[("2026-07", "MDMA")] == 2
    assert filas[("2026-08", "MDMA")] == 1
    assert filas[("2026-08", "cocaina")] == 1
    assert filas[("2026-09", "cocaina")] == 2
    assert filas[("2026-04", "ketamina")] == 1


def test_tendencias_filtra_por_trimestre(tmp_path):
    db = _db_fixture_conocida(tmp_path)
    conn = conectar(db)
    filas = tendencias(conn, trimestre="2026-Q3")
    conn.close()
    sustancias = {f["sustancia_declarada"] for f in filas}
    assert "ketamina" not in sustancias  # abril queda fuera de Q3
    assert sum(f["conteo"] for f in filas) == 6  # 7 filas totales - 1 (abril)


def test_tasa_adulteracion_valores_exactos(tmp_path):
    db = _db_fixture_conocida(tmp_path)
    conn = conectar(db)
    tasa = {r["sustancia_declarada"]: r for r in tasa_adulteracion(conn)}
    conn.close()

    mdma = tasa["MDMA"]
    assert mdma["total"] == 3
    assert mdma["no_coincide"] == 1
    assert mdma["tasa"] == pytest.approx(1 / 3)

    cocaina = tasa["cocaina"]
    assert cocaina["total"] == 3
    assert cocaina["no_coincide"] == 2
    assert cocaina["tasa"] == pytest.approx(2 / 3)

    ketamina = tasa["ketamina"]
    assert ketamina["total"] == 1
    assert ketamina["no_coincide"] == 0
    assert ketamina["tasa"] == 0.0


def test_tasa_adulteracion_sin_registros_no_divide_por_cero(tmp_path):
    db = tmp_path / "vacia.db"
    conn = conectar(db)
    assert tasa_adulteracion(conn) == []
    conn.close()


def test_atenciones_por_tipo_conteo_exacto(tmp_path):
    db = _db_fixture_conocida(tmp_path)
    conn = conectar(db)
    conteos = {r["tipo"]: r["conteo"] for r in atenciones_por_tipo(conn)}
    conn.close()
    assert conteos["hidratacion"] == 2
    assert conteos["escucha"] == 1
    assert conteos["derivacion"] == 1


def test_atenciones_por_tipo_filtra_por_trimestre(tmp_path):
    db = _db_fixture_conocida(tmp_path)
    conn = conectar(db)
    conteos = {r["tipo"]: r["conteo"] for r in atenciones_por_tipo(conn, trimestre="2026-Q3")}
    conn.close()
    assert "derivacion" not in conteos  # abril queda fuera de Q3
    assert conteos["hidratacion"] == 2


# ---------------------------------------------------------------------------
# informe_trimestral -- >=3 tablas + disclaimer, sobre datos demo
# ---------------------------------------------------------------------------

def test_informe_demo_contiene_disclaimer_y_3_tablas(tmp_path):
    db = _db_demo_completa(tmp_path)
    md = informe_trimestral(db_path=db)

    assert "PRESUNTIVO" in md
    assert "DEMO/FICTICIOS" in md
    # el disclaimer debe aparecer ANTES de cualquier tabla (al inicio)
    primer_tabla = md.index("|")
    assert md.index("DISCLAIMER") < primer_tabla

    assert md.count("## ") >= 3  # al menos 3 secciones == al menos 3 tablas
    assert "Tendencias por sustancia declarada y mes" in md
    assert "Tasa de no-coincidencia por sustancia declarada" in md
    assert "Atenciones por tipo" in md

    # al menos 3 tablas markdown reales (separador de header)
    assert md.count("| --- ") >= 3 or md.count("|---") >= 3 or md.count("| ---") >= 3


def test_informe_demo_ascii_puro(tmp_path):
    db = _db_demo_completa(tmp_path)
    md = informe_trimestral(db_path=db)
    md.encode("ascii")  # lanza UnicodeEncodeError si hay algo no-ASCII


def test_informe_filtrado_por_trimestre_sin_datos_no_rompe(tmp_path):
    db = _db_demo_completa(tmp_path)
    # trimestre valido pero sin datos demo -> tablas vacias, no crashea
    md = informe_trimestral(db_path=db, trimestre="2019-Q1")
    assert "DISCLAIMER" in md
    assert "(sin datos)" in md


def test_informe_trimestre_invalido_propaga_value_error(tmp_path):
    db = _db_demo_completa(tmp_path)
    with pytest.raises(ValueError):
        informe_trimestral(db_path=db, trimestre="no-es-trimestre")


# ---------------------------------------------------------------------------
# resumen_json -- DB ausente vs DB con datos
# ---------------------------------------------------------------------------

def test_resumen_json_db_ausente_no_disponible_y_no_crea_archivo(tmp_path):
    db = tmp_path / "no_existe.db"
    out = resumen_json(db_path=db)
    assert out == {"disponible": False}
    assert not db.exists()  # una lectura NUNCA crea la DB como side-effect


def test_resumen_json_db_con_datos(tmp_path):
    db = _db_demo_completa(tmp_path)
    out = resumen_json(db_path=db)
    assert out["disponible"] is True
    assert out["total_testeos"] == 30
    assert out["total_atenciones"] == 15
    assert out["total_encuestas"] == 15
    assert 0.0 <= out["tasa_no_coincidencia_global"] <= 1.0
    assert out["ultimo_ingest"] is not None
    assert "PRESUNTIVO" in out["disclaimer"]


def test_resumen_json_no_lanza_ante_db_corrupta(tmp_path):
    db = tmp_path / "corrupta.db"
    db.write_bytes(b"esto no es un archivo sqlite valido")
    out = resumen_json(db_path=db)
    assert out.get("disponible") is False


# ---------------------------------------------------------------------------
# endpoint del hub: GET /api/rd-datos-summary
# ---------------------------------------------------------------------------

def test_hub_endpoint_rd_datos_summary_sin_db(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "flujo.web.hub.rd_datos_resumen_json",
        lambda: {"disponible": False},
    )
    handler = HubRequestHandler.__new__(HubRequestHandler)
    out = handler._get_rd_datos_summary()
    assert out == {"disponible": False}


def test_hub_endpoint_rd_datos_summary_con_db(monkeypatch, tmp_path):
    db = _db_demo_completa(tmp_path)

    from flujo.rd.informe import resumen_json as real_resumen_json

    monkeypatch.setattr(
        "flujo.web.hub.rd_datos_resumen_json",
        lambda: real_resumen_json(db_path=db),
    )
    handler = HubRequestHandler.__new__(HubRequestHandler)
    out = handler._get_rd_datos_summary()
    assert out["disponible"] is True
    assert out["total_testeos"] == 30


def test_hub_do_get_registra_ruta_rd_datos_summary():
    """Regresion barata: la ruta debe estar cableada en do_GET (fuente),
    igual que el resto de endpoints GET del hub."""
    import inspect
    from flujo.web import hub

    src = inspect.getsource(hub.HubRequestHandler.do_GET)
    assert '"/api/rd-datos-summary"' in src


# ---------------------------------------------------------------------------
# exportar_csv_agregados -- defensa en profundidad (RUT inyectado -> rechazo)
# ---------------------------------------------------------------------------

def test_exportar_csv_agregados_filas_limpias(tmp_path):
    filas = [
        {"sustancia_declarada": "MDMA", "no_coincide": 1, "total": 3, "tasa": "0.33"},
        {"sustancia_declarada": "cocaina", "no_coincide": 2, "total": 3, "tasa": "0.67"},
    ]
    out = tmp_path / "tasa.csv"
    n = exportar_csv_agregados(filas, out)
    assert n == 2
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["sustancia_declarada"] == "MDMA"


def test_exportar_csv_agregados_rut_inyectado_se_rechaza(tmp_path):
    """RUT chileno valido inyectado en un campo de un agregado sintetico
    (simula una fuga de schema futura): la fila entera se omite, el RUT
    jamas llega al CSV."""
    rut_valido = "12.345.678-5"
    filas = [
        {"sustancia_declarada": "MDMA", "no_coincide": 1, "total": 3, "tasa": "0.33"},
        {
            "sustancia_declarada": f"MDMA (contacto RUT {rut_valido})",
            "no_coincide": 0,
            "total": 1,
            "tasa": "0.0",
        },
    ]
    out = tmp_path / "tasa_con_rut.csv"
    n = exportar_csv_agregados(filas, out)
    assert n == 1  # solo la fila limpia

    contenido = out.read_text(encoding="utf-8")
    assert rut_valido not in contenido
    assert "12345678" not in contenido.replace(".", "").replace("-", "")


def test_exportar_csv_agregados_vacio_escribe_archivo_vacio(tmp_path):
    out = tmp_path / "vacio.csv"
    n = exportar_csv_agregados([], out)
    assert n == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""
