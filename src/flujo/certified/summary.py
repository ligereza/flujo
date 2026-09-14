"""Conservative summaries that compose, and refuse to certify past their coverage.

A summary is what lets a query answer something about every member of a group
without opening any of them. It is useful only when it is SOUND, and the audit
that produced this module found exactly one recurring way to make it unsound:

    a summary built over a SUBSET certifying over the WHOLE.

The fix is structural rather than remembered. Every summary carries
``n_members`` and, per authority, how many of those members that authority
actually covered. A negative certificate is refused unless the two are equal.
That is the difference between "no evidence of X" and "evidence of no X", and it
is enforced here so no caller has to remember it.

Two design choices are load-bearing:

**Universal facts are counted, not flagged.** Storing ``all_blend: bool`` needs
an AND at every join and has a dangerous identity element -- an empty summary
would claim every universal vacuously. Storing ``counts["blend"]`` instead makes
the join a sum, and both ``any`` and ``all`` become derived:

    any_X  =  counts[X] > 0
    all_X  =  counts[X] == n_members

**Ranges carry their source.** A date hull over release dates is sound; the same
hull over mtimes is meaningless, and the corpus proves it -- all 330 files in the
Instagram ``other`` surface have mtimes inside a 55 second window, because they
were written by one export. So ``ranges`` is always paired with
``range_sources``, and a hull whose sources are mixed refuses to certify.

The join is a semilattice operation: associative, commutative, idempotent. That
is what lets a parent summary be computed from its children once and reused,
instead of rescanning members.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

CONTRACT = "mak-conservative-summary-v1"

# The three kinds of thing a certificate can be about. Keeping them apart is the
# whole point: a POLICY_CLAIM is complete by construction and therefore always
# certifiable, which makes it the most dangerous kind to mistake for a fact.
WORLD_CLAIM = "WORLD_CLAIM"
CORPUS_CLAIM = "CORPUS_CLAIM"
POLICY_CLAIM = "POLICY_CLAIM"
CLAIM_TYPES = (WORLD_CLAIM, CORPUS_CLAIM, POLICY_CLAIM)

# Epistemic states. The middle one may never be serialised or consumed as the
# first one, and no destructive action may depend on it alone.
CERTIFIED_EQUIVALENT = "≡"      # equivalence relative to an explicit contract
UNRESOLVED = "≈"                # insufficient evidence
CERTIFIED_DISTINCT = "≠"        # certified distinction


class SummaryError(ValueError):
    """A summary was asked for something it cannot answer soundly."""


@dataclass(frozen=True)
class Summary:
    """A conservative over-approximation of a set of corpus members.

    Every field composes. Nothing here is a semantic conclusion: ``sets`` holds
    observed values, ``counts`` holds how many members carry a property, and
    ``covered`` holds how much of the group each authority actually saw.
    """

    scope: str
    n_members: int = 0
    # authority name -> how many members that authority produced evidence for
    covered: Mapping[str, int] = field(default_factory=dict)
    # observed value sets, e.g. "extension" -> {".blend", ".png"}
    sets: Mapping[str, frozenset] = field(default_factory=dict)
    # how many members carry a named property, e.g. "has_3d_format" -> 12
    counts: Mapping[str, int] = field(default_factory=dict)
    # numeric hulls, e.g. "date" -> (min, max)
    ranges: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    # which source each hull was drawn from, e.g. "date" -> {"release_date"}
    range_sources: Mapping[str, frozenset] = field(default_factory=dict)
    # evidence source ids that contributed anything to this summary
    provenance: frozenset = field(default_factory=frozenset)

    # ------------------------------------------------------------ derived views

    def any(self, prop: str) -> bool:
        """At least one member carries ``prop``. Sound with partial coverage."""
        return int(self.counts.get(prop, 0)) > 0

    def all(self, prop: str) -> bool | None:
        """Every member carries ``prop``, or None when it cannot be decided.

        Returns None for an empty group rather than True. A vacuous universal is
        exactly the kind of quiet claim this module exists to prevent.
        """
        if self.n_members == 0:
            return None
        return int(self.counts.get(prop, 0)) == self.n_members

    def none(self, prop: str) -> bool:
        """No member carries ``prop`` AS OBSERVED. Not the same as 'no member has it'.

        Callers must pair this with :meth:`complete_for` before treating it as a
        negative certificate.
        """
        return int(self.counts.get(prop, 0)) == 0

    def complete_for(self, authority: str) -> bool:
        """Did this authority see every member of the group?

        The single guard that turns "absence of evidence" into "evidence of
        absence". Without it a summary built over a subset certifies over the
        whole, which is the defect this module was written to make impossible.
        """
        if self.n_members == 0:
            return False
        return int(self.covered.get(authority, 0)) == self.n_members

    def uncovered(self, authority: str) -> int:
        return max(self.n_members - int(self.covered.get(authority, 0)), 0)

    def values(self, key: str) -> frozenset:
        return self.sets.get(key, frozenset())

    def hull(self, key: str) -> tuple[float, float] | None:
        return self.ranges.get(key)

    def hull_is_source_pure(self, key: str) -> bool:
        """A hull mixing sources cannot certify. Measured: the `other` surface.

        All 330 files there share a 55 second mtime window written by one export,
        so an mtime hull says when bytes were copied, never when work was shown.
        """
        sources = self.range_sources.get(key, frozenset())
        return len(sources) == 1

    # -------------------------------------------------------------------- join

    def join(self, other: "Summary", *, scope: str | None = None) -> "Summary":
        """The semilattice join. Associative, commutative, idempotent."""
        return Summary(
            scope=scope if scope is not None else _common_scope(self.scope, other.scope),
            n_members=self.n_members + other.n_members,
            covered=_add(self.covered, other.covered),
            sets=_union(self.sets, other.sets),
            counts=_add(self.counts, other.counts),
            ranges=_hull(self.ranges, other.ranges),
            range_sources=_union(self.range_sources, other.range_sources),
            provenance=self.provenance | other.provenance,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "scope": self.scope,
            "n_members": self.n_members,
            "covered": dict(sorted(self.covered.items())),
            "sets": {k: sorted(v) for k, v in sorted(self.sets.items())},
            "counts": dict(sorted(self.counts.items())),
            "ranges": {k: list(v) for k, v in sorted(self.ranges.items())},
            "range_sources": {k: sorted(v) for k, v in sorted(self.range_sources.items())},
            "provenance": sorted(self.provenance),
        }


def empty(scope: str) -> Summary:
    return Summary(scope=scope)


def join_all(summaries: Iterable[Summary], *, scope: str) -> Summary:
    out = empty(scope)
    for item in summaries:
        out = out.join(item, scope=scope)
    return out


# ---------------------------------------------------------------- field merges

def _add(a: Mapping[str, int], b: Mapping[str, int]) -> dict[str, int]:
    out = dict(a)
    for key, value in b.items():
        out[key] = int(out.get(key, 0)) + int(value)
    return out


def _union(a: Mapping[str, frozenset], b: Mapping[str, frozenset]) -> dict[str, frozenset]:
    out = {key: frozenset(value) for key, value in a.items()}
    for key, value in b.items():
        out[key] = out.get(key, frozenset()) | frozenset(value)
    return out


def _hull(a: Mapping[str, tuple[float, float]],
          b: Mapping[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    out = dict(a)
    for key, (lo, hi) in b.items():
        if key in out:
            olo, ohi = out[key]
            out[key] = (min(olo, lo), max(ohi, hi))
        else:
            out[key] = (lo, hi)
    return out


def _common_scope(a: str, b: str) -> str:
    if a == b:
        return a
    parts_a, parts_b = a.split("/"), b.split("/")
    shared = []
    for pa, pb in zip(parts_a, parts_b):
        if pa != pb:
            break
        shared.append(pa)
    return "/".join(shared) if shared else ""


def from_member(scope: str, *, authorities_covering: Iterable[str] = (),
                sets: Mapping[str, Iterable] | None = None,
                properties: Iterable[str] = (),
                values: Mapping[str, tuple[float, str]] | None = None,
                provenance: Iterable[str] = ()) -> Summary:
    """Build the leaf summary of a single corpus member.

    ``values`` maps a range key to ``(number, source)``; the source is recorded
    so a later hull can refuse to certify when sources were mixed.
    """
    ranges: dict[str, tuple[float, float]] = {}
    sources: dict[str, frozenset] = {}
    for key, (number, source) in (values or {}).items():
        ranges[key] = (float(number), float(number))
        sources[key] = frozenset({str(source)})
    return Summary(
        scope=scope,
        n_members=1,
        covered={name: 1 for name in authorities_covering},
        sets={key: frozenset(value) for key, value in (sets or {}).items()},
        counts={name: 1 for name in properties},
        ranges=ranges,
        range_sources=sources,
        provenance=frozenset(provenance),
    )
