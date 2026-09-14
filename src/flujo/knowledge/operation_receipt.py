"""Read-only receipt for a bounded structural operation executed by MAK."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import required_text as _text, sha256_hex as _hash


SCHEMA = "mak-operation-receipt-v1"
ALGORITHM_VERSION = "operation-receipt-1"
DEFAULT_ARTIFACT = Path("/home/mak/work/grammar-lab-20260912/artifacts/q610_cross_version_structural_execution.json")


def build_operation_receipt(artifact_path: str | Path | None = None) -> dict[str, Any]:
    configured = str(artifact_path or os.environ.get("MAK_OPERATION_RECEIPT_ARTIFACT", "")).strip()
    path = Path(configured).expanduser() if configured else DEFAULT_ARTIFACT
    raw = path.read_bytes()
    artifact = json.loads(raw.decode("utf-8"))
    if artifact.get("version") != "cross-version-structural-execution-v1":
        raise ValueError("operation_artifact_version_invalid")
    allowed = artifact.get("allowed_operation")
    execution = artifact.get("valid_execution")
    package = artifact.get("package")
    rejections = artifact.get("rejections")
    invariants = artifact.get("invariants")
    if not all(isinstance(value, Mapping) for value in (allowed, execution, package, rejections, invariants)):
        raise ValueError("operation_artifact_shape_invalid")
    if execution.get("accepted") is not True or not isinstance(execution.get("expanded"), list):
        raise ValueError("operation_execution_invalid")
    if any(not isinstance(key, str) or not key for key in execution["expanded"]):
        raise ValueError("operation_expansion_invalid")
    required_invariants = (
        "declared_operation_accepted", "declared_expansion_exact",
        "unsupported_operation_rejected", "wrong_dialect_rejected",
        "semantic_equivalence_authorized",
    )
    if any(invariants.get(key) is not True for key in required_invariants[:-1]) or invariants.get(required_invariants[-1]) is not False:
        raise ValueError("operation_artifact_invariants_invalid")
    receipt = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "status": "executed_structural_only",
        "source": {
            "kind": "grammar_lab_q610_artifact",
            "ref": "grammar-lab:Q-610:artifact",
            "sha256": _hash(raw),
        },
        "operation": {
            "name": _text(allowed.get("operation"), "operation.name"),
            "dialect": _text(allowed.get("dialect"), "operation.dialect"),
            "expanded_keys": list(execution["expanded"]),
            "expanded_count": len(execution["expanded"]),
            "execution_reason": _text(execution.get("reason"), "operation.execution_reason"),
        },
        "provenance": {
            "library_source_ref": _text(allowed.get("library_source_ref"), "provenance.library_source_ref"),
            "evaluation_source_ref": _text(allowed.get("evaluation_source_ref"), "provenance.evaluation_source_ref"),
            "package_sha256": _text(package.get("serialized_payload_sha256"), "provenance.package_sha256"),
        },
        "rejected_attempts": [
            {"kind": "operation", "reason": _text((rejections.get("unsupported_operation") or {}).get("reason"), "rejected.operation")},
            {"kind": "dialect", "reason": _text((rejections.get("wrong_dialect") or {}).get("reason"), "rejected.dialect")},
        ],
        "control": {
            "database_write": False,
            "decision_write": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
            "semantic_equivalence_authorized": False,
        },
        "limitations": [
            "Recibo estructural local; no convierte la expansión en verdad artística ni equivalencia semántica.",
            "La superficie no escribe decisiones, selección, promoción ni publicación.",
        ],
    }
    validate_operation_receipt(receipt)
    return receipt


def validate_operation_receipt(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("operation_receipt_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "status", "source", "operation", "provenance", "rejected_attempts", "control", "limitations"}
    if set(payload) != expected or payload.get("available") is not True or payload.get("read_only") is not True or payload.get("status") != "executed_structural_only":
        raise ValueError("operation_receipt_fields_invalid")
    source = payload["source"]
    if set(source) != {"kind", "ref", "sha256"} or source["kind"] != "grammar_lab_q610_artifact" or source["ref"] != "grammar-lab:Q-610:artifact" or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("operation_receipt_source_invalid")
    operation = payload["operation"]
    if set(operation) != {"name", "dialect", "expanded_keys", "expanded_count", "execution_reason"} or operation["name"] != "expand_library_program" or operation["dialect"] != "super-mario-feature-v1" or operation["execution_reason"] != "declared_operation_executed":
        raise ValueError("operation_receipt_operation_invalid")
    if not isinstance(operation["expanded_keys"], list) or operation["expanded_count"] != len(operation["expanded_keys"]):
        raise ValueError("operation_receipt_expansion_invalid")
    provenance = payload["provenance"]
    if set(provenance) != {"library_source_ref", "evaluation_source_ref", "package_sha256"} or not all(isinstance(value, str) and value for value in provenance.values()):
        raise ValueError("operation_receipt_provenance_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", provenance["package_sha256"]):
        raise ValueError("operation_receipt_package_hash_invalid")
    rejected = payload["rejected_attempts"]
    if rejected != [{"kind": "operation", "reason": "operation_not_allowed"}, {"kind": "dialect", "reason": "dialect_not_allowed"}]:
        raise ValueError("operation_receipt_rejections_invalid")
    if payload["control"] != {"database_write": False, "decision_write": False, "selection_effect": "none", "promotion": "none", "publication": False, "semantic_equivalence_authorized": False}:
        raise ValueError("operation_receipt_control_invalid")
    if not isinstance(payload["limitations"], list) or any(not isinstance(value, str) or not value for value in payload["limitations"]):
        raise ValueError("operation_receipt_limitations_invalid")
    return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_operation_receipt", "validate_operation_receipt"]
