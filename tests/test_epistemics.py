"""Attack the ASSERTED/PROVEN split: a declaration must never pass for a witness.

Each test fails if the old collapse -- treating vocabulary=YES typed into a
dict as though it were a measurement -- comes back.

The forcing case throughout is the one recorded in epistemics.py: a scan
flagged 1372 QuickTime files as fully traversed with a complete vocabulary and
found 0 XMP packets, while a crude window scan of the same files found 180.
The vocabulary was ASSERTED complete and was false, because the walker looked
only for Adobe's uuid box and QuickTime stores the packet in an atom named
XMP_.
"""

from __future__ import annotations

import pytest

from flujo.substrate.epistemics import (
    ASSERTED,
    DECODER_LIMIT,
    CONFLICT,
    INCOMPLETE_AUTHORITY,
    INVALID_QUERY,
    KNOWN_CONTAINERS,
    MISSING_EVIDENCE,
    NO,
    OUT_OF_DOMAIN,
    REMEDY,
    UNASSESSED,
    UNKNOWN_CAUSES,
    VERDICTS,
    YES,
    Completeness,
    EpistemicError,
    Witness,
)


def _witness(**overrides) -> Witness:
    fields = {
        "spec_citation": "test spec clause",
        "adversarial_check": "whole-file scan of a test sample",
        "files_checked": 42,
    }
    fields.update(overrides)
    return Witness(**fields)


# ------------------------------------------------- 1 & 2: the whole point

def test_asserted_looking_vocabulary_without_a_witness_is_not_evidence():
    """traversal YES and vocabulary YES, but no witness: still no license.

    This is exactly the isobmff shape before this module existed: both flags
    would read YES, and the old boolean collapse would say a miss is evidence
    of absence. It is not, absent a witness.
    """
    claim = Completeness(traversal=YES, vocabulary=YES)
    assert claim.witness is None
    assert claim.negative_is_evidence is False


def test_the_same_claim_with_a_witness_is_evidence():
    claim = Completeness(traversal=YES, vocabulary=YES, witness=_witness())
    assert claim.negative_is_evidence is True


# ------------------------------------------------- 3: what a witness must be

def test_a_witness_with_an_empty_spec_citation_is_rejected():
    with pytest.raises(EpistemicError):
        _witness(spec_citation="")
    with pytest.raises(EpistemicError):
        _witness(spec_citation="   ")  # whitespace-only is still empty


def test_a_witness_that_checked_zero_files_is_rejected():
    with pytest.raises(EpistemicError):
        _witness(files_checked=0)


def test_a_witness_with_an_empty_adversarial_check_is_rejected():
    with pytest.raises(EpistemicError):
        _witness(adversarial_check="")


def test_a_well_formed_witness_is_accepted():
    w = _witness()
    assert w.spec_citation and w.adversarial_check and w.files_checked > 0


# ------------------------------------------------- 4: KNOWN_CONTAINERS re-grade

def test_no_known_container_entry_claims_yes():
    """Every entry is ASSERTED or NO; none has had the adversarial check run.

    The count is asserted too, so adding a new format without a Witness trips
    this test rather than silently reintroducing a YES.
    """
    assert len(KNOWN_CONTAINERS) == 4
    for fmt, entry in KNOWN_CONTAINERS.items():
        assert entry["vocabulary_complete"] in (ASSERTED, NO), (
            f"{fmt}: vocabulary_complete must be ASSERTED or NO, "
            f"never YES without a Witness")
        assert entry["vocabulary_complete"] != YES


def test_known_container_grades_match_the_measured_state():
    assert KNOWN_CONTAINERS["png"]["vocabulary_complete"] == ASSERTED
    assert KNOWN_CONTAINERS["jpeg"]["vocabulary_complete"] == ASSERTED
    assert KNOWN_CONTAINERS["isobmff"]["vocabulary_complete"] == ASSERTED
    assert KNOWN_CONTAINERS["generic"]["vocabulary_complete"] == NO
    # Every entry names exactly what would upgrade it, so the path off
    # ASSERTED is data rather than folklore.
    for fmt, entry in KNOWN_CONTAINERS.items():
        assert entry.get("upgrade_check"), f"{fmt}: no upgrade_check recorded"


# ------------------------------------------------- 5: ASSERTED is legal

def test_asserted_is_a_legal_verdict():
    assert ASSERTED in VERDICTS
    Completeness(vocabulary=ASSERTED)  # must not raise


def test_a_bogus_verdict_still_raises():
    with pytest.raises(EpistemicError):
        Completeness(vocabulary="probably")


# ------------------------------------------------- 6: the claim text

def test_strongest_negative_claim_names_the_asserted_gap():
    claim = Completeness(traversal=YES, vocabulary=ASSERTED)
    text = claim.strongest_negative_claim
    assert "ASSERTED" in text
    assert "PROVEN" in text


def test_the_quicktime_numbers_are_recorded_somewhere_in_the_module():
    import flujo.substrate.epistemics as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "1372" in source
    assert "180" in source
    # 0 packets found is the measurement; check it appears as its own claim,
    # not just as an incidental digit somewhere in the file.
    assert "0 XMP packets" in source or "found 0" in source


# ------------------------------------------------- 7: UNKNOWN causes unchanged

def test_six_unknown_causes_each_have_a_distinct_remedy():
    """Not a duplicate of test_substrate.py's version: just a guard that this
    module's own change did not touch the UNKNOWN taxonomy."""
    assert len(UNKNOWN_CAUSES) == 6
    assert set(UNKNOWN_CAUSES) == {
        MISSING_EVIDENCE, INCOMPLETE_AUTHORITY, OUT_OF_DOMAIN,
        DECODER_LIMIT, CONFLICT, INVALID_QUERY,
    }
    for cause in UNKNOWN_CAUSES:
        assert cause in REMEDY and REMEDY[cause]
    assert len({REMEDY[c] for c in UNKNOWN_CAUSES}) == 6


# ------------------------------------------------- 8: as_dict keys intact

def test_as_dict_still_carries_the_keys_other_modules_read():
    claim = Completeness(traversal=YES, vocabulary=YES, witness=_witness())
    out = claim.as_dict()
    for key in ("contract", "traversal", "vocabulary", "authority", "corpus",
                "semantic", "negative_is_evidence", "strongest_negative_claim",
                "note"):
        assert key in out
    assert out["negative_is_evidence"] is True
    assert isinstance(out["negative_is_evidence"], bool)


def test_as_dict_witness_is_none_when_unwitnessed():
    out = Completeness(traversal=YES, vocabulary=YES).as_dict()
    assert out["witness"] is None
    assert out["negative_is_evidence"] is False
