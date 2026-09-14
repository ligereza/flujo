"""Project Vigia discoveries into bounded, non-dispatched capture plans.

Vigia discovers listings; ``research_source_capture.capture_one`` owns the
capture boundary.  This bridge preserves that separation: it normalizes and
deduplicates URLs, asks the existing capture consumer for a *plan* only, and
never fetches, persists or dispatches anything.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Callable
from urllib.parse import urlsplit

from ._contract_helpers import sha256_ref as _hash, stable_json

from tools.research_source_capture import capture_one
from tools.source_pipeline import canonical_url


SCHEMA = "flujo-vigia-capture-plans-v1"
ALGORITHM_VERSION = "vigia-to-bounded-capture-plan-1"
SOURCE_CONTRACT = "vigia.correr.nuevos"
RECEIPT_SCHEMA = "flujo-vigia-capture-receipts-v1"
RECEIPT_ALGORITHM_VERSION = "vigia-capture-plan-to-receipt-1"
_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "source_contract", "input_hash", "root",
    "backend", "max_plans", "plans", "skipped", "controls",
    "reconciliation", "provenance",
}
_PLAN_FIELDS = {
    "plan_id", "url", "source_ids", "item_hashes", "titles",
    "capture_plan", "dispatch", "provenance",
}
_SKIPPED_FIELDS = {"source_id", "item_hash", "title", "url", "reason"}
_RECEIPT_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "source_plan_schema", "source_plan_hash",
    "root", "backend", "max_captures", "receipts", "skipped", "controls",
    "reconciliation", "provenance",
}
_RECEIPT_FIELDS = {
    "plan_id", "url", "source_ids", "item_hashes", "titles", "status",
    "capture_id", "source_id", "text_path", "error", "provenance",
}
_RECEIPT_SKIPPED_FIELDS = {"plan_id", "url", "reason"}


class VigiaCaptureBridgeError(ValueError):
    """Raised for malformed Vigia discoveries or capture-plan output."""


def _text(value: Any, field: str, *, required: bool = True, limit: int = 1000) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise VigiaCaptureBridgeError(f"{field}_must_be_string")
    value = value.strip()
    if required and not value:
        raise VigiaCaptureBridgeError(f"{field}_required")
    if len(value) > limit:
        raise VigiaCaptureBridgeError(f"{field}_too_long")
    return value


def _canonical_url(value: Any) -> str:
    url = _text(value, "url", limit=4000)
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VigiaCaptureBridgeError("url_invalid")
    # Keep URL normalization aligned with the standalone capture consumer.
    normalized = canonical_url(url)
    if not normalized:
        raise VigiaCaptureBridgeError("url_invalid")
    return normalized


def _candidate_rows(discoveries: Any) -> list[dict[str, str]]:
    if isinstance(discoveries, Mapping):
        discoveries = discoveries.get("results")
    if not isinstance(discoveries, list):
        raise VigiaCaptureBridgeError("vigia_results_must_be_list")
    rows: list[dict[str, str]] = []
    for source_index, source in enumerate(discoveries):
        if not isinstance(source, Mapping):
            raise VigiaCaptureBridgeError(f"source[{source_index}]_must_be_object")
        source_id = _text(source.get("id"), f"source[{source_index}].id", limit=240)
        listings = source.get("nuevos")
        if not isinstance(listings, list):
            raise VigiaCaptureBridgeError(f"source[{source_index}].nuevos_must_be_list")
        for item_index, item in enumerate(listings):
            if not isinstance(item, Mapping):
                raise VigiaCaptureBridgeError(f"source[{source_index}].nuevos[{item_index}]_must_be_object")
            item_hash = _text(item.get("h"), "item_hash", limit=300)
            title = _text(item.get("titulo", item.get("title", "")), "title", required=False, limit=1000)
            raw_url = item.get("url")
            if not isinstance(raw_url, str) or not raw_url.strip():
                rows.append({"source_id": source_id, "item_hash": item_hash, "title": title, "url": "", "reason": "url_missing"})
                continue
            try:
                url = _canonical_url(raw_url)
            except VigiaCaptureBridgeError as exc:
                rows.append({"source_id": source_id, "item_hash": item_hash, "title": title, "url": str(raw_url), "reason": str(exc)})
                continue
            rows.append({"source_id": source_id, "item_hash": item_hash, "title": title, "url": url})
    return rows


def _semantic_input(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {"source_contract": SOURCE_CONTRACT, "rows": sorted(rows, key=lambda row: (row["url"], row["source_id"], row["item_hash"], row["title"], row.get("reason", "")))}


def _skipped(row: Mapping[str, str]) -> dict[str, str]:
    return {field: str(row.get(field, "")) for field in ("source_id", "item_hash", "title", "url", "reason")}


def _validate_capture_plan(plan: Mapping[str, Any]) -> None:
    if plan.get("decision") != "plan" or plan.get("network_called") is not False:
        raise VigiaCaptureBridgeError("capture_consumer_returned_non_plan")
    if not isinstance(plan.get("url"), str) or not plan.get("url"):
        raise VigiaCaptureBridgeError("capture_plan_url_missing")
    if not isinstance(plan.get("root"), str) or not plan.get("root"):
        raise VigiaCaptureBridgeError("capture_plan_root_missing")


def _build_plan(
    rows: list[dict[str, str]],
    *,
    root: str,
    backend: str,
    capture_planner: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    url = rows[0]["url"]
    source_ids = sorted({row["source_id"] for row in rows})
    item_hashes = sorted({row["item_hash"] for row in rows})
    titles = sorted({row["title"] for row in rows if row["title"]})
    plan_id = "capture-plan:" + hashlib.sha256(stable_json({"url": url}).encode("utf-8")).hexdigest()
    capture_plan = capture_planner(url, root=root, backend=backend, record=False)
    if not isinstance(capture_plan, Mapping):
        raise VigiaCaptureBridgeError("capture_plan_not_object")
    _validate_capture_plan(capture_plan)
    return {
        "plan_id": plan_id,
        "url": url,
        "source_ids": source_ids,
        "item_hashes": item_hashes,
        "titles": titles,
        "capture_plan": dict(capture_plan),
        "dispatch": False,
        "provenance": {
            "source_contract": SOURCE_CONTRACT,
            "candidate_count_collapsed": len(rows),
            "promotion": "none",
            "network_called": False,
        },
    }


def build_vigia_capture_plans(
    discoveries: Any,
    *,
    root: str,
    backend: str = "auto",
    max_plans: int = 20,
    capture_planner: Callable[..., dict[str, Any]] = capture_one,
) -> dict[str, Any]:
    """Build bounded plans from Vigia ``nuevos`` rows without side effects."""
    if not isinstance(root, str) or not root.strip():
        raise VigiaCaptureBridgeError("root_required")
    if not isinstance(backend, str) or not backend.strip():
        raise VigiaCaptureBridgeError("backend_required")
    if isinstance(max_plans, bool) or not isinstance(max_plans, int) or max_plans < 1:
        raise VigiaCaptureBridgeError("max_plans_invalid")
    rows = _candidate_rows(discoveries)
    valid = [row for row in rows if row.get("url") and not row.get("reason")]
    invalid = [_skipped(row) for row in rows if not row.get("url") or row.get("reason")]
    groups: dict[str, list[dict[str, str]]] = {}
    for row in valid:
        groups.setdefault(row["url"], []).append(row)
    urls = sorted(groups)
    bounded_urls = urls[:max_plans]
    for url in urls[max_plans:]:
        for row in groups[url]:
            invalid.append(_skipped({**row, "reason": "max_plans_reached"}))
    plans = [_build_plan(groups[url], root=root, backend=backend, capture_planner=capture_planner) for url in bounded_urls]
    plans.sort(key=lambda row: row["plan_id"])
    invalid.sort(key=lambda row: (row["reason"], row["url"], row["source_id"], row["item_hash"]))
    semantic_input = _semantic_input(rows)
    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "source_contract": SOURCE_CONTRACT,
        "input_hash": _hash(semantic_input),
        "root": root,
        "backend": backend,
        "max_plans": max_plans,
        "plans": plans,
        "skipped": invalid,
        "controls": {"network_called": False, "database_write": False, "dispatch": False, "promotion": "none"},
        "reconciliation": {
            "candidate_count": len(rows),
            "unique_url_count": len(urls),
            "planned_count": len(plans),
            "skipped_count": len(invalid),
            "deduplicated_count": len(valid) - len(urls),
            "bounded": True,
            "loss": 0,
            "deterministic_order": True,
        },
        "provenance": {"source_contract": SOURCE_CONTRACT, "capture_consumer": "tools/research_source_capture.py:capture_one", "promotion": "none", "deterministic": True},
    }


def validate_vigia_capture_plans(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
        return False
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("source_contract") != SOURCE_CONTRACT:
        return False
    if not isinstance(payload.get("input_hash"), str) or not payload["input_hash"].startswith("sha256:"):
        return False
    plans = payload.get("plans")
    skipped = payload.get("skipped")
    if not isinstance(plans, list) or not isinstance(skipped, list):
        return False
    if plans != sorted(plans, key=lambda row: row.get("plan_id", "")):
        return False
    ids: set[str] = set()
    urls: set[str] = set()
    for row in plans:
        if not isinstance(row, Mapping) or set(row) != _PLAN_FIELDS:
            return False
        if not isinstance(row.get("plan_id"), str) or row["plan_id"] in ids or row.get("url") in urls:
            return False
        ids.add(row["plan_id"]); urls.add(row.get("url"))
        if row.get("dispatch") is not False or not isinstance(row.get("source_ids"), list) or row["source_ids"] != sorted(set(row["source_ids"])):
            return False
        if not isinstance(row.get("item_hashes"), list) or row["item_hashes"] != sorted(set(row["item_hashes"])):
            return False
        if not isinstance(row.get("titles"), list) or row["titles"] != sorted(set(row["titles"])):
            return False
        capture_plan = row.get("capture_plan")
        if not isinstance(capture_plan, Mapping) or capture_plan.get("decision") != "plan" or capture_plan.get("network_called") is not False or capture_plan.get("url") != row.get("url"):
            return False
        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping) or provenance.get("promotion") != "none":
            return False
    skipped_keys = []
    for row in skipped:
        if not isinstance(row, Mapping) or set(row) != _SKIPPED_FIELDS:
            return False
        if not row.get("source_id") or not row.get("item_hash") or not row.get("reason"):
            return False
        skipped_keys.append((row["reason"], row["url"], row["source_id"], row["item_hash"]))
    if skipped_keys != sorted(skipped_keys):
        return False
    controls = payload.get("controls")
    if not isinstance(controls, Mapping) or controls != {"network_called": False, "database_write": False, "dispatch": False, "promotion": "none"}:
        return False
    recon = payload.get("reconciliation")
    if not isinstance(recon, Mapping) or recon.get("planned_count") != len(plans) or recon.get("skipped_count") != len(skipped) or recon.get("loss") != 0 or recon.get("deterministic_order") is not True:
        return False
    return True


def _receipt_row(
    plan: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = result.get("receipt")
    capture_info = result.get("capture")
    if not isinstance(capture_info, Mapping):
        capture_info = {}
    if not isinstance(receipt, Mapping):
        status = "abstained" if result.get("decision") == "abstain" else "failed"
        return {
            "plan_id": plan["plan_id"],
            "url": plan["url"],
            "source_ids": list(plan["source_ids"]),
            "item_hashes": list(plan["item_hashes"]),
            "titles": list(plan["titles"]),
            "status": status,
            "capture_id": "",
            "source_id": "",
            "text_path": "",
            "error": str(result.get("reason") or capture_info.get("error") or "capture_receipt_missing"),
            "provenance": {
                "source_plan_id": plan["plan_id"],
                "network_called": result.get("network_called") is True,
                "promotion": "none",
            },
        }
    status = str(receipt.get("status") or capture_info.get("status") or "failed")
    if status not in {"captured", "failed"}:
        status = "failed"
    return {
        "plan_id": plan["plan_id"],
        "url": plan["url"],
        "source_ids": list(plan["source_ids"]),
        "item_hashes": list(plan["item_hashes"]),
        "titles": list(plan["titles"]),
        "status": status,
        "capture_id": str(receipt.get("capture_id") or ""),
        "source_id": str(receipt.get("source_id") or ""),
        "text_path": str(receipt.get("text_path") or ""),
        "error": str(capture_info.get("error") or ""),
        "provenance": {
            "source_plan_id": plan["plan_id"],
            "network_called": result.get("network_called") is True,
            "promotion": "none",
        },
    }


def capture_vigia_plans(
    plan_payload: Mapping[str, Any],
    *,
    capture_executor: Callable[..., dict[str, Any]] = capture_one,
    max_captures: int | None = None,
) -> dict[str, Any]:
    """Execute an already validated plan through the existing capture gate.

    This is intentionally a separate, explicit operation from
    :func:`build_vigia_capture_plans`.  It is the only bridge operation that
    may call ``capture_one(record=True)``.  The caller must opt into this
    function (the CLI requires ``--record``); tests and integrations can inject
    a capture executor without network access.
    """
    if not isinstance(plan_payload, Mapping) or not validate_vigia_capture_plans(plan_payload):
        raise VigiaCaptureBridgeError("capture_plan_invalid")
    plans = list(plan_payload["plans"])
    if max_captures is None:
        max_captures = len(plans) if plans else 1
    if isinstance(max_captures, bool) or not isinstance(max_captures, int) or max_captures < 1:
        raise VigiaCaptureBridgeError("max_captures_invalid")
    bounded = plans[:max_captures]
    skipped = [
        {"plan_id": plan["plan_id"], "url": plan["url"], "reason": "max_captures_reached"}
        for plan in plans[max_captures:]
    ]
    receipts: list[dict[str, Any]] = []
    network_called = False
    database_write = False
    for plan in bounded:
        capture_plan = plan["capture_plan"]
        try:
            result = capture_executor(
                plan["url"],
                root=capture_plan["root"],
                backend=capture_plan.get("backend", plan_payload["backend"]),
                record=True,
            )
        except (OSError, ValueError, TypeError) as exc:
            result = {"decision": "error", "reason": f"capture_executor:{exc}", "network_called": False}
        if not isinstance(result, Mapping):
            result = {"decision": "error", "reason": "capture_executor_non_object", "network_called": False}
        network_called = network_called or result.get("network_called") is True
        database_write = database_write or isinstance(result.get("receipt"), Mapping)
        receipts.append(_receipt_row(plan, result))
    receipts.sort(key=lambda row: row["plan_id"])
    skipped.sort(key=lambda row: (row["plan_id"], row["url"], row["reason"]))
    captured_count = sum(row["status"] == "captured" for row in receipts)
    failed_count = sum(row["status"] != "captured" for row in receipts)
    return {
        "schema": RECEIPT_SCHEMA,
        "algorithm_version": RECEIPT_ALGORITHM_VERSION,
        "source_plan_schema": SCHEMA,
        "source_plan_hash": plan_payload["input_hash"],
        "root": plan_payload["root"],
        "backend": plan_payload["backend"],
        "max_captures": max_captures,
        "receipts": receipts,
        "skipped": skipped,
        "controls": {
            "network_called": network_called,
            "database_write": database_write,
            "dispatch": False,
            "promotion": "none",
        },
        "reconciliation": {
            "planned_count": len(plans),
            "attempted_count": len(receipts),
            "captured_count": captured_count,
            "failed_count": failed_count,
            "skipped_count": len(skipped),
            "loss": 0,
            "deterministic_order": True,
            "receipt_ids_unique": len({row["capture_id"] for row in receipts if row["capture_id"]}) == captured_count,
        },
        "provenance": {
            "source_plan_hash": plan_payload["input_hash"],
            "capture_consumer": "tools/research_source_capture.py:capture_one",
            "record_explicit": True,
            "promotion": "none",
        },
    }


def validate_vigia_capture_receipts(
    plan_payload: Mapping[str, Any],
    receipt_payload: Mapping[str, Any],
) -> bool:
    """Strictly validate receipts against their exact source plan."""
    if not isinstance(plan_payload, Mapping) or not validate_vigia_capture_plans(plan_payload):
        return False
    if not isinstance(receipt_payload, Mapping) or set(receipt_payload) != _RECEIPT_TOP_LEVEL_FIELDS:
        return False
    if receipt_payload.get("schema") != RECEIPT_SCHEMA or receipt_payload.get("algorithm_version") != RECEIPT_ALGORITHM_VERSION:
        return False
    if receipt_payload.get("source_plan_schema") != SCHEMA or receipt_payload.get("source_plan_hash") != plan_payload.get("input_hash"):
        return False
    if receipt_payload.get("root") != plan_payload.get("root") or receipt_payload.get("backend") != plan_payload.get("backend"):
        return False
    max_captures = receipt_payload.get("max_captures")
    if isinstance(max_captures, bool) or not isinstance(max_captures, int) or max_captures < 1:
        return False
    receipts = receipt_payload.get("receipts")
    skipped = receipt_payload.get("skipped")
    if not isinstance(receipts, list) or not isinstance(skipped, list):
        return False
    if receipts != sorted(receipts, key=lambda row: row.get("plan_id", "")):
        return False
    plan_by_id = {row["plan_id"]: row for row in plan_payload["plans"]}
    seen_plans: set[str] = set()
    seen_capture_ids: set[str] = set()
    for row in receipts:
        if not isinstance(row, Mapping) or set(row) != _RECEIPT_FIELDS:
            return False
        plan_id = row.get("plan_id")
        if not isinstance(plan_id, str) or plan_id not in plan_by_id or plan_id in seen_plans:
            return False
        seen_plans.add(plan_id)
        plan = plan_by_id[plan_id]
        if row.get("url") != plan["url"] or row.get("source_ids") != plan["source_ids"] or row.get("item_hashes") != plan["item_hashes"] or row.get("titles") != plan["titles"]:
            return False
        if row.get("status") not in {"captured", "failed", "abstained"}:
            return False
        for key in ("capture_id", "source_id", "text_path", "error"):
            if not isinstance(row.get(key), str):
                return False
        if row["status"] == "captured":
            if not row["capture_id"] or not row["source_id"]:
                return False
            if row["capture_id"] in seen_capture_ids:
                return False
            seen_capture_ids.add(row["capture_id"])
        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping) or provenance.get("source_plan_id") != plan_id or provenance.get("promotion") != "none":
            return False
    skipped_keys = []
    for row in skipped:
        if not isinstance(row, Mapping) or set(row) != _RECEIPT_SKIPPED_FIELDS:
            return False
        if row.get("plan_id") not in plan_by_id or row.get("plan_id") in seen_plans or not isinstance(row.get("url"), str) or not isinstance(row.get("reason"), str) or not row["reason"]:
            return False
        if row["url"] != plan_by_id[row["plan_id"]]["url"]:
            return False
        skipped_keys.append((row["plan_id"], row["url"], row["reason"]))
    if skipped_keys != sorted(skipped_keys):
        return False
    expected_receipt_plans = {row["plan_id"] for row in plan_payload["plans"][:max_captures]}
    expected_skipped_plans = {row["plan_id"] for row in plan_payload["plans"][max_captures:]}
    if set(seen_plans) != expected_receipt_plans or {row["plan_id"] for row in skipped} != expected_skipped_plans:
        return False
    controls = receipt_payload.get("controls")
    if not isinstance(controls, Mapping) or set(controls) != {
        "network_called", "database_write", "dispatch", "promotion",
    } or not isinstance(controls.get("network_called"), bool) or not isinstance(
        controls.get("database_write"), bool
    ) or controls.get("dispatch") is not False or controls.get("promotion") != "none":
        return False
    provenance = receipt_payload.get("provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != {
        "source_plan_hash", "capture_consumer", "record_explicit", "promotion",
    } or provenance.get("source_plan_hash") != plan_payload.get("input_hash") or provenance.get(
        "capture_consumer"
    ) != "tools/research_source_capture.py:capture_one" or provenance.get("record_explicit") is not True or provenance.get(
        "promotion"
    ) != "none":
        return False
    reconciliation = receipt_payload.get("reconciliation")
    if not isinstance(reconciliation, Mapping):
        return False
    if reconciliation.get("planned_count") != len(plan_payload["plans"]):
        return False
    if reconciliation.get("attempted_count") != len(receipts) or reconciliation.get("skipped_count") != len(skipped) or reconciliation.get("loss") != 0 or reconciliation.get("deterministic_order") is not True:
        return False
    if reconciliation.get("captured_count") != len(seen_capture_ids):
        return False
    if reconciliation.get("failed_count") != sum(row["status"] != "captured" for row in receipts):
        return False
    return True


def compile_capture_plans(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for the public bridge."""
    return build_vigia_capture_plans(*args, **kwargs)
