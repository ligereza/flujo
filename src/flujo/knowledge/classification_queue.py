"""Put a door on the classification queue, and stop asking what is not a question.

Measured before writing anything:

    classification_queue     8273 rows, ALL pending
    distinct reasons         4 -- one template per candidate kind
    writers of `status`      none; the producer is the only code that touches it

Same disease as the project queue, second location: one producer, zero
consumers, so nothing could ever be marked answered. But the shape of the
problem is different, and copying the previous door would have been wrong.

8273 is not a number of questions
---------------------------------
It is a number of ROWS. Decomposed by evidence that can be checked:

    1463  inside a virtual environment   pyvenv.cfg proven on disk
    2566  byte-identical to a repo file  sha256 match, canonical path named
    1035  in the live repository         needs a person
    3209  everywhere else                needs a person

So 4029 rows -- 48.7% -- are not questions for a human at all, and they are not
"probably not" either: each carries a check anyone can repeat. The 1463 come from
ONE directory, a Windows virtualenv copied onto the box, which the scanner walked
into because its skip list held names rather than a definition. That cause is
fixed in ``tools/build_mak_knowledge_db.py``; these rows are the backlog it left.

The question itself is malformed, and that is why it never moved
---------------------------------------------------------------
"python implementation requires purpose and consumer classification" bundles two
questions whose natural units are different, and no single decision can answer
both. The counterexample is in the data: 44 queued files are zero-byte
``__init__.py``. Byte-identical content, so identical PURPOSE -- a package marker
-- and they sit in 5 different trees, so different CONSUMERS.

    purpose / project    a function of content   -> one answer per content class
    consumer / route     a function of position  -> one answer per file

Bundled, the cheap half is held hostage by the expensive half 8273 times. Split,
the queue becomes answerable. ``QUESTION_PARTS`` states the split for each kind
instead of leaving it implicit.

What a person is actually asked
-------------------------------
For the rows that do need a person, the unit is ``(candidate_kind, directory)``,
because the coarse half of every question is a property of the directory: a
corpus folder is reference material, a tests folder is tests. Measured on the
authored rows, 5 directories cover half of them and 87 cover 80%.

This module never resolves anything by itself. The machine rules produce
PROPOSALS with their evidence; applying them is one signed act that authorises a
RULE, not 4029 separate judgements. Nothing is deleted: a resolved row keeps its
reason and its evidence, and every resolution is appended to an audit table.
"""

from __future__ import annotations

import json
import os
import posixpath
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .feature_policy import FeaturePolicyError, may_decide
from ._io_helpers import utc_now_iso as _now

CONTRACT = "mak-classification-queue-v1"

STATUS_PENDING = "pending"
STATUS_INSTALLED_DEPENDENCY = "installed_dependency"
STATUS_COPY_OF_CANONICAL = "copy_of_canonical"
STATUS_CLASSIFIED = "classified"
STATUS_ABSTAINED = "abstained"

RESOLVED_STATUSES = frozenset({
    STATUS_INSTALLED_DEPENDENCY, STATUS_COPY_OF_CANONICAL,
    STATUS_CLASSIFIED, STATUS_ABSTAINED,
})

RULE_VIRTUALENV = "inside_virtual_environment"
RULE_CANONICAL_COPY = "byte_identical_to_canonical"

# Which halves of the bundled question a human answer actually covered.
#
# A NEGATIVE coarse answer subsumes the fine one: if a folder is machine-generated
# corpus rather than authored work, asking which proposal each file belongs to is
# moot. A POSITIVE coarse answer does not: naming the project still leaves every
# file's consumer open. Same asymmetry the project review queue has between
# rejection and acceptance, and it is not a coincidence -- a negative claim about
# a container settles its contents, a positive one does not.
#
# Recorded per resolution so a coarse-only answer stays visible instead of
# vanishing from the pending count as if the whole question were closed.
COVERS_COARSE_ONLY = "coarse_only"
COVERS_BOTH = "both"
COVERAGE_CHOICES = (COVERS_COARSE_ONLY, COVERS_BOTH)

# The two halves of each bundled question, and the unit each half is answered in.
# Stated here so the split is a declaration rather than something a reader has to
# reconstruct from the row count.
QUESTION_PARTS: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "tool": (("purpose", "content_class"), ("consumer", "file")),
    "idea": (("project", "directory"), ("proposal", "file")),
    "interface": (("route", "file"), ("consumer", "file")),
    "consumer": (("route_validation", "import"), ("runtime_reach", "file")),
}

RESOLUTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS classification_resolutions (
    resolution_id INTEGER PRIMARY KEY,
    queue_id INTEGER NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    rule TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY(queue_id) REFERENCES classification_queue(queue_id)
);
CREATE INDEX IF NOT EXISTS idx_class_resolutions_queue
    ON classification_resolutions(queue_id, created_at);
"""


class ClassificationQueueError(ValueError):
    """The queue was asked for something it cannot answer honestly."""


def _require_ordering_permission(feature_name: str, question: str) -> dict[str, Any]:
    """Require the epistemic gate before emitting a machine proposal."""
    try:
        permission = may_decide(
            feature_name, question, authority_consulted=True)
    except FeaturePolicyError as exc:
        raise ClassificationQueueError(
            f"ordering_policy_refused: {exc}") from exc
    if not permission.allowed:
        raise ClassificationQueueError(
            f"ordering_policy_refused: {permission.reason}")
    return permission.as_dict()


@dataclass(frozen=True)
class Candidate:
    """One queued row, with the facts the join already provides."""

    queue_id: int
    artifact_id: int
    candidate_kind: str
    reason: str
    status: str
    path: str
    sha256: str | None
    size_bytes: int
    root_kind: str

    @property
    def directory(self) -> str:
        return posixpath.dirname(self.path)

    @property
    def parts(self) -> tuple[tuple[str, str], tuple[str, str]] | None:
        return QUESTION_PARTS.get(self.candidate_kind)


@dataclass(frozen=True)
class Proposal:
    """A machine claim about one row, with the check that backs it."""

    queue_id: int
    path: str
    to_status: str
    rule: str
    evidence: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"queue_id": self.queue_id, "path": self.path,
                "to_status": self.to_status, "rule": self.rule,
                "evidence": [dict(item) for item in self.evidence]}


@dataclass
class QuestionGroup:
    """What a person is actually asked, once the rows are folded."""

    candidate_kind: str
    directory: str
    rows: int
    content_classes: int
    bytes_total: int
    coarse_part: str
    coarse_unit: str
    fine_part: str
    fine_unit: str
    examples: tuple[str, ...] = ()
    queue_ids: tuple[int, ...] = field(default=(), repr=False)

    @property
    def sort_key(self) -> tuple[int, str, str]:
        return (-self.rows, self.candidate_kind, self.directory)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_kind": self.candidate_kind,
            "directory": self.directory,
            "rows": self.rows,
            "content_classes": self.content_classes,
            "bytes": self.bytes_total,
            "coarse_question": {"asks": self.coarse_part, "unit": self.coarse_unit},
            "fine_question": {"asks": self.fine_part, "unit": self.fine_unit},
            "examples": list(self.examples),
        }


def _read_only(database: str | Path) -> sqlite3.Connection:
    path = Path(database).expanduser()
    if not path.is_file():
        raise ClassificationQueueError(f"knowledge_database_missing: {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def load_candidates(database: str | Path, *, status: str = STATUS_PENDING,
                    kind: str | None = None) -> list[Candidate]:
    query = ("SELECT c.queue_id, c.artifact_id, c.candidate_kind, c.reason, c.status,"
             " a.path, a.sha256, a.size_bytes, a.root_kind"
             " FROM classification_queue c JOIN artifacts a USING(artifact_id)"
             " WHERE c.status = ?")
    params: list[Any] = [status]
    if kind:
        query += " AND c.candidate_kind = ?"
        params.append(kind)
    with _read_only(database) as con:
        rows = con.execute(query + " ORDER BY c.queue_id", params).fetchall()
    return [Candidate(**dict(row)) for row in rows]


def virtual_environment_root(path: str) -> str | None:
    """The ancestor directory Python marked as a virtual environment.

    Checked against the filesystem, not against a name. Returns ``None`` when
    nothing above the file carries ``pyvenv.cfg`` -- including when the path no
    longer exists, because an unreadable disk is not evidence of anything.
    """
    parts = path.split(os.sep)
    for index in range(len(parts) - 1, 1, -1):
        candidate = os.sep.join(parts[:index])
        if not candidate:
            continue
        try:
            if os.path.isfile(os.path.join(candidate, "pyvenv.cfg")):
                return candidate
        except OSError:
            return None
    return None


def canonical_index(database: str | Path, canonical_root: str) -> dict[str, str]:
    """One representative path per content class inside the canonical root."""
    root = canonical_root.rstrip("/") + "/"
    index: dict[str, str] = {}
    with _read_only(database) as con:
        for row in con.execute(
            "SELECT path, sha256 FROM artifacts WHERE path LIKE ? AND sha256 IS NOT NULL"
            " ORDER BY path", (root + "%",)
        ):
            index.setdefault(str(row["sha256"]), str(row["path"]))
    return index


def machine_proposals(candidates: Sequence[Candidate], *,
                      canonical: Mapping[str, str],
                      canonical_root: str) -> list[Proposal]:
    """Rows a check can settle, with the check attached. Applies nothing.

    Order matters and is not arbitrary: a file inside a virtual environment is an
    installed dependency even when its bytes happen to match something in the
    repository, because the repository may vendor the same file.
    """
    root = canonical_root.rstrip("/") + "/"
    out: list[Proposal] = []
    for item in candidates:
        env_root = virtual_environment_root(item.path)
        if env_root:
            policy = _require_ordering_permission(
                "declared_marker", "provenance class (installed vs authored)")
            out.append(Proposal(
                item.queue_id, item.path, STATUS_INSTALLED_DEPENDENCY,
                RULE_VIRTUALENV,
                ({"kind": "filesystem_check",
                  "detail": f"{env_root}/pyvenv.cfg exists, so this tree was "
                             "installed by a package manager, not authored"},
                  {"kind": "ordering_policy", "detail": policy},),
            ))
            continue
        if item.path.startswith(root):
            continue
        if item.sha256 and item.sha256 in canonical:
            policy = _require_ordering_permission(
                "content_hash", "that two rows are the same content")
            out.append(Proposal(
                item.queue_id, item.path, STATUS_COPY_OF_CANONICAL,
                RULE_CANONICAL_COPY,
                ({"kind": "content_identity",
                  "detail": f"sha256 identical to {canonical[item.sha256]}"},
                 {"kind": "scope_note",
                   "detail": "the canonical file carries the classification; this "
                              "copy inherits the coarse half and nothing else"},
                 {"kind": "ordering_policy", "detail": policy}),
            ))
    return out


def question_groups(candidates: Sequence[Candidate],
                    settled: Iterable[int] = ()) -> list[QuestionGroup]:
    """The rows that need a person, folded into the unit they are asked in."""
    skip = set(settled)
    buckets: dict[tuple[str, str], list[Candidate]] = {}
    for item in candidates:
        if item.queue_id in skip:
            continue
        buckets.setdefault((item.candidate_kind, item.directory), []).append(item)
    groups: list[QuestionGroup] = []
    for (kind, directory), rows in buckets.items():
        parts = QUESTION_PARTS.get(kind)
        coarse, fine = parts if parts else (("unknown", "file"), ("unknown", "file"))
        groups.append(QuestionGroup(
            candidate_kind=kind,
            directory=directory,
            rows=len(rows),
            content_classes=len({r.sha256 for r in rows if r.sha256}),
            bytes_total=sum(r.size_bytes for r in rows),
            coarse_part=coarse[0], coarse_unit=coarse[1],
            fine_part=fine[0], fine_unit=fine[1],
            examples=tuple(posixpath.basename(r.path) for r in rows[:4]),
            queue_ids=tuple(r.queue_id for r in rows),
        ))
    groups.sort(key=lambda group: group.sort_key)
    return groups


def coverage(groups: Sequence[QuestionGroup], fraction: float = 0.8) -> int:
    """How many groups a person must answer to reach ``fraction`` of the rows."""
    if not 0 < fraction <= 1:
        raise ClassificationQueueError(f"fraction_out_of_range: {fraction}")
    total = sum(group.rows for group in groups)
    if not total:
        return 0
    seen = 0
    for index, group in enumerate(groups, start=1):
        seen += group.rows
        if seen >= total * fraction:
            return index
    return len(groups)


def apply_resolutions(database: str | Path,
                      decisions: Sequence[Mapping[str, Any]], *,
                      decided_by: str, reason: str) -> dict[str, Any]:
    """Write resolutions and their audit rows in one transaction.

    Each decision needs ``queue_id`` and ``to_status``; ``rule`` and ``evidence``
    are optional. A row that is already resolved is left alone and reported, so
    re-running never overwrites an answer that is already there.
    """
    decided_by = str(decided_by or "").strip()
    reason = str(reason or "").strip()
    if not decided_by:
        raise ClassificationQueueError("a_resolution_needs_an_actor")
    if not reason:
        raise ClassificationQueueError("a_resolution_needs_a_reason")

    path = Path(database).expanduser()
    if not path.is_file():
        raise ClassificationQueueError(f"knowledge_database_missing: {path}")

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    now = _now()
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(RESOLUTION_SCHEMA)
        with con:
            for decision in decisions:
                queue_id = int(decision["queue_id"])
                to_status = str(decision["to_status"])
                if to_status not in RESOLVED_STATUSES:
                    raise ClassificationQueueError(f"unknown_status: {to_status}")
                row = con.execute(
                    "SELECT status FROM classification_queue WHERE queue_id = ?",
                    (queue_id,)).fetchone()
                if row is None:
                    skipped.append({"queue_id": queue_id, "why": "unknown_queue_id"})
                    continue
                from_status = str(row["status"])
                if from_status != STATUS_PENDING:
                    skipped.append({"queue_id": queue_id,
                                    "why": f"already_{from_status}"})
                    continue
                con.execute(
                    "UPDATE classification_queue SET status = ? WHERE queue_id = ?",
                    (to_status, queue_id))
                con.execute(
                    "INSERT INTO classification_resolutions"
                    "(queue_id,from_status,to_status,rule,decided_by,reason,"
                    " evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (queue_id, from_status, to_status,
                     str(decision.get("rule") or ""), decided_by,
                     str(decision.get("reason") or reason),
                     json.dumps(list(decision.get("evidence") or ()),
                                ensure_ascii=False, sort_keys=True),
                     now))
                applied.append({"queue_id": queue_id, "to_status": to_status})
    finally:
        con.close()
    return {"contract": CONTRACT, "applied": applied, "skipped": skipped,
            "decided_by": decided_by}


def summary(database: str | Path, *, canonical_root: str) -> dict[str, Any]:
    """What the queue costs, in the units a person actually spends."""
    candidates = load_candidates(database)
    canonical = canonical_index(database, canonical_root)
    proposals = machine_proposals(candidates, canonical=canonical,
                                  canonical_root=canonical_root)
    settled = {proposal.queue_id for proposal in proposals}
    groups = question_groups(candidates, settled)
    by_rule: dict[str, int] = {}
    for proposal in proposals:
        by_rule[proposal.rule] = by_rule.get(proposal.rule, 0) + 1
    with _read_only(database) as con:
        by_status = {str(row[0]): int(row[1]) for row in con.execute(
            "SELECT status, count(*) FROM classification_queue GROUP BY 1")}
        try:
            open_fine = int(con.execute(
                "SELECT count(*) FROM classification_resolutions WHERE rule = ?",
                (COVERS_COARSE_ONLY,)).fetchone()[0])
            resolutions = int(con.execute(
                "SELECT count(*) FROM classification_resolutions").fetchone()[0])
        except sqlite3.OperationalError:
            open_fine, resolutions = 0, 0
    return {
        "contract": CONTRACT,
        "rows_by_status": by_status,
        "pending_rows": len(candidates),
        "machine_resolvable": len(settled),
        "machine_rules": by_rule,
        "human_rows": len(candidates) - len(settled),
        "human_questions": len(groups),
        "questions_for_half_the_rows": coverage(groups, 0.5),
        "questions_for_80_percent": coverage(groups, 0.8),
        "by_kind": {kind: sum(1 for c in candidates if c.candidate_kind == kind)
                    for kind in sorted({c.candidate_kind for c in candidates})},
        "resolutions_recorded": resolutions,
        "fine_questions_still_open": open_fine,
    }
