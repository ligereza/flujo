"""Attack the resolver: each test fails if a specific confusion returns.

The confusion this module replaces: a resolver that returns ``str | None``
cannot tell "one candidate" from "twenty-nine candidates" apart, and that
collapse produced three retracted measurements built on a signal that could
not individuate (see the module docstring in resolution.py for the measured
collision counts: 29, 23, 25).
"""

from __future__ import annotations

import math

import pytest

from flujo.substrate.epistemics import MISSING_EVIDENCE, REMEDY, UNKNOWN_CAUSES
from flujo.substrate.resolution import (
    AmbiguousResolutionError,
    Absent,
    Many,
    Unique,
    admits,
    class_strength,
    individuating_deficit,
    require_unique,
    resolve,
)


def test_singleton_is_unique_with_zero_deficit():
    # k == 1: a singleton anonymity set hides nothing.
    resolution = resolve(["obj-a"], witness="only candidate in scope")
    assert isinstance(resolution, Unique)
    assert resolution.value == "obj-a"
    assert individuating_deficit(1) == 0.0
    assert require_unique(resolution, claim="x is obj-a") == "obj-a"


def test_29_collision_gives_many_and_matches_the_measured_deficit():
    # Measured collision: normal.jpg is declared as an input by 29 Blender
    # project files. log2(29) approx 4.858.
    candidates = tuple(f"project_{i}.blend" for i in range(29))
    resolution = resolve(candidates)
    assert isinstance(resolution, Many)
    assert resolution.k == 29

    deficit = individuating_deficit(29)
    assert deficit == pytest.approx(4.858, abs=1e-3)

    with pytest.raises(AmbiguousResolutionError) as excinfo:
        require_unique(resolution, claim="normal.jpg belongs to project X")
    assert "29" in str(excinfo.value)


def test_arity_is_multiplicative_not_a_category():
    # A binary claim over the same collision class needs two independent
    # picks, so the deficit doubles. It does not switch to a different rule.
    single = individuating_deficit(29, arity=1)
    double = individuating_deficit(29, arity=2)
    assert double == pytest.approx(2 * single)


def test_counterexample_singleton_collision_admits_individuating_claim():
    # The first proposed rule forbade all individual claims and was wrong:
    # a collision class of size 1 has a trivial permutation group, so an
    # individuating claim over it IS derivable.
    resolution = resolve(["obj-only"], witness="unique path match")
    assert admits(resolution, arity=1) is True


def test_many_does_not_admit_individuating_claims():
    resolution = resolve(["a", "b", "c"])
    assert admits(resolution, arity=1) is False
    assert admits(resolution, arity=3) is False


def test_both_directions_grow_with_k_at_once():
    # The "inversion" is not a paradox: k is a sample size for a class-level
    # claim (strength grows) and an anonymity-set size for an individuating
    # claim (deficit grows) at the same time, over the same set.
    assert class_strength(29) > class_strength(2)
    assert individuating_deficit(29) > individuating_deficit(2)


def test_many_exposes_no_single_value_attribute():
    resolution = resolve(["a", "b"])
    assert isinstance(resolution, Many)
    # Accidentally reading one candidate out of Many is the exact bug this
    # module exists to make impossible.
    for tempting_name in ("value", "first", "one", "item", "__iter__",
                           "__getitem__", "__next__"):
        assert not hasattr(resolution, tempting_name), tempting_name
    assert resolution.candidates == ("a", "b")


def test_unique_with_empty_witness_raises():
    with pytest.raises(ValueError):
        Unique(value="x", witness="")


def test_absent_with_undeclared_cause_raises():
    assert "not_a_real_cause" not in UNKNOWN_CAUSES
    with pytest.raises(ValueError):
        Absent(cause="not_a_real_cause")


def test_require_unique_on_absent_names_the_remedy():
    resolution = resolve([], cause=MISSING_EVIDENCE)
    assert isinstance(resolution, Absent)
    with pytest.raises(AmbiguousResolutionError) as excinfo:
        require_unique(resolution, claim="x exists")
    message = str(excinfo.value)
    assert MISSING_EVIDENCE in message
    assert REMEDY[MISSING_EVIDENCE] in message


def test_resolve_deduplicates_same_candidate():
    # Two observations of one object are not two objects. That is a separate
    # collapse and it must not sneak in here.
    resolution = resolve(["same-object", "same-object"],
                          witness="two observations, one object")
    assert isinstance(resolution, Unique)
    assert resolution.value == "same-object"


def test_individuating_deficit_rejects_k_below_one():
    with pytest.raises(ValueError):
        individuating_deficit(0)


def test_class_strength_rejects_k_below_one():
    with pytest.raises(ValueError):
        class_strength(0)


def test_deficit_matches_log2_directly():
    # Direct check against math.log2 so the formula itself cannot drift.
    assert individuating_deficit(8) == pytest.approx(math.log2(8))
    assert individuating_deficit(8) == pytest.approx(3.0)
