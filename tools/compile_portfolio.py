#!/usr/bin/env python3
"""Compile the claim base and render every declared portfolio format."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.portfolio_claims import (  # noqa: E402
    compile_portfolio_claims,
    validate_portfolio_claims,
)
from flujo.knowledge.portfolio_format import load_format_library  # noqa: E402
from flujo.knowledge.human_decision_log import (  # noqa: E402
    consumer_decision_summary,
    curatorial_relations,
    read_human_decisions,
)
from flujo.knowledge.portfolio_render import (  # noqa: E402
    build_portfolio_episode,
    render_markdown,
    render_portfolio,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--authority", type=Path, default=ROOT / "data" / "artist_discographies.json")
    parser.add_argument("--archive", type=Path, default=ROOT / "iskvw" / "datos" / "archivo.json")
    parser.add_argument("--declared-inputs", type=Path, default=None)
    parser.add_argument("--blend-targets", type=Path, default=None)
    parser.add_argument("--practices", type=Path, default=ROOT / "data" / "portfolio_practices.json")
    parser.add_argument("--attestations", type=Path, default=ROOT / "data" / "portfolio_attestations.json")
    parser.add_argument("--screen-setup-root", type=Path, default=None)
    parser.add_argument("--formats", type=Path, default=ROOT / "data" / "portfolio_formats")
    parser.add_argument("--selections", type=Path, default=None)
    parser.add_argument("--classifications", type=Path, default=None)
    parser.add_argument("--connections", type=Path, default=None)
    parser.add_argument("--feedback", type=Path, default=None)
    parser.add_argument("--external-proposals", type=Path, default=None)
    parser.add_argument("--project-id", default="mak-portfolio-production-20260828")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "portfolio")
    parser.add_argument("--mak", action="store_true",
                        help="fill every optional input from MAK's canonical evidence paths")
    args = parser.parse_args(argv)

    decision = None
    relations: list = []
    log = None
    # MAK's evidence lives outside the repo, so seven of these default to None
    # and the compiler runs happily degraded: it renders fewer formats from a
    # smaller claim base and says nothing about it. Measured 2026-08-29 on this
    # machine: without them, 256 claims and F7-lectura-curatorial infeasible;
    # with them, 287 claims and F7 rendered with 13 items. Absence read as
    # health, which is the same defect `flujo doctor` had with `_airdrop/`.
    #
    # `--mak` fills them from the paths that docs/PORTAFOLIO_PRODUCCION.md
    # declares, and only when they actually exist. The default stays untouched
    # so no caller changes behaviour without asking for it.
    MAK_EVIDENCE = Path("/home/mak/plataforma/director_runs/portfolio-editor-20260808")
    if args.mak:
        for attr, candidate in (
            ("selections", MAK_EVIDENCE / "selections.jsonl"),
            ("classifications", MAK_EVIDENCE / "classifications.jsonl"),
            ("connections", MAK_EVIDENCE / "connections.jsonl"),
            ("feedback", MAK_EVIDENCE / "copilot_feedback.jsonl"),
            ("external_proposals", MAK_EVIDENCE / "copilot_external.jsonl"),
            ("declared_inputs", ROOT / "data" / "ssd_evidence" / "declared_inputs.json"),
            ("blend_targets", ROOT / "data" / "ssd_evidence" / "blend_dependency_targets.json"),
            ("screen_setup_root", Path("/media/mak/PortableSSD")),
        ):
            if getattr(args, attr) is None and candidate.exists():
                setattr(args, attr, candidate)

    # Whatever the caller asked for, say out loud what is missing. A compiler
    # that degrades in silence teaches the reader that the smaller result is
    # the whole result.
    absent = [name for name, value in (
        ("decisiones humanas: selections", args.selections),
        ("decisiones humanas: classifications", args.classifications),
        ("decisiones humanas: connections", args.connections),
        ("decisiones humanas: feedback", args.feedback),
        ("propuestas externas", args.external_proposals),
        ("ScreenSetups de Resolume", args.screen_setup_root),
        ("insumos declarados del SSD", args.declared_inputs),
        ("objetivos de dependencia .blend", args.blend_targets),
    ) if value is None or not Path(value).exists()]
    if absent:
        print("AVISO: se compila SIN esta evidencia, el resultado sera menor:",
              file=sys.stderr)
        for name in absent:
            print(f"  falta  {name}", file=sys.stderr)
        print("  para la corrida completa en MAK: --mak", file=sys.stderr)

    if any((args.selections, args.classifications, args.connections,
            args.feedback, args.external_proposals)):
        log = read_human_decisions(
            selections_path=args.selections,
            classifications_path=args.classifications,
            connections_path=args.connections,
            feedback_path=args.feedback,
            external_path=args.external_proposals)
        decision = consumer_decision_summary(log)
        relations = curatorial_relations(log)

    claims = compile_portfolio_claims(
        index_path=args.index,
        authority_path=args.authority,
        archive_path=args.archive,
        declared_inputs_path=args.declared_inputs,
        blend_targets_path=args.blend_targets,
        practices_path=args.practices,
        attestations_path=args.attestations,
        screen_setup_root=args.screen_setup_root,
        human_relations=relations,
    )
    validate_portfolio_claims(claims)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "claims.json").write_text(
        json.dumps(claims, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    summary = []
    for spec in load_format_library(args.formats)["formats"]:
        payload = render_portfolio(spec, claims)
        stem = spec["format_id"]
        (args.out / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (args.out / f"{stem}.md").write_text(render_markdown(payload), encoding="utf-8")
        document = payload.get("document")
        summary.append({
            "format_id": stem,
            "status": payload["status"],
            "item_count": document["item_count"] if document else 0,
            "section_count": len(document["sections"]) if document else 0,
            "render_hash": payload.get("render_hash"),
            "blocking": [row["slot_id"] for row in payload["feasibility"]["blocking"]],
        })
    if log is not None:
        (args.out / "human_decisions.json").write_text(
            json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    episode = build_portfolio_episode(
        [render_portfolio(spec, claims)
         for spec in load_format_library(args.formats)["formats"]],
        claims, project_id=args.project_id, consumer_decision=decision)
    (args.out / "episode.json").write_text(
        json.dumps(episode, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(json.dumps({
        "claims_hash": claims["claims_hash"],
        "episode_id": episode["episode_id"],
        "consumer_decision": episode["consumer_decision"].get("status"),
        "human_relation_count": claims.get("human_relation_count"),
        "human_relation_states": claims.get("human_relation_states"),
        "baseline_selection_rate": episode["observed_outcome"].get("selection_rate"),
        "claim_count": claims["claim_count"],
        "claims_by_state": claims["claims_by_state"],
        "practice_kind_counts": claims["practice_kind_counts"],
        "formats": summary,
        "out": str(args.out),
    }, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
