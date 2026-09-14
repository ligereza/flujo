"""Portable application-draft and research-brief compiler with no dispatch."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ._contract_helpers import nullable_text as _text
from ._io_helpers import load_json_file as load_json


PLAN_SCHEMA = "mak-product-plan-v1"
OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
PACKAGE_SCHEMA = "mak-application-research-package-v1"
_STATUSES = {"supported", "missing", "contradicted", "unresolved"}


def _stable_hash(value: Mapping[str, Any]) -> str:
    def canonical(node: Any) -> Any:
        if isinstance(node, Mapping):
            return {
                str(key): canonical(child)
                for key, child in sorted(node.items(), key=lambda item: str(item[0]))
            }
        if isinstance(node, list):
            return sorted((canonical(child) for child in node), key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return copy.deepcopy(node)

    encoded = json.dumps(
        canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _refs(value: Any) -> list[str]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return sorted({item.strip() for item in values if isinstance(item, str) and item.strip()})


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _source_gate(opportunity: Mapping[str, Any], plan: Mapping[str, Any]) -> tuple[str, str]:
    validity = _mapping(_mapping(opportunity.get("source")).get("validity"))
    status = _text(validity.get("status"))
    if status == "current_verified" and validity.get("confirmed") is True:
        return "pass", "source_current_verified_and_confirmed"
    if status in {"expired", "ineligible"}:
        return "fail", f"source_{status}"
    return "abstain", "source_not_current_verified_or_unconfirmed"


def _gate_status(plan: Mapping[str, Any], key: str) -> tuple[str, str]:
    value = plan.get(key)
    if isinstance(value, Mapping):
        declared = _text(value.get("declared"))
        passed = value.get("passed")
        if declared == "pass" and passed is True:
            return "pass", f"{key}_passed"
        if declared == "fail" or passed is False:
            return "fail", f"{key}_failed"
    status = _text(value)
    if status == "pass":
        return "pass", f"{key}_passed"
    if status == "fail":
        return "fail", f"{key}_failed"
    return "abstain", f"{key}_not_passed"


def _plan_program(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    program = plan.get("program")
    if isinstance(program, Mapping):
        return program
    programs = plan.get("programs")
    if isinstance(programs, list) and len(programs) == 1 and isinstance(programs[0], Mapping):
        return programs[0]
    return plan


def _selected_programs(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = plan.get("selected_programs")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, Mapping)]
    program = _plan_program(plan)
    return [program] if isinstance(program, Mapping) and _text(program.get("program_id")) else []


def _claim_statuses(plan: Mapping[str, Any]) -> dict[str, str]:
    raw = plan.get("claim_index")
    result: dict[str, str] = {}
    rows = raw.items() if isinstance(raw, Mapping) else []
    for key, value in rows:
        if isinstance(value, Mapping):
            value = value.get("status", value.get("result"))
        if value in _STATUSES:
            result[str(key)] = value
    for row in raw if isinstance(raw, list) else []:
        if isinstance(row, Mapping) and _text(row.get("requirement_id")) and row.get("status") in _STATUSES:
            result[_text(row["requirement_id"])] = row["status"]
    return result


def _status_map(plan: Mapping[str, Any], program: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    raw = program.get("requirement_statuses", plan.get("requirement_statuses"))
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if isinstance(key, str) and value in _STATUSES:
                result[key] = value
    for key, status in (("supported_requirement_ids", "supported"), ("missing_requirement_ids", "missing"), ("contradicted_requirement_ids", "contradicted"), ("unresolved_requirement_ids", "unresolved")):
        for requirement_id in _refs(program.get(key, plan.get(key))):
            result[requirement_id] = status
    return result


def _bindings(plan: Mapping[str, Any], program: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = program.get("bindings", plan.get("bindings", []))
    result = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, Mapping) and _text(row.get("requirement_id")):
            result[_text(row["requirement_id"])] = row
    return result


def _atom_rows(plan: Mapping[str, Any], program: Mapping[str, Any]) -> list[dict[str, Any]]:
    atoms = program.get("content_atoms", plan.get("content_atoms", []))
    result = []
    for atom in atoms if isinstance(atoms, list) else []:
        if not isinstance(atom, Mapping):
            continue
        result.append({
            "atom_id": _text(atom.get("atom_id")) or "",
            "section": _text(atom.get("section")) or "",
            "content": atom.get("content"),
            "requirement_id": _text(atom.get("requirement_id")),
            "unit_ids": _refs(atom.get("unit_ids")),
            "evidence_refs": _refs(atom.get("evidence_refs")),
            "status": atom.get("status", "unresolved"),
        })
    return sorted(result, key=lambda row: (row["section"], row["atom_id"]))


def _job_rows(plan: Mapping[str, Any], program: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]]]:
    rows = program.get("research_jobs", plan.get("research_jobs", plan.get("jobs", [])))
    jobs = []
    rejected = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            rejected.append({"reason": "job_not_object"})
            continue
        job_id = _text(row.get("job_id"))
        requirement_id = _text(row.get("requirement_id"))
        if not job_id or not requirement_id:
            rejected.append({"job_id": job_id, "requirement_id": requirement_id, "reason": "job_or_requirement_id_missing"})
            continue
        jobs.append(row)
    return jobs, rejected


def compile_application_research_package(plan: Mapping[str, Any], opportunity: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA:
        errors.append("plan_schema_invalid")
    if not isinstance(opportunity, Mapping) or opportunity.get("schema") != OPPORTUNITY_SCHEMA:
        errors.append("opportunity_schema_invalid")
    if errors:
        return _empty(errors)
    opportunity_id = _text(opportunity.get("opportunity_id"))
    if _text(plan.get("opportunity_id")) and _text(plan.get("opportunity_id")) != opportunity_id:
        errors.append("plan_opportunity_mismatch")
    programs = _selected_programs(plan)
    if not programs:
        errors.append("selected_programs_missing")
    opportunity_constraints = [row for row in plan.get("_unused", [])] if False else (opportunity.get("constraints") if isinstance(opportunity.get("constraints"), list) else [])
    constraint_ids = {_text(row.get("constraint_id")) for row in opportunity_constraints if isinstance(row, Mapping)}
    constraint_ids.discard(None)
    hard_gate_ids = set(_refs(opportunity.get("hard_gates")))
    status_from_claims = _claim_statuses(plan)
    program_ids = []
    program_requirement_ids: set[str] = set()
    all_atoms: list[dict[str, Any]] = []
    program_rows: list[dict[str, Any]] = []
    for program in programs:
        program_id = _text(program.get("program_id"))
        if not program_id:
            errors.append("program_id_missing")
            continue
        program_ids.append(program_id)
        reqs = set(_refs(program.get("requirement_ids")))
        missing = set(_refs(program.get("missing_requirement_ids")))
        program_requirement_ids.update(reqs)
        foreign = sorted(reqs - constraint_ids)
        if foreign:
            errors.append("program_requirement_not_in_opportunity:" + ",".join(foreign))
        source_status = _text(program.get("source_gate_status")) or "abstain"
        hard_status = _text(program.get("hard_gate_status")) or "abstain"
        ready = program.get("ready") is True
        program_rows.append({"program_id": program_id, "selection": program.get("selection"), "rank": program.get("rank"), "unit_ids": _refs(program.get("unit_ids")), "evidence_refs": _refs(program.get("evidence_refs")), "requirement_ids": sorted(reqs), "missing_requirement_ids": sorted(missing), "risk_flags": _refs(program.get("risk_flags")), "source_gate_status": source_status, "hard_gate_status": hard_status, "ready": ready})
        all_atoms.extend(_atom_rows({"content_atoms": program.get("content_atoms", [])}, program))
    program_rows.sort(key=lambda row: (row["rank"] if isinstance(row["rank"], int) else 10**9, row["program_id"]))
    source_status, source_reason = _source_gate(opportunity, plan)
    target = _mapping(plan.get("targets"))
    application_target = _mapping(target.get("application_draft"))
    research_target = _mapping(target.get("research_brief"))
    target_status = _text(application_target.get("status")) or "blocked"
    requirements = []
    for raw in sorted((row for row in opportunity_constraints if isinstance(row, Mapping)), key=lambda row: _text(row.get("constraint_id")) or ""):
        requirement_id = _text(raw.get("constraint_id"))
        if not requirement_id:
            errors.append("constraint_id_missing")
            continue
        statuses = []
        bound_programs = []
        for program in programs:
            reqs = set(_refs(program.get("requirement_ids")))
            missing = set(_refs(program.get("missing_requirement_ids")))
            if requirement_id in missing: statuses.append("missing")
            elif requirement_id in reqs: statuses.append(status_from_claims.get(requirement_id, "supported"))
            if requirement_id in reqs or requirement_id in missing: bound_programs.append(_text(program.get("program_id")))
        status = "contradicted" if "contradicted" in statuses else "supported" if "supported" in statuses else "missing" if "missing" in statuses else status_from_claims.get(requirement_id, "unresolved")
        requirements.append({"requirement_id": requirement_id, "kind": raw.get("kind"), "hard_gate": requirement_id in hard_gate_ids, "required": raw.get("required") is True, "status": status if status in _STATUSES else "unresolved", "program_ids": sorted(p for p in bound_programs if p), "unit_ids": sorted({u for p in programs if requirement_id in _refs(p.get("requirement_ids")) for u in _refs(p.get("unit_ids"))}), "evidence_refs": sorted({ref for p in programs if requirement_id in _refs(p.get("requirement_ids")) for ref in _refs(p.get("evidence_refs"))})})
    missing_required = [row for row in requirements if row["required"] and row["status"] != "supported"]
    contradicted = [row for row in requirements if row["status"] == "contradicted"]
    jobs_raw = plan.get("research_jobs", [])
    research_jobs, rejected_jobs = [], []
    technical_prefix = f"source-validity:{opportunity_id}"
    for job in jobs_raw if isinstance(jobs_raw, list) else []:
        if not isinstance(job, Mapping) or not _text(job.get("job_id")):
            rejected_jobs.append({"reason": "job_id_missing"})
            continue
        req_ids = _refs(job.get("requirement_ids"))
        if not req_ids and _text(job.get("requirement_id")):
            req_ids = [_text(job["requirement_id"])]
        invalid = [req for req in req_ids if req not in constraint_ids and req != technical_prefix]
        if invalid or not req_ids:
            rejected_jobs.append({"job_id": job.get("job_id"), "requirement_ids": req_ids, "reason": "job_requirement_not_in_plan_or_opportunity"})
            continue
        for req_id in req_ids:
            research_jobs.append({"job_id": _text(job["job_id"]), "requirement_id": req_id, "question": job.get("question"), "domain": job.get("domain"), "priority_rank": job.get("priority_rank"), "voi": job.get("voi"), "source_policy": job.get("source_policy"), "source_groups": job.get("independent_source_groups", job.get("source_groups", [])), "closure_criteria": job.get("closure_criteria", []), "status": job.get("status", "planned_not_dispatched"), "dispatch": False})
    research_jobs.sort(key=lambda row: (row["priority_rank"] if isinstance(row["priority_rank"], int) else 10**9, row["job_id"], row["requirement_id"]))
    reasons = []
    if target_status != "draftable": reasons.append(f"target_application_status:{target_status}")
    if source_status != "pass": reasons.append(source_reason)
    if any(row["source_gate_status"] != "pass" or row["hard_gate_status"] != "pass" or not row["ready"] for row in program_rows): reasons.append("selected_program_gate_not_ready")
    if missing_required: reasons.append("required_requirements_missing_or_unresolved")
    if contradicted: reasons.append("requirements_contradicted")
    reasons.extend(errors)
    app_status = "draftable" if not reasons else "blocked_with_reasons"
    research_status = _text(research_target.get("status")) or ("not_required" if not research_jobs else "draftable")
    if research_status == "not_required": research_jobs = []
    return {"schema": PACKAGE_SCHEMA, "input_hashes": {"product_plan": _stable_hash(plan), "opportunity_constraints": _stable_hash(opportunity)}, "application_draft": {"status": app_status, "blocked_with_reasons": sorted(set(reasons)), "program_ids": program_ids, "opportunity_id": opportunity_id, "programs": program_rows, "requirements": requirements, "sections": sorted(all_atoms, key=lambda row: (row["section"], row["atom_id"])), "submission_ready": False, "submission": False}, "research_brief": {"status": research_status, "jobs": research_jobs, "rejected_jobs": sorted(rejected_jobs, key=lambda row: json.dumps(row, sort_keys=True)), "gaps": [{"requirement_id": row["requirement_id"], "status": row["status"], "closure_criteria": next((job["closure_criteria"] for job in research_jobs if job["requirement_id"] == row["requirement_id"]), [])} for row in missing_required], "dispatch": False}, "controls": {"submission": False, "dispatch": False, "promotion": "none", "training_permitted": False, "user_review_required": False}, "provenance": {"source_schemas": [PLAN_SCHEMA, OPPORTUNITY_SCHEMA], "source_gate_status": source_status, "hard_gate_status": "pass" if all(row["hard_gate_status"] == "pass" for row in program_rows) else "abstain", "deterministic": True, "errors": sorted(set(errors))}}


def _empty(errors: list[str]) -> dict[str, Any]:
    return {"schema": PACKAGE_SCHEMA, "application_draft": {"status": "blocked_with_reasons", "blocked_with_reasons": sorted(set(errors)), "submission_ready": False, "submission": False, "requirements": [], "sections": []}, "research_brief": {"jobs": [], "rejected_jobs": [], "gaps": [], "frontier": [], "dispatch": False}, "controls": {"submission": False, "dispatch": False, "promotion": "none", "training_permitted": False, "user_review_required": False}, "provenance": {"source_schemas": [PLAN_SCHEMA, OPPORTUNITY_SCHEMA], "errors": sorted(set(errors)), "deterministic": True}}
