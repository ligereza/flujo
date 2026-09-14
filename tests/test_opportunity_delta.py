from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.flujo.knowledge.opportunity_constraints import (
    INPUT_SCHEMA,
    compile_opportunity_constraints,
)
from src.flujo.knowledge.opportunity_delta import (
    SCHEMA,
    OpportunityDeltaError,
    compare_opportunity_constraints,
    stable_json,
    validate_opportunity_delta,
)
from tools.compile_opportunity_delta import main


def _package(*, content: str = "local-v1", validity: dict | None = None, extra: bool = False) -> dict:
    requirements = [
        {"id": "gate:field-study", "kind": "hard_gate", "field": "field_study_required", "evidence_refs": ["p2-field-study"]},
    ]
    evidence = [
        {"evidence_id": "p2-field-study", "kind": "hard_gate", "field": "field_study_required", "value": True, "locator": {"page": 2}},
    ]
    if extra:
        requirements.append({"id": "document:advance", "kind": "required_document", "field": "advance_of_research", "evidence_refs": ["p27-advance"]})
        evidence.append({"evidence_id": "p27-advance", "kind": "required_document", "field": "advance_of_research", "value": {"pages": 2}, "locator": {"page": 27}})
    return {
        "schema": INPUT_SCHEMA,
        "opportunity_id": "opportunity:fixture",
        "title": "Opportunity fixture",
        "source": {
            "ref": "fixture/bases.pdf",
            "url": "https://example.test/bases.pdf",
            "content": content,
            "version": "fixture-v1",
            "validity": validity or {"status": "observed_local", "confirmed": False},
        },
        "requirements": requirements,
        "evidence": evidence,
    }


def _constraints(**kwargs: object) -> dict:
    return compile_opportunity_constraints(_package(**kwargs))


def test_no_semantic_change_is_deterministic_and_does_not_recompute() -> None:
    previous = _constraints()
    current = copy.deepcopy(previous)
    first = compare_opportunity_constraints(previous, current)
    second = compare_opportunity_constraints(copy.deepcopy(previous), copy.deepcopy(current))
    assert first == second
    assert first["schema"] == SCHEMA
    assert first["changes"] == []
    assert first["impact"]["recompute_required"] is False
    assert validate_opportunity_delta(previous, current, first) is True


def test_constraint_change_identifies_requirement_and_all_downstream_consumers() -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    delta = compare_opportunity_constraints(previous, current)
    assert delta["affected_requirement_ids"] == ["document:advance"]
    assert delta["impact"]["recompute_required"] is True
    assert "product_plan" in delta["impact"]["affected_consumers"]
    assert delta["reconciliation"]["truth_promotions"] == 0
    row = next(item for item in delta["changes"] if item["item_id"] == "document:advance")
    assert row["change_type"] == "added"
    assert row["evidence_refs"] == ["p27-advance"]


def test_validity_change_is_semantic_and_preserves_source_provenance() -> None:
    previous = _constraints()
    current = _constraints(validity={"status": "current_verified", "confirmed": True, "effective_to": "2026-09-10"})
    delta = compare_opportunity_constraints(previous, current)
    assert delta["impact"]["recompute_required"] is True
    assert "source_validity_changed" in delta["impact"]["reason_codes"]
    change = next(item for item in delta["changes"] if item["domain"] == "source")
    assert change["changed_fields"] == ["validity"]
    assert change["previous"]["source_hash"] == change["current"]["source_hash"]
    unknown_change = next(item for item in delta["changes"] if item["domain"] == "unknowns")
    assert unknown_change["changed_fields"] == ["value"]
    assert unknown_change["evidence_refs"] == []
    assert validate_opportunity_delta(previous, current, delta) is True


def test_source_content_change_without_requirement_change_is_provenance_only() -> None:
    previous = _constraints(content="local-v1")
    current = _constraints(content="local-v2")
    delta = compare_opportunity_constraints(previous, current)
    assert delta["affected_requirement_ids"] == []
    assert delta["impact"]["recompute_required"] is False
    assert delta["impact"]["reason_codes"] == ["source_provenance_changed_only"]


def test_real_arica_baseline_enriched_diff_is_consumable() -> None:
    root = Path(__file__).parents[1] / "experiments/pilots/ARICA-FONDART-2027/runs"
    # experiments/pilots/ is gitignored on purpose: it holds real pilot
    # evidence. On MAK it is present, in a clean checkout it is not, and
    # reading it unguarded is why CI went red while this suite stayed green.
    if not (root / "full-baseline/opportunity.json").is_file():
        pytest.skip("experiments/pilots/ARICA-FONDART-2027 is not in this clone")
    previous = json.loads((root / "full-baseline/opportunity.json").read_text(encoding="utf-8"))
    current = json.loads((root / "enriched/opportunity.json").read_text(encoding="utf-8"))
    delta = compare_opportunity_constraints(previous, current)
    assert delta["opportunity_id"] == "fondart-nacional-investigacion-2027"
    assert delta["impact"]["recompute_required"] is True
    assert delta["impact"]["reason_codes"] == ["source_validity_changed", "unknowns_changed"]
    assert delta["reconciliation"]["change_count"] == 2
    unknown_change = next(item for item in delta["changes"] if item["domain"] == "unknowns")
    assert unknown_change["changed_fields"] == ["value"]
    assert unknown_change["evidence_refs"] == ["p28-deadline-local"]


def test_mismatched_or_malformed_inputs_fail_closed() -> None:
    previous = _constraints()
    current = _constraints()
    current["opportunity_id"] = "opportunity:other"
    with pytest.raises(OpportunityDeltaError):
        compare_opportunity_constraints(previous, current)
    malformed = copy.deepcopy(previous)
    malformed["schema"] = "wrong"
    with pytest.raises(OpportunityDeltaError):
        compare_opportunity_constraints(previous, malformed)
    assert validate_opportunity_delta(previous, previous, {"schema": SCHEMA}) is False


def test_cli_file_to_file_is_canonical(tmp_path: Path) -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"
    output_path = tmp_path / "delta.json"
    previous_path.write_text(stable_json(previous), encoding="utf-8")
    current_path.write_text(stable_json(current), encoding="utf-8")
    assert main(["--previous", str(previous_path), "--current", str(current_path), "--output", str(output_path)]) == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == compare_opportunity_constraints(previous, current)
    assert payload["schema"] == SCHEMA
