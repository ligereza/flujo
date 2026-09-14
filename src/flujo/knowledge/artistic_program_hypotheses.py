"""Generate deterministic, evidence-bounded artistic-program hypotheses.

This is a possibility field, not a product compiler and not a narrative
generator.  It consumes the accepted opportunity constraints, practice
evidence state and opportunity fit contracts.  It preserves explicit
requirement bindings, fit abstentions, hard/source gates and physical
evidence namespaces without inventing titles, concepts, intention, authorship
or eligibility.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import stable_json

from .opportunity_constraints import (
    OpportunityConstraintsError,
    validate_opportunity_constraints,
)
from .opportunity_fit import FIT_SCHEMA
from .practice_evidence_state import (
    SCHEMA as PRACTICE_SCHEMA,
    validate_practice_evidence_state,
)


SCHEMA = "mak-artistic-program-candidates-v1"
OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
ALGORITHM_VERSION = "artistic-program-hypotheses-1"

_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "practice_identity",
    "input_hashes", "fit_summary", "abstentions", "candidates",
    "provenance", "reconciliation",
}
_CANDIDATE_FIELDS = {
    "program_id", "basis", "status", "unit_ids", "requirement_ids",
    "supported_claim_ids", "candidate_claim_ids", "evidence_refs",
    "counterevidence_refs", "missing_requirement_ids", "research_action_ids",
    "resource_refs", "alternatives", "generation_reasons", "risk_flags",
    "provenance",
}
_FIT_DECISIONS = {"abstain", "supported", "contradicted"}
_FIT_STATUSES = {"missing", "unresolved", "supported", "contradicted"}
_GATE_STATUSES = {"abstain", "pass", "fail"}
_BASIS_VALUES = {"practice_native", "opportunity_conditioned"}
_CANDIDATE_STATUSES = {"candidate", "unknown"}
_HASH_PREFIX = "sha256:"


class ArtisticProgramHypothesesError(ValueError):
    """Invalid accepted input or invalid deterministic hypothesis payload."""


def _hash(value: Any) -> str:
    return _HASH_PREFIX + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ArtisticProgramHypothesesError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ArtisticProgramHypothesesError(f"{field}_required")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtisticProgramHypothesesError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArtisticProgramHypothesesError(f"{field}_must_be_list")
    return value


def _refs(value: Any, field: str, *, sorted_unique: bool = False) -> list[str]:
    rows = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise ArtisticProgramHypothesesError(f"{field}_invalid")
    result = sorted(set(rows))
    if sorted_unique and rows != result:
        raise ArtisticProgramHypothesesError(f"{field}_not_sorted_unique")
    return result


def _source_hash(value: Any, field: str) -> str:
    result = _text(value, field)
    if not result.startswith(_HASH_PREFIX) or len(result) != 71:
        raise ArtisticProgramHypothesesError(f"{field}_invalid_hash")
    try:
        int(result[len(_HASH_PREFIX):], 16)
    except ValueError as exc:
        raise ArtisticProgramHypothesesError(f"{field}_invalid_hash") from exc
    return result


def _validate_fit(fit: Mapping[str, Any]) -> None:
    if fit.get("schema") != FIT_SCHEMA:
        raise ArtisticProgramHypothesesError("fit_schema_invalid")
    validation = _mapping(fit.get("validation"), "fit.validation")
    if not isinstance(validation.get("valid"), bool):
        raise ArtisticProgramHypothesesError("fit.validation.valid_invalid")
    errors = _refs(validation.get("errors", []), "fit.validation.errors")
    if errors != sorted(errors):
        raise ArtisticProgramHypothesesError("fit.validation.errors_not_sorted")
    if fit.get("decision") not in _FIT_DECISIONS:
        raise ArtisticProgramHypothesesError("fit_decision_invalid")
    for field in (
        "matrix", "allowed_claims", "required_but_unsupported",
        "research_job_candidates",
    ):
        _list(fit.get(field), f"fit.{field}")
    if fit.get("hard_gate_status", "abstain") not in _GATE_STATUSES:
        raise ArtisticProgramHypothesesError("fit_hard_gate_status_invalid")
    if fit.get("source_gate_status", "abstain") not in _GATE_STATUSES:
        raise ArtisticProgramHypothesesError("fit_source_gate_status_invalid")
    matrix_ids: list[str] = []
    for index, raw in enumerate(fit["matrix"]):
        row = _mapping(raw, f"fit.matrix[{index}]")
        requirement_id = _text(row.get("requirement_id"), f"fit.matrix[{index}].requirement_id")
        matrix_ids.append(requirement_id)
        if row.get("status") not in _FIT_STATUSES:
            raise ArtisticProgramHypothesesError(f"fit.matrix[{index}].status_invalid")
        if not isinstance(row.get("required"), bool) or not isinstance(row.get("hard_gate"), bool):
            raise ArtisticProgramHypothesesError(f"fit.matrix[{index}].gate_flags_invalid")
        cells = _list(row.get("cells", []), f"fit.matrix[{index}].cells")
        for cell_index, raw_cell in enumerate(cells):
            cell = _mapping(raw_cell, f"fit.matrix[{index}].cells[{cell_index}]")
            _text(cell.get("evidence_ref"), f"fit.matrix[{index}].cells[{cell_index}].evidence_ref")
            if cell.get("status") not in _FIT_STATUSES:
                raise ArtisticProgramHypothesesError("fit_cell_status_invalid")
    if len(matrix_ids) != len(set(matrix_ids)):
        raise ArtisticProgramHypothesesError("fit_matrix_requirement_ids_duplicate")
    for index, raw in enumerate(fit["required_but_unsupported"]):
        row = _mapping(raw, f"fit.required_but_unsupported[{index}]")
        _text(row.get("requirement_id"), "fit.required_requirement_id")
        if row.get("status") not in _FIT_STATUSES:
            raise ArtisticProgramHypothesesError("fit_required_status_invalid")
        if not isinstance(row.get("hard_gate"), bool):
            raise ArtisticProgramHypothesesError("fit_required_hard_gate_invalid")
    action_ids: list[str] = []
    for index, raw in enumerate(fit["research_job_candidates"]):
        row = _mapping(raw, f"fit.research_job_candidates[{index}]")
        action_ids.append(_text(row.get("candidate_id"), "fit.research_candidate_id"))
        _text(row.get("requirement_id"), "fit.research_requirement_id")
    if len(action_ids) != len(set(action_ids)):
        raise ArtisticProgramHypothesesError("fit_research_action_ids_duplicate")


def _canonical_fit(fit: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize order-only differences before hashing or consumption."""
    result = copy.deepcopy(dict(fit))
    result["validation"] = dict(result.get("validation", {}))
    result["validation"]["errors"] = sorted(result["validation"].get("errors", []))
    result["matrix"] = sorted(
        (dict(row) for row in result.get("matrix", [])),
        key=lambda row: row.get("requirement_id", ""),
    )
    for row in result["matrix"]:
        row["cells"] = sorted(row.get("cells", []), key=lambda cell: cell.get("evidence_ref", ""))
    result["allowed_claims"] = sorted(
        result.get("allowed_claims", []),
        key=lambda row: (row.get("requirement_id", ""), stable_json(row)),
    )
    result["required_but_unsupported"] = sorted(
        result.get("required_but_unsupported", []),
        key=lambda row: row.get("requirement_id", ""),
    )
    result["research_job_candidates"] = sorted(
        result.get("research_job_candidates", []),
        key=lambda row: row.get("candidate_id", ""),
    )
    return result


def _fit_summary(fit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision": fit["decision"],
        "validation": copy.deepcopy(dict(fit["validation"])),
        "hard_gate_status": fit.get("hard_gate_status", "abstain"),
        "source_gate_status": fit.get("source_gate_status", "abstain"),
        "source_gate_reason": fit.get("source_gate_reason", "fit_source_gate_not_declared"),
        "coverage_reason": fit.get("coverage_reason"),
    }


def _practice_index(practice: Mapping[str, Any]) -> dict[str, Any]:
    units = sorted(
        (_mapping(row, "practice.units") for row in practice["units"]),
        key=lambda row: _text(row.get("unit_id"), "practice.unit_id"),
    )
    unit_ids = [_text(row.get("unit_id"), "practice.unit_id") for row in units]
    if len(unit_ids) != len(set(unit_ids)):
        raise ArtisticProgramHypothesesError("practice_unit_ids_duplicate")
    unit_by_id = {row["unit_id"]: row for row in units}
    claims_by_id: dict[str, dict[str, Any]] = {}
    claims_by_unit: dict[str, list[dict[str, Any]]] = {unit_id: [] for unit_id in unit_ids}
    all_claims: list[dict[str, Any]] = []
    claims = _mapping(practice["claims"], "practice.claims")
    for status in ("supported", "candidate", "unknown"):
        for raw in _list(claims.get(status), f"practice.claims.{status}"):
            row = dict(_mapping(raw, f"practice.claims.{status}"))
            claim_id = _text(row.get("claim_id"), "practice.claim_id")
            if claim_id in claims_by_id:
                raise ArtisticProgramHypothesesError("practice_claim_id_collision")
            if row.get("status") != status:
                raise ArtisticProgramHypothesesError("practice_claim_status_mismatch")
            refs = _refs(row.get("evidence_refs", []), "practice.claim.evidence_refs")
            requirement_ids = _refs(row.get("requirement_ids", []), "practice.claim.requirement_ids")
            unit_id = _text(row.get("unit_id"), "practice.claim.unit_id", required=False)
            row["evidence_refs"] = refs
            row["requirement_ids"] = requirement_ids
            row["unit_id"] = unit_id
            claims_by_id[claim_id] = row
            all_claims.append(row)
            if unit_id in claims_by_unit:
                claims_by_unit[unit_id].append(row)

    dimension_rows: list[dict[str, Any]] = []
    rows_by_unit: dict[str, list[dict[str, Any]]] = {unit_id: [] for unit_id in unit_ids}
    resources_by_unit: dict[str, set[str]] = {unit_id: set() for unit_id in unit_ids}
    practice_refs: set[str] = set()
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        for raw in _list(practice.get(dimension), f"practice.{dimension}"):
            row = dict(_mapping(raw, f"practice.{dimension}"))
            unit_id = _text(row.get("unit_id"), f"practice.{dimension}.unit_id")
            if unit_id not in unit_by_id:
                raise ArtisticProgramHypothesesError("practice_dimension_unit_unresolved")
            refs = _refs(row.get("evidence_refs", []), f"practice.{dimension}.evidence_refs")
            requirement_ids = _refs(row.get("requirement_ids", []), f"practice.{dimension}.requirement_ids")
            row["dimension"] = dimension
            row["evidence_refs"] = refs
            row["requirement_ids"] = requirement_ids
            dimension_rows.append(row)
            rows_by_unit[unit_id].append(row)
            practice_refs.update(refs)
            if dimension == "resources":
                resources_by_unit[unit_id].update(refs)
    for row in all_claims:
        practice_refs.update(row["evidence_refs"])
    bindings_by_unit: dict[str, set[str]] = {unit_id: set() for unit_id in unit_ids}
    for unit_id, rows in claims_by_unit.items():
        for row in rows:
            bindings_by_unit[unit_id].update(row["requirement_ids"])
    for row in dimension_rows:
        bindings_by_unit[row["unit_id"]].update(row["requirement_ids"])
    return {
        "units": units,
        "unit_by_id": unit_by_id,
        "unit_ids": unit_ids,
        "claims_by_id": claims_by_id,
        "claims_by_unit": claims_by_unit,
        "rows_by_unit": rows_by_unit,
        "resources_by_unit": resources_by_unit,
        "bindings_by_unit": bindings_by_unit,
        "practice_refs": practice_refs,
    }


def _opportunity_index(opportunity: Mapping[str, Any]) -> dict[str, Any]:
    constraints = sorted(
        (_mapping(row, "opportunity.constraints") for row in opportunity["constraints"]),
        key=lambda row: _text(row.get("constraint_id"), "opportunity.constraint_id"),
    )
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in constraints:
        requirement_id = _text(row.get("constraint_id"), "opportunity.constraint_id")
        if requirement_id in by_id:
            raise ArtisticProgramHypothesesError("opportunity_requirement_id_collision")
        by_id[requirement_id] = row
    documentary_refs: set[str] = set()
    for row in constraints:
        documentary_refs.update(_refs(row.get("evidence_refs", []), "opportunity.constraint.evidence_refs"))
    for raw in _list(opportunity.get("evidence"), "opportunity.evidence"):
        evidence = _mapping(raw, "opportunity.evidence")
        documentary_refs.add(_text(evidence.get("evidence_id"), "opportunity.evidence_id"))
    return {
        "constraints": constraints,
        "by_id": by_id,
        "requirement_ids": set(by_id),
        "hard_gates": set(_refs(opportunity.get("hard_gates"), "opportunity.hard_gates")),
        "documentary_refs": documentary_refs,
    }


def _fit_index(fit: Mapping[str, Any]) -> dict[str, Any]:
    matrix = {row["requirement_id"]: row for row in fit["matrix"]}
    actions = {row["candidate_id"]: row for row in fit["research_job_candidates"]}
    action_by_requirement: dict[str, set[str]] = {}
    for action_id, row in actions.items():
        action_by_requirement.setdefault(row["requirement_id"], set()).add(action_id)
    contradicted_refs: set[str] = set()
    for row in fit["matrix"]:
        contradicted_refs.update(
            cell["evidence_ref"] for cell in row.get("cells", []) if cell.get("status") == "contradicted"
        )
    return {
        "matrix": matrix,
        "actions": actions,
        "action_by_requirement": action_by_requirement,
        "contradicted_refs": contradicted_refs,
    }


def _candidate_semantics(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(candidate[key])
        for key in sorted(_CANDIDATE_FIELDS - {"program_id", "provenance"})
    }


def program_id_for(candidate: Mapping[str, Any]) -> str:
    """Return a deterministic technical ID without titles or semantic prose."""
    return "program:" + hashlib.sha256(stable_json(_candidate_semantics(candidate)).encode("utf-8")).hexdigest()


def _provenance(
    opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit_hash: str,
    *, basis: str, unit_ids: list[str], requirement_ids: list[str],
) -> dict[str, Any]:
    return {
        "opportunity_schema": OPPORTUNITY_SCHEMA,
        "practice_schema": PRACTICE_SCHEMA,
        "fit_schema": FIT_SCHEMA,
        "opportunity_input_hash": opportunity["input_hash"],
        "practice_state_hash": practice["state_hash"],
        "fit_input_hash": fit_hash,
        "basis": basis,
        "unit_ids": list(unit_ids),
        "requirement_ids": list(requirement_ids),
        "source_rescan": False,
        "claims_promoted": 0,
    }


def _make_candidate(
    *, basis: str, status: str, unit_ids: list[str], requirement_ids: list[str],
    supported_claim_ids: list[str], candidate_claim_ids: list[str], evidence_refs: list[str],
    counterevidence_refs: list[str], missing_requirement_ids: list[str],
    research_action_ids: list[str], resource_refs: list[str], alternatives: list[str],
    generation_reasons: list[str], risk_flags: list[str],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = {
        "program_id": "",
        "basis": basis,
        "status": status,
        "unit_ids": sorted(set(unit_ids)),
        "requirement_ids": sorted(set(requirement_ids)),
        "supported_claim_ids": sorted(set(supported_claim_ids)),
        "candidate_claim_ids": sorted(set(candidate_claim_ids)),
        "evidence_refs": sorted(set(evidence_refs)),
        "counterevidence_refs": sorted(set(counterevidence_refs)),
        "missing_requirement_ids": sorted(set(missing_requirement_ids)),
        "research_action_ids": sorted(set(research_action_ids)),
        "resource_refs": sorted(set(resource_refs)),
        "alternatives": sorted(set(alternatives)),
        "generation_reasons": sorted(set(generation_reasons)),
        "risk_flags": sorted(set(risk_flags)),
        "provenance": copy.deepcopy(dict(provenance)),
    }
    candidate["program_id"] = program_id_for(candidate)
    return candidate


def _practice_native_candidates(
    index: Mapping[str, Any], opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    claims_by_unit = index["claims_by_unit"]
    for unit_id in index["unit_ids"]:
        unit = index["unit_by_id"][unit_id]
        claims = claims_by_unit[unit_id]
        dimensions = index["rows_by_unit"][unit_id]
        supported = [row["claim_id"] for row in claims if row["status"] == "supported" and row["evidence_refs"]]
        candidate = [row["claim_id"] for row in claims if row["status"] == "candidate" and row["evidence_refs"]]
        refs = [ref for row in claims + dimensions for ref in row["evidence_refs"]]
        reasons = ["explicit_practice_unit"]
        if supported or candidate:
            reasons.append("explicit_practice_claim")
        if dimensions:
            reasons.append("explicit_practice_dimension")
        risks: list[str] = []
        if any(row["status"] == "unknown" for row in claims):
            risks.append("practice_claim_unknown")
        if not refs:
            risks.append("practice_evidence_missing")
        if unit.get("status") == "unresolved_unit":
            risks.append("practice_unit_unresolved")
        status = "candidate" if refs and (supported or candidate or dimensions) else "unknown"
        rows.append(_make_candidate(
            basis="practice_native",
            status=status,
            unit_ids=[unit_id],
            requirement_ids=[],
            supported_claim_ids=supported,
            candidate_claim_ids=candidate,
            evidence_refs=refs,
            counterevidence_refs=[],
            missing_requirement_ids=[],
            research_action_ids=[],
            resource_refs=sorted(index["resources_by_unit"][unit_id]),
            alternatives=list(unit.get("alternatives", [])),
            generation_reasons=reasons,
            risk_flags=risks,
            provenance=_provenance(
                opportunity, practice, fit_hash,
                basis="practice_native", unit_ids=[unit_id], requirement_ids=[],
            ),
        ))
    return rows


def _conditioned_candidate(
    unit_ids: list[str], index: Mapping[str, Any], opportunity: Mapping[str, Any],
    practice: Mapping[str, Any], opportunity_index: Mapping[str, Any], fit: Mapping[str, Any], fit_index: Mapping[str, Any],
    fit_hash: str,
) -> dict[str, Any]:
    bound_ids = set()
    for unit_id in unit_ids:
        bound_ids.update(index["bindings_by_unit"].get(unit_id, set()))
    valid_bound_ids = bound_ids & opportunity_index["requirement_ids"]
    requirement_ids = valid_bound_ids | opportunity_index["hard_gates"]
    if not requirement_ids:
        requirement_ids = {
            row["constraint_id"] for row in opportunity_index["constraints"] if row.get("required") is True
        }
    missing: set[str] = set()
    counter_refs: set[str] = set()
    for requirement_id in requirement_ids:
        row = fit_index["matrix"].get(requirement_id)
        if row is None or row.get("status") != "supported":
            missing.add(requirement_id)
        if row is not None:
            counter_refs.update(
                cell["evidence_ref"] for cell in row.get("cells", []) if cell.get("status") == "contradicted"
            )

    supported_claim_ids: list[str] = []
    candidate_claim_ids: list[str] = []
    evidence_refs: list[str] = []
    for unit_id in unit_ids:
        for row in index["claims_by_unit"].get(unit_id, []):
            if not (set(row["requirement_ids"]) & requirement_ids):
                continue
            evidence_refs.extend(row["evidence_refs"])
            if row["status"] == "supported":
                supported_claim_ids.append(row["claim_id"])
            elif row["status"] == "candidate":
                candidate_claim_ids.append(row["claim_id"])
        for row in index["rows_by_unit"].get(unit_id, []):
            if set(row["requirement_ids"]) & requirement_ids:
                evidence_refs.extend(row["evidence_refs"])

    action_ids = {
        action_id
        for requirement_id in missing
        for action_id in fit_index["action_by_requirement"].get(requirement_id, set())
    }
    risks: list[str] = []
    source_gate = fit.get("source_gate_status", "abstain")
    hard_gate = fit.get("hard_gate_status", "abstain")
    decision = fit["decision"]
    if source_gate != "pass":
        risks.append("source_gate_" + source_gate)
    if hard_gate != "pass":
        risks.append("hard_gate_" + hard_gate)
    if decision != "supported":
        risks.append("fit_decision_" + decision)
    risks.extend("missing_requirement:" + item for item in sorted(missing))
    if counter_refs:
        risks.append("fit_counterevidence")
    if candidate_claim_ids:
        risks.append("candidate_practice_claim")
    if any(
        set(row["requirement_ids"]) & requirement_ids
        for unit_id in unit_ids
        for row in index["claims_by_unit"].get(unit_id, [])
        if row["status"] == "unknown"
    ):
        risks.append("unknown_practice_evidence")
    status = "candidate" if decision == "supported" and source_gate == "pass" and hard_gate == "pass" and not missing else "unknown"
    reasons = ["explicit_requirement_binding"] if valid_bound_ids else ["opportunity_requirements_without_practice_binding"]
    if opportunity_index["hard_gates"]:
        reasons.append("explicit_opportunity_hard_gates")
    return _make_candidate(
        basis="opportunity_conditioned",
        status=status,
        unit_ids=unit_ids,
        requirement_ids=sorted(requirement_ids),
        supported_claim_ids=supported_claim_ids,
        candidate_claim_ids=candidate_claim_ids,
        evidence_refs=evidence_refs,
        counterevidence_refs=sorted(counter_refs),
        missing_requirement_ids=sorted(missing),
        research_action_ids=sorted(action_ids),
        resource_refs=[
            ref for unit_id in unit_ids for ref in sorted(index["resources_by_unit"].get(unit_id, set()))
        ],
        alternatives=[
            alternative
            for unit_id in unit_ids
            for alternative in index["unit_by_id"].get(unit_id, {}).get("alternatives", [])
        ],
        generation_reasons=reasons,
        risk_flags=risks,
        provenance=_provenance(
            opportunity, practice, fit_hash,
            basis="opportunity_conditioned", unit_ids=unit_ids,
            requirement_ids=sorted(requirement_ids),
        ),
    )


def _abstentions(opportunity: Mapping[str, Any], fit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    validation = fit["validation"]
    for error in validation.get("errors", []):
        rows.append({"code": "fit_validation:" + error, "source": "opportunity_fit"})
    if fit["decision"] == "abstain":
        rows.append({"code": "fit_decision_abstain", "source": "opportunity_fit"})
    if fit["decision"] == "contradicted":
        rows.append({"code": "fit_decision_contradicted", "source": "opportunity_fit"})
    if fit.get("source_gate_status", "abstain") != "pass":
        rows.append({
            "code": "source_gate_" + fit.get("source_gate_status", "abstain"),
            "reason": fit.get("source_gate_reason", "not_declared"),
            "source": "opportunity_fit",
        })
    if fit.get("hard_gate_status", "abstain") != "pass":
        rows.append({"code": "hard_gate_" + fit.get("hard_gate_status", "abstain"), "source": "opportunity_fit"})
    for row in fit.get("required_but_unsupported", []):
        rows.append({
            "code": "missing_requirement:" + row["requirement_id"],
            "status": row["status"],
            "source": "opportunity_fit",
        })
    return sorted(rows, key=stable_json)


def _validate_candidate(
    candidate: Mapping[str, Any], *, unit_ids: set[str], requirement_ids: set[str],
    claim_ids: set[str], practice_refs: set[str], action_ids: set[str],
    opportunity_hash: str, practice_hash: str, fit_hash: str,
) -> None:
    if set(candidate) != _CANDIDATE_FIELDS:
        raise ArtisticProgramHypothesesError("candidate_fields_invalid")
    if candidate.get("basis") not in _BASIS_VALUES or candidate.get("status") not in _CANDIDATE_STATUSES:
        raise ArtisticProgramHypothesesError("candidate_basis_or_status_invalid")
    for field in (
        "unit_ids", "requirement_ids", "supported_claim_ids", "candidate_claim_ids",
        "evidence_refs", "counterevidence_refs", "missing_requirement_ids",
        "research_action_ids", "resource_refs", "alternatives", "generation_reasons", "risk_flags",
    ):
        _refs(candidate.get(field), "candidate." + field, sorted_unique=True)
    if not set(candidate["unit_ids"]).issubset(unit_ids):
        raise ArtisticProgramHypothesesError("candidate_unit_unresolved")
    if not set(candidate["requirement_ids"]).issubset(requirement_ids):
        raise ArtisticProgramHypothesesError("candidate_requirement_unresolved")
    if not set(candidate["missing_requirement_ids"]).issubset(set(candidate["requirement_ids"])):
        raise ArtisticProgramHypothesesError("candidate_missing_requirement_unresolved")
    if not set(candidate["supported_claim_ids"] + candidate["candidate_claim_ids"]).issubset(claim_ids):
        raise ArtisticProgramHypothesesError("candidate_claim_unresolved")
    if not set(candidate["evidence_refs"] + candidate["counterevidence_refs"]).issubset(practice_refs):
        raise ArtisticProgramHypothesesError("candidate_evidence_unresolved")
    if not set(candidate["research_action_ids"]).issubset(action_ids):
        raise ArtisticProgramHypothesesError("candidate_research_action_unresolved")
    provenance = _mapping(candidate.get("provenance"), "candidate.provenance")
    if provenance.get("source_rescan") is not False or provenance.get("claims_promoted") != 0:
        raise ArtisticProgramHypothesesError("candidate_provenance_unsafe")
    if provenance.get("opportunity_input_hash") != opportunity_hash:
        raise ArtisticProgramHypothesesError("candidate_opportunity_hash_mismatch")
    if provenance.get("practice_state_hash") != practice_hash:
        raise ArtisticProgramHypothesesError("candidate_practice_hash_mismatch")
    if provenance.get("fit_input_hash") != fit_hash:
        raise ArtisticProgramHypothesesError("candidate_fit_hash_mismatch")
    if candidate["program_id"] != program_id_for(candidate):
        raise ArtisticProgramHypothesesError("candidate_program_id_mismatch")


def validate_program_payload(
    opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Strictly validate an output against the three accepted input contracts."""
    validate_opportunity_constraints(opportunity)
    practice_errors = validate_practice_evidence_state(practice)
    if practice_errors:
        raise ArtisticProgramHypothesesError("practice_invalid:" + ",".join(practice_errors))
    _validate_fit(fit)
    if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
        raise ArtisticProgramHypothesesError("payload_fields_invalid")
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ArtisticProgramHypothesesError("payload_schema_invalid")
    if payload.get("opportunity_id") != opportunity.get("opportunity_id"):
        raise ArtisticProgramHypothesesError("payload_opportunity_id_mismatch")
    hashes = _mapping(payload.get("input_hashes"), "payload.input_hashes")
    expected_fit_hash = _hash(_canonical_fit(fit))
    if hashes != {
        "opportunity_constraints": opportunity["input_hash"],
        "practice_evidence_state": practice["state_hash"],
        "opportunity_fit": expected_fit_hash,
    }:
        raise ArtisticProgramHypothesesError("payload_input_hashes_mismatch")
    if payload.get("fit_summary") != _fit_summary(_canonical_fit(fit)):
        raise ArtisticProgramHypothesesError("payload_fit_summary_mismatch")
    if payload.get("abstentions") != _abstentions(opportunity, _canonical_fit(fit)):
        raise ArtisticProgramHypothesesError("payload_abstentions_mismatch")
    candidates = _list(payload.get("candidates"), "payload.candidates")
    ids = [candidate.get("program_id") for candidate in candidates if isinstance(candidate, Mapping)]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ArtisticProgramHypothesesError("candidate_order_or_ids_invalid")
    index = _practice_index(practice)
    opportunity_index = _opportunity_index(opportunity)
    fit_index = _fit_index(fit)
    claim_ids = set(index["claims_by_id"])
    action_ids = set(fit_index["actions"])
    for candidate in candidates:
        _validate_candidate(
            _mapping(candidate, "payload.candidate"),
            unit_ids=set(index["unit_ids"]),
            requirement_ids=opportunity_index["requirement_ids"],
            claim_ids=claim_ids,
            practice_refs=index["practice_refs"],
            action_ids=action_ids,
            opportunity_hash=opportunity["input_hash"],
            practice_hash=practice["state_hash"],
            fit_hash=expected_fit_hash,
        )
    reconciliation = _mapping(payload.get("reconciliation"), "payload.reconciliation")
    if reconciliation.get("truth_promotions") != 0 or reconciliation.get("deterministic_order") is not True:
        raise ArtisticProgramHypothesesError("payload_reconciliation_unsafe")
    if reconciliation.get("candidate_count") != len(candidates):
        raise ArtisticProgramHypothesesError("payload_candidate_count_mismatch")
    return True


def generate_artistic_program_hypotheses(
    opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit: Mapping[str, Any],
) -> dict[str, Any]:
    """Generate a deterministic possibility field from accepted contracts."""
    validate_opportunity_constraints(opportunity)
    practice_errors = validate_practice_evidence_state(practice)
    if practice_errors:
        raise ArtisticProgramHypothesesError("practice_invalid:" + ",".join(practice_errors))
    _validate_fit(fit)
    fit_canonical = _canonical_fit(fit)
    fit_hash = _hash(fit_canonical)
    practice_index = _practice_index(practice)
    opportunity_index = _opportunity_index(opportunity)
    fit_index = _fit_index(fit_canonical)
    collision = opportunity_index["documentary_refs"] & practice_index["practice_refs"]
    if collision:
        raise ArtisticProgramHypothesesError("evidence_id_namespace_collision:" + ",".join(sorted(collision)))
    candidates = _practice_native_candidates(practice_index, opportunity, practice, fit_hash)

    bound_units = [
        unit_id for unit_id in practice_index["unit_ids"]
        if practice_index["bindings_by_unit"].get(unit_id, set()) & opportunity_index["requirement_ids"]
    ]
    if bound_units:
        candidates.extend(
            _conditioned_candidate(
                [unit_id], practice_index, opportunity, practice, opportunity_index,
                fit_canonical, fit_index, fit_hash,
            )
            for unit_id in bound_units
        )
    elif opportunity_index["requirement_ids"]:
        candidates.append(
            _conditioned_candidate(
                [], practice_index, opportunity, practice, opportunity_index,
                fit_canonical, fit_index, fit_hash,
            )
        )
    candidates.sort(key=lambda row: row["program_id"])
    input_hashes = {
        "opportunity_constraints": opportunity["input_hash"],
        "practice_evidence_state": practice["state_hash"],
        "opportunity_fit": fit_hash,
    }
    abstentions = _abstentions(opportunity, fit_canonical)
    status_counts = {status: sum(row["status"] == status for row in candidates) for status in sorted(_CANDIDATE_STATUSES)}
    basis_counts = {basis: sum(row["basis"] == basis for row in candidates) for basis in sorted(_BASIS_VALUES)}
    payload = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity["opportunity_id"],
        "practice_identity": fit_canonical.get("practice_identity"),
        "input_hashes": input_hashes,
        "fit_summary": _fit_summary(fit_canonical),
        "abstentions": abstentions,
        "candidates": candidates,
        "provenance": {
            "source_schemas": {
                "opportunity": OPPORTUNITY_SCHEMA,
                "practice": PRACTICE_SCHEMA,
                "fit": FIT_SCHEMA,
            },
            "source_rescan": False,
            "claims_promoted": 0,
        },
        "reconciliation": {
            "candidate_count": len(candidates),
            "candidate_status_counts": status_counts,
            "basis_counts": basis_counts,
            "practice_unit_count": len(practice_index["unit_ids"]),
            "practice_units_with_conditioned_candidates": len(bound_units),
            "practice_evidence_ref_count": len(practice_index["practice_refs"]),
            "opportunity_requirement_count": len(opportunity_index["requirement_ids"]),
            "fit_research_action_count": len(fit_index["actions"]),
            "evidence_id_namespace_collision": False,
            "truth_promotions": 0,
            "deterministic_order": candidates == sorted(candidates, key=lambda row: row["program_id"]),
            "source_gate_status": fit_canonical.get("source_gate_status", "abstain"),
            "hard_gate_status": fit_canonical.get("hard_gate_status", "abstain"),
            "fit_decision": fit_canonical["decision"],
        },
    }
    validate_program_payload(opportunity, practice, fit_canonical, payload)
    return payload


def validate_artistic_program_candidates(
    opportunity: Mapping[str, Any], practice: Mapping[str, Any], fit: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    return validate_program_payload(opportunity, practice, fit, payload)


# Compact names for consumers that describe the operation as generation or
# validation.  They remain aliases to the single pure implementation.
generate_program_candidates = generate_artistic_program_hypotheses
validate_payload = validate_program_payload


__all__ = [
    "ALGORITHM_VERSION", "ArtisticProgramHypothesesError", "SCHEMA",
    "generate_artistic_program_hypotheses", "program_id_for",
    "generate_program_candidates", "validate_artistic_program_candidates",
    "validate_payload", "validate_program_payload",
]
