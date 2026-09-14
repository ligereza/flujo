"""Build an artist-first map for visual portfolio review."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


RULES = (
    ("artist", "drefquila", ("drefquila", "dref_kun")),
    ("artist", "marlon-breeze", ("marlon breeze", "marlonbreeze")),
    ("artist", "ober", ("ober",)),
    ("artist", "harry-nach", ("harry nach", "harrynach")),
    ("artist", "sweet-tooth-skully", ("sweet tooth skully", "sweettoothskully")),
    ("artist", "youngkisz", ("youngkisz",)),
    ("collab", "tomas-pca", ("tomas.pca", "tomas.pcaa")),
    ("collab", "xascona", ("xascona",)),
    ("collab", "par4noi4rt", ("par4noi4rt",)),
    ("work", "zootropo", ("zootropo",)),
    ("work", "shisholina", ("shisholina",)),
    ("work", "rd-lsd", (" lsd", "\"lsd\"")),
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _haystack(row: dict) -> str:
    return " ".join((row.get("nota_humana", ""), row.get("descripcion_original", ""))).lower()


def _entities(row: dict) -> list[dict]:
    text = _haystack(row)
    found = []
    for kind, entity_id, needles in RULES:
        if any(needle in text for needle in needles):
            found.append({"kind": kind, "id": entity_id, "source": "metadata_or_human_note"})
    return found


def build(source: dict, context: dict | None = None) -> dict:
    media = []
    subjects = defaultdict(list)
    subject_kinds = {}
    for row in source.get("media", []):
        entities = _entities(row)
        artist = [e["id"] for e in entities if e["kind"] == "artist"]
        role = row.get("rol_provisional", "revisar")
        item = {
            "media": row.get("media"),
            "publicacion_id": row.get("publicacion_id"),
            "fecha": row.get("fecha_publicacion"),
            "descripcion_original": row.get("descripcion_original", ""),
            "nota_humana": row.get("nota_humana", ""),
            "decision_humana": row.get("decision_humana"),
            "role": role,
            "entities": entities,
            "primary_subject": artist[0] if artist else next(
                (e["id"] for e in entities if e["kind"] == "work"), None),
            "needs_review": not bool(entities),
        }
        media.append(item)
        for entity in entities:
            subjects[entity["id"]].append(row.get("media"))
            subject_kinds[entity["id"]] = entity["kind"]

    ctx = context or {}
    events = ctx.get("event_candidates", [])
    return {
        "schema": "faro-mapa-visual-artist-first-v1",
        "status": "draft_not_promoted",
        "rules": [
            "artista o cliente agrupa primero; evento y venue son relaciones",
            "colabs conserva usernames sin promoverlos a artista o cliente",
            "obra_concepto no es artista, venue ni evento",
            "sin episodio confirmado es un estado, nunca una entidad",
            "descripcion_original se conserva completa",
        ],
        "entities": [
            {"id": key, "kind": subject_kinds.get(key, "unknown"), "media": values}
            for key, values in sorted(subjects.items())
        ],
        "media": media,
        "event_candidates": events,
        "external_evidence": ctx.get("external_evidence", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--context", type=Path)
    args = parser.parse_args()
    context = _read(args.context) if args.context else {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(_read(args.source), context),
                                       ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
