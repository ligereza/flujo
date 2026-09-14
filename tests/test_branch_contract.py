"""The branch contract separates the current ref from inherited lane metadata."""

from __future__ import annotations

from tools.branch_contract import disposition, interpret_ref
from tools.capabilities import _ref_inventory


def test_canonical_mak_profile_is_an_operational_ref() -> None:
    result = interpret_ref("MAK", {
        "branch": "MAK",
        "canonical_ref": "MAK",
        "lane": "MAK",
        "kind": "operational",
        "integration_target": "main",
    })

    assert result["current_ref"] == "MAK"
    assert result["canonical_ref"] == "MAK"
    assert result["lane"] == "MAK"
    assert result["kind"] == "operational"
    assert result["comparison_ref"] == "MAK"
    assert result["integration_target"] == "main"
    assert result["profile_scope"] == "canonical"
    assert result["issues"] == []
    assert disposition("MAK", result) == "canonical"


def test_topic_branch_can_inherit_mak_lane_without_becoming_mak_ref() -> None:
    result = interpret_ref("fix/ig-download-resolution-disclosure", {"branch": "MAK"})

    assert result["current_ref"] == "fix/ig-download-resolution-disclosure"
    assert result["canonical_ref"] == "MAK"
    assert result["lane"] == "MAK"
    assert result["kind"] == "topic"
    assert result["comparison_ref"] == "MAK"
    assert result["integration_target"] == "main"
    assert result["profile_scope"] == "inherited"
    assert result["issues"] == []
    assert disposition(result["current_ref"], result) == "topic_active_or_recover_selectively"


def test_integration_alias_is_not_counted_as_duplicate_work() -> None:
    result = interpret_ref("integration/flujo-canonical-20260911", {"branch": "FLUJO"})

    assert result["current_ref"] != result["canonical_ref"]
    assert result["canonical_ref"] == "FLUJO"
    assert result["kind"] == "integration-alias"
    assert result["comparison_ref"] == "FLUJO"
    assert result["integration_target"] == "main"
    assert disposition(result["current_ref"], result) == "alias_or_checkpoint"


def test_canonical_ref_conflict_remains_a_real_failure() -> None:
    result = interpret_ref("MAK", {"branch": "FLUJO", "canonical_ref": "FLUJO"})

    assert any(issue.startswith("profile_branch_mismatch:") for issue in result["issues"])


def test_canonical_flujo_profile_is_operational_and_promotes_to_main() -> None:
    result = interpret_ref("FLUJO", {
        "branch": "FLUJO",
        "canonical_ref": "FLUJO",
        "lane": "FLUJO",
        "kind": "operational",
        "integration_target": "main",
    })

    assert result["canonical_ref"] == "FLUJO"
    assert result["lane"] == "FLUJO"
    assert result["kind"] == "operational"
    assert result["comparison_ref"] == "FLUJO"
    assert result["integration_target"] == "main"
    assert result["issues"] == []


def test_historia_is_historical_without_deployment_target() -> None:
    result = interpret_ref("historia", {})

    assert result["kind"] == "historical"
    assert result["lane"] == "historical"
    assert result["comparison_ref"] is None
    assert result["integration_target"] is None


def test_canonical_lane_conflicts_are_reported() -> None:
    mak = interpret_ref("MAK", {"canonical_ref": "MAK", "lane": "FLUJO", "kind": "operational", "integration_target": "main"})
    flujo = interpret_ref("FLUJO", {"canonical_ref": "FLUJO", "lane": "MAK", "kind": "operational", "integration_target": "main"})

    assert any(issue.startswith("profile_lane_mismatch:") for issue in mak["issues"])
    assert any(issue.startswith("profile_lane_mismatch:") for issue in flujo["issues"])


def test_automated_ref_retains_lane_and_is_reevaluated() -> None:
    result = interpret_ref("dependabot/pip/pip-64f81b6e5d", {"branch": "MAK"})

    assert result["kind"] == "automated"
    assert result["lane"] == "MAK"
    assert result["comparison_ref"] == "MAK"
    assert result["integration_target"] == "main"
    assert disposition(result["current_ref"], result) == "automated_reevaluate"


def test_live_ref_inventory_reports_aliases_without_counting_them_as_work() -> None:
    from pathlib import Path

    inventory = _ref_inventory(Path(__file__).resolve().parents[1])
    assert inventory["available"] is True
    assert inventory["ref_count"] >= inventory["unique_sha_count"]
    assert inventory["alias_group_count"] >= 1
    main = next(row for row in inventory["refs"] if row["name"] == "main")
    assert main["kind"] == "integrated"
    assert main["disposition"] == "canonical"
    assert inventory["ref_counts"]["head"] > 0
    assert inventory["ref_counts"]["remote_tracking"] > 0
    assert inventory["ref_counts"]["tag"] > 0
    assert inventory["ref_counts"]["annotated_tag"] > 0
    house_history = next(
        row for row in inventory["refs"] if row["name"] == "archive/house-history"
    )
    assert house_history["ref_kind"] == "annotated_tag"
    assert house_history["object_sha"] != house_history["peeled_commit_sha"]
    assert house_history["kind"] == "historical"
    assert house_history["disposition"] == "historical_preserve"
    assert house_history["aliases"] == ["archive/house-history"]
