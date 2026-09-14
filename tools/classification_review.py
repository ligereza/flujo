#!/usr/bin/env python3
"""Read the classification queue and answer it in the unit it is asked in.

Measured before this tool existed: 8273 rows, every one `pending`, four distinct
question templates, and no code anywhere that writes `status`. The same disease
as the project queue -- one producer, zero consumers -- in a second place.

But 8273 is a number of rows, not of questions. Nearly half carry a check a
machine can repeat, and the rest fold into the directory the coarse half of each
question is really about: 3 groups cover half the remaining rows.

Default mode is read-only. `apply-rules` and `classify` are the only writers, and
both refuse without an actor and a reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.classification_queue import (  # noqa: E402
    COVERAGE_CHOICES,
    COVERS_BOTH,
    COVERS_COARSE_ONLY,
    QUESTION_PARTS,
    RULE_CANONICAL_COPY,
    RULE_VIRTUALENV,
    STATUS_ABSTAINED,
    STATUS_CLASSIFIED,
    ClassificationQueueError,
    apply_resolutions,
    canonical_index,
    coverage,
    load_candidates,
    machine_proposals,
    question_groups,
    summary,
)

DEFAULT_DB = ROOT / "data" / "mak_knowledge.db"
# `/home/mak` is the physical MAK checkout.  `/home/mak/flujo` remains a
# compatibility adapter, but using it as the default canonical path makes
# copy proposals report the alias instead of the box's real root.
DEFAULT_CANONICAL = "/home/mak"


def _load(db: Path, canonical_root: str):
    candidates = load_candidates(db)
    canonical = canonical_index(db, canonical_root)
    proposals = machine_proposals(candidates, canonical=canonical,
                                  canonical_root=canonical_root)
    groups = question_groups(candidates, {p.queue_id for p in proposals})
    return candidates, proposals, groups


def _print_groups(groups, limit: int) -> None:
    shown = groups[:limit] if limit > 0 else groups
    print(f"{'rows':>6} {'classes':>7}  {'kind':<10} {'coarse question':<26} directory")
    for group in shown:
        asks = f"{group.coarse_part}/{group.coarse_unit}"
        print(f"{group.rows:>6} {group.content_classes:>7}  "
              f"{group.candidate_kind:<10} {asks:<26} {group.directory}")
    if len(shown) < len(groups):
        print(f"... {len(groups) - len(shown)} more groups; --limit 0 for all")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--canonical-root", default=DEFAULT_CANONICAL,
                        help="the tree whose copy elsewhere is a copy, not a question")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="what the queue costs in answers")

    listing = sub.add_parser("list", help="the questions a person is actually asked")
    listing.add_argument("--limit", type=int, default=15)
    listing.add_argument("--kind", default=None, choices=sorted(QUESTION_PARTS))
    listing.add_argument("--json", action="store_true")

    showing = sub.add_parser("show", help="one group in full")
    showing.add_argument("directory")
    showing.add_argument("--kind", required=True, choices=sorted(QUESTION_PARTS))

    proposing = sub.add_parser("propose", help="what a check can settle (read-only)")
    proposing.add_argument("--rule", default=None,
                           choices=(RULE_VIRTUALENV, RULE_CANONICAL_COPY))
    proposing.add_argument("--limit", type=int, default=10)

    applying = sub.add_parser("apply-rules",
                              help="sign the machine rules in one act (writes)")
    applying.add_argument("--actor", required=True)
    applying.add_argument("--reason", required=True)
    applying.add_argument("--rule", default=None,
                          choices=(RULE_VIRTUALENV, RULE_CANONICAL_COPY))
    applying.add_argument("--dry-run", action="store_true")

    classifying = sub.add_parser("classify", help="answer one group (writes)")
    classifying.add_argument("directory")
    classifying.add_argument("--kind", required=True, choices=sorted(QUESTION_PARTS))
    classifying.add_argument("--answer", required=True, help="the coarse answer")
    classifying.add_argument("--covers", required=True, choices=COVERAGE_CHOICES,
                             help="coarse_only leaves the per-file half recorded as open")
    classifying.add_argument("--actor", required=True)
    classifying.add_argument("--to", default=STATUS_CLASSIFIED,
                             choices=(STATUS_CLASSIFIED, STATUS_ABSTAINED))
    classifying.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    try:
        if args.command == "summary":
            print(json.dumps(summary(args.db, canonical_root=args.canonical_root),
                             indent=2, ensure_ascii=False))
            return 0

        candidates, proposals, groups = _load(args.db, args.canonical_root)

        if args.command == "list":
            if args.kind:
                groups = [g for g in groups if g.candidate_kind == args.kind]
            if args.json:
                print(json.dumps([g.as_dict() for g in groups[:args.limit or None]],
                                 indent=2, ensure_ascii=False))
            else:
                _print_groups(groups, args.limit)
                print(f"\n{len(groups)} groups | "
                      f"{coverage(groups, 0.5)} answers reach half the rows | "
                      f"{coverage(groups, 0.8)} reach 80%")
            return 0

        if args.command == "show":
            match = [g for g in groups if g.directory == args.directory
                     and g.candidate_kind == args.kind]
            if not match:
                raise ClassificationQueueError(
                    f"no_pending_group: {args.kind} in {args.directory}")
            group = match[0]
            print(json.dumps(group.as_dict(), indent=2, ensure_ascii=False))
            print(f"queue_ids: {len(group.queue_ids)} rows, first 12: "
                  f"{list(group.queue_ids[:12])}")
            return 0

        if args.command == "propose":
            chosen = [p for p in proposals if not args.rule or p.rule == args.rule]
            by_rule: dict[str, int] = {}
            for proposal in chosen:
                by_rule[proposal.rule] = by_rule.get(proposal.rule, 0) + 1
            print(json.dumps({"proposals": len(chosen), "by_rule": by_rule},
                             indent=2, ensure_ascii=False))
            for proposal in chosen[:args.limit]:
                print(f"  {proposal.rule:<28} {proposal.path}")
                for item in proposal.evidence:
                    print(f"      {item['kind']}: {item['detail']}")
            return 0

        if args.command == "apply-rules":
            chosen = [p for p in proposals if not args.rule or p.rule == args.rule]
            decisions = [{"queue_id": p.queue_id, "to_status": p.to_status,
                          "rule": p.rule, "evidence": list(p.evidence),
                          "reason": args.reason} for p in chosen]
            if args.dry_run:
                by_rule: dict[str, int] = {}
                for proposal in chosen:
                    by_rule[proposal.rule] = by_rule.get(proposal.rule, 0) + 1
                print(json.dumps({"would_apply": len(decisions), "by_rule": by_rule,
                                  "actor": args.actor, "reason": args.reason},
                                 indent=2, ensure_ascii=False))
                return 0
            result = apply_resolutions(args.db, decisions, decided_by=args.actor,
                                       reason=args.reason)
            print(json.dumps({"applied": len(result["applied"]),
                              "skipped": len(result["skipped"]),
                              "decided_by": result["decided_by"]},
                             indent=2, ensure_ascii=False))
            return 0

        match = [g for g in groups if g.directory == args.directory
                 and g.candidate_kind == args.kind]
        if not match:
            raise ClassificationQueueError(
                f"no_pending_group: {args.kind} in {args.directory}")
        group = match[0]
        evidence = [{"kind": "human_attestation", "detail": args.answer},
                    {"kind": "scope_note",
                     "detail": f"answers the {group.coarse_part} half, asked per "
                               f"{group.coarse_unit}"}]
        if args.covers == COVERS_COARSE_ONLY:
            evidence.append({"kind": "open_question",
                             "detail": f"the {group.fine_part} half stays open, "
                                       f"asked per {group.fine_unit}"})
        decisions = [{"queue_id": qid, "to_status": args.to,
                      "rule": args.covers, "evidence": evidence,
                      "reason": args.answer} for qid in group.queue_ids]
        if args.dry_run:
            print(json.dumps({"would_answer": group.as_dict(),
                              "rows": len(decisions), "covers": args.covers,
                              "actor": args.actor}, indent=2, ensure_ascii=False))
            return 0
        result = apply_resolutions(args.db, decisions, decided_by=args.actor,
                                   reason=args.answer)
        print(json.dumps({"applied": len(result["applied"]),
                          "skipped": len(result["skipped"]),
                          "covers": args.covers,
                          "still_open": (group.fine_part
                                         if args.covers == COVERS_COARSE_ONLY else None)},
                         indent=2, ensure_ascii=False))
        return 0
    except ClassificationQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
