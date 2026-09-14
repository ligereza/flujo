"""Resolving an identifier to an object, without lying about how many objects.

The previous resolver returned ``str | None``. That signature collapses "one
candidate matched" and "twenty-nine candidates matched" into the same shape --
a present string -- and a caller reading it cannot tell the two apart. That
collapse produced three retracted measurements in a row: a claim about ONE
object's dependency graph was built from a signal that could not individuate.
The measured collision: the filename ``normal.jpg`` is declared as an input by
29 different Blender project files, ``roughness.jpg`` by 23,
``defaultmaterial_roughness.jpg`` by 25.

The precise bug is existential instantiation without a uniqueness proof. The
evidence gave ``exists x. P(x)`` over a set of size k and the caller treated it
as a definite description ("the x such that P(x)"). In type-theory terms: the
code used ``choice`` where only ``unique_choice`` was licensed. ``choice``
needs nothing but nonemptiness; ``unique_choice`` needs k == 1, and only the
second one lets you extract a single value and use it.

The discriminator for what a source can support is NOT "is the claim about a
class or an individual" -- that framing over-rejects. The real discriminator
is INVARIANCE: this source is invariant under permuting the objects inside a
collision class, so a claim is derivable from it only if the claim's truth
value is invariant under that same permutation group. Consequence: an
individuating claim over a collision class of size 1 is perfectly admissible,
because a permutation group over one element is trivial. A rule that forbids
all individual claims is wrong; see the counterexample test below.

There is no paradox in the two directions the same number k plays.
As evidence for a class-level claim, k is a SAMPLE SIZE and strength grows
with k. As evidence for an individuating claim, k is an ANONYMITY-SET SIZE and
exactly log2(k) bits are missing to pick one member out of it. Both grow with
k at once; they are not opposites, they are two different questions asked of
the same set. For an n-ary claim the requirement is the product structure over
n independent picks, so the deficit is n * log2(k) -- arity enters
MULTIPLICATIVELY, not as a category that flips admissibility on or off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .epistemics import REMEDY, UNKNOWN_CAUSES

CONTRACT = "mak-resolution-v1"


class AmbiguousResolutionError(ValueError):
    """The only unsound step (pick one value out of many) was attempted anyway."""


@dataclass(frozen=True)
class Unique:
    """Exactly one candidate. ``witness`` is the stated reason it is the one."""

    value: Any
    witness: str

    def __post_init__(self) -> None:
        if not self.witness:
            # An empty witness is a uniqueness claim with no stated reason,
            # which is the exact thing this module exists to stop.
            raise ValueError("Unique.witness must be non-empty")


@dataclass(frozen=True)
class Many:
    """More than one candidate. No attribute here yields a single value.

    Reading one candidate out of Many by accident (``.value``, iterating and
    taking the first, indexing ``[0]``) is the exact bug this module replaces.
    Only ``candidates`` (the full tuple) and ``k`` (the count) are exposed.
    """

    candidates: tuple[Any, ...]

    @property
    def k(self) -> int:
        return len(self.candidates)


@dataclass(frozen=True)
class Absent:
    """Zero candidates, with a cause drawn from the declared vocabulary."""

    cause: str

    def __post_init__(self) -> None:
        if self.cause not in UNKNOWN_CAUSES:
            raise ValueError(f"undeclared_unknown_cause: {self.cause}")


Resolution = Unique | Many | Absent


def resolve(candidates: Any, *, witness: str = "", cause: str = "") -> Resolution:
    """Classify a set of candidates as Absent, Unique, or Many.

    Candidates are deduplicated first: two observations of the same object are
    not two objects, and counting them as two is a separate collapse that must
    not sneak in here. Deduplication uses equality, in encounter order, so
    that non-hashable candidates are still accepted.
    """
    deduped: list[Any] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)

    if not deduped:
        # Absent.__post_init__ validates cause against UNKNOWN_CAUSES, so an
        # unstated or unknown cause is rejected there rather than duplicated
        # here.
        return Absent(cause=cause)
    if len(deduped) == 1:
        return Unique(value=deduped[0], witness=witness)
    return Many(candidates=tuple(deduped))


def individuating_deficit(k: int, arity: int = 1) -> float:
    """Bits missing to pick one member of a size-k anonymity set, n times over.

    Zero iff k == 1: a singleton set hides nothing. Arity multiplies rather
    than branches into a category, because an n-ary claim is n independent
    picks from the same set, and independent picks compose by adding bits
    (equivalently, multiplying the deficit of one pick by n).
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if arity < 1:
        raise ValueError(f"arity must be >= 1, got {arity}")
    if k == 1:
        return 0.0
    return arity * math.log2(k)


def class_strength(k: int) -> float:
    """Sample-size strength of a class-level claim drawn from k candidates.

    sqrt(k): the scale is concentration-like (a bound on how a class-level
    estimate should tighten as the sample grows) and is used here ONLY
    ordinally, to compare two values of k against each other, never as a
    calibrated probability or confidence level.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    return math.sqrt(k)


def admits(resolution: Resolution, *, arity: int) -> bool:
    """True iff an individuating claim of this arity is derivable from this."""
    if isinstance(resolution, Unique):
        return True
    if isinstance(resolution, Many):
        # A collision class of size > 1 has a nontrivial permutation group;
        # any individuating claim's truth value flips under some permutation
        # in it, so none is derivable regardless of arity.
        return False
    return False


def candidate_count(resolution: Resolution) -> int:
    """How many objects matched. 1 for Unique, k for Many, 0 for Absent.

    Persisted on the evidence row so an ambiguous referent stops being invisible:
    an edge whose object matched 8 candidates used to look exactly like one that
    matched 1.
    """
    if isinstance(resolution, Unique):
        return 1
    if isinstance(resolution, Many):
        return resolution.k
    return 0


def is_present(resolution: Resolution) -> bool:
    """Whether the corpus contains this referent at all.

    True for Many as well as Unique, and that is not a weakening. "This id
    resolves somewhere in this corpus" is invariant under permuting the objects
    that carry it, so it factors through the collision class and Many supports
    it perfectly. Only ``admits`` is stricter, because naming WHICH object does
    not factor through it.

    Kept as a function rather than left to truthiness: a frozen dataclass is
    truthy, so `if resolve(...)` would silently be True even for Absent.
    """
    return not isinstance(resolution, Absent)


def require_unique(resolution: Resolution, *, claim: str) -> Any:
    """The one unsound step (extract a single value), made an explicit term.

    Returns the value for Unique. Raises AmbiguousResolutionError for Many,
    naming k and the arity-1 deficit in bits, and for Absent, naming the
    cause and its remedy.
    """
    if isinstance(resolution, Unique):
        return resolution.value
    if isinstance(resolution, Many):
        k = resolution.k
        deficit = individuating_deficit(k, arity=1)
        raise AmbiguousResolutionError(
            f"cannot resolve claim '{claim}': {k} candidates "
            f"(deficit {deficit:.3f} bits), not one"
        )
    remedy = REMEDY[resolution.cause]
    raise AmbiguousResolutionError(
        f"cannot resolve claim '{claim}': absent, cause={resolution.cause}, "
        f"remedy: {remedy}"
    )
