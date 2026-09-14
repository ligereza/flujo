"""Versioned replay/holdout contracts for MAK Learn v2.

The suite stores references to real tests or evidence; it does not copy source
trees or turn a test name into a learned label.  Groups are kept entirely in
one split so a project/subsystem cannot leak from replay into holdout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .project_ir import stable_json


REPLAY_SCHEMA = "mak-replay-suite-v1"
SPLITS = ("replay", "holdout")


class ReplaySuiteError(ValueError):
    """A replay suite is incomplete, duplicated or not independent."""


def suite_fingerprint(suite: Mapping[str, Any]) -> str:
    """Hash only the declared suite, excluding a stored fingerprint field."""
    payload = {key: value for key, value in suite.items() if key != "fingerprint"}
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def validate_replay_suite(
    suite: Mapping[str, Any], *, source_root: str | Path | None = None,
) -> dict[str, Any]:
    if suite.get("schema") != REPLAY_SCHEMA:
        raise ReplaySuiteError("replay_bad_schema")
    suite_id = str(suite.get("suite_id") or "").strip()
    cases = suite.get("cases")
    if not suite_id:
        raise ReplaySuiteError("replay_missing_suite_id")
    if not isinstance(cases, list) or not cases:
        raise ReplaySuiteError("replay_missing_cases")
    seen: set[str] = set()
    groups: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    base = Path(source_root).expanduser() if source_root is not None else None
    for case in cases:
        if not isinstance(case, Mapping):
            raise ReplaySuiteError("replay_case_not_mapping")
        case_id = str(case.get("case_id") or "").strip()
        group_id = str(case.get("group_id") or "").strip()
        split = str(case.get("split") or "").strip().casefold()
        refs = case.get("source_refs")
        validator = case.get("validator")
        expected = case.get("expected")
        if not case_id or case_id in seen:
            raise ReplaySuiteError("replay_duplicate_or_missing_case_id")
        if not group_id:
            raise ReplaySuiteError(f"replay_missing_group: {case_id}")
        if split not in SPLITS:
            raise ReplaySuiteError(f"replay_bad_split: {case_id}")
        if not isinstance(refs, list) or not refs:
            raise ReplaySuiteError(f"replay_missing_source_refs: {case_id}")
        if not all(str(ref).strip() for ref in refs):
            raise ReplaySuiteError(f"replay_blank_source_ref: {case_id}")
        if not isinstance(validator, Mapping) or not str(validator.get("kind") or "").strip():
            raise ReplaySuiteError(f"replay_missing_validator: {case_id}")
        if not isinstance(expected, Mapping) or not str(expected.get("status") or "").strip():
            raise ReplaySuiteError(f"replay_missing_expected_status: {case_id}")
        previous_split = groups.get(group_id)
        if previous_split and previous_split != split:
            raise ReplaySuiteError(f"replay_group_leaks_split: {group_id}")
        groups[group_id] = split
        if base is not None:
            missing = [str(base / str(ref)) for ref in refs if not (base / str(ref)).is_file()]
            if missing:
                raise ReplaySuiteError(f"replay_missing_source: {case_id}:{missing[0]}")
        seen.add(case_id)
        normalized.append(dict(case))
    result = {"schema": REPLAY_SCHEMA, "suite_id": suite_id, "cases": normalized}
    actual = suite_fingerprint(result)
    declared = str(suite.get("fingerprint") or "").strip()
    if declared and declared != actual:
        raise ReplaySuiteError("replay_fingerprint_mismatch")
    result["fingerprint"] = actual
    result["splits"] = {
        split: sum(1 for case in normalized if str(case["split"]).casefold() == split)
        for split in SPLITS
    }
    result["groups"] = len(groups)
    return result


def load_replay_suite(path: str | Path, *, source_root: str | Path | None = None) -> dict[str, Any]:
    path = Path(path).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReplaySuiteError("replay_manifest_missing") from exc
    except json.JSONDecodeError as exc:
        raise ReplaySuiteError("replay_manifest_invalid_json") from exc
    return validate_replay_suite(payload, source_root=source_root)


def evaluate_predictions(
    suite: Mapping[str, Any], predictions: Mapping[str, Any], *,
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a declared candidate without promoting it or writing state."""
    checked = validate_replay_suite(suite)
    by_split: dict[str, dict[str, Any]] = {
        split: {"total": 0, "correct": 0, "missing": [], "errors": []}
        for split in SPLITS
    }
    baseline_correct = 0
    for case in checked["cases"]:
        case_id = str(case["case_id"])
        split = str(case["split"]).casefold()
        bucket = by_split[split]
        bucket["total"] += 1
        expected = str(case["expected"]["status"])
        prediction = predictions.get(case_id)
        if isinstance(prediction, Mapping):
            actual = str(prediction.get("status") or "")
        else:
            actual = str(prediction or "")
        if not actual:
            bucket["missing"].append(case_id)
        elif actual == expected:
            bucket["correct"] += 1
        else:
            bucket["errors"].append({"case_id": case_id, "expected": expected, "actual": actual})
        if baseline is not None:
            base_prediction = baseline.get(case_id)
            base_actual = str(base_prediction.get("status") or "") if isinstance(base_prediction, Mapping) else str(base_prediction or "")
            baseline_correct += int(base_actual == expected)
    for bucket in by_split.values():
        bucket["accuracy"] = bucket["correct"] / bucket["total"] if bucket["total"] else 0.0
    total = sum(bucket["total"] for bucket in by_split.values())
    correct = sum(bucket["correct"] for bucket in by_split.values())
    missing = sum(len(bucket["missing"]) for bucket in by_split.values())
    errors = sum(len(bucket["errors"]) for bucket in by_split.values())
    status = "abstained" if missing else ("passed" if not errors and total else "failed")
    return {
        "schema": "mak-learning-evaluation-v1",
        "suite_id": checked["suite_id"],
        "dataset_fingerprint": checked["fingerprint"],
        "status": status,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "missing": missing,
        "errors": errors,
        "by_split": by_split,
        "baseline_correct": baseline_correct if baseline is not None else None,
    }
