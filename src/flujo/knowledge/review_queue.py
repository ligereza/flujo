"""Order the review queue by how much one human answer resolves.

Why this exists
---------------
Measured on the live learning database before this module was written:

- ``project_records``: 34 ``review_required``, 4 ``active``, 1 ``candidate``
- ``project_transitions``: **0 rows**
- ``transition_project()``: 1 call in the whole repository, inside its own test

Four machines were built that write records a person has to read, the state
machine that records a person's answer was written and validated, and no surface
was ever built to reach it. Nothing had ever been decided, so nothing had ever
been consumed. The queue was not slow -- it had no door.

The problem under the feature
-----------------------------
A human's attention is the scarcest resource in this system and the queue only
grows: 34 project records today, 8273 rows pending in ``classification_queue``.
So the question is not "how do we display a list" but "which question, asked
first, resolves the most records".

That is answerable without inventing a score. The containment edges form a
forest, and one kind of answer propagates along it, so the number of records a
single decision can settle is a COUNT, not a judgement. It is reported next to
the item rather than folded into a ranking number.

What propagates and what does not
---------------------------------
Rejection propagates downward. A folder that is an ``Adobe After Effects
Auto-Save`` directory cannot contain a delivered work, because the rejection is a
claim about what the container IS, and its contents are inside that container.

Acceptance does not propagate. A real work legitimately holds both delivered
pieces and working material, so "this is a work" says nothing about its children.

The asymmetry is falsifiable: if the operator ever overrides an inherited
rejection, that is a counterexample and the override is what should be recorded.
Nothing is inherited automatically -- inheritance is proposed and the operator
applies it explicitly.

Ordering, and the weakest link in it
------------------------------------
Lexicographic, never a weighted sum, because the keys are not commensurable:

1. ``leverage`` descending -- how many pending descendants one answer could
   settle. Measured, and the reason this module exists.
2. ``bytes_total`` descending -- a proxy for how much of the operator's own
   labour sits in the folder. This is the WEAKEST of the three and the one to
   replace first if a better observation appears; it is a tiebreaker inside equal
   leverage and never trades against it.
3. ``title`` ascending -- so the order is reproducible.

What this module never does
---------------------------
It does not decide. It orders, it presents the evidence already in the record,
and every write requires a reason and an actor from outside. It cannot invent
evidence: ``active`` and ``verified`` are refused by the schema without any, and
that refusal is passed through rather than worked around.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .project_ir import ALLOWED_TRANSITIONS, LearningStore, ProjectIRError
from ..substrate import Absent, Many, Resolution, resolve
from ..substrate.epistemics import MISSING_EVIDENCE

CONTRACT = "mak-review-queue-v1"

REVIEW_STATE = "review_required"

# Four records in the live queue came from elsewhere (research notes, a maths
# capsule) and carry no reconstruction block. They are still pending and still
# belong in the queue, but calling their role "unknown" would collide with the
# epistemic UNKNOWN label, which means something else entirely.
NOT_RECONSTRUCTED = "not_from_reconstruction"

# A decision that rejects the container. Its pending descendants can inherit it,
# as a PROPOSAL, because the claim is about what the container is.
REJECTING_STATES = frozenset({"quarantined", "contradicted"})

# A decision that accepts the container. Nothing is inherited: a work holds both
# delivered pieces and working material.
ACCEPTING_STATES = frozenset({"active", "verified"})

# The schema refuses these without evidence, so the door has to ask for it.
EVIDENCE_REQUIRED_STATES = frozenset({"active", "verified"})


class ReviewQueueError(ValueError):
    """The queue was asked for something it cannot answer honestly."""


@dataclass
class QueueItem:
    """One record waiting for a person, with the facts already measured."""

    project_id: str
    title: str
    state: str
    role: str
    scope: str
    asset_count: int
    bytes_total: int
    media_mix: dict[str, int]
    parent_title: str | None
    pending_descendants: tuple[str, ...]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    updated_at: str = ""
    _subtree_bytes: int = 0

    @property
    def rejection_leverage(self) -> int:
        """Records a REJECTION here would settle, counting this one.

        Named for the rejecting case on purpose. Acceptance does not propagate,
        so for "this is a work" the number is always 1 no matter how large the
        subtree is. Calling it plain "leverage" would have promised the operator
        a saving that only one of the two answers actually pays.
        """
        return 1 + len(self.pending_descendants)

    @property
    def subtree_bytes(self) -> int:
        """Set by ``load_queue``: this record plus its pending descendants.

        ``bytes_total`` counts only the artifacts assigned directly to this
        record. For a container that is much smaller than the work under it --
        LYON measures 27.2 GB directly and 250.9 GB in its scope -- reporting
        only the direct figure invites the reader to misjudge the material.
        """
        return self._subtree_bytes

    @property
    def sort_key(self) -> tuple[int, int, str]:
        """Lexicographic, by rejection leverage then by material then by name."""
        return (-self.rejection_leverage, -self.subtree_bytes, self.title)

    @property
    def material_key(self) -> tuple[int, str]:
        """For the recognition pass, where every leverage is 1."""
        return (-self.subtree_bytes, self.title)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "state": self.state,
            "role": self.role,
            "scope": self.scope,
            "assets": self.asset_count,
            "bytes_direct": self.bytes_total,
            "bytes_subtree": self.subtree_bytes,
            "media_mix": dict(self.media_mix),
            "parent": self.parent_title,
            "rejection_leverage": self.rejection_leverage,
            "pending_descendants": list(self.pending_descendants),
            "unknowns": list(self.unknowns),
            "evidence": list(self.evidence),
            "updated_at": self.updated_at,
            "decisions_available": sorted(ALLOWED_TRANSITIONS.get(self.state, ())),
        }


def _read_only(database: str | Path) -> sqlite3.Connection:
    path = Path(database).expanduser()
    if not path.is_file():
        raise ReviewQueueError(f"learning_database_missing: {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _bytes_of(record: Mapping[str, Any]) -> int:
    total = 0
    for artifact in record.get("artifacts", ()):
        try:
            total += int(artifact.get("size_bytes") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _parent_title(record: Mapping[str, Any]) -> str | None:
    """The container, read from the direction the graph now actually states.

    ``contained_by`` is the inverse of ``contains`` and only exists because the
    projector used to state both directions with the same predicate. Reading
    ``contains`` here would have found the record's own children.
    """
    for relation in record.get("relations", ()):
        if relation.get("predicate") != "contained_by":
            continue
        target = str(relation.get("object") or "")
        # reconstruction://<scope>/<path>
        parts = target.split("://", 1)
        if len(parts) != 2:
            continue
        rest = parts[1].split("/", 1)
        if len(rest) != 2:
            continue
        return rest[1]
    return None


PASS_PRUNE = "prune"
PASS_RECOGNIZE = "recognize"


def load_queue(database: str | Path, *, state: str = REVIEW_STATE,
               scope: str | None = None,
               review_pass: str = PASS_PRUNE) -> list[QueueItem]:
    """Every record in ``state``, ordered for the pass the caller is doing.

    There are two real passes and they want opposite orders, so choosing one
    silently would have served one of them badly:

    - ``prune`` -- reject the containers that are not works at all. Rejection
      propagates down the containment tree, so the biggest subtree first is the
      cheapest route through the queue.
    - ``recognize`` -- name the works among what survived. Every leverage is 1
      here, so the order is by material, largest first.
    """
    if review_pass not in {PASS_PRUNE, PASS_RECOGNIZE}:
        raise ReviewQueueError(f"unknown_review_pass: {review_pass}")
    with _read_only(database) as con:
        rows = con.execute(
            "SELECT project_id, title, state, ir_json, updated_at "
            "FROM project_records WHERE state = ? ORDER BY title", (state,)
        ).fetchall()

    parsed: list[tuple[sqlite3.Row, dict[str, Any]]] = []
    for row in rows:
        try:
            record = json.loads(row["ir_json"])
        except json.JSONDecodeError:
            continue
        parsed.append((row, record))

    pending_titles = {str(record.get("title") or row["title"])
                      for row, record in parsed}
    children: dict[str, list[str]] = {}
    for row, record in parsed:
        parent = _parent_title(record)
        if parent is not None:
            children.setdefault(parent, []).append(
                str(record.get("title") or row["title"]))

    def descendants(title: str, seen: frozenset[str] = frozenset()) -> list[str]:
        # A cycle would mean the containment graph is not a forest, which would
        # itself be a finding. Guard rather than recurse forever.
        if title in seen:
            return []
        out: list[str] = []
        for child in sorted(children.get(title, ())):
            if child not in pending_titles:
                continue
            out.append(child)
            out.extend(descendants(child, seen | {title}))
        return out

    items: list[QueueItem] = []
    for row, record in parsed:
        reconstruction = record.get("reconstruction") or {}
        feature = reconstruction.get("feature") or {}
        title = str(record.get("title") or row["title"])
        item_scope = str(reconstruction.get("scope") or "")
        if scope and item_scope != scope and not title.startswith(f"{scope}/") \
                and title != scope:
            continue
        items.append(QueueItem(
            project_id=str(row["project_id"]),
            title=title,
            state=str(row["state"]),
            role=str(reconstruction.get("role") or NOT_RECONSTRUCTED),
            scope=item_scope,
            asset_count=int(feature.get("asset_count") or 0),
            bytes_total=_bytes_of(record),
            media_mix=dict(feature.get("media_mix") or {}),
            parent_title=_parent_title(record),
            pending_descendants=tuple(dict.fromkeys(descendants(title))),
            evidence=list(record.get("evidence") or ()),
            unknowns=list(record.get("unknowns") or ()),
            updated_at=str(row["updated_at"] or ""),
        ))
    # A THIRD occurrence of the audited pattern: this used to be
    # ``by_title = {item.title: item for item in items}``, a dict literal that
    # silently kept whichever same-titled record was built last and dropped
    # its bytes from every subtree total above it. This is a read total, not a
    # write, so the fix is not Unique/Many/Absent (nothing here picks "the"
    # project to mutate) -- it is to stop discarding rows and sum bytes_total
    # across every item that carries a given descendant title.
    by_title: dict[str, list[QueueItem]] = {}
    for entry in items:
        by_title.setdefault(entry.title, []).append(entry)
    for item in items:
        item._subtree_bytes = item.bytes_total + sum(
            entry.bytes_total
            for title in item.pending_descendants
            for entry in by_title.get(title, ()))
    if review_pass == PASS_RECOGNIZE:
        items.sort(key=lambda item: item.material_key)
    else:
        items.sort(key=lambda item: item.sort_key)
    return items


def inherited_proposals(item: QueueItem, to_state: str) -> list[str]:
    """Descendants a rejecting decision would carry, as a proposal only.

    Empty for an accepting decision, on purpose: a work contains working
    material, so accepting the parent proves nothing about the children.
    """
    if to_state in REJECTING_STATES:
        return list(item.pending_descendants)
    return []


def resolve_title(items: Sequence[QueueItem], title: str) -> Resolution:
    """Every pending item with exactly this title, as a Resolution.

    MEASURED: ``project_records.title`` carries no UNIQUE constraint in the
    DDL (plain ``title TEXT NOT NULL``) and is written by three producers
    (``reconstruction_adapter`` sets ``title=project_path``, unique by
    construction; ``source_learning`` and ``math_kernel`` pass an arbitrary
    human- or JSON-authored ``case["title"]`` into the same table). A title
    lookup can therefore already return 0, 1, or N rows even though the
    snapshot measured at audit time (41 rows, 0 duplicate titles) had not
    shown a collision yet. This replaces the previous
    ``by_title = {item.title: item for item in items}`` dict literal, which
    silently kept whichever same-titled row happened to be built last.
    """
    matches = [item for item in items if item.title == title]
    return resolve(matches, witness=f"title matched exactly one pending item: {title}",
                    cause=MISSING_EVIDENCE)


def decide(database: str | Path, project_id: str, to_state: str, *,
           reason: str, actor: str,
           evidence: Sequence[Mapping[str, Any]] = (),
           cascade_titles: Iterable[str] = ()) -> dict[str, Any]:
    """Record one human decision, and only the ones asked for.

    ``cascade_titles`` must be named explicitly by the caller. An inherited
    rejection is a proposal until a person applies it, so nothing propagates as
    a side effect of this call.

    If any name in ``cascade_titles`` resolves to more than one pending
    record, the WHOLE call is refused before a single ``transition_project``
    executes -- including the primary ``project_id`` decision. A partial
    cascade is worse than none: the operator who asked for it believes the
    whole subtree was handled, when only the unambiguous half of it was.
    """
    reason = str(reason or "").strip()
    actor = str(actor or "").strip()
    if not reason:
        raise ReviewQueueError("a_decision_needs_a_reason")
    if not actor:
        raise ReviewQueueError("a_decision_needs_an_actor")
    if to_state in EVIDENCE_REQUIRED_STATES and not evidence:
        # The schema refuses this too. Saying so here names the reason instead of
        # surfacing "invalid_transition_record" from three layers down.
        raise ReviewQueueError(f"{to_state}_requires_evidence")

    rows = [dict(item) for item in evidence]
    store = LearningStore(Path(database).expanduser())
    applied: list[dict[str, str]] = []
    refused: list[dict[str, str]] = []

    cascade_names = [str(title) for title in cascade_titles]
    cascade_children: list[tuple[str, str]] = []
    if cascade_names:
        items = load_queue(database)
        target = next((item for item in items if item.project_id == project_id), None)
        if target is not None:
            target_resolution = resolve_title(items, target.title)
            if isinstance(target_resolution, Many):
                raise ReviewQueueError(
                    f"cascade_ambiguous: parent {target.title}:"
                    f"{target_resolution.k}_candidates")
        resolutions = {title: resolve_title(items, title) for title in cascade_names}
        ambiguous = {title: res for title, res in resolutions.items()
                    if isinstance(res, Many)}
        if ambiguous:
            detail = ",".join(f"{title}:{res.k}_candidates"
                              for title, res in ambiguous.items())
            raise ReviewQueueError(f"cascade_ambiguous: {detail}")
        for title in cascade_names:
            resolution = resolutions[title]
            if isinstance(resolution, Absent):
                refused.append({"title": title, "error": "not_pending"})
                continue
            child = resolution.value
            cascade_children.append((child.project_id,
                                     f"inherited from the decision on this container: {reason}"))

    targets = [(project_id, reason)] + cascade_children
    for target_id, target_reason in targets:
        try:
            store.transition_project(target_id, to_state, reason=target_reason,
                                     evidence=rows, actor=actor)
        except ProjectIRError as exc:
            refused.append({"project_id": target_id, "error": str(exc)})
            continue
        applied.append({"project_id": target_id, "to_state": to_state})

    return {"contract": CONTRACT, "applied": applied, "refused": refused,
            "actor": actor}


def summary(items: Sequence[QueueItem]) -> dict[str, Any]:
    """What the queue costs, in the units a person actually spends."""
    roots = [item for item in items if item.parent_title is None]
    return {
        "contract": CONTRACT,
        "pending": len(items),
        "roots": len(roots),
        "max_rejection_leverage": max(
            (item.rejection_leverage for item in items), default=0),
        "answers_to_clear_by_containment": len(roots),
        "bytes": sum(item.bytes_total for item in items),
        "assets": sum(item.asset_count for item in items),
        "by_role": {role: sum(1 for i in items if i.role == role)
                    for role in sorted({i.role for i in items})},
        "by_scope": {scope: sum(1 for i in items if i.scope == scope)
                     for scope in sorted({i.scope for i in items})},
    }
