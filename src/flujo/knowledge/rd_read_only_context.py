"""Bounded read-only context for the RD projection and its candidate joins."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import nonnegative_int as _int, required_mapping as _mapping, required_text as _text, without_ok as _without_ok

SCHEMA = "mak-rd-read-only-context-v1"
ALGORITHM_VERSION = "rd-read-only-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False}


def build_rd_read_only_context(summary: Mapping[str, Any], topics: Mapping[str, Any], crosswalk: Mapping[str, Any], relations: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    summary = _without_ok(_mapping(summary, "summary")); topics = _without_ok(_mapping(topics, "topics")); crosswalk = _without_ok(_mapping(crosswalk, "crosswalk")); relations = _without_ok(_mapping(relations, "relations"))
    database = _mapping(topics.get("database"), "topics.database"); source_crosswalk = _mapping(summary.get("crosswalk"), "summary.crosswalk")
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "source": {"summary_schema": _text(summary.get("schema"), "summary.schema"), "canonical_projection": _text(summary.get("canonical_projection"), "summary.canonical_projection"), "legacy_runtime_boundary": _text(summary.get("legacy_runtime_boundary"), "summary.legacy_runtime_boundary"), "crosswalk_status": _text(source_crosswalk.get("status"), "summary.crosswalk.status")}, "topics": {"schema": _text(topics.get("schema"), "topics.schema"), "read_only": topics.get("read_only") is True, "mutation": _text(topics.get("mutation"), "topics.mutation"), "topic_count": len(topics.get("topics", [])) if isinstance(topics.get("topics"), list) else -1, "canonical_rows": _int(database.get("canonical_rows"), "topics.database.canonical_rows"), "runtime_rows": _int(database.get("runtime_rows"), "topics.database.runtime_rows")}, "crosswalk": {"schema": _text(crosswalk.get("schema"), "crosswalk.schema"), "status": _text(crosswalk.get("status"), "crosswalk.status"), "mutation": _text(crosswalk.get("mutation"), "crosswalk.mutation"), "identity_join": _text(crosswalk.get("identity_join"), "crosswalk.identity_join"), "entity_count": len(crosswalk.get("entities", [])) if isinstance(crosswalk.get("entities"), list) else -1}, "relations": {"schema": _text(relations.get("schema"), "relations.schema"), "status": _text(relations.get("status"), "relations.status"), "mutation": _text(relations.get("mutation"), "relations.mutation"), "join_rule": _text(relations.get("join_rule"), "relations.join_rule"), "producer_count": len(relations.get("producers", [])) if isinstance(relations.get("producers"), list) else -1, "venue_count": len(relations.get("venues", [])) if isinstance(relations.get("venues"), list) else -1, "relation_count": len(relations.get("relations", [])) if isinstance(relations.get("relations"), list) else -1}, "boundary": {"crosswalk_is_review_only": crosswalk.get("status") == "review_only" and source_crosswalk.get("status") == "review_only", "candidate_graph_is_unconfirmed": relations.get("status") == "read_only_candidate_graph", "identity_requires_explicit_provenance": crosswalk.get("identity_join") == "explicit_provenance_only" and relations.get("join_rule") == "explicit_venue_id_or_provenance_only", "counts_are_checkout_local": True, "semantic_claim": False}, "control": dict(_CONTROL), "next_action": "human_review_rd_projection_and_candidate_joins_before_any_crosswalk_or_relation_decision"}
    validate_rd_read_only_context(result); return result


def validate_rd_read_only_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("rd_context_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "source", "topics", "crosswalk", "relations", "boundary", "control", "next_action"}
    if set(payload) != expected: raise ValueError("rd_context_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    source = payload["source"]
    if set(source) != {"summary_schema", "canonical_projection", "legacy_runtime_boundary", "crosswalk_status"} or source["crosswalk_status"] != "review_only": raise ValueError("rd_context_source_invalid")
    for field in source: _text(source[field], f"source.{field}")
    topics = payload["topics"]
    if set(topics) != {"schema", "read_only", "mutation", "topic_count", "canonical_rows", "runtime_rows"} or topics["read_only"] is not True or topics["mutation"] != "disabled": raise ValueError("rd_context_topics_invalid")
    _text(topics["schema"], "topics.schema")
    for field in ("topic_count", "canonical_rows", "runtime_rows"): _int(topics[field], f"topics.{field}")
    crosswalk = payload["crosswalk"]
    if set(crosswalk) != {"schema", "status", "mutation", "identity_join", "entity_count"} or crosswalk["status"] != "review_only" or crosswalk["mutation"] != "disabled" or crosswalk["identity_join"] != "explicit_provenance_only": raise ValueError("rd_context_crosswalk_invalid")
    for field in ("schema", "status", "mutation", "identity_join"): _text(crosswalk[field], f"crosswalk.{field}")
    _int(crosswalk["entity_count"], "crosswalk.entity_count")
    relations = payload["relations"]
    if set(relations) != {"schema", "status", "mutation", "join_rule", "producer_count", "venue_count", "relation_count"} or relations["status"] != "read_only_candidate_graph" or relations["mutation"] != "disabled" or relations["join_rule"] != "explicit_venue_id_or_provenance_only": raise ValueError("rd_context_relations_invalid")
    for field in ("schema", "status", "mutation", "join_rule"): _text(relations[field], f"relations.{field}")
    for field in ("producer_count", "venue_count", "relation_count"): _int(relations[field], f"relations.{field}")
    if payload["boundary"] != {"crosswalk_is_review_only": True, "candidate_graph_is_unconfirmed": True, "identity_requires_explicit_provenance": True, "counts_are_checkout_local": True, "semantic_claim": False}: raise ValueError("rd_context_boundary_invalid")
    if payload["control"] != _CONTROL: raise ValueError("rd_context_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_rd_read_only_context", "validate_rd_read_only_context"]
