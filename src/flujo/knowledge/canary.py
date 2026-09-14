"""Read-only canary evaluation for MAK Learn v2.

Canaries are labelled cases from projects that are not present in the
training population.  This module validates the boundary and computes a
report; persistence is explicit and records evidence only.  It never changes
the active router or promotes a candidate lesson.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from .project_ir import LearningStore, ProjectIRError, stable_json


CANARY_SCHEMA = "mak-learning-canary-v1"


class CanaryError(ValueError):
    """A canary packet is incomplete, leaked or ambiguous."""


def _declared_cases(cases: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, Mapping):
            raise CanaryError("canary_case_not_mapping")
        case_id = str(case.get("case_id") or "").strip()
        project_id = str(case.get("project_id") or "").strip()
        group_id = str(case.get("group_id") or "").strip()
        expected_label = str(case.get("expected_label") or "").strip()
        refs = case.get("source_refs")
        validator = case.get("validator")
        validation = case.get("validation")
        if not case_id or case_id in seen:
            raise CanaryError("canary_duplicate_or_missing_case_id")
        if not project_id:
            raise CanaryError(f"canary_missing_project_id: {case_id}")
        if not group_id:
            raise CanaryError(f"canary_missing_group_id: {case_id}")
        if not expected_label:
            raise CanaryError(f"canary_missing_expected_label: {case_id}")
        if not isinstance(refs, list) or not refs or not all(str(ref).strip() for ref in refs):
            raise CanaryError(f"canary_missing_source_refs: {case_id}")
        if not isinstance(validator, Mapping) or not str(validator.get("kind") or "").strip():
            raise CanaryError(f"canary_missing_validator: {case_id}")
        validation_status = str(validation.get("status") or "").casefold() if isinstance(validation, Mapping) else ""
        if validation_status not in {"ok", "passed", "verified"}:
            raise CanaryError(f"canary_validation_not_passed: {case_id}")
        normalized.append({
            "case_id": case_id,
            "project_id": project_id,
            "group_id": group_id,
            "expected_label": expected_label,
            "source_refs": [str(ref).strip() for ref in refs],
            "validator": dict(validator),
            "validation": dict(validation),
        })
        seen.add(case_id)
    if not normalized:
        raise CanaryError("canary_missing_cases")
    return normalized


def canary_fingerprint(cases: Iterable[Mapping[str, Any]]) -> str:
    """Fingerprint declarations, excluding candidate predictions."""
    normalized = _declared_cases(cases)
    return hashlib.sha256(stable_json(normalized).encode("utf-8")).hexdigest()


def evaluate_canary(
    cases: Iterable[Mapping[str, Any]],
    predictions: Mapping[str, Any],
    *,
    candidate_policy_id: str,
    training_project_ids: Iterable[str],
    training_group_ids: Iterable[str],
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a candidate against explicit, out-of-training cases."""
    candidate_policy_id = str(candidate_policy_id or "").strip()
    if not candidate_policy_id:
        raise CanaryError("canary_missing_candidate_policy")
    declared = _declared_cases(cases)
    training = {str(project_id).strip() for project_id in training_project_ids if str(project_id).strip()}
    if not training:
        raise CanaryError("canary_training_population_required")
    training_groups = {str(group_id).strip() for group_id in training_group_ids if str(group_id).strip()}
    if not training_groups:
        raise CanaryError("canary_training_groups_required")
    leaked = sorted({case["project_id"] for case in declared} & training)
    if leaked:
        raise CanaryError("canary_project_in_training: " + ",".join(leaked))
    leaked_groups = sorted({case["group_id"] for case in declared} & training_groups)
    if leaked_groups:
        raise CanaryError("canary_group_in_training: " + ",".join(leaked_groups))

    correct = 0
    missing: list[str] = []
    errors: list[dict[str, str]] = []
    baseline_correct = 0
    for case in declared:
        case_id = case["case_id"]
        expected = case["expected_label"]
        prediction = predictions.get(case_id)
        if isinstance(prediction, Mapping):
            actual = str(prediction.get("label") or prediction.get("tool_id") or "").strip()
        else:
            actual = str(prediction or "").strip()
        if not actual or actual.casefold() in {"abstain", "abstained"}:
            missing.append(case_id)
        elif actual == expected:
            correct += 1
        else:
            errors.append({"case_id": case_id, "expected": expected, "actual": actual})
        if baseline is not None:
            base = baseline.get(case_id)
            base_label = str(base.get("label") or base.get("tool_id") or "").strip() if isinstance(base, Mapping) else str(base or "").strip()
            baseline_correct += int(base_label == expected)

    total = len(declared)
    status = "failed" if errors else ("abstained" if missing else "passed")
    return {
        "schema": CANARY_SCHEMA,
        "candidate_policy_id": candidate_policy_id,
        "dataset_fingerprint": canary_fingerprint(declared),
        "status": status,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "missing": len(missing),
        "missing_case_ids": missing,
        "errors": errors,
        "new_project_count": len({case["project_id"] for case in declared}),
        "new_project_ids": sorted({case["project_id"] for case in declared}),
        "new_group_ids": sorted({case["group_id"] for case in declared}),
        "case_ids": [case["case_id"] for case in declared],
        "baseline_correct": baseline_correct if baseline is not None else None,
    }


def record_canary_evaluation(
    database: str | Path,
    report: Mapping[str, Any],
    *,
    target_kind: str,
    target_id: str,
    evidence: Iterable[Mapping[str, Any]] = (),
    evaluation_id: str | None = None,
) -> str:
    """Append a canary report as evidence without changing policy state."""
    if report.get("schema") != CANARY_SCHEMA:
        raise CanaryError("canary_bad_report_schema")
    if int(report.get("new_project_count") or 0) < 1:
        raise CanaryError("canary_requires_new_project")
    fingerprint = str(report.get("dataset_fingerprint") or "").strip()
    if not fingerprint:
        raise CanaryError("canary_missing_dataset_fingerprint")
    try:
        return LearningStore(database).record_learning_evaluation(
            target_kind=target_kind, target_id=target_id,
            dataset_fingerprint=fingerprint, split_kind="canary",
            status=str(report.get("status") or "abstained"), metrics=dict(report),
            evidence=evidence, candidate_policy_id=str(report.get("candidate_policy_id") or ""),
            evaluation_id=evaluation_id,
        )
    except ProjectIRError as exc:
        raise CanaryError(str(exc)) from exc
