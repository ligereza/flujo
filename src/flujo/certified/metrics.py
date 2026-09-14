"""Measure the engine by the things that would show it lying.

The brief forbids judging this by label counts, corpus percentage classified, or
raw speedup. What remains is harder and more useful:

- certified coverage, broken out BY CLAIM TYPE, because a POLICY_CLAIM is
  complete by construction and a corpus of them proves nothing;
- the UNKNOWN rate, which is a result and not a failure;
- how much corpus was never opened because a certificate permitted it;
- provenance completeness;
- and the one number with a target of exactly zero: FALSE CERTIFIED CLAIMS.

The soundness audit is the centre of this module. It takes every certificate the
engine issued over an internal node and then does the expensive thing the engine
refused to do -- opens every descendant leaf and checks the certificate against
each one. A conservative summary must be monotone: if a group certifies NO, no
member of it may certify YES. Any violation means the summary is not an
over-approximation, which is the only bug in this design that matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .certify import Certificate, certify
from .contracts import CERTIFIED_NO, CERTIFIED_YES, UNKNOWN, QueryContract
from .summary import POLICY_CLAIM, WORLD_CLAIM
from .tree import TreeNode

CONTRACT = "mak-certified-metrics-v1"


@dataclass
class Violation:
    """A certificate that a member contradicts. The target count is zero."""

    contract_id: str
    node_scope: str
    node_verdict: str
    member_scope: str
    member_verdict: str
    n_members: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.contract_id, "node": self.node_scope,
            "node_said": self.node_verdict, "member": self.member_scope,
            "member_said": self.member_verdict, "group_size": self.n_members,
        }


@dataclass
class SoundnessReport:
    contract_id: str
    certificates_checked: int = 0
    members_verified: int = 0
    violations: list[Violation] = field(default_factory=list)
    leaves_weaker_than_group: int = 0

    @property
    def sound(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.contract_id,
            "certificates_checked": self.certificates_checked,
            "members_verified": self.members_verified,
            "false_certified_claims": len(self.violations),
            "sound": self.sound,
            "leaves_weaker_than_group": self.leaves_weaker_than_group,
            "violations": [v.as_dict() for v in self.violations[:20]],
        }


def audit_soundness(root: TreeNode, contract: QueryContract,
                    arg: Mapping[str, Any] | None = None) -> SoundnessReport:
    """Open everything a certificate let us skip, and check the certificate held.

    This is deliberately the expensive path. It exists so that the cheap path can
    be trusted, and it is the only measurement whose acceptable value is zero.
    """
    report = SoundnessReport(contract_id=contract.id)
    stack: list[TreeNode] = [root]
    while stack:
        node = stack.pop()
        cert = certify(contract, node.summary, arg)
        if not cert.certified:
            stack.extend(node.children)
            continue
        report.certificates_checked += 1
        opposite = CERTIFIED_YES if cert.verdict == CERTIFIED_NO else CERTIFIED_NO
        for leaf in node.descendants():
            if not leaf.is_leaf:
                continue
            report.members_verified += 1
            leaf_cert = certify(contract, leaf.summary, arg)
            if leaf_cert.verdict == opposite:
                report.violations.append(Violation(
                    contract_id=contract.id, node_scope=node.scope,
                    node_verdict=cert.verdict, member_scope=leaf.scope,
                    member_verdict=leaf_cert.verdict,
                    n_members=node.summary.n_members))
            elif leaf_cert.verdict == UNKNOWN:
                report.leaves_weaker_than_group += 1
    return report


@dataclass
class EngineReport:
    """What the engine achieved across the whole contract set, by claim type."""

    corpus: str
    members: int
    queries_run: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)

    def add(self, contract: QueryContract, refinement, soundness: SoundnessReport | None):
        d = refinement.as_dict()
        self.queries_run += 1
        self.rows.append({
            "query": contract.id,
            "Q": contract.question,
            "claim_type": contract.claim_type,
            "answers": "Q" if contract.answers_question_directly else "P",
            "decidable": contract.decidable,
            "members_pruned": d["members_pruned"],
            "members_opened": d["members_opened"],
            "prune_fraction": d["prune_fraction"],
            "unknown_rate": d["unknown_rate"],
            "certificates": d["certificates"],
            "nodes_visited": d["nodes_visited"],
            "world_claims": d["world_claims"],
            "false_certified_claims": (len(soundness.violations)
                                       if soundness else None),
            "sound": soundness.sound if soundness else None,
        })

    def totals(self) -> dict[str, Any]:
        by_claim: dict[str, dict[str, int]] = {}
        for row in self.rows:
            slot = by_claim.setdefault(row["claim_type"],
                                       {"queries": 0, "pruned": 0, "certificates": 0})
            slot["queries"] += 1
            slot["pruned"] += row["members_pruned"]
            slot["certificates"] += row["certificates"]
        decidable = [r for r in self.rows if r["decidable"]]
        certifying = [r for r in self.rows if r["certificates"] > 0]
        false_claims = sum(r["false_certified_claims"] or 0 for r in self.rows)
        return {
            "contract": CONTRACT,
            "corpus": self.corpus,
            "members": self.members,
            "queries_run": self.queries_run,
            "queries_with_a_predicate": len(decidable),
            "queries_that_certified_something": len(certifying),
            "queries_that_certified_nothing": [
                r["query"] for r in self.rows if r["certificates"] == 0],
            "FALSE_CERTIFIED_CLAIMS": false_claims,
            "soundness_audited": sum(1 for r in self.rows if r["sound"] is not None),
            "by_claim_type": by_claim,
            "world_claim_certificates": sum(r["world_claims"] for r in self.rows),
            "mean_prune_fraction_over_certifying_queries": (
                round(sum(r["prune_fraction"] for r in certifying) / len(certifying), 4)
                if certifying else 0.0),
        }

    def as_dict(self) -> dict[str, Any]:
        return {"totals": self.totals(), "rows": self.rows}


def provenance_completeness(root: TreeNode) -> dict[str, Any]:
    """Does every member carry a recorded source, and which authorities reach it?

    A certificate without provenance is unauditable, so this is measured over the
    whole tree rather than sampled.
    """
    leaves = [n for n in root.descendants() if n.is_leaf]
    if not leaves:
        return {"contract": CONTRACT, "members": 0}
    without = [n.scope for n in leaves if not n.summary.provenance]
    authorities: dict[str, int] = {}
    for leaf in leaves:
        for name in leaf.summary.covered:
            authorities[name] = authorities.get(name, 0) + 1
    total = len(leaves)
    return {
        "contract": CONTRACT,
        "members": total,
        "members_without_provenance": len(without),
        "provenance_complete": not without,
        "examples_missing": without[:5],
        "authority_coverage": {name: {"members": count,
                                      "fraction": round(count / total, 4)}
                               for name, count in sorted(authorities.items())},
        "complete_authorities": sorted(name for name, count in authorities.items()
                                       if count == total),
        "partial_authorities": sorted(name for name, count in authorities.items()
                                      if count < total),
    }
