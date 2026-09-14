#!/usr/bin/env python3
"""Read the review queue and record one human decision at a time.

Measured before this tool existed: 34 project records waiting in
``review_required``, ``project_transitions`` empty, and the one function that can
move a project's state called exactly once in the repository -- inside its own
test. Four producers wrote into a queue with no door.

Default mode is read-only. ``decide`` is the only subcommand that writes, and it
refuses without a reason and an actor, because a decision nobody signed is not
better than no decision.

Nothing cascades on its own. A rejection can be inherited by the contents of the
rejected container, but only when ``--cascade`` names that explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.review_queue import (  # noqa: E402
    ACCEPTING_STATES,
    PASS_PRUNE,
    PASS_RECOGNIZE,
    REJECTING_STATES,
    ReviewQueueError,
    decide,
    inherited_proposals,
    load_queue,
    resolve_title,
    summary,
)
from flujo.substrate import Absent, Many, resolve  # noqa: E402
from flujo.substrate.epistemics import MISSING_EVIDENCE  # noqa: E402

DEFAULT_DB = ROOT / "data" / "mak_knowledge.db"


def _gb(value: int) -> str:
    return f"{value / 1e9:7.2f} GB"


def _resolve_target(items, needle: str):
    """Every queue item whose title or project_id equals ``needle``.

    MEASURED defect this replaces: ``project_records.title`` has no UNIQUE
    constraint (plain ``title TEXT NOT NULL``) and is written by three
    producers, so the old ``for item in items: if needle in (...): return
    item`` returned whichever matching row happened to be first -- silently.
    Collecting every match and classifying the count (0 / 1 / N) is the fix;
    the caller decides what to do with a 0 or an N, it is never picked here.
    """
    matches = [item for item in items if needle in (item.title, item.project_id)]
    return resolve(matches, witness=f"target '{needle}' matched exactly one queue item",
                    cause=MISSING_EVIDENCE)


def _print_candidates(needle: str, candidates) -> None:
    """The full candidate list an ambiguous target matched, and the way out.

    Required by the audit: an ambiguous target must never raise a raw
    traceback at the operator. It must see every project_id and state that
    matched, and be told the unambiguous escape hatch (project_id is the
    table's PRIMARY KEY, so it can never itself be ambiguous).
    """
    print(f"ambiguous target '{needle}': {len(candidates)} candidates matched, "
          "not one", file=sys.stderr)
    for candidate in candidates:
        print(f"  project_id={candidate.project_id}  state={candidate.state:<14}"
              f"title={candidate.title}", file=sys.stderr)
    print("re-run with the project_id shown above instead of the title",
          file=sys.stderr)


def _require_target(items, needle: str):
    """Resolve ``needle`` the way every write path here must.

    Returns the ``QueueItem`` for a Unique match. Returns ``None`` for Many,
    after already printing the full candidate list (requirement 3 of the
    audit: no traceback, a non-zero exit, nothing written). Raises
    ``ReviewQueueError`` for Absent, unchanged from the previous behaviour.
    """
    resolution = _resolve_target(items, needle)
    if isinstance(resolution, Many):
        _print_candidates(needle, resolution.candidates)
        return None
    if isinstance(resolution, Absent):
        raise ReviewQueueError(f"not_pending: {needle}")
    return resolution.value


def _print_table(items, review_pass: str) -> None:
    if not items:
        print("the queue is empty")
        return
    header = "reject" if review_pass == PASS_PRUNE else "material"
    print(f"{'#':>3}  {header:>8}  {'subtree':>10}  {'assets':>7}  role                    title")
    for index, item in enumerate(items, start=1):
        left = (str(item.rejection_leverage) if review_pass == PASS_PRUNE
                else f"{item.subtree_bytes / 1e9:.0f}G")
        print(f"{index:>3}  {left:>8}  {_gb(item.subtree_bytes)}  "
              f"{item.asset_count:>7}  {item.role:<22}  {item.title}")


def _show(item) -> None:
    print(f"title        {item.title}")
    print(f"project_id   {item.project_id}")
    print(f"state        {item.state}")
    print(f"role         {item.role}")
    print(f"scope        {item.scope or '-'}")
    print(f"container    {item.parent_title or '-'}")
    print(f"assets       {item.asset_count}")
    print(f"bytes        {_gb(item.bytes_total)} directly assigned")
    print(f"             {_gb(item.subtree_bytes)} including pending contents")
    if item.media_mix:
        mix = ", ".join(f"{k}={v}" for k, v in sorted(item.media_mix.items()))
        print(f"media        {mix}")
    if item.pending_descendants:
        print(f"contains     {len(item.pending_descendants)} pending records:")
        for title in item.pending_descendants:
            print(f"               {title}")
        print("             a rejection here can be inherited by all of them")
        print("             an acceptance cannot: a work holds working material too")
    print(f"unknowns     {', '.join(item.unknowns) or '-'}")
    print("evidence")
    for row in item.evidence:
        print("               " + json.dumps(row, ensure_ascii=False, sort_keys=True))
    print(f"decisions    {', '.join(sorted(item.as_dict()['decisions_available']))}")
    accepting = sorted(ACCEPTING_STATES)
    print(f"             {', '.join(accepting)} require --evidence")
    print(f"             {', '.join(sorted(REJECTING_STATES))} may use --cascade")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="what is waiting, ordered for one pass")
    listing.add_argument("--pass", dest="review_pass", default=PASS_PRUNE,
                         choices=(PASS_PRUNE, PASS_RECOGNIZE))
    listing.add_argument("--scope", default=None)
    listing.add_argument("--limit", type=int, default=20)
    listing.add_argument("--json", action="store_true")

    sub.add_parser("summary", help="what the queue costs in answers")

    showing = sub.add_parser("show", help="every measured fact about one record")
    showing.add_argument("target", help="title or project_id")
    showing.add_argument("--json", action="store_true")

    deciding = sub.add_parser("decide", help="record one human decision (writes)")
    deciding.add_argument("target", help="title or project_id")
    deciding.add_argument("--to", required=True, help="destination state")
    deciding.add_argument("--reason", required=True)
    deciding.add_argument("--actor", required=True, help="who is signing this")
    deciding.add_argument("--evidence", action="append", default=[],
                          help="a checkable reason; required to accept")
    deciding.add_argument("--cascade", action="store_true",
                          help="also apply a rejection to the pending contents")
    deciding.add_argument("--dry-run", action="store_true",
                          help="print what would be written and write nothing")

    args = parser.parse_args(argv)

    try:
        if args.command == "summary":
            print(json.dumps(summary(load_queue(args.db)), indent=2, ensure_ascii=False))
            return 0

        if args.command == "list":
            items = load_queue(args.db, scope=args.scope, review_pass=args.review_pass)
            shown = items[: args.limit] if args.limit > 0 else items
            if args.json:
                print(json.dumps([item.as_dict() for item in shown],
                                 indent=2, ensure_ascii=False))
            else:
                _print_table(shown, args.review_pass)
                if len(shown) < len(items):
                    print(f"... {len(items) - len(shown)} more; --limit 0 for all")
            return 0

        if args.command == "show":
            item = _require_target(load_queue(args.db), args.target)
            if item is None:
                return 1
            if args.json:
                print(json.dumps(item.as_dict(), indent=2, ensure_ascii=False))
            else:
                _show(item)
            return 0

        items = load_queue(args.db)
        item = _require_target(items, args.target)
        if item is None:
            return 1
        evidence = [{"kind": "human_attestation", "detail": text}
                    for text in args.evidence]
        cascade = inherited_proposals(item, args.to) if args.cascade else []
        if args.cascade and not cascade:
            print(f"nothing to cascade: {args.to} does not propagate downward",
                  file=sys.stderr)

        # Resolve every cascade title up front so a dry-run can show the
        # ambiguity too (requirement 5): the old dry-run only echoed what the
        # broken first-match resolver had already picked, so it could never
        # reveal this class of problem.
        cascade_resolutions = {title: resolve_title(items, title) for title in cascade}
        cascade_preview = []
        for title in cascade:
            resolution = cascade_resolutions[title]
            if isinstance(resolution, Many):
                cascade_preview.append({
                    "title": title, "ambiguous": True,
                    "candidates": [{"project_id": c.project_id, "state": c.state}
                                   for c in resolution.candidates],
                })
            elif isinstance(resolution, Absent):
                cascade_preview.append({"title": title, "error": "not_pending"})
            else:
                cascade_preview.append({"title": title,
                                        "project_id": resolution.value.project_id})

        if args.dry_run:
            print(json.dumps({
                "would_decide": item.title, "project_id": item.project_id,
                "from_state": item.state, "to_state": args.to,
                "reason": args.reason, "actor": args.actor,
                "evidence": evidence, "cascade": cascade_preview,
            }, indent=2, ensure_ascii=False))
            return 0

        # Requirement 4: if ANY cascade title is ambiguous, refuse the WHOLE
        # cascade before writing anything -- a partial cascade is worse than
        # none, because the operator believes the subtree was handled.
        # ``decide()`` enforces this too (it re-resolves against its own
        # read), so this is the friendly surface and that is the guarantee.
        ambiguous_titles = [title for title, r in cascade_resolutions.items()
                            if isinstance(r, Many)]
        if ambiguous_titles:
            for title in ambiguous_titles:
                _print_candidates(title, cascade_resolutions[title].candidates)
            print("cascade refused: nothing was written for this decision or its "
                  "cascade", file=sys.stderr)
            return 1

        result = decide(args.db, item.project_id, args.to, reason=args.reason,
                        actor=args.actor, evidence=evidence, cascade_titles=cascade)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if not result["refused"] else 1
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
