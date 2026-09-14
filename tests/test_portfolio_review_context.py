from __future__ import annotations

import copy

import pytest

from flujo.knowledge.portfolio_review_context import (
    compile_portfolio_review_context,
    validate_portfolio_review_context,
)


pytestmark = pytest.mark.flujo


def _archive_view() -> dict:
    return {
        "schema": "mak-archive-portfolio-view-v1",
        "source": {
            "path_hint": "iskvw/datos/archivo.json",
            "input_hash": "sha256:" + "a" * 64,
        },
        "selection": {"selected_item_count": 65},
        "reconciliation": {"omitted_piece_count": 1969},
    }


def _project() -> dict:
    return {
        "project_id": "project-1",
        "title": "A pending project",
        "state": "review_required",
        "unknowns": ["missing evidence"],
        "evidence": [{"kind": "application_package", "status": "observed"}],
    }


def test_review_context_keeps_project_unbound_without_typed_relation() -> None:
    payload = compile_portfolio_review_context(
        _archive_view(), [_project()], project_id="project-1")

    assert payload["schema"] == "mak-portfolio-review-context-v1"
    assert payload["relation"] == {
        "status": "needs_evidence",
        "typed_relation_present": False,
        "evidence_refs": [],
        "selection_effect": "none",
        "reason": "La cola no contiene una relación tipada archivo-proyecto con referencias explícitas.",
    }
    assert payload["project"]["unknowns"] == ["missing evidence"]
    assert payload["control"]["decision_write"] is False
    assert validate_portfolio_review_context(payload) is True


def test_review_context_without_project_is_explicitly_unbound() -> None:
    payload = compile_portfolio_review_context(_archive_view(), [])

    assert payload["relation"]["status"] == "unbound"
    assert payload["project"]["project_id"] is None
    assert payload["relation"]["selection_effect"] == "none"


def test_review_context_refuses_a_claimed_typed_relation() -> None:
    payload = compile_portfolio_review_context(_archive_view(), [])
    tampered = copy.deepcopy(payload)
    tampered["relation"]["status"] = "typed"

    with pytest.raises(ValueError, match="relation_status_invalid"):
        validate_portfolio_review_context(tampered)
