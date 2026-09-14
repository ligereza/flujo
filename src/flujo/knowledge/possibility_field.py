"""Deterministic strategic field for artistic-program hypotheses.

The module aggregates evaluated candidates; it does not certify meaning,
quality, or eligibility, and does not generate a portfolio or application.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ._contract_helpers import nullable_text as _text
from ._io_helpers import load_json_file as load_json


CANDIDATE_SCHEMA = "mak-artistic-program-candidates-v1"
EVALUATION_SCHEMA = "mak-artistic-program-evaluation-v1"
FIELD_SCHEMA = "mak-possibility-field-v1"

SCORE_WEIGHTS = {
    "evidence": 0.25,
    "requirement_coverage": 0.20,
    "research_readiness_voi": 0.15,
    "capability_reuse": 0.15,
    "diversity": 0.15,
    "risk": -0.04,
    "contradiction": -0.04,
    "cost": -0.02,
}
_COMPONENT_KEYS = tuple(SCORE_WEIGHTS)
_POSITIVE = {"accepted", "accept", "approved"}
_REJECTED = {"rejected", "reject", "discarded"}
_ABSTAINED = {"abstained", "abstain", "unknown", "unresolved", "invalid"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _refs(value: Any) -> list[str]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return sorted({item.strip() for item in values if isinstance(item, str) and item.strip()})


def _bounded(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _bundle_rows(value: Any, schema: str, keys: tuple[str, ...]) -> tuple[list[Mapping[str, Any]], list[str]]:
    bundles = value if isinstance(value, list) else [value]
    rows: list[Mapping[str, Any]] = []
    errors: list[str] = []
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, Mapping):
            errors.append(f"bundle_{index}_not_object")
            continue
        if bundle.get("schema") != schema:
            errors.append(f"bundle_{index}_schema_invalid")
        raw_rows = None
        for key in keys:
            value = bundle.get(key)
            if isinstance(value, list):
                raw_rows = value
                break
            if key == "results" and isinstance(value, Mapping):
                raw_rows = list(value.values())
                break
        if raw_rows is None:
            errors.append(f"bundle_{index}_rows_missing")
            continue
        for row_index, row in enumerate(raw_rows):
            if not isinstance(row, Mapping):
                errors.append(f"bundle_{index}_row_{row_index}_not_object")
            else:
                rows.append(row)
    return rows, errors


def _status(row: Mapping[str, Any], evaluation: Mapping[str, Any] | None = None) -> str:
    values = [row.get("decision"), row.get("status"), row.get("evaluation_status")]
    if evaluation:
        values = [evaluation.get("result"), evaluation.get("decision"), evaluation.get("status"), *values]
    for value in values:
        status = _text(value)
        if status:
            return status.casefold()
    return "unknown"


def _reasons(*rows: Mapping[str, Any] | None) -> list[Any]:
    result: list[Any] = []
    for row in rows:
        if not row:
            continue
        for key in ("errors", "warnings", "reasons", "rejection_reasons", "abstention_reasons", "reason"):
            value = row.get(key)
            if isinstance(value, list):
                result.extend(value)
            elif value is not None:
                result.append(value)
    return result


def _stable_unique_json_values(values: Iterable[Any]) -> list[Any]:
    """Deduplicate JSON-like reasons without changing their structure."""
    keyed: dict[str, Any] = {}
    for value in values:
        key = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        keyed.setdefault(key, value)
    return [keyed[key] for key in sorted(keyed)]


def _alignment_gate(row: Mapping[str, Any], evaluation: Mapping[str, Any] | None, key: str) -> tuple[str, str]:
    source = (evaluation or {}).get(key)
    if not isinstance(source, Mapping):
        source = row.get(key) if isinstance(row.get(key), Mapping) else {}
    declared = _text(source.get("declared"))
    passed = source.get("passed")
    if declared == "pass" and passed is True:
        return "pass", f"{key}:declared_passed"
    if declared == "fail":
        return "fail", f"{key}:declared_or_passed_failed"
    if declared in {"abstain", "unknown", "stale"}:
        return "abstain", f"{key}:declared_abstain"
    if passed is False:
        return "fail", f"{key}:declared_or_passed_failed"
    return "abstain", f"{key}:not_declared_pass"


def _metric(row: Mapping[str, Any], evaluation: Mapping[str, Any] | None, names: tuple[str, ...], default: float = 0.0) -> tuple[float, bool]:
    sources = [row, evaluation or {}]
    features = (evaluation or {}).get("learning_features")
    if not isinstance(features, Mapping):
        features = (row.get("learning_features") if isinstance(row.get("learning_features"), Mapping) else {})
    sources = [row, evaluation or {}, features]
    for source in sources:
        for name in names:
            value = _bounded(source.get(name))
            if value is not None:
                return max(0.0, min(1.0, value)), True
    return default, False


def _candidate_record(row: Mapping[str, Any], evaluation: Mapping[str, Any] | None) -> dict[str, Any]:
    candidate_id = _text(row.get("candidate_id")) or _text(row.get("program_id"))
    unit_ids = _refs(row.get("unit_ids"))
    evidence_refs = _refs(row.get("evidence_refs"))
    resources = _refs(row.get("resource_refs")) or _refs(row.get("resources"))
    features = (evaluation or {}).get("learning_features") if isinstance(evaluation, Mapping) else None
    features = features if isinstance(features, Mapping) else {}
    components: dict[str, float] = {}
    observed: dict[str, bool] = {}
    for key, names in {
        "evidence": ("evidence_score", "evidence_coverage"),
        "requirement_coverage": ("requirement_coverage", "coverage"),
        "research_readiness_voi": ("research_readiness", "voi", "voi_score"),
        "capability_reuse": ("capability_reuse", "reuse_score"),
        "risk": ("risk", "risk_score"),
        "contradiction": ("contradiction", "contradiction_score"),
        "cost": ("cost", "cost_score"),
    }.items():
        components[key], observed[key] = _metric(row, evaluation, names)
    evidence_count = _bounded(features.get("evidence_ref_count"))
    counterevidence_count = _bounded(features.get("counterevidence_ref_count"))
    if evidence_count is not None and counterevidence_count is not None and evidence_count + counterevidence_count > 0:
        components["evidence"] = evidence_count / (evidence_count + counterevidence_count)
        observed["evidence"] = True
    requirement_count = _bounded(features.get("requirement_count"))
    missing_count = _bounded(features.get("missing_requirement_count"))
    if requirement_count is not None and missing_count is not None and requirement_count > 0:
        components["requirement_coverage"] = max(0.0, min(1.0, (requirement_count - missing_count) / requirement_count))
        observed["requirement_coverage"] = True
    action_ids = _refs(row.get("research_action_ids"))
    missing_ids = _refs(row.get("missing_requirement_ids"))
    if action_ids or missing_ids:
        components["research_readiness_voi"] = len(action_ids) / (len(action_ids) + len(missing_ids)) if action_ids or missing_ids else 0.0
        observed["research_readiness_voi"] = True
    if resources:
        components["capability_reuse"] = 1.0
        observed["capability_reuse"] = True
    risk_count = _bounded(features.get("risk_flag_count"))
    if risk_count is not None:
        components["risk"] = min(1.0, risk_count)
        observed["risk"] = True
    if counterevidence_count is not None:
        components["contradiction"] = min(1.0, counterevidence_count)
        observed["contradiction"] = True
    components["diversity"] = 0.0
    status = _status(row, evaluation)
    source_gate_status, source_gate_reason = _alignment_gate(row, evaluation, "source_gate_alignment")
    hard_gate_status, _ = _alignment_gate(row, evaluation, "hard_gate_alignment")
    return {
        "candidate_id": candidate_id,
        "title": _text(row.get("title")) or _text(row.get("name")) or candidate_id,
        "unit_ids": unit_ids,
        "evidence_refs": evidence_refs,
        "resource_refs": resources,
        "status": status,
        "source_gate_status": source_gate_status,
        "source_gate_reason": source_gate_reason,
        "hard_gate_status": hard_gate_status,
        "ready": status in _POSITIVE and source_gate_status == "pass" and hard_gate_status in {"pass", "passed"},
        "components": components,
        "component_observed": observed,
        "research_gaps": row.get("research_gaps", row.get("gaps", [])),
        "learning_features": dict(features),
        "research_action_ids": action_ids,
        "missing_requirement_ids": missing_ids,
        "basis": _text(row.get("basis")) or "unknown",
        "requirement_ids": _refs(row.get("requirement_ids")),
        "risk_flags": _refs(row.get("risk_flags")),
        "reasons": _reasons(row, evaluation),
        "raw": row,
    }


def _base_score(record: Mapping[str, Any]) -> float:
    components = record["components"]
    return round(sum(SCORE_WEIGHTS[key] * components[key] for key in _COMPONENT_KEYS if key != "diversity"), 12)


def _fit_inputs(candidate_bundles: Any, evaluation_bundles: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    candidates, errors = _bundle_rows(candidate_bundles, CANDIDATE_SCHEMA, ("candidates", "program_candidates"))
    evaluations, eval_errors = _bundle_rows(evaluation_bundles, EVALUATION_SCHEMA, ("results", "evaluations", "candidate_evaluations"))
    errors.extend(eval_errors)
    eval_by_id = {
        (_text(row.get("program_id")) or _text(row.get("candidate_id"))): row
        for row in evaluations
        if _text(row.get("program_id")) or _text(row.get("candidate_id"))
    }
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    abstained: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(candidates):
        candidate_id = _text(row.get("candidate_id")) or _text(row.get("program_id"))
        if not candidate_id:
            abstained.append({"candidate_id": None, "reasons": ["candidate_id_missing"]})
            continue
        if candidate_id in seen:
            abstained.append({"candidate_id": candidate_id, "reasons": ["candidate_id_duplicate"]})
            continue
        seen.add(candidate_id)
        evaluation = eval_by_id.get(candidate_id)
        if evaluation is None:
            abstained.append({**_candidate_record(row, None), "reasons": ["evaluation_missing"]})
            continue
        record = _candidate_record(row, evaluation)
        status = record["status"]
        if status in _POSITIVE:
            valid.append(record)
        elif status in _REJECTED:
            rejection_reasons = list(record["reasons"] or ["evaluation_rejected"])
            if record["source_gate_status"] != "pass":
                rejection_reasons.append(f"source_gate:{record['source_gate_status']}")
            if record["hard_gate_status"] not in {"pass", "passed"}:
                rejection_reasons.append(f"hard_gate:{record['hard_gate_status']}")
            rejected.append({**record, "reasons": _stable_unique_json_values(rejection_reasons)})
        else:
            abstained.append({**record, "reasons": record["reasons"] or ["evaluation_abstained_or_unknown"]})
    return valid, rejected, abstained, sorted(set(errors))


def build_possibility_field(candidate_bundles: Any, evaluation_bundles: Any) -> dict[str, Any]:
    accepted, rejected, abstained, errors = _fit_inputs(candidate_bundles, evaluation_bundles)
    if errors:
        return {
            "schema": FIELD_SCHEMA, "candidates_ranked": [], "rejected": rejected,
            "abstained": abstained, "research_frontier": [], "resource_conflicts": [],
            "diversity_summary": {"selected": [], "unique_unit_ids": [], "unique_evidence_refs": []},
            "score_policy": {"weights": SCORE_WEIGHTS, "components": list(_COMPONENT_KEYS), "non_probabilistic": True},
            "provenance": {"candidate_schemas": [CANDIDATE_SCHEMA], "evaluation_schemas": [EVALUATION_SCHEMA], "errors": errors},
            "learning_gate": {"training_permitted": False}, "decision": "abstain",
        }

    for record in accepted:
        record["base_score"] = _base_score(record)
    selected_units: set[str] = set()
    selected_evidence: set[str] = set()
    selected_resources: set[str] = set()
    conflicts: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    remaining = list(accepted)
    order = 0
    while remaining:
        scored_remaining: list[tuple[float, str, dict[str, Any], list[str], list[str], list[str], float]] = []
        for candidate in remaining:
            unit_overlap = sorted(selected_units.intersection(candidate["unit_ids"]))
            evidence_overlap = sorted(selected_evidence.intersection(candidate["evidence_refs"]))
            resource_overlap = sorted(selected_resources.intersection(candidate["resource_refs"]))
            diversity_value = 1.0 if not unit_overlap and not evidence_overlap else 0.0
            score = round(candidate["base_score"] + SCORE_WEIGHTS["diversity"] * diversity_value, 12)
            scored_remaining.append((score, candidate["candidate_id"], candidate, unit_overlap, evidence_overlap, resource_overlap, diversity_value))
        best_score = max(item[0] for item in scored_remaining)
        score, _, record, unit_overlap, evidence_overlap, resource_overlap, diversity_value = min(
            (item for item in scored_remaining if item[0] == best_score), key=lambda item: item[1]
        )
        order += 1
        record["components"]["diversity"] = diversity_value
        if resource_overlap:
            conflicts.append({"candidate_id": record["candidate_id"], "with_resources": resource_overlap})
        ranked.append({
            "candidate_id": record["candidate_id"], "title": record["title"], "rank": order,
            "score": score, "base_score": record["base_score"], "components": record["components"],
            "component_observed": record["component_observed"], "unit_ids": record["unit_ids"],
            "evidence_refs": record["evidence_refs"], "resource_refs": record["resource_refs"],
            "basis": record["basis"], "requirement_ids": record["requirement_ids"],
            "missing_requirement_ids": record["missing_requirement_ids"],
            "research_action_ids": record["research_action_ids"], "risk_flags": record["risk_flags"],
            "ready": record["ready"], "source_gate_status": record["source_gate_status"],
            "hard_gate_status": record["hard_gate_status"], "research_gaps": record["research_gaps"],
            "learning_features": record["learning_features"], "selection": "ranked",
        })
        selected_units.update(record["unit_ids"])
        selected_evidence.update(record["evidence_refs"])
        selected_resources.update(record["resource_refs"])
        remaining.remove(record)

    frontier = []
    frontier_sources = ranked + [item for item in abstained if item.get("candidate_id")]
    for item in frontier_sources:
        candidate_id = item["candidate_id"]
        for requirement_id in _refs(item.get("missing_requirement_ids")):
            frontier.append({"candidate_id": candidate_id, "kind": "missing_requirement", "requirement_id": requirement_id, "dispatch": False})
        for action_id in _refs(item.get("research_action_ids")):
            frontier.append({"candidate_id": candidate_id, "kind": "research_action", "research_action_id": action_id, "dispatch": False})
        for risk_flag in _refs(item.get("risk_flags")):
            frontier.append({"candidate_id": candidate_id, "kind": "risk_flag", "risk_flag": risk_flag, "dispatch": False})
            if item.get("source_gate_status") == "abstain" and "source" in risk_flag.casefold():
                frontier.append({"candidate_id": candidate_id, "kind": "refresh_source_validity", "risk_flag": risk_flag, "dispatch": False})
    frontier.sort(key=lambda item: (item["candidate_id"], item["kind"], json.dumps(item, sort_keys=True, ensure_ascii=False)))
    conflicts.sort(key=lambda item: (item["candidate_id"], item["with_resources"]))
    return {
        "schema": FIELD_SCHEMA, "decision": "supported" if ranked else "abstain",
        "candidates_ranked": ranked, "rejected": rejected, "abstained": abstained,
        "research_frontier": frontier, "resource_conflicts": conflicts,
        "diversity_summary": {"selected": [item["candidate_id"] for item in ranked], "unique_unit_ids": sorted(selected_units), "unique_evidence_refs": sorted(selected_evidence)},
        "score_policy": {"weights": SCORE_WEIGHTS, "components": list(_COMPONENT_KEYS), "non_probabilistic": True, "tie_break": "candidate_id_ascending"},
        "provenance": {"candidate_schemas": [CANDIDATE_SCHEMA], "evaluation_schemas": [EVALUATION_SCHEMA], "accepted_count": len(ranked), "rejected_count": len(rejected), "abstained_count": len(abstained)},
        "learning_gate": {"training_permitted": False, "features_carried": any(bool(item["learning_features"]) for item in ranked)},
    }
