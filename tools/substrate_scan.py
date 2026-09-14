#!/usr/bin/env python3
"""Scan a corpus into the identity substrate, recording everything a repeat needs.

The previous measurement of this corpus could not be repeated, and the reason was
not carelessness about the numbers -- it was that five of the nine things a
repeat requires were never written down: the commit, the extractor version, the
file manifest, the errors with their paths, and a hash of the output. Worse, the
table that was reported spliced two runs made with two different versions of the
extractor, so the totals corresponded to no execution that had ever happened.

So this tool refuses to produce a result without a run record:

    commit          git HEAD, and whether the tree was dirty
    command         argv, verbatim
    root            the path, plus the device and filesystem it resolved to
    extractor       a digest of the extractor sources actually imported
    manifest        every candidate: path, size, mtime, and digest when hashed
    errors          every failure, WITH its path
    output          a digest of the result document, so two runs can be compared

A dirty tree is recorded rather than refused, because refusing would tempt a
throwaway commit. But the flag is what a later reader needs in order to distrust
the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.substrate import Substrate, ingest_file  # noqa: E402
from flujo.substrate import xmp as xmp_module  # noqa: E402
from flujo.substrate import ingest as ingest_module  # noqa: E402
from flujo.substrate import schema as schema_module  # noqa: E402
from flujo.substrate import epistemics as epistemics_module  # noqa: E402

CONTRACT = "mak-substrate-scan-v1"

DEFAULT_EXTENSIONS = (
    ".aep", ".psd", ".ai", ".pdf", ".indd", ".prproj", ".eps", ".svg", ".jpg",
    ".jpeg", ".tif", ".tiff", ".png", ".mov", ".mp4", ".dng", ".cr2", ".nef",
    ".webp", ".gif", ".avc", ".xml",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def extractor_version() -> dict[str, str]:
    """Digest the sources actually imported, not a hand-maintained number.

    A version string someone has to remember to bump is a version string that
    stops being true. This one cannot drift from the code it describes.
    """
    parts = {}
    for name, module in (("xmp", xmp_module), ("ingest", ingest_module),
                         ("schema", schema_module),
                         ("epistemics", epistemics_module)):
        source = Path(module.__file__).read_bytes()
        parts[name] = hashlib.sha256(source).hexdigest()[:16]
    combined = hashlib.sha256(
        "|".join(f"{k}:{v}" for k, v in sorted(parts.items())).encode()).hexdigest()
    return {**parts, "combined": combined[:32]}


def git_state() -> dict[str, Any]:
    # `run` used to fold a FAILED git call (not a repo, git missing, timeout)
    # into the same empty string as "no output" -- so `tree_dirty: bool(dirty)`
    # read as False (clean) for a check that never ran at all, and `commit`
    # came back "" indistinguishable from a repo with no history. This tool's
    # own docstring is "refuses to produce a result without a run record"; a
    # dirty flag that is silently wrong is not a run record, it is a guess
    # wearing one.
    def run(*args: str) -> tuple[str, bool]:
        try:
            out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                 text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return "", False
        return out.stdout.strip(), out.returncode == 0
    dirty, dirty_ok = run("status", "--porcelain=v1")
    commit, commit_ok = run("rev-parse", "HEAD")
    branch, branch_ok = run("rev-parse", "--abbrev-ref", "HEAD")
    available = dirty_ok and commit_ok and branch_ok
    return {"commit": commit,
            "branch": branch,
            "available": available,
            # None (not False) when unavailable: an unmeasured tree must not
            # be reported as a clean one.
            "tree_dirty": bool(dirty) if available else None,
            "dirty_paths": dirty.splitlines()[:20] if available else []}


def root_identity(root: Path) -> dict[str, Any]:
    """Which physical thing the root resolved to, not just what it was called."""
    resolved = root.resolve()
    out: dict[str, Any] = {"given": str(root), "resolved": str(resolved)}
    try:
        stat = os.stat(resolved)
        out["device"] = stat.st_dev
    except OSError as exc:
        out["error"] = str(exc)
    try:
        with open("/proc/mounts", encoding="utf-8") as handle:
            best = ""
            for line in handle:
                parts = line.split()
                if len(parts) >= 3 and str(resolved).startswith(parts[1]) \
                        and len(parts[1]) > len(best):
                    best, out["mount"], out["fstype"] = parts[1], parts[1], parts[2]
    except OSError:
        pass
    return out


def build_manifest(root: Path, extensions: tuple[str, ...], *,
                   limit: int | None, hash_files: bool) -> dict[str, Any]:
    """Enumerate the candidates and describe each one. This IS the line base."""
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    wanted = {e.lower() for e in extensions}
    for current, dirs, files in os.walk(root, onerror=lambda e: errors.append(
            {"path": getattr(e, "filename", "?"), "error": str(e),
             "stage": "walk"})):
        dirs.sort()
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() not in wanted:
                continue
            absolute = Path(current) / name
            relative = str(absolute.relative_to(root))
            row: dict[str, Any] = {"path": relative}
            try:
                stat = absolute.stat()
                row["size"] = stat.st_size
                row["mtime_ns"] = stat.st_mtime_ns
            except OSError as exc:
                errors.append({"path": relative, "error": str(exc),
                               "stage": "stat"})
                continue
            if hash_files:
                try:
                    digest = hashlib.sha256()
                    with open(absolute, "rb") as handle:
                        while True:
                            block = handle.read(1 << 20)
                            if not block:
                                break
                            digest.update(block)
                    row["sha256"] = digest.hexdigest()
                except OSError as exc:
                    errors.append({"path": relative, "error": str(exc),
                                   "stage": "hash"})
            entries.append(row)
            if limit and len(entries) >= limit:
                break
        if limit and len(entries) >= limit:
            break
    entries.sort(key=lambda row: row["path"])
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return {"files": len(entries), "errors": errors,
            "manifest_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "entries": entries}


def scan(root: Path, *, extensions: tuple[str, ...], limit: int | None,
         hash_files: bool, db: Path | None, manifest_entries: list | None = None
         ) -> dict[str, Any]:
    """Extract XMP from every candidate and tally, deterministically ordered."""
    import collections
    started = time.time()
    if manifest_entries is None:
        manifest = build_manifest(root, extensions, limit=limit,
                                 hash_files=hash_files)
        manifest_entries = manifest["entries"]
        manifest_errors = manifest["errors"]
        manifest_hash = manifest["manifest_sha256"]
    else:
        manifest_errors = []
        payload = json.dumps(manifest_entries, sort_keys=True,
                             separators=(",", ":"))
        manifest_hash = hashlib.sha256(payload.encode()).hexdigest()

    substrate = Substrate(db) if db else None
    by_ext: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: dict.fromkeys(
            ("seen", "traversal_yes", "vocabulary_yes", "negative_is_evidence",
             "packets", "document_id", "instance_id", "original_document_id",
             "derived_from", "history", "ingredients", "pantry", "error"), 0))
    methods: dict[str, int] = collections.Counter()
    errors: list[dict[str, str]] = list(manifest_errors)
    documents: dict[str, list[str]] = collections.defaultdict(list)
    history_lengths: list[int] = []
    ingredient_total = 0

    for row in manifest_entries:
        relative = row["path"]
        extension = os.path.splitext(relative)[1].lower()
        bucket = by_ext[extension]
        bucket["seen"] += 1
        absolute = root / relative
        result = xmp_module.extract(str(absolute))
        methods[result.method] += 1
        if result.error:
            bucket["error"] += 1
            errors.append({"path": relative, "error": result.error,
                           "stage": "extract"})
            continue
        levels = result.levels
        bucket["traversal_yes"] += int(levels.traversal == epistemics_module.YES)
        bucket["vocabulary_yes"] += int(levels.vocabulary == epistemics_module.YES)
        bucket["negative_is_evidence"] += int(levels.negative_is_evidence)
        bucket["packets"] += result.packets
        fields = result.fields
        if fields:
            for name in ("document_id", "instance_id", "original_document_id"):
                if getattr(fields, name):
                    bucket[name] += 1
            if fields.derived_from:
                bucket["derived_from"] += 1
            if fields.history:
                bucket["history"] += 1
                history_lengths.append(len(fields.history))
            if fields.ingredients:
                bucket["ingredients"] += 1
                ingredient_total += len(fields.ingredients)
            if fields.pantry:
                bucket["pantry"] += 1
            if fields.document_id:
                documents[fields.document_id].append(relative)
        if substrate is not None:
            try:
                ingest_file(substrate, absolute, root_id=str(root),
                            relative_path=relative, hash_content=hash_files,
                            read_references=extension in (".avc", ".xml"))
            except Exception as exc:                      # noqa: BLE001
                errors.append({"path": relative, "error": repr(exc),
                               "stage": "ingest"})

    totals = {key: sum(bucket[key] for bucket in by_ext.values())
              for key in next(iter(by_ext.values()))} if by_ext else {}
    shared = {key: sorted(paths) for key, paths in documents.items()
              if len(paths) > 1}
    result: dict[str, Any] = {
        "contract": CONTRACT,
        "manifest_sha256": manifest_hash,
        "files": len(manifest_entries),
        "by_extension": {k: dict(v) for k, v in sorted(by_ext.items())},
        "totals": totals,
        "methods": dict(sorted(methods.items())),
        "errors": sorted(errors, key=lambda row: (row["stage"], row["path"])),
        "error_count": len(errors),
        "distinct_document_ids": len(documents),
        "shared_document_ids": len(shared),
        "files_in_shared_groups": sum(len(v) for v in shared.values()),
        "shared_groups": [{"document_id": k, "files": v}
                          for k, v in sorted(shared.items())],
        "history_events_total": sum(history_lengths),
        "history_files": len(history_lengths),
        "history_max": max(history_lengths) if history_lengths else 0,
        "ingredient_refs_total": ingredient_total,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    if substrate is not None:
        result["substrate_summary"] = substrate.summary()
        result["reference_resolution"] = substrate.resolve_pending_references()
    return result


def output_digest(result: dict[str, Any]) -> str:
    """Hash everything a repeat should reproduce, excluding wall time."""
    comparable = {k: v for k, v in result.items()
                  if k not in ("elapsed_seconds", "substrate_summary",
                               "reference_resolution")}
    return hashlib.sha256(json.dumps(comparable, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root")
    parser.add_argument("--out", type=Path, required=True,
                        help="where to write the run record")
    parser.add_argument("--db", type=Path, default=None,
                        help="also ingest into a substrate database")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--hash-files", action="store_true",
                        help="compute a full digest of every candidate")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--reuse-manifest", type=Path, default=None,
                        help="scan exactly the files a previous run recorded")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: root_not_a_directory: {root}", file=sys.stderr)
        return 2

    record: dict[str, Any] = {
        "contract": CONTRACT,
        "started_at": _now(),
        "command": ["substrate_scan.py", *(argv if argv is not None else sys.argv[1:])],
        "git": git_state(),
        "extractor_version": extractor_version(),
        "root": root_identity(root),
        "python": sys.version.split()[0],
        "extensions": list(DEFAULT_EXTENSIONS),
    }

    reused = None
    if args.reuse_manifest:
        previous = json.loads(args.reuse_manifest.read_text(encoding="utf-8"))
        reused = previous["manifest"]["entries"]
        record["reused_manifest_from"] = str(args.reuse_manifest)
        record["reused_manifest_sha256"] = previous["manifest"]["manifest_sha256"]

    if args.manifest_only:
        manifest = build_manifest(root, DEFAULT_EXTENSIONS, limit=args.limit,
                                  hash_files=args.hash_files)
        record["manifest"] = manifest
        record["finished_at"] = _now()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(json.dumps({"files": manifest["files"],
                          "manifest_sha256": manifest["manifest_sha256"],
                          "errors": len(manifest["errors"])}, indent=1))
        return 0

    if reused is None:
        manifest = build_manifest(root, DEFAULT_EXTENSIONS, limit=args.limit,
                                  hash_files=args.hash_files)
        record["manifest"] = {k: v for k, v in manifest.items() if k != "entries"}
        record["manifest"]["entries"] = manifest["entries"]
        reused = manifest["entries"]

    result = scan(root, extensions=DEFAULT_EXTENSIONS, limit=args.limit,
                  hash_files=args.hash_files, db=args.db,
                  manifest_entries=reused)
    record["result"] = result
    record["output_sha256"] = output_digest(result)
    record["finished_at"] = _now()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "files": result["files"],
        "output_sha256": record["output_sha256"],
        "manifest_sha256": result["manifest_sha256"],
        "errors": result["error_count"],
        "commit": record["git"]["commit"][:12],
        "git_available": record["git"]["available"],
        "tree_dirty": record["git"]["tree_dirty"],
        "extractor": record["extractor_version"]["combined"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
