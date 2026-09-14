"""Falsifiable internal curation over the already-projected archive view.

The contracurator is deliberately a *consumer* of
``mak-archive-portfolio-view-v1``.  It does not scan files, recreate the
archive, infer an artist, or turn an observed description into an authorial
statement.  It can only select a bounded exhibition when the view itself
contains a relation and contextual reason for every selected source record.

Its product episode is a pure ``LearningStore.record_episode`` projection.
Persisting it is explicit and requires a pre-existing Project IR record; the
Hub remains read-only.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .product_view import ProductViewError, validate_archive_portfolio_view
from .project_ir import LearningStore
from ._contract_helpers import sha256_ref as _hash


SCHEMA = "mak-contracurator-exhibition-v1"
ALGORITHM_VERSION = "contracurator-1"
EPISODE_SCHEMA = "mak-contracurator-product-episode-v1"
MIN_SELECTION = 8
MAX_SELECTION = 12


class ContracuratorError(ValueError):
    """The archive view cannot sustain a bounded curatorial decision."""


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContracuratorError(f"{field}_must_be_object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContracuratorError(f"{field}_must_be_nonempty_string")
    return value.strip()


def _source_refs(rows: list[Mapping[str, Any]], field: str) -> list[str]:
    refs = [_text(row.get("source_ref"), f"{field}.source_ref") for row in rows]
    if len(refs) != len(set(refs)):
        raise ContracuratorError(f"{field}_source_refs_not_unique")
    return sorted(refs)


def _relation_index(view: Mapping[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    rows = view.get("relationships")
    if not isinstance(rows, list):
        raise ContracuratorError("archive_view_relationships_missing")
    by_item: dict[str, list[dict[str, Any]]] = {}
    typed: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, "archive_view.relationship")
        left = _text(row.get("piece_a"), "archive_view.relationship.piece_a")
        right = _text(row.get("piece_b"), "archive_view.relationship.piece_b")
        relation = {
            "source_ref": _text(row.get("source_ref"), "archive_view.relationship.source_ref"),
            "piece_a": left,
            "piece_b": right,
            "class": _text(row.get("class"), "archive_view.relationship.class"),
            "weight": row.get("weight"),
            "epistemic_status": _text(
                row.get("epistemic_status"), "archive_view.relationship.epistemic_status"),
        }
        typed.append(relation)
        by_item.setdefault(left, []).append(relation)
        by_item.setdefault(right, []).append(relation)
    for item_id in by_item:
        by_item[item_id].sort(key=lambda row: row["source_ref"])
    return by_item, sorted(typed, key=lambda row: row["source_ref"])


def _selection_row(
    item: Mapping[str, Any], *, relation_refs: list[str], reason_codes: list[str],
    contextual_reason: str,
) -> dict[str, Any]:
    return {
        "source_ref": _text(item.get("source_ref"), "item.source_ref"),
        "item_id": _text(item.get("item_id"), "item.item_id"),
        "roles": sorted(_text(role, "item.role") for role in item.get("roles", [])),
        "relation_refs": sorted(set(relation_refs)),
        "reason_codes": sorted(set(reason_codes)),
        "contextual_reason": contextual_reason,
    }


def _counterevidence(
    *, counter_id: str, statement: str, source_refs: list[str], reason: str,
) -> dict[str, Any]:
    return {
        "counterevidence_id": counter_id,
        "statement": statement,
        "source_refs": sorted(set(source_refs)),
        "reason": reason,
    }


def _assessment(
    *, selected: list[dict[str, Any]], counterevidence: list[dict[str, Any]],
    name_route_authorship_dependency: bool, derived_as_independent_work: bool,
    extra_rejections: list[str] | None = None,
) -> dict[str, Any]:
    reasons = list(extra_rejections or [])
    if not MIN_SELECTION <= len(selected) <= MAX_SELECTION:
        reasons.append("selection_size_out_of_bounds")
    if not selected or any(not row["source_ref"] for row in selected):
        reasons.append("selected_source_ref_missing")
    if any(not row["contextual_reason"] or not row["relation_refs"] for row in selected):
        reasons.append("selected_contextual_relation_missing")
    if not counterevidence:
        reasons.append("counterevidence_missing")
    if name_route_authorship_dependency:
        reasons.append("depends_on_name_route_or_authorship")
    if derived_as_independent_work:
        reasons.append("derived_record_counted_as_independent_work")
    unique = sorted(set(reasons))
    coverage = 0.0 if not selected else sum(bool(row["relation_refs"]) for row in selected) / len(selected)
    return {
        "status": "survives" if not unique else "defeated",
        "rejection_reasons": unique,
        "coherence": round(coverage, 6),
        "coverage": round(coverage, 6),
        "evidence_debt": len(unique),
        "name_route_authorship_dependency": name_route_authorship_dependency,
        "derived_as_independent_work": derived_as_independent_work,
    }


def _thesis(
    *, thesis_id: str, position: str, selection: list[dict[str, Any]],
    counterevidence: list[dict[str, Any]], name_route_authorship_dependency: bool,
    derived_as_independent_work: bool, extra_rejections: list[str] | None = None,
) -> dict[str, Any]:
    assessment = _assessment(
        selected=selection,
        counterevidence=counterevidence,
        name_route_authorship_dependency=name_route_authorship_dependency,
        derived_as_independent_work=derived_as_independent_work,
        extra_rejections=extra_rejections,
    )
    return {
        "thesis_id": thesis_id,
        "position": position,
        "source_refs": _source_refs(selection, thesis_id + ".selection"),
        "selection": selection,
        "counterevidence": counterevidence,
        "assessment": assessment,
    }


def _ranked(items: list[Mapping[str, Any]], relation_index: Mapping[str, list[dict[str, Any]]]) -> list[Mapping[str, Any]]:
    """Rank only from typed relationship evidence; IDs break equal scores only."""
    def sort_key(item: Mapping[str, Any]) -> tuple[float, int, str]:
        relations = relation_index.get(str(item.get("item_id")), [])
        weight = sum(float(row["weight"]) for row in relations if isinstance(row["weight"], (int, float)))
        return (-weight, -len(relations), str(item.get("source_ref")))
    return sorted(items, key=sort_key)


def _episode(
    *, input_hash: str, theses: list[dict[str, Any]], result: Mapping[str, Any], limits: list[str],
    order_basis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    semantic = {
        "algorithm_version": ALGORITHM_VERSION,
        "input_hash": input_hash,
        "theses": theses,
        "result": result,
        "limits": limits,
        "order_basis": dict(order_basis or {}),
    }
    episode_hash = _hash(semantic)
    episode_id = "episode:contracurator:" + episode_hash[7:39]
    survived = result.get("status") == "survived"
    validation = {
        "status": "passed" if survived else "abstained",
        "checks": [
            "archive_view_contract",
            "three_competing_theses",
            "selected_source_refs_complete",
            "counterevidence_present",
            "no_name_route_authorship_inference",
            "no_untyped_derivative_as_work",
        ],
        "truth_promotions": 0,
        "artistic_fact_mutations": 0,
    }
    projection = {
        "project_id": None,
        "objective": "test a falsifiable internal curatorial thesis",
        "phase": "contracurator",
        "action": {
            "input_hash": input_hash,
            "candidate_thesis_ids": [row["thesis_id"] for row in theses],
            **({"order_basis": dict(order_basis)} if order_basis else {}),
        },
        "observation": {
            "theses": copy.deepcopy(theses),
            "limits": list(limits),
            **({"order_basis": dict(order_basis)} if order_basis else {}),
        },
        "outcome": copy.deepcopy(dict(result)),
        "validation": validation,
        "status": "needs_evidence" if survived else "abstained",
        "provider": "mak-contracurator",
        "model": "",
        "cost": {},
        "parent_episode_id": None,
        "episode_id": episode_id,
        "started_at": None,
        "finished_at": None,
        "source_snapshot_hash": "",
        "code_commit": "",
        "tool_versions": {},
    }
    episode = {
        "schema": EPISODE_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "episode_id": episode_id,
        "episode_hash": episode_hash,
        "status": "open" if survived else "abstained",
        "input": {
            "archive_view_hash": input_hash,
            **({"ssd_order_foundation": dict(order_basis)} if order_basis else {}),
        },
        "thesis_ids": [row["thesis_id"] for row in theses],
        "discarded_thesis_ids": [
            row["thesis_id"] for row in theses if row["assessment"]["status"] == "defeated"
        ],
        "result_status": result.get("status"),
        "limits": list(limits),
        "control": {
            "database_write": False,
            "publication": False,
            "submission": False,
            "dispatch": False,
            "training_permitted": False,
            "promotion": "none",
        },
        "record_episode_projection": projection,
    }
    return episode


_MAX_HUB_CLASS_SAMPLES = 3
_MAX_HUB_SIDE_REFS = 2


def _bounded_side(side: Any) -> dict[str, Any]:
    """Project one question side without carrying the whole SSD container."""
    if not isinstance(side, Mapping):
        return {}
    return {
        "container": side.get("container"),
        "container_binding": side.get("container_binding"),
        "ssd_project_count": side.get("ssd_project_count"),
        "ssd_asset_count": side.get("ssd_asset_count"),
        "ssd_bytes": side.get("ssd_bytes"),
        "hash_pending_assets": side.get("hash_pending_assets"),
        "tie_asset_count": side.get("tie_asset_count"),
        "authority": side.get("authority"),
        "source_ref": side.get("source_ref"),
        "ssd_project_refs": [
            {
                "project_id": row.get("project_id"),
                "project_path": row.get("project_path"),
                "asset_count": row.get("asset_count"),
                "source_ref": row.get("source_ref"),
            }
            for row in (side.get("ssd_project_refs") or [])[:_MAX_HUB_SIDE_REFS]
            if isinstance(row, Mapping)
        ],
        "tie_asset_refs": [
            {
                "relative_path": row.get("relative_path"),
                "bytes": row.get("bytes"),
                "verdict": row.get("verdict"),
                "source_ref": row.get("source_ref"),
            }
            for row in (side.get("tie_asset_refs") or [])[:_MAX_HUB_SIDE_REFS]
            if isinstance(row, Mapping)
        ],
        "intake": {
            "status": (side.get("intake") or {}).get("status"),
            "candidate_count": (side.get("intake") or {}).get("candidate_count", 0),
            "role": (side.get("intake") or {}).get("role"),
            "candidates": [
                {
                    "project_path": row.get("project_path"),
                    "rank": row.get("rank"),
                    "reason": row.get("reason"),
                    "source_ref": row.get("source_ref"),
                }
                for row in ((side.get("intake") or {}).get("candidates") or [])[:_MAX_HUB_SIDE_REFS]
                if isinstance(row, Mapping)
            ],
        },
        "reconstruction": {
            "status": (side.get("reconstruction") or {}).get("status"),
            "decided_project_count": (side.get("reconstruction") or {}).get(
                "decided_project_count", 0),
            "role_counts": (side.get("reconstruction") or {}).get("role_counts") or {},
            "epistemic_status_counts": (side.get("reconstruction") or {}).get(
                "epistemic_status_counts") or {},
            "source_refs": ((side.get("reconstruction") or {}).get("source_refs") or [])[:1],
        },
        "index_relations": {
            "touching_container": (side.get("index_relations") or {}).get(
                "touching_container", 0),
            "crossing_containers": (side.get("index_relations") or {}).get(
                "crossing_containers", 0),
        },
    }


def _question_projection(row: Mapping[str, Any], *, full: bool) -> dict[str, Any]:
    """Project one operator question for the Hub without answering it.

    The compact form is enough to see the frontier; the full form carries the
    evidence for, against and missing so a human can see what a real answer
    would need.  Neither form ever influences the selection.
    """
    dossier = row.get("dossier") if isinstance(row.get("dossier"), Mapping) else {}
    byte_identity = dossier.get("byte_identity") if isinstance(dossier.get("byte_identity"), Mapping) else {}
    projection: dict[str, Any] = {
        "question_id": row.get("question_id"),
        "status": row.get("status"),
        "left": row.get("left"),
        "right": row.get("right"),
        "question": row.get("question"),
        "answers": row.get("answers"),
        "examples": row.get("examples"),
        "shared_bytes": row.get("shared_bytes"),
        "shared_classes": row.get("shared_classes"),
        "authority_context": row.get("authority_context"),
        "evidence_ref": row.get("evidence_ref"),
        "reopen_when": row.get("reopen_when"),
        "reopen_when_source": row.get("reopen_when_source"),
        "evidence_grade": dossier.get("evidence_grade"),
        "substantive_shared_bytes": dossier.get("substantive_shared_bytes"),
        "unbound_containers": dossier.get("unbound_containers") or [],
        "actionable_evidence_kinds": dossier.get("actionable_evidence_kinds") or [],
        "adds_actionable_evidence": dossier.get("adds_actionable_evidence"),
        "deferral_reason": dossier.get("deferral_reason", ""),
        "identity_tiers": (byte_identity.get("identity_tiers") or {}),
        "typed_relation_binding_this_pair": (
            (dossier.get("typed_relations") or {}).get("binding_this_pair", 0)),
        "machine_answerable": False,
        "selection_effect": "none",
    }
    if not full:
        return projection
    projection["byte_identity"] = {
        "status": byte_identity.get("status"),
        "matches_declared_question": byte_identity.get("matches_declared_question"),
        "recomputed_shared_classes": byte_identity.get("recomputed_shared_classes"),
        "recomputed_shared_bytes": byte_identity.get("recomputed_shared_bytes"),
        "substantive_class_count": byte_identity.get("substantive_class_count"),
        "substantive_shared_bytes": byte_identity.get("substantive_shared_bytes"),
        "zero_byte_class_count": byte_identity.get("zero_byte_class_count"),
        "appledouble_class_count": byte_identity.get("appledouble_class_count"),
        "classes_spanning_more_than_two_containers": byte_identity.get(
            "classes_spanning_more_than_two_containers"),
        "other_containers_in_shared_classes": byte_identity.get(
            "other_containers_in_shared_classes") or [],
        "verdicts": byte_identity.get("verdicts") or {},
        "source_ref": byte_identity.get("source_ref"),
        "class_samples": [
            {
                "content_id": sample.get("content_id"),
                "bytes_each": sample.get("bytes_each"),
                "distinct_roots": sample.get("distinct_roots"),
                "degenerate": sample.get("degenerate"),
                "source_ref": sample.get("source_ref"),
            }
            for sample in (byte_identity.get("class_samples") or [])[:_MAX_HUB_CLASS_SAMPLES]
            if isinstance(sample, Mapping)
        ],
    }
    projection["byte_identity"]["identity_tiers"] = byte_identity.get("identity_tiers") or {}
    projection["byte_identity"]["shared_member_path_count"] = byte_identity.get(
        "shared_member_path_count", 0)
    projection["byte_identity"]["shared_member_paths"] = (
        byte_identity.get("shared_member_paths") or [])[:8]
    sides = dossier.get("sides") if isinstance(dossier.get("sides"), Mapping) else {}
    projection["sides"] = {
        "left": _bounded_side(sides.get("left")),
        "right": _bounded_side(sides.get("right")),
    }
    projection["typed_relations"] = dossier.get("typed_relations")
    for field in ("evidence_for", "evidence_against", "missing_evidence"):
        projection[field] = [
            {"statement": item.get("statement"), "source_ref": item.get("source_ref")}
            for item in (dossier.get(field) or []) if isinstance(item, Mapping)
        ]
    projection["declared_input_signals"] = dossier.get("declared_input_signals")
    projection["resolution"] = dossier.get("resolution")
    return projection


def _order_basis_metadata(order_basis: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Keep the SSD foundation visible without using an unbound crosswalk."""
    if order_basis is None:
        return None
    schema = _text(order_basis.get("schema"), "ssd_order_foundation.schema")
    if schema != "mak-ssd-order-foundation-v1":
        raise ContracuratorError("ssd_order_foundation_schema_invalid")
    semantic_hash = _text(order_basis.get("semantic_hash"), "ssd_order_foundation.semantic_hash")
    if not semantic_hash.startswith("sha256:"):
        raise ContracuratorError("ssd_order_foundation_hash_invalid")
    status = _text(order_basis.get("status"), "ssd_order_foundation.status")
    crosswalk = order_basis.get("crosswalk_to_iskvw")
    if not isinstance(crosswalk, Mapping):
        raise ContracuratorError("ssd_order_foundation_crosswalk_missing")
    crosswalk_status = _text(crosswalk.get("status"), "ssd_order_foundation.crosswalk.status")
    if crosswalk_status not in {"bound", "candidate", "unresolved"}:
        raise ContracuratorError("ssd_order_foundation_crosswalk_status_invalid")
    inventory = order_basis.get("inventory")
    order = order_basis.get("order")
    if not isinstance(inventory, Mapping) or not isinstance(order, Mapping):
        raise ContracuratorError("ssd_order_foundation_order_summary_missing")
    bucket_counts = order.get("bucket_counts")
    projection = order.get("order_projection_result")
    if not isinstance(bucket_counts, Mapping) or not isinstance(projection, Mapping):
        raise ContracuratorError("ssd_order_foundation_order_summary_invalid")
    identity = projection.get("identity")
    relations = projection.get("relations")
    door = projection.get("door")
    if not isinstance(identity, Mapping) or not isinstance(relations, Mapping) or not isinstance(door, Mapping):
        raise ContracuratorError("ssd_order_foundation_order_projection_invalid")
    operator_review = order_basis.get("operator_review")
    if not isinstance(operator_review, Mapping):
        raise ContracuratorError("ssd_order_foundation_operator_review_missing")
    question_rows = operator_review.get("questions")
    if not isinstance(question_rows, list):
        raise ContracuratorError("ssd_order_foundation_operator_questions_invalid")
    triage = operator_review.get("triage")
    if not isinstance(triage, Mapping):
        raise ContracuratorError("ssd_order_foundation_operator_triage_missing")
    queue = operator_review.get("attestation_queue")
    if not isinstance(queue, list):
        raise ContracuratorError("ssd_order_foundation_attestation_queue_invalid")
    if any(row.get("answered") is not False for row in queue if isinstance(row, Mapping)):
        raise ContracuratorError("ssd_order_foundation_attestation_queue_prefilled")
    frontier = order_basis.get("research_frontier")
    if not isinstance(frontier, Mapping):
        raise ContracuratorError("ssd_order_foundation_research_frontier_missing")
    if frontier.get("dispatch") is not False or frontier.get("create_job_invoked") is not False:
        raise ContracuratorError("ssd_order_foundation_research_frontier_dispatched")
    pilot = frontier.get("existing_pilot_chain")
    if isinstance(pilot, Mapping) and pilot.get("status") == "present_pilot_scope":
        # A pilot payload may be cited but never adopted as an order resolution.
        if pilot.get("scope") != "pilot_case_run_not_the_ssd_order_frontier":
            raise ContracuratorError("ssd_order_foundation_pilot_chain_scope_invalid")
        statuses = pilot.get("relation_statuses")
        if not isinstance(statuses, Mapping) or set(statuses) - {"candidate"}:
            raise ContracuratorError("ssd_order_foundation_pilot_chain_promoted")
        pilot_frontier = pilot.get("research_frontier")
        if isinstance(pilot_frontier, Mapping) and pilot_frontier.get("dispatched_job_count"):
            raise ContracuratorError("ssd_order_foundation_pilot_chain_dispatched")
    audit = crosswalk.get("binding_audit")
    if not isinstance(audit, Mapping):
        raise ContracuratorError("ssd_order_foundation_crosswalk_binding_audit_missing")
    if crosswalk_status != "bound" and (
        audit.get("with_typed_reference") or audit.get("with_shared_content_hash")
        or audit.get("with_delivery_receipt")
    ):
        raise ContracuratorError("ssd_order_foundation_crosswalk_binding_contradiction")
    # A pre-existing operational link may be reported but never as a typed one.
    for label in (audit.get("operational_possible_link_classes") or {}):
        relation, _, method = str(label).partition("/")
        if not relation.startswith("possible_") or method != "path_token":
            raise ContracuratorError("ssd_order_foundation_operational_link_promoted")
    asked_rows = [row for row in question_rows if isinstance(row, Mapping) and row.get("status") == "ask"]
    deferred_rows = [row for row in question_rows if isinstance(row, Mapping) and row.get("status") == "deferred"]
    return {
        "schema": schema,
        "semantic_hash": semantic_hash,
        "status": status,
        "crosswalk_status": crosswalk_status,
        "inventory": {
            "assets": inventory.get("assets"),
            "projects": inventory.get("projects"),
            "families": inventory.get("families"),
            "relations": inventory.get("relations"),
            "hash_pending": (inventory.get("hash_state") or {}).get("pending"),
        },
        "order_summary": {
            "bucket_counts": dict(bucket_counts),
            "certified_same": identity.get("certified_same"),
            "certified_distinct": identity.get("certified_distinct"),
            "operator_ties": relations.get("still_a_tie_for_the_operator"),
            "questions_to_ask": door.get("questions_to_ask"),
        },
        "operator_review": {
            "schema": operator_review.get("schema"),
            "status": operator_review.get("status"),
            "asked_count": operator_review.get("asked_count"),
            "deferred_count": operator_review.get("deferred_count"),
            "questions_before_triage": operator_review.get("questions_before_triage"),
            "coverage_of_disputed_bytes": operator_review.get("coverage_of_disputed_bytes"),
            "machine_answerable": operator_review.get("machine_answerable"),
            "selection_effect": operator_review.get("selection_effect"),
            "source_ref": operator_review.get("source_ref"),
            "source_sha256": operator_review.get("source_sha256"),
            "dossier_algorithm": operator_review.get("dossier_algorithm"),
            "evidence_sources": operator_review.get("evidence_sources"),
            "identity_tiers": operator_review.get("identity_tiers"),
            "index_relation_reality": operator_review.get("index_relation_reality"),
            "triage": dict(triage),
            "attestation_queue_status": operator_review.get("attestation_queue_status"),
            "answers_recorded": operator_review.get("answers_recorded"),
            "attestation_queue": [dict(row) for row in queue if isinstance(row, Mapping)],
            "question_samples": [
                _question_projection(row, full=True) for row in asked_rows
            ],
            "deferred_samples": [
                _question_projection(row, full=False) for row in deferred_rows
            ],
        },
        "research_frontier": {
            "status": frontier.get("status"),
            "scope": frontier.get("scope"),
            "compiled": frontier.get("compiled"),
            "job_count": frontier.get("job_count"),
            "reason": frontier.get("reason"),
            "precision_note": frontier.get("precision_note"),
            "reopen_when": frontier.get("reopen_when"),
            "dispatch": False,
            "create_job_invoked": False,
            "existing_pilot_chain": {
                "status": (frontier.get("existing_pilot_chain") or {}).get("status"),
                "scope": (frontier.get("existing_pilot_chain") or {}).get("scope"),
                "relations_ref": (frontier.get("existing_pilot_chain") or {}).get("relations_ref"),
                "relations_sha256": (frontier.get("existing_pilot_chain") or {}).get("relations_sha256"),
                "relation_count": (frontier.get("existing_pilot_chain") or {}).get("relation_count"),
                "relation_statuses": (frontier.get("existing_pilot_chain") or {}).get("relation_statuses"),
                "reason_codes": (frontier.get("existing_pilot_chain") or {}).get("reason_codes"),
                "evidence_kinds": (frontier.get("existing_pilot_chain") or {}).get("evidence_kinds"),
                "declared_alternatives": (frontier.get("existing_pilot_chain") or {}).get("declared_alternatives"),
                "research_frontier": (frontier.get("existing_pilot_chain") or {}).get("research_frontier"),
                "why_not_adopted": (frontier.get("existing_pilot_chain") or {}).get("why_not_adopted"),
                "not_usable_for": (frontier.get("existing_pilot_chain") or {}).get("not_usable_for"),
            },
            "blocking_gates": [
                {
                    "gate": gate.get("gate"),
                    "why_refused": gate.get("why_refused"),
                    "source_ref": gate.get("source_ref"),
                }
                for gate in (frontier.get("blocking_gates") or []) if isinstance(gate, Mapping)
            ],
        },
        "crosswalk_candidate_count": crosswalk.get("candidate_relation_count", 0),
        "crosswalk_binding_audit": crosswalk.get("binding_audit"),
        "used_for_selection": crosswalk_status == "bound",
        "selection_guard": (
            "typed_ssd_iskvw_crosswalk_present"
            if crosswalk_status == "bound" else
            "candidate_ssd_iskvw_crosswalk_selection_remains_archive_only"
            if crosswalk_status == "candidate" else
            "no_typed_ssd_iskvw_crosswalk_selection_remains_archive_only"
        ),
    }


def _order_basis_digest(order_basis: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Compact the order basis for the durable episode.

    The episode records *that* the frontier changed and under which hashes, not
    a fourth copy of every question dossier.  The full evidence stays in the
    compiled foundation and is reachable by ``semantic_hash``.
    """
    if order_basis is None:
        return None
    review = order_basis.get("operator_review")
    review = review if isinstance(review, Mapping) else {}
    frontier = order_basis.get("research_frontier")
    frontier = frontier if isinstance(frontier, Mapping) else {}
    queue = review.get("attestation_queue")
    return {
        "schema": order_basis.get("schema"),
        "semantic_hash": order_basis.get("semantic_hash"),
        "status": order_basis.get("status"),
        "crosswalk_status": order_basis.get("crosswalk_status"),
        "crosswalk_candidate_count": order_basis.get("crosswalk_candidate_count"),
        "used_for_selection": order_basis.get("used_for_selection"),
        "selection_guard": order_basis.get("selection_guard"),
        "inventory": order_basis.get("inventory"),
        "order_summary": order_basis.get("order_summary"),
        "operator_review": {
            "schema": review.get("schema"),
            "status": review.get("status"),
            "asked_count": review.get("asked_count"),
            "deferred_count": review.get("deferred_count"),
            "questions_before_triage": review.get("questions_before_triage"),
            "coverage_of_disputed_bytes": review.get("coverage_of_disputed_bytes"),
            "machine_answerable": review.get("machine_answerable"),
            "selection_effect": review.get("selection_effect"),
            "source_ref": review.get("source_ref"),
            "source_sha256": review.get("source_sha256"),
            "dossier_algorithm": review.get("dossier_algorithm"),
            "evidence_sources": review.get("evidence_sources"),
            "triage": review.get("triage"),
            "attestation_queue_status": review.get("attestation_queue_status"),
            "answers_recorded": review.get("answers_recorded"),
            "attestation_queue_length": len(queue) if isinstance(queue, list) else 0,
            "identity_tiers": review.get("identity_tiers"),
            "index_relation_reality": review.get("index_relation_reality"),
        },
        "crosswalk_binding_audit": order_basis.get("crosswalk_binding_audit"),
        "research_frontier": {
            "status": frontier.get("status"),
            "compiled": frontier.get("compiled"),
            "job_count": frontier.get("job_count"),
            "reason": frontier.get("reason"),
            "dispatch": frontier.get("dispatch"),
            "create_job_invoked": frontier.get("create_job_invoked"),
            "blocking_gates": [
                gate.get("gate")
                for gate in (frontier.get("blocking_gates") or []) if isinstance(gate, Mapping)
            ],
            "existing_pilot_chain": {
                "status": (frontier.get("existing_pilot_chain") or {}).get("status"),
                "relations_sha256": (frontier.get("existing_pilot_chain") or {}).get(
                    "relations_sha256"),
                "relation_count": (frontier.get("existing_pilot_chain") or {}).get(
                    "relation_count"),
                "adopted": False,
            },
        },
    }


def compile_contracurator_exhibition(
    archive_view: Mapping[str, Any],
    *,
    ssd_order_foundation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce three testable theses and mount only a single survivor.

    The winner is intentionally modest: it is an argument about a visible
    archive boundary, rather than an assertion about a person, a style, or an
    artistic identity.  If that boundary is not evidenced, the only valid
    result is ``abstain``.
    """
    try:
        validate_archive_portfolio_view(archive_view)
    except ProductViewError as error:
        raise ContracuratorError("archive_view_invalid:" + str(error)) from error
    view = copy.deepcopy(dict(archive_view))
    order_basis = _order_basis_metadata(ssd_order_foundation)
    items = view["items"]
    if not isinstance(items, list):  # guarded above; retains a local type boundary.
        raise ContracuratorError("archive_view_items_invalid")
    by_id = {str(item["item_id"]): item for item in items if isinstance(item, Mapping)}
    relation_index, typed_relations = _relation_index(view)
    input_hash = _text(view["source"].get("input_hash"), "archive_view.source.input_hash")

    declared = [item for item in items if "declared_work" in item.get("roles", [])]
    observed = [item for item in items if "observed_archive_piece" in item.get("roles", [])]
    practice = [item for item in items if "practice_context" in item.get("roles", [])]
    declared_ids = {str(item["item_id"]) for item in declared}
    observed_refs = [_text(item.get("source_ref"), "observed.source_ref") for item in observed]
    practice_refs = [_text(item.get("source_ref"), "practice.source_ref") for item in practice]

    # Thesis A uses all declared works only when they can each be contextualized
    # by an explicit, typed source relation to another declared work.
    declared_selection: list[dict[str, Any]] = []
    for item in sorted(declared, key=lambda row: str(row["source_ref"])):
        item_id = str(item["item_id"])
        relations = [
            row for row in relation_index.get(item_id, [])
            if row["class"] == "etiqueta"
            and row["epistemic_status"] == "source_label_link"
            and ((row["piece_a"] if row["piece_b"] == item_id else row["piece_b"]) in declared_ids)
        ]
        declared_selection.append(_selection_row(
            item,
            relation_refs=[row["source_ref"] for row in relations],
            reason_codes=["declared_work", "typed_source_label_relation"],
            contextual_reason=(
                "Registro declarado como obra y situado por vínculos fuente de clase "
                "etiqueta hacia otros registros declarados; no se interpreta el nombre."
            ),
        ))
    declared_counter = [
        _counterevidence(
            counter_id="counter:observed-is-not-authorship",
            statement="El campo observado ofrece material visual, pero no declaraciones autorales ni una relación tipada con esta selección.",
            source_refs=observed_refs,
            reason="La observación de fuente no se promueve a identidad, serie ni autoría.",
        ),
        _counterevidence(
            counter_id="counter:labels-do-not-prove-series",
            statement="Los vínculos etiqueta preservan una clasificación de fuente; no prueban una serie ni una intención artística.",
            source_refs=[row["source_ref"] for row in typed_relations if row["class"] == "etiqueta"],
            reason="La tesis se limita a la separación exhibible entre declaración, observación y contexto.",
        ),
    ]
    declared_missing_context = [
        "declared_selection_missing_typed_context"
        if any(not row["relation_refs"] for row in declared_selection) else ""
    ]
    thesis_boundary = _thesis(
        thesis_id="thesis:declared-boundary",
        position=(
            "Este archivo no autoriza una identidad total: convierte la diferencia entre obra "
            "declarada, observación y práctica técnica en la condición misma de la exposición."
        ),
        selection=declared_selection,
        counterevidence=declared_counter,
        name_route_authorship_dependency=False,
        derived_as_independent_work=False,
        extra_rejections=[reason for reason in declared_missing_context if reason],
    )

    # Thesis B intentionally tests, then rejects, the tempting claim that the
    # operational context is artwork.  Its relationships remain links, not a
    # typed derivative relation, and the existing archive contract calls these
    # rows practice context rather than independent work.
    practice_candidates = _ranked(practice, relation_index)[:MIN_SELECTION]
    practice_selection = []
    for item in practice_candidates:
        refs = [row["source_ref"] for row in relation_index.get(str(item["item_id"]), [])]
        practice_selection.append(_selection_row(
            item,
            relation_refs=refs,
            reason_codes=["practice_context", "typed_relation_connectivity"],
            contextual_reason=(
                "Registro de práctica con vínculos de fuente conservados; estos vínculos no se "
                "reclasifican como relación derivada ni como obra."
            ),
        ))
    thesis_practice = _thesis(
        thesis_id="thesis:operation-as-work",
        position="El archivo sería, ante todo, una historia operativa presentada como obra independiente.",
        selection=practice_selection,
        counterevidence=[
            _counterevidence(
                counter_id="counter:practice-is-context",
                statement="La propia vista clasifica estas filas como práctica y contexto, no como obra declarada.",
                source_refs=practice_refs,
                reason="Un vínculo semántico o de etiqueta no sustituye una relación tipada de derivación.",
            ),
        ],
        name_route_authorship_dependency=False,
        derived_as_independent_work=True,
        extra_rejections=["practice_context_is_not_independent_work", "typed_derivation_relation_missing"],
    )

    # Thesis C must expose its own arbitrary point: observed records have no
    # typed relations in the bounded view.  The reference ordering is recorded
    # as a failure condition, never smuggled into a surviving selection.
    observed_candidates = sorted(observed, key=lambda row: str(row["source_ref"]))[:MIN_SELECTION]
    observed_selection = [
        _selection_row(
            item,
            relation_refs=[row["source_ref"] for row in relation_index.get(str(item["item_id"]), [])],
            reason_codes=["observed_archive_piece", "source_ref_order_test"],
            contextual_reason=(
                "Registro observado sin declaración autoral; su inclusión prueba que no hay una "
                "base relacional suficiente para montarlo como identidad."
            ),
        )
        for item in observed_candidates
    ]
    thesis_observed = _thesis(
        thesis_id="thesis:observed-image-identity",
        position="El archivo sería una identidad visual deducible del campo observado.",
        selection=observed_selection,
        counterevidence=[
            _counterevidence(
                counter_id="counter:observed-descriptions-limited",
                statement="Las descripciones observadas no son declaraciones del artista y los registros elegidos carecen de relaciones tipadas en esta vista.",
                source_refs=observed_refs,
                reason="Sin relación contextual, la muestra dependería de un orden de referencias y no de evidencia curatorial.",
            ),
        ],
        name_route_authorship_dependency=True,
        derived_as_independent_work=False,
        extra_rejections=["observed_records_lack_typed_context", "source_ref_order_required"],
    )

    theses = [thesis_boundary, thesis_practice, thesis_observed]
    survivors = [row for row in theses if row["assessment"]["status"] == "survives"]
    survivors.sort(key=lambda row: (
        -row["assessment"]["coherence"],
        -row["assessment"]["coverage"],
        row["assessment"]["evidence_debt"],
        row["thesis_id"],
    ))
    limits = [
        "No infiere autoría, publicación, identidad ni calidad artística.",
        "Los títulos y los source_ref identifican registros; no son evidencia semántica de la tesis.",
        "Los vínculos etiqueta y semántico se conservan como relaciones de fuente, no como series o derivaciones.",
        "La versión alternativa de campo observado queda en abstención: no se monta como exposición.",
        "El episodio es candidato de aprendizaje operativo; training_permitted=false.",
    ]
    if len(survivors) != 1:
        result: dict[str, Any] = {
            "status": "abstain",
            "selected_thesis_id": None,
            "exhibition": None,
            "reason": "no_unique_evidence_bounded_thesis_survives",
            "limits": limits,
        }
    else:
        winner = survivors[0]
        selected_refs = winner["source_refs"]
        excluded = []
        selected_by_ref = {row["source_ref"] for row in winner["selection"]}
        for item in sorted(items, key=lambda row: str(row["source_ref"])):
            source_ref = _text(item.get("source_ref"), "item.source_ref")
            if source_ref in selected_by_ref:
                continue
            roles = set(item.get("roles", []))
            if "observed_archive_piece" in roles:
                reason = "observed_source_record_not_promoted_to_authorial_or_identity_claim"
            elif "practice_context" in roles:
                reason = "practice_context_not_counted_as_independent_work_without_typed_derivation"
            else:
                reason = "outside_surviving_thesis_scope"
            excluded.append({
                "source_ref": source_ref,
                "item_id": _text(item.get("item_id"), "item.item_id"),
                "reason": reason,
            })
        result = {
            "status": "survived",
            "selected_thesis_id": winner["thesis_id"],
            "exhibition": {
                "title": "La diferencia no se aplana",
                "source_refs": selected_refs,
                "selection": copy.deepcopy(winner["selection"]),
                "curatorial_text": (
                    "Esta exposición no convierte las filas visibles en una identidad total. Monta "
                    "ocho registros que la fuente ya declara como obra y conserva sus vínculos de "
                    "etiqueta como contexto, no como una serie inventada. El gesto cultural está en "
                    "no aplanar: lo observado permanece observado y la práctica técnica permanece "
                    "contexto. Lo que este archivo puede hacer, con la evidencia actual, es volver "
                    "esa diferencia una experiencia de lectura sin atribuir autoría ni valor artístico."
                ),
                "why_in": copy.deepcopy(winner["selection"]),
                "why_out": excluded,
                "alternative_version": {
                    "title": "Campo observado sin convertirlo en identidad",
                    "status": "abstain_not_exhibition",
                    "source_refs": thesis_observed["source_refs"],
                    "reason": (
                        "Propone un contra-montaje de registros observados, pero se retira porque la "
                        "selección exigiría orden por source_ref y las observaciones no son declaraciones autorales."
                    ),
                },
            },
            "reason": "one_thesis_survives_by_coherence_coverage_and_lowest_evidence_debt",
            "limits": limits,
        }
    episode = _episode(
        input_hash=input_hash, theses=theses, result=result, limits=limits,
        order_basis=_order_basis_digest(order_basis),
    )
    payload = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "scope": "iskvw_internal_falsifiable_curation",
        "status": result["status"],
        "input": {
            "archive_view_schema": view["schema"],
            "archive_view_hash": _hash(view),
            "source_hash": input_hash,
            "visible_item_count": len(items),
            "source_rescan": False,
            **({"ssd_order_foundation_hash": order_basis["semantic_hash"]} if order_basis else {}),
        },
        "theses": theses,
        "result": result,
        "product_episode": episode,
        "control": {
            "publication": False,
            "submission": False,
            "dispatch": False,
            "database_write": False,
            "training_permitted": False,
            "promotion": "none",
        },
        "provenance": {
            "consumer_of": "mak-archive-portfolio-view-v1",
            "source_ref_required_for_selected": True,
            "filename_is_not_authorship": True,
            "observed_text_is_not_author_statement": True,
            "typed_derivation_required_for_independent_derivative": True,
            "deterministic": True,
            **({"ssd_order_foundation": order_basis} if order_basis else {}),
        },
    }
    validate_contracurator_exhibition(payload)
    return payload


def validate_contracurator_exhibition(payload: Mapping[str, Any]) -> bool:
    """Validate the standalone result without re-reading the archive."""
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ContracuratorError("schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ContracuratorError("algorithm_version_invalid")
    if payload.get("scope") != "iskvw_internal_falsifiable_curation":
        raise ContracuratorError("scope_invalid")
    if payload.get("status") not in {"survived", "abstain"}:
        raise ContracuratorError("status_invalid")
    expected = {"schema", "algorithm_version", "scope", "status", "input", "theses", "result", "product_episode", "control", "provenance"}
    if set(payload) != expected:
        raise ContracuratorError("field_set_invalid")
    input_data = _mapping(payload.get("input"), "input")
    if input_data.get("archive_view_schema") != "mak-archive-portfolio-view-v1" or input_data.get("source_rescan") is not False:
        raise ContracuratorError("input_contract_invalid")
    _text(input_data.get("archive_view_hash"), "input.archive_view_hash")
    _text(input_data.get("source_hash"), "input.source_hash")
    if not isinstance(input_data.get("visible_item_count"), int) or input_data["visible_item_count"] < 0:
        raise ContracuratorError("input_visible_item_count_invalid")
    theses = payload.get("theses")
    if not isinstance(theses, list) or len(theses) != 3:
        raise ContracuratorError("thesis_count_invalid")
    expected_ids = ["thesis:declared-boundary", "thesis:operation-as-work", "thesis:observed-image-identity"]
    if [row.get("thesis_id") if isinstance(row, Mapping) else None for row in theses] != expected_ids:
        raise ContracuratorError("thesis_ids_invalid")
    for row in theses:
        thesis = _mapping(row, "thesis")
        if set(thesis) != {"thesis_id", "position", "source_refs", "selection", "counterevidence", "assessment"}:
            raise ContracuratorError("thesis_fields_invalid")
        selection = thesis.get("selection")
        if not isinstance(selection, list) or len(selection) > MAX_SELECTION:
            raise ContracuratorError("thesis_selection_size_invalid")
        refs = _source_refs(selection, "thesis.selection")
        if thesis.get("source_refs") != refs:
            raise ContracuratorError("thesis_source_refs_invalid")
        for selected in selection:
            selected_row = _mapping(selected, "thesis.selection_row")
            if set(selected_row) != {"source_ref", "item_id", "roles", "relation_refs", "reason_codes", "contextual_reason"}:
                raise ContracuratorError("selection_fields_invalid")
            if not isinstance(selected_row.get("relation_refs"), list) or not isinstance(selected_row.get("reason_codes"), list):
                raise ContracuratorError("selection_lists_invalid")
            _text(selected_row.get("contextual_reason"), "selection.contextual_reason")
        counters = thesis.get("counterevidence")
        if not isinstance(counters, list) or not counters:
            raise ContracuratorError("counterevidence_missing")
        assessment = _mapping(thesis.get("assessment"), "thesis.assessment")
        if assessment.get("status") not in {"survives", "defeated"} or not isinstance(assessment.get("rejection_reasons"), list):
            raise ContracuratorError("thesis_assessment_invalid")
        if len(selection) < MIN_SELECTION and "selection_size_out_of_bounds" not in assessment["rejection_reasons"]:
            raise ContracuratorError("undersized_thesis_must_be_defeated")
    result = _mapping(payload.get("result"), "result")
    if result.get("status") != payload.get("status"):
        raise ContracuratorError("result_status_mismatch")
    survivors = [row for row in theses if row["assessment"]["status"] == "survives"]
    if payload["status"] == "survived":
        if len(survivors) != 1 or result.get("selected_thesis_id") != survivors[0]["thesis_id"]:
            raise ContracuratorError("survivor_invalid")
        exhibition = _mapping(result.get("exhibition"), "result.exhibition")
        refs = exhibition.get("source_refs")
        if refs != survivors[0]["source_refs"] or not MIN_SELECTION <= len(refs) <= MAX_SELECTION:
            raise ContracuratorError("exhibition_selection_invalid")
        if not isinstance(exhibition.get("why_in"), list) or not isinstance(exhibition.get("why_out"), list):
            raise ContracuratorError("exhibition_map_missing")
        if any(not isinstance(row, Mapping) or not row.get("source_ref") for row in exhibition["why_out"]):
            raise ContracuratorError("exhibition_exclusion_source_ref_missing")
    elif result.get("selected_thesis_id") is not None or result.get("exhibition") is not None:
        raise ContracuratorError("abstention_must_not_mount_exhibition")
    control = _mapping(payload.get("control"), "control")
    if control != {"publication": False, "submission": False, "dispatch": False, "database_write": False, "training_permitted": False, "promotion": "none"}:
        raise ContracuratorError("control_invalid")
    provenance = _mapping(payload.get("provenance"), "provenance")
    required_flags = ("source_ref_required_for_selected", "filename_is_not_authorship", "observed_text_is_not_author_statement", "typed_derivation_required_for_independent_derivative", "deterministic")
    if provenance.get("consumer_of") != "mak-archive-portfolio-view-v1" or any(provenance.get(flag) is not True for flag in required_flags):
        raise ContracuratorError("provenance_invalid")
    episode = _mapping(payload.get("product_episode"), "product_episode")
    if episode.get("schema") != EPISODE_SCHEMA or episode.get("result_status") != payload["status"]:
        raise ContracuratorError("product_episode_invalid")
    return True


def record_contracurator_episode(
    store: LearningStore,
    exhibition: Mapping[str, Any],
    *,
    project_id: str,
    code_commit: str = "",
    tool_versions: Mapping[str, Any] | None = None,
) -> str:
    """Append the prepared episode to an existing Project IR record.

    This is intentionally not called by the Hub.  The caller names the
    already-existing project and supplies code provenance when it wants the
    source snapshot in the ledger's native provenance fields.
    """
    validate_contracurator_exhibition(exhibition)
    projection = _mapping(exhibition["product_episode"].get("record_episode_projection"), "record_episode_projection")
    project_id = _text(project_id, "project_id")
    source_hash = _text(exhibition["input"].get("source_hash"), "input.source_hash")
    versions = dict(tool_versions or {})
    use_versioned_provenance = bool(code_commit or versions)
    if use_versioned_provenance and (not code_commit or not versions):
        raise ContracuratorError("code_provenance_incomplete")
    return store.record_episode(
        project_id=project_id,
        objective=projection["objective"],
        phase=projection["phase"],
        action=projection["action"],
        observation=projection["observation"],
        outcome=projection["outcome"],
        validation=projection["validation"],
        status=projection["status"],
        provider=projection["provider"],
        model=projection["model"],
        cost=projection["cost"],
        parent_episode_id=projection["parent_episode_id"],
        episode_id=projection["episode_id"],
        source_snapshot_hash=source_hash if use_versioned_provenance else "",
        code_commit=code_commit,
        tool_versions=versions,
    )


__all__ = [
    "ALGORITHM_VERSION", "ContracuratorError", "EPISODE_SCHEMA", "MAX_SELECTION",
    "MIN_SELECTION", "SCHEMA", "compile_contracurator_exhibition",
    "record_contracurator_episode", "validate_contracurator_exhibition",
]
