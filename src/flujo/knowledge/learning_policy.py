"""Small, auditable policy learner for the MAK knowledge ledger.

This is deliberately not presented as deep learning.  It is the first honest
learning layer: verified episodes become labelled examples, projects are kept
as groups when splitting train/holdout, and a categorical Naive Bayes policy
can only become a candidate after an independent holdout gate passes.

Unknown, abstained, failed and ``needs_evidence`` episodes are retained as
observations but are never silently converted into negative labels.  The
module is read-only unless ``record_policy`` is called explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .project_ir import LearningStore, stable_json
from .project_router import TOOL_CATALOG


POLICY_SCHEMA = "mak-learning-policy-v1"
ALGORITHM = "categorical-naive-bayes"
VERIFIED_EPISODE_STATUSES = {"succeeded", "verified"}
VERIFIED_OUTCOME_STATUSES = {"succeeded", "success", "verified", "accepted"}
VERIFIED_VALIDATION_STATUSES = {"ok", "passed", "verified"}
MIN_EXAMPLES = 4
MIN_HOLDOUT = 2
MIN_HOLDOUT_GROUPS = 2
MIN_ACCURACY = 0.60

_ROUTE_TOOL_IDS_BY_PATH: dict[str, set[str]] = defaultdict(set)
for _contract in TOOL_CATALOG:
    if _contract.mode in {"read_only", "plan_only"}:
        _ROUTE_TOOL_IDS_BY_PATH[_contract.path].add(_contract.tool_id)
_ROUTE_TOOL_BY_PATH = {
    path: next(iter(tool_ids))
    for path, tool_ids in _ROUTE_TOOL_IDS_BY_PATH.items()
    if len(tool_ids) == 1
}


@dataclass(frozen=True)
class Example:
    episode_id: str
    project_id: str
    label: str
    features: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Dataset:
    examples: tuple[Example, ...]
    excluded: Mapping[str, int]
    fingerprint: str


def _json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _tokens(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.casefold().strip()] if value.strip() else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [str(item).casefold().strip() for item in value if str(item).strip()]
    return []


def _declared_route_label(action: Mapping[str, Any], validation: Mapping[str, Any]) -> str:
    """Extract only an explicit route identity backed by a known contract."""
    decision = action.get("decision")
    selected = decision.get("selected") if isinstance(decision, Mapping) else None
    if isinstance(selected, Mapping):
        label = str(selected.get("tool_id") or "").strip()
        if label in {contract.tool_id for contract in TOOL_CATALOG}:
            return label
    route_label = str(action.get("route_label") or "").strip()
    if route_label in {contract.tool_id for contract in TOOL_CATALOG}:
        return route_label
    checks = validation.get("checks")
    if isinstance(checks, Sequence) and not isinstance(checks, (str, bytes)) and "project_ir_route" in checks:
        return _ROUTE_TOOL_BY_PATH.get(str(action.get("tool") or "").strip(), "")
    return ""


def _features(project: Mapping[str, Any], episode: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    features: list[tuple[str, str]] = []
    state = str(project.get("state") or "unknown").casefold()
    features.append(("state", state))
    source = project.get("source") if isinstance(project.get("source"), Mapping) else {}
    features.append(("source_kind", str(source.get("kind") or "unknown").casefold()))
    for domain in _tokens(project.get("domains")):
        features.append(("domain", domain))
    formats = []
    for artifact in project.get("artifacts", []) if isinstance(project.get("artifacts"), list) else []:
        if isinstance(artifact, Mapping):
            formats.extend(_tokens(artifact.get("format_family")))
    for format_family in sorted(set(formats or ["unknown"])):
        features.append(("format", format_family))
    phase = episode["phase"] if hasattr(episode, "keys") and "phase" in episode.keys() else "unknown"
    features.append(("phase", str(phase or "unknown").casefold()))
    artifact_count = len(project.get("artifacts", [])) if isinstance(project.get("artifacts"), list) else 0
    features.append(("artifact_count", "0" if artifact_count == 0 else "1-8" if artifact_count <= 8 else "9+"))
    return tuple(sorted(features))


def compile_dataset(database: str | Path) -> Dataset:
    """Compile only explicitly successful and validated route episodes."""
    path = Path(database).expanduser()
    if not path.is_file():
        return Dataset((), {"database_missing": 1}, "")
    excluded: Counter[str] = Counter()
    examples: list[Example] = []
    try:
        with sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                """SELECT e.episode_id,e.project_id,e.phase,e.status,e.action_json,
                          e.outcome_json,e.validation_json,r.ir_json
                     FROM project_episodes e
                     JOIN project_records r ON r.project_id=e.project_id
                    ORDER BY e.episode_id"""
            ).fetchall()
    except sqlite3.Error:
        return Dataset((), {"database_unreadable": 1}, "")

    for row in rows:
        if str(row["status"]).casefold() not in VERIFIED_EPISODE_STATUSES:
            excluded["episode_not_verified"] += 1
            continue
        action = _json_object(row["action_json"])
        outcome = _json_object(row["outcome_json"])
        validation = _json_object(row["validation_json"])
        label = _declared_route_label(action, validation)
        if not label:
            excluded["missing_route_label"] += 1
            continue
        if str(outcome.get("status") or "").casefold() not in VERIFIED_OUTCOME_STATUSES:
            excluded["outcome_not_verified"] += 1
            continue
        if str(validation.get("status") or "").casefold() not in VERIFIED_VALIDATION_STATUSES:
            excluded["validation_not_passed"] += 1
            continue
        project = _json_object(row["ir_json"])
        examples.append(Example(
            episode_id=str(row["episode_id"]),
            project_id=str(row["project_id"]),
            label=label,
            features=_features(project, row),
        ))

    fingerprint = hashlib.sha256(stable_json([
        {"episode_id": item.episode_id, "project_id": item.project_id,
         "label": item.label, "features": item.features}
        for item in examples
    ]).encode("utf-8")).hexdigest() if examples else ""
    return Dataset(tuple(examples), dict(sorted(excluded.items())), fingerprint)


def _group_split(examples: Sequence[Example]) -> tuple[list[Example], list[Example]]:
    """Split by project id, never by episode, with a non-empty group target.

    A hash bucket can legally produce an empty holdout for a small dataset.
    That makes the gate depend on luck rather than evidence.  We order project
    groups by their stable hash and take enough whole groups for at least two
    independent holdout projects, while always leaving one group for training.
    """
    grouped: dict[str, list[Example]] = defaultdict(list)
    for example in examples:
        grouped[example.project_id].append(example)
    if len(grouped) <= MIN_HOLDOUT_GROUPS:
        return list(examples), []
    ordered = sorted(
        grouped,
        key=lambda project_id: (hashlib.sha256(project_id.encode("utf-8")).hexdigest(), project_id),
    )
    group_labels = {
        project_id: {item.label for item in grouped[project_id]}
        for project_id in grouped
    }
    label_group_counts = Counter(
        label for labels in group_labels.values() for label in labels
    )
    target = max(MIN_HOLDOUT, math.ceil(len(examples) / 5))
    holdout_projects: list[str] = []
    holdout_count = 0
    for project_id in ordered:
        if len(holdout_projects) >= len(ordered) - 1:
            break
        labels = group_labels[project_id]
        # A holdout group is useful only when every one of its labels still
        # has another project represented in training.
        selected_label_counts = Counter(
            label
            for selected in holdout_projects
            for label in group_labels[selected]
        )
        if any(
            label_group_counts[label] < 2
            or selected_label_counts[label] + 1 >= label_group_counts[label]
            for label in labels
        ):
            continue
        holdout_projects.append(project_id)
        holdout_count += len(grouped[project_id])
        if len(holdout_projects) >= MIN_HOLDOUT_GROUPS and holdout_count >= target:
            break
    if len(holdout_projects) < MIN_HOLDOUT_GROUPS:
        return list(examples), []
    holdout_ids = set(holdout_projects)
    return (
        [example for example in examples if example.project_id not in holdout_ids],
        [example for example in examples if example.project_id in holdout_ids],
    )


def _fit(train: Sequence[Example]) -> dict[str, Any]:
    classes = sorted({item.label for item in train})
    class_counts = Counter(item.label for item in train)
    values: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    for item in train:
        for feature, value in item.features:
            values[feature].add(value)
            counts[item.label][(feature, value)] += 1
    return {
        "schema": POLICY_SCHEMA,
        "algorithm": ALGORITHM,
        "classes": classes,
        "class_counts": dict(sorted(class_counts.items())),
        "feature_values": {key: sorted(values[key]) for key in sorted(values)},
        "feature_counts": {
            label: {f"{feature}={value}": count for (feature, value), count in sorted(counts[label].items())}
            for label in classes
        },
        "train_count": len(train),
    }


def _predict(model: Mapping[str, Any], features: Sequence[tuple[str, str]]) -> tuple[str, float]:
    classes = [str(item) for item in model.get("classes", [])]
    class_counts = {str(key): int(value) for key, value in dict(model.get("class_counts", {})).items()}
    total = max(1, sum(class_counts.values()))
    feature_values = {str(key): list(values) for key, values in dict(model.get("feature_values", {})).items()}
    feature_counts = {
        str(label): {str(key): int(value) for key, value in dict(values).items()}
        for label, values in dict(model.get("feature_counts", {})).items()
    }
    scores: dict[str, float] = {}
    for label in classes:
        score = math.log((class_counts.get(label, 0) + 1) / (total + len(classes)))
        denominator_base = class_counts.get(label, 0)
        for feature, value in features:
            choices = feature_values.get(feature, [])
            count = feature_counts.get(label, {}).get(f"{feature}={value}", 0)
            score += math.log((count + 1) / (denominator_base + len(choices) + 1))
        scores[label] = score
    if not scores:
        return "", 0.0
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winner, best = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else best - 2.0
    confidence = 1.0 / (1.0 + math.exp(max(-40.0, min(40.0, second - best))))
    return winner, round(confidence, 6)


def fit_learning_policy(database: str | Path) -> dict[str, Any]:
    dataset = compile_dataset(database)
    base = {
        "schema": POLICY_SCHEMA,
        "algorithm": ALGORITHM,
        "database": Path(database).expanduser().name,
        "dataset_fingerprint": dataset.fingerprint,
        "eligible_examples": len(dataset.examples),
        "excluded": dict(dataset.excluded),
        "recordable": False,
    }
    if len(dataset.examples) < MIN_EXAMPLES:
        return {**base, "status": "abstain", "reason": "insufficient_verified_examples"}
    train, holdout = _group_split(dataset.examples)
    holdout_projects = sorted({item.project_id for item in holdout})
    if len(holdout) < MIN_HOLDOUT or len(holdout_projects) < MIN_HOLDOUT_GROUPS:
        return {
            **base, "status": "abstain", "reason": "no_independent_holdout",
            "train_count": len(train), "holdout_count": len(holdout),
            "holdout_project_count": len(holdout_projects),
        }
    model = _fit(train)
    if len(model["classes"]) < 2:
        return {
            **base, "status": "abstain", "reason": "insufficient_label_classes",
            "train_count": len(train), "holdout_count": len(holdout),
            "holdout_project_count": len(holdout_projects),
        }
    train_labels = set(model["classes"])
    holdout_labels = {item.label for item in holdout}
    unseen_labels = sorted(holdout_labels - train_labels)
    if unseen_labels:
        return {
            **base, "status": "abstain", "reason": "holdout_label_unseen",
            "train_count": len(train), "holdout_count": len(holdout),
            "holdout_projects": holdout_projects, "unseen_holdout_labels": unseen_labels,
        }
    predictions = [_predict(model, item.features)[0] for item in holdout]
    correct = sum(prediction == item.label for prediction, item in zip(predictions, holdout))
    accuracy = correct / len(holdout)
    baseline = max(Counter(item.label for item in holdout).values()) / len(holdout)
    evaluation = {
        "train_count": len(train), "holdout_count": len(holdout),
        "holdout_accuracy": round(accuracy, 6), "holdout_baseline": round(baseline, 6),
        "correct": correct,
        "holdout_projects": holdout_projects,
    }
    if accuracy < MIN_ACCURACY:
        return {**base, "status": "abstain", "reason": "holdout_below_gate", "evaluation": evaluation}
    version = hashlib.sha256(stable_json({"dataset": dataset.fingerprint, "evaluation": evaluation, "model": model}).encode("utf-8")).hexdigest()[:20]
    return {
        **base, "status": "candidate", "reason": "holdout_gate_passed", "policy_version": version,
        "evaluation": evaluation, "model": model, "recordable": True,
    }


def record_policy(database: str | Path, result: Mapping[str, Any]) -> str:
    """Persist a gated policy as a candidate semantic rule, never promoted."""
    if result.get("status") != "candidate" or not result.get("recordable"):
        raise ValueError("learning_policy_not_recordable")
    version = str(result.get("policy_version") or "")
    if not version:
        raise ValueError("learning_policy_missing_version")
    trigger = {"kind": "learned_route_policy", "schema": POLICY_SCHEMA, "policy_version": version}
    action = {"tool": "learned_route_policy", "algorithm": ALGORITHM, "model": result.get("model"), "evaluation": result.get("evaluation")}
    evidence = [{"kind": "holdout_evaluation", "dataset_fingerprint": result.get("dataset_fingerprint"), "policy_version": version, "evaluation": result.get("evaluation")}]
    store = LearningStore(database)
    rule_id = "rule_learning_" + version
    evaluation_id = "evaluation-policy-" + version
    rule_id = store.upsert_rule(
        trigger=trigger, action=action, evidence=evidence,
        scope={"policy": "route_selection", "features": "project_ir_and_episode"},
        evaluation_id=evaluation_id, rule_id=rule_id,
    )
    evaluation = result.get("evaluation") if isinstance(result.get("evaluation"), Mapping) else {}
    store.record_learning_evaluation(
        target_kind="semantic_rule", target_id=rule_id,
        dataset_fingerprint=str(result.get("dataset_fingerprint") or ""),
        split_kind="holdout", status="passed", metrics=evaluation,
        evidence=evidence, candidate_policy_id=version,
        evaluation_id=evaluation_id,
    )
    return rule_id


def record_verified_result(database: str | Path, packet_path: str | Path) -> str:
    """Record one validator-backed result from an existing Project IR.

    Real workflows call this only after their own validator passes. It refuses
    incomplete packets and never creates a project implicitly.
    """
    packet_file = Path(packet_path).expanduser()
    try:
        packet = json.loads(packet_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("verified_result_packet_invalid") from exc
    if not isinstance(packet, Mapping) or packet.get("schema") != "mak-verified-result-v1":
        raise ValueError("verified_result_bad_schema")
    project_id = str(packet.get("project_id") or "").strip()
    tool_id = str(packet.get("tool_id") or "").strip()
    objective = str(packet.get("objective") or "verified consumer execution").strip()
    phase = str(packet.get("phase") or "verified_execution").strip()
    result = packet.get("result") if isinstance(packet.get("result"), Mapping) else {}
    validation = packet.get("validation") if isinstance(packet.get("validation"), Mapping) else {}
    evidence = packet.get("evidence")
    if not project_id or not tool_id or not isinstance(evidence, list) or not evidence:
        raise ValueError("verified_result_missing_identity_or_evidence")
    if str(result.get("status") or "").casefold() not in VERIFIED_OUTCOME_STATUSES:
        raise ValueError("verified_result_outcome_not_accepted")
    if str(validation.get("status") or "").casefold() not in VERIFIED_VALIDATION_STATUSES:
        raise ValueError("verified_result_validation_not_passed")
    if not str(validation.get("validator") or "").strip() or not isinstance(validation.get("checks"), list) or not validation["checks"]:
        raise ValueError("verified_result_validator_checks_required")

    path = Path(database).expanduser()
    packet_fingerprint = hashlib.sha256(stable_json(dict(packet)).encode("utf-8")).hexdigest()
    try:
        with sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True) as con:
            row = con.execute("SELECT 1 FROM project_records WHERE project_id=?", (project_id,)).fetchone()
    except sqlite3.Error as exc:
        raise ValueError("verified_result_database_unreadable") from exc
    if not row:
        raise ValueError("verified_result_project_missing")

    status = "verified" if str(result.get("status")).casefold() == "verified" else "succeeded"
    action = {
        "component": "verified_result_adapter",
        "decision": {"selected": {"tool_id": tool_id}},
        "packet_fingerprint": packet_fingerprint,
    }
    outcome = {"status": str(result.get("status")), "evidence": list(evidence), "details": dict(result)}
    validation_payload = {**dict(validation), "evidence_count": len(evidence)}
    return LearningStore(path).record_episode(
        project_id=project_id, objective=objective, phase=phase,
        action=action, observation={"packet_schema": packet.get("schema"), "validator": validation.get("validator")},
        outcome=outcome, validation=validation_payload, status=status,
        provider=str(packet.get("provider") or "local-validator"),
        model=str(packet.get("model") or ""), cost=packet.get("cost") if isinstance(packet.get("cost"), Mapping) else {},
        parent_episode_id=str(packet.get("parent_episode_id") or "") or None,
        episode_id=str(packet.get("episode_id") or "episode_verified_" + packet_fingerprint[:24]),
        finished_at=str(packet.get("finished_at") or "") or None,
        source_snapshot_hash=str(packet.get("source_snapshot_hash") or ""),
        code_commit=str(packet.get("code_commit") or ""),
        tool_versions=packet.get("tool_versions") if isinstance(packet.get("tool_versions"), Mapping) else {},
    )


def learning_summary(database: str | Path) -> dict[str, Any]:
    result = fit_learning_policy(database)
    return {key: result[key] for key in (
        "schema", "algorithm", "database", "status", "reason", "eligible_examples", "excluded", "recordable",
        "policy_version", "evaluation",
    ) if key in result}


def _cli(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Compile and evaluate MAK verified learning episodes")
    parser.add_argument("--db", required=True, help="explicit SQLite path")
    parser.add_argument("--record", action="store_true", help="persist a gated policy as a candidate rule")
    parser.add_argument("--record-result", type=Path, help="record one validator-backed result packet")
    args = parser.parse_args(list(argv))
    if args.record_result:
        episode_id = record_verified_result(args.db, args.record_result)
        print(json.dumps({"recorded": True, "episode_id": episode_id, "packet": str(args.record_result)}, ensure_ascii=False, sort_keys=True))
        return 0
    result = fit_learning_policy(args.db)
    if args.record:
        result = dict(result)
        if result.get("status") != "candidate":
            result["recorded"] = False
        else:
            result["rule_id"] = record_policy(args.db, result)
            result["recorded"] = True
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
