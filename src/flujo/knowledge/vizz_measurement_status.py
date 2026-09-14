"""Read-only MAK summary of a VIZZ measurement refusal."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import required_text as _text, sha256_hex as _hash


SCHEMA = "mak-vizz-measurement-status-v1"
ALGORITHM_VERSION = "vizz-measurement-status-1"
REVISION_SCHEMA = "mak-vizz-measurement-status-revision-v1"
REVISION_ALGORITHM_VERSION = "vizz-measurement-status-revision-1"
DEFAULT_ARTIFACT = Path("/home/mak/work/grammar-lab-20260912/artifacts/q830_vizz_measurement_lineage_projection.json")
DEFAULT_ARTIFACT_SHA256 = "d77f3ab57615321d48c5f8a66d7ad659dff56ae01c5671b0400331d89547288c"


def build_vizz_measurement_status(artifact_path: str | Path | None = None, *, expected_sha256: str | None = None) -> dict[str, Any]:
    configured = str(artifact_path or os.environ.get("MAK_VIZZ_MEASUREMENT_ARTIFACT", "")).strip()
    path = Path(configured).expanduser() if configured else DEFAULT_ARTIFACT
    raw = path.read_bytes()
    expected_hash = (expected_sha256 or os.environ.get("MAK_VIZZ_MEASUREMENT_EXPECTED_SHA256", DEFAULT_ARTIFACT_SHA256)).strip().lower()
    if _hash(raw) != expected_hash:
        raise ValueError("vizz_measurement_artifact_stale")
    artifact = json.loads(raw.decode("utf-8"))
    if artifact.get("version") != "vizz-measurement-gate-v1":
        raise ValueError("vizz_measurement_artifact_version_invalid")
    refused = artifact.get("refused_measurement")
    invariants = artifact.get("invariants")
    if not isinstance(refused, Mapping) or not isinstance(invariants, Mapping):
        raise ValueError("vizz_measurement_artifact_shape_invalid")
    if refused.get("status") != "MEASUREMENT_REFUSED" or refused.get("execution", {}).get("triangulation_attempted") is not False:
        raise ValueError("vizz_measurement_artifact_not_refused")
    context = refused.get("context")
    if not isinstance(context, Mapping):
        raise ValueError("vizz_measurement_artifact_context_invalid")
    calibration_audit_sha256 = context.get("calibration_audit_sha256")
    calibration_provenance_ref = context.get("calibration_provenance_ref")
    if calibration_audit_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", str(calibration_audit_sha256)):
        raise ValueError("vizz_measurement_calibration_lineage_invalid")
    if calibration_provenance_ref is not None and (not isinstance(calibration_provenance_ref, str) or not calibration_provenance_ref.strip()):
        raise ValueError("vizz_measurement_calibration_lineage_invalid")
    if any(invariants.get(key) is not True for key in (
        "measurement_refused", "triangulation_not_attempted", "no_depth_result_emitted",
        "metric_depth_remains_unauthorized", "publication_remains_closed",
    )):
        raise ValueError("vizz_measurement_artifact_invariants_invalid")
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "status": "unknown_measurement_refused",
        "measurement": {
            "status": refused["status"],
            "unknown": True,
            "triangulation_attempted": False,
            "depth_result_present": False,
            "calibration_status": refused.get("context", {}).get("calibration_status"),
        },
        "reason": _text(refused.get("reason"), "measurement.reason"),
        "provenance": {
            "ref": "grammar-lab:Q-650:artifact",
            "sha256": _hash(raw),
            "source_schema": "vizz-measurement-gate-v1",
            "calibration_audit_sha256": calibration_audit_sha256,
            "calibration_provenance_ref": calibration_provenance_ref,
        },
        "next_action": "provide_physical_calibration_evidence_before_metric_measurement",
        "control": {
            "database_write": False,
            "decision_write": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
        },
    }
    validate_vizz_measurement_status(result)
    return result


def validate_vizz_measurement_status(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("vizz_measurement_status_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "status", "measurement", "reason", "provenance", "next_action", "control"}
    if set(payload) != expected or payload.get("available") is not True or payload.get("read_only") is not True or payload.get("status") != "unknown_measurement_refused":
        raise ValueError("vizz_measurement_status_fields_invalid")
    measurement = payload["measurement"]
    if measurement != {
        "status": "MEASUREMENT_REFUSED",
        "unknown": True,
        "triangulation_attempted": False,
        "depth_result_present": False,
        "calibration_status": measurement.get("calibration_status"),
    } or measurement["calibration_status"] not in {"CALIBRATION_EVIDENCE_REQUIRED", "CALIBRATION_REQUIRED"}:
        raise ValueError("vizz_measurement_status_measurement_invalid")
    _text(payload["reason"], "reason")
    provenance = payload["provenance"]
    if set(provenance) != {"ref", "sha256", "source_schema", "calibration_audit_sha256", "calibration_provenance_ref"} or provenance["ref"] != "grammar-lab:Q-650:artifact" or provenance["source_schema"] != "vizz-measurement-gate-v1" or not re.fullmatch(r"[0-9a-f]{64}", provenance["sha256"]):
        raise ValueError("vizz_measurement_status_provenance_invalid")
    if provenance["calibration_audit_sha256"] is not None and not re.fullmatch(r"[0-9a-f]{64}", provenance["calibration_audit_sha256"]):
        raise ValueError("vizz_measurement_calibration_lineage_invalid")
    if provenance["calibration_provenance_ref"] is not None and (not isinstance(provenance["calibration_provenance_ref"], str) or not provenance["calibration_provenance_ref"].strip()):
        raise ValueError("vizz_measurement_calibration_lineage_invalid")
    if payload["next_action"] != "provide_physical_calibration_evidence_before_metric_measurement":
        raise ValueError("vizz_measurement_status_next_action_invalid")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "selection_effect": "none",
        "promotion": "none",
        "publication": False,
    }:
        raise ValueError("vizz_measurement_status_control_invalid")
    return True


def build_vizz_measurement_revision(
    artifact_path: str | Path,
    *,
    expected_sha256: str,
    previous_sha256: str,
) -> dict[str, Any]:
    """Accept a new artifact only when its explicit lineage points backward."""
    path = Path(artifact_path).expanduser()
    raw = path.read_bytes()
    current_sha256 = _hash(raw)
    if current_sha256 != expected_sha256.strip().lower():
        raise ValueError("vizz_measurement_artifact_stale")
    artifact = json.loads(raw.decode("utf-8"))
    lineage = artifact.get("lineage")
    if not isinstance(lineage, Mapping) or not isinstance(lineage.get("revision_id"), str) or not lineage["revision_id"].strip() or lineage.get("previous_artifact_sha256") != previous_sha256.strip().lower():
        raise ValueError("vizz_measurement_lineage_invalid")
    if lineage["previous_artifact_sha256"] == current_sha256:
        raise ValueError("vizz_measurement_lineage_must_change_hash")
    current = build_vizz_measurement_status(path, expected_sha256=current_sha256)
    result = {
        "schema": REVISION_SCHEMA,
        "algorithm_version": REVISION_ALGORITHM_VERSION,
        "status": "revision_accepted",
        "revision": {
            "revision_id": lineage["revision_id"].strip(),
            "previous_artifact_sha256": lineage["previous_artifact_sha256"],
            "current_artifact_sha256": current_sha256,
        },
        "current": {
            "status": current["status"],
            "unknown": current["measurement"]["unknown"],
            "next_action": current["next_action"],
            "source_ref": current["provenance"]["ref"],
        },
        "control": current["control"],
    }
    validate_vizz_measurement_revision(result)
    return result


def validate_vizz_measurement_revision(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != REVISION_SCHEMA or payload.get("algorithm_version") != REVISION_ALGORITHM_VERSION or payload.get("status") != "revision_accepted":
        raise ValueError("vizz_measurement_revision_header_invalid")
    if set(payload) != {"schema", "algorithm_version", "status", "revision", "current", "control"}:
        raise ValueError("vizz_measurement_revision_fields_invalid")
    revision = payload["revision"]
    if set(revision) != {"revision_id", "previous_artifact_sha256", "current_artifact_sha256"} or not isinstance(revision["revision_id"], str) or not revision["revision_id"].strip() or not re.fullmatch(r"[0-9a-f]{64}", revision["previous_artifact_sha256"]) or not re.fullmatch(r"[0-9a-f]{64}", revision["current_artifact_sha256"]) or revision["previous_artifact_sha256"] == revision["current_artifact_sha256"]:
        raise ValueError("vizz_measurement_revision_lineage_invalid")
    current = payload["current"]
    if current != {
        "status": "unknown_measurement_refused",
        "unknown": True,
        "next_action": "provide_physical_calibration_evidence_before_metric_measurement",
        "source_ref": "grammar-lab:Q-650:artifact",
    }:
        raise ValueError("vizz_measurement_revision_current_invalid")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "selection_effect": "none",
        "promotion": "none",
        "publication": False,
    }:
        raise ValueError("vizz_measurement_revision_control_invalid")
    return True


__all__ = ["ALGORITHM_VERSION", "REVISION_ALGORITHM_VERSION", "REVISION_SCHEMA", "SCHEMA", "build_vizz_measurement_revision", "build_vizz_measurement_status", "validate_vizz_measurement_revision", "validate_vizz_measurement_status"]
