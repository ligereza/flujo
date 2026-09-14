"""Deterministic contract for the Git, Windows, and MAK planes.

The manifest is a catalog of physical surfaces, not a migration command. It
records authority, ownership, provenance, explicit file evidence, and transport
gates without copying or moving any existing material.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Mapping

from ._io_helpers import sha256_file as _sha256_file


SCHEMA = "three-plane-local-surfaces-v1"
SURFACE_IDS = ("git_transport", "windows_director", "mak_operational")


class ManifestInputError(ValueError):
    """Raised when explicit manifest evidence cannot be read safely."""


_SURFACE_DEFINITIONS = {
    "git_transport": {
        "surface_id": "git_transport",
        "plane": "git_transport",
        "physical_node": "git",
        "surface_kind": "reviewed_projection",
        "authority_role": "projection_only",
        "owner": "reviewed_projection",
        "producer": "reviewed_gate",
        "root_uri": "git://flujo",
        "provenance": {
            "source_surface": "windows_director",
            "source_kind": "selected_reproducible_material",
            "status": "declared",
            "evidence_required": True,
        },
        "transport": {
            "eligibility": "reviewed_only",
            "direction": "windows_to_git",
            "mode": "projection",
            "human_gate_required": True,
            "material_moved": False,
        },
    },
    "windows_director": {
        "surface_id": "windows_director",
        "plane": "director_creative",
        "physical_node": "windows",
        "surface_kind": "director_workspace",
        "authority_role": "local_authority",
        "owner": "director",
        "producer": "director",
        "root_uri": "file:///C:/IA/flujo",
        "provenance": {
            "source_surface": None,
            "source_kind": "physical_local_material",
            "status": "declared",
            "evidence_required": True,
        },
        "transport": {
            "eligibility": "review_required",
            "direction": "windows_to_git",
            "mode": "selected_projection_only",
            "human_gate_required": True,
            "material_moved": False,
        },
    },
    "mak_operational": {
        "surface_id": "mak_operational",
        "plane": "operational_knowledge",
        "physical_node": "mak",
        "surface_kind": "operational_knowledge_store",
        "authority_role": "local_authority",
        "owner": "MAK",
        "producer": "MAK",
        "root_uri": "file:///home/mak",
        "provenance": {
            "source_surface": None,
            "source_kind": "physical_local_knowledge",
            "status": "declared",
            "evidence_required": True,
        },
        "transport": {
            "eligibility": "review_required",
            "direction": "mak_to_review_surface",
            "mode": "read_only_reference",
            "human_gate_required": True,
            "material_moved": False,
        },
    },
}


def _artifact_evidence(surface_id: str, paths: Iterable[str | Path]) -> dict:
    resolved = []
    for value in paths:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise ManifestInputError(f"explicit artifact is not a file: {path}")
        resolved.append(path)

    artifacts = []
    for index, path in enumerate(sorted(set(resolved), key=lambda item: item.as_posix()), start=1):
        artifacts.append(
            {
                "artifact_id": f"{surface_id}:artifact:{index:04d}",
                "uri": path.as_uri(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return {
        "algorithm": "sha256",
        "scope": "explicit_artifacts_only",
        "status": "complete" if artifacts else "not_computed",
        "artifacts": artifacts,
    }


def build_manifest(
    artifact_paths: Mapping[str, Iterable[str | Path]] | None = None,
) -> dict:
    """Build the three-plane manifest without changing any source surface.

    ``artifact_paths`` is intentionally explicit. Directories are never
    scanned, and omitted surfaces retain an explicit ``not_computed`` hash
    status rather than implying that their contents are empty or trusted.
    """

    supplied = artifact_paths or {}
    unknown = sorted(set(supplied) - set(SURFACE_IDS))
    if unknown:
        raise ManifestInputError("unknown surface ids: " + ", ".join(unknown))

    surfaces = []
    for surface_id in SURFACE_IDS:
        surface = dict(_SURFACE_DEFINITIONS[surface_id])
        surface["provenance"] = dict(surface["provenance"])
        surface["transport"] = dict(surface["transport"])
        surface["hashes"] = _artifact_evidence(surface_id, supplied.get(surface_id, ()))
        surfaces.append(surface)

    return {
        "schema": SCHEMA,
        "contract": {
            "authority_order": ["local_surfaces", "catalog", "git_projection"],
            "local_surfaces_are_authoritative": True,
            "git_is_runtime_authority": False,
            "bidirectional_sync": False,
            "primary_writer": "not_configured",
        },
        "materialization": {
            "status": "not_applied",
            "material_moved": False,
            "files_copied": 0,
            "writes_to_source_surfaces": False,
        },
        "surfaces": surfaces,
    }


def canonical_bytes(manifest: Mapping) -> bytes:
    """Return stable ASCII JSON bytes for storage or hashing."""

    return (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode(
        "ascii"
    )


def write_manifest(manifest: Mapping, output: str | Path) -> None:
    """Write a canonical manifest; this does not touch any source surface."""

    Path(output).write_bytes(canonical_bytes(manifest))


def _artifact_argument(value: str) -> tuple[str, Path]:
    surface_id, separator, path = value.partition("=")
    if not separator or not surface_id or not path:
        raise argparse.ArgumentTypeError("artifact must use SURFACE_ID=PATH")
    return surface_id, Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a read-only three-plane surface manifest")
    parser.add_argument("--output", type=Path, help="canonical ASCII JSON output path")
    parser.add_argument(
        "--artifact",
        action="append",
        type=_artifact_argument,
        default=[],
        metavar="SURFACE_ID=PATH",
        help="hash one explicit file as evidence; repeatable; never scans directories",
    )
    args = parser.parse_args(argv)
    evidence: dict[str, list[Path]] = {}
    for surface_id, path in args.artifact:
        evidence.setdefault(surface_id, []).append(path)
    manifest = build_manifest(evidence)
    if args.output:
        write_manifest(manifest, args.output)
    else:
        print(canonical_bytes(manifest).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
