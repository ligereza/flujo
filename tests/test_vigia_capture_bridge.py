from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.flujo.knowledge.vigia_capture_bridge import (
    RECEIPT_SCHEMA,
    SCHEMA,
    VigiaCaptureBridgeError,
    build_vigia_capture_plans,
    capture_vigia_plans,
    stable_json,
    validate_vigia_capture_plans,
    validate_vigia_capture_receipts,
)
from tools.compile_vigia_capture_plans import main


def _discoveries() -> list[dict]:
    return [{
        "id": "fondos",
        "nuevos": [
            {"h": "b", "titulo": "Residencia B", "url": "https://example.test/call"},
            {"h": "a", "titulo": "Residencia A", "url": "https://example.test/call"},
            {"h": "bad", "titulo": "Sin URL"},
        ],
    }]


def _planner(url: str, *, root: str, backend: str, record: bool) -> dict:
    assert record is False
    return {
        "schema": "mak-source-capture-gate-v1",
        "decision": "plan",
        "url": url,
        "backend": backend,
        "root": root,
        "available_backends": ["fixture"],
        "network_called": False,
        "next_action": "record",
    }


def test_deduplicates_url_preserves_all_vigia_provenance_and_no_network() -> None:
    payload = build_vigia_capture_plans(_discoveries(), root="/tmp/captures", capture_planner=_planner)
    assert payload["schema"] == SCHEMA
    assert len(payload["plans"]) == 1
    plan = payload["plans"][0]
    assert plan["source_ids"] == ["fondos"]
    assert plan["item_hashes"] == ["a", "b"]
    assert plan["titles"] == ["Residencia A", "Residencia B"]
    assert plan["dispatch"] is False
    assert payload["controls"] == {"network_called": False, "database_write": False, "dispatch": False, "promotion": "none"}
    assert payload["reconciliation"]["deduplicated_count"] == 1
    assert len(payload["skipped"]) == 1
    assert validate_vigia_capture_plans(payload) is True


def test_invalid_urls_and_plan_limit_are_explicit_skips() -> None:
    rows = [{"id": "source", "nuevos": [
        {"h": "one", "titulo": "One", "url": "https://example.test/one"},
        {"h": "two", "titulo": "Two", "url": "https://example.test/two"},
        {"h": "three", "titulo": "Three", "url": "ftp://example.test/three"},
    ]}]
    payload = build_vigia_capture_plans(rows, root="/tmp/captures", max_plans=1, capture_planner=_planner)
    assert len(payload["plans"]) == 1
    assert {row["reason"] for row in payload["skipped"]} == {"max_plans_reached", "url_invalid"}
    assert validate_vigia_capture_plans(payload) is True


def test_reordering_is_byte_deterministic() -> None:
    first = build_vigia_capture_plans(_discoveries(), root="/tmp/captures", capture_planner=_planner)
    reordered = [{"id": "fondos", "nuevos": list(reversed(_discoveries()[0]["nuevos"]))}]
    second = build_vigia_capture_plans(reordered, root="/tmp/captures", capture_planner=_planner)
    assert stable_json(first) == stable_json(second)


def test_malformed_input_and_tampering_fail_closed() -> None:
    with pytest.raises(VigiaCaptureBridgeError):
        build_vigia_capture_plans({"wrong": []}, root="/tmp/captures", capture_planner=_planner)
    payload = build_vigia_capture_plans(_discoveries(), root="/tmp/captures", capture_planner=_planner)
    tampered = copy.deepcopy(payload)
    tampered["plans"][0]["dispatch"] = True
    assert validate_vigia_capture_plans(tampered) is False


def test_cli_file_to_file_is_read_only_plan(tmp_path: Path) -> None:
    source = tmp_path / "vigia.json"
    output = tmp_path / "plans.json"
    source.write_text(json.dumps(_discoveries()), encoding="utf-8")
    assert main(["--input", str(source), "--root", str(tmp_path / "captures"), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA
    assert payload["controls"]["network_called"] is False
    assert validate_vigia_capture_plans(payload) is True


def _executor(url: str, *, root: str, backend: str, record: bool) -> dict:
    assert record is True
    return {
        "schema": "mak-source-capture-gate-v1",
        "decision": "record",
        "url": url,
        "network_called": True,
        "capture": {"status": "captured", "used_backend": backend, "error": ""},
        "receipt": {
            "capture_id": "capture:" + url.rsplit("/", 1)[-1],
            "source_id": "source:" + url.rsplit("/", 1)[-1],
            "text_path": str(Path(root) / "captures" / "text.txt"),
            "status": "captured",
            "url": url,
        },
    }


def test_explicit_capture_mode_persists_plan_provenance_without_dispatch() -> None:
    plans = build_vigia_capture_plans(
        [{"id": "source", "nuevos": [
            {"h": "a", "titulo": "One official page", "url": "https://example.test/one"},
            {"h": "b", "titulo": "Two official page", "url": "https://example.test/two"},
        ]}],
        root="/tmp/captures",
        capture_planner=_planner,
    )
    receipts = capture_vigia_plans(plans, capture_executor=_executor)
    assert receipts["schema"] == RECEIPT_SCHEMA
    assert receipts["source_plan_hash"] == plans["input_hash"]
    assert [row["status"] for row in receipts["receipts"]] == ["captured", "captured"]
    assert receipts["controls"]["dispatch"] is False
    assert receipts["controls"]["promotion"] == "none"
    assert validate_vigia_capture_receipts(plans, receipts) is True


def test_capture_mode_is_bounded_and_preserves_failed_receipt() -> None:
    plans = build_vigia_capture_plans(
        [{"id": "source", "nuevos": [
            {"h": "a", "titulo": "One official page", "url": "https://example.test/one"},
            {"h": "b", "titulo": "Two official page", "url": "https://example.test/two"},
        ]}],
        root="/tmp/captures",
        capture_planner=_planner,
    )

    def failing_executor(url: str, **_kwargs: object) -> dict:
        return {"decision": "error", "reason": "fixture_failure", "network_called": True, "url": url}

    receipts = capture_vigia_plans(plans, capture_executor=failing_executor, max_captures=1)
    assert receipts["reconciliation"] == {
        "planned_count": 2,
        "attempted_count": 1,
        "captured_count": 0,
        "failed_count": 1,
        "skipped_count": 1,
        "loss": 0,
        "deterministic_order": True,
        "receipt_ids_unique": True,
    }
    assert receipts["receipts"][0]["status"] == "failed"
    assert receipts["skipped"][0]["reason"] == "max_captures_reached"
    assert receipts["controls"]["network_called"] is True
    assert receipts["controls"]["database_write"] is False
    assert validate_vigia_capture_receipts(plans, receipts) is True


def test_receipts_validator_rejects_plan_mismatch() -> None:
    plans = build_vigia_capture_plans(_discoveries(), root="/tmp/captures", capture_planner=_planner)
    receipts = capture_vigia_plans(plans, capture_executor=_executor)
    tampered = copy.deepcopy(receipts)
    tampered["source_plan_hash"] = "sha256:wrong"
    assert validate_vigia_capture_receipts(plans, tampered) is False


def test_receipts_validator_requires_exact_controls_and_provenance() -> None:
    plans = build_vigia_capture_plans(_discoveries(), root="/tmp/captures", capture_planner=_planner)
    receipts = capture_vigia_plans(plans, capture_executor=_executor)
    tampered = copy.deepcopy(receipts)
    tampered["controls"]["extra"] = True
    assert validate_vigia_capture_receipts(plans, tampered) is False
    tampered = copy.deepcopy(receipts)
    tampered["controls"]["dispatch"] = True
    assert validate_vigia_capture_receipts(plans, tampered) is False
    tampered = copy.deepcopy(receipts)
    tampered["provenance"]["record_explicit"] = False
    assert validate_vigia_capture_receipts(plans, tampered) is False
