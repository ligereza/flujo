"""Replay the real classification errors and assert the policy refuses them.

Every test in the first group is an error that actually happened in this
repository, recorded in ``docs/ordering_chaos.md``. A registry that cannot refuse
the mistakes already made is decoration, so each one is stated as the decision
that was taken and asserted to be denied now.

The second group pins the properties that make the registry safe to extend: an
undeclared feature cannot decide anything, a chain is only as strong as its
weakest link, and a fold that declares nothing about a question abstains rather
than assuming it holds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo.knowledge.feature_policy import (
    CONFIDENCE_ORDER,
    CONTRACT,
    FeaturePolicyError,
    UndeclaredFeatureError,
    audit,
    authority,
    confidence_ceiling,
    feature,
    fold_is_valid,
    load_registry,
    may_decide,
    weakest,
)

REPO = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------ the real errors

def test_a_filename_cannot_decide_that_a_file_is_junk():
    """Class 1. 1599 records of the operator's own artworks, read off a hash.

    The filenames looked like ``bf4453cd0709-18029801425410081.md``, I concluded
    machine-generated corpus, and was one step from recommending they all be
    dismissed. They were per-artwork records with concepts, palette and technique.
    """
    for question in ("purpose", "value", "whether a file is junk"):
        verdict = may_decide("filename", question)
        assert not verdict.allowed, f"filename was allowed to decide {question}"
        assert verdict.confidence_ceiling == "none"


def test_a_filename_may_decide_a_track_only_after_the_discography_was_asked():
    """Class 1, the other direction. The same feature was the strongest key.

    MERECEDORA sat in the open-questions list for days and is a released single.
    The distinction is not the feature, it is whether anything was consulted that
    could have said it was wrong.
    """
    alone = may_decide("filename", "track_identity")
    assert not alone.allowed
    assert "artist_discography" in alone.reason

    asked = may_decide("filename", "track_identity", authority_consulted=True)
    assert asked.allowed
    assert asked.confidence_ceiling == "strong"
    assert asked.authority == "artist_discography"
    # Even with the authority it never reaches proof: a common word can match.
    assert asked.confidence_ceiling != "proof"


def test_a_tool_default_name_may_decide_nothing_at_all():
    """Class 1. ('Slice 1', 1920, 1080) produced three false positive rig matches.

    That string is Resolume's default. It is what the file says when the operator
    has said nothing, and it was weighted as though it were a statement.
    """
    for question in ("similarity", "identity", "anything at all"):
        assert not may_decide("tool_default_name", question).allowed
    # Recognising the silence IS a permitted decision, because it converts a false
    # positive into an explicit abstention -- but knowing a name is a default
    # requires knowing the defaults, so it needs its authority like anything else.
    unasked = may_decide("tool_default_name", "that this name carries no information")
    assert not unasked.allowed
    assert "tool_default_registry" in unasked.reason

    asked = may_decide("tool_default_name", "that this name carries no information",
                       authority_consulted=True)
    assert asked.allowed
    assert asked.confidence_ceiling == "proof", "a string comparison is proof"
    # Proof of SILENCE only. It still licenses no similarity claim.
    assert not may_decide("tool_default_name", "similarity",
                          authority_consulted=True).allowed


def test_a_container_decides_provenance_and_never_meaning():
    """Class 2. BERLIN 1 and berlin 2 are the same room with zero shared surfaces.

    A ScreenSetup named after a venue describes a dated deployment. The container
    says who the work was for; it never says what the work is.
    """
    assert may_decide("path_or_container", "provenance").allowed
    assert may_decide("path_or_container",
                      "which client or commission a work belongs to").allowed
    for question in ("meaning", "identity of a place"):
        assert not may_decide("path_or_container", question).allowed


def test_a_hash_proves_identity_and_says_nothing_about_role():
    """Class 6. 44 zero-byte __init__.py files, one purpose, five consumers."""
    proven = may_decide("content_hash", "that two rows are the same content",
                        authority_consulted=True)
    assert proven.allowed and proven.confidence_ceiling == "proof"
    for question in ("purpose", "consumer", "which copy matters more"):
        assert not may_decide("content_hash", question,
                              authority_consulted=True).allowed


def test_a_vision_description_never_reaches_a_geometry_match():
    """Class 5. Of 1818 entries with a machine reading, zero carry the author's.

    Expensive and unrefutable is the worst pair in the table, so the ceiling has
    to sit strictly below the structured features it competes with.
    """
    described = confidence_ceiling("vision_description", authority_consulted=True)
    geometry = confidence_ceiling("vector_or_scene_geometry", authority_consulted=True)
    anchor = confidence_ceiling("structural_anchor")
    assert CONFIDENCE_ORDER.index(described) < CONFIDENCE_ORDER.index(geometry)
    assert CONFIDENCE_ORDER.index(described) < CONFIDENCE_ORDER.index(anchor)
    assert not may_decide("vision_description", "concept").allowed
    assert not may_decide("vision_description", "authorship").allowed


def test_only_a_human_may_decide_authorship_and_publication():
    """Of 2034 archive pieces, 8 carry both a date and the author's own sentence.

    No quantity of machine perception manufactures the other 2026.
    """
    for question in ("authorship", "publication", "value", "concept"):
        assert may_decide("human_attestation", question).allowed
        for name in ("filename", "vision_description", "structural_anchor",
                     "publication_surface", "content_hash"):
            verdict = may_decide(name, question, authority_consulted=True)
            assert not verdict.allowed, (
                f"{name} was allowed to decide {question}")


def test_the_surface_decides_a_work_but_not_whether_it_is_published():
    """The operator's rule, which corrected 240 stories filed as finished work.

    The registry keeps the domain words the operator uses ("obra", "registro")
    as VALUES, because they are what he calls the things. The identifiers
    around them stay English, which is the repository rule.
    """
    assert may_decide("publication_surface", "obra vs registro").allowed  # a declared value
    assert not may_decide("publication_surface", "whether it goes on the web").allowed
    mapping = feature("publication_surface")["mapping"]
    assert mapping["posts"] == "obra" and mapping["reels"] == "obra"
    assert mapping["stories"] == "registro"
    assert mapping["archived_posts"] == "not obra"
    assert "UNRESOLVED" in mapping["other"], (
        "the 330 files in 'other' must stay unresolved until measured")


def test_a_declared_marker_beats_a_list_of_names():
    """The root cause of 1463 queue rows, 17.7% of the whole queue.

    A hand-written skip list missed a Windows virtualenv called ``env``. The
    marker PEP 405 obliges the interpreter to write does not miss it.
    """
    marker = may_decide("declared_marker", "provenance class (installed vs authored)",
                        authority_consulted=True)
    assert marker.allowed and marker.confidence_ceiling == "proof"
    assert not may_decide("declared_marker",
                          "provenance class (installed vs authored)").allowed
    pep = authority("pep_405_environment_marker")
    assert "pyvenv.cfg" in pep["consult"]
    assert pep["failure_mode"], "an authority must declare how it fails"


def test_containment_propagates_a_rejection_and_not_an_acceptance():
    """The asymmetry the project review queue is built on, stated as a fold."""
    assert fold_is_valid("containment", "propagating a REJECTION downward").allowed
    assert not fold_is_valid("containment",
                             "propagating an ACCEPTANCE downward").allowed


def test_folding_by_content_is_valid_for_purpose_and_invalid_for_consumer():
    assert fold_is_valid("content_identity", "purpose").allowed
    assert not fold_is_valid("content_identity", "consumer").allowed
    assert fold_is_valid("directory", "project").allowed
    assert not fold_is_valid("directory", "route").allowed


def test_a_date_window_links_and_never_identifies():
    """The join between the SSD and Instagram is association, not identity."""
    assert fold_is_valid("release_date_window",
                         "linking an obra to the registro that shared it").allowed
    assert not fold_is_valid("release_date_window",
                             "asserting two works are the same").allowed


# ------------------------------------------------- properties of the registry

def test_an_undeclared_feature_cannot_decide_anything():
    """What stops the next quiet shortcut from arriving."""
    with pytest.raises(UndeclaredFeatureError, match="undeclared_feature"):
        may_decide("vibes", "value")
    with pytest.raises(FeaturePolicyError, match="undeclared_folding_relation"):
        fold_is_valid("looks_similar", "purpose")


def test_a_question_the_feature_says_nothing_about_is_refused_not_assumed():
    verdict = may_decide("structural_anchor", "which venue it was shown at")
    assert not verdict.allowed
    assert "does not declare" in verdict.reason


def test_a_fold_that_declares_nothing_abstains():
    verdict = fold_is_valid("directory", "release date")
    assert not verdict.allowed
    assert "declares nothing" in verdict.reason


def test_a_chain_is_as_strong_as_its_weakest_link_never_a_sum():
    """Adding confidences would assert an exchange rate nobody measured."""
    assert weakest("proof", "strong") == "strong"
    assert weakest("strong", "weak", "proof") == "weak"
    assert weakest("proof") == "proof"
    assert weakest() == "none"
    with pytest.raises(FeaturePolicyError, match="unknown_confidence"):
        weakest("strong", "pretty sure")


def test_every_feature_declares_its_cost_authority_and_the_error_that_taught_it():
    registry = load_registry()
    assert registry["schema"] == CONTRACT
    for item in registry["features"]:
        assert item["cost"] in ("free", "cheap", "medium", "expensive", "human")
        assert item["learned_from"], f"{item['name']} has no recorded origin"
        assert item["max_confidence_without_authority"] in CONFIDENCE_ORDER
        assert item["max_confidence_with_authority"] in CONFIDENCE_ORDER
        without = CONFIDENCE_ORDER.index(item["max_confidence_without_authority"])
        with_auth = CONFIDENCE_ORDER.index(item["max_confidence_with_authority"])
        assert with_auth >= without, (
            f"{item['name']} claims less with its authority than without it")


def test_no_free_feature_may_decide_meaning_on_its_own():
    """The single rule that would have prevented most of docs/ordering_chaos.md."""
    report = audit()
    for row in report["rows"]:
        if row["cost"] != "free" or row["alone"] == "none":
            continue
        # path_or_container is the one free feature that decides alone, and only
        # provenance. Anything else appearing here is a regression.
        assert row["feature"] == "path_or_container", (
            f"{row['feature']} is free and decides alone: {row['decides']}")
        assert not any("meaning" in entry or "purpose" in entry
                       for entry in row["decides"])


def test_every_authority_says_how_to_consult_it_and_how_it_fails():
    registry = load_registry()
    for name, item in registry["authorities"].items():
        for field in ("what", "consult", "can_refute", "why_it_exists", "failure_mode"):
            assert item.get(field), f"authority {name} is missing {field}"


def test_the_learning_contract_measures_held_out_decisions():
    """Accuracy on decisions already seen always looks good and means nothing."""
    contract = load_registry()["learning_contract"]
    assert "HELD-OUT" in contract["the_only_honest_metric"]
    assert "abstention" in contract["the_only_honest_metric"].casefold()
    assert contract["negative_result_is_a_result"]


def test_the_prose_record_and_the_registry_stay_together():
    """A registry whose reasoning is gone is a table of magic numbers."""
    prose = REPO / "docs" / "ordering_chaos.md"
    assert prose.is_file(), "docs/ordering_chaos.md is the reasoning behind the registry"
    text = prose.read_text(encoding="utf-8")
    assert "data/ordering_features.json" in text
    for marker in ("Class 1", "Class 2", "Class 3", "Class 4", "Class 5", "Class 6"):
        assert marker in text, f"{marker} disappeared from the error record"


def test_the_registry_is_valid_json_with_no_unreachable_authority():
    registry = load_registry()
    declared = set(registry["authorities"])
    used = {item["refutable_by"] for item in registry["features"]
            if item.get("refutable_by")}
    assert used <= declared
    unused = declared - used
    assert not unused, f"authority declared but never used: {sorted(unused)}"


# ------------------------------------ the authority cache the policy points at

DISCOGRAPHIES = REPO / "data" / "artist_discographies.json"


def _discographies() -> dict:
    return json.loads(DISCOGRAPHIES.read_text(encoding="utf-8"))


def test_the_declared_discography_authority_has_a_durable_local_cache():
    """A policy that names an authority nobody can open is not enforceable.

    ``filename`` may only decide a track identity once ``artist_discography``
    has been consulted. That authority now has a versioned cache with the URL of
    every datum, so a later run can audit the lookup instead of repeating it.
    """
    assert DISCOGRAPHIES.is_file(), (
        "data/ordering_features.json declares artist_discography; "
        "data/artist_discographies.json is where it lives")
    payload = _discographies()
    assert payload["schema"] == "mak-artist-discographies-v1"
    assert payload["containers"], "the cache is empty"
    assert "absence" in payload["purpose"].casefold(), (
        "the cache must state that absence is not evidence")


def test_every_cached_track_carries_the_url_that_proves_it():
    """A release date with no source is the datum this authority exists to refuse."""
    for container, entry in _discographies()["containers"].items():
        for track in entry["tracks"]:
            assert track.get("source_url"), (
                f"{container}: track {track.get('title')!r} has no source_url")
            assert track.get("title"), f"{container}: a track has no title"
        assert entry.get("kind"), f"{container} has no declared kind"
        assert entry.get("confidence") in ("confirmed", "probable", "unknown")


def test_a_container_with_no_tracks_is_allowed_and_says_why():
    """FELINA resolved to nothing and SCD to a venue. Both are real answers.

    An identity probe that returns no discography has not failed: a container can
    be a venue, an event or a logo project. What is not allowed is an empty
    result with no reason attached.
    """
    containers = _discographies()["containers"]
    empty = {name: entry for name, entry in containers.items()
             if not entry["tracks"]}
    assert empty, "the fixture no longer covers the no-tracks case"
    for name, entry in empty.items():
        assert entry.get("why") or entry.get("notes"), (
            f"{name} has no tracks and no explanation")


def test_the_confirmed_matches_that_validated_the_key_are_still_present():
    """If these disappear, the track key lost the evidence that established it."""
    lyon = _discographies()["containers"]["LYON"]
    titles = {track["title"].casefold() for track in lyon["tracks"]}
    for expected in ("la merecedora", "nebula", "comando estelar", "pasajero"):
        assert expected in titles, f"LYON lost the confirmed track {expected!r}"
    dated = {track["title"].casefold(): track["release_date"]
             for track in lyon["tracks"]}
    assert dated["la merecedora"].startswith("2025-12")
    assert dated["nebula"].startswith("2025-10")
