from __future__ import annotations

from flujo.knowledge.portfolio_relation_evidence_plan import (
    build_relation_evidence_plan,
    validate_relation_evidence_plan,
)


def _context(project=None, relation_status="needs_evidence"):
    return {
        "schema": "mak-portfolio-review-context-v1",
        "available": True,
        "read_only": True,
        "project": project or {
            "project_id": "project-1",
            "title": "Project",
            "state": "review_required",
            "unknowns": ["method: missing"],
            "evidence": [],
        },
        "relation": {
            "status": relation_status,
            "typed_relation_present": False,
            "selection_effect": "none",
            "evidence_refs": [],
        },
    }


def test_unbound_context_is_a_valid_read_only_plan():
    result = build_relation_evidence_plan(_context({
        "project_id": None,
        "title": None,
        "state": None,
        "unknowns": [],
        "evidence": [],
    }, relation_status="unbound"))

    assert validate_relation_evidence_plan(result) is True
    assert result["relation"]["status"] == "unbound"
    assert result["requirements"] == []
    assert result["next_action"] == "select_project_id_before_planning_relation_evidence"


def test_missing_project_record_keeps_id_without_fabricating_title():
    result = build_relation_evidence_plan(_context({
        "project_id": "missing-project",
        "title": None,
        "state": None,
        "unknowns": [],
        "evidence": [],
    }, relation_status="unbound"))

    assert result["project"] == {
        "project_id": "missing-project",
        "title": None,
        "state": None,
        "unknown_count": 0,
        "observed_evidence_count": 0,
    }
