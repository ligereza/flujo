from __future__ import annotations

import json
from pathlib import Path

from flujo.vj.event_context import build_vj_event_context, event_to_plano_draft, read_vj_event_context


def _write_sources(tmp_path: Path) -> tuple[Path, Path]:
    productoras, venues = tmp_path / "productoras", tmp_path / "venues"
    productoras.mkdir()
    venues.mkdir()
    (venues / "venue-demo.yaml").write_text(
        "id: venue-demo\nname: Sala Demo\ntype: club\nscale_default: base\n"
        "capacity_bucket: medium\n", encoding="utf-8"
    )
    (productoras / "demo.json").write_text(json.dumps({
        "name": "Demo Producer", "confirmed": "human-confirmed",
        "venues": [{"nombre": "Sala Demo", "venue_id": "venue-demo",
                     "preferido": True, "estado": "confirmado"}],
        "eventos": [{"nombre": "Demo Night -- lineup DJ Alpha (co-org Partner)",
                     "fecha": "20 noviembre 2026", "venue": "Sala Demo",
                     "estado": "activo_anunciado", "fuente": "official source"}],
    }, ensure_ascii=True), encoding="utf-8")
    return productoras, venues


def test_build_preserves_source_venue_and_does_not_join_by_name(tmp_path: Path) -> None:
    productoras, venues = _write_sources(tmp_path)
    output = tmp_path / "vj_event_context.db"
    build_vj_event_context(output, productoras_dir=productoras, venues_dir=venues)
    payload = read_vj_event_context(output)
    assert payload["available"] is True
    assert payload["summary"]["events"] == 1
    event = payload["events"][0]
    assert event["eventKey"] == "producer_event:demo:0"
    assert event["dateIso"] == "2026-11-20"
    assert event["lineup"] == ["DJ Alpha"]
    assert event["coOrganizers"] == ["Partner"]
    assert event["venueLinks"][0]["venueId"] is None
    assert event["venueLinks"][0]["identityStatus"] == "unmatched_name"
    assert payload["producerVenues"][0]["venueId"] == "venue-demo"


def test_explicit_event_venue_id_is_the_only_event_join(tmp_path: Path) -> None:
    productoras, venues = _write_sources(tmp_path)
    path = productoras / "demo.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    profile["eventos"][0]["venue_id"] = "venue-demo"
    path.write_text(json.dumps(profile, ensure_ascii=True), encoding="utf-8")
    output = tmp_path / "vj_event_context.db"
    build_vj_event_context(output, productoras_dir=productoras, venues_dir=venues)
    event = read_vj_event_context(output)["events"][0]
    assert event["venueLinks"][0]["venueId"] == "venue-demo"
    assert event["venueLinks"][0]["identityStatus"] == "explicit_canonical"

def test_plano_draft_requires_operational_fields_without_guessing(tmp_path: Path) -> None:
    productoras, venues = _write_sources(tmp_path)
    output = tmp_path / "vj_event_context.db"
    build_vj_event_context(output, productoras_dir=productoras, venues_dir=venues)
    event = read_vj_event_context(output)["events"][0]

    draft = event_to_plano_draft(event)
    assert draft["proposal_only"] is True
    assert draft["ready_for_render"] is False
    assert draft["missing_fields"] == ["pack", "duracion_horas", "asistentes_estimados"]
    assert draft["event"]["nombre"] == "Demo Night -- lineup DJ Alpha (co-org Partner)"
    assert draft["event"]["ubicacion"] == "Sala Demo"

    ready = event_to_plano_draft(
        event, pack="INFO", duration_hours=6, attendees=250, layout_mode="grid_2x"
    )
    assert ready["ready_for_render"] is True
    assert ready["event"]["pack"] == "INFO"

def test_missing_database_is_read_only_and_non_mutating(tmp_path: Path) -> None:
    output = tmp_path / "not-built.db"
    payload = read_vj_event_context(output)
    assert payload == {"schema": "mak-vj-event-context-v1", "available": False,
                       "read_only": True, "database": str(output.resolve()),
                       "reason": "not_built"}
    assert not output.exists()
