"""Refuse to let a cheap feature decide an expensive question.

Almost every classification error recorded in ``docs/ordering_chaos.md`` has the
same shape: a feature that was free to read was allowed to settle a question it
could not settle. A filename decided that 1599 records of the operator's own
artworks were machine junk. A Resolume slice called ``Slice 1`` decided that
three unrelated rigs were the same rig, when that string is the tool's default
and carries no information at all. A count of files on disk decided that four
bodies of work were in the database when two were.

The failure was never the feature. It was letting the feature decide without
asking whether anything could have said it was wrong.

So this module makes ``data/ordering_features.json`` binding. Before a feature is
used to classify anything, the caller asks here, and the answer is either a
permission with a confidence ceiling attached or a refusal that names the missing
authority. A feature that is not declared in the registry cannot be used at all,
which is what stops the next undeclared shortcut from arriving quietly.

The registry is not a lookup table of right answers. It records, per feature,
what it COSTS and what can REFUTE it -- because those two properties are knowable
in advance, and accuracy is not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT = "mak-ordering-features-v1"

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data" / "ordering_features.json"

# Ordered weakest to strongest. A ceiling is a promise about the most a piece of
# evidence may claim, never a score to be combined with another one.
CONFIDENCE_ORDER = ("none", "weak", "moderate", "strong", "proof")

PROOF = "proof"
NONE = "none"


class FeaturePolicyError(ValueError):
    """The registry was asked something it cannot answer honestly."""


class UndeclaredFeatureError(FeaturePolicyError):
    """A feature tried to decide something without being declared first."""


@dataclass(frozen=True)
class Permission:
    """The answer to "may this feature decide this?"."""

    feature: str
    question: str
    allowed: bool
    confidence_ceiling: str
    authority: str | None
    authority_consulted: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "question": self.question,
            "allowed": self.allowed,
            "confidence_ceiling": self.confidence_ceiling,
            "authority": self.authority,
            "authority_consulted": self.authority_consulted,
            "reason": self.reason,
        }


@lru_cache(maxsize=4)
def load_registry(path: str | None = None) -> dict[str, Any]:
    """Read and validate the declared feature registry."""
    target = Path(path) if path else REGISTRY_PATH
    if not target.is_file():
        raise FeaturePolicyError(f"feature_registry_missing: {target}")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FeaturePolicyError(f"feature_registry_unreadable: {exc}") from exc
    if payload.get("schema") != CONTRACT:
        raise FeaturePolicyError(f"feature_registry_bad_schema: {payload.get('schema')}")
    for field in ("features", "authorities", "folding_relations", "decision_rule",
                  "learning_contract"):
        if field not in payload:
            raise FeaturePolicyError(f"feature_registry_missing_{field}")
    names = [str(item.get("name")) for item in payload["features"]]
    if len(names) != len(set(names)):
        raise FeaturePolicyError("feature_registry_duplicate_feature")
    for item in payload["features"]:
        for field in ("cost", "evidence_kind", "may_decide", "may_not_decide",
                      "max_confidence_without_authority", "max_confidence_with_authority",
                      "learned_from"):
            if field not in item:
                raise FeaturePolicyError(
                    f"feature_{item.get('name')}_missing_{field}")
        for field in ("max_confidence_without_authority",
                      "max_confidence_with_authority"):
            if item[field] not in CONFIDENCE_ORDER:
                raise FeaturePolicyError(
                    f"feature_{item['name']}_bad_{field}: {item[field]}")
        authority = item.get("refutable_by")
        if authority and authority not in payload["authorities"]:
            raise FeaturePolicyError(
                f"feature_{item['name']}_unknown_authority: {authority}")
    return payload


def feature(name: str, *, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(registry) if registry else load_registry()
    for item in payload["features"]:
        if item["name"] == name:
            return dict(item)
    raise UndeclaredFeatureError(
        f"undeclared_feature: {name}. Declare it in data/ordering_features.json "
        "with its cost and what can refute it before using it to classify.")


def _matches(question: str, declared: Sequence[str]) -> bool:
    """A declared entry may carry a parenthetical condition; compare the head."""
    wanted = question.strip().casefold()
    for entry in declared:
        head = str(entry).split("(")[0].strip().casefold()
        if head == wanted or wanted == str(entry).strip().casefold():
            return True
    return False


def may_decide(name: str, question: str, *, authority_consulted: bool = False,
               registry: Mapping[str, Any] | None = None) -> Permission:
    """Whether this feature may settle this question, and how strongly.

    ``authority_consulted`` must be True only when the feature's declared
    authority was actually consulted for THIS item -- not when it exists in
    principle. That distinction is the whole point: the discography could have
    resolved ``MERECEDORA`` on the first day and nobody asked it.
    """
    item = feature(name, registry=registry)
    authority = item.get("refutable_by")
    ceiling = (item["max_confidence_with_authority"] if authority_consulted
               else item["max_confidence_without_authority"])

    if _matches(question, item["may_not_decide"]):
        return Permission(name, question, False, NONE, authority, authority_consulted,
                          f"{name} is declared as never deciding {question}")
    if not _matches(question, item["may_decide"]):
        return Permission(
            name, question, False, NONE, authority, authority_consulted,
            f"{name} does not declare {question}; declare it in the registry "
            "or abstain")
    if ceiling == NONE:
        missing = authority or "no authority is declared for this feature"
        return Permission(
            name, question, False, NONE, authority, authority_consulted,
            f"{name} alone cannot decide {question}: consult {missing} first")
    return Permission(name, question, True, ceiling, authority, authority_consulted,
                      f"{name} may decide {question} at most {ceiling}")


def confidence_ceiling(name: str, *, authority_consulted: bool = False,
                       registry: Mapping[str, Any] | None = None) -> str:
    item = feature(name, registry=registry)
    return (item["max_confidence_with_authority"] if authority_consulted
            else item["max_confidence_without_authority"])


def weakest(*labels: str) -> str:
    """The ceiling of a combination is its weakest member, never a sum.

    Adding confidences would assert an exchange rate nobody measured, which is
    the error the lexicographic cascade in ``project_reconstruction`` exists to
    avoid. A chain of evidence is only as strong as its weakest link.
    """
    if not labels:
        return NONE
    for label in labels:
        if label not in CONFIDENCE_ORDER:
            raise FeaturePolicyError(f"unknown_confidence: {label}")
    return min(labels, key=CONFIDENCE_ORDER.index)


def fold_is_valid(relation: str, question: str, *,
                  registry: Mapping[str, Any] | None = None) -> Permission:
    """Whether folding many rows into one answer is valid for this question.

    Folding by the wrong equivalence relation produces a confident wrong answer
    at scale, which is worse than no answer. Content identity is valid for
    purpose and invalid for consumer; containment propagates a rejection and not
    an acceptance.
    """
    payload = dict(registry) if registry else load_registry()
    for entry in payload["folding_relations"]:
        if entry["relation"] != relation:
            continue
        if _matches(question, entry["invalid_for"]):
            return Permission(relation, question, False, NONE, None, False,
                              f"{relation} is invalid for {question}: {entry['why']}")
        if _matches(question, entry["valid_for"]):
            return Permission(relation, question, True, "strong", None, False,
                              f"{relation} is valid for {question}")
        return Permission(
            relation, question, False, NONE, None, False,
            f"{relation} declares nothing about {question}; abstain rather than "
            "assume the fold holds")
    raise FeaturePolicyError(f"undeclared_folding_relation: {relation}")


def authority(name: str, *, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(registry) if registry else load_registry()
    try:
        return dict(payload["authorities"][name])
    except KeyError:
        raise FeaturePolicyError(f"undeclared_authority: {name}") from None


def audit(registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """What the registry currently permits, for a human to read in one screen."""
    payload = dict(registry) if registry else load_registry()
    rows = []
    for item in payload["features"]:
        rows.append({
            "feature": item["name"],
            "cost": item["cost"],
            "authority": item.get("refutable_by"),
            "alone": item["max_confidence_without_authority"],
            "with_authority": item["max_confidence_with_authority"],
            "decides": list(item["may_decide"]),
        })
    free_and_decisive = [row["feature"] for row in rows
                         if row["cost"] == "free" and row["alone"] != NONE]
    return {
        "contract": CONTRACT,
        "features": len(rows),
        "authorities": sorted(payload["authorities"]),
        "folding_relations": [entry["relation"]
                              for entry in payload["folding_relations"]],
        "rows": rows,
        "free_features_that_may_decide_alone": free_and_decisive,
        "decision_rule": payload["decision_rule"],
    }
