"""Build a read-only, evidence-first order of the existing PortableSSD index.

This is a projection over artifacts that already exist.  It does not scan the
SSD, write any source database, move files, or turn a directory name into
authorship.  The order is a review order: it says which evidence-backed
project units should be inspected first and which rows must remain unresolved.

The projection deliberately keeps the SSD and ISKVW as separate contexts.  A
crosswalk is reported only when an explicit typed reference exists; a matching
word, basename, or media shape is not enough.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from .product_view import stable_json


SCHEMA = "mak-ssd-order-foundation-v1"
ALGORITHM_VERSION = "evidence-first-order-2-operator-dossier"

# Read-only corroboration sources for the operator frontier.  They are optional:
# when a path is absent the dossier degrades to ``missing_evidence`` instead of
# guessing.  They are never written, rescanned or promoted to identity.
DEFAULT_TIE_DB = Path("/home/mak/.claude/jobs/3428381a/tmp/ties_full.db")
DEFAULT_DECLARED_INPUTS = Path("/home/mak/.claude/jobs/3428381a/tmp/declared_inputs.json")
DEFAULT_BLEND_TARGETS = Path("/home/mak/.claude/jobs/3428381a/tmp/blend_dependency_targets.json")

# SHA-256 of the empty byte string.  A "shared content class" of zero bytes is a
# filesystem coincidence, never shared artistic material.
EMPTY_CONTENT_ID = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

_MAX_CLASS_SAMPLES = 5
_MAX_ASSET_SAMPLES = 3
_MAX_PROJECT_SAMPLES = 5
_MAX_MEMBER_PATHS = 25
_MAX_RELATION_ROWS = 6

# Tier names are the order projection's own vocabulary; this module reproduces
# the assignment from the byte ledger instead of re-deciding it.
TIER_LOOSE_ROOT = "T1_loose_copy_at_disk_root"
TIER_CROSSES_ROOTS = "T2_crosses_roots_needs_an_answer"
TIER_INSIDE_ONE_PROJECT = "T3_inside_one_project_left_alone"


class SSDOrderFoundationError(ValueError):
    """Existing sources cannot support a conservative order projection."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_ref(path: Path, *, include_hash: bool = True) -> dict[str, Any]:
    if not path.is_file():
        raise SSDOrderFoundationError(f"source_missing:{path}")
    stat = path.stat()
    result: dict[str, Any] = {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "read_only": True,
    }
    if include_hash:
        result["sha256"] = _sha256(path)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SSDOrderFoundationError(f"json_source_invalid:{path}") from exc
    if not isinstance(value, dict):
        raise SSDOrderFoundationError(f"json_source_not_object:{path}")
    return value


def _ro(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise SSDOrderFoundationError(f"source_missing:{path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _one(con: sqlite3.Connection, query: str, args: tuple[Any, ...] = ()) -> Any:
    row = con.execute(query, args).fetchone()
    return None if row is None else row[0]


def _authority(authority_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(authority_path)
    containers = payload.get("containers")
    if not isinstance(containers, Mapping):
        raise SSDOrderFoundationError("research_authority_containers_missing")
    result: dict[str, dict[str, Any]] = {}
    for key, raw in containers.items():
        if isinstance(raw, Mapping):
            result[str(key)] = {
                "kind": raw.get("kind", ""),
                "confidence": raw.get("confidence", ""),
                "canonical_name": raw.get("canonical_name", ""),
                "evidence_urls": sorted(str(url) for url in raw.get("evidence_urls", []) if url),
            }
    return result


def _reconstruction_roles(directory: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    roles: dict[str, dict[str, Any]] = {}
    refs: list[dict[str, Any]] = []
    if not directory.is_dir():
        return roles, refs
    for path in sorted(directory.glob("*/reconstruction.json")):
        payload = _read_json(path)
        scope = str(payload.get("scope") or "")
        summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
        ref = {
            "path": str(path),
            "sha256": _sha256(path),
            "scope": scope,
            "schema": payload.get("schema", ""),
            "summary": {
                "baseline_rows": summary.get("baseline_rows", 0),
                "relations": summary.get("relations", 0),
                "unknown_decisions": summary.get("unknown_decisions", 0),
                "unknown_relations": summary.get("unknown_relations", 0),
                "balanced": (summary.get("reconciliation") or {}).get("balanced"),
            },
        }
        refs.append(ref)
        decisions = payload.get("decisions")
        if isinstance(decisions, Mapping):
            for project_path, decision in decisions.items():
                if not isinstance(decision, Mapping):
                    continue
                roles[str(project_path)] = {
                    "role": str(decision.get("role") or ""),
                    "epistemic_status": str(decision.get("epistemic_status") or ""),
                    "rule": str(decision.get("rule") or ""),
                    "source_ref": f"{path}#/decisions/{project_path}",
                }
    return roles, refs


def _knowledge_records(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    """Index existing Project IR by its declared title; never infer by path tokens."""
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    episodes: dict[str, int] = Counter()
    con = _ro(path)
    try:
        for row in con.execute(
            "SELECT project_id,title,state,source_root_ref,fingerprint FROM project_records"
        ):
            record = dict(row)
            by_title[str(record.get("title") or "")].append({
                "project_id": str(record["project_id"]),
                "state": str(record.get("state") or ""),
                "source_root_ref": str(record.get("source_root_ref") or ""),
                "fingerprint": str(record.get("fingerprint") or ""),
            })
        for row in con.execute(
            "SELECT project_id,count(*) AS count FROM project_episodes GROUP BY project_id"
        ):
            episodes[str(row["project_id"])] = int(row["count"])
    finally:
        con.close()
    return by_title, dict(episodes)


def _basename(value: Any) -> str:
    """Return a locator basename without treating its path as semantics."""
    text = str(value or "").replace("\\", "/")
    return text.rsplit("/", 1)[-1]


def _crosswalk_binding_lookup(
    *,
    index_path: Path,
    knowledge_path: Path,
    intake_path: Path | None,
    asset_ids: set[str],
    piece_refs: set[str],
    piece_ids: set[str],
    locators: set[str],
) -> dict[str, Any]:
    """Search every existing base for a real typed reference behind a locator.

    A locator that merely appears inside a generated filename is recorded as a
    derived echo, never as a reference.  The point of this lookup is to be able
    to say ``typed_reference_count=0`` as a measured result instead of an
    assumption.
    """
    con = _ro(index_path)
    try:
        asset_state = {
            str(row["asset_id"]): {
                "hash_state": str(row["hash_state"] or ""),
                "has_full_sha256": bool(row["full_sha256"]),
                "has_sample_sha256": bool(row["sample_sha256"]),
                "bytes": int(row["bytes"] or 0),
                "media_kind": str(row["media_kind"] or ""),
            }
            for row in con.execute(
                "SELECT asset_id,hash_state,full_sha256,sample_sha256,bytes,media_kind "
                "FROM assets")
            if str(row["asset_id"]) in asset_ids
        }
        relation_hits: Counter[str] = Counter()
        for row in con.execute("SELECT left_id,right_id FROM relations"):
            for ref in (str(row["left_id"]), str(row["right_id"])):
                if ref in asset_ids:
                    relation_hits[ref] += 1
    finally:
        con.close()

    echoes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    relation_refs: dict[str, list[str]] = defaultdict(list)
    scanned: list[str] = []
    if knowledge_path.is_file():
        kcon = _ro(knowledge_path)
        try:
            tables = {
                str(row[0]) for row in kcon.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "artifacts" in tables:
                scanned.append(f"{knowledge_path}#artifacts")
                for locator in sorted(locators):
                    for row in kcon.execute(
                        "SELECT relative_path,name,sha256,declared_work_id,artifact_kind "
                        "FROM artifacts WHERE name LIKE ? ORDER BY relative_path",
                        (f"%{locator}%",),
                    ):
                        echoes[locator].append({
                            "kind": "derived_locator_echo",
                            "relative_path": str(row["relative_path"] or ""),
                            "artifact_kind": str(row["artifact_kind"] or ""),
                            "has_sha256": bool(row["sha256"]),
                            "declared_work_id": str(row["declared_work_id"] or ""),
                            "is_typed_reference": False,
                            "reason": (
                                "the locator appears inside a generated filename; a filename "
                                "substring is not a reference to the SSD asset"
                            ),
                            "source_ref": f"{knowledge_path}#artifacts/{row['relative_path']}",
                        })
            for table in ("entity_relations", "context_relations", "project_artifacts"):
                if table not in tables:
                    continue
                scanned.append(f"{knowledge_path}#{table}")
                columns = [
                    str(row[1]) for row in kcon.execute(f"PRAGMA table_info({table})")
                ]
                text_columns = [
                    name for name in columns
                    if name.lower().endswith(("_id", "_ref", "path", "json", "key", "kind"))
                ]
                if not text_columns:
                    continue
                needles = sorted(asset_ids | piece_refs)
                clause = " OR ".join(
                    f"{name} LIKE ?" for name in text_columns for _ in (0,)
                )
                for needle in needles:
                    params = tuple(f"%{needle}%" for _ in text_columns)
                    for _ in kcon.execute(
                        f"SELECT 1 FROM {table} WHERE {clause} LIMIT 1", params
                    ):
                        relation_refs[needle].append(f"{knowledge_path}#{table}")
        finally:
            kcon.close()
    # The existing operational link tables do carry ISKVW piece ids.  Read them
    # and classify them, because the honest answer is not "nothing matched" but
    # "these matched and here is why none of them binds".
    link_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for store_path, table, project_column in (
        (intake_path, "mak_links", "project_id"),
        (knowledge_path, "operational_curation_links", "project_record_id"),
    ):
        if store_path is None or not store_path.is_file():
            continue
        lcon = _ro(store_path)
        try:
            names = {
                str(row[0]) for row in lcon.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
            }
            if table not in names:
                continue
            scanned.append(f"{store_path}#{table}")
            for piece_id in sorted(piece_ids):
                for row in lcon.execute(
                    f"SELECT {project_column} AS project_ref,relation,mak_path,confidence,"
                    f"evidence_json FROM {table} WHERE mak_path LIKE ? ORDER BY mak_path",
                    (f"%{piece_id}%",),
                ):
                    try:
                        evidence = json.loads(row["evidence_json"] or "{}")
                    except json.JSONDecodeError:
                        evidence = {}
                    method = str((evidence or {}).get("method") or "")
                    link_rows[piece_id].append({
                        "kind": "operational_possible_link",
                        "store_ref": f"{store_path}#{table}",
                        "relation": str(row["relation"] or ""),
                        "project_ref": str(row["project_ref"] or ""),
                        "mak_path": str(row["mak_path"] or ""),
                        "confidence": row["confidence"],
                        "declared_method": method,
                        "endpoint_is_a_crosswalk_ssd_asset": False,
                        "is_typed_reference": False,
                        "reason": (
                            f"the link is '{row['relation']}' at confidence "
                            f"{row['confidence']} whose declared method is '{method}'; its "
                            f"left endpoint is an intake project, not one of the crosswalk "
                            f"SSD assets, and a path token is not evidence of a work"
                        ),
                    })
        finally:
            lcon.close()
    for rows in link_rows.values():
        rows.sort(key=lambda item: (item["store_ref"], item["mak_path"]))
    return {
        "asset_state": asset_state,
        "index_relation_hits": dict(relation_hits),
        "derived_locator_echoes": {key: value for key, value in echoes.items()},
        "operational_possible_links": dict(link_rows),
        "typed_reference_refs": {key: sorted(set(value)) for key, value in relation_refs.items()},
        "bases_scanned": sorted(set(scanned + [f"{index_path}#relations"])),
    }


def _archive_crosswalk(
    archive_path: Path,
    index_path: Path,
    research_corpus_dir: Path | None = None,
    knowledge_path: Path | None = None,
    intake_path: Path | None = None,
) -> dict[str, Any]:
    payload = _read_json(archive_path)
    pieces = payload.get("piezas")
    links = payload.get("vinculos")
    if not isinstance(pieces, list) or not isinstance(links, list):
        raise SSDOrderFoundationError("iskvw_archive_shape_invalid")

    # The only admissible bridge here is a repeated external media locator
    # already present in both source records.  It is a candidate locator
    # relation, never a work, authorship, publication or delivery claim.
    con = _ro(index_path)
    try:
        assets_by_basename: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in con.execute(
            "SELECT asset_id,relative_path,bytes,hash_state,full_sha256,sample_sha256 "
            "FROM assets"
        ):
            asset = dict(row)
            assets_by_basename[_basename(asset["relative_path"])].append(asset)
    finally:
        con.close()

    candidates: list[dict[str, Any]] = []
    for piece_index, row in enumerate(pieces):
        if not isinstance(row, Mapping):
            continue
        media = row.get("medio") if isinstance(row.get("medio"), Mapping) else {}
        extra = row.get("extra") if isinstance(row.get("extra"), Mapping) else {}
        original = extra.get("fuente_original") if isinstance(extra.get("fuente_original"), Mapping) else {}
        media_src = _basename(media.get("src"))
        original_route = _basename(original.get("ruta"))
        if not media_src or media_src != original_route:
            continue
        assets = assets_by_basename.get(media_src, [])
        if not assets:
            continue
        piece_id = str(row.get("id") or "")
        if not piece_id:
            continue
        iskvw_declaration = {
            "piece_class": str(row.get("clase") or ""),
            "piece_state": str(row.get("estado") or ""),
            "media_type": str(media.get("tipo") or ""),
            "source_original_state": str(original.get("estado") or ""),
            "source_original_role": str(original.get("rol") or ""),
            "carries_content_hash": any(
                key in row or key in media or key in extra
                for key in ("sha256", "hash", "checksum")
            ),
            "source_ref": f"{archive_path}#/piezas/{piece_index}",
            "note": (
                "a role declared on the ISKVW side describes that projection only; it does "
                "not bind the SSD asset and is not a delivery receipt"
            ),
        }
        for asset in assets:
            relation_basis = {
                "piece_id": piece_id,
                "asset_id": str(asset["asset_id"]),
                "external_locator": media_src,
                "relation_type": "same_external_media_locator",
            }
            corpus_ref = None
            corpus_sha256 = None
            if research_corpus_dir is not None:
                corpus_path = research_corpus_dir / f"{piece_id}.md"
                if corpus_path.is_file():
                    corpus_ref = str(corpus_path)
                    corpus_sha256 = _sha256(corpus_path)
            evidence_refs = [
                f"{archive_path}#/piezas/{piece_index}/medio/src",
                f"{archive_path}#/piezas/{piece_index}/extra/fuente_original/ruta",
                f"{index_path}#assets/{asset['asset_id']}",
            ]
            if corpus_ref:
                evidence_refs.append(corpus_ref)
            candidates.append({
                "relation_id": "ssd-iskvw-locator:" + hashlib.sha256(
                    stable_json(relation_basis).encode("utf-8")
                ).hexdigest()[:32],
                "relation_type": "same_external_media_locator",
                "status": "candidate",
                "ssd_artifact_ref": "ssd_asset_" + str(asset["asset_id"])[:40],
                "ssd_index_asset_id": str(asset["asset_id"]),
                "iskvw_source_ref": f"iskvw:piece:{piece_id}",
                "external_locator": media_src,
                "evidence_refs": sorted(evidence_refs),
                "evidence_for": [
                    "ISKVW media.src and fuente_original.ruta share the same external locator",
                    "SSD index contains one asset with that exact locator basename",
                    *(["Research corpus preserves the same ISKVW locator" ] if corpus_ref else []),
                ],
                "evidence_against": [
                    "SSD full hash is unavailable or not a shared source receipt",
                    "ISKVW source media is marked absent",
                    "Research corpus is derived from ISKVW and is not an independent source",
                    "locator does not establish authorship, publication, delivery or work identity",
                ],
                "missing_evidence": ["full_content_hash_or_delivery_receipt"],
                "selection_eligible": False,
                "ssd_hash_state": str(asset.get("hash_state") or ""),
                "ssd_sample_sha256": asset.get("sample_sha256"),
                "research_corpus_ref": corpus_ref,
                "research_corpus_sha256": corpus_sha256,
                "iskvw_declaration": iskvw_declaration,
            })
    candidates.sort(key=lambda row: row["relation_id"])
    piece_ids = {row["iskvw_source_ref"] for row in candidates}
    asset_ids = {row["ssd_index_asset_id"] for row in candidates}

    # Cycle 4: prove the binding is absent instead of asserting it.
    lookup = _crosswalk_binding_lookup(
        index_path=index_path,
        knowledge_path=knowledge_path if knowledge_path is not None else Path("/nonexistent"),
        intake_path=intake_path,
        asset_ids=asset_ids,
        piece_refs=piece_ids,
        piece_ids={ref.split("iskvw:piece:", 1)[-1] for ref in piece_ids},
        locators={row["external_locator"] for row in candidates},
    )
    typed_reference_total = 0
    shared_hash_total = 0
    delivery_receipt_total = 0
    echo_total = 0
    link_total = 0
    for row in candidates:
        asset_state = lookup["asset_state"].get(row["ssd_index_asset_id"], {})
        declaration = row["iskvw_declaration"]
        echoes = lookup["derived_locator_echoes"].get(row["external_locator"], [])
        echo_total += len(echoes)
        piece_id = row["iskvw_source_ref"].split("iskvw:piece:", 1)[-1]
        possible_links = lookup["operational_possible_links"].get(piece_id, [])
        link_total += len(possible_links)
        typed_refs = sorted(set(
            lookup["typed_reference_refs"].get(row["ssd_index_asset_id"], [])
            + lookup["typed_reference_refs"].get(row["iskvw_source_ref"], [])
        ))
        index_hits = int(lookup["index_relation_hits"].get(row["ssd_index_asset_id"], 0))
        shared_hash = bool(asset_state.get("has_full_sha256")) and declaration["carries_content_hash"]
        if shared_hash:
            shared_hash_total += 1
        receipt = bool(typed_refs) and declaration["source_original_state"] not in {"ausente", ""}
        if receipt:
            delivery_receipt_total += 1
        is_typed = bool(typed_refs) or index_hits > 0
        if is_typed:
            typed_reference_total += 1
        row["binding_check"] = {
            "content_hash": {
                "shared_content_hash": shared_hash,
                "ssd_hash_state": asset_state.get("hash_state", ""),
                "ssd_has_full_sha256": bool(asset_state.get("has_full_sha256")),
                "ssd_has_sample_sha256": bool(asset_state.get("has_sample_sha256")),
                "iskvw_carries_content_hash": declaration["carries_content_hash"],
                "reason": (
                    "both sides expose a full content hash and they match"
                    if shared_hash else
                    "no full content hash is available on at least one side, so byte identity "
                    "between the SSD asset and the ISKVW piece cannot be computed"
                ),
                "source_refs": sorted({
                    f"{index_path}#assets/{row['ssd_index_asset_id']}",
                    declaration["source_ref"],
                }),
            },
            "delivery_receipt": {
                "present": receipt,
                "iskvw_piece_state": declaration["piece_state"],
                "iskvw_source_original_state": declaration["source_original_state"],
                "iskvw_source_original_role": declaration["source_original_role"],
                "reason": (
                    "a receipt binding the SSD asset to a delivery was found"
                    if receipt else
                    "the ISKVW source media is marked absent and no base carries a delivery, "
                    "publication or contract receipt for this pair"
                ),
                "source_ref": declaration["source_ref"],
            },
            "typed_reference": {
                "is_typed_reference": is_typed,
                "index_relations_touching_asset": index_hits,
                "typed_reference_refs": typed_refs,
                "derived_locator_echo_count": len(echoes),
                "derived_locator_echoes": echoes[:_MAX_ASSET_SAMPLES],
                "operational_possible_link_count": len(possible_links),
                "operational_possible_links": possible_links[:_MAX_ASSET_SAMPLES],
                "bases_scanned": lookup["bases_scanned"],
                "reason": (
                    "a typed reference was located in an existing base"
                    if is_typed else
                    "no base carries a typed reference between the SSD asset and the ISKVW "
                    "piece; a locator inside a generated filename is not a reference"
                ),
            },
            "research_corpus": {
                "ref": row.get("research_corpus_ref"),
                "sha256": row.get("research_corpus_sha256"),
                "derived_from_iskvw": True,
                "independent_confirmation": False,
                "reason": (
                    "the corpus note is generated from the same ISKVW projection, so it "
                    "repeats the locator instead of confirming it"
                ),
            },
            "verdict": "candidate",
            "selection_eligible": False,
        }
        if possible_links:
            row["evidence_against"] = sorted(set(row["evidence_against"]) | {
                f"{len(possible_links)} pre-existing operational link(s) name this ISKVW "
                f"piece, but their declared method is a path token and their endpoint is an "
                f"intake project rather than the SSD asset",
            })
        row["evidence_against"] = sorted(set(row["evidence_against"]) | {
            f"SSD asset hash_state is '{asset_state.get('hash_state', 'unknown')}' with no full content hash",
            f"ISKVW fuente_original.estado is '{declaration['source_original_state']}'",
            "no typed reference exists in any scanned base",
        })
        row["missing_evidence"] = sorted(set(row["missing_evidence"]) | {
            "full_content_hash_on_both_sides",
            "delivery_or_publication_receipt",
            "typed_relation_in_an_existing_base",
        })
    unique_one_to_one = (
        len(candidates) == len(piece_ids) == len(asset_ids)
        and bool(candidates)
    )
    status = "candidate" if candidates else "unresolved"
    return {
        "status": status,
        "typed_reference_count": typed_reference_total,
        "binding_audit": {
            "candidates_checked": len(candidates),
            "with_shared_content_hash": shared_hash_total,
            "with_delivery_receipt": delivery_receipt_total,
            "with_typed_reference": typed_reference_total,
            "derived_locator_echoes": echo_total,
            "operational_possible_links": link_total,
            "operational_possible_link_classes": dict(sorted(Counter(
                f"{link['relation']}/{link['declared_method']}"
                for rows in lookup["operational_possible_links"].values()
                for link in rows
            ).items())),
            "bases_scanned": lookup["bases_scanned"],
            "ssd_hash_states": dict(sorted(Counter(
                lookup["asset_state"].get(row["ssd_index_asset_id"], {}).get("hash_state", "")
                for row in candidates
            ).items())),
            "iskvw_source_original_states": dict(sorted(Counter(
                row["iskvw_declaration"]["source_original_state"] for row in candidates
            ).items())),
            "iskvw_source_original_roles": dict(sorted(Counter(
                row["iskvw_declaration"]["source_original_role"] for row in candidates
            ).items())),
            "conclusion": (
                "measured, not assumed: no candidate reaches a content hash, a delivery "
                "receipt or a typed reference, so every row stays a candidate"
                if not (shared_hash_total or delivery_receipt_total or typed_reference_total)
                else "at least one candidate now carries binding evidence and must be reviewed"
            ),
        },
        "candidate_relation_count": len(candidates),
        "candidate_piece_count": len(piece_ids),
        "candidate_asset_count": len(asset_ids),
        "research_corpus_match_count": sum(
            bool(row.get("research_corpus_ref")) for row in candidates
        ),
        "unique_one_to_one": unique_one_to_one,
        "reason": (
            "exact external media locators yield candidate SSD↔ISKVW relations; "
            "they remain non-authoritative until content or delivery evidence binds them"
            if candidates else
            "no typed SSD↔ISKVW reference or exact external media locator candidate"
        ),
        "archive_ref": str(archive_path),
        "archive_sha256": _sha256(archive_path),
        "archive_piece_count": len(pieces),
        "archive_link_count": len(links),
        "index_ref": str(index_path),
        "evidence_samples": candidates[:5],
        "candidate_relations": candidates,
    }


def _tie_evidence(ties_path: Path) -> dict[str, Any] | None:
    """Load the existing byte-identity ledger read-only.

    Returns ``None`` when the source is absent so the frontier degrades to an
    explicit evidence gap instead of inventing a corroboration.
    """
    if not ties_path.is_file():
        return None
    con = _ro(ties_path)
    try:
        classes: dict[str, dict[str, Any]] = {}
        for row in con.execute(
            "SELECT content_id,member_count,bytes_each,total_bytes,distinct_roots,"
            "roots_json,extensions_json,crosses_roots FROM identity_class"
        ):
            record = dict(row)
            content_id = str(record["content_id"])
            try:
                roots = sorted(str(value) for value in json.loads(record["roots_json"] or "[]"))
                extensions = sorted(str(value) for value in json.loads(record["extensions_json"] or "[]"))
            except json.JSONDecodeError as exc:
                raise SSDOrderFoundationError(f"tie_class_roots_invalid:{content_id}") from exc
            classes[content_id] = {
                "content_id": content_id,
                "member_count": int(record["member_count"] or 0),
                "bytes_each": int(record["bytes_each"] or 0),
                "total_bytes": int(record["total_bytes"] or 0),
                "distinct_roots": int(record["distinct_roots"] or 0),
                "roots": roots,
                "extensions": extensions,
                "crosses_roots": bool(record["crosses_roots"]),
            }
        by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
        appledouble: set[str] = set()
        for row in con.execute(
            "SELECT asset_id,relative_path,container_root,bytes,content_id,verdict,"
            "is_appledouble FROM identity_asset"
        ):
            record = dict(row)
            content_id = str(record["content_id"] or "")
            if not content_id:
                continue
            if int(record["is_appledouble"] or 0):
                appledouble.add(content_id)
            by_class[content_id].append({
                "asset_id": str(record["asset_id"]),
                "relative_path": str(record["relative_path"] or ""),
                "container_root": str(record["container_root"] or ""),
                "bytes": int(record["bytes"] or 0),
                "verdict": str(record["verdict"] or ""),
            })
        run_ids = sorted(str(row[0]) for row in con.execute("SELECT run_id FROM identity_run"))
    finally:
        con.close()
    for members in by_class.values():
        members.sort(key=lambda member: (member["container_root"], member["relative_path"], member["asset_id"]))
    # Reproduce the order projection's tier rule from the ledger itself: a class
    # that crosses roots and keeps a member directly at the volume root is the
    # loose-copy tier; the rest of the crossing classes need an answer.
    tier_counts: Counter[str] = Counter()
    for content_id, record in classes.items():
        members = by_class.get(content_id, ())
        if not record["crosses_roots"]:
            tier = TIER_INSIDE_ONE_PROJECT
        elif any("/" not in member["relative_path"] for member in members):
            tier = TIER_LOOSE_ROOT
        else:
            tier = TIER_CROSSES_ROOTS
        record["identity_tier"] = tier
        tier_counts[tier] += 1
    by_root: dict[str, list[str]] = defaultdict(list)
    for content_id, record in classes.items():
        for root in record["roots"]:
            by_root[root].append(content_id)
    for content_ids in by_root.values():
        content_ids.sort()
    return {
        "path": ties_path,
        "classes": classes,
        "members": dict(by_class),
        "appledouble_content_ids": appledouble,
        "classes_by_root": dict(by_root),
        "run_ids": run_ids,
        "tier_counts": dict(sorted(tier_counts.items())),
    }


def _declared_input_signals(
    declared_path: Path, blend_targets_path: Path
) -> dict[str, Any] | None:
    """Load the existing native-scene declarations as dependency context only."""
    declared: dict[str, int] = {}
    blend_targets: set[str] = set()
    refs: list[dict[str, Any]] = []
    if declared_path.is_file():
        payload = _read_json(declared_path)
        for key, value in payload.items():
            if isinstance(value, int):
                declared[str(key).lower()] = value
        refs.append(_file_ref(declared_path))
    if blend_targets_path.is_file():
        try:
            rows = json.loads(blend_targets_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SSDOrderFoundationError(f"json_source_invalid:{blend_targets_path}") from exc
        if not isinstance(rows, list):
            raise SSDOrderFoundationError(f"blend_targets_not_array:{blend_targets_path}")
        blend_targets = {str(value) for value in rows if value}
        refs.append(_file_ref(blend_targets_path))
    if not refs:
        return None
    return {
        "declared_inputs": declared,
        "declared_inputs_ref": str(declared_path) if declared_path.is_file() else "",
        "blend_targets": blend_targets,
        "blend_targets_ref": str(blend_targets_path) if blend_targets_path.is_file() else "",
        "refs": refs,
    }


def _container_index(index_path: Path) -> dict[str, dict[str, Any]]:
    """Aggregate the existing SSD index by its own ``container_root`` column.

    This is a join on the source's own vocabulary, not an inference from a
    directory name.  A container that does not appear here is reported as
    unbound rather than silently treated as a project.
    """
    con = _ro(index_path)
    try:
        containers: dict[str, dict[str, Any]] = {}
        for row in con.execute(
            "SELECT container_root,project_id,project_path,asset_count,bytes,storage_role,"
            "owner_status FROM projects ORDER BY container_root,project_path,project_id"
        ):
            record = dict(row)
            root = str(record["container_root"] or "")
            bucket = containers.setdefault(root, {
                "container": root,
                "project_count": 0,
                "asset_count": 0,
                "bytes": 0,
                "storage_roles": Counter(),
                "projects": [],
            })
            bucket["project_count"] += 1
            bucket["asset_count"] += int(record["asset_count"] or 0)
            bucket["bytes"] += int(record["bytes"] or 0)
            bucket["storage_roles"][str(record["storage_role"] or "")] += 1
            bucket["projects"].append({
                "project_id": str(record["project_id"]),
                "project_path": str(record["project_path"]),
                "asset_count": int(record["asset_count"] or 0),
                "bytes": int(record["bytes"] or 0),
                "storage_role": str(record["storage_role"] or ""),
                "owner_status": str(record["owner_status"] or ""),
                "source_ref": f"{index_path}#projects/{record['project_id']}",
            })
        pending: Counter[str] = Counter()
        for row in con.execute(
            "SELECT substr(relative_path,1,instr(relative_path,'/')-1) AS root,count(*) AS count "
            "FROM assets WHERE hash_state='pending' GROUP BY root"
        ):
            pending[str(row["root"] or "")] = int(row["count"] or 0)
    finally:
        con.close()
    for bucket in containers.values():
        bucket["storage_roles"] = dict(sorted(bucket["storage_roles"].items()))
        bucket["hash_pending_assets"] = int(pending.get(bucket["container"], 0))
    return containers


def _index_relation_context(index_path: Path) -> dict[str, Any]:
    """Read the index relation table and measure what it can actually bind.

    The relation count alone is misleading: a measured duplicate over the empty
    byte string binds nothing, and an endpoint that does not resolve to an
    asset, project or family cannot connect two containers.  This helper keeps
    those distinctions instead of reporting one total.
    """
    con = _ro(index_path)
    try:
        asset_container: dict[str, str] = {}
        for row in con.execute("SELECT asset_id,relative_path FROM assets"):
            path = str(row["relative_path"] or "")
            asset_container[str(row["asset_id"])] = path.split("/", 1)[0] if "/" in path else path
        project_container = {
            str(row["project_id"]): str(row["container_root"] or "")
            for row in con.execute("SELECT project_id,container_root FROM projects")
        }
        family_container: dict[str, str] = {}
        for row in con.execute(
            "SELECT f.family_id AS family_id,p.container_root AS container_root "
            "FROM families f JOIN projects p ON p.project_id=f.project_id"
        ):
            family_container[str(row["family_id"])] = str(row["container_root"] or "")
        rows = [dict(row) for row in con.execute(
            "SELECT relation_id,left_id,relation,right_id,evidence_json,confidence,status "
            "FROM relations ORDER BY relation,relation_id")]
    finally:
        con.close()

    def resolve(ref: str) -> tuple[str, str]:
        """Return (container, endpoint_kind) for one relation endpoint."""
        if ref in asset_container:
            return asset_container[ref], "asset"
        if ref in project_container:
            return project_container[ref], "project"
        if ref in family_container:
            return family_container[ref], "family"
        if ref.startswith("family:") and ref[7:] in family_container:
            return family_container[ref[7:]], "family_ref"
        head = ref.replace("\\", "/").split("#", 1)[0]
        head = head.split("/", 1)[0] if "/" in head else head
        if head in project_container.values():
            return head, "unresolved_locator"
        return "", "unresolved"

    by_container: dict[str, list[dict[str, Any]]] = defaultdict(list)
    empty_hash_duplicates = 0
    substantive_duplicates = 0
    cross_container = 0
    cross_container_typed = 0
    typed_non_duplicate = 0
    for row in rows:
        try:
            evidence = json.loads(row["evidence_json"] or "{}")
        except json.JSONDecodeError:
            evidence = {}
        if not isinstance(evidence, Mapping):
            evidence = {}
        left_container, left_kind = resolve(str(row["left_id"]))
        right_container, right_kind = resolve(str(row["right_id"]))
        crosses = bool(
            left_container and right_container and left_container != right_container
        )
        if row["relation"] == "exact_duplicate":
            if evidence.get("full_sha256") == EMPTY_CONTENT_ID.removeprefix("sha256:"):
                empty_hash_duplicates += 1
            else:
                substantive_duplicates += 1
        else:
            typed_non_duplicate += 1
        if crosses:
            cross_container += 1
            if row["relation"] != "exact_duplicate":
                cross_container_typed += 1
        record = {
            "relation": str(row["relation"]),
            "status": str(row["status"] or ""),
            "confidence": row["confidence"],
            "left_container": left_container,
            "left_endpoint_kind": left_kind,
            "right_container": right_container,
            "right_endpoint_kind": right_kind,
            "crosses_containers": crosses,
            "declared_policy": str(evidence.get("policy") or ""),
            "structure_status": str(evidence.get("structure_status") or ""),
            "source_ref": f"{index_path}#relations/{row['relation_id']}",
        }
        for container in {left_container, right_container} - {""}:
            by_container[container].append(record)
    for records in by_container.values():
        records.sort(key=lambda item: (item["relation"], item["source_ref"]))
    return {
        "index_ref": str(index_path),
        "relation_total": len(rows),
        "exact_duplicate_on_empty_content": empty_hash_duplicates,
        "exact_duplicate_substantive": substantive_duplicates,
        "typed_non_duplicate_relations": typed_non_duplicate,
        "cross_container_relations": cross_container,
        "cross_container_typed_non_duplicate_relations": cross_container_typed,
        "by_container": dict(by_container),
    }


def _container_triangulation(
    *,
    containers: Mapping[str, Mapping[str, Any]],
    intake_candidates: Mapping[str, Mapping[str, Any]],
    reconstruction: Mapping[str, Mapping[str, Any]],
    index_path: Path,
) -> dict[str, dict[str, Any]]:
    """Fold intake and reconstruction evidence onto each indexed container."""
    result: dict[str, dict[str, Any]] = {}
    for container, bucket in containers.items():
        intake_rows = []
        role_counts: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        role_refs: list[str] = []
        for project in bucket["projects"]:
            candidate = intake_candidates.get(project["project_id"])
            if candidate:
                intake_rows.append({
                    "project_id": project["project_id"],
                    "project_path": project["project_path"],
                    "rank": candidate.get("rank"),
                    "score": candidate.get("score"),
                    "reason": candidate.get("reason"),
                    "source_ref": candidate.get("source_ref"),
                })
            role = reconstruction.get(project["project_path"])
            if role:
                role_counts[str(role.get("role") or "")] += 1
                status_counts[str(role.get("epistemic_status") or "")] += 1
                if len(role_refs) < _MAX_PROJECT_SAMPLES:
                    role_refs.append(str(role.get("source_ref") or ""))
        intake_rows.sort(key=lambda row: (row["rank"] if row["rank"] is not None else 10**9,
                                          row["project_path"]))
        result[container] = {
            "intake": {
                "status": "candidate_selected" if intake_rows else "not_selected",
                "candidate_count": len(intake_rows),
                "candidates": intake_rows[:_MAX_PROJECT_SAMPLES],
                "role": "workflow_attention_only",
                "note": (
                    "bounded intake attention is not artistic value, readiness, "
                    "authorship or publication"
                ),
            },
            "reconstruction": {
                "status": "reconstructed" if role_counts else "not_reconstructed",
                "decided_project_count": sum(role_counts.values()),
                "role_counts": dict(sorted(role_counts.items())),
                "epistemic_status_counts": dict(sorted(status_counts.items())),
                "source_refs": sorted(set(role_refs)),
                "note": (
                    "a reconstructed role describes containment and balance, never "
                    "authorship or a commission"
                ),
            },
        }
    return result


def _question_dossier(
    *,
    question_id: str,
    left: str,
    right: str,
    declared_shared_bytes: int,
    declared_shared_classes: int,
    examples: list[str],
    answers: list[str],
    reopen_when: str,
    reopen_when_source: str,
    authority_context: Mapping[str, Any],
    evidence_ref: str,
    ties: Mapping[str, Any] | None,
    ties_ref: Mapping[str, Any] | None,
    containers: Mapping[str, Mapping[str, Any]],
    index_path: Path,
    declared_signals: Mapping[str, Any] | None,
    triangulation: Mapping[str, Mapping[str, Any]],
    relation_context: Mapping[str, Any],
    order_tiers: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble one deterministic operator ficha.

    Every statement carries the source that produced it.  The dossier never
    answers the question: it only makes the existing evidence, its absence and
    its degeneracy explicit so a human attestation can be prioritized.
    """
    evidence_for: list[dict[str, Any]] = []
    evidence_against: list[dict[str, Any]] = []
    missing_evidence: list[dict[str, Any]] = []

    ties_source = str(ties_ref["path"]) if ties_ref else ""
    byte_identity: dict[str, Any]
    if ties is None:
        byte_identity = {
            "status": "missing_source",
            "source_ref": str(DEFAULT_TIE_DB),
            "reason": "the byte-identity ledger is not present; the question keeps its declared counts only",
        }
        missing_evidence.append({
            "statement": "independent byte-identity ledger for this container pair",
            "source_ref": str(DEFAULT_TIE_DB),
        })
    else:
        shared_ids = sorted(
            set(ties["classes_by_root"].get(left, ()))
            & set(ties["classes_by_root"].get(right, ()))
        )
        shared = [ties["classes"][content_id] for content_id in shared_ids]
        recomputed_bytes = sum(row["bytes_each"] for row in shared)
        matches = (
            len(shared) == declared_shared_classes
            and recomputed_bytes == declared_shared_bytes
        )
        empty_ids = [row["content_id"] for row in shared if row["bytes_each"] == 0]
        appledouble_ids = [
            row["content_id"] for row in shared
            if row["content_id"] in ties["appledouble_content_ids"]
        ]
        substantive = [
            row for row in shared
            if row["bytes_each"] > 0
            and row["content_id"] not in ties["appledouble_content_ids"]
        ]
        substantive_bytes = sum(row["bytes_each"] for row in substantive)
        spanning = [row for row in shared if row["distinct_roots"] > 2]
        other_roots = sorted(
            {root for row in spanning for root in row["roots"]} - {left, right}
        )
        verdicts: Counter[str] = Counter()
        for content_id in shared_ids:
            for member in ties["members"].get(content_id, ()):  # noqa: PLC0206 - keyed lookup
                verdicts[member["verdict"]] += 1
        samples = sorted(
            shared, key=lambda row: (-row["bytes_each"], row["content_id"])
        )[:_MAX_CLASS_SAMPLES]
        tiers: Counter[str] = Counter(row.get("identity_tier", "") for row in shared)
        member_paths = sorted(
            {
                (member["bytes"], member["relative_path"])
                for content_id in shared_ids
                for member in ties["members"].get(content_id, ())
            },
            key=lambda item: (-item[0], item[1]),
        )
        byte_identity = {
            "identity_tiers": dict(sorted(tiers.items())),
            "identity_tier_rule_source_ref": (
                f"{order_tiers.get('source_ref', '')}"
            ),
            "shared_member_path_count": len(member_paths),
            "shared_member_paths": [path for _, path in member_paths[:_MAX_MEMBER_PATHS]],
            "status": "recomputed",
            "source_ref": f"{ties_source}#identity_class",
            "member_source_ref": f"{ties_source}#identity_asset",
            "run_ids": list(ties["run_ids"]),
            "recomputed_shared_classes": len(shared),
            "recomputed_shared_bytes": recomputed_bytes,
            "declared_shared_classes": declared_shared_classes,
            "declared_shared_bytes": declared_shared_bytes,
            "matches_declared_question": matches,
            "verdicts": dict(sorted(verdicts.items())),
            "zero_byte_class_count": len(empty_ids),
            "appledouble_class_count": len(appledouble_ids),
            "substantive_class_count": len(substantive),
            "substantive_shared_bytes": substantive_bytes,
            "classes_spanning_more_than_two_containers": len(spanning),
            "other_containers_in_shared_classes": other_roots,
            "class_samples": [
                {
                    "content_id": row["content_id"],
                    "member_count": row["member_count"],
                    "bytes_each": row["bytes_each"],
                    "distinct_roots": row["distinct_roots"],
                    "roots": row["roots"],
                    "extensions": row["extensions"],
                    "degenerate": (
                        "zero_byte_content" if row["bytes_each"] == 0 else
                        "appledouble_resource_fork"
                        if row["content_id"] in ties["appledouble_content_ids"] else ""
                    ),
                    "source_ref": f"{ties_source}#identity_class/{row['content_id']}",
                }
                for row in samples
            ],
        }
        if matches:
            evidence_for.append({
                "statement": (
                    f"the declared {declared_shared_classes} shared content classes and "
                    f"{declared_shared_bytes} shared bytes are reproduced exactly from an "
                    f"independent byte-identity ledger"
                ),
                "source_ref": f"{ties_source}#identity_class",
            })
        else:
            evidence_against.append({
                "statement": (
                    f"the byte-identity ledger reports {len(shared)} shared classes and "
                    f"{recomputed_bytes} shared bytes, which does not reproduce the question"
                ),
                "source_ref": f"{ties_source}#identity_class",
            })
        if substantive:
            evidence_for.append({
                "statement": (
                    f"{len(substantive)} shared classes carry {substantive_bytes} substantive "
                    f"bytes that are byte-identical in both containers"
                ),
                "source_ref": f"{ties_source}#identity_class",
            })
        if empty_ids:
            evidence_against.append({
                "statement": (
                    f"{len(empty_ids)} of the shared classes are the zero-byte content class; "
                    f"empty files are a filesystem coincidence, not shared material"
                ),
                "source_ref": f"{ties_source}#identity_class/{EMPTY_CONTENT_ID}",
            })
        if appledouble_ids:
            evidence_against.append({
                "statement": (
                    f"{len(appledouble_ids)} of the shared classes are AppleDouble resource "
                    f"forks written by the filesystem, not authored content"
                ),
                "source_ref": f"{ties_source}#identity_asset(is_appledouble=1)",
            })
        if not substantive:
            evidence_against.append({
                "statement": (
                    "no shared class carries substantive bytes; this tie rests entirely on "
                    "filesystem metadata and cannot support either declared answer"
                ),
                "source_ref": f"{ties_source}#identity_class",
            })
        if spanning:
            evidence_against.append({
                "statement": (
                    f"{len(spanning)} shared classes also appear in "
                    f"{len(other_roots)} other containers ({', '.join(other_roots) or 'none'}); "
                    f"a pairwise identity answer would be arbitrary"
                ),
                "source_ref": f"{ties_source}#identity_class",
            })
        evidence_against.append({
            "statement": (
                "byte identity proves identical content, not the same commission; the "
                "declared answers are facts about commission history"
            ),
            "source_ref": evidence_ref,
        })

    sides: dict[str, Any] = {}
    for label, container in (("left", left), ("right", right)):
        bucket = containers.get(container)
        side: dict[str, Any] = {
            "container": container,
            "authority": dict(authority_context.get(label) or {}),
        }
        if bucket is None:
            side["container_binding"] = "unbound"
            side["ssd_project_count"] = 0
            side["ssd_asset_count"] = 0
            side["ssd_bytes"] = 0
            side["ssd_project_refs"] = []
            side["hash_pending_assets"] = 0
            side["source_ref"] = f"{index_path}#projects(container_root={container})"
            evidence_against.append({
                "statement": (
                    f"'{container}' is not a container_root in the SSD index; the tie names a "
                    f"locator that the index does not carry as a project container"
                ),
                "source_ref": f"{index_path}#projects(container_root={container})",
            })
            missing_evidence.append({
                "statement": f"an indexed SSD project container for '{container}'",
                "source_ref": f"{index_path}#projects",
            })
        else:
            side["container_binding"] = "bound_to_ssd_index_container_root"
            side["ssd_project_count"] = bucket["project_count"]
            side["ssd_asset_count"] = bucket["asset_count"]
            side["ssd_bytes"] = bucket["bytes"]
            side["storage_roles"] = dict(bucket["storage_roles"])
            side["hash_pending_assets"] = bucket["hash_pending_assets"]
            side["ssd_project_refs"] = [
                dict(row) for row in sorted(
                    bucket["projects"], key=lambda row: (-row["bytes"], row["project_path"])
                )[:_MAX_PROJECT_SAMPLES]
            ]
            side["source_ref"] = f"{index_path}#projects(container_root={container})"
            evidence_for.append({
                "statement": (
                    f"'{container}' exists in the SSD index as {bucket['project_count']} "
                    f"indexed project rows holding {bucket['asset_count']} assets"
                ),
                "source_ref": side["source_ref"],
            })
            if bucket["hash_pending_assets"]:
                missing_evidence.append({
                    "statement": (
                        f"full content hashes for {bucket['hash_pending_assets']} assets under "
                        f"'{container}' are still pending"
                    ),
                    "source_ref": f"{index_path}#assets(hash_state=pending)",
                })
        if ties is not None:
            members = [
                member
                for content_id in sorted(
                    set(ties["classes_by_root"].get(left, ()))
                    & set(ties["classes_by_root"].get(right, ()))
                )
                for member in ties["members"].get(content_id, ())
                if member["container_root"] == container
            ]
            side["tie_asset_count"] = len(members)
            side["tie_asset_refs"] = [
                {
                    "asset_id": member["asset_id"],
                    "relative_path": member["relative_path"],
                    "bytes": member["bytes"],
                    "verdict": member["verdict"],
                    "source_ref": f"{ties_source}#identity_asset/{member['asset_id']}",
                }
                for member in sorted(
                    members, key=lambda row: (-row["bytes"], row["relative_path"])
                )[:_MAX_ASSET_SAMPLES]
            ]
        else:
            side["tie_asset_count"] = 0
            side["tie_asset_refs"] = []
        if side["authority"].get("status") != "authority_bound_context":
            missing_evidence.append({
                "statement": f"a URL-bound external authority for '{container}'",
                "source_ref": side["authority"].get("evidence_ref", ""),
            })
        context = triangulation.get(container)
        if context is None:
            side["intake"] = {"status": "container_not_indexed", "candidate_count": 0}
            side["reconstruction"] = {"status": "container_not_indexed",
                                      "decided_project_count": 0}
        else:
            side["intake"] = dict(context["intake"])
            side["reconstruction"] = dict(context["reconstruction"])
            if side["intake"]["candidate_count"]:
                evidence_for.append({
                    "statement": (
                        f"'{container}' holds {side['intake']['candidate_count']} bounded "
                        f"intake candidate(s); this is workflow attention, not artistic value"
                    ),
                    "source_ref": (side["intake"]["candidates"][0] or {}).get("source_ref", ""),
                })
            else:
                missing_evidence.append({
                    "statement": f"a bounded intake candidate under '{container}'",
                    "source_ref": f"{index_path}#projects(container_root={container})",
                })
            if side["reconstruction"]["decided_project_count"]:
                evidence_for.append({
                    "statement": (
                        f"'{container}' has {side['reconstruction']['decided_project_count']} "
                        f"reconstructed project decisions "
                        f"({', '.join(f'{k}={v}' for k, v in side['reconstruction']['role_counts'].items())}); "
                        f"containment is not authorship"
                    ),
                    "source_ref": (side["reconstruction"]["source_refs"] or [""])[0],
                })
            else:
                missing_evidence.append({
                    "statement": f"a reconstructed project decision for '{container}'",
                    "source_ref": f"{index_path}#projects(container_root={container})",
                })
        relations = list((relation_context.get("by_container") or {}).get(container, ()))
        side["index_relations"] = {
            "touching_container": len(relations),
            "crossing_containers": sum(1 for row in relations if row["crosses_containers"]),
            "rows": relations[:_MAX_RELATION_ROWS],
        }
        sides[label] = side

    declared_input_block: dict[str, Any]
    if declared_signals is None:
        declared_input_block = {
            "status": "missing_source",
            "role": "dependency_context_only",
            "source_ref": str(DEFAULT_DECLARED_INPUTS),
        }
    else:
        paths: list[str] = []
        if ties is not None:
            for content_id in sorted(
                set(ties["classes_by_root"].get(left, ()))
                & set(ties["classes_by_root"].get(right, ()))
            ):
                paths.extend(
                    member["relative_path"] for member in ties["members"].get(content_id, ())
                )
        blend_hits = sorted({path for path in paths if path in declared_signals["blend_targets"]})
        declared_hits = sorted({
            _basename(path).lower() for path in paths
            if _basename(path).lower() in declared_signals["declared_inputs"]
        })
        declared_input_block = {
            "status": "matched" if (blend_hits or declared_hits) else "no_match",
            "role": "dependency_context_only",
            "blend_declared_target_matches": blend_hits[:_MAX_ASSET_SAMPLES],
            "blend_declared_target_match_count": len(blend_hits),
            "declared_input_basename_matches": [
                {
                    "basename": name,
                    "declaring_scene_count": declared_signals["declared_inputs"][name],
                    "source_ref": f"{declared_signals['declared_inputs_ref']}#{name}",
                }
                for name in declared_hits[:_MAX_ASSET_SAMPLES]
            ],
            "declared_input_basename_match_count": len(declared_hits),
            "source_refs": sorted(
                ref for ref in (
                    declared_signals["declared_inputs_ref"],
                    declared_signals["blend_targets_ref"],
                ) if ref
            ),
            "note": (
                "a native scene declaring a file as an input is dependency evidence; it does "
                "not establish a commission, a work identity or an author"
            ),
        }
        if blend_hits or declared_hits:
            evidence_against.append({
                "statement": (
                    f"{len(blend_hits) + len(declared_hits)} shared members are declared inputs "
                    f"of native scenes, which is consistent with reuse rather than one work"
                ),
                "source_ref": declared_input_block["source_refs"][0]
                if declared_input_block["source_refs"] else evidence_ref,
            })

    # The decisive question for this tie is not how many relations exist, but
    # whether any typed relation actually connects the two named containers.
    left_relations = list((relation_context.get("by_container") or {}).get(left, ()))
    right_relations = list((relation_context.get("by_container") or {}).get(right, ()))
    pair = {left, right}
    binding = [
        row for row in left_relations + right_relations
        if {row["left_container"], row["right_container"]} == pair
        and row["relation"] != "exact_duplicate"
    ]
    unresolved_endpoints = sum(
        1 for row in left_relations + right_relations
        if "unresolved" in (row["left_endpoint_kind"], row["right_endpoint_kind"])
    )
    touching = left_relations + right_relations
    typed_relation_block = {
        "binding_this_pair": len(binding),
        "relations_touching_either_container": len(touching),
        "typed_non_duplicate_touching_either_container": sum(
            1 for row in touching if row["relation"] != "exact_duplicate"),
        "empty_content_duplicates_touching_either_container": sum(
            1 for row in touching if row["relation"] == "exact_duplicate"),
        "unresolved_endpoints": unresolved_endpoints,
        "index_relation_total": relation_context.get("relation_total", 0),
        "index_exact_duplicate_on_empty_content": relation_context.get(
            "exact_duplicate_on_empty_content", 0),
        "index_exact_duplicate_substantive": relation_context.get(
            "exact_duplicate_substantive", 0),
        "index_typed_non_duplicate_relations": relation_context.get(
            "typed_non_duplicate_relations", 0),
        "index_cross_container_relations": relation_context.get(
            "cross_container_relations", 0),
        "index_cross_container_typed_non_duplicate_relations": relation_context.get(
            "cross_container_typed_non_duplicate_relations", 0),
        "rows": binding[:_MAX_RELATION_ROWS],
        "source_ref": f"{index_path}#relations",
    }
    if binding:
        evidence_for.append({
            "statement": (
                f"{len(binding)} typed relation(s) in the SSD index connect '{left}' and "
                f"'{right}' directly"
            ),
            "source_ref": f"{index_path}#relations",
        })
    else:
        evidence_against.append({
            "statement": (
                f"no typed relation in the SSD index connects '{left}' and '{right}'; the "
                f"index holds "
                f"{relation_context.get('typed_non_duplicate_relations', 0)} non-duplicate "
                f"typed relations in total and "
                f"{relation_context.get('cross_container_typed_non_duplicate_relations', 0)} "
                f"of them cross a container boundary"
            ),
            "source_ref": f"{index_path}#relations",
        })
        missing_evidence.append({
            "statement": (
                f"one typed, container-crossing relation between '{left}' and '{right}'"
            ),
            "source_ref": f"{index_path}#relations",
        })
    if relation_context.get("exact_duplicate_substantive") == 0:
        evidence_against.append({
            "statement": (
                f"all {relation_context.get('exact_duplicate_on_empty_content', 0)} measured "
                f"exact_duplicate relations in the SSD index are on the empty content class, "
                f"so the index binds no substantive duplicate anywhere"
            ),
            "source_ref": f"{index_path}#relations(relation=exact_duplicate)",
        })
    evidence_against.append({
        "statement": (
            "container names, filenames and routes are locators; they are not authorship, "
            "title, series or work identity"
        ),
        "source_ref": evidence_ref,
    })
    missing_evidence.append({
        "statement": (
            "an operator attestation about the commission history behind both containers"
        ),
        "source_ref": evidence_ref,
    })
    missing_evidence.append({
        "statement": (
            "a delivery, publication or contract receipt binding either container to a commission"
        ),
        "source_ref": evidence_ref,
    })

    substantive_bytes = int(byte_identity.get("substantive_shared_bytes", 0) or 0)
    substantive_classes = int(byte_identity.get("substantive_class_count", 0) or 0)
    # Say plainly whether this tie brought any evidence a human could act on, so
    # a deferred row is deferred for a stated reason rather than by omission.
    new_evidence: list[str] = []
    if substantive_classes:
        new_evidence.append("substantive_shared_bytes")
    if typed_relation_block["binding_this_pair"]:
        new_evidence.append("typed_relation_binding_the_pair")
    if any(
        sides[label]["intake"].get("candidate_count") for label in ("left", "right")
    ):
        new_evidence.append("bounded_intake_candidate")
    if any(
        sides[label]["reconstruction"].get("decided_project_count")
        for label in ("left", "right")
    ):
        new_evidence.append("reconstructed_project_decision")
    if any(
        sides[label]["authority"].get("status") == "authority_bound_context"
        for label in ("left", "right")
    ):
        new_evidence.append("authority_bound_external_context")
    if declared_input_block.get("status") == "matched":
        new_evidence.append("declared_native_scene_input")
    if ties is None:
        grade = "unverified_no_ledger"
    elif substantive_classes == 0:
        grade = "metadata_only"
    elif substantive_classes < int(byte_identity.get("recomputed_shared_classes", 0) or 0):
        grade = "partially_degenerate"
    else:
        grade = "substantive"
    unbound = sorted({
        sides[label]["container"] for label in ("left", "right")
        if sides[label]["container_binding"] == "unbound"
    })
    return {
        "question_id": question_id,
        "left": left,
        "right": right,
        "declared_shared_bytes": declared_shared_bytes,
        "declared_shared_classes": declared_shared_classes,
        "examples": list(examples),
        "possible_answers": list(answers),
        "answer_source_ref": evidence_ref,
        "byte_identity": byte_identity,
        "sides": sides,
        "typed_relations": typed_relation_block,
        "declared_input_signals": declared_input_block,
        "evidence_for": sorted(evidence_for, key=lambda row: (row["source_ref"], row["statement"])),
        "evidence_against": sorted(evidence_against, key=lambda row: (row["source_ref"], row["statement"])),
        "missing_evidence": sorted(missing_evidence, key=lambda row: (row["source_ref"], row["statement"])),
        "evidence_grade": grade,
        "actionable_evidence_kinds": sorted(new_evidence),
        "adds_actionable_evidence": bool(new_evidence),
        "deferral_reason": (
            ""
            if new_evidence else
            "no substantive shared bytes, no typed relation binding the pair, no intake "
            "candidate, no reconstructed decision and no authority-bound context on either "
            "side; nothing here moves the question without a human"
        ),
        "substantive_shared_bytes": substantive_bytes,
        "unbound_containers": unbound,
        "reopen_when": reopen_when,
        "reopen_when_source": reopen_when_source,
        "resolution": {
            "status": "unresolved",
            "resolved_by": "operator_attestation_only",
            "reason": (
                "byte evidence can show identical content but never which commission a "
                "container belongs to"
            ),
        },
        "machine_answerable": False,
        "selection_effect": "none",
    }


def _operator_review(
    order_path: Path,
    authority: Mapping[str, Mapping[str, Any]],
    authority_path: Path,
    *,
    index_path: Path,
    ties_path: Path,
    declared_inputs_path: Path,
    blend_targets_path: Path,
    intake_candidates: Mapping[str, Mapping[str, Any]],
    reconstruction: Mapping[str, Mapping[str, Any]],
    order_tiers: Mapping[str, Any],
) -> dict[str, Any]:
    """Carry the existing tie/questions ledger into the review foundation.

    The questions are deliberately preserved as operator questions.  Their
    answer is a fact about commission history, not something a filename,
    route or duplicate byte class can establish.
    """
    questions_path = order_path.with_name("questions.json")
    payload = _read_json(questions_path)
    ties = _tie_evidence(ties_path)
    ties_ref = _file_ref(ties_path) if ties is not None else None
    declared_signals = _declared_input_signals(declared_inputs_path, blend_targets_path)
    containers = _container_index(index_path)
    relation_context = _index_relation_context(index_path)
    triangulation = _container_triangulation(
        containers=containers,
        intake_candidates=intake_candidates,
        reconstruction=reconstruction,
        index_path=index_path,
    )
    asked = payload.get("ask")
    deferred = payload.get("deferred")
    if not isinstance(asked, list) or not isinstance(deferred, list):
        raise SSDOrderFoundationError("operator_questions_shape_invalid")

    def context(container: str) -> dict[str, Any]:
        bound = authority.get(container)
        if not bound or not bound.get("evidence_urls"):
            return {
                "status": "missing_or_unbound",
                "container": container,
                "role": "external_context_only",
                "evidence_ref": f"{authority_path}#containers/{container}",
            }
        return {
            "status": "authority_bound_context",
            "container": container,
            "kind": str(bound.get("kind") or ""),
            "confidence": str(bound.get("confidence") or ""),
            "role": "external_context_only",
            "evidence_url_count": len(bound.get("evidence_urls") or []),
            "evidence_ref": f"{authority_path}#containers/{container}",
        }

    def row(raw: Any, *, state: str, index: int) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise SSDOrderFoundationError("operator_question_row_invalid")
        question = str(raw.get("question") or "").strip()
        left = str(raw.get("left") or "").strip()
        right = str(raw.get("right") or "").strip()
        reason = str(raw.get("why_not_machine_answerable") or "").strip()
        examples = raw.get("examples")
        answers = raw.get("answers")
        if not question or not left or not right or not reason:
            raise SSDOrderFoundationError("operator_question_text_missing")
        if not isinstance(examples, list) or not examples:
            raise SSDOrderFoundationError("operator_question_examples_missing")
        if not isinstance(answers, list) or not answers:
            raise SSDOrderFoundationError("operator_question_answers_missing")
        result = {
            "question_id": f"order-question:{state}:{index:02d}",
            "status": state,
            "left": left,
            "right": right,
            "question": question,
            "answers": sorted(str(value) for value in answers if value),
            "examples": sorted(str(value) for value in examples if value),
            "shared_bytes": int(raw.get("shared_bytes") or 0),
            "shared_classes": int(raw.get("shared_classes") or 0),
            "why_not_machine_answerable": reason,
            "authority_context": {
                "left": context(left),
                "right": context(right),
            },
            "evidence_ref": f"{questions_path}#/{'ask' if state == 'ask' else 'deferred'}/{index}",
        }
        declared_reopen = str(raw.get("reopen_when") or "").strip()
        if declared_reopen:
            reopen_when, reopen_source = declared_reopen, str(questions_path)
        else:
            # The asked rows carry no source-declared condition.  The derived one
            # is a statement about this projection's own recomputation, never a
            # claim about the archive.
            reopen_when = (
                f"an operator attests the commission history of '{left}' and '{right}', or the "
                f"recomputed shared byte-identity classes between them change"
            )
            reopen_source = "derived:byte_identity_recomputation"
        result["reopen_when"] = reopen_when
        result["reopen_when_source"] = reopen_source
        result["machine_answerable"] = False
        result["selection_effect"] = "none"
        result["dossier"] = _question_dossier(
            question_id=result["question_id"],
            left=left,
            right=right,
            declared_shared_bytes=result["shared_bytes"],
            declared_shared_classes=result["shared_classes"],
            examples=result["examples"],
            answers=result["answers"],
            reopen_when=reopen_when,
            reopen_when_source=reopen_source,
            authority_context=result["authority_context"],
            evidence_ref=result["evidence_ref"],
            ties=ties,
            ties_ref=ties_ref,
            containers=containers,
            index_path=index_path,
            declared_signals=declared_signals,
            triangulation=triangulation,
            relation_context=relation_context,
            order_tiers=order_tiers,
        )
        if not result["answers"] or not result["examples"]:
            raise SSDOrderFoundationError("operator_question_values_missing")
        return result

    asked_rows = [row(value, state="ask", index=index) for index, value in enumerate(asked)]
    deferred_rows = [row(value, state="deferred", index=index) for index, value in enumerate(deferred)]
    questions = asked_rows + deferred_rows
    grades: Counter[str] = Counter(row["dossier"]["evidence_grade"] for row in questions)
    binding_questions = sum(
        1 for row in questions if row["dossier"]["typed_relations"]["binding_this_pair"]
    )
    unbound_rows = [row for row in questions if row["dossier"]["unbound_containers"]]
    reproduced = sum(
        1 for row in questions
        if row["dossier"]["byte_identity"].get("matches_declared_question") is True
    )
    # The queue is an attention order for a human attestation.  It is not an
    # answer, a ranking of artistic value, or an input to any selection.
    attestation_queue = [
        {
            "rank": rank,
            "question_id": row["question_id"],
            "status": row["status"],
            "left": row["left"],
            "right": row["right"],
            "evidence_grade": row["dossier"]["evidence_grade"],
            "substantive_shared_bytes": row["dossier"]["substantive_shared_bytes"],
            "actionable_evidence_kinds": row["dossier"]["actionable_evidence_kinds"],
            "deferral_reason": row["dossier"]["deferral_reason"],
            "unbound_containers": row["dossier"]["unbound_containers"],
            "answered": False,
            "answer": None,
            "attested_by": None,
            "selection_effect": "none",
            "evidence_ref": row["evidence_ref"],
        }
        for rank, row in enumerate(sorted(
            questions,
            key=lambda item: (
                0 if item["status"] == "ask" else 1,
                -item["dossier"]["substantive_shared_bytes"],
                item["question_id"],
            ),
        ), 1)
    ]
    evidence_sources = [
        {"role": "operator_questions", **_file_ref(questions_path)},
        {"role": "ssd_index", "path": str(index_path), "read_only": True},
    ]
    if ties_ref is not None:
        evidence_sources.append({"role": "byte_identity_ledger", **ties_ref})
    else:
        evidence_sources.append({
            "role": "byte_identity_ledger", "path": str(ties_path),
            "status": "missing", "read_only": True,
        })
    if declared_signals is not None:
        for ref in declared_signals["refs"]:
            evidence_sources.append({"role": "native_scene_declarations", **ref})
    return {
        "schema": "mak-order-operator-review-v1",
        "status": "review_required",
        "source_ref": str(questions_path),
        "source_sha256": _sha256(questions_path),
        "asked_count": len(asked_rows),
        "deferred_count": len(deferred_rows),
        "questions_before_triage": int(payload.get("questions_before_triage") or len(asked_rows) + len(deferred_rows)),
        "coverage_of_disputed_bytes": float(payload.get("coverage_of_disputed_bytes") or 0.0),
        "cut_rule": str(payload.get("cut_rule") or ""),
        "machine_answerable": False,
        "selection_effect": "none",
        "dossier_algorithm": "byte-identity-corroboration-2-triangulated",
        "identity_tiers": {
            "rule": (
                "reproduced from the byte ledger: a class crossing roots with a member at "
                "the volume root is the loose-copy tier, the rest of the crossing classes "
                "need an answer, and non-crossing classes stay inside one project"
            ),
            "declared_by_order_projection": dict(order_tiers.get("declared") or {}),
            "recomputed_from_ledger": (ties or {}).get("tier_counts", {}),
            "reproduces_declared_totals": bool(
                ties is not None
                and {
                    key: int((value or {}).get("classes", 0))
                    for key, value in (order_tiers.get("declared") or {}).items()
                    if isinstance(value, Mapping)
                } == (ties or {}).get("tier_counts", {})
            ),
            "source_refs": sorted({
                str(order_tiers.get("source_ref") or ""),
                f"{ties_path}#identity_class" if ties is not None else str(ties_path),
            }),
        },
        "index_relation_reality": {
            "relation_total": relation_context["relation_total"],
            "exact_duplicate_on_empty_content": relation_context["exact_duplicate_on_empty_content"],
            "exact_duplicate_substantive": relation_context["exact_duplicate_substantive"],
            "typed_non_duplicate_relations": relation_context["typed_non_duplicate_relations"],
            "cross_container_relations": relation_context["cross_container_relations"],
            "cross_container_typed_non_duplicate_relations": relation_context[
                "cross_container_typed_non_duplicate_relations"],
            "questions_with_a_binding_typed_relation": binding_questions,
            "source_ref": f"{index_path}#relations",
            "note": (
                "the relation count is not binding power: a duplicate over the empty byte "
                "string and an endpoint that does not resolve connect nothing"
            ),
        },
        "evidence_sources": evidence_sources,
        "triage": {
            "basis": "byte_identity_substance_only",
            "not_an_answer": True,
            "not_artistic_quality": True,
            "questions_reproduced_from_independent_ledger": reproduced,
            "grade_counts": dict(sorted(grades.items())),
            "questions_with_unbound_container": len(unbound_rows),
            "questions_with_actionable_evidence": sum(
                1 for row in questions if row["dossier"]["adds_actionable_evidence"]),
            "questions_without_actionable_evidence": sum(
                1 for row in questions if not row["dossier"]["adds_actionable_evidence"]),
            "actionable_evidence_kind_counts": dict(sorted(Counter(
                kind for row in questions
                for kind in row["dossier"]["actionable_evidence_kinds"]
            ).items())),
            "unbound_containers": sorted(
                {name for row in unbound_rows for name in row["dossier"]["unbound_containers"]}
            ),
            "note": (
                "a metadata_only grade means the shared bytes are empty files or AppleDouble "
                "forks; it lowers the evidence, it does not answer or close the question"
            ),
        },
        "attestation_queue": attestation_queue,
        "attestation_queue_status": "pending_human_input",
        "answers_recorded": 0,
        "questions": questions,
    }


DEFAULT_PILOT_CROSS_ARCHIVE_RUN = Path(
    "experiments/pilots/DREFQUILA/runs/cross-archive-escarlata-20260826")


def _pilot_cross_archive_chain(run_dir: Path) -> dict[str, Any]:
    """Reference the pre-existing pilot cross-archive chain without adopting it.

    A valid ``mak-cross-archive-relations-v1`` payload does exist, at pilot
    scope.  It only exists because that run declared an artist identity per
    archive and accepted a catalogue-title/filename signal, which its own
    ``reason_codes`` state.  It is therefore citable provenance and never a
    resolution for an order tie or an ISKVW selection.
    """
    relations_path = run_dir / "relations.json"
    frontier_path = run_dir / "research-frontier.json"
    if not relations_path.is_file():
        return {
            "status": "absent",
            "reason": "no pilot cross-archive relation payload is present",
            "expected_ref": str(relations_path),
        }
    relations = _read_json(relations_path)
    rows = relations.get("relations")
    rows = rows if isinstance(rows, list) else []
    archives = relations.get("archives")
    archives = archives if isinstance(archives, list) else []
    reason_codes: Counter[str] = Counter()
    evidence_kinds: Counter[str] = Counter()
    alternatives: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        statuses[str(row.get("status") or "")] += 1
        for code in row.get("reason_codes") or []:
            reason_codes[str(code)] += 1
        for item in row.get("evidence_for") or []:
            if isinstance(item, Mapping):
                evidence_kinds[str(item.get("kind") or "")] += 1
        for item in row.get("alternatives") or []:
            alternatives[str(item)] += 1
    frontier: dict[str, Any] = {"status": "absent"}
    if frontier_path.is_file():
        payload = _read_json(frontier_path)
        jobs = payload.get("jobs")
        jobs = jobs if isinstance(jobs, list) else []
        frontier = {
            "status": "compiled_not_dispatched",
            "ref": str(frontier_path),
            "sha256": _sha256(frontier_path),
            "schema": str(payload.get("schema") or ""),
            "job_count": len(jobs),
            "dispatched_job_count": sum(
                1 for job in jobs if isinstance(job, Mapping) and job.get("dispatch")),
            "control": dict(payload.get("control") or {}),
        }
    return {
        "status": "present_pilot_scope",
        "scope": "pilot_case_run_not_the_ssd_order_frontier",
        "relations_ref": str(relations_path),
        "relations_sha256": _sha256(relations_path),
        "relations_schema": str(relations.get("schema") or ""),
        "relation_count": len(rows),
        "relation_statuses": dict(sorted(statuses.items())),
        "archives": [
            {
                "archive_id": str(row.get("archive_id") or ""),
                "declared_artist_identity": str(row.get("artist_identity") or ""),
                "binding_status": str(row.get("binding_status") or ""),
            }
            for row in archives if isinstance(row, Mapping)
        ],
        "reason_codes": dict(sorted(reason_codes.items())),
        "evidence_kinds": dict(sorted(evidence_kinds.items())),
        "declared_alternatives": dict(sorted(alternatives.items())),
        "research_frontier": frontier,
        "why_not_adopted": [
            "the payload exists only because each archive declared an artist identity, "
            "which this projection refuses to assert for an SSD container",
            "its positive evidence includes artifact_name_signal and local_title_match, "
            "which are filename/title similarity, not content or delivery binding",
            "it declares same_title_different_work as a live alternative and "
            "exact_cross_archive_content_unavailable as counterevidence",
            "its relations stay status=candidate with truth_promotions=0",
        ],
        "usable_for": [
            "citable provenance that the cross-archive pipeline runs and is reproducible",
        ],
        "not_usable_for": [
            "answering any of the 50 operator ties",
            "binding any of the 52 SSD-ISKVW locator candidates",
            "selecting, naming or ranking an ISKVW piece",
        ],
    }


def _research_frontier_abstention(
    crosswalk: Mapping[str, Any], pilot_chain: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record why the existing research frontier cannot be compiled from here.

    ``cross_archive_research_frontier`` only accepts a validated
    ``mak-cross-archive-relations-v1`` payload, and ``cross_archive_relations``
    only produces one when every archive declares an ``artist_identity`` and a
    catalogue track title matches the artifact's filename stem.  Both gates are
    exactly the inferences this projection refuses to make, so the honest
    result is abstention with the blocking gates named.
    """
    module = "src/flujo/knowledge/cross_archive_relations.py"
    frontier_module = "src/flujo/knowledge/cross_archive_research_frontier.py"
    blocking = [
        {
            "gate": "archive_missing_artist_identity",
            "requirement": (
                "every archive descriptor must declare an artist_identity before any "
                "cross-archive relation is produced"
            ),
            "why_refused": (
                "the SSD containers are locators; assigning an artist to DREFGIRA, DrefQuila, "
                "HARRY or BAHPARTY would be an authorship inference"
            ),
            "source_ref": f"{module}#_descriptor",
        },
        {
            "gate": "catalog_track_title_matches_filename_stem",
            "requirement": (
                "an artifact joins a catalogue work only when the track title tokens are a "
                "subset of the filename stem tokens"
            ),
            "why_refused": (
                "that is textual similarity between a filename and a title, which this "
                "projection does not accept as evidence of a work"
            ),
            "source_ref": f"{module}#_matching_artifacts",
        },
        {
            "gate": "relation_payload_schema_required",
            "requirement": (
                "the frontier compiler validates a mak-cross-archive-relations-v1 payload "
                "with typed relations and next probes"
            ),
            "why_refused": (
                "the only available SSD-ISKVW bridge is a shared external media locator with "
                "typed_reference_count=0; it is not a typed relation"
            ),
            "source_ref": f"{frontier_module}#compile_cross_archive_research_frontier",
        },
    ]
    return {
        "schema": "mak-research-frontier-jobs-v1",
        "status": "abstain",
        "scope": "ssd_order_frontier",
        "compiled": False,
        "job_count": 0,
        "dispatch": False,
        "create_job_invoked": False,
        "network_called": False,
        "reason": (
            "no_ssd_order_input_reaches_a_typed_relation_without_a_forbidden_inference"
        ),
        "precision_note": (
            "this abstention is about the SSD order frontier only. A valid "
            "mak-cross-archive-relations-v1 payload does exist at pilot scope and a "
            "non-dispatched research frontier was already compiled from it; it is cited as "
            "provenance and is not adopted here, because it rests on a declared artist "
            "identity plus a catalogue-title/filename signal."
        ),
        "existing_pilot_chain": dict(pilot_chain or {"status": "not_examined"}),
        "blocking_gates": blocking,
        "available_input": {
            "kind": "same_external_media_locator",
            "status": crosswalk.get("status"),
            "candidate_relation_count": crosswalk.get("candidate_relation_count", 0),
            "typed_reference_count": crosswalk.get("typed_reference_count", 0),
            "selection_eligible": False,
            "missing_evidence": ["typed_relation", "full_content_hash_or_delivery_receipt"],
        },
        "reopen_when": (
            "one SSD asset and one ISKVW piece share a full content hash or a delivery "
            "receipt, producing a typed relation with explicit source refs"
        ),
        "limits": [
            "A shared locator is not a work, an authorship claim or a delivery.",
            "No research job was created, queued, dispatched or written to any research store.",
        ],
    }


def compile_ssd_order_foundation(
    *,
    index_path: str | Path,
    order_projection_path: str | Path,
    intake_db: str | Path,
    knowledge_db: str | Path,
    research_authority_path: str | Path,
    reconstruction_dir: str | Path,
    archive_path: str | Path,
    research_corpus_dir: str | Path | None = None,
    ties_path: str | Path | None = None,
    declared_inputs_path: str | Path | None = None,
    blend_targets_path: str | Path | None = None,
    pilot_cross_archive_run: str | Path | None = None,
) -> dict[str, Any]:
    """Compile the evidence-first order from existing sources only."""
    index = Path(index_path).expanduser().resolve()
    order_path = Path(order_projection_path).expanduser().resolve()
    intake = Path(intake_db).expanduser().resolve()
    knowledge = Path(knowledge_db).expanduser().resolve()
    authority_path = Path(research_authority_path).expanduser().resolve()
    recon_dir = Path(reconstruction_dir).expanduser().resolve()
    archive = Path(archive_path).expanduser().resolve()
    corpus_dir = (
        Path(research_corpus_dir).expanduser().resolve()
        if research_corpus_dir is not None else None
    )
    ties = Path(ties_path or DEFAULT_TIE_DB).expanduser()
    declared_inputs = Path(declared_inputs_path or DEFAULT_DECLARED_INPUTS).expanduser()
    blend_targets = Path(blend_targets_path or DEFAULT_BLEND_TARGETS).expanduser()

    index_ref = _file_ref(index)
    order = _read_json(order_path)
    if order.get("contract") != "mak-order-projection-v1":
        raise SSDOrderFoundationError("order_projection_contract_invalid")
    inputs = order.get("inputs")
    if not isinstance(inputs, list) or not inputs or not isinstance(inputs[0], Mapping):
        raise SSDOrderFoundationError("order_projection_input_missing")
    if inputs[0].get("sha256") != index_ref["sha256"]:
        raise SSDOrderFoundationError("order_projection_stale_against_index")

    authority = _authority(authority_path)
    reconstruction, reconstruction_refs = _reconstruction_roles(recon_dir)
    knowledge_by_title, knowledge_episodes = _knowledge_records(knowledge)
    intake_con = _ro(intake)
    try:
        intake_run = intake_con.execute(
            "SELECT * FROM intake_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if intake_run is None:
            raise SSDOrderFoundationError("intake_run_missing")
        intake_run_dict = dict(intake_run)
        if str(intake_run_dict.get("source_ref") or "") != str(index):
            raise SSDOrderFoundationError("intake_source_mismatch")
        candidates = {
            str(row["project_id"]): {
                "rank": int(row["rank"]),
                "score": float(row["score"]),
                "reason": str(row["reason"] or ""),
                "source_ref": f"{intake}#project_candidates/{row['rank']}",
            }
            for row in intake_con.execute(
                "SELECT project_id,rank,score,reason FROM project_candidates "
                "WHERE run_id=? ORDER BY rank", (intake_run_dict["run_id"],)
            )
        }
    finally:
        intake_con.close()
    order_result_for_tiers = order.get("result") if isinstance(order.get("result"), Mapping) else {}
    order_tiers = {
        "source_ref": f"{order_path}#/result/tiers",
        "declared": dict(order_result_for_tiers.get("tiers") or {}),
    }
    operator_review = _operator_review(
        order_path, authority, authority_path,
        index_path=index,
        ties_path=ties,
        declared_inputs_path=declared_inputs,
        blend_targets_path=blend_targets,
        intake_candidates=candidates,
        reconstruction=reconstruction,
        order_tiers=order_tiers,
    )


    con = _ro(index)
    try:
        inventory = {
            "assets": int(_one(con, "SELECT count(*) FROM assets") or 0),
            "projects": int(_one(con, "SELECT count(*) FROM projects") or 0),
            "families": int(_one(con, "SELECT count(*) FROM families") or 0),
            "relations": int(_one(con, "SELECT count(*) FROM relations") or 0),
            "exact_duplicate_relations": int(_one(con, "SELECT count(*) FROM relations WHERE relation='exact_duplicate' AND status='measured'") or 0),
            "hash_state": {
                str(row["hash_state"]): int(row["count"])
                for row in con.execute("SELECT hash_state,count(*) AS count FROM assets GROUP BY hash_state")
            },
        }
        role_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for row in con.execute(
            "SELECT project_id,member_role,count(*) AS count FROM project_members GROUP BY project_id,member_role"
        ):
            role_counts[str(row["project_id"])][str(row["member_role"])] = int(row["count"])

        project_rows: list[dict[str, Any]] = []
        for row in con.execute(
            "SELECT project_id,project_path,container_root,dimensionality,owner_status,"
            "storage_role,asset_count,bytes,anchor_count,strategy,confidence "
            "FROM projects ORDER BY project_path,project_id"
        ):
            project = dict(row)
            project_id = str(project["project_id"])
            project_path = str(project["project_path"])
            root = str(project.get("container_root") or project_path.split("/", 1)[0])
            role = reconstruction.get(project_path)
            intake_candidate = candidates.get(project_id)
            knowledge_records = knowledge_by_title.get(project_path, [])
            knowledge_ref_ids = [str(item["project_id"]) for item in knowledge_records]
            if role and role.get("role") == "project_unit" and intake_candidate:
                bucket, bucket_rank = "A_project_unit_with_intake", 1
            elif role and role.get("role") == "project_unit":
                bucket, bucket_rank = "B_reconstructed_project_unit", 2
            elif intake_candidate:
                bucket, bucket_rank = "C_intake_candidate", 3
            elif role and role.get("role") == "subproject":
                bucket, bucket_rank = "D_reconstructed_subproject", 4
            elif role and role.get("role") in {"shared_resource", "library_dependency"}:
                bucket, bucket_rank = "E_resource_not_independent_unit", 5
            else:
                bucket, bucket_rank = "F_indexed_only", 6

            evidence_refs = [f"{index}#projects/{project_id}"]
            if intake_candidate:
                evidence_refs.append(intake_candidate["source_ref"])
            if role:
                evidence_refs.append(str(role["source_ref"]))
            for record in knowledge_records:
                evidence_refs.append(f"{knowledge}#project_records/{record['project_id']}")
            if root in authority:
                evidence_refs.append(f"{authority_path}#containers/{root}")
            project_rows.append({
                "order_rank": None,
                "project_id": project_id,
                "project_path": project_path,
                "container_root": root,
                "review_bucket": bucket,
                "review_bucket_rank": bucket_rank,
                "external_context_authority": authority.get(root, {
                    "status": "missing",
                    "reason": "no local research authority bound for this container",
                }),
                "reconstruction": role or {"role": "indexed_only", "epistemic_status": "unknown"},
                "intake_candidate": intake_candidate,
                "knowledge_project_records": knowledge_ref_ids,
                "knowledge_episode_count": sum(knowledge_episodes.get(pid, 0) for pid in knowledge_ref_ids),
                "physical_observation": {
                    "dimensionality": project.get("dimensionality"),
                    "storage_role": project.get("storage_role"),
                    "asset_count": int(project.get("asset_count") or 0),
                    "bytes": int(project.get("bytes") or 0),
                    "anchor_count": int(project.get("anchor_count") or 0),
                    "strategy": project.get("strategy"),
                    "confidence": project.get("confidence"),
                    "member_roles": dict(sorted(role_counts[project_id].items())),
                },
                "evidence_refs": sorted(set(evidence_refs)),
                "reason": (
                    "review project unit already selected by the bounded intake"
                    if bucket == "A_project_unit_with_intake" else
                    "reconstructed project unit with balanced source evidence"
                    if bucket == "B_reconstructed_project_unit" else
                    "intake candidate; selection is workflow attention, not artistic quality"
                    if bucket == "C_intake_candidate" else
                    "subproject remains separately addressable; containment is not authorship"
                    if bucket == "D_reconstructed_subproject" else
                    "resource/dependency is retained but cannot become an independent work"
                    if bucket == "E_resource_not_independent_unit" else
                    "indexed physical observation without a stronger bound"
                ),
            })
    finally:
        con.close()

    project_rows.sort(key=lambda row: (
        row["review_bucket_rank"],
        (row["intake_candidate"] or {}).get("rank", 10**9),
        row["project_path"],
        row["project_id"],
    ))
    for rank, row in enumerate(project_rows, 1):
        row["order_rank"] = rank

    crosswalk = _archive_crosswalk(
        archive, index, corpus_dir, knowledge_path=knowledge, intake_path=intake)
    pilot_run = Path(pilot_cross_archive_run or DEFAULT_PILOT_CROSS_ARCHIVE_RUN)
    if not pilot_run.is_absolute():
        pilot_run = (Path(__file__).resolve().parents[3] / pilot_run)
    pilot_chain = _pilot_cross_archive_chain(pilot_run)
    order_result = order.get("result") if isinstance(order.get("result"), Mapping) else {}
    unresolved_ties = int((order_result.get("relations") or {}).get("still_a_tie_for_the_operator", 0) or 0)
    pending_hashes = int(inventory["hash_state"].get("pending", 0) or 0)
    bucket_counts = Counter(row["review_bucket"] for row in project_rows)
    status = "partial_order" if unresolved_ties or pending_hashes else "ordered_for_review"

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "status": status,
        "source": {
            "index": index_ref,
            "order_projection": {
                "path": str(order_path),
                "semantic_hash": order.get("output_sha256", ""),
                "index_sha256": inputs[0].get("sha256", ""),
                "contract": order.get("contract", ""),
                "run_started_at": order.get("started_at", ""),
                "run_finished_at": order.get("finished_at", ""),
            },
            "operator_questions": {
                **_file_ref(order_path.with_name("questions.json")),
                "schema": operator_review["schema"],
            },
            "intake": {**_file_ref(intake), "run": intake_run_dict},
            "knowledge": _file_ref(knowledge),
            "research_authority": {**_file_ref(authority_path), "schema": _read_json(authority_path).get("schema", "")},
            "reconstructions": reconstruction_refs,
        },
        "inventory": inventory,
        "order": {
            "basis": "evidence_first_review_order",
            "not_artistic_quality": True,
            "project_count": len(project_rows),
            "bucket_counts": dict(sorted(bucket_counts.items())),
            "projects": project_rows,
            "order_projection_result": order_result,
        },
        "triangulation": [
            {
                "source": "portable_ssd_index",
                "supports": ["physical paths, bytes, media kind, project/family membership, measured duplicate relations"],
                "does_not_support": ["authorship, artistic quality, work identity from names/routes"],
            },
            {
                "source": "order_projection",
                "supports": ["certified byte-identity tiers, show/dependency holds, operator question queue"],
                "does_not_support": ["same work versus reused output across commissions"],
            },
            {
                "source": "application_intake",
                "supports": ["bounded workflow attention and explicit source-linked candidate status"],
                "does_not_support": ["artistic value, authorship, readiness or publication"],
            },
            {
                "source": "project_ir_and_reconstruction",
                "supports": ["explicit project-unit/subproject/resource roles and balanced assignments"],
                "does_not_support": ["containment as authorship or resource as an independent work"],
            },
            {
                "source": "research_authority",
                "supports": ["container context or track identity only where a URL-backed authority exists"],
                "does_not_support": ["turning a filename into a work without the declared authority"],
            },
            {
                "source": "research_corpus",
                "supports": ["preserved ISKVW locator and bounded observation context"],
                "does_not_support": ["independent confirmation of SSD content, authorship or delivery"],
            },
        ],
        "crosswalk_to_iskvw": crosswalk,
        "operator_review": operator_review,
        "research_frontier": _research_frontier_abstention(crosswalk, pilot_chain),
        "limits": [
            "No SSD file was moved, renamed, deleted or rehashed by this projection.",
            "The 50 operator ties from the existing order remain unresolved; a model must not answer them.",
            "Pending full hashes remain an evidence gap even when sample hashes or names look similar.",
            "The SSD order is not silently joined to ISKVW; the explicit crosswalk is unresolved until a typed reference exists.",
            "No ranking value is an artistic-quality score or an authorship claim.",
            "Operator questions remain unresolved; no tie is auto-resolved from path, name or duplicate bytes.",
            "The operator dossier grades byte evidence only; a metadata_only grade lowers the evidence of a tie and never answers or closes it.",
            "The attestation queue is an attention order for a human; it carries no answer and has no selection effect.",
            "No research frontier job was compiled, created or dispatched; the cross-archive pipeline is refused because its own gates require an artist identity and a filename/title match.",
        ],
        "next_actions": [
            f"Keep the {operator_review['asked_count']} high-leverage order questions for operator attestation; do not auto-fill them.",
            f"Retain the {operator_review['deferred_count']} deferred questions as a reopenable frontier.",
            "Use project-unit and explicitly authority-bound rows as the bounded review frontier.",
            "Before an SSD-grounded Contracurator thesis, create one typed SSD↔ISKVW relation or abstain from that claim.",
            "Answer the attestation queue in rank order; substantive ties carry byte evidence, metadata_only ties do not.",
        ],
        "control": {
            "source_rescan": False,
            "physical_mutation": False,
            "database_write": False,
            "network_called": False,
            "publication": False,
            "training_permitted": False,
            "promotion": "none",
        },
    }
    result["semantic_hash"] = "sha256:" + hashlib.sha256(
        stable_json({k: v for k, v in result.items() if k != "semantic_hash"}).encode("utf-8")
    ).hexdigest()
    return result


__all__ = [
    "ALGORITHM_VERSION", "DEFAULT_BLEND_TARGETS", "DEFAULT_DECLARED_INPUTS",
    "DEFAULT_PILOT_CROSS_ARCHIVE_RUN", "DEFAULT_TIE_DB", "EMPTY_CONTENT_ID",
    "SCHEMA", "SSDOrderFoundationError",
    "compile_ssd_order_foundation",
]
