"""Attack the pairing: a source may not support a claim it cannot bear.

`Evidence` used to validate its predicate against a vocabulary and its authority
against a vocabulary, and never validate the PAIR. So "which source may support
which claim" was a discipline somebody had to remember, and it was not
remembered: three measurements in a row were retracted after a signal was used
for a claim outside its reach.

Two rules are pinned here, and each test fails if one is loosened:

- an authority may assert only the predicates declared for it;
- an authority whose measurement is SYMMETRIC may never orient an edge. A digest
  proves two objects are equal, and equality has no direction. A graded overlap
  score is the first thing that would break this, because the temptation with a
  partial-content measure is to read it as "B came from A".

And the cardinality rule: a lookup that can match several objects must say so.
`resolve_external_id` ended in `LIMIT 1` over a query matching document_id, which
is shared by design. Measured on the real corpus: 120 DocumentIDs are carried by
more than one state, group sizes 2 to 8.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flujo.substrate.epistemics import MISSING_EVIDENCE
from flujo.substrate.resolution import Absent, Many, Unique, admits, is_present
from flujo.substrate.schema import (
    ADMISSIBLE_PREDICATES,
    AUTHORITIES,
    DERIVED_FROM,
    DIRECTED_PREDICATES,
    OBSERVED_AT,
    PREDICATES,
    REFERENCES,
    SAME_CONTENT,
    SYMMETRIC_MEASUREMENT_AUTHORITIES,
    SYMMETRIC_PREDICATES,
    ArtifactState,
    Evidence,
    Substrate,
    SubstrateError,
    _check_admissibility_table,
)


def evidence(authority: str, predicate: str) -> Evidence:
    return Evidence(
        evidence_id="e1", subject="state:a", predicate=predicate, object="state:b",
        authority=authority, extractor="test", method="test", search_completeness="exhaustive",
        recorded_at="2026-08-24T00:00:00+00:00")


def test_every_authority_declares_what_it_may_assert() -> None:
    assert set(ADMISSIBLE_PREDICATES) == set(AUTHORITIES)
    for authority, allowed in ADMISSIBLE_PREDICATES.items():
        assert allowed, f"{authority} may assert nothing, which is surely wrong"
        assert allowed <= set(PREDICATES)
    _check_admissibility_table()


def test_a_digest_may_prove_equality() -> None:
    assert evidence("content_digest", SAME_CONTENT).predicate == SAME_CONTENT


def test_a_digest_may_not_orient_an_edge() -> None:
    """The load-bearing test. Equality has no direction."""
    with pytest.raises(SubstrateError) as caught:
        evidence("content_digest", DERIVED_FROM)
    assert "inadmissible_pair" in str(caught.value)
    assert "content_digest" in str(caught.value)


def test_no_symmetric_measurement_is_granted_a_directed_predicate() -> None:
    for authority in SYMMETRIC_MEASUREMENT_AUTHORITIES:
        assert not (ADMISSIBLE_PREDICATES[authority] & DIRECTED_PREDICATES)


def test_the_table_is_checked_at_import_not_at_first_write(monkeypatch) -> None:
    """A bad row is a design error, so it must fail before any record hits it."""
    monkeypatch.setitem(ADMISSIBLE_PREDICATES, "content_digest",
                        frozenset({SAME_CONTENT, DERIVED_FROM}))
    with pytest.raises(SubstrateError) as caught:
        _check_admissibility_table()
    assert "symmetric_measurement_may_not_orient" in str(caught.value)


def test_the_filesystem_may_not_claim_a_derivation() -> None:
    with pytest.raises(SubstrateError):
        evidence("filesystem", DERIVED_FROM)
    assert evidence("filesystem", OBSERVED_AT).predicate == OBSERVED_AT


def test_a_regex_over_bytes_may_only_say_a_path_was_mentioned() -> None:
    assert evidence("resolume_reference_regex", REFERENCES)
    with pytest.raises(SubstrateError):
        evidence("resolume_reference_regex", DERIVED_FROM)


def test_the_operator_is_the_one_audited_downgrade() -> None:
    """A human may orient an edge from judgement. Nothing else may."""
    for predicate in PREDICATES:
        assert evidence("operator", predicate).predicate == predicate


def test_symmetric_and_directed_partition_the_vocabulary() -> None:
    assert not (SYMMETRIC_PREDICATES & DIRECTED_PREDICATES)
    assert SYMMETRIC_PREDICATES | DIRECTED_PREDICATES | {OBSERVED_AT} == set(PREDICATES)


# ------------------------------------------------------------------ cardinality

def state(name: str, *, document_id: str) -> ArtifactState:
    return ArtifactState(state_id=f"state:{name}", document_id=document_id,
                         id_source="xmp_instance_id")


def test_a_shared_document_id_resolves_to_many_not_to_one(tmp_path: Path) -> None:
    """A shared DocumentID is what a lineage IS, so k > 1 is the normal case."""
    sub = Substrate(tmp_path / "s.db")
    for name in ("a", "b", "c"):
        sub.put_state(state(name, document_id="SHARED"))
    resolved = sub.resolve_external_id("xmp:SHARED")
    assert isinstance(resolved, Many)
    assert resolved.k == 3
    # Present, because "this id resolves here" survives the collision...
    assert is_present(resolved) is True
    # ...but it cannot name WHICH state, at any arity.
    assert admits(resolved, arity=1) is False


def test_a_unique_document_id_still_individuates(tmp_path: Path) -> None:
    """The counterexample: k == 1 makes the individuating claim admissible."""
    sub = Substrate(tmp_path / "s.db")
    sub.put_state(state("only", document_id="LONELY"))
    resolved = sub.resolve_external_id("xmp:LONELY")
    assert isinstance(resolved, Unique)
    assert admits(resolved, arity=1) is True


def test_an_id_the_corpus_lacks_is_absent_with_a_cause(tmp_path: Path) -> None:
    sub = Substrate(tmp_path / "s.db")
    resolved = sub.resolve_external_id("xmp:NOWHERE")
    assert isinstance(resolved, Absent)
    assert resolved.cause == MISSING_EVIDENCE
    assert is_present(resolved) is False


def test_a_resolution_is_truthy_so_truthiness_must_never_be_used() -> None:
    """Pins the trap. `if resolve(...)` reads Absent as success."""
    absent = Absent(cause=MISSING_EVIDENCE)
    assert bool(absent) is True, "if this is False the trap is gone, update the note"
    assert is_present(absent) is False


def test_candidate_count_survives_the_database(tmp_path: Path) -> None:
    """A field nobody persists is a field nobody has.

    This asserts the round trip, because the risk with a new column is not that
    the dataclass forgets it but that the INSERT does.
    """
    sub = Substrate(tmp_path / "s.db")
    sub.put_evidence(Evidence(
        evidence_id="amb", subject="state:a", predicate=REFERENCES,
        object="basename:normal.jpg", authority="resolume_reference_regex",
        extractor="test", method="test", search_completeness="bounded",
        recorded_at="2026-08-24T00:00:00+00:00", candidate_count=29))
    row = next(e for e in sub.edges() if e["evidence_id"] == "amb")
    assert row["candidate_count"] == 29


def test_the_deficit_is_readable_from_a_stored_row() -> None:
    ambiguous = Evidence(
        evidence_id="e", subject="state:a", predicate=REFERENCES,
        object="basename:x", authority="resolume_reference_regex",
        extractor="t", method="t", search_completeness="bounded",
        recorded_at="2026-08-24T00:00:00+00:00", candidate_count=8)
    assert ambiguous.individuating_deficit_bits == 3.0
    unique = Evidence(
        evidence_id="e2", subject="state:a", predicate=REFERENCES,
        object="basename:x", authority="resolume_reference_regex",
        extractor="t", method="t", search_completeness="bounded",
        recorded_at="2026-08-24T00:00:00+00:00", candidate_count=1)
    assert unique.individuating_deficit_bits == 0.0


def test_a_directed_edge_may_not_point_at_an_ambiguous_state(tmp_path: Path) -> None:
    """The rule with teeth: 8 candidates is 8 times one too many."""
    with pytest.raises(SubstrateError) as caught:
        Evidence(
            evidence_id="bad", subject="state:a", predicate=DERIVED_FROM,
            object="state:one_of_eight", authority="xmp_packet",
            extractor="t", method="t", search_completeness="exhaustive",
            recorded_at="2026-08-24T00:00:00+00:00",
            object_kind="state", candidate_count=8)
    assert "ambiguous_referent_for_directed_edge" in str(caught.value)
    # The operator may, because a human orienting an edge from judgement is the
    # one audited downgrade in the system.
    assert Evidence(
        evidence_id="ok", subject="state:a", predicate=DERIVED_FROM,
        object="state:one_of_eight", authority="operator",
        extractor="t", method="t", search_completeness="exhaustive",
        recorded_at="2026-08-24T00:00:00+00:00",
        object_kind="state", candidate_count=8)
