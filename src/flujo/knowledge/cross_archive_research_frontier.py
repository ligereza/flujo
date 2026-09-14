"""Project cross-archive evidence gaps into the existing Research frontier.

This is a pure bridge.  It does not create a research job, call a provider or
write a database.  A relation candidate becomes a technical research frontier
job only when its own payload declares missing evidence.  The synthetic
``opportunity_id`` is a namespace for the frontier, not an opportunity claim.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json

from tools.research_job_router import ADAPTERS, detect_domain

from .cross_archive_relations import SCHEMA as RELATION_SCHEMA
from .cross_archive_relations import validate_cross_archive_relations_payload_shape


SCHEMA = "mak-research-frontier-jobs-v1"
ALGORITHM_VERSION = "cross-archive-relation-to-research-1"
JOB_STATUS = "planned_not_dispatched"

_TOP_LEVEL_FIELDS = {
    "schema", "algorithm_version", "opportunity_id", "input_hashes", "control",
    "jobs", "abstentions", "rejected_candidates", "adapter_projection",
    "provenance", "reconciliation",
}
_JOB_FIELDS = {
    "job_id", "candidate_id", "opportunity_id", "requirement_ids",
    "research_action_ids", "question", "domain", "priority_rank", "voi",
    "source_policy", "independent_source_groups_required", "status", "dispatch",
    "provenance",
}


class CrossArchiveResearchFrontierError(ValueError):
    """Raised when the cross-archive to Research boundary is invalid."""


def _canonical_relation_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize only order-bearing collections before hashing the input."""
    result = copy.deepcopy(dict(payload))
    for field, key in (("archives", "archive_id"), ("relations", "relation_id")):
        rows = result.get(field)
        if isinstance(rows, list):
            result[field] = sorted(rows, key=lambda row: str(row.get(key, "")))
    if isinstance(result.get("skipped"), list):
        result["skipped"] = sorted(result["skipped"], key=stable_json)
    return result


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _sorted_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise CrossArchiveResearchFrontierError(f"{field}_not_list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise CrossArchiveResearchFrontierError(f"{field}_invalid")
    result = sorted(set(value))
    if result != value:
        raise CrossArchiveResearchFrontierError(f"{field}_not_sorted_unique")
    return result


def _relation_inputs(payload: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], set[str]]:
    if not isinstance(payload, Mapping) or not validate_cross_archive_relations_payload_shape(payload):
        raise CrossArchiveResearchFrontierError("relation_payload_invalid")
    if payload.get("schema") != RELATION_SCHEMA:
        raise CrossArchiveResearchFrontierError("relation_schema_invalid")
    relations = payload.get("relations")
    archives = payload.get("archives")
    if not isinstance(relations, list) or not isinstance(archives, list):
        raise CrossArchiveResearchFrontierError("relation_collections_invalid")
    archive_ids: set[str] = set()
    for index, archive in enumerate(archives):
        if not isinstance(archive, Mapping) or not _text(archive.get("archive_id")):
            raise CrossArchiveResearchFrontierError(f"archive_{index}_invalid")
        archive_id = _text(archive["archive_id"])
        if archive_id in archive_ids:
            raise CrossArchiveResearchFrontierError(f"duplicate_archive_id:{archive_id}")
        archive_ids.add(archive_id)
    result: list[Mapping[str, Any]] = []
    relation_ids: set[str] = set()
    required = {
        "relation_id", "source_archive_id", "source_ref", "target_archive_id",
        "target_ref", "relation", "work_id", "status", "evidence_refs",
        "evidence_for", "evidence_against", "missing_evidence", "next_probe",
        "alternatives",
    }
    for index, relation in enumerate(relations):
        if not isinstance(relation, Mapping) or set(relation) < required:
            raise CrossArchiveResearchFrontierError(f"relation_{index}_invalid")
        relation_id = _text(relation.get("relation_id"))
        if not relation_id or relation_id in relation_ids:
            raise CrossArchiveResearchFrontierError(f"relation_id_invalid:{relation_id}")
        relation_ids.add(relation_id)
        if _text(relation.get("source_archive_id")) not in archive_ids:
            raise CrossArchiveResearchFrontierError(f"relation_{index}_source_archive_unknown")
        if _text(relation.get("target_archive_id")) not in archive_ids:
            raise CrossArchiveResearchFrontierError(f"relation_{index}_target_archive_unknown")
        for field in ("source_ref", "target_ref", "relation", "work_id", "status"):
            if not _text(relation.get(field)):
                raise CrossArchiveResearchFrontierError(f"relation_{index}_{field}_required")
        if relation.get("status") != "candidate":
            raise CrossArchiveResearchFrontierError(f"relation_{index}_status_invalid")
        _sorted_strings(relation.get("evidence_refs"), f"relation_{index}.evidence_refs")
        _sorted_strings(relation.get("missing_evidence"), f"relation_{index}.missing_evidence")
        _sorted_strings(relation.get("alternatives"), f"relation_{index}.alternatives")
        if not isinstance(relation.get("evidence_for"), list) or not isinstance(relation.get("evidence_against"), list):
            raise CrossArchiveResearchFrontierError(f"relation_{index}_evidence_invalid")
        if relation.get("missing_evidence") and not _text(relation.get("next_probe")):
            raise CrossArchiveResearchFrontierError(f"relation_{index}_next_probe_required")
        result.append(relation)
    return result, relation_ids


def _catalog_title(relations: Sequence[Mapping[str, Any]], work_id: str) -> str:
    titles: set[str] = set()
    for relation in relations:
        for evidence in relation.get("evidence_for", []):
            if isinstance(evidence, Mapping) and evidence.get("kind") == "catalog_track":
                title = _text(evidence.get("title"))
                if title:
                    titles.add(title)
    if len(titles) > 1:
        raise CrossArchiveResearchFrontierError(f"work_title_conflict:{work_id}")
    return next(iter(titles), work_id)


def _job_id(semantics: Mapping[str, Any]) -> str:
    return "cross-research-job:" + hashlib.sha256(stable_json(semantics).encode("utf-8")).hexdigest()[:32]


def compile_cross_archive_research_frontier(
    relation_payload: Mapping[str, Any], *, _validate: bool = True,
) -> dict[str, Any]:
    relations, relation_ids = _relation_inputs(relation_payload)
    relation_hash = _hash(_canonical_relation_payload(relation_payload))
    opportunity_id = "cross-archive:" + relation_hash.removeprefix("sha256:")[:32]
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for relation in relations:
        if not relation.get("missing_evidence"):
            continue
        pair = tuple(sorted((
            _text(relation["source_archive_id"]),
            _text(relation["target_archive_id"]),
        )))
        key = (_text(relation["work_id"]), pair[0], pair[1])
        groups.setdefault(key, []).append(relation)

    jobs: list[dict[str, Any]] = []
    relation_ids_with_jobs: set[str] = set()
    for rank, (key, rows) in enumerate(sorted(groups.items()), 1):
        work_id, source_archive_id, target_archive_id = key
        rows = sorted(rows, key=lambda row: _text(row["relation_id"]))
        title = _catalog_title(rows, work_id)
        probes = sorted({_text(row["next_probe"]) for row in rows if _text(row.get("next_probe"))})
        if not probes:
            raise CrossArchiveResearchFrontierError(f"group_next_probe_missing:{work_id}")
        question = (
            f"Verificar la vinculacion exacta de entrega o publicacion de la "
            f"colaboracion del artista y obra '{title}' entre los archivos "
            f"'{source_archive_id}' y '{target_archive_id}'. " + " ".join(probes)
        )
        domain, scores = detect_domain(question)
        adapter = ADAPTERS[domain]
        candidate_id = f"cross-relation-group:{work_id}:{source_archive_id}:{target_archive_id}"
        requirement_id = f"relation-binding:{work_id}"
        relation_row_ids = sorted({_text(row["relation_id"]) for row in rows})
        semantics = {
            "candidate_id": candidate_id,
            "opportunity_id": opportunity_id,
            "requirement_ids": [requirement_id],
            "research_action_ids": [],
            "question": question,
            "domain": domain,
            "relation_ids": relation_row_ids,
        }
        job = {
            "job_id": _job_id(semantics),
            "candidate_id": candidate_id,
            "opportunity_id": opportunity_id,
            "requirement_ids": [requirement_id],
            "research_action_ids": [],
            "question": question,
            "domain": domain,
            "priority_rank": rank,
            "voi": {"value": None, "status": "unresolved", "numerator": None, "denominator": None},
            "source_policy": adapter["source_policy"],
            "independent_source_groups_required": 2,
            "status": JOB_STATUS,
            "dispatch": False,
            "provenance": {
                "source_relation_schema": RELATION_SCHEMA,
                "source_relation_hash": relation_hash,
                "relation_ids": relation_row_ids,
                "evidence_refs": sorted({ref for row in rows for ref in row["evidence_refs"]}),
                "missing_evidence": sorted({ref for row in rows for ref in row["missing_evidence"]}),
                "domain_source": "research_job_router.detect_domain",
                "domain_scores": scores,
                "adapter_projection": {
                    "question": question,
                    "domain": domain,
                    "source_policy": adapter["source_policy"],
                    "constraint_policy": adapter["constraint_policy"],
                    "create_job_compatible": True,
                    "create_job_invoked": False,
                },
                "frontier_kind": "cross_archive_relation",
                "dispatch": False,
                "create_job_invoked": False,
            },
        }
        jobs.append(job)
        relation_ids_with_jobs.update(relation_row_ids)
    jobs.sort(key=lambda row: row["job_id"])
    abstentions = [
        {"relation_id": _text(row["relation_id"]), "reason": "no_missing_evidence_declared"}
        for row in relations if _text(row["relation_id"]) not in relation_ids_with_jobs
    ]
    abstentions.sort(key=lambda row: row["relation_id"])
    output = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity_id,
        "input_hashes": {"cross_archive_relations": relation_hash},
        "control": {
            "all_dispatch_disabled": True,
            "input_valid": True,
            "database_write": False,
            "network_called": False,
            "promotion": "none",
        },
        "jobs": jobs,
        "abstentions": abstentions,
        "rejected_candidates": [],
        "adapter_projection": [
            {
                "job_id": job["job_id"],
                "question": job["question"],
                "domain": job["domain"],
                "source_policy": job["source_policy"],
                "constraint_policy": job["provenance"]["adapter_projection"]["constraint_policy"],
                "create_job_compatible": True,
                "create_job_invoked": False,
            }
            for job in jobs
        ],
        "provenance": {
            "source_schema": RELATION_SCHEMA,
            "source_relation_hash": relation_hash,
            "opportunity_id_is_namespace_only": True,
            "source_rescan": False,
            "database_write": False,
            "network_called": False,
            "promotion": "none",
        },
        "reconciliation": {
            "relation_count": len(relations),
            "relation_ids_unique": len(relation_ids) == len(relations),
            "relations_with_jobs": len(relation_ids_with_jobs),
            "relations_without_jobs": len(relations) - len(relation_ids_with_jobs),
            "job_count": len(jobs),
            "job_ids_unique": len({job["job_id"] for job in jobs}) == len(jobs),
            "dispatch_count": 0,
            "truth_promotions": 0,
            "deterministic_order": True,
            "relation_loss": 0,
        },
    }
    if _validate:
        validate_cross_archive_research_frontier(output, relation_payload)
    return output


def validate_cross_archive_research_frontier(
    payload: Mapping[str, Any], relation_payload: Mapping[str, Any],
) -> bool:
    """Strictly validate the bridge output against its relation input."""
    try:
        expected = compile_cross_archive_research_frontier(relation_payload, _validate=False)
    except (CrossArchiveResearchFrontierError, TypeError, ValueError):
        return False
    if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
        return False
    if stable_json(payload) != stable_json(expected):
        return False
    for job in payload.get("jobs", []):
        if set(job) != _JOB_FIELDS:
            return False
        if job.get("status") != JOB_STATUS or job.get("dispatch") is not False:
            return False
        if not isinstance(job.get("requirement_ids"), list) or not job["requirement_ids"]:
            return False
        if not isinstance(job.get("research_action_ids"), list):
            return False
        if not isinstance(job.get("provenance"), Mapping):
            return False
        if job["provenance"].get("dispatch") is not False:
            return False
    return True


__all__ = [
    "SCHEMA",
    "ALGORITHM_VERSION",
    "CrossArchiveResearchFrontierError",
    "compile_cross_archive_research_frontier",
    "validate_cross_archive_research_frontier",
]
