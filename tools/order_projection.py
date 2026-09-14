#!/usr/bin/env python3
"""Project certified identity into an order the operator can act on.

ORDER IS A PROJECTION, NOT A MOVE

Nothing here touches a file. The question is never "where should this file live"
but "what has to stay true after it moves", so every proposal carries the check
that would invalidate it.

WHAT THIS BUYS, AND FOR WHOM

Two consumers that already exist had both stopped at the same missing fact and
both said so in their own words.

``project_reconstruction.cross_root_relations``:

    a sample is not an identity ... Therefore a shared sample hash never decides
    project identity here; it produces an explicit tie
    tie_breaker_needed: compute full_sha256 for the overlapping assets

``show_asset_usage`` (in its ``limites``):

    full_sha256 existe para 112 de 45536 assets del indice, asi que la
    verificacion por contenido no esta disponible para el 99,75 %

The tie-breaker now exists for the assets that were in dispute: 1348 groups,
4104 assets, 1347 groups resolved. This tool hands it to both.

THE THREE TIERS, AND WHY ONLY ONE IS SAFE

    T1  a copy loose at the top of the disk while the same bytes sit inside a
        folder. No decision needed: which of the two is the stray is a fact
        about the filesystem.
    T2  the same bytes under two container roots. Identical bytes have two
        readings -- one work filed twice, or an output reused in a second
        commission -- and content cannot choose. Operator question.
    T3  duplication inside one project. Left alone. A render pipeline may
        legitimately need a copy in two places, and this tool has no evidence
        about which.

Even T1 is only a proposal, and only after the dependency check below.

THE DEPENDENCY CHECK

A Resolume composition names its clips by path. If a candidate for removal is
named by a composition, removing it breaks a show that has already been played.
So every T1 proposal is tested against the ``.usage.json`` records produced by
``show_asset_usage``, and a hit downgrades the proposal to HOLD with the reason
attached. The check is by basename because that is the only key those
compositions offer -- which means it can produce a false HOLD but never a false
SAFE, and that is the direction the asymmetry has to point.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo import runrecord                                          # noqa: E402
from flujo.knowledge import certified_identity as ci                 # noqa: E402

CONTRACT = "mak-order-projection-v1"
DEFAULT_INDEX = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")

SAFE = "SAFE_TO_DEDUPLICATE"
HOLD = "HOLD_A_SHOW_DEPENDS_ON_IT"
HOLD_BLEND = "HOLD_A_BLEND_DECLARES_IT"


def load_show_dependencies(usage_dir: Path) -> dict[str, list[str]]:
    """Basenames a Resolume composition names, and which composition names them."""
    depended: dict[str, list[str]] = defaultdict(list)
    if not usage_dir.is_dir():
        return depended
    for record in sorted(usage_dir.rglob("*.usage.json")):
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        show = (payload.get("composicion") or {}).get("composition_name") or record.stem
        for reference in payload.get("referencias") or []:
            cited = reference.get("archivo_citado") or ""
            basename = re.split(r"[\\/]", cited)[-1]
            if basename:
                depended[basename.casefold()].append(show)
    return depended


def tier_classes(index_path: Path, identity: ci.IdentityIndex
                 ) -> dict[str, list[dict[str, Any]]]:
    con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    paths = dict(con.execute("SELECT asset_id, relative_path FROM assets"))
    loose = {r[0] for r in con.execute(
        "SELECT relative_path FROM assets WHERE relative_path NOT LIKE '%/%'")}
    project_of = dict(con.execute(
        "SELECT asset_id, project_id FROM project_members"))
    con.close()

    tiers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for content_id, klass in identity.classes.items():
        if klass.member_count < 2:
            continue
        members = [paths[a] for a in identity.members_of[content_id] if a in paths]
        if len(members) < 2:
            continue
        strays = [m for m in members if m in loose]
        projects = {project_of.get(a) for a in identity.members_of[content_id]
                    if a in project_of}
        entry = {
            "content_id": content_id,
            "members": members,
            "bytes_each": klass.bytes_each,
            "reclaimable_bytes": klass.reclaimable_bytes,
            "strays": strays,
            "roots": list(klass.roots),
        }
        if strays and len(members) > len(strays):
            tiers["T1_loose_copy_at_disk_root"].append(entry)
        elif len(projects) > 1 and klass.crosses_roots:
            tiers["T2_crosses_roots_needs_an_answer"].append(entry)
        else:
            tiers["T3_inside_one_project_left_alone"].append(entry)
    return tiers


def propose_safe_actions(tier_one: list[dict[str, Any]],
                         depended: dict[str, list[str]],
                         blend_targets: set[str] | None = None
                         ) -> list[dict[str, Any]]:
    """Two independent dependency checks, and either one can veto.

    The Resolume check is by basename, which is all a composition offers. The
    .blend check is by EXACT path, because a ``//`` declaration resolves against
    the .blend's own directory and can therefore be verified rather than
    guessed. 57 such edges were proven, 11 of them crossing container roots --
    ``SUERTE/TREBOL.blend`` reaching into ``DREFMOVISTAR/textures/``, and
    ``SCD/cityhigh.blend`` into ``MARLONLOLLA/LT26/``. Those are dependencies no
    identity measurement finds, because they are not copies.
    """
    targets = blend_targets or set()
    proposals = []
    for entry in sorted(tier_one, key=lambda e: -e["reclaimable_bytes"]):
        for stray in entry["strays"]:
            basename = stray.rsplit("/", 1)[-1].casefold()
            shows = depended.get(basename, [])
            opened_by_blend = stray in targets
            keeps = [m for m in entry["members"] if m != stray]
            proposals.append({
                "verdict": (HOLD if shows
                            else HOLD_BLEND if opened_by_blend else SAFE),
                "redundant_copy": stray,
                "identical_copies_that_remain": keeps,
                "bytes_freed": entry["bytes_each"],
                "proof": f"full sha256 identical: {entry['content_id']}",
                # What must stay true after the move, stated per proposal.
                "invariant": f"{len(keeps)} byte-identical copy(ies) remain at "
                             f"{keeps[0] if keeps else '(none)'}",
                **({"held_because": f"named by the Resolume composition(s) "
                                    f"{sorted(set(shows))}, by basename; a "
                                    f"basename hit can be a false hold but "
                                    f"never a false safe"} if shows
                   else {"held_because": "a .blend declares this EXACT path as "
                                         "something it opens; verified, not "
                                         "guessed"} if opened_by_blend else {}),
            })
    return proposals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--identity", type=Path, required=True,
                        help="the sidecar written by resolve_identity_ties.py")
    parser.add_argument("--declared-inputs", type=Path, default=None,
                        help="basename -> count, from the .blend sweep")
    parser.add_argument("--show-usage", type=Path,
                        default=Path("/home/mak/curatoria_inbox/show_usage"))
    parser.add_argument("--blend-dependencies", type=Path, default=None,
                        help="paths a .blend declares it opens, exact match")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.index.is_file():
        print(json.dumps({"aborted": "index_missing"}))
        return 2

    record = runrecord.record(
        contract=CONTRACT, argv=sys.argv[1:],
        modules=[runrecord, ci, sys.modules[__name__]],
        repo=ROOT, inputs=[args.index, args.identity])

    identity = ci.load_identity(args.identity)
    declarations: dict[str, int] | None = None
    if args.declared_inputs and args.declared_inputs.is_file():
        lowered = json.loads(args.declared_inputs.read_text(encoding="utf-8"))
        con = sqlite3.connect(f"file:{args.index}?mode=ro", uri=True)
        declarations = {}
        for (relative,) in con.execute("SELECT relative_path FROM assets"):
            basename = relative.rsplit("/", 1)[-1]
            count = lowered.get(basename.casefold())
            if count:
                declarations[basename] = count
        con.close()

    overlaps = ci.root_overlaps(args.index, identity, declarations=declarations)
    relations = ci.identity_relations(overlaps)
    triaged = ci.triage(ci.open_questions(relations, overlaps))
    tiers = tier_classes(args.index, identity)
    depended = load_show_dependencies(args.show_usage)
    blend_targets: set[str] = set()
    if args.blend_dependencies and args.blend_dependencies.is_file():
        blend_targets = set(json.loads(
            args.blend_dependencies.read_text(encoding="utf-8")))
    proposals = propose_safe_actions(tiers["T1_loose_copy_at_disk_root"],
                                     depended, blend_targets)

    result = {
        "identity": identity.summary(),
        "tiers": {name: {"classes": len(entries),
                         "reclaimable_bytes": sum(e["reclaimable_bytes"]
                                                  for e in entries)}
                  for name, entries in sorted(tiers.items())},
        "relations": {
            "root_pairs_with_proven_shared_content": len(overlaps),
            "certified_library_reuse": sum(
                1 for r in relations if r.epistemic_status == "EMPIRICAL"),
            "still_a_tie_for_the_operator": sum(
                1 for r in relations if r.epistemic_status == "UNKNOWN"),
        },
        "door": {
            "questions_before_triage": triaged["asked_count"] + triaged["deferred_count"],
            "questions_to_ask": triaged["asked_count"],
            "coverage_of_disputed_bytes": triaged["coverage_of_disputed_bytes"],
            "deferred": triaged["deferred_count"],
            "deferred_bytes": triaged["deferred_bytes"],
            "cut_rule": triaged["cut_rule"],
        },
        "safe_actions": {
            "proposals": len(proposals),
            "safe": sum(1 for p in proposals if p["verdict"] == SAFE),
            "held_by_a_show": sum(1 for p in proposals if p["verdict"] == HOLD),
            "held_by_a_blend": sum(1 for p in proposals
                                   if p["verdict"] == HOLD_BLEND),
            "blend_declared_paths_known": len(blend_targets),
            "bytes_if_all_safe_applied": sum(
                p["bytes_freed"] for p in proposals if p["verdict"] == SAFE),
            "show_basenames_known": len(depended),
        },
        "declarations_used": len(declarations or {}),
    }
    record.update(finished_at=runrecord.now(), result=result)
    record["output_sha256"] = runrecord.result_digest(result)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "order_projection.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "questions.json").write_text(
        json.dumps(triaged, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "safe_actions.json").write_text(
        json.dumps(proposals, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1, sort_keys=True))
    print(f"output_sha256 {record['output_sha256']}")
    print(f"escrito en {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
