"""Adversarial tests for the operator frontier deepening.

The dossier may strengthen or weaken the evidence behind a tie.  It must never
answer one, close one, or let SSD/operator material reach the ISKVW selection.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from flujo.knowledge.contracurator import (
    ContracuratorError,
    compile_contracurator_exhibition,
)
from flujo.knowledge.product_view import project_archive_portfolio_view, stable_json
from flujo.knowledge.ssd_order_foundation import (
    DEFAULT_BLEND_TARGETS,
    DEFAULT_DECLARED_INPUTS,
    DEFAULT_TIE_DB,
    EMPTY_CONTENT_ID,
    compile_ssd_order_foundation,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")
ORDER = Path("/home/mak/curatoria_inbox/order/2026-08-24/order_projection.json")
INTAKE = Path("/home/mak/research/intake/portable-ssd-20260813-scd-r4/intake.sqlite")
RECONSTRUCTION = Path("/home/mak/curatoria_inbox/project_reconstruction/2026-08-21")
CORPUS = Path("/home/mak/research/corpus")
KNOWLEDGE_DB = ROOT / "data" / "mak_knowledge.db"

# Every test in this file goes through _compile(), and _compile() always
# passes knowledge_db, reconstruction_dir and research_corpus_dir -- even the
# tmp_path tests below only override one narrow, unrelated argument. KNOWLEDGE_DB
# is *.db and gitignored; RECONSTRUCTION and CORPUS live under /home/mak
# entirely outside the repository. On a clean checkout (and on CI's
# ubuntu-latest, which has no /home/mak at all) compile_ssd_order_foundation
# raises SSDOrderFoundationError("source_missing:...") from inside the
# module-scoped `foundation` fixture's setup, which is why the failure showed
# up as 24 ERRORs rather than 24 FAILEDs: the INDEX/ORDER/INTAKE/DEFAULT_TIE_DB
# check here did not cover these three sources.
_REQUIRED = (INDEX, ORDER, INTAKE, RECONSTRUCTION, CORPUS, KNOWLEDGE_DB, DEFAULT_TIE_DB)


def _sources_present() -> bool:
    return all(path.exists() for path in _REQUIRED)


pytestmark = pytest.mark.skipif(
    not _sources_present(), reason="real read-only SSD order sources are not mounted")


def _compile(**overrides):
    kwargs = dict(
        index_path=INDEX,
        order_projection_path=ORDER,
        intake_db=INTAKE,
        knowledge_db=ROOT / "data" / "mak_knowledge.db",
        research_authority_path=ROOT / "data" / "artist_discographies.json",
        reconstruction_dir=RECONSTRUCTION,
        archive_path=ROOT / "iskvw" / "datos" / "archivo.json",
        research_corpus_dir=CORPUS,
    )
    kwargs.update(overrides)
    return compile_ssd_order_foundation(**kwargs)


@pytest.fixture(scope="module")
def foundation() -> dict:
    return _compile()


@pytest.fixture(scope="module")
def view() -> dict:
    archive = json.loads((ROOT / "iskvw" / "datos" / "archivo.json").read_text(encoding="utf-8"))
    return project_archive_portfolio_view(archive, max_items_per_format=24)


def test_all_fifty_ties_are_reproduced_from_an_independent_byte_ledger(foundation: dict) -> None:
    review = foundation["operator_review"]
    questions = review["questions"]

    assert review["asked_count"] == 6
    assert review["deferred_count"] == 44
    assert len(questions) == 50
    assert review["machine_answerable"] is False
    assert review["selection_effect"] == "none"
    for row in questions:
        identity = row["dossier"]["byte_identity"]
        assert identity["status"] == "recomputed"
        # The ledger is a second source: it must land on the same numbers the
        # question already declares, or the mismatch must be visible.
        assert identity["recomputed_shared_classes"] == row["shared_classes"]
        assert identity["recomputed_shared_bytes"] == row["shared_bytes"]
        assert identity["matches_declared_question"] is True
    assert review["triage"]["questions_reproduced_from_independent_ledger"] == 50


def test_metadata_only_ties_are_graded_down_but_never_answered(foundation: dict) -> None:
    review = foundation["operator_review"]
    grades = review["triage"]["grade_counts"]
    metadata_only = [
        row for row in review["questions"]
        if row["dossier"]["evidence_grade"] == "metadata_only"
    ]

    assert grades["metadata_only"] == len(metadata_only) == 15
    for row in metadata_only:
        dossier = row["dossier"]
        identity = dossier["byte_identity"]
        assert identity["substantive_class_count"] == 0
        assert identity["zero_byte_class_count"] or identity["appledouble_class_count"]
        # Weak evidence is not an answer.
        assert dossier["resolution"]["status"] == "unresolved"
        assert dossier["resolution"]["resolved_by"] == "operator_attestation_only"
        assert dossier["machine_answerable"] is False
        assert dossier["selection_effect"] == "none"
        assert row["answers"], "the source answer options must survive the downgrade"
        assert any(
            "no shared class carries substantive bytes" in item["statement"]
            for item in dossier["evidence_against"]
        )


def test_zero_byte_and_appledouble_classes_are_named_as_counterevidence(foundation: dict) -> None:
    questions = {row["question_id"]: row for row in foundation["operator_review"]["questions"]}
    empty_backed = [
        row for row in questions.values()
        if row["dossier"]["byte_identity"].get("zero_byte_class_count")
    ]
    fork_backed = [
        row for row in questions.values()
        if row["dossier"]["byte_identity"].get("appledouble_class_count")
    ]

    assert empty_backed and fork_backed
    for row in empty_backed:
        statements = [item["statement"] for item in row["dossier"]["evidence_against"]]
        refs = [item["source_ref"] for item in row["dossier"]["evidence_against"]]
        assert any("zero-byte content class" in text for text in statements)
        assert any(EMPTY_CONTENT_ID in ref for ref in refs)
    for row in fork_backed:
        statements = [item["statement"] for item in row["dossier"]["evidence_against"]]
        assert any("AppleDouble" in text for text in statements)


def test_unbound_containers_are_reported_instead_of_assumed(foundation: dict) -> None:
    review = foundation["operator_review"]
    unbound = [row for row in review["questions"] if row["dossier"]["unbound_containers"]]

    assert review["triage"]["questions_with_unbound_container"] == len(unbound) == 7
    assert review["triage"]["unbound_containers"] == ["Spotlight-V100", "_KAYAKAZE 2025 2.xml"]
    for row in unbound:
        dossier = row["dossier"]
        for name in dossier["unbound_containers"]:
            side = next(
                dossier["sides"][label] for label in ("left", "right")
                if dossier["sides"][label]["container"] == name
            )
            assert side["container_binding"] == "unbound"
            assert side["ssd_project_count"] == 0
            assert any(
                f"'{name}' is not a container_root" in item["statement"]
                for item in dossier["evidence_against"]
            )
            assert any(
                f"an indexed SSD project container for '{name}'" == item["statement"]
                for item in dossier["missing_evidence"]
            )


def test_every_dossier_claim_carries_a_source_ref(foundation: dict) -> None:
    for row in foundation["operator_review"]["questions"]:
        dossier = row["dossier"]
        assert dossier["evidence_for"] and dossier["evidence_against"]
        assert dossier["missing_evidence"]
        for field in ("evidence_for", "evidence_against", "missing_evidence"):
            for item in dossier[field]:
                assert item["statement"].strip()
                assert item["source_ref"].strip()
        assert dossier["reopen_when"].strip()
        assert dossier["reopen_when_source"].strip()
        assert dossier["possible_answers"] == row["answers"]
        assert any(
            item["statement"].startswith("an operator attestation")
            for item in dossier["missing_evidence"]
        )


def test_attestation_queue_is_ordered_but_empty_of_answers(foundation: dict) -> None:
    review = foundation["operator_review"]
    queue = review["attestation_queue"]

    assert len(queue) == 50
    assert review["attestation_queue_status"] == "pending_human_input"
    assert review["answers_recorded"] == 0
    assert [row["rank"] for row in queue] == list(range(1, 51))
    # The six asked ties lead the queue; nothing carries an answer.
    assert all(row["status"] == "ask" for row in queue[:6])
    assert all(
        row["answered"] is False and row["answer"] is None
        and row["attested_by"] is None and row["selection_effect"] == "none"
        for row in queue
    )
    asked_bytes = [row["substantive_shared_bytes"] for row in queue[:6]]
    assert asked_bytes == sorted(asked_bytes, reverse=True)


def test_missing_tie_ledger_degrades_to_an_evidence_gap(tmp_path: Path) -> None:
    result = _compile(ties_path=tmp_path / "absent.db")
    review = result["operator_review"]

    assert review["asked_count"] == 6 and review["deferred_count"] == 44
    assert review["triage"]["grade_counts"] == {"unverified_no_ledger": 50}
    for row in review["questions"]:
        identity = row["dossier"]["byte_identity"]
        assert identity["status"] == "missing_source"
        # An absent source must never become a corroboration.
        assert "recomputed_shared_classes" not in identity
        assert any(
            item["statement"].startswith("independent byte-identity ledger")
            for item in row["dossier"]["missing_evidence"]
        )


def test_research_frontier_abstains_and_names_its_blocking_gates(foundation: dict) -> None:
    frontier = foundation["research_frontier"]

    assert frontier["status"] == "abstain"
    assert frontier["compiled"] is False
    assert frontier["job_count"] == 0
    assert frontier["dispatch"] is False
    assert frontier["create_job_invoked"] is False
    assert frontier["network_called"] is False
    gates = {row["gate"] for row in frontier["blocking_gates"]}
    assert gates == {
        "archive_missing_artist_identity",
        "catalog_track_title_matches_filename_stem",
        "relation_payload_schema_required",
    }
    for row in frontier["blocking_gates"]:
        assert row["source_ref"].startswith("src/flujo/knowledge/")
        assert row["why_refused"].strip()
    assert frontier["available_input"]["typed_reference_count"] == 0
    assert frontier["available_input"]["selection_eligible"] is False


def test_foundation_is_deterministic_and_writes_nothing(foundation: dict) -> None:
    replay = _compile()

    assert stable_json(replay) == stable_json(foundation)
    assert foundation["control"] == {
        "source_rescan": False,
        "physical_mutation": False,
        "database_write": False,
        "network_called": False,
        "publication": False,
        "training_permitted": False,
        "promotion": "none",
    }


def test_operator_frontier_cannot_move_the_iskvw_selection(view: dict, foundation: dict) -> None:
    without = compile_contracurator_exhibition(view)
    with_basis = compile_contracurator_exhibition(view, ssd_order_foundation=foundation)

    # The deepened frontier is visible, and the selection is byte-identical.
    assert with_basis["result"]["exhibition"]["source_refs"] == \
        without["result"]["exhibition"]["source_refs"]
    assert len(with_basis["result"]["exhibition"]["source_refs"]) == 8
    assert stable_json(with_basis["theses"]) == stable_json(without["theses"])
    basis = with_basis["provenance"]["ssd_order_foundation"]
    assert basis["used_for_selection"] is False
    assert basis["crosswalk_status"] == "candidate"
    assert basis["crosswalk_candidate_count"] == 52
    review = basis["operator_review"]
    assert len(review["question_samples"]) == 6
    assert len(review["deferred_samples"]) == 44
    assert len(review["attestation_queue"]) == 50
    assert review["machine_answerable"] is False
    assert review["selection_effect"] == "none"
    assert basis["research_frontier"]["job_count"] == 0


def test_hub_basis_fails_closed_on_a_prefilled_or_dispatched_frontier(
    view: dict, foundation: dict,
) -> None:
    answered = copy.deepcopy(foundation)
    answered["operator_review"]["attestation_queue"][0]["answered"] = True
    with pytest.raises(ContracuratorError, match="attestation_queue_prefilled"):
        compile_contracurator_exhibition(view, ssd_order_foundation=answered)

    dispatched = copy.deepcopy(foundation)
    dispatched["research_frontier"]["dispatch"] = True
    with pytest.raises(ContracuratorError, match="research_frontier_dispatched"):
        compile_contracurator_exhibition(view, ssd_order_foundation=dispatched)

    stripped = copy.deepcopy(foundation)
    del stripped["research_frontier"]
    with pytest.raises(ContracuratorError, match="research_frontier_missing"):
        compile_contracurator_exhibition(view, ssd_order_foundation=stripped)

    untriaged = copy.deepcopy(foundation)
    del untriaged["operator_review"]["triage"]
    with pytest.raises(ContracuratorError, match="operator_triage_missing"):
        compile_contracurator_exhibition(view, ssd_order_foundation=untriaged)


def test_episode_references_the_frontier_by_hash_not_by_copy(
    view: dict, foundation: dict,
) -> None:
    result = compile_contracurator_exhibition(view, ssd_order_foundation=foundation)
    digest = result["product_episode"]["input"]["ssd_order_foundation"]

    assert digest["semantic_hash"] == foundation["semantic_hash"]
    assert digest["operator_review"]["attestation_queue_length"] == 50
    assert digest["operator_review"]["triage"] == foundation["operator_review"]["triage"]
    assert digest["used_for_selection"] is False
    # The durable episode must not carry a fourth copy of every dossier.
    assert "questions" not in digest["operator_review"]
    assert "question_samples" not in digest["operator_review"]
    assert "attestation_queue" not in digest["operator_review"]
    assert result["product_episode"]["control"]["database_write"] is False
    assert result["product_episode"]["control"]["training_permitted"] is False


def test_declared_native_inputs_stay_dependency_context(foundation: dict) -> None:
    rows = [
        row for row in foundation["operator_review"]["questions"]
        if row["dossier"]["declared_input_signals"].get("status") == "matched"
    ]

    assert DEFAULT_DECLARED_INPUTS.exists() and DEFAULT_BLEND_TARGETS.exists()
    assert rows, "the real sources contain at least one declared-input match"
    for row in rows:
        signals = row["dossier"]["declared_input_signals"]
        assert signals["role"] == "dependency_context_only"
        assert signals["source_refs"]
        assert "does not establish a commission" in signals["note"]
        # A declared input argues for reuse; it never answers the question.
        assert row["dossier"]["resolution"]["status"] == "unresolved"


# --- Cycle 8: adversarial attacks on the triangulated frontier --------------


def test_identity_tier_is_reproduced_not_asserted(foundation: dict) -> None:
    tiers = foundation["operator_review"]["identity_tiers"]
    declared = {
        key: int(value["classes"])
        for key, value in tiers["declared_by_order_projection"].items()
    }

    assert tiers["reproduces_declared_totals"] is True
    assert tiers["recomputed_from_ledger"] == declared
    assert declared == {
        "T1_loose_copy_at_disk_root": 24,
        "T2_crosses_roots_needs_an_answer": 458,
        "T3_inside_one_project_left_alone": 865,
    }
    # Every tie must land in a tier drawn from the projection's own vocabulary.
    allowed = set(declared)
    for row in foundation["operator_review"]["questions"]:
        observed = row["dossier"]["byte_identity"].get("identity_tiers") or {}
        assert observed and not set(observed) - allowed
        assert sum(observed.values()) == row["shared_classes"]


def test_index_relation_count_is_not_treated_as_binding_power(foundation: dict) -> None:
    reality = foundation["operator_review"]["index_relation_reality"]

    assert reality["relation_total"] == 113
    # The decisive measured facts: no substantive duplicate and no typed
    # relation that crosses a container boundary.
    assert reality["exact_duplicate_on_empty_content"] == 111
    assert reality["exact_duplicate_substantive"] == 0
    assert reality["typed_non_duplicate_relations"] == 2
    assert reality["cross_container_typed_non_duplicate_relations"] == 0
    assert reality["questions_with_a_binding_typed_relation"] == 0
    for row in foundation["operator_review"]["questions"]:
        typed = row["dossier"]["typed_relations"]
        assert typed["binding_this_pair"] == 0
        assert any(
            "no typed relation in the SSD index connects" in item["statement"]
            for item in row["dossier"]["evidence_against"]
        )


def test_every_crosswalk_candidate_is_measured_not_assumed(foundation: dict) -> None:
    crosswalk = foundation["crosswalk_to_iskvw"]
    audit = crosswalk["binding_audit"]

    assert crosswalk["typed_reference_count"] == 0
    assert crosswalk["status"] == "candidate"
    assert audit["candidates_checked"] == 52
    assert audit["with_shared_content_hash"] == 0
    assert audit["with_delivery_receipt"] == 0
    assert audit["with_typed_reference"] == 0
    assert audit["ssd_hash_states"] == {"pending": 52}
    assert audit["iskvw_source_original_states"] == {"ausente": 52}
    assert len(audit["bases_scanned"]) >= 4
    for row in crosswalk["candidate_relations"]:
        check = row["binding_check"]
        assert check["verdict"] == "candidate"
        assert check["selection_eligible"] is False
        assert check["content_hash"]["shared_content_hash"] is False
        assert check["delivery_receipt"]["present"] is False
        assert check["typed_reference"]["is_typed_reference"] is False
        assert check["research_corpus"]["independent_confirmation"] is False
        assert row["selection_eligible"] is False


def test_a_locator_inside_a_generated_filename_is_never_a_reference(foundation: dict) -> None:
    crosswalk = foundation["crosswalk_to_iskvw"]
    echoing = [
        row for row in crosswalk["candidate_relations"]
        if row["binding_check"]["typed_reference"]["derived_locator_echo_count"]
    ]

    # The real bases do contain contact-sheet thumbnails whose filename embeds
    # the locator.  That is the exact near-miss the guard rule exists for.
    assert echoing, "the real knowledge base carries at least one derived echo"
    assert crosswalk["binding_audit"]["derived_locator_echoes"] >= len(echoing)
    for row in echoing:
        typed = row["binding_check"]["typed_reference"]
        assert typed["is_typed_reference"] is False
        for echo in typed["derived_locator_echoes"]:
            assert echo["kind"] == "derived_locator_echo"
            assert echo["is_typed_reference"] is False
            assert echo["has_sha256"] is False
            assert not echo["declared_work_id"]
            assert "filename substring is not a reference" in echo["reason"]


def test_pilot_cross_archive_chain_is_cited_but_never_adopted(foundation: dict) -> None:
    frontier = foundation["research_frontier"]
    pilot = frontier["existing_pilot_chain"]

    assert frontier["status"] == "abstain"
    assert frontier["scope"] == "ssd_order_frontier"
    assert frontier["job_count"] == 0
    # The abstention must be precise: a valid payload does exist at pilot scope.
    assert "pilot scope" in frontier["precision_note"]
    assert pilot["status"] == "present_pilot_scope"
    assert pilot["scope"] == "pilot_case_run_not_the_ssd_order_frontier"
    assert pilot["relations_schema"] == "mak-cross-archive-relations-v1"
    assert pilot["relation_statuses"] == {"candidate": pilot["relation_count"]}
    # It only exists because of the two inferences this projection refuses.
    assert pilot["reason_codes"].get("local_title_match")
    assert pilot["evidence_kinds"].get("artifact_name_signal")
    assert pilot["declared_alternatives"].get("same_title_different_work")
    assert all(row["declared_artist_identity"] for row in pilot["archives"])
    assert pilot["research_frontier"]["dispatched_job_count"] == 0
    assert "answering any of the 50 operator ties" in pilot["not_usable_for"]


def test_pilot_chain_absence_degrades_without_breaking(tmp_path: Path) -> None:
    result = _compile(pilot_cross_archive_run=tmp_path / "no-such-run")
    frontier = result["research_frontier"]

    assert frontier["status"] == "abstain"
    assert frontier["existing_pilot_chain"]["status"] == "absent"
    assert result["crosswalk_to_iskvw"]["typed_reference_count"] == 0


def test_deferral_is_stated_not_silent(foundation: dict) -> None:
    review = foundation["operator_review"]
    silent = [
        row for row in review["questions"]
        if not row["dossier"]["adds_actionable_evidence"]
    ]

    assert review["triage"]["questions_without_actionable_evidence"] == len(silent)
    for row in silent:
        dossier = row["dossier"]
        assert dossier["deferral_reason"], "a tie with no evidence must say so"
        assert dossier["actionable_evidence_kinds"] == []
        assert dossier["resolution"]["status"] == "unresolved"
    for row in review["questions"]:
        if row["dossier"]["adds_actionable_evidence"]:
            assert row["dossier"]["deferral_reason"] == ""
            assert row["dossier"]["actionable_evidence_kinds"]


def test_hub_basis_rejects_a_promoted_or_dispatched_pilot_chain(
    view: dict, foundation: dict,
) -> None:
    promoted = copy.deepcopy(foundation)
    promoted["research_frontier"]["existing_pilot_chain"]["relation_statuses"] = {"bound": 6}
    with pytest.raises(ContracuratorError, match="pilot_chain_promoted"):
        compile_contracurator_exhibition(view, ssd_order_foundation=promoted)

    dispatched = copy.deepcopy(foundation)
    dispatched["research_frontier"]["existing_pilot_chain"]["research_frontier"][
        "dispatched_job_count"] = 1
    with pytest.raises(ContracuratorError, match="pilot_chain_dispatched"):
        compile_contracurator_exhibition(view, ssd_order_foundation=dispatched)

    rescoped = copy.deepcopy(foundation)
    rescoped["research_frontier"]["existing_pilot_chain"]["scope"] = "ssd_order_frontier"
    with pytest.raises(ContracuratorError, match="pilot_chain_scope_invalid"):
        compile_contracurator_exhibition(view, ssd_order_foundation=rescoped)


def test_hub_basis_rejects_a_binding_claim_on_an_unbound_crosswalk(
    view: dict, foundation: dict,
) -> None:
    for field in ("with_typed_reference", "with_shared_content_hash", "with_delivery_receipt"):
        tampered = copy.deepcopy(foundation)
        tampered["crosswalk_to_iskvw"]["binding_audit"][field] = 1
        with pytest.raises(ContracuratorError, match="crosswalk_binding_contradiction"):
            compile_contracurator_exhibition(view, ssd_order_foundation=tampered)

    stripped = copy.deepcopy(foundation)
    del stripped["crosswalk_to_iskvw"]["binding_audit"]
    with pytest.raises(ContracuratorError, match="crosswalk_binding_audit_missing"):
        compile_contracurator_exhibition(view, ssd_order_foundation=stripped)


def test_renaming_a_container_cannot_manufacture_a_binding(
    view: dict, foundation: dict,
) -> None:
    """A folder name is a locator: rewriting it must not create evidence."""
    renamed = copy.deepcopy(foundation)
    for row in renamed["operator_review"]["questions"]:
        row["left"] = f"OBRA MAESTRA {row['left']}"
        row["right"] = f"OBRA MAESTRA {row['right']}"
        row["dossier"]["left"] = row["left"]
        row["dossier"]["right"] = row["right"]
    result = compile_contracurator_exhibition(view, ssd_order_foundation=renamed)
    basis = result["provenance"]["ssd_order_foundation"]

    # The rename travels as a label and changes nothing that binds.
    assert basis["used_for_selection"] is False
    assert basis["crosswalk_binding_audit"]["with_typed_reference"] == 0
    assert basis["operator_review"]["machine_answerable"] is False
    for row in basis["operator_review"]["question_samples"]:
        assert row["typed_relation_binding_this_pair"] == 0
        assert row["selection_effect"] == "none"
    assert result["result"]["exhibition"]["source_refs"] == \
        compile_contracurator_exhibition(view)["result"]["exhibition"]["source_refs"]


def test_stripping_evidence_lists_does_not_soften_the_verdict(
    view: dict, foundation: dict,
) -> None:
    stripped = copy.deepcopy(foundation)
    for row in stripped["operator_review"]["questions"]:
        row["dossier"]["evidence_against"] = []
        row["dossier"]["missing_evidence"] = []
    result = compile_contracurator_exhibition(view, ssd_order_foundation=stripped)
    basis = result["provenance"]["ssd_order_foundation"]

    # Removing counterevidence from the basis must not promote anything: the
    # crosswalk stays candidate, the queue stays unanswered, selection is fixed.
    assert basis["crosswalk_status"] == "candidate"
    assert basis["used_for_selection"] is False
    assert basis["operator_review"]["answers_recorded"] == 0
    assert result["status"] == "survived"
    assert len(result["result"]["exhibition"]["source_refs"]) == 8
    assert result["product_episode"]["control"]["database_write"] is False


def test_preexisting_operational_links_are_classified_not_promoted(foundation: dict) -> None:
    """The real bases DO name these ISKVW pieces. None of those links binds."""
    crosswalk = foundation["crosswalk_to_iskvw"]
    audit = crosswalk["binding_audit"]
    linked = [
        row for row in crosswalk["candidate_relations"]
        if row["binding_check"]["typed_reference"]["operational_possible_link_count"]
    ]

    # 20 of the 52 candidates are named by pre-existing operational links.
    assert linked, "the real operational link tables name at least one crosswalk piece"
    assert audit["operational_possible_links"] >= len(linked)
    # Every class present must be a possible link resting on a path token.
    assert audit["operational_possible_link_classes"]
    for label, count in audit["operational_possible_link_classes"].items():
        relation, _, method = label.partition("/")
        assert relation.startswith("possible_"), relation
        assert method == "path_token", method
        assert count > 0
    # And the verdict is unmoved.
    assert crosswalk["typed_reference_count"] == 0
    assert audit["with_typed_reference"] == 0
    for row in linked:
        typed = row["binding_check"]["typed_reference"]
        assert typed["is_typed_reference"] is False
        assert row["selection_eligible"] is False
        for link in typed["operational_possible_links"]:
            assert link["is_typed_reference"] is False
            assert link["endpoint_is_a_crosswalk_ssd_asset"] is False
            assert link["declared_method"] == "path_token"
            assert "path token is not evidence of a work" in link["reason"]
        assert any(
            "declared method is a path token" in item
            for item in row["evidence_against"]
        )


def test_binding_lookup_names_every_base_it_actually_read(foundation: dict) -> None:
    scanned = foundation["crosswalk_to_iskvw"]["binding_audit"]["bases_scanned"]

    # The claim "typed_reference_count=0" is only as strong as the surfaces read,
    # so the surfaces must be enumerated in the payload.
    assert len(scanned) >= 7
    assert any(ref.endswith("#relations") for ref in scanned)
    assert any(ref.endswith("#artifacts") for ref in scanned)
    assert any(ref.endswith("#entity_relations") for ref in scanned)
    assert any(ref.endswith("#operational_curation_links") for ref in scanned)
    assert any(ref.endswith("#mak_links") for ref in scanned)
    assert all(ref.count("#") == 1 and ref.startswith("/") for ref in scanned)
