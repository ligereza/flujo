import json
import subprocess
import sys
from pathlib import Path

from flujo.knowledge.possibility_field import build_possibility_field
from flujo.knowledge.artistic_program_hypotheses import generate_artistic_program_hypotheses
from flujo.knowledge.artistic_program_evaluator import evaluate_artistic_program_payload

REPO_ROOT = Path(__file__).resolve().parents[1]


def candidates(rows):
    return {"schema": "mak-artistic-program-candidates-v1", "bundle_id": "bundle-1", "candidates": rows}


def evaluations(rows):
    return {"schema": "mak-artistic-program-evaluation-v1", "evaluation_id": "eval-1", "results": {item["program_id"]: item for item in rows}}


def row(cid, **extra):
    return {"candidate_id": cid, "title": cid, "status": "accepted", "unit_ids": [cid], "evidence_refs": [f"e:{cid}"], "source_gate_status": "pass", "hard_gate_status": "pass", **extra}


def ev(cid, **extra):
    return {"program_id": cid, "result": "accepted", "source_gate_alignment": {"declared": "pass", "passed": True}, "hard_gate_alignment": {"declared": "pass", "passed": True}, "learning_features": {"training_permitted": False}, **extra}


def test_reordering_and_explicit_score_components():
    result = build_possibility_field(
        candidates([row("low", evidence_score=.2), row("high", evidence_score=.9)]),
        evaluations([ev("low"), ev("high")]),
    )
    assert [item["candidate_id"] for item in result["candidates_ranked"]] == ["high", "low"]
    assert set(result["score_policy"]["weights"]) == set(result["score_policy"]["components"])
    assert result["score_policy"]["non_probabilistic"] is True


def test_deterministic_tie_break():
    result = build_possibility_field(candidates([row("b"), row("a")]), evaluations([ev("b"), ev("a")]))
    assert [item["candidate_id"] for item in result["candidates_ranked"]] == ["a", "b"]


def test_invalid_candidate_is_abstained():
    result = build_possibility_field(candidates([{"status": "accepted"}]), evaluations([]))
    assert result["abstained"][0]["reasons"] == ["candidate_id_missing"]


def test_accepted_candidate_without_evaluation_is_abstained():
    result = build_possibility_field(candidates([row("no-eval")]), evaluations([]))
    assert result["candidates_ranked"] == []
    assert result["abstained"][0]["reasons"] == ["evaluation_missing"]


def test_high_score_with_failed_hard_gate_is_not_ready():
    result = build_possibility_field(candidates([row("risky", evidence_score=1)]), evaluations([ev("risky", hard_gate_alignment={"declared": "fail", "passed": False})]))
    assert result["candidates_ranked"][0]["ready"] is False
    assert result["candidates_ranked"][0]["hard_gate_status"] == "fail"


def test_explicit_rejected_evaluation_stays_rejected_when_gates_abstain():
    result = build_possibility_field(
        candidates([row("false-hypothesis")]),
        evaluations([
            ev(
                "false-hypothesis",
                result="rejected",
                source_gate_alignment={"declared": "abstain", "passed": False},
                hard_gate_alignment={"declared": "abstain", "passed": False},
                errors=["program_empty"],
            )
        ]),
    )
    assert result["candidates_ranked"] == []
    assert result["abstained"] == []
    assert result["research_frontier"] == []
    assert result["rejected"][0]["candidate_id"] == "false-hypothesis"
    assert result["rejected"][0]["reasons"] == [
        "hard_gate:abstain", "program_empty", "source_gate:abstain"
    ]


def test_rejected_mapping_reasons_are_deterministic_and_preserved():
    evaluation = ev(
        "mapped-rejection",
        result="rejected",
        errors=[{"code": "empty_program", "detail": {"count": 0}}],
        reasons=[{"code": "empty_program", "detail": {"count": 0}}, {"code": "missing_basis"}],
        source_gate_alignment={"declared": "abstain", "passed": False},
        hard_gate_alignment={"declared": "abstain", "passed": False},
    )
    first = build_possibility_field(candidates([row("mapped-rejection")]), evaluations([evaluation]))
    second = build_possibility_field(candidates([row("mapped-rejection")]), evaluations([evaluation]))
    assert first == second
    assert first["abstained"] == []
    assert first["research_frontier"] == []
    assert first["rejected"][0]["reasons"] == [
        "hard_gate:abstain",
        "source_gate:abstain",
        {"code": "empty_program", "detail": {"count": 0}},
        {"code": "missing_basis"},
    ]


def test_diversity_and_shared_resources_are_visible():
    result = build_possibility_field(
        candidates([row("a", unit_ids=["u1"], evidence_refs=["e1"], resource_refs=["room"]), row("b", unit_ids=["u1"], evidence_refs=["e1"], resource_refs=["room"]), row("c", unit_ids=["u2"], evidence_refs=["e2"], resource_refs=["other"])]),
        evaluations([ev("a"), ev("b"), ev("c")]),
    )
    assert result["diversity_summary"]["unique_unit_ids"] == ["u1", "u2"]
    assert any(item["candidate_id"] == "b" for item in result["resource_conflicts"])


def test_multiple_opportunities_and_practice_native_are_preserved():
    result = build_possibility_field(
        [candidates([row("native", opportunity_id="practice-native")]), candidates([row("other", opportunity_id="call-2")])],
        [evaluations([ev("native")]), evaluations([ev("other")])],
    )
    assert {item["candidate_id"] for item in result["candidates_ranked"]} == {"native", "other"}


def test_research_frontier_and_learning_features_never_train():
    result = build_possibility_field(candidates([row("r", missing_requirement_ids=["req:r"], research_action_ids=["action:r"], risk_flags=["source_validity_unverified"], learning_features={"x": 1})]), evaluations([ev("r")]))
    assert {item["kind"] for item in result["research_frontier"]} == {"missing_requirement", "research_action", "risk_flag"}
    assert result["learning_gate"] == {"training_permitted": False, "features_carried": True}


def test_abstained_records_preserve_control_fields_and_frontier():
    result = build_possibility_field(
        candidates([row("a", basis="opportunity_conditioned", requirement_ids=["req:a"], missing_requirement_ids=["req:a"], research_action_ids=["action:a"], risk_flags=["source_validity_unverified"])]),
        evaluations([ev("a", result="abstain", source_gate_alignment={"declared": "abstain", "passed": False})]),
    )
    assert result["candidates_ranked"] == []
    abstained = result["abstained"][0]
    assert abstained["basis"] == "opportunity_conditioned"
    assert abstained["missing_requirement_ids"] == ["req:a"]
    assert abstained["research_action_ids"] == ["action:a"]
    assert any(item["kind"] == "refresh_source_validity" for item in result["research_frontier"])


def test_zero_candidates():
    result = build_possibility_field(candidates([]), evaluations([]))
    assert result["decision"] == "abstain"
    assert result["candidates_ranked"] == []


def test_real_generator_to_evaluator_to_possibility_field_cross_smoke():
    from test_artistic_program_evaluator import _candidate, _inputs, _payload

    opportunity, practice, fit = _inputs()
    generated = generate_artistic_program_hypotheses(opportunity, practice, fit)
    evaluated = evaluate_artistic_program_payload(opportunity, practice, fit, generated)
    result = build_possibility_field(generated, evaluated)
    assert evaluated["schema"] == "mak-artistic-program-evaluation-v1"
    assert set(evaluated["results"]) == {item["program_id"] for item in generated["candidates"]}
    assert result["provenance"]["accepted_count"] >= 1
    assert all(item["learning_features"].get("training_permitted") is False for item in result["candidates_ranked"])


def test_real_observed_local_source_abstains_but_keeps_frontier():
    from test_artistic_program_evaluator import _inputs

    opportunity, practice, fit = _inputs(source_status="observed_local", confirmed=False)
    generated = generate_artistic_program_hypotheses(opportunity, practice, fit)
    evaluated = evaluate_artistic_program_payload(opportunity, practice, fit, generated)
    result = build_possibility_field(generated, evaluated)
    assert result["candidates_ranked"] == []
    assert len(result["abstained"]) == 2
    assert result["research_frontier"]
    assert all(item.get("ready") is not True for item in result["abstained"])


def test_cli_stdout(tmp_path):
    candidates_path = tmp_path / "candidates.json"
    evaluations_path = tmp_path / "evaluations.json"
    candidates_path.write_text(json.dumps(candidates([row("cli")])), encoding="utf-8")
    evaluations_path.write_text(json.dumps(evaluations([ev("cli")])), encoding="utf-8")
    command = [sys.executable, "tools/build_possibility_field.py", str(candidates_path), str(evaluations_path)]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["schema"] == "mak-possibility-field-v1"
