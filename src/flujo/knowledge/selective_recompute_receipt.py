"""Observe whether an opportunity delta is reflected in bounded outputs.

This projection never executes a consumer.  It compares already materialized
output hashes with the consumers declared by ``mak-opportunity-delta-v1`` and
reports missing or unexplained changes instead of treating them as causality.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json

from .opportunity_delta import validate_opportunity_delta


SCHEMA = "mak-selective-recompute-receipt-v1"
ALGORITHM_VERSION = "opportunity-delta-output-reconciliation-1"
_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "delta_hash",
    "previous_input_hash", "current_input_hash", "affected_consumers",
    "before_outputs", "after_outputs", "changed_outputs",
    "changed_affected_consumers", "missing_affected_consumers",
    "unexplained_outputs", "status", "controls", "reconciliation",
    "provenance",
}
_OUTPUT_TO_CONSUMER = {
    "fit": "opportunity_fit",
    "programs": "artistic_program_hypotheses",
    "possibility": "possibility_field",
    "research-frontier": "research_frontier_bridge",
    "product-plan": "product_plan",
    "portfolio-dossier": "portfolio_dossier",
    "application-research": "application_research_package",
    "episode": "product_episode",
    "autonomy": "autonomy_plan",
}
_DIRECT_SOURCE_OUTPUTS = {"opportunity"}


class SelectiveRecomputeReceiptError(ValueError):
    """Raised when the causal comparison cannot be made safely."""


def _output_map(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise SelectiveRecomputeReceiptError(f"{name}_must_be_nonempty_object")
    result: dict[str, str] = {}
    for key, digest in value.items():
        if not isinstance(key, str) or not key or key in result:
            raise SelectiveRecomputeReceiptError(f"{name}_key_invalid")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise SelectiveRecomputeReceiptError(f"{name}_hash_invalid")
        result[key] = digest
    return dict(sorted(result.items()))


def _require_delta(delta: Any) -> Mapping[str, Any]:
    if not isinstance(delta, Mapping):
        raise SelectiveRecomputeReceiptError("delta_must_be_object")
    return delta


def _project(delta: Mapping[str, Any], before_outputs: Mapping[str, str], after_outputs: Mapping[str, str]) -> dict[str, Any]:
    before = _output_map(before_outputs, "before_outputs")
    after = _output_map(after_outputs, "after_outputs")
    affected = sorted(set(delta["impact"]["affected_consumers"]))
    names = sorted(set(before) | set(after))
    changed = sorted(name for name in names if before.get(name) != after.get(name))
    changed_affected = sorted(
        _OUTPUT_TO_CONSUMER[name]
        for name in changed
        if name in _OUTPUT_TO_CONSUMER and _OUTPUT_TO_CONSUMER[name] in affected
    )
    missing = sorted(
        consumer for consumer in affected
        if not any(_OUTPUT_TO_CONSUMER.get(name) == consumer for name in after)
    )
    unexplained = sorted(
        name for name in changed
        if name not in _DIRECT_SOURCE_OUTPUTS
        and (_OUTPUT_TO_CONSUMER.get(name) not in affected)
    )
    if not delta["impact"]["recompute_required"]:
        status = "no_recompute_expected" if not changed else "unexpected_output_change"
    elif unexplained:
        status = "mixed_or_unexplained"
    elif missing:
        status = "incomplete_output_coverage"
    else:
        status = "causally_bounded"
    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": delta["opportunity_id"],
        "delta_hash": _hash(delta),
        "previous_input_hash": delta["previous_input_hash"],
        "current_input_hash": delta["current_input_hash"],
        "affected_consumers": affected,
        "before_outputs": before,
        "after_outputs": after,
        "changed_outputs": changed,
        "changed_affected_consumers": changed_affected,
        "missing_affected_consumers": missing,
        "unexplained_outputs": unexplained,
        "status": status,
        "controls": {
            "execution_performed": False,
            "database_write": False,
            "network_called": False,
            "publication": False,
            "submission": False,
            "dispatch": False,
            "promotion": "none",
            "training_permitted": False,
        },
        "reconciliation": {
            "before_output_count": len(before),
            "after_output_count": len(after),
            "changed_output_count": len(changed),
            "affected_consumer_count": len(affected),
            "changed_affected_consumer_count": len(changed_affected),
            "missing_affected_consumer_count": len(missing),
            "unexplained_output_count": len(unexplained),
            "truth_promotions": 0,
            "deterministic": True,
        },
        "provenance": {
            "delta_schema": delta["schema"],
            "output_hash_source": "caller_materialized_manifests",
            "execution_observed": False,
            "promotion": "none",
        },
    }


def build_selective_recompute_receipt(
    previous_constraints: Mapping[str, Any],
    current_constraints: Mapping[str, Any],
    delta: Mapping[str, Any],
    before_outputs: Mapping[str, str],
    after_outputs: Mapping[str, str],
) -> dict[str, Any]:
    """Compare materialized output hashes against a validated semantic delta."""
    delta = _require_delta(delta)
    if not validate_opportunity_delta(previous_constraints, current_constraints, delta):
        raise SelectiveRecomputeReceiptError("delta_invalid")
    output = _project(delta, before_outputs, after_outputs)
    if not validate_selective_recompute_receipt(previous_constraints, current_constraints, delta, output):
        raise SelectiveRecomputeReceiptError("generated_receipt_failed_validation")
    return output


def validate_selective_recompute_receipt(
    previous_constraints: Mapping[str, Any],
    current_constraints: Mapping[str, Any],
    delta: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    try:
        if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
            return False
        if not validate_opportunity_delta(previous_constraints, current_constraints, delta):
            return False
        expected = _project(delta, payload["before_outputs"], payload["after_outputs"])
        return payload == expected
    except (SelectiveRecomputeReceiptError, TypeError, ValueError, KeyError):
        return False
