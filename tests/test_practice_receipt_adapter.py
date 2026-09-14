from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.practice_receipt_adapter import (
    PracticeReceiptAdapterError,
    adapt_practice_receipts,
    apply_practice_receipt_evidence_to_project_ir,
    validate_practice_receipt_evidence,
)
from flujo.knowledge.practice_evidence_state import build_practice_evidence_state


ROOT = Path(__file__).resolve().parents[1]


def _receipt(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _inputs() -> tuple[dict, dict, dict, dict]:
    c04 = _receipt("experiments/cycles/C04/real_evidence.json")
    c05 = _receipt("experiments/cycles/C05/real_export_witness.json")
    c06 = _receipt("experiments/cycles/C06/real_export_graph.json")
    bindings = {
        "schema": "mak-practice-receipt-bindings-v1",
        "archive_id": "archive-arica-001",
        "bindings": {
            "c04_aep": {
                "receipt_ref": "C02/aep_endpoint/observation.json#/input",
                "artifact_ref": "artifact-ref:arica-aep",
            },
            "c04_media": {
                "receipt_ref": "C04/media_observer/real-observation",
                "artifact_ref": "artifact-ref:tottem-ojo",
            },
            "c05_source": {
                "receipt_ref": "authoring:blend:ARICA/RAYU.blend",
                "artifact_ref": "artifact-ref:rayu-blend",
            },
            "c05_target": {
                "receipt_ref": "artifact:glb:rayu_resources.glb",
                "artifact_ref": "artifact-ref:rayu-glb",
            },
        },
    }
    return c04, c05, c06, bindings


def test_real_receipts_emit_bounded_technical_evidence() -> None:
    c04, c05, c06, bindings = _inputs()
    result = adapt_practice_receipts(c04, c05, c06, bindings)
    assert validate_practice_receipt_evidence(result) == []
    assert result["schema"] == "mak-practice-receipt-evidence-v1"
    assert result["policy"] == {
        "pure": True,
        "deterministic": True,
        "source_rescan": False,
        "filesystem_resolution": False,
        "basename_resolution": False,
        "hash_resolution": False,
        "similarity_resolution": False,
        "source_mutation": False,
    }
    roles = [row for row in result["predicates"] if row["predicate"] == "OUTPUT_ROLE"]
    assert roles == [{
        "predicate_id": "c04:output_role",
        "predicate": "OUTPUT_ROLE",
        "status": "unknown",
        "subject_ref": "artifact-ref:tottem-ojo",
        "evidence_refs": [],
        "source_receipts": ["mak-cycle-c04-real-evidence-v1"],
        "requirement_ids": [],
        "details": {"reason": "no_explicit_export_event_with_evidence_refs"},
    }]
    exports = [row for row in result["predicates"] if row["predicate"] == "EXPORTS_TO"]
    assert exports[0]["subject_ref"] == "artifact-ref:rayu-blend"
    assert exports[0]["object_ref"] == "artifact-ref:rayu-glb"
    assert "publication" in result["forbidden_inferences"]
    assert "artistic_authorship" in result["forbidden_inferences"]
    assert result["project_ir_practice_projection"]["manifestations"] == []


def test_is_deterministic_and_does_not_mutate_inputs() -> None:
    c04, c05, c06, bindings = _inputs()
    before = copy.deepcopy((c04, c05, c06, bindings))
    first = adapt_practice_receipts(c04, c05, c06, bindings)
    second = adapt_practice_receipts(c04, c05, c06, bindings)
    assert first == second
    assert (c04, c05, c06, bindings) == before


def test_projection_is_consumable_by_project_ir_practice_state() -> None:
    c04, c05, c06, bindings = _inputs()
    packet = adapt_practice_receipts(c04, c05, c06, bindings)
    projection = packet["project_ir_practice_projection"]
    artifacts = [
        {
            "artifact_id": ref,
            "artifact_ref": ref,
            "relative_path": f"explicit-binding/{index}.ref",
            "availability": "observed",
        }
        for index, ref in enumerate(projection["bound_artifact_refs"])
    ]
    record = {
        "schema": "mak-project-ir-v1",
        "project_id": "receipt-adapter-fixture",
        "title": "Technical receipt fixture",
        "state": "candidate",
        "source": {"kind": "explicit_receipt_binding", "root_ref": "receipt://C04-C06"},
        "purpose": "test technical evidence projection",
        "domains": ["archive"],
        "artifacts": artifacts,
        "relations": [],
        "evidence": [],
        "unknowns": [],
        "next_action": "preserve_bounded_claims",
        "provenance": {"producer": "test", "method": "explicit_binding"},
        "archive_id": "archive-arica-001",
        "snapshot_id": "snapshot-receipts",
        "input_hash": "sha256:receipt-fixture",
        "archive_unit": {
            "unit_id": "unit:receipt-adapter-fixture",
            "role": "technical_evidence",
            "status": "provisional_unit",
            "member_refs": projection["bound_artifact_refs"],
            "dependency_refs": [],
            "candidate_ids": [],
            "evidence_for": [],
            "evidence_against": [],
            "alternatives": [],
            "missing_evidence": [],
        },
    }
    bundle = {
        "schema": "mak-archive-project-ir-bundle-v1",
        "target_project_ir_schema": "mak-project-ir-v1",
        "records": [record],
    }
    enriched = apply_practice_receipt_evidence_to_project_ir(bundle, packet)
    assert enriched["practice_receipt_enrichment"]["records_touched"] == 1
    assert record["evidence"] == []
    state = build_practice_evidence_state(enriched)
    supported = {row["statement"] for row in state["claims"]["supported"]}
    unknown = {row["statement"] for row in state["claims"]["unknown"]}
    assert {"LOCAL_MEDIA_OBSERVED", "USES", "EXPORT_EVENT", "EXPORTS_TO"} <= supported
    assert "OUTPUT_ROLE" in unknown
    assert state["manifestations"] == []
    assert [row["value"] for row in state["media"]] == ["local_video_observed"]
    assert [row["value"] for row in state["resources"]] == ["glb_export_artifact_observed"]


def test_project_ir_enrichment_requires_every_exact_bound_ref() -> None:
    c04, c05, c06, bindings = _inputs()
    packet = adapt_practice_receipts(c04, c05, c06, bindings)
    bundle = {
        "schema": "mak-archive-project-ir-bundle-v1",
        "target_project_ir_schema": "mak-project-ir-v1",
        "records": [],
    }
    with pytest.raises(PracticeReceiptAdapterError, match="bound_artifact_owner_count"):
        apply_practice_receipt_evidence_to_project_ir(bundle, packet)


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda c04, c05, c06, bindings: c04["evaluation"]["claims"]["output_role"].update(status="supported"), "c04_output_role_not_unknown"),
        (lambda c04, c05, c06, bindings: c05["witness"]["checks"]["output_is_blender_glb"].update(status="fail"), "c05_check_failed:output_is_blender_glb"),
        (lambda c04, c05, c06, bindings: c06["edges"][0].update(target_ref="artifact:other"), "c05_c06_target_conflict"),
        (lambda c04, c05, c06, bindings: bindings["bindings"]["c05_target"].update(receipt_ref="rayu_resources.glb"), "binding_c05_target_receipt_ref_mismatch"),
        (lambda c04, c05, c06, bindings: bindings["bindings"]["c04_media"].pop("artifact_ref"), "binding_c04_media_artifact_ref_missing"),
    ],
)
def test_conflicts_and_implicit_bindings_fail_closed(mutator, error: str) -> None:
    c04, c05, c06, bindings = _inputs()
    mutator(c04, c05, c06, bindings)
    with pytest.raises(PracticeReceiptAdapterError, match=error):
        adapt_practice_receipts(c04, c05, c06, bindings)


def test_cli_reads_only_named_receipts_and_writes_requested_output(tmp_path: Path) -> None:
    _, _, _, bindings = _inputs()
    bindings_path = tmp_path / "bindings.json"
    output = tmp_path / "evidence.json"
    bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/adapt_practice_receipts.py",
            "--bindings", str(bindings_path),
            "--output", str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_hash"].startswith("sha256:")


def test_cli_returns_two_for_bad_binding(tmp_path: Path) -> None:
    _, _, _, bindings = _inputs()
    bindings["bindings"].pop("c04_aep")
    bindings_path = tmp_path / "bindings.json"
    bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "tools/adapt_practice_receipts.py", "--bindings", str(bindings_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "binding_c04_aep_missing" in result.stderr
