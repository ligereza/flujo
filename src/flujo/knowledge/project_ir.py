"""Open Project IR and append-only learning ledger for MAK.

This module is deliberately conservative.  It records references, metadata,
hashes and outcomes; it never copies a source tree and it never promotes an
unknown input to active truth without evidence.  The SQLite schema is an
extension point for the existing ``data/mak_knowledge.db`` database, but the
caller must explicitly choose the database path.

The first learning target is operational policy: remember what was tried,
what evidence was produced and when the system abstained.  Model weights are
not changed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ._contract_helpers import compact_json as stable_json
from ._io_helpers import utc_now_iso as now_iso


SCHEMA = "mak-project-ir-v1"
LEARNING_SCHEMA = "mak-learning-ledger-v1"
MAK_LEARN_V2_SCHEMA = "mak-learning-v2"

PROJECT_STATES = (
    "candidate",
    "unknown",
    "review_required",
    "active",
    "verified",
    "stale",
    "contradicted",
    "historical",
    "quarantined",
)
EPISODE_STATES = (
    "proposed",
    "running",
    "succeeded",
    "failed",
    "abstained",
    "needs_evidence",
    "rejected",
    "verified",
)
RULE_STATUSES = ("candidate", "promoted", "stale", "rejected", "retracted")
RULE_VERDICTS = ("support", "contradict", "neutral")
EVIDENCE_STATES = ("unverified", "observed", "verified", "contradicted")
RUN_EVENT_STATES = ("proposed", "running", "observed", "validated", "recorded", "rejected")
EVALUATION_SPLITS = ("replay", "holdout", "canary", "shadow")
EVALUATION_STATUSES = ("pending", "passed", "failed", "abstained")

FORMAT_FAMILIES = {
    ".py": "code", ".js": "code", ".ts": "code", ".html": "web",
    ".css": "web", ".svg": "vector", ".json": "data", ".jsonl": "data",
    ".yaml": "data", ".yml": "data", ".toml": "data", ".csv": "data",
    ".db": "database", ".sqlite": "database", ".sqlite3": "database",
    ".md": "text", ".txt": "text", ".odt": "document", ".pdf": "document",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
    ".gif": "image", ".mp4": "video", ".mov": "video", ".webm": "video",
    ".mkv": "video", ".wav": "audio", ".mp3": "audio", ".blend": "3d",
    ".obj": "3d", ".fbx": "3d", ".gltf": "3d", ".glb": "3d",
    ".zip": "archive", ".7z": "archive", ".tar": "archive", ".gz": "archive",
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", ".venv", "venv", "trash", "$recycle.bin",
}

ALLOWED_TRANSITIONS = {
    "candidate": {"unknown", "review_required", "active", "quarantined", "historical"},
    "unknown": {"candidate", "review_required", "quarantined", "historical"},
    "review_required": {"candidate", "active", "verified", "quarantined", "contradicted"},
    "active": {"verified", "stale", "contradicted", "review_required", "historical"},
    "verified": {"stale", "contradicted", "review_required", "historical"},
    "stale": {"active", "review_required", "historical", "quarantined"},
    "contradicted": {"review_required", "historical", "quarantined"},
    "historical": {"candidate", "review_required"},
    "quarantined": {"candidate", "review_required", "historical"},
}


class ProjectIRError(ValueError):
    """Invalid Project IR or unsafe bounded inventory request."""


class InventoryLimitError(ProjectIRError):
    """The requested source exceeds the explicit bounded inventory limit."""


def slug(value: str, fallback: str = "project") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    return text[:80] or fallback


def _text(value: Any, limit: int = 1000) -> str:
    return str(value or "").strip()[:limit]


def _list_text(values: Any, limit: int = 48) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    if not isinstance(values, Sequence):
        return []
    return [_text(item, 400) for item in values[:limit] if _text(item, 400)]


def format_family(path: str | Path) -> str:
    suffix = Path(path).suffix.casefold()
    return FORMAT_FAMILIES.get(suffix, "unknown")


def media_type(path: str | Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def _hash_file(path: Path, max_bytes: int) -> tuple[str, str]:
    if path.stat().st_size > max_bytes:
        return "", "skipped_size_limit"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), "full"


def inventory_source(
    source_root: str | Path,
    *,
    max_files: int = 5000,
    max_hash_bytes: int = 32 * 1024 * 1024,
) -> list[dict[str, Any]]:
    """Inventory one bounded source directory without copying it.

    File contents are read only for bounded SHA-256 hashing.  Large files
    remain traceable through size and mtime, with an explicit hash status.
    Symlinks and skipped system/cache directories are not followed.
    """
    root = Path(source_root).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"source_root_not_directory: {root}")
    rows: list[dict[str, Any]] = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name.casefold() not in SKIP_DIRS)
        for name in sorted(filenames):
            if len(rows) >= max_files:
                raise InventoryLimitError(f"max_files_exceeded: {max_files}")
            path = Path(current) / name
            if path.is_symlink():
                continue
            try:
                stat = path.stat()
                digest, hash_status = _hash_file(path, max_hash_bytes)
            except OSError as exc:
                rows.append({
                    "relative_path": path.relative_to(root).as_posix(),
                    "availability": "unreadable",
                    "error": type(exc).__name__,
                })
                continue
            relative = path.relative_to(root).as_posix()
            basis = f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\0{digest}"
            rows.append({
                "artifact_id": "artifact_" + hashlib.sha256(basis.encode()).hexdigest()[:32],
                "relative_path": relative,
                "name": path.name,
                "suffix": path.suffix.casefold(),
                "format_family": format_family(path),
                "media_type": media_type(path),
                "size_bytes": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
                "sha256": digest,
                "hash_status": hash_status,
                "availability": "present",
            })
    return sorted(rows, key=lambda item: item.get("relative_path", ""))


def build_project_ir(
    *,
    project_id: str,
    title: str,
    source_root: str | Path,
    artifacts: Iterable[Mapping[str, Any]] = (),
    domains: Iterable[str] = (),
    purpose: str = "",
    state: str = "candidate",
    evidence: Iterable[Mapping[str, Any]] = (),
    unknowns: Iterable[str] = (),
    relations: Iterable[Mapping[str, Any]] = (),
    source_kind: str = "folder",
    source_ref: str = "",
) -> dict[str, Any]:
    """Build a portable project record from references, never source copies."""
    normalized_id = slug(project_id)
    normalized_state = _text(state, 40).casefold() or "candidate"
    if normalized_state not in PROJECT_STATES:
        raise ProjectIRError(f"project_bad_state: {normalized_state}")
    rows = [dict(item) for item in artifacts]
    normalized_artifacts = []
    for item in rows:
        relative = _text(item.get("relative_path") or item.get("source_path"), 1000)
        if not relative:
            raise ProjectIRError("artifact_missing_relative_path")
        normalized_artifacts.append({
            "artifact_id": _text(item.get("artifact_id"), 100) or "artifact_" + hashlib.sha256(relative.encode()).hexdigest()[:32],
            "relative_path": relative,
            "name": _text(item.get("name") or Path(relative).name, 240),
            "suffix": _text(item.get("suffix") or Path(relative).suffix, 40).casefold(),
            "format_family": _text(item.get("format_family") or format_family(relative), 40),
            "media_type": _text(item.get("media_type") or media_type(relative), 160),
            "size_bytes": int(item.get("size_bytes") or 0),
            "mtime_ns": int(item.get("mtime_ns") or 0),
            "sha256": _text(item.get("sha256"), 64),
            "hash_status": _text(item.get("hash_status") or "not_computed", 40),
            "availability": _text(item.get("availability") or "present", 40),
            "role": _text(item.get("role") or "source", 80),
        })
    record = {
        "schema": SCHEMA,
        "project_id": normalized_id,
        "title": _text(title, 300) or normalized_id,
        "state": normalized_state,
        "source": {
            "kind": _text(source_kind, 80) or "folder",
            "root_ref": _text(source_ref or str(source_root), 1000),
            "root_exists": Path(source_root).is_dir(),
        },
        "purpose": _text(purpose, 1200),
        "domains": sorted(set(_list_text(domains, 24))),
        "artifacts": sorted(normalized_artifacts, key=lambda item: item["relative_path"]),
        "relations": [dict(item) for item in relations],
        "evidence": [dict(item) for item in evidence],
        "unknowns": _list_text(unknowns, 48),
        "next_action": "review_evidence" if normalized_state in {"unknown", "review_required"} else "select_consumer",
        "provenance": {
            "producer": "flujo.knowledge.project_ir",
            "method": "bounded_reference_inventory",
            "created_at": now_iso(),
        },
    }
    errors = validate_project_ir(record)
    if errors:
        raise ProjectIRError("invalid_project_ir: " + ",".join(errors))
    return record


def project_ir_from_application_package(
    package: Mapping[str, Any], *, source_ref: str = "application-package"
) -> dict[str, Any]:
    """Adapt an existing application draft into Project IR.

    Application drafts are evidence-bearing candidates, not proof of a
    finished project.  Their explicit gaps become ``unknowns`` and their
    MAK links become relations; source assets remain references.
    """
    if package.get("schema") != "mak-application-package-v1":
        raise ProjectIRError("application_bad_schema")
    project = package.get("project")
    if not isinstance(project, Mapping):
        raise ProjectIRError("application_missing_project")
    project_id = _text(project.get("project_id"), 100) or _text(package.get("application_id"), 100)
    if not project_id:
        raise ProjectIRError("application_missing_project_id")
    evidence_block = package.get("evidence") if isinstance(package.get("evidence"), Mapping) else {}
    source_root = _text(project.get("path") or source_ref, 1000)
    source_index_ref = _text(evidence_block.get("source_index"), 1000)
    if source_index_ref:
        try:
            index_path = Path(source_index_ref).expanduser()
            if index_path.is_file():
                index = json.loads(index_path.read_text(encoding="utf-8"))
                indexed_root = _text(index.get("source_root"), 1000) if isinstance(index, Mapping) else ""
                if indexed_root:
                    source_root = indexed_root
        except (OSError, ValueError, TypeError):
            pass
    assets = evidence_block.get("representative_assets", [])
    if not isinstance(assets, list):
        assets = []
    artifacts = []
    for item in assets[:48]:
        if not isinstance(item, Mapping):
            continue
        reference = _text(item.get("relative_path") or item.get("path") or item.get("mak_path"), 1000)
        if not reference:
            continue
        family = format_family(reference)
        if _text(item.get("media_kind"), 40).casefold() in {"structural", "3d"}:
            family = "3d"
        artifacts.append({
            "relative_path": reference,
            "name": Path(reference).name,
            "format_family": family,
            "media_type": media_type(reference),
            "size_bytes": int(item.get("bytes") or 0),
            "sha256": _text(item.get("full_sha256"), 64),
            "hash_status": "full" if item.get("full_sha256") else "not_computed",
            "availability": _text(item.get("availability") or "referenced", 40),
            "role": "representative_asset",
        })
    links = evidence_block.get("mak_links", [])
    if not isinstance(links, list):
        links = []
    relations = []
    for item in links[:48]:
        if not isinstance(item, Mapping):
            continue
        mak_path = _text(item.get("mak_path"), 1000)
        if mak_path:
            normalized_path = mak_path.replace("\\", "/").casefold()
            plane = "historical_win" if "/win/" in normalized_path or "/actions-runner/" in normalized_path else "active_mak"
            relations.append({
                "subject": project_id,
                "predicate": _text(item.get("relation") or "consumer_link", 120),
                "object": mak_path,
                "confidence": item.get("confidence", "unknown"),
                "plane": plane,
            })
    gaps = package.get("gaps", [])
    unknowns = []
    if isinstance(gaps, list):
        for gap in gaps[:48]:
            if isinstance(gap, Mapping):
                field = _text(gap.get("field"), 160)
                reason = _text(gap.get("reason"), 300)
                if field:
                    unknowns.append(f"{field}: {reason}" if reason else field)
    dimensionality = _text(project.get("dimensionality"), 80)
    fund = package.get("fund") if isinstance(package.get("fund"), Mapping) else {}
    fund_name = _text(fund.get("name") or fund.get("id"), 160)
    evidence = [{
        "kind": "application_package",
        "source_ref": source_ref,
        "application_id": _text(package.get("application_id"), 160),
        "status": "observed",
        "readiness": package.get("readiness"),
    }]
    record = build_project_ir(
        project_id=project_id,
        title=_text(project.get("title"), 300) or project_id,
        source_root=source_root,
        artifacts=artifacts,
        domains=[item for item in ("mak", "funding", dimensionality) if item],
        purpose=f"application_candidate:{fund_name}" if fund_name else "application_candidate",
        state="review_required",
        evidence=evidence,
        unknowns=unknowns,
        relations=relations,
        source_kind="application_package",
        source_ref=source_root,
    )
    record["application"] = {
        "application_id": _text(package.get("application_id"), 160),
        "fund": fund_name,
        "status": _text(package.get("status"), 120),
        "readiness": package.get("readiness"),
        "source_index": source_index_ref,
        "project_path": _text(project.get("path"), 1000),
    }
    return record


def load_application_package(path: str | Path) -> dict[str, Any]:
    package_path = Path(path).expanduser()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if not isinstance(package, dict):
        raise ProjectIRError("application_package_not_object")
    return project_ir_from_application_package(package, source_ref=str(package_path))


def validate_project_ir(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("schema", "project_id", "title", "state", "source", "purpose",
                "domains", "artifacts", "relations", "evidence", "unknowns",
                "next_action", "provenance")
    errors.extend("missing_" + key for key in required if key not in record)
    if record.get("schema") != SCHEMA:
        errors.append("bad_schema")
    if not _text(record.get("project_id"), 100):
        errors.append("missing_project_id")
    if record.get("state") not in PROJECT_STATES:
        errors.append("bad_state")
    for key in ("domains", "artifacts", "relations", "evidence", "unknowns"):
        if key in record and not isinstance(record[key], list):
            errors.append(key + "_not_list")
    source = record.get("source")
    if not isinstance(source, Mapping) or not _text(source.get("root_ref"), 1000):
        errors.append("bad_source")
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping) or not _text(provenance.get("producer"), 200):
        errors.append("bad_provenance")
    if record.get("state") in {"active", "verified"} and not record.get("evidence"):
        errors.append("active_requires_evidence")
    for index, artifact in enumerate(record.get("artifacts", [])):
        if not isinstance(artifact, Mapping) or not _text(artifact.get("relative_path"), 1000):
            errors.append(f"artifact_{index}_bad_reference")
    return errors


def _json(value: Any) -> str:
    return stable_json(value if value is not None else {})


def _record_fingerprint(record: Mapping[str, Any]) -> str:
    """Hash semantic content while ignoring volatile creation/update times."""
    snapshot = json.loads(json.dumps(record, ensure_ascii=False))
    provenance = snapshot.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("created_at", None)
        provenance.pop("updated_at", None)
    return hashlib.sha256(stable_json(snapshot).encode("utf-8")).hexdigest()


class LearningStore:
    """SQLite persistence for Project IR, episodes and explicit transitions."""

    def __init__(self, database: str | Path):
        self.database = Path(database).expanduser()

    def connect(self) -> sqlite3.Connection:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def ensure_schema(self, connection: sqlite3.Connection | None = None) -> None:
        own = connection is None
        con = connection or self.connect()
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS project_records (
                    project_id TEXT PRIMARY KEY,
                    schema_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    state TEXT NOT NULL,
                    source_root_ref TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    ir_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES project_records(project_id),
                    relative_path TEXT NOT NULL,
                    format_family TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    mtime_ns INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL DEFAULT '',
                    hash_status TEXT NOT NULL,
                    availability TEXT NOT NULL,
                    role TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(project_id, relative_path)
                );
                CREATE TABLE IF NOT EXISTS project_episodes (
                    episode_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES project_records(project_id),
                    objective TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    observation_json TEXT NOT NULL,
                    outcome_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    cost_json TEXT NOT NULL,
                    parent_episode_id TEXT,
                    source_snapshot_hash TEXT NOT NULL DEFAULT '',
                    code_commit TEXT NOT NULL DEFAULT '',
                    tool_versions_json TEXT NOT NULL DEFAULT '{}',
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS project_transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES project_records(project_id),
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_rules (
                    rule_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    trigger_json TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    scope_json TEXT NOT NULL DEFAULT '{}',
                    evidence_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    support_count INTEGER NOT NULL DEFAULT 0,
                    contradiction_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    promoted_at TEXT,
                    expires_at TEXT,
                    evaluation_id TEXT NOT NULL DEFAULT '',
                    retracted_at TEXT,
                    retraction_reason TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS project_contracts (
                    contract_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    contract_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fingerprint TEXT NOT NULL UNIQUE,
                    updated_at TEXT NOT NULL,
                    UNIQUE(kind, contract_key)
                );
                CREATE TABLE IF NOT EXISTS rule_observations (
                    observation_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL REFERENCES semantic_rules(rule_id),
                    episode_id TEXT NOT NULL REFERENCES project_episodes(episode_id),
                    verdict TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(rule_id, episode_id, verdict)
                );
                CREATE TABLE IF NOT EXISTS mak_run_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL REFERENCES project_records(project_id),
                    episode_id TEXT REFERENCES project_episodes(episode_id),
                    parent_event_id TEXT REFERENCES mak_run_events(event_id),
                    event_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    source_snapshot_hash TEXT NOT NULL,
                    code_commit TEXT NOT NULL,
                    tool_versions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                /*
                 * Operational propositions are part of the existing
                 * LearningStore authority, but are not project episodes or
                 * execution checkpoints.  The event JSON is the append-only
                 * record; the scalar columns are read indexes only.
                 */
                CREATE TABLE IF NOT EXISTS mak_operational_events (
                    event_id TEXT PRIMARY KEY,
                    archive_id TEXT NOT NULL,
                    proposition_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mak_operational_events_archive
                    ON mak_operational_events(archive_id, proposition_id, event_id);
                CREATE INDEX IF NOT EXISTS idx_mak_operational_events_proposition
                    ON mak_operational_events(proposition_id, event_id);
                CREATE TRIGGER IF NOT EXISTS mak_operational_events_no_update
                    BEFORE UPDATE ON mak_operational_events
                    BEGIN SELECT RAISE(ABORT, 'mak_operational_events_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS mak_operational_events_no_delete
                    BEFORE DELETE ON mak_operational_events
                    BEGIN SELECT RAISE(ABORT, 'mak_operational_events_append_only'); END;
                CREATE TABLE IF NOT EXISTS learning_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    target_kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    dataset_fingerprint TEXT NOT NULL,
                    split_kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    baseline_policy_id TEXT NOT NULL DEFAULT '',
                    candidate_policy_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                /*
                 * Archive-memory v2 is additive.  The first archive-memory
                 * tables were keyed by content and therefore cannot represent
                 * two physical paths with equal bytes.  They remain untouched
                 * as legacy data; the v2 tables are the canonical observer
                 * materialisation and deliberately have no content UNIQUE
                 * constraint.
                 */
                CREATE TABLE IF NOT EXISTS archive_memory_v2_archives (
                    archive_id TEXT PRIMARY KEY,
                    source_root_ref TEXT NOT NULL,
                    first_ingested_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS archive_memory_v2_snapshots (
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    semantic_hash TEXT NOT NULL,
                    semantic_json TEXT NOT NULL,
                    input_schema TEXT NOT NULL,
                    limits_json TEXT NOT NULL DEFAULT '{}',
                    change_set_json TEXT NOT NULL DEFAULT '{}',
                    source_root_ref TEXT NOT NULL,
                    first_ingested_at TEXT NOT NULL,
                    PRIMARY KEY (archive_id, snapshot_id),
                    FOREIGN KEY (archive_id) REFERENCES archive_memory_v2_archives(archive_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_v2_artifacts (
                    archive_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    physical_id TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    first_ingested_at TEXT NOT NULL,
                    PRIMARY KEY (archive_id, artifact_id),
                    UNIQUE (archive_id, physical_id),
                    UNIQUE (archive_id, artifact_ref),
                    FOREIGN KEY (archive_id) REFERENCES archive_memory_v2_archives(archive_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_v2_artifact_states (
                    state_id TEXT PRIMARY KEY,
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    physical_id TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    references_json TEXT NOT NULL DEFAULT '[]',
                    kind TEXT NOT NULL,
                    availability TEXT NOT NULL,
                    size INTEGER,
                    mtime_ns INTEGER,
                    extension TEXT NOT NULL DEFAULT '',
                    family TEXT NOT NULL DEFAULT 'unknown',
                    media_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                    content_sha256 TEXT,
                    content_id TEXT,
                    symlink_target TEXT,
                    error_code TEXT,
                    error_operation TEXT,
                    artifact_json TEXT NOT NULL DEFAULT '{}',
                    first_ingested_at TEXT NOT NULL,
                    UNIQUE (archive_id, snapshot_id, artifact_id),
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_v2_snapshots(archive_id, snapshot_id),
                    FOREIGN KEY (archive_id, artifact_id)
                        REFERENCES archive_memory_v2_artifacts(archive_id, artifact_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_v2_observations (
                    archive_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    observation_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    artifact_refs_json TEXT NOT NULL DEFAULT '[]',
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    method TEXT,
                    tool_version TEXT,
                    observed_at TEXT,
                    first_ingested_at TEXT NOT NULL,
                    PRIMARY KEY (archive_id, snapshot_id, observation_id),
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_v2_snapshots(archive_id, snapshot_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_v2_transformation_events (
                    archive_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    inputs_json TEXT NOT NULL DEFAULT '[]',
                    outputs_json TEXT NOT NULL DEFAULT '[]',
                    witness_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    tool_version TEXT NOT NULL DEFAULT '',
                    occurred_at TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (archive_id, event_id),
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_v2_snapshots(archive_id, snapshot_id)
                );
                CREATE INDEX IF NOT EXISTS idx_archive_memory_v2_snapshots_archive
                    ON archive_memory_v2_snapshots(archive_id, snapshot_id);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_v2_states_snapshot
                    ON archive_memory_v2_artifact_states(archive_id, snapshot_id, relative_path);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_v2_observations_snapshot
                    ON archive_memory_v2_observations(archive_id, snapshot_id);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_v2_events_snapshot
                    ON archive_memory_v2_transformation_events(archive_id, snapshot_id);
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_snapshots_no_update
                    BEFORE UPDATE ON archive_memory_v2_snapshots
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_snapshots_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_snapshots_no_delete
                    BEFORE DELETE ON archive_memory_v2_snapshots
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_snapshots_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_artifacts_no_update
                    BEFORE UPDATE ON archive_memory_v2_artifacts
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_artifacts_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_artifacts_no_delete
                    BEFORE DELETE ON archive_memory_v2_artifacts
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_artifacts_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_states_no_update
                    BEFORE UPDATE ON archive_memory_v2_artifact_states
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_states_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_states_no_delete
                    BEFORE DELETE ON archive_memory_v2_artifact_states
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_states_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_observations_no_update
                    BEFORE UPDATE ON archive_memory_v2_observations
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_observations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_observations_no_delete
                    BEFORE DELETE ON archive_memory_v2_observations
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_observations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_events_no_update
                    BEFORE UPDATE ON archive_memory_v2_transformation_events
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_events_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_v2_events_no_delete
                    BEFORE DELETE ON archive_memory_v2_transformation_events
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_v2_events_append_only'); END;
                CREATE TABLE IF NOT EXISTS archive_memory_archives (
                    archive_id TEXT PRIMARY KEY,
                    person_id TEXT NOT NULL DEFAULT '',
                    source_root_ref TEXT NOT NULL,
                    archive_fingerprint TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS archive_memory_snapshots (
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    snapshot_hash TEXT NOT NULL,
                    source_root_ref TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (archive_id, snapshot_id),
                    UNIQUE (archive_id, snapshot_hash),
                    FOREIGN KEY (archive_id) REFERENCES archive_memory_archives(archive_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_artifacts (
                    archive_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    format_family TEXT NOT NULL DEFAULT 'unknown',
                    media_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    first_seen_at TEXT NOT NULL,
                    PRIMARY KEY (archive_id, artifact_id),
                    UNIQUE (archive_id, content_sha256),
                    FOREIGN KEY (archive_id) REFERENCES archive_memory_archives(archive_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_artifact_states (
                    state_id TEXT PRIMARY KEY,
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    state_json TEXT NOT NULL DEFAULT '{}',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    observed_at TEXT NOT NULL,
                    UNIQUE (archive_id, snapshot_id, artifact_id, relative_path),
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_snapshots(archive_id, snapshot_id),
                    FOREIGN KEY (archive_id, artifact_id)
                        REFERENCES archive_memory_artifacts(archive_id, artifact_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_observations (
                    observation_id TEXT PRIMARY KEY,
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    value_json TEXT NOT NULL DEFAULT '{}',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    tool_version TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'observed',
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_snapshots(archive_id, snapshot_id)
                );
                CREATE TABLE IF NOT EXISTS archive_memory_transformation_events (
                    event_id TEXT PRIMARY KEY,
                    archive_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    inputs_json TEXT NOT NULL DEFAULT '[]',
                    outputs_json TEXT NOT NULL DEFAULT '[]',
                    witness_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    tool_version TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (archive_id, snapshot_id)
                        REFERENCES archive_memory_snapshots(archive_id, snapshot_id)
                );
                CREATE INDEX IF NOT EXISTS idx_project_artifacts_project
                    ON project_artifacts(project_id);
                CREATE INDEX IF NOT EXISTS idx_project_episodes_project
                    ON project_episodes(project_id, status);
                CREATE INDEX IF NOT EXISTS idx_project_transitions_project
                    ON project_transitions(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_rule_observations_rule
                    ON rule_observations(rule_id, verdict);
                CREATE INDEX IF NOT EXISTS idx_mak_run_events_project
                    ON mak_run_events(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_learning_evaluations_target
                    ON learning_evaluations(target_kind, target_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_snapshots_archive
                    ON archive_memory_snapshots(archive_id, observed_at);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_artifacts_archive
                    ON archive_memory_artifacts(archive_id, content_sha256);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_states_snapshot
                    ON archive_memory_artifact_states(archive_id, snapshot_id);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_observations_subject
                    ON archive_memory_observations(archive_id, subject_type, subject_id, observed_at);
                CREATE INDEX IF NOT EXISTS idx_archive_memory_events_snapshot
                    ON archive_memory_transformation_events(archive_id, snapshot_id, occurred_at);
                CREATE TRIGGER IF NOT EXISTS mak_run_events_no_update
                    BEFORE UPDATE ON mak_run_events
                    BEGIN SELECT RAISE(ABORT, 'mak_run_events_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS mak_run_events_no_delete
                    BEFORE DELETE ON mak_run_events
                    BEGIN SELECT RAISE(ABORT, 'mak_run_events_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS project_episodes_no_update
                    BEFORE UPDATE ON project_episodes
                    BEGIN SELECT RAISE(ABORT, 'project_episodes_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS project_episodes_no_delete
                    BEFORE DELETE ON project_episodes
                    BEGIN SELECT RAISE(ABORT, 'project_episodes_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS learning_evaluations_no_update
                    BEFORE UPDATE ON learning_evaluations
                    BEGIN SELECT RAISE(ABORT, 'learning_evaluations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS learning_evaluations_no_delete
                    BEFORE DELETE ON learning_evaluations
                    BEGIN SELECT RAISE(ABORT, 'learning_evaluations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_snapshots_no_update
                    BEFORE UPDATE ON archive_memory_snapshots
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_snapshots_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_snapshots_no_delete
                    BEFORE DELETE ON archive_memory_snapshots
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_snapshots_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_artifacts_no_update
                    BEFORE UPDATE ON archive_memory_artifacts
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_artifacts_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_artifacts_no_delete
                    BEFORE DELETE ON archive_memory_artifacts
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_artifacts_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_states_no_update
                    BEFORE UPDATE ON archive_memory_artifact_states
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_states_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_states_no_delete
                    BEFORE DELETE ON archive_memory_artifact_states
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_states_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_observations_no_update
                    BEFORE UPDATE ON archive_memory_observations
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_observations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_observations_no_delete
                    BEFORE DELETE ON archive_memory_observations
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_observations_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_events_no_update
                    BEFORE UPDATE ON archive_memory_transformation_events
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_events_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS archive_memory_events_no_delete
                    BEFORE DELETE ON archive_memory_transformation_events
                    BEGIN SELECT RAISE(ABORT, 'archive_memory_events_append_only'); END;
                """
            )
            v2_observation_columns = {
                str(row[1]) for row in con.execute(
                    "PRAGMA table_info(archive_memory_v2_observations)"
                )
            }
            for column, definition in (
                ("method", "TEXT"),
                ("tool_version", "TEXT"),
                ("observed_at", "TEXT"),
            ):
                if column not in v2_observation_columns:
                    con.execute(
                        f"ALTER TABLE archive_memory_v2_observations ADD COLUMN {column} {definition}"
                    )
            event_columns = {
                str(row[1]) for row in con.execute("PRAGMA table_info(mak_run_events)")
            }
            if "run_id" not in event_columns:
                con.execute(
                    "ALTER TABLE mak_run_events ADD COLUMN run_id TEXT NOT NULL DEFAULT ''"
                )
            episode_columns = {
                str(row[1]) for row in con.execute("PRAGMA table_info(project_episodes)")
            }
            for column, definition in (
                ("source_snapshot_hash", "TEXT NOT NULL DEFAULT ''"),
                ("code_commit", "TEXT NOT NULL DEFAULT ''"),
                ("tool_versions_json", "TEXT NOT NULL DEFAULT '{}'"),
            ):
                if column not in episode_columns:
                    con.execute(f"ALTER TABLE project_episodes ADD COLUMN {column} {definition}")
            rule_columns = {
                str(row[1]) for row in con.execute("PRAGMA table_info(semantic_rules)")
            }
            for column, definition in (
                ("scope_json", "TEXT NOT NULL DEFAULT '{}'"),
                ("expires_at", "TEXT"),
                ("evaluation_id", "TEXT NOT NULL DEFAULT ''"),
                ("retracted_at", "TEXT"),
                ("retraction_reason", "TEXT NOT NULL DEFAULT ''"),
            ):
                if column not in rule_columns:
                    con.execute(f"ALTER TABLE semantic_rules ADD COLUMN {column} {definition}")
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_mak_run_events_run ON mak_run_events(run_id, created_at)"
            )
            if own:
                con.commit()
        finally:
            if own:
                con.close()

    def save_project(self, record: Mapping[str, Any]) -> str:
        errors = validate_project_ir(record)
        if errors:
            raise ProjectIRError("invalid_project_ir: " + ",".join(errors))
        project_id = str(record["project_id"])
        encoded = stable_json(dict(record))
        fingerprint = _record_fingerprint(record)
        now = now_iso()
        with self.connect() as con:
            self.ensure_schema(con)
            previous = con.execute(
                "SELECT version, created_at, fingerprint FROM project_records WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if previous and previous["fingerprint"] == fingerprint:
                return fingerprint
            version = int(previous["version"]) + 1 if previous else 1
            created = previous["created_at"] if previous else now
            # A re-derivation refreshes the evidence, never the verdict.
            #
            # The producers here always emit ``review_required``, so re-running
            # an import over a project a person had already moved to ``active``
            # would silently drag it back into the queue and delete the only
            # thing in this database that a machine cannot regenerate. It is
            # harmless today only because nothing had ever been decided.
            #
            # A recorded transition is the evidence that someone decided. When
            # one exists, the stored state wins and the incoming one is dropped.
            state = str(record["state"])
            if previous:
                decided = con.execute(
                    "SELECT to_state FROM project_transitions WHERE project_id=? "
                    "ORDER BY created_at DESC, rowid DESC LIMIT 1",
                    (project_id,),
                ).fetchone()
                if decided:
                    state = str(decided["to_state"])
            con.execute(
                """INSERT INTO project_records
                   (project_id,schema_name,title,state,source_root_ref,fingerprint,ir_json,version,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project_id) DO UPDATE SET
                   schema_name=excluded.schema_name,title=excluded.title,state=excluded.state,
                   source_root_ref=excluded.source_root_ref,fingerprint=excluded.fingerprint,
                   ir_json=excluded.ir_json,version=excluded.version,updated_at=excluded.updated_at""",
                (project_id, SCHEMA, record["title"], state,
                 record["source"]["root_ref"], fingerprint, encoded, version, created, now),
            )
            current_paths = {str(artifact["relative_path"]) for artifact in record["artifacts"]}
            if current_paths:
                placeholders = ",".join("?" for _ in current_paths)
                con.execute(
                    f"UPDATE project_artifacts SET availability='stale',observed_at=? WHERE project_id=? AND relative_path NOT IN ({placeholders})",
                    (now, project_id, *sorted(current_paths)),
                )
            else:
                con.execute(
                    "UPDATE project_artifacts SET availability='stale',observed_at=? WHERE project_id=?",
                    (now, project_id),
                )
            for artifact in record["artifacts"]:
                con.execute(
                    """INSERT INTO project_artifacts
                       (artifact_id,project_id,relative_path,format_family,media_type,size_bytes,mtime_ns,sha256,hash_status,availability,role,observed_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(project_id,relative_path) DO UPDATE SET
                       artifact_id=excluded.artifact_id,format_family=excluded.format_family,
                       media_type=excluded.media_type,size_bytes=excluded.size_bytes,mtime_ns=excluded.mtime_ns,
                       sha256=excluded.sha256,hash_status=excluded.hash_status,availability=excluded.availability,
                       role=excluded.role,observed_at=excluded.observed_at""",
                    (artifact["artifact_id"], project_id, artifact["relative_path"],
                     artifact["format_family"], artifact["media_type"], artifact["size_bytes"],
                     artifact["mtime_ns"], artifact["sha256"], artifact["hash_status"],
                     artifact["availability"], artifact["role"], now),
                )
        return fingerprint

    def record_episode(
        self,
        *,
        project_id: str,
        objective: str,
        phase: str,
        action: Mapping[str, Any],
        observation: Mapping[str, Any],
        outcome: Mapping[str, Any],
        validation: Mapping[str, Any],
        status: str,
        provider: str = "local",
        model: str = "",
        cost: Mapping[str, Any] | None = None,
        parent_episode_id: str | None = None,
        episode_id: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        source_snapshot_hash: str = "",
        code_commit: str = "",
        tool_versions: Mapping[str, Any] | None = None,
    ) -> str:
        if status not in EPISODE_STATES:
            raise ProjectIRError(f"episode_bad_status: {status}")
        episode_id = episode_id or "episode_" + uuid.uuid4().hex
        explicit_started_at = started_at is not None
        explicit_finished_at = finished_at is not None
        start = started_at or now_iso()
        source_snapshot_hash = _text(source_snapshot_hash, 128)
        code_commit = _text(code_commit, 128)
        if tool_versions is None:
            tool_versions = {}
        if not isinstance(tool_versions, Mapping):
            raise ProjectIRError("episode_tool_versions_not_mapping")
        if bool(source_snapshot_hash) != bool(code_commit) or bool(source_snapshot_hash) != bool(tool_versions):
            raise ProjectIRError("episode_versioned_provenance_incomplete")
        encoded_tools = _json(tool_versions)
        payload = (
            project_id, _text(objective, 1200), _text(phase, 120),
            _json(action), _json(observation), _json(outcome), _json(validation),
            status, _text(provider, 160) or "local", _text(model, 160), _json(cost),
            _text(parent_episode_id, 120), source_snapshot_hash, code_commit, encoded_tools,
        )
        with self.connect() as con:
            self.ensure_schema(con)
            if not con.execute("SELECT 1 FROM project_records WHERE project_id=?", (project_id,)).fetchone():
                raise ProjectIRError(f"episode_unknown_project: {project_id}")
            existing = con.execute(
                """SELECT project_id,objective,phase,action_json,observation_json,
                   outcome_json,validation_json,status,provider,model,cost_json,parent_episode_id,
                   source_snapshot_hash,code_commit,tool_versions_json,started_at,finished_at
                   FROM project_episodes WHERE episode_id=?""",
                (episode_id,),
            ).fetchone()
            if existing:
                # A caller that supplies a stable episode id but no timestamps
                # is replaying the same logical write.  The generated start
                # time is storage metadata, not episode identity; requiring it
                # to match made otherwise identical retries conflict.
                existing_core = tuple(existing[:-2])
                times_match = (
                    (not explicit_started_at or existing[-2] == start)
                    and (not explicit_finished_at or existing[-1] == finished_at)
                )
                if existing_core == payload and times_match:
                    return episode_id
                raise ProjectIRError(f"episode_id_conflict: {episode_id}")
            con.execute(
                """INSERT INTO project_episodes
                (episode_id,project_id,objective,phase,action_json,observation_json,outcome_json,validation_json,status,provider,model,cost_json,parent_episode_id,source_snapshot_hash,code_commit,tool_versions_json,started_at,finished_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (episode_id, *payload, start, finished_at),
            )
        return episode_id

    def append_run_event(
        self, *, project_id: str, event_type: str, state: str,
        payload: Mapping[str, Any], source_snapshot_hash: str, code_commit: str,
        tool_versions: Mapping[str, Any], episode_id: str | None = None,
        parent_event_id: str | None = None, run_id: str | None = None,
        event_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        """Append one director event with mandatory execution provenance.

        Events are immutable.  Repeating the same ``event_id`` is idempotent
        only when every stored field matches; a different payload is a hard
        conflict.  This is the durable control surface for MAK Learn v2, not
        a second source of truth and not an automatic policy promoter.
        """
        if state not in RUN_EVENT_STATES:
            raise ProjectIRError(f"run_event_bad_state: {state}")
        event_type = _text(event_type, 160)
        source_snapshot_hash = _text(source_snapshot_hash, 128)
        code_commit = _text(code_commit, 128)
        if not event_type:
            raise ProjectIRError("run_event_missing_type")
        if not source_snapshot_hash:
            raise ProjectIRError("run_event_missing_source_snapshot_hash")
        if not code_commit:
            raise ProjectIRError("run_event_missing_code_commit")
        if not isinstance(tool_versions, Mapping):
            raise ProjectIRError("run_event_tool_versions_not_mapping")
        event_id = event_id or "event_" + uuid.uuid4().hex
        run_id = _text(run_id, 160) or "run_" + event_id.removeprefix("event_")
        created_at = created_at or now_iso()
        encoded_payload = _json(payload)
        encoded_tools = _json(tool_versions)
        values = (
            run_id, project_id, episode_id, parent_event_id, event_type, state,
            encoded_payload, source_snapshot_hash, code_commit, encoded_tools,
        )
        with self.connect() as con:
            self.ensure_schema(con)
            if not con.execute("SELECT 1 FROM project_records WHERE project_id=?", (project_id,)).fetchone():
                raise ProjectIRError(f"run_event_unknown_project: {project_id}")
            if episode_id and not con.execute("SELECT 1 FROM project_episodes WHERE episode_id=?", (episode_id,)).fetchone():
                raise ProjectIRError(f"run_event_unknown_episode: {episode_id}")
            if parent_event_id and not con.execute("SELECT 1 FROM mak_run_events WHERE event_id=?", (parent_event_id,)).fetchone():
                raise ProjectIRError(f"run_event_unknown_parent: {parent_event_id}")
            if parent_event_id:
                parent = con.execute(
                    "SELECT run_id FROM mak_run_events WHERE event_id=?", (parent_event_id,)
                ).fetchone()
                if parent and str(parent["run_id"]) != run_id:
                    raise ProjectIRError("run_event_parent_run_mismatch")
            existing = con.execute(
                """SELECT run_id,project_id,episode_id,parent_event_id,event_type,state,
                   payload_json,source_snapshot_hash,code_commit,tool_versions_json
                   FROM mak_run_events WHERE event_id=?""", (event_id,),
            ).fetchone()
            if existing:
                if tuple(existing) == values:
                    return event_id
                raise ProjectIRError(f"run_event_id_conflict: {event_id}")
            con.execute(
                """INSERT INTO mak_run_events
                   (event_id,run_id,project_id,episode_id,parent_event_id,event_type,state,
                    payload_json,source_snapshot_hash,code_commit,tool_versions_json,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id, *values, created_at),
            )
        return event_id

    def append_operational_event(self, event: Mapping[str, Any]) -> str:
        """Append one semantic proposition event to the existing ledger.

        This is intentionally separate from ``mak_run_events``: operational
        propositions do not require a Project IR row or an execution episode.
        The caller computes the semantic ``event_id``.  ``recorded_at`` is
        storage metadata only, so retrying an event with a different clock
        value remains idempotent and preserves the first stored timestamp.
        """
        if not isinstance(event, Mapping):
            raise ProjectIRError("operational_event_not_mapping")
        event_id = _text(event.get("event_id"), 240)
        archive_id = _text(event.get("archive_id"), 240)
        proposition_id = _text(event.get("proposition_id"), 240)
        event_type = _text(event.get("event_type"), 80)
        if not event_id or not archive_id or not proposition_id or not event_type:
            raise ProjectIRError("operational_event_identity_incomplete")
        stored = dict(event)
        recorded_at = _text(stored.get("recorded_at"), 80) or now_iso()
        stored["recorded_at"] = recorded_at
        encoded = stable_json(stored)

        def semantic(value: Mapping[str, Any]) -> str:
            comparable = dict(value)
            comparable.pop("event_id", None)
            comparable.pop("recorded_at", None)
            return stable_json(comparable)

        with self.connect() as con:
            self.ensure_schema(con)
            existing = con.execute(
                "SELECT event_json FROM mak_operational_events WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if existing:
                try:
                    previous = json.loads(existing["event_json"])
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ProjectIRError("operational_event_stored_json_invalid") from exc
                if isinstance(previous, Mapping) and semantic(previous) == semantic(stored):
                    return event_id
                raise ProjectIRError(f"operational_event_id_conflict: {event_id}")
            con.execute(
                """INSERT INTO mak_operational_events
                   (event_id,archive_id,proposition_id,event_type,event_json,recorded_at)
                   VALUES (?,?,?,?,?,?)""",
                (event_id, archive_id, proposition_id, event_type, encoded, recorded_at),
            )
        return event_id

    def operational_events(self, archive_id: str | None = None) -> list[dict[str, Any]]:
        """Read operational events without creating schema or mutating data."""
        if not self.database.is_file():
            return []
        uri = "file:" + str(self.database.resolve()) + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            con.row_factory = sqlite3.Row
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mak_operational_events'"
            ).fetchone()
            if not exists:
                return []
            if archive_id is None:
                rows = con.execute(
                    "SELECT event_json FROM mak_operational_events "
                    "ORDER BY archive_id, proposition_id, event_id"
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT event_json FROM mak_operational_events WHERE archive_id=? "
                    "ORDER BY proposition_id, event_id",
                    (archive_id,),
                ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                value = json.loads(row["event_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ProjectIRError("operational_event_json_invalid") from exc
            if not isinstance(value, dict):
                raise ProjectIRError("operational_event_json_not_object")
            result.append(value)
        return result

    def run_events(self, run_id: str) -> list[dict[str, Any]]:
        """Read one persisted director checkpoint chain without changing data."""
        run_id = _text(run_id, 160)
        if not run_id:
            raise ProjectIRError("run_event_missing_run_id")
        if not self.database.is_file():
            return []
        uri = "file:" + str(self.database.resolve()) + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM mak_run_events WHERE run_id=? ORDER BY created_at, rowid",
                (run_id,),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            for field in ("payload_json", "tool_versions_json"):
                try:
                    item[field.removesuffix("_json")] = json.loads(item[field])
                except (TypeError, json.JSONDecodeError):
                    item[field.removesuffix("_json")] = {}
            output.append(item)
        return output

    def record_learning_evaluation(
        self, *, target_kind: str, target_id: str, dataset_fingerprint: str,
        split_kind: str, status: str, metrics: Mapping[str, Any],
        evidence: Iterable[Mapping[str, Any]] = (),
        baseline_policy_id: str = "", candidate_policy_id: str = "",
        evaluation_id: str | None = None, created_at: str | None = None,
    ) -> str:
        """Append an evaluation report without changing any active policy.

        A passed report is evidence for a later, explicit promotion decision;
        it is never promotion itself.  ``dataset_fingerprint`` makes the
        replay/holdout population addressable and prevents an untracked split
        from becoming a learning claim.
        """
        if split_kind not in EVALUATION_SPLITS:
            raise ProjectIRError(f"evaluation_bad_split: {split_kind}")
        if status not in EVALUATION_STATUSES:
            raise ProjectIRError(f"evaluation_bad_status: {status}")
        target_kind = _text(target_kind, 160)
        target_id = _text(target_id, 240)
        dataset_fingerprint = _text(dataset_fingerprint, 128)
        if not target_kind or not target_id:
            raise ProjectIRError("evaluation_missing_target")
        if not dataset_fingerprint:
            raise ProjectIRError("evaluation_missing_dataset_fingerprint")
        if not isinstance(metrics, Mapping):
            raise ProjectIRError("evaluation_metrics_not_mapping")
        evaluation_id = evaluation_id or "evaluation_" + uuid.uuid4().hex
        created_at = created_at or now_iso()
        values = (
            target_kind, target_id, dataset_fingerprint, split_kind, status,
            _json(metrics), _json(list(evidence)), _text(baseline_policy_id, 240),
            _text(candidate_policy_id, 240),
        )
        with self.connect() as con:
            self.ensure_schema(con)
            existing = con.execute(
                """SELECT target_kind,target_id,dataset_fingerprint,split_kind,status,
                   metrics_json,evidence_json,baseline_policy_id,candidate_policy_id
                   FROM learning_evaluations WHERE evaluation_id=?""", (evaluation_id,),
            ).fetchone()
            if existing:
                if tuple(existing) == values:
                    return evaluation_id
                raise ProjectIRError(f"evaluation_id_conflict: {evaluation_id}")
            con.execute(
                """INSERT INTO learning_evaluations
                   (evaluation_id,target_kind,target_id,dataset_fingerprint,split_kind,
                    status,metrics_json,evidence_json,baseline_policy_id,candidate_policy_id,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (evaluation_id, *values, created_at),
            )
        return evaluation_id

    def transition_project(
        self, project_id: str, to_state: str, *, reason: str,
        evidence: Iterable[Mapping[str, Any]] = (), actor: str = "system",
    ) -> None:
        if to_state not in PROJECT_STATES:
            raise ProjectIRError(f"project_bad_state: {to_state}")
        evidence_rows = [dict(item) for item in evidence]
        with self.connect() as con:
            self.ensure_schema(con)
            row = con.execute("SELECT state, ir_json FROM project_records WHERE project_id=?", (project_id,)).fetchone()
            if not row:
                raise ProjectIRError(f"unknown_project: {project_id}")
            from_state = str(row["state"])
            if to_state == from_state:
                return
            if to_state not in ALLOWED_TRANSITIONS.get(from_state, set()):
                raise ProjectIRError(f"transition_not_allowed: {from_state}->{to_state}")
            record = json.loads(row["ir_json"])
            record["state"] = to_state
            record["evidence"] = list(record.get("evidence", [])) + evidence_rows
            record["provenance"]["updated_at"] = now_iso()
            errors = validate_project_ir(record)
            if errors:
                raise ProjectIRError("invalid_transition_record: " + ",".join(errors))
            encoded = stable_json(record)
            con.execute(
                "UPDATE project_records SET state=?, fingerprint=?, ir_json=?, version=version+1, updated_at=? WHERE project_id=?",
                (to_state, hashlib.sha256(encoded.encode()).hexdigest(), encoded, now_iso(), project_id),
            )
            con.execute(
                "INSERT INTO project_transitions(project_id,from_state,to_state,reason,evidence_json,actor,created_at) VALUES (?,?,?,?,?,?,?)",
                (project_id, from_state, to_state, _text(reason, 1200), _json(evidence_rows), _text(actor, 160), now_iso()),
            )

    def upsert_rule(
        self, *, trigger: Mapping[str, Any], action: Mapping[str, Any],
        evidence: Iterable[Mapping[str, Any]] = (), scope: Mapping[str, Any] | None = None,
        expires_at: str | None = None, evaluation_id: str | None = None,
        rule_id: str | None = None,
    ) -> str:
        """Register a candidate semantic rule without promoting it."""
        scope = dict(scope or {})
        fingerprint = hashlib.sha256(
            stable_json({"trigger": dict(trigger), "action": dict(action), "scope": scope}).encode("utf-8")
        ).hexdigest()
        rule_id = rule_id or "rule_" + fingerprint[:24]
        now = now_iso()
        with self.connect() as con:
            self.ensure_schema(con)
            con.execute(
                """INSERT INTO semantic_rules
                   (rule_id,fingerprint,trigger_json,action_json,scope_json,evidence_json,status,
                    created_at,updated_at,expires_at,evaluation_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(fingerprint) DO UPDATE SET
                   trigger_json=excluded.trigger_json, action_json=excluded.action_json,
                   scope_json=excluded.scope_json, evidence_json=excluded.evidence_json,
                   expires_at=excluded.expires_at, evaluation_id=excluded.evaluation_id,
                   updated_at=excluded.updated_at""",
                (rule_id, fingerprint, _json(trigger), _json(action), _json(scope),
                 _json(list(evidence)), "candidate", now, now, _text(expires_at, 80),
                 _text(evaluation_id, 240)),
            )
            actual = con.execute("SELECT rule_id FROM semantic_rules WHERE fingerprint=?", (fingerprint,)).fetchone()
            if actual:
                rule_id = str(actual["rule_id"])
        return rule_id

    def observe_rule(
        self, *, rule_id: str, episode_id: str, verdict: str,
        evidence: Iterable[Mapping[str, Any]] = (), observation_id: str | None = None,
    ) -> str:
        """Append one support/contradiction observation to a rule candidate."""
        if verdict not in RULE_VERDICTS:
            raise ProjectIRError(f"rule_bad_verdict: {verdict}")
        observation_id = observation_id or "observation_" + uuid.uuid4().hex
        with self.connect() as con:
            self.ensure_schema(con)
            rule = con.execute("SELECT rule_id FROM semantic_rules WHERE rule_id=?", (rule_id,)).fetchone()
            episode = con.execute("SELECT status FROM project_episodes WHERE episode_id=?", (episode_id,)).fetchone()
            if not rule:
                raise ProjectIRError(f"unknown_rule: {rule_id}")
            if not episode:
                raise ProjectIRError(f"unknown_episode: {episode_id}")
            con.execute(
                """INSERT INTO rule_observations(observation_id,rule_id,episode_id,verdict,evidence_json,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (observation_id, rule_id, episode_id, verdict, _json(list(evidence)), now_iso()),
            )
            if verdict == "support":
                column = "support_count"
            elif verdict == "contradict":
                column = "contradiction_count"
            else:
                return observation_id
            con.execute(f"UPDATE semantic_rules SET {column}={column}+1,updated_at=? WHERE rule_id=?", (now_iso(), rule_id))
        return observation_id

    def promote_rule(
        self, rule_id: str, *, min_support: int = 2,
        evaluation_id: str | None = None,
    ) -> None:
        """Promote only a rule supported by independently verified episodes.

        Promotion is intentionally strict.  A failed/unknown episode may be
        recorded, but it cannot teach the active router.  Contradictions
        always block promotion until an explicit future review changes state.
        A passed independent holdout evaluation for this exact rule is also
        mandatory; a generic replay-suite pass is not sufficient.
        """
        if min_support < 1:
            raise ProjectIRError("min_support_must_be_positive")
        with self.connect() as con:
            self.ensure_schema(con)
            rule = con.execute("SELECT * FROM semantic_rules WHERE rule_id=?", (rule_id,)).fetchone()
            if not rule:
                raise ProjectIRError(f"unknown_rule: {rule_id}")
            if rule["status"] != "candidate":
                raise ProjectIRError(f"rule_not_candidate: {rule['status']}")
            expires_at = str(rule["expires_at"] or "")
            if expires_at and expires_at <= now_iso():
                con.execute(
                    "UPDATE semantic_rules SET status='stale',updated_at=? WHERE rule_id=?",
                    (now_iso(), rule_id),
                )
                con.commit()
                raise ProjectIRError("rule_expired")
            evaluation_id = _text(evaluation_id, 240)
            if not evaluation_id:
                raise ProjectIRError("rule_promotion_evaluation_required")
            evaluation = con.execute(
                """SELECT target_kind,target_id,split_kind,status
                   FROM learning_evaluations WHERE evaluation_id=?""", (evaluation_id,),
            ).fetchone()
            if not evaluation:
                raise ProjectIRError("rule_promotion_evaluation_missing")
            if evaluation["target_kind"] != "semantic_rule" or evaluation["target_id"] != rule_id:
                raise ProjectIRError("rule_promotion_evaluation_target_mismatch")
            if evaluation["split_kind"] != "holdout" or evaluation["status"] != "passed":
                raise ProjectIRError("rule_promotion_evaluation_not_passed_holdout")
            if int(rule["support_count"]) < min_support:
                raise ProjectIRError("rule_insufficient_support")
            if int(rule["contradiction_count"]) > 0:
                raise ProjectIRError("rule_has_contradictions")
            supports = con.execute(
                """SELECT e.status, e.validation_json
                   FROM rule_observations o JOIN project_episodes e ON e.episode_id=o.episode_id
                   WHERE o.rule_id=? AND o.verdict='support'""", (rule_id,),
            ).fetchall()
            if len(supports) < min_support:
                raise ProjectIRError("rule_support_observations_missing")
            for episode in supports:
                if episode["status"] not in {"succeeded", "verified"}:
                    raise ProjectIRError("rule_support_episode_not_verified")
                try:
                    validation = json.loads(episode["validation_json"])
                except json.JSONDecodeError as exc:
                    raise ProjectIRError("rule_support_validation_invalid") from exc
                if str(validation.get("status", "")).casefold() not in {"ok", "passed", "verified"}:
                    raise ProjectIRError("rule_support_validation_not_passed")
            con.execute(
                "UPDATE semantic_rules SET status='promoted',promoted_at=?,evaluation_id=?,updated_at=? WHERE rule_id=?",
                (now_iso(), evaluation_id, now_iso(), rule_id),
            )

    def retract_rule(self, rule_id: str, *, reason: str) -> None:
        """Explicitly retract a candidate or promoted lesson with a reason."""
        reason = _text(reason, 1200)
        if not reason:
            raise ProjectIRError("rule_retraction_reason_required")
        with self.connect() as con:
            self.ensure_schema(con)
            rule = con.execute("SELECT status FROM semantic_rules WHERE rule_id=?", (rule_id,)).fetchone()
            if not rule:
                raise ProjectIRError(f"unknown_rule: {rule_id}")
            con.execute(
                """UPDATE semantic_rules
                   SET status='retracted',retracted_at=?,retraction_reason=?,updated_at=?
                   WHERE rule_id=?""",
                (now_iso(), reason, now_iso(), rule_id),
            )

    def rules(self, *, status: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as con:
            self.ensure_schema(con)
            if status is None:
                rows = con.execute("SELECT * FROM semantic_rules ORDER BY updated_at, rule_id").fetchall()
            else:
                rows = con.execute("SELECT * FROM semantic_rules WHERE status=? ORDER BY updated_at, rule_id", (status,)).fetchall()
            return [dict(row) for row in rows]

    def summary(self, project_id: str | None = None) -> dict[str, Any]:
        with self.connect() as con:
            self.ensure_schema(con)
            where = " WHERE project_id=?" if project_id else ""
            args = (project_id,) if project_id else ()
            projects = con.execute("SELECT state, COUNT(*) AS count FROM project_records" + where + " GROUP BY state", args).fetchall()
            episodes = con.execute("SELECT status, COUNT(*) AS count FROM project_episodes" + where + " GROUP BY status", args).fetchall()
            rules = con.execute("SELECT status, COUNT(*) AS count FROM semantic_rules GROUP BY status").fetchall()
            return {
                "schema": LEARNING_SCHEMA,
                "projects": {row["state"]: row["count"] for row in projects},
                "episodes": {row["status"]: row["count"] for row in episodes},
                "rules": {row["status"]: row["count"] for row in rules},
                "project_id": project_id or "",
            }


def inspect_learning_target(database: str | Path) -> dict[str, Any]:
    """Inspect a potential target without creating tables or changing bytes."""
    path = Path(database).expanduser()
    expected = {
        "project_records", "project_artifacts", "project_episodes",
        "project_transitions", "semantic_rules", "rule_observations",
        "project_contracts", "mak_run_events", "learning_evaluations",
        "mak_operational_events",
        "archive_memory_v2_archives", "archive_memory_v2_snapshots",
        "archive_memory_v2_artifacts", "archive_memory_v2_artifact_states",
        "archive_memory_v2_observations", "archive_memory_v2_transformation_events",
        "archive_memory_archives", "archive_memory_snapshots",
        "archive_memory_artifacts", "archive_memory_artifact_states",
        "archive_memory_observations", "archive_memory_transformation_events",
    }
    if not path.is_file():
        return {
            "schema": LEARNING_SCHEMA,
            "database": path.name,
            "exists": False,
            "read_only": True,
            "compatible": True,
            "present": [],
            "missing": sorted(expected),
        }
    try:
        con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
        present = {
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ) if row[0] in expected
        }
        con.close()
        present_names = sorted(present)
        if not present:
            materialization = "not_applied"
        elif present == expected:
            materialization = "already_applied"
        else:
            materialization = "partial"
        return {
            "schema": LEARNING_SCHEMA,
            "database": path.name,
            "exists": True,
            "read_only": True,
            "compatible": True,
            "present": present_names,
            "missing": sorted(expected - present),
            "materialization": materialization,
        }
    except (OSError, sqlite3.Error) as exc:
        return {
            "schema": LEARNING_SCHEMA,
            "database": path.name,
            "exists": True,
            "read_only": True,
            "compatible": False,
            "error": type(exc).__name__,
        }


def migration_dry_run(
    database: str | Path, *, application_dir: str | Path | None = None,
    max_packages: int = 200,
) -> dict[str, Any]:
    """Build a machine-readable migration impact report without applying it."""
    target = inspect_learning_target(database)
    report: dict[str, Any] = {
        "schema": "mak-learning-migration-dry-run-v1",
        "target": target,
        "writes_performed": False,
        "migration": "not_needed" if target.get("materialization") == "already_applied" else "not_applied",
        "collisions": [],
        "compatible": bool(target.get("compatible")),
        "action": target.get("materialization", "not_applied"),
        "intake": {"available": False, "packages": 0, "projects": [], "review_required": 0, "unknowns": 0},
    }
    if application_dir is None:
        return report
    root = Path(application_dir).expanduser()
    if not root.is_dir():
        report["intake"] = {"available": False, "reason": "directory_missing", "directory": root.name}
        return report
    packages = sorted(root.glob("*.json"))
    if len(packages) > max_packages:
        report["intake"] = {"available": False, "reason": "max_packages_exceeded", "max_packages": max_packages}
        return report
    project_ids: list[str] = []
    unknowns = 0
    review_required = 0
    for path in packages:
        try:
            record = load_application_package(path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        project_ids.append(str(record["project_id"]))
        unknowns += len(record.get("unknowns", []))
        review_required += record.get("state") == "review_required"
    report["intake"] = {
        "available": True,
        "directory": root.name,
        "packages": len(project_ids),
        "projects": sorted(set(project_ids)),
        "review_required": review_required,
        "unknowns": unknowns,
    }
    return report


def _cli(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="MAK Project IR and learning ledger")
    parser.add_argument("--db", required=True, help="explicit SQLite path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--source-root", required=True)
    ingest.add_argument("--project-id", required=True)
    ingest.add_argument("--title", default="")
    ingest.add_argument("--state", choices=PROJECT_STATES, default="candidate")
    ingest.add_argument("--domain", action="append", default=[])
    application = sub.add_parser("import-application")
    application.add_argument("--package", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--project-id")
    sub.add_parser("inspect")
    migration = sub.add_parser("migration-report")
    migration.add_argument("--intake-dir")
    args = parser.parse_args(list(argv))
    store = LearningStore(args.db)
    if args.command == "init":
        store.ensure_schema()
        print(json.dumps({"schema": LEARNING_SCHEMA, "database": str(store.database), "status": "ready"}, ensure_ascii=False))
        return 0
    if args.command == "ingest":
        artifacts = inventory_source(args.source_root)
        record = build_project_ir(
            project_id=args.project_id, title=args.title or args.project_id,
            source_root=args.source_root, artifacts=artifacts, domains=args.domain,
            state=args.state, source_kind="folder",
        )
        fingerprint = store.save_project(record)
        print(json.dumps({"project_id": record["project_id"], "artifacts": len(artifacts), "fingerprint": fingerprint}, ensure_ascii=False))
        return 0
    if args.command == "import-application":
        record = load_application_package(args.package)
        fingerprint = store.save_project(record)
        print(json.dumps({"project_id": record["project_id"], "state": record["state"], "unknowns": len(record["unknowns"]), "fingerprint": fingerprint}, ensure_ascii=False))
        return 0
    if args.command == "inspect":
        print(json.dumps(inspect_learning_target(store.database), ensure_ascii=False))
        return 0
    if args.command == "migration-report":
        print(json.dumps(migration_dry_run(store.database, application_dir=args.intake_dir), ensure_ascii=False))
        return 0
    print(json.dumps(store.summary(args.project_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
