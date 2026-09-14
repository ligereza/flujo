"""Why something is unknown, and what kind of completeness was actually achieved.

Two vocabularies that were previously collapsed, each collapse having produced a
measured failure.

**Causes of UNKNOWN.** A single UNKNOWN cannot be acted on. "I have no evidence"
and "two adapters disagree" and "my decoder cannot read this format" call for
three different next steps -- ask, adjudicate, write an adapter -- and a caller
that sees only UNKNOWN takes none of them. The causes are kept internally and
may collapse to a bare UNKNOWN at the boundary.

**Levels of completeness.** The previous version had one boolean, and it lied.
During the scan that found zero XMP packets in 1372 QuickTime files, every one
of those files was flagged ``exhaustive`` -- true, because the walker had visited
every node of the tree it knew how to traverse, and useless, because it was
looking for Adobe's ``uuid`` box in a container that stores the packet in an
atom named ``XMP_``. The flag described an intention to traverse, not coverage.

So completeness is five separate questions and NONE implies the next:

    traversal   did the walker visit every node of the structure it traverses?
    vocabulary  is the set of packet-bearing containers it knows complete for
                this format?                                  <- FALSE for .mov
    authority   did the authority reach every member of the group?
    corpus      is the corpus itself complete over the domain of the question?
    semantic    does absence of the evidence imply absence of the fact?

The .mov failure lived entirely in the gap between the first and the second, and
there was no field able to express it. That is why this module exists.

**ASSERTED vs PROVEN.** The vocabulary verdict above still came from a hand
typed table, ``KNOWN_CONTAINERS``, and treating a dict entry as a measurement is
exactly the closed-world assumption that produced the .mov failure in the first
place: vocabulary_complete was YES for isobmff, nobody had run an adversarial
check against real QuickTime files, and a scan then flagged 1372 of them as
vocabulary complete and found 0 XMP packets, while a crude window scan of the
same files found 180. So a fourth verdict, ASSERTED, separates "someone declared
this" from YES, which now means "a witness backs this". A witness is defined as
data in the ``Witness`` dataclass below: a cited spec clause for the container
set, plus an adversarial whole-file scan of real data that found nothing outside
the declared containers, recorded with the file count it covered. Only a
``Completeness`` carrying a real ``Witness`` may license ``negative_is_evidence``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT = "mak-epistemics-v1"

# --------------------------------------------------------- causes of UNKNOWN

MISSING_EVIDENCE = "MISSING_EVIDENCE"
"""No evidence was found. The next step is to look somewhere else, or to ask."""

INCOMPLETE_AUTHORITY = "INCOMPLETE_AUTHORITY"
"""Evidence exists but the authority did not cover every member. Extend coverage."""

OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
"""The question does not apply to this object. Not a gap; a category error."""

DECODER_LIMIT = "DECODER_LIMIT"
"""This layer cannot read the format or the container. Write an adapter."""

CONFLICT = "CONFLICT"
"""Two pieces of evidence disagree. Adjudicate; never average."""

INVALID_QUERY = "INVALID_QUERY"
"""The question is malformed for this vocabulary. Fix the question."""

UNKNOWN_CAUSES = (MISSING_EVIDENCE, INCOMPLETE_AUTHORITY, OUT_OF_DOMAIN,
                  DECODER_LIMIT, CONFLICT, INVALID_QUERY)

# What a caller should do next. Kept beside the cause because a cause whose
# remedy is unstated tends to be treated as a dead end.
REMEDY = {
    MISSING_EVIDENCE: "look elsewhere, or ask the operator",
    INCOMPLETE_AUTHORITY: "extend the authority's coverage over the group",
    OUT_OF_DOMAIN: "nothing: the question does not apply here",
    DECODER_LIMIT: "write or fix an adapter for this format",
    CONFLICT: "adjudicate between the disagreeing sources",
    INVALID_QUERY: "restate the question in the declared vocabulary",
}

# ------------------------------------------------------- completeness levels

TRAVERSAL = "traversal"
VOCABULARY = "vocabulary"
AUTHORITY = "authority"
CORPUS = "corpus"
SEMANTIC = "semantic"

COMPLETENESS_LEVELS = (TRAVERSAL, VOCABULARY, AUTHORITY, CORPUS, SEMANTIC)

LEVEL_MEANING = {
    TRAVERSAL: "every node of the structure this walker traverses was visited",
    VOCABULARY: "the set of packet-bearing containers this walker knows is "
                "complete for the format",
    AUTHORITY: "the authority produced evidence for every member of the group",
    CORPUS: "the corpus is complete over the domain of the question",
    SEMANTIC: "absence of this evidence implies absence of the fact",
}

# A level may be asserted, denied, backed by a witness, or simply not assessed.
# UNASSESSED is the honest default the old boolean could not express; ASSERTED
# is the one this module did not have until the isobmff entry below proved it
# was needed: "declared true" and "shown true" are different claims, and only
# YES here means the second one.
YES = "yes"
NO = "no"
UNASSESSED = "unassessed"
ASSERTED = "asserted"
VERDICTS = (YES, NO, UNASSESSED, ASSERTED)


class EpistemicError(ValueError):
    """A completeness claim or an UNKNOWN cause was stated outside the vocabulary."""


@dataclass(frozen=True)
class Witness:
    """What promotes a vocabulary claim from ASSERTED to PROVEN (YES).

    Both fields below must be substantively present, not merely typed: a
    citation gives clause (a), the container set is normative; the adversarial
    check plus its file count gives clause (b), the set was tested against real
    data and nothing was found outside it. Either half missing is exactly the
    isobmff gap -- a citation with no check behind it -- so the constructor
    rejects a Witness that cannot back both halves.
    """

    spec_citation: str
    adversarial_check: str
    files_checked: int

    def __post_init__(self) -> None:
        if not self.spec_citation.strip():
            raise EpistemicError("witness_missing_spec_citation")
        if not self.adversarial_check.strip():
            raise EpistemicError("witness_missing_adversarial_check")
        if self.files_checked <= 0:
            raise EpistemicError("witness_checked_zero_files")


@dataclass(frozen=True)
class Completeness:
    """Five independent verdicts. None of them implies another."""

    traversal: str = UNASSESSED
    vocabulary: str = UNASSESSED
    authority: str = UNASSESSED
    corpus: str = UNASSESSED
    semantic: str = NO           # default NO: tools strip metadata, so absence of
                                 # evidence never implies absence of the fact.
    witness: Witness | None = None
    note: str = ""

    def __post_init__(self) -> None:
        for level in COMPLETENESS_LEVELS:
            value = getattr(self, level)
            if value not in VERDICTS:
                raise EpistemicError(f"bad_{level}_verdict: {value}")

    @property
    def negative_is_evidence(self) -> bool:
        """A miss means something only when traversal AND vocabulary both hold
        AND the vocabulary claim is backed by a witness, not merely declared.

        The witness clause exists because the first two conditions alone were
        already met, and false, once: vocabulary_complete was YES (now ASSERTED)
        for isobmff with no witness ever run, and a scan flagged 1372 QuickTime
        files as vocabulary complete on that assertion alone, finding 0 XMP
        packets where a crude window scan of the same files found 180. Semantic
        completeness would be needed to go further still, and it is never
        available for embedded metadata, so even a witnessed negative stops at
        the decoder's claim: "no packet exists in this file under a PROVEN
        complete vocabulary" -- which is NOT "this file has no provenance".
        """
        return (self.traversal == YES and self.vocabulary == YES
                and self.witness is not None)

    @property
    def strongest_negative_claim(self) -> str:
        """The exact sentence a negative from this search is allowed to be."""
        if self.traversal != YES:
            return "nothing: the structure was not fully traversed"
        if self.vocabulary == ASSERTED:
            return ("nothing: the vocabulary is ASSERTED, not PROVEN -- a "
                    "declaration with no witness behind it. An assertion alone "
                    "produced exactly this false completeness once: 1372 "
                    "QuickTime files were flagged vocabulary complete, the scan "
                    "found 0 XMP packets in them, and a crude window scan of "
                    "the same files found 180")
        if self.vocabulary != YES:
            return ("nothing: the walker's container vocabulary is not known to be "
                    "complete for this format, which is exactly the .mov failure")
        if self.semantic == YES:
            return "the fact is absent"
        return ("no evidence of this kind exists in this object, under this "
                "decoder version. NOT that the fact is absent.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "traversal": self.traversal,
            "vocabulary": self.vocabulary,
            "authority": self.authority,
            "corpus": self.corpus,
            "semantic": self.semantic,
            "witness": (
                {
                    "spec_citation": self.witness.spec_citation,
                    "adversarial_check": self.witness.adversarial_check,
                    "files_checked": self.witness.files_checked,
                }
                if self.witness is not None else None
            ),
            "negative_is_evidence": self.negative_is_evidence,
            "strongest_negative_claim": self.strongest_negative_claim,
            "note": self.note,
        }


@dataclass(frozen=True)
class Unknown:
    """An UNKNOWN with its cause kept, and its remedy stated."""

    cause: str
    detail: str = ""
    completeness: Completeness | None = None

    def __post_init__(self) -> None:
        if self.cause not in UNKNOWN_CAUSES:
            raise EpistemicError(f"undeclared_unknown_cause: {self.cause}")

    @property
    def remedy(self) -> str:
        return REMEDY[self.cause]

    def outward(self) -> str:
        """What a consumer outside this layer sees. The cause stays inside."""
        return "UNKNOWN"

    def as_dict(self) -> dict[str, Any]:
        out = {
            "contract": CONTRACT,
            "verdict": "UNKNOWN",
            "cause": self.cause,
            "remedy": self.remedy,
            "detail": self.detail,
        }
        if self.completeness is not None:
            out["completeness"] = self.completeness.as_dict()
        return out


# The vocabulary a walker declares for a format. Kept as data so a gap is
# visible rather than implicit in code, which is what hid the .mov failure.
#
# An entry may be YES only when the adversarial check (b) was actually run and
# recorded as a Witness. ASSERTED means the containers are named and justified
# but the check is still absent or ineligible. "upgrade_check" names exactly
# what would need to be run to move an entry to YES, so the path off ASSERTED
# is data too.
KNOWN_CONTAINERS: dict[str, dict[str, Any]] = {
    "png": {
        "containers": [
            "iTXt chunk keyed XML:com.adobe.xmp, deflated or plain",
            "legacy tEXt chunk keyed XML:com.adobe.xmp",
        ],
        "vocabulary_complete": ASSERTED,
        "why": "The PNG specification registers XML:com.adobe.xmp for iTXt; "
               "real Adobe exports in this corpus also use the older tEXt "
               "chunk with that keyword. The first complete scan found zero "
               "markers outside both containers in 14327 readable PNGs, but "
               "17 extension-named sidecars were not PNGs and one PNG lacked "
               "IEND; the full 14345-candidate witness therefore remains "
               "ineligible.",
        "upgrade_check": "rerun against a declared valid-PNG corpus, or "
                          "resolve the 18 invalid extension candidates, then "
                          "record the no-outside-marker result as a Witness",
    },
    "jpeg": {
        "containers": ["APP1 with the Adobe XAP header",
                       "APP1 with the Extended XMP header"],
        "vocabulary_complete": ASSERTED,
        "why": "XMP part 3 defines these two for JPEG, so clause (a) holds. "
               "Clause (b) does not: no whole-file adversarial scan of the "
               "corpus JPEGs has been run to confirm no packet lives "
               "elsewhere, so this is asserted, not proven.",
        "upgrade_check": "whole-file adversarial scan of the corpus JPEGs for "
                          "an XMP packet outside both APP1 headers, recorded "
                          "as a Witness with the file count it covered",
    },
    "isobmff": {
        "containers": ["uuid box with Adobe's registered UUID (MP4)",
                       "XMP_ atom inside moov/udta (QuickTime)"],
        "vocabulary_complete": ASSERTED,
        "why": "This is the entry that DEMONSTRABLY failed clause (b) once: "
               "the QuickTime XMP_ atom was MISSING from this list in the "
               "first version, and a scan asserted vocabulary_complete=YES on "
               "citation (a) alone. It flagged 1372 QuickTime files as "
               "vocabulary complete and found 0 XMP packets in them, while a "
               "crude window scan of the same 1372 files found 180. Both "
               "containers are listed now, but no adversarial whole-file scan "
               "has been run against this corrected list, so it stays "
               "asserted, not proven -- the same shortcut must not repeat.",
        "upgrade_check": "a second adversarial whole-file scan of a real "
                          "QuickTime/MP4 sample against BOTH containers "
                          "listed here, finding 0 packets outside them, "
                          "recorded as a Witness with the file count covered",
    },
    "generic": {
        "containers": ["a raw <?xpacket ... ?> or <x:xmpmeta> region"],
        "vocabulary_complete": NO,
        "why": "A packet may be stored in a format-specific structure this "
               "fallback cannot name. TIFF tag 700 and PDF metadata streams are "
               "two known cases that are found only by luck here.",
        "upgrade_check": "none upgrades this entry itself: it is a fallback "
                          "for formats with no dedicated locator, so the fix "
                          "is a real locator per format (TIFF, PDF, ...) with "
                          "its own graded vocabulary, not a Witness for this one",
    },
}

# CONSEQUENCE FOR tools/substrate_scan.py, which this module may not edit:
# it counts a "vocabulary_yes" column by comparing levels.vocabulary == YES.
# Every entry above is now ASSERTED or NO, never YES, so that column goes to
# zero. That is the correct outcome, not a regression: the previously reported
# figure of 23367 of 24478 files (95.5%) "vocabulary complete" was read off
# this table as an assertion, and was never a measurement -- the isobmff row
# above is the proof. Do not re-grade any entry back to YES to restore that
# number; the only legitimate way back to YES is a real Witness.
