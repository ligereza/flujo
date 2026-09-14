"""Additive evidence return: proposals only, never mutations or promotions."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ._io_helpers import load_json_file as load_json
from ._contract_helpers import nullable_text as _text, stable_json as _stable


OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
PRACTICE_SCHEMA = "mak-practice-evidence-state-v1"
FIT_SCHEMA = "mak-opportunity-fit-v1"
FRONTIER_SCHEMA = "mak-research-frontier-jobs-v1"
TRIANGULATION_SCHEMA = "mak-research-triangulation-v1"
RETURN_SCHEMA = "mak-evidence-return-v1"
SUPPORTED = "supported_candidate"


def _id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_stable(value).encode("utf-8")).hexdigest()[:20]


def _refs(value: Any) -> list[str]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return sorted({v.strip() for v in values if isinstance(v, str) and v.strip()})


def _bundle_rows(value: Any, key: str) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        rows = value.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
    return []


def _validate_inputs(opportunity: Any, practice: Any, fit: Any, frontier: Any, triangulation: Any) -> list[str]:
    errors = []
    for name, value, schema in (
        ("opportunity", opportunity, OPPORTUNITY_SCHEMA),
        ("practice", practice, PRACTICE_SCHEMA),
        ("fit", fit, FIT_SCHEMA),
        ("frontier", frontier, FRONTIER_SCHEMA),
        ("triangulation", triangulation, TRIANGULATION_SCHEMA),
    ):
        if not isinstance(value, Mapping):
            errors.append(f"{name}_not_object")
        elif value.get("schema") != schema:
            errors.append(f"{name}_schema_invalid")
    if isinstance(frontier, Mapping) and not isinstance(frontier.get("jobs"), list):
        errors.append("frontier_jobs_missing")
    if isinstance(triangulation, Mapping) and not isinstance(triangulation.get("results"), list):
        errors.append("triangulation_results_missing")
    return sorted(set(errors))


def _source_groups(row: Mapping[str, Any]) -> list[str]:
    values = row.get("independent_source_groups", row.get("source_groups", []))
    result = []
    for value in values if isinstance(values, list) else []:
        if isinstance(value, Mapping):
            group = _text(value.get("group_id")) or _text(value.get("source_group"))
        else:
            group = _text(value)
        if group:
            result.append(group)
    return sorted(set(result))


def _practice_artifacts(practice: Mapping[str, Any]) -> set[str]:
    result = set()
    for row in practice.get("artifacts", []) if isinstance(practice.get("artifacts"), list) else []:
        if isinstance(row, Mapping) and _text(row.get("artifact_ref")):
            result.add(_text(row["artifact_ref"]))
    return result


def _proposal_id(kind: str, job_id: str, refs: list[str]) -> str:
    return _id(kind + ":", {"job_id": job_id, "refs": refs})


def build_evidence_return(opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit: Mapping[str, Any], frontier: Mapping[str, Any], triangulation: Mapping[str, Any]) -> dict[str, Any]:
    errors = _validate_inputs(opportunity, practice, fit, frontier, triangulation)
    if errors:
        return {
            "schema": RETURN_SCHEMA, "opportunity_evidence_proposals": [], "practice_evidence_proposals": [],
            "binding_proposals": [], "contradiction_notices": [], "unresolved": [],
            "fit_recompute": {"required": False, "reason": "input_validation_error", "input_hashes": {}},
            "ledger_episode_candidate": {"status": "candidate", "promotion": "none", "training_permitted": False, "proposal_count": 0},
            "provenance": {"source_schemas": [OPPORTUNITY_SCHEMA, PRACTICE_SCHEMA, FIT_SCHEMA, FRONTIER_SCHEMA, TRIANGULATION_SCHEMA], "promotion": "none", "training_permitted": False, "validation_errors": errors, "deterministic": True},
        }
    opportunity_proposals: list[dict[str, Any]] = []
    practice_proposals: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    artifacts = _practice_artifacts(practice) if isinstance(practice, Mapping) else set()
    jobs = {(_text(row.get("job_id")) or ""): row for row in _bundle_rows(frontier, "jobs")}
    frontier_hashes = frontier.get("input_hashes") if isinstance(frontier.get("input_hashes"), Mapping) else {}
    results = sorted(_bundle_rows(triangulation, "results"), key=lambda row: (_text(row.get("job_id")) or "", _text(row.get("requirement_id")) or ""))
    for result in results:
        job_id = _text(result.get("job_id"))
        requirement_id = _text(result.get("requirement_id"))
        if not job_id or not requirement_id:
            unresolved.append({"job_id": job_id, "requirement_id": requirement_id, "reason": "job_or_requirement_id_missing"})
            continue
        job = jobs.get(job_id, {})
        if not job:
            unresolved.append({"job_id": job_id, "requirement_id": requirement_id, "status": "unresolved", "reason": "job_not_in_frontier", "promotion": "none"})
            continue
        job_requirement_ids = _refs(job.get("requirement_ids"))
        if not job_requirement_ids and _text(job.get("requirement_id")):
            # Compatibility with the singular pre-3A shape is explicit and
            # only applies when the plural field is absent.
            job_requirement_ids = [_text(job["requirement_id"])]
        if requirement_id not in job_requirement_ids:
            unresolved.append({"job_id": job_id, "requirement_id": requirement_id, "status": "unresolved", "reason": "requirement_not_declared_by_frontier_job", "declared_requirement_ids": job_requirement_ids, "promotion": "none"})
            continue
        status = _text(result.get("status")) or "unresolved"
        refs = _refs(result.get("evidence_refs"))
        counter_refs = _refs(result.get("counterevidence_refs"))
        groups = _source_groups(result)
        provenance = result.get("provenance") if isinstance(result.get("provenance"), Mapping) else {}
        if status in {"contradicted_candidate", "mixed_conflict"}:
            contradictions.append({"job_id": job_id, "requirement_id": requirement_id, "status": status, "evidence_refs": refs, "counterevidence_refs": counter_refs, "promotion": "none", "provenance": provenance})
            continue
        if status != SUPPORTED or len(groups) < 2 or not refs:
            unresolved.append({"job_id": job_id, "requirement_id": requirement_id, "status": status, "source_groups": groups, "evidence_refs": refs, "reason": "two_independent_groups_and_refs_required" if status == SUPPORTED else status, "promotion": "none"})
            continue
        scope = _text(job.get("scope")) or _text(result.get("scope")) or "opportunity"
        artifact_refs = _refs(job.get("artifact_refs")) or _refs(result.get("artifact_refs"))
        if scope == "practice":
            dangling = sorted(set(artifact_refs) - artifacts)
            if not artifact_refs or dangling:
                unresolved.append({"job_id": job_id, "requirement_id": requirement_id, "status": "unresolved", "reason": "artifact_ref_dangling_or_missing", "artifact_refs": artifact_refs, "dangling_artifact_refs": dangling, "promotion": "none"})
                continue
            proposal = {"proposal_id": _proposal_id("practice", job_id, refs), "job_id": job_id, "requirement_id": requirement_id, "status": "candidate_pending_ingestion", "evidence_refs": refs, "artifact_refs": artifact_refs, "source_groups": groups, "claims": result.get("claims", []), "promotion": "none", "training_permitted": False, "provenance": provenance}
            practice_proposals.append(proposal)
        else:
            proposal = {"proposal_id": _proposal_id("opportunity", job_id, refs), "job_id": job_id, "requirement_id": requirement_id, "status": "candidate_pending_ingestion", "evidence_refs": refs, "source_groups": groups, "claims": result.get("claims", []), "promotion": "none", "training_permitted": False, "provenance": provenance}
            opportunity_proposals.append(proposal)
        bindings.append({"binding_id": _proposal_id("binding", job_id, refs), "job_id": job_id, "requirement_id": requirement_id, "evidence_refs": refs, "status": "candidate_pending_ingestion", "promotion": "none"})
    for collection in (opportunity_proposals, practice_proposals, bindings, contradictions, unresolved):
        collection.sort(key=_stable)
    required = bool(opportunity_proposals or practice_proposals or contradictions)
    reason = "evidence_return_proposals_pending_ingestion" if required else "no_promotable_evidence_return"
    fit_hash = fit.get("state_hash") or fit.get("input_hash") or frontier_hashes.get("opportunity_fit")
    input_hashes = {"opportunity": opportunity.get("input_hash"), "practice": practice.get("state_hash") or practice.get("input_hash"), "fit": fit_hash}
    return {
        "schema": RETURN_SCHEMA,
        "opportunity_evidence_proposals": opportunity_proposals,
        "practice_evidence_proposals": practice_proposals,
        "binding_proposals": bindings,
        "contradiction_notices": contradictions,
        "unresolved": unresolved,
        "fit_recompute": {"required": required, "reason": reason, "input_hashes": input_hashes},
        "ledger_episode_candidate": {"status": "candidate", "promotion": "none", "training_permitted": False, "proposal_count": len(opportunity_proposals) + len(practice_proposals)},
        "provenance": {"source_schemas": [OPPORTUNITY_SCHEMA, PRACTICE_SCHEMA, FIT_SCHEMA, FRONTIER_SCHEMA, TRIANGULATION_SCHEMA], "promotion": "none", "training_permitted": False, "validation_errors": errors, "deterministic": True},
    }


def dry_run_evidence_return(*inputs: Mapping[str, Any]) -> dict[str, Any]:
    result = build_evidence_return(*inputs)
    return {"dry_run": True, "applied": False, "would_change": copy.deepcopy(result), "result": result}
