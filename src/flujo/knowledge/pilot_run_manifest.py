"""Deterministic, read-only execution of the accepted MAK evidence chain.

The module composes existing contracts.  It does not introduce a new truth
authority, mutate an archive, open a database, dispatch research, publish, or
submit.  Filesystem materialization belongs to the thin CLI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import sha256_ref as sha256_json

from .application_research_package import compile_application_research_package
from .archive_observer import observe_archive
from .archive_observer import validate_batch as validate_observation_batch
from .archive_project_ir_adapter import adapt_archive_units_to_project_ir
from .archive_project_ir_evaluator import evaluate_project_ir_payload
from .archive_reconstruction import project_archive_snapshot
from .archive_relation_evaluator import evaluate_relation_payload
from .archive_relation_inference import infer_archive_relations
from .archive_unit_evaluator import evaluate_unit_payload
from .archive_unit_reconstruction import reconstruct_archive_units
from .artistic_program_evaluator import evaluate_artistic_program_payload
from .artistic_program_hypotheses import generate_artistic_program_hypotheses
from .autonomy_plan import compile_autonomy_plan
from .evidence_return import build_evidence_return
from .opportunity_constraints import compile_opportunity_constraints
from .opportunity_validity_capture import apply_opportunity_validity_capture
from .opportunity_fit import evaluate_opportunity_fit
from .portfolio_dossier import compile_portfolio_dossier
from .possibility_field import build_possibility_field
from .practice_evidence_state import (
    build_practice_evidence_state,
    validate_practice_evidence_state,
)
from .practice_receipt_adapter import apply_practice_receipt_evidence_to_project_ir
from .product_episode import compile_product_episode
from .product_learning import evaluate_product_learning
from .product_plan import compile_product_plan
from .product_view import project_product_view
from .research_evidence_triangulation import triangulate_research_evidence
from .research_frontier_bridge import compile_research_frontier


SCHEMA = "mak-pilot-run-manifest-v1"
ALGORITHM_VERSION = "accepted-chain-replay-2"


class PilotRunError(ValueError):
    """Raised when an accepted boundary fails closed during replay."""


def stable_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        allow_nan=False,
    )


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PilotRunError(f"{name}_must_be_object")
    return value


def _require_valid(report: Mapping[str, Any], name: str) -> None:
    if report.get("valid") is not True:
        errors = report.get("errors", [])
        raise PilotRunError(f"{name}_invalid:{stable_json(errors)}")


def build_pilot_outputs_from_observation(
    observation: Mapping[str, Any],
    opportunity_package: Mapping[str, Any],
    *,
    source_rescan: bool = False,
    archive_root: str | None = None,
    max_files: int | None = None,
    practice_receipt_evidence: Mapping[str, Any] | None = None,
    opportunity_validity_capture: Mapping[str, Any] | None = None,
    technical_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay the canonical accepted chain from one immutable observation."""
    observation = _require_mapping(observation, "observation")
    if validate_observation_batch(observation) is not True:
        raise PilotRunError("observation_invalid")
    archive_id = str(observation.get("archive_id") or "")
    if not isinstance(archive_id, str) or not archive_id.strip():
        raise PilotRunError("archive_id_required")
    package = _require_mapping(opportunity_package, "opportunity_package")
    projection = project_archive_snapshot(observation)
    relations = infer_archive_relations(projection)
    relation_report = evaluate_relation_payload(projection, relations)
    _require_valid(relation_report, "relations")
    units = reconstruct_archive_units(projection, relations)
    unit_report = evaluate_unit_payload(projection, relations, units)
    _require_valid(unit_report, "units")
    project_ir = adapt_archive_units_to_project_ir(projection, relations, units)
    project_ir_report = evaluate_project_ir_payload(projection, relations, units, project_ir)
    _require_valid(project_ir_report, "project_ir")
    project_ir_practice = project_ir
    if practice_receipt_evidence is not None:
        project_ir_practice = apply_practice_receipt_evidence_to_project_ir(
            project_ir, practice_receipt_evidence
        )
    practice = build_practice_evidence_state(project_ir_practice)
    practice_errors = validate_practice_evidence_state(practice)
    if practice_errors:
        raise PilotRunError("practice_invalid:" + stable_json(practice_errors))

    package_for_run = package
    if opportunity_validity_capture is not None:
        package_for_run = apply_opportunity_validity_capture(
            package, opportunity_validity_capture
        )
    opportunity = compile_opportunity_constraints(package_for_run)
    fit = evaluate_opportunity_fit(opportunity, practice)
    programs = generate_artistic_program_hypotheses(opportunity, practice, fit)
    program_evaluation = evaluate_artistic_program_payload(
        opportunity, practice, fit, programs
    )
    possibility = build_possibility_field(programs, program_evaluation)
    frontier = compile_research_frontier(possibility, fit, opportunity)
    empty_results = {
        "schema": "mak-research-result-batch-v1",
        "algorithm_version": "pilot-no-dispatch-1",
        "results": [],
    }
    triangulation = triangulate_research_evidence(frontier, empty_results)
    evidence_return = build_evidence_return(
        opportunity, practice, fit, frontier, triangulation
    )
    product_plan = compile_product_plan(
        opportunity,
        practice,
        fit,
        programs,
        possibility,
        frontier,
        evidence_return,
    )
    dossier = compile_portfolio_dossier(product_plan, practice, technical_context)
    application = compile_application_research_package(product_plan, opportunity)
    portfolio_view = project_product_view(product_plan, dossier, application)
    episode = compile_product_episode(product_plan, dossier, application)
    learning = evaluate_product_learning([episode])
    autonomy = compile_autonomy_plan(
        product_plan, dossier, application, evidence_return, learning
    )

    outputs = {
        "observation": observation,
        "projection": projection,
        "relations": relations,
        "relation-report": relation_report,
        "units": units,
        "unit-report": unit_report,
        "project-ir": project_ir,
        "project-ir-report": project_ir_report,
        "practice": practice,
        "opportunity": opportunity,
        "fit": fit,
        "programs": programs,
        "program-evaluation": program_evaluation,
        "possibility": possibility,
        "research-frontier": frontier,
        "triangulation": triangulation,
        "evidence-return": evidence_return,
        "product-plan": product_plan,
        "portfolio-dossier": dossier,
        "portfolio-view": portfolio_view,
        "application-research": application,
        "episode": episode,
        "learning": learning,
        "autonomy": autonomy,
    }
    if practice_receipt_evidence is not None:
        outputs["practice-receipt-evidence"] = practice_receipt_evidence
        outputs["project-ir-practice"] = project_ir_practice
    if opportunity_validity_capture is not None:
        outputs["opportunity-validity-capture"] = opportunity_validity_capture
    if technical_context is not None:
        outputs["technical-context"] = technical_context
    output_hashes = {name: sha256_json(value) for name, value in sorted(outputs.items())}
    semantic_input = {
        "archive_id": archive_id,
        "snapshot_id": observation.get("snapshot_id"),
        "opportunity_input_hash": opportunity.get("input_hash"),
        "algorithm_version": ALGORITHM_VERSION,
        "practice_receipt_evidence_hash": (
            sha256_json(practice_receipt_evidence)
            if practice_receipt_evidence is not None else None
        ),
        "opportunity_validity_capture_hash": (
            sha256_json(opportunity_validity_capture)
            if opportunity_validity_capture is not None else None
        ),
        "technical_context_hash": (
            sha256_json(technical_context)
            if technical_context is not None else None
        ),
    }
    manifest = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": "pilot:" + hashlib.sha256(
            stable_json(semantic_input).encode("utf-8")
        ).hexdigest(),
        "inputs": {
            **semantic_input,
            "archive_root": archive_root,
            "max_files": max_files,
            "source_rescan": source_rescan,
            "source_mutation": False,
        },
        "outputs": [
            {"name": name, "file": f"{name}.json", "sha256": output_hashes[name]}
            for name in sorted(outputs)
        ],
        "controls": {
            "database_writes": False,
            "network_calls": False,
            "research_dispatch": False,
            "publication": False,
            "submission": False,
            "training": False,
        },
        "summary": {
            "artifacts": len(observation.get("artifacts", [])),
            "observations": len(observation.get("observations", [])),
            "relation_candidates": len(relations.get("candidates", [])),
            "units": len(units.get("units", [])),
            "assigned": units.get("reconciliation", {}).get("assigned"),
            "unassigned": units.get("reconciliation", {}).get("unassigned"),
            "project_records": len(project_ir.get("records", [])),
            "practice_receipt_enriched": practice_receipt_evidence is not None,
            "opportunity_validity": opportunity.get("source", {}).get("validity"),
            "fit_decision": fit.get("decision"),
            "dossier_status": dossier.get("status"),
            "application_status": application.get("application_draft", {}).get("status"),
            "portfolio_view_technical_relations": len(
                portfolio_view.get("technical_evidence", [])
            ),
            "autonomy_actions": [
                row.get("action") for row in autonomy.get("prioritized_actions", [])
            ],
        },
    }
    return {"manifest": manifest, "outputs": outputs}


def build_pilot_outputs(
    archive_root: str,
    archive_id: str,
    opportunity_package: Mapping[str, Any],
    *,
    max_files: int | None = None,
    practice_receipt_evidence: Mapping[str, Any] | None = None,
    opportunity_validity_capture: Mapping[str, Any] | None = None,
    technical_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Observe once, then run the same replay path used by durable snapshots."""
    if not isinstance(archive_root, str) or not archive_root.strip():
        raise PilotRunError("archive_root_required")
    if not isinstance(archive_id, str) or not archive_id.strip():
        raise PilotRunError("archive_id_required")
    observer_kwargs: dict[str, Any] = {}
    if max_files is not None:
        if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
            raise PilotRunError("max_files_invalid")
        observer_kwargs["max_files"] = max_files
    observation = observe_archive(archive_root, archive_id, **observer_kwargs)
    return build_pilot_outputs_from_observation(
        observation,
        opportunity_package,
        source_rescan=True,
        archive_root=archive_root,
        max_files=max_files,
        practice_receipt_evidence=practice_receipt_evidence,
        opportunity_validity_capture=opportunity_validity_capture,
        technical_context=technical_context,
    )


def validate_pilot_run(result: Any) -> list[str]:
    """Validate an in-memory run result without repairing it."""
    errors: list[str] = []
    if not isinstance(result, Mapping):
        return ["result_not_object"]
    manifest = result.get("manifest")
    outputs = result.get("outputs")
    if not isinstance(manifest, Mapping) or not isinstance(outputs, Mapping):
        return ["manifest_or_outputs_missing"]
    if manifest.get("schema") != SCHEMA:
        errors.append("manifest_schema_invalid")
    if manifest.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append("algorithm_version_invalid")
    rows = manifest.get("outputs")
    if not isinstance(rows, list):
        errors.append("manifest_outputs_not_list")
        rows = []
    names = [row.get("name") for row in rows if isinstance(row, Mapping)]
    if names != sorted(outputs):
        errors.append("manifest_output_names_mismatch")
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("manifest_output_row_invalid")
            continue
        name = row.get("name")
        if name not in outputs or row.get("sha256") != sha256_json(outputs.get(name)):
            errors.append(f"output_hash_mismatch:{name}")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, Mapping):
        errors.append("manifest_inputs_not_object")
    else:
        technical_context = outputs.get("technical-context")
        declared_context_hash = inputs.get("technical_context_hash")
        if technical_context is None:
            if declared_context_hash is not None:
                errors.append("technical_context_hash_without_output")
        elif declared_context_hash != sha256_json(technical_context):
            errors.append("technical_context_hash_mismatch")
    controls = manifest.get("controls")
    if not isinstance(controls, Mapping) or any(controls.get(key) is not False for key in (
        "database_writes", "network_calls", "research_dispatch", "publication",
        "submission", "training",
    )):
        errors.append("controls_not_fail_closed")
    return sorted(set(errors))
