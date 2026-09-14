"""When to spend the operator, and how a provisional fold stays reopenable.

Two rules govern asking a person anything. Ask only when no available authority
can resolve the query, and only when the distinction has actual future-query
value -- measured as the number of members a single answer would settle across
how many contracts. Never ask in order to empty a queue: the queue is not the
work, and the measured cost curve on this corpus was 791 members settled per
answer for the first three questions against 1.6 for the last five hundred.

An answer comes back as typed evidence with an authority, a scope and a
provenance. It is never stored as a naked field, because a naked field cannot be
audited, cannot be scoped, and cannot be superseded.

The rest of this module is the machinery that keeps an unresolved fold honest.
``≈`` is not ``≡``, may never be serialised as it, and may never license a
destructive or outward-facing action on its own. And a fold must carry more than
a way back: it must carry a way for the system to come to SUSPECT it should go
back. A monitor whose features are the very features the fold lacks can never
fire, which is a circularity that fails silently, so it is refused here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .certify import Certificate, certify
from .contracts import QueryContract
from .summary import (
    CERTIFIED_DISTINCT,
    CERTIFIED_EQUIVALENT,
    UNRESOLVED,
)
from .tree import TreeNode

CONTRACT = "mak-oracle-and-residue-v1"

# The five channels by which a fold may come to be suspected. The first four cost
# nothing until they fire; the fifth costs coverage always, and is the backstop
# for a fold that is genuinely invisible to the other four.
MONITOR_HETEROGENEITY = "internal_heterogeneity"
MONITOR_QUERY_PRESSURE = "query_pressure"
MONITOR_NEW_AUTHORITY = "new_authority_arrival"
MONITOR_OPERATOR_DISAGREEMENT = "operator_disagreement"
MONITOR_ADVERSARIAL_BUDGET = "adversarial_sampling_budget"
MONITORS = (MONITOR_HETEROGENEITY, MONITOR_QUERY_PRESSURE, MONITOR_NEW_AUTHORITY,
            MONITOR_OPERATOR_DISAGREEMENT, MONITOR_ADVERSARIAL_BUDGET)

# Actions a provisional fold may never license by itself.
IRREVERSIBLE_ACTIONS = frozenset({"delete", "overwrite", "publish", "send",
                                  "deduplicate", "archive_destructive"})


class OracleError(ValueError):
    """The oracle was asked to do something it must refuse."""


# --------------------------------------------------------------- asking a human

@dataclass(frozen=True)
class OracleRequest:
    """One question worth a person's attention, with the reason it is worth it."""

    contract_id: str
    question: str
    scope: str
    n_members: int
    why_unresolved: str
    missing_authority: str
    settles_members: int
    settles_contracts: tuple[str, ...] = ()

    @property
    def value(self) -> int:
        """Members settled, weighted by how many contracts the answer unlocks."""
        return self.settles_members * max(len(self.settles_contracts), 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.contract_id, "Q": self.question, "scope": self.scope,
            "n_members": self.n_members, "why_unresolved": self.why_unresolved,
            "missing_authority": self.missing_authority,
            "settles_members": self.settles_members,
            "also_unlocks": list(self.settles_contracts), "value": self.value,
        }


def oracle_queue(root: TreeNode, contract: QueryContract,
                 arg: Mapping[str, Any] | None = None, *,
                 min_members: int = 2, limit: int = 20) -> list[OracleRequest]:
    """The shallowest unresolved nodes, ranked by what one answer would settle.

    Shallowest on purpose: an answer at a high node settles its whole subtree, and
    the measured shape of this corpus is that a handful of high answers cover most
    members. Nodes below ``min_members`` are omitted rather than asked, because a
    question that settles one item has to justify itself some other way.
    """
    requests: list[OracleRequest] = []
    frontier: list[TreeNode] = [root]
    while frontier:
        node = frontier.pop(0)
        cert = certify(contract, node.summary, arg)
        if cert.certified:
            continue
        if node.summary.n_members >= min_members:
            requests.append(OracleRequest(
                contract_id=contract.id, question=contract.question,
                scope=node.scope, n_members=node.summary.n_members,
                why_unresolved=cert.reason,
                missing_authority=_missing_authority(contract, node),
                settles_members=node.summary.n_members,
                settles_contracts=(contract.id,)))
            continue          # do not also ask about its children
        frontier.extend(node.children)
    requests.sort(key=lambda r: (-r.value, r.scope))
    return requests[:limit]


def _missing_authority(contract: QueryContract, node: TreeNode) -> str:
    """Which declared authority failed to reach this group.

    Naming it is what makes the fold discoverable later: a registry keyed on this
    string can fire every waiting fold the moment a tool producing it arrives.
    """
    gaps = [name for name in contract.authorities
            if not node.summary.complete_for(name)]
    if gaps:
        return gaps[0]
    return contract.authorities[0] if contract.authorities else "none_declared"


@dataclass(frozen=True)
class OperatorEvidence:
    """A human answer, typed. Never a naked field."""

    authority: str
    scope: str
    contract_id: str
    claim: str
    actor: str
    reason: str
    recorded_at: str
    supersedes: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = {
            "contract": CONTRACT, "authority": self.authority, "scope": self.scope,
            "query": self.contract_id, "claim": self.claim, "actor": self.actor,
            "reason": self.reason, "recorded_at": self.recorded_at,
        }
        if self.supersedes:
            out["supersedes"] = self.supersedes
        return out


def record_answer(request: OracleRequest, claim: str, *, actor: str, reason: str,
                  recorded_at: str, supersedes: str = "") -> OperatorEvidence:
    """Turn an answer into evidence. Refuses an unsigned or unscoped one."""
    if not str(actor).strip():
        raise OracleError("an_answer_needs_an_actor")
    if not str(reason).strip():
        raise OracleError("an_answer_needs_a_reason")
    if not str(claim).strip():
        raise OracleError("an_answer_needs_a_claim")
    if not request.scope:
        raise OracleError("an_answer_needs_a_scope")
    return OperatorEvidence(
        authority="operator_attestation", scope=request.scope,
        contract_id=request.contract_id, claim=str(claim), actor=str(actor),
        reason=str(reason), recorded_at=str(recorded_at), supersedes=supersedes)


# ------------------------------------------------------- provisional folds

@dataclass(frozen=True)
class Monitor:
    """A channel by which a fold may come to be suspected."""

    channel: str
    features: tuple[str, ...]
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"channel": self.channel, "features": list(self.features),
                "note": self.note}


@dataclass(frozen=True)
class ProvisionalFold:
    """A group treated as one thing WITHOUT a certificate, kept reopenable."""

    scope: str
    contract_id: str
    epistemic_state: str
    n_members: int
    residue: tuple[str, ...]
    missing_authority: str
    reopen_when: tuple[str, ...]
    monitors: tuple[Monitor, ...]
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT, "scope": self.scope, "query": self.contract_id,
            "epistemic_state": self.epistemic_state, "n_members": self.n_members,
            "residue": list(self.residue),
            "missing_authority": self.missing_authority,
            "reopen_when": list(self.reopen_when),
            "monitors": [m.as_dict() for m in self.monitors],
            "reason": self.reason,
            "may_license_irreversible_action": False,
        }


def validate_fold(fold: ProvisionalFold) -> None:
    """Refuse a fold that cannot be reopened, or cannot be suspected.

    Four refusals, each one a defect this project actually met:

    1. ``≈`` presented as ``≡`` -- the same silence in a database, the opposite
       in epistemology.
    2. no residue -- reversible in principle and unrecoverable in fact.
    3. no named missing authority -- nothing to key a future arrival on.
    4. a monitor built on the missing feature -- circular, and it fails silently.
    """
    if fold.epistemic_state == CERTIFIED_EQUIVALENT:
        raise OracleError(
            "a_provisional_fold_may_not_claim_certified_equivalence: use ≈. A "
            "fold without a certificate is a confession, not a conclusion.")
    if fold.epistemic_state not in (UNRESOLVED, CERTIFIED_DISTINCT):
        raise OracleError(f"unknown_epistemic_state: {fold.epistemic_state}")
    if not fold.residue:
        raise OracleError(
            "a_provisional_fold_needs_residue_sufficient_to_recompute_the_split")
    if not fold.missing_authority or fold.missing_authority == "none_declared":
        raise OracleError(
            "a_provisional_fold_must_name_the_authority_it_lacks: without the "
            "name, no arriving tool can wake it")
    if not fold.monitors:
        raise OracleError(
            "a_provisional_fold_needs_at_least_one_monitor: residue makes it "
            "reversible, a monitor makes it DISCOVERABLY reversible")
    for monitor in fold.monitors:
        if monitor.channel not in MONITORS:
            raise OracleError(f"unknown_monitor_channel: {monitor.channel}")
        if fold.missing_authority in monitor.features:
            raise OracleError(
                f"circular_monitor: {monitor.channel} watches "
                f"{fold.missing_authority!r}, which is the very evidence this "
                "fold lacks, so it can never fire")


def assert_may_act(state: str, action: str) -> None:
    """No destructive or outward-facing action may rest on ``≈`` alone.

    Residue restores knowledge. It does not restore deleted bytes and it does not
    unsend a publication.
    """
    if action in IRREVERSIBLE_ACTIONS and state != CERTIFIED_EQUIVALENT:
        raise OracleError(
            f"irreversible_action_on_uncertified_state: {action!r} requires a "
            f"certificate, and this group is {state!r}")


# ------------------------------------------------------- the cheapest monitor

def heterogeneity_signal(node: TreeNode, *, spread_threshold: float = 20.0,
                         key: str = "bytes") -> dict[str, Any]:
    """Suspicion, never evidence, from the dispersion of refutable attributes.

    This is the cheapest of the five channels and it is the one that would have
    caught the failure that actually happened: ``projects.dimensionality`` marked
    774 rows ``3d`` averaging 0.11 GB while 25 mixed rows averaged 20 GB, a 180x
    spread inside a single declared class, unchallenged for months. No domain
    knowledge was needed -- only the class looking at itself.

    Deliberately uses attributes DISJOINT from whatever a fold lacks, which is
    why the payload key is a parameter and never the missing authority.
    """
    values = [float(leaf.payload.get(key, 0) or 0)
              for leaf in node.descendants() if leaf.is_leaf]
    values = [v for v in values if v > 0]
    if len(values) < 4:
        return {"contract": CONTRACT, "scope": node.scope, "signal": False,
                "reason": "too few measured members to say anything"}
    values.sort()
    median = values[len(values) // 2]
    spread = (values[-1] / median) if median else float("inf")
    return {
        "contract": CONTRACT,
        "scope": node.scope,
        "members_measured": len(values),
        "key": key,
        "median": median,
        "max": values[-1],
        "spread": round(spread, 2),
        "threshold": spread_threshold,
        "signal": spread >= spread_threshold,
        "status": "SUSPICION_ONLY",
        "reason": (f"max/median = {spread:.1f}x on {key} inside one group; a wide "
                   "spread is a reason to look, never a reason to conclude"),
    }
