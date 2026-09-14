"""Deterministic link between opportunity constraints and practice evidence.

This module only constructs a link and research candidates. It does not decide
success, promote facts, or dispatch jobs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from ._contract_helpers import nullable_text as _text
from ._io_helpers import load_json_file as load_json


OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
PRACTICE_SCHEMA = "mak-practice-evidence-state-v1"
FIT_SCHEMA = "mak-opportunity-fit-v1"

_STATUSES = {"supported", "missing", "contradicted", "unresolved"}
_POSITIVE = {"supported", "verified", "observed"}
_UNKNOWN = {"unknown", "unresolved", "candidate", "missing", "pending"}
_DIMENSIONS = ("media", "capabilities", "temporality", "manifestations", "resources")


def _error_result(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": FIT_SCHEMA,
        "decision": "abstain",
        "validation": {"valid": False, "errors": sorted(set(errors))},
        "matrix": [],
        "hard_gate_status": "abstain",
        "weighted_coverage": None,
        "weighted_coverage_numerator": None,
        "weighted_coverage_denominator": None,
        "coverage_reason": "validation_error",
        "allowed_claims": [],
        "required_but_unsupported": [],
        "research_job_candidates": [],
        "practice_identity": None,
    }


def _number(value: Any, *, minimum: float = 0.0) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) and value >= minimum else None


def _as_refs(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return sorted({item for item in value if isinstance(item, str) and item})
    return []


def _normalise_inputs(opportunity: Mapping[str, Any], practice: Mapping[str, Any]):
    errors: list[str] = []
    if opportunity.get("schema") != OPPORTUNITY_SCHEMA:
        errors.append("opportunity_schema_invalid")
    if practice.get("schema") != PRACTICE_SCHEMA:
        errors.append("practice_schema_invalid")
    if not _text(opportunity.get("opportunity_id")):
        errors.append("opportunity_id_missing")
    for key in ("tenant", "archive_id", "snapshot_id"):
        if not _text(practice.get(key)):
            errors.append(f"practice_{key}_missing")
    if not isinstance(practice.get("claims"), Mapping):
        errors.append("practice_claims_missing_or_invalid")
    for dimension in _DIMENSIONS:
        if not isinstance(practice.get(dimension), list):
            errors.append(f"practice_{dimension}_missing_or_invalid")

    criteria = opportunity.get("criteria")
    criteria_rows = criteria if isinstance(criteria, list) else []
    criteria_by_field: dict[str, list[Mapping[str, Any]]] = {}
    criteria_by_id: dict[str, Mapping[str, Any]] = {}
    for row in criteria_rows:
        if isinstance(row, Mapping):
            field = _text(row.get("field"))
            criterion_id = _text(row.get("criterion_id"))
            if field:
                criteria_by_field.setdefault(field, []).append(row)
            if criterion_id:
                criteria_by_id[criterion_id] = row
    hard_gates = set(_as_refs(opportunity.get("hard_gates")))
    raw_constraints = opportunity.get("constraints")
    if not isinstance(raw_constraints, list) or not raw_constraints:
        errors.append("constraints_missing_or_empty")
        raw_constraints = []
    constraints: list[dict[str, Any]] = []
    seen_requirements: set[str] = set()
    for index, raw in enumerate(raw_constraints):
        if not isinstance(raw, Mapping):
            errors.append(f"constraint_{index}_not_object")
            continue
        requirement_id = _text(raw.get("constraint_id"))
        field = _text(raw.get("field"))
        kind = _text(raw.get("kind"))
        label = field or kind or requirement_id
        required = raw.get("required")
        hard_gate = requirement_id in hard_gates
        mapped_criteria = list(criteria_by_field.get(field or "", []))
        direct_criterion = criteria_by_id.get(requirement_id)
        if direct_criterion is not None and direct_criterion not in mapped_criteria:
            mapped_criteria.append(direct_criterion)
        weight = _number(mapped_criteria[0].get("weight")) if len(mapped_criteria) == 1 else None
        if not requirement_id:
            errors.append(f"constraint_{index}_requirement_id_missing")
            continue
        if requirement_id in seen_requirements:
            errors.append(f"constraint_duplicate:{requirement_id}")
        seen_requirements.add(requirement_id)
        if not field:
            errors.append(f"constraint_{requirement_id}_field_missing")
        if not kind:
            errors.append(f"constraint_{requirement_id}_kind_missing")
        if not isinstance(required, bool):
            errors.append(f"constraint_{requirement_id}_required_missing")
        if not isinstance(hard_gate, bool):
            errors.append(f"constraint_{requirement_id}_hard_gate_invalid")
        constraints.append(
            {
                "requirement_id": requirement_id,
                "label": label or requirement_id,
                "field": field or requirement_id,
                "kind": kind or "unknown",
                "required": required is True,
                "hard_gate": hard_gate,
                "weight": weight,
                "evidence_refs": _as_refs(raw.get("evidence_refs")),
                "research_questions": _as_refs(raw.get("research_questions")),
                "research": raw.get("research") if isinstance(raw.get("research"), Mapping) else {},
                "opportunity_status": _text(raw.get("status")) or "unknown",
                "criteria_mapping": [
                    _text(item.get("criterion_id")) or _text(item.get("field")) or "unknown"
                    for item in mapped_criteria
                ],
            }
        )

    # The accepted Stage 1B contract has no ``practice_id`` or ``evidence``
    # array. Evidence is projected only from claims and the five dimensions;
    # artifact rows by themselves are deliberately not projected.
    raw_evidence: list[Mapping[str, Any]] = []
    claims = practice.get("claims", {})
    for claim_status, rows in claims.items() if isinstance(claims, Mapping) else []:
        if not isinstance(rows, list):
            errors.append(f"practice_claims_{claim_status}_not_list")
            continue
        for row in rows:
            if isinstance(row, Mapping):
                raw_evidence.append({**row, "kind": "claim", "status": row.get("status", claim_status)})
    for dimension in _DIMENSIONS:
        for row in practice.get(dimension, []) if isinstance(practice.get(dimension), list) else []:
            if isinstance(row, Mapping):
                raw_evidence.append({**row, "kind": dimension})
    evidence: dict[str, dict[str, Any]] = {}
    explicit_evidence_ids: set[str] = set()
    for index, raw in enumerate(raw_evidence):
        if not isinstance(raw, Mapping):
            errors.append(f"evidence_{index}_not_object")
            continue
        refs = _as_refs(raw.get("evidence_refs"))
        explicit_evidence_id = _text(raw.get("evidence_id")) or _text(raw.get("id"))
        evidence_id = explicit_evidence_id or (
            refs[0] if refs else f"{raw.get('kind', 'evidence')}:{index}"
        )
        if not evidence_id:
            errors.append(f"evidence_{index}_id_missing")
            continue
        if explicit_evidence_id and explicit_evidence_id in explicit_evidence_ids:
            errors.append(f"evidence_duplicate:{evidence_id}")
        if explicit_evidence_id:
            explicit_evidence_ids.add(explicit_evidence_id)
        normalized = {
            "evidence_id": evidence_id,
            "status": _text(raw.get("status")) or _text(raw.get("claim_status")) or "unknown",
            "evidence_refs": refs,
            "requirement_ids": _as_refs(raw.get("requirement_ids")) or _as_refs(raw.get("supports")),
            "source_ref": _text(raw.get("provenance_ref")) or _text(raw.get("source_ref")),
            "kind": _text(raw.get("kind")) or _text(raw.get("evidence_type")) or "unknown",
            "similarity_only": False,
        }
        # Keep every declared evidence reference addressable. A claim or
        # dimension row may cite several refs and must retain its provenance.
        for ref in refs or [evidence_id]:
            prior = evidence.get(ref)
            if prior is None:
                evidence[ref] = {**normalized, "evidence_id": ref}
            else:
                statuses = {prior["status"], normalized["status"]}
                merged_status = "contradicted" if "contradicted" in statuses else (
                    "supported" if statuses & _POSITIVE else "candidate" if "candidate" in statuses else "unknown"
                )
                evidence[ref] = {
                    **prior,
                    "status": merged_status,
                    "evidence_refs": sorted(set(prior["evidence_refs"] + refs)),
                    "source_ref": prior["source_ref"] or normalized["source_ref"],
                    "kind": prior["kind"],
                }
    identity = ":".join(str(practice[key]).strip() for key in ("tenant", "archive_id", "snapshot_id"))
    contradiction_rows = opportunity.get("contradictions") if isinstance(opportunity.get("contradictions"), list) else []
    contradiction_ids = {
        _text(row.get("constraint_id")) for row in contradiction_rows if isinstance(row, Mapping)
    }
    contradiction_ids.discard(None)
    hard_gate_ids = {row["requirement_id"] for row in constraints if row["hard_gate"]}
    hard_contradiction = bool(contradiction_ids & hard_gate_ids) or any(
        row["hard_gate"] and row["opportunity_status"] == "contradicted" for row in constraints
    )
    any_contradiction = bool(contradiction_ids) or any(
        row["opportunity_status"] == "contradicted" for row in constraints
    )
    source = opportunity.get("source")
    validity = source.get("validity") if isinstance(source, Mapping) else None
    source_status = _text(validity.get("status")) if isinstance(validity, Mapping) else None
    source_confirmed = validity.get("confirmed") is True if isinstance(validity, Mapping) else False
    if source_status == "current_verified" and source_confirmed:
        source_gate_status, source_gate_reason = "pass", "source_current_verified_and_confirmed"
    elif source_status in {"expired", "ineligible"}:
        source_gate_status, source_gate_reason = "fail", f"source_validity_{source_status}"
    else:
        source_gate_status, source_gate_reason = "abstain", "source_validity_not_current_verified_or_unconfirmed"
    reconciliation = opportunity.get("reconciliation")
    declared_criteria_status = reconciliation.get("criteria_weight_status") if isinstance(reconciliation, Mapping) else None
    if declared_criteria_status is None:
        if not criteria_rows or any(_number(row.get("weight")) is None for row in criteria_rows if isinstance(row, Mapping)):
            declared_criteria_status = "incomplete_weights"
        elif not all(isinstance(row, Mapping) for row in criteria_rows):
            declared_criteria_status = "incomplete_weights"
        else:
            total = sum(float(row["weight"]) for row in criteria_rows)
            declared_criteria_status = "complete" if math.isclose(total, 1.0, abs_tol=1e-9) else "incomplete_weights"
    return constraints, evidence, sorted(set(errors)), f"practice:{identity}", hard_contradiction, any_contradiction, declared_criteria_status, source_gate_status, source_gate_reason


def _cell_status(requirement: Mapping[str, Any], evidence_id: str, evidence: Mapping[str, Any] | None) -> tuple[str, str]:
    if evidence is None:
        return "missing", "evidence_ref_not_found"
    if evidence["similarity_only"]:
        return "unresolved", "similarity_is_not_evidence"
    status = str(evidence["status"]).lower()
    if status == "contradicted":
        return "contradicted", "explicit_contradiction"
    if status in _POSITIVE and evidence["source_ref"]:
        return "supported", "explicit_provenance"
    if status in _POSITIVE:
        return "unresolved", "positive_status_without_provenance"
    if status in _UNKNOWN:
        return "unresolved", "unknown_is_not_negative"
    return "unresolved", "unsupported_evidence_status"


def _aggregate(cells: list[dict[str, Any]]) -> str:
    statuses = {cell["status"] for cell in cells}
    if "contradicted" in statuses:
        return "contradicted"
    if "supported" in statuses:
        return "supported"
    if "unresolved" in statuses:
        return "unresolved"
    return "missing"


def _candidate(constraint: Mapping[str, Any], opportunity_id: str, ordinal: int) -> dict[str, Any]:
    research = dict(constraint.get("research", {}))
    questions = list(constraint.get("research_questions", []))
    question = questions[0] if questions else f"Verificar: {constraint['label']}"
    resolution = _number(research.get("resolution_probability"), minimum=0.0)
    utility = _number(research.get("utility_delta"), minimum=0.0)
    risk = _number(research.get("risk_avoided"), minimum=0.0)
    cost = _number(research.get("cost"), minimum=0.0)
    time = _number(research.get("time"), minimum=0.0)
    resolution = 0.5 if resolution is None else min(1.0, resolution)
    utility = 1.0 if utility is None else utility
    risk = 0.0 if risk is None else risk
    cost = 1.0 if cost is None else cost
    time = 1.0 if time is None else time
    numerator = resolution * utility + risk
    denominator = cost + time
    if denominator == 0:
        voi = None
        voi_status = "undefined_zero_cost"
    else:
        voi = numerator / denominator
        voi_status = "defined"
    return {
        "candidate_id": f"research:{opportunity_id}:{constraint['requirement_id']}:{ordinal}",
        "requirement_id": constraint["requirement_id"],
        "question": question,
        "domain": research.get("domain", "general"),
        "status": "planned_not_dispatched",
        "dispatched": False,
        "resolution_probability": resolution,
        "utility_delta": utility,
        "risk_avoided": risk,
        "cost": cost,
        "time": time,
        "voi_numerator": numerator,
        "voi_denominator": denominator,
        "voi": voi,
        "voi_status": voi_status,
    }


def evaluate_opportunity_fit(opportunity: Mapping[str, Any], practice: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate two contracts and abstain structurally when essentials are missing."""
    if not isinstance(opportunity, Mapping) or not isinstance(practice, Mapping):
        return _error_result(["inputs_must_be_objects"])
    constraints, evidence, errors, practice_identity, hard_contradiction, any_contradiction, criteria_status, source_gate_status, source_gate_reason = _normalise_inputs(opportunity, practice)
    result = _error_result(errors) if errors else {
        "schema": FIT_SCHEMA,
        "decision": "abstain",
        "validation": {"valid": True, "errors": []},
        "matrix": [],
        "hard_gate_status": "abstain",
        "weighted_coverage": None,
        "weighted_coverage_numerator": None,
        "weighted_coverage_denominator": None,
        "allowed_claims": [],
        "required_but_unsupported": [],
        "research_job_candidates": [],
        "coverage_reason": None,
        "source_gate_status": source_gate_status,
        "source_gate_reason": source_gate_reason,
    }
    matrix: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    supported_weight = 0.0
    total_weight = 0.0
    for ordinal, constraint in enumerate(constraints):
        # Opportunity evidence_refs are documentary refs proving that the
        # requirement exists in the call. They are never applicant evidence.
        # Only an explicit internal requirement_ids/supports relation can
        # connect practice evidence to this constraint.
        refs = sorted(
            eid for eid, item in evidence.items()
            if constraint["requirement_id"] in item["requirement_ids"]
        )
        cells = []
        for ref in refs:
            status, reason = _cell_status(constraint, ref, evidence.get(ref))
            cells.append({"evidence_ref": ref, "status": status, "reason": reason})
            if status == "missing":
                errors.append(f"evidence_ref_not_found:{ref}")
        status = _aggregate(cells)
        matrix.append({
            "requirement_id": constraint["requirement_id"],
            "label": constraint["label"],
            "required": constraint["required"],
            "hard_gate": constraint["hard_gate"],
            "weight": constraint["weight"],
            "status": status,
            "cells": cells,
            "opportunity_status": constraint["opportunity_status"],
            "criteria_mapping": constraint["criteria_mapping"],
        })
        if constraint["kind"] == "criterion" and constraint["weight"] is not None:
            total_weight += constraint["weight"]
            if status == "supported":
                supported_weight += constraint["weight"]
        if status == "supported":
            supported_refs = [cell["evidence_ref"] for cell in cells if cell["status"] == "supported"]
            claims.append({"requirement_id": constraint["requirement_id"], "claim": constraint["label"], "evidence_refs": supported_refs})
        if constraint["required"] and status != "supported":
            unsupported.append({"requirement_id": constraint["requirement_id"], "label": constraint["label"], "status": status, "hard_gate": constraint["hard_gate"]})
            if status in {"missing", "unresolved"}:
                candidates.append(_candidate(constraint, str(opportunity.get("opportunity_id", "unknown")), ordinal))

    scored_constraints = [row for row in constraints if row["kind"] == "criterion"]
    unmapped = [row["requirement_id"] for row in scored_constraints if row["weight"] is None]
    if errors:
        result["coverage_reason"] = "input_validation_error"
    elif criteria_status != "complete":
        result["coverage_reason"] = f"criteria_weight_status:{criteria_status}"
    elif unmapped:
        result["coverage_reason"] = "criterion_mapping_incomplete_or_ambiguous:" + ",".join(sorted(unmapped))
    elif not scored_constraints:
        result["coverage_reason"] = "no_scored_criteria"
    elif total_weight > 0:
        result["weighted_coverage"] = supported_weight / total_weight
        result["weighted_coverage_numerator"] = supported_weight
        result["weighted_coverage_denominator"] = total_weight
        result["coverage_reason"] = "criteria_complete_and_unambiguous"
    hard_rows = [row for row in matrix if row["hard_gate"]]
    if hard_contradiction:
        result["hard_gate_status"] = "fail"
    elif errors or any(row["status"] in {"missing", "unresolved"} for row in hard_rows):
        result["hard_gate_status"] = "abstain"
    elif any(row["status"] == "contradicted" for row in hard_rows):
        result["hard_gate_status"] = "fail"
    else:
        result["hard_gate_status"] = "pass"
    if source_gate_status == "fail":
        result["decision"] = "contradicted"
    elif source_gate_status != "pass":
        result["decision"] = "abstain"
    elif any_contradiction or any(row["status"] == "contradicted" and row["required"] for row in matrix):
        result["decision"] = "contradicted"
    elif errors or unsupported:
        result["decision"] = "abstain"
    else:
        result["decision"] = "supported"
    result["validation"] = {"valid": not errors, "errors": sorted(set(errors))}
    result["practice_identity"] = practice_identity
    result["matrix"] = matrix
    result["allowed_claims"] = claims
    result["required_but_unsupported"] = unsupported
    candidates.sort(key=lambda item: (item["voi"] is not None, item["voi"] if item["voi"] is not None else item["voi_numerator"]), reverse=True)
    result["research_job_candidates"] = candidates
    return result
