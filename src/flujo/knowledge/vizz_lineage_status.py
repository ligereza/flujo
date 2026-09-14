"""Read-only MAK view of a VIZZ revision lineage."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import required_text as _text, sha256_hex as _hash


SCHEMA = "mak-vizz-lineage-status-v1"
ALGORITHM_VERSION = "vizz-lineage-status-1"
DEFAULT_ARTIFACT = Path("/home/mak/work/grammar-lab-20260912/artifacts/q680_vizz_measurement_lineage_revision.json")
DEFAULT_ARTIFACT_SHA256 = "c1dffd721470bb0c051db7d13737c05c554602a12187a54fa50d1b4a75524008"


def build_vizz_lineage_status(artifact_path: str | Path | None = None) -> dict[str, Any]:
    configured = str(artifact_path or os.environ.get("MAK_VIZZ_LINEAGE_ARTIFACT", "")).strip()
    path = Path(configured).expanduser() if configured else DEFAULT_ARTIFACT
    raw = path.read_bytes()
    expected_hash = os.environ.get("MAK_VIZZ_LINEAGE_EXPECTED_SHA256", DEFAULT_ARTIFACT_SHA256).strip().lower()
    if _hash(raw) != expected_hash:
        raise ValueError("vizz_lineage_artifact_stale")
    artifact = json.loads(raw.decode("utf-8"))
    if artifact.get("version") != "vizz-measurement-lineage-revision-v1":
        raise ValueError("vizz_lineage_artifact_version_invalid")
    previous = artifact.get("previous")
    revision = artifact.get("revision")
    invariants = artifact.get("invariants")
    if not all(isinstance(value, Mapping) for value in (previous, revision, invariants)):
        raise ValueError("vizz_lineage_artifact_shape_invalid")
    if not all(invariants.get(key) is True for key in ("revision_accepted", "lineage_points_to_previous", "revision_hash_differs", "unknown_preserved_across_revision", "controls_remain_closed")):
        raise ValueError("vizz_lineage_artifact_invariants_invalid")
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "status": "revision_context_only",
        "current": {
            "ref": "grammar-lab:Q-650:artifact",
            "sha256": _text(previous.get("sha256"), "current.sha256"),
            "status": _text(previous.get("status"), "current.status"),
        },
        "revision": {
            "revision_id": _text(revision.get("revision", {}).get("revision_id"), "revision.id"),
            "previous_artifact_sha256": _text(revision.get("revision", {}).get("previous_artifact_sha256"), "revision.previous_sha256"),
            "current_artifact_sha256": _text(revision.get("revision", {}).get("current_artifact_sha256"), "revision.current_sha256"),
            "status": "revision_accepted",
        },
        "provenance": {
            "ref": "grammar-lab:Q-680:artifact",
            "sha256": _hash(raw),
            "source_schema": "vizz-measurement-lineage-revision-v1",
        },
        "control": {
            "database_write": False,
            "decision_write": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
            "current_state_replaced": False,
        },
    }
    validate_vizz_lineage_status(result)
    return result


def validate_vizz_lineage_status(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("vizz_lineage_status_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "status", "current", "revision", "provenance", "control"}
    if set(payload) != expected or payload.get("available") is not True or payload.get("read_only") is not True or payload.get("status") != "revision_context_only":
        raise ValueError("vizz_lineage_status_fields_invalid")
    current = payload["current"]
    if set(current) != {"ref", "sha256", "status"} or current["ref"] != "grammar-lab:Q-650:artifact" or current["status"] != "unknown_measurement_refused" or not re.fullmatch(r"[0-9a-f]{64}", current["sha256"]):
        raise ValueError("vizz_lineage_status_current_invalid")
    revision = payload["revision"]
    if set(revision) != {"revision_id", "previous_artifact_sha256", "current_artifact_sha256", "status"} or revision["status"] != "revision_accepted" or not isinstance(revision["revision_id"], str) or not revision["revision_id"].strip() or not re.fullmatch(r"[0-9a-f]{64}", revision["previous_artifact_sha256"]) or not re.fullmatch(r"[0-9a-f]{64}", revision["current_artifact_sha256"]) or revision["previous_artifact_sha256"] != current["sha256"] or revision["previous_artifact_sha256"] == revision["current_artifact_sha256"]:
        raise ValueError("vizz_lineage_status_revision_invalid")
    provenance = payload["provenance"]
    if set(provenance) != {"ref", "sha256", "source_schema"} or provenance["ref"] != "grammar-lab:Q-680:artifact" or provenance["source_schema"] != "vizz-measurement-lineage-revision-v1" or not re.fullmatch(r"[0-9a-f]{64}", provenance["sha256"]):
        raise ValueError("vizz_lineage_status_provenance_invalid")
    if payload["control"] != {"database_write": False, "decision_write": False, "selection_effect": "none", "promotion": "none", "publication": False, "current_state_replaced": False}:
        raise ValueError("vizz_lineage_status_control_invalid")
    return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_vizz_lineage_status", "validate_vizz_lineage_status"]
