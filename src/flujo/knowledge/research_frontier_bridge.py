"""Project the possibility field into non-dispatched Research frontier jobs.

This module is a pure read-only bridge. It reuses the domain vocabulary and
source policies from tools.research_job_router but never calls create_job and
never opens SQLite. Questions are copied from the fit action that owns the
referenced action ID. The only generated question is the explicit technical
refresh of an opportunity's official validity.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json

from tools.research_job_router import ADAPTERS, detect_domain
from .opportunity_constraints import validate_opportunity_constraints


SCHEMA = "mak-research-frontier-jobs-v1"
POSSIBILITY_SCHEMA = "mak-possibility-field-v1"
FIT_SCHEMA = "mak-opportunity-fit-v1"
OPPORTUNITY_SCHEMA = "mak-opportunity-constraints-v1"
ALGORITHM_VERSION = "possibility-to-research-frontier-1"
JOB_STATUS = "planned_not_dispatched"

_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "input_hashes",
    "control", "jobs", "abstentions", "rejected_candidates",
    "adapter_projection", "provenance", "reconciliation",
}
_JOB_FIELDS = {
    "job_id", "candidate_id", "opportunity_id", "requirement_ids",
    "research_action_ids", "question", "domain", "priority_rank", "voi",
    "source_policy", "independent_source_groups_required", "status", "dispatch",
    "provenance",
}
_FIT_DECISIONS = {"abstain", "supported", "contradicted"}
_GATE_STATUSES = {"abstain", "pass", "fail"}
_FRONTIER_KINDS = {"research_action", "missing_requirement", "risk_flag", "refresh_source_validity"}


class ResearchFrontierBridgeError(ValueError):
    """Invalid accepted input or invalid deterministic frontier payload."""


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ResearchFrontierBridgeError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ResearchFrontierBridgeError(f"{field}_required")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResearchFrontierBridgeError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ResearchFrontierBridgeError(f"{field}_must_be_list")
    return value


def _refs(value: Any, field: str, *, sorted_unique: bool = False) -> list[str]:
    rows = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise ResearchFrontierBridgeError(f"{field}_invalid")
    result = sorted(set(rows))
    if sorted_unique and rows != result:
        raise ResearchFrontierBridgeError(f"{field}_not_sorted_unique")
    return result


def _finite(value: Any, field: str, *, allow_none: bool = True) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResearchFrontierBridgeError(f"{field}_must_be_number")
    result = float(value)
    if not math.isfinite(result):
        raise ResearchFrontierBridgeError(f"{field}_not_finite")
    return result


def _canonical_possibility(field: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(field))
    for name, key in (
        ("candidates_ranked", "candidate_id"),
        ("abstained", "candidate_id"),
        ("rejected", "candidate_id"),
    ):
        rows = result.get(name, [])
        for row in rows:
            if isinstance(row, dict):
                for ref_key in ("requirement_ids", "missing_requirement_ids", "research_action_ids", "risk_flags"):
                    values = row.get(ref_key)
                    if isinstance(values, list):
                        row[ref_key] = sorted(set(values))
        result[name] = sorted(rows, key=lambda row: (str(row.get(key) or ""), stable_json(row)))
    result["research_frontier"] = sorted(result.get("research_frontier", []), key=stable_json)
    return result


def _validate_possibility(field: Mapping[str, Any]) -> None:
    if not isinstance(field, Mapping):
        raise ResearchFrontierBridgeError("possibility_must_be_object")
    if field.get("schema") != POSSIBILITY_SCHEMA:
        raise ResearchFrontierBridgeError("possibility_schema_invalid")
    for name in ("candidates_ranked", "abstained", "rejected", "research_frontier"):
        _list(field.get(name), "possibility." + name)
    if field.get("decision") is not None:
        _text(field.get("decision"), "possibility.decision")
    provenance = field.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ResearchFrontierBridgeError("possibility.provenance_invalid")
    if "errors" in provenance:
        _refs(provenance.get("errors", []), "possibility.provenance.errors")
    for name in ("candidates_ranked", "abstained", "rejected"):
        for index, raw in enumerate(field[name]):
            row = _mapping(raw, f"possibility.{name}[{index}]")
            candidate_id = row.get("candidate_id")
            if candidate_id is not None:
                _text(candidate_id, f"possibility.{name}[{index}].candidate_id")
            for key in ("research_action_ids", "missing_requirement_ids", "risk_flags"):
                if key in row:
                    _refs(row[key], f"possibility.{name}[{index}].{key}")
            if name == "candidates_ranked" and row.get("rank") is not None:
                if isinstance(row["rank"], bool) or not isinstance(row["rank"], int) or row["rank"] < 1:
                    raise ResearchFrontierBridgeError("possibility_rank_invalid")
    for index, raw in enumerate(field["research_frontier"]):
        row = _mapping(raw, f"possibility.research_frontier[{index}]")
        _text(row.get("candidate_id"), "possibility.frontier.candidate_id")
        kind = _text(row.get("kind"), "possibility.frontier.kind")
        if kind not in _FRONTIER_KINDS:
            raise ResearchFrontierBridgeError("possibility.frontier.kind_invalid")
        if "research_action_id" in row and row["research_action_id"] is not None:
            _text(row["research_action_id"], "possibility.frontier.research_action_id")
        if "requirement_id" in row and row["requirement_id"] is not None:
            _text(row["requirement_id"], "possibility.frontier.requirement_id")
        if "dispatch" in row and row["dispatch"] is not False:
            raise ResearchFrontierBridgeError("possibility.frontier_dispatch_must_be_false")


def _canonical_fit(fit: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(fit))
    validation = result.get("validation")
    if not isinstance(validation, Mapping):
        raise ResearchFrontierBridgeError("fit_validation_invalid")
    result["validation"] = dict(validation)
    result["validation"]["errors"] = sorted(_refs(result["validation"].get("errors", []), "fit.validation.errors"))
    result["matrix"] = sorted(result.get("matrix", []), key=lambda row: row.get("requirement_id", ""))
    for row in result["matrix"]:
        row["cells"] = sorted(row.get("cells", []), key=lambda cell: cell.get("evidence_ref", ""))
    result["required_but_unsupported"] = sorted(
        result.get("required_but_unsupported", []), key=lambda row: row.get("requirement_id", "")
    )
    result["research_job_candidates"] = sorted(
        result.get("research_job_candidates", []), key=lambda row: row.get("candidate_id", "")
    )
    return result


def _validate_fit(fit: Mapping[str, Any]) -> None:
    if not isinstance(fit, Mapping):
        raise ResearchFrontierBridgeError("fit_must_be_object")
    if fit.get("schema") != FIT_SCHEMA:
        raise ResearchFrontierBridgeError("fit_schema_invalid")
    validation = _mapping(fit.get("validation"), "fit.validation")
    if not isinstance(validation.get("valid"), bool):
        raise ResearchFrontierBridgeError("fit.validation.valid_invalid")
    _refs(validation.get("errors", []), "fit.validation.errors")
    if fit.get("decision") not in _FIT_DECISIONS:
        raise ResearchFrontierBridgeError("fit_decision_invalid")
    for field in ("matrix", "required_but_unsupported", "research_job_candidates"):
        _list(fit.get(field), "fit." + field)
    if fit.get("hard_gate_status", "abstain") not in _GATE_STATUSES:
        raise ResearchFrontierBridgeError("fit_hard_gate_status_invalid")
    if fit.get("source_gate_status", "abstain") not in _GATE_STATUSES:
        raise ResearchFrontierBridgeError("fit_source_gate_status_invalid")
    action_ids: list[str] = []
    for index, raw in enumerate(fit["research_job_candidates"]):
        row = _mapping(raw, f"fit.research_job_candidates[{index}]")
        action_ids.append(_text(row.get("candidate_id"), "fit.research_action_id"))
        _text(row.get("requirement_id"), "fit.research_requirement_id")
        _text(row.get("question"), "fit.research_question")
        _finite(row.get("voi"), "fit.research_voi")
        _finite(row.get("voi_numerator"), "fit.research_voi_numerator")
        _finite(row.get("voi_denominator"), "fit.research_voi_denominator")
    if len(action_ids) != len(set(action_ids)):
        raise ResearchFrontierBridgeError("fit_research_action_id_duplicate")


def _validate_opportunity(opportunity: Mapping[str, Any]) -> None:
    if not isinstance(opportunity, Mapping):
        raise ResearchFrontierBridgeError("opportunity_must_be_object")
    if opportunity.get("schema") != OPPORTUNITY_SCHEMA:
        raise ResearchFrontierBridgeError("opportunity_schema_invalid")
    _text(opportunity.get("opportunity_id"), "opportunity_id")
    _text(opportunity.get("input_hash"), "opportunity.input_hash")
    try:
        validate_opportunity_constraints(opportunity)
    except Exception as exc:
        raise ResearchFrontierBridgeError("opportunity_contract_invalid:" + str(exc)) from exc


def _adapter_for(action: Mapping[str, Any], question: str) -> tuple[str, Mapping[str, Any], str]:
    declared = action.get("domain")
    if isinstance(declared, str) and declared.strip():
        domain = declared.strip().casefold()
        if domain in ADAPTERS:
            return domain, ADAPTERS[domain], "fit_action"
        return "general", ADAPTERS["general"], "unknown_domain_fallback"
    detected, _scores = detect_domain(question)
    if detected not in ADAPTERS:
        detected = "general"
    return detected, ADAPTERS[detected], "router_detect_domain"


def _voi(action: Mapping[str, Any]) -> dict[str, Any]:
    value = _finite(action.get("voi"), "action.voi")
    numerator = _finite(action.get("voi_numerator"), "action.voi_numerator")
    denominator = _finite(action.get("voi_denominator"), "action.voi_denominator")
    status = _text(action.get("voi_status"), "action.voi_status", required=False) or "unresolved"
    if status == "defined" and (value is None or numerator is None or denominator is None):
        status = "unresolved"
    return {"value": value, "status": status, "numerator": numerator, "denominator": denominator}


def _job_id(semantic: Mapping[str, Any]) -> str:
    return "research-frontier:" + hashlib.sha256(stable_json(semantic).encode("utf-8")).hexdigest()


def _action_index(fit: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        _text(row.get("candidate_id"), "fit.research_action_id"): row
        for row in fit["research_job_candidates"]
    }


def _rank_index(field: Mapping[str, Any]) -> tuple[dict[str, int], set[str]]:
    ranks: dict[str, int] = {}
    rejected: set[str] = set()
    for index, row in enumerate(field["candidates_ranked"], 1):
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id.strip():
            ranks[candidate_id] = int(row.get("rank", index))
    next_rank = max(ranks.values(), default=0) + 1
    for row in sorted(field["abstained"], key=lambda item: (str(item.get("candidate_id") or ""), stable_json(item))):
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id.strip() and candidate_id not in ranks:
            ranks[candidate_id] = next_rank
            next_rank += 1
    for row in field["rejected"]:
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id.strip():
            rejected.add(candidate_id)
    return ranks, rejected


def _frontier_sources(
    field: Mapping[str, Any],
    action_index: Mapping[str, Mapping[str, Any]],
    opportunity_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ranks, rejected = _rank_index(field)
    by_candidate: dict[str, Mapping[str, Any]] = {}
    opportunity_candidate = f"opportunity-scope:{opportunity_id}"
    for name in ("candidates_ranked", "abstained"):
        for row in field[name]:
            candidate_id = row.get("candidate_id")
            if isinstance(candidate_id, str) and candidate_id.strip():
                by_candidate[candidate_id] = row

    def add(candidate_id: str, action_id: str | None, kind: str, requirement_id: str | None, source: str) -> None:
        if candidate_id in rejected:
            return
        rows.append({
            "candidate_id": candidate_id,
            "action_id": action_id or "",
            "kind": kind,
            "requirement_id": requirement_id or "",
            "source": source,
            "priority_rank": ranks.get(candidate_id, max(ranks.values(), default=0) + 1),
        })

    for index, raw in enumerate(field["research_frontier"]):
        row = dict(raw)
        candidate_id = _text(row.get("candidate_id"), "frontier.candidate_id")
        kind = _text(row.get("kind"), "frontier.kind")
        action_id = row.get("research_action_id")
        if action_id is not None:
            action_id = _text(action_id, "frontier.research_action_id")
        requirement_id = row.get("requirement_id")
        if requirement_id is not None:
            requirement_id = _text(requirement_id, "frontier.requirement_id")
        if kind == "research_action":
            add(candidate_id, action_id, kind, requirement_id, f"frontier:{index}")
        elif kind == "missing_requirement":
            matching = [
                action_id_for for action_id_for, action in action_index.items()
                if action.get("requirement_id") == requirement_id
            ]
            if matching:
                for action_id_for in sorted(matching):
                    add(candidate_id, action_id_for, kind, requirement_id, f"frontier:{index}")
            else:
                add(candidate_id, None, kind, requirement_id, f"frontier:{index}")
        elif kind == "refresh_source_validity":
            add(opportunity_candidate, None, kind, requirement_id, f"frontier:{index}")
        elif kind == "risk_flag" and "source" in str(row.get("risk_flag", "")).casefold():
            add(opportunity_candidate, None, "refresh_source_validity", requirement_id, f"frontier:{index}")

    for candidate_id, row in sorted(by_candidate.items()):
        if candidate_id in rejected:
            continue
        for action_id in _refs(row.get("research_action_ids", []), f"candidate.{candidate_id}.research_action_ids"):
            add(candidate_id, action_id, "research_action", None, f"candidate:{candidate_id}")
        if row.get("source_gate_status") == "abstain":
            add(opportunity_candidate, None, "refresh_source_validity", None, f"candidate:{candidate_id}")

    referenced_actions = {row["action_id"] for row in rows if row["action_id"]}
    for action_id, action in sorted(action_index.items()):
        if action_id in referenced_actions:
            continue
        requirement_id = action.get("requirement_id")
        add(
            opportunity_candidate,
            action_id,
            "research_action",
            requirement_id if isinstance(requirement_id, str) else None,
            f"fit:unbound-action:{action_id}",
        )
    return rows


def _make_job(
    source: Mapping[str, Any], action: Mapping[str, Any] | None, action_id: str,
    *, frontier_kind: str, requirement_id: str, opportunity: Mapping[str, Any],
    possibility_hash: str, fit_hash: str, priority_rank: int, frontier_sources: list[str],
    source_gate_status: str, hard_gate_status: str,
) -> dict[str, Any]:
    resolved = action is not None
    refresh = frontier_kind == "refresh_source_validity"
    if refresh:
        question = f"Verify current validity of opportunity {opportunity['opportunity_id']} from an official source"
        domain = "general"
        adapter = ADAPTERS[domain]
        domain_source = "technical_refresh"
        voi = {"value": None, "status": "unresolved", "numerator": None, "denominator": None}
        source_policy = "official-source-only"
        source_groups = 1
    elif resolved:
        question = _text(action.get("question"), "fit.research_question")
        domain, adapter, domain_source = _adapter_for(action, question)
        voi = _voi(action)
        source_policy = adapter["source_policy"]
        source_groups = action.get("independent_source_groups_required", 2)
        if isinstance(source_groups, bool) or not isinstance(source_groups, int) or source_groups < 1:
            source_groups = 2
    else:
        question = f"Unresolved research action reference {action_id}"
        domain = "general"
        adapter = ADAPTERS[domain]
        domain_source = "unresolved_action_fallback"
        voi = {"value": None, "status": "unresolved", "numerator": None, "denominator": None}
        source_policy = adapter["source_policy"]
        source_groups = 2
    resolved_requirement_id = requirement_id
    if refresh:
        # This is an operational source-validity probe, not an artistic
        # constraint. Keep it addressable by triangulation without borrowing
        # or inventing a requirement from the program domain.
        resolved_requirement_id = f"source-validity:{opportunity['opportunity_id']}"
    if not resolved_requirement_id and resolved:
        candidate_requirement_id = action.get("requirement_id")
        if isinstance(candidate_requirement_id, str) and candidate_requirement_id.strip():
            resolved_requirement_id = candidate_requirement_id.strip()
    requirement_ids = [resolved_requirement_id] if resolved_requirement_id else []
    semantic = {
        "candidate_id": source["candidate_id"],
        "opportunity_id": opportunity["opportunity_id"],
        "requirement_ids": requirement_ids,
        "research_action_ids": [action_id] if resolved else [],
        "question": question,
        "domain": domain,
        "frontier_kind": frontier_kind,
    }
    return {
        "job_id": _job_id(semantic),
        "candidate_id": source["candidate_id"],
        "opportunity_id": opportunity["opportunity_id"],
        "requirement_ids": requirement_ids,
        "research_action_ids": [action_id] if resolved else [],
        "question": question,
        "domain": domain,
        "priority_rank": priority_rank,
        "voi": voi,
        "source_policy": source_policy,
        "independent_source_groups_required": source_groups,
        "status": JOB_STATUS,
        "dispatch": False,
        "provenance": {
            "possibility_schema": POSSIBILITY_SCHEMA,
            "fit_schema": FIT_SCHEMA,
            "opportunity_schema": OPPORTUNITY_SCHEMA,
            "possibility_field_hash": possibility_hash,
            "fit_input_hash": fit_hash,
            "opportunity_input_hash": opportunity["input_hash"],
            "frontier_kind": frontier_kind,
            "frontier_sources": sorted(set(frontier_sources)),
            "action_resolved": resolved,
            "action_id_received": action_id or None,
            "domain_source": domain_source,
            "source_gate_status": source_gate_status,
            "hard_gate_status": hard_gate_status,
            "create_job_invoked": False,
            "adapter_projection": {
                "question": question,
                "domain": domain,
                "source_policy": source_policy,
                "constraint_policy": adapter["constraint_policy"] if not refresh else "official source only; do not infer current validity from a local snapshot",
                "create_job_compatible": True,
                "create_job_invoked": False,
            },
            "dispatch": False,
        },
    }


def _validate_job(job: Mapping[str, Any], action_ids: set[str], opportunity_id: str) -> None:
    if set(job) != _JOB_FIELDS:
        raise ResearchFrontierBridgeError("job_fields_invalid")
    _text(job.get("job_id"), "job.job_id")
    _text(job.get("candidate_id"), "job.candidate_id")
    if job.get("opportunity_id") != opportunity_id:
        raise ResearchFrontierBridgeError("job_opportunity_id_mismatch")
    _refs(job.get("requirement_ids"), "job.requirement_ids", sorted_unique=True)
    action_refs = _refs(job.get("research_action_ids"), "job.research_action_ids", sorted_unique=True)
    if any(action_id not in action_ids for action_id in action_refs):
        raise ResearchFrontierBridgeError("job_action_id_unresolved")
    _text(job.get("question"), "job.question")
    _text(job.get("domain"), "job.domain")
    if isinstance(job.get("priority_rank"), bool) or not isinstance(job.get("priority_rank"), int) or job["priority_rank"] < 1:
        raise ResearchFrontierBridgeError("job_priority_invalid")
    voi = _mapping(job.get("voi"), "job.voi")
    if set(voi) != {"value", "status", "numerator", "denominator"}:
        raise ResearchFrontierBridgeError("job_voi_fields_invalid")
    _finite(voi.get("value"), "job.voi.value")
    _finite(voi.get("numerator"), "job.voi.numerator")
    _finite(voi.get("denominator"), "job.voi.denominator")
    _text(voi.get("status"), "job.voi.status")
    _text(job.get("source_policy"), "job.source_policy")
    if isinstance(job.get("independent_source_groups_required"), bool) or not isinstance(job.get("independent_source_groups_required"), int) or job["independent_source_groups_required"] < 1:
        raise ResearchFrontierBridgeError("job_source_groups_invalid")
    if job.get("status") != JOB_STATUS or job.get("dispatch") is not False:
        raise ResearchFrontierBridgeError("job_dispatch_state_invalid")
    provenance = _mapping(job.get("provenance"), "job.provenance")
    if provenance.get("dispatch") is not False or provenance.get("create_job_invoked") is not False:
        raise ResearchFrontierBridgeError("job_provenance_dispatch_invalid")


def _abstentions(field: Mapping[str, Any], fit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in field["abstained"]:
        if isinstance(row, Mapping):
            candidate_id = row.get("candidate_id")
            if isinstance(candidate_id, str) and candidate_id.strip():
                rows.append({"candidate_id": candidate_id, "source": "possibility_field", "reason": "candidate_abstained"})
    for error in fit["validation"].get("errors", []):
        rows.append({"candidate_id": None, "source": "opportunity_fit", "reason": "fit_validation:" + error})
    if fit["decision"] == "abstain":
        rows.append({"candidate_id": None, "source": "opportunity_fit", "reason": "fit_decision_abstain"})
    if fit["decision"] == "contradicted":
        rows.append({"candidate_id": None, "source": "opportunity_fit", "reason": "fit_decision_contradicted"})
    return sorted(rows, key=stable_json)


def _validate_payload(
    opportunity: Mapping[str, Any], possibility: Mapping[str, Any], fit: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    _validate_opportunity(opportunity)
    _validate_possibility(possibility)
    _validate_fit(fit)
    if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
        raise ResearchFrontierBridgeError("payload_fields_invalid")
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ResearchFrontierBridgeError("payload_schema_invalid")
    if payload.get("opportunity_id") != opportunity["opportunity_id"]:
        raise ResearchFrontierBridgeError("payload_opportunity_id_invalid")
    canonical_possibility = _canonical_possibility(possibility)
    canonical_fit = _canonical_fit(fit)
    expected_hashes = {
        "possibility_field": _hash(canonical_possibility),
        "opportunity_fit": _hash(canonical_fit),
        "opportunity_constraints": opportunity["input_hash"],
    }
    if payload.get("input_hashes") != expected_hashes:
        raise ResearchFrontierBridgeError("payload_input_hashes_invalid")
    action_ids = set(_action_index(canonical_fit))
    jobs = _list(payload.get("jobs"), "payload.jobs")
    job_ids = [job.get("job_id") for job in jobs if isinstance(job, Mapping)]
    if job_ids != sorted(job_ids) or len(job_ids) != len(set(job_ids)):
        raise ResearchFrontierBridgeError("payload_job_order_invalid")
    for job in jobs:
        _validate_job(_mapping(job, "payload.job"), action_ids, opportunity["opportunity_id"])
    if payload.get("rejected_candidates") != sorted(_rank_index(canonical_possibility)[1]):
        raise ResearchFrontierBridgeError("payload_rejected_candidates_invalid")
    control = _mapping(payload.get("control"), "payload.control")
    if control.get("all_dispatch_disabled") is not True or not isinstance(control.get("input_valid"), bool):
        raise ResearchFrontierBridgeError("payload_control_invalid")
    adapter_projection = _list(payload.get("adapter_projection"), "payload.adapter_projection")
    expected_projection = [
        {
            "job_id": job["job_id"],
            "question": job["question"],
            "domain": job["domain"],
            "source_policy": job["source_policy"],
            "constraint_policy": job["provenance"]["adapter_projection"]["constraint_policy"],
            "create_job_compatible": True,
            "create_job_invoked": False,
        }
        for job in jobs
    ]
    if adapter_projection != expected_projection:
        raise ResearchFrontierBridgeError("payload_adapter_projection_invalid")
    if payload.get("abstentions") != _abstentions(canonical_possibility, canonical_fit):
        raise ResearchFrontierBridgeError("payload_abstentions_invalid")
    reconciliation = _mapping(payload.get("reconciliation"), "payload.reconciliation")
    if reconciliation.get("job_count") != len(jobs) or reconciliation.get("dispatch_count") != 0:
        raise ResearchFrontierBridgeError("payload_reconciliation_invalid")
    if reconciliation.get("deterministic_order") is not True:
        raise ResearchFrontierBridgeError("payload_deterministic_order_invalid")
    return True


def compile_research_frontier(
    possibility: Mapping[str, Any], fit: Mapping[str, Any], opportunity: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a pure, non-dispatched frontier from accepted contracts."""
    _validate_opportunity(opportunity)
    _validate_possibility(possibility)
    _validate_fit(fit)
    canonical_possibility = _canonical_possibility(possibility)
    canonical_fit = _canonical_fit(fit)
    possibility_hash = _hash(canonical_possibility)
    fit_hash = _hash(canonical_fit)
    action_index = _action_index(canonical_fit)
    ranks, rejected = _rank_index(canonical_possibility)
    possibility_errors = canonical_possibility.get("provenance", {}).get("errors", [])
    fit_errors = canonical_fit["validation"].get("errors", [])
    input_valid = canonical_fit["validation"].get("valid") is True and not fit_errors and not possibility_errors
    sources = _frontier_sources(
        canonical_possibility, action_index, opportunity["opportunity_id"]
    ) if input_valid else []
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    fit_source_gate = canonical_fit.get("source_gate_status", "abstain")
    fit_hard_gate = canonical_fit.get("hard_gate_status", "abstain")
    for source in sources:
        candidate_id = source["candidate_id"]
        if candidate_id in rejected:
            continue
        action_id = source["action_id"]
        frontier_kind = source["kind"]
        action = action_index.get(action_id) if action_id else None
        normalized_requirement_id = source["requirement_id"]
        if action is not None:
            action_requirement_id = action.get("requirement_id")
            if isinstance(action_requirement_id, str) and action_requirement_id.strip():
                normalized_requirement_id = action_requirement_id.strip()
        grouping_kind = "resolved_action" if action_id else frontier_kind
        key = (candidate_id, action_id, grouping_kind, normalized_requirement_id)
        entry = grouped.setdefault(key, {**source, "frontier_sources": []})
        entry["frontier_sources"].append(source["source"])
    jobs: list[dict[str, Any]] = []
    for key, source in sorted(grouped.items(), key=lambda item: item[0]):
        candidate_id, action_id, _grouping_kind, requirement_id = key
        frontier_kind = source["kind"]
        jobs.append(_make_job(
            source, action_index.get(action_id) if action_id else None, action_id,
            frontier_kind=frontier_kind, requirement_id=requirement_id,
            opportunity=opportunity, possibility_hash=possibility_hash,
            fit_hash=fit_hash, priority_rank=ranks.get(candidate_id, source["priority_rank"]),
            frontier_sources=source["frontier_sources"],
            source_gate_status=fit_source_gate, hard_gate_status=fit_hard_gate,
        ))
    jobs.sort(key=lambda row: row["job_id"])
    adapter_projection = [
        {
            "job_id": job["job_id"],
            "question": job["question"],
            "domain": job["domain"],
            "source_policy": job["source_policy"],
            "constraint_policy": job["provenance"]["adapter_projection"]["constraint_policy"],
            "create_job_compatible": True,
            "create_job_invoked": False,
        }
        for job in jobs
    ]
    payload = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity["opportunity_id"],
        "input_hashes": {
            "possibility_field": possibility_hash,
            "opportunity_fit": fit_hash,
            "opportunity_constraints": opportunity["input_hash"],
        },
        "control": {
            "possibility_decision": canonical_possibility.get("decision"),
            "fit_decision": canonical_fit["decision"],
            "source_gate_status": fit_source_gate,
            "hard_gate_status": fit_hard_gate,
            "rejected_candidate_ids": sorted(rejected),
            "all_dispatch_disabled": True,
            "input_valid": input_valid,
            "invalid_input_reasons": sorted(
                (["fit_validation_invalid"] if canonical_fit["validation"].get("valid") is not True else [])
                + ["fit:" + error for error in fit_errors]
                + ["possibility:" + error for error in possibility_errors]
            ),
        },
        "jobs": jobs,
        "abstentions": _abstentions(canonical_possibility, canonical_fit),
        "rejected_candidates": sorted(rejected),
        "adapter_projection": adapter_projection,
        "provenance": {
            "possibility_schema": POSSIBILITY_SCHEMA,
            "fit_schema": FIT_SCHEMA,
            "opportunity_schema": OPPORTUNITY_SCHEMA,
            "source_rescan": False,
            "database_write": False,
            "network_called": False,
            "create_job_invoked": False,
        },
        "reconciliation": {
            "job_count": len(jobs),
            "resolved_action_job_count": sum(bool(job["research_action_ids"]) for job in jobs),
            "unresolved_action_job_count": sum(not job["research_action_ids"] for job in jobs),
            "dispatch_count": 0,
            "rejected_candidate_count": len(rejected),
            "invalid_input": not input_valid,
            "invalid_input_reason_count": len(
                (["fit_validation_invalid"] if canonical_fit["validation"].get("valid") is not True else [])
                + ["fit:" + error for error in fit_errors]
                + ["possibility:" + error for error in possibility_errors]
            ),
            "duplicate_frontier_groups_collapsed": sum(max(0, len(source["frontier_sources"]) - 1) for source in grouped.values()),
            "candidate_ids_preserved": len({job["candidate_id"] for job in jobs}) <= len(jobs),
            "deterministic_order": jobs == sorted(jobs, key=lambda row: row["job_id"]),
            "source_gate_status": fit_source_gate,
            "hard_gate_status": fit_hard_gate,
        },
    }
    _validate_payload(opportunity, canonical_possibility, canonical_fit, payload)
    return payload


def validate_research_frontier_payload(
    possibility: Mapping[str, Any], fit: Mapping[str, Any], opportunity: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    return _validate_payload(opportunity, possibility, fit, payload)


compile_frontier = compile_research_frontier
validate_payload = validate_research_frontier_payload


__all__ = [
    "ALGORITHM_VERSION", "JOB_STATUS", "ResearchFrontierBridgeError", "SCHEMA",
    "compile_frontier", "compile_research_frontier", "stable_json", "validate_payload",
    "validate_research_frontier_payload",
]
