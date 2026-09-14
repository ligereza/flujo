"""Portable, evidence-bounded portfolio and curatorial dossier compiler.

The compiler consumes a product-plan projection and the accepted
mak-practice-evidence-state-v1 contract. It does not import a product-plan
producer, read an archive, open a database or publish an asset. Curatorial
ordering is retained as a provisional selection decision; it is never used to
upgrade an evidence status or to invent a title, author or work identity.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import canonical_sha256_ref as _hash, canonicalize as _canonical, optional_text as _text, stable_json


PLAN_SCHEMA = "mak-product-plan-v1"
PRACTICE_SCHEMA = "mak-practice-evidence-state-v1"
SCHEMA = "mak-portfolio-dossier-v1"
ALGORITHM_VERSION = "portfolio-dossier-1"
DOSSIER_HASH_ALGORITHM = "sha256-canonical-portfolio-dossier-without-hash-v1"

CLAIM_STATUSES = frozenset({"supported", "candidate", "unknown"})
CLAIM_TYPES = frozenset({"documented_fact", "candidate", "unknown"})
TRUTH_STATUSES = frozenset({"active", "verified", "promoted", "published", "truth"})
PROGRAM_STATUSES = frozenset({
    "candidate", "accepted", "provisional", "draft", "abstain", "abstained",
    "unresolved", "unknown", "selected",
})
PUBLIC_ELIGIBILITY = frozenset({"eligible", "unknown", "blocked"})
LICENSE_ALLOWLIST = frozenset({
    "cleared", "licensed", "explicitly_cleared", "public_domain", "cc0",
    "cc-by", "cc-by-sa", "cc-by-nc", "cc_by", "cc_by_sa", "cc_by_nc",
})
PRIVATE_VALUES = frozenset({"private", "restricted", "internal", "confidential", "blocked"})
TECHNICAL_CONTEXT_SCHEMA = "mak-project-context-v1"
TECHNICAL_CONTEXT_STATUSES = frozenset({"candidate", "observed"})


class PortfolioDossierError(ValueError):
    """Raised when a plan, practice state or dossier violates the boundary."""

    def __init__(self, message: str, errors: Sequence[str] | None = None) -> None:
        self.errors = list(errors or [])
        super().__init__(message)


def _copy_json(value: Any) -> Any:
    copied = copy.deepcopy(value)
    try:
        stable_json(copied)
    except (TypeError, ValueError) as error:
        raise PortfolioDossierError(f"input_not_json:{error}") from error
    return copied


_PRIVATE_KEYS = {
    "path", "relative_path", "root_ref", "root_path", "private_path",
    "raw", "raw_bytes", "content", "content_bytes",
}


def _safe_projection(value: Any, field: str) -> Any:
    copied = _copy_json(value)

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if _text(key).casefold() in _PRIVATE_KEYS:
                    raise PortfolioDossierError(f"{field}_private_field:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(copied)
    return copied


def _refs(value: Any, field: str, *, allow_empty: bool = True) -> tuple[list[str], str | None]:
    if not isinstance(value, list):
        return [], f"{field}_not_list"
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return [], f"{field}_invalid"
    result = sorted(set(value))
    if not allow_empty and not result:
        return [], f"{field}_empty"
    if result != value:
        return result, f"{field}_not_sorted_unique"
    return result, None


def _row_index(value: Any, field: str, id_field: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize list or id-keyed mapping without changing its input."""
    errors: list[str] = []
    if isinstance(value, list):
        raw_rows = [("", row) for row in value]
    elif isinstance(value, Mapping):
        raw_rows = [(str(key), row) for key, row in value.items()]
    else:
        return [], [f"{field}_not_list_or_map"]
    seen: dict[str, dict[str, Any]] = {}
    for index, (mapping_id, raw) in enumerate(raw_rows):
        if not isinstance(raw, Mapping):
            errors.append(f"{field}_{index}_not_object")
            continue
        row = _copy_json(dict(raw))
        row_id = _text(row.get(id_field)) or _text(mapping_id)
        if not row_id:
            errors.append(f"{field}_{index}_{id_field}_missing")
            continue
        row[id_field] = row_id
        prior = seen.get(row_id)
        if prior is not None and prior != row:
            errors.append(f"{field}_{id_field}_conflict:{row_id}")
            continue
        seen[row_id] = row
    return [seen[key] for key in sorted(seen)], errors


def _status(value: Any, default: str = "unknown") -> str:
    text = _text(value).casefold()
    if text in TRUTH_STATUSES:
        return text
    return text or default


def _practice_identity(plan: Mapping[str, Any], practice: Mapping[str, Any]) -> dict[str, Any]:
    raw = plan.get("practice_identity")
    if isinstance(raw, str):
        identity: dict[str, Any] = {"identity": _text(raw)}
    elif isinstance(raw, Mapping):
        identity = _safe_projection(dict(raw), "practice_identity")
    else:
        identity = {}
    for key in ("tenant", "archive_id", "snapshot_id", "input_hash", "state_hash"):
        value = _text(practice.get(key))
        if value:
            declared = _text(identity.get(key))
            if declared and declared != value:
                raise PortfolioDossierError(f"practice_identity_mismatch:{key}")
            identity[key] = value
    if not identity.get("archive_id") or not identity.get("snapshot_id"):
        raise PortfolioDossierError("practice_identity_missing_archive_or_snapshot")
    return {key: identity[key] for key in sorted(identity)}


def _validate_plan_shape(plan: Any) -> list[str]:
    if not isinstance(plan, Mapping):
        return ["plan_not_object"]
    errors: list[str] = []
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("plan_schema_invalid")
    required = {
        "opportunity_id", "practice_identity", "selected_programs", "claim_index",
        "asset_index", "targets", "gaps", "control",
    }
    errors.extend(f"plan_missing_{key}" for key in sorted(required - set(plan)))
    if not _text(plan.get("opportunity_id")):
        errors.append("plan_opportunity_id_missing")
    if not isinstance(plan.get("practice_identity"), (Mapping, str)):
        errors.append("plan_practice_identity_invalid")
    if not isinstance(plan.get("selected_programs"), list):
        errors.append("plan_selected_programs_invalid")
    if not isinstance(plan.get("targets"), Mapping):
        errors.append("plan_targets_invalid")
    elif "portfolio_dossier" not in plan["targets"]:
        errors.append("plan_portfolio_dossier_target_missing")
    if not isinstance(plan.get("gaps"), list):
        errors.append("plan_gaps_invalid")
    if not isinstance(plan.get("control"), Mapping):
        errors.append("plan_control_invalid")
    else:
        if plan["control"].get("publication") is True or plan["control"].get("export") is True:
            errors.append("plan_external_output_not_allowed")
        if plan["control"].get("promotion") not in {None, "none"}:
            errors.append("plan_promotion_not_none")
    return sorted(set(errors))


def _validate_practice_shape(practice: Any) -> list[str]:
    if not isinstance(practice, Mapping):
        return ["practice_not_object"]
    errors: list[str] = []
    if practice.get("schema") != PRACTICE_SCHEMA:
        errors.append("practice_schema_invalid")
    for key in ("archive_id", "snapshot_id", "input_hash"):
        if not _text(practice.get(key)):
            errors.append(f"practice_{key}_missing")
    for key in ("units", "artifacts"):
        if not isinstance(practice.get(key), list):
            errors.append(f"practice_{key}_invalid")
    if not isinstance(practice.get("claims"), Mapping):
        errors.append("practice_claims_invalid")
    return sorted(set(errors))


def _normalise_practice(
    practice: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    set[str],
    set[str],
    list[str],
]:
    errors: list[str] = []
    artifact_by_ref: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(practice.get("artifacts", [])):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_artifact_{index}_not_object")
            continue
        row = _copy_json(dict(raw))
        ref = _text(row.get("artifact_ref"))
        if not ref:
            errors.append(f"practice_artifact_{index}_ref_missing")
            continue
        prior = artifact_by_ref.get(ref)
        if prior is not None and prior != row:
            errors.append(f"practice_artifact_ref_conflict:{ref}")
        artifact_by_ref[ref] = row

    unit_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(practice.get("units", [])):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_unit_{index}_not_object")
            continue
        row = _copy_json(dict(raw))
        unit_id = _text(row.get("unit_id"))
        if not unit_id:
            errors.append(f"practice_unit_{index}_id_missing")
            continue
        if unit_id in unit_by_id and unit_by_id[unit_id] != row:
            errors.append(f"practice_unit_id_conflict:{unit_id}")
        unit_by_id[unit_id] = row

    claim_by_id: dict[str, dict[str, Any]] = {}
    raw_claims = practice.get("claims", {})
    for bucket, rows in raw_claims.items() if isinstance(raw_claims, Mapping) else []:
        if not isinstance(rows, list):
            errors.append(f"practice_claim_bucket_invalid:{bucket}")
            continue
        for index, raw in enumerate(rows):
            if not isinstance(raw, Mapping):
                errors.append(f"practice_claim_{bucket}_{index}_not_object")
                continue
            row = _copy_json(dict(raw))
            claim_id = _text(row.get("claim_id"))
            if not claim_id:
                errors.append(f"practice_claim_{bucket}_{index}_id_missing")
                continue
            row_status = _status(row.get("status"), bucket if bucket in CLAIM_STATUSES else "unknown")
            if row_status in TRUTH_STATUSES:
                errors.append(f"practice_claim_truth_status:{claim_id}")
                row_status = "unknown"
            if row_status not in CLAIM_STATUSES:
                errors.append(f"practice_claim_status_invalid:{claim_id}")
                row_status = "unknown"
            refs, ref_error = _refs(row.get("evidence_refs", []), f"practice_claim_{claim_id}_evidence_refs")
            if ref_error and ref_error != f"practice_claim_{claim_id}_evidence_refs_not_sorted_unique":
                errors.append(ref_error)
            requirements, req_error = _refs(row.get("requirement_ids", []), f"practice_claim_{claim_id}_requirement_ids")
            if req_error and req_error != f"practice_claim_{claim_id}_requirement_ids_not_sorted_unique":
                errors.append(req_error)
            row["status"] = row_status
            row["evidence_refs"] = refs
            row["requirement_ids"] = requirements
            prior = claim_by_id.get(claim_id)
            if prior is not None and prior != row:
                errors.append(f"practice_claim_id_conflict:{claim_id}")
            claim_by_id[claim_id] = row

    artifact_refs = set(artifact_by_ref)

    # Unit evidence is a wider explicit namespace than physical assets.
    # Candidate/observation refs are provenance, not publicable assets.
    practice_evidence_refs = set(artifact_refs)

    def collect_evidence_refs(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "evidence_refs" and isinstance(child, list):
                    practice_evidence_refs.update(
                        item for item in child
                        if isinstance(item, str) and item.strip()
                    )
                collect_evidence_refs(child)
        elif isinstance(value, list):
            for child in value:
                collect_evidence_refs(child)

    collect_evidence_refs(practice)
    for claim_id, claim in claim_by_id.items():
        for ref in claim["evidence_refs"]:
            if ref not in practice_evidence_refs:
                errors.append(f"practice_claim_evidence_ref_ajeno:{claim_id}:{ref}")
        unit_id = _text(claim.get("unit_id"))
        if unit_id and unit_id not in unit_by_id:
            errors.append(f"practice_claim_unit_ref_ajeno:{claim_id}:{unit_id}")
    for unit_id, unit in unit_by_id.items():
        member_refs = unit.get("member_refs", unit.get("artifact_refs", []))
        refs, ref_error = _refs(member_refs, f"practice_unit_{unit_id}_member_refs")
        if ref_error and ref_error != f"practice_unit_{unit_id}_member_refs_not_sorted_unique":
            errors.append(ref_error)
        for ref in refs:
            if ref not in artifact_refs:
                errors.append(f"practice_unit_member_ref_ajeno:{unit_id}:{ref}")
        dependency_refs, dependency_error = _refs(
            unit.get("dependency_refs", []),
            f"practice_unit_{unit_id}_dependency_refs",
        )
        if dependency_error and dependency_error != f"practice_unit_{unit_id}_dependency_refs_not_sorted_unique":
            errors.append(dependency_error)
        for ref in dependency_refs:
            if ref not in artifact_refs:
                errors.append(f"practice_unit_dependency_ref_ajeno:{unit_id}:{ref}")
    return (
        artifact_by_ref,
        unit_by_id,
        claim_by_id,
        artifact_refs,
        practice_evidence_refs,
        sorted(set(errors)),
    )


def _program_refs(program: Mapping[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = program.get(key)
        if isinstance(raw, list):
            values.extend(item for item in raw if isinstance(item, str) and item.strip())
    return sorted(set(values))


def _plan_claim_rows(plan: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    rows, errors = _row_index(plan.get("claim_index"), "plan_claim_index", "claim_id")
    result = {row["claim_id"]: row for row in rows}
    for claim_id, row in result.items():
        if _status(row.get("status")) in TRUTH_STATUSES:
            errors.append(f"plan_claim_truth_status:{claim_id}")
        refs, ref_error = _refs(row.get("evidence_refs", []), f"plan_claim_{claim_id}_evidence_refs")
        if ref_error and ref_error != f"plan_claim_{claim_id}_evidence_refs_not_sorted_unique":
            errors.append(ref_error)
        requirements, req_error = _refs(row.get("requirement_ids", []), f"plan_claim_{claim_id}_requirement_ids")
        if req_error and req_error != f"plan_claim_{claim_id}_requirement_ids_not_sorted_unique":
            errors.append(req_error)
        if "evidence_refs" in row:
            row["evidence_refs"] = refs
        if "requirement_ids" in row:
            row["requirement_ids"] = requirements
        if "status" in row:
            row["status"] = _status(row.get("status"))
    return result, sorted(set(errors))


def _merge_claims(
    plan_claims: Mapping[str, Mapping[str, Any]],
    practice_claims: Mapping[str, Mapping[str, Any]],
    selected_claim_ids: set[str],
    practice_evidence_refs: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    result: dict[str, dict[str, Any]] = {}
    for claim_id in sorted(selected_claim_ids):
        plan_row = dict(plan_claims.get(claim_id, {}))
        practice_row = dict(practice_claims.get(claim_id, {}))
        if not plan_row and not practice_row:
            errors.append(f"claim_ref_ajeno:{claim_id}")
            continue
        row = dict(practice_row)
        for key, value in plan_row.items():
            if key in {"evidence_refs", "requirement_ids", "unit_ids"} and not value:
                continue
            if key == "status" and "status" not in plan_row:
                continue
            row[key] = value
        practice_status = _status(practice_row.get("status")) if practice_row else "unknown"
        selected_status = _status(row.get("status"), practice_status)
        if selected_status in TRUTH_STATUSES:
            errors.append(f"claim_truth_promotion:{claim_id}")
            selected_status = "unknown"
        if selected_status not in CLAIM_STATUSES:
            errors.append(f"claim_status_invalid:{claim_id}")
            selected_status = "unknown"
        rank = {"unknown": 0, "candidate": 1, "supported": 2}
        if practice_row and rank[selected_status] > rank.get(practice_status, 0):
            errors.append(f"claim_status_promotion:{claim_id}")
        refs = _refs(row.get("evidence_refs", []), f"claim_{claim_id}_evidence_refs")[0]
        requirements = _refs(row.get("requirement_ids", []), f"claim_{claim_id}_requirement_ids")[0]
        for ref in refs:
            if ref not in practice_evidence_refs:
                errors.append(f"claim_evidence_ref_ajeno:{claim_id}:{ref}")
        row["claim_id"] = claim_id
        row["status"] = selected_status
        row["evidence_refs"] = refs
        row["requirement_ids"] = requirements
        row["unit_ids"] = _program_refs(row, "unit_ids") or (
            [_text(row["unit_id"])] if _text(row.get("unit_id")) else []
        )
        result[claim_id] = row
    return result, sorted(set(errors))


def _asset_eligibility(row: Mapping[str, Any], artifact: Mapping[str, Any]) -> str:
    private = row.get("private") is True or artifact.get("private") is True
    availability = _text(
        row.get("availability") or artifact.get("availability")
    ).casefold()
    if availability in {"missing", "unavailable", "unreadable", "inaccessible", "error", "blocked"}:
        return "blocked"
    privacy = _text(
        row.get("privacy") or row.get("visibility")
        or artifact.get("privacy") or artifact.get("visibility")
    ).casefold()
    if private or privacy in PRIVATE_VALUES:
        return "blocked"
    declared = row.get(
        "public_eligibility",
        row.get("public", artifact.get("public_eligibility", artifact.get("public"))),
    )
    if isinstance(declared, bool):
        declared = "eligible" if declared else "blocked"
    declared_text = _text(declared).casefold()
    if declared_text in {"blocked", "false", "no", "ineligible", "private"}:
        return "blocked"
    license_state = _text(
        row.get("license_state") or row.get("license")
        or artifact.get("license_state") or artifact.get("license")
    ).casefold()
    if declared_text in {"eligible", "public", "true", "yes"}:
        return "eligible" if license_state in LICENSE_ALLOWLIST else "blocked"
    return "eligible" if license_state in LICENSE_ALLOWLIST and declared_text else "unknown"


def _asset_rows(
    plan: Mapping[str, Any],
    artifact_by_ref: Mapping[str, Mapping[str, Any]],
    practice_evidence_refs: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows, errors = _row_index(plan.get("asset_index"), "plan_asset_index", "artifact_ref")
    output: list[dict[str, Any]] = []
    for row in rows:
        ref = row["artifact_ref"]
        artifact = artifact_by_ref.get(ref)
        if artifact is None:
            errors.append(f"asset_ref_ajeno:{ref}")
            continue
        program_ids = _program_refs(row, "program_ids")
        if _text(row.get("program_id")):
            program_ids = sorted(set(program_ids + [_text(row["program_id"])]))
        proposed_function = _text(
            row.get("function") or row.get("proposed_function") or row.get("role")
        ) or "unassigned_asset_candidate"
        eligibility = _asset_eligibility(row, artifact)
        evidence_refs = _refs(
            row.get("evidence_refs", artifact.get("evidence_refs", [])),
            f"asset_{ref}_evidence_refs",
        )[0]
        for evidence_ref in evidence_refs:
            if evidence_ref not in practice_evidence_refs:
                errors.append(f"asset_evidence_ref_ajeno:{ref}:{evidence_ref}")
        # Non-physical candidate/observation refs remain provenance on the
        # unit/sequence; they must never become asset or public-manifest refs.
        evidence_refs = [
            evidence_ref for evidence_ref in evidence_refs
            if evidence_ref in artifact_by_ref
        ]
        output.append({
            "artifact_ref": ref,
            "physical_id": _text(artifact.get("physical_id")) or None,
            "content_id": _text(artifact.get("content_id")) or None,
            "proposed_function": proposed_function,
            "public_eligibility": eligibility,
            "program_ids": program_ids,
            "evidence_refs": evidence_refs,
            "license_state": _text(
                row.get("license_state") or row.get("license")
                or artifact.get("license_state") or artifact.get("license")
            ) or "unknown",
        })
    return sorted(output, key=lambda item: item["artifact_ref"]), sorted(set(errors))


def _selected_programs(
    plan: Mapping[str, Any],
    unit_by_id: Mapping[str, Mapping[str, Any]],
    claim_by_id: Mapping[str, Mapping[str, Any]],
    artifact_refs: set[str],
    practice_evidence_refs: set[str],
) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    rows, errors = _row_index(plan.get("selected_programs"), "selected_programs", "program_id")
    output: list[dict[str, Any]] = []
    selected_claim_ids: set[str] = set()
    for row in rows:
        program_id = row["program_id"]
        status = _status(row.get("status"), "candidate")
        if status in TRUTH_STATUSES:
            errors.append(f"program_truth_status:{program_id}")
        if status not in PROGRAM_STATUSES:
            errors.append(f"program_status_invalid:{program_id}")
            status = "unknown"
        selection = _text(row.get("selection")).casefold()
        selection_basis = _text(row.get("selection_basis")).casefold()
        research_first_without_unit = (
            selection in {"abstained_research_first", "research_first"}
            or selection_basis in {"abstained_research_first", "research_first"}
        ) and row.get("ready") is False
        unit_ids, unit_error = _refs(
            row.get("unit_ids", []),
            f"program_{program_id}_unit_ids",
            allow_empty=research_first_without_unit,
        )
        if unit_error and unit_error != f"program_{program_id}_unit_ids_not_sorted_unique":
            errors.append(unit_error)
        for unit_id in unit_ids:
            unit = unit_by_id.get(unit_id)
            if unit is None:
                errors.append(f"program_unit_ref_ajeno:{program_id}:{unit_id}")
            else:
                unit_evidence_refs = _refs(
                    unit.get("evidence_refs", []),
                    f"unit_{unit_id}_evidence_refs",
                )[0]
                # Unit evidence may be an observation/candidate namespace;
                # it is not an asset and must never enter an asset manifest.
                for ref in unit_evidence_refs:
                    if ref not in practice_evidence_refs:
                        errors.append(f"unit_evidence_ref_ajeno:{unit_id}:{ref}")
                dependency_refs = _refs(
                    unit.get("dependency_refs", []),
                    f"unit_{unit_id}_dependency_refs",
                )[0]
                for ref in dependency_refs:
                    if ref not in artifact_refs:
                        errors.append(f"unit_dependency_ref_ajeno:{unit_id}:{ref}")
        requirement_ids = _refs(
            row.get("requirement_ids", []), f"program_{program_id}_requirement_ids"
        )[0]
        supported = _refs(
            row.get("supported_claim_ids", []), f"program_{program_id}_supported_claim_ids"
        )[0]
        candidate = _refs(
            row.get("candidate_claim_ids", []), f"program_{program_id}_candidate_claim_ids"
        )[0]
        # The accepted plan's supported/candidate partitions are the only
        # claim bindings allowed to drive narrative atoms.  A broad legacy
        # claim_ids field must not silently turn an unselected claim into a
        # dossier statement.
        claim_ids = sorted(set(supported + candidate))
        if set(supported) & set(candidate):
            errors.append(f"program_claim_partition_overlap:{program_id}")
        selected_claim_ids.update(claim_ids)
        for claim_id in claim_ids:
            if claim_id not in claim_by_id:
                errors.append(f"program_claim_ref_ajeno:{program_id}:{claim_id}")
        evidence_refs = _refs(
            row.get("evidence_refs", []), f"program_{program_id}_evidence_refs"
        )[0]
        for ref in evidence_refs:
            if ref not in practice_evidence_refs:
                errors.append(f"program_evidence_ref_ajeno:{program_id}:{ref}")
        asset_refs = _program_refs(row, "asset_refs", "artifact_refs", "resource_refs")
        for ref in asset_refs:
            if ref not in artifact_refs:
                errors.append(f"program_asset_ref_ajeno:{program_id}:{ref}")
        missing = _refs(
            row.get("missing_requirement_ids", []),
            f"program_{program_id}_missing_requirement_ids",
        )[0]
        if not set(missing) <= set(requirement_ids):
            errors.append(f"program_missing_requirement_ref_ajeno:{program_id}")
        rank = None
        rank_source = None
        for rank_key in ("rank", "sequence_rank", "curatorial_rank", "priority_rank"):
            raw_rank = row.get(rank_key)
            if isinstance(raw_rank, int) and not isinstance(raw_rank, bool) and raw_rank > 0:
                rank = raw_rank
                rank_source = rank_key
                break
        emphasis = _refs(
            row.get("emphasis_claim_ids", []), f"program_{program_id}_emphasis_claim_ids"
        )[0]
        if not set(emphasis) <= set(claim_ids):
            errors.append(f"program_emphasis_claim_ref_ajeno:{program_id}")
        output.append({
            "program_id": program_id,
            "status": status,
            "unit_ids": unit_ids,
            "requirement_ids": requirement_ids,
            "supported_claim_ids": supported,
            "candidate_claim_ids": candidate,
            "claim_ids": claim_ids,
            "evidence_refs": evidence_refs,
            "asset_refs": asset_refs,
            "missing_requirement_ids": missing,
            "alternatives": _refs(
                row.get("alternatives", []), f"program_{program_id}_alternatives"
            )[0],
            "emphasis_claim_ids": emphasis,
            "rank": rank,
            "sequence_rank": rank,
            "rank_source": rank_source,
            "selection_basis": _text(row.get("selection_basis")) or "product_plan_selection",
        })
    output.sort(key=lambda row: (row["sequence_rank"] is None, row["sequence_rank"] or 0, row["program_id"]))
    return output, selected_claim_ids, sorted(set(errors))


def _narrative_atoms(claims: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = []
    for claim_id in sorted(claims):
        row = claims[claim_id]
        status = row["status"]
        atom_type = {
            "supported": "documented_fact",
            "candidate": "candidate",
            "unknown": "unknown",
        }[status]
        evidence_refs = list(row.get("evidence_refs", []))
        if status == "supported" and not evidence_refs:
            atom_type = "unknown"
        semantic = {
            "claim_id": claim_id,
            "type": atom_type,
            "statement": _text(row.get("statement") or row.get("value")),
            "evidence_refs": evidence_refs,
            "requirement_ids": list(row.get("requirement_ids", [])),
            "unit_ids": list(row.get("unit_ids", [])),
        }
        atoms.append({
            "atom_id": "atom:" + hashlib.sha256(stable_json(semantic).encode("utf-8")).hexdigest()[:32],
            **semantic,
            "status": "provisional" if atom_type != "documented_fact" else "documented",
        })
    return atoms


def _sequence(
    programs: Sequence[Mapping[str, Any]],
    unit_by_id: Mapping[str, Mapping[str, Any]],
    claims: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    explicit_rank = any(row.get("rank") is not None for row in programs)
    explicit_legacy_rank = any(
        row.get("rank") is not None and row.get("rank_source") != "rank"
        for row in programs
    )
    if explicit_rank and not explicit_legacy_rank:
        basis = "explicit_plan_rank"
    elif explicit_rank:
        basis = "explicit_plan_rank_with_legacy_alias"
    else:
        basis = "deterministic_program_id"
    sequence: list[dict[str, Any]] = []
    for position, program in enumerate(programs, 1):
        program_id = program["program_id"]
        sequence.append({
            "sequence_kind": "program",
            "position": position,
            "program_id": program_id,
            "unit_ids": list(program["unit_ids"]),
            "status": "provisional_selection",
            "order_basis": basis,
            "selection_basis": program["selection_basis"],
            "emphasis_claim_ids": list(program["emphasis_claim_ids"]),
            "evidence_refs": list(program["evidence_refs"]),
        })
        for unit_position, unit_id in enumerate(sorted(program["unit_ids"]), 1):
            unit = unit_by_id[unit_id]
            unit_refs = _refs(unit.get("evidence_refs", []), f"unit_{unit_id}_evidence_refs")[0]
            sequence.append({
                "sequence_kind": "unit",
                "position": position,
                "unit_position": unit_position,
                "program_id": program_id,
                "unit_id": unit_id,
                "unit_status": _status(unit.get("status"), "unknown"),
                "status": "provisional_selection",
                "order_basis": "deterministic_unit_id",
                "emphasis_claim_ids": [
                    claim_id for claim_id in program["emphasis_claim_ids"] if claim_id in claims
                ],
                "evidence_refs": unit_refs,
            })
    program_ids = [row["program_id"] for row in programs]
    alternate_ids = sorted(program_ids, reverse=True)
    alternatives: list[dict[str, Any]] = []
    if len(program_ids) > 1 and alternate_ids != program_ids:
        alternatives.append({
            "sequence_id": "alternative:reverse-program-id",
            "program_ids": alternate_ids,
            "status": "candidate",
            "basis": "provisional_order_alternative",
            "evidence_refs": [],
        })
    return sequence, alternatives, basis


def _requirement_coverage(
    programs: Sequence[Mapping[str, Any]],
    claims: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    requirement_ids = sorted({req for program in programs for req in program["requirement_ids"]})
    rows: list[dict[str, Any]] = []
    for requirement_id in requirement_ids:
        supporting = sorted({
            claim_id for claim_id, claim in claims.items()
            if requirement_id in claim.get("requirement_ids", []) and claim.get("status") == "supported"
        })
        candidates = sorted({
            claim_id for claim_id, claim in claims.items()
            if requirement_id in claim.get("requirement_ids", []) and claim.get("status") == "candidate"
        })
        programs_for_req = sorted({
            program["program_id"] for program in programs
            if requirement_id in program["requirement_ids"]
        })
        program_rows = [
            program for program in programs
            if requirement_id in program["requirement_ids"]
        ]
        declared_missing = any(
            requirement_id in program.get("missing_requirement_ids", [])
            for program in programs
        )
        program_evidence_refs = sorted({
            evidence_ref
            for program in program_rows
            for evidence_ref in program.get("evidence_refs", [])
        })
        if supporting:
            coverage_status = "documented_fact"
        elif candidates:
            coverage_status = "candidate"
        elif program_rows or program_evidence_refs:
            coverage_status = "candidate"
        else:
            coverage_status = "unknown"
        refs = sorted({
            ref for claim_id in supporting + candidates
            for ref in claims[claim_id].get("evidence_refs", [])
        } | set(program_evidence_refs))
        explicit_program_binding = bool(program_rows)
        has_explicit_association = bool(explicit_program_binding or refs)
        if supporting:
            coverage_basis = "supported_claim"
        elif candidates:
            coverage_basis = "candidate_claim"
        elif explicit_program_binding:
            coverage_basis = "explicit_program_binding"
        elif refs:
            coverage_basis = "explicit_evidence_binding"
        else:
            coverage_basis = "no_explicit_association"
        rows.append({
            "requirement_id": requirement_id,
            "coverage_status": coverage_status,
            "coverage_basis": coverage_basis,
            "program_ids": programs_for_req,
            "supported_claim_ids": supporting,
            "candidate_claim_ids": candidates,
            "evidence_refs": refs,
            "explicit_program_binding": explicit_program_binding,
            "missing": declared_missing or not has_explicit_association,
        })
    return rows


def _dossier_without_hash(dossier: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(dossier))
    result.pop("dossier_hash", None)
    return result


def _technical_context_projection(
    technical_context: Mapping[str, Any] | None,
    expected_identity: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Keep technical context as provenance without making cultural claims.

    ``project_tool_observations_to_context`` already produces the shared
    ``mak-project-context-v1`` contract.  The dossier only carries its
    technical relations, never paths, tool payloads, project rows or a
    relation promoted to authorship/work truth.  This makes a PSD-to-logo
    observation useful to a curator while keeping it outside claims and
    public assets.
    """
    if technical_context is None:
        return None, []
    if not isinstance(technical_context, Mapping):
        return None, ["technical_context_not_object"]
    context = _copy_json(technical_context)
    from .project_context import validate_context

    context_errors = validate_context(context)
    if context_errors:
        return None, [f"technical_context_{error}" for error in context_errors]
    context_id = _text(context.get("context_id"))
    if not context_id:
        return None, ["technical_context_context_id_missing"]
    provenance = context.get("provenance")
    if expected_identity is not None:
        if not isinstance(provenance, Mapping):
            return None, ["technical_context_provenance_missing"]
        identity_errors: list[str] = []
        for key in ("archive_id", "snapshot_id"):
            expected = _text(expected_identity.get(key))
            observed = _text(provenance.get(key))
            if expected and observed and expected != observed:
                identity_errors.append(f"technical_context_identity_mismatch:{key}")
            elif expected and not observed:
                identity_errors.append(f"technical_context_identity_missing:{key}")
        if identity_errors:
            return None, sorted(identity_errors)
    source_ids = {
        _text(source.get("source_id"))
        for source in context.get("sources", [])
        if isinstance(source, Mapping)
    }
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, relation in enumerate(context.get("relations", [])):
        if not isinstance(relation, Mapping):
            errors.append(f"technical_context_relation_{index}_not_object")
            continue
        predicate = _text(relation.get("predicate"))
        if not predicate.startswith("technical_"):
            continue
        subject = _text(relation.get("subject"))
        object_ref = _text(relation.get("object"))
        status = _text(relation.get("status") or relation.get("requested_status")).casefold()
        raw_sources = relation.get("source_ids")
        if not subject or not object_ref:
            errors.append(f"technical_context_relation_{index}_endpoint_missing")
            continue
        if status not in TECHNICAL_CONTEXT_STATUSES:
            errors.append(f"technical_context_relation_{index}_status_not_candidate")
            continue
        if not isinstance(raw_sources, list) or any(
            not isinstance(value, str) or not value.strip() for value in raw_sources
        ):
            errors.append(f"technical_context_relation_{index}_source_ids_invalid")
            continue
        evidence_refs = sorted(set(raw_sources))
        if evidence_refs != raw_sources:
            errors.append(f"technical_context_relation_{index}_source_ids_not_sorted_unique")
        if any(value not in source_ids for value in evidence_refs):
            errors.append(f"technical_context_relation_{index}_source_ref_unresolved")
        metadata = relation.get("metadata", {})
        if not isinstance(metadata, Mapping):
            errors.append(f"technical_context_relation_{index}_metadata_invalid")
            metadata = {}
        if metadata.get("truth_promotion") is True:
            errors.append(f"technical_context_relation_{index}_truth_promotion")
        raw_signals = metadata.get("signals", [])
        if not isinstance(raw_signals, list) or any(
            not isinstance(value, str) or not value.strip() for value in raw_signals
        ):
            errors.append(f"technical_context_relation_{index}_signals_invalid")
            raw_signals = []
        signals = sorted(set(raw_signals))
        semantic = {
            "context_id": context_id,
            "subject_ref": subject,
            "predicate": predicate,
            "object_ref": object_ref,
            "status": status,
            "evidence_refs": evidence_refs,
            "signals": signals,
        }
        rows.append({
            "evidence_id": "technical-evidence:" + hashlib.sha256(
                stable_json(semantic).encode("utf-8")
            ).hexdigest()[:32],
            "subject_ref": subject,
            "predicate": predicate,
            "object_ref": object_ref,
            "status": status,
            "evidence_refs": evidence_refs,
            "signals": signals,
            "artistic_truth": False,
            "asset_selection": False,
        })
    rows.sort(key=lambda row: row["evidence_id"])
    if errors:
        return None, sorted(set(errors))
    return {
        "context_id": context_id,
        "context_hash": _hash(context),
        "relations": rows,
        "provenance_only": True,
        "claim_promotion": False,
        "asset_selection": False,
    }, []


def compile_portfolio_dossier(
    plan: Mapping[str, Any],
    practice_state: Mapping[str, Any],
    technical_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one deterministic internal dossier from accepted evidence state.

    The optional technical context is a provenance-only projection.  Omitting
    it preserves the original dossier contract and output.
    """
    plan_copy = _copy_json(plan)
    practice_copy = _copy_json(practice_state)
    errors = _validate_plan_shape(plan_copy) + _validate_practice_shape(practice_copy)
    if errors:
        unique_errors = sorted(set(errors))
        raise PortfolioDossierError("input_invalid:" + ",".join(unique_errors), unique_errors)

    (
        artifact_by_ref,
        unit_by_id,
        practice_claims,
        artifact_refs,
        practice_evidence_refs,
        practice_errors,
    ) = _normalise_practice(practice_copy)
    plan_claims, plan_claim_errors = _plan_claim_rows(plan_copy)
    errors = practice_errors + plan_claim_errors
    identity = _practice_identity(plan_copy, practice_copy)
    programs, selected_claim_ids, program_errors = _selected_programs(
        plan_copy,
        unit_by_id,
        plan_claims | practice_claims,
        artifact_refs,
        practice_evidence_refs,
    )
    errors.extend(program_errors)
    claims, claim_errors = _merge_claims(
        plan_claims,
        practice_claims,
        selected_claim_ids,
        practice_evidence_refs,
    )
    errors.extend(claim_errors)
    asset_manifest, asset_errors = _asset_rows(
        plan_copy,
        artifact_by_ref,
        practice_evidence_refs,
    )
    errors.extend(asset_errors)
    technical_projection, technical_errors = _technical_context_projection(
        technical_context, identity
    )
    errors.extend(technical_errors)
    if errors:
        unique_errors = sorted(set(errors))
        raise PortfolioDossierError("input_invalid:" + ",".join(unique_errors), unique_errors)

    sequence, alternate_sequences, order_basis = _sequence(programs, unit_by_id, claims)
    narrative_atoms = _narrative_atoms(claims)
    requirement_coverage = _requirement_coverage(programs, claims)
    omissions: list[dict[str, Any]] = []
    gaps: list[str] = []
    for gap in plan_copy.get("gaps", []):
        if isinstance(gap, Mapping):
            code = _text(gap.get("code") or gap.get("gap_id") or gap.get("reason"))
            if code:
                gaps.append(code)
            else:
                raise PortfolioDossierError("plan_gap_without_code")
        elif _text(gap):
            gaps.append(_text(gap))
        else:
            raise PortfolioDossierError("plan_gap_invalid")
    research_status = _text(plan_copy.get("control", {}).get("research_status")).casefold()
    if research_status in {"abstain", "abstained", "unresolved"}:
        gaps.append("research_first_abstained")
    for row in requirement_coverage:
        if row["missing"]:
            reason = f"missing_requirement_evidence:{row['requirement_id']}"
            gaps.append(reason)
            omissions.append({
                "kind": "requirement",
                "requirement_id": row["requirement_id"],
                "reason": "missing_evidence",
                "status": "open",
            })
    for gap in practice_copy.get("gaps", []) if isinstance(practice_copy.get("gaps"), list) else []:
        if isinstance(gap, Mapping):
            code = _text(gap.get("code"))
            if code:
                gaps.append(f"practice:{code}")
        elif _text(gap):
            gaps.append(f"practice:{_text(gap)}")
    public_manifest: list[dict[str, Any]] = []
    for row in asset_manifest:
        if row["public_eligibility"] == "eligible":
            public_manifest.append(dict(row))
        else:
            omissions.append({
                "kind": "asset",
                "artifact_ref": row["artifact_ref"],
                "reason": (
                    "private_or_license_not_explicit"
                    if row["public_eligibility"] == "blocked"
                    else "public_eligibility_unknown"
                ),
                "status": "excluded_from_public_manifest",
            })
    if not programs:
        gaps.append("no_selected_programs")
    gaps = sorted(set(gaps))
    status = "draft_only" if programs else "blocked"
    control = {
        "publication": False,
        "export": False,
        "promotion": "none",
        "training_permitted": False,
        "source_rescan": False,
        "database_write": False,
        "network_called": False,
        "curatorial_order_provisional": True,
        "facts_separated_from_curatorial_decision": True,
        "private_assets_excluded_from_public_manifest": True,
    }
    input_hashes = {
        "product_plan": _hash(plan_copy),
    }
    if technical_projection is not None:
        input_hashes["technical_context"] = technical_projection["context_hash"]
    dossier: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": _text(plan_copy["opportunity_id"]),
        "input_hashes": input_hashes,
        "practice_identity": identity,
        "selected_programs": programs,
        "claim_index": [
            {
                "claim_id": claim_id,
                "status": row["status"],
                "statement": _text(row.get("statement") or row.get("value")),
                "evidence_refs": list(row.get("evidence_refs", [])),
                "requirement_ids": list(row.get("requirement_ids", [])),
                "unit_ids": list(row.get("unit_ids", [])),
                "narrative_type": {
                    "supported": "documented_fact",
                    "candidate": "candidate",
                    "unknown": "unknown",
                }[row["status"]],
            }
            for claim_id, row in sorted(claims.items())
        ],
        "asset_index": asset_manifest,
        "targets": {"portfolio_dossier": _safe_projection(
            plan_copy["targets"]["portfolio_dossier"], "portfolio_dossier_target"
        )},
        "curatorial_sequence": sequence,
        "curatorial_decision": {
            "order_basis": order_basis,
            "status": "provisional",
            "selected_program_ids": [program["program_id"] for program in programs],
            "emphasis_is_not_fact": True,
        },
        "narrative_atoms": narrative_atoms,
        "asset_manifest": asset_manifest,
        "public_manifest": public_manifest,
        "public_asset_manifest": public_manifest,
        "requirement_coverage": requirement_coverage,
        "omissions": sorted(omissions, key=stable_json),
        "gaps": gaps,
        "alternate_sequences": alternate_sequences,
        "status": status,
        "control": control,
        "valid": True,
        "errors": [],
    }
    if technical_projection is not None:
        dossier["technical_context"] = technical_projection
    dossier["dossier_hash"] = "dossier:" + _hash(_dossier_without_hash(dossier))
    validation_errors = validate_portfolio_dossier(dossier)
    if validation_errors:
        raise PortfolioDossierError(
            "dossier_invalid:" + ",".join(validation_errors), validation_errors
        )
    return dossier


def validate_portfolio_dossier(dossier: Any) -> list[str]:
    """Return deterministic structural errors without repairing the dossier."""
    if not isinstance(dossier, Mapping):
        return ["dossier_not_object"]
    errors: list[str] = []
    if dossier.get("schema") != SCHEMA:
        errors.append("dossier_schema_invalid")
    if dossier.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append("dossier_algorithm_version_invalid")
    if dossier.get("status") not in {"draft_only", "blocked"}:
        errors.append("dossier_status_invalid")
    control = dossier.get("control")
    if not isinstance(control, Mapping):
        errors.append("dossier_control_invalid")
    else:
        if control.get("publication") is not False:
            errors.append("dossier_publication_not_false")
        if control.get("export") is not False:
            errors.append("dossier_export_not_false")
        if control.get("promotion") != "none":
            errors.append("dossier_promotion_not_none")
        if control.get("training_permitted") is not False:
            errors.append("dossier_training_not_false")
    list_fields = (
        "selected_programs", "claim_index", "asset_index", "curatorial_sequence",
        "narrative_atoms", "asset_manifest", "public_manifest", "public_asset_manifest",
        "requirement_coverage", "omissions", "gaps", "alternate_sequences",
    )
    for key in list_fields:
        if not isinstance(dossier.get(key), list):
            errors.append(f"dossier_{key}_invalid")
    claim_ids: set[str] = set()
    for row in dossier.get("claim_index", []) if isinstance(dossier.get("claim_index"), list) else []:
        if not isinstance(row, Mapping) or not _text(row.get("claim_id")):
            errors.append("dossier_claim_id_missing")
            continue
        claim_id = _text(row["claim_id"])
        if claim_id in claim_ids:
            errors.append(f"dossier_claim_duplicate:{claim_id}")
        claim_ids.add(claim_id)
        if row.get("narrative_type") not in CLAIM_TYPES:
            errors.append(f"dossier_claim_type_invalid:{claim_id}")
        _, ref_error = _refs(
            row.get("evidence_refs"), f"dossier_claim_{claim_id}_evidence_refs"
        )
        if ref_error:
            errors.append(ref_error)
    asset_ids: set[str] = set()
    for row in dossier.get("asset_manifest", []) if isinstance(dossier.get("asset_manifest"), list) else []:
        if not isinstance(row, Mapping) or not _text(row.get("artifact_ref")):
            errors.append("dossier_asset_ref_missing")
            continue
        ref = _text(row["artifact_ref"])
        if ref in asset_ids:
            errors.append(f"dossier_asset_duplicate:{ref}")
        asset_ids.add(ref)
        if row.get("public_eligibility") not in PUBLIC_ELIGIBILITY:
            errors.append(f"dossier_asset_eligibility_invalid:{ref}")
        if any(key in row for key in ("path", "relative_path", "raw", "raw_bytes", "content")):
            errors.append(f"dossier_asset_private_field:{ref}")
    public_rows = dossier.get("public_manifest", [])
    public_ids = {
        _text(row.get("artifact_ref")) for row in public_rows
        if isinstance(row, Mapping)
    } if isinstance(public_rows, list) else set()
    if not public_ids <= asset_ids:
        errors.append("dossier_public_manifest_ref_ajeno")
    if any(
        isinstance(row, Mapping) and row.get("public_eligibility") != "eligible"
        for row in public_rows if isinstance(public_rows, list)
    ):
        errors.append("dossier_public_manifest_ineligible_asset")
    if dossier.get("public_asset_manifest") != dossier.get("public_manifest"):
        errors.append("dossier_public_asset_manifest_mismatch")
    technical_context = dossier.get("technical_context")
    if technical_context is not None:
        if not isinstance(technical_context, Mapping):
            errors.append("dossier_technical_context_invalid")
        else:
            expected_fields = {
                "context_id", "context_hash", "relations", "provenance_only",
                "claim_promotion", "asset_selection",
            }
            if set(technical_context) != expected_fields:
                errors.append("dossier_technical_context_field_set_invalid")
            if not _text(technical_context.get("context_id")):
                errors.append("dossier_technical_context_id_missing")
            context_hash = technical_context.get("context_hash")
            if not isinstance(context_hash, str) or not context_hash.startswith("sha256:"):
                errors.append("dossier_technical_context_hash_invalid")
            if technical_context.get("provenance_only") is not True:
                errors.append("dossier_technical_context_not_provenance_only")
            if technical_context.get("claim_promotion") is not False:
                errors.append("dossier_technical_context_claim_promotion")
            if technical_context.get("asset_selection") is not False:
                errors.append("dossier_technical_context_asset_selection")
            relation_ids: set[str] = set()
            for row in technical_context.get("relations", []) if isinstance(technical_context.get("relations"), list) else []:
                if not isinstance(row, Mapping):
                    errors.append("dossier_technical_relation_invalid")
                    continue
                required = {
                    "evidence_id", "subject_ref", "predicate", "object_ref", "status",
                    "evidence_refs", "signals", "artistic_truth", "asset_selection",
                }
                if set(row) != required:
                    errors.append("dossier_technical_relation_field_set_invalid")
                    continue
                evidence_id = _text(row.get("evidence_id"))
                if not evidence_id or evidence_id in relation_ids:
                    errors.append("dossier_technical_relation_id_invalid")
                relation_ids.add(evidence_id)
                if not _text(row.get("subject_ref")) or not _text(row.get("object_ref")):
                    errors.append("dossier_technical_relation_endpoint_invalid")
                if not _text(row.get("predicate")).startswith("technical_"):
                    errors.append("dossier_technical_relation_predicate_invalid")
                if row.get("status") not in TECHNICAL_CONTEXT_STATUSES:
                    errors.append("dossier_technical_relation_status_invalid")
                for field in ("evidence_refs", "signals"):
                    refs, ref_error = _refs(row.get(field), f"dossier_technical_{field}")
                    if ref_error:
                        errors.append(ref_error)
                if row.get("artistic_truth") is not False or row.get("asset_selection") is not False:
                    errors.append("dossier_technical_relation_promotion")
            if isinstance(technical_context.get("relations"), list):
                if technical_context["relations"] != sorted(
                    technical_context["relations"], key=lambda row: row.get("evidence_id", "")
                ):
                    errors.append("dossier_technical_relations_not_sorted")
            if dossier.get("input_hashes", {}).get("technical_context") != context_hash:
                errors.append("dossier_technical_context_hash_not_declared")
    expected_hash = dossier.get("dossier_hash")
    if not isinstance(expected_hash, str) or not expected_hash.startswith("dossier:sha256:"):
        errors.append("dossier_hash_missing")
    elif expected_hash != "dossier:" + _hash(_dossier_without_hash(dossier)):
        errors.append("dossier_hash_mismatch")
    return sorted(set(errors))


def assert_portfolio_dossier(dossier: Any) -> bool:
    errors = validate_portfolio_dossier(dossier)
    if errors:
        raise PortfolioDossierError("dossier_invalid:" + ",".join(errors), errors)
    return True


compile_dossier = compile_portfolio_dossier
build_portfolio_dossier = compile_portfolio_dossier
validate_dossier = validate_portfolio_dossier
assert_dossier = assert_portfolio_dossier


__all__ = [
    "ALGORITHM_VERSION", "PLAN_SCHEMA", "PRACTICE_SCHEMA", "SCHEMA",
    "TECHNICAL_CONTEXT_SCHEMA",
    "PortfolioDossierError", "assert_dossier", "assert_portfolio_dossier",
    "build_portfolio_dossier", "compile_dossier", "compile_portfolio_dossier",
    "stable_json", "validate_dossier", "validate_portfolio_dossier",
]
