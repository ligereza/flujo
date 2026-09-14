"""Read the decisions a person already made, from the existing editor logs.

This is the natural supervision the directive points at: years of finished work
include selections the artist already made and fields the artist already
declared.  Nothing here needs a new label, a new queue or a new question.

Two logs, two different roles:

- ``selections.jsonl`` records **consumer decisions** — what was selected,
  deselected or discarded, with timestamps.  These are the outcome signal a
  learning episode needs; they are never claims about the work.
- ``classifications.jsonl`` records **declarations by a named person**
  (``owner: human``) about ownership, context kind, purpose, lane and triage.
  A declaration by a named authority is what lifts an ownership claim past
  ``candidate``.

The editor normally writes declarations as ``status: human_draft`` with
``promotion: none``; an explicit confirmation may instead be
``status: human_confirmed``.  Both are carried through without promotion: the
status records what the person did, and never becomes an automatic truth claim.

Read-only.  Later events win over earlier ones for the same item, so churn
resolves without discarding history.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .product_view import stable_json


SCHEMA = "mak-human-decision-log-v1"
ALGORITHM_VERSION = "human-decision-log-1"

# Selection vocabulary observed in the existing log.  An unknown decision is
# retained and counted, never silently mapped onto a known one.
SELECTED = "seleccionar"
DESELECTED = "deseleccionar"
DISCARDED = "descartar"

# Declaration fields the editor writes.  Only these are read; anything else is
# counted as unmapped so a new field is visible instead of ignored.
DECLARATION_FIELDS = (
    "ownership", "context_kind", "purpose", "nature", "format", "lane", "triage",
)
# Triage vocabulary observed in the log's ``triage`` field.
TRIAGE_WORK = "work"
TRIAGE_RECORD = "record"
TRIAGE_REVIEW = "review"
TRIAGE_DISCARD = "discard"
# Which declared fields can lift a claim, and which verb they speak to.
_ATTESTING_FIELDS = {
    "ownership": "es_mio",
    "context_kind": "ocurrio",
    "lane": "ocurrio",
}

# Relation kinds a person drew between two items.  They divide by what they
# assert: a source fact about how the material was published or dated, versus an
# interpretation about what the material means.  The distinction is kept because
# only the second is curatorial reading, and both were made by the same hand.
RELATION_KINDS = {
    "same_carousel": "source_publication_structure",
    "same_date_context": "source_dating",
    "same_event": "source_context",
    "shared_concept": "interpretation",
    "visual_similarity": "interpretation",
}
# A machine provider may propose, never attest.  Any provider other than the
# person is recorded as a proposal that stays candidate.
_HUMAN_PROVIDER = "human"

# A published item is identified by its platform media id: a long numeric stem.
# Anything else in these logs is a fixture or a placeholder, and a curatorial
# reading about *published* material must not include it.  The rule is positive
# — what a published id looks like — rather than a growing list of bad prefixes.
_MIN_PLATFORM_ID_DIGITS = 12


def _is_published_item(item_id: str) -> bool:
    stem = item_id.rsplit(".", 1)[0] if "." in item_id else item_id
    return stem.isdigit() and len(stem) >= _MIN_PLATFORM_ID_DIGITS


class HumanDecisionLogError(ValueError):
    """The existing decision log cannot be read."""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HumanDecisionLogError(f"jsonl_invalid:{path}:{number}") from exc
        if not isinstance(value, Mapping):
            raise HumanDecisionLogError(f"jsonl_row_not_object:{path}:{number}")
        rows.append(dict(value))
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_human_decisions(
    *,
    selections_path: str | Path | None = None,
    classifications_path: str | Path | None = None,
    connections_path: str | Path | None = None,
    feedback_path: str | Path | None = None,
    external_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve every existing decision log into a read-only final state."""
    selections_file = Path(selections_path).expanduser() if selections_path else None
    classifications_file = (
        Path(classifications_path).expanduser() if classifications_path else None)

    sources: list[dict[str, Any]] = []
    selection_events: list[dict[str, Any]] = []
    if selections_file is not None and selections_file.is_file():
        selection_events = _read_jsonl(selections_file)
        sources.append({
            "role": "consumer_decisions",
            "path": str(selections_file),
            "sha256": _sha256(selections_file),
            "event_count": len(selection_events),
        })
    connection_events: list[dict[str, Any]] = []
    feedback_events: list[dict[str, Any]] = []
    external_events: list[dict[str, Any]] = []
    declaration_events: list[dict[str, Any]] = []
    if classifications_file is not None and classifications_file.is_file():
        declaration_events = _read_jsonl(classifications_file)
        sources.append({
            "role": "named_person_declarations",
            "path": str(classifications_file),
            "sha256": _sha256(classifications_file),
            "event_count": len(declaration_events),
        })
    for path_value, role, sink in (
        (connections_path, "person_drawn_relations", connection_events),
        (feedback_path, "person_feedback_on_proposals", feedback_events),
        (external_path, "machine_proposals", external_events),
    ):
        if path_value is None:
            continue
        candidate = Path(path_value).expanduser()
        if not candidate.is_file():
            continue
        sink.extend(_read_jsonl(candidate))
        sources.append({
            "role": role,
            "path": str(candidate),
            "sha256": _sha256(candidate),
            "event_count": len(sink),
        })
    if not sources:
        raise HumanDecisionLogError("no_decision_log_present")

    # Selections: last event per item wins; the churn is retained as a count.
    by_item_selection: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selection_events:
        item = str(row.get("item_id") or "")
        if item:
            by_item_selection[item].append(row)
    selections: dict[str, dict[str, Any]] = {}
    unknown_decisions: Counter[str] = Counter()
    for item, rows in by_item_selection.items():
        ordered = sorted(rows, key=lambda entry: str(entry.get("ts") or ""))
        final = ordered[-1]
        decision = str(final.get("decision") or "")
        if decision not in {SELECTED, DESELECTED, DISCARDED}:
            unknown_decisions[decision] += 1
        selections[item] = {
            "decision": decision,
            "decided_at": str(final.get("ts") or ""),
            "event_count": len(ordered),
            "changed_mind": len({str(entry.get("decision")) for entry in ordered}) > 1,
            "history": [
                {"decision": str(entry.get("decision") or ""),
                 "ts": str(entry.get("ts") or "")}
                for entry in ordered
            ],
        }

    # Declarations: last non-empty value per (item, field).
    by_item_field: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    unmapped_fields: Counter[str] = Counter()
    owners: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    promotions: Counter[str] = Counter()
    for row in sorted(declaration_events, key=lambda entry: str(entry.get("ts") or "")):
        item = str(row.get("item_id") or "")
        if not item:
            continue
        owners[str(row.get("owner") or "")] += 1
        statuses[str(row.get("status") or "")] += 1
        promotions[str(row.get("promotion") or "")] += 1
        fields = row.get("fields")
        if not isinstance(fields, Mapping):
            continue
        for key, value in fields.items():
            name = str(key)
            if name not in DECLARATION_FIELDS:
                unmapped_fields[name] += 1
                continue
            text = str(value or "").strip()
            if not text:
                continue
            source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
            by_item_field[item][name] = {
                "value": text,
                "declared_at": str(row.get("ts") or ""),
                "owner": str(row.get("owner") or ""),
                "status": str(row.get("status") or ""),
                "promotion": str(row.get("promotion") or ""),
                "asset_path": str(source.get("asset_path") or ""),
                "dated": str(source.get("fecha") or ""),
            }

    declarations: dict[str, dict[str, Any]] = {}
    for item, fields in by_item_field.items():
        declarations[item] = {
            "fields": dict(sorted(fields.items())),
            "attesting_fields": sorted(set(fields) & set(_ATTESTING_FIELDS)),
            "declared_by": sorted({row["owner"] for row in fields.values() if row["owner"]}),
            "kept_as_draft": all(
                row["status"] == "human_draft" for row in fields.values()),
            "promotion": sorted({row["promotion"] for row in fields.values()}),
        }

    field_value_counts: Counter[str] = Counter()
    for fields in by_item_field.values():
        for name, row in fields.items():
            field_value_counts[f"{name}={row['value']}"] += 1

    # Relations a person drew.  Deduplicated on the unordered pair plus the kind,
    # because A-B and B-A are the same statement.
    relations: dict[str, dict[str, Any]] = {}
    unknown_relation_kinds: Counter[str] = Counter()
    for row in sorted(connection_events, key=lambda entry: str(entry.get("ts") or "")):
        left = str(row.get("source_id") or "")
        right = str(row.get("target_id") or "")
        kind = str(row.get("relation") or "")
        if not left or not right or not kind:
            continue
        if kind not in RELATION_KINDS:
            unknown_relation_kinds[kind] += 1
        pair = tuple(sorted((left, right)))
        key = f"{pair[0]}|{pair[1]}|{kind}"
        relations[key] = {
            "both_published": _is_published_item(left) and _is_published_item(right),
            "left": pair[0],
            "right": pair[1],
            "relation": kind,
            "asserts": RELATION_KINDS.get(kind, "unmapped"),
            "drawn_at": str(row.get("ts") or ""),
            "drawn_by": _HUMAN_PROVIDER,
        }

    # Feedback on proposals.  An accept by a person is confirmation; anything
    # from another provider is a proposal and stays a proposal.
    feedback: dict[str, dict[str, Any]] = {}
    facet_actions: dict[str, Counter[str]] = defaultdict(Counter)
    non_human_feedback = 0
    for row in sorted(feedback_events, key=lambda entry: str(entry.get("ts") or "")):
        work = row.get("work") if isinstance(row.get("work"), Mapping) else {}
        provider = str(work.get("provider") or "")
        if provider != _HUMAN_PROVIDER:
            non_human_feedback += 1
            continue
        left = str(row.get("source_id") or "")
        right = str(row.get("target_id") or "")
        kind = str(row.get("relation") or "")
        action = str(row.get("action") or "")
        facet = str(row.get("facet") or "")
        if not left or not right:
            continue
        facet_actions[facet][action] += 1
        pair = tuple(sorted((left, right)))
        feedback[f"{pair[0]}|{pair[1]}|{kind}"] = {
            "action": action,
            "facet": facet,
            "relation": kind,
            "confirmed_by": provider,
            "work_status": str(work.get("status") or ""),
            "at": str(row.get("ts") or ""),
        }

    # Machine curatorial inferences: counted and named, never attesting.
    external_providers: Counter[str] = Counter()
    external_hypotheses = 0
    external_unknowns = 0
    for row in external_events:
        external_providers[str(row.get("provider") or "")] += 1
        inference = row.get("inference") if isinstance(row.get("inference"), Mapping) else {}
        external_hypotheses += len(inference.get("hypotheses") or [])
        external_unknowns += len(inference.get("unknowns") or [])

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "sources": sources,
        "consumer_decisions": {
            "item_count": len(selections),
            "event_count": len(selection_events),
            "final_counts": dict(sorted(Counter(
                row["decision"] for row in selections.values()).items())),
            "items_where_the_person_changed_their_mind": sum(
                1 for row in selections.values() if row["changed_mind"]),
            "unknown_decision_values": dict(sorted(unknown_decisions.items())),
            "by_item": dict(sorted(selections.items())),
            "note": (
                "these are decisions a person already made; they are the outcome "
                "signal for learning, never a claim about the work"
            ),
        },
        "declarations": {
            "item_count": len(declarations),
            "event_count": len(declaration_events),
            "declared_by": dict(sorted(owners.items())),
            "status_counts": dict(sorted(statuses.items())),
            "promotion_counts": dict(sorted(promotions.items())),
            "field_value_counts": dict(sorted(field_value_counts.items())),
            "unmapped_fields": dict(sorted(unmapped_fields.items())),
            "attesting_field_map": dict(sorted(_ATTESTING_FIELDS.items())),
            "by_item": dict(sorted(declarations.items())),
            "note": (
                "a declaration by a named person is what lifts an ownership claim "
                "past candidate; human_draft and human_confirmed are retained "
                "with promotion=none, and neither is auto-promoted"
            ),
        },
        "relations": {
            "pair_count": len(relations),
            "event_count": len(connection_events),
            "kind_counts": dict(sorted(Counter(
                row["relation"] for row in relations.values()).items())),
            "asserts_counts": dict(sorted(Counter(
                row["asserts"] for row in relations.values()).items())),
            "unknown_kinds": dict(sorted(unknown_relation_kinds.items())),
            "published_pair_count": sum(
                1 for row in relations.values() if row["both_published"]),
            "non_published_pair_count": sum(
                1 for row in relations.values() if not row["both_published"]),
            "non_published_examples": sorted({
                item
                for row in relations.values() if not row["both_published"]
                for item in (row["left"], row["right"])
                if not _is_published_item(item)
            })[:6],
            "non_published_note": (
                "a pair is only carried into curatorial output when both ids are "
                "platform media ids; placeholders and replay fixtures are counted "
                "here because a fixture in a decision log is a fact about the log, "
                "not about the work"
            ),
            "confirmed_pair_count": sum(
                1 for key, row in relations.items()
                if feedback.get(key, {}).get("action") == "accept"),
            "by_pair": dict(sorted(relations.items())),
            "note": (
                "a person drew these; a source-structure relation states how the "
                "material was published or dated, an interpretation states what it "
                "means, and only the second is curatorial reading"
            ),
        },
        "feedback": {
            "pair_count": len(feedback),
            "event_count": len(feedback_events),
            "non_human_rows_ignored": non_human_feedback,
            "action_counts": dict(sorted(Counter(
                row["action"] for row in feedback.values()).items())),
            "by_facet": {
                facet: dict(sorted(counts.items()))
                for facet, counts in sorted(facet_actions.items())
            },
            "by_pair": dict(sorted(feedback.items())),
            "note": (
                "an accept by the person confirms a proposal; only rows whose work "
                "provider is the person are read here"
            ),
        },
        "machine_proposals": {
            "event_count": len(external_events),
            "providers": dict(sorted(external_providers.items())),
            "hypothesis_count": external_hypotheses,
            "unknown_count": external_unknowns,
            "attesting": False,
            "note": (
                "an external provider may propose and may name its unknowns; it can "
                "never attest, so nothing here lifts a claim above candidate"
            ),
        },
        "control": {
            "source_rescan": False,
            "physical_mutation": False,
            "database_write": False,
            "network_called": False,
            "read_only": True,
            "promotion": "none",
        },
        "limits": [
            "A discard is a decision about a portfolio, not a judgement of the work.",
            "A relation drawn between two items is a curatorial statement, never "
            "evidence that they are one work.",
            "A machine proposal is never an attestation, whatever its confidence.",
            "A human draft or confirmed declaration is evidence of what the person "
            "said, not an automatically promoted truth.",
            "An item absent from both logs is undecided, not rejected.",
        ],
    }
    result["log_hash"] = "sha256:" + hashlib.sha256(
        stable_json(result).encode("utf-8")).hexdigest()
    return result


def attesting_declarations(log: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Declarations that can lift a claim, indexed by item id."""
    result: dict[str, list[dict[str, Any]]] = {}
    declarations = log.get("declarations")
    if not isinstance(declarations, Mapping):
        return result
    for item, row in (declarations.get("by_item") or {}).items():
        rows: list[dict[str, Any]] = []
        for name in row.get("attesting_fields") or []:
            field = (row.get("fields") or {}).get(name)
            if not isinstance(field, Mapping):
                continue
            rows.append({
                "field": name,
                "verb": _ATTESTING_FIELDS[name],
                "value": field["value"],
                "declared_by": field["owner"],
                "declared_at": field["declared_at"],
                "kept_as_draft": field["status"] == "human_draft",
                "promotion": field["promotion"],
                "dated": field["dated"],
                "asset_path": field["asset_path"],
            })
        if rows:
            result[str(item)] = sorted(rows, key=lambda entry: entry["field"])
    return result


def triage_declarations(log: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return named-person record-vs-work calls keyed by numeric source id."""
    result: dict[str, dict[str, Any]] = {}
    declarations = log.get("declarations")
    if not isinstance(declarations, Mapping):
        return result
    for item, row in (declarations.get("by_item") or {}).items():
        field = (row.get("fields") or {}).get("triage")
        if not isinstance(field, Mapping) or not field.get("value"):
            continue
        stem = str(item).rsplit(".", 1)[0]
        if not stem.isdigit():
            continue
        result[stem] = {
            "value": field["value"],
            "declared_by": field["owner"],
            "declared_at": field["declared_at"],
            "kept_as_draft": field["status"] == "human_draft",
        }
    return result


def curatorial_relations(log: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Relations a person drew, with their confirmation state, for the claim base."""
    relations = log.get("relations")
    if not isinstance(relations, Mapping):
        return []
    feedback = (log.get("feedback") or {}).get("by_pair") or {}
    rows: list[dict[str, Any]] = []
    for key, row in (relations.get("by_pair") or {}).items():
        if not row.get("both_published"):
            continue
        confirmation = feedback.get(key) or {}
        rows.append({
            **row,
            "confirmed": confirmation.get("action") == "accept",
            "confirmation_facet": confirmation.get("facet") or "",
            # An interpretation the person also confirmed through the feedback
            # surface has two routes; a source-structure relation is a fact about
            # the publication and does not need a second one.
            "state": (
                "externally_attested"
                if confirmation.get("action") == "accept"
                or row["asserts"].startswith("source_")
                else "candidate"
            ),
        })
    return sorted(rows, key=lambda entry: (entry["left"], entry["right"], entry["relation"]))


def consumer_decision_summary(log: Mapping[str, Any]) -> dict[str, Any]:
    """Fold the selection log into the shape a learning episode needs."""
    decisions = log.get("consumer_decisions")
    decisions = decisions if isinstance(decisions, Mapping) else {}
    counts = dict(decisions.get("final_counts") or {})
    selected = int(counts.get(SELECTED, 0))
    discarded = int(counts.get(DISCARDED, 0)) + int(counts.get(DESELECTED, 0))
    total = selected + discarded
    return {
        "status": "recorded" if total else "pending",
        "decided_by": "human",
        "source_refs": [row["path"] for row in log.get("sources", [])
                        if row.get("role") == "consumer_decisions"],
        "log_hash": log.get("log_hash"),
        "item_count": int(decisions.get("item_count") or 0),
        "selected": selected,
        "rejected": discarded,
        "selection_rate": round(selected / total, 4) if total else None,
        "changed_mind_count": int(
            decisions.get("items_where_the_person_changed_their_mind") or 0),
        "counts": counts,
        "note": (
            "a real person selected and discarded these items; the rate is a "
            "measured outcome, not a quality score"
        ),
    }


__all__ = [
    "ALGORITHM_VERSION", "DECLARATION_FIELDS", "DESELECTED", "DISCARDED",
    "HumanDecisionLogError", "RELATION_KINDS", "SCHEMA", "SELECTED",
    "TRIAGE_DISCARD", "TRIAGE_RECORD", "TRIAGE_REVIEW", "TRIAGE_WORK",
    "attesting_declarations", "consumer_decision_summary", "curatorial_relations",
    "read_human_decisions", "triage_declarations",
]
