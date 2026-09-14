"""Loss-aware projection from annotated MCP rows to MAK shot events.

The projection is intentionally mechanical.  It does not infer players,
coordinates, spin, fatigue, or counterfactual outcomes that are absent from
the source row.  Every event keeps a raw reference, source hash, parser
version, and explicit unknown-token inventory so a later Project IR consumer
can audit the transform instead of treating JSONL as ground truth.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .mcp import ingest_rows


SHOT_EVENT_SCHEMA = "mak.tennis.shot_event.v0.1"
TRANSFORM_ID = "mcp-minimal-v0.1->shot-event-v0.1"
UNKNOWN_ID = "UNKNOWN"


def _text(value: Any, fallback: str = UNKNOWN_ID) -> str:
    value = str(value or "").strip()
    return value or fallback


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _event_id(record: Mapping[str, Any], side: str, index: int) -> str:
    basis = "|".join(
        _text(record.get(key), "")
        for key in ("source_id", "source_file", "source_row", "source_sha256")
    )
    digest = hashlib.sha256(f"{basis}|{side}|{index}".encode("utf-8")).hexdigest()
    return "mcp-shot-" + digest[:24]


def _point_end_observed(point_end: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(point_end, Mapping):
        return {}
    kind = _text(point_end.get("type"), "")
    observed: dict[str, Any] = {}
    if kind == "winner":
        observed["winner"] = True
    elif kind in {"forced_error", "unforced_error"}:
        observed["error_type"] = kind
    if point_end.get("error"):
        observed["error_qualifier"] = str(point_end["error"])
    return observed


def row_to_shot_events(record: Mapping[str, Any], *, project_id: str = "") -> list[dict[str, Any]]:
    """Convert one :func:`ingest_rows` record to schema-shaped shot events."""
    raw = record.get("raw")
    parsed = record.get("parsed")
    if not isinstance(raw, Mapping) or not isinstance(parsed, Mapping):
        raise ValueError("mcp_record_requires_raw_and_parsed")
    source_row = _text(record.get("source_row"), "0")
    match_id = _text(raw.get("match_id") or raw.get("match"))
    point_id = _text(raw.get("point_id") or raw.get("point"), f"{UNKNOWN_ID}:{source_row}")
    source_record_id = f"{_text(record.get('source_file'))}:{source_row}"
    source = {
        "source_id": _text(record.get("source_id"), "SRC_MCP"),
        "source_record_id": source_record_id,
        "source_sha256": _text(record.get("source_sha256"), UNKNOWN_ID),
        "video_ref": None,
        "frame_start": None,
        "frame_contact": None,
        "frame_end": None,
    }
    events: list[dict[str, Any]] = []
    for side in ("first_serve_sequence", "second_serve_sequence"):
        sequence = parsed.get(side)
        if not isinstance(sequence, Mapping):
            continue
        shots = sequence.get("shots") if isinstance(sequence.get("shots"), list) else []
        has_explicit_unit = bool(sequence.get("serve_direction") or shots or sequence.get("point_end"))
        if not has_explicit_unit:
            continue
        units: list[tuple[str, Mapping[str, Any] | None]] = []
        if sequence.get("serve_direction"):
            units.append(("serve", {"serve_direction": sequence["serve_direction"]}))
        units.extend(("shot", shot if isinstance(shot, Mapping) else {}) for shot in shots)
        if not units:
            units.append(("outcome", None))
        for index, (kind, unit) in enumerate(units):
            observed: dict[str, Any] = {}
            if unit:
                if kind == "serve":
                    observed.update(unit)
                else:
                    observed.update({
                        "shot_type": unit.get("type"),
                        "direction_class": unit.get("direction"),
                        "depth_class": unit.get("return_depth"),
                    })
            if index == len(units) - 1:
                observed.update(_point_end_observed(sequence.get("point_end")))
            unknown_tokens = sequence.get("unknown_tokens")
            unknown_tokens = unknown_tokens if isinstance(unknown_tokens, list) else []
            event: dict[str, Any] = {
                "schema": SHOT_EVENT_SCHEMA,
                "shot_id": _event_id(record, side, index),
                "source": source,
                "epistemic_status": _text(record.get("epistemic_status"), "ANNOTATED"),
                "match_id": match_id,
                "point_id": point_id,
                "rally_index": _optional_int(raw.get("rally_index") or raw.get("rally")),
                "shot_index": index,
                "actor": raw.get("actor") or raw.get("player") or None,
                "timestamp_ref": None,
                "observed": observed,
                "derived": {
                    "uncertainty": {
                        "unknown_tokens": unknown_tokens,
                        "unmodeled": ["ball_xyz", "spin_estimate", "fatigue_proxy"],
                    }
                },
                "outcome": {},
                "provenance": {
                    "raw_ref": f"{source['source_id']}:{source_record_id}",
                    "transform_chain": [TRANSFORM_ID],
                    "model_versions": {},
                    "human_review": None,
                    "project_ref": f"project:{project_id}" if project_id else None,
                },
            }
            events.append(event)
    return events


def ingest_shot_events(source: str | Path, *, project_id: str = "") -> Iterable[dict[str, Any]]:
    """Yield shot events from a local MCP CSV without network access."""
    for record in ingest_rows(source):
        yield from row_to_shot_events(record, project_id=project_id)


def write_shot_events_jsonl(
    source: str | Path, destination: str | Path, *, project_id: str = ""
) -> int:
    """Write deterministic shot-event JSONL and return the event count."""
    count = 0
    with Path(destination).expanduser().open("w", encoding="utf-8") as output:
        for event in ingest_shot_events(source, project_id=project_id):
            output.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
