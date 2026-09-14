#!/usr/bin/env python3
"""Ask the corpus a question, and get a typed answer or an honest UNKNOWN.

Read-only. Nothing here writes to the index, the Instagram export, or the
repository.

    certified_query.py contracts
    certified_query.py ask q2_dimension --corpus ssd --scope LYON
    certified_query.py ask q1_commission --corpus ssd --client HARRY
    certified_query.py ask q4_work_or_record --corpus ig
    certified_query.py queue q3_track --corpus ssd
    certified_query.py audit --corpus ssd
    certified_query.py heterogeneity --corpus ssd --scope LYON

Every answer says which of two things it settled: the human question, or a
narrowed predicate the evidence can actually support. It never answers the first
by proving the second, and a negative is refused whenever the authority behind it
did not reach every member of the group.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.certified import (  # noqa: E402
    ContractError,
    build_ig_tree,
    build_ssd_tree,
    certify,
    load_contracts,
    refine,
)
from flujo.certified.metrics import (  # noqa: E402
    EngineReport,
    audit_soundness,
    provenance_completeness,
)
from flujo.certified.oracle import heterogeneity_signal, oracle_queue  # noqa: E402
from flujo.certified.tree import TreeError  # noqa: E402

SSD_QUERIES = ("q1_commission", "q2_dimension", "q3_track", "q6_application",
               "q10_delivered", "q11_authored", "q12_duplicate", "q13_record_kind",
               "q8_concept", "q9_rig", "q14_entity_role")
IG_QUERIES = ("q4_work_or_record", "q5_publishes", "q7_shown_when",
              "q13_record_kind", "q6_application")


def _tree(corpus: str, scope: str | None):
    if corpus == "ssd":
        return build_ssd_tree(scope=scope)
    if corpus == "ig":
        return build_ig_tree()
    raise ContractError(f"unknown_corpus: {corpus}")


def _arg(args) -> dict:
    out: dict = {}
    if args.client:
        out["client"] = args.client
    if args.track:
        out["track"] = args.track
    if args.role:
        out["role"] = args.role
    if args.window:
        lo, hi = args.window.split(",", 1)
        out["window"] = (float(lo), float(hi))
    return out


def _print_contracts(contracts) -> None:
    print(f"{'id':22s} {'claim':14s} {'answers':7s} {'grade':6s} question")
    for cid in sorted(contracts):
        c = contracts[cid]
        answers = ("Q" if c.answers_question_directly
                   else ("P" if c.decidable else "-"))
        print(f"{c.id:22s} {c.claim_type:14s} {answers:7s} "
              f"{c.verdict[:22]:24s} {c.question}")
    print()
    print("answers=Q  the certificate settles the human question.")
    print("answers=P  it settles a NARROWED predicate; read P before believing it.")
    print("answers=-  no predicate is known; this query only ever abstains.")


def main(argv: list[str] | None = None) -> int:
    # The shared flags live on a parent parser so they may be written either
    # before or after the subcommand. Putting them only on the top level is an
    # argparse trap: `ask q2 --corpus ssd` fails, which is exactly how anyone
    # would type it.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--corpus", choices=("ssd", "ig"), default="ssd")
    shared.add_argument("--scope", default=None,
                        help="restrict the SSD tree to one container root")
    shared.add_argument("--client", default=None)
    shared.add_argument("--track", default=None)
    shared.add_argument("--role", default=None)
    shared.add_argument("--window", default=None, metavar="LO,HI")
    shared.add_argument("--json", action="store_true")

    parser = argparse.ArgumentParser(
        description=__doc__, parents=[shared],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("contracts", parents=[shared],
                   help="the fourteen audited contracts")
    asking = sub.add_parser("ask", parents=[shared],
                            help="answer one query over one corpus")
    asking.add_argument("query")
    asking.add_argument("--show-certificates", type=int, default=0,
                        help="print the first N certificates in full")
    queueing = sub.add_parser("queue", parents=[shared], help="what is worth asking the operator")
    queueing.add_argument("query")
    queueing.add_argument("--limit", type=int, default=10)
    auditing = sub.add_parser("audit", parents=[shared], help="run every query and verify soundness")
    auditing.add_argument("--no-soundness", action="store_true",
                          help="skip the expensive member-by-member verification")
    sub.add_parser("provenance", parents=[shared], help="which authorities reach which members")
    sub.add_parser("heterogeneity", parents=[shared], help="the cheapest monitor: suspicion only")

    args = parser.parse_args(argv)
    contracts = load_contracts()

    try:
        if args.command == "contracts":
            if args.json:
                print(json.dumps([c.as_dict() for c in contracts.values()],
                                 indent=2, ensure_ascii=False))
            else:
                _print_contracts(contracts)
            return 0

        if args.command == "ask":
            if args.query not in contracts:
                raise ContractError(f"unknown_query: {args.query}")
            contract = contracts[args.query]
            tree = _tree(args.corpus, args.scope)
            arg = _arg(args)
            top = certify(contract, tree.summary, arg)
            run = refine(tree, contract, arg)
            if args.json:
                print(json.dumps({"answer": top.as_dict(),
                                  "refinement": run.as_dict()},
                                 indent=2, ensure_ascii=False))
                return 0
            print(f"Q  {contract.question}")
            print(f"P  {contract.predicate}")
            print()
            print(top.human_line())
            print()
            d = run.as_dict()
            print(f"corpus not opened because a certificate permitted it: "
                  f"{d['members_pruned']}/{d['members_total']} "
                  f"({100 * d['prune_fraction']:.1f}%)")
            print(f"opened and still unresolved: {d['members_unresolved']}  "
                  f"UNKNOWN rate {100 * d['unknown_rate']:.1f}%")
            print(f"nodes visited: {d['nodes_visited']}   certificates: "
                  f"{d['certificates']}   by claim type: {d['by_claim_type']}")
            print(f"certificates that are claims about the WORLD: {d['world_claims']}")
            if d["split_nodes"]:
                print(f"certified distinctions found (children disagreed): "
                      f"{d['split_nodes']}")
            for cert in run.certified()[: args.show_certificates]:
                print()
                print(cert.human_line())
            return 0

        if args.command == "queue":
            if args.query not in contracts:
                raise ContractError(f"unknown_query: {args.query}")
            tree = _tree(args.corpus, args.scope)
            requests = oracle_queue(tree, contracts[args.query], _arg(args),
                                    limit=args.limit)
            if args.json:
                print(json.dumps([r.as_dict() for r in requests], indent=2,
                                 ensure_ascii=False))
                return 0
            if not requests:
                print("nothing worth asking: every group is certified or too small")
                return 0
            print(f"{'settles':>8}  {'missing authority':28s} scope")
            for r in requests:
                print(f"{r.settles_members:>8}  {r.missing_authority:28s} {r.scope}")
            print()
            print("Asked shallowest-first: an answer high in the tree settles its "
                  "whole subtree. Never ask to empty a queue.")
            return 0

        if args.command == "audit":
            tree = _tree(args.corpus, args.scope)
            ids = SSD_QUERIES if args.corpus == "ssd" else IG_QUERIES
            report = EngineReport(corpus=args.corpus,
                                  members=tree.summary.n_members)
            defaults = {"q7_shown_when": {"window": (2025 * 12 + 1, 2025 * 12 + 12)},
                        "q12_duplicate": {"canonical_hashes": set()}}
            for cid in ids:
                arg = dict(defaults.get(cid, {}))
                arg.update(_arg(args))
                run = refine(tree, contracts[cid], arg)
                sound = (None if args.no_soundness
                         else audit_soundness(tree, contracts[cid], arg))
                report.add(contracts[cid], run, sound)
            if args.json:
                print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
                return 0
            print(f"{'query':22s} {'claim':14s} {'ans':4s} {'pruned':>7} "
                  f"{'opened':>7} {'prune%':>7} {'certs':>6} {'false':>6}")
            for row in report.rows:
                false = row["false_certified_claims"]
                print(f"{row['query']:22s} {row['claim_type']:14s} "
                      f"{row['answers']:4s} {row['members_pruned']:>7} "
                      f"{row['members_opened']:>7} "
                      f"{100 * row['prune_fraction']:>6.1f}% "
                      f"{row['certificates']:>6} "
                      f"{('-' if false is None else str(false)):>6}")
            t = report.totals()
            print()
            print(f"FALSE CERTIFIED CLAIMS: {t['FALSE_CERTIFIED_CLAIMS']}  "
                  f"(target 0)")
            print(f"queries with a predicate at all: "
                  f"{t['queries_with_a_predicate']}/{t['queries_run']}")
            print(f"queries that certified something: "
                  f"{t['queries_that_certified_something']}/{t['queries_run']}")
            print(f"certificates about the WORLD: {t['world_claim_certificates']}")
            print(f"by claim type: {t['by_claim_type']}")
            if t["queries_that_certified_nothing"]:
                print(f"certified nothing: {t['queries_that_certified_nothing']}")
            return 0

        if args.command == "provenance":
            tree = _tree(args.corpus, args.scope)
            print(json.dumps(provenance_completeness(tree), indent=2,
                             ensure_ascii=False))
            return 0

        tree = _tree(args.corpus, args.scope)
        print(json.dumps(heterogeneity_signal(tree), indent=2, ensure_ascii=False))
        return 0

    except (ContractError, TreeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
