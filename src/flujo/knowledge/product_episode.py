"""Pure product-decision episode adapter for the MAK learning boundary.

This module records no episode.  It converts the common product plan and its
compiled consumers into a deterministic candidate that can be mapped to the
existing ``LearningStore.record_episode`` contract.  A later external receipt
is kept as an observation of the product decision; it never changes practice
claims, authorship or identity.
"""

from __future__ import annotations

import copy
import datetime as _datetime
import hashlib
import re
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import canonical_sha256_ref as _hash, stable_json

from .learning_policy import VERIFIED_OUTCOME_STATUSES, VERIFIED_VALIDATION_STATUSES
from .portfolio_dossier import validate_portfolio_dossier
from .project_ir import EPISODE_STATES


SCHEMA = "mak-product-episode-candidate-v1"
ALGORITHM_VERSION = "product-episode-adapter-1"
PLAN_SCHEMA = "mak-product-plan-v1"
DOSSIER_SCHEMA = "mak-portfolio-dossier-v1"
PACKAGE_SCHEMA = "mak-application-research-package-v1"
OUTCOME_RECEIPT_SCHEMA = "mak-product-outcome-receipt-v1"
PRODUCT_IDS = ("portfolio_dossier", "application_draft", "research_brief")
PRODUCT_SIGNAL_SCOPES = {
    "portfolio_dossier": ("attention", "ranking"),
    "application_draft": ("attention", "ranking"),
    "research_brief": ("query_selection", "voi_calibration"),
}
LEARNING_SCOPES = (
    "attention",
    "query_selection",
    "ranking",
    "voi_calibration",
)
FORBIDDEN_LEARNING_SCOPES = (
    "authorship",
    "claim_promotion",
    "identity",
    "truth",
)
SUCCESS_OUTCOME_STATUSES = frozenset(VERIFIED_OUTCOME_STATUSES)
FAILURE_OUTCOME_STATUSES = frozenset({"failed", "failure", "rejected"})
ACCEPTED_OUTCOME_STATUSES = SUCCESS_OUTCOME_STATUSES | FAILURE_OUTCOME_STATUSES
_VALID_CLAIM_STATUSES = frozenset({"supported", "candidate", "unknown"})
_HEX_SHA256 = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


class ProductEpisodeError(ValueError):
    """Raised when a product episode boundary is unsafe or ambiguous."""


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ProductEpisodeError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ProductEpisodeError(f"{field}_required")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductEpisodeError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProductEpisodeError(f"{field}_must_be_list")
    return value


def _refs(value: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    rows = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise ProductEpisodeError(f"{field}_invalid")
    result = sorted(set(item.strip() for item in rows))
    if not allow_empty and not result:
        raise ProductEpisodeError(f"{field}_empty")
    return result


def _hash_token(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _HEX_SHA256.fullmatch(result):
        raise ProductEpisodeError(f"{field}_not_sha256")
    digest = result[7:] if result.startswith("sha256:") else result
    return "sha256:" + digest.lower()


def _iso_datetime(value: Any, field: str) -> _datetime.datetime:
    text = _text(value, field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _datetime.datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ProductEpisodeError(f"{field}_invalid_iso8601") from error
    if parsed.tzinfo is None:
        raise ProductEpisodeError(f"{field}_timezone_required")
    return parsed


def _optional_iso(value: Any, field: str) -> str | None:
    if value is None:
        return None
    _iso_datetime(value, field)
    return _text(value, field)


def _input_hashes(
    product_plan: Mapping[str, Any],
    portfolio_dossier: Mapping[str, Any],
    application_package: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    return {
        "product_plan": _hash(product_plan),
        "portfolio_dossier": _hash(portfolio_dossier),
        "application_research_package": _hash(application_package),
        "outcome_receipt": _hash(outcome_receipt) if outcome_receipt is not None else None,
    }


def _identity_group(
    plan: Mapping[str, Any],
    dossier: Mapping[str, Any],
) -> dict[str, Any]:
    """Build archive grouping only from dossier's structured identity object."""
    identity = _mapping(dossier.get("practice_identity"), "portfolio_dossier.practice_identity")
    tenant = _text(identity.get("tenant"), "practice_identity.tenant")
    archive_id = _text(identity.get("archive_id"), "practice_identity.archive_id")
    snapshot_id = _text(identity.get("snapshot_id"), "practice_identity.snapshot_id")
    state_hash = _hash_token(identity.get("state_hash"), "practice_identity.state_hash")
    plan_hashes = _mapping(plan.get("input_hashes"), "product_plan.input_hashes")
    declared_state_hash = _hash_token(
        plan_hashes.get("practice_evidence_state"),
        "product_plan.input_hashes.practice_evidence_state",
    )
    if state_hash != declared_state_hash:
        raise ProductEpisodeError("practice_identity_state_hash_mismatch")

    plan_identity = plan.get("practice_identity")
    if isinstance(plan_identity, Mapping):
        for field, value in (("tenant", tenant), ("archive_id", archive_id), ("snapshot_id", snapshot_id)):
            if field in plan_identity and _text(plan_identity.get(field), f"plan.practice_identity.{field}") != value:
                raise ProductEpisodeError(f"practice_identity_{field}_mismatch")
        if "state_hash" in plan_identity and _hash_token(
            plan_identity.get("state_hash"), f"plan.practice_identity.state_hash"
        ) != state_hash:
            raise ProductEpisodeError("practice_identity_state_hash_mismatch")
    elif plan_identity is not None and not isinstance(plan_identity, str):
        raise ProductEpisodeError("plan.practice_identity_invalid")

    group_semantics: dict[str, str] = {
        "tenant": tenant,
        "archive_id": archive_id,
    }
    group = {
        "group_id": "identity-group:" + hashlib.sha256(
            stable_json(group_semantics).encode("utf-8")
        ).hexdigest()[:32],
        "tenant": tenant,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "state_hash": state_hash,
    }
    if "artist_identity" in identity:
        artist_identity = _text(identity.get("artist_identity"), "practice_identity.artist_identity")
        group["artist_identity"] = artist_identity
        group_semantics["artist_identity"] = artist_identity
        group["group_id"] = "identity-group:" + hashlib.sha256(
            stable_json(group_semantics).encode("utf-8")
        ).hexdigest()[:32]
    return group


def _signal_scopes(product_id: str) -> list[str]:
    try:
        return list(PRODUCT_SIGNAL_SCOPES[product_id])
    except KeyError as error:
        raise ProductEpisodeError("product_signal_scope_product_unknown") from error


def _validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("schema") != PLAN_SCHEMA:
        raise ProductEpisodeError("product_plan_schema_invalid")
    for field in (
        "opportunity_id", "selected_programs", "claim_index", "asset_index",
        "practice_evidence_refs", "targets", "control", "input_hashes",
    ):
        if field not in plan:
            raise ProductEpisodeError(f"product_plan_{field}_missing")
    opportunity_id = _text(plan.get("opportunity_id"), "product_plan.opportunity_id")
    input_hashes = _mapping(plan.get("input_hashes"), "product_plan.input_hashes")
    if not input_hashes or any(not isinstance(value, str) or not value for value in input_hashes.values()):
        raise ProductEpisodeError("product_plan_input_hashes_invalid")
    control = _mapping(plan.get("control"), "product_plan.control")
    expected_control = {
        "promotion": "none",
        "training_permitted": False,
        "publication": False,
        "submission": False,
        "dispatch": False,
        "user_review_required": False,
    }
    if control != expected_control:
        raise ProductEpisodeError("product_plan_control_invalid")

    programs = _list(plan.get("selected_programs"), "product_plan.selected_programs")
    program_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(programs):
        row = _mapping(raw, f"product_plan.selected_programs[{index}]")
        program_id = _text(row.get("program_id"), "product_plan.program_id")
        if program_id in program_by_id:
            raise ProductEpisodeError("product_plan_program_id_collision")
        program_by_id[program_id] = row
        for field in (
            "unit_ids", "evidence_refs", "requirement_ids", "missing_requirement_ids",
            "risk_flags", "supported_claim_ids", "candidate_claim_ids",
        ):
            _refs(row.get(field, []), f"product_plan.program.{field}")

    practice_refs = set(_refs(
        plan.get("practice_evidence_refs"),
        "product_plan.practice_evidence_refs",
    ))
    assets = _list(plan.get("asset_index"), "product_plan.asset_index")
    asset_by_ref: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(assets):
        row = _mapping(raw, f"product_plan.asset_index[{index}]")
        artifact_ref = _text(row.get("artifact_ref"), "product_plan.artifact_ref")
        if artifact_ref in asset_by_ref:
            raise ProductEpisodeError("product_plan_artifact_ref_collision")
        asset_by_ref[artifact_ref] = row
        asset_evidence_refs = _refs(row.get("evidence_refs", []), "product_plan.asset.evidence_refs")
        if not {artifact_ref, *asset_evidence_refs}.issubset(practice_refs):
            raise ProductEpisodeError("product_plan_asset_evidence_ref_foreign")
        program_refs = _refs(row.get("program_ids", []), "product_plan.asset.program_ids")
        if not set(program_refs).issubset(program_by_id):
            raise ProductEpisodeError("product_plan_asset_program_ref_foreign")

    claims = _list(plan.get("claim_index"), "product_plan.claim_index")
    claim_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(claims):
        row = _mapping(raw, f"product_plan.claim_index[{index}]")
        claim_id = _text(row.get("claim_id"), "product_plan.claim_id")
        if claim_id in claim_by_id:
            raise ProductEpisodeError("product_plan_claim_id_collision")
        status = _text(row.get("status"), "product_plan.claim.status")
        if status not in _VALID_CLAIM_STATUSES:
            raise ProductEpisodeError("product_plan_claim_status_invalid")
        claim_by_id[claim_id] = row
        refs = _refs(row.get("evidence_refs", []), "product_plan.claim.evidence_refs")
        if not set(refs).issubset(practice_refs):
            raise ProductEpisodeError("product_plan_claim_evidence_ref_foreign")

    for row in program_by_id.values():
        supported = set(_refs(row.get("supported_claim_ids", []), "product_plan.program.supported_claim_ids"))
        candidate = set(_refs(row.get("candidate_claim_ids", []), "product_plan.program.candidate_claim_ids"))
        if supported & candidate:
            raise ProductEpisodeError("product_plan_claim_partition_overlap")
        if not (supported | candidate).issubset(claim_by_id):
            raise ProductEpisodeError("product_plan_program_claim_ref_foreign")
        if not set(_refs(row.get("evidence_refs", []), "product_plan.program.evidence_refs")).issubset(practice_refs):
            raise ProductEpisodeError("product_plan_program_evidence_ref_foreign")

    program_requirement_ids = {
        requirement_id
        for row in program_by_id.values()
        for requirement_id in _refs(
            row.get("requirement_ids", []), "product_plan.program.requirement_ids"
        )
    }
    research_requirement_ids: set[str] = set()
    for raw in _list(plan.get("research_jobs", []), "product_plan.research_jobs"):
        row = _mapping(raw, "product_plan.research_job")
        research_requirement_ids.update(_refs(
            row.get("requirement_ids", []),
            "product_plan.research_job.requirement_ids",
        ))

    targets = _mapping(plan.get("targets"), "product_plan.targets")
    if set(targets) != set(PRODUCT_IDS):
        raise ProductEpisodeError("product_plan_target_keys_invalid")
    for product_id in PRODUCT_IDS:
        target = _mapping(targets[product_id], f"product_plan.target.{product_id}")
        if target.get("status") not in {"draftable", "blocked", "not_required"}:
            raise ProductEpisodeError("product_plan_target_status_invalid")

    decision_at = None
    for key in ("decision_at", "selected_at", "compiled_at"):
        if key in plan:
            candidate = _optional_iso(plan.get(key), f"product_plan.{key}")
            if decision_at is not None and candidate != decision_at:
                raise ProductEpisodeError("product_plan_decision_timestamp_conflict")
            decision_at = candidate
    return {
        "opportunity_id": opportunity_id,
        "program_by_id": program_by_id,
        "claim_by_id": claim_by_id,
        "asset_by_ref": asset_by_ref,
        "practice_refs": practice_refs,
        "program_requirement_ids": program_requirement_ids,
        "research_requirement_ids": research_requirement_ids,
        "requirement_ids": program_requirement_ids | research_requirement_ids,
        "targets": targets,
        "decision_at": decision_at,
    }


def _validate_dossier(
    dossier: Mapping[str, Any],
    opportunity_id: str,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if dossier.get("schema") != DOSSIER_SCHEMA:
        raise ProductEpisodeError("portfolio_dossier_schema_invalid")
    errors = validate_portfolio_dossier(dossier)
    if errors:
        raise ProductEpisodeError("portfolio_dossier_contract_invalid:" + ",".join(errors))
    if _text(dossier.get("opportunity_id"), "portfolio_dossier.opportunity_id") != opportunity_id:
        raise ProductEpisodeError("portfolio_dossier_opportunity_mismatch")
    rows = _list(dossier.get("selected_programs"), "portfolio_dossier.selected_programs")
    dossier_program_ids = {
        _text(row.get("program_id"), "portfolio_dossier.program_id")
        for row in rows
        if isinstance(row, Mapping)
    }
    program_ids = set(context["program_by_id"])
    if dossier_program_ids != program_ids:
        raise ProductEpisodeError("portfolio_dossier_program_refs_mismatch")
    plan_claim_ids = set(context["claim_by_id"])
    plan_asset_refs = set(context["asset_by_ref"])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        program_evidence = set(_refs(
            row.get("evidence_refs", []),
            "portfolio_dossier.program.evidence_refs",
        ))
        if not program_evidence.issubset(context["practice_refs"]):
            raise ProductEpisodeError("portfolio_dossier_program_evidence_ref_foreign")
        claim_refs = set(_refs(
            row.get("supported_claim_ids", []),
            "portfolio_dossier.program.supported_claim_ids",
        )) | set(_refs(
            row.get("candidate_claim_ids", []),
            "portfolio_dossier.program.candidate_claim_ids",
        ))
        if not claim_refs.issubset(plan_claim_ids):
            raise ProductEpisodeError("portfolio_dossier_program_claim_ref_foreign")
    for raw in _list(dossier.get("claim_index"), "portfolio_dossier.claim_index"):
        row = _mapping(raw, "portfolio_dossier.claim")
        claim_id = _text(row.get("claim_id"), "portfolio_dossier.claim_id")
        if claim_id not in plan_claim_ids:
            raise ProductEpisodeError("portfolio_dossier_claim_ref_foreign")
        if not set(_refs(
            row.get("evidence_refs", []), "portfolio_dossier.claim.evidence_refs"
        )).issubset(context["practice_refs"]):
            raise ProductEpisodeError("portfolio_dossier_claim_evidence_ref_foreign")
    for raw in _list(dossier.get("asset_manifest"), "portfolio_dossier.asset_manifest"):
        row = _mapping(raw, "portfolio_dossier.asset")
        if _text(row.get("artifact_ref"), "portfolio_dossier.artifact_ref") not in plan_asset_refs:
            raise ProductEpisodeError("portfolio_dossier_asset_ref_foreign")
    return {
        "status": _text(dossier.get("status"), "portfolio_dossier.status"),
        "narrative_atom_count": len(_list(dossier.get("narrative_atoms"), "portfolio_dossier.narrative_atoms")),
        "requirement_coverage": copy.deepcopy(_list(dossier.get("requirement_coverage"), "portfolio_dossier.requirement_coverage")),
        "asset_count": len(_list(dossier.get("asset_manifest"), "portfolio_dossier.asset_manifest")),
    }


def _validate_package(
    package: Mapping[str, Any],
    opportunity_id: str,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if package.get("schema") != PACKAGE_SCHEMA:
        raise ProductEpisodeError("application_research_package_schema_invalid")
    application = _mapping(package.get("application_draft"), "application_research_package.application_draft")
    research = _mapping(package.get("research_brief"), "application_research_package.research_brief")
    controls = _mapping(package.get("controls"), "application_research_package.controls")
    expected_controls = {
        "submission": False,
        "dispatch": False,
        "promotion": "none",
        "training_permitted": False,
        "user_review_required": False,
    }
    if controls != expected_controls:
        raise ProductEpisodeError("application_research_package_control_invalid")
    if _text(application.get("opportunity_id"), "application.opportunity_id") != opportunity_id:
        raise ProductEpisodeError("application_opportunity_mismatch")
    package_program_ids = set(_refs(application.get("program_ids"), "application.program_ids"))
    program_ids = set(context["program_by_id"])
    if package_program_ids != program_ids:
        raise ProductEpisodeError("application_program_refs_mismatch")
    if application.get("submission") is not False or research.get("dispatch") is not False:
        raise ProductEpisodeError("application_research_package_external_action_enabled")
    jobs = _list(research.get("jobs"), "application_research_package.research_jobs")
    requirement_ids = set(context["requirement_ids"])
    for raw in _list(application.get("programs"), "application.programs"):
        row = _mapping(raw, "application.program")
        if _text(row.get("program_id"), "application.program_id") not in program_ids:
            raise ProductEpisodeError("application_program_ref_foreign")
        if not set(_refs(
            row.get("evidence_refs", []), "application.program.evidence_refs"
        )).issubset(context["practice_refs"]):
            raise ProductEpisodeError("application_program_evidence_ref_foreign")
        if not set(_refs(
            row.get("requirement_ids", []), "application.program.requirement_ids"
        )).issubset(context["program_requirement_ids"]):
            raise ProductEpisodeError("application_program_requirement_ref_foreign")
    for raw in jobs:
        row = _mapping(raw, "application_research_package.research_job")
        if row.get("dispatch") is not False:
            raise ProductEpisodeError("application_research_job_dispatch_enabled")
        declared = row.get("requirement_ids")
        if declared is None and row.get("requirement_id") is not None:
            declared = [row.get("requirement_id")]
        for requirement_id in _refs(declared or [], "application.research_job.requirement_ids"):
            if requirement_id not in requirement_ids and not requirement_id.startswith("source-validity:"):
                raise ProductEpisodeError("application_research_requirement_ref_foreign")
    return {
        "application_status": _text(application.get("status"), "application.status"),
        "research_status": _text(research.get("status"), "research.status"),
        "research_job_count": len(jobs),
    }


def _source_refs(receipt: Mapping[str, Any]) -> list[dict[str, str]]:
    rows = _list(receipt.get("source_refs"), "outcome.source_refs")
    if not rows:
        raise ProductEpisodeError("outcome_source_refs_required")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"outcome.source_refs[{index}]")
        ref = _text(row.get("ref"), "outcome.source_ref")
        if ref in seen:
            raise ProductEpisodeError("outcome_source_ref_collision")
        seen.add(ref)
        digest = _hash_token(row.get("sha256"), "outcome.source_ref.sha256")
        output.append({"ref": ref, "sha256": digest})
    return sorted(output, key=lambda row: row["ref"])


def _outcome(
    receipt: Mapping[str, Any] | None,
    *,
    opportunity_id: str,
    product_ids: set[str],
    program_ids: set[str],
    decision_at: str | None,
) -> dict[str, Any]:
    if receipt is None:
        return {
            "status": "unresolved",
            "eligible": False,
            "eligibility": "not_observed",
            "reason_codes": ["outcome_not_received"],
            "outcome_id": None,
            "product_id": None,
            "program_id": None,
            "opportunity_id": opportunity_id,
            "observed_at": None,
            "source_refs": [],
            "label_candidate": None,
            "artistic_facts_unchanged": True,
            "training_permitted": False,
        }
    if receipt.get("schema") != OUTCOME_RECEIPT_SCHEMA:
        raise ProductEpisodeError("outcome_receipt_schema_invalid")
    outcome_id = _text(receipt.get("outcome_id"), "outcome.outcome_id")
    product_id = _text(receipt.get("product_id"), "outcome.product_id")
    program_id = _text(receipt.get("program_id"), "outcome.program_id")
    receipt_opportunity_id = _text(receipt.get("opportunity_id"), "outcome.opportunity_id")
    if product_id not in product_ids:
        raise ProductEpisodeError("outcome_product_ref_foreign")
    if program_id not in program_ids:
        raise ProductEpisodeError("outcome_program_ref_foreign")
    if receipt_opportunity_id != opportunity_id:
        raise ProductEpisodeError("outcome_opportunity_ref_foreign")
    observed_at = _text(receipt.get("observed_at"), "outcome.observed_at")
    observed_dt = _iso_datetime(observed_at, "outcome.observed_at")
    source_refs = _source_refs(receipt)
    validation = _mapping(receipt.get("validation"), "outcome.validation")
    validation_status = _text(validation.get("status"), "outcome.validation.status").casefold()
    validator = _text(validation.get("validator"), "outcome.validation.validator")
    checks = _refs(validation.get("checks"), "outcome.validation.checks", allow_empty=False)
    if validation_status not in VERIFIED_VALIDATION_STATUSES:
        raise ProductEpisodeError("outcome_validation_not_passed")
    status = _text(receipt.get("status"), "outcome.status").casefold()
    if status not in ACCEPTED_OUTCOME_STATUSES:
        raise ProductEpisodeError("outcome_status_not_verifiable")

    reasons: list[str] = []
    if decision_at is None:
        reasons.append("decision_timestamp_missing")
    else:
        if observed_dt <= _iso_datetime(decision_at, "product_plan.decision_at"):
            reasons.append("outcome_not_posterior_to_decision")
    eligible = not reasons
    label = "success" if status in SUCCESS_OUTCOME_STATUSES else "failure"
    signal_scopes = _signal_scopes(product_id)
    label_candidate = {
        "status": "candidate",
        "label": label,
        "external_status": status,
        "signal_scopes": signal_scopes,
        "source_outcome_id": outcome_id,
        "training_permitted": False,
        "not_practice_truth": True,
    } if eligible else None
    return {
        "status": status if eligible else "unresolved",
        "eligible": eligible,
        "eligibility": "verified_external_receipt" if eligible else "ineligible",
        "reason_codes": sorted(reasons),
        "outcome_id": outcome_id,
        "product_id": product_id,
        "program_id": program_id,
        "opportunity_id": opportunity_id,
        "observed_at": observed_at,
        "source_refs": source_refs,
        "validation": {"status": validation_status, "validator": validator, "checks": checks},
        "label_candidate": label_candidate,
        "artistic_facts_unchanged": True,
        "training_permitted": False,
    }


def _decision(plan: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    programs = context["program_by_id"]
    targets = context["targets"]
    program_rows = []
    for program_id, row in sorted(programs.items()):
        program_rows.append({
            "program_id": program_id,
            "selection": _text(row.get("selection"), "product_plan.program.selection", required=False) or "unknown",
            "rank": row.get("rank"),
            "ready": row.get("ready") is True,
            "source_gate_status": row.get("source_gate_status"),
            "hard_gate_status": row.get("hard_gate_status"),
        })
    product_ids = sorted(
        product_id for product_id in PRODUCT_IDS
        if _mapping(targets[product_id], f"product_plan.target.{product_id}").get("status") != "not_required"
    )
    return {
        "kind": "common_product_plan_selection",
        "opportunity_id": context["opportunity_id"],
        "selected_program_ids": sorted(programs),
        "selected_product_ids": product_ids,
        "programs": program_rows,
        "target_statuses": {
            product_id: _mapping(targets[product_id], f"product_plan.target.{product_id}").get("status")
            for product_id in PRODUCT_IDS
        },
        "source": "mak-product-plan-v1",
    }


def _observation(
    plan: Mapping[str, Any],
    context: Mapping[str, Any],
    dossier_state: Mapping[str, Any],
    package_state: Mapping[str, Any],
    identity_group: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_refs = set(context["practice_refs"])
    gate_rows = []
    for program_id, row in sorted(context["program_by_id"].items()):
        gate_rows.append({
            "program_id": program_id,
            "ready": row.get("ready") is True,
            "source_gate_status": row.get("source_gate_status"),
            "hard_gate_status": row.get("hard_gate_status"),
            "missing_requirement_ids": _refs(row.get("missing_requirement_ids", []), "program.missing_requirement_ids"),
            "risk_flags": _refs(row.get("risk_flags", []), "program.risk_flags"),
        })
    claims = _list(plan.get("claim_index"), "product_plan.claim_index")
    return {
        "status": "observed",
        "practice_identity": copy.deepcopy(plan.get("practice_identity")),
        "identity_group": copy.deepcopy(dict(identity_group)),
        "practice_snapshot_hash": _mapping(plan.get("input_hashes"), "product_plan.input_hashes").get("practice_evidence_state"),
        "evidence_refs": sorted(evidence_refs),
        "program_gates": gate_rows,
        "product_gates": {
            "portfolio_dossier": dossier_state["status"],
            "application_draft": package_state["application_status"],
            "research_brief": package_state["research_status"],
        },
        "signal_scopes_by_product": {
            product_id: _signal_scopes(product_id)
            for product_id in PRODUCT_IDS
        },
        "requirement_coverage": copy.deepcopy(dossier_state["requirement_coverage"]),
        "counts": {
            "programs": len(context["program_by_id"]),
            "claims": len(claims),
            "assets": len(context["asset_by_ref"]),
            "narrative_atoms": dossier_state["narrative_atom_count"],
            "research_jobs": package_state["research_job_count"],
        },
        "truth_promotions": 0,
        "artistic_facts_changed": False,
    }


def _project_id(plan: Mapping[str, Any]) -> str | None:
    explicit = plan.get("project_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    identity = plan.get("practice_identity")
    if isinstance(identity, Mapping):
        value = identity.get("project_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _record_projection(
    *,
    plan: Mapping[str, Any],
    decision: Mapping[str, Any],
    observation: Mapping[str, Any],
    outcome: Mapping[str, Any],
    validation: Mapping[str, Any],
    episode_id: str,
    parent_episode_id: str | None,
    decision_at: str | None,
) -> dict[str, Any]:
    record_status = "proposed" if outcome.get("eligible") is True else "needs_evidence"
    if record_status not in EPISODE_STATES:
        raise ProductEpisodeError("record_episode_status_invalid")
    return {
        "project_id": _project_id(plan),
        "objective": "evaluate compiled product decision",
        "phase": "product_compilation",
        "action": copy.deepcopy(dict(decision)),
        "observation": copy.deepcopy(dict(observation)),
        "outcome": copy.deepcopy(dict(outcome)),
        "validation": copy.deepcopy(dict(validation)),
        "status": record_status,
        "provider": "mak-product-episode-adapter",
        "model": "",
        "cost": {},
        "parent_episode_id": parent_episode_id,
        "episode_id": episode_id,
        "started_at": decision_at,
        "finished_at": outcome.get("observed_at") if outcome.get("eligible") else None,
        "source_snapshot_hash": "",
        "code_commit": "",
        "tool_versions": {},
    }


def _validate_payload(payload: Mapping[str, Any]) -> bool:
    required = {
        "schema", "algorithm_version", "status", "episode_id", "episode_hash", "parent_episode_id",
        "parent_hash", "input_hashes", "opportunity_id", "product_ids", "program_ids",
        "decision", "observation", "outcome", "learning_scope", "forbidden_learning_scopes",
        "control", "provenance", "reconciliation", "record_episode_projection",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ProductEpisodeError("product_episode_payload_fields_invalid")
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ProductEpisodeError("product_episode_payload_schema_invalid")
    if payload.get("status") not in {"open", "unresolved", "candidate"}:
        raise ProductEpisodeError("product_episode_status_invalid")
    episode_id = _text(payload.get("episode_id"), "episode_id")
    if not episode_id.startswith("episode:product:"):
        raise ProductEpisodeError("episode_id_prefix_invalid")
    _hash_token(payload.get("episode_hash"), "episode_hash")
    parent = payload.get("parent_episode_id")
    if parent is not None:
        _text(parent, "parent_episode_id")
    if payload.get("parent_hash") is not None:
        _hash_token(payload.get("parent_hash"), "parent_hash")
    input_hashes = _mapping(payload.get("input_hashes"), "input_hashes")
    if set(input_hashes) != {"product_plan", "portfolio_dossier", "application_research_package", "outcome_receipt"}:
        raise ProductEpisodeError("input_hash_keys_invalid")
    for key, value in input_hashes.items():
        if value is not None:
            _hash_token(value, f"input_hashes.{key}")
    opportunity_id = _text(payload.get("opportunity_id"), "opportunity_id")
    product_ids = _refs(payload.get("product_ids"), "product_ids")
    program_ids = _refs(payload.get("program_ids"), "program_ids")
    decision = _mapping(payload.get("decision"), "decision")
    if _text(decision.get("opportunity_id"), "decision.opportunity_id") != opportunity_id:
        raise ProductEpisodeError("decision_opportunity_mismatch")
    if _refs(decision.get("selected_product_ids"), "decision.selected_product_ids") != product_ids:
        raise ProductEpisodeError("decision_product_ids_mismatch")
    if _refs(decision.get("selected_program_ids"), "decision.selected_program_ids") != program_ids:
        raise ProductEpisodeError("decision_program_ids_mismatch")
    observation = _mapping(payload.get("observation"), "observation")
    evidence_refs = _refs(observation.get("evidence_refs"), "observation.evidence_refs")
    identity_group = _mapping(observation.get("identity_group"), "observation.identity_group")
    tenant = _text(identity_group.get("tenant"), "identity_group.tenant")
    archive_id = _text(identity_group.get("archive_id"), "identity_group.archive_id")
    _text(identity_group.get("snapshot_id"), "identity_group.snapshot_id")
    _hash_token(identity_group.get("state_hash"), "identity_group.state_hash")
    group_semantics = {"tenant": tenant, "archive_id": archive_id}
    if "artist_identity" in identity_group:
        group_semantics["artist_identity"] = _text(
            identity_group.get("artist_identity"), "identity_group.artist_identity"
        )
    expected_group_id = "identity-group:" + hashlib.sha256(
        stable_json(group_semantics).encode("utf-8")
    ).hexdigest()[:32]
    if identity_group.get("group_id") != expected_group_id:
        raise ProductEpisodeError("identity_group_id_invalid")
    signal_scopes = _mapping(
        observation.get("signal_scopes_by_product"),
        "observation.signal_scopes_by_product",
    )
    if set(signal_scopes) != set(PRODUCT_IDS):
        raise ProductEpisodeError("observation_signal_scope_keys_invalid")
    for product_id in PRODUCT_IDS:
        if _refs(signal_scopes[product_id], f"observation.signal_scopes.{product_id}") != _signal_scopes(product_id):
            raise ProductEpisodeError("observation_signal_scope_invalid")
    if _hash_token(
        observation.get("practice_snapshot_hash"),
        "observation.practice_snapshot_hash",
    ) != _hash_token(identity_group.get("state_hash"), "identity_group.state_hash"):
        raise ProductEpisodeError("observation_identity_state_hash_mismatch")
    outcome = _mapping(payload.get("outcome"), "outcome")
    outcome_refs = _source_refs(outcome) if outcome.get("source_refs") else []
    if outcome.get("product_id") is not None and outcome.get("product_id") not in product_ids:
        raise ProductEpisodeError("payload_outcome_product_ref_foreign")
    if outcome.get("program_id") is not None and outcome.get("program_id") not in program_ids:
        raise ProductEpisodeError("payload_outcome_program_ref_foreign")
    if outcome.get("opportunity_id") != opportunity_id:
        raise ProductEpisodeError("payload_outcome_opportunity_mismatch")
    if not isinstance(outcome.get("eligible"), bool) or not isinstance(outcome.get("artistic_facts_unchanged"), bool):
        raise ProductEpisodeError("outcome_flags_invalid")
    label_candidate = outcome.get("label_candidate")
    if outcome.get("eligible"):
        candidate = _mapping(label_candidate, "outcome.label_candidate")
        if candidate.get("status") != "candidate" or candidate.get("training_permitted") is not False:
            raise ProductEpisodeError("outcome_label_candidate_invalid")
        expected_scopes = _signal_scopes(_text(outcome.get("product_id"), "outcome.product_id"))
        if _refs(candidate.get("signal_scopes"), "outcome.label_candidate.signal_scopes") != expected_scopes:
            raise ProductEpisodeError("outcome_label_signal_scope_invalid")
    elif label_candidate is not None:
        raise ProductEpisodeError("ineligible_outcome_label_candidate_present")
    provenance = _mapping(payload.get("provenance"), "provenance")
    if provenance.get("identity_group") != dict(identity_group):
        raise ProductEpisodeError("provenance_identity_group_mismatch")
    if provenance.get("signal_scopes_by_product") != dict(signal_scopes):
        raise ProductEpisodeError("provenance_signal_scope_mismatch")
    scopes = _refs(payload.get("learning_scope"), "learning_scope", allow_empty=False)
    if set(scopes) != set(LEARNING_SCOPES):
        raise ProductEpisodeError("learning_scope_invalid")
    forbidden = _refs(payload.get("forbidden_learning_scopes"), "forbidden_learning_scopes", allow_empty=False)
    if set(forbidden) != set(FORBIDDEN_LEARNING_SCOPES):
        raise ProductEpisodeError("forbidden_learning_scope_invalid")
    control = _mapping(payload.get("control"), "control")
    if control != {
        "database_write": False,
        "promotion": "none",
        "training_permitted": False,
        "user_review_required": False,
    }:
        raise ProductEpisodeError("control_invalid")
    reconciliation = _mapping(payload.get("reconciliation"), "reconciliation")
    if reconciliation.get("truth_promotions") != 0 or reconciliation.get("artistic_fact_mutations") != 0:
        raise ProductEpisodeError("reconciliation_truth_mutation_invalid")
    if reconciliation.get("outcome_source_ref_count") != len(outcome_refs):
        raise ProductEpisodeError("reconciliation_outcome_ref_count_invalid")
    projection = _mapping(payload.get("record_episode_projection"), "record_episode_projection")
    projection_fields = {
        "project_id", "objective", "phase", "action", "observation", "outcome",
        "validation", "status", "provider", "model", "cost", "parent_episode_id",
        "episode_id", "started_at", "finished_at", "source_snapshot_hash",
        "code_commit", "tool_versions",
    }
    if set(projection) != projection_fields or projection.get("episode_id") != episode_id:
        raise ProductEpisodeError("record_projection_fields_invalid")
    if projection.get("status") not in {"proposed", "needs_evidence"}:
        raise ProductEpisodeError("record_projection_status_invalid")
    if not isinstance(evidence_refs, list):
        raise ProductEpisodeError("observation_evidence_refs_invalid")
    return True


def _compile(
    product_plan: Mapping[str, Any],
    portfolio_dossier: Mapping[str, Any],
    application_package: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    plan = copy.deepcopy(dict(_mapping(product_plan, "product_plan")))
    dossier = copy.deepcopy(dict(_mapping(portfolio_dossier, "portfolio_dossier")))
    package = copy.deepcopy(dict(_mapping(application_package, "application_research_package")))
    receipt = copy.deepcopy(dict(outcome_receipt)) if outcome_receipt is not None else None
    context = _validate_plan(plan)
    program_ids = set(context["program_by_id"])
    dossier_state = _validate_dossier(dossier, context["opportunity_id"], context)
    package_state = _validate_package(package, context["opportunity_id"], context)
    identity_group = _identity_group(plan, dossier)
    product_ids = sorted(
        product_id for product_id in PRODUCT_IDS
        if context["targets"][product_id].get("status") != "not_required"
    )
    decision = _decision(plan, context)
    observation = _observation(
        plan, context, dossier_state, package_state, identity_group
    )
    outcome = _outcome(
        receipt,
        opportunity_id=context["opportunity_id"],
        product_ids=set(product_ids),
        program_ids=program_ids,
        decision_at=context["decision_at"],
    )
    parent_episode_id = None
    if receipt is not None and receipt.get("parent_episode_id") is not None:
        parent_episode_id = _text(receipt.get("parent_episode_id"), "outcome.parent_episode_id")
    if plan.get("parent_episode_id") is not None:
        plan_parent = _text(plan.get("parent_episode_id"), "product_plan.parent_episode_id")
        if parent_episode_id is not None and parent_episode_id != plan_parent:
            raise ProductEpisodeError("parent_episode_id_conflict")
        parent_episode_id = plan_parent
    input_hashes = _input_hashes(plan, dossier, package, receipt)
    parent_hash = _hash({"parent_episode_id": parent_episode_id}) if parent_episode_id else None
    semantic = {
        "algorithm_version": ALGORITHM_VERSION,
        "input_hashes": input_hashes,
        "parent_episode_id": parent_episode_id,
        "opportunity_id": context["opportunity_id"],
        "product_ids": product_ids,
        "program_ids": sorted(program_ids),
        "identity_group": identity_group,
        "decision": decision,
        "observation": observation,
        "outcome": outcome,
    }
    episode_hash = _hash(semantic)
    episode_id = "episode:product:" + episode_hash[7:39]
    episode_status = "candidate" if outcome["eligible"] else ("open" if receipt is None else "unresolved")
    validation = {
        "status": "passed" if outcome["eligible"] else "abstained",
        "checks": [
            "product_plan_contract",
            "portfolio_dossier_contract",
            "application_research_package_contract",
            "decision_observation_outcome_separated",
            "no_practice_truth_promotion",
        ],
        "outcome_eligible": outcome["eligible"],
        "training_permitted": False,
        "learning_scope": list(LEARNING_SCOPES),
    }
    projection = _record_projection(
        plan=plan,
        decision=decision,
        observation=observation,
        outcome=outcome,
        validation=validation,
        episode_id=episode_id,
        parent_episode_id=parent_episode_id,
        decision_at=context["decision_at"],
    )
    payload = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "status": episode_status,
        "episode_id": episode_id,
        "episode_hash": episode_hash,
        "parent_episode_id": parent_episode_id,
        "parent_hash": parent_hash,
        "input_hashes": input_hashes,
        "opportunity_id": context["opportunity_id"],
        "product_ids": product_ids,
        "program_ids": sorted(program_ids),
        "decision": decision,
        "observation": observation,
        "outcome": outcome,
        "learning_scope": list(LEARNING_SCOPES),
        "forbidden_learning_scopes": list(FORBIDDEN_LEARNING_SCOPES),
        "control": {
            "database_write": False,
            "promotion": "none",
            "training_permitted": False,
            "user_review_required": False,
        },
        "provenance": {
            "source_schemas": [PLAN_SCHEMA, DOSSIER_SCHEMA, PACKAGE_SCHEMA],
            "outcome_receipt_schema": OUTCOME_RECEIPT_SCHEMA if receipt is not None else None,
            "identity_group": copy.deepcopy(identity_group),
            "signal_scopes_by_product": {
                product_id: _signal_scopes(product_id)
                for product_id in PRODUCT_IDS
            },
            "deterministic": True,
            "source_rescan": False,
            "database_write": False,
            "record_episode_mappable": _project_id(plan) is not None,
            "promotion": "none",
            "training_permitted": False,
        },
        "reconciliation": {
            "program_count": len(program_ids),
            "product_count": len(product_ids),
            "practice_evidence_ref_count": len(observation["evidence_refs"]),
            "outcome_source_ref_count": len(outcome["source_refs"]),
            "outcome_eligible": outcome["eligible"],
            "truth_promotions": 0,
            "artistic_fact_mutations": 0,
            "training_permitted": False,
            "recorded": False,
        },
        "record_episode_projection": projection,
    }
    _validate_payload(payload)
    return payload


def compile_product_episode(
    product_plan: Mapping[str, Any],
    portfolio_dossier: Mapping[str, Any],
    application_package: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile a recordable-shaped episode candidate without persistence."""
    return _compile(product_plan, portfolio_dossier, application_package, outcome_receipt)


def validate_product_episode(
    product_plan: Mapping[str, Any],
    portfolio_dossier: Mapping[str, Any],
    application_package: Mapping[str, Any],
    payload: Mapping[str, Any],
    outcome_receipt: Mapping[str, Any] | None = None,
) -> bool:
    expected = _compile(product_plan, portfolio_dossier, application_package, outcome_receipt)
    if payload != expected:
        raise ProductEpisodeError("product_episode_payload_not_replay_equal")
    return True


compile_episode = compile_product_episode
validate_episode = validate_product_episode


__all__ = [
    "ACCEPTED_OUTCOME_STATUSES", "ALGORITHM_VERSION", "FORBIDDEN_LEARNING_SCOPES",
    "LEARNING_SCOPES", "OUTCOME_RECEIPT_SCHEMA", "PRODUCT_SIGNAL_SCOPES",
    "ProductEpisodeError", "SCHEMA",
    "compile_episode", "compile_product_episode", "stable_json", "validate_episode",
    "validate_product_episode",
]
