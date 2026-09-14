#!/usr/bin/env python3
"""Build and review the bounded real ARICA-01 portfolio evidence slice."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARICA = Path("/home/mak/curatoria_inbox/ARICA")
DB = ROOT / "data" / "mak_knowledge.db"
OUTPUT = ROOT / "experiments" / "cycles" / "ARICA-01"
PROJECT_ID = "arica-01-portfolio-evidence"

INPUTS = (
    "RAYU.blend",
    "rayu_export.py",
    "rayu_export_done.txt",
    "rayu_resources.glb",
    "ARICA.aep",
    "tottem_ojo.mp4",
    "MYRA/MYRA_final.mp4",
    "MYRA/estado.json",
    "MYRA/mapping_guide.txt",
    "MYRA/log_maestro.txt",
    "MYRA/bridge/render_done.txt",
    "MYRA/bridge/voidrender_1783145672.txt",
    "MYRA/render_20s/f_0000.png",
    "MYRA/render_20s/f_0599.png",
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot(paths: list[Path], evidence_paths: list[Path]) -> tuple[str, list[dict[str, Any]]]:
    rows = []
    for path in [*paths, *evidence_paths]:
        stat = path.stat()
        rows.append({
            "path": str(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": _sha256(path),
        })
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), rows


def _build() -> dict[str, Any]:
    paths = [(ARICA / relative).resolve() for relative in INPUTS]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing_arica_inputs:" + ",".join(missing))
    c07 = _load_module("mak_arica01_c07", ROOT / "experiments/cycles/C07/practice_graph.py")
    c06 = _load_module("mak_arica01_c06", ROOT / "experiments/cycles/C06/export_graph_bridge.py")
    graph = c07.build_graph(paths, root=ARICA)
    witness_path = ROOT / "experiments/cycles/C05/real_export_witness.json"
    c06_graph_path = ROOT / "experiments/cycles/C06/real_export_graph.json"
    c04_path = ROOT / "experiments/cycles/C04/real_evidence.json"
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    c06_graph = c06.materialize(witness)
    c04 = json.loads(c04_path.read_text(encoding="utf-8"))
    snapshot_hash, snapshot_rows = _snapshot(paths, [witness_path, c06_graph_path, c04_path])

    candidates = list(graph["relation_candidates"])
    export_edge = c06_graph["edges"][0] if c06_graph.get("edges") else None
    if export_edge:
        candidates.append({
            "id": "candidate:export_witness:authoring:blend:ARICA/RAYU.blend->artifact:glb:rayu_resources.glb",
            "source_id": "authoring:blend:ARICA/RAYU.blend",
            "target_id": "artifact:glb:rayu_resources.glb",
            "relation": "EXPORTS_TO",
            "status": "supported",
            "score": 1.0,
            "evidence_refs": export_edge["evidence_refs"],
            "missing_evidence": ["final_delivery_or_publication_record"],
            "next_probe": "review whether this exported GLB belongs in the portfolio",
            "claim_limit": export_edge["claim_limit"],
        })
    uses_claim = c04["evaluation"]["claims"]["uses"]
    candidates.append({
        "id": "candidate:uses:artifact:ARICA.aep->artifact:tottem_ojo.mp4",
        "source_id": "artifact:ARICA.aep",
        "target_id": "artifact:tottem_ojo.mp4",
        "relation": "uses",
        "status": uses_claim["status"],
        "score": 0.86,
        "evidence_refs": uses_claim["evidence_refs"],
        "missing_evidence": ["explicit_export_event"],
        "next_probe": "inspect an export log or composition delivery record",
        "claim_limit": c04["limits"]["claim_limit"],
    })
    candidates.append({
        "id": "candidate:version_of:artifact:MYRA/MYRA_final.mp4->missing_source",
        "source_id": "artifact:MYRA/MYRA_final.mp4",
        "target_id": None,
        "relation": "version_of",
        "status": "unresolved_candidate",
        "score": 0.18,
        "evidence_refs": [
            "ARICA/MYRA/MYRA_final.mp4#sha256",
            "ARICA/MYRA/bridge/render_done.txt#observed",
        ],
        "missing_evidence": ["authoring_project_or_export_manifest"],
        "next_probe": "locate the native project, export manifest, or public publication record",
        "claim_limit": "MYRA_final.mp4 is an observed output; source binding remains unknown",
    })
    evidence = [
        {"kind": "c07_observation", "status": "observed", "schema": graph["schema"], "summary": graph["summary"]},
        {"kind": "c05_export_witness", "status": witness["witness"]["status"], "source_ref": str(witness_path), "evidence_refs": witness["witness"]["evidence_refs"]},
        {"kind": "c06_export_graph", "status": c06_graph["claim"]["status"], "source_ref": str(c06_graph_path), "evidence_refs": c06_graph["claim"]["evidence_refs"]},
        {"kind": "c04_aep_media_evaluation", "status": c04["status"], "source_ref": str(c04_path), "claim": c04["evaluation"]["claims"]},
    ]
    unknowns = [
        "MYRA_final.mp4 source_binding=unknown",
        "ARICA.aep/tottem_ojo.mp4 output_role=unknown",
        "public_manifestation_catalog=unavailable",
    ]
    from flujo.knowledge.portfolio_evidence import build_project_record
    record = build_project_record(
        project_id=PROJECT_ID,
        title="ARICA-01 real artist archive evidence slice",
        source_root=ARICA,
        observed_artifacts=graph["artifacts"],
        relation_candidates=candidates,
        evidence=evidence,
        unknowns=unknowns,
        source_snapshot_hash=snapshot_hash,
        graph_observation=graph,
    )
    from flujo.knowledge.project_ir import LearningStore
    LearningStore(DB).save_project(record)
    return {"record": record, "snapshot_rows": snapshot_rows, "witness": witness, "c06_graph": c06_graph}


def _write_outputs(record: dict[str, Any], snapshot_rows: list[dict[str, Any]]) -> None:
    from flujo.knowledge.portfolio_evidence import build_draft, queue_payload
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "input_snapshot.json").write_text(json.dumps({
        "schema": "mak-arica01-input-snapshot-v1", "project_id": PROJECT_ID,
        "source_root": str(ARICA), "source_snapshot_hash": record.get("source_snapshot_hash"),
        "inputs": snapshot_rows,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "relation_queue.json").write_text(json.dumps(queue_payload(record), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "portfolio_draft.json").write_text(json.dumps(build_draft(record), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="observe the explicit ARICA-01 inputs and persist one Project IR record")
    parser.add_argument("--queue", action="store_true", help="print the persisted human relation queue")
    parser.add_argument("--draft", action="store_true", help="print the current derived portfolio draft")
    parser.add_argument("--candidate-id")
    parser.add_argument("--action", choices=("accept", "reject", "correct", "request_evidence"))
    parser.add_argument("--actor", default="human", help="provenance actor for a persisted review")
    parser.add_argument("--note", default="")
    parser.add_argument("--corrected-relation", default="")
    parser.add_argument("--corrected-target-id", default="")
    args = parser.parse_args(argv)
    from flujo.knowledge.portfolio_evidence import apply_human_decision, build_draft, load_record, queue_payload
    if args.build:
        built = _build()
        _write_outputs(built["record"], built["snapshot_rows"])
        print(json.dumps({"ok": True, "operation": "build", "project_id": PROJECT_ID, "artifacts": len(built["record"]["artifacts"]), "candidates": len(built["record"]["relations"]), "source_snapshot_hash": built["record"]["source_snapshot_hash"]}, ensure_ascii=False, sort_keys=True))
        return 0
    record = load_record(DB, PROJECT_ID)
    if args.candidate_id or args.action:
        if not args.candidate_id or not args.action:
            parser.error("--candidate-id and --action are required together")
        result = apply_human_decision(DB, project_id=PROJECT_ID, candidate_id=args.candidate_id, action=args.action, actor=args.actor, note=args.note, corrected_relation=args.corrected_relation, corrected_target_id=args.corrected_target_id, source_snapshot_hash=record.get("source_snapshot_hash", ""))
        _write_outputs(load_record(DB, PROJECT_ID), json.loads((OUTPUT / "input_snapshot.json").read_text(encoding="utf-8"))["inputs"])
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.draft:
        print(json.dumps(build_draft(record), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps(queue_payload(record), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
