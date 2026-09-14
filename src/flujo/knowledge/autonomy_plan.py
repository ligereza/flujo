"""Pure bounded-autonomy policy: project actions without executing them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ._contract_helpers import nullable_text as _text
from ._io_helpers import load_json_file as load_json


PLAN_SCHEMA = "mak-product-plan-v1"
DOSSIER_SCHEMA = "mak-portfolio-dossier-v1"
APPLICATION_SCHEMA = "mak-application-research-package-v1"
RETURN_SCHEMA = "mak-evidence-return-v1"
LEARNING_SCHEMA = "mak-product-learning-evaluation-v1"
OUTPUT_SCHEMA = "mak-autonomy-plan-v1"
ALLOWED_ACTIONS = ("observe", "research", "recompute", "compile", "wait", "abstain")


def _refs(value: Any) -> list[str]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return sorted({item.strip() for item in values if isinstance(item, str) and item.strip()})


def _object_refs(value: Any, key: str = "program_id") -> list[str]:
    if isinstance(value, list) and any(isinstance(item, Mapping) for item in value):
        return sorted({str(item[key]) for item in value if isinstance(item, Mapping) and _text(item.get(key))})
    return _refs(value)


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _voi(value: Any) -> tuple[float, Any]:
    """Return a safe sort value and preserve the real VOI object unchanged."""
    if isinstance(value, Mapping):
        candidate = value.get("value")
        status = _text(value.get("status"))
        if status in {"defined", "observed", "valid"} and isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
            candidate = float(candidate)
            if candidate == candidate and candidate not in {float("inf"), float("-inf")}:
                return candidate, value
        return 0.0, value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if numeric == numeric and numeric not in {float("inf"), float("-inf")}:
            return numeric, value
    return 0.0, value


def _action(kind: str, *, opportunity_id: str | None = None, program_ids=None, requirement_ids=None, job_ids=None, reason=None, priority_basis=None, expected_information_gain="unknown", preconditions=None, success=None, failure=None, max_attempts=1) -> dict[str, Any]:
    refs = {"opportunity_id": opportunity_id, "program_ids": _object_refs(program_ids), "requirement_ids": _refs(requirement_ids), "job_ids": _refs(job_ids)}
    body = {"action": kind, **refs, "reason": reason, "priority_basis": priority_basis or {}, "expected_information_gain": expected_information_gain, "preconditions": preconditions or [], "success_observations": success or [], "failure_observations": failure or [], "max_attempts": max_attempts, "dispatch": False, "conductor_projection": "plan-only"}
    body["action_id"] = "action:" + hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:20]
    return body


def _valid_learning(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("schema") == LEARNING_SCHEMA and value.get("status") in {"policy_candidate", "shadow"} and value.get("training_permitted") is False and isinstance(value.get("evidence"), Mapping)


def compile_autonomy_plan(plan: Mapping[str, Any], dossier: Mapping[str, Any], application: Mapping[str, Any], evidence_return: Mapping[str, Any], learning: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors = []
    for name, value, schema in (("plan", plan, PLAN_SCHEMA), ("dossier", dossier, DOSSIER_SCHEMA), ("application", application, APPLICATION_SCHEMA), ("evidence_return", evidence_return, RETURN_SCHEMA)):
        if not isinstance(value, Mapping) or value.get("schema") != schema:
            errors.append(f"{name}_schema_invalid")
    learning_valid = _valid_learning(learning)
    if isinstance(learning, Mapping) and learning.get("schema") != LEARNING_SCHEMA:
        errors.append("learning_schema_invalid")
    opportunity_id = _text(plan.get("opportunity_id")) if isinstance(plan, Mapping) else None
    if errors:
        actions = [_action("abstain", opportunity_id=opportunity_id, reason="input_contract_invalid", priority_basis={"uncertainty": 1.0}, preconditions=["all required contracts validate"], failure=["contract remains invalid"])]
        return _output(plan, actions, errors, learning_valid)

    actions: list[dict[str, Any]] = []
    target = plan.get("targets") if isinstance(plan.get("targets"), Mapping) else {}
    app_target = target.get("application_draft") if isinstance(target.get("application_draft"), Mapping) else {}
    research_target = target.get("research_brief") if isinstance(target.get("research_brief"), Mapping) else {}
    app_status = _text(application.get("application_draft", {}).get("status")) if isinstance(application.get("application_draft"), Mapping) else None
    contradicted = bool(evidence_return.get("contradiction_notices")) or app_status == "contradicted"
    if contradicted:
        actions.append(_action("abstain", opportunity_id=opportunity_id, reason="contradiction_or_invalid_state", priority_basis={"hard_gate": 1.0, "uncertainty": 1.0}, failure=["contradiction remains unresolved"]))
    proposals = evidence_return.get("opportunity_evidence_proposals", []) + evidence_return.get("practice_evidence_proposals", []) if isinstance(evidence_return.get("opportunity_evidence_proposals"), list) and isinstance(evidence_return.get("practice_evidence_proposals"), list) else []
    if proposals:
        actions.append(_action("recompute", opportunity_id=opportunity_id, requirement_ids=[row.get("requirement_id") for row in proposals], reason="evidence_return_pending_ingestion", priority_basis={"uncertainty": 1.0}, preconditions=["candidate evidence is ingested", "promotion remains none"], success=["fit input hash changes deterministically"], failure=["evidence remains pending_ingestion"]))
    jobs = application.get("research_brief", {}).get("jobs", []) if isinstance(application.get("research_brief"), Mapping) else []
    gaps = application.get("research_brief", {}).get("gaps", []) if isinstance(application.get("research_brief"), Mapping) else []
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, Mapping) or job.get("dispatch") is not False:
                continue
            voi_value, voi_raw = _voi(job.get("voi"))
            actions.append(_action("research", opportunity_id=opportunity_id, program_ids=plan.get("selected_programs", []), requirement_ids=job.get("requirement_ids", job.get("requirement_id")), job_ids=job.get("job_id"), reason="research_job_unresolved", priority_basis={"hard_gate": 1.0 if str(job.get("requirement_id", "")).startswith("source-validity:") else 0.0, "priority_rank": job.get("priority_rank"), "deadline": job.get("deadline"), "voi": voi_value, "voi_observed": voi_raw, "uncertainty": 1.0}, expected_information_gain=job.get("expected_information_gain", "unknown"), preconditions=["job status planned_not_dispatched", "dispatch remains false"], success=["triangulation result closes requirement"], failure=["capture unresolved"], max_attempts=job.get("max_attempts", 1)))
    if isinstance(gaps, list):
        for gap in gaps:
            if isinstance(gap, Mapping) and str(gap.get("kind", "")).casefold() in {"archive", "missing_evidence"}:
                actions.append(_action("observe", opportunity_id=opportunity_id, requirement_ids=gap.get("requirement_id"), reason="missing_archive_evidence", priority_basis={"uncertainty": 1.0}, preconditions=["archive source remains read-only"], success=["archive evidence state changes"], failure=["evidence remains missing"]))
    stale = False
    plan_hashes = plan.get("input_hashes") if isinstance(plan.get("input_hashes"), Mapping) else {}
    for source in (dossier, application):
        hashes = source.get("input_hashes") if isinstance(source, Mapping) and isinstance(source.get("input_hashes"), Mapping) else {}
        if hashes and plan_hashes and any(key in plan_hashes and key in hashes and plan_hashes[key] != hashes[key] for key in plan_hashes):
            stale = True
    if stale:
        actions.append(_action("compile", opportunity_id=opportunity_id, program_ids=[row.get("program_id") for row in plan.get("selected_programs", []) if isinstance(row, Mapping)], reason="product_or_plan_input_hash_stale", priority_basis={"uncertainty": 1.0}, preconditions=["source contracts unchanged during compile"], success=["output input hashes match current plan"], failure=["hash remains stale"]))
    if not actions and app_target.get("status") == "draftable" and research_target.get("status") == "not_required":
        actions.append(_action("wait", opportunity_id=opportunity_id, reason="ready_without_authorized_external_action", priority_basis={"uncertainty": 0.0}, preconditions=["no pending proposals or jobs"], success=["state hash remains unchanged"], failure=["new gap or proposal appears"]))
    if not actions:
        actions.append(_action("wait", opportunity_id=opportunity_id, reason="no_actionable_change", priority_basis={"uncertainty": 0.0}, preconditions=["no unresolved jobs"], success=["no state change"], failure=["new actionable gap appears"]))
    dedup = {item["action_id"]: item for item in actions}
    ordered = sorted(dedup.values(), key=lambda item: (-float(item["priority_basis"].get("hard_gate") or 0), -float(item["priority_basis"].get("voi") or 0), item["action"], item["action_id"]))
    return _output(plan, ordered, errors, learning_valid)


def _output(plan: Mapping[str, Any], actions: list[dict[str, Any]], errors: list[str], learning_valid: bool) -> dict[str, Any]:
    opportunity_id = _text(plan.get("opportunity_id")) if isinstance(plan, Mapping) else None
    state = {"opportunity_id": opportunity_id, "plan_id": plan.get("plan_id") if isinstance(plan, Mapping) else None, "input_hashes": plan.get("input_hashes", {}) if isinstance(plan, Mapping) else {}, "learning_priority_usable": learning_valid}
    return {"schema": OUTPUT_SCHEMA, "current_state": state, "prioritized_actions": actions, "stop_conditions": {"max_attempts": 1, "stop_on_no_hash_change": True, "stop_on_budget_exhausted": True, "stop_on_closure": True, "loop": False}, "control": {"database_write": False, "dispatch": False, "publication": False, "submission": False, "promotion": "none", "training": False, "user_review_required": False}, "provenance": {"errors": sorted(set(errors)), "deterministic": True, "learning_evaluation_used_only_for_priority": learning_valid, "conductor_projection": "plan-only"}}
