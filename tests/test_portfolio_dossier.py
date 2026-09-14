from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.portfolio_dossier import (
    PortfolioDossierError,
    _hash,
    assert_portfolio_dossier,
    compile_portfolio_dossier,
    stable_json,
    validate_portfolio_dossier,
)


def _practice() -> dict:
    return {
        "schema": "mak-practice-evidence-state-v1",
        "algorithm_version": "practice-evidence-state-1",
        "tenant": "mak",
        "archive_id": "archive:generic",
        "snapshot_id": "snapshot:one",
        "input_hash": "sha256:practice-input",
        "state_hash": "sha256:practice-state",
        "source_schema": "mak-archive-project-ir-bundle-v1",
        "units": [
            {
                "unit_id": "unit:one",
                "role": "project_unit",
                "status": "provisional_unit",
                "member_refs": ["artifact:one"],
                "dependency_refs": [],
                "evidence_refs": ["artifact:one"],
            },
            {
                "unit_id": "unit:two",
                "role": "project_unit",
                "status": "unresolved_unit",
                "member_refs": ["artifact:two", "artifact:duplicate"],
                "dependency_refs": ["artifact:dependency"],
                "evidence_refs": ["artifact:two"],
            },
        ],
        "artifacts": [
            {
                "artifact_ref": "artifact:one",
                "physical_id": "physical:one",
                "content_id": "content:same",
                "availability": "available",
                "kind": "file",
                "evidence_refs": ["artifact:one"],
            },
            {
                "artifact_ref": "artifact:two",
                "physical_id": "physical:two",
                "content_id": "content:same",
                "availability": "available",
                "kind": "file",
                "evidence_refs": ["artifact:two"],
            },
            {
                "artifact_ref": "artifact:duplicate",
                "physical_id": "physical:duplicate",
                "content_id": "content:same",
                "availability": "available",
                "kind": "file",
                "evidence_refs": ["artifact:duplicate"],
            },
            {
                "artifact_ref": "artifact:private",
                "physical_id": "physical:private",
                "content_id": "content:private",
                "availability": "available",
                "kind": "file",
                "private": True,
                "evidence_refs": ["artifact:private"],
            },
            {
                "artifact_ref": "artifact:dependency",
                "physical_id": "physical:dependency",
                "content_id": "content:dependency",
                "availability": "available",
                "kind": "file",
                "evidence_refs": ["artifact:dependency"],
            },
        ],
        "media": [],
        "capabilities": [],
        "temporality": [],
        "manifestations": [],
        "resources": [],
        "claims": {
            "supported": [{
                "claim_id": "claim:fact",
                "unit_id": "unit:one",
                "status": "supported",
                "statement": "A documented archive fact",
                "evidence_refs": ["artifact:one"],
                "requirement_ids": ["req:one"],
            }],
            "candidate": [{
                "claim_id": "claim:candidate",
                "unit_id": "unit:two",
                "status": "candidate",
                "statement": "A provisional relation",
                "evidence_refs": ["artifact:two"],
                "requirement_ids": ["req:two"],
            }],
            "unknown": [{
                "claim_id": "claim:unknown",
                "unit_id": "unit:two",
                "status": "unknown",
                "statement": "An unresolved archive question",
                "evidence_refs": [],
                "requirement_ids": ["req:two"],
            }],
        },
        "dependencies": [{
            "unit_id": "unit:two",
            "target_ref": "artifact:dependency",
            "status": "candidate",
            "evidence_refs": ["artifact:dependency"],
        }],
        "ambiguous_refs": [],
        "unassigned_refs": [],
        "gaps": ["research_first_abstained"],
        "abstentions": [],
        "provenance": {"producer": "fixture", "source_rescan": False},
        "reconciliation": {"duplicate_physical_refs_collapsed": False},
    }


def _plan() -> dict:
    return {
        "schema": "mak-product-plan-v1",
        "algorithm_version": "product-plan-fixture-1",
        "opportunity_id": "opportunity:generic",
        "practice_identity": {
            "archive_id": "archive:generic",
            "snapshot_id": "snapshot:one",
            "input_hash": "sha256:practice-input",
        },
        "selected_programs": [
            {
                "program_id": "program:beta",
                "status": "candidate",
                "rank": 2,
                "unit_ids": ["unit:two"],
                "requirement_ids": ["req:two"],
                "candidate_claim_ids": ["claim:candidate", "claim:unknown"],
                "supported_claim_ids": [],
                "evidence_refs": ["artifact:two"],
                "asset_refs": ["artifact:private", "artifact:duplicate"],
                "missing_requirement_ids": ["req:two"],
                "emphasis_claim_ids": ["claim:candidate"],
                "selection_basis": "fixture_candidate",
            },
            {
                "program_id": "program:alpha",
                "status": "accepted",
                "rank": 1,
                "unit_ids": ["unit:one"],
                "requirement_ids": ["req:one"],
                "candidate_claim_ids": [],
                "supported_claim_ids": ["claim:fact"],
                "evidence_refs": ["artifact:one"],
                "asset_refs": ["artifact:one"],
                "missing_requirement_ids": [],
                "emphasis_claim_ids": ["claim:fact"],
                "selection_basis": "fixture_supported",
            },
        ],
        "claim_index": [
            {
                "claim_id": "claim:fact",
                "status": "supported",
                "statement": "A documented archive fact",
                "evidence_refs": ["artifact:one"],
                "requirement_ids": ["req:one"],
                "unit_ids": ["unit:one"],
            },
            {
                "claim_id": "claim:candidate",
                "status": "candidate",
                "statement": "A provisional relation",
                "evidence_refs": ["artifact:two"],
                "requirement_ids": ["req:two"],
                "unit_ids": ["unit:two"],
            },
            {
                "claim_id": "claim:unknown",
                "status": "unknown",
                "statement": "An unresolved archive question",
                "evidence_refs": [],
                "requirement_ids": ["req:two"],
                "unit_ids": ["unit:two"],
            },
        ],
        "asset_index": [
            {
                "artifact_ref": "artifact:one",
                "function": "primary_reference",
                "public_eligibility": "eligible",
                "license_state": "cleared",
                "program_ids": ["program:alpha"],
            },
            {
                "artifact_ref": "artifact:duplicate",
                "function": "supporting_reference",
                "public_eligibility": "eligible",
                "license_state": "cleared",
                "program_ids": ["program:beta"],
            },
            {
                "artifact_ref": "artifact:private",
                "function": "private_reference",
                "private": True,
                "program_ids": ["program:beta"],
            },
            {
                "artifact_ref": "artifact:dependency",
                "function": "dependency_reference",
                "public_eligibility": "unknown",
                "program_ids": [],
            },
        ],
        "targets": {"portfolio_dossier": {"mode": "internal_draft", "audience": "portable"}},
        "gaps": ["research_first_abstained"],
        "control": {
            "publication": False,
            "export": False,
            "promotion": "none",
            "training_permitted": False,
            "research_status": "abstained",
        },
    }


def _technical_context() -> dict:
    return {
        "schema": "mak-project-context-v1",
        "context_id": "tool-context:surface",
        "title": "Technical archive observations",
        "entities": [
            {
                "entity_id": "artifact:one",
                "kind": "physical_artifact",
                "display_name": "native.psd",
            },
            {
                "entity_id": "artifact:two",
                "kind": "physical_artifact",
                "display_name": "logo.png",
            },
        ],
        "sources": [
            {
                "source_id": "tool-observation:surface",
                "source_type": "technical_tool_observation",
                "independence_group": "tool:archive-toolchain",
                "locator": "artifact:one",
                "claim": "technical_observation:surface_match_retrieval",
                "status": "observed",
                "metadata": {
                    "relative_path": "private/native.psd",
                    "facts": {"target_ref": "artifact:two"},
                },
            },
        ],
        "relations": [
            {
                "subject": "artifact:one",
                "predicate": "technical_surface_match_candidate",
                "object": "artifact:two",
                "status": "candidate",
                "source_ids": ["tool-observation:surface"],
                "metadata": {
                    "signals": ["perceptual_surface_similarity"],
                    "relative_path": "private/native.psd",
                    "truth_promotion": False,
                },
            },
        ],
        "projects": [],
        "provenance": {
            "archive_id": "archive:generic",
            "snapshot_id": "snapshot:one",
            "input_hash": "sha256:technical-input",
            "source_schema": "mak-archive-tool-observations-v1",
        },
    }


def test_generic_archive_two_programs_and_no_invented_names() -> None:
    dossier = compile_portfolio_dossier(_plan(), _practice())
    assert dossier["schema"] == "mak-portfolio-dossier-v1"
    assert dossier["status"] == "draft_only"
    assert [row["program_id"] for row in dossier["selected_programs"]] == [
        "program:alpha", "program:beta",
    ]
    assert len(dossier["curatorial_sequence"]) == 4
    assert dossier["alternate_sequences"]
    assert not any("title" in row or "author" in row for row in dossier["selected_programs"])
    assert dossier["curatorial_decision"]["emphasis_is_not_fact"] is True


def test_real_4a_shape_preserves_rank_binding_claims_and_asset_programs() -> None:
    plan = _plan()
    plan["selected_programs"] = [
        {
            "program_id": "program:ranked-second",
            "rank": 2,
            "status": "candidate",
            "unit_ids": ["unit:two"],
            "requirement_ids": ["req:media"],
            "supported_claim_ids": [],
            "candidate_claim_ids": [],
            "evidence_refs": ["artifact:two"],
            "asset_refs": ["artifact:two"],
            "missing_requirement_ids": [],
            "alternatives": [],
        },
        {
            "program_id": "program:ranked-first",
            "rank": 1,
            "status": "accepted",
            "unit_ids": ["unit:one"],
            "requirement_ids": ["req:gate"],
            "supported_claim_ids": ["claim:fact"],
            "candidate_claim_ids": [],
            "evidence_refs": ["artifact:one"],
            "asset_refs": ["artifact:one"],
            "missing_requirement_ids": [],
            "alternatives": [],
        },
    ]
    plan["claim_index"] = [{
        "claim_id": "claim:fact",
        "status": "supported",
        "statement": "A documented archive fact",
        "evidence_refs": ["artifact:one"],
        "requirement_ids": ["req:gate"],
        "unit_ids": ["unit:one"],
    }]
    plan["asset_index"] = [
        {
            "artifact_ref": "artifact:one",
            "function": "primary_reference",
            "public_eligibility": "eligible",
            "license_state": "cleared",
            "program_ids": ["program:ranked-first"],
        },
        {
            "artifact_ref": "artifact:two",
            "function": "supporting_reference",
            "public_eligibility": "eligible",
            "license_state": "cleared",
            "program_ids": ["program:ranked-second"],
        },
    ]

    dossier = compile_portfolio_dossier(plan, _practice())
    assert [row["program_id"] for row in dossier["selected_programs"]] == [
        "program:ranked-first", "program:ranked-second",
    ]
    assert [row["rank"] for row in dossier["selected_programs"]] == [1, 2]

    coverage = {
        row["requirement_id"]: row for row in dossier["requirement_coverage"]
    }
    assert coverage["req:gate"]["coverage_status"] == "documented_fact"
    assert coverage["req:gate"]["missing"] is False
    assert coverage["req:gate"]["supported_claim_ids"] == ["claim:fact"]
    assert coverage["req:media"]["coverage_status"] == "candidate"
    assert coverage["req:media"]["coverage_basis"] == "explicit_program_binding"
    assert coverage["req:media"]["missing"] is False
    assert {
        (row["claim_id"], row["type"])
        for row in dossier["narrative_atoms"]
    } == {("claim:fact", "documented_fact")}
    assets = {row["artifact_ref"]: row for row in dossier["asset_manifest"]}
    assert assets["artifact:one"]["program_ids"] == ["program:ranked-first"]
    assert assets["artifact:two"]["program_ids"] == ["program:ranked-second"]


def test_unit_evidence_namespaces_stay_provenance_not_assets() -> None:
    practice = _practice()
    practice["units"][1]["evidence_refs"] = [
        "artifact:two",
        "candidate:relation-two",
        "observation:unit-two",
    ]
    plan = _plan()
    plan["selected_programs"][0]["evidence_refs"] = [
        "artifact:two",
        "candidate:relation-two",
        "observation:unit-two",
    ]
    next(
        row for row in plan["asset_index"]
        if row["artifact_ref"] == "artifact:duplicate"
    )["evidence_refs"] = [
        "candidate:relation-two",
        "observation:unit-two",
    ]

    dossier = compile_portfolio_dossier(plan, practice)

    asset_refs = {
        row["artifact_ref"]
        for row in dossier["asset_manifest"]
    }
    assert asset_refs == {
        "artifact:dependency",
        "artifact:duplicate",
        "artifact:one",
        "artifact:private",
    }
    assert all(
        ref.startswith("artifact:")
        for row in dossier["asset_manifest"]
        for ref in [row["artifact_ref"]]
    )
    unit_rows = [
        row for row in dossier["curatorial_sequence"]
        if row.get("sequence_kind") == "unit" and row.get("unit_id") == "unit:two"
    ]
    assert unit_rows[0]["evidence_refs"] == [
        "artifact:two",
        "candidate:relation-two",
        "observation:unit-two",
    ]
    assert dossier["selected_programs"][1]["evidence_refs"] == [
        "artifact:two",
        "candidate:relation-two",
        "observation:unit-two",
    ]
    assert all(
        not any(ref.startswith(("candidate:", "observation:")) for ref in row.get("evidence_refs", []))
        for row in dossier["asset_manifest"]
    )
    duplicate = next(
        row for row in dossier["asset_manifest"]
        if row["artifact_ref"] == "artifact:duplicate"
    )
    assert duplicate["evidence_refs"] == []


def test_research_first_without_unit_is_allowed_only_when_not_ready() -> None:
    plan = _plan()
    plan["selected_programs"] = [copy.deepcopy(plan["selected_programs"][0])]
    program = plan["selected_programs"][0]
    program["selection"] = "abstained_research_first"
    program["selection_basis"] = "research_first"
    program["ready"] = False
    program["unit_ids"] = []
    program["asset_refs"] = []
    program["supported_claim_ids"] = []
    program["candidate_claim_ids"] = []
    program["emphasis_claim_ids"] = []
    program["missing_requirement_ids"] = []
    plan["claim_index"] = []
    plan["asset_index"] = []

    dossier = compile_portfolio_dossier(plan, _practice())

    assert dossier["status"] == "draft_only"
    assert dossier["selected_programs"][0]["unit_ids"] == []
    assert dossier["curatorial_sequence"][0]["sequence_kind"] == "program"


def test_research_first_ready_without_unit_fails_closed() -> None:
    plan = _plan()
    program = plan["selected_programs"][0]
    program["selection"] = "abstained_research_first"
    program["selection_basis"] = "research_first"
    program["ready"] = True
    program["unit_ids"] = []
    with pytest.raises(PortfolioDossierError) as error:
        compile_portfolio_dossier(plan, _practice())
    assert "program_" in str(error.value)
    assert "unit_ids_empty" in str(error.value)


def test_abstained_research_first_still_allows_internal_draft() -> None:
    dossier = compile_portfolio_dossier(_plan(), _practice())
    assert dossier["status"] == "draft_only"
    assert "research_first_abstained" in dossier["gaps"]
    assert dossier["control"]["publication"] is False
    assert dossier["control"]["promotion"] == "none"


def test_research_first_without_rank_uses_deterministic_program_id_order() -> None:
    plan = _plan()
    for program in plan["selected_programs"]:
        program.pop("rank")
        program["selection_basis"] = "research_first"
    dossier = compile_portfolio_dossier(plan, _practice())
    assert [row["program_id"] for row in dossier["selected_programs"]] == [
        "program:alpha", "program:beta",
    ]
    assert dossier["curatorial_decision"]["order_basis"] == "deterministic_program_id"


def test_private_asset_is_excluded_and_duplicates_remain_physical() -> None:
    dossier = compile_portfolio_dossier(_plan(), _practice())
    all_refs = [row["artifact_ref"] for row in dossier["asset_manifest"]]
    public_refs = [row["artifact_ref"] for row in dossier["public_manifest"]]
    assert "artifact:private" in all_refs
    assert "artifact:private" not in public_refs
    assert "artifact:duplicate" in public_refs
    assert len([
        row for row in dossier["asset_manifest"]
        if row["content_id"] == "content:same"
    ]) == 2
    assert all(
        row.get("sequence_kind") != "unit" or row.get("unit_id") != "artifact:dependency"
        for row in dossier["curatorial_sequence"]
    )
    assert all("path" not in row and "raw" not in row for row in dossier["asset_manifest"])


def test_candidate_and_unknown_narrative_atoms_are_visible() -> None:
    dossier = compile_portfolio_dossier(_plan(), _practice())
    atoms = {row["claim_id"]: row for row in dossier["narrative_atoms"]}
    assert atoms["claim:fact"]["type"] == "documented_fact"
    assert atoms["claim:candidate"]["type"] == "candidate"
    assert atoms["claim:unknown"]["type"] == "unknown"
    assert atoms["claim:unknown"]["evidence_refs"] == []


def test_deterministic_and_non_mutating() -> None:
    plan = _plan()
    practice = _practice()
    original_plan = copy.deepcopy(plan)
    original_practice = copy.deepcopy(practice)
    first = compile_portfolio_dossier(plan, practice)
    shuffled_plan = copy.deepcopy(plan)
    shuffled_plan["selected_programs"].reverse()
    shuffled_plan["claim_index"].reverse()
    shuffled_plan["asset_index"].reverse()
    second = compile_portfolio_dossier(shuffled_plan, copy.deepcopy(practice))
    assert first == second
    assert plan == original_plan
    assert practice == original_practice
    assert assert_portfolio_dossier(first) is True
    assert validate_portfolio_dossier(first) == []


def test_dossier_declares_consumed_product_plan_hash() -> None:
    plan = _plan()
    dossier = compile_portfolio_dossier(plan, _practice())
    assert dossier["input_hashes"] == {"product_plan": _hash(plan)}


def test_technical_context_reaches_dossier_as_provenance_only() -> None:
    context = _technical_context()
    dossier = compile_portfolio_dossier(_plan(), _practice(), context)

    assert dossier["technical_context"]["provenance_only"] is True
    assert dossier["technical_context"]["claim_promotion"] is False
    assert dossier["technical_context"]["asset_selection"] is False
    assert len(dossier["technical_context"]["relations"]) == 1
    relation = dossier["technical_context"]["relations"][0]
    assert relation["predicate"] == "technical_surface_match_candidate"
    assert relation["evidence_refs"] == ["tool-observation:surface"]
    assert relation["artistic_truth"] is False
    assert relation["asset_selection"] is False
    assert "technical_context" in dossier["input_hashes"]
    assert validate_portfolio_dossier(dossier) == []
    encoded = stable_json(dossier)
    assert "private/native.psd" not in encoded


def test_technical_context_reorder_is_deterministic_and_promotion_fails_closed() -> None:
    context = _technical_context()
    first = compile_portfolio_dossier(_plan(), _practice(), context)
    reordered = copy.deepcopy(context)
    reordered["sources"].reverse()
    reordered["relations"].reverse()
    second = compile_portfolio_dossier(_plan(), _practice(), reordered)
    assert first == second

    promoted = copy.deepcopy(context)
    promoted["relations"][0]["metadata"]["truth_promotion"] = True
    with pytest.raises(PortfolioDossierError, match="technical_context_relation_0_truth_promotion"):
        compile_portfolio_dossier(_plan(), _practice(), promoted)


def test_technical_context_cannot_cross_archive_or_snapshot_boundary() -> None:
    context = _technical_context()
    context["provenance"]["archive_id"] = "archive:other"
    with pytest.raises(PortfolioDossierError, match="technical_context_identity_mismatch:archive_id"):
        compile_portfolio_dossier(_plan(), _practice(), context)

    context = _technical_context()
    context["provenance"]["snapshot_id"] = "snapshot:other"
    with pytest.raises(PortfolioDossierError, match="technical_context_identity_mismatch:snapshot_id"):
        compile_portfolio_dossier(_plan(), _practice(), context)


def test_foreign_refs_fail_closed() -> None:
    plan = _plan()
    plan["selected_programs"][0]["evidence_refs"] = ["artifact:not-in-practice"]
    with pytest.raises(PortfolioDossierError) as error:
        compile_portfolio_dossier(plan, _practice())
    assert "program_evidence_ref_ajeno" in str(error.value)


def test_cli_file_to_stdout(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    practice_path = tmp_path / "practice.json"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
    practice_path.write_text(json.dumps(_practice()), encoding="utf-8")
    result = subprocess.run([
        sys.executable, "tools/compile_portfolio_dossier.py",
        str(plan_path), str(practice_path),
    ], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    dossier = json.loads(result.stdout)
    assert dossier["schema"] == "mak-portfolio-dossier-v1"
    assert dossier["control"]["export"] is False
    output_path = tmp_path / "dossier.json"
    written = subprocess.run([
        sys.executable, "tools/compile_portfolio_dossier.py",
        "--plan", str(plan_path), "--practice", str(practice_path),
        "--output", str(output_path),
    ], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert written.returncode == 0
    assert written.stdout == ""
    assert json.loads(output_path.read_text(encoding="utf-8")) == dossier


def test_cli_can_carry_technical_context(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    practice_path = tmp_path / "practice.json"
    context_path = tmp_path / "context.json"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
    practice_path.write_text(json.dumps(_practice()), encoding="utf-8")
    context_path.write_text(json.dumps(_technical_context()), encoding="utf-8")

    result = subprocess.run([
        sys.executable, "tools/compile_portfolio_dossier.py",
        "--plan", str(plan_path), "--practice", str(practice_path),
        "--technical-context", str(context_path),
    ], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    dossier = json.loads(result.stdout)
    assert len(dossier["technical_context"]["relations"]) == 1
    assert dossier["control"]["publication"] is False
