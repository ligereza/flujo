"""Certify a query against a summary, and refine only where a certificate fails.

Two things live here and nowhere else.

**The completeness veto.** A rule proposes a verdict from a summary. Before a
negative is allowed out, this module checks that every authority the rule leaned
on actually covered every member of the group. If it did not, the negative
becomes UNKNOWN with the uncovered count named. No rule can forget this, because
no rule performs it.

**The refinement walk.** When a node returns UNKNOWN its children are opened and
the question is asked again. When a node returns a certificate, its members are
never opened. That is the whole operational lesson kept from BVH traversal: the
bound licenses the skip, and the skip is where the work disappears.

What this module refuses to do is present a narrowed predicate as the human
question. Every certificate says which of the two it answered, and a caller can
read ``answers`` before believing anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .contracts import (
    CERTIFIED_NO,
    CERTIFIED_YES,
    UNKNOWN,
    QueryContract,
    rule_for,
)
from .summary import (
    CERTIFIED_DISTINCT,
    CERTIFIED_EQUIVALENT,
    POLICY_CLAIM,
    Summary,
    UNRESOLVED,
)

CONTRACT = "mak-certified-answer-v1"


class Node(Protocol):
    """Anything with a conservative summary and possibly children."""

    summary: Summary
    children: Sequence["Node"]


@dataclass(frozen=True)
class Certificate:
    """A typed answer with its provenance, or a typed refusal."""

    verdict: str
    contract_id: str
    question: str
    predicate: str
    answers: str                 # "Q" when the predicate IS the question, else "P"
    claim_type: str
    epistemic_state: str         # ≡ certified for this contract, ≈ unresolved, ≠ split
    scope: str
    n_members: int
    reason: str
    authorities: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    coverage: Mapping[str, str] = field(default_factory=dict)
    vetoed: str = ""             # set when a proposed negative was refused

    @property
    def certified(self) -> bool:
        return self.verdict in (CERTIFIED_YES, CERTIFIED_NO)

    @property
    def is_about_the_world(self) -> bool:
        return self.answers == "Q" and self.claim_type != POLICY_CLAIM

    def as_dict(self) -> dict[str, Any]:
        out = {
            "contract": CONTRACT,
            "verdict": self.verdict,
            "query": self.contract_id,
            "answers": self.answers,
            "Q": self.question,
            "P": self.predicate,
            "claim_type": self.claim_type,
            "epistemic_state": self.epistemic_state,
            "scope": self.scope,
            "n_members": self.n_members,
            "reason": self.reason,
            "authorities": list(self.authorities),
            "provenance": list(self.provenance),
            "coverage": dict(self.coverage),
        }
        if self.vetoed:
            out["vetoed"] = self.vetoed
        return out

    def human_line(self) -> str:
        mark = {CERTIFIED_YES: "YES", CERTIFIED_NO: "NO ",
                UNKNOWN: "?  "}[self.verdict]
        about = "about the world" if self.is_about_the_world else (
            f"about {'our policy' if self.claim_type == POLICY_CLAIM else 'the index'}")
        return (f"[{mark}] {self.scope or '(root)'}  n={self.n_members}  "
                f"{self.epistemic_state}  {self.claim_type} ({about})\n"
                f"       {self.reason}")


def certify(contract: QueryContract, summary: Summary,
            arg: Mapping[str, Any] | None = None) -> Certificate:
    """Ask one contract of one summary. Never opens a member."""
    arg = dict(arg or {})
    rule = rule_for(contract.id)
    verdict, reason, needed = rule(summary, arg)

    coverage = {name: f"{summary.covered.get(name, 0)}/{summary.n_members}"
                for name in (needed or contract.authorities)
                if name in summary.covered or name in (needed or ())}
    vetoed = ""

    # ---- the completeness veto. Absence of evidence is evidence of absence only
    # ---- when the source is complete for the predicate.
    if verdict == CERTIFIED_NO:
        for name in needed:
            if not summary.complete_for(name):
                missing = summary.uncovered(name)
                vetoed = (
                    f"a negative was proposed but {name!r} covered "
                    f"{summary.covered.get(name, 0)} of {summary.n_members} members; "
                    f"{missing} uncovered member(s) could each carry what this "
                    "certificate claims is absent")
                verdict = UNKNOWN
                reason = vetoed
                break

    if verdict in (CERTIFIED_YES, CERTIFIED_NO):
        state = CERTIFIED_EQUIVALENT
    else:
        state = UNRESOLVED

    return Certificate(
        verdict=verdict,
        contract_id=contract.id,
        question=contract.question,
        predicate=contract.predicate,
        answers="Q" if contract.answers_question_directly else "P",
        claim_type=contract.claim_type,
        epistemic_state=state,
        scope=summary.scope,
        n_members=summary.n_members,
        reason=reason,
        authorities=tuple(needed),
        provenance=tuple(sorted(summary.provenance)),
        coverage=coverage,
        vetoed=vetoed,
    )


@dataclass
class Refinement:
    """What a walk cost and what it avoided."""

    contract_id: str
    certificates: list[Certificate] = field(default_factory=list)
    nodes_visited: int = 0
    members_pruned: int = 0      # covered by a certificate, never opened
    members_opened: int = 0      # a leaf whose certificate failed
    members_unresolved: int = 0  # opened and still UNKNOWN
    split_nodes: int = 0         # nodes whose children disagreed: a ≠

    @property
    def total_members(self) -> int:
        return self.members_pruned + self.members_opened

    @property
    def prune_fraction(self) -> float:
        total = self.total_members
        return (self.members_pruned / total) if total else 0.0

    @property
    def unknown_rate(self) -> float:
        total = self.total_members
        return (self.members_unresolved / total) if total else 0.0

    def certified(self) -> list[Certificate]:
        return [c for c in self.certificates if c.certified]

    def by_claim_type(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.certified():
            out[c.claim_type] = out.get(c.claim_type, 0) + 1
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "query": self.contract_id,
            "nodes_visited": self.nodes_visited,
            "members_total": self.total_members,
            "members_pruned": self.members_pruned,
            "members_opened": self.members_opened,
            "members_unresolved": self.members_unresolved,
            "prune_fraction": round(self.prune_fraction, 4),
            "unknown_rate": round(self.unknown_rate, 4),
            "split_nodes": self.split_nodes,
            "certificates": len(self.certified()),
            "by_claim_type": self.by_claim_type(),
            "world_claims": sum(1 for c in self.certified() if c.is_about_the_world),
        }


def refine(root: Node, contract: QueryContract,
           arg: Mapping[str, Any] | None = None, *,
           collect: bool = True, max_nodes: int = 2_000_000) -> Refinement:
    """Certify the root; where it cannot, open children and ask again.

    A node covered by a certificate contributes its whole member count to
    ``members_pruned`` and its children are never visited. That number -- corpus
    NOT opened because a certificate permitted it -- is the measurement this
    engine exists to produce.
    """
    out = Refinement(contract_id=contract.id)
    stack: list[Node] = [root]
    while stack:
        if out.nodes_visited >= max_nodes:
            break
        node = stack.pop()
        out.nodes_visited += 1
        cert = certify(contract, node.summary, arg)
        children = list(getattr(node, "children", ()) or ())

        if cert.certified:
            if collect:
                out.certificates.append(cert)
            out.members_pruned += node.summary.n_members
            continue

        if not children:
            # A leaf we were forced to open, and still cannot answer.
            out.members_opened += node.summary.n_members
            out.members_unresolved += node.summary.n_members
            if collect:
                out.certificates.append(cert)
            continue

        # Record a certified distinction when the children do not agree. This is
        # the only place a ≠ is produced, and it is produced from evidence.
        verdicts = {certify(contract, child.summary, arg).verdict for child in children}
        if len({v for v in verdicts if v != UNKNOWN}) > 1:
            out.split_nodes += 1
        stack.extend(children)
    return out


def answer(root: Node, contract: QueryContract,
           arg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The single call a caller makes: a typed answer plus what it cost."""
    run = refine(root, contract, arg)
    top = certify(contract, root.summary, arg)
    return {
        "contract": CONTRACT,
        "answer": top.as_dict(),
        "refinement": run.as_dict(),
        "note": ("The answer field is the certificate at the root. When it is "
                 "UNKNOWN the refinement field reports which parts of the corpus "
                 "were still settled underneath it."),
    }
