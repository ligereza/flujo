"""Bounded deterministic simulation for explicit cultural research grammars.

This consumer implements the ``simulate`` step as a symbolic L-system
projection.  It never infers rules from prose, never calls a model or an
external service, and labels every trajectory as simulated rather than
observed biological reality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


MANIFEST_SCHEMA = "mak-research-simulation-manifest-v1"
RESULT_SCHEMA = "mak-research-simulation-result-v1"
MAX_ITERATIONS = 12
DEFAULT_MAX_SYMBOLS = 10000


def _text(value: Any) -> str:
    return str(value or "").strip()


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("bad_schema")
    for key in ("simulation_id", "project_id", "domain", "axiom"):
        if not _text(manifest.get(key)):
            errors.append("missing_" + key)
    try:
        iterations = int(manifest.get("iterations"))
    except (TypeError, ValueError):
        iterations = -1
    if iterations < 0 or iterations > MAX_ITERATIONS:
        errors.append("iterations_out_of_bounds")
    rules = manifest.get("rules")
    if not isinstance(rules, Mapping) or not rules:
        errors.append("missing_rules")
    else:
        for symbol, replacement in rules.items():
            if not isinstance(symbol, str) or len(symbol) != 1:
                errors.append("rule_symbol_not_single_character")
            if not isinstance(replacement, str):
                errors.append("rule_replacement_not_string")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        errors.append("missing_provenance")
    elif not isinstance(provenance.get("evidence_refs"), list) or not provenance.get("evidence_refs"):
        errors.append("missing_evidence_refs")
    if _text(manifest.get("claim_scope")).casefold() not in {"visual_grammar", "symbolic_projection"}:
        errors.append("claim_scope_not_bounded")
    try:
        max_symbols = int(manifest.get("max_symbols", DEFAULT_MAX_SYMBOLS))
    except (TypeError, ValueError):
        max_symbols = 0
    if max_symbols < 1 or max_symbols > 100000:
        errors.append("max_symbols_out_of_bounds")
    return errors


def simulate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest)
    if errors:
        return {
            "schema": RESULT_SCHEMA,
            "simulation_id": _text(manifest.get("simulation_id")),
            "project_id": _text(manifest.get("project_id")),
            "decision": "abstain",
            "errors": errors,
            "model_not_reality": True,
            "observed_or_simulated": "simulated",
        }
    state = _text(manifest["axiom"])
    rules = {str(key): str(value) for key, value in dict(manifest["rules"]).items()}
    iterations = int(manifest["iterations"])
    max_symbols = int(manifest.get("max_symbols", DEFAULT_MAX_SYMBOLS))
    trajectory = [{"iteration": 0, "state": state, "symbol_count": len(state)}]
    if len(state) > max_symbols:
        errors = ["symbol_budget_exceeded"]
    else:
        errors = []
        for iteration in range(1, iterations + 1):
            state = "".join(rules.get(symbol, symbol) for symbol in state)
            if len(state) > max_symbols:
                errors.append("symbol_budget_exceeded")
                break
            trajectory.append({"iteration": iteration, "state": state, "symbol_count": len(state)})
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "simulation_id": _text(manifest["simulation_id"]),
        "project_id": _text(manifest["project_id"]),
        "decision": "simulated" if not errors else "abstain",
        "errors": errors,
        "observed_or_simulated": "simulated",
        "model_not_reality": True,
        "claim_scope": _text(manifest["claim_scope"]),
        "trajectory": trajectory,
        "environment": dict(manifest.get("environment") or {}),
        "provenance": {
            "evidence_refs": list(manifest["provenance"]["evidence_refs"]),
            "transform": "bounded_symbol_rewrite_v1",
            "rules_declared_by_input": True,
        },
    }
    return result


def load_and_simulate(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("manifest_not_object")
    return simulate_manifest(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = load_and_simulate(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": RESULT_SCHEMA, "decision": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.expanduser().write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if result["decision"] == "simulated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
