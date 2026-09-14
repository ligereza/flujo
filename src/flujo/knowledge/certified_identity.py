"""Feed certified byte identity into the project reconstruction that exists.

WHY THIS IS NOT A SECOND SYSTEM

``project_reconstruction.cross_root_relations`` already asks this question and
already names the answer it is missing. Its own tie-breaker text reads:

    compute full_sha256 for the overlapping assets, or obtain an operator
    attestation

That is the remedy, written down by the code that needed it. 4104 assets in 1348
sample-hash ties have now been resolved by full content digest, so the
tie-breaker exists and this module hands it over. Nothing new is decided here
that the cascade was not already trying to decide.

WHAT IT CHANGES, AND WHY THE SECOND ONE MATTERS MORE

1. ``identity_undecided`` becomes a real verdict. Measured: 1347 of 1348 groups
   resolved, 4097 assets CERTIFIED_SAME, 7 CERTIFIED_DISTINCT, 0 left unknown.

2. The lexical gate can go. The existing comparison only considers roots that
   share a four-character prefix:

       prefix = scope_root.casefold()[:4]
       lexical_neighbours = [r for r in roots if r.casefold()[:4] == prefix]

   That gate was correct when identity was unavailable -- comparing every root
   to every root on sample hashes would have produced noise. But it means
   ``LYON`` and ``SCD`` were never compared at all, and they share 188 certified
   content classes. Certified identity removes the need for the gate: content
   equality is not a similarity score, so it can be applied to every pair.

WHY A NEW PREDICATE, AND ONLY ONE

``shares_library_with`` means "both roots use the same purchased item", and its
own evidence says so: "a shared library item does not make two commissions one
project". Two roots sharing 8.84 GiB of rendered video are not doing that. Using
one predicate for both would repeat exactly the bug this vocabulary already
fixed once, when ``shared_resource`` meant a symmetric root pair in one place
and a directed owner-resource edge in another, and direction became
unrecoverable from the name.

So: ``shares_output_with``, symmetric, its own inverse, declared beside the rest.

WHAT IT REFUSES TO DECIDE

Sharing an output has two readings that content cannot separate:

    the same work filed under two names
    an output legitimately reused in a second commission

Both produce identical bytes in two places. This module raises that as a tie for
the operator instead of guessing, because the answer is a fact about the
commissions and not about the files. That is the whole point of the door: the
questions that reach the human are the ones no available authority can answer.

An image is left UNDECIDED between input and output on purpose. A .jpg may be a
purchased texture or a rendered frame, and ``media_kind`` cannot tell them
apart. What can is a .blend declaring it as a texture, which is why
``root_overlaps`` takes that evidence when it exists and does not pretend to
have it when it does not.

WHY BASENAME EVIDENCE IS ADMISSIBLE HERE AND NOWHERE NEAR OWNERSHIP

The declarations are matched by basename, and that is worthless for some claims
and sound for this one. The line between them is what the claim is ABOUT.

Measured: ``normal.jpg`` is declared by 29 different .blend files,
``roughness.jpg`` by 23, ``defaultmaterial_roughness.jpg`` by 25. Dozens of
separately purchased materials ship a file with the same generic name.

  INVALID   "this project's dependencies are present on this disk, because a
            file with that basename exists somewhere". A first pass classified
            231 of 873 .blend files as integrated on exactly that reasoning and
            it was wrong -- the generic names resolve against somebody else's
            purchased material. Under strict resolution, where a ``//`` path is
            checked against the .blend's own directory, only 88 are proven.

  VALID     "a file named X is opened as an input by Blender, therefore a file
            named X is an input rather than a render". This claim is about the
            class of filename, not about one project's dependency graph, and 29
            blends declaring ``normal.jpg`` makes it STRONGER, not weaker.

``show_asset_usage`` had already written the warning in its own limits -- "una
coincidencia de nombre es candidata, no identidad de bytes" -- and the first
pass here ignored it. The distinction above is what the second pass learned.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .project_reconstruction import (
    EMPIRICAL,
    Evidence,
    REL_SHARES_LIBRARY_WITH,
    REL_UNRELATED,
    UNKNOWN,
    UnitRelation,
)

CONTRACT = "mak-certified-identity-v1"

# Symmetric, and its own inverse. Declared here and registered by
# ``register_predicate`` so ``inverse_relation`` never has to guess.
REL_SHARES_OUTPUT_WITH = "shares_output_with"

CERTIFIED_SAME = "CERTIFIED_SAME"
CERTIFIED_DISTINCT = "CERTIFIED_DISTINCT"

# What a shared asset of this media kind is, as far as the index alone can say.
# ``image`` is deliberately absent: a texture and a rendered frame are both
# images, and guessing between them is how a purchased asset starts looking like
# a work.
KIND_ROLE = {
    "video": "output",
    "structural": "source",
    "pdf": "document",
}
UNDECIDED_KIND = "undecided"

# A file sitting loose at the top of the disk has no container, so the first
# path segment IS the filename. Treating that as a container root produced
# questions like "do '2.mov' and 'BAHPARTY' share a work?" -- which is not a
# question about two commissions at all. It is one file dragged out to the
# root, and the machine can say so without asking anybody.
ROLE_LOOSE_COPY = "loose_copy_at_root"


def register_predicate() -> None:
    """Teach the existing vocabulary the one new predicate, with its inverse."""
    from . import project_reconstruction as pr
    pr.RELATION_INVERSES.setdefault(REL_SHARES_OUTPUT_WITH, REL_SHARES_OUTPUT_WITH)


@dataclass(frozen=True)
class ContentClass:
    content_id: str
    member_count: int
    bytes_each: int
    reclaimable_bytes: int
    roots: tuple[str, ...]
    extensions: tuple[str, ...]
    crosses_roots: bool


@dataclass
class IdentityIndex:
    """Certified content identity, keyed the way the archive index is keyed."""

    content_of: dict[str, str] = field(default_factory=dict)
    verdict_of: dict[str, str] = field(default_factory=dict)
    classes: dict[str, ContentClass] = field(default_factory=dict)
    members_of: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    run: dict[str, Any] = field(default_factory=dict)

    @property
    def certified_assets(self) -> int:
        return sum(1 for v in self.verdict_of.values() if v == CERTIFIED_SAME)

    def summary(self) -> dict[str, Any]:
        crossing = [c for c in self.classes.values() if c.crosses_roots]
        return {
            "contract": CONTRACT,
            "assets_with_a_verdict": len(self.verdict_of),
            "certified_same": self.certified_assets,
            "certified_distinct": sum(1 for v in self.verdict_of.values()
                                      if v == CERTIFIED_DISTINCT),
            "content_classes": len(self.classes),
            "classes_crossing_roots": len(crossing),
            "reclaimable_bytes": sum(c.reclaimable_bytes
                                     for c in self.classes.values()),
        }


def load_identity(sidecar: str | Path) -> IdentityIndex:
    """Read the sidecar. The archive index is never opened for writing anywhere."""
    path = Path(sidecar).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"identity_sidecar_missing: {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    index = IdentityIndex()
    for content_id, count, each, reclaim, roots, exts, crosses in con.execute(
            "SELECT content_id, member_count, bytes_each, reclaimable_bytes, "
            "roots_json, extensions_json, crosses_roots FROM identity_class"):
        index.classes[content_id] = ContentClass(
            content_id=content_id, member_count=count, bytes_each=each or 0,
            reclaimable_bytes=reclaim or 0, roots=tuple(json.loads(roots)),
            extensions=tuple(json.loads(exts)), crosses_roots=bool(crosses))
    for asset_id, content_id, verdict in con.execute(
            "SELECT asset_id, content_id, verdict FROM identity_asset"):
        index.verdict_of[asset_id] = verdict
        if content_id:
            index.content_of[asset_id] = content_id
            index.members_of[content_id].append(asset_id)
    row = con.execute("SELECT record_json FROM identity_run LIMIT 1").fetchone()
    if row:
        index.run = json.loads(row[0])
    con.close()
    return index


@dataclass
class RootOverlap:
    """Two container roots, and exactly what content they provably share."""

    left: str
    right: str
    shared_classes: int = 0
    shared_bytes: int = 0
    by_role: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_by_role: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    nested: bool = False
    loose: bool = False
    declaring_blends: int = 0
    examples: list[str] = field(default_factory=list)

    @property
    def dominant_role(self) -> str:
        if not self.bytes_by_role:
            return UNDECIDED_KIND
        return max(self.bytes_by_role.items(), key=lambda kv: kv[1])[0]

    def as_dict(self) -> dict[str, Any]:
        return {
            "left": self.left, "right": self.right,
            "shared_classes": self.shared_classes,
            "shared_bytes": self.shared_bytes,
            "by_role": dict(self.by_role),
            "bytes_by_role": dict(self.bytes_by_role),
            "dominant_role": self.dominant_role,
            "nested": self.nested,
            "loose": self.loose,
            "declaring_blends": self.declaring_blends,
            "examples": self.examples[:5],
        }


def root_overlaps(index_path: str | Path, identity: IdentityIndex,
                  *, declarations: Mapping[str, str] | None = None
                  ) -> list[RootOverlap]:
    """Every unordered pair of roots that provably shares content.

    No lexical gate. Content equality is not a similarity score, so there is no
    noise to suppress by only comparing roots with similar names -- and that gate
    is what kept LYON and SCD from ever being compared.
    """
    con = sqlite3.connect(f"file:{Path(index_path).expanduser()}?mode=ro", uri=True)
    kinds: dict[str, str] = {}
    paths: dict[str, str] = {}
    for asset_id, kind, relative in con.execute(
            "SELECT asset_id, media_kind, relative_path FROM assets"):
        kinds[asset_id] = kind or ""
        paths[asset_id] = relative
    # Which top-level names are files rather than directories. Read from the
    # index instead of guessed from the extension: a directory may be named
    # "x.mov" and a file may have no extension at all.
    loose_files = {r[0] for r in con.execute(
        "SELECT relative_path FROM assets WHERE relative_path NOT LIKE '%/%'")}
    con.close()

    declared_inputs = declarations or {}
    pairs: dict[tuple[str, str], RootOverlap] = {}
    for content_id, klass in identity.classes.items():
        if not klass.crosses_roots:
            continue
        members = identity.members_of.get(content_id, [])
        role = UNDECIDED_KIND
        declaring = 0
        for asset_id in members:
            # A .blend that declares this basename as a texture settles what the
            # media kind cannot: an image can be a purchased texture or a
            # rendered frame, and only the file that opens it knows which.
            basename = paths.get(asset_id, "").rsplit("/", 1)[-1]
            declaring = max(declaring, int(declared_inputs.get(basename, 0) or 0))
        if declaring:
            role = "source"
        else:
            observed = {KIND_ROLE.get(kinds.get(a, ""), UNDECIDED_KIND)
                        for a in members}
            observed.discard(UNDECIDED_KIND)
            role = observed.pop() if len(observed) == 1 else UNDECIDED_KIND
        roots = sorted(set(klass.roots))
        for i, left in enumerate(roots):
            for right in roots[i + 1:]:
                key = (left, right)
                overlap = pairs.setdefault(key, RootOverlap(
                    left=left, right=right,
                    nested=right.startswith(left + "/") or left.startswith(right + "/"),
                    loose=left in loose_files or right in loose_files))
                overlap.shared_classes += 1
                overlap.shared_bytes += klass.bytes_each
                overlap.by_role[role] += 1
                overlap.bytes_by_role[role] += klass.bytes_each
                overlap.declaring_blends = max(overlap.declaring_blends, declaring)
                if len(overlap.examples) < 6:
                    # One member from each side, so the example shows the pair
                    # rather than the same file three times.
                    for asset_id in members:
                        shown = paths.get(asset_id, "")
                        if shown.startswith((left, right)) and shown not in overlap.examples:
                            overlap.examples.append(shown)
    return sorted(pairs.values(), key=lambda o: -o.shared_bytes)


def identity_relations(overlaps: Iterable[RootOverlap]) -> list[UnitRelation]:
    """Turn provable overlap into relations in the vocabulary that exists.

    Three outcomes, and the third one is the point:

      source-dominated   shares_library_with, EMPIRICAL. Reuse of an input.
      output-dominated   shares_output_with, UNKNOWN with the alternatives kept.
                         Content cannot distinguish "one work, two names" from
                         "output reused in a second commission", so it does not.
      undecided          shares_output_with, UNKNOWN, waiting on the declaration
                         evidence that would settle the role.
    """
    register_predicate()
    relations: list[UnitRelation] = []
    for overlap in overlaps:
        provable = Evidence(
            "certified_content_identity", "relation",
            f"{overlap.shared_classes} content classes, "
            f"{overlap.shared_bytes} bytes, are byte-identical under both roots, "
            "proven by full sha256 rather than by a sample")
        if overlap.loose:
            relations.append(UnitRelation(
                overlap.left, REL_SHARES_LIBRARY_WITH, overlap.right, EMPIRICAL,
                evidence_for=[provable, Evidence(
                    "one_side_is_a_loose_file", "observation",
                    "one of these two names is a file at the top of the disk, "
                    "not a container. This is a copy dragged out of its folder, "
                    "which is a fact about the filesystem and needs no operator "
                    "decision")]))
            continue
        if overlap.nested:
            relations.append(UnitRelation(
                overlap.left, REL_SHARES_LIBRARY_WITH, overlap.right, EMPIRICAL,
                evidence_for=[provable, Evidence(
                    "one_contains_the_other", "derived_feature",
                    "these two rows are a folder and its own ancestor, so the "
                    "shared content is the same file counted twice by the "
                    "folder scan, not two copies")]))
            continue
        if overlap.dominant_role == "source":
            declared = ([Evidence(
                "declared_as_input_by_a_blend", "relation",
                f"{overlap.declaring_blends} .blend files declare a file of this "
                "name as something they open. Matching is by basename, so a "
                "collision is possible; the claim is that SOME project uses an "
                "input with this name, which is what settles input vs output")]
                if overlap.declaring_blends else [])
            relations.append(UnitRelation(
                overlap.left, REL_SHARES_LIBRARY_WITH, overlap.right, EMPIRICAL,
                evidence_for=[provable, *declared, Evidence(
                    "shared_content_is_input", "derived_feature",
                    "the shared bytes are sources or declared textures, which "
                    "is reuse of an input")],
                evidence_against=[Evidence(
                    "reuse_is_not_identity", "derived_feature",
                    "a shared input does not make two commissions one work")]))
            continue
        relations.append(UnitRelation(
            overlap.left, REL_SHARES_OUTPUT_WITH, overlap.right, UNKNOWN,
            evidence_for=[provable],
            evidence_against=[Evidence(
                "identical_bytes_have_two_readings", "derived_feature",
                "one work filed twice, and an output reused in a second "
                "commission, produce the same bytes in both places")],
            alternatives=["same_work_under_two_names",
                          "output_reused_in_a_second_commission"],
            tie_breaker_needed="the operator: this is a fact about the "
                               "commissions, not about the files"))
    return relations


def open_questions(relations: Iterable[UnitRelation],
                   overlaps: Iterable[RootOverlap]) -> list[dict[str, Any]]:
    """The questions that must reach the operator, heaviest first.

    Sorted by shared bytes because the first decisions in the previous door were
    worth 791 rows each and the last 512 were worth 1.6. A door that is not
    sorted by leverage spends the scarce resource -- attention -- on the tail.
    """
    weight = {(o.left, o.right): o for o in overlaps}
    questions = []
    for relation in relations:
        if relation.epistemic_status != UNKNOWN:
            continue
        overlap = weight.get((relation.left, relation.right))
        questions.append({
            "left": relation.left,
            "right": relation.right,
            "question": f"{relation.left!r} and {relation.right!r} share "
                        f"{overlap.shared_classes if overlap else 0} identical "
                        f"contents. Is that one work filed under two names, or "
                        f"an output you reused in a second commission?",
            "answers": list(relation.alternatives),
            "shared_bytes": overlap.shared_bytes if overlap else 0,
            "shared_classes": overlap.shared_classes if overlap else 0,
            "examples": overlap.examples[:3] if overlap else [],
            "why_not_machine_answerable": relation.tie_breaker_needed,
        })
    questions.sort(key=lambda q: -q["shared_bytes"])
    return questions


def triage(questions: list[dict[str, Any]], *, coverage: float = 0.93,
           max_asked: int = 25) -> dict[str, Any]:
    """Split the questions into the ones worth asking now and the residue.

    Attention is the scarce resource, not disk. In the previous door the first
    three operator decisions were worth 791 rows each and the last 512 were
    worth 1.6, so a door that is not cut by leverage spends the scarce resource
    on the tail. Measured here: 6 of 50 questions carry 93% of the disputed
    bytes, and 20 of them carry less than 0.01 GiB each.

    Nothing is dropped. Every deferred question keeps a ``reopen_when``, because
    a provisional fold must preserve not only how to reopen but a channel by
    which the system can come to suspect that it should. Without that the
    deferred questions are indistinguishable from questions that were answered.
    """
    ordered = sorted(questions, key=lambda q: -q["shared_bytes"])
    total = sum(q["shared_bytes"] for q in ordered) or 1
    ask: list[dict[str, Any]] = []
    running = 0
    for question in ordered:
        if len(ask) >= max_asked or running / total >= coverage:
            break
        ask.append(question)
        running += question["shared_bytes"]
    deferred = []
    for question in ordered[len(ask):]:
        deferred.append({
            **question,
            # The monitor. Not built on the missing feature: it fires on a
            # query naming either root, which is observable without knowing the
            # answer to the question itself.
            "reopen_when": f"any query names {question['left']!r} or "
                           f"{question['right']!r}, or the shared bytes grow",
        })
    return {
        "ask": ask,
        "deferred": deferred,
        "asked_count": len(ask),
        "deferred_count": len(deferred),
        "coverage_of_disputed_bytes": round(running / total, 4),
        "deferred_bytes": total - running,
        # Stated, never implied: a cap that is not logged reads as full coverage.
        "cut_rule": f"sorted by shared bytes, stopped at {coverage:.0%} coverage "
                    f"or {max_asked} questions, whichever came first",
    }
