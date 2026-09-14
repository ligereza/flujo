"""Explicit, idempotent continuation for one local research-job process."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from collections import Counter
from typing import Any

from ._io_helpers import utc_now_iso as _now


SCHEMA = "mak-research-job-continuation-v1"
ALGORITHM_VERSION = "research-job-continuation-1"
SUPPORTED_PROCESS = "extract"
CONFIRMATION_SCHEMA = "mak-research-human-confirmation-v1"
READINESS_SCHEMA = "mak-research-normalize-readiness-v1"
PLAN_SCHEMA = "mak-research-normalize-plan-v1"
DRY_RUN_SCHEMA = "mak-research-normalize-dry-run-v1"
LICENSE_SCHEMA = "mak-research-license-review-v1"
SOURCE_REVIEW_SCHEMA = "mak-research-license-source-review-v1"
COMPATIBILITY_SCHEMA = "mak-research-license-compatibility-plan-v1"
DEFAULT_SOURCE_REVIEW_ARTIFACT = Path("/home/mak/work/grammar-lab-20260912/artifacts/q910_license_source_review.json")
DEFAULT_SOURCE_REVIEW_SHA256 = "d09cb1c902e51e1510db0c7d7017861789eb1c3dbdf0a0841d2690d680811f70"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _error(error: str, detail: str, code: int) -> tuple[dict[str, Any], int]:
    return ({"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": False, "read_only": False, "status": "not_executed", "error": error, "detail": detail, "control": {"database_write": False, "decision_write": False, "promotion": "none", "publication": False}}, code)


def _ensure_receipts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS research_continuation_receipts (
           id INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
           job_id INTEGER NOT NULL, expected_process TEXT NOT NULL,
           status TEXT NOT NULL, payload_json TEXT NOT NULL,
           created_at TEXT NOT NULL
        )"""
    )


def _captured_records(conn: sqlite3.Connection, job_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT id,url,title,capture_status,http_status,raw_sha256,text_sha256,
                  license_state,license_evidence,credits_estimate
           FROM job_sources WHERE job_id=? AND capture_status='captured'
           ORDER BY id""", (job_id,)
    ).fetchall()
    return [{
        "source_ref": f"research-job:{job_id}:source:{row['id']}",
        "url": row["url"],
        "title": row["title"],
        "capture_status": row["capture_status"],
        "http_status": row["http_status"],
        "raw_sha256": row["raw_sha256"],
        "text_sha256": row["text_sha256"],
        "license_state": row["license_state"],
        "license_evidence": row["license_evidence"],
        "credits_estimate": row["credits_estimate"],
        "extraction_status": "source_record_only",
    } for row in rows]


def _ensure_confirmations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS research_extraction_confirmations (
           id INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
           job_id INTEGER NOT NULL, actor_id TEXT NOT NULL, actor_kind TEXT NOT NULL,
           input_sha256 TEXT NOT NULL, status TEXT NOT NULL,
           payload_json TEXT NOT NULL, created_at TEXT NOT NULL
        )"""
    )


def resume_research_job(
    db_path: str | Path,
    output_root: str | Path,
    *,
    job_id: int,
    expected_process: str,
    request_id: str,
) -> tuple[dict[str, Any], int]:
    """Execute exactly one persisted next process; repeat requests are no-ops."""

    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return _error("job_id_invalido", "job_id debe ser entero", 400)
    expected_process = str(expected_process or "").strip()
    request_id = str(request_id or "").strip()
    if job_id < 1:
        return _error("job_id_invalido", "job_id debe ser positivo", 400)
    if expected_process != SUPPORTED_PROCESS:
        return _error("process_not_supported", f"solo se puede reanudar {SUPPORTED_PROCESS} en esta versión", 409)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}", request_id):
        return _error("request_id_invalido", "request_id debe ser estable y alfanumérico", 400)
    db_path = Path(db_path).expanduser()
    output_root = Path(output_root).expanduser()
    if not db_path.is_file():
        return _error("research_registry_missing", "no existe el registro de research", 503)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        _ensure_receipts(conn)
        existing = conn.execute("SELECT payload_json FROM research_continuation_receipts WHERE request_id=?", (request_id,)).fetchone()
        if existing is not None:
            payload = json.loads(existing["payload_json"])
            payload["idempotent_replay"] = True
            conn.commit()
            return payload, 200
        job = conn.execute("SELECT id,question,domain,status,next_process FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None:
            conn.rollback()
            return _error("research_job_not_found", f"no existe el job {job_id}", 404)
        if job["next_process"] != expected_process:
            conn.rollback()
            return _error("next_process_mismatch", f"el job está en {job['next_process']}, no en {expected_process}", 409)
        records = _captured_records(conn, job_id)
        if not records:
            conn.rollback()
            return _error("captured_sources_missing", "extract requiere al menos una fuente capturada", 409)
        input_hash = _hash(records)
        continuation_dir = output_root / str(job_id) / "continuations"
        continuation_dir.mkdir(parents=True, exist_ok=True)
        output_path = continuation_dir / f"{request_id}.json"
        output = {
            "schema": "mak-research-extraction-v1",
            "job_id": job_id,
            "process": SUPPORTED_PROCESS,
            "question": job["question"],
            "domain": job["domain"],
            "input_sha256": input_hash,
            "records": records,
            "model_calls": 0,
            "external_calls": 0,
            "promotion": "none",
            "publication": False,
            "note": "extracción determinista de registros capturados; no interpreta ni publica claims",
        }
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        conn.execute("UPDATE job_steps SET status='done' WHERE job_id=? AND process_key=?", (job_id, SUPPORTED_PROCESS))
        conn.execute("UPDATE research_jobs SET status='extracted', next_process='normalize' WHERE id=?", (job_id,))
        conn.execute(
            "INSERT INTO audit_events(event_type,object_type,object_id,detail,created_at) VALUES (?,?,?,?,?)",
            ("continuation_extract", "research_job", job_id, f"request_id={request_id}; records={len(records)}; input_sha256={input_hash}; model_calls=0", _now()),
        )
        done_steps = conn.execute("SELECT COUNT(*) FROM job_steps WHERE job_id=? AND status='done'", (job_id,)).fetchone()[0]
        payload = {
            "schema": SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "available": True,
            "read_only": False,
            "idempotent_replay": False,
            "request_id": request_id,
            "job_id": job_id,
            "process": SUPPORTED_PROCESS,
            "status": "COMPLETED",
            "execution": {"kind": "deterministic_local", "model_calls": 0, "external_calls": 0},
            "previous_next_process": expected_process,
            "next_process": "normalize",
            "done_steps": done_steps,
            "output_ref": f"research/jobs/{job_id}/continuations/{request_id}.json",
            "input_sha256": input_hash,
            "control": {"database_write": True, "decision_write": False, "promotion": "none", "publication": False},
            "provenance": {"source": f"research-job:{job_id}:captured-sources", "deterministic": True, "interpretation_performed": False, "human_confirmation_required_for_next_transition": True},
        }
        conn.execute("INSERT INTO research_continuation_receipts(request_id,job_id,expected_process,status,payload_json,created_at) VALUES (?,?,?,?,?,?)", (request_id, job_id, expected_process, payload["status"], json.dumps(payload, ensure_ascii=False, sort_keys=True), _now()))
        conn.commit()
        return payload, 200


def confirm_research_extraction(
    db_path: str | Path,
    output_root: str | Path,
    *,
    job_id: int,
    actor: str,
    input_sha256: str,
    request_id: str,
) -> tuple[dict[str, Any], int]:
    """Record human confirmation without advancing the next process."""
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return _error("job_id_invalido", "job_id debe ser entero", 400)
    actor = str(actor or "").strip()
    input_sha256 = str(input_sha256 or "").strip().lower()
    request_id = str(request_id or "").strip()
    if job_id < 1:
        return _error("job_id_invalido", "job_id debe ser positivo", 400)
    if not actor or len(actor) > 160 or actor.lower() in {"system", "auto", "agent"}:
        return _error("human_actor_required", "la confirmación necesita un actor humano explícito", 400)
    if not re.fullmatch(r"[0-9a-f]{64}", input_sha256):
        return _error("input_sha256_invalido", "input_sha256 debe ser SHA-256", 400)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}", request_id):
        return _error("request_id_invalido", "request_id debe ser estable y alfanumérico", 400)
    db_path = Path(db_path).expanduser()
    output_root = Path(output_root).expanduser()
    if not db_path.is_file():
        return _error("research_registry_missing", "no existe el registro de research", 503)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        _ensure_confirmations(conn)
        existing = conn.execute("SELECT payload_json FROM research_extraction_confirmations WHERE request_id=?", (request_id,)).fetchone()
        if existing is not None:
            payload = json.loads(existing["payload_json"])
            if payload.get("job_id") != job_id or payload.get("input_sha256") != input_sha256 or payload.get("actor_id") != actor or payload.get("actor_kind") != "human":
                conn.rollback()
                return _error("request_id_conflict", "request_id ya fue usado con otra confirmación", 409)
            payload["idempotent_replay"] = True
            conn.commit()
            return payload, 200
        job = conn.execute("SELECT id,status,next_process FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None:
            conn.rollback()
            return _error("research_job_not_found", f"no existe el job {job_id}", 404)
        if job["status"] != "extracted" or job["next_process"] != "normalize":
            conn.rollback()
            return _error("extraction_confirmation_not_ready", "el job debe estar en extracted/normalize", 409)
        records = _captured_records(conn, job_id)
        capture_rows = conn.execute(
            "SELECT id,text_path,text_sha256 FROM job_sources WHERE job_id=? AND capture_status='captured' ORDER BY id",
            (job_id,),
        ).fetchall()
        current_hash = _hash(records)
        if current_hash != input_sha256:
            conn.rollback()
            return _error("extraction_hash_mismatch", "las fuentes capturadas cambiaron desde extract", 409)
        matching_output = None
        for candidate in sorted((output_root / str(job_id) / "continuations").glob("*.json")):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if data.get("schema") == "mak-research-extraction-v1" and data.get("job_id") == job_id and data.get("input_sha256") == input_sha256:
                matching_output = candidate
                break
        if matching_output is None:
            conn.rollback()
            return _error("extraction_output_missing", "no hay una salida extract vigente para confirmar", 409)
        payload = {
            "schema": CONFIRMATION_SCHEMA,
            "algorithm_version": "research-human-confirmation-1",
            "available": True,
            "read_only": False,
            "idempotent_replay": False,
            "request_id": request_id,
            "job_id": job_id,
            "actor_id": actor,
            "actor_kind": "human",
            "status": "CONFIRMED",
            "input_sha256": input_sha256,
            "next_process": "normalize",
            "execution": {"kind": "human_confirmation_only", "process_advanced": False, "normalize_execution": False},
            "output_ref": f"research/jobs/{job_id}/continuations/{matching_output.name}",
            "control": {"database_write": True, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
            "provenance": {"source": f"research-job:{job_id}:extract", "human_confirmed": True, "interpretation_performed": False},
        }
        conn.execute(
            "INSERT INTO audit_events(event_type,object_type,object_id,detail,created_at) VALUES (?,?,?,?,?)",
            ("human_confirmation_extract", "research_job", job_id, f"request_id={request_id}; actor_id={actor}; actor_kind=human; input_sha256={input_sha256}; next_process=normalize", _now()),
        )
        conn.execute(
            "INSERT INTO research_extraction_confirmations(request_id,job_id,actor_id,actor_kind,input_sha256,status,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (request_id, job_id, actor, "human", input_sha256, payload["status"], json.dumps(payload, ensure_ascii=False, sort_keys=True), _now()),
        )
        conn.commit()
        return payload, 200


def normalize_readiness(db_path: str | Path, *, job_id: int) -> tuple[dict[str, Any], int]:
    """Read the normalize gate without creating tables or changing state."""
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return ({"schema": READINESS_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    if job_id < 1:
        return ({"schema": READINESS_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    db_path = Path(db_path).expanduser()
    if not db_path.is_file():
        return ({"schema": READINESS_SCHEMA, "available": False, "read_only": True, "error": "research_registry_missing"}, 503)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT id,status,next_process FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None:
            return ({"schema": READINESS_SCHEMA, "available": False, "read_only": True, "error": "research_job_not_found"}, 404)
        current_hash = _hash(_captured_records(conn, job_id))
        confirmation = None
        try:
            row = conn.execute(
                "SELECT actor_id,actor_kind,input_sha256,status FROM research_extraction_confirmations WHERE job_id=? AND input_sha256=? ORDER BY id DESC LIMIT 1",
                (job_id, current_hash),
            ).fetchone()
            if row is not None:
                confirmation = {"actor_id": row["actor_id"], "actor_kind": row["actor_kind"], "input_sha256": row["input_sha256"], "status": row["status"]}
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                return ({"schema": READINESS_SCHEMA, "available": False, "read_only": True, "error": "research_confirmation_schema_invalid"}, 503)
    state_ready = job["status"] == "extracted" and job["next_process"] == "normalize"
    confirmed = state_ready and confirmation is not None and confirmation["status"] == "CONFIRMED" and confirmation["actor_kind"] == "human"
    return ({
        "schema": READINESS_SCHEMA,
        "algorithm_version": "research-normalize-readiness-1",
        "available": True,
        "read_only": True,
        "job_id": job_id,
        "job_status": job["status"],
        "next_process": job["next_process"],
        "input_sha256": current_hash,
        "current_input_sha256": current_hash,
        "human_attestation": {"present": confirmed, "actor_id": confirmation["actor_id"] if confirmation else None, "actor_kind": confirmation["actor_kind"] if confirmation else None, "matches_input_sha256": confirmation is not None and confirmation["input_sha256"] == current_hash},
        "execution": {"normalize_execution": False},
        "normalization_allowed": False,
        "next_action": "confirm_extraction_with_human_actor" if not confirmed else "provide_normalize_adapter_before_execution",
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
    }, 200)


def normalize_plan(db_path: str | Path, *, job_id: int) -> tuple[dict[str, Any], int]:
    """Build a structural normalize plan without writing or authorizing it."""
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return ({"schema": PLAN_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    if job_id < 1:
        return ({"schema": PLAN_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    db_path = Path(db_path).expanduser()
    if not db_path.is_file():
        return ({"schema": PLAN_SCHEMA, "available": False, "read_only": True, "error": "research_registry_missing"}, 503)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT id,status,next_process FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None:
            return ({"schema": PLAN_SCHEMA, "available": False, "read_only": True, "error": "research_job_not_found"}, 404)
        records = _captured_records(conn, job_id)
        current_hash = _hash(records)
        confirmation = None
        try:
            row = conn.execute(
                "SELECT actor_id,actor_kind,input_sha256,status FROM research_extraction_confirmations WHERE job_id=? AND input_sha256=? ORDER BY id DESC LIMIT 1",
                (job_id, current_hash),
            ).fetchone()
            if row is not None:
                confirmation = {"actor_id": row["actor_id"], "actor_kind": row["actor_kind"], "input_sha256": row["input_sha256"], "status": row["status"]}
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                return ({"schema": PLAN_SCHEMA, "available": False, "read_only": True, "error": "research_confirmation_schema_invalid"}, 503)
    confirmed = job["status"] == "extracted" and job["next_process"] == "normalize" and confirmation is not None and confirmation["status"] == "CONFIRMED" and confirmation["actor_kind"] == "human" and confirmation["input_sha256"] == current_hash
    return ({
        "schema": PLAN_SCHEMA,
        "algorithm_version": "research-normalize-plan-1",
        "available": True,
        "read_only": True,
        "job_id": job_id,
        "job_status": job["status"],
        "next_process": job["next_process"],
        "input_sha256": current_hash,
        "human_attestation": {"present": confirmed, "actor_id": confirmation["actor_id"] if confirmation else None, "actor_kind": confirmation["actor_kind"] if confirmation else None, "matches_input_sha256": confirmation is not None and confirmation["input_sha256"] == current_hash},
        "plan": {
            "record_count": len(records),
            "operations": ["preserve_source_ref", "preserve_raw_and_text_hashes", "validate_license_fields", "emit_candidates_for_human_mapping"],
            "preview": [{"source_ref": row["source_ref"], "title": row["title"], "raw_sha256": row["raw_sha256"], "text_sha256": row["text_sha256"], "license_state": row["license_state"], "candidate_kind": "unmapped_source_record"} for row in records],
            "semantic_claims_created": False,
        },
        "execution_allowed": False,
        "next_action": "confirm_extraction_with_human_actor" if not confirmed else "implement_and_review_normalize_adapter",
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
    }, 200)


def normalize_dry_run(db_path: str | Path, *, job_id: int) -> tuple[dict[str, Any], int]:
    """Project the bounded normalize output without canonicalizing or writing."""
    plan, code = normalize_plan(db_path, job_id=job_id)
    if code != 200:
        plan["schema"] = DRY_RUN_SCHEMA
        return plan, code
    preview = plan["plan"]["preview"]
    return ({
        "schema": DRY_RUN_SCHEMA,
        "algorithm_version": "research-normalize-dry-run-1",
        "available": True,
        "read_only": True,
        "job_id": plan["job_id"],
        "job_status": plan["job_status"],
        "next_process": plan["next_process"],
        "input_sha256": plan["input_sha256"],
        "human_attestation": plan["human_attestation"],
        "dry_run": {"would_preserve": preview, "records": len(preview), "semantic_transform_performed": False, "database_rows_created": 0},
        "execution": {"attempted": False, "normalize_execution": False, "model_calls": 0, "external_calls": 0},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False, "learning_demonstrated": False},
        "next_action": plan["next_action"],
    }, 200)


def license_review(db_path: str | Path, *, job_id: int) -> tuple[dict[str, Any], int]:
    """Summarize captured-source license evidence without approving it."""
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        return ({"schema": LICENSE_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    if job_id < 1:
        return ({"schema": LICENSE_SCHEMA, "available": False, "read_only": True, "error": "job_id_invalido"}, 400)
    db_path = Path(db_path).expanduser()
    if not db_path.is_file():
        return ({"schema": LICENSE_SCHEMA, "available": False, "read_only": True, "error": "research_registry_missing"}, 503)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT id,status,next_process FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None:
            return ({"schema": LICENSE_SCHEMA, "available": False, "read_only": True, "error": "research_job_not_found"}, 404)
        records = _captured_records(conn, job_id)
        capture_rows = conn.execute(
            "SELECT id,text_path,text_sha256 FROM job_sources WHERE job_id=? AND capture_status='captured' ORDER BY id",
            (job_id,),
        ).fetchall()
    states = Counter(str(row["license_state"] or "unknown") for row in records)
    capture_integrity = []
    for row in capture_rows:
        capture_path = Path(str(row["text_path"] or "")).expanduser()
        exists = capture_path.is_file()
        matches = exists and hashlib.sha256(capture_path.read_bytes()).hexdigest() == row["text_sha256"]
        capture_integrity.append({"source_id": row["id"], "text_sha256_matches": matches})
    sources = [{
        "source_ref": row["source_ref"],
        "title": row["title"],
        "text_sha256": row["text_sha256"],
        "license_state": row["license_state"],
        "license_evidence": row["license_evidence"],
        "verification": "verified" if row["license_state"] == "verified" else "pending_review",
    } for row in records]
    return ({
        "schema": LICENSE_SCHEMA,
        "algorithm_version": "research-license-review-1",
        "available": True,
        "read_only": True,
        "job_id": job_id,
        "job_status": job["status"],
        "next_process": job["next_process"],
        "input_sha256": _hash(records),
        "sources": sources,
        "counts": dict(sorted(states.items())),
        "capture_integrity": {"checked": len(capture_integrity), "matches": sum(1 for item in capture_integrity if item["text_sha256_matches"]), "all_match": bool(capture_integrity) and all(item["text_sha256_matches"] for item in capture_integrity)},
        "ready_for_attestation": bool(sources) and all(source["verification"] == "verified" for source in sources) and bool(capture_integrity) and all(item["text_sha256_matches"] for item in capture_integrity),
        "next_action": "repair_capture_integrity_before_license_review" if any(not item["text_sha256_matches"] for item in capture_integrity) else ("verify_license_evidence_before_human_attestation" if any(source["verification"] != "verified" for source in sources) else "human_attestation_review"),
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
    }, 200)


def license_source_review(
    db_path: str | Path,
    *,
    job_id: int,
    artifact_path: str | Path | None = None,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Project pinned official-source findings without changing license state."""
    current, code = license_review(db_path, job_id=job_id)
    if code != 200:
        current["schema"] = SOURCE_REVIEW_SCHEMA
        return current, code
    configured = str(artifact_path or os.environ.get("MAK_LICENSE_SOURCE_REVIEW_ARTIFACT", "")).strip()
    path = Path(configured).expanduser() if configured else DEFAULT_SOURCE_REVIEW_ARTIFACT
    if not path.is_file():
        return ({"schema": SOURCE_REVIEW_SCHEMA, "available": False, "read_only": True, "error": "license_source_review_missing"}, 503)
    raw = path.read_bytes()
    expected = (expected_sha256 or os.environ.get("MAK_LICENSE_SOURCE_REVIEW_EXPECTED_SHA256", DEFAULT_SOURCE_REVIEW_SHA256)).strip().lower()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        return ({"schema": SOURCE_REVIEW_SCHEMA, "available": False, "read_only": True, "error": "license_source_review_stale"}, 409)
    try:
        artifact = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ({"schema": SOURCE_REVIEW_SCHEMA, "available": False, "read_only": True, "error": "license_source_review_invalid"}, 409)
    findings = artifact.get("findings")
    controls = artifact.get("controls")
    current_refs = sorted(source["source_ref"] for source in current["sources"])
    finding_refs = sorted(str(item.get("source_ref") or "") for item in findings) if isinstance(findings, list) else []
    if artifact.get("schema") != SOURCE_REVIEW_SCHEMA or artifact.get("job_id") != job_id or artifact.get("input_sha256") != current["input_sha256"] or finding_refs != current_refs or not isinstance(findings, list) or len(findings) != 4 or not isinstance(controls, dict) or controls != {"registry_write": False, "attestation": False, "normalize": False, "promotion": "none", "publication": False}:
        return ({"schema": SOURCE_REVIEW_SCHEMA, "available": False, "read_only": True, "error": "license_source_review_invalid"}, 409)
    conflict_count = sum(1 for item in findings if item.get("license_state") == "source_verified_conflict")
    unknown_count = sum(1 for item in findings if "unknown" in str(item.get("license_state", "")) or "pending" in str(item.get("license_state", "")))
    return ({
        "schema": SOURCE_REVIEW_SCHEMA,
        "algorithm_version": "research-license-source-review-1",
        "available": True,
        "read_only": True,
        "job_id": job_id,
        "input_sha256": current["input_sha256"],
        "source_review_sha256": digest,
        "findings": findings,
        "conflicts": conflict_count,
        "unknown_or_pending": unknown_count,
        "ready_for_attestation": False,
        "next_action": "human_review_license_compatibility_and_source_scope",
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
    }, 200)


def license_compatibility_plan(db_path: str | Path, *, job_id: int) -> tuple[dict[str, Any], int]:
    """Classify review actions without making a legal or editorial decision."""
    source_review, code = license_source_review(db_path, job_id=job_id)
    if code != 200:
        source_review["schema"] = COMPATIBILITY_SCHEMA
        return source_review, code
    items = []
    for finding in source_review["findings"]:
        state = str(finding.get("license_state") or "")
        if state == "source_verified" and finding.get("official_license") == "MIT":
            action = "candidate_pending_human_notice_review"
        elif state == "source_verified_conflict":
            action = "blocked_conflict_requires_scope_review"
        elif "unknown" in state:
            action = "blocked_unknown_license"
        else:
            action = "blocked_package_scope_review"
        items.append({"source_ref": finding.get("source_ref"), "license_state": state, "official_license": finding.get("official_license"), "compatibility_action": action})
    return ({
        "schema": COMPATIBILITY_SCHEMA,
        "algorithm_version": "research-license-compatibility-plan-1",
        "available": True,
        "read_only": True,
        "job_id": job_id,
        "input_sha256": source_review["input_sha256"],
        "source_review_sha256": source_review["source_review_sha256"],
        "items": items,
        "candidate_count": sum(1 for item in items if item["compatibility_action"] == "candidate_pending_human_notice_review"),
        "blocked_count": sum(1 for item in items if item["compatibility_action"] != "candidate_pending_human_notice_review"),
        "ready_for_attestation": False,
        "legal_conclusion": False,
        "next_action": "human_review_license_compatibility_and_source_scope",
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "promotion": "none", "publication": False},
    }, 200)


__all__ = ["ALGORITHM_VERSION", "COMPATIBILITY_SCHEMA", "CONFIRMATION_SCHEMA", "DEFAULT_SOURCE_REVIEW_ARTIFACT", "DEFAULT_SOURCE_REVIEW_SHA256", "DRY_RUN_SCHEMA", "LICENSE_SCHEMA", "PLAN_SCHEMA", "READINESS_SCHEMA", "SCHEMA", "SOURCE_REVIEW_SCHEMA", "SUPPORTED_PROCESS", "confirm_research_extraction", "license_compatibility_plan", "license_review", "license_source_review", "normalize_dry_run", "normalize_plan", "normalize_readiness", "resume_research_job"]
