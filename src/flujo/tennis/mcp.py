"""Minimal, loss-aware parser for Tennis Abstract Match Charting notation.

The parser intentionally understands only a small declared subset. Raw rows,
unknown tokens and source hashes remain available to later curators; this
module never guesses a token or claims to reconstruct video/3D state.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SERVE_DIR = {"4": "wide", "5": "body", "6": "T"}
SHOT_TYPE = {"f": "forehand", "b": "backhand", "s": "backhand_slice", "r": "forehand_slice"}
SHOT_DIR = {"1": "to_receiver_forehand_side", "2": "middle", "3": "to_receiver_backhand_side"}
RETURN_DEPTH = {"7": "shallow_service_box", "8": "medium_deep", "9": "very_deep"}
POINT_END = {"*": "winner", "#": "forced_error", "@": "unforced_error"}
ERROR = {"n": "net", "w": "wide", "d": "deep", "x": "wide_and_deep"}


def parse_minimal(notation: str | None) -> dict[str, Any]:
    """Parse only explicitly known MCP symbols and preserve everything else."""
    raw = notation or ""
    index = 0
    output: dict[str, Any] = {
        "raw": raw,
        "serve_direction": None,
        "shots": [],
        "point_end": None,
        "unknown_tokens": [],
        "parser_version": "mcp-minimal-v0.1",
    }
    if index < len(raw) and raw[index] in SERVE_DIR:
        output["serve_direction"] = SERVE_DIR[raw[index]]
        index += 1
    while index < len(raw):
        token = raw[index]
        if token in POINT_END:
            output["point_end"] = {"type": POINT_END[token], "raw": token}
            index += 1
            continue
        if token in ERROR and index + 1 < len(raw) and raw[index + 1] in {"#", "@"}:
            output["point_end"] = {
                "type": POINT_END[raw[index + 1]],
                "error": ERROR[token],
                "raw": raw[index:index + 2],
            }
            index += 2
            continue
        if token in SHOT_TYPE:
            shot: dict[str, Any] = {"type": SHOT_TYPE[token], "raw": token, "direction": None, "return_depth": None}
            index += 1
            if index < len(raw) and raw[index] in SHOT_DIR:
                shot["direction"] = SHOT_DIR[raw[index]]
                shot["raw"] += raw[index]
                index += 1
            if index < len(raw) and raw[index] in RETURN_DEPTH:
                shot["return_depth"] = RETURN_DEPTH[raw[index]]
                shot["raw"] += raw[index]
                index += 1
            output["shots"].append(shot)
            continue
        output["unknown_tokens"].append({"index": index, "raw": token})
        index += 1
    return output


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_rows(source: str | Path) -> Iterable[dict[str, Any]]:
    """Yield annotated rows from a local MCP CSV without acquiring data."""
    path = Path(source).expanduser().resolve()
    source_hash = sha256_file(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            yield {
                "source_id": "SRC_MCP",
                "source_file": path.name,
                "source_sha256": source_hash,
                "source_row": row_number,
                "raw": dict(row),
                "parsed": {
                    "first_serve_sequence": parse_minimal(row.get("1st", "")),
                    "second_serve_sequence": parse_minimal(row.get("2nd", "")),
                },
                "epistemic_status": "ANNOTATED",
            }


def write_jsonl(source: str | Path, destination: str | Path) -> int:
    """Write a local, hash-linked JSONL projection and return row count."""
    count = 0
    with Path(destination).expanduser().open("w", encoding="utf-8") as output:
        for record in ingest_rows(source):
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
