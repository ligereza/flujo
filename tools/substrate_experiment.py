#!/usr/bin/env python3
"""The pre-registered adversarial experiment on a real artistic chain.

PRE-REGISTRATION. The predictions below are stated before the run and are not
edited afterwards. If a prediction fails, the failure is the result.

The chain is not synthetic and the renaming is not mine. ``ICLODU5`` is an
export or upload staging folder where a tool already replaced every meaningful
name with a random one, and the XMP DocumentID is what still connects the two.
That makes it a naturally occurring adversarial case: the destruction of the name
happened in the operator's real workflow years ago, not in a fixture.

    CHAIN A   SUERTE/Comp 17.mp4        ->  ICLODU5/ROQX6471.MP4
              "Comp 17" is After Effects' default composition name, so the
              upstream name is itself a tool default. Both sides of this pair
              are names that carry no authored meaning.

    CHAIN B   3D JJJ/letrap3.mp4        ->  ICLODU5/AKIF9709.MP4

    CHAIN C   DrefQuila/cristaal.mov   <->  BAHPARTY/bah/cristaal.mov
              The same work in two clients' folders.

    CONTROL   LYON/COMANDO/textures/Mad_AC_03.jpg
              SCD/textures/Mad_AC_03.jpg
              One purchased texture inside two different commissions.

PREDICTIONS

P1  Each pair is byte-identical, so each pair yields ONE Content and TWO
    Observations. If a pair yields two Contents, the sizes matched by accident.

P2  Each pair yields ONE ArtifactState, because a shared InstanceID or a shared
    digest keys them the same.

P3  Each pair sits in ONE Lineage, and the lineage survives the perturbation.

P4  Under perturbation -- every directory renamed to noise, every basename
    replaced, mtimes rewritten, half the files moved inside a ZIP -- the set of
    Content ids and the set of Lineage ids are UNCHANGED. Not similar: equal.

P5  No basename or extension from the original survives anywhere in the
    perturbed observations.

P6  CONTROL: the shared texture produces same_content and same_lineage edges ON
    THE TEXTURE, and produces ZERO edges relating the two commissions. This
    prediction is weak by construction and is recorded as such: the substrate has
    no container entity, so there is nothing available to merge. The control can
    only fail if the substrate invents a relation, not if it resists one.

P7  A prediction that may well fail: the exported side of chains A and B will
    carry an ``xmpMM:Ingredients`` list naming its sources, giving a
    source -> export edge. The corpus scan found 0 of 120 shared-DocumentID
    groups crossing an extension, which is evidence against this, so P7 is
    expected to FAIL and is stated in order to be falsified rather than omitted.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.substrate import (  # noqa: E402
    OBSERVED_AT,
    REFERENCES,
    SAME_CONTENT,
    SAME_LINEAGE,
    USES,
    Substrate,
    extract,
    ingest_archive,
    ingest_file,
)

SSD = Path("/media/mak/PortableSSD")

CHAINS = {
    "A_comp17_to_export": ["SUERTE/Comp 17.mp4", "ICLODU5/ROQX6471.MP4"],
    "B_letrap_to_export": ["3D JJJ/letrap3.mp4", "ICLODU5/AKIF9709.MP4"],
    "C_cristaal_two_clients": ["DrefQuila/cristaal.mov",
                               "BAHPARTY/bah/cristaal.mov"],
    "CONTROL_shared_texture": ["LYON/COMANDO/textures/Mad_AC_03.jpg",
                               "SCD/textures/Mad_AC_03.jpg"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sets_of(sub: Substrate) -> dict[str, set]:
    con = sub.connect()
    return {
        "content": {r[0] for r in con.execute("SELECT content_id FROM content")},
        "state": {r[0] for r in con.execute("SELECT state_id FROM artifact_state")},
        "lineage": {r[0] for r in con.execute("SELECT lineage_id FROM lineage")},
        "basename": {r[0] for r in con.execute("SELECT basename FROM observation")},
        "extension": {r[0] for r in con.execute("SELECT extension FROM observation")},
    }


def ingest_originals(work: Path) -> tuple[Substrate, dict[str, Any]]:
    sub = Substrate(work / "original.db")
    detail: dict[str, Any] = {}
    for chain, members in CHAINS.items():
        rows = []
        for relative in members:
            source = SSD / relative
            result = ingest_file(sub, source, root_id="SSD",
                                relative_path=relative, hash_content=True)
            xmp = extract(str(source))
            rows.append({
                "path": relative,
                "content_id": result.get("content_id"),
                "state_id": result.get("state_id"),
                "id_source": result.get("id_source"),
                "lineage_id": result.get("lineage_id"),
                "instance_id": xmp.fields.instance_id if xmp.fields else None,
                "document_id": xmp.fields.document_id if xmp.fields else None,
                "ingredients": len(xmp.fields.ingredients) if xmp.fields else 0,
                "history": len(xmp.fields.history) if xmp.fields else 0,
                "creator_tool": xmp.fields.creator_tool if xmp.fields else None,
            })
        detail[chain] = rows
    sub.resolve_pending_references()
    return sub, detail


def perturb(work: Path) -> list[tuple[Path, str, str | None]]:
    """Destroy every path, basename and extension. Keep the bytes.

    Returns (absolute, relative, container) so the caller can ingest what it
    finds rather than what it put there.
    """
    staged = work / "perturbed"
    staged.mkdir(parents=True, exist_ok=True)
    plan: list[tuple[Path, str, str | None]] = []
    index = 0
    for members in CHAINS.values():
        for relative in members:
            source = SSD / relative
            # A name derived from the position alone: no basename, no extension,
            # nothing a matcher could latch onto.
            opaque = staged / f"d{index % 3}" / f"s{index}" / f"{index * 7919 % 613}"
            opaque.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, opaque)
            os.utime(opaque, (631152000, 631152000))     # 1990-01-01
            if index % 2 == 0:
                plan.append((opaque, str(opaque.relative_to(staged)), None))
            else:
                bundle = staged / f"pack{index}.zip"
                with zipfile.ZipFile(bundle, "w") as zf:
                    zf.write(opaque, arcname=f"w{index}/{index}")
                opaque.unlink()
                plan.append((bundle, f"pack{index}.zip", "zip"))
            index += 1
    return plan


def main(argv: list[str] | None = None) -> int:
    # A real parser, because the previous version took argv[0] as a directory and
    # created it. The repository's own tool ratchet invokes every live tool with
    # --help, so that version answered "what do you do?" by making a directory
    # called "--help". Asking a tool what it does must never write anything.
    import argparse
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument("workdir", help="where to write the substrates and the "
                                        "experiment record")
    args = parser.parse_args(argv)
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "contract": "mak-substrate-experiment-v1",
        "started_at": _now(),
        "chains": {k: list(v) for k, v in CHAINS.items()},
        "predictions": [line.strip() for line in __doc__.splitlines()
                        if line.strip().startswith("P")][:7],
    }

    missing = [rel for members in CHAINS.values() for rel in members
               if not (SSD / rel).is_file()]
    if missing:
        report["aborted"] = {"missing": missing}
        print(json.dumps(report, indent=1))
        return 2

    original, detail = ingest_originals(work)
    report["original"] = detail
    before = sets_of(original)

    perturbed_sub = Substrate(work / "perturbed.db")
    for absolute, relative, kind in perturb(work):
        if kind == "zip":
            ingest_archive(perturbed_sub, absolute, root_id="PERT",
                           relative_path=relative, hash_content=True)
        else:
            ingest_file(perturbed_sub, absolute, root_id="PERT",
                        relative_path=relative, hash_content=True)
    perturbed_sub.resolve_pending_references()
    after = sets_of(perturbed_sub)

    # --------------------------------------------------------------- verdicts
    verdicts: dict[str, Any] = {}

    per_chain = {}
    for chain, rows in detail.items():
        contents = {r["content_id"] for r in rows}
        states = {r["state_id"] for r in rows}
        lineages = {r["lineage_id"] for r in rows if r["lineage_id"]}
        per_chain[chain] = {
            "files": len(rows),
            "distinct_content": len(contents),
            "distinct_state": len(states),
            "distinct_lineage": len(lineages),
            "id_sources": sorted({r["id_source"] for r in rows}),
            "ingredients": [r["ingredients"] for r in rows],
            "history": [r["history"] for r in rows],
            "tools": sorted({r["creator_tool"] for r in rows if r["creator_tool"]}),
        }
    verdicts["per_chain"] = per_chain

    verdicts["P1_one_content_per_pair"] = all(
        v["distinct_content"] == 1 for v in per_chain.values())
    verdicts["P2_one_state_per_pair"] = all(
        v["distinct_state"] == 1 for v in per_chain.values())
    verdicts["P3_one_lineage_per_pair"] = {
        chain: v["distinct_lineage"] for chain, v in per_chain.items()}
    verdicts["P4_content_survives_perturbation"] = (
        before["content"] == after["content"])
    verdicts["P4_lineage_survives_perturbation"] = (
        before["lineage"] == after["lineage"])
    verdicts["P4_state_survives_perturbation"] = before["state"] == after["state"]
    verdicts["P5_no_original_name_survives"] = {
        "shared_basenames": sorted(before["basename"] & after["basename"]),
        "shared_extensions": sorted(before["extension"] & after["extension"]),
    }
    control_rows = detail["CONTROL_shared_texture"]
    control_states = {r["state_id"] for r in control_rows}
    cross_edges = [e for e in original.edges()
                   if e["subject"] in control_states
                   and e["predicate"] not in (OBSERVED_AT, SAME_CONTENT,
                                              SAME_LINEAGE)]
    verdicts["P6_control_invents_no_relation"] = {
        "edges_beyond_observation_content_lineage": len(cross_edges),
        "note": "weak by construction: the substrate has no container entity, so "
                "there is nothing available to merge. It can only fail by "
                "inventing a relation.",
    }
    verdicts["P7_export_declares_its_sources"] = {
        "ingredients_per_file": {chain: v["ingredients"]
                                 for chain, v in per_chain.items()},
        "any": any(n for v in per_chain.values() for n in v["ingredients"]),
    }

    report["before"] = {k: len(v) for k, v in before.items()}
    report["after"] = {k: len(v) for k, v in after.items()}
    report["verdicts"] = verdicts
    report["original_summary"] = original.summary()
    report["perturbed_summary"] = perturbed_sub.summary()
    report["finished_at"] = _now()

    out = work / "experiment.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k in ("before", "after", "verdicts")},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
