"""Shared interpretation of Git refs and branch profiles.

``branch_profile.json`` was originally written for canonical checkouts and its
``branch`` field therefore means the lane that owns the work.  A topic or
worktree checkout can inherit that profile without becoming the canonical ref.
This module keeps that distinction in one small compatibility layer used by
the existing capability, release and runtime checks.
"""

from __future__ import annotations

from typing import Any, Mapping


CANONICAL_REFS = frozenset({"main", "MAK", "FLUJO", "historia"})
LANES = frozenset({"main", "MAK", "FLUJO", "integrated", "historical"})

# ``integration_target`` is the final promotion destination.  It is not the
# ref against which a lane is compared right now; that is ``comparison_ref``.
CANONICAL_DEFAULTS = {
    "main": {"lane": "integrated", "kind": "integrated", "integration_target": "main", "comparison_ref": "main"},
    "MAK": {"lane": "MAK", "kind": "operational", "integration_target": "main", "comparison_ref": "MAK"},
    "FLUJO": {"lane": "FLUJO", "kind": "operational", "integration_target": "main", "comparison_ref": "FLUJO"},
    "historia": {"lane": "historical", "kind": "historical", "integration_target": None, "comparison_ref": None},
}


def ref_name(value: str | None) -> str:
    """Normalize a local or ``refs/remotes/...`` name to its branch name."""
    text = str(value or "").strip()
    if text.startswith("refs/remotes/"):
        text = text.removeprefix("refs/remotes/")
        if "/" in text:
            text = text.split("/", 1)[1]
    elif text.startswith("refs/heads/"):
        text = text.removeprefix("refs/heads/")
    return text


def _pattern_kind(current_ref: str) -> str:
    if current_ref in CANONICAL_REFS:
        return {
            "main": "integrated",
            "MAK": "operational",
            "FLUJO": "operational",
            "historia": "historical",
        }[current_ref]
    if current_ref.startswith("dependabot/"):
        return "automated"
    if current_ref == "DIRECTOR" or current_ref.startswith("archive/"):
        return "historical"
    if current_ref.startswith("integration/") or "main-union" in current_ref:
        return "integration-alias"
    if current_ref.startswith("worktree-"):
        return "worktree"
    if current_ref.split("/", 1)[0] in {"docs", "feat", "fix", "test", "chore", "perf", "refactor"}:
        return "topic"
    return "auxiliary"


def interpret_ref(current_ref: str | None, profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return one semantic view without conflating comparison and promotion."""
    current = ref_name(current_ref)
    profile = profile if isinstance(profile, Mapping) else {}
    declared = str(
        profile.get("canonical_ref")
        or profile.get("lane")
        or profile.get("branch")
        or ""
    ).strip()
    pattern_kind = _pattern_kind(current)
    kind = str(profile.get("kind") or "").strip() or pattern_kind
    if current not in CANONICAL_REFS:
        # A copied canonical profile is inherited metadata, not a claim about
        # the current ref.  Names with their own topology signal take priority.
        kind = pattern_kind
    if "main-union" in current:
        canonical = "main"
        lane = "integrated"
    elif current in CANONICAL_REFS:
        canonical = declared if declared in CANONICAL_REFS else current
        lane = (
            str(profile.get("lane"))
            if profile.get("lane") in LANES
            else str(CANONICAL_DEFAULTS.get(canonical, {}).get("lane") or canonical)
        )
    else:
        canonical = declared if declared in {"MAK", "FLUJO", "main", "historia"} else None
        if pattern_kind == "historical" and not canonical:
            canonical = current or None
            lane = "historical"
        else:
            lane = "integrated" if canonical == "main" else canonical

    explicit_current = profile.get("current_ref")
    explicit_integration_target = profile.get("integration_target")
    issues: list[str] = []
    if current in CANONICAL_REFS and canonical != current:
        issues.append(f"profile_branch_mismatch:{canonical or declared or None}->{current}")
    if explicit_current and str(explicit_current) != current:
        issues.append(f"profile_current_ref_mismatch:{explicit_current}->{current}")
    if current not in CANONICAL_REFS and not canonical:
        issues.append("profile_canonical_ref_missing")
    if current not in CANONICAL_REFS and declared and declared != canonical:
        # The legacy ``branch`` field is an inherited lane for topics and
        # worktrees.  A topology-named integration ref may therefore quite
        # legitimately inherit MAK/FLUJO while resolving to another
        # canonical integration ref.  Only an explicit canonical/lane claim
        # is contradictory here; do not turn inherited metadata into a
        # false-positive blocker.
        if profile.get("canonical_ref") is not None or profile.get("lane") is not None:
            issues.append(f"profile_lane_mismatch:{declared}->{canonical}")

    defaults = CANONICAL_DEFAULTS.get(canonical or "")
    if current in CANONICAL_REFS and defaults:
        if lane != defaults["lane"]:
            issues.append(f"profile_lane_mismatch:{lane}->{defaults['lane']}")
        if kind != defaults["kind"]:
            issues.append(f"profile_kind_mismatch:{kind}->{defaults['kind']}")

    if explicit_integration_target is not None:
        if explicit_integration_target not in {"main", "MAK", "FLUJO"}:
            issues.append(f"integration_target_invalid:{explicit_integration_target}")
        integration_target = explicit_integration_target
    elif defaults:
        integration_target = defaults["integration_target"]
    elif kind == "historical" or lane == "historical":
        integration_target = None
    else:
        # Inherited operational work promotes through the integrated baseline.
        integration_target = "main" if lane in {"MAK", "FLUJO", "integrated"} else None

    if current in CANONICAL_REFS and defaults:
        expected_target = defaults["integration_target"]
        if integration_target != expected_target:
            issues.append(f"integration_target_mismatch:{integration_target}->{expected_target}")

    if kind == "historical" or lane == "historical":
        comparison_ref = None
    elif current in CANONICAL_REFS:
        comparison_ref = current
    elif "main-union" in current or lane == "integrated":
        comparison_ref = "main"
    else:
        comparison_ref = lane if lane in {"MAK", "FLUJO"} else None

    return {
        "current_ref": current or None,
        "canonical_ref": canonical,
        "lane": lane,
        "kind": kind,
        "comparison_ref": comparison_ref,
        "integration_target": integration_target,
        "profile_declared_ref": declared or None,
        "profile_scope": "canonical" if current in CANONICAL_REFS else "inherited",
        "issues": issues,
    }


def disposition(current_ref: str | None, semantics: Mapping[str, Any]) -> str:
    """Name the bounded disposition used by the ref inventory."""
    current = ref_name(current_ref)
    kind = str(semantics.get("kind") or "auxiliary")
    if current in CANONICAL_REFS:
        return "canonical"
    if kind == "historical":
        return "historical_preserve"
    if kind == "automated":
        return "automated_reevaluate"
    if kind == "integration-alias":
        return "alias_or_checkpoint"
    if kind == "worktree":
        return "worktree_checkpoint"
    if kind == "topic":
        return "topic_active_or_recover_selectively"
    return "auxiliary_review"
