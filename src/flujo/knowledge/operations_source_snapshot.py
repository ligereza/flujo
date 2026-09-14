"""Logical, read-only snapshot of operational surfaces for parity diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import hashlib, json, re

from ._contract_helpers import nonnegative_int as _int, required_mapping as _map, required_text as _text
from .operations_read_only_map import ENDPOINTS, validate_operations_read_only_map

SCHEMA = "mak-operations-source-snapshot-v1"
ALGORITHM_VERSION = "operations-source-snapshot-1"
_CONTROL = {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False}
_BOUNDARY = {"contract_parity_is_not_snapshot_parity": True, "local_counts_may_differ": True, "semantic_claim": False, "learning_demonstrated": False}
def _logical_ref(value: Any, field: str) -> str:
    value = _text(value, field)
    if value.startswith("/") or "/home/" in value or "\\" in value: raise ValueError(f"{field}_absolute_or_host_path")
    return value
def _endpoint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not value.startswith("/api/") or "\\" in value or "//" in value: raise ValueError(f"{field}_invalid")
    return value
def _fingerprint(entry: Mapping[str, Any]) -> str:
    safe = {key: entry.get(key) for key in ("endpoint", "source_schema", "counts", "source_hash_or_ref")}
    return "sha256:" + hashlib.sha256(json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def build_operations_source_snapshot(operations_map: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    operations_map = _map(operations_map, "operations_map"); validate_operations_read_only_map(operations_map); entries = []
    for source in operations_map["entries"]:
        entries.append({"endpoint": _endpoint(source["endpoint"], "entry.endpoint"), "source_schema": _logical_ref(source["source_schema"], "entry.source_schema"), "source_fingerprint": _fingerprint(source), "counts": {str(key): _int(value, f"entry.counts.{key}") for key, value in source["counts"].items()}, "source_ref": _logical_ref(source["source_hash_or_ref"], "entry.source_ref")})
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "scope": "read_only", "source_policy": "logical_refs_only", "entries": entries, "boundary": dict(_BOUNDARY), "control": dict(_CONTROL), "next_action": "compare_contract_parity_separately_from_local_snapshot_differences"}; validate_operations_source_snapshot(result); return result
def validate_operations_source_snapshot(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("operations_source_snapshot_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "scope", "source_policy", "entries", "boundary", "control", "next_action"}
    if set(payload) != expected: raise ValueError("operations_source_snapshot_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    if payload["scope"] != "read_only" or payload["source_policy"] != "logical_refs_only": raise ValueError("operations_source_snapshot_scope_invalid")
    entries = payload["entries"]
    if not isinstance(entries, list) or [item.get("endpoint") for item in entries if isinstance(item, Mapping)] != ENDPOINTS: raise ValueError("operations_source_snapshot_endpoint_order_invalid")
    for item in entries:
        item = _map(item, "entry")
        if set(item) != {"endpoint", "source_schema", "source_fingerprint", "counts", "source_ref"}: raise ValueError("operations_source_snapshot_entry_shape_invalid")
        _endpoint(item["endpoint"], "entry.endpoint"); _logical_ref(item["source_schema"], "entry.source_schema"); _logical_ref(item["source_ref"], "entry.source_ref")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", item["source_fingerprint"]): raise ValueError("operations_source_snapshot_fingerprint_invalid")
        for key, value in _map(item["counts"], "entry.counts").items(): _text(key, "entry.count_key"); _int(value, f"entry.counts.{key}")
    if payload["boundary"] != _BOUNDARY or payload["control"] != _CONTROL: raise ValueError("operations_source_snapshot_boundary_or_control_invalid")
    _text(payload["next_action"], "next_action"); return True
__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_operations_source_snapshot", "validate_operations_source_snapshot"]
