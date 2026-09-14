#!/usr/bin/env python3
"""Run the adversarial whole-file witness for PNG XMP vocabulary.

The PNG locator can walk every declared chunk, but that alone does not prove
that an XMP packet cannot be hiding somewhere else in the file.  This tool
walks the complete byte stream and chunk table, validates every chunk CRC, and
looks for the raw packet markers used by the extractor outside an iTXt or tEXt
chunk whose keyword is ``XML:com.adobe.xmp``.  It also records a manifest with a
SHA-256 for every candidate, so the corpus and the bytes covered by the
witness are repeatable.

This is deliberately a bounded claim: it witnesses the extractor's raw
lexical packet vocabulary, not arbitrary compressed or encrypted bytes hidden
in an unknown PNG extension.  A hit, malformed PNG, CRC error, race, or walk
error keeps the witness ineligible and is reported rather than guessed away.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.substrate.xmp import PNG_MAGIC, PNG_XMP_KEYWORD  # noqa: E402

CONTRACT = "mak-png-xmp-witness-v1"
PNG_EXTENSIONS = {".png", ".apng"}
BLOCK_SIZE = 1 << 20
PROBE_SIZE = 256
RAW_MARKERS = (b"<?xpacket", b"<x:xmpmeta")
SPEC_CITATION = (
    "W3C PNG Specification (Third Edition), 11.3.3.1 Keywords and text "
    "strings and 11.3.3.4 iTXt, registered keyword XML:com.adobe.xmp; "
    "https://www.w3.org/TR/png-3/"
)
ADVERSARIAL_RULE = (
    "For every candidate byte, validate the PNG chunk table and CRCs, then "
    "search all data outside iTXt or tEXt chunks keyed XML:com.adobe.xmp for "
    "the raw packet markers <?xpacket or <x:xmpmeta used by this extractor."
)


class PngWitnessError(ValueError):
    """The file cannot support an exhaustive witness result."""


class RawMarkerScanner:
    """Find markers even when a read block splits one across two reads."""

    def __init__(self) -> None:
        self._tail = b""
        self.hits: set[str] = set()
        self.max_marker = max(map(len, RAW_MARKERS))

    def feed(self, data: bytes) -> None:
        if not data:
            return
        combined = self._tail + data
        for marker in RAW_MARKERS:
            if marker in combined:
                self.hits.add(marker.decode("ascii"))
        self._tail = combined[-(self.max_marker - 1):]

    def reset(self) -> None:
        """Do not join marker bytes across an excluded XMP container."""
        self._tail = b""


def _read_exact(handle: BinaryIO, size: int) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise PngWitnessError(f"truncated: wanted={size} got={len(data)}")
    return data


def _feed_trailing(handle: BinaryIO, *, digest: Any, scanner: RawMarkerScanner,
                   offset: int) -> tuple[int, int]:
    total = 0
    while True:
        block = handle.read(BLOCK_SIZE)
        if not block:
            break
        digest.update(block)
        scanner.feed(block)
        total += len(block)
    return total, offset + total


def scan_png(path: Path) -> dict[str, Any]:
    """Read one PNG from byte zero to EOF and return only measured facts."""
    before = path.stat()
    digest = hashlib.sha256()
    scanner = RawMarkerScanner()
    chunks = 0
    xmp_containers = 0
    iend_seen = False
    trailing_bytes = 0
    physical_offset = 0

    with path.open("rb") as handle:
        signature = _read_exact(handle, 8)
        digest.update(signature)
        physical_offset += len(signature)
        if signature != PNG_MAGIC:
            raise PngWitnessError("bad_signature")

        while not iend_seen:
            header = handle.read(8)
            if not header:
                raise PngWitnessError("missing_IEND")
            if len(header) != 8:
                raise PngWitnessError("truncated_chunk_header")
            digest.update(header)
            physical_offset += 8
            length, kind = struct.unpack(">I4s", header)
            chunks += 1
            crc = zlib.crc32(kind)

            # Keep only enough data to classify a text chunk.  The rest is
            # streamed so a large IDAT or private chunk cannot exhaust RAM.
            probe_size = min(length, PROBE_SIZE)
            probe = _read_exact(handle, probe_size)
            digest.update(probe)
            crc = zlib.crc32(probe, crc)
            physical_offset += probe_size
            is_xmp_container = (
                kind in (b"iTXt", b"tEXt")
                and probe.startswith(PNG_XMP_KEYWORD + b"\x00")
            )
            if is_xmp_container:
                xmp_containers += 1
                scanner.reset()
            else:
                scanner.feed(probe)

            remaining = length - probe_size
            while remaining:
                block = handle.read(min(BLOCK_SIZE, remaining))
                if not block:
                    raise PngWitnessError(
                        f"truncated_chunk_data: kind={kind!r} remaining={remaining}")
                digest.update(block)
                crc = zlib.crc32(block, crc)
                physical_offset += len(block)
                remaining -= len(block)
                if not is_xmp_container:
                    scanner.feed(block)

            crc_bytes = _read_exact(handle, 4)
            digest.update(crc_bytes)
            physical_offset += 4
            declared_crc = struct.unpack(">I", crc_bytes)[0]
            if (crc & 0xFFFFFFFF) != declared_crc:
                raise PngWitnessError(
                    f"crc_mismatch: kind={kind.decode('latin1')!r}")

            if kind == b"IEND":
                if length != 0:
                    raise PngWitnessError("IEND_has_data")
                iend_seen = True

        # Bytes after IEND are outside the declared PNG chunk vocabulary.  We
        # still hash and inspect them instead of silently dropping them.
        trailing_bytes, physical_offset = _feed_trailing(
            handle, digest=digest, scanner=scanner, offset=physical_offset)

    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise PngWitnessError("file_changed_during_scan")

    return {
        "path": str(path),
        "size": before.st_size,
        "mtime_ns": before.st_mtime_ns,
        "sha256": digest.hexdigest(),
        "chunks": chunks,
        "xmp_containers": xmp_containers,
        "outside_markers": sorted(scanner.hits),
        "trailing_bytes": trailing_bytes,
        "bytes_read": physical_offset,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_state() -> dict[str, Any]:
    # `run` used to fold a FAILED git call (not a repo, git missing, timeout)
    # into the same empty string as "clean, no output" -- so `tree_dirty` read
    # False and `commit` read "" for a check that never ran, indistinguishable
    # from a genuinely clean tree. Same family as `flujo doctor` reporting
    # `airdrop pendiente: OK` by testing a directory that did not exist.
    def run(*args: str) -> tuple[str, bool]:
        try:
            out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                 text=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            return "", False
        return out.stdout.strip(), out.returncode == 0

    dirty, dirty_ok = run("status", "--porcelain=v1")
    commit, commit_ok = run("rev-parse", "HEAD")
    branch, branch_ok = run("rev-parse", "--abbrev-ref", "HEAD")
    available = dirty_ok and commit_ok and branch_ok
    return {
        "commit": commit,
        "branch": branch,
        "available": available,
        # None (not False) when unavailable: an unmeasured tree must not be
        # reported as a clean one.
        "tree_dirty": bool(dirty) if available else None,
        "dirty_paths": dirty.splitlines()[:20] if available else [],
    }


def _candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            if Path(name).suffix.lower() in PNG_EXTENSIONS:
                paths.append(Path(current) / name)
    return sorted(paths, key=lambda item: str(item.relative_to(root)))


def _stable_digest(record: dict[str, Any]) -> str:
    comparable = {key: value for key, value in record.items()
                  if key not in {"started_at", "finished_at", "elapsed_seconds",
                                 "output_sha256"}}
    return hashlib.sha256(json.dumps(
        comparable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(root: Path, *, limit: int | None = None,
        argv: list[str] | None = None) -> dict[str, Any]:
    """Run the witness and return its complete report before serialization."""
    started = time.time()
    candidates = _candidates(root)
    if limit is not None:
        candidates = candidates[:limit]
    files: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    outside_hits: list[dict[str, Any]] = []
    for path in candidates:
        relative = str(path.relative_to(root))
        try:
            row = scan_png(path)
            row["path"] = relative
            files.append(row)
            if row["outside_markers"]:
                outside_hits.append({
                    "path": relative,
                    "markers": row["outside_markers"],
                })
        except (OSError, PngWitnessError) as exc:
            errors.append({"path": relative, "error": str(exc)})

    valid = len(files)
    eligible = bool(candidates) and valid == len(candidates) and not errors \
        and not outside_hits
    report: dict[str, Any] = {
        "contract": CONTRACT,
        "started_at": _now(),
        "command": argv or [],
        "git": _git_state(),
        "root": str(root.resolve()),
        "spec_citation": SPEC_CITATION,
        "adversarial_rule": ADVERSARIAL_RULE,
        "candidate_count": len(candidates),
        "files_checked": valid,
        "valid_png_files": valid,
        "error_count": len(errors),
        "errors": errors,
        "outside_marker_file_count": len(outside_hits),
        "outside_marker_hits": outside_hits,
        "xmp_container_file_count": sum(1 for row in files
                                         if row["xmp_containers"]),
        "xmp_container_count": sum(row["xmp_containers"] for row in files),
        "eligible_for_witness": eligible,
        "files": files,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    report["output_sha256"] = _stable_digest(report)
    report["finished_at"] = _now()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"error: root_not_a_directory: {args.root}", file=sys.stderr)
        return 2
    report = run(args.root, limit=args.limit,
                 argv=["png_xmp_witness.py", *(argv or sys.argv[1:])])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "candidate_count": report["candidate_count"],
        "files_checked": report["files_checked"],
        "errors": report["error_count"],
        "outside_marker_files": report["outside_marker_file_count"],
        "xmp_container_files": report["xmp_container_file_count"],
        "eligible_for_witness": report["eligible_for_witness"],
        "output_sha256": report["output_sha256"],
    }, indent=1))
    return 0 if report["eligible_for_witness"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
