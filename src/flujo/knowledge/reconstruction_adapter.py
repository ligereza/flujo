"""Adapt a persisted SSD reconstruction into the shared Project IR contract.

The reconstruction is an index observation, not a mounted source tree. This
adapter therefore keeps every artifact as an indexed reference and marks the
result ``review_required``. It is a bridge for Curatoria and Portfolio routing;
it is not an application generator and never publishes a private SSD path.

Each record carries its own incident edges with itself as the subject, which
means an edge whose other endpoint is this record has to be stated from the
other side -- with the inverse predicate. Keeping the predicate while swapping
the endpoints is a silent inversion, and it happened: see
``project_reconstruction.RELATION_INVERSES``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .project_ir import build_project_ir, format_family, media_type
from .project_reconstruction import inverse_relation


ADAPTER_SCHEMA = "mak-reconstruction-project-ir-v1"
RECONSTRUCTION_SCHEMA = "mak-project-reconstruction-v1"
INDEX_SOURCE_KIND = "portable_ssd_index"
UNIT_ROLES = {"project_unit", "subproject", "exported_product"}


class ReconstructionAdapterError(ValueError):
    """Raised when the persisted reconstruction cannot be consumed safely."""


def load_reconstruction(path: str | Path) -> dict[str, Any]:
    """Load and validate a persisted reconstruction without changing it."""
    reconstruction_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(reconstruction_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconstructionAdapterError(
            f"cannot read reconstruction: {reconstruction_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReconstructionAdapterError("reconstruction_not_object")
    if payload.get("schema") != RECONSTRUCTION_SCHEMA:
        raise ReconstructionAdapterError("unsupported_reconstruction_schema")
    for field in ("index_path", "index_fingerprint", "scope", "units",
                  "decisions", "features", "relations", "asset_assignment"):
        if field not in payload:
            raise ReconstructionAdapterError(f"reconstruction_missing_{field}")
    if not isinstance(payload["units"], list):
        raise ReconstructionAdapterError("reconstruction_units_not_list")
    if not isinstance(payload["decisions"], dict):
        raise ReconstructionAdapterError("reconstruction_decisions_not_object")
    if not isinstance(payload["features"], dict):
        raise ReconstructionAdapterError("reconstruction_features_not_object")
    if not isinstance(payload["relations"], list):
        raise ReconstructionAdapterError("reconstruction_relations_not_list")
    if not isinstance(payload["asset_assignment"], dict):
        raise ReconstructionAdapterError("reconstruction_asset_assignment_not_object")
    return payload


def _index_path(payload: Mapping[str, Any], override: str | Path | None = None) -> Path:
    declared = Path(str(payload["index_path"])).expanduser().resolve()
    if override is None:
        return declared
    supplied = Path(override).expanduser().resolve()
    if supplied != declared:
        raise ReconstructionAdapterError("index_override_does_not_match_reconstruction")
    return supplied


def _load_assets(index_path: Path, asset_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Read only the assigned rows needed by the current reconstruction."""
    if not index_path.is_file():
        raise FileNotFoundError(f"index_not_found: {index_path}")
    if not asset_ids:
        return {}
    result: dict[str, dict[str, Any]] = {}
    con = sqlite3.connect("file:" + str(index_path) + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        values = sorted(asset_ids)
        for offset in range(0, len(values), 400):
            batch = values[offset:offset + 400]
            placeholders = ",".join("?" for _ in batch)
            rows = con.execute(
                "SELECT asset_id, relative_path, extension, media_kind, bytes, "
                "mtime_ns, full_sha256, sample_sha256 "
                f"FROM assets WHERE asset_id IN ({placeholders})", batch
            ).fetchall()
            for row in rows:
                result[str(row["asset_id"])] = dict(row)
    finally:
        con.close()
    missing = asset_ids - set(result)
    if missing:
        raise ReconstructionAdapterError(
            f"reconstruction_assets_missing_from_index: {len(missing)}"
        )
    return result


def _source_locator(payload: Mapping[str, Any], project_path: str) -> str:
    fingerprint = str(payload.get("index_fingerprint") or "")
    scope = str(payload.get("scope") or "")
    return f"portable-ssd-index://{fingerprint}/{scope}/{project_path}"


def _artifact_rows(
    payload: Mapping[str, Any], project_path: str,
    assets: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    assignment = payload["asset_assignment"]
    rows = []
    for asset_id, owner in sorted(assignment.items()):
        if str(owner) != project_path:
            continue
        asset = assets.get(str(asset_id))
        if asset is None:
            continue
        relative = str(asset.get("relative_path") or "")
        full_sha = str(asset.get("full_sha256") or "")
        sample_sha = str(asset.get("sample_sha256") or "")
        rows.append({
            "artifact_id": "ssd_asset_" + str(asset_id)[:40],
            "relative_path": relative,
            "name": Path(relative).name,
            "format_family": format_family(relative),
            "media_type": media_type(relative),
            "size_bytes": int(asset.get("bytes") or 0),
            "mtime_ns": int(asset.get("mtime_ns") or 0),
            "sha256": full_sha,
            "hash_status": "full" if full_sha else ("sample" if sample_sha else "not_computed"),
            "availability": "indexed",
            "role": "reconstructed_asset",
        })
    return rows


def _relations_for(
    payload: Mapping[str, Any], project_path: str, project_id: str,
) -> list[dict[str, Any]]:
    output = []
    scope = str(payload.get("scope") or "")
    for relation in payload["relations"]:
        if not isinstance(relation, Mapping):
            continue
        left = str(relation.get("left") or "")
        right = str(relation.get("right") or "")
        if project_path not in {left, right}:
            continue
        predicate = str(relation.get("relation") or "related_to")
        # Every record keeps its own edges with itself as the subject, so the
        # edge has to be re-anchored whenever this record is the object side.
        # Re-anchoring without inverting the predicate is what turned 24
        # ``contains`` edges into 56, half of them backwards, and would have
        # said a purchased texture contains the work that uses it.
        if left == project_path:
            object_path = right
        else:
            object_path = left
            predicate = inverse_relation(predicate)
        output.append({
            "subject": project_id,
            "predicate": predicate,
            "object": f"reconstruction://{scope}/{object_path}",
            "confidence": str(relation.get("epistemic_status") or "UNKNOWN"),
            "plane": "portable_ssd_index",
        })
    return output


def _unknowns(decision: Mapping[str, Any], project_path: str) -> list[str]:
    unknowns = ["physical_source_mount_unverified"]
    if str(decision.get("epistemic_status") or "") == "UNKNOWN":
        unknowns.append(f"reconstruction_decision_unknown:{project_path}")
    tie_breaker = str(decision.get("tie_breaker_needed") or "").strip()
    if tie_breaker:
        unknowns.append(f"reconstruction_tie_breaker:{tie_breaker}")
    return unknowns


def project_irs_from_reconstruction(
    reconstruction: Mapping[str, Any], *, source_ref: str = "reconstruction.json",
    index_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Create one reviewable Project IR record per reconstructed unit.

    Library dependencies and shared resources intentionally do not become
    projects. They remain relations/assets of the nearest reconstructed unit.
    """
    if reconstruction.get("schema") != RECONSTRUCTION_SCHEMA:
        raise ReconstructionAdapterError("unsupported_reconstruction_schema")
    index_path = _index_path(reconstruction, index_override)
    units = [
        unit for unit in reconstruction["units"]
        if isinstance(unit, Mapping) and str(unit.get("role") or "") in UNIT_ROLES
    ]
    asset_ids = {
        str(asset_id) for asset_id, owner in reconstruction["asset_assignment"].items()
        if str(owner) in {str(unit.get("project_path") or "") for unit in units}
    }
    assets = _load_assets(index_path, asset_ids)
    records = []
    for unit in sorted(units, key=lambda row: str(row.get("project_path") or "")):
        project_path = str(unit.get("project_path") or "").strip()
        project_id = str(unit.get("project_id") or "").strip()
        if not project_path or not project_id:
            raise ReconstructionAdapterError("reconstruction_unit_missing_identity")
        decision = reconstruction["decisions"].get(project_path)
        feature = reconstruction["features"].get(project_path)
        if not isinstance(decision, Mapping) or not isinstance(feature, Mapping):
            raise ReconstructionAdapterError(f"unit_missing_decision_or_feature:{project_path}")
        record = build_project_ir(
            project_id=project_id,
            title=project_path,
            source_root=_source_locator(reconstruction, project_path),
            artifacts=_artifact_rows(reconstruction, project_path, assets),
            domains=("mak", "curatoria", "portfolio"),
            purpose="reconstructed_project_unit_for_curatoria_and_portfolio_review",
            state="review_required",
            evidence=[{
                "kind": "reconstruction",
                "status": "observed",
                "schema": reconstruction["schema"],
                "algorithm_version": reconstruction.get("algorithm_version", ""),
                "index_fingerprint": reconstruction.get("index_fingerprint", ""),
                "scope": reconstruction.get("scope", ""),
                "project_path": project_path,
                "role": unit.get("role", ""),
                "epistemic_status": unit.get("epistemic_status", "UNKNOWN"),
                "rule": decision.get("rule", ""),
            }, {
                "kind": "source_index",
                "status": "referenced",
                "source_ref": str(reconstruction.get("index_path") or ""),
            }],
            unknowns=_unknowns(decision, project_path),
            relations=_relations_for(reconstruction, project_path, project_id),
            source_kind=INDEX_SOURCE_KIND,
            source_ref=source_ref,
        )
        record["reconstruction"] = {
            "schema": reconstruction["schema"],
            "algorithm_version": reconstruction.get("algorithm_version", ""),
            "scope": reconstruction.get("scope", ""),
            "project_path": project_path,
            "role": unit.get("role", ""),
            "feature": {
                "asset_count": feature.get("asset_count", 0),
                "anchor_count": feature.get("anchor_count", 0),
                "dimensionality": feature.get("dimensionality", "unknown"),
                "media_mix": feature.get("media_mix", {}),
            },
        }
        record["consumer_policy"] = {
            "curatoria": "review_before_perception",
            "portfolio": "never_auto_publish",
            "postulacion": "not_created_by_this_adapter",
        }
        records.append(record)
    return records


def adapt_reconstruction(
    path: str | Path, *, index_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load a persisted payload and return Project IR records."""
    reconstruction_path = Path(path).expanduser().resolve()
    payload = load_reconstruction(reconstruction_path)
    return project_irs_from_reconstruction(
        payload, source_ref=str(reconstruction_path), index_override=index_override,
    )
