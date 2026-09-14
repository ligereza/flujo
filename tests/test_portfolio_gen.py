"""Tests del generador de portfolio (tools/portfolio/generar_portfolio.py).

Offline: sin red y sin depender de la historia completa de git (en CI el
checkout puede ser shallow); la parte git se prueba solo en su logica pura.
"""
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "tools" / "portfolio"))

import generar_portfolio as gp  # noqa: E402
from catalog_contract import CatalogContractError, load_catalog  # noqa: E402


def test_es_publicable_filtra_sensibles():
    for ruta in [
        ".env", "tools/vibo_voz/.env", "desktop/config.json", "2.txt",
        "algo/id_rsa", "certs/server.pem", "data/flujo.db", "backup.zip",
        "src/__pycache__/x.pyc", "web/node_modules/a/b.js", "_airdrop/x.md",
        "sub-3ff58c1c-055f-49d3-a830-2f42c23ccbd4-resource-providers-2026-07-10.csv",
    ]:
        assert not gp.es_publicable(ruta), ruta


def test_es_publicable_filtra_ruido_generado():
    assert not gp.es_publicable("context/flujo_hub.html")
    assert not gp.es_publicable("web/package-lock.json")


def test_es_publicable_acepta_normales():
    for ruta in [
        "src/flujo/eventos/flyer_auto.py", "docs/viejo.md",
        "svg/suplementos_rd/pieza.svg", "tools/keyboard_map.txt",
        "docs/CLI.md",
    ]:
        assert gp.es_publicable(ruta), ruta


def test_compactar_borrados_conserva_el_mas_reciente():
    eventos = [
        {"ruta": "a.py", "borrado": "2026-07-01", "commit": "222", "ext": "py"},
        {"ruta": "b.py", "borrado": "2026-06-01", "commit": "111", "ext": "py"},
        {"ruta": "a.py", "borrado": "2026-01-01", "commit": "000", "ext": "py"},
    ]
    salida = gp.compactar_borrados(eventos)
    assert [e["ruta"] for e in salida] == ["a.py", "b.py"]
    assert salida[0]["commit"] == "222"  # el mas nuevo gana


def test_proyectos_curados_validos():
    curado = json.loads(gp._CURADO.read_text(encoding="utf-8"))
    ids = [p["id"] for p in curado["proyectos"]]
    assert len(ids) == len(set(ids)), "ids duplicados"
    for p in curado["proyectos"]:
        for campo in ("id", "nombre", "linea", "estado", "descripcion"):
            assert p.get(campo), f"{p.get('id')}: falta {campo}"


def test_catalog_contract_distinguishes_visual_works():
    catalog = load_catalog(gp._CURADO)
    assert catalog["contract"]["name"] == "portfolio_project_catalog"
    assert catalog["contract"]["visual_works_source"] == "iskvw/datos/obras.json"


def test_catalog_contract_rejects_duplicate_or_non_ascii_ids(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps({
            "proyectos": [
                {"id": "ok-id", "nombre": "A", "linea": "cultura",
                 "estado": "activo", "descripcion": "x"},
                {"id": "ok-id", "nombre": "B", "linea": "cultura",
                 "estado": "activo", "descripcion": "y"},
            ]
        }), encoding="utf-8")
    try:
        load_catalog(path)
    except CatalogContractError as exc:
        assert "duplicate project id" in str(exc)
    else:
        raise AssertionError("duplicate ids must fail the catalogue contract")


def test_construir_proyectos_agrega_metadata():
    datos = gp.construir_proyectos()
    assert datos["version_flujo"] == gp.leer_version()
    assert datos["generado"]
    assert datos["proyectos"]


def test_minar_borrados_shape():
    # Tolerante a checkouts shallow: la lista puede ser corta o vacia,
    # pero cada entrada respeta el contrato y el filtro.
    entradas = gp.minar_borrados(max_entradas=50)
    assert len(entradas) <= 50
    for e in entradas:
        assert set(e) == {"ruta", "borrado", "commit", "ext"}
        assert gp.es_publicable(e["ruta"])
