from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.flujo.knowledge.opportunity_constraints import INPUT_SCHEMA, compile_opportunity_constraints
from src.flujo.knowledge.opportunity_delta import compare_opportunity_constraints
from src.flujo.knowledge.selective_recompute_receipt import (
    SCHEMA,
    SelectiveRecomputeReceiptError,
    build_selective_recompute_receipt,
    stable_json,
    validate_selective_recompute_receipt,
)


def _package(*, content: str = "v1", extra: bool = False) -> dict:
    requirements = [{"id": "gate:field", "kind": "hard_gate", "field": "field_required", "evidence_refs": ["p2"]}]
    evidence = [{"evidence_id": "p2", "kind": "hard_gate", "field": "field_required", "value": True, "locator": {"page": 2}}]
    if extra:
        requirements.append({"id": "document:advance", "kind": "required_document", "field": "advance", "evidence_refs": ["p27"]})
        evidence.append({"evidence_id": "p27", "kind": "required_document", "field": "advance", "value": {"pages": 2}, "locator": {"page": 27}})
    return {
        "schema": INPUT_SCHEMA,
        "opportunity_id": "opportunity:fixture",
        "title": "Opportunity fixture",
        "source": {"ref": "fixture.pdf", "url": "https://example.test/bases.pdf", "content": content, "version": "v1", "validity": {"status": "observed_local", "confirmed": False}},
        "requirements": requirements,
        "evidence": evidence,
    }


def _constraints(*, extra: bool = False, content: str = "v1") -> dict:
    return compile_opportunity_constraints(_package(extra=extra, content=content))


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _outputs(seed: str, *, changed: str | None = None) -> dict[str, str]:
    names = ["fit", "programs", "possibility", "research-frontier", "product-plan", "portfolio-dossier", "application-research", "episode", "autonomy", "opportunity"]
    return {name: _digest((changed if changed == name else seed)[0]) for name in names}


def test_receipt_is_causally_bounded_when_all_declared_consumers_are_observed() -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    delta = compare_opportunity_constraints(previous, current)
    receipt = build_selective_recompute_receipt(previous, current, delta, _outputs("a"), _outputs("a", changed="fit"))
    assert receipt["schema"] == SCHEMA
    assert receipt["status"] == "causally_bounded"
    assert receipt["changed_affected_consumers"] == ["opportunity_fit"]
    assert receipt["unexplained_outputs"] == []
    assert receipt["controls"]["execution_performed"] is False
    assert validate_selective_recompute_receipt(previous, current, delta, receipt) is True


def test_mixed_inputs_are_reported_not_falsely_attributed() -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    delta = compare_opportunity_constraints(previous, current)
    after = _outputs("a", changed="fit")
    after["triangulation"] = _digest("b")
    receipt = build_selective_recompute_receipt(previous, current, delta, _outputs("a"), after)
    assert receipt["status"] == "mixed_or_unexplained"
    assert receipt["unexplained_outputs"] == ["triangulation"]


def test_provenance_only_delta_requires_no_recompute() -> None:
    previous = _constraints(content="v1")
    current = _constraints(content="v2")
    delta = compare_opportunity_constraints(previous, current)
    outputs = _outputs("a")
    receipt = build_selective_recompute_receipt(previous, current, delta, outputs, outputs)
    assert receipt["status"] == "no_recompute_expected"
    assert receipt["changed_outputs"] == []


def test_tampering_and_invalid_hashes_fail_closed() -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    delta = compare_opportunity_constraints(previous, current)
    receipt = build_selective_recompute_receipt(previous, current, delta, _outputs("a"), _outputs("a", changed="fit"))
    tampered = copy.deepcopy(receipt)
    tampered["status"] = "causally_bounded"
    tampered["unexplained_outputs"] = ["fake"]
    assert validate_selective_recompute_receipt(previous, current, delta, tampered) is False
    with pytest.raises(SelectiveRecomputeReceiptError):
        build_selective_recompute_receipt(previous, current, delta, {"fit": "bad"}, _outputs("a"))


def test_real_arica_manifests_expose_mixed_direct_enrichments() -> None:
    root = Path(__file__).parents[1] / "experiments/pilots/ARICA-FONDART-2027/runs"
    # experiments/pilots/ is gitignored on purpose: it holds real pilot
    # evidence. On MAK it is present, in a clean checkout it is not, and
    # reading it unguarded is why CI went red while this suite stayed green.
    if not (root / "full-baseline/opportunity.json").is_file():
        pytest.skip("experiments/pilots/ARICA-FONDART-2027 is not in this clone")
    previous = json.loads((root / "full-baseline/opportunity.json").read_text(encoding="utf-8"))
    current = json.loads((root / "enriched/opportunity.json").read_text(encoding="utf-8"))
    delta = compare_opportunity_constraints(previous, current)
    before_manifest = json.loads((root / "full-baseline/manifest.json").read_text(encoding="utf-8"))
    after_manifest = json.loads((root / "enriched/manifest.json").read_text(encoding="utf-8"))
    before = {row["name"]: row["sha256"] for row in before_manifest["outputs"]}
    after = {row["name"]: row["sha256"] for row in after_manifest["outputs"]}
    receipt = build_selective_recompute_receipt(previous, current, delta, before, after)
    assert receipt["status"] == "mixed_or_unexplained"
    assert receipt["reconciliation"]["changed_output_count"] == 17
    assert "practice" in receipt["unexplained_outputs"]


def test_cli_is_deterministic(tmp_path: Path) -> None:
    previous = _constraints()
    current = _constraints(extra=True)
    delta = compare_opportunity_constraints(previous, current)
    paths = {}
    for name, value in (("previous", previous), ("current", current), ("delta", delta)):
        path = tmp_path / f"{name}.json"
        path.write_text(stable_json(value), encoding="utf-8")
        paths[name] = path
    for name, value in (("before", _outputs("a")), ("after", _outputs("a", changed="fit"))):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"outputs": [{"name": key, "sha256": value[key]} for key in sorted(value)]}), encoding="utf-8")
        paths[name] = path
    command = [sys.executable, "tools/compile_selective_recompute_receipt.py", "--previous-constraints", str(paths["previous"]), "--current-constraints", str(paths["current"]), "--delta", str(paths["delta"]), "--before-manifest", str(paths["before"]), "--after-manifest", str(paths["after"])]
    first = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    second = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
