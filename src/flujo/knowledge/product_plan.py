"""Compile one evidence-governed plan for MAK cultural products.

The plan is a shared, read-only projection.  Portfolio, application and
research targets consume the same selected programs, practice claims, assets,
requirements and gaps; they do not reconstruct the archive independently.
External opportunity and research evidence never become proof of the artist's
work.  No target is published, submitted, dispatched or promoted here.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json

from .artistic_program_hypotheses import validate_artistic_program_candidates
from .opportunity_constraints import validate_opportunity_constraints
from .practice_evidence_state import validate_practice_evidence_state
from .research_frontier_bridge import validate_research_frontier_payload


SCHEMA = "mak-product-plan-v1"
ALGORITHM_VERSION = "common-product-plan-2"
OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
PRACTICE_SCHEMA = "mak-practice-evidence-state-v1"
FIT_SCHEMA = "mak-opportunity-fit-v1"
PROGRAM_SCHEMA = "mak-artistic-program-candidates-v1"
POSSIBILITY_SCHEMA = "mak-possibility-field-v1"
FRONTIER_SCHEMA = "mak-research-frontier-jobs-v1"
RETURN_SCHEMA = "mak-evidence-return-v1"
TARGETS = ("portfolio_dossier", "application_draft", "research_brief")
TARGET_STATUSES = {"draftable", "blocked", "not_required"}
_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "practice_identity",
    "input_hashes", "selected_programs", "claim_index", "asset_index",
    "practice_evidence_refs",
    "targets", "research_jobs", "gaps", "control", "provenance",
    "reconciliation",
}
_SELECTED_FIELDS = {
    "program_id", "selection", "rank", "unit_ids", "evidence_refs",
    "requirement_ids", "missing_requirement_ids", "risk_flags",
    "supported_claim_ids", "candidate_claim_ids", "source_gate_status",
    "hard_gate_status", "ready",
}
_CONTROL_FIELDS = {
    "promotion", "training_permitted", "publication", "submission",
    "dispatch", "user_review_required",
}
_CLAIM_FIELDS = {
    "claim_id", "unit_id", "status", "statement", "evidence_refs",
    "requirement_ids", "source_status", "provenance_ref", "evidence_scope",
}
_ASSET_FIELDS = {
    "asset_ref", "artifact_ref", "unit_id", "artifact_id", "physical_id",
    "content_id", "relative_path", "availability", "kind", "role",
    "evidence_refs", "evidence_scope", "program_ids",
}


class ProductPlanError(ValueError):
    """Raised when an accepted input or product-plan payload is unsafe."""


def _canonical(value: Any) -> Any:
    """Canonicalize order-only JSON differences without mutating the input."""
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, list):
        rows = [_canonical(item) for item in value]
        return sorted(rows, key=stable_json)
    return copy.deepcopy(value)


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ProductPlanError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ProductPlanError(f"{field}_required")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductPlanError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProductPlanError(f"{field}_must_be_list")
    return value


def _refs(value: Any, field: str, *, sorted_unique: bool = False) -> list[str]:
    rows = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise ProductPlanError(f"{field}_invalid")
    result = sorted(set(rows))
    if sorted_unique and rows != result:
        raise ProductPlanError(f"{field}_not_sorted_unique")
    return result


def _optional_refs(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    return _refs(value, field)


def _input_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductPlanError(f"{field}_missing")
    return value.strip()


def _raise_contract(name: str, error: Exception) -> None:
    raise ProductPlanError(f"{name}_contract_invalid:{error}") from error


def _validate_evidence_return(
    evidence_return: Mapping[str, Any],
    frontier: Mapping[str, Any],
    practice: Mapping[str, Any],
) -> None:
    if evidence_return.get("schema") != RETURN_SCHEMA:
        raise ProductPlanError("evidence_return_schema_invalid")
    for field in (
        "opportunity_evidence_proposals", "practice_evidence_proposals",
        "binding_proposals", "contradiction_notices", "unresolved",
    ):
        _list(evidence_return.get(field), "evidence_return." + field)
    provenance = _mapping(evidence_return.get("provenance"), "evidence_return.provenance")
    if provenance.get("promotion") != "none" or provenance.get("training_permitted") is not False:
        raise ProductPlanError("evidence_return_promotion_or_training_invalid")
    fit_recompute = _mapping(evidence_return.get("fit_recompute"), "evidence_return.fit_recompute")
    if not isinstance(fit_recompute.get("required"), bool):
        raise ProductPlanError("evidence_return.fit_recompute_required_invalid")
    jobs = {
        _text(row.get("job_id"), "frontier.job_id"): row
        for row in _list(frontier.get("jobs"), "frontier.jobs")
    }
    practice_artifacts = {
        _text(row.get("artifact_ref"), "practice.artifact_ref")
        for row in _list(practice.get("artifacts"), "practice.artifacts")
    }
    seen_proposals: set[str] = set()
    for collection_name in ("opportunity_evidence_proposals", "practice_evidence_proposals", "binding_proposals"):
        for index, raw in enumerate(evidence_return[collection_name]):
            row = _mapping(raw, f"evidence_return.{collection_name}[{index}]")
            proposal_id = _text(row.get("proposal_id", row.get("binding_id")), f"{collection_name}.id")
            if proposal_id in seen_proposals:
                raise ProductPlanError("evidence_return_proposal_id_collision")
            seen_proposals.add(proposal_id)
            job_id = _text(row.get("job_id"), f"{collection_name}.job_id")
            requirement_id = _text(row.get("requirement_id"), f"{collection_name}.requirement_id")
            job = jobs.get(job_id)
            if job is None:
                raise ProductPlanError("evidence_return_job_ref_foreign")
            if requirement_id not in _refs(job.get("requirement_ids"), "frontier.job.requirement_ids"):
                raise ProductPlanError("evidence_return_requirement_ref_foreign")
            if collection_name == "practice_evidence_proposals":
                refs = _refs(row.get("artifact_refs", []), f"{collection_name}.artifact_refs")
                if not set(refs).issubset(practice_artifacts):
                    raise ProductPlanError("evidence_return_artifact_ref_foreign")
            if row.get("promotion") not in {None, "none"}:
                raise ProductPlanError("evidence_return_promotion_invalid")
    for collection_name in ("contradiction_notices", "unresolved"):
        for index, raw in enumerate(evidence_return[collection_name]):
            row = _mapping(raw, f"evidence_return.{collection_name}[{index}]")
            job_id = row.get("job_id")
            if job_id is not None and _text(job_id, f"{collection_name}.job_id") not in jobs:
                raise ProductPlanError("evidence_return_diagnostic_job_ref_foreign")


def _validate_possibility(
    possibility: Mapping[str, Any],
    program_ids: set[str],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], set[str]]:
    if possibility.get("schema") != POSSIBILITY_SCHEMA:
        raise ProductPlanError("possibility_schema_invalid")
    provenance = _mapping(possibility.get("provenance"), "possibility.provenance")
    if provenance.get("errors"):
        raise ProductPlanError("possibility_contains_validation_errors")
    ranked = _list(possibility.get("candidates_ranked"), "possibility.candidates_ranked")
    abstained = _list(possibility.get("abstained"), "possibility.abstained")
    rejected = _list(possibility.get("rejected"), "possibility.rejected")
    selected_ids: set[str] = set()
    for collection_name, rows in (("candidates_ranked", ranked), ("abstained", abstained)):
        for index, raw in enumerate(rows):
            row = _mapping(raw, f"possibility.{collection_name}[{index}]")
            candidate_id = _text(row.get("candidate_id"), f"{collection_name}.candidate_id")
            if candidate_id not in program_ids:
                raise ProductPlanError("possibility_candidate_ref_foreign")
            if candidate_id in selected_ids:
                raise ProductPlanError("possibility_candidate_id_collision")
            selected_ids.add(candidate_id)
            if collection_name == "candidates_ranked":
                rank = row.get("rank")
                if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
                    raise ProductPlanError("possibility_rank_invalid")
    rejected_ids: set[str] = set()
    for index, raw in enumerate(rejected):
        row = _mapping(raw, f"possibility.rejected[{index}]")
        candidate_id = _text(row.get("candidate_id"), "possibility.rejected.candidate_id")
        if candidate_id not in program_ids:
            raise ProductPlanError("possibility_rejected_ref_foreign")
        if candidate_id in selected_ids or candidate_id in rejected_ids:
            raise ProductPlanError("possibility_candidate_id_collision")
        rejected_ids.add(candidate_id)
    return [dict(row) for row in ranked], [dict(row) for row in abstained], rejected_ids


def _practice_indexes(practice: Mapping[str, Any]) -> dict[str, Any]:
    units = _list(practice.get("units"), "practice.units")
    artifacts = _list(practice.get("artifacts"), "practice.artifacts")
    unit_ids: set[str] = set()
    artifact_by_ref: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(units):
        row = _mapping(raw, f"practice.units[{index}]")
        unit_id = _text(row.get("unit_id"), "practice.unit_id")
        if unit_id in unit_ids:
            raise ProductPlanError("practice_unit_id_collision")
        unit_ids.add(unit_id)
    practice_refs: set[str] = set()
    for index, raw in enumerate(artifacts):
        row = _mapping(raw, f"practice.artifacts[{index}]")
        artifact_ref = _text(row.get("artifact_ref"), "practice.artifact_ref")
        if artifact_ref in artifact_by_ref:
            raise ProductPlanError("practice_artifact_ref_collision")
        artifact_by_ref[artifact_ref] = row
        practice_refs.add(artifact_ref)
        practice_refs.update(_optional_refs(row.get("evidence_refs"), "practice.artifact.evidence_refs"))
    claims = _mapping(practice.get("claims"), "practice.claims")
    claims_by_id: dict[str, Mapping[str, Any]] = {}
    for status in ("supported", "candidate", "unknown"):
        for index, raw in enumerate(_list(claims.get(status), f"practice.claims.{status}")):
            row = _mapping(raw, f"practice.claims.{status}[{index}]")
            claim_id = _text(row.get("claim_id"), "practice.claim_id")
            if claim_id in claims_by_id:
                raise ProductPlanError("practice_claim_id_collision")
            if row.get("status") != status:
                raise ProductPlanError("practice_claim_status_mismatch")
            claims_by_id[claim_id] = row
            practice_refs.update(_optional_refs(row.get("evidence_refs"), "practice.claim.evidence_refs"))
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        for index, raw in enumerate(_list(practice.get(dimension), f"practice.{dimension}")):
            row = _mapping(raw, f"practice.{dimension}[{index}]")
            practice_refs.update(_optional_refs(row.get("evidence_refs"), f"practice.{dimension}.evidence_refs"))
    return {
        "unit_ids": unit_ids,
        "artifact_by_ref": artifact_by_ref,
        "claims_by_id": claims_by_id,
        "practice_refs": practice_refs,
    }


def _opportunity_indexes(opportunity: Mapping[str, Any]) -> dict[str, Any]:
    requirements: set[str] = set()
    for index, raw in enumerate(_list(opportunity.get("constraints"), "opportunity.constraints")):
        row = _mapping(raw, f"opportunity.constraints[{index}]")
        requirement_id = _text(row.get("constraint_id"), "opportunity.constraint_id")
        if requirement_id in requirements:
            raise ProductPlanError("opportunity_requirement_id_collision")
        requirements.add(requirement_id)
    return {"requirement_ids": requirements}


def _fit_indexes(fit: Mapping[str, Any]) -> dict[str, Any]:
    action_ids: set[str] = set()
    for index, raw in enumerate(_list(fit.get("research_job_candidates"), "fit.research_job_candidates")):
        row = _mapping(raw, f"fit.research_job_candidates[{index}]")
        action_id = _text(row.get("candidate_id"), "fit.research_action_id")
        if action_id in action_ids:
            raise ProductPlanError("fit_research_action_id_collision")
        action_ids.add(action_id)
    return {"action_ids": action_ids}


def _program_indexes(
    program_payload: Mapping[str, Any],
    practice_index: Mapping[str, Any],
    opportunity_index: Mapping[str, Any],
    fit_index: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(_list(program_payload.get("candidates"), "program.candidates")):
        row = _mapping(raw, f"program.candidates[{index}]")
        program_id = _text(row.get("program_id"), "program.program_id")
        if program_id in result:
            raise ProductPlanError("program_id_collision")
        result[program_id] = row
        for field, universe in (
            ("unit_ids", practice_index["unit_ids"]),
            ("supported_claim_ids", set(practice_index["claims_by_id"])),
            ("candidate_claim_ids", set(practice_index["claims_by_id"])),
            ("evidence_refs", practice_index["practice_refs"]),
            ("counterevidence_refs", practice_index["practice_refs"]),
            ("resource_refs", practice_index["practice_refs"]),
            ("requirement_ids", opportunity_index["requirement_ids"]),
            ("missing_requirement_ids", opportunity_index["requirement_ids"]),
            ("research_action_ids", fit_index["action_ids"]),
        ):
            refs = _refs(row.get(field), f"program.{field}")
            if not set(refs).issubset(universe):
                raise ProductPlanError(f"program_{field}_ref_foreign")
    return result


def _claim_index(practice: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    claims = _mapping(practice.get("claims"), "practice.claims")
    for status in ("supported", "candidate", "unknown"):
        for raw in claims[status]:
            row = _mapping(raw, "practice.claim")
            rows.append({
                "claim_id": _text(row.get("claim_id"), "claim.claim_id"),
                "unit_id": _text(row.get("unit_id"), "claim.unit_id", required=False),
                "status": _text(row.get("status"), "claim.status"),
                "statement": row.get("statement"),
                "evidence_refs": _refs(row.get("evidence_refs", []), "claim.evidence_refs"),
                "requirement_ids": _refs(row.get("requirement_ids", []), "claim.requirement_ids"),
                "source_status": _text(row.get("source_status"), "claim.source_status", required=False) or "unknown",
                "provenance_ref": _text(row.get("provenance_ref"), "claim.provenance_ref", required=False),
                "evidence_scope": "practice",
            })
    return sorted(rows, key=lambda row: row["claim_id"])


def _asset_index(
    practice: Mapping[str, Any],
    selected: list[Mapping[str, Any]],
    programs: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project physical assets and explicit program associations only.

    A program may point to a practice artifact through its evidence refs or
    resource refs, or through an explicit unit membership.  Content identity,
    filenames and similarity are deliberately absent from this join so that
    byte-identical physical artifacts remain separate rows.
    """
    programs_by_explicit_ref: dict[str, set[str]] = {}
    programs_by_unit: dict[str, set[str]] = {}
    for row in selected:
        program_id = _text(row.get("program_id"), "selected_program.program_id")
        source = programs[program_id]
        explicit_refs = set(_refs(row.get("evidence_refs"), "selected_program.evidence_refs"))
        explicit_refs.update(_refs(source.get("resource_refs"), "program.resource_refs"))
        for ref in explicit_refs:
            programs_by_explicit_ref.setdefault(ref, set()).add(program_id)
        for unit_id in _refs(row.get("unit_ids"), "selected_program.unit_ids"):
            programs_by_unit.setdefault(unit_id, set()).add(program_id)

    rows: list[dict[str, Any]] = []
    for raw in practice["artifacts"]:
        row = _mapping(raw, "practice.artifact")
        artifact_ref = _text(row.get("artifact_ref"), "artifact.artifact_ref")
        unit_id = _text(row.get("unit_id"), "artifact.unit_id", required=False)
        evidence_refs = _refs(row.get("evidence_refs", []), "artifact.evidence_refs")
        association_refs = {artifact_ref, *evidence_refs}
        program_ids = set()
        for ref in association_refs:
            program_ids.update(programs_by_explicit_ref.get(ref, set()))
        if unit_id:
            program_ids.update(programs_by_unit.get(unit_id, set()))
        rows.append({
            "asset_ref": artifact_ref,
            "artifact_ref": artifact_ref,
            "unit_id": unit_id,
            "artifact_id": row.get("artifact_id"),
            "physical_id": row.get("physical_id"),
            "content_id": row.get("content_id"),
            "relative_path": _text(row.get("relative_path"), "artifact.relative_path", required=False),
            "availability": _text(row.get("availability"), "artifact.availability", required=False) or "unknown",
            "kind": row.get("kind"),
            "role": row.get("role"),
            "evidence_refs": evidence_refs,
            "evidence_scope": "practice",
            "program_ids": sorted(program_ids),
        })
    return sorted(rows, key=lambda row: row["asset_ref"])


def _selected_programs(
    ranked: list[Mapping[str, Any]],
    abstained: list[Mapping[str, Any]],
    programs: Mapping[str, Mapping[str, Any]],
    fit: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selection, source_rows in (("ranked", ranked), ("abstained_research_first", abstained)):
        for source in source_rows:
            program_id = _text(source.get("candidate_id"), "possibility.candidate_id")
            program = programs[program_id]
            requirements = _refs(program.get("requirement_ids"), "program.requirement_ids")
            missing = sorted(set(_refs(program.get("missing_requirement_ids"), "program.missing_requirement_ids")) | set(_refs(source.get("missing_requirement_ids", []), "possibility.missing_requirement_ids")))
            unit_ids = _refs(program.get("unit_ids"), "program.unit_ids")
            evidence_refs = _refs(program.get("evidence_refs"), "program.evidence_refs")
            supported_claim_ids = _refs(
                program.get("supported_claim_ids"), "program.supported_claim_ids"
            )
            candidate_claim_ids = _refs(
                program.get("candidate_claim_ids"), "program.candidate_claim_ids"
            )
            if set(supported_claim_ids) & set(candidate_claim_ids):
                raise ProductPlanError("program_claim_partition_overlap")
            risks = sorted(set(_refs(program.get("risk_flags"), "program.risk_flags")) | set(_refs(source.get("risk_flags", []), "possibility.risk_flags")))
            source_gate = _text(source.get("source_gate_status"), "possibility.source_gate_status", required=False) or fit.get("source_gate_status", "abstain")
            hard_gate = _text(source.get("hard_gate_status"), "possibility.hard_gate_status", required=False) or fit.get("hard_gate_status", "abstain")
            rank = source.get("rank") if selection == "ranked" else None
            source_ready = source.get("ready")
            ready = bool(source_ready) if isinstance(source_ready, bool) else (
                selection == "ranked" and program.get("status") == "candidate"
                and not missing and source_gate == "pass" and hard_gate == "pass"
            )
            rows.append({
                "program_id": program_id,
                "selection": selection,
                "rank": rank,
                "unit_ids": unit_ids,
                "evidence_refs": evidence_refs,
                "requirement_ids": requirements,
                "missing_requirement_ids": missing,
                "risk_flags": risks,
                "supported_claim_ids": supported_claim_ids,
                "candidate_claim_ids": candidate_claim_ids,
                "source_gate_status": source_gate,
                "hard_gate_status": hard_gate,
                "ready": ready,
            })
    return sorted(rows, key=lambda row: (
        0 if row["selection"] == "ranked" else 1,
        row["rank"] if isinstance(row["rank"], int) else 10**9,
        row["program_id"],
    ))


def _gaps(
    selected: list[Mapping[str, Any]],
    possibility: Mapping[str, Any],
    frontier: Mapping[str, Any],
    evidence_return: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for program in selected:
        for requirement_id in program["missing_requirement_ids"]:
            rows.append({
                "code": "missing_requirement",
                "program_id": program["program_id"],
                "requirement_id": requirement_id,
                "evidence_scope": "practice_or_opportunity_binding",
            })
        for risk_flag in program["risk_flags"]:
            rows.append({"code": "risk_flag", "program_id": program["program_id"], "risk_flag": risk_flag})
        if program["selection"] == "abstained_research_first":
            rows.append({"code": "possibility_abstained", "program_id": program["program_id"]})
    if fit.get("source_gate_status", "abstain") != "pass":
        rows.append({"code": "source_gate_not_pass", "status": fit.get("source_gate_status", "abstain")})
    if fit.get("hard_gate_status", "abstain") != "pass":
        rows.append({"code": "hard_gate_not_pass", "status": fit.get("hard_gate_status", "abstain")})
    for raw in _list(frontier.get("jobs"), "frontier.jobs"):
        job = _mapping(raw, "frontier.job")
        rows.append({
            "code": "research_job_pending",
            "job_id": _text(job.get("job_id"), "frontier.job_id"),
            "requirement_ids": _refs(job.get("requirement_ids"), "frontier.job.requirement_ids"),
        })
    if evidence_return.get("unresolved") or evidence_return.get("opportunity_evidence_proposals") or evidence_return.get("practice_evidence_proposals"):
        rows.append({"code": "evidence_return_pending_ingestion", "count": sum(
            len(evidence_return.get(name, []))
            for name in ("unresolved", "opportunity_evidence_proposals", "practice_evidence_proposals")
        )})
    for key in ("ambiguous_refs", "unassigned_refs"):
        for ref in _refs(practice.get(key, []), "practice." + key):
            rows.append({"code": "practice_partition_unresolved", "partition": key, "artifact_ref": ref})
    return sorted({stable_json(row): row for row in rows}.values(), key=stable_json)


def _target(
    status: str,
    reasons: list[str],
    selected: list[Mapping[str, Any]],
    claims: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    jobs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "status": status,
        "reasons": sorted(set(reasons)),
        "selected_program_ids": sorted(row["program_id"] for row in selected),
        "claim_count": len(claims),
        "asset_count": len(assets),
        "research_job_count": len(jobs),
    }


def _targets(
    selected: list[Mapping[str, Any]],
    claims: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    jobs: list[Mapping[str, Any]],
    gaps: list[Mapping[str, Any]],
    fit: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    internal = bool(claims or assets)
    ranked = [row for row in selected if row["selection"] == "ranked"]
    missing = sorted({
        requirement_id
        for row in selected
        for requirement_id in row["missing_requirement_ids"]
    })
    portfolio_reasons = ["internal_practice_evidence_available"] if internal else ["practice_evidence_missing"]
    if not ranked and selected:
        portfolio_reasons.append("ranked_programs_absent_research_first_preserved")
    portfolio_status = "draftable" if internal else "blocked"
    application_reasons: list[str] = []
    if fit.get("source_gate_status") != "pass":
        application_reasons.append("source_gate_not_pass")
    if fit.get("hard_gate_status") != "pass":
        application_reasons.append("hard_gate_not_pass")
    if fit.get("decision") != "supported":
        application_reasons.append("fit_not_supported")
    if fit.get("validation", {}).get("errors"):
        application_reasons.append("fit_validation_errors")
    if not ranked:
        application_reasons.append("no_ranked_program")
    if missing:
        application_reasons.append("missing_requirements")
    application_status = "draftable" if not application_reasons else "blocked"
    research_reasons = []
    if jobs:
        research_reasons.append("research_jobs_pending_ingestion")
    if any(row["code"] in {"missing_requirement", "risk_flag", "possibility_abstained", "evidence_return_pending_ingestion"} for row in gaps):
        research_reasons.append("evidence_gaps_present")
    research_status = "draftable" if research_reasons else "not_required"
    return {
        "portfolio_dossier": _target(portfolio_status, portfolio_reasons, selected, claims, assets, jobs),
        "application_draft": _target(application_status, application_reasons, selected, claims, assets, jobs),
        "research_brief": _target(research_status, research_reasons, selected, claims, assets, jobs),
    }


def _validate_plan_payload(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
        raise ProductPlanError("payload_fields_invalid")
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ProductPlanError("payload_schema_invalid")
    if not isinstance(payload.get("opportunity_id"), str) or not payload["opportunity_id"]:
        raise ProductPlanError("payload_opportunity_id_invalid")
    if not isinstance(payload.get("practice_identity"), str) or not payload["practice_identity"]:
        raise ProductPlanError("payload_practice_identity_invalid")
    hashes = _mapping(payload.get("input_hashes"), "payload.input_hashes")
    expected_hash_names = {
        "opportunity_constraints", "practice_evidence_state", "opportunity_fit",
        "artistic_program_candidates", "possibility_field",
        "research_frontier", "evidence_return",
    }
    if set(hashes) != expected_hash_names or any(not isinstance(value, str) or not value for value in hashes.values()):
        raise ProductPlanError("payload_input_hashes_invalid")
    selected = _list(payload.get("selected_programs"), "payload.selected_programs")
    program_ids: list[str] = []
    for raw in selected:
        row = _mapping(raw, "payload.selected_program")
        if set(row) != _SELECTED_FIELDS:
            raise ProductPlanError("selected_program_fields_invalid")
        program_ids.append(_text(row.get("program_id"), "selected_program.program_id"))
        if row.get("selection") not in {"ranked", "abstained_research_first"}:
            raise ProductPlanError("selected_program_selection_invalid")
        if row.get("rank") is not None and (isinstance(row.get("rank"), bool) or not isinstance(row.get("rank"), int) or row["rank"] < 1):
            raise ProductPlanError("selected_program_rank_invalid")
        for field in ("unit_ids", "evidence_refs", "requirement_ids", "missing_requirement_ids", "risk_flags"):
            _refs(row.get(field), "selected_program." + field, sorted_unique=True)
        for field in ("supported_claim_ids", "candidate_claim_ids"):
            _refs(row.get(field), "selected_program." + field, sorted_unique=True)
        if row.get("source_gate_status") not in {"abstain", "pass", "fail"}:
            raise ProductPlanError("selected_program_source_gate_invalid")
        if row.get("hard_gate_status") not in {"abstain", "pass", "fail"}:
            raise ProductPlanError("selected_program_hard_gate_invalid")
        if not isinstance(row.get("ready"), bool):
            raise ProductPlanError("selected_program_ready_invalid")
    if len(program_ids) != len(set(program_ids)):
        raise ProductPlanError("selected_program_id_collision")
    expected_program_order = [
        row["program_id"] for row in sorted(
            selected,
            key=lambda row: (
                0 if row["selection"] == "ranked" else 1,
                row["rank"] if isinstance(row["rank"], int) else 10**9,
                row["program_id"],
            ),
        )
    ]
    if program_ids != expected_program_order:
        raise ProductPlanError("selected_program_order_invalid")
    claims = _list(payload.get("claim_index"), "payload.claim_index")
    practice_evidence_refs = set(_refs(
        payload.get("practice_evidence_refs"),
        "payload.practice_evidence_refs",
        sorted_unique=True,
    ))
    claim_ids: list[str] = []
    for raw in claims:
        row = _mapping(raw, "payload.claim")
        if set(row) != _CLAIM_FIELDS:
            raise ProductPlanError("claim_fields_invalid")
        claim_ids.append(_text(row.get("claim_id"), "claim.claim_id"))
        _refs(row.get("evidence_refs"), "claim.evidence_refs", sorted_unique=True)
        if not set(row["evidence_refs"]).issubset(practice_evidence_refs):
            raise ProductPlanError("claim_evidence_ref_foreign")
        _refs(row.get("requirement_ids"), "claim.requirement_ids", sorted_unique=True)
        if row.get("evidence_scope") != "practice":
            raise ProductPlanError("claim_evidence_scope_invalid")
    if claim_ids != sorted(set(claim_ids)):
        raise ProductPlanError("claim_id_order_or_collision")
    claim_id_set = set(claim_ids)
    for row in selected:
        supported = set(row["supported_claim_ids"])
        candidate = set(row["candidate_claim_ids"])
        if supported & candidate:
            raise ProductPlanError("selected_program_claim_partition_overlap")
        if not (supported | candidate).issubset(claim_id_set):
            raise ProductPlanError("selected_program_claim_ref_foreign")
    assets = _list(payload.get("asset_index"), "payload.asset_index")
    asset_ids: list[str] = []
    for raw in assets:
        row = _mapping(raw, "payload.asset")
        if set(row) != _ASSET_FIELDS:
            raise ProductPlanError("asset_fields_invalid")
        asset_ids.append(_text(row.get("asset_ref"), "asset.asset_ref"))
        _refs(row.get("evidence_refs"), "asset.evidence_refs", sorted_unique=True)
        if not {row["artifact_ref"], *row["evidence_refs"]}.issubset(practice_evidence_refs):
            raise ProductPlanError("asset_evidence_ref_foreign")
        program_refs = _refs(row.get("program_ids"), "asset.program_ids", sorted_unique=True)
        if not set(program_refs).issubset(set(program_ids)):
            raise ProductPlanError("asset_program_ref_foreign")
        if row.get("evidence_scope") != "practice":
            raise ProductPlanError("asset_evidence_scope_invalid")
    if asset_ids != sorted(set(asset_ids)):
        raise ProductPlanError("asset_id_order_or_collision")
    targets = _mapping(payload.get("targets"), "payload.targets")
    if set(targets) != set(TARGETS):
        raise ProductPlanError("target_keys_invalid")
    for target_id in TARGETS:
        target = _mapping(targets[target_id], "payload.target")
        status = target.get("status")
        if status not in TARGET_STATUSES or not isinstance(target.get("reasons"), list):
            raise ProductPlanError("target_status_invalid")
        if target["reasons"] != sorted(set(target["reasons"])):
            raise ProductPlanError("target_reason_order_invalid")
    jobs = _list(payload.get("research_jobs"), "payload.research_jobs")
    job_ids: list[str] = []
    for raw in jobs:
        row = _mapping(raw, "payload.research_job")
        job_ids.append(_text(row.get("job_id"), "research_job.job_id"))
        if row.get("dispatch") is not False or row.get("evidence_return_status") != "pending_ingestion":
            raise ProductPlanError("research_job_dispatch_or_return_invalid")
    if job_ids != sorted(set(job_ids)):
        raise ProductPlanError("research_job_order_or_collision")
    control = _mapping(payload.get("control"), "payload.control")
    if set(control) != _CONTROL_FIELDS or control != {
        "promotion": "none", "training_permitted": False, "publication": False,
        "submission": False, "dispatch": False, "user_review_required": False,
    }:
        raise ProductPlanError("control_invalid")
    return True


def _compile(
    opportunity: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
    program_candidates: Mapping[str, Any],
    possibility: Mapping[str, Any],
    frontier: Mapping[str, Any],
    evidence_return: Mapping[str, Any],
) -> dict[str, Any]:
    for name, value in (
        ("opportunity", opportunity), ("practice", practice), ("fit", fit),
        ("program_candidates", program_candidates), ("possibility", possibility),
        ("frontier", frontier), ("evidence_return", evidence_return),
    ):
        if not isinstance(value, Mapping):
            raise ProductPlanError(name + "_must_be_object")
    try:
        validate_opportunity_constraints(opportunity)
    except Exception as error:
        _raise_contract("opportunity", error)
    practice_errors = validate_practice_evidence_state(practice)
    if practice_errors:
        raise ProductPlanError("practice_contract_invalid:" + ",".join(practice_errors))
    try:
        validate_artistic_program_candidates(opportunity, practice, fit, program_candidates)
    except Exception as error:
        _raise_contract("program_candidates", error)
    try:
        validate_research_frontier_payload(possibility, fit, opportunity, frontier)
    except Exception as error:
        _raise_contract("research_frontier", error)
    _validate_evidence_return(evidence_return, frontier, practice)

    practice_index = _practice_indexes(practice)
    opportunity_index = _opportunity_indexes(opportunity)
    fit_index = _fit_indexes(fit)
    programs = _program_indexes(program_candidates, practice_index, opportunity_index, fit_index)
    ranked, abstained, rejected = _validate_possibility(possibility, set(programs))
    selected = _selected_programs(ranked, abstained, programs, fit)
    claims = _claim_index(practice)
    assets = _asset_index(practice, selected, programs)
    jobs = []
    for raw in _list(frontier.get("jobs"), "frontier.jobs"):
        job = copy.deepcopy(dict(_mapping(raw, "frontier.job")))
        job["evidence_return_status"] = "pending_ingestion"
        jobs.append(job)
    jobs.sort(key=lambda row: row["job_id"])
    gaps = _gaps(selected, possibility, frontier, evidence_return, practice, fit)
    targets = _targets(selected, claims, assets, jobs, gaps, fit)
    program_hash = _hash(_canonical(program_candidates))
    possibility_hash = _hash(_canonical(possibility))
    frontier_hash = _hash(_canonical(frontier))
    return_hash = _hash(_canonical(evidence_return))
    payload = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": _text(opportunity.get("opportunity_id"), "opportunity_id"),
        "practice_identity": _text(practice.get("practice_identity"), "practice_identity", required=False)
        or f"practice:{practice.get('tenant', 'mak')}:{practice.get('archive_id', 'unknown')}:{practice.get('snapshot_id', 'unknown')}",
        "input_hashes": {
            "opportunity_constraints": _input_hash(opportunity.get("input_hash"), "opportunity.input_hash"),
            "practice_evidence_state": _input_hash(practice.get("state_hash"), "practice.state_hash"),
            "opportunity_fit": _hash(_canonical(fit)),
            "artistic_program_candidates": program_hash,
            "possibility_field": possibility_hash,
            "research_frontier": frontier_hash,
            "evidence_return": return_hash,
        },
        "selected_programs": selected,
        "claim_index": claims,
        "asset_index": assets,
        "practice_evidence_refs": sorted(practice_index["practice_refs"]),
        "targets": targets,
        "research_jobs": jobs,
        "gaps": gaps,
        "control": {
            "promotion": "none",
            "training_permitted": False,
            "publication": False,
            "submission": False,
            "dispatch": False,
            "user_review_required": False,
        },
        "provenance": {
            "source_schemas": [
                OPPORTUNITY_SCHEMA, PRACTICE_SCHEMA, FIT_SCHEMA, PROGRAM_SCHEMA,
                POSSIBILITY_SCHEMA, FRONTIER_SCHEMA, RETURN_SCHEMA,
            ],
            "source_rescan": False,
            "database_write": False,
            "network_called": False,
            "evidence_return_status": "pending_ingestion" if jobs else "not_started",
            "rejected_program_ids": sorted(rejected),
            "promotion": "none",
            "training_permitted": False,
        },
        "reconciliation": {
            "selected_program_count": len(selected),
            "ranked_program_count": len(ranked),
            "abstained_program_count": len(abstained),
            "rejected_program_count": len(rejected),
            "claim_count": len(claims),
            "asset_count": len(assets),
            "research_job_count": len(jobs),
            "gap_count": len(gaps),
            "practice_claims_only": True,
            "external_evidence_in_claim_index": 0,
            "truth_promotions": 0,
            "pending_ingestion": len(jobs),
            "deterministic_order": True,
            "balanced": True,
        },
    }
    _validate_plan_payload(payload)
    return payload


def compile_product_plan(
    opportunity: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
    program_candidates: Mapping[str, Any],
    possibility: Mapping[str, Any],
    frontier: Mapping[str, Any],
    evidence_return: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a deterministic common plan without side effects."""
    return _compile(
        opportunity, practice, fit, program_candidates, possibility,
        frontier, evidence_return,
    )


def validate_product_plan(
    opportunity: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
    program_candidates: Mapping[str, Any],
    possibility: Mapping[str, Any],
    frontier: Mapping[str, Any],
    evidence_return: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Validate both the upstream contracts and the plan's own safety gates."""
    expected = _compile(
        opportunity, practice, fit, program_candidates, possibility,
        frontier, evidence_return,
    )
    if payload != expected:
        raise ProductPlanError("payload_not_replay_equal")
    return True


compile_plan = compile_product_plan
validate_plan = validate_product_plan


__all__ = [
    "ALGORITHM_VERSION", "ProductPlanError", "SCHEMA", "compile_plan",
    "compile_product_plan", "stable_json", "validate_plan",
    "validate_product_plan",
]
