"""Human-readable, evidence-bounded projection of the common product outputs."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import canonical_sha256_ref as _hash, stable_json
from .portfolio_dossier import validate_portfolio_dossier


SCHEMA = "mak-product-view-v1"
ALGORITHM_VERSION = "product-view-1"
PLAN_SCHEMA = "mak-product-plan-v1"
DOSSIER_SCHEMA = "mak-portfolio-dossier-v1"
PACKAGE_SCHEMA = "mak-application-research-package-v1"
ARCHIVE_VIEW_SCHEMA = "mak-archive-portfolio-view-v1"
ARCHIVE_VIEW_ALGORITHM_VERSION = "archive-portfolio-view-1"


class ProductViewError(ValueError):
    """Raised when product consumers cannot be joined without inventing data."""


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ProductViewError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ProductViewError(f"{field}_required")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductViewError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProductViewError(f"{field}_must_be_list")
    return value


def _refs(value: Any, field: str) -> list[str]:
    rows = _list(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in rows):
        raise ProductViewError(f"{field}_invalid")
    return sorted(set(item.strip() for item in rows))


def _validate_inputs(
    plan: Mapping[str, Any],
    dossier: Mapping[str, Any],
    package: Mapping[str, Any],
) -> tuple[str, str, str]:
    if plan.get("schema") != PLAN_SCHEMA:
        raise ProductViewError("product_plan_schema_invalid")
    selected_programs = _list(plan.get("selected_programs"), "product_plan.selected_programs")
    for raw in selected_programs:
        _mapping(raw, "product_plan.selected_program")
    if dossier.get("schema") != DOSSIER_SCHEMA:
        raise ProductViewError("portfolio_dossier_schema_invalid")
    dossier_errors = validate_portfolio_dossier(dossier)
    if dossier_errors:
        raise ProductViewError("portfolio_dossier_invalid:" + ",".join(dossier_errors))
    if package.get("schema") != PACKAGE_SCHEMA:
        raise ProductViewError("application_package_schema_invalid")
    application = _mapping(package.get("application_draft"), "application_draft")
    research = _mapping(package.get("research_brief"), "research_brief")
    controls = _mapping(package.get("controls"), "application_package.controls")
    if any(controls.get(key) is not False for key in ("submission", "dispatch", "training_permitted")):
        raise ProductViewError("application_package_control_not_fail_closed")
    opportunity_id = _text(plan.get("opportunity_id"), "product_plan.opportunity_id")
    if _text(dossier.get("opportunity_id"), "portfolio_dossier.opportunity_id") != opportunity_id:
        raise ProductViewError("opportunity_id_mismatch")
    if _text(application.get("opportunity_id"), "application_draft.opportunity_id") != opportunity_id:
        raise ProductViewError("application_opportunity_id_mismatch")
    plan_hash = _hash(plan)
    dossier_hashes = _mapping(dossier.get("input_hashes"), "portfolio_dossier.input_hashes")
    package_hashes = _mapping(package.get("input_hashes"), "application_package.input_hashes")
    if dossier_hashes.get("product_plan") != plan_hash:
        raise ProductViewError("portfolio_dossier_product_plan_hash_mismatch")
    if package_hashes.get("product_plan") != plan_hash:
        raise ProductViewError("application_package_product_plan_hash_mismatch")
    return opportunity_id, plan_hash, _text(dossier.get("dossier_hash"), "portfolio_dossier.dossier_hash")


def _count_values(rows: list[Mapping[str, Any]], field: str) -> dict[str, int]:
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProductViewError(f"product_plan.{field}_row_must_be_object")
    values = sorted({_text(row.get(field), field, required=False) or "unknown" for row in rows})
    return {value: sum(1 for row in rows if (_text(row.get(field), field, required=False) or "unknown") == value) for value in values}


def _technical_evidence_projection(
    dossier: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Expose the dossier's technical observations without changing their status.

    The dossier has already filtered the shared project context to technical
    relations.  This second boundary is deliberately strict: the product view
    must not accidentally leak paths/tool payloads or turn a surface signal
    into an artistic claim or an asset-selection decision.
    """
    raw_context = dossier.get("technical_context")
    if raw_context is None:
        return [], None
    context = _mapping(raw_context, "portfolio_dossier.technical_context")
    expected_context_fields = {
        "context_id", "context_hash", "relations", "provenance_only",
        "claim_promotion", "asset_selection",
    }
    if set(context) != expected_context_fields:
        raise ProductViewError("technical_context_field_set_invalid")
    if context.get("provenance_only") is not True:
        raise ProductViewError("technical_context_not_provenance_only")
    if context.get("claim_promotion") is not False:
        raise ProductViewError("technical_context_claim_promotion")
    if context.get("asset_selection") is not False:
        raise ProductViewError("technical_context_asset_selection")
    context_hash = _text(context.get("context_hash"), "technical_context.context_hash")
    if not context_hash.startswith("sha256:"):
        raise ProductViewError("technical_context_hash_invalid")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(context.get("relations"), "technical_context.relations")):
        row = _mapping(raw, f"technical_context.relation_{index}")
        expected_fields = {
            "evidence_id", "subject_ref", "predicate", "object_ref", "status",
            "evidence_refs", "signals", "artistic_truth", "asset_selection",
        }
        if set(row) != expected_fields:
            raise ProductViewError(f"technical_context_relation_{index}_field_set_invalid")
        evidence_id = _text(row.get("evidence_id"), "technical_evidence.evidence_id")
        if not evidence_id.startswith("technical-evidence:"):
            raise ProductViewError(f"technical_context_relation_{index}_id_invalid")
        subject_ref = _text(row.get("subject_ref"), "technical_evidence.subject_ref")
        predicate = _text(row.get("predicate"), "technical_evidence.predicate")
        object_ref = _text(row.get("object_ref"), "technical_evidence.object_ref")
        status = _text(row.get("status"), "technical_evidence.status")
        if not predicate.startswith("technical_"):
            raise ProductViewError(f"technical_context_relation_{index}_predicate_invalid")
        if status not in {"candidate", "observed"}:
            raise ProductViewError(f"technical_context_relation_{index}_status_invalid")
        evidence_refs = _refs(
            row.get("evidence_refs"),
            f"technical_evidence.{evidence_id}.evidence_refs",
        )
        if evidence_refs != row.get("evidence_refs"):
            raise ProductViewError(f"technical_context_relation_{index}_evidence_refs_not_sorted_unique")
        signals = _refs(
            row.get("signals"),
            f"technical_evidence.{evidence_id}.signals",
        )
        if signals != row.get("signals"):
            raise ProductViewError(f"technical_context_relation_{index}_signals_not_sorted_unique")
        if row.get("artistic_truth") is not False or row.get("asset_selection") is not False:
            raise ProductViewError(f"technical_context_relation_{index}_promotion")
        rows.append({
            "evidence_id": evidence_id,
            "subject_ref": subject_ref,
            "predicate": predicate,
            "object_ref": object_ref,
            "status": status,
            "evidence_refs": evidence_refs,
            "signals": signals,
            "artistic_truth": False,
            "asset_selection": False,
        })
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ProductViewError("technical_evidence_ids_not_unique")
    if rows != sorted(rows, key=lambda row: row["evidence_id"]):
        raise ProductViewError("technical_evidence_not_sorted")
    return rows, context_hash


def project_product_view(
    plan: Mapping[str, Any],
    dossier: Mapping[str, Any],
    package: Mapping[str, Any],
) -> dict[str, Any]:
    """Join existing product consumers into a bounded human-facing view."""
    opportunity_id, plan_hash, dossier_hash = _validate_inputs(plan, dossier, package)
    technical_evidence, technical_context_hash = _technical_evidence_projection(dossier)
    application = _mapping(package["application_draft"], "application_draft")
    research = _mapping(package["research_brief"], "research_brief")
    atoms = _list(dossier.get("narrative_atoms"), "portfolio_dossier.narrative_atoms")
    claims = []
    for raw in atoms:
        row = _mapping(raw, "portfolio_dossier.narrative_atom")
        claim_id = _text(row.get("claim_id"), "narrative_atom.claim_id")
        evidence_refs = _refs(row.get("evidence_refs"), f"narrative_atom.{claim_id}.evidence_refs")
        claims.append({
            "claim_id": claim_id,
            "type": _text(row.get("type"), f"narrative_atom.{claim_id}.type"),
            "status": "supported" if row.get("type") == "documented_fact" else _text(row.get("type"), f"narrative_atom.{claim_id}.type"),
            "statement": _text(row.get("statement"), f"narrative_atom.{claim_id}.statement"),
            "evidence_refs": evidence_refs,
            "unit_ids": _refs(row.get("unit_ids"), f"narrative_atom.{claim_id}.unit_ids"),
        })
    claims.sort(key=lambda row: row["claim_id"])

    asset_manifest = _list(dossier.get("asset_manifest"), "portfolio_dossier.asset_manifest")
    public_manifest = _list(dossier.get("public_manifest"), "portfolio_dossier.public_manifest")
    public_refs = set()
    for raw in public_manifest:
        row = _mapping(raw, "public_asset")
        public_refs.add(_text(row.get("artifact_ref"), "public_asset.artifact_ref"))
    asset_summary = {
        "internal_asset_count": len(asset_manifest),
        "public_eligible_count": len(public_manifest),
        "public_asset_refs": sorted(ref for ref in public_refs if ref),
        "private_or_license_unknown_count": len(asset_manifest) - len(public_manifest),
        "physical_identity_preserved": len({row.get("artifact_ref") for row in asset_manifest}) == len(asset_manifest),
    }
    programs = _list(plan.get("selected_programs"), "product_plan.selected_programs")
    for raw in programs:
        _mapping(raw, "product_plan.selected_program")
    program_summary = {
        "total_rows": len(programs),
        "selection_counts": _count_values(programs, "selection"),
        "ready_count": sum(row.get("ready") is True for row in programs if isinstance(row, Mapping)),
        "supported_claim_program_count": sum(bool(row.get("supported_claim_ids")) for row in programs if isinstance(row, Mapping)),
    }
    jobs = []
    for raw in _list(research.get("jobs"), "research_brief.jobs"):
        row = _mapping(raw, "research_brief.job")
        jobs.append({
            "job_id": _text(row.get("job_id"), "research_job.job_id"),
            "requirement_id": _text(row.get("requirement_id"), "research_job.requirement_id"),
            "question": _text(row.get("question"), "research_job.question"),
            "domain": _text(row.get("domain"), "research_job.domain"),
            "priority_rank": row.get("priority_rank"),
            "voi": copy.deepcopy(row.get("voi")),
            "status": _text(row.get("status"), "research_job.status"),
            "dispatch": row.get("dispatch"),
        })
    jobs.sort(key=lambda row: (row["priority_rank"] if isinstance(row["priority_rank"], int) else 10**9, row["job_id"], row["requirement_id"]))
    dossier_gaps = _list(dossier.get("gaps"), "portfolio_dossier.gaps")
    research_gaps = _list(research.get("gaps"), "research_brief.gaps")
    blocked_reasons = _refs(application.get("blocked_with_reasons", []), "application_draft.blocked_with_reasons")
    gap_codes = sorted({str(gap) for gap in dossier_gaps if isinstance(gap, str)} | {
        str(row.get("requirement_id")) for row in research_gaps if isinstance(row, Mapping) and row.get("requirement_id")
    } | set(blocked_reasons))
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "scope": "portfolio_general_internal_draft",
        "opportunity_id": opportunity_id,
        "status": "draft_only",
        "lineage": {
            "product_plan_hash": plan_hash,
            "portfolio_dossier_hash": dossier_hash,
            "application_package_product_plan_hash": plan_hash,
            "shared_product_plan_hash": True,
        },
        "selection": program_summary,
        "claims": claims,
        "technical_evidence": technical_evidence,
        "assets": asset_summary,
        "research": {
            "status": _text(research.get("status"), "research_brief.status"),
            "pending_job_count": len(jobs),
            "jobs": jobs,
        },
        "application": {
            "status": _text(application.get("status"), "application_draft.status"),
            "submission_ready": application.get("submission_ready") is True,
            "blocked_reasons": blocked_reasons,
        },
        "gaps": {
            "count": len(dossier_gaps) + len(research_gaps) + len(blocked_reasons),
            "codes": gap_codes,
            "dossier_gap_count": len(dossier_gaps),
            "research_gap_count": len(research_gaps),
        },
        "control": {
            "publication": False,
            "submission": False,
            "dispatch": False,
            "training_permitted": False,
            "promotion": "none",
        },
        "provenance": {
            "source_schemas": [PLAN_SCHEMA, DOSSIER_SCHEMA, PACKAGE_SCHEMA],
            "deterministic": True,
            "claims_are_evidence_bounded": True,
            "public_assets_only_when_explicitly_eligible": True,
            "technical_evidence_is_provenance_only": True,
        },
    }
    if technical_context_hash is not None:
        result["lineage"]["technical_context_hash"] = technical_context_hash
    return result


def validate_product_view(payload: Any) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ProductViewError("product_view_schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ProductViewError("product_view_algorithm_version_invalid")
    if payload.get("scope") != "portfolio_general_internal_draft":
        raise ProductViewError("product_view_scope_invalid")
    lineage = _mapping(payload.get("lineage"), "product_view.lineage")
    if lineage.get("shared_product_plan_hash") is not True:
        raise ProductViewError("product_view_lineage_not_shared")
    control = _mapping(payload.get("control"), "product_view.control")
    if any(control.get(key) is not False for key in ("publication", "submission", "dispatch", "training_permitted")):
        raise ProductViewError("product_view_control_not_fail_closed")
    if control.get("promotion") != "none":
        raise ProductViewError("product_view_promotion_not_none")
    for key in ("claims", "research"):
        if key not in payload:
            raise ProductViewError(f"product_view_{key}_missing")
    if "technical_evidence" in payload:
        technical_rows = _list(payload.get("technical_evidence"), "product_view.technical_evidence")
        seen_ids: set[str] = set()
        for index, raw in enumerate(technical_rows):
            row = _mapping(raw, f"product_view.technical_evidence_{index}")
            expected_fields = {
                "evidence_id", "subject_ref", "predicate", "object_ref", "status",
                "evidence_refs", "signals", "artistic_truth", "asset_selection",
            }
            if set(row) != expected_fields:
                raise ProductViewError(f"product_view_technical_evidence_{index}_field_set_invalid")
            evidence_id = _text(row.get("evidence_id"), "product_view.technical_evidence.evidence_id")
            if not evidence_id.startswith("technical-evidence:") or evidence_id in seen_ids:
                raise ProductViewError(f"product_view_technical_evidence_{index}_id_invalid")
            seen_ids.add(evidence_id)
            if not _text(row.get("subject_ref"), "product_view.technical_evidence.subject_ref") or not _text(row.get("object_ref"), "product_view.technical_evidence.object_ref"):
                raise ProductViewError(f"product_view_technical_evidence_{index}_endpoint_invalid")
            if not _text(row.get("predicate"), "product_view.technical_evidence.predicate").startswith("technical_"):
                raise ProductViewError(f"product_view_technical_evidence_{index}_predicate_invalid")
            if row.get("status") not in {"candidate", "observed"}:
                raise ProductViewError(f"product_view_technical_evidence_{index}_status_invalid")
            for field in ("evidence_refs", "signals"):
                refs = _refs(row.get(field), f"product_view.technical_evidence.{field}")
                if refs != row.get(field):
                    raise ProductViewError(f"product_view_technical_evidence_{index}_{field}_not_sorted_unique")
            if row.get("artistic_truth") is not False or row.get("asset_selection") is not False:
                raise ProductViewError(f"product_view_technical_evidence_{index}_promotion")
        if technical_rows != sorted(technical_rows, key=lambda row: row["evidence_id"]):
            raise ProductViewError("product_view_technical_evidence_not_sorted")
    if "technical_context_hash" in lineage:
        technical_hash = _text(lineage.get("technical_context_hash"), "product_view.technical_context_hash")
        if not technical_hash.startswith("sha256:"):
            raise ProductViewError("product_view_technical_context_hash_invalid")
        if "technical_evidence" not in payload:
            raise ProductViewError("product_view_technical_evidence_missing")
    return True


def render_product_markdown(view: Mapping[str, Any]) -> str:
    validate_product_view(view)
    claims = view["claims"]
    lines = [
        "# MAK — borrador interno de portafolio",
        "",
        f"Estado: `{view['status']}` · oportunidad: `{view['opportunity_id']}`",
        "",
        "Este documento es una proyección auditable del plan común. No es una publicación ni una postulación enviada.",
        "",
        "## Qué puede defenderse",
        "",
    ]
    if claims:
        for row in claims:
            refs = ", ".join(f"`{ref}`" for ref in row["evidence_refs"]) or "sin referencias de evidencia"
            lines.extend([f"- **{row['status']}** `{row['claim_id']}`: {row['statement']}", f"  Evidencia: {refs}"])
    else:
        lines.append("No hay claims narrativos apoyados en este run.")
    technical_rows = view.get("technical_evidence", [])
    lines.extend(["", "## Evidencia técnica auxiliar", ""])
    if technical_rows:
        for row in technical_rows:
            refs = ", ".join(f"`{ref}`" for ref in row["evidence_refs"]) or "sin referencias"
            signals = ", ".join(row["signals"]) or "sin señales declaradas"
            lines.append(
                f"- `{row['subject_ref']}` — `{row['predicate']}` — `{row['object_ref']}` "
                f"({row['status']}); señales: {signals}; evidencia: {refs}"
            )
        lines.append("Estas relaciones son auxiliares y no prueban autoría ni identidad de obra.")
    else:
        lines.append("No hay evidencia técnica auxiliar en este run.")
        lines.append("La ausencia de esta señal no prueba autoría ni identidad de obra.")
    assets = view["assets"]
    lines.extend([
        "",
        "## Assets",
        "",
        f"Inventario interno: {assets['internal_asset_count']} assets físicos; elegibles para manifestación pública: {assets['public_eligible_count']}.",
    ])
    if assets["public_asset_refs"]:
        lines.append("Refs públicas explícitas: " + ", ".join(f"`{ref}`" for ref in assets["public_asset_refs"]))
    else:
        lines.append("No hay assets con elegibilidad pública explícita; no se muestran como publicables.")
    lines.extend(["", "## Research pendiente", ""])
    if view["research"]["jobs"]:
        for job in view["research"]["jobs"]:
            lines.append(f"- `{job['job_id']}` ({job['domain']}): {job['question']} — dispatch `{job['dispatch']}`")
    else:
        lines.append("No hay trabajos de research pendientes.")
    lines.extend([
        "",
        "## Estado de postulación",
        "",
        f"`{view['application']['status']}`; submission_ready=`{view['application']['submission_ready']}`.",
        "Razones: " + (", ".join(f"`{reason}`" for reason in view["application"]["blocked_reasons"]) or "ninguna"),
        "",
        "## Provenance",
        "",
        f"product_plan: `{view['lineage']['product_plan_hash']}`",
        f"portfolio_dossier: `{view['lineage']['portfolio_dossier_hash']}`",
        "El orden es provisional y no convierte una hipótesis en verdad autoral.",
    ])
    return "\n".join(lines) + "\n"


def _archive_piece_ref(piece_id: str) -> str:
    return f"iskvw:piece:{piece_id}"


def _archive_piece_source_stem(piece_id: str) -> str | None:
    """The numeric source id encoded by corpus piece identifiers."""
    if not piece_id.startswith("corpus-"):
        return None
    tail = piece_id.rsplit("-", 1)[-1]
    return tail if tail.isdigit() else None


def _archive_public_media(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {"tipo": "ninguno"}
    medium = _mapping(value, field)
    media_type = _text(medium.get("tipo"), f"{field}.tipo", required=False) or "ninguno"
    result: dict[str, Any] = {"tipo": media_type}
    for key in ("src", "poster"):
        if key not in medium or medium.get(key) is None:
            continue
        ref = _text(medium.get(key), f"{field}.{key}")
        if ref.startswith(("/", "~")) or ref.startswith(".."):
            raise ProductViewError(f"{field}.{key}_private_path")
        result[key] = ref
    if "estado_fuente" in medium:
        state = _text(medium.get("estado_fuente"), f"{field}.estado_fuente", required=False)
        if state:
            result["source_state"] = state
    return result


def _archive_source(archive: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    if not isinstance(archive, Mapping):
        raise ProductViewError("archive_source_must_be_object")
    if archive.get("version") != 1:
        raise ProductViewError("archive_source_version_invalid")
    _text(archive.get("fuente"), "archive_source.fuente")
    raw_pieces = _list(archive.get("piezas"), "archive_source.piezas")
    raw_links = _list(archive.get("vinculos"), "archive_source.vinculos")
    pieces: list[dict[str, Any]] = []
    piece_ids: set[str] = set()
    for index, raw in enumerate(raw_pieces):
        row = _mapping(raw, f"archive_source.piece_{index}")
        piece_id = _text(row.get("id"), f"archive_source.piece_{index}.id")
        if piece_id in piece_ids:
            raise ProductViewError(f"archive_source_duplicate_piece:{piece_id}")
        piece_ids.add(piece_id)
        title = row.get("titulo")
        if title is not None and not isinstance(title, str):
            raise ProductViewError(f"archive_source_piece_title_invalid:{piece_id}")
        summary = row.get("resumen")
        if summary is not None and not isinstance(summary, str):
            raise ProductViewError(f"archive_source_piece_summary_invalid:{piece_id}")
        piece_class = _text(row.get("clase"), f"archive_source.piece_{index}.clase")
        date = row.get("fecha")
        if date is not None and not isinstance(date, str):
            raise ProductViewError(f"archive_source_piece_date_invalid:{piece_id}")
        tags = row.get("etiquetas", [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise ProductViewError(f"archive_source_piece_tags_invalid:{piece_id}")
        weight = row.get("peso", 1)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or weight < 0:
            raise ProductViewError(f"archive_source_piece_weight_invalid:{piece_id}")
        state = row.get("estado", "unknown")
        if not isinstance(state, str) or not state.strip():
            raise ProductViewError(f"archive_source_piece_state_invalid:{piece_id}")
        extra = row.get("extra", {})
        if extra is None:
            extra = {}
        if not isinstance(extra, Mapping):
            raise ProductViewError(f"archive_source_piece_extra_invalid:{piece_id}")
        perceived = extra.get("percibido")
        if perceived is not None and not isinstance(perceived, str):
            raise ProductViewError(f"archive_source_piece_perceived_invalid:{piece_id}")
        medium = _archive_public_media(row.get("medio"), f"archive_source.piece_{index}.medio")
        pieces.append({
            "id": piece_id,
            "title": title.strip() if isinstance(title, str) and title.strip() else None,
            "summary": summary.strip() if isinstance(summary, str) and summary.strip() else None,
            "class": piece_class,
            "date": date.strip() if isinstance(date, str) and date.strip() else None,
            "tags": sorted(set(tag.strip() for tag in tags)),
            "weight": weight,
            "medium": medium,
            "state": state.strip(),
            "perceived_observation": perceived.strip() if isinstance(perceived, str) and perceived.strip() else None,
        })
    links: list[dict[str, Any]] = []
    link_keys: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_links):
        row = _mapping(raw, f"archive_source.link_{index}")
        left = _text(row.get("de"), f"archive_source.link_{index}.de")
        right = _text(row.get("a"), f"archive_source.link_{index}.a")
        if left not in piece_ids or right not in piece_ids:
            raise ProductViewError(f"archive_source_link_endpoint_unknown:{left}:{right}")
        if left == right:
            raise ProductViewError(f"archive_source_self_link:{left}")
        weight = row.get("peso")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or not 0 <= weight <= 1:
            raise ProductViewError(f"archive_source_link_weight_invalid:{left}:{right}")
        link_class = _text(row.get("clase", "unknown"), f"archive_source.link_{index}.clase", required=False) or "unknown"
        key = (min(left, right), max(left, right), link_class)
        if key in link_keys:
            raise ProductViewError(f"archive_source_duplicate_link:{key[0]}:{key[1]}:{key[2]}")
        link_keys.add(key)
        links.append({"left": key[0], "right": key[1], "class": link_class, "weight": weight})
    return pieces, sorted(links, key=lambda row: (row["left"], row["right"], row["class"])), _hash(archive)


def project_archive_portfolio_view(
    archive: Mapping[str, Any],
    *,
    max_items_per_format: int = 24,
    human_triage: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project the existing ISKVW archive into four non-destructive portfolio readings.

    This is intentionally a consumer of ``iskvw/datos/archivo.json`` rather
    than a second archive model.  The source already distinguishes declared
    pieces, observed corpus material and code; this projection keeps those
    boundaries visible and gives each selected row its source reference.

    ``human_triage`` is optional read-only enrichment from a named person's
    existing record-vs-work decisions. It moves explicitly triaged records out
    of the declared and observed readings without inventing a new class.
    """
    if isinstance(max_items_per_format, bool) or not isinstance(max_items_per_format, int) or not 1 <= max_items_per_format <= 500:
        raise ProductViewError("archive_view_max_items_invalid")
    pieces, links, input_hash = _archive_source(archive)
    degrees: dict[str, int] = {row["id"]: 0 for row in pieces}
    for link in links:
        degrees[link["left"]] += 1
        degrees[link["right"]] += 1
    by_id = {row["id"]: row for row in pieces}
    human_triage = human_triage or {}

    documented_record_ids = sorted(
        row["id"] for row in pieces
        if row["class"] == "obra"
        and (stem := _archive_piece_source_stem(row["id"])) is not None
        and (declared := human_triage.get(stem))
        and declared.get("value") == "record"
    )
    documented_record_set = set(documented_record_ids)
    declared_ids = sorted(
        row["id"] for row in pieces
        if row["class"] == "obra" and row["title"] and row["summary"]
        and row["id"] not in documented_record_set
    )
    observed_rows = [
        row for row in pieces
        if row["class"] == "obra"
        and row["id"] not in set(declared_ids)
        and row["id"] not in documented_record_set
    ]
    observed_rows.sort(key=lambda row: (
        -int(bool(row["medium"].get("src"))),
        -int(bool(row["perceived_observation"])),
        -float(row["weight"]),
        -degrees[row["id"]],
        row["id"],
    ))
    observed_ids = sorted(row["id"] for row in observed_rows[:max_items_per_format])
    practice_rows = [row for row in pieces if row["class"] == "codigo"]
    practice_rows.sort(key=lambda row: (-float(row["weight"]), -degrees[row["id"]], row["id"]))
    practice_ids = sorted(row["id"] for row in practice_rows[:max_items_per_format])

    roles: dict[str, list[str]] = {}
    for piece_id in declared_ids:
        roles[piece_id] = ["declared_work"]
    for piece_id in documented_record_ids:
        roles.setdefault(piece_id, []).append("documented_record")
    for piece_id in observed_ids:
        roles.setdefault(piece_id, []).append("observed_archive_piece")
    for piece_id in practice_ids:
        roles.setdefault(piece_id, []).append("practice_context")

    selected_ids = sorted(roles)
    items: list[dict[str, Any]] = []
    for piece_id in selected_ids:
        row = by_id[piece_id]
        reasons = []
        if "declared_work" in roles[piece_id]:
            reasons.extend(["source_class_obra", "explicit_title", "explicit_summary"])
        if "documented_record" in roles[piece_id]:
            triage = human_triage[_archive_piece_source_stem(piece_id)]
            reasons.append("human_triage_record")
            if not triage.get("kept_as_draft", True):
                reasons.append("human_triage_confirmed")
        if "observed_archive_piece" in roles[piece_id]:
            reasons.append("bounded_observed_archive_selection")
            if row["perceived_observation"]:
                reasons.append("source_perception_available")
        if "practice_context" in roles[piece_id]:
            reasons.extend(["source_class_codigo", "bounded_practice_selection"])
        if "declared_work" in roles[piece_id]:
            epistemic_status = "declared_source_record"
        elif "documented_record" in roles[piece_id]:
            epistemic_status = "human_declared_record"
        else:
            epistemic_status = "observed_source_record"
        item = {
            "item_id": piece_id,
            "source_ref": _archive_piece_ref(piece_id),
            "roles": sorted(roles[piece_id]),
            "title": row["title"],
            "summary": row["summary"],
            "observed_description": row["perceived_observation"],
            "class": row["class"],
            "date": row["date"],
            "tags": row["tags"],
            "weight": row["weight"],
            "medium": row["medium"],
            "source_state": row["state"],
            "link_degree": degrees[piece_id],
            "selection_reasons": sorted(set(reasons)),
            "epistemic_status": epistemic_status,
            "observed_description_is_not_author_statement": bool(row["perceived_observation"]),
        }
        items.append(item)
    selected_set = set(selected_ids)
    projected_links = [
        {
            "source_ref": f"iskvw:link:{link['left']}:{link['right']}:{link['class']}",
            "piece_a": link["left"],
            "piece_b": link["right"],
            "class": link["class"],
            "weight": link["weight"],
            "epistemic_status": "measured_link" if link["class"] == "semantico" else "source_label_link",
        }
        for link in links
        if link["left"] in selected_set and link["right"] in selected_set
    ]
    projected_links.sort(key=lambda row: row["source_ref"])
    formats = [
        {
            "format_id": "declared-works",
            "purpose": "source-declared works with human-facing text",
            "selection_rule": ["class=obra", "title_present", "summary_present"],
            "item_ids": declared_ids,
            "omitted_count": 0,
        },
        {
            "format_id": "documented-record",
            "purpose": "pieces a named person has already triaged as a record of a work, not the work itself",
            "selection_rule": ["class=obra", "human_triage=record"],
            "item_ids": documented_record_ids,
            "omitted_count": 0,
        },
        {
            "format_id": "observed-field",
            "purpose": "bounded visual/archive field without inventing titles",
            "selection_rule": ["class=obra", "not_declared_work", "not_documented_record", f"max_items={max_items_per_format}"],
            "item_ids": observed_ids,
            "omitted_count": max(0, len(observed_rows) - len(observed_ids)),
        },
        {
            "format_id": "practice-context",
            "purpose": "code and technical practice as context, not artwork",
            "selection_rule": ["class=codigo", f"max_items={max_items_per_format}"],
            "item_ids": practice_ids,
            "omitted_count": max(0, len(practice_rows) - len(practice_ids)),
        },
    ]
    class_counts: dict[str, int] = {}
    state_counts: dict[str, int] = {}
    medium_counts: dict[str, int] = {}
    for row in pieces:
        class_counts[row["class"]] = class_counts.get(row["class"], 0) + 1
        state_counts[row["state"]] = state_counts.get(row["state"], 0) + 1
        medium_type = row["medium"].get("tipo", "ninguno")
        medium_counts[medium_type] = medium_counts.get(medium_type, 0) + 1
    omitted_by_class: dict[str, int] = {}
    for row in pieces:
        if row["id"] not in selected_set:
            omitted_by_class[row["class"]] = omitted_by_class.get(row["class"], 0) + 1
    generated = archive.get("generado")
    if generated is not None and not isinstance(generated, str):
        raise ProductViewError("archive_source.generated_invalid")
    result = {
        "schema": ARCHIVE_VIEW_SCHEMA,
        "algorithm_version": ARCHIVE_VIEW_ALGORITHM_VERSION,
        "scope": "general_archive_portfolio",
        "status": "draft_only",
        "source": {
            "kind": "iskvw_archive_projection",
            "path_hint": "iskvw/datos/archivo.json",
            "version": archive["version"],
            "fuente": archive["fuente"],
            "generated": generated,
            "input_hash": input_hash,
        },
        "formats": formats,
        "items": items,
        "relationships": projected_links,
        "catalog": {
            "piece_count": len(pieces),
            "link_count": len(links),
            "class_counts": {key: class_counts[key] for key in sorted(class_counts)},
            "state_counts": {key: state_counts[key] for key in sorted(state_counts)},
            "medium_counts": {key: medium_counts[key] for key in sorted(medium_counts)},
        },
        "selection": {
            "selected_item_count": len(items),
            "declared_work_count": len(declared_ids),
            "documented_record_count": len(documented_record_ids),
            "observed_field_count": len(observed_ids),
            "practice_context_count": len(practice_ids),
            "max_items_per_format": max_items_per_format,
            "omitted_piece_count": len(pieces) - len(items),
            "omitted_by_class": {key: omitted_by_class[key] for key in sorted(omitted_by_class)},
        },
        "gaps": sorted(set(
            (["unlabeled_archive_material"] if observed_rows else [])
            + (["technical_context_is_not_artwork"] if practice_rows else [])
            + (["omitted_bounded_selection"] if len(pieces) > len(items) else [])
            + (["selected_items_without_media_ref"] if any(not item["medium"].get("src") for item in items) else [])
            + (["selected_items_without_date"] if any(not item["date"] for item in items) else [])
        )),
        "control": {
            "publication": False,
            "submission": False,
            "dispatch": False,
            "training_permitted": False,
            "source_mutation": False,
            "promotion": "none",
        },
        "provenance": {
            "source_schema": "iskvw-archive-v1",
            "source_hash": input_hash,
            "deterministic": True,
            "physical_items_not_merged": True,
            "filename_is_not_authorship": True,
            "observed_text_is_not_author_statement": True,
            "relationship_classes_preserved": True,
            "unselected_source_items_remain_in_input": True,
        },
        "reconciliation": {
            "source_piece_count": len(pieces),
            "source_link_count": len(links),
            "selected_item_count": len(items),
            "projected_link_count": len(projected_links),
            "omitted_piece_count": len(pieces) - len(items),
            "selected_ids_unique": len(selected_ids) == len(set(selected_ids)),
            "relationship_endpoints_selected": all(
                row["piece_a"] in selected_set and row["piece_b"] in selected_set
                for row in projected_links
            ),
            "source_preserved_by_hash": True,
            "truth_promotions": 0,
        },
    }
    validate_archive_portfolio_view(result)
    return result


def validate_archive_portfolio_view(payload: Any) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != ARCHIVE_VIEW_SCHEMA:
        raise ProductViewError("archive_portfolio_view_schema_invalid")
    if payload.get("algorithm_version") != ARCHIVE_VIEW_ALGORITHM_VERSION:
        raise ProductViewError("archive_portfolio_view_algorithm_version_invalid")
    if payload.get("scope") != "general_archive_portfolio" or payload.get("status") != "draft_only":
        raise ProductViewError("archive_portfolio_view_scope_or_status_invalid")
    expected_top = {
        "schema", "algorithm_version", "scope", "status", "source", "formats", "items",
        "relationships", "catalog", "selection", "gaps", "control", "provenance", "reconciliation",
    }
    if set(payload) != expected_top:
        raise ProductViewError("archive_portfolio_view_fields_invalid")
    source = _mapping(payload.get("source"), "archive_portfolio_view.source")
    if set(source) != {"kind", "path_hint", "version", "fuente", "generated", "input_hash"}:
        raise ProductViewError("archive_portfolio_view_source_fields_invalid")
    if source.get("kind") != "iskvw_archive_projection" or source.get("path_hint") != "iskvw/datos/archivo.json" or source.get("version") != 1:
        raise ProductViewError("archive_portfolio_view_source_invalid")
    _text(source.get("fuente"), "archive_portfolio_view.source.fuente")
    if source.get("generated") is not None:
        _text(source.get("generated"), "archive_portfolio_view.source.generated")
    input_hash = _text(source.get("input_hash"), "archive_portfolio_view.source.input_hash")
    if not input_hash.startswith("sha256:") or len(input_hash) != len("sha256:") + 64:
        raise ProductViewError("archive_portfolio_view_source_hash_invalid")
    items = _list(payload.get("items"), "archive_portfolio_view.items")
    item_ids: list[str] = []
    for index, raw in enumerate(items):
        row = _mapping(raw, f"archive_portfolio_view.item_{index}")
        expected = {
            "item_id", "source_ref", "roles", "title", "summary", "observed_description", "class", "date",
            "tags", "weight", "medium", "source_state", "link_degree", "selection_reasons", "epistemic_status",
            "observed_description_is_not_author_statement",
        }
        if set(row) != expected:
            raise ProductViewError(f"archive_portfolio_view.item_{index}_fields_invalid")
        item_id = _text(row.get("item_id"), f"archive_portfolio_view.item_{index}.item_id")
        if item_id in item_ids or row.get("source_ref") != _archive_piece_ref(item_id):
            raise ProductViewError(f"archive_portfolio_view.item_{index}_identity_invalid")
        item_ids.append(item_id)
        roles = _refs(row.get("roles"), f"archive_portfolio_view.item_{index}.roles")
        if roles != row.get("roles") or not set(roles) <= {"declared_work", "documented_record", "observed_archive_piece", "practice_context"}:
            raise ProductViewError(f"archive_portfolio_view.item_{index}_roles_invalid")
        for field in ("title", "summary", "observed_description", "date"):
            if row.get(field) is not None and not isinstance(row.get(field), str):
                raise ProductViewError(f"archive_portfolio_view.item_{index}_{field}_invalid")
        _text(row.get("class"), f"archive_portfolio_view.item_{index}.class")
        _refs(row.get("tags"), f"archive_portfolio_view.item_{index}.tags")
        if row.get("tags") != sorted(set(row.get("tags"))):
            raise ProductViewError(f"archive_portfolio_view.item_{index}_tags_not_sorted_unique")
        weight = row.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or weight < 0:
            raise ProductViewError(f"archive_portfolio_view.item_{index}_weight_invalid")
        if not isinstance(row.get("link_degree"), int) or row["link_degree"] < 0:
            raise ProductViewError(f"archive_portfolio_view.item_{index}_link_degree_invalid")
        _refs(row.get("selection_reasons"), f"archive_portfolio_view.item_{index}.selection_reasons")
        if row.get("epistemic_status") not in {"declared_source_record", "human_declared_record", "observed_source_record"}:
            raise ProductViewError(f"archive_portfolio_view.item_{index}_epistemic_status_invalid")
        if not isinstance(row.get("observed_description_is_not_author_statement"), bool):
            raise ProductViewError(f"archive_portfolio_view.item_{index}_observation_flag_invalid")
        _archive_public_media(row.get("medium"), f"archive_portfolio_view.item_{index}.medium")
    if item_ids != sorted(item_ids) or len(item_ids) != len(set(item_ids)):
        raise ProductViewError("archive_portfolio_view_items_not_sorted_unique")
    for index, raw in enumerate(_list(payload.get("relationships"), "archive_portfolio_view.relationships")):
        row = _mapping(raw, f"archive_portfolio_view.relationship_{index}")
        expected = {"source_ref", "piece_a", "piece_b", "class", "weight", "epistemic_status"}
        if set(row) != expected:
            raise ProductViewError(f"archive_portfolio_view.relationship_{index}_fields_invalid")
        left = _text(row.get("piece_a"), f"archive_portfolio_view.relationship_{index}.piece_a")
        right = _text(row.get("piece_b"), f"archive_portfolio_view.relationship_{index}.piece_b")
        if left >= right or left not in item_ids or right not in item_ids:
            raise ProductViewError(f"archive_portfolio_view.relationship_{index}_endpoints_invalid")
        link_class = _text(row.get("class"), f"archive_portfolio_view.relationship_{index}.class")
        expected_ref = f"iskvw:link:{left}:{right}:{link_class}"
        if row.get("source_ref") != expected_ref:
            raise ProductViewError(f"archive_portfolio_view.relationship_{index}_source_ref_invalid")
        weight = row.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or not 0 <= weight <= 1:
            raise ProductViewError(f"archive_portfolio_view.relationship_{index}_weight_invalid")
        if row.get("epistemic_status") not in {"measured_link", "source_label_link"}:
            raise ProductViewError(f"archive_portfolio_view.relationship_{index}_epistemic_invalid")
    relationships = payload["relationships"]
    if relationships != sorted(relationships, key=lambda row: row["source_ref"]):
        raise ProductViewError("archive_portfolio_view_relationships_not_sorted")
    formats = _list(payload.get("formats"), "archive_portfolio_view.formats")
    format_ids: list[str] = []
    for index, raw in enumerate(formats):
        row = _mapping(raw, f"archive_portfolio_view.format_{index}")
        if set(row) != {"format_id", "purpose", "selection_rule", "item_ids", "omitted_count"}:
            raise ProductViewError(f"archive_portfolio_view.format_{index}_fields_invalid")
        format_id = _text(row.get("format_id"), f"archive_portfolio_view.format_{index}.format_id")
        format_ids.append(format_id)
        _text(row.get("purpose"), f"archive_portfolio_view.format_{index}.purpose")
        _refs(row.get("selection_rule"), f"archive_portfolio_view.format_{index}.selection_rule")
        item_refs = _refs(row.get("item_ids"), f"archive_portfolio_view.format_{index}.item_ids")
        if item_refs != row.get("item_ids") or not set(item_refs) <= set(item_ids):
            raise ProductViewError(f"archive_portfolio_view.format_{index}_items_invalid")
        if not isinstance(row.get("omitted_count"), int) or row["omitted_count"] < 0:
            raise ProductViewError(f"archive_portfolio_view.format_{index}_omitted_invalid")
    if format_ids != ["declared-works", "documented-record", "observed-field", "practice-context"]:
        raise ProductViewError("archive_portfolio_view_formats_invalid")
    catalog = _mapping(payload.get("catalog"), "archive_portfolio_view.catalog")
    if set(catalog) != {"piece_count", "link_count", "class_counts", "state_counts", "medium_counts"}:
        raise ProductViewError("archive_portfolio_view_catalog_fields_invalid")
    for field in ("piece_count", "link_count"):
        if not isinstance(catalog.get(field), int) or catalog[field] < 0:
            raise ProductViewError(f"archive_portfolio_view_catalog_{field}_invalid")
    for field in ("class_counts", "state_counts", "medium_counts"):
        counts = _mapping(catalog.get(field), f"archive_portfolio_view.catalog.{field}")
        if any(not isinstance(key, str) or not isinstance(value, int) or value < 0 for key, value in counts.items()):
            raise ProductViewError(f"archive_portfolio_view_catalog_{field}_values_invalid")
        if list(counts) != sorted(counts):
            raise ProductViewError(f"archive_portfolio_view_catalog_{field}_not_sorted")
    selection = _mapping(payload.get("selection"), "archive_portfolio_view.selection")
    required_selection = {"selected_item_count", "declared_work_count", "documented_record_count", "observed_field_count", "practice_context_count", "max_items_per_format", "omitted_piece_count", "omitted_by_class"}
    if set(selection) != required_selection:
        raise ProductViewError("archive_portfolio_view_selection_fields_invalid")
    for field in required_selection - {"omitted_by_class"}:
        if not isinstance(selection.get(field), int) or selection[field] < 0:
            raise ProductViewError(f"archive_portfolio_view_selection_{field}_invalid")
    if selection["selected_item_count"] != len(items) or selection["omitted_piece_count"] != catalog["piece_count"] - len(items):
        raise ProductViewError("archive_portfolio_view_selection_reconciliation_invalid")
    omitted_by_class = _mapping(selection.get("omitted_by_class"), "archive_portfolio_view.selection.omitted_by_class")
    if list(omitted_by_class) != sorted(omitted_by_class) or any(not isinstance(value, int) or value < 0 for value in omitted_by_class.values()):
        raise ProductViewError("archive_portfolio_view_omitted_by_class_invalid")
    gaps = _refs(payload.get("gaps"), "archive_portfolio_view.gaps")
    if gaps != payload.get("gaps"):
        raise ProductViewError("archive_portfolio_view_gaps_not_sorted_unique")
    control = _mapping(payload.get("control"), "archive_portfolio_view.control")
    if control != {
        "publication": False, "submission": False, "dispatch": False,
        "training_permitted": False, "source_mutation": False, "promotion": "none",
    }:
        raise ProductViewError("archive_portfolio_view_control_not_fail_closed")
    provenance = _mapping(payload.get("provenance"), "archive_portfolio_view.provenance")
    if provenance.get("source_hash") != input_hash or provenance.get("deterministic") is not True or provenance.get("physical_items_not_merged") is not True or provenance.get("filename_is_not_authorship") is not True or provenance.get("observed_text_is_not_author_statement") is not True or provenance.get("relationship_classes_preserved") is not True or provenance.get("unselected_source_items_remain_in_input") is not True:
        raise ProductViewError("archive_portfolio_view_provenance_invalid")
    reconciliation = _mapping(payload.get("reconciliation"), "archive_portfolio_view.reconciliation")
    expected_reconciliation = {
        "source_piece_count", "source_link_count", "selected_item_count", "projected_link_count",
        "omitted_piece_count", "selected_ids_unique", "relationship_endpoints_selected", "source_preserved_by_hash", "truth_promotions",
    }
    if set(reconciliation) != expected_reconciliation:
        raise ProductViewError("archive_portfolio_view_reconciliation_fields_invalid")
    if reconciliation["source_piece_count"] != catalog["piece_count"] or reconciliation["selected_item_count"] != len(items) or reconciliation["omitted_piece_count"] != selection["omitted_piece_count"] or reconciliation["projected_link_count"] != len(relationships) or reconciliation["selected_ids_unique"] is not True or reconciliation["relationship_endpoints_selected"] is not True or reconciliation["source_preserved_by_hash"] is not True or reconciliation["truth_promotions"] != 0:
        raise ProductViewError("archive_portfolio_view_reconciliation_invalid")
    return True


def render_archive_portfolio_markdown(view: Mapping[str, Any]) -> str:
    validate_archive_portfolio_view(view)
    source = view["source"]
    lines = [
        "# MAK — borrador general del archivo",
        "",
        "Cuatro lecturas del mismo archivo, sin fusionar identidad ni convertir observaciones en autoría.",
        "",
        f"Fuente: `{source['path_hint']}` · piezas: {view['catalog']['piece_count']} · vínculos: {view['catalog']['link_count']}",
        f"Estado: `{view['status']}` · hash: `{source['input_hash']}`",
        "",
        "## Formatos propuestos",
        "",
    ]
    for fmt in view["formats"]:
        lines.append(f"- **{fmt['format_id']}**: {fmt['purpose']} ({len(fmt['item_ids'])} seleccionados; {fmt['omitted_count']} omitidos por límite).")
    lines.extend(["", "## Obras declaradas", ""])
    declared = [row for row in view["items"] if "declared_work" in row["roles"]]
    if not declared:
        lines.append("No hay registros con título y resumen explícitos.")
    for row in declared:
        media = row["medium"].get("src") or "sin media declarada"
        lines.extend([f"- **{row['title']}** ({row['date'] or 'sin fecha'}) — {row['summary']}", f"  Media: `{media}` · evidencia: `{row['source_ref']}`"])
    lines.extend(["", "## Registros documentados (una persona ya lo marcó: es registro, no obra)", ""])
    documented = [row for row in view["items"] if "documented_record" in row["roles"]]
    if not documented:
        lines.append("Nadie ha triado ningún ítem como registro todavía.")
    for row in documented:
        description = row["observed_description"] or "sin descripción perceptual"
        lines.append(f"- `{row['item_id']}` — {description}; media `{row['medium'].get('src') or 'sin ref'}`; evidencia `{row['source_ref']}`.")
    lines.extend(["", "## Campo observado (no son títulos autorales)", ""])
    observed = [row for row in view["items"] if "observed_archive_piece" in row["roles"]]
    if not observed:
        lines.append("No hay material observado seleccionado.")
    for row in observed:
        description = row["observed_description"] or "sin descripción perceptual"
        lines.append(f"- `{row['item_id']}` — {description}; media `{row['medium'].get('src') or 'sin ref'}`; vínculos medidos {row['link_degree']}.")
    lines.extend(["", "## Práctica y código (contexto, no obra automáticamente)", ""])
    practice = [row for row in view["items"] if "practice_context" in row["roles"]]
    for row in practice:
        lines.append(f"- `{row['item_id']}` — {row['title'] or 'sin título declarado'}; peso de fuente {row['weight']}; evidencia `{row['source_ref']}`.")
    lines.extend(["", "## Vínculos conservados", ""])
    for relation in view["relationships"]:
        lines.append(f"- `{relation['piece_a']}` ↔ `{relation['piece_b']}` · `{relation['class']}` · peso {relation['weight']} · `{relation['epistemic_status']}`")
    if not view["relationships"]:
        lines.append("No hay vínculos entre los elementos seleccionados.")
    lines.extend([
        "", "## Límites", "",
        "El campo observado conserva percepción y referencias de fuente; no la presenta como declaración del artista.",
        "Los registros de código quedan como contexto de práctica. Los elementos omitidos permanecen en el archivo fuente y no fueron borrados ni fusionados.",
        "", "Control: publicación=false · submission=false · dispatch=false · training=false · promotion=none", "",
    ])
    return "\n".join(lines)


__all__ = [
    "ALGORITHM_VERSION", "ARCHIVE_VIEW_ALGORITHM_VERSION", "ARCHIVE_VIEW_SCHEMA",
    "ProductViewError", "SCHEMA", "project_archive_portfolio_view", "project_product_view",
    "render_archive_portfolio_markdown", "render_product_markdown", "stable_json",
    "validate_archive_portfolio_view", "validate_product_view",
]
