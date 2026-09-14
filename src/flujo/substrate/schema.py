"""The minimum identity substrate: Content, ArtifactState, Lineage, Observation, Evidence.

Five entities and nothing else. No PROJECT, no practice model, no global
classification. The single claim being tested here is that these five can be
kept apart, because collapsing any pair of them destroys something the corpus
actually contains.

Why each one has to exist separately, with the measurement that forced it:

**Content** is byte identity. It is proof and it is the only thing here that is.
It survives a path change, a zip, a new disk. It does NOT survive a re-export,
and full digests exist for 112 of 45536 SSD assets, so most of the corpus has no
Content identity at all yet.

**ArtifactState** is one incarnation of a document. Two states may share Content
(the same bytes in two places) or share nothing (a re-export changes every
byte). Adobe writes ``xmpMM:InstanceID`` for exactly this notion, which is why
it is preferred as the state key over anything synthetic.

**Lineage** is documentary continuity across states whose bytes differ. Measured:
1367 files carry a DocumentID and 1340 carry an OriginalDocumentID. Without this
entity a re-export looks like an unrelated file, and the corpus is full of them.

**Observation** is where and when something was seen. It is PLURAL and dated. A
location is an observation, never an identity -- the measured failure mode was
treating the folder scan row as the unit, which makes an unzip create a new
object and forbids a project from spanning two disks.

**Evidence** backs every relation. No edge exists without a row saying which
extractor produced it, by what method, and whether a negative from that method
would have meant anything. That last field is what stops a bounded window scan
from being read as absence.

The predicate vocabulary keeps two things apart that a naive reader merges:

    xmpMM:History      operations on THIS document's own chain -> revision_in_lineage
    xmpMM:Ingredients  OTHER documents that went into it       -> uses

History members are self-states over time. Ingredients are other lineages
flowing in. Folding them into one edge class would make a document its own
dependency, and would make a dependency look like a version.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .epistemics import CONFLICT, MISSING_EVIDENCE, UNKNOWN_CAUSES
from .resolution import (Resolution, candidate_count, is_present,
                         resolve)

CONTRACT = "mak-identity-substrate-v1"

# ---------------------------------------------------------------- predicates
#
# Only what this substrate can actually support. PROJECT membership,
# conflicts_with and published_as are deliberately absent: nothing here can
# establish them, and declaring a predicate the layer cannot justify is how a
# vocabulary starts lying.

SAME_CONTENT = "same_content"                 # identical bytes. Proof.
SAME_LINEAGE = "same_lineage"                 # shared DocumentID / OriginalDocumentID
DERIVED_FROM = "derived_from"                 # xmpMM:DerivedFrom, immediate parent
REVISION_IN_LINEAGE = "revision_in_lineage"   # xmpMM:History event, a self-state
USES = "uses"                                 # xmpMM:Ingredients, ANOTHER document
PANTRY_COPY_OF = "pantry_copy_of"             # xmpMM:Pantry, embedded ingredient metadata
REFERENCES = "references"                     # a path string inside a project file
# A project file declaring WHERE IT WRITES, which is not the same claim as
# mentioning a path. Measured 2026-08-24: 26 declared render output paths
# resolve to real directories holding 2021 files among 927 .blend files; 55
# files remain DECODER_LIMIT. The declaration lives in the SOURCE, so it
# survives any re-encode of the output. That is the only reason the
# source-to-render chain is recoverable at all: it is read backwards from the
# project, never forwards from the export.
RENDERS_TO = "renders_to"                     # a project file's output path
OBSERVED_AT = "observed_at"                   # a state seen at a location

CONFLICTS_WITH = "conflicts_with"             # two claims that cannot both hold

PREDICATES = (SAME_CONTENT, SAME_LINEAGE, DERIVED_FROM, REVISION_IN_LINEAGE,
              USES, PANTRY_COPY_OF, REFERENCES, RENDERS_TO, OBSERVED_AT,
              CONFLICTS_WITH)

# Which predicates say "this is the same document over time" and which say
# "this document consumed that one". Kept explicit so no caller can conflate them.
# Symmetry, declared rather than inferred from the name. A predicate that is its
# own inverse states a fact about a PAIR; a directed one states a fact about an
# ordered pair, and orienting it requires an asymmetry in the evidence itself.
SYMMETRIC_PREDICATES = frozenset({SAME_CONTENT, SAME_LINEAGE, CONFLICTS_WITH})
DIRECTED_PREDICATES = frozenset(PREDICATES) - SYMMETRIC_PREDICATES - {OBSERVED_AT}

# Which predicates each authority is allowed to assert.
#
# THIS PAIRING IS THE CHECK THAT WAS MISSING. Evidence validated its predicate
# against a vocabulary and its authority against a vocabulary, and never
# validated the PAIR -- so "which source may support which claim" was a
# discipline somebody had to remember. It was not remembered: three measurements
# in a row were retracted after a source was used for a claim it could not bear.
#
# Every pair the code writes today is already admissible, so this table breaks
# nothing. That is the point: it codifies what is correct now so the NEXT pair
# has to be declared instead of assumed.
ADMISSIBLE_PREDICATES: dict[str, frozenset[str]] = {
    "content_digest": frozenset({SAME_CONTENT}),
    "xmp_packet": frozenset({SAME_LINEAGE, DERIVED_FROM, REVISION_IN_LINEAGE,
                             USES, PANTRY_COPY_OF, CONFLICTS_WITH}),
    "resolume_reference_regex": frozenset({REFERENCES}),
    # A project file may say what it opens and what it writes. It may NOT say
    # that one document derived from another: naming an output directory is not
    # the same claim as orienting a lineage, and 482 files in one declared
    # directory is 482 candidates for which one this save produced.
    "blend_declaration": frozenset({REFERENCES, USES, RENDERS_TO}),
    "aftereffects_declaration": frozenset({REFERENCES, USES, RENDERS_TO}),
    "filesystem": frozenset({OBSERVED_AT}),
    # The operator is the audited downgrade: the one authority that may orient an
    # edge from judgement rather than from a measurement. Every unsound step in
    # the system is supposed to pass through here and be visible as such.
    "operator": frozenset(PREDICATES),
}

# An authority whose measurement is SYMMETRIC cannot orient an edge. A digest
# says two objects are equal; equality has no direction, and no amount of it
# yields one. A graded overlap measure would be the first thing to violate this
# -- the temptation with a partial-content score is to read it as "B came from
# A" -- so the rule is enforced structurally rather than left as advice.
SYMMETRIC_MEASUREMENT_AUTHORITIES = frozenset({"content_digest"})


def _check_admissibility_table() -> None:
    """Validate the table at import time, not at the first write.

    A bad row here is a design error, and a design error should stop the module
    from loading rather than wait for the one record that happens to hit it.
    """
    for authority, allowed in ADMISSIBLE_PREDICATES.items():
        if authority not in AUTHORITIES:
            raise SubstrateError(f"admissibility_for_undeclared_authority: {authority}")
        undeclared = allowed - set(PREDICATES)
        if undeclared:
            raise SubstrateError(
                f"admissibility_names_undeclared_predicate: {sorted(undeclared)}")
        if authority in SYMMETRIC_MEASUREMENT_AUTHORITIES:
            oriented = allowed & DIRECTED_PREDICATES
            if oriented:
                raise SubstrateError(
                    f"symmetric_measurement_may_not_orient: {authority} was "
                    f"granted {sorted(oriented)}")
    missing = set(AUTHORITIES) - set(ADMISSIBLE_PREDICATES)
    if missing:
        raise SubstrateError(f"authority_without_admissibility: {sorted(missing)}")


SELF_CONTINUITY = frozenset({SAME_LINEAGE, DERIVED_FROM, REVISION_IN_LINEAGE})
CROSS_DOCUMENT = frozenset({USES, PANTRY_COPY_OF, REFERENCES, RENDERS_TO})

# What the object of an edge IS, and whether this corpus contains it. These were
# previously conflated, so "an ingredient that does not exist" and "an ingredient
# whose state has not been ingested yet" looked identical -- and most History
# instanceIDs name states that are simply not on this disk.
OBJ_STATE = "state"
OBJ_CONTENT = "content"
OBJ_OBSERVATION = "observation"
OBJ_LINEAGE = "lineage"
OBJ_EXTERNAL_ID = "external_id"      # an id written by a tool, e.g. an XMP GUID
OBJ_BASENAME = "basename"            # a name mentioned inside a project file
OBJECT_KINDS = (OBJ_STATE, OBJ_CONTENT, OBJ_OBSERVATION, OBJ_LINEAGE,
                OBJ_EXTERNAL_ID, OBJ_BASENAME)

RESOLVED = "resolved"                        # the object is a known entity here
UNRESOLVED_IN_CORPUS = "unresolved_in_corpus"  # a valid id, nothing here carries it
NOT_RESOLVABLE_BY_THIS_LAYER = "not_resolvable_by_this_layer"
RESOLUTIONS = (RESOLVED, UNRESOLVED_IN_CORPUS, NOT_RESOLVABLE_BY_THIS_LAYER)

# ---------------------------------------------------------------- authorities
#
# Each carries the class of claim it can support and whether a negative from it
# means anything. A regex over bytes is a real extractor and a weak authority;
# saying so in the schema is cheaper than remembering it.

AUTHORITIES: dict[str, dict[str, Any]] = {
    "content_digest": {
        "what": "SHA-256 over the whole file.",
        "claim": "byte identity",
        "strength": "proof",
        "negative_is_evidence": True,
        "note": "A partial or sampled digest is NOT this authority and must not "
                "be recorded under it.",
    },
    "xmp_packet": {
        "what": "An XMP packet located by the format's own rules.",
        "claim": "document identity, instance identity, declared derivation",
        "strength": "strong",
        "negative_is_evidence": "only when search_completeness is exhaustive",
        "note": "Some applications strip metadata on export, so a missing packet "
                "does not prove a file was never derived.",
    },
    "resolume_reference_regex": {
        "what": "A byte-level regular expression over a Resolume composition, "
                "matching Windows-style media paths.",
        "claim": "that the composition mentions a path",
        "strength": "weak",
        "negative_is_evidence": False,
        "coverage": "unmeasured. Verified once on two files: 104 matches in "
                    "SHOWCAUPOLICAN (37 distinct, 19 resolved) and 232 in "
                    "sampier (73 distinct, 0 resolved).",
        "note": "NOT A PARSER. It cannot see a reference the writer stored in a "
                "form the pattern does not match, it cannot tell an active clip "
                "from a stale one, and a match is a mention rather than a "
                "dependency. Marked weak on purpose.",
    },
    "blend_declaration": {
        "what": "A static parse of a .blend file's block chain. Blender is never "
                "launched, because launching an application to learn what it "
                "references makes the answer depend on that application's "
                "version, its addons and its ability to find the files.",
        "claim": "that the project declares it opens or writes this path",
        "strength": "strong",
        "negative_is_evidence": False,
        "coverage": "Measured 2026-08-24 over 927 .blend files: 872 parsed and "
                    "55 are DECODER_LIMIT. The parsed files carry 192 scene "
                    "output declarations; 26 resolve to directories holding "
                    "2021 candidate files, while suspect directories are not "
                    "persisted as ordinary render edges. A declaration NOT "
                    "found may still exist: node groups, library overrides and "
                    "linked scenes are not modelled.",
        "note": "A declared path is evidence with real weight because the file "
                "states it. Its ABSENCE is not evidence, which is why "
                "negative_is_evidence is False.",
    },
    "aftereffects_declaration": {
        "what": "A bounded lexical extraction of structured fullpath records "
                "from an .aep RIFX/Egg container.",
        "claim": "that the composition declares it opens or uses this path",
        "strength": "strong",
        "negative_is_evidence": False,
        "coverage": "Measured 2026-08-24 over /home/mak/RD and "
                    "/home/mak/curatoria_inbox: 145 files, 138 with "
                    "references, 2304 unique-per-file declared paths, 309 "
                    "unique path strings, and 0 DECODER_LIMIT. This is a "
                    "bounded filesystem measurement, not a claim that the MAK "
                    "corpus is complete; the 408-file claim was not reproduced.",
        "note": "A declared path is evidence of a project reference, not a "
                "delivered output. This reader emits no RENDERS_TO edge and "
                "does not decide whether a video in a folder is the work.",
    },
    "filesystem": {
        "what": "Path, size and timestamps as reported by the operating system.",
        "claim": "that a state was observed at a location at a time",
        "strength": "moderate",
        "negative_is_evidence": False,
        "note": "Decides provenance, never meaning. A copy operation rewrites "
                "mtime: measured, 330 files sharing a 55 second window.",
    },
    "operator": {
        "what": "The person states it.",
        "claim": "anything",
        "strength": "proof",
        "negative_is_evidence": False,
    },
}


class SubstrateError(ValueError):
    """The substrate was asked to record something it cannot justify."""


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------- entities

@dataclass(frozen=True)
class Content:
    """Byte identity. The only proof-grade entity here."""

    content_id: str          # "sha256:<hex>"
    size: int
    digest_algorithm: str = "sha256"
    format_detected: str = ""

    @staticmethod
    def of_file(path: str | Path, *, chunk: int = 1 << 20) -> "Content":
        digest = hashlib.sha256()
        total = 0
        with open(path, "rb") as handle:
            while True:
                block = handle.read(chunk)
                if not block:
                    break
                digest.update(block)
                total += len(block)
        return Content(content_id=f"sha256:{digest.hexdigest()}", size=total,
                       format_detected=os.path.splitext(str(path))[1].lower())


@dataclass(frozen=True)
class ArtifactState:
    """One incarnation of a document. May or may not have known Content."""

    state_id: str
    content_id: str | None = None
    document_id: str | None = None
    instance_id: str | None = None
    original_document_id: str | None = None
    creator_tool: str | None = None
    claimed_created: str | None = None
    claimed_modified: str | None = None
    id_source: str = "synthetic"   # "xmp_instance_id" | "content" | "synthetic"

    @property
    def has_embedded_identity(self) -> bool:
        return bool(self.instance_id or self.document_id)


@dataclass(frozen=True)
class Lineage:
    """Documentary continuity across states whose bytes differ."""

    lineage_id: str
    key_source: str          # "original_document_id" | "document_id"

    @staticmethod
    def key_for(document_id: str | None,
                original_document_id: str | None) -> "Lineage | None":
        """Prefer the ORIGINAL id: it is the root of the chain, not this link."""
        if original_document_id:
            return Lineage(f"lineage:{original_document_id}", "original_document_id")
        if document_id:
            return Lineage(f"lineage:{document_id}", "document_id")
        return None


@dataclass(frozen=True)
class Observation:
    """Where and when a state was seen. Plural and dated, never an identity."""

    observation_id: str
    state_id: str
    root_id: str
    relative_path: str
    observed_at: str
    container_path: str | None = None   # set when the file lives inside an archive
    basename: str = ""
    extension: str = ""
    fs_size: int | None = None
    fs_mtime: str | None = None


@dataclass(frozen=True)
class Evidence:
    """Why one relation is believed. Every edge needs one."""

    evidence_id: str
    subject: str
    predicate: str
    object: str
    authority: str
    extractor: str
    method: str
    search_completeness: str
    recorded_at: str
    detail: str = ""
    ordinal: int | None = None      # position inside a History or Ingredients list
    object_kind: str = OBJ_EXTERNAL_ID
    object_resolution: str = NOT_RESOLVABLE_BY_THIS_LAYER
    unknown_cause: str = ""         # set when this row records a gap, not a fact
    # How many objects the referent lookup matched. 1 means the referent was
    # individuated; more means the row is present-but-ambiguous, and 0 means the
    # lookup was never performed. Recorded because an edge whose object matched
    # 8 candidates used to look identical to one that matched exactly 1, and the
    # difference is exactly log2(8) = 3 bits of missing individuation. Measured
    # on the real corpus: 120 DocumentIDs are carried by more than one state,
    # group sizes 2 to 8.
    candidate_count: int = 0

    def __post_init__(self) -> None:
        if self.predicate not in PREDICATES:
            raise SubstrateError(f"undeclared_predicate: {self.predicate}")
        if self.authority not in AUTHORITIES:
            raise SubstrateError(f"undeclared_authority: {self.authority}")
        allowed = ADMISSIBLE_PREDICATES[self.authority]
        if self.predicate not in allowed:
            raise SubstrateError(
                f"inadmissible_pair: authority {self.authority!r} may not assert "
                f"{self.predicate!r}; it may assert {sorted(allowed)}")
        if self.object_kind not in OBJECT_KINDS:
            raise SubstrateError(f"undeclared_object_kind: {self.object_kind}")
        if self.object_resolution not in RESOLUTIONS:
            raise SubstrateError(
                f"undeclared_object_resolution: {self.object_resolution}")
        if self.unknown_cause and self.unknown_cause not in UNKNOWN_CAUSES:
            raise SubstrateError(f"undeclared_unknown_cause: {self.unknown_cause}")
        if self.candidate_count < 0:
            raise SubstrateError(f"negative_candidate_count: {self.candidate_count}")
        # An ambiguous referent may be RESOLVED -- "the id is here" survives the
        # collision -- but it must never be recorded as having individuated one.
        if self.candidate_count > 1 and self.predicate in DIRECTED_PREDICATES \
                and self.authority not in ("operator",):
            if self.object_kind == OBJ_STATE:
                raise SubstrateError(
                    f"ambiguous_referent_for_directed_edge: {self.predicate} "
                    f"points at a state chosen from {self.candidate_count} "
                    f"candidates, which is {self.candidate_count} times one too "
                    f"many")

    @property
    def negative_would_be_evidence(self) -> bool:
        """Whether an absent match from this authority and method means anything."""
        rule = AUTHORITIES[self.authority]["negative_is_evidence"]
        if rule is True:
            return True
        if rule is False:
            return False
        return self.search_completeness == "exhaustive"

    @property
    def individuating_deficit_bits(self) -> float:
        """Bits missing before this row could name ONE object. Zero iff k == 1."""
        from math import log2
        return log2(self.candidate_count) if self.candidate_count > 1 else 0.0

    @property
    def is_self_continuity(self) -> bool:
        return self.predicate in SELF_CONTINUITY

    @property
    def is_cross_document(self) -> bool:
        return self.predicate in CROSS_DOCUMENT


# ----------------------------------------------------------------- persistence

DDL = """
CREATE TABLE IF NOT EXISTS content (
    content_id TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    digest_algorithm TEXT NOT NULL,
    format_detected TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS artifact_state (
    state_id TEXT PRIMARY KEY,
    content_id TEXT,
    document_id TEXT,
    instance_id TEXT,
    original_document_id TEXT,
    creator_tool TEXT,
    claimed_created TEXT,
    claimed_modified TEXT,
    id_source TEXT NOT NULL,
    FOREIGN KEY(content_id) REFERENCES content(content_id)
);
CREATE INDEX IF NOT EXISTS idx_state_content ON artifact_state(content_id);
CREATE INDEX IF NOT EXISTS idx_state_document ON artifact_state(document_id);
CREATE INDEX IF NOT EXISTS idx_state_instance ON artifact_state(instance_id);

CREATE TABLE IF NOT EXISTS lineage (
    lineage_id TEXT PRIMARY KEY,
    key_source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lineage_member (
    lineage_id TEXT NOT NULL,
    state_id TEXT NOT NULL,
    PRIMARY KEY(lineage_id, state_id),
    FOREIGN KEY(lineage_id) REFERENCES lineage(lineage_id),
    FOREIGN KEY(state_id) REFERENCES artifact_state(state_id)
);

CREATE TABLE IF NOT EXISTS observation (
    observation_id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL,
    root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    container_path TEXT,
    observed_at TEXT NOT NULL,
    basename TEXT NOT NULL DEFAULT '',
    extension TEXT NOT NULL DEFAULT '',
    fs_size INTEGER,
    fs_mtime TEXT,
    FOREIGN KEY(state_id) REFERENCES artifact_state(state_id)
);
CREATE INDEX IF NOT EXISTS idx_obs_state ON observation(state_id);
CREATE INDEX IF NOT EXISTS idx_obs_path ON observation(root_id, relative_path);

-- Append-only. A relation is never edited, only superseded by a later row.
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    authority TEXT NOT NULL,
    extractor TEXT NOT NULL,
    method TEXT NOT NULL,
    search_completeness TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    ordinal INTEGER,
    object_kind TEXT NOT NULL DEFAULT 'external_id',
    object_resolution TEXT NOT NULL DEFAULT 'not_resolvable_by_this_layer',
    unknown_cause TEXT NOT NULL DEFAULT '',
    candidate_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ev_subject ON evidence(subject, predicate);
CREATE INDEX IF NOT EXISTS idx_ev_object ON evidence(object, predicate);
CREATE INDEX IF NOT EXISTS idx_ev_predicate ON evidence(predicate);
"""


class Substrate:
    """SQLite persistence for the five entities. Evidence is append-only."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(DDL)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    # ------------------------------------------------------------- writes

    def put_content(self, content: Content) -> str:
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO content(content_id,size,digest_algorithm,"
                "format_detected) VALUES(?,?,?,?)",
                (content.content_id, content.size, content.digest_algorithm,
                 content.format_detected))
        return content.content_id

    def put_state(self, state: ArtifactState) -> list[dict[str, str]]:
        """Upsert a state, RECORDING any contradiction instead of swallowing it.

        The previous version used COALESCE for every field, so a second adapter
        offering a different document_id for the same state was silently ignored.
        The evidence table preserved disagreement and the state table erased it,
        which is incoherent: a reader of the state table would have seen one
        value and had no way to learn that another had been claimed.

        Now a differing non-null value writes a ``conflicts_with`` row and the
        FIRST value is kept, on the grounds that arbitrary is better than
        silently-last -- but neither is adjudication, and the conflict row is
        what says so. Returns the conflicts it found.
        """
        conflicts: list[dict[str, str]] = []
        now = _now()
        with self.connect() as con:
            previous = con.execute(
                "SELECT document_id, instance_id, original_document_id, content_id "
                "FROM artifact_state WHERE state_id=?", (state.state_id,)).fetchone()
            if previous is not None:
                for column in ("document_id", "instance_id",
                               "original_document_id", "content_id"):
                    old_value = previous[column]
                    new_value = getattr(state, column)
                    if old_value and new_value and old_value != new_value:
                        conflict = {"state_id": state.state_id, "field": column,
                                    "kept": str(old_value), "rejected": str(new_value)}
                        conflicts.append(conflict)
                        eid = "ev:conflict:" + hashlib.sha256(
                            f"{state.state_id}|{column}|{old_value}|{new_value}"
                            .encode()).hexdigest()[:24]
                        con.execute(
                            "INSERT OR IGNORE INTO evidence(evidence_id,subject,"
                            "predicate,object,authority,extractor,method,"
                            "search_completeness,recorded_at,detail,ordinal,"
                            "object_kind,object_resolution,unknown_cause) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (eid, state.state_id, CONFLICTS_WITH, str(new_value),
                             "operator" if state.id_source == "operator" else "xmp_packet",
                             "Substrate.put_state", "field_comparison", "exhaustive",
                             now,
                             f"{column}: kept {old_value!r}, rejected {new_value!r}. "
                             "NOT adjudicated -- the first value was kept because "
                             "arbitrary beats silently-last, and this row is the "
                             "record that no decision was made.",
                             None, OBJ_EXTERNAL_ID, NOT_RESOLVABLE_BY_THIS_LAYER,
                             CONFLICT))
            con.execute(
                "INSERT INTO artifact_state(state_id,content_id,document_id,"
                "instance_id,original_document_id,creator_tool,claimed_created,"
                "claimed_modified,id_source) VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(state_id) DO UPDATE SET "
                # EXISTING value first. The other order let a later adapter
                # overwrite an earlier claim in silence, which is the very bug
                # the conflict row above exists to prevent. New evidence fills
                # nulls; it never replaces a value already claimed.
                "content_id=COALESCE(content_id,excluded.content_id),"
                "document_id=COALESCE(document_id,excluded.document_id),"
                "instance_id=COALESCE(instance_id,excluded.instance_id),"
                "original_document_id=COALESCE(original_document_id,"
                "excluded.original_document_id),"
                "creator_tool=COALESCE(creator_tool,excluded.creator_tool)",
                (state.state_id, state.content_id, state.document_id,
                 state.instance_id, state.original_document_id, state.creator_tool,
                 state.claimed_created, state.claimed_modified, state.id_source))
        return conflicts

    def put_lineage(self, lineage: Lineage, state_id: str) -> str:
        with self.connect() as con:
            con.execute("INSERT OR IGNORE INTO lineage(lineage_id,key_source) "
                        "VALUES(?,?)", (lineage.lineage_id, lineage.key_source))
            con.execute("INSERT OR IGNORE INTO lineage_member(lineage_id,state_id) "
                        "VALUES(?,?)", (lineage.lineage_id, state_id))
        return lineage.lineage_id

    def put_observation(self, observation: Observation) -> str:
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO observation(observation_id,state_id,root_id,"
                "relative_path,container_path,observed_at,basename,extension,"
                "fs_size,fs_mtime) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (observation.observation_id, observation.state_id, observation.root_id,
                 observation.relative_path, observation.container_path,
                 observation.observed_at, observation.basename, observation.extension,
                 observation.fs_size, observation.fs_mtime))
        return observation.observation_id

    def put_evidence(self, evidence: Evidence) -> str:
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO evidence(evidence_id,subject,predicate,object,"
                "authority,extractor,method,search_completeness,recorded_at,detail,"
                "ordinal,object_kind,object_resolution,unknown_cause,"
                "candidate_count) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (evidence.evidence_id, evidence.subject, evidence.predicate,
                 evidence.object, evidence.authority, evidence.extractor,
                 evidence.method, evidence.search_completeness, evidence.recorded_at,
                 evidence.detail, evidence.ordinal, evidence.object_kind,
                 evidence.object_resolution, evidence.unknown_cause,
                 evidence.candidate_count))
        return evidence.evidence_id

    # -------------------------------------------------------------- reads

    def states_for_content(self, content_id: str) -> list[str]:
        with self.connect() as con:
            return [r[0] for r in con.execute(
                "SELECT state_id FROM artifact_state WHERE content_id=? "
                "ORDER BY state_id", (content_id,))]

    def observations_for_state(self, state_id: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM observation WHERE state_id=? ORDER BY relative_path",
                (state_id,))]

    def lineage_of(self, state_id: str) -> list[str]:
        with self.connect() as con:
            return [r[0] for r in con.execute(
                "SELECT lineage_id FROM lineage_member WHERE state_id=? "
                "ORDER BY lineage_id", (state_id,))]

    def members_of_lineage(self, lineage_id: str) -> list[str]:
        with self.connect() as con:
            return [r[0] for r in con.execute(
                "SELECT state_id FROM lineage_member WHERE lineage_id=? "
                "ORDER BY state_id", (lineage_id,))]

    def edges(self, *, predicate: str | None = None, subject: str | None = None
              ) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence WHERE 1=1"
        params: list[Any] = []
        if predicate:
            query += " AND predicate=?"
            params.append(predicate)
        if subject:
            query += " AND subject=?"
            params.append(subject)
        with self.connect() as con:
            # Ordinal first: a History chain is a SEQUENCE, and ordering by a
            # hashed evidence_id makes that sequence unrecoverable. Rows without
            # an ordinal sort after those with one, then by id for determinism.
            return [dict(r) for r in con.execute(
                query + " ORDER BY (ordinal IS NULL), ordinal, evidence_id",
                params)]

    def resolve_external_id(self, external: str) -> Resolution:
        """EVERY state carrying this XMP id. Not one of them: every one.

        An id written by a tool names a document that may or may not be on this
        disk. Most History instanceIDs name states that are simply not here, and
        the substrate must be able to say that WITHOUT implying the state never
        existed.

        The previous version ended in ``LIMIT 1`` and returned
        ``row[0] if row else None`` -- over a query that matches document_id,
        which is SHARED BY DESIGN, because a shared DocumentID is what a lineage
        IS. Measured on this corpus: 120 DocumentIDs are carried by more than one
        state, group sizes 2 to 8, the largest being 8 reference images exported
        in one batch. So this lookup routinely had k > 1 and silently answered
        with one arbitrary row.

        Both callers only ever tested presence, which is a class-level use and was
        always sound. The trap was the signature: it promised a single state_id,
        so the first caller to actually USE the returned id would have built a
        claim about ONE object on a lookup that could not individuate.
        """
        needle = external.split(":", 1)[-1] if external.startswith("xmp:") else external
        with self.connect() as con:
            rows = con.execute(
                "SELECT state_id FROM artifact_state WHERE instance_id=? OR "
                "document_id=? OR original_document_id=? ORDER BY state_id",
                (needle, needle, needle)).fetchall()
        return resolve([r[0] for r in rows],
                       witness=f"the only state carrying {needle!r} in this corpus",
                       cause=MISSING_EVIDENCE)

    def resolve_pending_references(self) -> dict[str, int]:
        """Re-check unresolved edges after a scan. Resolution is provisional.

        At ingest time a referent may not have been read yet, so an edge is first
        recorded unresolved. This pass upgrades the ones the corpus turned out to
        contain. It never downgrades: an edge already resolved stays resolved.
        """
        upgraded = 0
        with self.connect() as con:
            rows = con.execute(
                "SELECT evidence_id, object FROM evidence WHERE object_resolution=? "
                "AND object_kind=?",
                (UNRESOLVED_IN_CORPUS, OBJ_EXTERNAL_ID)).fetchall()
            ambiguous = 0
            for evidence_id, obj in rows:
                found = self.resolve_external_id(obj)
                if is_present(found):
                    # Write the cardinality too. Without it an edge upgraded by
                    # this pass would carry candidate_count 0, which means "the
                    # lookup was never performed" -- a different and false claim
                    # from "the lookup matched k objects".
                    k = candidate_count(found)
                    con.execute("UPDATE evidence SET object_resolution=?, "
                                "unknown_cause='', candidate_count=? "
                                "WHERE evidence_id=?",
                                (RESOLVED, k, evidence_id))
                    upgraded += 1
                    if k > 1:
                        ambiguous += 1
            still = con.execute(
                "SELECT count(*) FROM evidence WHERE object_resolution=?",
                (UNRESOLVED_IN_CORPUS,)).fetchone()[0]
        return {"checked": len(rows), "upgraded_to_resolved": upgraded,
                # Resolved and ambiguous at once is a real state, not a
                # contradiction: the id is here, and it is carried by more than
                # one object. Counted separately so it stops being invisible.
                "upgraded_but_ambiguous": ambiguous,
                "still_unresolved_in_corpus": still}

    def summary(self) -> dict[str, Any]:
        with self.connect() as con:
            counts = {name: con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                      for name in ("content", "artifact_state", "lineage",
                                   "lineage_member", "observation", "evidence")}
            by_pred = {r[0]: r[1] for r in con.execute(
                "SELECT predicate, count(*) FROM evidence GROUP BY 1 ORDER BY 2 DESC")}
            multi = con.execute(
                "SELECT count(*) FROM (SELECT state_id FROM observation "
                "GROUP BY state_id HAVING count(*) > 1)").fetchone()[0]
            shared = con.execute(
                "SELECT count(*) FROM (SELECT content_id FROM artifact_state "
                "WHERE content_id IS NOT NULL GROUP BY content_id "
                "HAVING count(*) > 1)").fetchone()[0]
            conflicts = con.execute(
                "SELECT count(*) FROM evidence WHERE predicate=?",
                (CONFLICTS_WITH,)).fetchone()[0]
            unresolved = {r[0]: r[1] for r in con.execute(
                "SELECT object_resolution, count(*) FROM evidence GROUP BY 1")}
            multi_state_lineages = con.execute(
                "SELECT count(*) FROM (SELECT lineage_id FROM lineage_member "
                "GROUP BY lineage_id HAVING count(*) > 1)").fetchone()[0]
        return {
            "contract": CONTRACT,
            "counts": counts,
            "evidence_by_predicate": by_pred,
            "states_seen_in_more_than_one_place": multi,
            "content_shared_by_more_than_one_state": shared,
            "lineages_with_more_than_one_state": multi_state_lineages,
            "self_continuity_edges": sum(v for k, v in by_pred.items()
                                         if k in SELF_CONTINUITY),
            "cross_document_edges": sum(v for k, v in by_pred.items()
                                        if k in CROSS_DOCUMENT),
            "recorded_conflicts": conflicts,
            "edges_by_object_resolution": unresolved,
        }
