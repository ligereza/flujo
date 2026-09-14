"""Read declared footage paths from an After Effects ``.aep`` file.

This is a bounded, read-only reader for the RIFX/Egg container used by the
After Effects projects in the MAK corpus. It scans the complete bytes of the
container for the structured ``fullpath`` records that After Effects stores for
footage and other project references. It does not open After Effects, render,
resolve a path to one filesystem file, or infer which file was delivered.

The scan is deliberately lexical rather than a claim to understand every
private After Effects chunk. Real files contain valid trailing bytes after the
size in the RIFX header and place records in chunk layouts a generic recursive
walker cannot model. We therefore record byte offsets and header accounting,
and reserve ``DECODER_LIMIT`` for an invalid header, a genuinely short file,
or the explicit size bound.

A declared ``fullpath`` is therefore evidence of a project reference. It is
not evidence of ``project -> output file`` and never emits ``RENDERS_TO`` by
itself. That distinction is intentional: a project folder can contain videos
as inputs, previews, working material, or deliverables, and the extension does
not decide which one it is.
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .epistemics import DECODER_LIMIT

CONTRACT = "mak-aepfile-v1"
MAGIC = b"RIFX"
FORM = b"Egg!"
MAX_BYTES = 512 << 20
EXHAUSTIVE = "exhaustive"

# The record vocabulary is stable across the sampled files. Keep the parser
# narrow: an arbitrary printable string is not silently promoted to a path.
FULLPATH = re.compile(rb'"fullpath"\s*:\s*"((?:\\.|[^"\\])*)"')
TARGET_IS_FOLDER = re.compile(rb'"target_is_folder"\s*:\s*(true|false)')
PLATFORM = re.compile(rb'"platform"\s*:\s*(-?\d+)')
SERVER_NAME = re.compile(rb'"server_name"\s*:\s*"((?:\\.|[^"\\])*)"')
SERVER_VOLUME = re.compile(rb'"server_volume_name"\s*:\s*"((?:\\.|[^"\\])*)"')


class AepError(ValueError):
    """The file is not a readable RIFX/Egg project within the bound."""


@dataclass(frozen=True)
class AepHeader:
    declared_size: int
    form: str
    trailing_bytes: int = 0


@dataclass
class AepReferences:
    path: str
    header: AepHeader | None = None
    declared: list[dict[str, Any]] = field(default_factory=list)
    chunks_seen: int = 0
    truncated: bool = False
    error: str = ""

    @property
    def completeness(self) -> str:
        return DECODER_LIMIT if self.error or self.truncated else EXHAUSTIVE


def _decode_json_string(raw: bytes, *, allow_empty: bool = False) -> str:
    """Decode one JSON-escaped string captured from the binary payload."""
    try:
        value = json.loads((b'"' + raw + b'"').decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AepError(f"invalid_fullpath_encoding: {exc}") from exc
    if not isinstance(value, str) or (not allow_empty and not value):
        raise AepError("fullpath_is_not_a_string")
    return value


def _count_top_level_chunks(blob: bytes, start: int, end: int) -> int:
    """Count bounded top-level chunks without interpreting private payloads."""
    offset = start
    seen = 0
    while offset < end:
        if offset + 8 > end:
            break
        size = struct.unpack(">I", blob[offset + 4:offset + 8])[0]
        body_start = offset + 8
        body_end = body_start + size
        seen += 1
        if body_end > end:
            break
        offset = body_end + (size & 1)
    return seen


def _extract_records(payload: bytes, base_offset: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for match in FULLPATH.finditer(payload):
        raw = match.group(1)
        try:
            fullpath = _decode_json_string(raw)
        except AepError:
            continue
        tail = payload[match.end():match.end() + 700]
        folder = TARGET_IS_FOLDER.search(tail)
        platform = PLATFORM.search(tail)
        server = SERVER_NAME.search(tail)
        volume = SERVER_VOLUME.search(tail)
        record: dict[str, Any] = {
            "kind": "after_effects_reference",
            "scan_method": "whole_file_structured_scan",
            "byte_offset": base_offset + match.start(),
            "declared_path": fullpath,
            "target_is_folder": (folder.group(1) == b"true") if folder else None,
            "platform": int(platform.group(1)) if platform else None,
        }
        if server:
            try:
                record["server_name"] = _decode_json_string(server.group(1), allow_empty=True)
            except AepError:
                pass
        if volume:
            try:
                record["server_volume_name"] = _decode_json_string(volume.group(1), allow_empty=True)
            except AepError:
                pass
        records.append(record)
    return records


def read_references(path: str | Path) -> AepReferences:
    """Read all structured ``fullpath`` declarations without launching AE."""
    target = Path(path)
    out = AepReferences(path=str(target))
    try:
        size = target.stat().st_size
        if size > MAX_BYTES:
            out.truncated = True
            raise AepError(f"file_exceeds_bound: {size}>{MAX_BYTES}")
        blob = target.read_bytes()
    except (OSError, AepError) as exc:
        out.error = str(exc)[:200]
        return out

    if len(blob) < 12 or blob[:4] != MAGIC:
        out.error = "invalid_rifx_header"
        return out
    declared_size = struct.unpack(">I", blob[4:8])[0]
    form = blob[8:12]
    declared_end = 8 + declared_size
    out.header = AepHeader(
        declared_size=declared_size,
        form=form.decode("ascii", "replace"),
        trailing_bytes=max(0, len(blob) - declared_end),
    )
    if form != FORM:
        out.error = f"unsupported_rifx_form: {form!r}"
        return out

    if declared_end > len(blob):
        out.truncated = True
    out.chunks_seen = _count_top_level_chunks(blob, 12, min(len(blob), declared_end))
    seen: set[tuple[str, str]] = set()
    for record in _extract_records(blob[12:], 12):
        key = (record["scan_method"], record["declared_path"])
        if key in seen:
            continue
        seen.add(key)
        out.declared.append(record)
    return out
