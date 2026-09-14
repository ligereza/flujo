"""Regenerable event context for the VJ surface.

This is a read model, not a second source of truth. It separates the event
calendar consumed by VJ tools from the RD catalog while keeping exact source
references and uncertainty visible.

Producer identity comes from the canonical profile filename. Event venue text
is preserved as a source assertion and receives a canonical venue id only when
the source event carries that exact id. A producer's usual venue is never
silently promoted to an event venue. Historical test links are not read here.

The database is ignored by Git and is safe to regenerate from the canonical
JSON/YAML sources. HTTP reads never build or mutate it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..rd.eventos import normalizar_evento

CONTRACT = "mak-vj-event-context-v1"
_REPO = Path(__file__).resolve().parents[3]
DEFAULT_CONTEXT_DB_PATH = _REPO / "data" / "vj_event_context.db"
DEFAULT_PRODUCTORAS_DIR = _REPO / "data" / "productoras"
DEFAULT_VENUES_DIR = _REPO / "knowledge" / "venues"
_UNRESOLVED_VENUES = {"", "needs_confirmation", "santiago"}

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE producers (
    slug TEXT PRIMARY KEY, name TEXT NOT NULL, confirmed TEXT,
    source_ref TEXT NOT NULL, source_sha256 TEXT NOT NULL
);
CREATE TABLE venues (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, venue_type TEXT, scale TEXT,
    capacity TEXT, source_ref TEXT NOT NULL, source_sha256 TEXT NOT NULL
);
CREATE TABLE events (
    event_key TEXT PRIMARY KEY,
    producer_slug TEXT NOT NULL REFERENCES producers(slug),
    source_ref TEXT NOT NULL, source_index INTEGER NOT NULL,
    name TEXT NOT NULL, date_raw TEXT, date_iso TEXT,
    date_confidence TEXT NOT NULL, venue_name TEXT, status TEXT,
    source_text TEXT, lineup_json TEXT NOT NULL,
    co_organizers_json TEXT NOT NULL
);
CREATE TABLE event_producers (
    event_key TEXT NOT NULL REFERENCES events(event_key),
    producer_slug TEXT NOT NULL REFERENCES producers(slug),
    role TEXT NOT NULL, method TEXT NOT NULL, status TEXT NOT NULL,
    evidence TEXT NOT NULL, PRIMARY KEY (event_key, producer_slug)
);
CREATE TABLE event_venues (
    event_key TEXT NOT NULL REFERENCES events(event_key),
    venue_id TEXT REFERENCES venues(id), venue_name TEXT NOT NULL,
    method TEXT NOT NULL, identity_status TEXT NOT NULL, status TEXT NOT NULL,
    evidence TEXT NOT NULL, PRIMARY KEY (event_key, venue_name)
);
CREATE TABLE producer_venues (
    producer_slug TEXT NOT NULL REFERENCES producers(slug),
    venue_id TEXT REFERENCES venues(id), venue_name TEXT NOT NULL,
    preferred INTEGER NOT NULL, source_state TEXT, notes TEXT,
    source_ref TEXT NOT NULL, PRIMARY KEY (producer_slug, venue_name, source_ref)
);
CREATE INDEX idx_events_date ON events(date_iso, event_key);
CREATE INDEX idx_events_producer ON events(producer_slug, event_key);
CREATE INDEX idx_event_venues_name ON event_venues(venue_name, event_key);
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _relative_ref(path: Path, root: Path, suffix: str = "") -> str:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.name
    return relative + suffix


def _source_fingerprint(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: _relative_ref(item, root)):
        digest.update(_relative_ref(path, root).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _load_venues(venues_dir: Path) -> dict[str, dict[str, Any]]:
    """Load canonical venue identities using RD's existing YAML reader."""
    from ..rd.database import _load_yaml

    result: dict[str, dict[str, Any]] = {}
    for path in sorted(venues_dir.glob("*.yaml")):
        raw = _load_yaml(path)
        if not isinstance(raw, dict):
            continue
        venue_id = str(raw.get("id") or path.stem).strip()
        if not venue_id or venue_id in result:
            continue
        result[venue_id] = {
            "id": venue_id,
            "name": str(raw.get("name") or raw.get("nombre") or venue_id),
            "venue_type": raw.get("type") or raw.get("tipo"),
            "scale": raw.get("scale_default") or raw.get("escala"),
            "capacity": raw.get("capacity_bucket") or raw.get("capacidad"),
            "source_ref": _relative_ref(path, _REPO),
            "source_sha256": _sha256(path),
        }
    return result


def _insert_metadata(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        ((key, str(value)) for key, value in values.items()),
    )


def _temp_destination(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
    )
    os.close(fd)
    return Path(name)


def build_vj_event_context(
    destination: str | Path | None = None,
    *,
    productoras_dir: str | Path | None = None,
    venues_dir: str | Path | None = None,
) -> Path:
    """Build the VJ read model atomically and return its path."""
    target = Path(destination) if destination is not None else DEFAULT_CONTEXT_DB_PATH
    prod_dir = Path(productoras_dir) if productoras_dir is not None else DEFAULT_PRODUCTORAS_DIR
    venue_dir = Path(venues_dir) if venues_dir is not None else DEFAULT_VENUES_DIR
    prod_dir, venue_dir = prod_dir.resolve(), venue_dir.resolve()
    target = target.expanduser().resolve()
    venues = _load_venues(venue_dir)
    profiles = []
    for path in sorted(prod_dir.glob("*.json")):
        raw = _load_json(path)
        if raw is not None:
            profiles.append((path, raw))

    source_paths = [*sorted(prod_dir.glob("*.json")), *sorted(venue_dir.glob("*.yaml"))]
    fingerprint_root = _REPO if _REPO in prod_dir.parents else prod_dir.parent
    temporary = _temp_destination(target)
    try:
        with sqlite3.connect(temporary) as conn:
            conn.executescript(_SCHEMA)
            _insert_metadata(conn, {
                "schema": CONTRACT,
                "built_at": datetime.now(timezone.utc).isoformat(),
                "productoras_dir": str(prod_dir),
                "venues_dir": str(venue_dir),
                "source_fingerprint": _source_fingerprint(source_paths, fingerprint_root),
                "source_count": len(source_paths),
            })
            for path, profile in profiles:
                conn.execute(
                    "INSERT INTO producers(slug, name, confirmed, source_ref, source_sha256) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (path.stem, str(profile.get("name") or path.stem), profile.get("confirmed"),
                     _relative_ref(path, _REPO), _sha256(path)),
                )
            for venue in venues.values():
                conn.execute(
                    "INSERT INTO venues(id, name, venue_type, scale, capacity, source_ref, source_sha256) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (venue["id"], venue["name"], venue["venue_type"], venue["scale"],
                     venue["capacity"], venue["source_ref"], venue["source_sha256"]),
                )

            event_count = event_venue_count = producer_venue_count = 0
            for path, profile in profiles:
                producer_slug = path.stem
                for index, raw_event in enumerate(profile.get("eventos") or []):
                    if not isinstance(raw_event, dict):
                        continue
                    event = normalizar_evento(raw_event)
                    event_key = f"producer_event:{producer_slug}:{index}"
                    source_ref = _relative_ref(path, _REPO, f"#eventos[{index}]")
                    venue_name = event.venue.strip()
                    conn.execute(
                        "INSERT INTO events(event_key, producer_slug, source_ref, source_index, "
                        "name, date_raw, date_iso, date_confidence, venue_name, status, source_text, "
                        "lineup_json, co_organizers_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (event_key, producer_slug, source_ref, index, event.nombre, event.fecha.crudo,
                         event.fecha.iso, event.fecha.confianza, venue_name or None, event.estado,
                         event.fuente, _json(event.lineup), _json(event.co_organiza)),
                    )
                    conn.execute(
                        "INSERT INTO event_producers(event_key, producer_slug, role, method, status, evidence) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (event_key, producer_slug, "source_owner", "source_profile",
                         "source_assertion", source_ref),
                    )
                    event_count += 1
                    if venue_name:
                        explicit_id = str(raw_event.get("venue_id") or "").strip() or None
                        venue_id = explicit_id if explicit_id in venues else None
                        identity_status = (
                            "explicit_canonical" if venue_id else
                            "unresolved_name" if venue_name.lower() in _UNRESOLVED_VENUES else
                            "unmatched_name"
                        )
                        status = (
                            "source_assertion" if identity_status == "explicit_canonical" else
                            "review_required" if identity_status != "unmatched_name" else
                            "source_assertion_unmatched"
                        )
                        method = "explicit_source_id" if venue_id else "source_event_field"
                        conn.execute(
                            "INSERT INTO event_venues(event_key, venue_id, venue_name, method, "
                            "identity_status, status, evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (event_key, venue_id, venue_name, method, identity_status, status, source_ref),
                        )
                        event_venue_count += 1

                for index, raw_venue in enumerate(profile.get("venues") or []):
                    if not isinstance(raw_venue, dict):
                        continue
                    venue_name = str(raw_venue.get("nombre") or "").strip()
                    if not venue_name:
                        continue
                    explicit_id = str(raw_venue.get("venue_id") or "").strip() or None
                    venue_id = explicit_id if explicit_id in venues else None
                    conn.execute(
                        "INSERT INTO producer_venues(producer_slug, venue_id, venue_name, preferred, "
                        "source_state, notes, source_ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (producer_slug, venue_id, venue_name, 1 if raw_venue.get("preferido") else 0,
                         raw_venue.get("estado"), raw_venue.get("notas"),
                         _relative_ref(path, _REPO, f"#venues[{index}]")),
                    )
                    producer_venue_count += 1

            _insert_metadata(conn, {
                "event_count": event_count,
                "event_venue_count": event_venue_count,
                "producer_venue_count": producer_venue_count,
                "producer_count": len(profiles),
                "venue_count": len(venues),
            })
            conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"vj context integrity_check failed: {integrity}")
        os.replace(temporary, target)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    return target


def _read_metadata(conn: sqlite3.Connection) -> dict[str, str]:
    return {row[0]: row[1] for row in conn.execute("SELECT key, value FROM metadata")}


def _loads(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _open_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def read_vj_event_context(
    database: str | Path | None = None,
    *,
    status: str | None = None,
    event_key: str | None = None,
) -> dict[str, Any]:
    """Return a read-only JSON payload for the VJ consumer."""
    path = (Path(database) if database is not None else DEFAULT_CONTEXT_DB_PATH).expanduser().resolve()
    if not path.is_file():
        return {"schema": CONTRACT, "available": False, "read_only": True,
                "database": str(path), "reason": "not_built"}

    with _open_readonly(path) as conn:
        metadata = _read_metadata(conn)
        clauses, params = [], []
        if status:
            clauses.append("e.status = ?")
            params.append(status)
        if event_key:
            clauses.append("e.event_key = ?")
            params.append(event_key)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        events = []
        rows = conn.execute(
            "SELECT e.*, p.name AS producer_name FROM events e "
            "JOIN producers p ON p.slug = e.producer_slug" + where + " "
            "ORDER BY CASE WHEN e.date_iso IS NULL THEN 1 ELSE 0 END, e.date_iso, e.event_key",
            params,
        )
        for row in rows:
            event = {
                "eventKey": row["event_key"], "producerSlug": row["producer_slug"],
                "producerName": row["producer_name"], "sourceRef": row["source_ref"],
                "name": row["name"], "dateRaw": row["date_raw"], "dateIso": row["date_iso"],
                "dateConfidence": row["date_confidence"], "venueName": row["venue_name"],
                "status": row["status"], "sourceText": row["source_text"],
                "lineup": _loads(row["lineup_json"], []),
                "coOrganizers": _loads(row["co_organizers_json"], []), "venueLinks": [],
            }
            for venue in conn.execute(
                "SELECT venue_id, venue_name, method, identity_status, status, evidence "
                "FROM event_venues WHERE event_key = ? ORDER BY venue_name", (row["event_key"],)
            ):
                event["venueLinks"].append({
                    "venueId": venue["venue_id"], "venueName": venue["venue_name"],
                    "method": venue["method"], "identityStatus": venue["identity_status"],
                    "status": venue["status"], "evidence": venue["evidence"],
                })
            events.append(event)

        producer_venues = [{
            "producerSlug": row["producer_slug"], "venueId": row["venue_id"],
            "venueName": row["venue_name"], "preferred": bool(row["preferred"]),
            "sourceState": row["source_state"], "notes": row["notes"],
            "sourceRef": row["source_ref"],
        } for row in conn.execute(
            "SELECT producer_slug, venue_id, venue_name, preferred, source_state, notes, source_ref "
            "FROM producer_venues ORDER BY producer_slug, venue_name"
        )]
        venues = [dict(row) for row in conn.execute(
            "SELECT id, name, venue_type, scale, capacity, source_ref FROM venues ORDER BY name"
        )]
        summary = {
            "producers": int(metadata.get("producer_count", 0)),
            "venues": int(metadata.get("venue_count", 0)),
            "events": int(metadata.get("event_count", 0)), "eventsReturned": len(events),
            "eventsWithDate": conn.execute(
                "SELECT COUNT(*) FROM events WHERE date_iso IS NOT NULL"
            ).fetchone()[0],
            "eventsWithLineup": conn.execute(
                "SELECT COUNT(*) FROM events WHERE lineup_json != '[]'"
            ).fetchone()[0],
            "eventVenueMentions": int(metadata.get("event_venue_count", 0)),
            "producerVenueLinks": int(metadata.get("producer_venue_count", 0)),
            "canonicalEventVenueLinks": conn.execute(
                "SELECT COUNT(*) FROM event_venues WHERE venue_id IS NOT NULL"
            ).fetchone()[0],
        }
    return {
        "schema": CONTRACT, "available": True, "read_only": True, "database": str(path),
        "source": {
            "productorasDir": metadata.get("productoras_dir"),
            "venuesDir": metadata.get("venues_dir"), "fingerprint": metadata.get("source_fingerprint"),
            "count": int(metadata.get("source_count", 0)),
        },
        "builtAt": metadata.get("built_at"), "summary": summary,
        "venues": venues, "producerVenues": producer_venues, "events": events,
    }

def event_to_plano_draft(
    event: dict[str, Any], *, pack: str | None = None,
    duration_hours: float | int | None = None,
    attendees: int | None = None, layout_mode: str | None = None,
) -> dict[str, Any]:
    """Map one VJ event to a proposal for the existing Plano/Rider engine."""
    draft: dict[str, Any] = {
        "event_key": event.get("eventKey"),
        "nombre": event.get("name") or "Evento",
        "fecha": event.get("dateIso") or event.get("dateRaw"),
        "ubicacion": event.get("venueName"),
        "lineup": list(event.get("lineup") or []),
        "co_organiza": list(event.get("coOrganizers") or []),
    }
    if pack:
        draft["pack"] = pack
    if duration_hours is not None:
        draft["duracion_horas"] = duration_hours
    if attendees is not None:
        draft["asistentes_estimados"] = attendees
    if layout_mode:
        draft["layout_mode"] = layout_mode
    required = ("pack", "duracion_horas", "asistentes_estimados")
    missing = [key for key in required if key not in draft]
    invalid: list[str] = []
    if isinstance(draft.get("duracion_horas"), (int, float)) and draft["duracion_horas"] <= 0:
        invalid.append("duracion_horas")
    if isinstance(draft.get("asistentes_estimados"), (int, float)) and draft["asistentes_estimados"] < 0:
        invalid.append("asistentes_estimados")
    return {
        "schema": "mak-vj-plano-draft-v1",
        "proposal_only": True,
        "ready_for_render": not missing and not invalid,
        "missing_fields": missing,
        "invalid_fields": invalid,
        "event": draft,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build the regenerable VJ event context")
    parser.add_argument("--output", type=Path, default=DEFAULT_CONTEXT_DB_PATH)
    args = parser.parse_args()
    print(build_vj_event_context(args.output))
