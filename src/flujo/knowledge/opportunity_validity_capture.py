"""Bounded official-source evidence for one opportunity validity refresh.

The adapter is pure: it does not fetch, persist, dispatch, publish, submit, or
decide applicant fit.  It translates already captured official receipts into
the accepted research-result batch and triangulates that batch against an
existing ``refresh_source_validity`` frontier job.  All Fondos de Cultura URLs
share one authority group, irrespective of whether they are HTML or PDF.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from typing import Any

from ._contract_helpers import stable_json
from urllib.parse import urlsplit

# Optional MAK peer: see flujo.autonomia. Without the MAK research tree the
# capture path raises a declared error instead of failing at import time.
try:  # pragma: no cover - exercised by the branch that lacks cultura/
    from cultura.mak_research.source_pipeline import canonical_url, source_id_for

    MAK_RESEARCH_AVAILABLE = True
except ImportError:
    canonical_url = None  # type: ignore[assignment]
    source_id_for = None  # type: ignore[assignment]
    MAK_RESEARCH_AVAILABLE = False
from .research_evidence_triangulation import triangulate_research_evidence
from .research_frontier_bridge import SCHEMA as FRONTIER_SCHEMA


SCHEMA = "mak-opportunity-validity-capture-v1"
RESULT_BATCH_SCHEMA = "mak-research-result-batch-v1"
ALGORITHM_VERSION = "official-opportunity-validity-capture-1"
AUTHORITY_GROUP = "authority:fondosdecultura.cl"
DEFAULT_MAX_CAPTURE_AGE_SECONDS = 7 * 24 * 60 * 60

OPPORTUNITY_URL = "https://www.fondosdecultura.cl/investigacion-fondart-nacional-2027/"
INDEX_URL = "https://www.fondosdecultura.cl/fondos/fondart-nacional/lineas-de-concurso/"
BASES_URL = "https://www.fondosdecultura.cl/wp-content/uploads/2026/08/investigacion-fondart-nacional-2027.pdf"
EXPECTED_URLS = {
    "opportunity_page": OPPORTUNITY_URL,
    "official_index": INDEX_URL,
    "official_bases_pdf": BASES_URL,
}

_HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$", re.IGNORECASE)
_OPEN_STATES = {"open", "abierta", "abierto", "vigente", "current"}
_CLOSED_STATES = {"closed", "cerrada", "cerrado", "expired", "vencida", "vencido"}

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _state(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if text in _OPEN_STATES:
        return "open"
    if text in _CLOSED_STATES:
        return "closed"
    return "unknown"


def _fold(value: str) -> str:
    return " ".join(
        "".join(
            char for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        ).split()
    )


def extract_official_opportunity_observations(role: str, text: str) -> dict[str, str]:
    """Extract only facts stated by captured content, never caller assertions."""
    if role not in EXPECTED_URLS or not isinstance(text, str):
        return {"opportunity_state": "unknown", "deadline": ""}
    folded = _fold(text)
    if "fondart" not in folded or "2027" not in folded:
        return {"opportunity_state": "unknown", "deadline": ""}

    state = "unknown"
    if role != "official_bases_pdf":
        open_patterns = (
            r"\bstate\s*[=:]\s*open\b",
            r"\bestado\s*[=:]?\s*(?:abierta|abierto|vigente)\b",
            r"\bconvocatoria\s+(?:se encuentra\s+)?abierta\b",
        )
        closed_patterns = (
            r"\bstate\s*[=:]\s*closed\b",
            r"\bestado\s*[=:]?\s*(?:cerrada|cerrado|vencida|vencido)\b",
            r"\bconvocatoria\s+(?:se encuentra\s+)?cerrada\b",
        )
        open_seen = any(re.search(pattern, folded) for pattern in open_patterns)
        closed_seen = any(re.search(pattern, folded) for pattern in closed_patterns)
        if role == "official_index":
            target_open = re.search(
                r"convocatorias abiertas.*?investigacion\s*-\s*fondart nacional 2027"
                r".*?plazo de postulacion\s*:\s*\d{1,2}-\d{1,2}-20\d{2}",
                folded,
            )
            target_closed = re.search(
                r"convocatorias cerradas.*?investigacion\s*-\s*fondart nacional 2027"
                r".*?plazo de postulacion\s*:\s*\d{1,2}-\d{1,2}-20\d{2}",
                folded,
            )
            open_seen = open_seen or bool(target_open)
            closed_seen = closed_seen or bool(target_closed)
        if open_seen != closed_seen:
            state = "open" if open_seen else "closed"

    deadline = ""
    iso_match = None if role == "official_bases_pdf" else re.search(
        r"\b(?:deadline\s*[=:]\s*)?(20\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b",
        folded,
    )
    if iso_match:
        candidate = f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"
        if _iso_date(candidate) is not None:
            deadline = candidate
    if not deadline and role == "official_index":
        index_match = re.search(
            r"investigacion\s*-\s*fondart nacional 2027\s+plazo de postulacion\s*:\s*"
            r"([0-2]?\d|3[01])-(0?[1-9]|1[0-2])-(20\d{2})",
            folded,
        )
        if index_match:
            candidate = f"{index_match.group(3)}-{int(index_match.group(2)):02d}-{int(index_match.group(1)):02d}"
            if _iso_date(candidate) is not None:
                deadline = candidate
    if not deadline and role != "official_bases_pdf":
        spanish_match = re.search(
            r"\b([0-2]?\d|3[01])\s+de\s+"
            r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
            r"(?:\s+de)?\s+(20\d{2})\b",
            folded,
        )
        if spanish_match:
            candidate = f"{spanish_match.group(3)}-{_MONTHS[spanish_match.group(2)]:02d}-{int(spanish_match.group(1)):02d}"
            if _iso_date(candidate) is not None:
                deadline = candidate
    return {"opportunity_state": state, "deadline": deadline}


def _role_for(receipt: Mapping[str, Any]) -> str:
    declared = str(receipt.get("role") or "").strip()
    if declared in EXPECTED_URLS:
        return declared
    final_url = canonical_url(str(receipt.get("final_url") or receipt.get("url") or ""))
    for role, expected in EXPECTED_URLS.items():
        if final_url == canonical_url(expected):
            return role
    return ""


def _normalize_hash(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return text[7:] if text.startswith("sha256:") else text


def _normalize_receipt(
    raw: Any, *, now: datetime, max_capture_age_seconds: int,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(raw, Mapping):
        return {}, ["receipt_not_object"]
    receipt = copy.deepcopy(dict(raw))
    role = _role_for(receipt)
    if not role:
        errors.append("receipt_role_or_url_unrecognized")
    expected_url = canonical_url(EXPECTED_URLS.get(role, ""))
    requested_url = canonical_url(str(receipt.get("requested_url") or receipt.get("url") or ""))
    final_url = canonical_url(str(receipt.get("final_url") or receipt.get("url") or ""))
    if not requested_url or requested_url != expected_url:
        errors.append("requested_url_mismatch")
    if not final_url or final_url != expected_url:
        errors.append("final_url_mismatch")
    host = (urlsplit(final_url).hostname or "").casefold().rstrip(".")
    if host != "www.fondosdecultura.cl":
        errors.append("final_host_not_official")
    capture_status = str(receipt.get("capture_status") or receipt.get("status") or "").strip().casefold()
    if capture_status not in {"captured", "success", "ok", "verified"}:
        errors.append("capture_status_not_success")
    http_status = receipt.get("http_status")
    if isinstance(http_status, bool) or not isinstance(http_status, int) or not 200 <= http_status < 300:
        errors.append("http_status_not_success")
    text = receipt.get("text", receipt.get("content"))
    if not isinstance(text, str) or not text.strip():
        errors.append("content_missing")
        text = ""
    raw_hash = _normalize_hash(receipt.get("raw_sha256"))
    text_hash = _normalize_hash(receipt.get("text_sha256"))
    if not _HASH_RE.fullmatch(raw_hash):
        errors.append("raw_sha256_invalid")
    if not _HASH_RE.fullmatch(text_hash):
        errors.append("text_sha256_invalid")
    elif text and text_hash != _digest(text):
        errors.append("text_sha256_mismatch")
    retrieved_at = _iso_datetime(receipt.get("retrieved_at") or receipt.get("captured_at"))
    if retrieved_at is None:
        errors.append("retrieved_at_invalid")
    elif retrieved_at > now:
        errors.append("retrieved_at_in_future")
    elif (now - retrieved_at).total_seconds() > max_capture_age_seconds:
        errors.append("capture_stale")
    extracted = extract_official_opportunity_observations(role, text)
    observed_state = extracted["opportunity_state"]
    deadline_text = extracted["deadline"]
    declared_state = _state(receipt.get("opportunity_state"))
    declared_deadline_text = str(receipt.get("deadline") or "").strip()
    declared_deadline = _iso_date(declared_deadline_text)
    if declared_deadline_text and declared_deadline is None:
        errors.append("declared_deadline_invalid")
    if declared_state != "unknown" and declared_state != observed_state:
        errors.append("declared_state_not_supported_by_content")
    if declared_deadline is not None and declared_deadline.isoformat() != deadline_text:
        errors.append("declared_deadline_not_supported_by_content")
    return {
        "role": role,
        "requested_url": requested_url,
        "final_url": final_url,
        "host": host,
        "source_id": source_id_for(final_url) if final_url else "",
        "source_group": AUTHORITY_GROUP,
        "capture_status": capture_status,
        "http_status": http_status,
        "raw_sha256": raw_hash,
        "text_sha256": text_hash,
        "retrieved_at": retrieved_at.isoformat().replace("+00:00", "Z") if retrieved_at else "",
        "opportunity_state": observed_state,
        "deadline": deadline_text,
        "license_state": str(receipt.get("license_state") or "official_public_source_review_pending"),
    }, sorted(set(errors))


def _refresh_jobs(frontier: Any, opportunity_id: str) -> tuple[list[Mapping[str, Any]], list[str]]:
    if not isinstance(frontier, Mapping) or frontier.get("schema") != FRONTIER_SCHEMA:
        return [], ["frontier_schema_invalid"]
    if frontier.get("opportunity_id") != opportunity_id:
        return [], ["frontier_opportunity_id_mismatch"]
    jobs: list[Mapping[str, Any]] = []
    errors: list[str] = []
    for raw in frontier.get("jobs", []) if isinstance(frontier.get("jobs"), list) else []:
        if not isinstance(raw, Mapping):
            continue
        provenance = raw.get("provenance") if isinstance(raw.get("provenance"), Mapping) else {}
        requirement_ids = raw.get("requirement_ids") if isinstance(raw.get("requirement_ids"), list) else []
        expected_requirement = f"source-validity:{opportunity_id}"
        if provenance.get("frontier_kind") == "refresh_source_validity" or expected_requirement in requirement_ids:
            if raw.get("dispatch") is not False or raw.get("status") != "planned_not_dispatched":
                errors.append("refresh_job_not_bounded")
            if raw.get("source_policy") != "official-source-only":
                errors.append("refresh_job_source_policy_invalid")
            if raw.get("independent_source_groups_required") != 1:
                errors.append("refresh_job_independence_policy_invalid")
            if requirement_ids != [expected_requirement]:
                errors.append("refresh_job_requirement_invalid")
            jobs.append(raw)
    if not jobs:
        errors.append("refresh_job_missing")
    return sorted(jobs, key=lambda row: str(row.get("job_id") or "")), sorted(set(errors))


def build_opportunity_validity_capture(
    frontier: Mapping[str, Any],
    receipts: Sequence[Mapping[str, Any]],
    *,
    opportunity_id: str,
    now: str,
    max_capture_age_seconds: int = DEFAULT_MAX_CAPTURE_AGE_SECONDS,
) -> dict[str, Any]:
    """Validate official receipts and return additive, non-promoting evidence."""
    errors: list[str] = []
    now_dt = _iso_datetime(now)
    if now_dt is None:
        now_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        errors.append("now_invalid")
    if isinstance(max_capture_age_seconds, bool) or not isinstance(max_capture_age_seconds, int) or max_capture_age_seconds < 1:
        max_capture_age_seconds = DEFAULT_MAX_CAPTURE_AGE_SECONDS
        errors.append("max_capture_age_seconds_invalid")
    jobs, frontier_errors = _refresh_jobs(frontier, opportunity_id)
    errors.extend(frontier_errors)
    normalized: list[dict[str, Any]] = []
    by_role: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(receipts):
        row, row_errors = _normalize_receipt(raw, now=now_dt, max_capture_age_seconds=max_capture_age_seconds)
        normalized.append(row)
        errors.extend(f"receipt[{index}]:{error}" for error in row_errors)
        role = row.get("role")
        if role:
            if role in by_role:
                errors.append(f"duplicate_role:{role}")
            by_role[role] = row
    missing_roles = sorted(set(EXPECTED_URLS) - set(by_role))
    errors.extend(f"missing_role:{role}" for role in missing_roles)
    state_roles = ("opportunity_page", "official_index")
    for role in state_roles:
        if by_role.get(role, {}).get("opportunity_state") == "unknown":
            errors.append(f"opportunity_state_missing:{role}")
    states = {row["opportunity_state"] for row in by_role.values() if row.get("opportunity_state") != "unknown"}
    deadlines = {row["deadline"] for row in by_role.values() if row.get("deadline")}
    if len(states) > 1:
        errors.append("opportunity_state_conflict")
    if len(deadlines) > 1:
        errors.append("deadline_conflict")
    state = next(iter(states), "unknown") if len(states) <= 1 else "unknown"
    deadline_text = next(iter(deadlines), "") if len(deadlines) <= 1 else ""
    deadline = _iso_date(deadline_text)
    if state == "unknown":
        errors.append("opportunity_state_missing")
    if deadline is None:
        errors.append("deadline_missing")
    evidence_complete = not errors
    if evidence_complete and (state == "closed" or (deadline and now_dt.date() > deadline)):
        validity_status = "expired"
        confirmed = True
    elif evidence_complete and state == "open" and deadline and now_dt.date() <= deadline:
        validity_status = "current_verified"
        confirmed = True
    else:
        validity_status = "observed_local"
        confirmed = False

    sources = [{
        "source_id": row["source_id"],
        "source_group": AUTHORITY_GROUP,
        "url": row["final_url"],
        "raw_sha256": row["raw_sha256"],
        "text_sha256": row["text_sha256"],
        "capture_status": row["capture_status"],
        "license_state": row["license_state"],
    } for row in sorted(normalized, key=lambda item: item.get("role", "")) if row.get("source_id")]
    results: list[dict[str, Any]] = []
    requirement_id = f"source-validity:{opportunity_id}"
    for job in jobs:
        claims: list[dict[str, Any]] = []
        if evidence_complete:
            semantic = {"status": validity_status, "confirmed": confirmed, "deadline": deadline_text}
            claims.append({
                "claim_id": "validity:" + _digest(stable_json({"job_id": job.get("job_id"), **semantic}))[:24],
                "requirement_id": requirement_id,
                "relation": "supports",
                "statement": "Official opportunity validity state and deadline captured",
                "value": semantic,
                "evidence_refs": sorted(
                    f"capture:{row['role']}:{row['text_sha256']}" for row in normalized if row.get("role")
                ),
                "source_ids": sorted(row["source_id"] for row in normalized if row.get("source_id")),
                "extraction_status": "candidate",
            })
        results.append({
            "job_id": str(job.get("job_id") or ""),
            "requirement_id": requirement_id,
            "question": str(job.get("question") or ""),
            "status": "captured" if evidence_complete else "unresolved",
            "sources": copy.deepcopy(sources),
            "claims": claims,
        })
    batch = {
        "schema": RESULT_BATCH_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "independent_source_groups_required": 1,
        "results": sorted(results, key=lambda row: row["job_id"]),
    }
    triangulation = triangulate_research_evidence(frontier, batch)
    supported = bool(triangulation.get("results")) and all(
        row.get("status") == "supported_candidate" for row in triangulation["results"]
    )
    proposals = []
    if supported and confirmed:
        refs = sorted({ref for row in triangulation["results"] for ref in row.get("evidence_refs", [])})
        proposals.append({
            "proposal_id": "opportunity-validity:" + _digest(stable_json({"opportunity_id": opportunity_id, "refs": refs}))[:24],
            "requirement_id": requirement_id,
            "status": "candidate_pending_ingestion",
            "validity": {"status": validity_status, "confirmed": True, "effective_to": deadline_text},
            "evidence_refs": refs,
            "source_groups": [AUTHORITY_GROUP],
            "promotion": "none",
            "training_permitted": False,
        })
    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity_id,
        "validity": {"status": validity_status, "confirmed": confirmed, "effective_to": deadline_text or None},
        "authority": {"group_id": AUTHORITY_GROUP, "host": "www.fondosdecultura.cl", "receipt_count": len(normalized)},
        "receipts": sorted(normalized, key=lambda row: row.get("role", "")),
        "research_result_batch": batch,
        "triangulation": triangulation,
        "additive_evidence": {
            "opportunity_evidence_proposals": proposals,
            "practice_evidence_proposals": [],
            "promotion": "none",
        },
        "control": {
            "network_called": False,
            "dispatch": False,
            "publication": False,
            "submission": False,
            "training_permitted": False,
            "readiness_declared": False,
            "fit_declared": False,
        },
        "errors": sorted(set(errors)),
        "valid": not errors and triangulation.get("valid") is True and supported,
    }


def apply_opportunity_validity_capture(
    opportunity_package: Any, capture: Any,
) -> dict[str, Any]:
    """Apply a validated capture to the matching package source, additively."""
    if not isinstance(opportunity_package, Mapping):
        raise ValueError("opportunity_package_not_object")
    if not isinstance(capture, Mapping) or capture.get("schema") != SCHEMA:
        raise ValueError("validity_capture_schema_invalid")
    if capture.get("valid") is not True or capture.get("errors") != []:
        raise ValueError("validity_capture_not_valid")
    package = copy.deepcopy(dict(opportunity_package))
    opportunity_id = str(package.get("opportunity_id") or "").strip()
    if capture.get("opportunity_id") != opportunity_id:
        raise ValueError("validity_capture_opportunity_id_mismatch")
    source = package.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("opportunity_source_missing")
    bases = [row for row in capture.get("receipts", []) if isinstance(row, Mapping) and row.get("role") == "official_bases_pdf"]
    if len(bases) != 1:
        raise ValueError("validity_capture_bases_receipt_invalid")
    if canonical_url(str(source.get("url") or "")) != canonical_url(str(bases[0].get("final_url") or "")):
        raise ValueError("validity_capture_source_url_mismatch")
    source_hash = _normalize_hash(source.get("sha256"))
    if not source_hash or source_hash != _normalize_hash(bases[0].get("raw_sha256")):
        raise ValueError("validity_capture_source_hash_mismatch")
    validity = capture.get("validity")
    if not isinstance(validity, Mapping) or validity.get("confirmed") is not True:
        raise ValueError("validity_capture_confirmation_missing")
    if validity.get("status") not in {"current_verified", "expired"}:
        raise ValueError("validity_capture_status_invalid")
    source_out = copy.deepcopy(dict(source))
    source_out["validity"] = {
        "status": validity["status"],
        "confirmed": True,
        "effective_to": validity.get("effective_to"),
    }
    package["source"] = source_out
    return package


compile_opportunity_validity_capture = build_opportunity_validity_capture


__all__ = [
    "ALGORITHM_VERSION", "AUTHORITY_GROUP", "BASES_URL", "DEFAULT_MAX_CAPTURE_AGE_SECONDS",
    "EXPECTED_URLS", "INDEX_URL", "OPPORTUNITY_URL", "SCHEMA",
    "build_opportunity_validity_capture", "compile_opportunity_validity_capture",
    "apply_opportunity_validity_capture", "extract_official_opportunity_observations",
    "stable_json",
]
