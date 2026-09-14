"""Render one portfolio document from a declared plant and a claim base.

Two answers, in this order:

1. **Feasibility, before producing.** For every slot, how many claims actually
   reach its declared state and permission.  A required slot that cannot be
   filled makes the document infeasible, and the gap is reported as a count and
   a reason -- never as a question queued for a person.
2. **The document.** Selection, ordering and captions, with every claim's state
   and refutation carried into the output.

The caption is where uncertainty is paid.  A claim that cannot fill a slot's
declared grammar is skipped rather than captioned loosely, because refusing to
caption hands the frame to a filename.

This module opens no database, reads no archive and publishes nothing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from .portfolio_claims import SCHEMA as CLAIMS_SCHEMA
from .portfolio_format import (
    PERMISSION_RANK,
    SCHEMA as FORMAT_SCHEMA,
    STATE_RANK,
    accepts,
)
from .product_view import stable_json


SCHEMA = "mak-portfolio-render-v1"
ALGORITHM_VERSION = "portfolio-render-1"

_STATE_LABEL = {
    "observed": "observado",
    "candidate": "candidato",
    "supported_candidate": "candidato con segunda ruta",
    "externally_attested": "atestiguado por una autoridad nombrada",
    "certified": "certificado",
}


class PortfolioRenderError(ValueError):
    """The plant and the claim base cannot produce an honest document."""


def _caption(grammar: str, fields: Mapping[str, Any]) -> str | None:
    """Fill a declared grammar, or return None if a field is missing.

    A missing field is not filled with a placeholder: the claim simply does not
    qualify for this slot.  Silence beats a caption the evidence cannot carry.
    """
    result = ""
    depth = 0
    name = ""
    for char in grammar:
        if char == "{":
            depth = 1
            name = ""
        elif char == "}":
            depth = 0
            key = name.strip()
            if key not in fields:
                return None
            value = fields[key]
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            result += str(value)
        elif depth:
            name += char
        else:
            result += char
    return result.strip() or None


def _eligible(
    slot: Mapping[str, Any], claims: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Claims that satisfy this slot completely, plus why the rest failed."""
    rejected = {
        "wrong_verb": 0, "wrong_layer": 0, "state_too_low": 0,
        "permission_too_low": 0, "caption_incomplete": 0,
        "field_value_not_allowed": 0,
    }
    rows: list[dict[str, Any]] = []
    for claim in claims:
        if str(claim.get("verb")) != slot["claim"]:
            rejected["wrong_verb"] += 1
            continue
        if str(claim.get("layer")) != slot["layer"]:
            rejected["wrong_layer"] += 1
            continue
        state = str(claim.get("state"))
        permission = str(claim.get("permission"))
        if state not in STATE_RANK or STATE_RANK[state] < STATE_RANK[slot["min_state"]]:
            rejected["state_too_low"] += 1
            continue
        if (
            permission not in PERMISSION_RANK
            or PERMISSION_RANK[permission] < PERMISSION_RANK[slot["min_permission"]]
        ):
            rejected["permission_too_low"] += 1
            continue
        fields = claim.get("caption_fields") or {}
        required = slot.get("require_fields") or {}
        if required and any(
            str(fields.get(name, "")) not in set(values)
            for name, values in required.items()
        ):
            rejected["field_value_not_allowed"] = rejected.get(
                "field_value_not_allowed", 0) + 1
            continue
        caption = _caption(str(slot["caption_grammar"]), fields)
        if caption is None:
            rejected["caption_incomplete"] += 1
            continue
        rows.append({
            "claim_id": str(claim.get("claim_id")),
            "subject": str(claim.get("subject")),
            "scope": str(claim.get("scope")),
            "state": state,
            "state_label": _STATE_LABEL.get(state, state),
            "permission": permission,
            "caption": caption,
            "generated_by": str(claim.get("generated_by")),
            "supported_by": list(claim.get("supported_by") or []),
            "evidence_refs": list(claim.get("evidence_refs") or []),
            "refuted_by": str(claim.get("refuted_by") or ""),
            "duplicate_routes": [],
        })
    # Strongest evidence first; the claim id only breaks exact ties, so the
    # order is never an artifact of insertion sequence.
    rows.sort(key=lambda row: (-STATE_RANK[row["state"]], row["subject"], row["claim_id"]))
    # Two independent routes to the same sentence are one line for a reader.  The
    # stronger row survives and records that a duplicate was folded into it, so
    # the second route is not silently lost.
    deduped: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        existing = seen.get(row["caption"])
        if existing is None:
            seen[row["caption"]] = row
            row["duplicate_routes"] = []
            deduped.append(row)
            continue
        rejected["duplicate_caption"] = rejected.get("duplicate_caption", 0) + 1
        existing["duplicate_routes"].append(row["generated_by"])
        existing["evidence_refs"] = sorted(
            set(existing["evidence_refs"]) | set(row["evidence_refs"]))
    return deduped, rejected


def assess_feasibility(
    portfolio_format: Mapping[str, Any], claim_base: Mapping[str, Any],
) -> dict[str, Any]:
    """Answer whether this plant can be filled, before producing anything."""
    if portfolio_format.get("schema") != FORMAT_SCHEMA:
        raise PortfolioRenderError("format_schema_invalid")
    if claim_base.get("schema") != CLAIMS_SCHEMA:
        raise PortfolioRenderError("claims_schema_invalid")
    claims = claim_base.get("claims")
    if not isinstance(claims, list):
        raise PortfolioRenderError("claims_missing")

    slots: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    for slot in portfolio_format["slots"]:
        rows, rejected = _eligible(slot, claims)
        minimum = int(slot["count"]["min"])
        maximum = int(slot["count"]["max"])
        satisfied = len(rows) >= minimum
        row = {
            "slot_id": slot["slot_id"],
            "claim": slot["claim"],
            "layer": slot["layer"],
            "min_state": slot["min_state"],
            "min_permission": slot["min_permission"],
            "required": bool(slot["required"]),
            "needs": minimum,
            "accepts_up_to": maximum,
            "eligible": len(rows),
            "will_render": min(len(rows), maximum),
            "satisfied": satisfied,
            "shortfall": max(0, minimum - len(rows)),
            "rejected_reasons": {k: v for k, v in sorted(rejected.items()) if v},
        }
        slots.append(row)
        if slot["required"] and not satisfied:
            blocking.append({
                "slot_id": slot["slot_id"],
                "shortfall": row["shortfall"],
                "reason": (
                    f"la ranura obligatoria '{slot['slot_id']}' pide {minimum} "
                    f"afirmaciones {slot['claim']} en capa {slot['layer']} con estado "
                    f">= {slot['min_state']} y permiso >= {slot['min_permission']}; "
                    f"hay {len(rows)}"
                ),
                "what_would_close_it": (
                    f"una afirmacion {slot['claim']} mas que alcance "
                    f"{slot['min_state']}, o una declaracion que la habilite"
                ),
            })
    feasible = not blocking
    return {
        "schema": "mak-portfolio-feasibility-v1",
        "format_id": portfolio_format["format_id"],
        "format_hash": portfolio_format.get("format_hash"),
        "claims_hash": claim_base.get("claims_hash"),
        "feasible": feasible,
        "status": "feasible" if feasible else "infeasible",
        "slots": slots,
        "blocking": blocking,
        "renderable_item_count": sum(row["will_render"] for row in slots),
        "max_items_total": portfolio_format["limits"]["max_items_total"],
    }


def render_portfolio(
    portfolio_format: Mapping[str, Any], claim_base: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce the document, or an explicit infeasibility with its gap."""
    feasibility = assess_feasibility(portfolio_format, claim_base)
    if not feasibility["feasible"]:
        return {
            "schema": SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "status": "infeasible",
            "format_id": portfolio_format["format_id"],
            "format_hash": portfolio_format.get("format_hash"),
            "claims_hash": claim_base.get("claims_hash"),
            "feasibility": feasibility,
            "document": None,
            "reason": "una o mas ranuras obligatorias no alcanzan su minimo declarado",
            "control": _control(),
        }

    claims = claim_base["claims"]
    budget = int(portfolio_format["limits"]["max_items_total"])
    eligible_by_slot = {
        slot["slot_id"]: _eligible(slot, claims)[0] for slot in portfolio_format["slots"]
    }

    # One claim may satisfy several slots.  It is assigned to exactly one, so the
    # document never repeats an item.  Assignment prefers the claim that fits the
    # fewest slots, which keeps a specific claim from being consumed by a broad
    # slot that a narrower required slot needed.
    slot_fit_count: dict[str, int] = {}
    for rows in eligible_by_slot.values():
        for row in rows:
            slot_fit_count[row["claim_id"]] = slot_fit_count.get(row["claim_id"], 0) + 1

    assigned: dict[str, list[dict[str, Any]]] = {
        slot["slot_id"]: [] for slot in portfolio_format["slots"]
    }
    taken: set[str] = set()

    def available(slot_id: str) -> list[dict[str, Any]]:
        return [
            row for row in eligible_by_slot[slot_id]
            if row["claim_id"] not in taken
        ]

    def specificity_order(
        rows: list[dict[str, Any]], prefer_scope: str = "any",
    ) -> list[dict[str, Any]]:
        def scope_rank(row: dict[str, Any]) -> int:
            if prefer_scope == "any":
                return 0
            scope = str(row["scope"])
            head = scope.split(":", 1)[0]
            return 0 if (scope == prefer_scope or head == prefer_scope) else 1
        return sorted(
            rows,
            key=lambda row: (
                scope_rank(row),
                slot_fit_count.get(row["claim_id"], 1),
                -STATE_RANK[row["state"]],
                row["subject"],
                row["claim_id"],
            ),
        )

    # Pass 1: required minimums first, narrowest slot first, so a slot with few
    # options is served before a slot with many.
    ordered_required = sorted(
        (slot for slot in portfolio_format["slots"] if slot["required"]),
        key=lambda slot: (len(eligible_by_slot[slot["slot_id"]]), slot["slot_id"]),
    )
    for slot in ordered_required:
        slot_id = slot["slot_id"]
        need = int(slot["count"]["min"])
        for row in specificity_order(available(slot_id), slot.get("prefer_scope", "any")):
            if len(assigned[slot_id]) >= need or len(taken) >= budget:
                break
            assigned[slot_id].append(row)
            taken.add(row["claim_id"])

    # Pass 2: optional minimums.
    for slot in portfolio_format["slots"]:
        if slot["required"]:
            continue
        slot_id = slot["slot_id"]
        need = int(slot["count"]["min"])
        for row in specificity_order(available(slot_id), slot.get("prefer_scope", "any")):
            if len(assigned[slot_id]) >= need or len(taken) >= budget:
                break
            assigned[slot_id].append(row)
            taken.add(row["claim_id"])

    # Pass 3: spend the remainder one item at a time, so no slot starves a later one.
    while len(taken) < budget:
        progressed = False
        for slot in portfolio_format["slots"]:
            slot_id = slot["slot_id"]
            if len(taken) >= budget:
                break
            if len(assigned[slot_id]) >= int(slot["count"]["max"]):
                continue
            pool = specificity_order(available(slot_id), slot.get("prefer_scope", "any"))
            if not pool:
                continue
            assigned[slot_id].append(pool[0])
            taken.add(pool[0]["claim_id"])
            progressed = True
        if not progressed:
            break

    sections: list[dict[str, Any]] = []
    used_total = 0
    for slot in portfolio_format["slots"]:
        slot_id = slot["slot_id"]
        selected = sorted(
            assigned[slot_id],
            key=lambda row: (-STATE_RANK[row["state"]], row["subject"], row["claim_id"]),
        )
        used_total += len(selected)
        if not selected and not slot["required"]:
            continue
        sections.append({
            "slot_id": slot["slot_id"],
            "title": slot["title"],
            "claim": slot["claim"],
            "layer": slot["layer"],
            "declared_min_state": slot["min_state"],
            "declared_min_permission": slot["min_permission"],
            "item_count": len(selected),
            "omitted_eligible": max(0, len(eligible_by_slot[slot_id]) - len(selected)),
            "items": selected,
        })

    document = {
        "title": portfolio_format["title"],
        "purpose": portfolio_format["purpose"],
        "language": portfolio_format["language"],
        "consumer": dict(portfolio_format["consumer"]),
        "declared_claims": list(portfolio_format["declared_claims"]),
        "forbidden_claims": list(portfolio_format["forbidden_claims"]),
        "forbidden_inferences": list(portfolio_format["forbidden_inferences"]),
        "sections": sections,
        "item_count": used_total,
        "limits_declared": dict(portfolio_format["limits"]),
        "states_present": sorted({
            item["state"] for section in sections for item in section["items"]}),
        "evidence_ref_count": len({
            ref for section in sections for item in section["items"]
            for ref in item["evidence_refs"]}),
    }
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "status": "rendered",
        "format_id": portfolio_format["format_id"],
        "format_hash": portfolio_format.get("format_hash"),
        "claims_hash": claim_base.get("claims_hash"),
        "feasibility": feasibility,
        "document": document,
        "reason": "todas las ranuras obligatorias alcanzan su minimo declarado",
        "control": _control(),
    }
    validate_portfolio_render(result, portfolio_format)
    result["render_hash"] = "sha256:" + hashlib.sha256(
        stable_json(result).encode("utf-8")).hexdigest()
    return result


def _control() -> dict[str, Any]:
    return {
        "source_rescan": False,
        "physical_mutation": False,
        "database_write": False,
        "network_called": False,
        "publication": False,
        "submission": False,
        "signed_document": False,
        "authorship_claimed": False,
        "training_permitted": False,
        "promotion": "none",
    }


def validate_portfolio_render(
    payload: Mapping[str, Any], portfolio_format: Mapping[str, Any],
) -> bool:
    """Enforce every ``invalid_if`` of the plant against the produced document."""
    if payload.get("schema") != SCHEMA:
        raise PortfolioRenderError("schema_invalid")
    if payload.get("status") == "infeasible":
        if payload.get("document") is not None:
            raise PortfolioRenderError("infeasible_must_not_carry_document")
        return True
    document = payload.get("document")
    if not isinstance(document, Mapping):
        raise PortfolioRenderError("document_missing")

    slots = {row["slot_id"]: row for row in portfolio_format["slots"]}
    forbidden = set(portfolio_format["forbidden_claims"])
    declared = set(portfolio_format["declared_claims"])
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        raise PortfolioRenderError("sections_missing")

    seen_claims: set[str] = set()
    for section in sections:
        slot_id = str(section.get("slot_id"))
        slot = slots.get(slot_id)
        if slot is None:
            raise PortfolioRenderError(f"section_not_in_format:{slot_id}")
        claim = str(section.get("claim"))
        if claim in forbidden:
            raise PortfolioRenderError(f"section_uses_forbidden_claim:{slot_id}:{claim}")
        if claim not in declared:
            raise PortfolioRenderError(f"section_claim_not_declared:{slot_id}:{claim}")
        items = section.get("items")
        if not isinstance(items, list):
            raise PortfolioRenderError(f"section_items_invalid:{slot_id}")
        if slot["required"] and len(items) < int(slot["count"]["min"]):
            raise PortfolioRenderError(f"required_slot_below_minimum:{slot_id}")
        if len(items) > int(slot["count"]["max"]):
            raise PortfolioRenderError(f"slot_above_maximum:{slot_id}")
        for item in items:
            claim_id = str(item.get("claim_id"))
            if claim_id in seen_claims:
                raise PortfolioRenderError(f"claim_used_twice:{claim_id}")
            seen_claims.add(claim_id)
            state = str(item.get("state"))
            if STATE_RANK[state] < STATE_RANK[slot["min_state"]]:
                raise PortfolioRenderError(f"item_state_below_slot_minimum:{claim_id}")
            permission = str(item.get("permission"))
            if PERMISSION_RANK[permission] < PERMISSION_RANK[slot["min_permission"]]:
                raise PortfolioRenderError(f"item_permission_below_slot_minimum:{claim_id}")
            if permission in {"prohibited", "aggregate_only"} and \
                    slot["min_permission"] not in {"aggregate_only"}:
                raise PortfolioRenderError(f"restricted_item_rendered_per_case:{claim_id}")
            if str(item.get("generated_by")) in (item.get("supported_by") or []):
                raise PortfolioRenderError(f"item_self_promoted:{claim_id}")
            if not str(item.get("caption") or "").strip():
                raise PortfolioRenderError(f"item_caption_empty:{claim_id}")
            if not str(item.get("refuted_by") or "").strip():
                raise PortfolioRenderError(f"item_missing_refutation:{claim_id}")
    if int(document.get("item_count") or 0) > int(portfolio_format["limits"]["max_items_total"]):
        raise PortfolioRenderError("document_above_max_items_total")
    control = payload.get("control")
    if not isinstance(control, Mapping):
        raise PortfolioRenderError("control_missing")
    for flag in ("publication", "submission", "signed_document",
                 "authorship_claimed", "training_permitted", "database_write"):
        if control.get(flag) is not False:
            raise PortfolioRenderError(f"control_{flag}_must_be_false")
    return True


def build_portfolio_episode(
    payloads: Sequence[Mapping[str, Any]],
    claim_base: Mapping[str, Any],
    *,
    project_id: str,
    consumer_decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a learning episode for what was produced.

    A learning record needs four fields that earlier episodes lacked: the
    *purpose*, the *variant produced*, the *consumer decision*, and the
    *observed outcome*.  The last two are unknown until a person uses the
    document, so they are recorded as pending rather than invented.  A hash that
    changed is not learning.
    """
    variants = []
    for payload in sorted(payloads, key=lambda row: str(row.get("format_id"))):
        document = payload.get("document")
        variants.append({
            "format_id": payload["format_id"],
            "format_hash": payload.get("format_hash"),
            "status": payload["status"],
            "render_hash": payload.get("render_hash"),
            "item_count": document["item_count"] if document else 0,
            "section_count": len(document["sections"]) if document else 0,
            "consumer": (document or {}).get("consumer", {}).get("kind"),
            "purpose": (document or {}).get("purpose"),
            "states_present": (document or {}).get("states_present", []),
            "blocking": [row["slot_id"] for row in payload["feasibility"]["blocking"]],
        })
    rendered = [row for row in variants if row["status"] == "rendered"]
    semantic = {
        "claims_hash": claim_base.get("claims_hash"),
        "variants": variants,
    }
    episode_hash = "sha256:" + hashlib.sha256(
        stable_json(semantic).encode("utf-8")).hexdigest()
    return {
        "schema": "mak-portfolio-product-episode-v1",
        "episode_id": "episode:portfolio:" + episode_hash[7:39],
        "episode_hash": episode_hash,
        "project_id": project_id,
        # Field 1 of 4: what this production was for.
        "purpose": (
            "produce a portfolio document per declared format from the claim base, "
            "and report infeasibility with its gap instead of abstaining silently"
        ),
        # Field 2 of 4: what was actually produced.
        "variant_produced": variants,
        "rendered_count": len(rendered),
        "infeasible_count": len(variants) - len(rendered),
        # Field 3 of 4: what a consumer decided.  Read from the decisions a person
        # already made, when a log exists; pending otherwise.
        "consumer_decision": dict(consumer_decision) if consumer_decision else {
            "status": "pending",
            "recorded": None,
            "decided_by": None,
            "note": (
                "no consumer decision log was supplied; a decision is the only thing "
                "that makes this episode learning rather than metadata"
            ),
        },
        # Field 4 of 4: the observed outcome.  A prior selection rate is a measured
        # outcome about a *previous* portfolio, not about these documents.
        "observed_outcome": (
            {
                "status": "prior_selection_measured",
                "kind": "human_selection_rate_on_a_previous_portfolio",
                "selection_rate": consumer_decision.get("selection_rate"),
                "selected": consumer_decision.get("selected"),
                "rejected": consumer_decision.get("rejected"),
                "source_refs": consumer_decision.get("source_refs"),
                "applies_to_these_documents": False,
                "note": (
                    "this rate was measured on an earlier portfolio surface; it is the "
                    "baseline these documents can be compared against, not their result"
                ),
            }
            if consumer_decision and consumer_decision.get("status") == "recorded"
            else {
                "status": "pending",
                "recorded": None,
                "kind": None,
                "note": "adjudicated, contracted, exhibited, or edited by the artist",
            }
        ),
        "claim_base": {
            "claims_hash": claim_base.get("claims_hash"),
            "claim_count": claim_base.get("claim_count"),
            "claims_by_state": claim_base.get("claims_by_state"),
            "practice_kind_counts": claim_base.get("practice_kind_counts"),
        },
        "control": _control(),
        "limits": [
            "A rendered document is a draft: nothing was published, submitted or signed.",
            "No claim was promoted by producing a document from it.",
            "This episode is not a training label.",
            "Without a consumer decision and an observed outcome, nothing was learned.",
        ],
    }


def episode_projection(episode: Mapping[str, Any]) -> dict[str, Any]:
    """Project the episode onto the existing LearningStore vocabulary."""
    return {
        "objective": str(episode["purpose"]),
        "phase": "portfolio_production",
        "action": {
            "claims_hash": episode["claim_base"]["claims_hash"],
            "format_ids": [row["format_id"] for row in episode["variant_produced"]],
        },
        "observation": {
            "variant_produced": episode["variant_produced"],
            "claim_base": episode["claim_base"],
            "limits": episode["limits"],
        },
        "outcome": {
            "rendered_count": episode["rendered_count"],
            "infeasible_count": episode["infeasible_count"],
            "consumer_decision": episode["consumer_decision"],
            "observed_outcome": episode["observed_outcome"],
            "learning": {
                "baseline_selection_rate": episode["observed_outcome"].get("selection_rate"),
                "complete": bool(
                    episode["consumer_decision"].get("status") == "recorded"
                    and episode["observed_outcome"].get("applies_to_these_documents")),
                "what_would_complete_it": (
                    "an outcome observed on these documents: adjudicated, contracted, "
                    "exhibited, or edited by the artist"
                ),
            },
        },
        "validation": {
            "status": "passed" if episode["rendered_count"] else "abstained",
            "checks": [
                "format_contract",
                "claim_base_contract",
                "feasibility_before_production",
                "no_self_promoted_claim",
                "authorship_ceiling",
                "permission_never_rendered_per_case",
                "caption_within_declared_fields",
            ],
            "truth_promotions": 0,
            "artistic_fact_mutations": 0,
            "learning_complete": bool(
                episode["consumer_decision"].get("status") == "recorded"
                and episode["observed_outcome"].get("applies_to_these_documents")),
        },
        "status": "needs_evidence",
        "provider": "mak-portfolio",
        "episode_id": episode["episode_id"],
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    """Human-readable rendering of what was produced, or of the gap."""
    lines: list[str] = []
    feasibility = payload.get("feasibility") or {}
    if payload.get("status") == "infeasible":
        lines.append(f"# {payload['format_id']} — no factible")
        lines.append("")
        lines.append(str(payload.get("reason") or ""))
        lines.append("")
        for row in feasibility.get("blocking") or []:
            lines.append(f"- **{row['slot_id']}**: {row['reason']}")
            lines.append(f"  - cerraria con: {row['what_would_close_it']}")
        return "\n".join(lines) + "\n"

    document = payload["document"]
    consumer = document["consumer"]
    lines.append(f"# {document['title']}")
    lines.append("")
    lines.append(document["purpose"])
    lines.append("")
    lines.append(f"**Para:** {consumer['kind']} · decide: {consumer['decision_it_supports']}")
    lines.append(f"**No sirve para:** {'; '.join(consumer['does_not_support'])}")
    lines.append("")
    for section in document["sections"]:
        lines.append(f"## {section['title']}")
        lines.append("")
        for item in section["items"]:
            lines.append(f"- {item['caption']}")
            support = (
                f", segunda ruta: {', '.join(item['supported_by'])}"
                if item["supported_by"] else ""
            )
            lines.append(
                f"  - evidencia: {item['state_label']}{support} · "
                f"origen: {item['generated_by']}")
            lines.append(f"  - se refuta si: {item['refuted_by']}")
        if section["omitted_eligible"]:
            lines.append("")
            lines.append(
                f"_{section['omitted_eligible']} afirmaciones elegibles quedaron fuera "
                f"por el limite declarado de la ranura; permanecen en la base._")
        lines.append("")
    lines.append("## Limites de este documento")
    lines.append("")
    lines.append(f"- Verbos declarados: {', '.join(document['declared_claims'])}")
    if document["forbidden_claims"]:
        lines.append(f"- Verbos prohibidos aqui: {', '.join(document['forbidden_claims'])}")
    for inference in document["forbidden_inferences"]:
        lines.append(f"- No se infiere: {inference}")
    lines.append(
        f"- Estados presentes: {', '.join(document['states_present'])} · "
        f"{document['evidence_ref_count']} referencias de evidencia")
    lines.append(
        "- publicacion=false · envio=false · autoria_reclamada=false · "
        "escritura_en_base=false · entrenamiento=false")
    return "\n".join(lines) + "\n"


__all__ = [
    "ALGORITHM_VERSION", "PortfolioRenderError", "SCHEMA", "assess_feasibility",
    "build_portfolio_episode", "episode_projection",
    "render_markdown", "render_portfolio", "validate_portfolio_render",
]
