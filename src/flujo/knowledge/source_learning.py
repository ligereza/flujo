"""Traceable source-memory ingestion for MAK.

The bridge joins selected historical messages with later research artifacts
without copying either source tree.  It verifies file and message hashes,
preserves epistemic classes, and can record only the ingestion outcome in the
existing Project IR learning ledger.  It does not validate mathematical truth.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._io_helpers import sha256_file as _sha256_file
from .learning_policy import record_verified_result
from .project_ir import LearningStore, build_project_ir, format_family, media_type, stable_json
from .project_router import route_project


CASE_SCHEMA = "mak-source-learning-case-v1"
VERIFICATION_SCHEMA = "mak-source-learning-verification-v1"
TOOL_ID = "source_learning_bridge"

EPISTEMIC_CLASSES = {
    "user_hypothesis",
    "model_output",
    "audited_result",
    "synthesis_candidate",
    "operational_guardrail",
    "non_claim",
}
EPISTEMIC_STATUSES = {
    "candidate",
    "unverified",
    "supported_by_local_audit",
    "active",
    "excluded",
}
MESSAGE_CLASSES = {"human": "user_hypothesis", "assistant": "model_output"}
REQUIRED_NON_CLAIMS = {"p_equals_np_proven", "handwritten_argument_refuted"}
CLASS_STATUS_CONTRACT = {
    "user_hypothesis": "candidate",
    "model_output": "unverified",
    "audited_result": "supported_by_local_audit",
    "synthesis_candidate": "candidate",
    "operational_guardrail": "active",
    "non_claim": "excluded",
}


class SourceLearningError(ValueError):
    """Invalid or unverifiable source-learning case."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceLearningError(f"json_unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise SourceLearningError(f"json_not_object: {path}")
    return value


def load_case(case_path: str | Path) -> dict[str, Any]:
    """Load one source-learning case without mutating its source or ledger."""
    return _load_object(Path(case_path).expanduser())


def validate_case(case: Mapping[str, Any]) -> list[str]:
    """Validate structure, references and epistemic boundaries."""
    errors: list[str] = []
    if case.get("schema") != CASE_SCHEMA:
        errors.append("bad_schema")
    for key in ("case_id", "title", "objective"):
        if not str(case.get(key) or "").strip():
            errors.append(f"missing_{key}")

    source_sets = case.get("source_sets")
    artifacts = case.get("source_artifacts")
    messages = case.get("message_refs")
    findings = case.get("findings")
    units = case.get("learning_units")
    non_claims = case.get("non_claims")
    for key, value in (
        ("source_sets", source_sets),
        ("source_artifacts", artifacts),
        ("message_refs", messages),
        ("findings", findings),
        ("learning_units", units),
        ("non_claims", non_claims),
    ):
        if not isinstance(value, list) or not value:
            errors.append(f"{key}_missing_or_empty")

    source_roots: dict[str, Path] = {}
    for index, item in enumerate(source_sets if isinstance(source_sets, list) else []):
        prefix = f"source_sets[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        source_id = str(item.get("source_id") or "")
        root = Path(str(item.get("root") or ""))
        if not source_id or source_id in source_roots:
            errors.append(prefix + "_bad_or_duplicate_id")
        if not root.is_absolute():
            errors.append(prefix + "_root_not_absolute")
        if not str(item.get("role") or "").strip() or not str(item.get("selection_policy") or "").strip():
            errors.append(prefix + "_missing_role_or_selection_policy")
        source_roots[source_id] = root

    artifact_ids: set[str] = set()
    conversation_exports: set[str] = set()
    for index, item in enumerate(artifacts if isinstance(artifacts, list) else []):
        prefix = f"source_artifacts[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        artifact_id = str(item.get("artifact_id") or "")
        if not artifact_id or artifact_id in artifact_ids:
            errors.append(prefix + "_bad_or_duplicate_id")
        artifact_ids.add(artifact_id)
        path = str(item.get("path") or "")
        source_id = str(item.get("source_set") or "")
        digest = str(item.get("sha256") or "")
        if not path or not Path(path).is_absolute():
            errors.append(prefix + "_path_not_absolute")
        if len(digest) != 64:
            errors.append(prefix + "_bad_sha256")
        if source_id not in source_roots:
            errors.append(prefix + "_bad_source_set")
        elif path:
            try:
                Path(path).resolve().relative_to(source_roots[source_id].resolve())
            except ValueError:
                errors.append(prefix + "_outside_source_root")
        if item.get("kind") == "conversation_export":
            conversation_exports.add(artifact_id)

    ref_ids = set(artifact_ids)
    for index, item in enumerate(messages if isinstance(messages, list) else []):
        prefix = f"message_refs[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        ref_id = str(item.get("ref_id") or "")
        if not ref_id or ref_id in ref_ids:
            errors.append(prefix + "_bad_or_duplicate_id")
        ref_ids.add(ref_id)
        if str(item.get("artifact_id") or "") not in conversation_exports:
            errors.append(prefix + "_bad_conversation_artifact")
        sender = str(item.get("sender") or "")
        expected_class = MESSAGE_CLASSES.get(sender)
        if not expected_class or item.get("epistemic_class") != expected_class:
            errors.append(prefix + "_sender_class_mismatch")
        if not str(item.get("conversation_id") or "") or not str(item.get("message_id") or ""):
            errors.append(prefix + "_missing_identity")
        if len(str(item.get("text_sha256") or "")) != 64:
            errors.append(prefix + "_bad_text_sha256")

    finding_ids: set[str] = set()
    for index, item in enumerate(findings if isinstance(findings, list) else []):
        prefix = f"findings[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        finding_id = str(item.get("finding_id") or "")
        if not finding_id or finding_id in finding_ids:
            errors.append(prefix + "_bad_or_duplicate_id")
        finding_ids.add(finding_id)
        epistemic_class = str(item.get("epistemic_class") or "")
        status = str(item.get("status") or "")
        if epistemic_class not in EPISTEMIC_CLASSES:
            errors.append(prefix + "_bad_epistemic_class")
        if status not in EPISTEMIC_STATUSES:
            errors.append(prefix + "_bad_status")
        if CLASS_STATUS_CONTRACT.get(epistemic_class) != status:
            errors.append(prefix + "_class_status_mismatch")
        evidence_refs = item.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            errors.append(prefix + "_missing_evidence_refs")
        elif any(str(ref) not in ref_ids for ref in evidence_refs):
            errors.append(prefix + "_unknown_evidence_ref")

    available_refs = ref_ids | finding_ids
    for index, item in enumerate(units if isinstance(units, list) else []):
        prefix = f"learning_units[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        for key in ("unit_id", "lesson", "action", "guardrail", "status"):
            if not str(item.get(key) or "").strip():
                errors.append(prefix + f"_missing_{key}")
        if item.get("status") not in {"candidate", "active"}:
            errors.append(prefix + "_bad_status")
        evidence_refs = item.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            errors.append(prefix + "_missing_evidence_refs")
        elif any(str(ref) not in available_refs for ref in evidence_refs):
            errors.append(prefix + "_unknown_evidence_ref")

    ladder = case.get("verification_ladder")
    if not isinstance(ladder, list) or not ladder:
        errors.append("verification_ladder_missing_or_empty")
    else:
        orders: list[int] = []
        for index, item in enumerate(ladder):
            prefix = f"verification_ladder[{index}]"
            if not isinstance(item, Mapping):
                errors.append(prefix + "_not_object")
                continue
            if not isinstance(item.get("order"), int) or int(item["order"]) < 1:
                errors.append(prefix + "_bad_order")
            else:
                orders.append(int(item["order"]))
            if not str(item.get("gate") or "").strip() or not str(item.get("failure_action") or "").strip():
                errors.append(prefix + "_missing_gate_or_failure_action")
        if orders != list(range(1, len(ladder) + 1)):
            errors.append("verification_ladder_not_contiguous")

    non_claim_rows = non_claims if isinstance(non_claims, list) else []
    for index, item in enumerate(non_claim_rows):
        prefix = f"non_claims[{index}]"
        if not isinstance(item, Mapping):
            errors.append(prefix + "_not_object")
            continue
        if not all(str(item.get(key) or "").strip() for key in ("claim_id", "statement", "reason")):
            errors.append(prefix + "_missing_fields")
        if item.get("status") != "excluded":
            errors.append(prefix + "_not_excluded")
    excluded = {
        str(item.get("claim_id") or "")
        for item in non_claim_rows if isinstance(item, Mapping)
        if item.get("status") == "excluded"
    }
    for claim_id in sorted(REQUIRED_NON_CLAIMS - excluded):
        errors.append("required_non_claim_missing:" + claim_id)
    return errors


def _conversation_index(path: Path) -> dict[tuple[str, str], Mapping[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceLearningError(f"conversation_export_unreadable: {path}") from exc
    if not isinstance(value, list):
        raise SourceLearningError(f"conversation_export_not_list: {path}")
    output: dict[tuple[str, str], Mapping[str, Any]] = {}
    for conversation in value:
        if not isinstance(conversation, Mapping):
            continue
        conversation_id = str(conversation.get("uuid") or "")
        messages = conversation.get("chat_messages")
        if not conversation_id or not isinstance(messages, list):
            continue
        for message in messages:
            if isinstance(message, Mapping) and message.get("uuid"):
                output[(conversation_id, str(message["uuid"]))] = message
    return output


def verify_case(case_path: str | Path) -> dict[str, Any]:
    """Verify hashes, selected messages and claim boundaries, read-only."""
    path = Path(case_path).expanduser().resolve()
    case = load_case(path)
    structural_errors = validate_case(case)
    checks: list[dict[str, Any]] = []
    for item in case.get("source_sets", []) if isinstance(case.get("source_sets"), list) else []:
        if not isinstance(item, Mapping):
            continue
        root = Path(str(item.get("root") or "")).expanduser()
        checks.append({
            "check": "source_root_present",
            "ref_id": str(item.get("source_id") or ""),
            "status": "passed" if root.is_dir() else "failed",
            "root": str(root),
        })
    artifact_paths: dict[str, Path] = {}
    for item in case.get("source_artifacts", []) if isinstance(case.get("source_artifacts"), list) else []:
        if not isinstance(item, Mapping):
            continue
        artifact_id = str(item.get("artifact_id") or "")
        source_path = Path(str(item.get("path") or "")).expanduser()
        artifact_paths[artifact_id] = source_path
        actual = _sha256_file(source_path) if source_path.is_file() else ""
        expected = str(item.get("sha256") or "")
        checks.append({
            "check": "source_artifact_sha256",
            "ref_id": artifact_id,
            "status": "passed" if actual and actual == expected else "failed",
            "path": str(source_path),
            "expected_sha256": expected,
            "actual_sha256": actual,
        })

    indexes: dict[str, dict[tuple[str, str], Mapping[str, Any]]] = {}
    for item in case.get("message_refs", []) if isinstance(case.get("message_refs"), list) else []:
        if not isinstance(item, Mapping):
            continue
        artifact_id = str(item.get("artifact_id") or "")
        source_path = artifact_paths.get(artifact_id)
        if source_path and source_path.is_file() and artifact_id not in indexes:
            try:
                indexes[artifact_id] = _conversation_index(source_path)
            except SourceLearningError:
                indexes[artifact_id] = {}
        key = (str(item.get("conversation_id") or ""), str(item.get("message_id") or ""))
        message = indexes.get(artifact_id, {}).get(key)
        actual_hash = ""
        actual_sender = ""
        if message:
            text = str(message.get("text") or "")
            actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            actual_sender = str(message.get("sender") or "")
        passed = bool(
            message
            and actual_hash == str(item.get("text_sha256") or "")
            and actual_sender == str(item.get("sender") or "")
        )
        checks.append({
            "check": "conversation_message_sha256",
            "ref_id": str(item.get("ref_id") or ""),
            "status": "passed" if passed else "failed",
            "conversation_id": key[0],
            "message_id": key[1],
            "expected_sha256": str(item.get("text_sha256") or ""),
            "actual_sha256": actual_hash,
            "expected_sender": str(item.get("sender") or ""),
            "actual_sender": actual_sender,
        })

    checks.append({
        "check": "epistemic_contract",
        "status": "passed" if not structural_errors else "failed",
        "errors": structural_errors,
    })
    status = "passed" if all(item["status"] == "passed" for item in checks) else "failed"
    fingerprint = hashlib.sha256(stable_json(case).encode("utf-8")).hexdigest()
    return {
        "schema": VERIFICATION_SCHEMA,
        "case_id": str(case.get("case_id") or ""),
        "case_path": str(path),
        "case_fingerprint": fingerprint,
        "status": status,
        "scope": "source_integrity_and_epistemic_contract_only",
        "mathematical_truth_validated": False,
        "counts": {
            "source_sets": len(case.get("source_sets", [])) if isinstance(case.get("source_sets"), list) else 0,
            "source_artifacts": len(case.get("source_artifacts", [])) if isinstance(case.get("source_artifacts"), list) else 0,
            "message_refs": len(case.get("message_refs", [])) if isinstance(case.get("message_refs"), list) else 0,
            "findings": len(case.get("findings", [])) if isinstance(case.get("findings"), list) else 0,
            "learning_units": len(case.get("learning_units", [])) if isinstance(case.get("learning_units"), list) else 0,
        },
        "checks": checks,
    }


def build_learning_project(case_path: str | Path, verification: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt one passed case to active Project IR while retaining claim scope."""
    if verification.get("schema") != VERIFICATION_SCHEMA or verification.get("status") != "passed":
        raise SourceLearningError("case_verification_not_passed")
    path = Path(case_path).expanduser().resolve()
    case = load_case(path)
    artifacts: list[dict[str, Any]] = []
    for item in case["source_artifacts"]:
        source_path = Path(str(item["path"])).expanduser()
        stat = source_path.stat()
        artifacts.append({
            "artifact_id": str(item["artifact_id"]),
            "relative_path": str(source_path),
            "name": source_path.name,
            "format_family": format_family(source_path),
            "media_type": media_type(source_path),
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": str(item["sha256"]),
            "hash_status": "full",
            "availability": "present",
            "role": str(item.get("role") or "source"),
        })
    manifest_stat = path.stat()
    artifacts.append({
        "relative_path": str(path),
        "name": path.name,
        "format_family": "data",
        "media_type": "application/json",
        "size_bytes": manifest_stat.st_size,
        "mtime_ns": manifest_stat.st_mtime_ns,
        "sha256": _sha256_file(path),
        "hash_status": "full",
        "availability": "present",
        "role": "learning_case_manifest",
    })
    project = build_project_ir(
        project_id=str(case["case_id"]),
        title=str(case["title"]),
        source_root=path.parent,
        artifacts=artifacts,
        domains=["source_memory", "mathematics"],
        purpose=str(case["objective"]),
        state="active",
        evidence=[{
            "kind": "source_learning_verification",
            "status": "verified",
            "scope": verification["scope"],
            "case_fingerprint": verification["case_fingerprint"],
            "checks_passed": len(verification["checks"]),
            "mathematical_truth_validated": False,
        }],
        unknowns=[
            "The truth value of P versus NP remains outside this ingestion verification.",
            "Candidate search heuristics require independent experiments before promotion.",
        ],
        relations=[
            {"subject": "historical_dialogue", "relation": "hypothesis_origin", "object": "research_package"},
            {"subject": "research_package", "relation": "audits_and_bounds", "object": "historical_dialogue"},
        ],
        source_kind="source_memory",
        source_ref=str(path),
    )
    project["layer"] = "cultural_research_first"
    project["source_learning"] = {
        "case_schema": CASE_SCHEMA,
        "case_fingerprint": verification["case_fingerprint"],
        "findings": list(case["findings"]),
        "learning_units": list(case["learning_units"]),
        "non_claims": list(case["non_claims"]),
        "verification_scope": verification["scope"],
    }
    return project


def ingest_case(
    case_path: str | Path,
    *,
    database: str | Path | None = None,
    record: bool = False,
) -> dict[str, Any]:
    """Verify and optionally record one case through existing MAK contracts."""
    verification = verify_case(case_path)
    result: dict[str, Any] = {"verification": verification, "recorded": False}
    if verification["status"] != "passed":
        return result
    project = build_learning_project(case_path, verification)
    decision = route_project(project)
    result["project_id"] = project["project_id"]
    result["route"] = decision
    selected = decision.get("selected") if isinstance(decision.get("selected"), Mapping) else {}
    route_passed = decision.get("decision") == "select" and selected.get("tool_id") == TOOL_ID
    result["route_contract_passed"] = route_passed
    if not record:
        return result
    if not database:
        raise SourceLearningError("record_requires_explicit_database")
    if not route_passed:
        raise SourceLearningError("source_learning_route_contract_failed")

    database_path = Path(database).expanduser()
    LearningStore(database_path).save_project(project)
    fingerprint = str(verification["case_fingerprint"])
    packet = {
        "schema": "mak-verified-result-v1",
        "project_id": project["project_id"],
        "tool_id": TOOL_ID,
        "episode_id": "episode-source-learning-" + fingerprint[:24],
        "objective": "ingest traceable source memory with explicit claim boundaries",
        "phase": "source_learning_ingestion",
        "result": {
            "status": "verified",
            "scope": verification["scope"],
            "case_fingerprint": fingerprint,
            "mathematical_truth_validated": False,
        },
        "validation": {
            "status": "passed",
            "validator": "flujo.knowledge.source_learning.verify_case",
            "checks": ["source_root_present", "source_artifact_sha256", "conversation_message_sha256", "epistemic_contract", "route_contract"],
        },
        "evidence": [
            {"kind": "case_manifest", "ref": str(Path(case_path).expanduser().resolve()), "semantic_sha256": fingerprint},
            {"kind": "verification_report", "case_fingerprint": fingerprint, "counts": verification["counts"]},
        ],
    }
    with tempfile.TemporaryDirectory(prefix="mak-source-learning-") as temp_dir:
        packet_path = Path(temp_dir) / "verified-result.json"
        packet_path.write_text(stable_json(packet), encoding="utf-8")
        episode_id = record_verified_result(database_path, packet_path)
    result["recorded"] = True
    result["episode_id"] = episode_id
    result["database"] = str(database_path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="mak-source-learning-case-v1 manifest")
    parser.add_argument("--db", type=Path, help="explicit LearningStore database")
    parser.add_argument("--record", action="store_true", help="record a verified Project IR episode")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = ingest_case(args.case, database=args.db, record=args.record)
    except (OSError, SourceLearningError, ValueError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["verification"]["status"] == "passed" and result.get("route_contract_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
