from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from flujo.knowledge.cross_archive_relations import (
    SCHEMA,
    CrossArchiveRelationError,
    compile_cross_archive_relations,
    project_archive_catalog_context,
    project_cross_archive_context,
    validate_cross_archive_relations,
)
from flujo.knowledge.project_context import validate_context


ROOT = Path(__file__).resolve().parents[1]
DREF_PRACTICE = ROOT / "experiments/pilots/DREFQUILA/runs/portable-sample-20260826/drefgira-reconstructed-practice.json"
HARRY_PRACTICE = ROOT / "experiments/pilots/HARRY-NACH-2026/runs/fondart-enriched-opportunity-20260826/practice.json"
CATALOG = ROOT / "data/artist_discographies.json"

# Every test here is about relations BETWEEN pilots, and all four sources above
# live under experiments/pilots/, which .gitignore keeps out of the repository
# on purpose: it is real pilot evidence. On MAK they are present; in a clean
# checkout they are not. Reading them unguarded is exactly why CI went red for
# six runs while this suite stayed green locally -- the suite was measuring a
# machine, not a repository.
pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in (DREF_PRACTICE, HARRY_PRACTICE)),
    reason="experiments/pilots/ is not in this clone")
DREF_CONTEXT = ROOT / "experiments/pilots/DREFQUILA/runs/metadata-federation-20260826/dref_context_federation.json"
HARRY_PROFILE = ROOT / "experiments/pilots/HARRY-NACH-2026/input/archive_profile.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _archives() -> list[dict]:
    dref_context = _load(DREF_CONTEXT)
    harry_profile = _load(HARRY_PROFILE)
    dref_scope = dref_context["scope"]
    return [
        {
            "practice": _load(DREF_PRACTICE),
            "schema": dref_context["schema"],
            **dref_scope,
            "source_ref": str(DREF_CONTEXT),
        },
        {
            "practice": _load(HARRY_PRACTICE),
            "archive_id": harry_profile["archive_id"],
            "artist_identity": harry_profile["declared_identity"]["artist"],
            "source_ref": str(HARRY_PROFILE),
            "binding_status": harry_profile["declared_identity"]["binding_status"],
        },
    ]


def test_real_escarlata_relation_keeps_physical_refs_and_is_candidate():
    payload = compile_cross_archive_relations(_archives(), _load(CATALOG), catalog_source_ref=str(CATALOG))
    assert payload["schema"] == SCHEMA
    assert payload["reconciliation"]["cross_archive_relation_count"] == 4
    assert payload["archives"][0]["practice_binding"] == "reconstructed_reference_only"
    assert payload["archives"][1]["practice_binding"] == "physical_snapshot"
    assert payload["control"]["physical_merge"] is False
    assert all(row["status"] == "candidate" for row in payload["relations"])
    assert all(row["relation"] == "shared_collaboration_track" for row in payload["relations"])
    assert all(row["source_ref"] != row["target_ref"] for row in payload["relations"])
    assert all(row["work_id"].startswith("catalog-track:") for row in payload["relations"])
    assert any("escarlata" in row["evidence_for"][0]["title"].lower() for row in payload["relations"])
    assert validate_cross_archive_relations(payload, _archives(), _load(CATALOG))


def test_same_input_is_byte_identical_and_order_independent():
    archives = _archives()
    catalog = _load(CATALOG)
    first = compile_cross_archive_relations(archives, catalog, catalog_source_ref=str(CATALOG))
    second = compile_cross_archive_relations(list(reversed(archives)), catalog, catalog_source_ref=str(CATALOG))
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(second, ensure_ascii=False, sort_keys=True)


def test_no_cross_archive_relation_without_catalog_feature():
    catalog = _load(CATALOG)
    altered = copy.deepcopy(catalog)
    altered["containers"]["DREFGIRA"]["tracks"] = [
        row for row in altered["containers"]["DREFGIRA"]["tracks"]
        if "escarlata" not in str(row.get("title", "")).lower()
    ]
    payload = compile_cross_archive_relations(_archives(), altered, catalog_source_ref="catalog://altered")
    assert payload["relations"] == []
    assert payload["reconciliation"]["physical_artifacts_merged"] == 0


def test_duplicate_archive_id_fails_closed():
    archives = _archives()
    archives[1]["archive_id"] = archives[0]["archive_id"]
    with pytest.raises(CrossArchiveRelationError, match="duplicate_archive_id"):
        compile_cross_archive_relations(archives, _load(CATALOG))


def test_invalid_practice_state_fails_closed():
    archives = _archives()
    archives[0]["practice"] = copy.deepcopy(archives[0]["practice"])
    archives[0]["practice"]["schema"] = "wrong"
    with pytest.raises(CrossArchiveRelationError, match="practice_invalid"):
        compile_cross_archive_relations(archives, _load(CATALOG))


def test_tampered_endpoint_or_promotion_fails_validator():
    payload = compile_cross_archive_relations(_archives(), _load(CATALOG), catalog_source_ref=str(CATALOG))
    tampered = copy.deepcopy(payload)
    tampered["relations"][0]["target_ref"] = "content:sha256:wrong"
    assert validate_cross_archive_relations(tampered, _archives(), _load(CATALOG)) is False


def test_existing_project_context_projection_is_valid_and_non_promoting():
    payload = compile_cross_archive_relations(_archives(), _load(CATALOG), catalog_source_ref=str(CATALOG))
    context = project_cross_archive_context(payload)
    assert context["schema"] == "mak-project-context-v1"
    assert validate_context(context) == []
    assert len(context["relations"]) == 8
    assert sum(row["predicate"] == "shared_collaboration_track" for row in context["relations"]) == 4
    assert sum(row["predicate"] == "candidate_manifestation_of" for row in context["relations"]) == 4
    assert any(
        row["predicate"] == "candidate_manifestation_of"
        and row["object"].startswith("catalog-track:")
        for row in context["relations"]
    )
    assert context["projects"] == []
    assert all(row["status"] == "candidate" for row in context["relations"])
    assert context["provenance"]["database_write"] is False
    assert len(context["role_bindings"]) == 4
    assert all(
        binding["artifact_role"] == "candidate_visual_manifestation"
        and binding["authorship_status"] == "not_inferred"
        and binding["status"] == "candidate"
        and binding["missing_evidence"] == [
            "native_authoring_project_or_explicit_visual_credit"
        ]
        for binding in context["role_bindings"]
    )
    assert {
        binding["holder_role"] for binding in context["role_bindings"]
    } == {"archive_observed", "reconstructed_reference"}
    assert context["participation_scope"] == {
        "status": "candidate",
        "scope": "matched_archive_artists_only",
        "exhaustive": False,
        "note": (
            "The context records only archive artists matched to this relation; "
            "the catalogue may name additional collaborators."
        ),
    }
    for relation in context["relations"]:
        evidence = relation["evidence"]
        assert evidence
        if relation["predicate"] == "shared_collaboration_track":
            assert sum(item.get("kind") == "artifact_role" for item in evidence) == 2
            assert {
                item["kind"] for item in evidence
            } >= {"artifact_role", "participation_scope"}
            assert next(
                item for item in evidence if item["kind"] == "participation_scope"
            )["exhaustive"] is False
        else:
            assert relation["predicate"] == "candidate_manifestation_of"
            assert any(item.get("kind") == "authorship_gap" for item in evidence)
    tampered = copy.deepcopy(payload)
    tampered["control"]["physical_merge"] = True
    assert validate_cross_archive_relations(tampered, _archives(), _load(CATALOG)) is False


def test_single_archive_catalog_context_recovers_artist_wide_pego_manifestation():
    archive = _archives()[0]
    catalog = _load(CATALOG)
    context = project_archive_catalog_context(archive, catalog, catalog_source_ref=str(CATALOG))
    assert context["schema"] == "mak-project-context-v1"
    assert context["scope"] == "archive_catalog_candidate_projection"
    assert validate_context(context) == []
    pego_ids = {
        entity["entity_id"]
        for entity in context["entities"]
        if entity["display_name"] == "Pego Fuerte"
    }
    assert len(pego_ids) == 1
    pego_relations = [
        relation for relation in context["relations"]
        if relation["object"] in pego_ids
    ]
    assert pego_relations
    assert any(
        "07 PEGO FUERTE.mp4" in str(item.get("relative_path", ""))
        for relation in pego_relations
        for item in relation["evidence"]
    )
    assert all(relation["status"] == "candidate" for relation in pego_relations)
    assert all(
        evidence.get("authorship_status") == "not_inferred"
        for relation in pego_relations
        for evidence in relation["evidence"]
        if evidence.get("kind") == "artifact_role"
    )
    assert context["projects"] == []
    assert context["reconciliation"]["physical_artifacts_merged"] == 0
    assert context["reconciliation"]["truth_promotions"] == 0
    assert context["provenance"]["network_called"] is False
    assert context["provenance"]["database_write"] is False
    assert all(
        "EDIT.mov" not in str(item.get("relative_path", ""))
        for relation in context["relations"]
        for item in relation["evidence"]
        if item.get("kind") == "artifact_name_signal"
    )


def test_single_archive_catalog_context_is_deterministic_and_non_mutating():
    archive = _archives()[0]
    catalog = _load(CATALOG)
    archive_before = copy.deepcopy(archive)
    catalog_before = copy.deepcopy(catalog)
    first = project_archive_catalog_context(archive, catalog, catalog_source_ref=str(CATALOG))
    second = project_archive_catalog_context(archive, catalog, catalog_source_ref=str(CATALOG))
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )
    assert archive == archive_before
    assert catalog == catalog_before
