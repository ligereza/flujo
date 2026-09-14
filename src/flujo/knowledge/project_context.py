"""Evidence-aware context graph for artists, visual projects and shows.

The graph reuses the existing ``entities`` catalog in ``mak_knowledge.db``.
It adds only source claims and project anchors, so a context is queryable
without becoming a second raw database.  A relation is never promoted to
``verified`` merely because a name or date looks plausible: the relation
needs two independent evidence groups.  Operator attestations remain
explicitly human-attested.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .project_ir import LearningStore, stable_json, now_iso
from ..substrate import Absent, Resolution, Unique, resolve
from ..substrate.epistemics import MISSING_EVIDENCE


SCHEMA = "mak-project-context-v1"
SOURCE_STATUSES = {"observed", "candidate", "human_attested", "verified"}
RELATION_STATUSES = SOURCE_STATUSES | {"needs_evidence", "contradicted"}


class ProjectContextError(ValueError):
    """Raised when a context package cannot be persisted safely."""


def _hash(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


def _json(value: Any) -> str:
    return stable_json(value if value is not None else {})


def validate_context(payload: Mapping[str, Any]) -> list[str]:
    """Return structural errors without touching the database."""
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append("bad_schema")
    for key in ("context_id", "title", "entities", "sources", "relations", "projects"):
        if key not in payload:
            errors.append("missing_" + key)
    if not isinstance(payload.get("entities"), list):
        errors.append("entities_not_list")
    if not isinstance(payload.get("sources"), list):
        errors.append("sources_not_list")
    if not isinstance(payload.get("relations"), list):
        errors.append("relations_not_list")
    if not isinstance(payload.get("projects"), list):
        errors.append("projects_not_list")
    entity_ids: set[str] = set()
    for index, entity in enumerate(payload.get("entities", [])):
        if not isinstance(entity, Mapping):
            errors.append(f"entity_{index}_not_object")
            continue
        entity_id = _text(entity.get("entity_id"), 160)
        if not entity_id:
            errors.append(f"entity_{index}_missing_id")
        elif entity_id in entity_ids:
            errors.append(f"duplicate_entity:{entity_id}")
        entity_ids.add(entity_id)
        if not _text(entity.get("kind"), 80):
            errors.append(f"entity_{index}_missing_kind")
        if not _text(entity.get("display_name"), 300):
            errors.append(f"entity_{index}_missing_display_name")
    source_ids: set[str] = set()
    for index, source in enumerate(payload.get("sources", [])):
        if not isinstance(source, Mapping):
            errors.append(f"source_{index}_not_object")
            continue
        source_id = _text(source.get("source_id"), 180)
        if not source_id:
            errors.append(f"source_{index}_missing_id")
        elif source_id in source_ids:
            errors.append(f"duplicate_source:{source_id}")
        source_ids.add(source_id)
        if not _text(source.get("source_type"), 80):
            errors.append(f"source_{index}_missing_type")
        if not _text(source.get("independence_group"), 120):
            errors.append(f"source_{index}_missing_independence_group")
    for index, relation in enumerate(payload.get("relations", [])):
        if not isinstance(relation, Mapping):
            errors.append(f"relation_{index}_not_object")
            continue
        subject = _text(relation.get("subject"), 160)
        obj = _text(relation.get("object"), 160)
        requested = _text(relation.get("status") or "candidate", 40)
        if subject not in entity_ids:
            errors.append(f"relation_{index}_unknown_subject:{subject}")
        if obj not in entity_ids:
            errors.append(f"relation_{index}_unknown_object:{obj}")
        if requested not in RELATION_STATUSES:
            errors.append(f"relation_{index}_bad_status:{requested}")
        evidence = relation.get("source_ids", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"relation_{index}_missing_source_ids")
        else:
            errors.extend(
                f"relation_{index}_unknown_source:{source_id}"
                for source_id in evidence if source_id not in source_ids
            )
    return errors


def load_context(path: str | Path) -> dict[str, Any]:
    context_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectContextError(f"cannot_read_context:{context_path}") from exc
    if not isinstance(payload, dict):
        raise ProjectContextError("context_not_object")
    errors = validate_context(payload)
    if errors:
        raise ProjectContextError("invalid_context:" + ",".join(errors))
    payload["source_package"] = str(context_path)
    return payload


def _ensure_catalog_schema(con: sqlite3.Connection) -> None:
    """Make isolated tests usable while reusing the production catalog."""
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER PRIMARY KEY,
            entity_kind TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            path TEXT,
            status TEXT NOT NULL DEFAULT 'unclassified',
            purpose TEXT,
            idea TEXT,
            origin TEXT,
            confidence TEXT NOT NULL DEFAULT 'low',
            UNIQUE(entity_kind, canonical_name, path)
        );
        CREATE TABLE IF NOT EXISTS context_sources (
            source_id TEXT PRIMARY KEY,
            context_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            independence_group TEXT NOT NULL,
            locator TEXT NOT NULL,
            claim TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            updated_at TEXT NOT NULL,
            UNIQUE(context_id, source_id)
        );
        CREATE TABLE IF NOT EXISTS context_relations (
            relation_id TEXT PRIMARY KEY,
            context_id TEXT NOT NULL,
            subject_key TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_key TEXT NOT NULL,
            subject_entity_id INTEGER NOT NULL,
            object_entity_id INTEGER NOT NULL,
            requested_status TEXT NOT NULL,
            status TEXT NOT NULL,
            source_ids_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            decision_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            updated_at TEXT NOT NULL,
            UNIQUE(context_id, subject_key, predicate, object_key)
        );
        CREATE TABLE IF NOT EXISTS project_contexts (
            project_id TEXT PRIMARY KEY,
            context_id TEXT NOT NULL,
            project_title TEXT NOT NULL,
            project_role TEXT NOT NULL,
            service_role TEXT NOT NULL,
            artist_entity_id INTEGER,
            album_entity_id INTEGER,
            tour_entity_id INTEGER,
            status TEXT NOT NULL,
            context_json TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_context_relations_subject
            ON context_relations(subject_entity_id, predicate);
        CREATE INDEX IF NOT EXISTS idx_context_relations_object
            ON context_relations(object_entity_id, predicate);
        CREATE INDEX IF NOT EXISTS idx_project_contexts_context
            ON project_contexts(context_id, status);
        """
    )


def _upsert_entity(con: sqlite3.Connection, context_id: str, entity: Mapping[str, Any]) -> int:
    path = f"context://{context_id}/{_text(entity['entity_id'], 160)}"
    status = _text(entity.get("status") or "candidate", 40)
    confidence = {
        "verified": "high", "human_attested": "medium", "observed": "medium",
    }.get(status, "low")
    row = con.execute(
        "SELECT entity_id FROM entities WHERE entity_kind=? AND canonical_name=? AND path=?",
        (_text(entity["kind"], 80), _text(entity["display_name"], 300), path),
    ).fetchone()
    values = (
        _text(entity["kind"], 80), _text(entity["display_name"], 300), path, status,
        _text(entity.get("purpose"), 1200), _text(entity.get("idea"), 1200),
        _text(entity.get("origin"), 1200), confidence,
    )
    if row:
        con.execute(
            """UPDATE entities SET status=?,purpose=?,idea=?,origin=?,confidence=?
               WHERE entity_id=?""", (*values[3:], int(row[0])),
        )
        return int(row[0])
    cursor = con.execute(
        """INSERT INTO entities
           (entity_kind,canonical_name,path,status,purpose,idea,origin,confidence)
           VALUES (?,?,?,?,?,?,?,?)""", values,
    )
    return int(cursor.lastrowid)


def _source_map(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["source_id"]): item for item in payload["sources"]}


def _effective_relation_status(
    relation: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    requested = _text(relation.get("status") or "candidate", 40)
    source_rows = [sources[source_id] for source_id in relation.get("source_ids", [])]
    groups = sorted({
        _text(source.get("independence_group"), 120)
        for source in source_rows
        if _text(source.get("independence_group"), 120)
    })
    human = any(_text(source.get("status"), 40) == "human_attested" for source in source_rows)
    if requested == "verified":
        if len(groups) >= 2:
            return "verified", {"rule": "two_independent_source_groups", "groups": groups}
        return "candidate", {
            "rule": "verified_downgraded_missing_independent_group",
            "groups": groups,
            "required_groups": 2,
        }
    if requested == "human_attested" and not human:
        return "candidate", {"rule": "attestation_source_missing", "groups": groups}
    return requested, {"rule": "declared_status_preserved", "groups": groups}


def _resolve_project(con: sqlite3.Connection, item: Mapping[str, Any]) -> Resolution:
    """Every ``project_records`` row a caller-supplied id or title matches.

    MEASURED: ``project_records.title`` carries no UNIQUE constraint in the
    DDL (plain ``title TEXT NOT NULL``) and is written by three producers --
    ``reconstruction_adapter`` sets ``title=project_path`` (unique by
    construction) but ``source_learning`` and ``math_kernel`` both pass an
    arbitrary human- or JSON-authored ``case["title"]`` into the same table.
    A title lookup can therefore return 0, 1, or N rows. ``project_id`` is the
    table's PRIMARY KEY, so at most one row can ever match it -- that branch
    stays the unambiguous escape hatch even when titles collide.
    """
    project_id = _text(item.get("project_id"), 180)
    if project_id:
        row = con.execute(
            "SELECT project_id,title,state FROM project_records WHERE project_id=?", (project_id,)
        ).fetchone()
        return resolve([row] if row else [],
                       witness=f"project_id primary key matched: {project_id}",
                       cause=MISSING_EVIDENCE)
    title = _text(item.get("title"), 300)
    if title:
        rows = con.execute(
            "SELECT project_id,title,state FROM project_records WHERE title=? ORDER BY project_id",
            (title,),
        ).fetchall()
        return resolve(rows, witness=f"title matched exactly one project_records row: {title}",
                       cause=MISSING_EVIDENCE)
    return Absent(cause=MISSING_EVIDENCE)


def _context_summary(payload: Mapping[str, Any], project: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "context_id": _text(payload["context_id"], 180),
        "title": _text(payload["title"], 300),
        "scope": _text(payload.get("scope"), 300),
        "project_role": _text(project.get("role") or "visual_project", 120),
        "service_role": _text(project.get("service_role") or "", 240),
        "unknowns": sorted(set(_text(item, 300) for item in payload.get("unknowns", []))),
    }


def persist_context(database: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Persist sources, entities, relations and project anchors idempotently."""
    errors = validate_context(payload)
    if errors:
        raise ProjectContextError("invalid_context:" + ",".join(errors))
    context_id = _text(payload["context_id"], 180)
    source_map = _source_map(payload)
    entity_map: dict[str, int] = {}
    relation_rows: list[dict[str, Any]] = []
    project_rows: list[dict[str, Any]] = []
    source_ref = _text(payload.get("source_package"), 1200)
    store = LearningStore(database)
    with store.connect() as con:
        store.ensure_schema(con)
        _ensure_catalog_schema(con)
        for entity in payload["entities"]:
            entity_map[str(entity["entity_id"])] = _upsert_entity(con, context_id, entity)
        for source in payload["sources"]:
            source_id = str(source["source_id"])
            source_fingerprint = _hash({
                "context_id": context_id, "source_id": source_id,
                "source_type": source.get("source_type"),
                "independence_group": source.get("independence_group"),
                "locator": source.get("locator"), "claim": source.get("claim"),
                "status": source.get("status"), "metadata": source.get("metadata", {}),
            })
            con.execute(
                """INSERT INTO context_sources
                   (source_id,context_id,source_type,independence_group,locator,claim,status,metadata_json,fingerprint,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_id) DO UPDATE SET
                   context_id=excluded.context_id,source_type=excluded.source_type,
                   independence_group=excluded.independence_group,locator=excluded.locator,
                   claim=excluded.claim,status=excluded.status,metadata_json=excluded.metadata_json,
                   fingerprint=excluded.fingerprint,updated_at=excluded.updated_at""",
                (source_id, context_id, _text(source["source_type"], 80),
                 _text(source["independence_group"], 120), _text(source.get("locator"), 1600),
                 _text(source.get("claim"), 2000), _text(source.get("status") or "observed", 40),
                 _json(source.get("metadata", {})), source_fingerprint, now_iso()),
            )
        for relation in payload["relations"]:
            subject = str(relation["subject"])
            obj = str(relation["object"])
            predicate = _text(relation["predicate"], 160)
            effective_status, decision = _effective_relation_status(relation, source_map)
            source_ids = [str(item) for item in relation.get("source_ids", [])]
            evidence = [
                {"source_id": source_id, "claim": source_map[source_id].get("claim", ""),
                 "locator": source_map[source_id].get("locator", ""),
                 "independence_group": source_map[source_id].get("independence_group", "")}
                for source_id in source_ids
            ]
            fingerprint = _hash({
                "context_id": context_id, "subject": subject, "predicate": predicate,
                "object": obj, "requested_status": relation.get("status"),
                "effective_status": effective_status, "source_ids": source_ids,
            })
            relation_id = "context-rel-" + fingerprint[:24]
            con.execute(
                """INSERT INTO context_relations
                   (relation_id,context_id,subject_key,predicate,object_key,subject_entity_id,object_entity_id,
                    requested_status,status,source_ids_json,evidence_json,decision_json,fingerprint,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(context_id,subject_key,predicate,object_key) DO UPDATE SET
                   subject_entity_id=excluded.subject_entity_id,object_entity_id=excluded.object_entity_id,
                   requested_status=excluded.requested_status,status=excluded.status,
                   source_ids_json=excluded.source_ids_json,evidence_json=excluded.evidence_json,
                   decision_json=excluded.decision_json,fingerprint=excluded.fingerprint,updated_at=excluded.updated_at""",
                (relation_id, context_id, subject, predicate, obj,
                 entity_map[subject], entity_map[obj], _text(relation.get("status") or "candidate", 40),
                 effective_status, _json(source_ids), _json(evidence), _json(decision), fingerprint, now_iso()),
            )
            relation_rows.append({
                "relation_id": relation_id, "subject": subject, "predicate": predicate,
                "object": obj, "requested_status": relation.get("status") or "candidate",
                "status": effective_status, "decision": decision, "source_ids": source_ids,
            })
        for project in payload["projects"]:
            resolution = _resolve_project(con, project)
            if not isinstance(resolution, Unique):
                # Absent or Many: writing project_contexts requires exactly one
                # project_records row (its PRIMARY KEY is the target), so an
                # ambiguous or missing title must not be narrowed to one by
                # picking a candidate here -- see _resolve_project's docstring
                # for the measured reason a title lookup can return N rows.
                unresolved = {"project_id": _text(project.get("project_id"), 180),
                             "title": _text(project.get("title"), 300), "resolved": False}
                if not isinstance(resolution, Absent):
                    unresolved["ambiguous"] = True
                    unresolved["candidates"] = [
                        {"project_id": str(candidate["project_id"]),
                         "state": str(candidate["state"])}
                        for candidate in resolution.candidates]
                project_rows.append(unresolved)
                continue
            row = resolution.value
            project_id = str(row["project_id"])
            summary = _context_summary(payload, project)
            entity_ids = project.get("entity_ids", {})
            artist_id = entity_map.get(str(entity_ids.get("artist")))
            album_id = entity_map.get(str(entity_ids.get("album")))
            tour_id = entity_map.get(str(entity_ids.get("tour")))
            fingerprint = _hash({"project_id": project_id, "summary": summary,
                                 "artist": artist_id, "album": album_id, "tour": tour_id})
            con.execute(
                """INSERT INTO project_contexts
                   (project_id,context_id,project_title,project_role,service_role,artist_entity_id,album_entity_id,
                    tour_entity_id,status,context_json,source_ref,fingerprint,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET
                   context_id=excluded.context_id,project_title=excluded.project_title,
                   project_role=excluded.project_role,service_role=excluded.service_role,
                   artist_entity_id=excluded.artist_entity_id,album_entity_id=excluded.album_entity_id,
                   tour_entity_id=excluded.tour_entity_id,status=excluded.status,
                   context_json=excluded.context_json,source_ref=excluded.source_ref,
                   fingerprint=excluded.fingerprint,updated_at=excluded.updated_at""",
                (project_id, context_id, str(row["title"]), summary["project_role"],
                 summary["service_role"], artist_id, album_id, tour_id,
                 _text(project.get("status") or "review_required", 40), _json(summary),
                 source_ref, fingerprint, now_iso()),
            )
            project_rows.append({"project_id": project_id, "title": str(row["title"]),
                                 "state": str(row["state"]), "resolved": True,
                                 "fingerprint": fingerprint})
    return {
        "schema": SCHEMA, "context_id": context_id,
        "database": str(Path(database).expanduser().resolve()),
        "entity_count": len(entity_map), "source_count": len(payload["sources"]),
        "relation_count": len(relation_rows), "project_count": len(project_rows),
        "relations": relation_rows, "projects": project_rows,
        "relation_statuses": {
            status: sum(row["status"] == status for row in relation_rows)
            for status in sorted(RELATION_STATUSES)
            if any(row["status"] == status for row in relation_rows)
        },
    }


def link_context_to_project_ir(database: str | Path, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Attach a compact context block to Project IR without changing its state."""
    errors = validate_context(payload)
    if errors:
        raise ProjectContextError("invalid_context:" + ",".join(errors))
    context_id = _text(payload["context_id"], 180)
    store = LearningStore(database)
    updates: list[dict[str, Any]] = []
    with store.connect() as con:
        store.ensure_schema(con)
        for project in payload["projects"]:
            resolution = _resolve_project(con, project)
            if not isinstance(resolution, Unique):
                # Requirement 6: an ambiguous title must produce an explicit
                # unresolved outcome the caller can see, not a silent no-op --
                # and it must not append/mutate this project's IR either way.
                unresolved = {"project_id": _text(project.get("project_id"), 180),
                             "title": _text(project.get("title"), 300), "resolved": False}
                if not isinstance(resolution, Absent):
                    unresolved["ambiguous"] = True
                    unresolved["candidates"] = [
                        {"project_id": str(candidate["project_id"]),
                         "state": str(candidate["state"])}
                        for candidate in resolution.candidates]
                updates.append(unresolved)
                continue
            row = resolution.value
            record = json.loads(con.execute(
                "SELECT ir_json FROM project_records WHERE project_id=?", (row["project_id"],)
            ).fetchone()[0])
            summary = _context_summary(payload, project)
            summary["anchor_entity_keys"] = project.get("entity_ids", {})
            summary["preserved_project_state"] = record.get("state")
            existing = record.get("project_context")
            record["project_context"] = summary
            evidence_marker = {"kind": "project_context", "status": "observed",
                               "schema": SCHEMA, "context_id": context_id,
                               "source_ref": _text(payload.get("source_package"), 1200)}
            evidence = list(record.get("evidence", []))
            if not any(item.get("kind") == "project_context" and item.get("context_id") == context_id
                       for item in evidence if isinstance(item, Mapping)):
                evidence.append(evidence_marker)
            record["evidence"] = evidence
            unknowns = list(record.get("unknowns", []))
            for unknown in payload.get("unknowns", []):
                if unknown not in unknowns:
                    unknowns.append(unknown)
            record["unknowns"] = unknowns
            context_relation = {
                "subject": record["project_id"], "predicate": "contextualized_by",
                "object": f"context://{context_id}", "confidence": "observed",
                "plane": "project_context", "context_id": context_id,
            }
            relations = list(record.get("relations", []))
            if not any(item.get("predicate") == "contextualized_by" and
                       item.get("object") == f"context://{context_id}"
                       for item in relations if isinstance(item, Mapping)):
                relations.append(context_relation)
            record["relations"] = relations
            fingerprint = store.save_project(record)
            updates.append({"project_id": str(row["project_id"]), "title": str(row["title"]),
                            "state": str(row["state"]), "fingerprint": fingerprint,
                            "state_preserved": record.get("state") == row["state"],
                            "had_previous_context": existing is not None})
    return updates


def build_report(result: Mapping[str, Any], updates: list[Mapping[str, Any]]) -> dict[str, Any]:
    # An unresolved entry (Absent or Many from _resolve_project) carries
    # "resolved": False and no "state_preserved" key at all, because nothing
    # was written for it. Counting it here via the ``False`` default would
    # misreport an ambiguous or missing title as a state change that never
    # happened, so it is excluded from the count rather than defaulted.
    written = [item for item in updates if item.get("resolved", True)]
    return {**dict(result), "project_ir_updates": [dict(item) for item in updates],
            "state_changes": sum(not item.get("state_preserved", False) for item in written),
            "postulations_created": 0}


def read_context(
    database: str | Path, *, context_id: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Read a compact context graph for Hub/Research consumers.

    The endpoint is intentionally query-only.  With no filter it returns the
    available context ids; a caller must name a context or project to receive
    the entity, relation and source cards.
    """
    path = Path(database).expanduser()
    if not path.is_file():
        return {"schema": "mak-project-context-read-v1", "available": False,
                "read_only": True, "reason": "database_missing", "contexts": []}
    try:
        con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        required = {"context_sources", "context_relations", "project_contexts", "entities"}
        present = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if not required <= present:
            con.close()
            return {"schema": "mak-project-context-read-v1", "available": False,
                    "read_only": True, "reason": "context_schema_not_initialized", "contexts": []}
        selected: set[str] = set()
        if project_id:
            selected.update(str(row[0]) for row in con.execute(
                "SELECT context_id FROM project_contexts WHERE project_id=?", (project_id,)
            ))
        if context_id:
            selected.add(str(context_id))
        if not selected:
            context_ids = [row[0] for row in con.execute(
                """SELECT context_id FROM context_sources
                   UNION SELECT context_id FROM context_relations
                   UNION SELECT context_id FROM project_contexts
                   ORDER BY context_id"""
            )]
            context_rows = [{
                "context_id": selected_id,
                "project_count": con.execute(
                    "SELECT COUNT(*) FROM project_contexts WHERE context_id=?", (selected_id,)
                ).fetchone()[0],
            } for selected_id in context_ids]
            con.close()
            return {"schema": "mak-project-context-read-v1", "available": True,
                    "read_only": True, "database": str(path.resolve()), "filtered": False,
                    "contexts": context_rows}
        contexts: list[dict[str, Any]] = []
        for selected_id in sorted(selected):
            context_projects = [dict(row) for row in con.execute(
                """SELECT project_id,project_title,project_role,service_role,status
                   FROM project_contexts WHERE context_id=? ORDER BY project_title,project_id""",
                (selected_id,),
            )]
            entities = [dict(row) for row in con.execute(
                """SELECT entity_id,entity_kind,canonical_name,status,confidence,purpose,idea,origin
                   FROM entities WHERE path LIKE ? ORDER BY entity_id""",
                (f"context://{selected_id}/%",),
            )]
            relations: list[dict[str, Any]] = []
            for row in con.execute(
                """SELECT r.subject_key,r.predicate,r.object_key,r.requested_status,r.status,
                          r.source_ids_json,r.decision_json,
                          s.canonical_name AS subject_name,o.canonical_name AS object_name
                   FROM context_relations r
                   JOIN entities s ON s.entity_id=r.subject_entity_id
                   JOIN entities o ON o.entity_id=r.object_entity_id
                   WHERE r.context_id=? ORDER BY r.subject_key,r.predicate,r.object_key""",
                (selected_id,),
            ):
                item = dict(row)
                item["source_ids"] = json.loads(item.pop("source_ids_json"))
                item["decision"] = json.loads(item.pop("decision_json"))
                relations.append(item)
            sources = [dict(row) for row in con.execute(
                """SELECT source_id,source_type,independence_group,locator,claim,status,metadata_json
                   FROM context_sources WHERE context_id=? ORDER BY source_id""",
                (selected_id,),
            )]
            for source in sources:
                source["metadata"] = json.loads(source.pop("metadata_json"))
            contexts.append({
                "context_id": selected_id,
                "projects": context_projects,
                "entities": entities,
                "relations": relations,
                "sources": sources,
                "relation_statuses": {
                    status: sum(row["status"] == status for row in relations)
                    for status in sorted(RELATION_STATUSES)
                    if any(row["status"] == status for row in relations)
                },
            })
        con.close()
        return {"schema": "mak-project-context-read-v1", "available": True,
                "read_only": True, "database": str(path.resolve()), "filtered": True,
                "filter": {"context_id": context_id or "", "project_id": project_id or ""},
                "contexts": contexts}
    except (OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        return {"schema": "mak-project-context-read-v1", "available": False,
                "read_only": True, "reason": type(exc).__name__, "contexts": []}
