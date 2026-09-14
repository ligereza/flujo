"""The fourteen query contracts, and the predicate each one may actually decide.

A contract separates the question a person asks from the predicate the evidence
can settle. Those are not the same thing, and conflating them was the defect the
adversarial audit found in nearly every certificate: "no ``.blend`` is indexed
here" was being reported as "this is not 3D".

So every contract declares both, and when they differ the certificate says which
one it answered. Nothing is allowed to answer Q by quietly proving P.

The declarative half lives in ``data/certified_queries.json`` -- wording,
authorities, completeness conditions, claim type, reopen conditions -- because
the operator has to be able to read and dispute it without reading code. The
rules live here, because a predicate like "every surface is inside the declared
obra set" is not expressible as data.

The completeness guard is NOT in the rules. It sits in ``certify`` so that no
individual rule can forget it. A rule proposes; the framework vetoes an unsound
negative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping

from .summary import (
    CLAIM_TYPES,
    CORPUS_CLAIM,
    POLICY_CLAIM,
    WORLD_CLAIM,
    Summary,
)

CONTRACT_FILE = Path(__file__).resolve().parents[3] / "data" / "certified_queries.json"
SCHEMA = "mak-certified-queries-v1"

CERTIFIED_YES = "CERTIFIED_YES"
CERTIFIED_NO = "CERTIFIED_NO"
UNKNOWN = "UNKNOWN"
VERDICTS = (CERTIFIED_YES, CERTIFIED_NO, UNKNOWN)

# Declared vocabulary of the summary payload. A rule may only read these keys, so
# a new field cannot be introduced without appearing here first.
SET_KEYS = ("container_root", "extension", "surface", "track_id", "entity_role",
            "sha256", "client")
COUNT_KEYS = ("has_3d_format", "has_author_statement", "unmatched_name", "undated",
              "in_virtualenv", "has_full_hash", "client_known")
RANGE_KEYS = ("date",)

# The declared 3D format set, in two tiers, because the distinction is a real
# judgement and hiding it inside one list is how the first version went wrong.
#
# History: q2 originally used {.blend} alone and was UNSOUND rather than merely
# imprecise -- measured on the real index, .blend is 70.1% of 3D files and 5
# projects hold a 3D format with no .blend at all, so the negative certificate
# was false for those 5. The set was then widened, and the ratchet in
# ``tests/test_certified_engine.py`` immediately found ANOTHER gap on its first
# run: a .3dm file nobody had declared. That is the test working, and it is why
# the set is audited against the corpus rather than trusted.
#
# A scene format is a file some 3D application authors and reopens.
SCENE_FORMATS = frozenset({
    ".blend", ".blend1", ".fbx", ".obj", ".gltf", ".glb", ".abc", ".usd",
    ".usda", ".usdc", ".c4d", ".max", ".ma", ".mb", ".dae", ".stl", ".3ds",
    ".ply", ".lwo", ".x3d", ".3dm",
})

# Pipeline data that only a 3D pipeline produces. A folder holding one of these
# and no scene file is still evidence of 3D work: a volume grid or a material
# sidecar does not arise from a 2D process.
PIPELINE_3D_FORMATS = frozenset({".vdb", ".mtl", ".spp"})

DECLARED_3D_FORMATS = SCENE_FORMATS | PIPELINE_3D_FORMATS

# Deliberately EXCLUDED, and the reason is recorded so nobody adds them later by
# pattern-matching on "looks 3D". Measured presence: .exr 6835, .hdr 9. Both are
# image formats -- a render output or an HDR texture -- and a 2D pipeline emits
# them too, so their presence is not evidence of 3D authorship. Adding them would
# make q2's POSITIVE certificate wrong instead of its negative.
EXCLUDED_FROM_3D = frozenset({".exr", ".hdr", ".png", ".jpg", ".tif", ".tga"})

# The operator's own words -- "obra" and "registro" -- stay as VALUES in
# data/certified_queries.json, because they are what he calls the things. The
# identifiers around them are English, which is the repository rule.
WORK_SURFACES = frozenset({"posts", "reels", "igtv"})
NOT_WORK_SURFACES = frozenset({"stories", "archived_posts"})
UNRESOLVED_SURFACES = frozenset({"other"})


class ContractError(ValueError):
    """A contract was missing, malformed, or asked for outside its scope."""


@dataclass(frozen=True)
class QueryContract:
    """Q, P, the authorities allowed to decide P, and what a negative requires."""

    id: str
    question: str
    predicate: str
    authorities: tuple[str, ...]
    completeness: str
    claim_type: str
    certifies_no: str
    certifies_yes: str
    unknown_when: str
    verdict: str
    reopen_when: tuple[str, ...]
    audit_note: str

    @property
    def decidable(self) -> bool:
        """False when no known predicate exists, i.e. the C cases."""
        return self.predicate.strip().lower() != "none known"

    @property
    def answers_question_directly(self) -> bool:
        """Whether a certificate on P may be reported as answering Q.

        Only when the predicate is not a narrowing. Every CORPUS_CLAIM and every
        POLICY_CLAIM here is a narrowing by construction: one speaks about the
        index, the other about a rule we wrote.
        """
        return self.claim_type == WORLD_CLAIM and self.decidable

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "Q": self.question, "P": self.predicate,
            "authorities": list(self.authorities), "claim_type": self.claim_type,
            "completeness": self.completeness, "verdict": self.verdict,
            "reopen_when": list(self.reopen_when),
        }


@lru_cache(maxsize=2)
def load_contracts(path: str | None = None) -> dict[str, QueryContract]:
    target = Path(path) if path else CONTRACT_FILE
    if not target.is_file():
        raise ContractError(f"contract_file_missing: {target}")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"contract_file_unreadable: {exc}") from exc
    if payload.get("schema") != SCHEMA:
        raise ContractError(f"contract_file_bad_schema: {payload.get('schema')}")
    out: dict[str, QueryContract] = {}
    for row in payload["contracts"]:
        for required in ("id", "Q", "P", "authorities", "completeness", "claim_type",
                         "certifies_no", "certifies_yes", "unknown_when", "verdict",
                         "reopen_when", "audit_note"):
            if required not in row:
                raise ContractError(f"contract_{row.get('id')}_missing_{required}")
        if row["claim_type"] not in CLAIM_TYPES:
            raise ContractError(
                f"contract_{row['id']}_bad_claim_type: {row['claim_type']}")
        contract = QueryContract(
            id=str(row["id"]), question=str(row["Q"]), predicate=str(row["P"]),
            authorities=tuple(row["authorities"]),
            completeness=str(row["completeness"]),
            claim_type=str(row["claim_type"]),
            certifies_no=str(row["certifies_no"]),
            certifies_yes=str(row["certifies_yes"]),
            unknown_when=str(row["unknown_when"]),
            verdict=str(row["verdict"]),
            reopen_when=tuple(row["reopen_when"]),
            audit_note=str(row["audit_note"]),
        )
        if contract.id in out:
            raise ContractError(f"duplicate_contract: {contract.id}")
        out[contract.id] = contract
    return out


# --------------------------------------------------------------------- the rules
#
# A rule proposes a verdict from the summary alone. It must never consult the
# corpus, and it must never enforce completeness -- ``certify`` does that, once,
# for every contract. Each rule returns (verdict, reason, authorities_for_no).

Rule = Callable[[Summary, Mapping[str, Any]], tuple[str, str, tuple[str, ...]]]


def _always_unknown(reason: str) -> Rule:
    def rule(summary: Summary, arg: Mapping[str, Any]):
        return UNKNOWN, reason, ()
    return rule


def _rule_commission(summary: Summary, arg: Mapping[str, Any]):
    wanted = str(arg.get("client", "")).strip()
    roots = summary.values("container_root")
    if not roots:
        return UNKNOWN, "no container_root observed in this group", ()
    if wanted:
        if wanted not in roots:
            return (CERTIFIED_NO,
                    f"no member sits under a container named {wanted!r}; "
                    f"observed roots: {sorted(roots)}",
                    ("ssd_index_paths",))
        return UNKNOWN, f"{wanted!r} is present among {len(roots)} roots", ()
    if len(roots) == 1:
        only = next(iter(roots))
        if summary.complete_for("operator_container_map"):
            return (CERTIFIED_YES, f"every member sits under {only!r} and the "
                    "operator has mapped that container to a client",
                    ("ssd_index_paths", "operator_container_map"))
        return (UNKNOWN, f"every member sits under {only!r}, but the "
                "container->client map does not cover it; folder is provenance, "
                "not client", ())
    return UNKNOWN, f"{len(roots)} distinct container roots present", ()


def _rule_dimension(summary: Summary, arg: Mapping[str, Any]):
    observed = summary.values("extension")
    three_d = observed & DECLARED_3D_FORMATS
    if summary.none("has_3d_format"):
        return (CERTIFIED_NO,
                f"no member carries an extension in the declared 3D set "
                f"({len(DECLARED_3D_FORMATS)} formats); observed: "
                f"{sorted(observed)[:8]}",
                ("ssd_index_extensions",))
    total = summary.all("has_3d_format")
    if total:
        return (CERTIFIED_YES,
                f"every member carries a declared 3D format: {sorted(three_d)}",
                ("ssd_index_extensions",))
    return (UNKNOWN,
            f"{summary.counts.get('has_3d_format', 0)} of {summary.n_members} "
            f"members carry a 3D format", ())


def _rule_track(summary: Summary, arg: Mapping[str, Any]):
    wanted = str(arg.get("track", "")).strip().casefold()
    unmatched = int(summary.counts.get("unmatched_name", 0))
    tracks = {str(t).casefold() for t in summary.values("track_id")}
    if unmatched:
        return (UNKNOWN,
                f"{unmatched} name(s) in this group were never resolved against a "
                "discography; an unresolved name could be any track, so no "
                "exclusion is sound", ())
    if wanted:
        if wanted not in tracks:
            return (CERTIFIED_NO,
                    f"no member resolves to {wanted!r}, and every name resolved",
                    ("artist_discography",))
        return UNKNOWN, f"{wanted!r} is present among {len(tracks)} tracks", ()
    if len(tracks) == 1:
        return (CERTIFIED_YES,
                f"every name resolves to the single track "
                f"{sorted(summary.values('track_id'))[0]!r}",
                ("artist_discography",))
    return UNKNOWN, f"{len(tracks)} distinct tracks resolved", ()


def _rule_work_or_record(summary: Summary, arg: Mapping[str, Any]):
    surfaces = summary.values("surface")
    if not surfaces:
        return UNKNOWN, "no publication surface observed", ()
    if surfaces & UNRESOLVED_SURFACES:
        return (UNKNOWN,
                "the group touches the `other` surface, which is not a semantic "
                "class: 330 files of mixed geometry whose mtimes all fall inside "
                "one 55 second export window", ())
    if surfaces <= WORK_SURFACES:
        return (CERTIFIED_YES,
                f"every surface is in the declared obra set: {sorted(surfaces)}",
                ("ig_export_surfaces", "operator_surface_rule"))
    if surfaces <= NOT_WORK_SURFACES:
        return (CERTIFIED_NO,
                f"every surface is outside the declared obra set: "
                f"{sorted(surfaces)}",
                ("ig_export_surfaces", "operator_surface_rule"))
    return UNKNOWN, f"the group mixes obra and record surfaces: {sorted(surfaces)}", ()


def _rule_publishes(summary: Summary, arg: Mapping[str, Any]):
    verdict, reason, authorities = _rule_work_or_record(summary, arg)
    if verdict == CERTIFIED_NO:
        return (CERTIFIED_NO,
                "not a work under the declared rule, therefore not a portfolio "
                f"candidate ({reason})", authorities)
    return (UNKNOWN,
            "publication is reserved to the operator by design: every post is a "
            "work, and which one goes up is his decision", ())


def _rule_application(summary: Summary, arg: Mapping[str, Any]):
    if summary.none("has_author_statement"):
        return (CERTIFIED_NO,
                "no member carries an author statement, and the declared policy "
                "requires one. THIS IS A POLICY CLAIM: the operator can write a "
                "statement for any piece in minutes, so this is a state of the "
                "record and not a property of the work",
                ("iskvw_archive_fields",))
    return (UNKNOWN,
            "carrying a statement makes a piece eligible, never selected", ())


def _rule_shown_when(summary: Summary, arg: Mapping[str, Any]):
    window = arg.get("window")
    if not window:
        return UNKNOWN, "no date window supplied", ()
    lo_q, hi_q = float(window[0]), float(window[1])
    hull = summary.hull("date")
    if hull is None:
        return UNKNOWN, "no date observed in this group", ()
    undated = int(summary.counts.get("undated", 0))
    if undated:
        return (UNKNOWN,
                f"{undated} of {summary.n_members} members carry no date from the "
                "declared source; an undated member could fall anywhere, so the "
                "hull cannot exclude", ())
    if not summary.hull_is_source_pure("date"):
        return (UNKNOWN,
                f"the date hull mixes sources {sorted(summary.range_sources.get('date', ()))}; "
                "a hull over mixed sources certifies nothing", ())
    lo, hi = hull
    source = next(iter(summary.range_sources["date"]))
    if hi < lo_q or lo > hi_q:
        return (CERTIFIED_NO,
                f"the group's {source} hull [{lo:.0f}, {hi:.0f}] does not meet the "
                f"window [{lo_q:.0f}, {hi_q:.0f}]", (source,))
    if lo_q <= lo and hi <= hi_q:
        return (CERTIFIED_YES,
                f"the whole {source} hull [{lo:.0f}, {hi:.0f}] lies inside the "
                "window", (source,))
    return UNKNOWN, f"the {source} hull straddles the window edge", ()


def _rule_authored(summary: Summary, arg: Mapping[str, Any]):
    if summary.all("in_virtualenv"):
        return (CERTIFIED_YES,
                "every member sits under a directory carrying pyvenv.cfg or an "
                "install target, so a package manager placed it (PEP 405)",
                ("pep_405_environment_marker",))
    if summary.any("in_virtualenv"):
        return (UNKNOWN,
                f"{summary.counts.get('in_virtualenv', 0)} of {summary.n_members} "
                "members sit inside an environment", ())
    return (UNKNOWN,
            "no Python environment marker was found, which is NOT evidence of own "
            "authorship: measured on this disk, blenderkit contributes 138 assets "
            "and downloaded asset folders 173, none inside a virtual environment",
            ())


def _rule_duplicate(summary: Summary, arg: Mapping[str, Any]):
    canonical = arg.get("canonical_hashes")
    if canonical is None:
        return UNKNOWN, "no canonical hash set supplied", ()
    if not summary.all("has_full_hash"):
        missing = summary.n_members - int(summary.counts.get("has_full_hash", 0))
        return (UNKNOWN,
                f"{missing} of {summary.n_members} members lack a FULL hash; a "
                "sample hash is not an identity", ())
    present = summary.values("sha256")
    overlap = present & frozenset(canonical)
    if not overlap:
        return (CERTIFIED_NO,
                f"none of the {len(present)} full hashes in this group appears in "
                "the canonical set", ("content_identity",))
    if present <= frozenset(canonical):
        return (CERTIFIED_YES,
                f"every one of the {len(present)} full hashes is present in the "
                "canonical set", ("content_identity",))
    return (UNKNOWN,
            f"{len(overlap)} of {len(present)} hashes are canonical copies", ())


def _rule_entity_role(summary: Summary, arg: Mapping[str, Any]):
    roles = summary.values("entity_role")
    wanted = str(arg.get("role", "")).strip()
    if not roles:
        return (UNKNOWN,
                "the entity appears in no declared role set; 3 venues and 21 "
                "productoras are declared, and sponsor is an exclusion list rather "
                "than a class, so 'not declared' is not 'not a venue'", ())
    if wanted and wanted not in roles:
        return (CERTIFIED_NO,
                f"the declared role set for this group is {sorted(roles)}, which "
                f"does not include {wanted!r}", ("declared_entity_roles",))
    if len(roles) == 1:
        return (CERTIFIED_YES,
                f"every member carries the single declared role "
                f"{sorted(roles)[0]!r}", ("declared_entity_roles",))
    return UNKNOWN, f"the group spans {len(roles)} declared roles", ()


RULES: dict[str, Rule] = {
    "q1_commission": _rule_commission,
    "q2_dimension": _rule_dimension,
    "q3_track": _rule_track,
    "q4_work_or_record": _rule_work_or_record,
    "q5_publishes": _rule_publishes,
    "q6_application": _rule_application,
    "q7_shown_when": _rule_shown_when,
    "q8_concept": _always_unknown(
        "no sound summary exists: the only available concepts come from a vision "
        "reading, and an incomplete per-member extraction cannot be unioned into "
        "an over-approximation of anything"),
    "q9_rig": _always_unknown(
        "no sound summary exists: 9 ScreenSetups on disk against far more shows, "
        "so even the exclusion fails. BERLIN 1 and berlin 2 name one room and "
        "share zero surfaces"),
    "q10_delivered": _always_unknown(
        "no delivery marker exists in the corpus; _v7 and _final are a naming "
        "convention, which is a free feature with no authority behind it"),
    "q11_authored": _rule_authored,
    "q12_duplicate": _rule_duplicate,
    "q13_record_kind": _always_unknown(
        "the predicate is not computable on a single member; no text-presence "
        "detector has a measured hit rate, and text presence would not separate a "
        "note about a work from a note about a process"),
    "q14_entity_role": _rule_entity_role,
}


def rule_for(contract_id: str) -> Rule:
    try:
        return RULES[contract_id]
    except KeyError:
        raise ContractError(
            f"no_rule_for_contract: {contract_id}. Every declared contract needs a "
            "rule, even one that only ever abstains.") from None
