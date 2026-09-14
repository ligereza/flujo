"""Deterministic, read-only triangulation of bounded research evidence.

This module normalizes research result batches without fetching sources,
opening a database or importing the research runner. URLs and hashes are
provenance metadata only. A candidate claim can reach a provisional support or
contradiction result only when its explicit evidence references resolve to
captured, hashed sources from the required number of independent groups and
domains. No result is promoted to truth.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit
from typing import Any

from ._contract_helpers import optional_text as _text, sha256_ref as _digest, stable_json


FRONTIER_SCHEMA = "mak-research-frontier-jobs-v1"
RESULT_BATCH_SCHEMA = "mak-research-result-batch-v1"
TRIANGULATION_SCHEMA = "mak-research-triangulation-v1"
ALGORITHM_VERSION = "research-evidence-triangulation-1"
REPORT_HASH_ALGORITHM = "sha256-canonical-triangulation-without-report-hash-v1"
PROMOTION = "none"

RESULT_STATUSES = frozenset({
    "supported_candidate", "contradicted_candidate", "mixed_conflict",
    "unresolved", "failed_capture",
})
RELATIONS = frozenset({"supports", "contradicts"})
EXTRACTION_STATUS = "candidate"
CAPTURED_STATUSES = frozenset({"captured", "success", "ok", "verified"})
FAILED_CAPTURE_STATUSES = frozenset({
    "failed", "capture_failed", "error", "unavailable", "blocked", "timeout",
})
CLAIM_FIELDS = frozenset({
    "claim_id", "requirement_id", "relation", "statement", "value",
    "evidence_refs", "source_ids", "extraction_status",
})
SOURCE_FIELDS = frozenset({
    "source_id", "source_group", "url", "raw_sha256", "text_sha256",
    "capture_status", "license_state",
})


class ResearchTriangulationError(ValueError):
    """Raised by the assertion API when a triangulation report is invalid."""

    def __init__(self, message: str, report: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = dict(report) if report is not None else None


def _identifier(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, str)):
        text = str(value).strip()
        return text
    return ""


def _error(code: str, detail: str = "", **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code}
    if detail:
        row["detail"] = detail
    row.update(extra)
    return row


def _sorted_unique_strings(value: Any) -> tuple[list[str], str | None]:
    if not isinstance(value, list):
        return [], "not_list"
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return [], "invalid_string"
    result = sorted(set(value))
    if value != result:
        return result, "not_sorted_unique"
    return result, None


def _hash_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{64}", value))


def _url_host(value: str) -> str:
    parsed = urlsplit(value)
    return (parsed.hostname or "").casefold().rstrip(".")


def _url_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def _source_capture_ok(source: Mapping[str, Any]) -> bool:
    return _text(source.get("capture_status")).casefold() in CAPTURED_STATUSES


def _source_hash_ok(source: Mapping[str, Any]) -> bool:
    return _hash_valid(source.get("raw_sha256")) and _hash_valid(source.get("text_sha256"))


def _source_valid(source: Mapping[str, Any]) -> bool:
    return (
        _text(source.get("source_id")) != ""
        and _text(source.get("source_group")) != ""
        and _url_valid(source.get("url"))
        and _source_capture_ok(source)
        and _source_hash_ok(source)
        and _text(source.get("license_state")) != ""
    )


def _claim_semantic_key(claim: Mapping[str, Any]) -> str:
    semantic = {
        "relation": claim.get("relation"),
        "statement": claim.get("statement"),
        "value": claim.get("value"),
    }
    return stable_json(semantic)


def _independent_sources(
    source_ids: Sequence[str], sources: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Select at most one source per explicit group and URL domain."""
    selected_ids: list[str] = []
    groups: list[str] = []
    domains: list[str] = []
    used_groups: set[str] = set()
    used_domains: set[str] = set()
    for source_id in sorted(set(source_ids)):
        source = sources.get(source_id)
        if not source or not _source_valid(source):
            continue
        group = _text(source.get("source_group"))
        domain = _url_host(_text(source.get("url")))
        if not group or not domain or group in used_groups or domain in used_domains:
            continue
        selected_ids.append(source_id)
        groups.append(group)
        domains.append(domain)
        used_groups.add(group)
        used_domains.add(domain)
    return selected_ids, sorted(groups), sorted(domains)


def _normalize_source(raw: Any, errors: list[dict[str, Any]], *, index: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        errors.append(_error("source_not_object", index=index))
        return {key: "" for key in SOURCE_FIELDS}
    if set(raw) - SOURCE_FIELDS:
        errors.append(_error("source_field_set_invalid", _text(raw.get("source_id")), index=index))
    source = {
        "source_id": _text(raw.get("source_id")),
        "source_group": _text(raw.get("source_group")),
        "url": _text(raw.get("url")),
        "raw_sha256": _text(raw.get("raw_sha256", raw.get("raw_hash"))),
        "text_sha256": _text(raw.get("text_sha256", raw.get("text_hash"))),
        "capture_status": _text(raw.get("capture_status", raw.get("status"))).casefold(),
        "license_state": _text(raw.get("license_state", raw.get("license"))),
    }
    if not source["source_id"]:
        errors.append(_error("source_id_missing", index=index))
    if not source["source_group"]:
        errors.append(_error("source_group_missing", source["source_id"], index=index))
    if not _url_valid(source["url"]):
        errors.append(_error("source_url_invalid", source["source_id"], index=index))
    if source["capture_status"] in CAPTURED_STATUSES:
        if not _hash_valid(source["raw_sha256"]):
            errors.append(_error("source_raw_hash_missing_or_invalid", source["source_id"], index=index))
        if not _hash_valid(source["text_sha256"]):
            errors.append(_error("source_text_hash_missing_or_invalid", source["source_id"], index=index))
    elif source["capture_status"] not in FAILED_CAPTURE_STATUSES:
        errors.append(_error("source_capture_status_invalid", source["source_id"], index=index))
    if not source["license_state"]:
        errors.append(_error("source_license_state_missing", source["source_id"], index=index))
    return source


def _normalize_claim(raw: Any, errors: list[dict[str, Any]], *, index: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        errors.append(_error("claim_not_object", index=index))
        return {
            "claim_id": "", "requirement_id": "", "relation": "",
            "statement": "", "value": None, "evidence_refs": [],
            "source_ids": [], "extraction_status": "",
        }
    claim = {
        "claim_id": _text(raw.get("claim_id")),
        "requirement_id": _text(raw.get("requirement_id")),
        "relation": _text(raw.get("relation")).casefold(),
        "statement": raw.get("statement", ""),
        "value": copy.deepcopy(raw.get("value")),
        "evidence_refs": sorted(set(raw.get("evidence_refs", [])))
        if isinstance(raw.get("evidence_refs"), list)
        and all(isinstance(item, str) and item.strip() for item in raw.get("evidence_refs", []))
        else [],
        "source_ids": sorted(set(raw.get("source_ids", [])))
        if isinstance(raw.get("source_ids"), list)
        and all(isinstance(item, str) and item.strip() for item in raw.get("source_ids", []))
        else [],
        "extraction_status": _text(raw.get("extraction_status")).casefold(),
    }
    if set(raw) - CLAIM_FIELDS:
        errors.append(_error("claim_field_set_invalid", claim["claim_id"], index=index))
    if not claim["claim_id"]:
        errors.append(_error("claim_id_missing", index=index))
    if not claim["requirement_id"]:
        errors.append(_error("claim_requirement_id_missing", claim["claim_id"], index=index))
    if claim["relation"] not in RELATIONS:
        errors.append(_error("claim_relation_invalid", claim["claim_id"], index=index))
    if "statement" not in raw and "value" not in raw:
        errors.append(_error("claim_statement_or_value_missing", claim["claim_id"], index=index))
    try:
        stable_json({"statement": claim["statement"], "value": claim["value"]})
    except (TypeError, ValueError):
        errors.append(_error("claim_semantics_not_serializable", claim["claim_id"], index=index))
        claim["statement"] = ""
        claim["value"] = None
    if not claim["evidence_refs"]:
        errors.append(_error("claim_evidence_refs_missing", claim["claim_id"], index=index))
    if not claim["source_ids"]:
        errors.append(_error("claim_source_ids_missing", claim["claim_id"], index=index))
    if claim["extraction_status"] != EXTRACTION_STATUS:
        errors.append(_error("claim_extraction_status_invalid", claim["claim_id"], index=index))
    return claim


def normalize_research_result_batch(batch: Any) -> dict[str, Any]:
    """Normalize one result batch without fetching or mutating its input."""
    errors: list[dict[str, Any]] = []
    if not isinstance(batch, Mapping):
        return {
            "schema": RESULT_BATCH_SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "results": [],
            "normalization_errors": [_error("result_batch_not_object")],
        }
    if batch.get("schema") != RESULT_BATCH_SCHEMA:
        errors.append(_error("result_batch_schema_invalid"))
    raw_results = batch.get("results")
    if not isinstance(raw_results, list):
        errors.append(_error("result_batch_results_invalid"))
        raw_results = []
    top_sources = batch.get("sources") if isinstance(batch.get("sources"), list) else []
    results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_results):
        if not isinstance(raw, Mapping):
            errors.append(_error("result_not_object", index=index))
            continue
        job_id = _identifier(raw.get("job_id"))
        requirement_id = _text(raw.get("requirement_id"))
        if not job_id:
            errors.append(_error("result_job_id_missing", index=index))
        if not requirement_id:
            errors.append(_error("result_requirement_id_missing", job_id, index=index))
        sources_raw = raw.get("sources") if isinstance(raw.get("sources"), list) else []
        if not sources_raw and top_sources:
            matching_top_sources = [
                source for source in top_sources
                if isinstance(source, Mapping)
                and _identifier(source.get("job_id")) == job_id
                and _text(source.get("requirement_id")) == requirement_id
            ]
            if matching_top_sources:
                sources_raw = matching_top_sources
            elif all(
                isinstance(source, Mapping)
                and not _identifier(source.get("job_id"))
                and not _text(source.get("requirement_id"))
                for source in top_sources
            ):
                sources_raw = top_sources
        source_errors: list[dict[str, Any]] = []
        sources = [
            _normalize_source(source, source_errors, index=source_index)
            for source_index, source in enumerate(sources_raw)
        ]
        errors.extend({**error, "job_id": job_id, "requirement_id": requirement_id} for error in source_errors)
        claim_errors: list[dict[str, Any]] = []
        raw_claims = raw.get("claims") if isinstance(raw.get("claims"), list) else []
        claims = [
            _normalize_claim(claim, claim_errors, index=claim_index)
            for claim_index, claim in enumerate(raw_claims)
        ]
        errors.extend({**error, "job_id": job_id, "requirement_id": requirement_id} for error in claim_errors)
        results.append({
            "job_id": job_id,
            "requirement_id": requirement_id,
            "question": _text(raw.get("question")),
            "status": _text(raw.get("status", "captured")).casefold() or "unknown",
            "sources": sorted(sources, key=lambda row: row["source_id"]),
            "claims": sorted(claims, key=lambda row: row["claim_id"]),
        })
    results.sort(key=lambda row: (row["job_id"], row["requirement_id"]))
    return {
        "schema": RESULT_BATCH_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "results": results,
        "normalization_errors": sorted(errors, key=stable_json),
    }


def adapt_execute_research_report(
    report: Mapping[str, Any], *, requirement_id: str | None = None,
    independent_source_groups_required: int = 2,
) -> dict[str, Any]:
    """Adapt the real execute-research report without inventing claims.

    The runner report has capture receipts but no extracted claims. The
    returned batch therefore always has an empty claims list; triangulation can
    only return unresolved or failed_capture for it.
    """
    errors: list[dict[str, Any]] = []
    if not isinstance(report, Mapping):
        return {
            "schema": RESULT_BATCH_SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "results": [],
            "normalization_errors": [_error("execute_report_not_object")],
        }
    job_id = _identifier(report.get("job_id"))
    if not job_id:
        errors.append(_error("execute_report_job_id_missing"))
    req = _text(report.get("requirement_id")) or _text(requirement_id)
    sources: list[dict[str, Any]] = []
    raw_sources = report.get("sources") if isinstance(report.get("sources"), list) else []
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, Mapping):
            errors.append(_error("execute_source_not_object", index=index))
            continue
        source_id = _text(raw.get("source_id"))
        if not source_id:
            source_id = "source:" + hashlib.sha256(
                stable_json({"job_id": job_id, "index": index, "url": _text(raw.get("url"))}).encode("utf-8")
            ).hexdigest()[:24]
        url = _text(raw.get("url"))
        host = _url_host(url)
        source_group = _text(raw.get("source_group")) or ("host:" + host if host else "adapter:unknown")
        sources.append({
            "source_id": source_id,
            "source_group": source_group,
            "url": url,
            "raw_sha256": _text(raw.get("raw_sha256", raw.get("raw_hash"))),
            "text_sha256": _text(raw.get("text_sha256", raw.get("text_hash"))),
            "capture_status": _text(raw.get("capture_status", raw.get("status"))).casefold() or "unknown",
            "license_state": _text(raw.get("license_state", raw.get("license"))) or "unknown_pending_source_review",
        })
    if not req:
        errors.append(_error("execute_report_requirement_id_missing", job_id))
    try:
        required = int(independent_source_groups_required)
    except (TypeError, ValueError):
        required = 0
        errors.append(_error("independent_source_groups_required_invalid", job_id))
    if required < 1:
        errors.append(_error("independent_source_groups_required_invalid", job_id))
    return {
        "schema": RESULT_BATCH_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "independent_source_groups_required": required,
        "results": [{
            "job_id": job_id,
            "requirement_id": req,
            "question": _text(report.get("question")),
            "status": _text(report.get("status", "unknown")).casefold() or "unknown",
            "sources": sorted(sources, key=lambda row: row["source_id"]),
            "claims": [],
        }],
        "normalization_errors": sorted(errors, key=stable_json),
        "provenance": {"adapter": "execute_research_job", "claims_extracted": False},
    }


def _refresh_requirement_id(frontier: Mapping[str, Any], job: Mapping[str, Any]) -> str:
    provenance = job.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("frontier_kind") != "refresh_source_validity":
        return ""
    opportunity_id = _text(frontier.get("opportunity_id"))
    return f"source-validity:{opportunity_id}" if opportunity_id else ""


def _frontier_context(frontier: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(frontier, Mapping):
        return [], [_error("frontier_not_object")]
    if frontier.get("schema") != FRONTIER_SCHEMA:
        errors.append(_error("frontier_schema_invalid"))
    raw_jobs = frontier.get("jobs")
    if not isinstance(raw_jobs, list):
        errors.append(_error("frontier_jobs_invalid"))
        return [], errors
    default_required = frontier.get("independent_source_groups_required", 2)
    contexts: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_jobs):
        if not isinstance(raw, Mapping):
            errors.append(_error("frontier_job_not_object", index=index))
            continue
        job_id = _identifier(raw.get("job_id"))
        if not job_id:
            errors.append(_error("frontier_job_id_missing", index=index))
        refresh_requirement_id = _refresh_requirement_id(frontier, raw)
        if "requirement_ids" in raw:
            requirement_ids, requirement_error = _sorted_unique_strings(raw.get("requirement_ids"))
            if requirement_error:
                code = (
                    "frontier_requirement_ids_invalid"
                    if requirement_error in {"not_list", "invalid_string"}
                    else "frontier_requirement_ids_not_sorted_unique"
                )
                errors.append(_error(code, job_id, index=index))
            requirement_rows = [{"requirement_id": item} for item in requirement_ids]
        else:
            errors.append(_error("frontier_requirement_ids_missing", job_id, index=index))
            requirement_rows = []
        if not requirement_rows and refresh_requirement_id:
            requirement_rows = [{"requirement_id": refresh_requirement_id}]
        elif not requirement_rows:
            errors.append(_error("frontier_requirement_ids_empty", job_id, index=index))
        for requirement_index, requirement_raw in enumerate(requirement_rows):
            if isinstance(requirement_raw, Mapping):
                requirement_id = _text(requirement_raw.get("requirement_id", requirement_raw.get("id")))
                required_raw = requirement_raw.get(
                    "independent_source_groups_required",
                    raw.get("independent_source_groups_required", default_required),
                )
            else:
                requirement_id = _text(requirement_raw)
                required_raw = raw.get("independent_source_groups_required", default_required)
            if not requirement_id:
                errors.append(_error("frontier_requirement_id_missing", job_id, index=requirement_index))
            try:
                required = int(required_raw)
            except (TypeError, ValueError):
                required = 0
                errors.append(_error("independent_source_groups_required_invalid", job_id, requirement_id=requirement_id))
            if required < 1:
                errors.append(_error("independent_source_groups_required_invalid", job_id, requirement_id=requirement_id))
            contexts.append({
                "job_id": job_id,
                "requirement_id": requirement_id,
                "question": _text(raw.get("question")),
                "required": required,
            })
    contexts.sort(key=lambda row: (row["job_id"], row["requirement_id"]))
    seen: set[tuple[str, str]] = set()
    for context in contexts:
        key = (context["job_id"], context["requirement_id"])
        if key in seen:
            errors.append(_error("frontier_job_requirement_duplicate", f"{key[0]}::{key[1]}"))
        seen.add(key)
    return contexts, sorted(errors, key=stable_json)


def _merge_batches(
    result_batches: Any,
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]], list[str]]:
    raw_batches = [result_batches] if isinstance(result_batches, Mapping) else result_batches
    errors: list[dict[str, Any]] = []
    if not isinstance(raw_batches, list):
        return {}, [_error("result_batches_invalid")], []
    aggregate: dict[tuple[str, str], dict[str, Any]] = {}
    source_by_id: dict[str, dict[str, Any]] = {}
    claim_by_id: dict[str, dict[str, Any]] = {}
    batch_schemas: list[str] = []
    for batch_index, raw_batch in enumerate(raw_batches):
        normalized = normalize_research_result_batch(raw_batch)
        batch_schemas.append(_text(normalized.get("schema")))
        errors.extend({**error, "batch_index": batch_index} for error in normalized["normalization_errors"])
        if isinstance(raw_batch, Mapping) and isinstance(raw_batch.get("normalization_errors"), list):
            errors.extend({**error, "batch_index": batch_index} for error in raw_batch["normalization_errors"] if isinstance(error, Mapping))
        for row in normalized["results"]:
            key = (row["job_id"], row["requirement_id"])
            item = aggregate.setdefault(key, {"questions": [], "statuses": [], "sources": {}, "claims": {}})
            question = _text(row.get("question"))
            if question:
                prior_questions = set(item["questions"])
                if prior_questions and question not in prior_questions:
                    errors.append(_error("result_question_conflict", key[0] + "::" + key[1], batch_index=batch_index))
                item["questions"].append(question)
            item["statuses"].append(row["status"])
            for source in row["sources"]:
                source_id = source["source_id"]
                prior = source_by_id.get(source_id)
                if prior is not None and prior != source:
                    errors.append(_error("source_id_conflict", source_id, batch_index=batch_index))
                    continue
                source_by_id[source_id] = source
                item["sources"][source_id] = source
            for claim in row["claims"]:
                claim_id = claim["claim_id"]
                prior_claim = claim_by_id.get(claim_id)
                if prior_claim is not None and prior_claim != claim:
                    errors.append(_error("claim_id_conflict", claim_id, batch_index=batch_index))
                    continue
                claim_by_id[claim_id] = claim
                item["claims"][claim_id] = claim
    return aggregate, sorted(errors, key=stable_json), sorted(set(batch_schemas))


def _result_for_context(
    context: Mapping[str, Any], item: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    job_id = str(context["job_id"])
    requirement_id = str(context["requirement_id"])
    required = int(context["required"])
    gaps: list[str] = []
    row_errors: list[dict[str, Any]] = []
    if item is None:
        gaps.append("result_missing")
        status = "unresolved"
        sources: dict[str, Mapping[str, Any]] = {}
        claims: list[Mapping[str, Any]] = []
        statuses: list[str] = []
    else:
        sources = dict(item["sources"])
        claims = list(item["claims"].values())
        statuses = [str(value).casefold() for value in item["statuses"]]
        if not claims:
            gaps.append("no_extracted_claims")
        if any(status in FAILED_CAPTURE_STATUSES for status in statuses):
            gaps.append("capture_failure_reported")

    valid_source_ids = {
        source_id for source_id, source in sources.items() if _source_valid(source)
    }
    invalid_source_ids = sorted(set(sources) - valid_source_ids)
    if invalid_source_ids:
        gaps.append("invalid_source_receipt")
    if any(not _source_capture_ok(source) for source in sources.values()):
        gaps.append("partial_capture_failure")

    support_groups: dict[str, set[str]] = {}
    contradiction_groups: dict[str, set[str]] = {}
    support_domains: dict[str, set[str]] = {}
    contradiction_domains: dict[str, set[str]] = {}
    support_claims: dict[str, set[str]] = {}
    contradiction_claims: dict[str, set[str]] = {}
    evidence_refs: set[str] = set()
    counterevidence_refs: set[str] = set()
    used_source_ids: set[str] = set()
    for claim in claims:
        claim_id = _text(claim.get("claim_id"))
        relation = _text(claim.get("relation")).casefold()
        extraction_status = _text(claim.get("extraction_status")).casefold()
        if relation not in RELATIONS or extraction_status != EXTRACTION_STATUS:
            gaps.append("invalid_claim")
            continue
        if _text(claim.get("requirement_id")) != requirement_id:
            gaps.append("claim_requirement_mismatch")
            continue
        source_ids = claim.get("source_ids") if isinstance(claim.get("source_ids"), list) else []
        evidence = claim.get("evidence_refs") if isinstance(claim.get("evidence_refs"), list) else []
        if not source_ids or not evidence:
            gaps.append("claim_evidence_or_sources_missing")
            continue
        if any(source_id not in sources for source_id in source_ids):
            gaps.append("claim_source_dangling")
            continue
        if any(source_id not in valid_source_ids for source_id in source_ids):
            gaps.append("claim_source_invalid")
            continue
        selected_ids, groups, domains = _independent_sources(source_ids, sources)
        if not groups:
            gaps.append("insufficient_independent_source_groups")
            continue
        signature = _claim_semantic_key(claim)
        used_source_ids.update(selected_ids)
        evidence_refs.update(evidence)
        if relation == "supports":
            support_groups.setdefault(signature, set()).update(groups)
            support_domains.setdefault(signature, set()).update(domains)
            support_claims.setdefault(signature, set()).add(claim_id)
        elif relation == "contradicts":
            contradiction_groups.setdefault(signature, set()).update(groups)
            contradiction_domains.setdefault(signature, set()).update(domains)
            contradiction_claims.setdefault(signature, set()).add(claim_id)

    support_winners = {
        signature for signature, groups in support_groups.items()
        if len(groups) >= required and len(support_domains.get(signature, set())) >= required
    }
    contradiction_winners = {
        signature for signature, groups in contradiction_groups.items()
        if len(groups) >= required and len(contradiction_domains.get(signature, set())) >= required
    }
    has_support = bool(support_winners)
    has_contradiction = bool(contradiction_winners)
    if support_groups and not has_support:
        gaps.append("insufficient_independent_source_groups")
    if contradiction_groups and not has_contradiction:
        gaps.append("insufficient_independent_source_groups")
    if has_support and has_contradiction:
        status = "mixed_conflict"
    elif has_support:
        status = "supported_candidate"
    elif has_contradiction:
        status = "contradicted_candidate"
    elif item is not None and (
        (
            any(status in FAILED_CAPTURE_STATUSES for status in statuses)
            and not any(_source_capture_ok(source) for source in sources.values())
        )
        or (
            sources
            and not any(_source_capture_ok(source) for source in sources.values())
        )
    ):
        status = "failed_capture"
        gaps.append("all_sources_failed_capture")
    else:
        status = "unresolved"
    independent_groups = sorted({
        group
        for signature in support_winners | contradiction_winners
        for group in (
            support_groups.get(signature, set())
            | contradiction_groups.get(signature, set())
        )
    })
    supporting_claim_ids = sorted({
        claim_id for signature in support_winners for claim_id in support_claims[signature]
    })
    contradicting_claim_ids = sorted({
        claim_id for signature in contradiction_winners for claim_id in contradiction_claims[signature]
    })
    if has_contradiction:
        counterevidence_refs.update(evidence_refs)
    source_ids = sorted(used_source_ids or set(sources))
    result = {
        "job_id": job_id,
        "requirement_id": requirement_id,
        "question": _text(context.get("question")) or (
            sorted(set(item.get("questions", [])))[0] if item and item.get("questions") else ""
        ),
        "status": status,
        "independent_source_groups_required": required,
        "independent_source_groups": independent_groups,
        "sources": [dict(sources[source_id]) for source_id in sorted(sources)],
        "source_ids": source_ids,
        "supporting_claim_ids": supporting_claim_ids,
        "contradicting_claim_ids": contradicting_claim_ids,
        "evidence_refs": sorted(evidence_refs),
        "counterevidence_refs": sorted(counterevidence_refs),
        "gaps": sorted(set(gaps)),
        "promotion": PROMOTION,
        "learning_features": {
            "training_permitted": False,
            "independent_source_group_count": len(independent_groups),
            "source_count": len(source_ids),
            "claim_count": len(claims),
            "support_candidate": has_support,
            "contradiction_candidate": has_contradiction,
        },
    }
    return result, row_errors


def triangulate_research_evidence(frontier: Mapping[str, Any], result_batches: Any) -> dict[str, Any]:
    """Return a deterministic triangulation report for one or more batches."""
    contexts, frontier_errors = _frontier_context(frontier)
    aggregate, batch_errors, batch_schemas = _merge_batches(result_batches)
    errors = frontier_errors + batch_errors
    frontier_pairs = sorted({(context["job_id"], context["requirement_id"]) for context in contexts})
    frontier_pair_set = set(frontier_pairs)
    unexpected_pairs = sorted(set(aggregate) - frontier_pair_set)
    unmatched_result_pairs = []
    for job_id, requirement_id in unexpected_pairs:
        item = aggregate[(job_id, requirement_id)]
        unmatched_result_pairs.append({
            "job_id": job_id,
            "requirement_id": requirement_id,
            "statuses": sorted(set(item["statuses"])),
            "source_count": len(item["sources"]),
            "claim_count": len(item["claims"]),
        })
        errors.append(_error(
            "result_pair_not_in_frontier",
            f"{job_id}::{requirement_id}",
            job_id=job_id,
            requirement_id=requirement_id,
        ))
    results = []
    for context in contexts:
        result, row_errors = _result_for_context(
            context, aggregate.get((context["job_id"], context["requirement_id"])),
        )
        results.append(result)
        errors.extend({**error, "job_id": context["job_id"], "requirement_id": context["requirement_id"]} for error in row_errors)
    results.sort(key=lambda row: (row["job_id"], row["requirement_id"]))
    result_map = {
        f"{row['job_id']}::{row['requirement_id']}": row for row in results
    }
    status_counts = {
        status: sum(row["status"] == status for row in results)
        for status in sorted(RESULT_STATUSES)
    }
    report: dict[str, Any] = {
        "schema": TRIANGULATION_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "frontier_schema": FRONTIER_SCHEMA,
        "result_batch_schemas": batch_schemas,
        "promotion": PROMOTION,
        "results": results,
        "result_by_job_requirement": result_map,
        "unmatched_result_pairs": unmatched_result_pairs,
        "errors": sorted(errors, key=stable_json),
        "reconciliation": {
            "job_requirement_count": len(results),
            "frontier_pair_count": len(frontier_pairs),
            "result_pair_count": len(aggregate),
            "matched_pair_count": len(frontier_pair_set & set(aggregate)),
            "unexpected_result_pair_count": len(unmatched_result_pairs),
            "unexpected_result_pairs": unmatched_result_pairs,
            "pair_reconciliation": not unmatched_result_pairs,
            "status_counts": status_counts,
            "promotion": PROMOTION,
            "training_permitted": False,
            "deterministic_order": results == sorted(results, key=lambda row: (row["job_id"], row["requirement_id"])),
            "independent_group_policy": "distinct_explicit_source_group_and_url_domain",
        },
        "learning_features": {"training_permitted": False, "result_count": len(results)},
        "valid": not errors,
        "status": "pass" if not errors else "fail",
    }
    report["report_hash"] = "report:" + _digest(report)
    return report


def assert_research_triangulation(frontier: Mapping[str, Any], result_batches: Any) -> bool:
    report = triangulate_research_evidence(frontier, result_batches)
    if not report["valid"]:
        codes = ",".join(sorted({str(error.get("code")) for error in report["errors"]}))
        raise ResearchTriangulationError(f"research_triangulation_invalid:{codes}", report)
    return True


normalize_research_results = normalize_research_result_batch
triangulate_research_results = triangulate_research_evidence
assert_triangulation = assert_research_triangulation


__all__ = [
    "ALGORITHM_VERSION", "FRONTIER_SCHEMA", "PROMOTION", "RESULT_BATCH_SCHEMA",
    "RESULT_STATUSES", "ResearchTriangulationError", "SOURCE_FIELDS",
    "TRIANGULATION_SCHEMA", "adapt_execute_research_report",
    "assert_research_triangulation", "assert_triangulation", "normalize_research_result_batch",
    "normalize_research_results", "stable_json", "triangulate_research_evidence",
    "triangulate_research_results",
]
