"""Independent falsification gate for provisional artistic-program candidates.

The evaluator consumes the three accepted Piso 1 projections:
``mak-opportunity-constraints-v1``, ``mak-practice-evidence-state-v1`` and
``mak-opportunity-fit-v1``.  It does not import a program generator, infer a
program from text, rescan an archive, access a database or modify payloads.

The candidate producer is intentionally outside this module.  A candidate is
accepted by this gate only as a structurally and evidentially aligned
possibility; the result is not a claim about artistic meaning, quality,
eligibility or publicability.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import optional_text as _text, sha256_ref as _digest, stable_json

from .opportunity_constraints import validate_opportunity_constraints
from .practice_evidence_state import validate_practice_evidence_state


OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
PRACTICE_SCHEMA = "mak-practice-evidence-state-v1"
FIT_SCHEMA = "mak-opportunity-fit-v1"
CANDIDATE_SCHEMA = "mak-artistic-program-candidates-v1"
REPORT_SCHEMA = "mak-artistic-program-evaluation-v1"
ALGORITHM_VERSION = "artistic-program-evaluator-1"
PROGRAM_ID_ALGORITHM = "sha256-canonical-program-semantic-fields-v1"
REPORT_HASH_ALGORITHM = "sha256-canonical-report-without-report-hash-v1"

PROGRAM_STATUSES = frozenset({
    "candidate", "unknown", "provisional", "unresolved", "pending_program", "unresolved_program",
})
TRUTH_STATUSES = frozenset({
    "accepted", "active", "verified", "promoted", "supported", "published", "truth",
})
FIT_DECISIONS = frozenset({"supported", "abstain", "contradicted"})
GATE_STATUSES = frozenset({"pass", "abstain", "fail"})
BASIS_VALUES = frozenset({"practice_native", "opportunity_conditioned"})
SOURCE_STATUSES = frozenset({
    "unknown", "observed_local", "current_verified", "expired", "ineligible",
    "contradicted", "stale",
})
PROGRAM_LIST_FIELDS = (
    "unit_ids", "requirement_ids", "supported_claim_ids", "candidate_claim_ids",
    "evidence_refs", "counterevidence_refs", "missing_requirement_ids",
    "research_action_ids", "resource_refs", "alternatives", "generation_reasons",
    "risk_flags",
)
PROGRAM_FIELDS = frozenset({
    "program_id", "basis", "status", "unit_ids", "requirement_ids",
    "supported_claim_ids", "candidate_claim_ids", "evidence_refs",
    "counterevidence_refs", "missing_requirement_ids", "research_action_ids",
    "resource_refs", "alternatives", "generation_reasons", "risk_flags",
    "provenance",
})


class ArtisticProgramEvaluationError(ValueError):
    """Raised by the assertion API when the independent gate fails."""

    def __init__(self, message: str, report: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = dict(report) if report is not None else None


def _sorted_unique_strings(value: Any) -> tuple[list[str] | None, str | None]:
    if not isinstance(value, list):
        return None, "not_list"
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None, "invalid_string"
    result = sorted(set(value))
    if value != result:
        return None, "not_sorted_unique"
    return result, None


def _string_set(value: Any) -> set[str]:
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def _error(code: str, detail: str = "", **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code}
    if detail:
        row["detail"] = detail
    row.update(extra)
    return row


def _error_codes(errors: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(error.get("code")) for error in errors if error.get("code")})


def _practice_state_hash(practice: Mapping[str, Any]) -> str:
    snapshot = copy.deepcopy(dict(practice))
    snapshot.pop("state_hash", None)
    return _digest(snapshot)


def program_id_for(
    program: Mapping[str, Any],
    *,
    opportunity_id: str = "",
    practice_identity: str = "",
) -> str:
    """Recompute the core's deterministic ID without provenance metadata.

    The evaluator repeats this small canonical rule locally instead of
    importing the candidate generator: all candidate semantic fields except
    ``program_id`` and ``provenance`` are sorted by field name and hashed.
    """
    semantic = {
        key: program.get(key)
        for key in sorted(PROGRAM_FIELDS - {"program_id", "provenance"})
    }
    return "program:" + hashlib.sha256(stable_json(semantic).encode("utf-8")).hexdigest()


def _canonical_fit(fit: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize order-only fit differences independently of the producer."""
    result = copy.deepcopy(dict(fit))
    validation = result.get("validation")
    if isinstance(validation, Mapping):
        result["validation"] = dict(validation)
        if isinstance(result["validation"].get("errors"), list):
            result["validation"]["errors"] = sorted(result["validation"]["errors"])
    if isinstance(result.get("matrix"), list):
        result["matrix"] = sorted(
            (dict(row) for row in result["matrix"] if isinstance(row, Mapping)),
            key=lambda row: row.get("requirement_id", ""),
        )
        for row in result["matrix"]:
            if isinstance(row.get("cells"), list):
                row["cells"] = sorted(
                    row["cells"], key=lambda cell: cell.get("evidence_ref", "")
                    if isinstance(cell, Mapping) else "",
                )
    for field, key in (
        ("allowed_claims", (lambda row: (row.get("requirement_id", ""), stable_json(row)))),
        ("required_but_unsupported", (lambda row: row.get("requirement_id", ""))),
        ("research_job_candidates", (lambda row: row.get("candidate_id", ""))),
    ):
        if isinstance(result.get(field), list):
            result[field] = sorted(
                (dict(row) for row in result[field] if isinstance(row, Mapping)),
                key=key,
            )
    return result


def fit_input_hash_for(fit: Mapping[str, Any]) -> str:
    """Return the canonical fit hash used by the candidate contract."""
    return _digest(_canonical_fit(fit))


def _safe_validate_inputs(
    opportunity: Any,
    practice: Any,
    fit: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "opportunity": opportunity if isinstance(opportunity, Mapping) else {},
        "practice": practice if isinstance(practice, Mapping) else {},
        "fit": fit if isinstance(fit, Mapping) else {},
        "opportunity_id": "",
        "practice_identity": "",
        "practice_hash": "",
        "fit_hash": "",
        "constraint_by_id": {},
        "requirement_ids": set(),
        "hard_gate_ids": set(),
        "practice_units": {},
        "claims_by_id": {},
        "evidence_by_ref": {},
        "internal_refs": set(),
        "physical_refs": set(),
        "content_ids": set(),
        "content_groups": {},
        "artifact_by_ref": {},
        "resource_refs": set(),
        "research_action_ids": set(),
        "expected_matrix": {},
        "expected_source_gate": "abstain",
        "expected_hard_gate": "abstain",
        "source_errors": errors,
    }
    if not isinstance(opportunity, Mapping):
        errors.append(_error("opportunity_not_object"))
    else:
        if opportunity.get("schema") != OPPORTUNITY_SCHEMA:
            errors.append(_error("opportunity_schema_invalid"))
        try:
            validate_opportunity_constraints(opportunity)
        except Exception as error:  # The report must remain a falsification result.
            errors.append(_error("opportunity_payload_invalid", str(error)))
        context["opportunity_id"] = _text(opportunity.get("opportunity_id"))
        if not context["opportunity_id"]:
            errors.append(_error("opportunity_id_missing"))

        constraints = opportunity.get("constraints")
        if not isinstance(constraints, list):
            errors.append(_error("opportunity_constraints_invalid"))
            constraints = []
        for index, row in enumerate(constraints):
            if not isinstance(row, Mapping):
                errors.append(_error("constraint_not_object", index=index))
                continue
            requirement_id = _text(row.get("constraint_id"))
            if not requirement_id:
                errors.append(_error("constraint_id_missing", index=index))
                continue
            if requirement_id in context["constraint_by_id"]:
                errors.append(_error("constraint_id_duplicate", requirement_id, index=index))
            context["constraint_by_id"][requirement_id] = row
            context["requirement_ids"].add(requirement_id)
            hard_gates = opportunity.get("hard_gates", [])
            if isinstance(hard_gates, list) and requirement_id in set(hard_gates):
                context["hard_gate_ids"].add(requirement_id)

    if not isinstance(practice, Mapping):
        errors.append(_error("practice_not_object"))
    else:
        if practice.get("schema") != PRACTICE_SCHEMA:
            errors.append(_error("practice_schema_invalid"))
        try:
            practice_errors = validate_practice_evidence_state(practice)
        except Exception as error:  # Keep malformed input in the report.
            practice_errors = [str(error)]
        errors.extend(_error("practice_payload_invalid", item) for item in practice_errors)
        context["practice_identity"] = ":".join(
            _text(practice.get(key)) for key in ("tenant", "archive_id", "snapshot_id")
        )
        context["practice_identity"] = "practice:" + context["practice_identity"]
        context["practice_hash"] = _text(practice.get("state_hash"))
        if context["practice_hash"]:
            try:
                if context["practice_hash"] != _practice_state_hash(practice):
                    errors.append(_error("practice_state_hash_mismatch"))
            except (TypeError, ValueError):
                errors.append(_error("practice_state_hash_uncomputable"))
        if not context["practice_hash"]:
            errors.append(_error("practice_state_hash_missing"))

        units = practice.get("units")
        if not isinstance(units, list):
            errors.append(_error("practice_units_invalid"))
            units = []
        for row in units:
            if not isinstance(row, Mapping) or not _text(row.get("unit_id")):
                errors.append(_error("practice_unit_id_invalid"))
                continue
            unit_id = _text(row.get("unit_id"))
            context["practice_units"][unit_id] = row
            context["internal_refs"].add(unit_id)
            for key in ("artifact_refs", "member_refs", "dependency_refs", "evidence_refs"):
                values = row.get(key)
                if isinstance(values, list):
                    context["internal_refs"].update(item for item in values if isinstance(item, str))

        artifacts = practice.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append(_error("practice_artifacts_invalid"))
            artifacts = []
        for row in artifacts:
            if not isinstance(row, Mapping):
                errors.append(_error("practice_artifact_not_object"))
                continue
            ref = _text(row.get("artifact_ref"))
            if not ref:
                errors.append(_error("practice_artifact_ref_missing"))
                continue
            if ref in context["physical_refs"]:
                errors.append(_error("practice_physical_ref_duplicate", ref))
            context["physical_refs"].add(ref)
            context["internal_refs"].add(ref)
            context["artifact_by_ref"][ref] = row
            content_id = _text(row.get("content_id"))
            if content_id:
                context["content_ids"].add(content_id)
                context["content_groups"].setdefault(content_id, set()).add(ref)
            if _text(row.get("role")).casefold() in {"resource", "shared_resource"}:
                context["resource_refs"].add(ref)

        claims = practice.get("claims") if isinstance(practice.get("claims"), Mapping) else {}
        for status, rows in claims.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, Mapping):
                    errors.append(_error("practice_claim_not_object"))
                    continue
                claim_id = _text(row.get("claim_id"))
                if not claim_id:
                    errors.append(_error("practice_claim_id_missing"))
                    continue
                context["claims_by_id"][claim_id] = row
                context["internal_refs"].add(claim_id)
                _index_practice_evidence(context, row, claim_id, status)

        for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
            rows = practice.get(dimension) if isinstance(practice.get(dimension), list) else []
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    errors.append(_error("practice_dimension_not_object", dimension=dimension, index=index))
                    continue
                value = _text(row.get("value"))
                if value:
                    context["internal_refs"].add(value)
                    if dimension == "resources":
                        context["resource_refs"].add(value)
                _index_practice_evidence(context, row, f"{dimension}:{index}", dimension)
                if dimension == "resources":
                    refs = row.get("evidence_refs")
                    if isinstance(refs, list):
                        context["resource_refs"].update(item for item in refs if isinstance(item, str))

        for dependency in practice.get("dependencies", []) if isinstance(practice.get("dependencies"), list) else []:
            if isinstance(dependency, Mapping):
                target = _text(dependency.get("target_ref"))
                if target:
                    context["internal_refs"].add(target)
                refs = dependency.get("evidence_refs")
                if isinstance(refs, list):
                    context["internal_refs"].update(item for item in refs if isinstance(item, str))

    if not isinstance(fit, Mapping):
        errors.append(_error("fit_not_object"))
    else:
        if fit.get("schema") != FIT_SCHEMA:
            errors.append(_error("fit_schema_invalid"))
        try:
            context["fit_hash"] = fit_input_hash_for(fit)
        except (TypeError, ValueError):
            errors.append(_error("fit_hash_uncomputable"))
        research_rows = fit.get("research_job_candidates")
        if isinstance(research_rows, list):
            for row in research_rows:
                if isinstance(row, Mapping):
                    action_id = _text(row.get("candidate_id")) or _text(row.get("research_action_id"))
                    if action_id:
                        context["research_action_ids"].add(action_id)

    _compute_gate_expectations(context, errors)
    return errors, context


def _index_practice_evidence(
    context: dict[str, Any],
    row: Mapping[str, Any],
    fallback_id: str,
    kind: Any,
) -> None:
    refs = row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else []
    refs = [item for item in refs if isinstance(item, str) and item]
    evidence_ids = refs or [fallback_id]
    requirement_ids = row.get("requirement_ids")
    if not isinstance(requirement_ids, list):
        requirement_ids = row.get("supports")
    requirement_ids = [item for item in requirement_ids if isinstance(item, str)] if isinstance(requirement_ids, list) else []
    status = _text(row.get("status")) or _text(kind) or "unknown"
    source_ref = _text(row.get("provenance_ref")) or _text(row.get("source_ref"))
    for evidence_id in evidence_ids:
        prior = context["evidence_by_ref"].get(evidence_id)
        statuses = {status, prior.get("status")} if prior else {status}
        if "contradicted" in statuses:
            merged_status = "contradicted"
        elif statuses & {"supported", "observed", "verified"}:
            merged_status = "supported"
        elif "candidate" in statuses:
            merged_status = "candidate"
        else:
            merged_status = "unknown"
        context["evidence_by_ref"][evidence_id] = {
            "status": merged_status,
            "requirement_ids": sorted(set(requirement_ids) | set(prior.get("requirement_ids", []) if prior else [])),
            "source_ref": source_ref or (prior.get("source_ref", "") if prior else ""),
            "kind": _text(kind),
        }
        context["internal_refs"].add(evidence_id)


def _compute_gate_expectations(context: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    opportunity = context["opportunity"]
    practice = context["practice"]
    if isinstance(opportunity, Mapping):
        source = opportunity.get("source") if isinstance(opportunity.get("source"), Mapping) else {}
        validity = source.get("validity") if isinstance(source.get("validity"), Mapping) else {}
        source_status = _text(validity.get("status")).casefold()
        confirmed = validity.get("confirmed") is True
        if source_status == "current_verified" and confirmed:
            context["expected_source_gate"] = "pass"
        elif source_status in {"expired", "ineligible"}:
            context["expected_source_gate"] = "fail"
        elif source_status in SOURCE_STATUSES:
            context["expected_source_gate"] = "abstain"
        else:
            context["expected_source_gate"] = "abstain"
            errors.append(_error("source_validity_invalid"))

    matrix: dict[str, str] = {}
    for requirement_id, constraint in context["constraint_by_id"].items():
        refs = [
            ref for ref, row in context["evidence_by_ref"].items()
            if requirement_id in row.get("requirement_ids", [])
        ]
        cells = [context["evidence_by_ref"][ref] for ref in refs]
        if not cells:
            matrix[requirement_id] = "missing"
        elif any(cell.get("status") == "contradicted" for cell in cells):
            matrix[requirement_id] = "contradicted"
        elif any(
            cell.get("status") == "supported" and cell.get("source_ref")
            for cell in cells
        ):
            matrix[requirement_id] = "supported"
        elif any(cell.get("status") in {"supported", "candidate", "unknown"} for cell in cells):
            matrix[requirement_id] = "unresolved"
        else:
            matrix[requirement_id] = "unresolved"
        if _text(constraint.get("status")).casefold() == "contradicted":
            matrix[requirement_id] = "contradicted"
    context["expected_matrix"] = matrix
    hard_rows = [matrix.get(requirement_id, "missing") for requirement_id in context["hard_gate_ids"]]
    contradiction_rows = opportunity.get("contradictions", []) if isinstance(opportunity, Mapping) else []
    contradiction_ids = {
        _text(row.get("constraint_id")) for row in contradiction_rows if isinstance(row, Mapping)
    }
    if any(requirement_id in contradiction_ids for requirement_id in context["hard_gate_ids"]):
        context["expected_hard_gate"] = "fail"
    elif any(status == "contradicted" for status in hard_rows):
        context["expected_hard_gate"] = "fail"
    elif any(status != "supported" for status in hard_rows):
        context["expected_hard_gate"] = "abstain"
    else:
        context["expected_hard_gate"] = "pass"


def _fit_alignment(context: Mapping[str, Any], errors: list[dict[str, Any]], warnings: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    fit = context["fit"] if isinstance(context["fit"], Mapping) else {}
    expected_source = str(context["expected_source_gate"])
    declared_source = _text(fit.get("source_gate_status")) or "missing"
    source_errors: list[str] = []
    if declared_source != expected_source:
        source_errors.append("source_gate_mismatch")
        if declared_source == "pass" and expected_source != "pass":
            source_errors.append("source_gate_false_green")
            errors.append(_error("source_gate_false_green"))
    hard_expected = str(context["expected_hard_gate"])
    declared_hard = _text(fit.get("hard_gate_status")) or "missing"
    hard_errors: list[str] = []
    if declared_hard != hard_expected:
        hard_errors.append("hard_gate_mismatch")
        if declared_hard == "pass" and hard_expected != "pass":
            hard_errors.append("hard_gate_false_green")
            errors.append(_error("hard_gate_false_green"))

    matrix = fit.get("matrix") if isinstance(fit.get("matrix"), list) else []
    declared_matrix = {
        row.get("requirement_id"): row.get("status")
        for row in matrix
        if isinstance(row, Mapping) and isinstance(row.get("requirement_id"), str)
    }
    matrix_errors: list[str] = []
    for requirement_id, expected in context["expected_matrix"].items():
        if declared_matrix.get(requirement_id) != expected:
            matrix_errors.append(f"matrix_status_mismatch:{requirement_id}")
            errors.append(_error("fit_matrix_status_mismatch", requirement_id))
    validation = fit.get("validation")
    if fit.get("schema") == FIT_SCHEMA and (
        not isinstance(validation, Mapping) or validation.get("valid") is not True
    ):
        errors.append(_error("fit_declared_invalid"))
    declared_decision = _text(fit.get("decision"))
    if declared_decision not in FIT_DECISIONS:
        errors.append(_error("fit_decision_invalid"))
    if declared_decision == "supported" and (expected_source != "pass" or hard_expected != "pass"):
        errors.append(_error("fit_decision_false_green"))
    if declared_source == "abstain" or declared_hard == "abstain":
        warnings.append("upstream_gate_abstention")
    return (
        {
            "expected": expected_source,
            "declared": declared_source,
            "passed": not source_errors,
            "errors": sorted(set(source_errors)),
        },
        {
            "expected": hard_expected,
            "declared": declared_hard,
            "passed": not hard_errors and not matrix_errors,
            "errors": sorted(set(hard_errors + matrix_errors)),
        },
    )


def _binding_values(
    payload: Mapping[str, Any],
    program: Mapping[str, Any],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for owner in (payload, payload.get("provenance", {}), payload.get("source", {}), program.get("provenance", {})):
        if not isinstance(owner, Mapping):
            continue
        aliases = {
            "opportunity_id": ("opportunity_id",),
            "opportunity_input_hash": ("opportunity_input_hash", "constraints_input_hash", "input_hash"),
            "practice_identity": ("practice_identity",),
            "practice_state_hash": ("practice_state_hash", "practice_hash", "state_hash"),
            "fit_hash": ("fit_hash", "fit_input_hash", "opportunity_fit_hash"),
        }
        for target, keys in aliases.items():
            if target in values:
                continue
            for key in keys:
                value = _text(owner.get(key))
                if value:
                    values[target] = value
                    break
    return values


def _validate_program(
    program: Any,
    index: int,
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    source_errors: Sequence[Mapping[str, Any]],
    resource_owners: Mapping[str, list[str]],
    source_gate_alignment: Mapping[str, Any],
    hard_gate_alignment: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []
    program_id = _text(program.get("program_id")) if isinstance(program, Mapping) else f"index:{index}"
    if not isinstance(program, Mapping):
        errors.append(_error("program_not_object", index=index))
        return _program_result(program_id, "rejected", errors, warnings, {}, {}, source_gate_alignment, hard_gate_alignment, [])
    errors.extend(_error(code) for code in source_gate_alignment.get("errors", []))
    errors.extend(_error(code) for code in hard_gate_alignment.get("errors", []))
    if set(program) != PROGRAM_FIELDS:
        errors.append(_error("program_field_set_invalid", index=index))
    basis = _text(program.get("basis")).casefold()
    if basis not in BASIS_VALUES:
        errors.append(_error("program_basis_invalid"))
    status = _text(program.get("status")).casefold()
    if status in TRUTH_STATUSES:
        errors.append(_error("program_truth_promotion"))
    elif status not in PROGRAM_STATUSES:
        errors.append(_error("program_status_invalid"))
    if program.get("basis") is None:
        errors.append(_error("program_basis_missing"))
    for field in PROGRAM_LIST_FIELDS:
        values, issue = _sorted_unique_strings(program.get(field))
        if issue:
            errors.append(_error(f"{field}_invalid", issue))
        elif values is not None and field not in {"alternatives", "generation_reasons", "risk_flags"} and any(value in context["content_ids"] for value in values):
            errors.append(_error(f"{field}_content_id_endpoint"))

    try:
        expected_id = program_id_for(
            program,
            opportunity_id=context["opportunity_id"],
            practice_identity=context["practice_identity"],
        )
    except (TypeError, ValueError):
        expected_id = ""
        errors.append(_error("program_id_uncomputable"))
    if expected_id and program_id != expected_id:
        errors.append(_error("program_id_mismatch", expected_id))

    binding = _binding_values(payload, program)
    expected_binding = {
        "opportunity_id": context["opportunity_id"],
        "opportunity_input_hash": _text(context["opportunity"].get("input_hash")),
        "practice_identity": context["practice_identity"],
        "practice_state_hash": context["practice_hash"],
        "fit_hash": context["fit_hash"],
    }
    for key, expected in expected_binding.items():
        if not expected:
            continue
        if not binding.get(key):
            errors.append(_error("provenance_binding_missing", key))
        elif binding[key] != expected:
            errors.append(_error("provenance_binding_mismatch", key))

    unit_ids = _string_set(program.get("unit_ids"))
    requirement_ids = _string_set(program.get("requirement_ids"))
    if not unit_ids:
        errors.append(_error("program_unit_binding_missing"))
    for unit_id in sorted(unit_ids - set(context["practice_units"])):
        errors.append(_error("program_unit_dangling", unit_id))
    if not requirement_ids and basis != "practice_native":
        errors.append(_error("program_requirement_binding_missing"))
    for requirement_id in sorted(requirement_ids - set(context["requirement_ids"])):
        errors.append(_error("program_requirement_dangling", requirement_id))

    claim_ids = set(context["claims_by_id"])
    supported_ids = _string_set(program.get("supported_claim_ids"))
    candidate_ids = _string_set(program.get("candidate_claim_ids"))
    if supported_ids & candidate_ids:
        errors.append(_error("claim_partition_overlap"))
    for claim_id in sorted((supported_ids | candidate_ids) - claim_ids):
        errors.append(_error("claim_id_dangling", claim_id))
    for claim_id in sorted(supported_ids):
        claim = context["claims_by_id"].get(claim_id, {})
        if _text(claim.get("status")).casefold() != "supported":
            errors.append(_error("supported_claim_status_invalid", claim_id))
        declared = _string_set(claim.get("requirement_ids"))
        if basis == "opportunity_conditioned" and (not declared or not declared & requirement_ids):
            errors.append(_error("supported_claim_unbound", claim_id))
    for claim_id in sorted(candidate_ids):
        claim = context["claims_by_id"].get(claim_id, {})
        if _text(claim.get("status")).casefold() != "candidate":
            errors.append(_error("candidate_claim_status_invalid", claim_id))
        declared = _string_set(claim.get("requirement_ids"))
        if basis == "opportunity_conditioned" and (not declared or not declared & requirement_ids):
            errors.append(_error("candidate_claim_unbound", claim_id))

    internal_refs = set(context["internal_refs"])
    external_refs = set()
    for row in context["opportunity"].get("evidence", []) if isinstance(context["opportunity"].get("evidence"), list) else []:
        if isinstance(row, Mapping) and _text(row.get("evidence_id")):
            external_refs.add(_text(row.get("evidence_id")))
    for field in ("evidence_refs", "counterevidence_refs"):
        values = program.get(field) if isinstance(program.get(field), list) else []
        for ref in sorted(_string_set(values) - internal_refs):
            if ref in external_refs:
                errors.append(_error("documentary_evidence_ref_used_as_internal", ref))
            elif ref in context["content_ids"]:
                errors.append(_error("content_id_endpoint", ref))
            else:
                errors.append(_error("evidence_ref_dangling", ref))

    evidence_ref_set = _string_set(program.get("evidence_refs")) | _string_set(
        program.get("counterevidence_refs")
    )
    if basis == "practice_native":
        for content_id, physical_refs in sorted(context["content_groups"].items()):
            selected = physical_refs & evidence_ref_set
            if selected and selected != physical_refs:
                errors.append(_error("duplicate_physical_ref_collapsed", content_id))

    resource_refs = _string_set(program.get("resource_refs"))
    for ref in sorted(resource_refs - set(context["resource_refs"])):
        if ref in context["content_ids"]:
            errors.append(_error("resource_content_id_endpoint", ref))
        else:
            errors.append(_error("resource_ref_dangling", ref))
    research_ids = _string_set(program.get("research_action_ids"))
    for action_id in sorted(research_ids - set(context["research_action_ids"])):
        errors.append(_error("research_action_id_dangling", action_id))

    missing = _string_set(program.get("missing_requirement_ids"))
    if not missing <= requirement_ids:
        errors.append(_error("missing_requirement_id_outside_program"))
    expected_missing = {
        requirement_id
        for requirement_id in requirement_ids
        if context["expected_matrix"].get(requirement_id) != "supported"
    }
    if missing != expected_missing:
        errors.append(_error("missing_requirement_reconciliation"))

    provenance = program.get("provenance") if isinstance(program.get("provenance"), Mapping) else {}
    if provenance and provenance.get("source_rescan") is not False:
        errors.append(_error("candidate_source_rescan_not_false"))
    if provenance and provenance.get("claims_promoted") != 0:
        errors.append(_error("candidate_truth_promotion"))

    resource_conflicts = [
        {"resource_ref": resource_ref, "program_ids": sorted(set(owners))}
        for resource_ref, owners in sorted(resource_owners.items())
        if program_id in owners and len(set(owners)) > 1
    ]
    if resource_conflicts:
        warnings.append("resource_conflict")

    evidence_refs = program.get("evidence_refs") if isinstance(program.get("evidence_refs"), list) else []
    evidence_reconciliation = {
        "evidence_refs_total": len(evidence_refs),
        "evidence_refs_resolved": not any(error["code"] in {"evidence_ref_dangling", "documentary_evidence_ref_used_as_internal", "content_id_endpoint"} for error in errors),
        "counterevidence_refs_total": len(program.get("counterevidence_refs", [])) if isinstance(program.get("counterevidence_refs"), list) else 0,
        "physical_refs_preserved": bool(set(context["physical_refs"])) and not any(
            error.get("code") in {"practice_physical_ref_duplicate", "duplicate_physical_ref_collapsed"}
            for error in errors
        ),
        "duplicate_physical_refs_collapsed": any(
            error.get("code") == "duplicate_physical_ref_collapsed" for error in errors
        ),
    }
    binding_reconciliation = {
        "unit_ids_resolved": not any(error["code"] == "program_unit_dangling" for error in errors),
        "requirement_ids_resolved": not any(error["code"] == "program_requirement_dangling" for error in errors),
        "supported_claims_bound": not any(error["code"] == "supported_claim_unbound" for error in errors),
        "candidate_claims_bound": not any(error["code"] == "candidate_claim_unbound" for error in errors),
        "missing_requirement_ids_exact": "missing_requirement_reconciliation" not in _error_codes(errors),
    }
    learning_features = {
        "training_permitted": False,
        "evidence_ref_count": evidence_reconciliation["evidence_refs_total"],
        "counterevidence_ref_count": evidence_reconciliation["counterevidence_refs_total"],
        "unit_count": len(unit_ids),
        "requirement_count": len(requirement_ids),
        "supported_claim_count": len(supported_ids),
        "candidate_claim_count": len(candidate_ids),
        "missing_requirement_count": len(missing),
        "risk_flag_count": len(program.get("risk_flags", [])) if isinstance(program.get("risk_flags"), list) else 0,
        "hard_gate_pass": hard_gate_alignment.get("declared") == "pass" and hard_gate_alignment.get("passed") is True,
        "source_gate_pass": source_gate_alignment.get("declared") == "pass" and source_gate_alignment.get("passed") is True,
    }
    if source_gate_alignment.get("declared") == "fail" or hard_gate_alignment.get("declared") == "fail":
        result_value = "rejected"
    elif not source_gate_alignment.get("passed", False) or not hard_gate_alignment.get("passed", False):
        result_value = "rejected"
    elif errors:
        result_value = "rejected"
    elif source_gate_alignment.get("declared") != "pass" or hard_gate_alignment.get("declared") != "pass":
        result_value = "abstain"
    elif status == "unknown" or missing:
        result_value = "abstain"
    else:
        result_value = "accepted"
    return _program_result(
        program_id, result_value, errors, warnings, evidence_reconciliation,
        binding_reconciliation, source_gate_alignment, hard_gate_alignment,
        resource_conflicts, learning_features,
    )


def _program_result(
    program_id: str,
    result_value: str,
    errors: Sequence[Mapping[str, Any]],
    warnings: Sequence[str],
    evidence_reconciliation: Mapping[str, Any],
    binding_reconciliation: Mapping[str, Any],
    source_gate_alignment: Mapping[str, Any],
    hard_gate_alignment: Mapping[str, Any],
    resource_conflicts: Sequence[Mapping[str, Any]],
    learning_features: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "program_id": program_id,
        "result": result_value,
        "errors": sorted([dict(error) for error in errors], key=stable_json),
        "warnings": sorted(set(str(item) for item in warnings)),
        "evidence_reconciliation": dict(evidence_reconciliation),
        "binding_reconciliation": dict(binding_reconciliation),
        "hard_gate_alignment": dict(hard_gate_alignment),
        "source_gate_alignment": dict(source_gate_alignment),
        "resource_conflicts": [dict(item) for item in resource_conflicts],
        "learning_features": dict(learning_features or {"training_permitted": False}),
    }


def evaluate_artistic_program_payload(
    opportunity: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic falsification report without repairing inputs."""
    source_errors, context = _safe_validate_inputs(opportunity, practice, fit)
    warnings: list[str] = []
    source_gate_alignment, hard_gate_alignment = _fit_alignment(context, source_errors, warnings)
    payload_errors: list[dict[str, Any]] = []
    if not isinstance(payload, Mapping):
        payload_errors.append(_error("candidate_payload_not_object"))
        candidate_rows: list[Any] = []
        payload = {}
    else:
        if payload.get("schema") != CANDIDATE_SCHEMA:
            payload_errors.append(_error("candidate_schema_invalid"))
        candidate_key = "candidates" if "candidates" in payload else "programs" if "programs" in payload else "candidates"
        if "candidates" in payload and "programs" in payload:
            payload_errors.append(_error("candidate_rows_aliases_conflict"))
        candidate_rows = payload.get(candidate_key)
        if not isinstance(candidate_rows, list):
            payload_errors.append(_error("candidates_invalid"))
            candidate_rows = []
        declared_opportunity = _text(payload.get("opportunity_id"))
        if declared_opportunity and declared_opportunity != context["opportunity_id"]:
            payload_errors.append(_error("candidate_opportunity_mismatch"))
        elif not declared_opportunity:
            payload_errors.append(_error("candidate_opportunity_missing"))

        declared_identity = _text(payload.get("practice_identity"))
        if declared_identity and declared_identity != context["practice_identity"]:
            payload_errors.append(_error("candidate_practice_identity_mismatch"))
        declared_hashes = payload.get("input_hashes")
        if declared_hashes is not None:
            expected_hashes = {
                "opportunity_constraints": _text(opportunity.get("input_hash"))
                if isinstance(opportunity, Mapping) else "",
                "practice_evidence_state": context["practice_hash"],
                "opportunity_fit": context["fit_hash"],
            }
            if not isinstance(declared_hashes, Mapping) or dict(declared_hashes) != expected_hashes:
                payload_errors.append(_error("candidate_input_hashes_mismatch"))
        declared_provenance = payload.get("provenance")
        if isinstance(declared_provenance, Mapping):
            if declared_provenance.get("source_rescan") is not False:
                payload_errors.append(_error("candidate_provenance_source_rescan"))
            if declared_provenance.get("claims_promoted") != 0:
                payload_errors.append(_error("candidate_provenance_truth_promotion"))
            source_schemas = declared_provenance.get("source_schemas")
            if isinstance(source_schemas, Mapping):
                expected_schemas = {
                    "opportunity": OPPORTUNITY_SCHEMA,
                    "practice": PRACTICE_SCHEMA,
                    "fit": FIT_SCHEMA,
                }
                if dict(source_schemas) != expected_schemas:
                    payload_errors.append(_error("candidate_provenance_source_schemas_mismatch"))
        declared_summary = payload.get("fit_summary")
        if isinstance(declared_summary, Mapping) and isinstance(fit, Mapping):
            canonical_fit = _canonical_fit(fit)
            expected_summary = {
                "decision": canonical_fit.get("decision"),
                "validation": canonical_fit.get("validation"),
                "hard_gate_status": canonical_fit.get("hard_gate_status", "abstain"),
                "source_gate_status": canonical_fit.get("source_gate_status", "abstain"),
                "source_gate_reason": canonical_fit.get("source_gate_reason", "fit_source_gate_not_declared"),
                "coverage_reason": canonical_fit.get("coverage_reason"),
            }
            if dict(declared_summary) != expected_summary:
                payload_errors.append(_error("candidate_fit_summary_mismatch"))
        declared_reconciliation = payload.get("reconciliation")
        if isinstance(declared_reconciliation, Mapping):
            if declared_reconciliation.get("candidate_count") != len(candidate_rows):
                payload_errors.append(_error("candidate_count_mismatch"))
            if declared_reconciliation.get("deterministic_order") is not True:
                payload_errors.append(_error("candidate_reconciliation_order_invalid"))
            if declared_reconciliation.get("truth_promotions") != 0:
                payload_errors.append(_error("candidate_reconciliation_truth_promotion"))

    ids = [
        _text(row.get("program_id")) if isinstance(row, Mapping) else f"index:{index}"
        for index, row in enumerate(candidate_rows)
    ]
    if ids != sorted(ids):
        payload_errors.append(_error("program_order_invalid"))
    if len(ids) != len(set(ids)):
        payload_errors.append(_error("program_id_duplicate"))

    resource_owners: dict[str, list[str]] = {}
    for row, program_id in zip(candidate_rows, ids):
        if isinstance(row, Mapping) and isinstance(row.get("resource_refs"), list):
            for resource_ref in row["resource_refs"]:
                if isinstance(resource_ref, str):
                    resource_owners.setdefault(resource_ref, []).append(program_id)

    results: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(candidate_rows):
        program_id = ids[index]
        result = _validate_program(
            row, index, payload, context, source_errors, resource_owners,
            source_gate_alignment, hard_gate_alignment,
        )
        results[program_id] = result

    all_errors = list(source_errors) + list(payload_errors)
    for program_id, result in results.items():
        all_errors.extend(
            _error(error.get("code", "program_error"), error.get("detail", ""), program_id=program_id)
            for error in result.get("errors", [])
        )
    reconciliation = {
        "program_count": len(candidate_rows),
        "result_counts": {
            value: sum(1 for result in results.values() if result.get("result") == value)
            for value in ("accepted", "rejected", "abstain")
        },
        "program_ids_unique": len(ids) == len(set(ids)),
        "program_order_deterministic": ids == sorted(ids),
        "physical_refs_preserved": not any(
            error.get("code") in {
                "practice_physical_ref_duplicate", "content_id_endpoint",
                "resource_content_id_endpoint", "program_content_id_endpoint",
                "duplicate_physical_ref_collapsed",
            }
            for error in all_errors
        ),
        "duplicate_physical_refs_collapsed": any(
            error.get("code") in {"practice_physical_ref_duplicate", "duplicate_physical_ref_collapsed"}
            for error in all_errors
        ),
        "truth_promotions": sum(
            1 for error in all_errors if error.get("code") in {
                "program_truth_promotion", "candidate_truth_promotion",
                "candidate_provenance_truth_promotion", "candidate_reconciliation_truth_promotion",
            }
        ),
        "training_permitted": False,
        "source_gate_false_green": any(error.get("code") == "source_gate_false_green" for error in all_errors),
        "hard_gate_false_green": any(error.get("code") == "hard_gate_false_green" for error in all_errors),
        "deterministic_order": ids == sorted(ids),
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "program_id_algorithm": PROGRAM_ID_ALGORITHM,
        "report_hash_algorithm": REPORT_HASH_ALGORITHM,
        "source": {
            "opportunity_schema": opportunity.get("schema") if isinstance(opportunity, Mapping) else None,
            "practice_schema": practice.get("schema") if isinstance(practice, Mapping) else None,
            "fit_schema": fit.get("schema") if isinstance(fit, Mapping) else None,
            "opportunity_id": context["opportunity_id"],
            "opportunity_input_hash": _text(opportunity.get("input_hash")) if isinstance(opportunity, Mapping) else None,
            "practice_identity": context["practice_identity"],
            "practice_state_hash": context["practice_hash"],
            "fit_hash": context["fit_hash"],
        },
        "results": {key: results[key] for key in sorted(results)},
        "errors": sorted(all_errors, key=stable_json),
        "warnings": sorted(set(warnings)),
        "reconciliation": reconciliation,
        "passed": not all_errors,
        "valid": not all_errors,
        "status": "pass" if not all_errors else "fail",
    }
    report["report_hash"] = "report:" + _digest(report)
    return report


def assert_artistic_program_payload(
    opportunity: Mapping[str, Any],
    practice: Mapping[str, Any],
    fit: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    report = evaluate_artistic_program_payload(opportunity, practice, fit, payload)
    if not report["valid"]:
        codes = ",".join(_error_codes(report["errors"]))
        raise ArtisticProgramEvaluationError(f"artistic_program_rejected:{codes}", report)
    return True


evaluate_artistic_program_candidates = evaluate_artistic_program_payload
assert_artistic_program_candidates = assert_artistic_program_payload
evaluate_artistic_program_hypotheses = evaluate_artistic_program_payload
assert_artistic_program_hypotheses = assert_artistic_program_payload


__all__ = [
    "ALGORITHM_VERSION", "ArtisticProgramEvaluationError", "CANDIDATE_SCHEMA",
    "PROGRAM_FIELDS", "PROGRAM_ID_ALGORITHM", "REPORT_SCHEMA", "fit_input_hash_for", "stable_json",
    "assert_artistic_program_candidates", "assert_artistic_program_hypotheses",
    "assert_artistic_program_payload", "evaluate_artistic_program_candidates",
    "evaluate_artistic_program_hypotheses", "evaluate_artistic_program_payload",
    "program_id_for",
]
