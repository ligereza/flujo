#!/usr/bin/env python3
"""Read-only verification of the learning hash maps against the live MAK tree.

The old session helper was tied to ``/home/mak/flujo`` and only understood one
map shape.  This version treats ``/home/mak`` as the current root, accepts both
``source_hashes`` lists and ``source_refs`` dictionaries, and reports path-only
references separately instead of pretending they are hash evidence.

It never rewrites a map or a source.  A non-zero exit code is reserved for an
unreadable map; changed or absent sources are findings, not execution errors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ROOT = Path("/home/mak")
HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class Declaration:
    bundle: str
    location: str
    raw_path: str
    expected: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_objects(value: Any, location: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        yield location, value
        for key, child in value.items():
            child_location = f"{location}/{key}"
            yield from iter_objects(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_objects(child, f"{location}/{index}")


def declarations(bundle: Path, payload: Any) -> tuple[list[Declaration], int]:
    hashed: list[Declaration] = []
    path_only = 0
    for location, obj in iter_objects(payload):
        raw_path = obj.get("path")
        expected = obj.get("sha256")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        if isinstance(expected, str) and HASH_RE.fullmatch(expected):
            hashed.append(
                Declaration(str(bundle), location or "/", raw_path, expected.lower())
            )
        else:
            path_only += 1
    return hashed, path_only


def canonical_path(raw: str, root: Path) -> Path:
    """Resolve a declaration without following an old root blindly.

    ``flujo`` is a compatibility adapter in this installation.  Prefer the
    canonical root when the corresponding path exists there, while retaining
    the adapter path as a fallback for an old declaration whose replacement is
    genuinely absent.
    """
    candidate = Path(raw).expanduser()
    old_prefix = str(root / "flujo") + "/"
    if candidate.is_absolute():
        text = str(candidate)
        if text.startswith(old_prefix):
            canonical = root / text[len(old_prefix) :]
            if canonical.exists():
                return canonical
        return candidate
    direct = root / candidate
    if direct.exists():
        return direct
    adapter = root / "flujo" / candidate
    return adapter if adapter.exists() else direct


def verify(root: Path) -> dict[str, Any]:
    bundles = sorted(root.glob("docs/*_learning/*/hashmap.json"))
    all_declarations: list[Declaration] = []
    bundle_rows: list[dict[str, Any]] = []
    unreadable = 0
    for bundle in bundles:
        try:
            payload = json.loads(bundle.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            unreadable += 1
            bundle_rows.append({"bundle": str(bundle), "error": f"{type(exc).__name__}: {exc}"})
            continue
        found, path_only = declarations(bundle, payload)
        all_declarations.extend(found)
        bundle_rows.append(
            {
                "bundle": str(bundle),
                "hash_declarations": len(found),
                "path_only_references": path_only,
            }
        )

    # Verify every declaration, then collapse to canonical paths for a useful
    # answer about current evidence.  Multiple declarations can intentionally
    # disagree because a map was generated before a later edit.
    findings: list[dict[str, Any]] = []
    for declaration in all_declarations:
        target = canonical_path(declaration.raw_path, root)
        if not target.is_file():
            status = "ausente"
            actual = ""
        else:
            try:
                actual = sha256(target)
            except OSError as exc:
                status = "ilegible"
                actual = f"{type(exc).__name__}: {exc}"
            else:
                status = "igual" if actual == declaration.expected else "cambiado"
        findings.append(
            {
                **asdict(declaration),
                "canonical_path": str(target),
                "status": status,
                "actual": actual,
            }
        )

    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        by_path[finding["canonical_path"]].append(finding)
    unique_status: list[dict[str, Any]] = []
    for path, rows in sorted(by_path.items()):
        statuses = Counter(row["status"] for row in rows)
        if "ausente" in statuses:
            status = "ausente"
        elif "ilegible" in statuses:
            status = "ilegible"
        elif "igual" in statuses and "cambiado" not in statuses:
            status = "igual"
        elif "cambiado" in statuses and "igual" not in statuses:
            status = "cambiado"
        else:
            status = "mixto"
        unique_status.append(
            {"canonical_path": path, "status": status, "declarations": len(rows)}
        )

    return {
        "schema": "mak-learning-hashmap-verification-v1",
        "root": str(root),
        "bundles": bundle_rows,
        "summary": {
            "bundle_count": len(bundles),
            "unreadable_bundles": unreadable,
            "hash_declarations": len(findings),
            "unique_canonical_paths": len(unique_status),
            "declaration_status": dict(sorted(Counter(f["status"] for f in findings).items())),
            "unique_path_status": dict(sorted(Counter(f["status"] for f in unique_status).items())),
        },
        "unique_paths": unique_status,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    args = parser.parse_args()
    result = verify(args.root.expanduser().resolve())
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"root: {result['root']}")
        print(f"bundles: {result['summary']['bundle_count']}  hash declarations: {result['summary']['hash_declarations']}")
        print(f"declarations: {result['summary']['declaration_status']}")
        print(f"unique paths: {result['summary']['unique_path_status']}")
        for row in result["unique_paths"]:
            if row["status"] != "igual":
                print(f"{row['status']:<8} {row['canonical_path']} ({row['declarations']} declarations)")
    return 1 if result["summary"]["unreadable_bundles"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
