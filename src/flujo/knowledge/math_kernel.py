"""Metadata-only mathematical search ecology on top of MAK Project IR.

MAK remains the cultural/research orchestrator.  This module stores target
capsules, bounded search requests and verifier result cards in the same SQLite
ledger while keeping formulas, proof terms and counterexamples behind sealed
references.  It can schedule work continuously in bounded cycles, but it
never declares a theorem from absence of a counterexample or from an
untrusted formal target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._io_helpers import sha256_file as _sha256_file
from .project_ir import LearningStore, build_project_ir, format_family, media_type, stable_json


TARGET_SCHEMA = "mak-math-target-capsule-v1"
REQUEST_SCHEMA = "mak-math-search-request-v1"
CARD_SCHEMA = "mak-math-result-card-v1"
MATH_LEDGER_SCHEMA = "mak-math-ledger-v1"

CARD_STATUSES = {
    "UNKNOWN",
    "GENERATED",
    "LEGAL",
    "ILLEGAL",
    "KILLED",
    "SURVIVED",
    "COUNTEREXAMPLE_VERIFIED",
    "LEMMA_VERIFIED",
    "PROOF_VERIFIED",
    "FORMAL_TARGET_UNTRUSTED",
    "NEEDS_MATH_CURATOR",
}
POLICIES = {"SIMPLE", "GRAVEYARD", "ALIEN", "CURATOR"}
SEMANTIC_STATUSES = {"UNTRUSTED", "PARTIAL", "VERIFIED", "FAILED"}
FORBIDDEN_CARD_KEYS = {
    "formal_statement",
    "proof_term",
    "proof_script",
    "symbolic_expression",
    "counterexample_object",
    "source_math_text",
    "derivation_trace",
}


class MathKernelError(ValueError):
    """Invalid capsule, request, result card or ledger transition."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(stable_json(dict(value)).encode("utf-8")).hexdigest()


def _load(path: str | Path) -> dict[str, Any]:
    file = Path(path).expanduser()
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MathKernelError(f"json_unreadable: {file}") from exc
    if not isinstance(value, dict):
        raise MathKernelError(f"json_not_object: {file}")
    return value


def load_target(path: str | Path) -> dict[str, Any]:
    return _load(path)


def validate_target(target: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if target.get("schema") != TARGET_SCHEMA:
        errors.append("bad_schema")
    for key in ("target_id", "title", "problem_family", "problem_status", "layer", "official_statement_ref"):
        if not _text(target.get(key)):
            errors.append("missing_" + key)
    if target.get("layer") != "cultural_research_first":
        errors.append("bad_first_layer")
    semantic_status = _text(target.get("semantic_fidelity_status"))
    if semantic_status not in SEMANTIC_STATUSES:
        errors.append("bad_semantic_fidelity_status")
    manifest = target.get("semantic_manifest")
    if not isinstance(manifest, Mapping):
        errors.append("missing_semantic_manifest")
    else:
        for key in ("domain", "quantifiers", "asymptotic_model", "computational_model", "conclusion"):
            if not _text(manifest.get(key)):
                errors.append("semantic_manifest_missing_" + key)
        if not isinstance(manifest.get("assumptions"), list):
            errors.append("semantic_manifest_assumptions_not_list")
    frame = target.get("conceptual_frame")
    if not isinstance(frame, Mapping):
        errors.append("missing_conceptual_frame")
    else:
        for key in ("hypothesis_id", "statement", "epistemic_status"):
            if not _text(frame.get(key)):
                errors.append("conceptual_frame_missing_" + key)
        if frame.get("theorem_claim_excluded") is not True:
            errors.append("conceptual_theorem_claim_not_excluded")
    for key in ("known_barriers", "dead_routes", "search_policies"):
        if not isinstance(target.get(key), list):
            errors.append(key + "_not_list")
    policies = target.get("search_policies") if isinstance(target.get("search_policies"), list) else []
    for index, policy in enumerate(policies):
        if not isinstance(policy, Mapping) or _text(policy.get("policy_id")) not in POLICIES:
            errors.append(f"search_policy_{index}_bad")
    provenance = target.get("provenance")
    if not isinstance(provenance, Mapping) or not _text(provenance.get("producer")):
        errors.append("bad_provenance")
    elif not isinstance(provenance.get("source_refs"), list) or not provenance.get("source_refs"):
        errors.append("provenance_source_refs_missing")
    if semantic_status == "VERIFIED" and not _text(target.get("formal_target_hash")):
        errors.append("verified_target_missing_formal_hash")
    return errors


def validate_search_request(request: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if request.get("schema") != REQUEST_SCHEMA:
        errors.append("bad_schema")
    for key in ("request_id", "target_id", "policy", "visibility"):
        if not _text(request.get(key)):
            errors.append("missing_" + key)
    if request.get("policy") not in POLICIES:
        errors.append("bad_policy")
    if request.get("visibility") != "METADATA_ONLY":
        errors.append("bad_visibility")
    budget = request.get("budget")
    if not isinstance(budget, Mapping) or int(budget.get("compute_units") or 0) < 1:
        errors.append("bad_budget")
    constraints = request.get("constraints")
    if not isinstance(constraints, Mapping) or not isinstance(constraints.get("target_legality_required"), bool):
        errors.append("bad_constraints")
    return errors


def validate_result_card(card: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if card.get("schema") != CARD_SCHEMA:
        errors.append("bad_schema")
    for key in ("card_id", "target_id", "candidate_id", "validator", "candidate_hash", "target_hash", "failure_class"):
        if not _text(card.get(key)):
            errors.append("missing_" + key)
    status = _text(card.get("status"))
    if status not in CARD_STATUSES:
        errors.append("bad_status")
    if _text(card.get("semantic_fidelity")) not in SEMANTIC_STATUSES:
        errors.append("bad_semantic_fidelity")
    if not isinstance(card.get("next_actions"), list):
        errors.append("next_actions_not_list")
    if not isinstance(card.get("artifact_refs"), list) or not card.get("artifact_refs"):
        errors.append("artifact_refs_missing")
    if any(key in card for key in FORBIDDEN_CARD_KEYS):
        errors.append("sealed_math_payload_leaked")
    if status == "PROOF_VERIFIED":
        if _text(card.get("axiom_report")) not in {"CLEAN", "EXPECTED_AXIOMS"}:
            errors.append("proof_missing_clean_axiom_report")
        if not _text(card.get("certificate_ref")):
            errors.append("proof_missing_certificate_ref")
        if not _text(card.get("dependency_lock_hash")):
            errors.append("proof_missing_dependency_lock")
    return errors


def build_math_project(target: Mapping[str, Any], target_path: str | Path) -> dict[str, Any]:
    errors = validate_target(target)
    if errors:
        raise MathKernelError("invalid_target: " + ",".join(errors))
    path = Path(target_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    stat = path.stat()
    fidelity = _text(target.get("semantic_fidelity_status"))
    artifact = {
        "relative_path": str(path),
        "name": path.name,
        # Keep the capsule inside the common Project IR while giving the
        # router a typed format.  A generic JSON/data label would make a
        # source-memory project about P versus NP compete with this scheduler.
        "format_family": "math_target",
        "media_type": media_type(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": _sha256_file(path),
        "hash_status": "full",
        "availability": "present",
        "role": "math_target_capsule",
    }
    relations = [
        {"subject": target["target_id"], "relation": "lives_in", "object": "cultural_research_first_layer"},
        {"subject": target["target_id"], "relation": "feeds", "object": "search_ecology"},
        {"subject": target["target_id"], "relation": "requires", "object": "math_curator"},
    ]
    for item in target.get("cross_domain_relations", []):
        if isinstance(item, Mapping):
            relations.append({
                "subject": target["target_id"],
                "relation": item.get("relation", "cross_domain"),
                "object": item.get("domain", "unknown"),
                "meaning": item.get("meaning", ""),
            })
    evidence = [{
        "kind": "math_target_capsule",
        "status": "verified" if fidelity == "VERIFIED" else "observed",
        "semantic_fidelity": fidelity,
        "theorem_claim_excluded": target["conceptual_frame"]["theorem_claim_excluded"],
        "capsule_fingerprint": fingerprint(target),
    }]
    unknowns = [
        "The target's informal-to-formal semantic fidelity is not verified." if fidelity != "VERIFIED" else "",
        "No mathematical theorem is promoted by this capsule or scheduler.",
    ]
    unknowns = [item for item in unknowns if item]
    project = build_project_ir(
        project_id=str(target["target_id"]),
        title=str(target["title"]),
        source_root=path.parent,
        artifacts=[artifact],
        domains=["cultura", "curatoria", "portfolio", "research", "mathematics"],
        purpose="mathematical search target inside the cultural-research first layer",
        state="active" if fidelity == "VERIFIED" else "review_required",
        evidence=evidence,
        unknowns=unknowns,
        relations=relations,
        source_kind="math_target_capsule",
        source_ref=str(path),
    )
    project["layer"] = "cultural_research_first"
    project["math_target"] = dict(target)
    return project


def _ensure_math_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS math_target_capsules (
            target_id TEXT PRIMARY KEY,
            capsule_fingerprint TEXT NOT NULL,
            capsule_json TEXT NOT NULL,
            project_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS math_search_requests (
            request_id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            policy TEXT NOT NULL,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS math_result_cards (
            card_id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL,
            status TEXT NOT NULL,
            card_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_math_requests_target ON math_search_requests(target_id, status, created_at);
        CREATE INDEX IF NOT EXISTS idx_math_cards_target ON math_result_cards(target_id, status, created_at);
        """
    )


def save_target(database: str | Path, target_path: str | Path) -> dict[str, Any]:
    target = load_target(target_path)
    errors = validate_target(target)
    if errors:
        raise MathKernelError("invalid_target: " + ",".join(errors))
    project = build_math_project(target, target_path)
    store = LearningStore(database)
    store.save_project(project)
    encoded = stable_json(target)
    with store.connect() as con:
        _ensure_math_schema(con)
        con.execute(
            """INSERT INTO math_target_capsules(target_id,capsule_fingerprint,capsule_json,project_id,updated_at)
               VALUES(?,?,?,?,datetime('now'))
               ON CONFLICT(target_id) DO UPDATE SET capsule_fingerprint=excluded.capsule_fingerprint,
               capsule_json=excluded.capsule_json,project_id=excluded.project_id,updated_at=excluded.updated_at""",
            (str(target["target_id"]), fingerprint(target), encoded, project["project_id"]),
        )
    return {"target_id": project["project_id"], "project": project, "capsule_fingerprint": fingerprint(target)}


def _target_row(database: str | Path, target_id: str) -> dict[str, Any]:
    path = Path(database).expanduser()
    if not path.is_file():
        raise MathKernelError("math_database_missing")
    try:
        with sqlite3.connect("file:" + str(path.resolve()) + "?mode=ro", uri=True) as con:
            row = con.execute(
                "SELECT capsule_fingerprint,capsule_json FROM math_target_capsules WHERE target_id=?",
                (target_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise MathKernelError("math_ledger_unreadable") from exc
    if not row:
        raise MathKernelError("math_target_not_registered: " + target_id)
    return {"fingerprint": row[0], "capsule": json.loads(row[1])}


def queue_search_request(database: str | Path, request: Mapping[str, Any]) -> str:
    errors = validate_search_request(request)
    if errors:
        raise MathKernelError("invalid_search_request: " + ",".join(errors))
    target = _target_row(database, str(request["target_id"]))
    if not target:
        raise MathKernelError("math_target_missing")
    store = LearningStore(database)
    with store.connect() as con:
        _ensure_math_schema(con)
        con.execute(
            """INSERT INTO math_search_requests(request_id,target_id,policy,status,request_json,created_at)
               VALUES(?,?,?,?,?,datetime('now')) ON CONFLICT(request_id) DO NOTHING""",
            (request["request_id"], request["target_id"], request["policy"], "queued", stable_json(request)),
        )
    return str(request["request_id"])


def classify_result(target: Mapping[str, Any], card: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_result_card(card)
    if errors:
        raise MathKernelError("invalid_result_card: " + ",".join(errors))
    result = dict(card)
    target_fidelity = _text(target.get("semantic_fidelity_status"))
    if result["status"] == "PROOF_VERIFIED":
        if target_fidelity != "VERIFIED":
            result["status"] = "FORMAL_TARGET_UNTRUSTED"
            result["failure_class"] = "TARGET_SEMANTIC_UNTRUSTED"
            result["next_actions"] = ["ESCALATE_MATH_CURATOR", "AUDIT_SEMANTIC_FIDELITY"]
        elif result.get("axiom_report") not in {"CLEAN", "EXPECTED_AXIOMS"}:
            result["status"] = "NEEDS_MATH_CURATOR"
            result["failure_class"] = "AXIOM_REPORT_NOT_ACCEPTED"
            result["next_actions"] = ["ESCALATE_MATH_CURATOR", "REVIEW_AXIOM_REPORT"]
    if result["status"] == "SURVIVED":
        result["next_actions"] = list(dict.fromkeys([*result.get("next_actions", []), "ALLOCATE_BOUNDED_MUTATION"]))
        result["failure_class"] = result.get("failure_class") or "NO_COUNTEREXAMPLE_FOUND"
    result["scope"] = "metadata_verifier_result_only"
    result["semantic_fidelity"] = target_fidelity
    return result


def record_result_card(database: str | Path, card_path: str | Path) -> dict[str, Any]:
    card = _load(card_path)
    errors = validate_result_card(card)
    if errors:
        raise MathKernelError("invalid_result_card: " + ",".join(errors))
    target_row = _target_row(database, str(card["target_id"]))
    if str(card["target_hash"]) != str(target_row["fingerprint"]):
        raise MathKernelError("result_target_hash_mismatch")
    classified = classify_result(target_row["capsule"], card)
    encoded = stable_json(classified)
    store = LearningStore(database)
    with store.connect() as con:
        _ensure_math_schema(con)
        con.execute(
            """INSERT INTO math_result_cards(card_id,target_id,candidate_id,status,card_json,created_at)
               VALUES(?,?,?,?,?,datetime('now')) ON CONFLICT(card_id) DO UPDATE SET
               status=excluded.status,card_json=excluded.card_json""",
            (classified["card_id"], classified["target_id"], classified["candidate_id"], classified["status"], encoded),
        )
    return classified


def _next_policy(cards: Sequence[Mapping[str, Any]]) -> str:
    if not cards:
        return "SIMPLE"
    statuses = [str(card.get("status") or "") for card in cards]
    if "FORMAL_TARGET_UNTRUSTED" in statuses or "NEEDS_MATH_CURATOR" in statuses:
        return "CURATOR"
    if all(status in {"KILLED", "COUNTEREXAMPLE_VERIFIED"} for status in statuses):
        return "GRAVEYARD"
    if "SURVIVED" in statuses or "LEMMA_VERIFIED" in statuses:
        return "ALIEN"
    return "SIMPLE"


def run_cycle(database: str | Path, target_path: str | Path, *, iterations: int = 1, compute_units: int = 1, max_expanded_cost: float = 100.0) -> dict[str, Any]:
    if iterations < 1 or iterations > 100:
        raise MathKernelError("iterations_out_of_bounds")
    saved = save_target(database, target_path)
    target = saved["project"]["math_target"]
    target_id = str(target["target_id"])
    with sqlite3.connect("file:" + str(Path(database).expanduser().resolve()) + "?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("SELECT card_json FROM math_result_cards WHERE target_id=? ORDER BY created_at", (target_id,)).fetchall()
            request_count = con.execute("SELECT COUNT(*) FROM math_search_requests WHERE target_id=?", (target_id,)).fetchone()[0]
        except sqlite3.Error:
            rows, request_count = [], 0
    cards = [json.loads(row["card_json"]) for row in rows]
    requests: list[dict[str, Any]] = []
    for index in range(iterations):
        policy = _next_policy(cards)
        request_number = int(request_count) + index
        request_id = "request-" + hashlib.sha256(f"{target_id}:{request_number}:{policy}".encode()).hexdigest()[:24]
        fidelity = _text(target.get("semantic_fidelity_status"))
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": request_id,
            "target_id": target_id,
            "policy": policy,
            "budget": {"compute_units": int(compute_units), "max_expanded_cost": float(max_expanded_cost)},
            "constraints": {
                "target_legality_required": True,
                "literature_mode": "CURATOR_ONLY" if fidelity != "VERIFIED" else "NO_TARGET_SPECIFIC",
            },
            "visibility": "METADATA_ONLY",
            "next_gate": "semantic_target_curator_before_truth_promotion" if fidelity != "VERIFIED" else "submit_candidate_to_math_worker",
        }
        queue_search_request(database, request)
        requests.append(request)
    return {
        "schema": MATH_LEDGER_SCHEMA,
        "target_id": target_id,
        "target_fidelity": target.get("semantic_fidelity_status"),
        "requests": requests,
        "frontier_size": len(cards),
        "truth_promotion": "blocked_until_semantic_fidelity_and_trusted_verifier",
    }


def math_summary(database: str | Path, target_id: str | None = None) -> dict[str, Any]:
    path = Path(database).expanduser()
    if not path.is_file():
        return {"schema": MATH_LEDGER_SCHEMA, "available": False, "reason": "database_missing"}
    try:
        with sqlite3.connect("file:" + str(path.resolve()) + "?mode=ro", uri=True) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='math_target_capsules'").fetchone()
            if not exists:
                return {"schema": MATH_LEDGER_SCHEMA, "available": False, "reason": "math_ledger_not_initialized"}
            target_filter = " WHERE target_id=?" if target_id else ""
            args = (target_id,) if target_id else ()
            target_count = con.execute("SELECT COUNT(*) FROM math_target_capsules" + target_filter, args).fetchone()[0]
            request_rows = con.execute("SELECT status,COUNT(*) FROM math_search_requests" + target_filter + " GROUP BY status", args).fetchall()
            card_rows = con.execute("SELECT status,COUNT(*) FROM math_result_cards" + target_filter + " GROUP BY status", args).fetchall()
        return {
            "schema": MATH_LEDGER_SCHEMA,
            "available": True,
            "target_count": target_count,
            "requests": {str(row[0]): int(row[1]) for row in request_rows},
            "cards": {str(row[0]): int(row[1]) for row in card_rows},
            "truth_promotion": "blocked_until_semantic_fidelity_and_trusted_verifier",
        }
    except sqlite3.Error as exc:
        return {"schema": MATH_LEDGER_SCHEMA, "available": False, "reason": type(exc).__name__}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "cycle", "submit-card", "summary"))
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--card", type=Path)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--compute-units", type=int, default=1)
    parser.add_argument("--max-expanded-cost", type=float, default=100.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "validate":
            if not args.target:
                raise MathKernelError("validate_requires_target")
            target = load_target(args.target)
            errors = validate_target(target)
            output = {"schema": TARGET_SCHEMA, "target_id": target.get("target_id", ""), "status": "passed" if not errors else "failed", "errors": errors}
        elif args.command == "cycle":
            if not args.target or not args.db:
                raise MathKernelError("cycle_requires_target_and_db")
            output = run_cycle(args.db, args.target, iterations=args.iterations, compute_units=args.compute_units, max_expanded_cost=args.max_expanded_cost)
        elif args.command == "submit-card":
            if not args.card or not args.db:
                raise MathKernelError("submit_card_requires_card_and_db")
            output = record_result_card(args.db, args.card)
        else:
            if not args.db:
                raise MathKernelError("summary_requires_db")
            output = math_summary(args.db)
    except (OSError, MathKernelError, ValueError) as exc:
        print(json.dumps({"schema": MATH_LEDGER_SCHEMA, "status": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if output.get("status", "passed") not in {"failed", "error"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
