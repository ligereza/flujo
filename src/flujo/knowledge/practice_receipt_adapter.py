"""Adapt the bounded C04-C06 receipts into technical practice evidence.

The adapter is pure: callers supply three already-loaded receipts plus an
explicit binding packet.  It never reads paths, resolves names or hashes, or
promotes a technical event into authorship, publication or artistic truth.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json as _stable_json

from .project_ir import SCHEMA as PROJECT_IR_SCHEMA, validate_project_ir


SCHEMA = "mak-practice-receipt-evidence-v1"
BINDINGS_SCHEMA = "mak-practice-receipt-bindings-v1"
ALGORITHM_VERSION = "practice-receipt-adapter-1"

C04_SCHEMA = "mak-cycle-c04-real-evidence-v1"
C05_SCHEMA = "mak-cycle-c05-export-witness-v1"
C06_SCHEMA = "mak-cycle-c06-export-graph-v1"

REQUIRED_C05_CHECKS = (
    "source_hash_matches_native_snapshot",
    "script_and_marker_agree",
    "marker_target_matches_output",
    "source_contains_exported_objects",
    "output_contains_exported_objects",
    "output_is_blender_glb",
    "output_after_script_and_marker",
)

FORBIDDEN_INFERENCES = (
    "artistic_authorship",
    "artwork_identity",
    "artistic_intent",
    "artistic_quality",
    "final_delivery",
    "public_exhibition",
    "publication",
    "submission",
    "absence_of_later_modification",
)


class PracticeReceiptAdapterError(ValueError):
    """Raised when receipts or explicit bindings fail closed."""


def _copy_object(value: Any, label: str) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    if not isinstance(copied, Mapping):
        raise PracticeReceiptAdapterError(f"{label}_not_object")
    try:
        _stable_json(copied)
    except (TypeError, ValueError) as error:
        raise PracticeReceiptAdapterError(f"{label}_not_json:{error}") from error
    return dict(copied)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _refs(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return sorted({item.strip() for item in value if isinstance(item, str) and item.strip()})


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PracticeReceiptAdapterError(f"{label}_missing")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PracticeReceiptAdapterError(code)


def _validate_c04(receipt: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    _require(receipt.get("schema") == C04_SCHEMA, "c04_schema_invalid")
    _require(receipt.get("status") == "observed", "c04_status_not_observed")
    evaluation = _object(receipt.get("evaluation"), "c04_evaluation")
    claims = _object(evaluation.get("claims"), "c04_claims")
    uses = _object(claims.get("uses"), "c04_uses_claim")
    output_role = _object(claims.get("output_role"), "c04_output_role_claim")
    limits = _object(receipt.get("limits"), "c04_limits")
    limit_role = _object(limits.get("output_role_claim"), "c04_limit_output_role_claim")
    _require(uses.get("status") == "supported", "c04_uses_not_supported")
    uses_refs = _refs(uses.get("evidence_refs"))
    _require(bool(uses_refs), "c04_uses_evidence_refs_missing")
    _require(output_role.get("status") == "unknown", "c04_output_role_not_unknown")
    _require(limit_role.get("status") == "unknown", "c04_limit_output_role_not_unknown")
    _require(limits.get("export_event_observed") is False, "c04_export_event_not_false")
    _require(evaluation.get("relations") == [], "c04_relations_not_empty")
    local_media = _object(claims.get("local_media"), "c04_local_media_claim")
    _require(local_media.get("status") == "observed", "c04_local_media_not_observed")
    media_refs = _refs(local_media.get("evidence_refs"))
    _require(bool(media_refs), "c04_local_media_evidence_refs_missing")
    return uses_refs, media_refs


def _validate_c05(receipt: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[str]]:
    _require(receipt.get("schema") == C05_SCHEMA, "c05_schema_invalid")
    policy = _object(receipt.get("read_policy"), "c05_read_policy")
    for key in ("directory_scan", "blender_opened", "scripts_executed", "inputs_written"):
        _require(policy.get(key) is False, f"c05_read_policy_{key}_not_false")
    witness = _object(receipt.get("witness"), "c05_witness")
    _require(witness.get("status") == "supported", "c05_witness_not_supported")
    _require(witness.get("event_type") == "export", "c05_event_type_not_export")
    _require(bool(_text(witness.get("source_ref"))), "c05_source_ref_missing")
    _require(bool(_text(witness.get("target_ref"))), "c05_target_ref_missing")
    refs = _refs(witness.get("evidence_refs"))
    _require(bool(refs), "c05_evidence_refs_missing")
    checks = _object(witness.get("checks"), "c05_checks")
    for name in REQUIRED_C05_CHECKS:
        check = _object(checks.get(name), f"c05_check_{name}")
        _require(check.get("status") == "pass", f"c05_check_failed:{name}")
    return witness, refs


def _validate_c06(
    receipt: Mapping[str, Any], c05_witness: Mapping[str, Any], c05_refs: list[str]
) -> Mapping[str, Any]:
    _require(receipt.get("schema") == C06_SCHEMA, "c06_schema_invalid")
    policy = _object(receipt.get("decision_policy"), "c06_decision_policy")
    _require(policy.get("filesystem_scan") is False, "c06_filesystem_scan_not_false")
    _require(policy.get("hidden_truth") is False, "c06_hidden_truth_not_false")
    _require(policy.get("status_override") is False, "c06_status_override_not_false")
    claim = _object(receipt.get("claim"), "c06_claim")
    _require(claim.get("status") == "supported", "c06_claim_not_supported")
    _require(_refs(claim.get("evidence_refs")) == c05_refs, "c05_c06_claim_refs_conflict")
    edges = receipt.get("edges")
    _require(isinstance(edges, list) and len(edges) == 1, "c06_expected_one_edge")
    edge = _object(edges[0], "c06_edge")
    _require(edge.get("relation") == "EXPORTS_TO", "c06_relation_invalid")
    _require(edge.get("status") == "supported", "c06_edge_not_supported")
    _require(edge.get("source_ref") == c05_witness.get("source_ref"), "c05_c06_source_conflict")
    _require(edge.get("target_ref") == c05_witness.get("target_ref"), "c05_c06_target_conflict")
    _require(_refs(edge.get("evidence_refs")) == c05_refs, "c05_c06_edge_refs_conflict")
    return edge


def _binding(
    packet: Mapping[str, Any], key: str, expected_receipt_ref: str
) -> dict[str, str]:
    bindings = _object(packet.get("bindings"), "bindings")
    row = _object(bindings.get(key), f"binding_{key}")
    receipt_ref = _text(row.get("receipt_ref"))
    artifact_ref = _text(row.get("artifact_ref"))
    _require(receipt_ref == expected_receipt_ref, f"binding_{key}_receipt_ref_mismatch")
    _require(bool(artifact_ref), f"binding_{key}_artifact_ref_missing")
    return {"binding_key": key, "receipt_ref": receipt_ref, "artifact_ref": artifact_ref}


def _predicate(
    *, predicate_id: str, predicate: str, status: str, subject_ref: str,
    evidence_refs: list[str], source_receipts: list[str], object_ref: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "predicate_id": predicate_id,
        "predicate": predicate,
        "status": status,
        "subject_ref": subject_ref,
        "evidence_refs": evidence_refs,
        "source_receipts": source_receipts,
        "requirement_ids": [],
    }
    if object_ref is not None:
        row["object_ref"] = object_ref
    if details:
        row["details"] = copy.deepcopy(dict(details))
    return row


def adapt_practice_receipts(
    c04: Any, c05: Any, c06: Any, bindings: Any
) -> dict[str, Any]:
    """Return deterministic technical evidence from explicitly bound receipts."""
    c04_record = _copy_object(c04, "c04")
    c05_record = _copy_object(c05, "c05")
    c06_record = _copy_object(c06, "c06")
    binding_packet = _copy_object(bindings, "bindings_packet")
    _require(binding_packet.get("schema") == BINDINGS_SCHEMA, "bindings_schema_invalid")
    archive_id = _text(binding_packet.get("archive_id"))
    _require(bool(archive_id), "bindings_archive_id_missing")
    _require(c04_record.get("archive_id") == archive_id, "c04_bindings_archive_id_mismatch")

    c04_uses_refs, c04_media_refs = _validate_c04(c04_record)
    c05_witness, c05_refs = _validate_c05(c05_record)
    c06_edge = _validate_c06(c06_record, c05_witness, c05_refs)

    expected = {
        "c04_aep": "C02/aep_endpoint/observation.json#/input",
        "c04_media": "C04/media_observer/real-observation",
        "c05_source": _text(c05_witness.get("source_ref")),
        "c05_target": _text(c05_witness.get("target_ref")),
    }
    lineage = [_binding(binding_packet, key, expected[key]) for key in sorted(expected)]
    bound = {row["binding_key"]: row["artifact_ref"] for row in lineage}

    artifact = _object(c04_record.get("artifact"), "c04_artifact")
    media_details = {
        "bytes": artifact.get("bytes"),
        "container": copy.deepcopy(artifact.get("container")),
        "dimensions": copy.deepcopy(artifact.get("dimensions")),
        "duration_seconds": artifact.get("duration_seconds"),
        "video_codec": artifact.get("video_codec"),
    }
    predicates = [
        _predicate(
            predicate_id="c04:local_media_observed", predicate="LOCAL_MEDIA_OBSERVED",
            status="observed", subject_ref=bound["c04_media"],
            evidence_refs=c04_media_refs, source_receipts=[C04_SCHEMA], details=media_details,
        ),
        _predicate(
            predicate_id="c04:aep_uses_media", predicate="USES", status="supported",
            subject_ref=bound["c04_aep"], object_ref=bound["c04_media"],
            evidence_refs=c04_uses_refs, source_receipts=[C04_SCHEMA],
        ),
        _predicate(
            predicate_id="c04:output_role", predicate="OUTPUT_ROLE", status="unknown",
            subject_ref=bound["c04_media"], evidence_refs=[], source_receipts=[C04_SCHEMA],
            details={"reason": "no_explicit_export_event_with_evidence_refs"},
        ),
        _predicate(
            predicate_id="c05:export_event", predicate="EXPORT_EVENT", status="supported",
            subject_ref=bound["c05_source"], object_ref=bound["c05_target"],
            evidence_refs=c05_refs, source_receipts=[C05_SCHEMA],
        ),
        _predicate(
            predicate_id="c06:exports_to", predicate="EXPORTS_TO", status="supported",
            subject_ref=bound["c05_source"], object_ref=bound["c05_target"],
            evidence_refs=c05_refs, source_receipts=[C05_SCHEMA, C06_SCHEMA],
        ),
    ]

    evidence = [
        {
            "evidence_id": row["predicate_id"],
            "kind": "technical_receipt",
            "claim": row["predicate"],
            "status": row["status"],
            "subject_ref": row["subject_ref"],
            **({"object_ref": row["object_ref"]} if "object_ref" in row else {}),
            "evidence_refs": row["evidence_refs"],
            "requirement_ids": [],
            "claim_limit": "technical predicate only",
        }
        for row in predicates
    ]
    relations = [
        {
            "relation_id": row["predicate_id"],
            "subject": row["subject_ref"],
            "predicate": row["predicate"],
            "object": row["object_ref"],
            "status": row["status"],
            "evidence_refs": row["evidence_refs"],
        }
        for row in predicates
        if "object_ref" in row
    ]
    gaps = [
        {"code": "c04_output_role_unknown", "artifact_ref": bound["c04_media"]},
        {"code": "artwork_identity_unverified"},
        {"code": "artistic_authorship_unverified"},
        {"code": "final_delivery_unverified", "artifact_ref": bound["c05_target"]},
        {"code": "publication_unverified", "artifact_ref": bound["c05_target"]},
        {"code": "public_exhibition_unverified", "artifact_ref": bound["c05_target"]},
        {"code": "post_export_modification_unknown", "artifact_ref": bound["c05_target"]},
    ]
    gaps.sort(key=_stable_json)

    projection = {
        "bound_artifact_refs": sorted(set(bound.values())),
        "evidence": evidence,
        "relations": relations,
        "media": [{
            "value": "local_video_observed",
            "status": "observed",
            "artifact_refs": [bound["c04_media"]],
            "evidence_refs": c04_media_refs,
            "requirement_ids": [],
        }],
        "capabilities": [],
        "temporality": [],
        "manifestations": [],
        "resources": [{
            "value": "glb_export_artifact_observed",
            "status": "supported",
            "artifact_refs": [bound["c05_target"]],
            "evidence_refs": c05_refs,
            "requirement_ids": [],
        }],
        "gaps": gaps,
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "archive_id": archive_id,
        "source_receipts": [C04_SCHEMA, C05_SCHEMA, C06_SCHEMA],
        "lineage": lineage,
        "predicates": predicates,
        "project_ir_practice_projection": projection,
        "gaps": gaps,
        "forbidden_inferences": list(FORBIDDEN_INFERENCES),
        "policy": {
            "pure": True,
            "deterministic": True,
            "source_rescan": False,
            "filesystem_resolution": False,
            "basename_resolution": False,
            "hash_resolution": False,
            "similarity_resolution": False,
            "source_mutation": False,
        },
    }
    result["evidence_hash"] = _hash(result)
    errors = validate_practice_receipt_evidence(result)
    if errors:
        raise PracticeReceiptAdapterError("output_invalid:" + ",".join(errors))
    return result


def validate_practice_receipt_evidence(value: Any) -> list[str]:
    """Validate an emitted adapter packet without repairing it."""
    if not isinstance(value, Mapping):
        return ["evidence_not_object"]
    errors: list[str] = []
    required = {
        "schema", "algorithm_version", "archive_id", "source_receipts", "lineage",
        "predicates", "project_ir_practice_projection", "gaps", "forbidden_inferences",
        "policy", "evidence_hash",
    }
    errors.extend("missing_" + key for key in sorted(required - set(value)))
    if value.get("schema") != SCHEMA:
        errors.append("bad_schema")
    if value.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append("bad_algorithm_version")
    if not _text(value.get("archive_id")):
        errors.append("archive_id_missing")
    lineage = value.get("lineage")
    if not isinstance(lineage, list) or len(lineage) != 4:
        errors.append("lineage_invalid")
    else:
        keys = []
        for row in lineage:
            if not isinstance(row, Mapping) or not _text(row.get("artifact_ref")) or not _text(row.get("receipt_ref")):
                errors.append("lineage_row_invalid")
                continue
            keys.append(row.get("binding_key"))
        if keys != sorted({"c04_aep", "c04_media", "c05_source", "c05_target"}):
            errors.append("lineage_binding_keys_invalid")
    predicates = value.get("predicates")
    if not isinstance(predicates, list) or len(predicates) != 5:
        errors.append("predicates_invalid")
    else:
        output_roles = [row for row in predicates if isinstance(row, Mapping) and row.get("predicate") == "OUTPUT_ROLE"]
        if len(output_roles) != 1 or output_roles[0].get("status") != "unknown" or output_roles[0].get("evidence_refs") != []:
            errors.append("output_role_not_unknown")
        for row in predicates:
            if not isinstance(row, Mapping) or not _text(row.get("subject_ref")):
                errors.append("predicate_binding_missing")
            elif not isinstance(row.get("evidence_refs"), list):
                errors.append("predicate_evidence_refs_invalid")
    forbidden = value.get("forbidden_inferences")
    if forbidden != list(FORBIDDEN_INFERENCES):
        errors.append("forbidden_inferences_invalid")
    policy = value.get("policy")
    if not isinstance(policy, Mapping) or any(policy.get(key) is not False for key in (
        "source_rescan", "filesystem_resolution", "basename_resolution", "hash_resolution",
        "similarity_resolution", "source_mutation",
    )):
        errors.append("policy_invalid")
    if isinstance(value.get("evidence_hash"), str):
        body = dict(value)
        body.pop("evidence_hash", None)
        try:
            if value["evidence_hash"] != _hash(body):
                errors.append("evidence_hash_mismatch")
        except (TypeError, ValueError):
            errors.append("evidence_hash_unserializable")
    else:
        errors.append("evidence_hash_invalid")
    return sorted(set(errors))


def _append_unique(target: list[Any], rows: Sequence[Any]) -> None:
    known = {_stable_json(row) for row in target}
    for row in rows:
        encoded = _stable_json(row)
        if encoded not in known:
            target.append(copy.deepcopy(row))
            known.add(encoded)
    target.sort(key=_stable_json)


def apply_practice_receipt_evidence_to_project_ir(
    project_ir_bundle: Any, evidence_packet: Any,
) -> dict[str, Any]:
    """Attach bounded receipt rows to the records that own their exact refs.

    This is an additive projection only. Every bound artifact must already
    resolve to exactly one Project IR record; no unit, project, or identity is
    created by the adapter.
    """
    bundle = _copy_object(project_ir_bundle, "project_ir_bundle")
    packet = _copy_object(evidence_packet, "evidence_packet")
    errors = validate_practice_receipt_evidence(packet)
    if errors:
        raise PracticeReceiptAdapterError("evidence_invalid:" + ",".join(errors))
    _require(bundle.get("schema") == "mak-archive-project-ir-bundle-v1", "project_ir_bundle_schema_invalid")
    _require(bundle.get("target_project_ir_schema") == PROJECT_IR_SCHEMA, "project_ir_target_schema_invalid")
    records = bundle.get("records")
    _require(isinstance(records, list), "project_ir_records_invalid")

    owners: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        _require(isinstance(record, Mapping), f"project_ir_record_invalid:{index}")
        for artifact in record.get("artifacts", []) if isinstance(record.get("artifacts"), list) else []:
            if not isinstance(artifact, Mapping):
                continue
            ref = _text(artifact.get("artifact_ref"))
            if ref:
                owners.setdefault(ref, []).append(index)
    projection = _object(packet.get("project_ir_practice_projection"), "practice_projection")
    bound_refs = _refs(projection.get("bound_artifact_refs"))
    for ref in bound_refs:
        count = len(owners.get(ref, []))
        _require(count == 1, f"bound_artifact_owner_count:{ref}:{count}")

    touched: set[int] = set()

    def owner_for(ref: Any) -> int:
        text = _text(ref)
        _require(text in owners and len(owners[text]) == 1, f"artifact_owner_unresolved:{text}")
        touched.add(owners[text][0])
        return owners[text][0]

    for key in ("evidence", "relations"):
        rows = projection.get(key)
        _require(isinstance(rows, list), f"practice_projection_{key}_invalid")
        for row in rows:
            _require(isinstance(row, Mapping), f"practice_projection_{key}_row_invalid")
            index = owner_for(row.get("subject_ref") if key == "evidence" else row.get("subject"))
            target = records[index].setdefault(key, [])
            _require(isinstance(target, list), f"project_ir_{key}_invalid:{index}")
            _append_unique(target, [row])

    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        rows = projection.get(dimension)
        _require(isinstance(rows, list), f"practice_projection_{dimension}_invalid")
        for row in rows:
            _require(isinstance(row, Mapping), f"practice_projection_{dimension}_row_invalid")
            refs = _refs(row.get("artifact_refs"))
            _require(bool(refs), f"practice_projection_{dimension}_artifact_refs_missing")
            for index in sorted({owner_for(ref) for ref in refs}):
                target = records[index].setdefault(dimension, [])
                _require(isinstance(target, list), f"project_ir_{dimension}_invalid:{index}")
                _append_unique(target, [row])

    gap_rows = projection.get("gaps")
    _require(isinstance(gap_rows, list), "practice_projection_gaps_invalid")
    global_gaps: list[Mapping[str, Any]] = []
    for row in gap_rows:
        _require(isinstance(row, Mapping), "practice_projection_gap_row_invalid")
        ref = _text(row.get("artifact_ref"))
        if ref:
            index = owner_for(ref)
            target = records[index].setdefault("gaps", [])
            _require(isinstance(target, list), f"project_ir_gaps_invalid:{index}")
            _append_unique(target, [row])
        else:
            global_gaps.append(row)
    for index in sorted(touched):
        target = records[index].setdefault("gaps", [])
        _require(isinstance(target, list), f"project_ir_gaps_invalid:{index}")
        _append_unique(target, global_gaps)
        record_errors = validate_project_ir(records[index])
        _require(not record_errors, f"enriched_project_ir_invalid:{index}:{','.join(record_errors)}")

    bundle["practice_receipt_evidence_hash"] = packet["evidence_hash"]
    bundle["practice_receipt_enrichment"] = {
        "mode": "additive_exact_artifact_binding",
        "records_touched": len(touched),
        "bound_artifact_refs": bound_refs,
        "promotion": "none",
    }
    return bundle


def serialize_practice_receipt_evidence(value: Mapping[str, Any]) -> str:
    errors = validate_practice_receipt_evidence(value)
    if errors:
        raise PracticeReceiptAdapterError("evidence_invalid:" + ",".join(errors))
    return _stable_json(value)


__all__ = [
    "ALGORITHM_VERSION", "BINDINGS_SCHEMA", "FORBIDDEN_INFERENCES", "SCHEMA",
    "PracticeReceiptAdapterError", "adapt_practice_receipts",
    "apply_practice_receipt_evidence_to_project_ir",
    "serialize_practice_receipt_evidence", "validate_practice_receipt_evidence",
]
