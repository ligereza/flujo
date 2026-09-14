"""Read-only contract tests for the RD/portfolio entity adapter."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flujo.rd.entity_crosswalk import CrosswalkError, load_crosswalk  # noqa: E402


def test_crosswalk_preserves_roles_and_review_status():
    crosswalk = load_crosswalk()
    assert crosswalk.status == "review_only"
    assert crosswalk.source_databases == ("data/rd.db", "data/rd_datos.db")
    assert crosswalk.by_id("openklub").role == "producer_or_brand"
    assert crosswalk.by_id("frvr").role == "artist_dj_headliner"
    assert crosswalk.by_id("scd_plaza_egana").publication == "gated"


def test_crosswalk_rejects_duplicate_ids_without_writing(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({
        "contract": "rd_portfolio_entity_crosswalk",
        "version": 1,
        "status": "review_only",
        "source_databases": ["data/rd.db", "data/rd_datos.db"],
        "entities": [{
            "canonical_id": "same", "role": "venue", "confidence": "low",
            "publication": "review_only", "evidence": ["fixture"]
        }, {
            "canonical_id": "same", "role": "venue", "confidence": "low",
            "publication": "review_only", "evidence": ["fixture"]
        }]
    }), encoding="utf-8")
    try:
        load_crosswalk(path)
    except CrosswalkError as exc:
        assert "duplicate canonical_id" in str(exc)
    else:
        raise AssertionError("duplicate crosswalk id unexpectedly passed")
    assert path.exists()


def test_crosswalk_rejects_unsafe_source_reference_without_writing(tmp_path):
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps({
        "contract": "rd_portfolio_entity_crosswalk",
        "version": 1,
        "status": "review_only",
        "source_databases": ["../data/rd.db"],
        "entities": [{
            "canonical_id": "venue",
            "role": "venue",
            "confidence": "low",
            "publication": "gated",
            "evidence": ["fixture"],
        }],
    }), encoding="utf-8")
    try:
        load_crosswalk(path)
    except CrosswalkError as exc:
        assert "normalized relative path" in str(exc)
    else:
        raise AssertionError("unsafe source reference unexpectedly passed")
    assert path.exists()
