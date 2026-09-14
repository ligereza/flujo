"""Mechanical evidence closure for a Project IR, without semantic invention."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from .project_ir import LearningStore, stable_json


EVIDENCE_SCHEMA = "mak-project-evidence-closure-v1"


def _path_exists(value: str) -> bool:
    try:
        return Path(value).expanduser().exists()
    except (OSError, ValueError):
        return False


def close_project_evidence(project: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    """Count observable local facts and keep semantic gaps explicit."""
    source = project.get("source") if isinstance(project.get("source"), Mapping) else {}
    root_ref = str(source.get("root_ref") or "")
    root = Path(root_ref).expanduser()
    artifacts = project.get("artifacts", [])
    artifact_rows = []
    for artifact in artifacts if isinstance(artifacts, list) else []:
        if not isinstance(artifact, Mapping):
            continue
        relative = str(artifact.get("relative_path") or "")
        path = root / relative if root_ref and relative else Path("/nonexistent")
        try:
            stat = path.stat()
            observed = {"relative_path": relative, "format_family": artifact.get("format_family", "unknown"), "exists": True, "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        except (OSError, ValueError):
            observed = {"relative_path": relative, "format_family": artifact.get("format_family", "unknown"), "exists": False}
        artifact_rows.append(observed)
    relations = []
    for relation in project.get("relations", []) if isinstance(project.get("relations"), list) else []:
        if not isinstance(relation, Mapping):
            continue
        target = str(relation.get("object") or "")
        relations.append({
            "target": target,
            "plane": relation.get("plane", "unknown"),
            "exists": _path_exists(target),
        })
    available = sum(1 for row in artifact_rows if row["exists"])
    missing = len(artifact_rows) - available
    format_counts: dict[str, int] = {}
    for row in artifact_rows:
        family = str(row.get("format_family") or "unknown")
        format_counts[family] = format_counts.get(family, 0) + 1
    active_links = sum(1 for row in relations if row["plane"] == "active_mak" and row["exists"])
    historical_links = sum(1 for row in relations if row["plane"] == "historical_win" and row["exists"])
    unknowns = [str(item) for item in project.get("unknowns", [])] if isinstance(project.get("unknowns"), list) else []
    checks = {
        "source_root_exists": root.is_dir(),
        "representative_artifacts_total": len(artifact_rows),
        "representative_artifacts_available": available,
        "representative_artifacts_missing": missing,
        "format_counts": format_counts,
        "active_mak_links_available": active_links,
        "historical_win_links_available": historical_links,
        "source_tree_copied": False,
        "repo_root": str(Path(repo_root).expanduser().resolve()),
    }
    status = "needs_evidence" if unknowns or not root.is_dir() or missing else "observed"
    closure = {
        "schema": EVIDENCE_SCHEMA,
        "project_id": project.get("project_id", ""),
        "state": project.get("state", "unknown"),
        "status": status,
        "checks": checks,
        "mechanically_proven": [
            "source_root_presence",
            "representative_asset_existence_and_metadata",
            "format_family_counts",
            "consumer_path_existence",
        ],
        "unknowns_preserved": unknowns,
        "relations": relations,
        "next_action": "collect_human_or_official_evidence_for_unknowns" if unknowns else "review_evidence",
    }
    closure["fingerprint"] = hashlib.sha256(stable_json(closure).encode("utf-8")).hexdigest()
    return closure


def record_evidence_closure(
    store: LearningStore, project: Mapping[str, Any], closure: Mapping[str, Any], *, episode_id: str,
) -> str:
    """Append one idempotent evidence observation to the Project ledger."""
    return store.record_episode(
        project_id=str(project.get("project_id") or ""),
        objective="close mechanically observable project evidence",
        phase="evidence_closure",
        action={"tool": "project_evidence_closure", "writes": 0},
        observation=dict(closure),
        outcome={"status": closure.get("status"), "fingerprint": closure.get("fingerprint")},
        validation={"status": "needs_evidence" if closure.get("status") == "needs_evidence" else "observed", "check": "bounded_local_evidence"},
        status="needs_evidence" if closure.get("status") == "needs_evidence" else "succeeded",
        provider="local", model="evidence-closure",
        episode_id=episode_id,
    )
