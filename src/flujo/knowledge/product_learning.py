"""Controlled, shadow-only evaluation of product episode candidates.

This module is intentionally smaller than a learning runtime.  It turns a
list of immutable ``mak-product-episode-candidate-v1`` records into a
deterministic evaluation package, using only explicitly verified external
outcomes.  Unknown, abstained and open outcomes are excluded rather than
treated as failures.  Archive and artist identity are used only to prevent
group leakage; they are never learning features.

No database, LearningStore, model training or policy activation is performed.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ._contract_helpers import stable_json

from .deep_learning_gate import evaluate_manifest
from .learning_policy import (
    VERIFIED_EPISODE_STATUSES,
    VERIFIED_OUTCOME_STATUSES,
    VERIFIED_VALIDATION_STATUSES,
)


EPISODE_SCHEMA = "mak-product-episode-candidate-v1"
SCHEMA = "mak-product-learning-evaluation-v1"
ALGORITHM_VERSION = "product-learning-counterfactual-1"
MANIFEST_SCHEMA = "mak-deep-learning-task-gate-v1"

ALLOWED_SIGNALS = frozenset({
    "ranking", "attention", "voi_calibration", "query_selection",
})
ALLOWED_ACTIONS = frozenset({
    "observe", "research", "recompute", "compile", "wait", "abstain",
})
FORBIDDEN_SIGNAL_NAMES = frozenset({
    "truth", "authorship", "identity", "claim_status", "artistic_worth",
})
OPEN_OUTCOME_STATUSES = frozenset({
    "unknown", "abstain", "abstained", "open", "pending", "unresolved",
    "needs_evidence", "not_observed", "inconclusive", "candidate", "ineligible",
})
SUCCESS_STATUSES = frozenset({"success", "succeeded", "successful"})
FAILURE_STATUSES = frozenset({"failure", "failed", "unsuccessful", "rejected"})
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
VERIFIED_VALIDATION_ALIASES = frozenset(
    set(VERIFIED_VALIDATION_STATUSES) | {"pass", "success", "succeeded"}
)
VERIFIED_EPISODE_ALIASES = frozenset(
    set(VERIFIED_EPISODE_STATUSES) | {"succeeded", "verified", "passed"}
)
CANDIDATE_EPISODE_STATUSES = frozenset({"candidate", "provisional", "pending"})
MIN_EXAMPLES = 4
MIN_HOLDOUT = 2
MIN_HOLDOUT_GROUPS = 2
MIN_TRAIN_GROUPS = 2

_REQUIRED_EPISODE_FIELDS = (
    "episode_id", "decision", "observation", "outcome", "validation",
    "learning_gate", "control", "provenance",
)
_CONTEXT_KEYS = frozenset({
    "candidate_count", "gap_count", "requirement_count", "unit_count",
    "program_count", "source_validity", "research_status", "product_status",
    "availability", "evidence_count", "uncertainty", "resource_conflict",
})
_PRIVATE_OR_TRUTH_KEYS = frozenset({
    "truth", "authorship", "identity", "claim_status", "artistic_worth",
})
_REAL_EPISODE_OPTIONAL_FIELDS = frozenset({"validation", "learning_gate"})


class ProductLearningError(ValueError):
    """Raised when a product-learning report fails closed validation."""

    def __init__(self, message: str, errors: Sequence[str] | None = None) -> None:
        self.errors = list(errors or [])
        super().__init__(message)


def _copy_json(value: Any) -> Any:
    copied = copy.deepcopy(value)
    try:
        stable_json(copied)
    except (TypeError, ValueError) as error:
        raise ProductLearningError(f"input_not_json:{error}") from error
    return copied


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _status(value: Any) -> str:
    return _text(value).casefold()


def _sorted_refs(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            refs.append(item.strip())
        elif isinstance(item, Mapping):
            ref = _text(item.get("ref") or item.get("evidence_ref") or item.get("source_ref"))
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def _refs_from(maps: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> list[str]:
    refs: list[str] = []
    for mapping in maps:
        for key in keys:
            refs.extend(_sorted_refs(mapping.get(key)))
    return sorted(set(refs))


def _verified_source_hash_refs(outcome: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    raw_refs = outcome.get("source_refs")
    if not isinstance(raw_refs, list) or not raw_refs:
        return [], ["source_refs_missing"]
    refs: list[str] = []
    errors: list[str] = []
    for index, raw in enumerate(raw_refs):
        if not isinstance(raw, Mapping):
            errors.append(f"source_ref_{index}_not_object")
            continue
        ref = _text(raw.get("ref") or raw.get("source_ref"))
        digest = _text(raw.get("sha256") or raw.get("hash"))
        if not ref:
            errors.append(f"source_ref_{index}_missing_ref")
        if not _SHA256_RE.fullmatch(digest):
            errors.append(f"source_ref_{index}_invalid_sha256")
        if ref:
            refs.append(ref)
    if len(refs) != len(set(refs)):
        errors.append("source_ref_duplicate")
    return sorted(set(refs)), sorted(set(errors))


def _first_value(maps: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str:
    for mapping in maps:
        for key in keys:
            value = _text(mapping.get(key))
            if value:
                return value
    return ""


def _external_marker(*maps: Mapping[str, Any]) -> bool:
    external_words = frozenset({
        "external", "environment", "observed_external", "external_validator",
        "independent_validator", "production_observation",
    })
    for mapping in maps:
        for key in ("external", "external_verified", "observed_externally", "independent"):
            if mapping.get(key) is True:
                return True
        for key in ("source", "source_kind", "origin", "origin_kind", "capture_status"):
            value = mapping.get(key)
            if isinstance(value, Mapping):
                value = value.get("kind") or value.get("source_kind") or value.get("status")
            if _status(value) in external_words:
                return True
        if mapping.get("eligible") is True and "external" in _status(mapping.get("eligibility")):
            return True
    return False


def _outcome_label(outcome: Mapping[str, Any]) -> str:
    candidates: list[Any] = [outcome.get("status"), outcome.get("result")]
    result = outcome.get("result")
    if isinstance(result, Mapping):
        candidates.insert(0, result.get("status"))
    for value in candidates:
        current = _status(value)
        if current in SUCCESS_STATUSES:
            return "success"
        if current in FAILURE_STATUSES:
            return "failure"
    return ""


def _valid_scalar(value: Any) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip().casefold()
    return None


def _forbidden_signal_in_decision(decision: Mapping[str, Any]) -> str | None:
    for key in ("signal", "learning_signal", "feature", "label", "target"):
        value = decision.get(key)
        if _status(value) in FORBIDDEN_SIGNAL_NAMES:
            return _status(value)
    for container_key in ("features", "context", "learning_features"):
        container = decision.get(container_key)
        if not isinstance(container, Mapping):
            continue
        for key, value in container.items():
            key_text = _status(key)
            if key_text in FORBIDDEN_SIGNAL_NAMES or _status(value) in FORBIDDEN_SIGNAL_NAMES:
                return key_text or _status(value)
    for key in decision:
        if _status(key) in _PRIVATE_OR_TRUTH_KEYS:
            return _status(key)
    return None


def _decision_signal(decision: Mapping[str, Any]) -> str:
    for key in ("signal", "learning_signal", "dimension"):
        value = _status(decision.get(key))
        if value:
            return value
    return ""


def _fallback_signal(row: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    explicit = _decision_signal(decision)
    if explicit:
        return explicit
    for source in (
        row.get("learning_scope"),
        _mapping(row.get("validation")).get("learning_scope"),
    ):
        if isinstance(source, list):
            allowed = sorted({_status(item) for item in source} & ALLOWED_SIGNALS)
            if allowed:
                return allowed[0]
    return ""


def _decision_action(decision: Mapping[str, Any]) -> str:
    for key in ("action", "candidate_action", "selected_action"):
        value = decision.get(key)
        if isinstance(value, Mapping):
            value = value.get("action") or value.get("action_id") or value.get("tool_id")
        text = _status(value)
        if text:
            return text
    selected = decision.get("selected")
    if isinstance(selected, Mapping):
        return _status(selected.get("action") or selected.get("action_id") or selected.get("tool_id"))
    kind = _status(decision.get("kind"))
    if kind == "common_product_plan_selection" or "compile" in kind:
        return "compile"
    return ""


def _decision_baseline_action(decision: Mapping[str, Any]) -> str:
    for key in ("baseline_action", "deterministic_baseline", "baseline"):
        value = decision.get(key)
        if isinstance(value, Mapping):
            value = value.get("action") or value.get("action_id")
        text = _status(value)
        if text:
            return text
    return "observe"


def _decision_alternatives(decision: Mapping[str, Any]) -> list[str]:
    values = decision.get("alternatives", decision.get("alternative_actions", []))
    if isinstance(values, Mapping):
        values = list(values)
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            value = value.get("action") or value.get("action_id")
        text = _status(value)
        if text and text not in FORBIDDEN_SIGNAL_NAMES:
            result.append(text)
    return sorted(set(result))


def _context_features(decision: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for container_key in ("features", "context"):
        container = decision.get(container_key)
        if not isinstance(container, Mapping):
            continue
        for key in sorted(container, key=str):
            key_text = _status(key)
            if key_text not in _CONTEXT_KEYS:
                continue
            scalar = _valid_scalar(container[key])
            if scalar is not None:
                result.append(("context:" + key_text, scalar))
    return tuple(sorted(set(result)))


def _group_binding(row: Mapping[str, Any]) -> tuple[str, str, str, str, list[str]]:
    provenance = _mapping(row.get("provenance"))
    observation = _mapping(row.get("observation"))
    outcome = _mapping(row.get("outcome"))
    validation = _mapping(row.get("validation"))
    practice_identity = _mapping(observation.get("practice_identity"))
    identity_groups = [
        _mapping(row.get("identity_group")),
        _mapping(provenance.get("identity_group")),
        _mapping(observation.get("identity_group")),
    ]
    identity_groups = [group for group in identity_groups if group]
    explicit_group_ids = [_text(group.get("group_id")) for group in identity_groups]
    explicit_group_ids = [group_id for group_id in explicit_group_ids if group_id]
    errors: list[str] = []
    if identity_groups:
        if not explicit_group_ids:
            errors.append("identity_group_id_missing")
        if len(set(explicit_group_ids)) > 1:
            errors.append("identity_group_binding_mismatch")
        if any(
            group.get("stable") is False
            or group.get("deterministic") is False
            or group.get("snapshot_independent") is False
            or _status(group.get("stability")) in {"unstable", "snapshot_scoped"}
            or (
                group.get("stable") is not True
                and group.get("deterministic") is not True
                and group.get("snapshot_independent") is not True
                and _status(group.get("stability")) != "stable"
                and not any(
                    _text(group.get(key))
                    for key in ("state_hash", "archive_id", "tenant")
                )
            )
            for group in identity_groups
        ):
            errors.append("identity_group_not_stable")
        group_id = explicit_group_ids[0] if explicit_group_ids else ""
        group_key = "identity_group.group_id"
    else:
        group_id = ""
        group_key = "archive_id+artist_identity"
    archive_values = [
        _first_value((provenance,), ("archive_id", "archive")),
        _first_value((observation,), ("archive_id", "archive")),
        _first_value((practice_identity,), ("archive_id", "archive")),
        _first_value((outcome,), ("archive_id", "archive")),
    ]
    artist_values = [
        _first_value((provenance,), ("artist_identity", "artist_id", "artist")),
        _first_value((observation,), ("artist_identity", "artist_id", "artist")),
        _first_value((practice_identity,), ("artist_identity", "artist_id", "artist")),
        _first_value((outcome,), ("artist_identity", "artist_id", "artist")),
    ]
    archive_id = next((value for value in archive_values if value), "")
    artist_identity = next((value for value in artist_values if value), "")
    if not identity_groups and not archive_id:
        errors.append("archive_id_missing")
    if not identity_groups and not artist_identity:
        errors.append("artist_identity_missing")
    if len({value for value in archive_values if value}) > 1:
        errors.append("archive_binding_mismatch")
    if len({value for value in artist_values if value}) > 1:
        errors.append("artist_binding_mismatch")
    maps = (provenance, observation, practice_identity, outcome, validation)
    evidence_refs = _refs_from(
        maps,
        ("evidence_refs", "source_refs", "external_refs", "validation_refs", "result_refs"),
    )
    if not evidence_refs:
        errors.append("external_evidence_ref_missing")
    if not _external_marker(outcome, validation, provenance, observation):
        errors.append("outcome_not_external")
    if not group_id:
        group_id = "group:" + hashlib.sha256(
            stable_json({"archive_id": archive_id, "artist_identity": artist_identity}).encode("utf-8")
        ).hexdigest()[:32]
    return archive_id, artist_identity, group_id, group_key, sorted(set(errors))


def _normalise_episode(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    episode_id = _text(row.get("episode_id"))
    decision = _mapping(row.get("decision"))
    observation = _mapping(row.get("observation"))
    outcome = _mapping(row.get("outcome"))
    control = _mapping(row.get("control"))
    provenance = _mapping(row.get("provenance"))
    projection = _mapping(row.get("record_episode_projection"))
    real_contract = bool(projection)
    validation = _mapping(projection.get("validation")) if real_contract else _mapping(row.get("validation"))
    learning_gate = _mapping(row.get("learning_gate"))
    forbidden = _forbidden_signal_in_decision(decision)
    if forbidden:
        errors.append("prohibited_signal:" + forbidden)

    label = ""
    signals: list[str] = []
    source_refs: list[str] = []
    if real_contract:
        # The real 5A adapter keeps validation below the recordable projection.
        # An open/unresolved candidate is a valid observation with no label.
        if outcome.get("eligible") is not True:
            return None, sorted(set(errors + ["outcome_open_not_negative"]))
        label_candidate = _mapping(outcome.get("label_candidate"))
        label = _status(label_candidate.get("label"))
        if _status(label_candidate.get("status")) != "candidate" or label not in {"success", "failure"}:
            errors.append("label_candidate_invalid")
        raw_scopes = label_candidate.get("signal_scopes")
        if not isinstance(raw_scopes, list):
            by_product = provenance.get("signal_scopes_by_product")
            selected_products = decision.get("selected_product_ids")
            if isinstance(by_product, Mapping) and isinstance(selected_products, list):
                raw_scopes = [
                    scope
                    for product_id in selected_products
                    for scope in (
                        by_product.get(product_id, [])
                        if isinstance(by_product.get(product_id, []), list) else []
                    )
                ]
            else:
                raw_scopes = None
        if not isinstance(raw_scopes, list):
            fallback_scopes = label_candidate.get("scope")
            if isinstance(fallback_scopes, list) and set(_status(item) for item in fallback_scopes) != set(ALLOWED_SIGNALS):
                raw_scopes = fallback_scopes
        if not isinstance(raw_scopes, list) or not raw_scopes:
            errors.append("signal_scopes_missing")
        else:
            signals = sorted({_status(item) for item in raw_scopes if _status(item)})
            invalid_scopes = sorted(set(signals) - set(ALLOWED_SIGNALS))
            if invalid_scopes:
                errors.extend(
                    "prohibited_or_unknown_signal_scope:" + item for item in invalid_scopes
                )
                signals = [item for item in signals if item in ALLOWED_SIGNALS]
        validation_status = _status(validation.get("status") or validation.get("result"))
        if validation_status not in VERIFIED_VALIDATION_ALIASES:
            errors.append("projection_validation_not_verified")
        checks = validation.get("checks")
        if not isinstance(checks, list) or not checks:
            errors.append("projection_validation_checks_missing")
        if validation.get("outcome_eligible") is not True:
            errors.append("projection_outcome_not_verified")
        eligibility = _status(outcome.get("eligibility"))
        if "external" not in eligibility and validation.get("external_receipt_verified") is not True:
            checks_text = {_status(item) for item in checks if isinstance(item, str)} if isinstance(checks, list) else set()
            if not any(
                any(token in check for token in ("external", "receipt", "binding", "source_digest"))
                for check in checks_text
            ):
                errors.append("external_receipt_binding_not_verified")
        nested_outcome_validation = _mapping(outcome.get("validation"))
        if nested_outcome_validation:
            nested_status = _status(nested_outcome_validation.get("status"))
            if nested_status not in VERIFIED_VALIDATION_ALIASES:
                errors.append("outcome_validation_not_verified")
        source_refs, source_errors = _verified_source_hash_refs(outcome)
        errors.extend("source_hash:" + error for error in source_errors)
    else:
        if not learning_gate:
            learning_scope = row.get("learning_scope")
            if not isinstance(learning_scope, list):
                learning_scope = _mapping(row.get("validation")).get("learning_scope")
            if isinstance(learning_scope, list):
                learning_gate = {
                    "status": "eligible" if outcome.get("eligible") is True else "shadow_only",
                    "signals": copy.deepcopy(learning_scope),
                    "training_permitted": False,
                }
        signal = _fallback_signal(row, decision)
        if signal not in ALLOWED_SIGNALS:
            errors.append("signal_not_allowed" if signal else "signal_missing")
        signals = [signal] if signal in ALLOWED_SIGNALS else []
        label = _outcome_label(outcome)
        outcome_status = _status(outcome.get("status"))
        if not label:
            if outcome_status in OPEN_OUTCOME_STATUSES or not outcome_status:
                errors.append("outcome_open_not_negative")
            else:
                errors.append("outcome_success_failure_required")
        validation_status = _status(validation.get("status") or validation.get("result"))
        if validation_status not in VERIFIED_VALIDATION_ALIASES:
            errors.append("validation_not_verified")
        source_refs = _refs_from(
            (outcome, validation, provenance, observation),
            ("evidence_refs", "source_refs", "external_refs", "validation_refs", "result_refs"),
        )
    episode_status = _status(row.get("status"))
    provenance_status = _status(provenance.get("episode_status"))
    if (
        episode_status
        and episode_status not in VERIFIED_EPISODE_ALIASES
        and episode_status not in CANDIDATE_EPISODE_STATUSES
    ) or (
        provenance_status
        and provenance_status not in VERIFIED_EPISODE_ALIASES
        and provenance_status not in CANDIDATE_EPISODE_STATUSES
    ):
        errors.append("episode_not_verified")
    if control.get("training_permitted") is True:
        errors.append("training_authorization_forbidden")
    if _status(control.get("promotion")) not in {"", "none"}:
        errors.append("promotion_forbidden")
    if not real_contract:
        gate_status = _status(
            learning_gate.get("status")
            or learning_gate.get("eligibility")
            or learning_gate.get("result")
        )
        gate_eligible = learning_gate.get("eligible") is True or learning_gate.get("passed") is True
        if not gate_eligible and gate_status not in {"eligible", "pass", "passed", "verified", "shadow_only"}:
            errors.append("learning_gate_not_passed")
        gate_signals = learning_gate.get("signals", learning_gate.get("allowed_signals"))
        if isinstance(gate_signals, list):
            invalid = sorted({
                _status(item) for item in gate_signals
                if _status(item) not in ALLOWED_SIGNALS
            })
            if invalid:
                errors.extend("prohibited_or_unknown_gate_signal:" + item for item in invalid)
    if real_contract and not (
        _mapping(row.get("identity_group"))
        or _mapping(row.get("observation")).get("identity_group")
        or _mapping(row.get("provenance")).get("identity_group")
    ):
        errors.append("identity_group_missing")
    archive_id, artist_identity, group_id, group_key, binding_errors = _group_binding(row)
    errors.extend(binding_errors)
    if real_contract and group_key != "identity_group.group_id":
        errors.append("identity_group_missing")
    action = _decision_action(decision)
    if not action:
        errors.append("decision_action_missing")
    context = _context_features(decision)
    features_by_signal = {
        signal: tuple(sorted({("signal", signal), ("action", action), *context}))
        for signal in signals
    }
    if errors:
        return None, sorted(set(errors))
    episode = {
        "episode_id": episode_id,
        "label": label,
        "signals": signals,
        "signal": signals[0],
        "action": action,
        "baseline_action": _decision_baseline_action(decision),
        "alternatives": _decision_alternatives(decision),
        "features_by_signal": features_by_signal,
        "features": features_by_signal[signals[0]],
        "group_id": group_id,
        "group_key": group_key,
        "archive_id": archive_id,
        "artist_identity": artist_identity,
        "evidence_refs": source_refs,
        "counterfactuals": outcome.get("counterfactuals", outcome.get("alternatives", {})),
        "real_contract": real_contract,
    }
    return episode, []


def _normalise_input(episodes: Any) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    if isinstance(episodes, Mapping) and isinstance(episodes.get("episodes"), list):
        episodes = episodes["episodes"]
    if not isinstance(episodes, list):
        return [], {}, ["episodes_not_list"]
    excluded: Counter[str] = Counter()
    structural_errors: list[str] = []
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    for index, raw in enumerate(episodes):
        if not isinstance(raw, Mapping):
            structural_errors.append(f"episode_{index}_not_object")
            continue
        row = _copy_json(dict(raw))
        if row.get("schema") != EPISODE_SCHEMA:
            structural_errors.append(f"episode_{index}_schema_invalid")
            continue
        missing = [key for key in _REQUIRED_EPISODE_FIELDS if key not in row]
        if "validation" in missing and isinstance(row.get("record_episode_projection"), Mapping):
            missing.remove("validation")
        if "learning_gate" in missing and (
            isinstance(row.get("learning_scope"), list)
            or isinstance(_mapping(row.get("validation")).get("learning_scope"), list)
        ):
            missing.remove("learning_gate")
        if missing:
            structural_errors.extend(f"episode_{index}_missing_{key}" for key in missing)
            continue
        episode_id = _text(row.get("episode_id"))
        if not episode_id:
            structural_errors.append(f"episode_{index}_id_missing")
            continue
        if episode_id in seen:
            structural_errors.append("duplicate_episode_id:" + episode_id)
            continue
        seen.add(episode_id)
        normalised, errors = _normalise_episode(row)
        if errors:
            for error in errors:
                excluded[error] += 1
            continue
        assert normalised is not None
        for signal in normalised["signals"]:
            expanded = copy.deepcopy(normalised)
            expanded["example_id"] = (
                normalised["episode_id"]
                if len(normalised["signals"]) == 1
                else normalised["episode_id"] + "::signal:" + signal
            )
            expanded["signal"] = signal
            expanded["features"] = normalised["features_by_signal"][signal]
            accepted.append(expanded)
    accepted.sort(key=lambda row: row["example_id"])
    return accepted, dict(sorted(excluded.items())), sorted(set(structural_errors))


def _dataset_fingerprint(examples: Sequence[Mapping[str, Any]]) -> str:
    payload = [
        {
            "example_id": row["example_id"],
            "episode_id": row["episode_id"],
            "label": row["label"],
            "signal": row["signal"],
            "action": row["action"],
            "group_id": row["group_id"],
            "features": list(row["features"]),
            "evidence_refs": list(row["evidence_refs"]),
        }
        for row in examples
    ]
    return "sha256:" + hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def _split_groups(examples: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in examples:
        grouped[str(row["group_id"])].append(dict(row))
    group_ids = sorted(
        grouped,
        key=lambda group_id: (hashlib.sha256(group_id.encode("utf-8")).hexdigest(), group_id),
    )
    metadata: dict[str, Any] = {
        "group_key": (
            next(iter({str(row.get("group_key")) for row in examples if row.get("group_key")}))
            if len({str(row.get("group_key")) for row in examples if row.get("group_key")}) == 1
            else "mixed_group_keys"
        ),
        "independent": False,
        "leakage_detected": False,
        "train_group_ids": [],
        "holdout_group_ids": [],
    }
    if len(group_ids) < MIN_HOLDOUT_GROUPS + MIN_TRAIN_GROUPS:
        return list(examples), [], metadata
    labels_by_group = {
        group_id: {str(row["label"]) for row in grouped[group_id]}
        for group_id in group_ids
    }
    candidate_sets: list[tuple[str, ...]] = []
    if len(group_ids) <= 64:
        for size in range(MIN_HOLDOUT_GROUPS, min(len(group_ids) - MIN_TRAIN_GROUPS, 4) + 1):
            candidate_sets.extend(itertools.combinations(group_ids, size))
            if candidate_sets:
                break
    if not candidate_sets:
        candidate_sets = [tuple(group_ids[:MIN_HOLDOUT_GROUPS])]
    chosen: tuple[str, ...] | None = None
    all_labels = {str(row["label"]) for row in examples}
    for candidate in candidate_sets:
        holdout_labels = set().union(*(labels_by_group[group_id] for group_id in candidate))
        train_labels = set().union(*(
            labels_by_group[group_id] for group_id in group_ids if group_id not in candidate
        ))
        if holdout_labels <= train_labels and holdout_labels and all_labels <= train_labels | holdout_labels:
            chosen = candidate
            break
    if chosen is None:
        return list(examples), [], metadata
    holdout_ids = set(chosen)
    train = [dict(row) for row in examples if row["group_id"] not in holdout_ids]
    holdout = [dict(row) for row in examples if row["group_id"] in holdout_ids]
    metadata.update({
        "independent": True,
        "train_group_ids": sorted({str(row["group_id"]) for row in train}),
        "holdout_group_ids": sorted(holdout_ids),
        "leakage_detected": bool(
            {str(row["group_id"]) for row in train}
            & {str(row["group_id"]) for row in holdout}
        ),
    })
    return train, holdout, metadata


def _majority(labels: Sequence[str]) -> str:
    counts = Counter(labels)
    if not counts:
        return ""
    return sorted(counts, key=lambda label: (-counts[label], label))[0]


def _fit_outcome_model(train: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    global_label = _majority([str(row["label"]) for row in train])
    by_features: dict[str, list[str]] = defaultdict(list)
    for row in train:
        key = stable_json(list(row["features"]))
        by_features[key].append(str(row["label"]))
    return {
        "algorithm": "deterministic-feature-majority",
        "global_prediction": global_label,
        "feature_predictions": {
            key: _majority(values) for key, values in sorted(by_features.items())
        },
        "train_count": len(train),
    }


def _predict_model(model: Mapping[str, Any], features: Sequence[Sequence[str]]) -> str:
    key = stable_json(features)
    predictions = model.get("feature_predictions", {})
    return _text(predictions.get(key)) or _text(model.get("global_prediction"))


def _accuracy(model: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    predictions = [
        _predict_model(model, list(row["features"])) for row in rows
    ]
    labels = [str(row["label"]) for row in rows]
    correct = sum(prediction == label for prediction, label in zip(predictions, labels))
    successes = sum(label == "success" for label in labels)
    total = len(labels)
    accuracy = correct / total if total else None
    success_rate = successes / total if total else None
    return {
        "count": total,
        "correct": correct,
        "accuracy": round(accuracy, 6) if accuracy is not None else None,
        "successes": successes,
        "failures": total - successes,
        "success_rate": round(success_rate, 6) if success_rate is not None else None,
        "predictions": [
            {"episode_id": row["episode_id"], "predicted": prediction, "observed": row["label"]}
            for row, prediction in zip(rows, predictions)
        ],
    }


def _uncertainty(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    count = int(evaluation.get("count") or 0)
    accuracy = evaluation.get("accuracy")
    if count <= 0 or not isinstance(accuracy, (int, float)):
        return {"status": "insufficient", "sample_count": count, "interval_95": None}
    margin = 1.96 * math.sqrt(max(0.0, accuracy * (1.0 - accuracy) / count))
    return {
        "status": "wide" if count < 8 else "estimated",
        "sample_count": count,
        "standard_error": round(math.sqrt(max(0.0, accuracy * (1.0 - accuracy) / count)), 6),
        "interval_95": [round(max(0.0, accuracy - margin), 6), round(min(1.0, accuracy + margin), 6)],
        "small_sample": count < 8,
    }


def _counterfactuals(
    examples: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    actions: set[str] = set()
    observed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in examples:
        actions.update(str(item) for item in row.get("alternatives", []))
        baseline_action = _text(row.get("baseline_action"))
        if baseline_action:
            actions.add(baseline_action)
        raw = row.get("counterfactuals")
        if isinstance(raw, Mapping):
            for action, value in raw.items():
                action_text = _status(action)
                if not action_text:
                    continue
                actions.add(action_text)
                value_map = _mapping(value)
                label = _outcome_label(value_map)
                if label and _external_marker(value_map) and _refs_from(
                    (value_map,), ("evidence_refs", "source_refs", "external_refs")
                ):
                    observed[action_text].append({
                        "episode_id": row["episode_id"],
                        "label": label,
                        "evidence_refs": _refs_from(
                            (value_map,), ("evidence_refs", "source_refs", "external_refs")
                        ),
                    })
    results: list[dict[str, Any]] = []
    for action in sorted(actions):
        rows = observed.get(action, [])
        if rows:
            successes = sum(row["label"] == "success" for row in rows)
            results.append({
                "action": action,
                "status": "observed_external",
                "count": len(rows),
                "successes": successes,
                "failures": len(rows) - successes,
                "evidence_refs": sorted({ref for row in rows for ref in row["evidence_refs"]}),
                "prediction": None,
                "training_permitted": False,
            })
        else:
            results.append({
                "action": action,
                "status": "unresolved",
                "count": 0,
                "successes": 0,
                "failures": 0,
                "evidence_refs": [],
                "prediction": None,
                "reason": "no_verified_counterfactual_outcome",
                "training_permitted": False,
            })
    if not results:
        results.append({
            "action": "unobserved",
            "status": "unresolved",
            "count": 0,
            "successes": 0,
            "failures": 0,
            "evidence_refs": [],
            "prediction": None,
            "reason": "no_explicit_alternative",
            "training_permitted": False,
        })
    if model is not None:
        for result in results:
            if result["action"] != "unobserved":
                feature_rows = [
                    list(row["features"])
                    for row in examples
                    if result["action"] in row.get("alternatives", [])
                ]
                if feature_rows:
                    result["prediction"] = _predict_model(model, feature_rows[0])
                    result["prediction_status"] = "shadow_prediction_only"
    return results


def _manifest(
    dataset_fingerprint: str,
    train: Sequence[Mapping[str, Any]],
    holdout: Sequence[Mapping[str, Any]],
    split: Mapping[str, Any],
    signals: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "task_id": "product-learning-shadow-" + (dataset_fingerprint.removeprefix("sha256:")[:20] or "empty"),
        "project_id": "product-learning-shadow",
        "objective": "evaluate bounded routing and attention signals without training",
        "input_ref": "mak-product-learning-dataset:" + (dataset_fingerprint or "empty"),
        "label_ref": "verified_external_outcome:success|failure",
        "signals": sorted(set(signals)),
        "split": {
            "train_ref": "product-learning-train:" + (dataset_fingerprint or "empty"),
            "holdout_ref": "product-learning-holdout:" + (dataset_fingerprint or "empty"),
            "independent": split.get("independent") is True,
            "group_key": split.get("group_key", "archive_id+artist_identity"),
            "holdout_count": len(holdout),
            "train_count": len(train),
            "train_group_count": len(split.get("train_group_ids", [])),
            "holdout_group_count": len(split.get("holdout_group_ids", [])),
        },
        "validator": {
            "path": "tools/evaluate_product_learning.py",
            "status": "ready",
        },
        "training_permitted": False,
        "promotion": "none",
        "shadow_only": True,
    }


def _input_group_key(episodes: Any) -> str:
    rows = episodes.get("episodes") if isinstance(episodes, Mapping) else episodes
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            if (
                isinstance(row.get("identity_group"), Mapping)
                or isinstance(_mapping(row.get("observation")).get("identity_group"), Mapping)
                or isinstance(_mapping(row.get("provenance")).get("identity_group"), Mapping)
            ):
                return "identity_group.group_id"
    return "archive_id+artist_identity"


def compile_learning_dataset(episodes: Any) -> dict[str, Any]:
    """Return a portable dataset projection without fitting or writing state."""
    examples, excluded, structural_errors = _normalise_input(episodes)
    fingerprint = _dataset_fingerprint(examples) if examples else ""
    group_key = _input_group_key(episodes)
    if examples:
        observed_group_keys = {row["group_key"] for row in examples}
        if len(observed_group_keys) == 1:
            group_key = next(iter(observed_group_keys))
    rows = [
        {
            "example_id": row["example_id"],
            "episode_id": row["episode_id"],
            "group_id": row["group_id"],
            "signal": row["signal"],
            "action": row["action"],
            "label": row["label"],
            "features": [list(feature) for feature in row["features"]],
            "evidence_refs": list(row["evidence_refs"]),
        }
        for row in examples
    ]
    return {
        "schema": "mak-product-learning-dataset-v1",
        "algorithm_version": ALGORITHM_VERSION,
        "examples": rows,
        "eligible_count": len(rows),
        "excluded": excluded,
        "structural_errors": structural_errors,
        "fingerprint": fingerprint,
        "group_key": group_key,
        "identity_used_as_feature": False,
        "training_permitted": False,
    }


def evaluate_product_learning(
    episodes: Any,
    *,
    manifest_root: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate verified episodes and return a deterministic shadow report."""
    group_key_hint = _input_group_key(episodes)
    examples, excluded, structural_errors = _normalise_input(episodes)
    dataset_fingerprint = _dataset_fingerprint(examples) if examples else ""
    train, holdout, split = _split_groups(examples)
    if split.get("group_key") == "mixed_group_keys" or not examples:
        split["group_key"] = group_key_hint
    model: dict[str, Any] | None = None
    baseline_eval: dict[str, Any] = {
        "strategy": "deterministic_majority_outcome",
        "count": len(holdout),
        "accuracy": None,
        "prediction": None,
        "training_permitted": False,
    }
    candidate_eval: dict[str, Any] = {
        "strategy": "deterministic_allowed_signal_lookup",
        "count": len(holdout),
        "accuracy": None,
        "training_permitted": False,
    }
    gains: dict[str, Any] = {
        "status": "insufficient_evidence",
        "accuracy_delta": None,
        "candidate_accuracy": None,
        "baseline_accuracy": None,
    }
    errors = list(structural_errors)
    for reason in excluded:
        if reason.startswith((
            "prohibited_signal:",
            "prohibited_or_unknown_gate_signal:",
            "prohibited_or_unknown_signal_scope:",
        )):
            errors.append("prohibited_learning_signal_in_input:" + reason.split(":", 1)[1])
    warnings: list[str] = []
    if len(examples) >= MIN_EXAMPLES and split["independent"] and not split["leakage_detected"]:
        model = _fit_outcome_model(train)
        candidate_eval = _accuracy(model, holdout)
        candidate_eval["strategy"] = "deterministic_allowed_signal_lookup"
        baseline_model = {
            "global_prediction": _majority([str(row["label"]) for row in train]),
            "algorithm": "deterministic-majority-baseline",
        }
        baseline_eval = _accuracy(baseline_model, holdout)
        baseline_eval["strategy"] = "deterministic_majority_outcome"
        baseline_eval["prediction"] = baseline_model["global_prediction"]
        delta = float(candidate_eval["accuracy"] or 0.0) - float(baseline_eval["accuracy"] or 0.0)
        gains = {
            "status": "observed",
            "accuracy_delta": round(delta, 6),
            "candidate_accuracy": candidate_eval["accuracy"],
            "baseline_accuracy": baseline_eval["accuracy"],
            "candidate_success_rate": candidate_eval["success_rate"],
        }
    else:
        if examples and not split["independent"]:
            warnings.append("no_independent_holdout")
        if split["leakage_detected"]:
            errors.append("group_leakage_detected")
    uncertainty = {
        "candidate": _uncertainty(candidate_eval),
        "baseline": _uncertainty(baseline_eval),
        "status": "wide" if candidate_eval.get("count", 0) < 8 else "estimated",
    }
    applicable_signals = sorted({str(row["signal"]) for row in examples})
    manifest = _manifest(dataset_fingerprint, train, holdout, split, applicable_signals)
    root = Path(manifest_root).expanduser() if manifest_root is not None else Path(__file__).resolve().parents[2]
    try:
        deep_learning_gate = evaluate_manifest(manifest, root=root)
    except (OSError, TypeError, ValueError) as error:
        deep_learning_gate = {
            "schema": MANIFEST_SCHEMA,
            "decision": "abstain",
            "training_permitted": False,
            "errors": ["deep_learning_gate_unavailable:" + str(error)],
        }
    if deep_learning_gate.get("decision") != "eligible":
        warnings.append("deep_learning_manifest_not_eligible")
    counterfactuals = _counterfactuals(examples, model)
    eligible_for_candidate = (
        not errors
        and len(examples) >= MIN_EXAMPLES
        and len(train) >= MIN_EXAMPLES - MIN_HOLDOUT
        and len(holdout) >= MIN_HOLDOUT
        and len(split["train_group_ids"]) >= MIN_TRAIN_GROUPS
        and len(split["holdout_group_ids"]) >= MIN_HOLDOUT_GROUPS
        and split["independent"] is True
        and split["leakage_detected"] is False
        and len({str(row["label"]) for row in examples}) >= 2
        and gains.get("status") == "observed"
        and float(gains.get("accuracy_delta") or 0.0) > 0.0
    )
    status = "policy_candidate" if eligible_for_candidate else "abstain"
    if status == "abstain" and not examples:
        warnings.append("no_verified_external_examples")
    if status == "abstain" and examples and gains.get("status") == "observed" and not eligible_for_candidate:
        warnings.append("candidate_did_not_exceed_deterministic_baseline")
    learning_features = {
        "signals": applicable_signals,
        "feature_names": ["signal", "action", "bounded_context"],
        "training_permitted": False,
        "exportable": True,
        "shadow_only": True,
        "truth_authority": False,
        "prohibited_signals": sorted(FORBIDDEN_SIGNAL_NAMES),
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "status": status,
        "valid": not errors,
        "policy_candidate": status == "policy_candidate",
        "shadow_only": True,
        "training_permitted": False,
        "dataset": {
            "schema": "mak-product-learning-dataset-v1",
            "fingerprint": dataset_fingerprint,
            "eligible_count": len(examples),
            "excluded": excluded,
            "group_key": split.get("group_key", "archive_id+artist_identity"),
            "identity_used_as_feature": False,
            "examples": [
                {
                    "example_id": row["example_id"],
                    "episode_id": row["episode_id"],
                    "group_id": row["group_id"],
                    "signal": row["signal"],
                    "action": row["action"],
                    "label": row["label"],
                    "features": [list(feature) for feature in row["features"]],
                    "evidence_refs": list(row["evidence_refs"]),
                }
                for row in examples
            ],
        },
        "split": {
            **split,
            "train_episode_ids": sorted(row["example_id"] for row in train),
            "holdout_episode_ids": sorted(row["example_id"] for row in holdout),
            "independent": split["independent"] is True,
            "minimum_holdout": MIN_HOLDOUT,
            "minimum_holdout_groups": MIN_HOLDOUT_GROUPS,
        },
        "baseline": baseline_eval,
        "candidate": candidate_eval,
        "gains": gains,
        "uncertainty": uncertainty,
        "counterfactual_alternatives": counterfactuals,
        "counterfactuals": counterfactuals,
        "learning_features": learning_features,
        "deep_learning_manifest_candidate": manifest,
        "deep_learning_gate": deep_learning_gate,
        "control": {
            "training_permitted": False,
            "policy_activation": False,
            "promotion": "none",
            "shadow_only": True,
            "database_write": False,
            "dispatch": False,
        },
        "provenance": {
            "source_schema": EPISODE_SCHEMA,
            "group_key": split.get("group_key", "archive_id+artist_identity"),
            "deterministic": True,
            "identity_used_as_feature": False,
            "external_verified_only": True,
        },
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "structural_errors": sorted(set(structural_errors)),
    }
    report["evaluation_hash"] = "evaluation:" + hashlib.sha256(
        stable_json(report).encode("utf-8")
    ).hexdigest()
    report["report_hash"] = report["evaluation_hash"]
    return report


def validate_product_learning(report: Any) -> list[str]:
    """Validate report shape and hard safety controls without repairing it."""
    if not isinstance(report, Mapping):
        return ["report_not_object"]
    errors: list[str] = []
    if report.get("schema") != SCHEMA:
        errors.append("schema_invalid")
    if report.get("status") not in {"policy_candidate", "abstain"}:
        errors.append("status_invalid")
    if report.get("valid") is not True:
        errors.append("report_not_valid")
    if report.get("errors") != []:
        errors.append("report_contains_errors")
    if report.get("status") == "policy_candidate" and report.get("valid") is not True:
        errors.append("candidate_not_valid")
    if report.get("training_permitted") is not False:
        errors.append("training_permitted_not_false")
    if report.get("shadow_only") is not True:
        errors.append("shadow_only_not_true")
    control = report.get("control")
    if not isinstance(control, Mapping):
        errors.append("control_missing")
    else:
        for key in ("training_permitted", "policy_activation", "database_write", "dispatch"):
            if control.get(key) is not False:
                errors.append("control_" + key + "_not_false")
        if control.get("promotion") != "none":
            errors.append("control_promotion_not_none")
    dataset = report.get("dataset")
    if not isinstance(dataset, Mapping):
        errors.append("dataset_missing")
    else:
        if dataset.get("identity_used_as_feature") is not False:
            errors.append("identity_used_as_feature")
        if not isinstance(dataset.get("examples"), list):
            errors.append("dataset_examples_invalid")
        if dataset.get("eligible_count") != len(dataset.get("examples", [])):
            errors.append("dataset_count_mismatch")
        example_ids = [
            row.get("example_id") or row.get("episode_id")
            for row in dataset.get("examples", [])
            if isinstance(row, Mapping)
        ]
        if example_ids != sorted(set(example_ids)):
            errors.append("dataset_episode_order_or_duplicate")
        for row in dataset.get("examples", []) if isinstance(dataset.get("examples"), list) else []:
            if not isinstance(row, Mapping):
                errors.append("dataset_example_not_object")
                continue
            if row.get("label") not in {"success", "failure"}:
                errors.append("dataset_label_invalid")
            feature_names = {
                str(feature[0]) for feature in row.get("features", [])
                if isinstance(feature, list) and feature
            }
            if feature_names & FORBIDDEN_SIGNAL_NAMES:
                errors.append("forbidden_feature_present")
    split = report.get("split")
    if not isinstance(split, Mapping):
        errors.append("split_missing")
    else:
        train_groups = set(split.get("train_group_ids", []))
        holdout_groups = set(split.get("holdout_group_ids", []))
        if train_groups & holdout_groups:
            errors.append("group_leakage")
        if split.get("independent") is not True and report.get("status") == "policy_candidate":
            errors.append("candidate_without_independent_holdout")
    learning_features = report.get("learning_features")
    if not isinstance(learning_features, Mapping) or learning_features.get("training_permitted") is not False:
        errors.append("learning_features_training_not_false")
    manifest = report.get("deep_learning_manifest_candidate")
    if not isinstance(manifest, Mapping) or manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("manifest_invalid")
    expected_hash = report.get("evaluation_hash")
    if not isinstance(expected_hash, str) or not expected_hash.startswith("evaluation:"):
        errors.append("evaluation_hash_missing")
    else:
        if report.get("report_hash") != expected_hash:
            errors.append("report_hash_mismatch")
        without_hash = dict(report)
        without_hash.pop("evaluation_hash", None)
        without_hash.pop("report_hash", None)
        actual = "evaluation:" + hashlib.sha256(stable_json(without_hash).encode("utf-8")).hexdigest()
        # The report hash is defined over the report before either hash field.
        if expected_hash != actual:
            errors.append("evaluation_hash_mismatch")
    return sorted(set(errors))


def assert_product_learning(report: Any) -> bool:
    errors = validate_product_learning(report)
    if errors:
        raise ProductLearningError("product_learning_invalid:" + ",".join(errors), errors)
    return True


evaluate_learning = evaluate_product_learning
compile_product_learning_dataset = compile_learning_dataset
validate_learning = validate_product_learning
assert_learning = assert_product_learning


__all__ = [
    "ALGORITHM_VERSION", "ALLOWED_SIGNALS", "EPISODE_SCHEMA", "SCHEMA",
    "ProductLearningError", "assert_learning", "assert_product_learning",
    "compile_learning_dataset", "compile_product_learning_dataset",
    "evaluate_learning", "evaluate_product_learning", "stable_json",
    "validate_learning", "validate_product_learning",
]
