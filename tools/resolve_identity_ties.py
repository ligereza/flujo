#!/usr/bin/env python3
"""Resolve the identity ties the existing index refuses to decide.

WHY THIS EXISTS

``archivo_index.sqlite`` carries ``hash_state='pending'`` for 45424 of its 45536
assets and a real ``full_sha256`` for 112 (0.25%). Every consumer downstream is
compensating for that. ``project_reconstruction`` says so in its own docstring:

    a sample is not an identity: two files can agree on a sample and differ in
    full content. Therefore a shared sample hash never decides project identity
    here; it produces an explicit tie with both alternatives preserved.

There are 1348 such ties over 4104 assets. They are not missing metadata. They
are 1348 decisions the system declines to take, by design, for want of one fact.
This tool supplies the fact.

THE ESCALATION HAS TWO STAGES, NOT THREE

    stage 0   byte size          free, already indexed
    stage 1   whole file         the only paid stage

A cheap DISAGREEMENT certifies difference: two files of different size are
different files, and no further reading can change that. Past size there is no
cheaper-than-whole-file test worth running on this corpus -- a middle stage was
tried, measured, and removed. What follows is why, kept rather than deleted
silently, because the reason generalizes past this one tool.

A THIRD STAGE WAS HERE. IT WAS DELETED. THIS IS THE MEASUREMENT THAT KILLED IT.

An earlier version inserted a stage 1 between these two: hash the last 64 KiB
of each file before paying for the whole thing. Measured on the 4104 disputed
assets of this corpus:

    assets in dispute            4104
    stage 0 distinctions            0
    stage 1 DISTINCTIONS            0        <- the whole justification, and it is zero
    bytes read by stage 1   197522805  (197 MB, spent for nothing)
    bytes read by stage 2 107815334311
    read amplification avoided    1.0x

Zero distinctions for 197 MB is not a rounding error to tune away.

SPECIFIC reason: the objects in dispute here are video containers and numbered
simulation caches, and both families write near-identical trailing bytes
(container trailers and footer atoms; fixed-layout cache blocks). Even the 7
assets that genuinely differ -- consecutive frames of a fluid cache under
``LYON/3/123_flip_fluid_cache/bakefiles/`` -- have matching tails, and still
had to escalate to a full read to be told apart.

GENERAL reason, worth keeping even though the specific one would have been
enough to delete this probe: a cheap test can only accelerate the side of a
decision that has a finite witness. "These two objects differ" has a witness --
the differing byte -- and a sublinear read can land on one and stop. "These two
objects are identical" has no witness over unbounded content: no partial read
can rule out a difference still unread, so no sublinear test can ever CERTIFY
agreement, only ever REJECT it. Stage 1 was built to accelerate the agreement
side, the side with no witness, so it was doomed by construction, independent
of which 64 KiB it happened to read. Any test that reads o(n) bits can only
reject objects that are far apart; near-duplicates are provably invisible to
it, and near-duplicates are exactly what a shared sample hash selects for.

THE CORRECT SHAPE, SO THE DELETION DOES NOT READ AS GIVING UP

With m objects and up to m*m pairs to compare, the right ladder amortizes PER
OBJECT, not per pair: size, then a strong fingerprint computed and cached once
per object, then a byte comparison only where fingerprints already agree. A
per-pair cheap probe -- re-reading some fixed slice of a file for every pair it
is compared against -- is the wrong shape regardless of which bytes it reads;
the tail was just the version that got measured and killed here. This tool
does not need the per-object cache today, because at this scale the whole-file
stage already dominates the budget, but a future increase in scale should reach
for that shape before reaching for a new cheap probe.

WHAT SURVIVED THE DELETION WITHOUT ANY CODE

The deleted stage also carried a shortcut: a file no larger than its 64 KiB
window was read whole, so its tail digest WAS its full digest, and it was
certified without a further read. Deleting the stage does not lose that
capability and does not cost anything extra: such a file now simply gets a
full digest at stage 1, for exactly the same number of bytes, because the old
window already covered the whole file. Nobody should "restore" a small-file
fast path later; it was never a separate cost to begin with.

WHAT IT WRITES

Nothing into the index. The index is read-only evidence and stays that way; the
verdicts land in a sidecar keyed by ``asset_id``. A duplicate that crosses two
container roots is separated from one that does not, because only the first is
evidence about whether two commissions share a work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo import runrecord                                          # noqa: E402
from flujo.substrate import epistemics                               # noqa: E402

CONTRACT = "mak-identity-ties-v1"
DEFAULT_INDEX = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")
DEFAULT_ROOT = Path("/media/mak/PortableSSD")

READ_BLOCK = 1 << 20

CERTIFIED_SAME = "CERTIFIED_SAME"
CERTIFIED_DISTINCT = "CERTIFIED_DISTINCT"
UNRESOLVED = "UNRESOLVED"

DDL = """
CREATE TABLE IF NOT EXISTS identity_run (
  run_id TEXT PRIMARY KEY, record_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS identity_asset (
  asset_id TEXT PRIMARY KEY,
  relative_path TEXT NOT NULL, extension TEXT, container_root TEXT,
  bytes INTEGER, sample_sha256 TEXT,
  full_sha256 TEXT,
  content_id TEXT, verdict TEXT NOT NULL,
  resolved_at_stage INTEGER, unknown_cause TEXT,
  is_appledouble INTEGER NOT NULL DEFAULT 0,
  run_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS identity_class (
  content_id TEXT PRIMARY KEY, member_count INTEGER NOT NULL,
  bytes_each INTEGER, total_bytes INTEGER, reclaimable_bytes INTEGER,
  distinct_roots INTEGER, roots_json TEXT, extensions_json TEXT,
  crosses_roots INTEGER NOT NULL, run_id TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_asset_content ON identity_asset(content_id);
CREATE INDEX IF NOT EXISTS idx_asset_verdict ON identity_asset(verdict);
"""


def container_root(relative_path: str) -> str:
    """The top-level directory. A duplicate crossing two of these means more."""
    head = relative_path.lstrip("./").split("/", 1)[0]
    return head or "(root)"


def is_appledouble(relative_path: str) -> bool:
    """macOS resource-fork stubs. Real duplicates, and never artworks.

    Kept and labelled rather than filtered: a tool that silently drops inputs
    cannot be checked against the index it read from.
    """
    return relative_path.rsplit("/", 1)[-1].startswith("._")


def digest_whole(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    read = 0
    with path.open("rb") as handle:
        while True:
            block = handle.read(READ_BLOCK)
            if not block:
                break
            digest.update(block)
            read += len(block)
    return digest.hexdigest(), read


def load_ties(index: Path) -> dict[str, list[dict[str, Any]]]:
    con = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    rows = con.execute("""
        SELECT asset_id, relative_path, extension, bytes, sample_sha256
        FROM assets
        WHERE sample_sha256 IS NOT NULL AND sample_sha256 <> ''
          AND sample_sha256 IN (
            SELECT sample_sha256 FROM assets
            WHERE sample_sha256 IS NOT NULL AND sample_sha256 <> ''
            GROUP BY 1 HAVING COUNT(*) > 1)
        ORDER BY sample_sha256, relative_path
    """).fetchall()
    con.close()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for asset_id, relative, extension, size, sample in rows:
        groups[sample].append({
            "asset_id": asset_id, "relative_path": relative,
            "extension": extension, "bytes": size or 0, "sample_sha256": sample,
            "container_root": container_root(relative),
            "is_appledouble": is_appledouble(relative),
        })
    return groups


def resolve(groups: dict[str, list[dict[str, Any]]], root: Path, *,
            full_budget: int | None) -> dict[str, Any]:
    stats = {
        "groups": len(groups),
        "assets": sum(len(v) for v in groups.values()),
        "stage0_resolved": 0, "stage1_resolved": 0,
        "bytes_read_stage1": 0,
        "bytes_if_naive": sum(m["bytes"] for v in groups.values() for m in v),
        "unresolved_over_budget": 0, "unreadable": 0,
    }
    decided: list[dict[str, Any]] = []

    # ---------------------------------------------------------------- stage 0
    # Subgroup by size. A size difference is a certified distinction that costs
    # nothing. Measured on this corpus: 0 of 4104 disputed assets resolved here
    # -- every tie group has members of identical size -- kept anyway because
    # on another corpus it is the cheapest win available, and its yield of 0
    # is a fact about this disk, not a reason to drop the free check.
    size_groups: list[tuple[str, int, list[dict[str, Any]]]] = []
    for sample, members in groups.items():
        by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for member in members:
            by_size[member["bytes"]].append(member)
        for size, subset in by_size.items():
            if len(subset) == 1:
                member = dict(subset[0], verdict=CERTIFIED_DISTINCT,
                              resolved_at_stage=0, content_id=None)
                decided.append(member)
                stats["stage0_resolved"] += 1
            else:
                size_groups.append((sample, size, subset))

    # ---------------------------------------------------------------- stage 1
    # Whole-file digest: the only paid stage. A 64 KiB tail probe used to sit
    # here; measured on these same 4104 assets it resolved 0 distinctions for
    # 197522805 bytes read, and was deleted -- see the module docstring for
    # why a sublinear read can never certify agreement, only reject it.
    #
    # Cross-root groups first: those are the ones that can change a project
    # verdict, so an interrupted run still leaves the valuable half decided.
    size_groups.sort(key=lambda item: (
        -len({m["container_root"] for m in item[2]}), item[1]))
    spent = 0
    for sample, size, group in size_groups:
        need = size * len(group)
        if full_budget is not None and spent + need > full_budget:
            for member in group:
                member.update(verdict=UNRESOLVED, resolved_at_stage=1,
                              unknown_cause=epistemics.MISSING_EVIDENCE,
                              content_id=None, note="full_hash_budget_exhausted")
                decided.append(member)
                stats["unresolved_over_budget"] += 1
            continue
        by_full: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in group:
            path = root / member["relative_path"]
            try:
                full, read = digest_whole(path)
            except OSError as error:
                member.update(verdict=UNRESOLVED, resolved_at_stage=1,
                              unknown_cause=epistemics.MISSING_EVIDENCE,
                              content_id=None, note=str(error)[:120])
                decided.append(member)
                stats["unreadable"] += 1
                continue
            member["full_sha256"] = full
            stats["bytes_read_stage1"] += read
            spent += read
            by_full[full].append(member)
        for full, klass in by_full.items():
            verdict = CERTIFIED_SAME if len(klass) > 1 else CERTIFIED_DISTINCT
            for member in klass:
                member.update(verdict=verdict, resolved_at_stage=1,
                              content_id=f"sha256:{full}" if len(klass) > 1 else None)
                decided.append(member)
                stats["stage1_resolved"] += 1
    return {"stats": stats, "assets": decided}


def build_classes(decided: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_content: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for member in decided:
        if member.get("content_id"):
            by_content[member["content_id"]].append(member)
    classes = []
    for content_id, members in by_content.items():
        roots = sorted({m["container_root"] for m in members})
        size = members[0]["bytes"]
        classes.append({
            "content_id": content_id,
            "member_count": len(members),
            "bytes_each": size,
            "total_bytes": size * len(members),
            # What a deduplication would free. Reported, never acted on.
            "reclaimable_bytes": size * (len(members) - 1),
            "distinct_roots": len(roots),
            "roots": roots,
            "extensions": sorted({m["extension"] or "" for m in members}),
            "crosses_roots": len(roots) > 1,
            "all_appledouble": all(m["is_appledouble"] for m in members),
        })
    classes.sort(key=lambda c: -c["reclaimable_bytes"])
    return classes


def persist(out_db: Path, record: dict[str, Any], decided: list[dict[str, Any]],
            classes: list[dict[str, Any]]) -> None:
    con = sqlite3.connect(out_db)
    con.executescript(DDL)
    run_id = record["code"]["version"] + ":" + record["started_at"]
    con.execute("INSERT OR REPLACE INTO identity_run VALUES (?,?)",
                (run_id, json.dumps(record, sort_keys=True)))
    con.executemany(
        "INSERT OR REPLACE INTO identity_asset (asset_id, relative_path, "
        "extension, container_root, bytes, sample_sha256, "
        "full_sha256, content_id, verdict, resolved_at_stage, unknown_cause, "
        "is_appledouble, run_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(m["asset_id"], m["relative_path"], m["extension"], m["container_root"],
          m["bytes"], m["sample_sha256"],
          m.get("full_sha256"), m.get("content_id"), m["verdict"],
          m.get("resolved_at_stage"), m.get("unknown_cause"),
          int(m["is_appledouble"]), run_id) for m in decided])
    con.executemany(
        "INSERT OR REPLACE INTO identity_class (content_id, member_count, "
        "bytes_each, total_bytes, reclaimable_bytes, distinct_roots, roots_json, "
        "extensions_json, crosses_roots, run_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(c["content_id"], c["member_count"], c["bytes_each"], c["total_bytes"],
          c["reclaimable_bytes"], c["distinct_roots"], json.dumps(c["roots"]),
          json.dumps(c["extensions"]), int(c["crosses_roots"]), run_id)
         for c in classes])
    con.commit()
    con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, required=True,
                        help="sidecar sqlite to write; the index is never written")
    parser.add_argument("--full-budget-gib", type=float, default=None,
                        help="cap on stage 1 reads. Groups left over are "
                             "recorded UNRESOLVED, never silently dropped.")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.index.is_file():
        print(json.dumps({"aborted": "index_missing", "index": str(args.index)}))
        return 2
    if not args.root.is_dir():
        print(json.dumps({"aborted": "root_not_mounted", "root": str(args.root)}))
        return 2

    record = runrecord.record(
        contract=CONTRACT, argv=sys.argv[1:],
        modules=[runrecord, epistemics, sys.modules[__name__]],
        repo=ROOT, inputs=[args.index], volumes=[args.root])

    budget = None if args.full_budget_gib is None else int(
        args.full_budget_gib * (1 << 30))
    started = time.monotonic()
    groups = load_ties(args.index)
    resolved = resolve(groups, args.root, full_budget=budget)
    classes = build_classes(resolved["assets"])
    elapsed = time.monotonic() - started

    stats = resolved["stats"]
    same = [c for c in classes if c["member_count"] > 1]
    result = {
        "stats": stats,
        "elapsed_seconds": round(elapsed, 1),
        "content_classes": len(same),
        "duplicate_assets": sum(c["member_count"] for c in same),
        "reclaimable_bytes": sum(c["reclaimable_bytes"] for c in same),
        "classes_crossing_roots": sum(1 for c in same if c["crosses_roots"]),
        "classes_all_appledouble": sum(1 for c in same if c["all_appledouble"]),
        "reclaimable_excluding_appledouble": sum(
            c["reclaimable_bytes"] for c in same if not c["all_appledouble"]),
        "verdicts": {v: sum(1 for m in resolved["assets"] if m["verdict"] == v)
                     for v in (CERTIFIED_SAME, CERTIFIED_DISTINCT, UNRESOLVED)},
        "read_amplification_avoided": round(
            stats["bytes_if_naive"] / max(1, stats["bytes_read_stage1"]), 1),
        "top_classes": [c for c in same if not c["all_appledouble"]][:15],
    }
    record.update(finished_at=runrecord.now(), result=result)
    record["output_sha256"] = runrecord.result_digest(
        record["result"], ignore=("elapsed_seconds",))

    persist(args.out, record, resolved["assets"], classes)
    if args.report:
        args.report.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                               encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "top_classes"},
                     indent=1, sort_keys=True))
    print(f"output_sha256 {record['output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
