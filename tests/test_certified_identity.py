"""Attack the bridge: certified identity must not become a second system.

Each test fails if a specific way of losing the plot is reintroduced:

- the new predicate without a declared inverse. ``inverse_relation`` refuses to
  guess, and it refuses because a silent guess is how 24 ``contains`` edges once
  became 56 with half of them pointing backwards.
- a shared purchased input reported as a shared work. That confusion is the
  reason 758 of 917 baseline rows described a downloaded model as a project.
- a shared OUTPUT reported as a certified anything. Identical bytes have two
  readings and content cannot choose between them, so the pair must stay a tie
  with both alternatives preserved.
- a question raised where the machine already knows the answer. A loose file at
  the top of the disk and a folder nested inside another are facts about the
  filesystem; spending operator attention on them is the failure the review
  queue was built to avoid.
- a lexical gate. The prior comparison only looked at roots sharing a four
  character prefix, so LYON and SCD were never compared despite sharing 191
  certified contents.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from flujo.knowledge import certified_identity as ci
from flujo.knowledge.project_reconstruction import (
    EMPIRICAL,
    REL_SHARES_LIBRARY_WITH,
    UNKNOWN,
    inverse_relation,
)


def build_index(tmp_path: Path, assets: list[tuple[str, str, str]]) -> Path:
    """A minimal archive index: (asset_id, relative_path, media_kind)."""
    path = tmp_path / "index.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE assets (asset_id TEXT, relative_path TEXT, "
                "media_kind TEXT, extension TEXT, bytes INTEGER)")
    con.executemany("INSERT INTO assets VALUES (?,?,?,?,?)",
                    [(a, p, k, Path(p).suffix, 100) for a, p, k in assets])
    con.commit()
    con.close()
    return path


def build_identity(classes: list[dict]) -> ci.IdentityIndex:
    index = ci.IdentityIndex()
    for entry in classes:
        content_id = entry["content_id"]
        index.classes[content_id] = ci.ContentClass(
            content_id=content_id, member_count=len(entry["members"]),
            bytes_each=entry.get("bytes_each", 100),
            reclaimable_bytes=entry.get("bytes_each", 100) * (len(entry["members"]) - 1),
            roots=tuple(entry["roots"]), extensions=tuple(entry.get("extensions", ())),
            crosses_roots=len(set(entry["roots"])) > 1)
        for asset_id in entry["members"]:
            index.content_of[asset_id] = content_id
            index.verdict_of[asset_id] = ci.CERTIFIED_SAME
            index.members_of[content_id].append(asset_id)
    return index


def test_the_new_predicate_has_a_declared_inverse() -> None:
    ci.register_predicate()
    assert inverse_relation(ci.REL_SHARES_OUTPUT_WITH) == ci.REL_SHARES_OUTPUT_WITH


def test_shared_source_is_library_reuse_not_one_work(tmp_path: Path) -> None:
    index = build_index(tmp_path, [
        ("a1", "LYON/textures/hdri.blend", "structural"),
        ("a2", "SCD/textures/hdri.blend", "structural"),
    ])
    identity = build_identity([
        {"content_id": "sha256:aa", "members": ["a1", "a2"],
         "roots": ["LYON", "SCD"], "extensions": [".blend"]}])
    overlaps = ci.root_overlaps(index, identity)
    assert len(overlaps) == 1
    relation = ci.identity_relations(overlaps)[0]
    assert relation.relation == REL_SHARES_LIBRARY_WITH
    assert relation.epistemic_status == EMPIRICAL
    # And the counter-evidence stays attached: reuse is not identity.
    assert any("not make two commissions one work" in e.detail
               for e in relation.evidence_against)
    assert ci.open_questions([relation], overlaps) == []


def test_shared_output_stays_a_tie_with_both_readings(tmp_path: Path) -> None:
    index = build_index(tmp_path, [
        ("a1", "DREFGIRA/ESCARLATA.mp4", "video"),
        ("a2", "DrefQuila/ESCARLATA.mp4", "video"),
    ])
    identity = build_identity([
        {"content_id": "sha256:bb", "members": ["a1", "a2"],
         "roots": ["DREFGIRA", "DrefQuila"], "bytes_each": 2 << 30}])
    overlaps = ci.root_overlaps(index, identity)
    relation = ci.identity_relations(overlaps)[0]
    assert relation.relation == ci.REL_SHARES_OUTPUT_WITH
    # The load-bearing assertion: certified bytes do NOT certify the relation.
    assert relation.epistemic_status == UNKNOWN
    assert set(relation.alternatives) == {"same_work_under_two_names",
                                          "output_reused_in_a_second_commission"}
    questions = ci.open_questions([relation], overlaps)
    assert len(questions) == 1
    assert questions[0]["why_not_machine_answerable"]
    # An example from each side, so the question is legible without a lookup.
    assert questions[0]["examples"][:2] == ["DREFGIRA/ESCARLATA.mp4",
                                            "DrefQuila/ESCARLATA.mp4"]


def test_a_loose_file_at_the_disk_root_is_never_a_question(tmp_path: Path) -> None:
    index = build_index(tmp_path, [
        ("a1", "2.mov", "video"),                       # loose at the top
        ("a2", "BAHPARTY/bah/2.mov", "video"),
    ])
    identity = build_identity([
        {"content_id": "sha256:cc", "members": ["a1", "a2"],
         "roots": ["2.mov", "BAHPARTY"]}])
    overlaps = ci.root_overlaps(index, identity)
    assert overlaps[0].loose is True
    relation = ci.identity_relations(overlaps)[0]
    assert relation.epistemic_status == EMPIRICAL
    assert ci.open_questions([relation], overlaps) == []


def test_a_folder_and_its_own_ancestor_is_never_a_question(tmp_path: Path) -> None:
    index = build_index(tmp_path, [
        ("a1", "DREFGIRA/x.mp4", "video"),
        ("a2", "DREFGIRA/OPCIONES/x.mp4", "video"),
    ])
    identity = build_identity([
        {"content_id": "sha256:dd", "members": ["a1", "a2"],
         "roots": ["DREFGIRA", "DREFGIRA/OPCIONES"]}])
    overlaps = ci.root_overlaps(index, identity)
    assert overlaps[0].nested is True
    relation = ci.identity_relations(overlaps)[0]
    assert relation.epistemic_status == EMPIRICAL
    assert any("counted twice by the folder scan" in e.detail
               for e in relation.evidence_for)
    assert ci.open_questions([relation], overlaps) == []


def test_a_declaration_turns_a_shared_image_into_a_shared_input(tmp_path: Path) -> None:
    """The evidence that only a .blend can supply.

    An image is a texture or a rendered frame and ``media_kind`` says "image"
    for both. Without the declaration this pair is a question; with it, it is
    library reuse and the operator is never asked.
    """
    index = build_index(tmp_path, [
        ("a1", "LYON/COMANDO/textures/park_parking_4k.exr", "image"),
        ("a2", "SCD/textures/park_parking_4k.exr", "image"),
    ])
    identity = build_identity([
        {"content_id": "sha256:ee", "members": ["a1", "a2"],
         "roots": ["LYON", "SCD"]}])

    without = ci.identity_relations(ci.root_overlaps(index, identity))[0]
    assert without.epistemic_status == UNKNOWN, "an image alone cannot be decided"

    overlaps = ci.root_overlaps(index, identity,
                                declarations={"park_parking_4k.exr": 3})
    with_declaration = ci.identity_relations(overlaps)[0]
    assert with_declaration.relation == REL_SHARES_LIBRARY_WITH
    assert with_declaration.epistemic_status == EMPIRICAL
    assert ci.open_questions([with_declaration], overlaps) == []
    # The weakness of basename matching is stated, not hidden.
    assert any("collision is possible" in e.detail
               for e in with_declaration.evidence_for)


def test_roots_with_no_lexical_similarity_are_still_compared(tmp_path: Path) -> None:
    """The gate that hid LYON against SCD for a whole reconstruction."""
    index = build_index(tmp_path, [
        ("a1", "LYON/a.mp4", "video"),
        ("a2", "SCD/a.mp4", "video"),
    ])
    identity = build_identity([
        {"content_id": "sha256:ff", "members": ["a1", "a2"],
         "roots": ["LYON", "SCD"]}])
    overlaps = ci.root_overlaps(index, identity)
    assert [(o.left, o.right) for o in overlaps] == [("LYON", "SCD")]


def test_content_confined_to_one_root_makes_no_pair(tmp_path: Path) -> None:
    index = build_index(tmp_path, [("a1", "LYON/a.mp4", "video"),
                                   ("a2", "LYON/b/a.mp4", "video")])
    identity = build_identity([
        {"content_id": "sha256:11", "members": ["a1", "a2"], "roots": ["LYON"]}])
    assert ci.root_overlaps(index, identity) == []


def test_questions_are_sorted_by_leverage(tmp_path: Path) -> None:
    index = build_index(tmp_path, [
        ("s1", "A/small.mp4", "video"), ("s2", "B/small.mp4", "video"),
        ("b1", "C/big.mp4", "video"), ("b2", "D/big.mp4", "video")])
    identity = build_identity([
        {"content_id": "sha256:small", "members": ["s1", "s2"],
         "roots": ["A", "B"], "bytes_each": 10},
        {"content_id": "sha256:big", "members": ["b1", "b2"],
         "roots": ["C", "D"], "bytes_each": 10_000}])
    overlaps = ci.root_overlaps(index, identity)
    questions = ci.open_questions(ci.identity_relations(overlaps), overlaps)
    assert [q["shared_bytes"] for q in questions] == [10_000, 10]


def test_triage_cuts_by_leverage_and_keeps_the_residue() -> None:
    questions = [{"left": f"L{i}", "right": f"R{i}", "shared_bytes": b,
                  "shared_classes": 1, "question": "?", "answers": [],
                  "examples": [], "why_not_machine_answerable": "operator"}
                 for i, b in enumerate([1000, 500, 300, 10, 5, 1, 1, 1])]
    out = ci.triage(questions, coverage=0.9)
    assert out["asked_count"] == 3
    assert [q["shared_bytes"] for q in out["ask"]] == [1000, 500, 300]
    assert out["deferred_count"] == 5
    # Nothing vanishes, and the cut is stated rather than implied.
    assert out["asked_count"] + out["deferred_count"] == len(questions)
    assert out["deferred_bytes"] == 18
    assert "stopped at 90% coverage" in out["cut_rule"]


def test_every_deferred_question_carries_a_monitor() -> None:
    """A fold that cannot be suspected is indistinguishable from an answer."""
    questions = [{"left": "A", "right": "B", "shared_bytes": b,
                  "shared_classes": 1, "question": "?", "answers": [],
                  "examples": [], "why_not_machine_answerable": "operator"}
                 for b in (1000, 1)]
    out = ci.triage(questions, coverage=0.5)
    assert out["deferred"], "nothing was deferred, the test proves nothing"
    for question in out["deferred"]:
        assert question["reopen_when"]
        # The monitor must be observable WITHOUT knowing the answer, or it can
        # never fire. A root name is; the work identity is not.
        assert "query names" in question["reopen_when"]


def test_triage_respects_a_hard_question_ceiling() -> None:
    questions = [{"left": f"L{i}", "right": "R", "shared_bytes": 100,
                  "shared_classes": 1, "question": "?", "answers": [],
                  "examples": [], "why_not_machine_answerable": "operator"}
                 for i in range(40)]
    out = ci.triage(questions, coverage=1.0, max_asked=5)
    assert out["asked_count"] == 5
    assert out["deferred_count"] == 35


def test_a_blend_declaring_the_exact_path_vetoes_a_safe_proposal(tmp_path: Path) -> None:
    """The second dependency check, and it verifies rather than guesses.

    The Resolume check can only match a basename, because that is all a
    composition offers. A ``//`` declaration in a .blend resolves against the
    .blend's own directory, so this one is an exact path and can only produce a
    true hold.
    """
    import importlib.util
    tool_path = Path(__file__).resolve().parents[1] / "tools" / "order_projection.py"
    spec = importlib.util.spec_from_file_location("order_projection_mod", tool_path)
    order = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(order)

    entry = {"content_id": "sha256:aa", "bytes_each": 100,
             "reclaimable_bytes": 100, "roots": ["x.png", "LYON"],
             "members": ["x.png", "LYON/tex/x.png"], "strays": ["x.png"]}

    free = order.propose_safe_actions([entry], {}, set())
    assert free[0]["verdict"] == order.SAFE

    vetoed = order.propose_safe_actions([entry], {}, {"x.png"})
    assert vetoed[0]["verdict"] == order.HOLD_BLEND
    assert "EXACT path" in vetoed[0]["held_because"]

    # A show veto outranks a blend veto: both are holds, and the show is the
    # one that already happened in front of an audience.
    both = order.propose_safe_actions([entry], {"x.png": ["sampier"]}, {"x.png"})
    assert both[0]["verdict"] == order.HOLD
