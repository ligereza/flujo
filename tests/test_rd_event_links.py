from __future__ import annotations

import json
import sqlite3

from flujo.rd.panel import datos_panel, rd_event_link


def _root(tmp_path):
    (tmp_path / "data" / "productoras").mkdir(parents=True)
    (tmp_path / "knowledge" / "logos" / "vector").mkdir(parents=True)
    (tmp_path / "knowledge" / "venues").mkdir(parents=True)
    (tmp_path / "data" / "productoras" / "acme.json").write_text(json.dumps({
        "name": "Acme",
        "eventos": [{
            "nombre": "Fecha Acme",
            "fecha": "2026-11-20",
            "venue": "Espacio Riesco",
            "fuente": "https://example.test/flyer",
        }],
    }), encoding="utf-8")
    (tmp_path / "knowledge" / "venues" / "espacio_riesco.yaml").write_text(
        "name: Espacio Riesco\n", encoding="utf-8")
    return tmp_path


def test_event_link_is_exact_and_pending_without_operating_data(tmp_path):
    root = _root(tmp_path)
    event = datos_panel(root)["productoras"][0]["eventos"][0]
    result = rd_event_link(root, event["event_key"])
    assert result["status"] == "pending_review"
    assert result["productora_slug"] == "acme"
    assert result["event"]["venue_link"]["status"] == "exact"
    assert set(result["missing"]) == {"pack", "duracion_horas", "asistentes_estimados"}


def test_event_link_consumes_existing_plano_engine_with_explicit_draft(tmp_path):
    root = _root(tmp_path)
    event = datos_panel(root)["productoras"][0]["eventos"][0]
    result = rd_event_link(root, event["event_key"], {
        "pack": "INFO",
        "duracion_horas": 4,
        "asistentes_estimados": 250,
    })
    assert result["status"] == "ready"
    assert result["render"]["layout"]["pack"] == "INFO"
    assert result["render"]["rider"]
    assert result["links"]["rider"]["status"] == "generated"
    assert result["links"]["layout"]["status"] == "generated"


def test_event_card_reports_exact_existing_sqlite_projection(tmp_path):
    root = _root(tmp_path)
    source_event = datos_panel(root)["productoras"][0]["eventos"][0]
    conn = sqlite3.connect(root / "data" / "rd.db")
    conn.execute(
        "CREATE TABLE productora_eventos ("
        "id INTEGER PRIMARY KEY, productora_slug TEXT, nombre TEXT, fecha TEXT, "
        "venue TEXT, estado TEXT, fuente TEXT, fuentes_primarias TEXT, "
        "sin_fuente_primaria INTEGER)"
    )
    conn.execute(
        "INSERT INTO productora_eventos VALUES (?,?,?,?,?,?,?,?,?)",
        (1, "acme", source_event["nombre"], source_event["fecha"],
         source_event["venue"], source_event["estado"], source_event["fuente"],
         "[]", 1),
    )
    conn.commit()
    conn.close()

    event = datos_panel(root)["productoras"][0]["eventos"][0]
    assert event["database_link"]["status"] == "exact"
    assert event["database_link"]["id"] == 1
    assert event["triangulacion"]["status"] == "exact"
    assert rd_event_link(root, event["event_key"])["links"]["database"]["id"] == 1


def test_triangulation_joins_event_and_declared_venue_projection(tmp_path):
    root = _root(tmp_path)
    source = json.loads((root / "data" / "productoras" / "acme.json").read_text(encoding="utf-8"))
    source["venues"] = [{
        "nombre": "Espacio Riesco",
        "venue_id": "espacio_riesco",
        "preferido": True,
        "estado": "confirmado",
    }]
    (root / "data" / "productoras" / "acme.json").write_text(
        json.dumps(source), encoding="utf-8")
    conn = sqlite3.connect(root / "data" / "rd.db")
    conn.execute(
        "CREATE TABLE productora_eventos ("
        "id INTEGER PRIMARY KEY, productora_slug TEXT, nombre TEXT, fecha TEXT, "
        "venue TEXT, estado TEXT, fuente TEXT, fuentes_primarias TEXT, "
        "sin_fuente_primaria INTEGER)"
    )
    conn.execute(
        "CREATE TABLE productora_venues ("
        "id INTEGER PRIMARY KEY, productora_slug TEXT, venue_nombre TEXT, "
        "venue_id TEXT, preferido INTEGER, estado TEXT)"
    )
    conn.execute(
        "INSERT INTO productora_eventos VALUES (?,?,?,?,?,?,?,?,?)",
        (1, "acme", "Fecha Acme", "2026-11-20", "Espacio Riesco", "", "", "[]", 1),
    )
    conn.execute(
        "INSERT INTO productora_venues VALUES (?,?,?,?,?,?)",
        (1, "acme", "Espacio Riesco", "espacio_riesco", 1, "confirmado"),
    )
    conn.commit()
    conn.close()

    event = datos_panel(root)["productoras"][0]["eventos"][0]
    assert event["database_link"]["venue"]["status"] == "exact"
    assert event["database_link"]["venue"]["venue_id"] == "espacio_riesco"
    assert event["triangulacion"]["identidad_completa"] is True
    assert rd_event_link(root, event["event_key"])["links"]["venue_source"]["status"] == "exact"
