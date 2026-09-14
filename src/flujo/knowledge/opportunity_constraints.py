"""Compile a local opportunity evidence package into operational constraints.

The compiler is deliberately a pure boundary between preserved documentary
evidence and downstream consumers.  It does not fetch a URL, read a PDF,
write a database, decide artistic fit, or assert that a locally observed call
is currently open.  Evidence must already carry a locator; missing evidence,
unconfirmed dates and contradictions remain explicit in the output.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

from ._contract_helpers import sha256_ref as _hash, stable_json


SCHEMA = "mak-opportunity-constraints-v1"
INPUT_SCHEMA = "mak-opportunity-document-package-v1"
ALGORITHM_VERSION = "opportunity-document-to-constraints-1"

_INPUT_SCHEMAS = {
    INPUT_SCHEMA,
    "mak-opportunity-evidence-package-v1",
}
_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "title", "source",
    "input_hash", "constraints", "hard_gates", "eligibility", "dates",
    "duration", "budget", "transfer", "required_documents", "criteria",
    "evidence", "contradictions", "unknowns", "provenance", "reconciliation",
}
_CONSTRAINT_FIELDS = {
    "constraint_id", "field", "kind", "required", "value", "status",
    "evidence_refs", "locator_refs",
}
_EVIDENCE_FIELDS = {
    "evidence_id", "kind", "field", "value", "status", "confirmed",
    "locator", "weight", "label", "note",
}
_STATUS_VALUES = {"supported", "unknown", "contradicted", "not_required"}
_SOURCE_STATUS_VALUES = {
    "unknown", "observed_local", "current_verified", "expired", "ineligible",
    "contradicted", "stale",
}
_HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
_SNAKE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.:-]{0,159}$")
_CATEGORY_KINDS = {
    "hard_gate", "eligibility", "date", "duration", "budget", "transfer",
    "required_document", "criterion",
}


class OpportunityConstraintsError(ValueError):
    """Invalid evidence package or invalid deterministic constraints payload."""


def _text(value: Any, field: str, *, required: bool = True, limit: int = 500) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise OpportunityConstraintsError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise OpportunityConstraintsError(f"{field}_required")
    if len(result) > limit:
        raise OpportunityConstraintsError(f"{field}_too_long")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OpportunityConstraintsError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise OpportunityConstraintsError(f"{field}_must_be_list")
    return value


def _hash_value(value: Any, field: str) -> str:
    text = _text(value, field, limit=80)
    if not _HASH_RE.fullmatch(text):
        raise OpportunityConstraintsError(f"{field}_must_be_sha256")
    return text if text.startswith("sha256:") else "sha256:" + text.lower()


def _optional_bool(value: Any, field: str, default: bool = True) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise OpportunityConstraintsError(f"{field}_must_be_boolean")
    return value


def _sorted_unique(values: Any, field: str) -> list[str]:
    rows = _list(values, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise OpportunityConstraintsError(f"{field}_contains_invalid_ref")
    result = sorted(set(rows))
    if rows != result:
        raise OpportunityConstraintsError(f"{field}_not_sorted_unique")
    return result


def _source_material(package: Mapping[str, Any], source: Mapping[str, Any]) -> Any:
    if "content" in source:
        return source["content"]
    if "text" in source:
        return source["text"]
    if "documents" in source:
        return source["documents"]
    if "documents" in package:
        return package["documents"]
    return None


def _source(package: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(package.get("source"), "source")
    source_ref = source.get("ref", source.get("source_ref"))
    source_ref = _text(source_ref, "source.ref", limit=2000)
    source_url = source.get("url", "")
    if source_url is not None:
        source_url = _text(source_url, "source.url", required=False, limit=2000)

    material = _source_material(package, source)
    explicit_hash = source.get("sha256", source.get("source_hash"))
    content_hash = _hash(material) if material is not None else None
    if material is not None and explicit_hash is not None and source.get("hash_material") == "content":
        if _hash_value(explicit_hash, "source.sha256") != content_hash:
            raise OpportunityConstraintsError("source_hash_mismatch")
    if explicit_hash is not None:
        source_hash = _hash_value(explicit_hash, "source.sha256")
    elif content_hash is not None:
        source_hash = content_hash
    else:
        raise OpportunityConstraintsError("source_hash_missing")

    version = source.get("version", source.get("revision", "unknown"))
    version = _text(version, "source.version", limit=200) if version is not None else "unknown"
    validity_raw = source.get("validity", {})
    validity = _mapping(validity_raw, "source.validity")
    validity_status = _text(
        validity.get("status", "unknown"), "source.validity.status", limit=40
    ).casefold()
    if validity_status not in _SOURCE_STATUS_VALUES:
        raise OpportunityConstraintsError("source.validity.status_invalid")
    confirmed = _optional_bool(validity.get("confirmed"), "source.validity.confirmed", False)
    if validity_status == "current_verified" and not confirmed:
        raise OpportunityConstraintsError("source.current_verified_requires_confirmation")
    effective_from = validity.get("effective_from")
    effective_to = validity.get("effective_to")
    for field, value in (("effective_from", effective_from), ("effective_to", effective_to)):
        if value is not None:
            _text(value, f"source.validity.{field}", limit=80)
    return {
        "source_ref": source_ref,
        "source_url": source_url,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "version": version,
        "validity": {
            "status": validity_status,
            "confirmed": confirmed,
            "effective_from": effective_from,
            "effective_to": effective_to,
        },
    }


def _locator(raw: Any, source_ref: str, field: str) -> dict[str, Any]:
    locator = _mapping(raw, field)
    page = locator.get("page")
    if page is not None:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise OpportunityConstraintsError(f"{field}.page_invalid")
    locator_source = locator.get("source_ref", source_ref)
    locator_source = _text(locator_source, f"{field}.source_ref", limit=2000)
    section = locator.get("section", "")
    anchor = locator.get("anchor", "")
    quote = locator.get("quote", "")
    for name, value, limit in (
        ("section", section, 300), ("anchor", anchor, 300), ("quote", quote, 2000)
    ):
        if value is not None:
            _text(value, f"{field}.{name}", required=False, limit=limit)
    if page is None and not section and not anchor and not quote:
        raise OpportunityConstraintsError(f"{field}_needs_page_or_anchor")
    return {
        "source_ref": locator_source,
        "page": page,
        "section": section or "",
        "anchor": anchor or "",
        "quote": quote or "",
    }


def _kind(value: Any, field: str) -> str:
    result = _text(value, field, limit=80).casefold()
    if not _SNAKE_RE.fullmatch(result):
        raise OpportunityConstraintsError(f"{field}_invalid")
    return result


def _normalize_evidence(package: Mapping[str, Any], source_ref: str) -> list[dict[str, Any]]:
    raw_rows = _list(package.get("evidence", []), "evidence")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_rows):
        item = _mapping(raw, f"evidence[{index}]")
        evidence_id = item.get("evidence_id", item.get("id"))
        evidence_id = _text(evidence_id, f"evidence[{index}].evidence_id", limit=200)
        if evidence_id in seen:
            raise OpportunityConstraintsError("evidence_id_duplicate")
        seen.add(evidence_id)
        kind = _kind(item.get("kind"), f"evidence[{index}].kind")
        field = _kind(item.get("field"), f"evidence[{index}].field")
        status = _text(item.get("status", "supported"), f"evidence[{index}].status", limit=40).casefold()
        if status not in _STATUS_VALUES - {"not_required"}:
            raise OpportunityConstraintsError(f"evidence[{index}].status_invalid")
        confirmed = _optional_bool(item.get("confirmed"), f"evidence[{index}].confirmed", True)
        normalized = {
            "evidence_id": evidence_id,
            "kind": kind,
            "field": field,
            "value": item.get("value"),
            "status": status,
            "confirmed": confirmed,
            "locator": _locator(item.get("locator"), source_ref, f"evidence[{index}].locator"),
            "weight": item.get("weight"),
            "label": _text(item.get("label", ""), f"evidence[{index}].label", required=False, limit=300),
            "note": _text(item.get("note", ""), f"evidence[{index}].note", required=False, limit=1000),
        }
        if normalized["weight"] is not None:
            if isinstance(normalized["weight"], bool) or not isinstance(normalized["weight"], (int, float)):
                raise OpportunityConstraintsError(f"evidence[{index}].weight_invalid")
            if not math.isfinite(float(normalized["weight"])) or not 0 <= float(normalized["weight"]) <= 1:
                raise OpportunityConstraintsError(f"evidence[{index}].weight_out_of_range")
            normalized["weight"] = float(normalized["weight"])
        rows.append(normalized)
    return sorted(rows, key=lambda item: item["evidence_id"])


def _categories(kind: str, field: str) -> set[str]:
    result = {kind}
    field_case = field.casefold()
    if kind == "hard_gate" or field_case.startswith(("gate_", "required_")):
        result.add("hard_gate")
    if kind == "eligibility" or any(token in field_case for token in ("eligib", "eligible", "incompat")):
        result.add("eligibility")
    if kind == "date" or any(token in field_case for token in ("date", "deadline", "window", "start", "end")):
        result.add("date")
    if kind == "duration" or any(token in field_case for token in ("duration", "months", "month", "term")):
        result.add("duration")
    if kind == "budget" or any(token in field_case for token in ("budget", "amount", "cost", "funding")):
        result.add("budget")
    if kind == "transfer" or any(token in field_case for token in ("transfer", "audience", "impact", "diffusion")):
        result.add("transfer")
    if kind == "required_document" or "document" in field_case or field_case.endswith("_docs"):
        result.add("required_document")
    return result


def _status_for(evidence: list[dict[str, Any]], refs: list[str], required: bool) -> str:
    if not required:
        return "not_required"
    selected = [row for row in evidence if row["evidence_id"] in refs]
    if not selected:
        return "unknown"
    if any(row["status"] == "contradicted" for row in selected):
        return "contradicted"
    if any(row["status"] == "supported" and row["confirmed"] for row in selected):
        return "supported"
    return "unknown"


def _constraint_rows(package: Mapping[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declarations = _list(package.get("requirements", []), "requirements")
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        by_field.setdefault(item["field"], []).append(item)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(declarations):
        item = _mapping(raw, f"requirements[{index}]")
        raw_id = item.get("constraint_id", item.get("id"))
        constraint_id = _text(raw_id, f"requirements[{index}].id", limit=200)
        if constraint_id in seen:
            raise OpportunityConstraintsError("constraint_id_duplicate")
        seen.add(constraint_id)
        field = _kind(item.get("field"), f"requirements[{index}].field")
        kind = _kind(item.get("kind", field), f"requirements[{index}].kind")
        required = _optional_bool(item.get("required"), f"requirements[{index}].required", True)
        raw_refs = item.get("evidence_refs")
        refs = sorted(set(raw_refs)) if raw_refs is not None else [row["evidence_id"] for row in by_field.get(field, [])]
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise OpportunityConstraintsError(f"requirements[{index}].evidence_refs_invalid")
        unknown_refs = sorted(set(refs) - {row["evidence_id"] for row in evidence})
        if unknown_refs:
            raise OpportunityConstraintsError("constraint_evidence_ref_missing")
        linked = [row for row in evidence if row["evidence_id"] in refs]
        status = _status_for(evidence, refs, required)
        if any(row["kind"] == "date" and not row["confirmed"] for row in linked):
            status = "unknown"
        value = item.get("value")
        if value is None and linked:
            values = [row["value"] for row in linked if row["value"] is not None]
            if values:
                value = values[0]
        rows.append({
            "constraint_id": constraint_id,
            "field": field,
            "kind": kind,
            "required": required,
            "value": value,
            "status": status,
            "evidence_refs": sorted(refs),
            "locator_refs": sorted({
                stable_json(row["locator"]) for row in linked
            }),
        })

    declared_fields = {row["field"] for row in rows}
    for item in evidence:
        if item["kind"] == "criterion":
            continue
        if item["field"] in declared_fields:
            continue
        constraint_id = "constraint:" + item["evidence_id"]
        rows.append({
            "constraint_id": constraint_id,
            "field": item["field"],
            "kind": item["kind"],
            "required": True,
            "value": item["value"],
            "status": "unknown" if not item["confirmed"] else item["status"],
            "evidence_refs": [item["evidence_id"]],
            "locator_refs": [stable_json(item["locator"])],
        })
    return sorted(rows, key=lambda item: item["constraint_id"])


def _criteria(evidence: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, float | None]:
    rows = []
    for item in evidence:
        if item["kind"] != "criterion":
            continue
        value = item["value"] if isinstance(item["value"], Mapping) else {}
        weight = item["weight"]
        if weight is None and isinstance(value, Mapping):
            weight = value.get("weight")
        if weight is not None:
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                raise OpportunityConstraintsError("criterion_weight_invalid")
            if not math.isfinite(float(weight)) or not 0 <= float(weight) <= 1:
                raise OpportunityConstraintsError("criterion_weight_out_of_range")
            weight = float(weight)
        name = item["label"] or item["field"]
        rows.append({
            "criterion_id": "criterion:" + item["evidence_id"],
            "name": name,
            "field": item["field"],
            "weight": weight,
            "status": item["status"] if item["confirmed"] else "unknown",
            "evidence_refs": [item["evidence_id"]],
            "locator_refs": [stable_json(item["locator"])],
        })
    rows.sort(key=lambda item: item["criterion_id"])
    if not rows:
        return rows, "unknown", None
    if any(row["weight"] is None for row in rows):
        return rows, "incomplete_weights", None
    total = round(sum(float(row["weight"]) for row in rows), 12)
    return rows, "complete" if math.isclose(total, 1.0, abs_tol=1e-9) else "incomplete_weights", total


def _index_ids(constraints: list[dict[str, Any]], category: str) -> list[str]:
    result = []
    for row in constraints:
        if category in _categories(row["kind"], row["field"]):
            result.append(row["constraint_id"])
    return sorted(result)


def _unknowns(
    source: Mapping[str, Any],
    constraints: list[dict[str, Any]],
    criteria_status: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if source["version"] == "unknown":
        rows.append({"code": "source_version_unknown", "constraint_ids": [], "evidence_refs": []})
    if source["validity"]["status"] == "unknown":
        rows.append({"code": "source_validity_unknown", "constraint_ids": [], "evidence_refs": []})
    elif source["validity"]["status"] == "observed_local":
        rows.append({"code": "source_current_status_unverified", "constraint_ids": [], "evidence_refs": []})
    for row in constraints:
        if row["status"] == "unknown":
            code = "requirement_without_evidence" if not row["evidence_refs"] else "constraint_status_unknown"
            rows.append({
                "code": code,
                "constraint_ids": [row["constraint_id"]],
                "evidence_refs": list(row["evidence_refs"]),
            })
    if criteria_status != "complete":
        rows.append({"code": "criteria_weights_incomplete", "constraint_ids": [], "evidence_refs": []})
    return sorted(rows, key=lambda item: (item["code"], item["constraint_ids"], item["evidence_refs"]))


def _contradictions(constraints: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["evidence_id"]: row for row in evidence}
    rows = []
    for constraint in constraints:
        linked = [by_id[ref] for ref in constraint["evidence_refs"] if ref in by_id]
        if not any(item["status"] == "contradicted" for item in linked):
            continue
        reason = "support_and_contradictory_evidence" if any(item["status"] == "supported" for item in linked) else "evidence_marked_contradicted"
        rows.append({
            "constraint_id": constraint["constraint_id"],
            "field": constraint["field"],
            "reason": reason,
            "evidence_refs": sorted(constraint["evidence_refs"]),
        })
    return sorted(rows, key=lambda item: item["constraint_id"])


def compile_opportunity_constraints(package: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one local documentary package without side effects."""
    if not isinstance(package, Mapping):
        raise OpportunityConstraintsError("package_must_be_object")
    schema = package.get("schema")
    if schema not in _INPUT_SCHEMAS:
        raise OpportunityConstraintsError("unsupported_input_schema")
    if "input_hash" in package:
        raise OpportunityConstraintsError("input_hash_reserved")
    opportunity_id = _text(package.get("opportunity_id"), "opportunity_id", limit=240)
    title = _text(package.get("title"), "title", limit=500)
    source = _source(package)
    evidence = _normalize_evidence(package, source["source_ref"])
    constraints = _constraint_rows(package, evidence)
    criteria, criteria_status, criteria_total = _criteria(evidence)
    contradictions = _contradictions(constraints, evidence)
    unknowns = _unknowns(source, constraints, criteria_status)
    hard_gates = _index_ids(constraints, "hard_gate")
    output = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity_id,
        "title": title,
        "source": source,
        "input_hash": _hash(package),
        "constraints": constraints,
        "hard_gates": hard_gates,
        "eligibility": _index_ids(constraints, "eligibility"),
        "dates": _index_ids(constraints, "date"),
        "duration": _index_ids(constraints, "duration"),
        "budget": _index_ids(constraints, "budget"),
        "transfer": _index_ids(constraints, "transfer"),
        "required_documents": _index_ids(constraints, "required_document"),
        "criteria": criteria,
        "evidence": evidence,
        "contradictions": contradictions,
        "unknowns": unknowns,
        "provenance": {
            "input_schema": schema,
            "source_ref": source["source_ref"],
            "source_hash": source["source_hash"],
            "locators_are_required": True,
            "claims_promoted": 0,
        },
        "reconciliation": {
            "input_evidence_count": len(evidence),
            "output_evidence_count": len(evidence),
            "constraint_count": len(constraints),
            "hard_gate_count": len(hard_gates),
            "criterion_count": len(criteria),
            "criteria_weight_status": criteria_status,
            "criteria_weight_total": criteria_total,
            "contradiction_count": len(contradictions),
            "unknown_count": len(unknowns),
            "claims_promoted": 0,
            "deterministic_order": True,
        },
    }
    validate_opportunity_constraints(output)
    return output


def validation_errors(payload: Mapping[str, Any]) -> list[str]:
    """Return structural errors without mutating or repairing the payload."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return ["payload_must_be_object"]
    if payload.get("schema") != SCHEMA:
        errors.append("schema_invalid")
    if set(payload) != _TOP_LEVEL_FIELDS:
        errors.append("top_level_fields_invalid")
    for field in ("opportunity_id", "title", "algorithm_version", "input_hash"):
        if not isinstance(payload.get(field), str) or not payload.get(field):
            errors.append(f"{field}_invalid")
    try:
        source = _mapping(payload.get("source"), "source")
        if set(source) != {"source_ref", "source_url", "source_hash", "content_hash", "version", "validity"}:
            errors.append("source_fields_invalid")
        _text(source.get("source_ref"), "source.source_ref")
        _hash_value(source.get("source_hash"), "source.source_hash")
        if source.get("content_hash") is not None:
            _hash_value(source.get("content_hash"), "source.content_hash")
        _text(source.get("version"), "source.version")
        validity = _mapping(source.get("validity"), "source.validity")
        if set(validity) != {"status", "confirmed", "effective_from", "effective_to"}:
            errors.append("validity_fields_invalid")
        if validity.get("status") not in _SOURCE_STATUS_VALUES:
            errors.append("validity_status_invalid")
        if not isinstance(validity.get("confirmed"), bool):
            errors.append("validity_confirmed_invalid")
    except OpportunityConstraintsError as exc:
        errors.append(str(exc))
    for field in ("constraints", "evidence", "hard_gates", "eligibility", "dates", "duration", "budget", "transfer", "required_documents", "criteria", "contradictions", "unknowns"):
        if not isinstance(payload.get(field), list):
            errors.append(f"{field}_must_be_list")
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    evidence_ids = []
    for item in evidence:
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_FIELDS:
            errors.append("evidence_fields_invalid")
            continue
        evidence_ids.append(item.get("evidence_id"))
        if item.get("status") not in _STATUS_VALUES - {"not_required"}:
            errors.append("evidence_status_invalid")
        if not isinstance(item.get("confirmed"), bool):
            errors.append("evidence_confirmed_invalid")
    if evidence_ids != sorted(evidence_ids) or len(set(evidence_ids)) != len(evidence_ids):
        errors.append("evidence_order_or_ids_invalid")
    constraint_ids = []
    for item in payload.get("constraints", []) if isinstance(payload.get("constraints"), list) else []:
        if not isinstance(item, Mapping) or set(item) != _CONSTRAINT_FIELDS:
            errors.append("constraint_fields_invalid")
            continue
        constraint_ids.append(item.get("constraint_id"))
        if item.get("status") not in _STATUS_VALUES:
            errors.append("constraint_status_invalid")
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or refs != sorted(set(refs)):
            errors.append("constraint_evidence_refs_invalid")
        if any(ref not in evidence_ids for ref in refs or []):
            errors.append("constraint_evidence_ref_unresolved")
    if constraint_ids != sorted(constraint_ids) or len(set(constraint_ids)) != len(constraint_ids):
        errors.append("constraint_order_or_ids_invalid")
    for item in payload.get("criteria", []) if isinstance(payload.get("criteria"), list) else []:
        if not isinstance(item, Mapping):
            errors.append("criterion_invalid")
            continue
        if set(item) != {"criterion_id", "name", "field", "weight", "status", "evidence_refs", "locator_refs"}:
            errors.append("criterion_fields_invalid")
        weight = item.get("weight")
        if weight is not None and (isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or not 0 <= float(weight) <= 1):
            errors.append("criterion_weight_invalid")
    for field in ("hard_gates", "eligibility", "dates", "duration", "budget", "transfer", "required_documents"):
        values = payload.get(field)
        if isinstance(values, list) and (values != sorted(set(values)) or any(value not in constraint_ids for value in values)):
            errors.append(f"{field}_index_invalid")
    recon = payload.get("reconciliation")
    if not isinstance(recon, Mapping):
        errors.append("reconciliation_invalid")
    else:
        if recon.get("claims_promoted") != 0:
            errors.append("claims_promoted")
        if recon.get("deterministic_order") is not True:
            errors.append("deterministic_order_invalid")
        if recon.get("input_evidence_count") != len(evidence) or recon.get("output_evidence_count") != len(evidence):
            errors.append("evidence_reconciliation_invalid")
        if recon.get("constraint_count") != len(payload.get("constraints", [])):
            errors.append("constraint_reconciliation_invalid")
    return sorted(set(errors))


def validate_opportunity_constraints(payload: Mapping[str, Any]) -> bool:
    errors = validation_errors(payload)
    if errors:
        raise OpportunityConstraintsError("invalid_constraints_payload:" + ",".join(errors))
    return True


def validate_payload(payload: Mapping[str, Any]) -> bool:
    """Compatibility alias for downstream consumers that use validate_payload."""
    return validate_opportunity_constraints(payload)


def compile_constraints(package: Mapping[str, Any]) -> dict[str, Any]:
    """Short alias for the public compiler."""
    return compile_opportunity_constraints(package)
