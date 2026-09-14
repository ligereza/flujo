"""Evidence-graph queue for the first real artist-archive slice.

This module is a thin product layer over the existing Project IR and learning
ledger.  It does not create a relation database or copy artistic inputs.  The
graph observed by C07/C04/C05/C06 is stored inside one Project IR record;
human decisions are appended as verified review episodes in the same ledger.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ._contract_helpers import compact_json as _json
from ._io_helpers import utc_now_iso as _now
from .project_ir import LearningStore, build_project_ir, format_family, media_type


SCHEMA = "mak-portfolio-evidence-v1"
QUEUE_SCHEMA = "mak-portfolio-evidence-queue-v1"
DRAFT_SCHEMA = "mak-portfolio-draft-v1"
CASE_SCOPE = "single_case"
CASE_ID = "ARICA-01"
PORTFOLIO_STATUS = "case_draft_not_full_portfolio"
DECISIONS = ("accept", "reject", "correct", "request_evidence")
DECISION_STATUS = {
    "accept": "accepted_by_human",
    "reject": "rejected_by_human",
    "correct": "corrected_by_human",
    "request_evidence": "needs_evidence",
}


class PortfolioEvidenceError(ValueError):
    """Invalid evidence queue or human decision."""


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("candidate_id") or candidate.get("id") or "").strip()


def _normalize_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = _candidate_id(candidate)
    if not candidate_id:
        raise PortfolioEvidenceError("relation_candidate_missing_id")
    result = dict(candidate)
    result["candidate_id"] = candidate_id
    result.setdefault("status", "unresolved_candidate")
    result.setdefault("score", 0.0)
    result.setdefault("evidence_refs", [])
    result.setdefault("missing_evidence", [])
    result.setdefault("next_probe", "review the relation evidence")
    return result


def _artifact_rows(observed_artifacts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in observed_artifacts:
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        rows.append({
            "artifact_id": str(item.get("id") or "artifact:" + path),
            "relative_path": path,
            "name": Path(path).name,
            "suffix": Path(path).suffix.casefold(),
            "format_family": format_family(path),
            "media_type": media_type(path),
            "size_bytes": int(item.get("bytes") or 0),
            "sha256": str(item.get("sha256") or ""),
            "hash_status": "full" if item.get("sha256") else "not_computed",
            "availability": "observed",
            "role": "observed_artifact",
        })
    return rows


def build_project_record(
    *,
    project_id: str,
    title: str,
    source_root: str | Path,
    observed_artifacts: Iterable[Mapping[str, Any]],
    relation_candidates: Iterable[Mapping[str, Any]],
    evidence: Iterable[Mapping[str, Any]],
    unknowns: Iterable[str],
    source_snapshot_hash: str,
    graph_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one reviewable Project IR record from observed evidence."""
    candidates = [_normalize_candidate(item) for item in relation_candidates]
    record = build_project_ir(
        project_id=project_id,
        title=title,
        source_root=source_root,
        artifacts=_artifact_rows(observed_artifacts),
        domains=("mak", "curatoria", "portfolio"),
        purpose="artist_archive_to_auditable_portfolio",
        state="review_required",
        evidence=evidence,
        unknowns=unknowns,
        relations=candidates,
        source_kind="artist_archive_bundle",
        source_ref=str(source_root),
    )
    # Keep the canonical Project IR schema intact so the existing ledger
    # validator remains the authority.  This layer is an attached product
    # projection, not a replacement record format.
    record["portfolio_evidence_schema"] = SCHEMA
    record["project_ir_schema"] = record.get("schema", "mak-project-ir-v1")
    record["portfolio_case"] = {
        "scope": CASE_SCOPE,
        "case_id": CASE_ID,
        "portfolio_status": PORTFOLIO_STATUS,
    }
    record["source_snapshot_hash"] = source_snapshot_hash
    record["evidence_graph"] = dict(graph_observation)
    record["portfolio_policy"] = {
        "auto_publish": False,
        "human_decisions": list(DECISIONS),
        "unknown_is_actionable": True,
        "source_of_truth": "project_records.ir_json",
    }
    record["portfolio_draft"] = build_draft(record)
    return record


def load_record(database: str | Path, project_id: str) -> dict[str, Any]:
    store = LearningStore(database)
    with store.connect() as connection:
        row = connection.execute(
            "SELECT ir_json FROM project_records WHERE project_id=?", (project_id,)
        ).fetchone()
    if row is None:
        raise PortfolioEvidenceError(f"portfolio_project_not_found:{project_id}")
    record = json.loads(row[0])
    if not isinstance(record, dict):
        raise PortfolioEvidenceError("portfolio_project_record_not_object")
    return record


def _review(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    value = candidate.get("human_review")
    return value if isinstance(value, dict) else None


def _review_history(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    value = candidate.get("human_review_history")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    review = _review(candidate)
    return [review] if review else []


def _effective_relation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    review = _review(candidate) or {}
    corrected = review.get("action") == "correct"
    return {
        "source_id": candidate.get("source_id"),
        "relation": candidate.get("corrected_relation") if corrected else candidate.get("relation"),
        "target_id": candidate.get("corrected_target_id") if corrected else candidate.get("target_id"),
        "candidate_id": candidate.get("candidate_id"),
        "review_action": review.get("action") or "pending",
    }


def _queue_metrics(items: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    rows = list(items)
    decided = sum(item.get("human_action") in DECISIONS for item in rows)
    pending = sum(item.get("human_action") == "pending" for item in rows)
    contradicted = sum(
        item.get("human_action") == "reject"
        or item.get("status") in {"contradicted", "rejected_by_human"}
        for item in rows
    )
    return {
        "candidates_total": len(rows),
        "decided": decided,
        "pending": pending,
        "contradicted": contradicted,
        "eligible_for_draft": sum(item.get("human_action") in {"accept", "correct"} for item in rows),
    }


def queue_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [
        _normalize_candidate(item)
        for item in record.get("relations", [])
        if isinstance(item, Mapping)
    ]
    items = []
    for candidate in candidates:
        review = _review(candidate)
        action = str(review.get("action")) if review else "pending"
        items.append({
            "candidate_id": candidate["candidate_id"],
            "source_id": candidate.get("source_id"),
            "target_id": candidate.get("target_id"),
            "relation": candidate.get("relation"),
            "status": candidate.get("status"),
            "score": candidate.get("score", 0.0),
            "evidence_refs": candidate.get("evidence_refs", []),
            "missing_evidence": candidate.get("missing_evidence", []),
            "next_probe": candidate.get("next_probe", ""),
            "claim_limit": candidate.get("claim_limit", ""),
            "score_breakdown": candidate.get("score_breakdown", {}),
            "alternatives": candidate.get("alternatives", []) if isinstance(candidate.get("alternatives", []), list) else [],
            "contradictions": candidate.get("contradictions", []) if isinstance(candidate.get("contradictions", []), list) else [],
            "original_relation": candidate.get("original_relation", candidate.get("relation")),
            "original_target_id": candidate.get("original_target_id", candidate.get("target_id")),
            "human_action": action,
            "human_review": review,
            "human_review_history": _review_history(candidate),
        })
    counts: dict[str, int] = {}
    for item in items:
        key = item["human_action"]
        counts[key] = counts.get(key, 0) + 1
    return {
        "schema": QUEUE_SCHEMA,
        "scope": CASE_SCOPE,
        "case_id": CASE_ID,
        "portfolio_status": PORTFOLIO_STATUS,
        "project_id": record.get("project_id"),
        "title": record.get("title"),
        "source_snapshot_hash": record.get("source_snapshot_hash", ""),
        "actions": list(DECISIONS),
        "promotion": "none",
        "items": items,
        "counts": counts,
        "metrics": _queue_metrics(items),
    }


def _artifact_by_id(record: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    graph = record.get("evidence_graph")
    artifacts = graph.get("artifacts", []) if isinstance(graph, Mapping) else []
    return {
        str(item.get("id")): item
        for item in artifacts
        if isinstance(item, Mapping) and item.get("id")
    }


def build_draft(record: Mapping[str, Any]) -> dict[str, Any]:
    """Build a derived portfolio draft without promoting any work publicly."""
    artifacts = _artifact_by_id(record)
    accepted = []
    pending = []
    contradicted = []
    for raw in record.get("relations", []):
        if not isinstance(raw, Mapping):
            continue
        candidate = _normalize_candidate(raw)
        review = _review(candidate)
        if review and review.get("action") in {"accept", "correct"}:
            accepted.append(candidate)
        elif review and review.get("action") == "reject":
            contradicted.append(candidate)
        else:
            pending.append(candidate)

    output_candidates = []
    for artifact_id, artifact in sorted(artifacts.items()):
        kind = str(artifact.get("kind") or "")
        path = str(artifact.get("path") or "")
        if kind not in {"image", "video"} and not path.endswith("rayu_resources.glb"):
            continue
        if path.endswith("MYRA/MYRA_final.mp4"):
            role = "observed_output_source_binding_unknown"
        elif path.endswith("tottem_ojo.mp4"):
            role = "aep_used_media_output_role_unknown"
        elif "/render_20s/" in path and Path(path).suffix.casefold() == ".png":
            role = "sequence_frame_not_standalone_work"
        elif path.endswith("rayu_resources.glb"):
            role = "export_artifact_final_delivery_unproven"
        else:
            role = "observed_media_candidate"
        output_candidates.append({
            "artifact_id": artifact_id,
            "path": path,
            "kind": kind,
            "role": role,
            "publication_status": "unverified",
            "evidence": list(artifact.get("evidence_refs") or []),
        })

    effective_relations = [_effective_relation(item) for item in accepted]
    selected_ids = sorted(
        f"{item['source_id']} -[{item['relation']}]-> {item['target_id']}"
        for item in effective_relations
    )
    relation_rows = []
    for item in accepted:
        effective = _effective_relation(item)
        relation_rows.append({
            **effective,
            "original_relation": item.get("original_relation", item.get("relation")),
            "original_target_id": item.get("original_target_id", item.get("target_id")),
            "evidence_refs": list(item.get("evidence_refs") or []),
            "claim_limit": item.get("claim_limit", ""),
            "human_review": _review(item),
        })
    pending_rows = [_normalize_candidate(item) for item in pending]
    contradicted_rows = [_normalize_candidate(item) for item in contradicted]
    eligible_work_ids = {
        str(item.get("target_id")) for item in effective_relations if item.get("target_id")
    }
    defensible_works = [
        item for item in output_candidates if item["artifact_id"] in eligible_work_ids
    ]
    pending_works = [
        item for item in output_candidates if item["artifact_id"] not in eligible_work_ids
    ]
    metrics = {
        "candidates_total": len(accepted) + len(pending) + len(contradicted),
        "decided": len(accepted) + len(contradicted) + sum(
            1 for item in pending if _review(item) and _review(item).get("action") == "request_evidence"
        ),
        "pending": sum(
            1 for item in pending
            if not _review(item) or _review(item).get("action") != "request_evidence"
        ),
        "contradicted": len(contradicted),
        "eligible_for_draft": len(accepted),
    }
    return {
        "schema": DRAFT_SCHEMA,
        "scope": CASE_SCOPE,
        "case_id": CASE_ID,
        "portfolio_status": PORTFOLIO_STATUS,
        "project_id": record.get("project_id"),
        "generated_at": _now(),
        "source_of_truth": "data/mak_knowledge.db:project_records.ir_json",
        "case_boundary": "This is one auditable project/process dossier, not the artist's full portfolio.",
        "promotion": "none",
        "selection": {
            "human_accepted_relation_keys": selected_ids,
            "human_accepted_relations": effective_relations,
            "accepted_relation_count": len(accepted),
            "pending_relation_count": len(pending),
            "contradicted_relation_count": len(contradicted),
        },
        "works": output_candidates,
        "defensible": {
            "relations": relation_rows,
            "works": defensible_works,
        },
        "pending": {
            "relations": pending_rows,
            "works": pending_works,
        },
        "contradicted": {
            "relations": contradicted_rows,
        },
        "audit": {
            "every_item_has_evidence": all(bool(item["evidence"]) for item in output_candidates),
            "source_snapshot_hash": record.get("source_snapshot_hash", ""),
            "unknowns": list(record.get("unknowns") or []),
            "metrics": metrics,
            "human_reviews": [
                item.get("human_review") for item in record.get("relations", [])
                if isinstance(item, Mapping) and item.get("human_review")
            ],
        },
    }


def apply_human_decision(
    database: str | Path,
    *,
    project_id: str,
    candidate_id: str,
    action: str,
    actor: str = "human",
    note: str = "",
    corrected_relation: str = "",
    corrected_target_id: str = "",
    source_snapshot_hash: str = "",
    code_revision: str = "working-tree:portfolio-evidence-v1",
) -> dict[str, Any]:
    """Persist one human review and regenerate the derived draft."""
    if action not in DECISIONS:
        raise PortfolioEvidenceError(f"unsupported_human_action:{action}")
    if action == "correct" and (not corrected_relation or not corrected_target_id):
        raise PortfolioEvidenceError("correct_requires_relation_and_target")
    note = str(note or "").strip()
    if not note:
        raise PortfolioEvidenceError("decision_requires_reason")
    record = load_record(database, project_id)
    found = None
    for item in record.get("relations", []):
        if isinstance(item, dict) and _candidate_id(item) == candidate_id:
            found = item
            break
    if found is None:
        raise PortfolioEvidenceError(f"candidate_not_found:{candidate_id}")
    decided_at = _now()
    original_relation = found.setdefault("original_relation", found.get("relation"))
    original_target_id = found.setdefault("original_target_id", found.get("target_id"))
    history = found.setdefault("human_review_history", [])
    if not isinstance(history, list):
        history = []
        found["human_review_history"] = history
    episode_id = "episode_portfolio_" + hashlib.sha256(
        _json({
            "project_id": project_id,
            "candidate_id": candidate_id,
            "action": action,
            "actor": actor or "human",
            "note": note,
            "corrected_relation": corrected_relation,
            "corrected_target_id": corrected_target_id,
        }).encode("utf-8")
    ).hexdigest()[:24]
    identity = {
        "action": action,
        "actor": actor or "human",
        "note": note[:1200],
        "corrected_relation": corrected_relation,
        "corrected_target_id": corrected_target_id,
    }
    previous = _review(found)
    if any(all(item.get(key) == value for key, value in identity.items()) for item in history if isinstance(item, dict)):
        return {"ok": True, "idempotent": True, "episode_id": episode_id,
                "queue": queue_payload(record), "draft": build_draft(record)}
    if previous and all(previous.get(key) == value for key, value in identity.items()):
        return {"ok": True, "idempotent": True, "episode_id": episode_id,
                "queue": queue_payload(record), "draft": build_draft(record)}
    review = {
        "decision_id": episode_id,
        "action": action,
        "actor": actor or "human",
        "note": note[:1200],
        "decided_at": decided_at,
        "original_relation": original_relation,
        "original_target_id": original_target_id,
        "corrected_relation": corrected_relation or None,
        "corrected_target_id": corrected_target_id or None,
        "provenance": {
            "source_snapshot_hash": source_snapshot_hash or record.get("source_snapshot_hash", ""),
            "candidate_evidence_refs": list(found.get("evidence_refs") or []),
            "promotion": "none",
        },
    }
    history.append(review)
    found["human_review"] = review
    found["status"] = DECISION_STATUS[action]
    if action == "correct":
        found["corrected_relation"] = corrected_relation
        found["corrected_target_id"] = corrected_target_id
    record["portfolio_draft"] = build_draft(record)

    store = LearningStore(database)
    store.save_project(record)
    store.record_episode(
        project_id=project_id,
        objective="review portfolio evidence relation",
        phase="curatorial_review",
        action={
            "candidate_id": candidate_id,
            "action": action,
            "actor": actor or "human",
            "original_relation": original_relation,
            "original_target_id": original_target_id,
            "corrected_relation": corrected_relation or None,
            "corrected_target_id": corrected_target_id or None,
        },
        observation={"candidate": found},
        outcome={"human_decision": action, "note": note[:1200]},
        validation={"status": "human_review_recorded", "promotion": "none"},
        status="verified",
        provider="human",
        model="",
        episode_id=episode_id,
        source_snapshot_hash=source_snapshot_hash or record.get("source_snapshot_hash", ""),
        code_commit=code_revision,
        tool_versions={"portfolio_evidence": SCHEMA},
        finished_at=decided_at,
    )
    updated = load_record(database, project_id)
    return {
        "ok": True,
        "idempotent": False,
        "episode_id": episode_id,
        "queue": queue_payload(updated),
        "draft": build_draft(updated),
    }
