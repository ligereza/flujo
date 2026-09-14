"""Read live-projection screen setups as first-class practice evidence.

A live performance leaves almost nothing behind: the show ends and the visuals
are gone.  What survives is the *configuration* — the projection surfaces, their
warp geometry, the canvas the operator built for that room.  That file is
technical evidence of work performed at a place and time, and a generative tool
cannot produce a coherent one.

The reader identifies the producing application from the document's own
structure, never from its filename or extension.  A generic ``.xml`` becomes
evidence only because its root element declares the tool that wrote it.

**Known unreliability, declared up front.**  These files are routinely produced
by saving an existing setup under a new name for a new room.  A save-as carries
forward the previous document name *and* the embedded ids of screens that were
kept.  Therefore:

- the declared name may be stale and is never identity;
- the embedded timestamps date *a configuration*, and a re-save may carry
  timestamps that predate this file's actual use;
- a divergence between declared name and filename is evidence of a save-as, not
  evidence of a relation between two shows.

Everything here is read-only.  The setup is evidence of a *configuration*, never
of authorship of the visuals played through it, and never of who operated it.
"""

from __future__ import annotations

import datetime
import hashlib
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .product_view import stable_json


SCHEMA = "mak-screen-setup-evidence-v1"
ALGORITHM_VERSION = "screen-setup-evidence-1"

# Application signatures, keyed by the root element the tool writes.  Adding a
# tool is data-shaped: a new entry, never a new code path.
_SIGNATURES: tuple[dict[str, Any], ...] = (
    {
        "tool": "Resolume Arena",
        "root_tag": "XmlState",
        "version_path": ".//versionInfo",
        "version_name_attr": "name",
        "canvas_path": ".//CurrentCompositionTextureSize",
        "screen_tag": "Screen",
        "slice_tag": "Slice",
        "output_tag": "OutputDevice",
        "warper_tag": "BezierWarper",
        "id_attr": "uniqueId",
        "kind": "live_projection_screen_setup",
    },
)

# uniqueId values in these documents are millisecond epochs.  Bound them so a
# random large integer is never read as a date.
_MIN_EPOCH_MS = 1_000_000_000_000   # 2001-09
_MAX_EPOCH_MS = 2_000_000_000_000   # 2033-05
_MAX_SCREEN_NAMES = 8


class ScreenSetupEvidenceError(ValueError):
    """The document cannot be read as a screen setup."""


def _epoch_day(value: Any) -> str | None:
    try:
        milliseconds = int(str(value))
    except (TypeError, ValueError):
        return None
    if not _MIN_EPOCH_MS <= milliseconds <= _MAX_EPOCH_MS:
        return None
    return datetime.datetime.fromtimestamp(
        milliseconds / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")


def _match_signature(root: ElementTree.Element) -> dict[str, Any] | None:
    for signature in _SIGNATURES:
        if root.tag != signature["root_tag"]:
            continue
        version = root.find(signature["version_path"])
        if version is None:
            continue
        declared = str(version.get(signature["version_name_attr"]) or "")
        if declared.strip() == signature["tool"]:
            return signature
    return None


def read_screen_setup(path: str | Path) -> dict[str, Any] | None:
    """Read one screen setup, or return None if the file is not one.

    Returning None rather than raising is deliberate: most ``.xml`` files in an
    archive are something else, and that is not an error.
    """
    source = Path(path)
    if not source.is_file():
        return None
    try:
        root = ElementTree.parse(source).getroot()
    except (ElementTree.ParseError, OSError, ValueError):
        return None
    signature = _match_signature(root)
    if signature is None:
        return None

    version = root.find(signature["version_path"])
    canvas = root.find(signature["canvas_path"])
    screens = root.findall(f".//{signature['screen_tag']}")
    slices = root.findall(f".//{signature['slice_tag']}")
    outputs = root.findall(f".//{signature['output_tag']}")
    warpers = root.findall(f".//{signature['warper_tag']}")

    days = sorted({
        day
        for element in root.iter()
        for key, value in element.attrib.items()
        if key == signature["id_attr"] and (day := _epoch_day(value))
    })
    screen_names = [
        str(element.get("name")).strip()
        for element in screens
        if str(element.get("name") or "").strip()
    ]
    width = int(canvas.get("width") or 0) if canvas is not None else 0
    height = int(canvas.get("height") or 0) if canvas is not None else 0

    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "source_ref": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_bytes": source.stat().st_size,
        "kind": signature["kind"],
        "tool": signature["tool"],
        "tool_version": ".".join(
            str(version.get(part) or "0")
            for part in ("majorVersion", "minorVersion", "microVersion")
        ) if version is not None else "",
        "tool_revision": str(version.get("revision") or "") if version is not None else "",
        # The document's own name may differ from its filename.  Both are kept:
        # the divergence is itself evidence, and neither is a work title.
        "declared_name": str(root.get("name") or "").strip(),
        "file_stem": source.stem,
        "name_matches_filename": str(root.get("name") or "").strip() == source.stem,
        "label_reliability": (
            "no_declared_name" if not str(root.get("name") or "").strip()
            else "matches_filename"
            if str(root.get("name") or "").strip() == source.stem
            else "stale_label_from_save_as"
        ),
        "canvas_width": width,
        "canvas_height": height,
        "canvas": f"{width}x{height}" if width and height else "",
        "aspect": round(width / height, 3) if width and height else None,
        "screen_count": len(screens),
        "slice_count": len(slices),
        "output_device_count": len(outputs),
        "warped_slice_count": len(warpers),
        "screen_names": screen_names[:_MAX_SCREEN_NAMES],
        "internal_days": days,
        # Named for what they are: the days on which *some* configuration in this
        # document was created.  A save-as inherits ids, so the earliest day may
        # belong to a mapping made for an earlier room.
        "earliest_configured_day": days[0] if days else None,
        "latest_configured_day": days[-1] if days else None,
        "configured_day_count": len(days),
        "dating_reliability": (
            "single_route_may_predate_this_file"
            if str(root.get("name") or "").strip() != source.stem
            else "single_route_internal"
        ),
        "limits": [
            "A screen setup proves a configuration, not authorship of the visuals.",
            "It does not prove who operated the show.",
            "The declared name is the document's own label, not a work title.",
            "A save-as carries the previous name and the ids of kept screens, so "
            "neither the label nor the earliest embedded day is a reliable date "
            "for this file's own use.",
        ],
    }


def scan_screen_setups(
    root: str | Path, *, patterns: Sequence[str] = ("*.xml",), max_files: int = 500,
) -> dict[str, Any]:
    """Scan one directory level for screen setups, read-only and bounded."""
    directory = Path(root).expanduser()
    if not directory.is_dir():
        raise ScreenSetupEvidenceError(f"scan_root_missing:{directory}")
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(sorted(directory.glob(pattern)))
    setups: list[dict[str, Any]] = []
    skipped = 0
    for candidate in sorted(set(candidates))[:max_files]:
        if candidate.name.startswith("._"):
            skipped += 1
            continue
        setup = read_screen_setup(candidate)
        if setup is None:
            skipped += 1
            continue
        setups.append(setup)
    setups.sort(key=lambda row: row["source_ref"])
    result = {
        "schema": "mak-screen-setup-scan-v1",
        "algorithm_version": ALGORITHM_VERSION,
        "scan_root": str(directory),
        "candidate_count": len(set(candidates)),
        "setup_count": len(setups),
        "skipped_count": skipped,
        "tools": sorted({row["tool"] for row in setups}),
        "canvases": sorted({row["canvas"] for row in setups if row["canvas"]}),
        "total_slices": sum(row["slice_count"] for row in setups),
        "total_screens": sum(row["screen_count"] for row in setups),
        "configured_day_span": [
            min((row["earliest_configured_day"] for row in setups
                 if row["earliest_configured_day"]), default=None),
            max((row["latest_configured_day"] for row in setups
                 if row["latest_configured_day"]), default=None),
        ],
        "label_reliability_counts": {
            key: sum(1 for row in setups if row["label_reliability"] == key)
            for key in ("matches_filename", "stale_label_from_save_as", "no_declared_name")
        },
        "setups": setups,
        "control": {
            "source_rescan": False,
            "physical_mutation": False,
            "database_write": False,
            "network_called": False,
            "read_only": True,
        },
    }
    result["scan_hash"] = "sha256:" + hashlib.sha256(
        stable_json(result).encode("utf-8")).hexdigest()
    return result


def derived_variant_groups(scan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Group setups that are variants of one mapping, by content not by name.

    Two documents that declare the same name, the same internal day range and
    the same slice count are one mapping saved twice — typically re-canvased for
    a different room or re-saved under a newer tool version.  This is a version
    relation established from content; it is not a claim that two shows are the
    same show.
    """
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    for setup in scan.get("setups", []):
        if not setup.get("declared_name") or not setup.get("earliest_configured_day"):
            continue
        key = (
            str(setup["declared_name"]),
            str(setup["earliest_configured_day"]),
            str(setup["latest_configured_day"]),
            int(setup["slice_count"]),
        )
        grouped.setdefault(key, []).append(setup)
    groups: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        if len(rows) < 2:
            continue
        groups.append({
            "declared_name": key[0],
            "internal_day_span": [key[1], key[2]],
            "slice_count": key[3],
            "member_count": len(rows),
            "members": [
                {
                    "source_ref": row["source_ref"],
                    "file_stem": row["file_stem"],
                    "canvas": row["canvas"],
                    "tool_version": row["tool_version"],
                    "tool_revision": row["tool_revision"],
                }
                for row in sorted(rows, key=lambda item: item["source_ref"])
            ],
            "relation": "same_mapping_recanvased_or_resaved",
            "status": "candidate",
            "most_likely_reading": (
                "one of these is a save-as of the other, with the document name and the "
                "kept screen ids carried forward unchanged"
            ),
            "evidence_for": [
                "identical declared name inside the document",
                "identical embedded day range",
                "identical slice count",
            ],
            "evidence_against": [
                "a save-as inherits the name and the ids, so the match may be an artifact "
                "of re-saving rather than a shared mapping in use",
                "the canvas geometry differs, so the rooms are probably different",
                "the tool version differs, so one is a later re-save",
                "a shared mapping never makes two shows the same show",
                "the label may simply never have been updated",
            ],
            "does_not_establish": [
                "that both files were used at the same venue",
                "that either file dates from its embedded days",
                "any commission, work or authorship relation",
            ],
            "distinct_canvases": sorted({row["canvas"] for row in rows if row["canvas"]}),
            "distinct_tool_versions": sorted({row["tool_version"] for row in rows}),
            "selection_effect": "none",
        })
    return groups


__all__ = [
    "ALGORITHM_VERSION", "SCHEMA", "ScreenSetupEvidenceError",
    "derived_variant_groups", "read_screen_setup", "scan_screen_setups",
]
