#!/usr/bin/env python3
"""Convert an indexed SSD or project folder into a traceable application package.

The source is never copied, moved, renamed, or rewritten.  The tool imports
the existing portable-SSD index (or scans one bounded project directory),
keeps every source reference and creates a derived SQLite workspace with
project candidates, relations, MAK consumers, funding targets, evidence gaps,
and application drafts.  JSON and HTML are machine/readable deliverables;
Markdown is deliberately not the primary output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "mak-application-intake-v1"
DEFAULT_MAK_DB = Path(__file__).resolve().parents[1] / "data" / "mak_knowledge.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def slug(value: str, fallback: str = "project") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")
    return text[:80] or fallback


def source_fingerprint(index_path: Path, source_root: str, summary: dict[str, Any]) -> str:
    stat = index_path.stat()
    payload = {
        "index": str(index_path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "source_root": source_root,
        "summary": summary,
    }
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def create_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS intake_runs (
            run_id TEXT PRIMARY KEY,
            schema_name TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            source_root TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            project_title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            artifact_count INTEGER NOT NULL DEFAULT 0,
            project_count INTEGER NOT NULL DEFAULT 0,
            relation_count INTEGER NOT NULL DEFAULT 0,
            mak_link_count INTEGER NOT NULL DEFAULT 0,
            application_count INTEGER NOT NULL DEFAULT 0,
            next_action TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS intake_projects (
            run_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            dimensionality TEXT NOT NULL,
            strategy TEXT NOT NULL,
            asset_count INTEGER NOT NULL,
            bytes INTEGER NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL,
            source_evidence TEXT NOT NULL,
            PRIMARY KEY(run_id, project_id)
        );
        CREATE TABLE IF NOT EXISTS intake_families (
            run_id TEXT NOT NULL,
            family_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            family_key TEXT NOT NULL,
            member_count INTEGER NOT NULL,
            bytes INTEGER NOT NULL,
            strategy TEXT NOT NULL,
            representative_asset_id TEXT,
            PRIMARY KEY(run_id, family_id)
        );
        CREATE TABLE IF NOT EXISTS intake_assets (
            run_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            project_id TEXT,
            family_id TEXT,
            relative_path TEXT NOT NULL,
            extension TEXT NOT NULL,
            media_kind TEXT NOT NULL,
            bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            full_sha256 TEXT,
            availability TEXT NOT NULL,
            source_evidence TEXT NOT NULL,
            PRIMARY KEY(run_id, asset_id)
        );
        CREATE TABLE IF NOT EXISTS project_candidates (
            run_id TEXT NOT NULL,
            rank INTEGER NOT NULL,
            project_id TEXT NOT NULL,
            score REAL NOT NULL,
            reason TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY(run_id, rank),
            UNIQUE(run_id, project_id)
        );
        CREATE TABLE IF NOT EXISTS intake_relations (
            relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            UNIQUE(run_id, source_type, source_id, relation, target_type, target_id)
        );
        CREATE TABLE IF NOT EXISTS mak_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            mak_path TEXT NOT NULL,
            artifact_id INTEGER,
            entity_kind TEXT,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            UNIQUE(run_id, project_id, relation, mak_path)
        );
        CREATE TABLE IF NOT EXISTS fund_targets (
            run_id TEXT NOT NULL,
            fund_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            requirements_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            PRIMARY KEY(run_id, fund_id)
        );
        CREATE TABLE IF NOT EXISTS application_packages (
            run_id TEXT NOT NULL,
            application_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            fund_id TEXT NOT NULL,
            status TEXT NOT NULL,
            readiness REAL NOT NULL,
            title TEXT NOT NULL,
            sections_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            gaps_json TEXT NOT NULL,
            outputs_json TEXT NOT NULL,
            PRIMARY KEY(run_id, application_id)
        );
        CREATE TABLE IF NOT EXISTS workflow_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_intake_assets_project
            ON intake_assets(run_id, project_id);
        CREATE INDEX IF NOT EXISTS idx_intake_links_project
            ON mak_links(run_id, project_id);
        """
    )


def read_source_summary(index_path: Path) -> tuple[str, dict[str, Any]]:
    summary_path = index_path.parent / "summary.json"
    if summary_path.is_file():
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return str(data.get("root") or ""), data
    return "", {}


def _media_kind(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".mxf"}:
        return "video"
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".exr"}:
        return "image"
    if suffix in {".blend", ".blend1", ".psd", ".psb", ".ai", ".aep", ".c4d", ".hip", ".kra", ".obj", ".fbx", ".glb", ".gltf"}:
        return "structural"
    if suffix in {".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".json", ".csv"}:
        return "document"
    return "other"


def _sha256_file(path: Path, limit: int = 16 * 1024 * 1024) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def scan_project_folder(source_root: Path, index_path: Path) -> tuple[Path, str, dict[str, Any]]:
    """Create a metadata-only temporary index for one bounded project folder."""
    source_root = source_root.resolve()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    project_id = "project_" + hashlib.sha256(str(source_root).encode("utf-8")).hexdigest()[:20]
    project_path = source_root.name or "project"
    rows: list[tuple] = []
    family_groups: dict[str, list[tuple]] = {}
    ignored = {".git", ".venv", "__pycache__", "node_modules", ".cache", "cache", "tmp"}
    for current, dirs, files in os.walk(source_root):
        dirs[:] = [name for name in dirs if name not in ignored and not name.startswith(".")]
        for name in files:
            path = Path(current) / name
            try:
                stat = path.stat()
            except OSError:
                continue
            relative = path.relative_to(source_root).as_posix()
            asset_id = "asset_" + hashlib.sha256(
                f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}".encode("utf-8")
            ).hexdigest()[:32]
            family_key = Path(relative).parent.as_posix() or "."
            rows.append((asset_id, relative, path.suffix.casefold(), _media_kind(path),
                         int(stat.st_size), int(stat.st_mtime_ns), _sha256_file(path)))
            family_groups.setdefault(family_key, []).append(rows[-1])
    total_bytes = sum(row[4] for row in rows)
    con = sqlite3.connect(index_path)
    con.executescript(
        """
        CREATE TABLE projects(project_id TEXT PRIMARY KEY, project_path TEXT, dimensionality TEXT,
            strategy TEXT, asset_count INTEGER, bytes INTEGER, confidence REAL, diagnostic_json TEXT);
        CREATE TABLE assets(asset_id TEXT PRIMARY KEY, source_key TEXT, relative_path TEXT, extension TEXT,
            media_kind TEXT, bytes INTEGER, mtime_ns INTEGER, full_sha256 TEXT);
        CREATE TABLE families(family_id TEXT PRIMARY KEY, project_id TEXT, family_key TEXT, member_count INTEGER,
            bytes INTEGER, strategy TEXT, representative_asset_id TEXT);
        CREATE TABLE project_members(asset_id TEXT PRIMARY KEY, project_id TEXT, family_id TEXT,
            member_role TEXT, is_representative INTEGER);
        CREATE TABLE relations(relation_id TEXT PRIMARY KEY, left_id TEXT, relation TEXT, right_id TEXT,
            confidence REAL, evidence_json TEXT);
        """
    )
    dimensionality = "mixto" if any(row[3] == "video" for row in rows) and any(row[3] == "structural" for row in rows) else (
        "motion" if any(row[3] == "video" for row in rows) else ("3d" if any(row[3] == "structural" for row in rows) else "2d"))
    con.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)",
                (project_id, project_path, dimensionality, "bounded_folder_scan", len(rows), total_bytes, 0.8,
                 stable_json({"source": str(source_root), "content_read": "hash_only_for_small_files"})))
    for row in rows:
        con.execute("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)",
                    (row[0], str(source_root), row[1], row[2], row[3], row[4], row[5], row[6]))
    for index, (family_key, members) in enumerate(sorted(family_groups.items()), 1):
        family_id = f"family_{index:06d}"
        con.execute("INSERT INTO families VALUES (?,?,?,?,?,?,?)",
                    (family_id, project_id, family_key, len(members), sum(row[4] for row in members),
                     "folder_group", members[0][0]))
        for member_index, row in enumerate(members):
            con.execute("INSERT INTO project_members VALUES (?,?,?,?,?)",
                        (row[0], project_id, family_id, "representative" if member_index == 0 else "member",
                         1 if member_index == 0 else 0))
    con.commit()
    con.close()
    summary = {"schema": "mak-project-intake-folder-v1", "root": str(source_root),
               "inventory": {"assets": len(rows), "bytes": total_bytes,
                              "media_kinds": {kind: sum(row[3] == kind for row in rows) for kind in sorted({row[3] for row in rows})}}}
    (index_path.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index_path, str(source_root), summary


def is_system_project(path: str) -> bool:
    value = path.replace("\\", "/").strip("/").casefold()
    return value.startswith(("$recycle.bin", ".spotlight-v100", ".trashes", ".fseventsd"))


def project_score(row: dict[str, Any], media: dict[str, int], mak_links: int) -> tuple[float, str]:
    dimensionality = str(row["dimensionality"])
    project_path = str(row.get("project_path") or row.get("relative_path") or "")
    score = {"mixto": 70.0, "3d": 66.0, "motion": 63.0, "2d": 52.0}.get(dimensionality, 20.0)
    if media.get("video", 0):
        score += 8
    if media.get("image", 0):
        score += 4
    if media.get("structural", 0):
        score += 8
    if mak_links:
        score += min(12, mak_links * 2)
    if int(row["asset_count"]) >= 10:
        score += 4
    if is_system_project(project_path):
        score = -100.0
    reason = "; ".join(filter(None, [
        dimensionality,
        "video" if media.get("video", 0) else "",
        "editable_or_structural" if media.get("structural", 0) else "",
        "MAK_consumer_link" if mak_links else "",
    ]))
    return round(score, 3), reason or "metadata_only"


def load_index(con_out: sqlite3.Connection, index_path: Path, source_root: str,
               run_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = sqlite3.connect(index_path)
    source.row_factory = sqlite3.Row
    source_summary = {}
    summary_path = index_path.parent / "summary.json"
    if summary_path.is_file():
        source_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_projects = [dict(row) for row in source.execute(
        "SELECT project_id, project_path, dimensionality, strategy, asset_count, bytes, confidence, diagnostic_json FROM projects"
    )]
    source_members = source.execute(
        "SELECT pm.project_id, a.asset_id, a.relative_path, a.extension, a.media_kind, a.bytes, a.mtime_ns, a.full_sha256, pm.family_id "
        "FROM project_members pm JOIN assets a ON a.asset_id=pm.asset_id"
    )
    media_by_project: dict[str, dict[str, int]] = {}
    asset_rows: list[dict[str, Any]] = []
    for row in source_members:
        item = dict(row)
        media_by_project.setdefault(item["project_id"], {})[item["media_kind"]] = (
            media_by_project.setdefault(item["project_id"], {}).get(item["media_kind"], 0) + 1
        )
        available = "external_missing"
        if source_root and (Path(source_root) / item["relative_path"]).exists():
            available = "source_present"
        con_out.execute(
            "INSERT INTO intake_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, item["asset_id"], item["project_id"], item["family_id"],
             item["relative_path"], item["extension"], item["media_kind"],
             int(item["bytes"]), int(item["mtime_ns"]), item["full_sha256"],
             available, stable_json({"index": str(index_path), "source_root": source_root})),
        )
        asset_rows.append(item)

    for row in source_projects:
        con_out.execute(
            "INSERT INTO intake_projects VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, row["project_id"], row["project_path"], row["project_path"],
             row["dimensionality"], row["strategy"], int(row["asset_count"]),
             int(row["bytes"]), float(row["confidence"]),
             "candidate" if not is_system_project(row["project_path"]) else "system_evidence",
             stable_json({"diagnostic": row["diagnostic_json"], "index": str(index_path)})),
        )
    for row in source.execute(
        "SELECT family_id, project_id, family_key, member_count, bytes, strategy, representative_asset_id FROM families"
    ):
        con_out.execute(
            "INSERT INTO intake_families VALUES (?,?,?,?,?,?,?,?)",
            (run_id, row["family_id"], row["project_id"], row["family_key"],
             int(row["member_count"]), int(row["bytes"]), row["strategy"],
             row["representative_asset_id"]),
        )
    for row in source.execute("SELECT relation, left_id, right_id, confidence, evidence_json FROM relations"):
        con_out.execute(
            "INSERT OR IGNORE INTO intake_relations(run_id,source_type,source_id,relation,target_type,target_id,confidence,evidence_json) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, "ssd_object", row["left_id"], row["relation"], "ssd_object",
             row["right_id"], float(row["confidence"] or 0), row["evidence_json"]),
        )
    source.close()
    return source_summary, source_projects


def link_mak(con_out: sqlite3.Connection, mak_db: Path, run_id: str,
             project_id: str, project_path: str) -> int:
    if not mak_db.is_file():
        return 0
    tokens = [t for t in re.split(r"[^a-z0-9]+", project_path.casefold()) if len(t) >= 3]
    if not tokens:
        return 0
    conn = sqlite3.connect(mak_db)
    conn.row_factory = sqlite3.Row
    count = 0
    seen: set[str] = set()
    for token in tokens[:5]:
        pattern = "%" + token + "%"
        rows = conn.execute(
            "SELECT artifact_id, path, root_kind FROM artifacts WHERE lower(path) LIKE ? OR lower(name) LIKE ? LIMIT 80",
            (pattern, pattern),
        )
        for row in rows:
            path = str(row["path"])
            if path in seen:
                continue
            seen.add(path)
            con_out.execute(
                "INSERT OR IGNORE INTO mak_links(run_id,project_id,relation,mak_path,artifact_id,entity_kind,confidence,evidence_json) VALUES (?,?,?,?,?,?,?,?)",
                (run_id, project_id, "possible_consumer_or_origin", path, row["artifact_id"],
                 "artifact", 0.55, stable_json({"token": token, "root_kind": row["root_kind"], "method": "path_token"})),
            )
            count += 1
    conn.close()
    return count


def add_known_mak_links(con_out: sqlite3.Connection, run_id: str, project_id: str) -> int:
    root = DEFAULT_MAK_DB.parent.parent
    known = [
        root / "projects/plano/plano_stands.py",
        root / "projects/plano/referencia_plano_teatro.py",
        root / "tools/venue_geometria_scd.py",
        root / "data/venues/scd-plaza-egana.json",
        root / "schemas/venue.schema.json",
    ]
    count = 0
    for path in known:
        if not path.is_file():
            continue
        con_out.execute(
            "INSERT OR IGNORE INTO mak_links(run_id,project_id,relation,mak_path,artifact_id,entity_kind,confidence,evidence_json) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, project_id, "known_consumer_or_origin", str(path), None, "venue_or_plano", 0.85,
             stable_json({"method": "authorized_local_crosswalk", "exists": True})),
        )
        count += 1
    return count


def select_candidates(con: sqlite3.Connection, run_id: str, project_path: str | None,
                      limit: int,
                      reconstruction: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = [dict(row) for row in con.execute(
        "SELECT * FROM intake_projects WHERE run_id=?", (run_id,)
    )]
    reconstruction_decisions = {}
    if reconstruction is not None:
        reconstruction_decisions = reconstruction.get("decisions") or {}
        allowed_roles = {"project_unit", "subproject", "exported_product"}
        rows = [
            row for row in rows
            if (decision := reconstruction_decisions.get(row["relative_path"]))
            and decision.get("role") in allowed_roles
        ]
    scored: list[dict[str, Any]] = []
    for row in rows:
        media = {r[0]: r[1] for r in con.execute(
            "SELECT media_kind,count(*) FROM intake_assets WHERE run_id=? AND project_id=? GROUP BY media_kind",
            (run_id, row["project_id"]),
        )}
        mak_count = con.execute(
            "SELECT count(*) FROM mak_links WHERE run_id=? AND project_id=?",
            (run_id, row["project_id"]),
        ).fetchone()[0]
        score, reason = project_score(row, media, int(mak_count))
        if reconstruction is not None:
            decision = reconstruction_decisions[row["relative_path"]]
            reason += "; reconstruction:%s" % decision["role"]
        if project_path and row["relative_path"].casefold() == project_path.casefold():
            score += 100
            reason += "; explicit_project"
        scored.append({"project_id": row["project_id"], "title": row["title"],
                       "path": row["relative_path"], "score": round(score, 3),
                       "reason": reason, "media": media, "mak_links": int(mak_count),
                       "asset_count": row["asset_count"], "bytes": row["bytes"],
                       "dimensionality": row["dimensionality"]})
    scored.sort(key=lambda item: (-item["score"], -item["bytes"], item["path"].casefold()))
    selected = scored[:max(1, limit)]
    for rank, item in enumerate(selected, 1):
        con.execute(
            "INSERT OR REPLACE INTO project_candidates VALUES (?,?,?,?,?,?,?)",
            (run_id, rank, item["project_id"], item["score"], item["reason"],
             stable_json(item), "selected" if rank == 1 else "candidate"),
        )
    return selected


def fund_spec(name: str) -> tuple[str, dict[str, Any], str]:
    fund_id = slug(name, "fund")
    if fund_id == "fondart":
        requirements = {
            "official_call": "required_and_unverified",
            "project_description": "required",
            "artistic_or_technical_method": "required",
            "schedule_and_budget": "required",
            "team_and_roles": "required",
            "evidence_and_portfolio": "required",
        }
        evidence = {"source": "local_fondart_adapter", "live_call_checked": False}
    else:
        requirements = {
            "official_call": "required_and_unverified",
            "project_description": "required",
            "method_and_impact": "required",
            "schedule_and_budget": "required",
            "team_and_roles": "required",
            "evidence_and_portfolio": "required",
        }
        evidence = {"source": "user_declared_target", "live_call_checked": False}
    return fund_id, requirements, stable_json(evidence)


def build_application(con: sqlite3.Connection, run_id: str, project: dict[str, Any],
                      fund_name: str, output_dir: Path,
                      reconstruction: dict[str, Any] | None = None) -> dict[str, Any]:
    fund_id, requirements, evidence_text = fund_spec(fund_name)
    con.execute(
        "INSERT OR REPLACE INTO fund_targets VALUES (?,?,?,?,?,?)",
        (run_id, fund_id, fund_name, "candidate_unverified", stable_json(requirements), evidence_text),
    )
    project_id = project["project_id"]
    links = [dict(row) for row in con.execute(
        "SELECT relation,mak_path,artifact_id,entity_kind,confidence,evidence_json FROM mak_links WHERE run_id=? AND project_id=? ORDER BY mak_path",
        (run_id, project_id),
    )]
    assets = [dict(row) for row in con.execute(
        "SELECT relative_path,media_kind,bytes,availability,full_sha256 FROM intake_assets WHERE run_id=? AND project_id=? ORDER BY bytes DESC LIMIT 80",
        (run_id, project_id),
    )]
    gaps = [
        {"field": "official_call", "severity": "blocking", "reason": "No se verifico una convocatoria vigente."},
        {"field": "problem_and_context", "severity": "blocking", "reason": "Debe formularse desde el proyecto, no inferirse del nombre de la carpeta."},
        {"field": "method", "severity": "blocking", "reason": "La metadata prueba existencia, no el metodo artistico completo."},
        {"field": "budget", "severity": "blocking", "reason": "No existe presupuesto autorizado en el indice."},
        {"field": "schedule", "severity": "blocking", "reason": "No existe cronograma verificable en el indice."},
        {"field": "team", "severity": "review", "reason": "No se promovieron identidades por nombre de carpeta."},
    ]
    readiness = 35.0
    if project["asset_count"] > 0:
        readiness += 15
    if project["mak_links"]:
        readiness += 20
    if project["media"].get("structural", 0):
        readiness += 10
    if project["media"].get("image", 0) or project["media"].get("video", 0):
        readiness += 10
    readiness = min(90.0, readiness)
    application_id = slug(f"{project['path']}-{fund_id}", "application")
    sections = {
        "title": project["title"],
        "one_line": "Borrador pendiente de formulacion humana y verificacion de convocatoria.",
        "project_basis": {
            "source_path": project["path"],
            "dimensionality": project["dimensionality"],
            "asset_count": project["asset_count"],
            "bytes": project["bytes"],
        },
        "problem_and_context": "PENDIENTE: formular con evidencia del proyecto y del contexto.",
        "artistic_or_technical_method": "PENDIENTE: describir proceso, herramientas, iteraciones y resultado.",
        "outputs": "PENDIENTE: definir obra, instalacion, exhibicion, prototipo o servicio.",
        "audience_and_impact": "PENDIENTE: identificar audiencia, venue o consumidor real.",
        "workplan": [],
        "budget": [],
    }
    evidence = {
        "source_index": str(output_dir / "source_index_reference.json"),
        "project_metadata": project,
        "mak_links": links,
        "representative_assets": assets,
        "rule": "metadata is evidence of existence, not proof of artistic claims",
    }
    outputs = {
        "json": str(output_dir / "applications" / f"{application_id}.json"),
        "html": str(output_dir / "applications" / f"{application_id}.html"),
    }
    reconstruction_ref = None
    reconstruction_decision = None
    if reconstruction is not None:
        reconstruction_ref = str(reconstruction.get("source_path") or "")
        reconstruction_decision = (reconstruction.get("decisions") or {}).get(
            project["path"]
        )
        if reconstruction_decision is None:
            raise ValueError(
                f"project {project['path']!r} is absent from reconstruction decisions"
            )
        project["reconstruction"] = {
            "role": reconstruction_decision["role"],
            "epistemic_status": reconstruction_decision["epistemic_status"],
            "rule": reconstruction_decision["rule"],
        }
        outputs["reconstruction"] = reconstruction_ref
    payload = {
        "schema": "mak-application-package-v1",
        "application_id": application_id,
        "status": "draft_with_evidence_gaps",
        "readiness": readiness,
        "fund": {"id": fund_id, "name": fund_name, "status": "candidate_unverified", "requirements": requirements},
        "project": project,
        "sections": sections,
        "evidence": evidence,
        "gaps": gaps,
        "next_action": "Completar gaps en orden: convocatoria oficial, contexto, metodo, presupuesto, cronograma y equipo.",
    }
    if reconstruction is not None:
        payload["evidence"]["reconstruction"] = {
            "schema": reconstruction.get("schema"),
            "algorithm_version": reconstruction.get("algorithm_version"),
            "scope": reconstruction.get("scope"),
            "index_fingerprint": reconstruction.get("index_fingerprint"),
            "source_path": reconstruction_ref,
            "decision": reconstruction_decision,
            "summary": reconstruction.get("summary"),
        }
    con.execute(
        "INSERT OR REPLACE INTO application_packages VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (run_id, application_id, project_id, fund_id, payload["status"], readiness,
         project["title"], stable_json(sections), stable_json(evidence), stable_json(gaps), stable_json(outputs)),
    )
    return payload


def render_application_html(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    esc = html.escape
    gaps = "".join(f"<li><b>{esc(g['field'])}</b> ({esc(g['severity'])}): {esc(g['reason'])}</li>" for g in payload["gaps"])
    links = "".join(f"<li><code>{esc(str(item['mak_path']))}</code> — {esc(item['relation'])}</li>" for item in payload["evidence"]["mak_links"])
    body = f"""<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Expediente {esc(payload['project']['title'])}</title>
<style>body{{font:16px system-ui;max-width:980px;margin:2rem auto;padding:0 1rem;color:#202020}}header{{border-bottom:3px solid #222;padding-bottom:1rem}}.score{{font-size:2rem;color:#845}}section{{margin:2rem 0;padding:1rem;background:#f5f1ea;border-radius:12px}}li{{margin:.55rem 0}}code{{overflow-wrap:anywhere}}</style>
<header><h1>{esc(payload['project']['title'])}</h1><p><b>Expediente estructurado:</b> {esc(payload['fund']['name'])} · <b>Estado:</b> {esc(payload['status'])}</p><div class="score">Readiness {payload['readiness']:.0f}/100</div></header>
<section><h2>Base del proyecto</h2><p>Ruta de origen: <code>{esc(payload['project']['path'])}</code></p><p>Dimensionalidad: {esc(payload['project']['dimensionality'])}; {payload['project']['asset_count']} activos; {payload['project']['bytes']:,} bytes.</p></section>
<section><h2>Secciones de postulación</h2><h3>Contexto</h3><p>{esc(payload['sections']['problem_and_context'])}</p><h3>Método</h3><p>{esc(payload['sections']['artistic_or_technical_method'])}</p><h3>Resultados</h3><p>{esc(payload['sections']['outputs'])}</p><h3>Audiencia e impacto</h3><p>{esc(payload['sections']['audience_and_impact'])}</p></section>
<section><h2>Relaciones MAK</h2><ul>{links or '<li>No hay consumidores vinculados todavía.</li>'}</ul></section>
<section><h2>Gaps que bloquean la postulación</h2><ul>{gaps}</ul><p><b>Siguiente acción:</b> {esc(payload['next_action'])}</p></section>
<footer>Generado desde evidencia local. No es una postulación enviada ni una verificación de convocatoria.</footer></html>"""
    path.write_text(body, encoding="utf-8")


def write_outputs(con: sqlite3.Connection, run_id: str, output_dir: Path,
                  source_ref: str, source_root: str, source_summary: dict[str, Any],
                  packages: list[dict[str, Any]], selected: list[dict[str, Any]],
                  reconstruction: dict[str, Any] | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "applications").mkdir(exist_ok=True)
    reference = {"schema": SCHEMA, "source_ref": source_ref, "source_root": source_root,
                 "source_summary": source_summary, "source_preserved": True,
                 "copied_source_tree": False}
    if reconstruction is not None:
        reference["reconstruction_ref"] = reconstruction.get("source_path")
        reference["reconstruction_schema"] = reconstruction.get("schema")
    (output_dir / "source_index_reference.json").write_text(stable_json(reference) + "\n", encoding="utf-8")
    for package in packages:
        json_path = output_dir / "applications" / f"{package['application_id']}.json"
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        render_application_html(package, output_dir / "applications" / f"{package['application_id']}.html")
    with (output_dir / "project_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rank", "project_id", "title", "path", "score", "reason", "asset_count", "bytes", "dimensionality", "mak_links"])
        writer.writeheader()
        for rank, item in enumerate(selected, 1):
            writer.writerow(dict(rank=rank, **{k: item[k] for k in writer.fieldnames if k != "rank"}))
    counts = {"artifacts": con.execute("select count(*) from intake_assets where run_id=?", (run_id,)).fetchone()[0],
              "projects": con.execute("select count(*) from intake_projects where run_id=?", (run_id,)).fetchone()[0],
              "relations": con.execute("select count(*) from intake_relations where run_id=?", (run_id,)).fetchone()[0],
              "mak_links": con.execute("select count(*) from mak_links where run_id=?", (run_id,)).fetchone()[0],
              "applications": len(packages)}
    manifest = {"schema": SCHEMA, "run_id": run_id, "source_ref": source_ref, "source_root": source_root,
                "counts": counts, "top_candidates": selected, "applications": [p["application_id"] for p in packages],
                "outputs": {"database": str(output_dir / "intake.sqlite"), "manifest": str(output_dir / "intake.json"),
                            "candidates_csv": str(output_dir / "project_candidates.csv")},
                "status": "draft_with_evidence_gaps", "next_action": "review application JSON/HTML and fill gaps before any submission"}
    if reconstruction is not None:
        manifest["reconstruction"] = {
            "schema": reconstruction.get("schema"),
            "algorithm_version": reconstruction.get("algorithm_version"),
            "scope": reconstruction.get("scope"),
            "source_path": reconstruction.get("source_path"),
        }
    (output_dir / "intake.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_intake(index_path: Path, output_dir: Path, project_path: str | None,
                 fund_names: list[str], candidate_limit: int,
                 mak_db: Path = DEFAULT_MAK_DB,
                 source_kind: str = "portable_ssd_index",
                 learning_db: Path | None = None,
                 reconstruction_path: Path | None = None) -> dict[str, Any]:
    source_root, source_summary = read_source_summary(index_path)
    fingerprint = source_fingerprint(index_path, source_root, source_summary)
    run_id = fingerprint[:20]
    reconstruction = None
    if reconstruction_path is not None:
        reconstruction = json.loads(reconstruction_path.read_text(encoding="utf-8"))
        if reconstruction.get("schema") != "mak-project-reconstruction-v1":
            raise ValueError("unsupported reconstruction schema")
        if Path(str(reconstruction.get("index_path"))).resolve() != index_path.resolve():
            raise ValueError("reconstruction index does not match intake index")
        reconstruction["source_path"] = str(reconstruction_path.resolve())
    output_db = output_dir / "intake.sqlite"
    con = connect(output_db)
    create_schema(con)
    con.execute("INSERT OR IGNORE INTO intake_runs(run_id,schema_name,source_kind,source_ref,source_root,source_fingerprint,project_title,created_at,status,next_action) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, SCHEMA, source_kind, str(index_path), source_root, fingerprint,
                 project_path or "SSD project intake", now_iso(), "running", "import_source_index"))
    con.execute("INSERT INTO workflow_events(run_id,stage,status,detail,created_at) VALUES (?,?,?,?,?)",
                (run_id, "import", "pass", "Imported existing index without copying source files", now_iso()))
    load_index(con, index_path, source_root, run_id)
    project_rows = [dict(row) for row in con.execute("select project_id,title,relative_path from intake_projects where run_id=?", (run_id,))]
    for row in project_rows:
        link_mak(con, mak_db, run_id, row["project_id"], row["relative_path"])
    explicit = next((r for r in project_rows if project_path and r["relative_path"].casefold() == project_path.casefold()), None)
    if explicit:
        add_known_mak_links(con, run_id, explicit["project_id"])
    selected = select_candidates(con, run_id, project_path, candidate_limit, reconstruction)
    if explicit:
        selected.sort(key=lambda x: (0 if x["project_id"] == explicit["project_id"] else 1, -x["score"]))
    packages: list[dict[str, Any]] = []
    target_projects = selected[:1] if project_path else selected[:min(3, len(selected))]
    for project in target_projects:
        for fund_name in fund_names:
            packages.append(build_application(
                con, run_id, project, fund_name, output_dir, reconstruction
            ))
    con.execute("UPDATE intake_runs SET status=?, artifact_count=?, project_count=?, relation_count=?, mak_link_count=?, application_count=?, next_action=? WHERE run_id=?",
                ("draft_with_evidence_gaps", con.execute("select count(*) from intake_assets where run_id=?", (run_id,)).fetchone()[0],
                 con.execute("select count(*) from intake_projects where run_id=?", (run_id,)).fetchone()[0],
                 con.execute("select count(*) from intake_relations where run_id=?", (run_id,)).fetchone()[0],
                 con.execute("select count(*) from mak_links where run_id=?", (run_id,)).fetchone()[0], len(packages),
                 "Fill official call, context, method, budget, schedule and team gaps", run_id))
    con.execute("INSERT INTO workflow_events(run_id,stage,status,detail,created_at) VALUES (?,?,?,?,?)",
                (run_id, "application", "pass", f"Generated {len(packages)} structured draft package(s) with explicit gaps", now_iso()))
    con.commit()
    write_outputs(
        con, run_id, output_dir, str(index_path), source_root, source_summary,
        packages, selected, reconstruction
    )
    con.commit()
    con.close()
    learning_materialized: list[dict[str, Any]] = []
    if learning_db is not None:
        # Explicit opt-in: normal intake remains a derived package only.
        from flujo.knowledge.project_ir import LearningStore, project_ir_from_application_package
        store = LearningStore(learning_db)
        for package in packages:
            record = project_ir_from_application_package(
                package, source_ref=str(output_dir / "applications" / f"{package['application_id']}.json"))
            fingerprint = store.save_project(record)
            learning_materialized.append({
                "project_id": record["project_id"],
                "state": record["state"],
                "unknowns": len(record["unknowns"]),
                "fingerprint": fingerprint,
            })
    return {"run_id": run_id, "output_db": str(output_db), "output_dir": str(output_dir),
            "source_root": source_root, "selected": selected,
            "applications": [p["application_id"] for p in packages],
            "learning_materialized": learning_materialized}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source-index", type=Path)
    source_group.add_argument("--source-root", type=Path, help="One bounded project folder; files are referenced, not copied")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--project-path", default=None, help="Exact project_path from the source index")
    parser.add_argument("--fund", action="append", dest="funds", default=["Fondart"], help="Funding target label; repeatable")
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--mak-db", type=Path, default=DEFAULT_MAK_DB)
    parser.add_argument("--learning-db", type=Path, default=None,
                        help="Explicit Project IR SQLite target; omitted means no learning DB write")
    parser.add_argument(
        "--reconstruction", type=Path, default=None,
        help="Persisted mak-project-reconstruction-v1 JSON to drive candidate selection",
    )
    args = parser.parse_args(argv)
    output_dir = args.out_dir.resolve()
    if args.source_root is not None:
        if not args.source_root.is_dir():
            parser.error(f"source root not found: {args.source_root}")
        source_index, source_root, _summary = scan_project_folder(
            args.source_root, output_dir / "source_index.sqlite")
        effective_project = args.project_path or args.source_root.name
        result = build_intake(source_index, output_dir, effective_project,
                              list(dict.fromkeys(args.funds)), args.candidate_limit,
                              args.mak_db.resolve(), "project_folder",
                              args.learning_db.resolve() if args.learning_db else None,
                              args.reconstruction.resolve() if args.reconstruction else None)
    else:
        if not args.source_index.is_file():
            parser.error(f"source index not found: {args.source_index}")
        result = build_intake(args.source_index.resolve(), output_dir, args.project_path,
                              list(dict.fromkeys(args.funds)), args.candidate_limit,
                              args.mak_db.resolve(), "portable_ssd_index",
                              args.learning_db.resolve() if args.learning_db else None,
                              args.reconstruction.resolve() if args.reconstruction else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
