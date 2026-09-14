"""Read-only MAK summary of the Q-750 structural source delta."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import required_text as _text, sha256_hex as _hash


SCHEMA = "mak-structural-delta-status-v1"
ALGORITHM_VERSION = "structural-delta-status-1"
DEFAULT_ARTIFACT = Path("/home/mak/work/grammar-lab-20260912/artifacts/q750_structural_source_delta_holdout.json")
DEFAULT_ARTIFACT_SHA256 = "07ff1284e39a26f16fc82a7c04716e2f0ffbe1f9264739c71691aa8badadefe0"


def build_structural_delta_status(artifact_path: str | Path | None = None) -> dict[str, Any]:
    configured = str(artifact_path or os.environ.get("MAK_STRUCTURAL_DELTA_ARTIFACT", "")).strip()
    path = Path(configured).expanduser() if configured else DEFAULT_ARTIFACT
    raw = path.read_bytes()
    expected_hash = os.environ.get("MAK_STRUCTURAL_DELTA_EXPECTED_SHA256", DEFAULT_ARTIFACT_SHA256).strip().lower()
    if _hash(raw) != expected_hash:
        raise ValueError("structural_delta_artifact_stale")
    artifact = json.loads(raw.decode("utf-8"))
    if artifact.get("version") != "structural-source-delta-holdout-v2":
        raise ValueError("structural_delta_artifact_version_invalid")
    delta = artifact.get("structural_delta")
    pins = artifact.get("pins")
    metrics = artifact.get("metrics")
    invariants = artifact.get("invariants")
    if not all(isinstance(value, Mapping) for value in (delta, pins, metrics, invariants)):
        raise ValueError("structural_delta_artifact_shape_invalid")
    if not all(invariants.get(key) is True for key in ("structural_change_present", "library_old_pin_only", "revision_residues_bound_to_new_pin", "old_pin_not_used_for_residues", "expansion_includes_revision_key", "consumer_expansion_exact", "tampered_residue_rejected")):
        raise ValueError("structural_delta_artifact_invariants_invalid")
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "status": "revision_only_delta",
        "delta": {
            "revision_only_key": _text(delta.get("revision_only_key"), "delta.revision_only_key"),
            "evaluated_keys": int(metrics.get("evaluated_keys", -1)),
            "shared_keys": int(metrics.get("old_library_keys", -1)),
            "residue_keys": int(metrics.get("residue_keys", -1)),
            "baseline_bytes": int(metrics.get("baseline_bytes", -1)),
            "library_total_bytes": int(metrics.get("library_total_bytes", -1)),
            "serialized_savings_bytes": int(metrics.get("serialized_savings_bytes", 0)),
        },
        "provenance": {
            "ref": "grammar-lab:Q-750:artifact",
            "sha256": _hash(raw),
            "library_pin": _text(pins.get("library"), "provenance.library_pin"),
            "evaluation_pin": _text(pins.get("evaluation"), "provenance.evaluation_pin"),
        },
        "control": {
            "database_write": False,
            "decision_write": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
            "learning_demonstrated": False,
        },
        "limits": [
            "revision-only delta; no semantic equivalence",
            "residuos nuevos no se atribuyen al pin antiguo",
            "no modifica el Portafolio ni el estado VIZZ",
        ],
    }
    validate_structural_delta_status(result)
    return result


def validate_structural_delta_status(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("structural_delta_status_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "status", "delta", "provenance", "control", "limits"}
    if set(payload) != expected or payload.get("available") is not True or payload.get("read_only") is not True or payload.get("status") != "revision_only_delta":
        raise ValueError("structural_delta_status_fields_invalid")
    delta = payload["delta"]
    if set(delta) != {"revision_only_key", "evaluated_keys", "shared_keys", "residue_keys", "baseline_bytes", "library_total_bytes", "serialized_savings_bytes"} or not isinstance(delta["revision_only_key"], str) or any(not isinstance(delta[field], int) or delta[field] < 0 for field in ("evaluated_keys", "shared_keys", "residue_keys", "baseline_bytes", "library_total_bytes")) or not isinstance(delta["serialized_savings_bytes"], int):
        raise ValueError("structural_delta_status_delta_invalid")
    provenance = payload["provenance"]
    if set(provenance) != {"ref", "sha256", "library_pin", "evaluation_pin"} or provenance["ref"] != "grammar-lab:Q-750:artifact" or not re.fullmatch(r"[0-9a-f]{64}", provenance["sha256"]) or not all(isinstance(provenance[field], str) and provenance[field] for field in ("library_pin", "evaluation_pin")):
        raise ValueError("structural_delta_status_provenance_invalid")
    if payload["control"] != {"database_write": False, "decision_write": False, "selection_effect": "none", "promotion": "none", "publication": False, "learning_demonstrated": False}:
        raise ValueError("structural_delta_status_control_invalid")
    if not isinstance(payload["limits"], list) or any(not isinstance(value, str) or not value for value in payload["limits"]):
        raise ValueError("structural_delta_status_limits_invalid")
    return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_structural_delta_status", "validate_structural_delta_status"]
