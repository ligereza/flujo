from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from flujo.knowledge.three_plane import (
    SCHEMA,
    ManifestInputError,
    build_manifest,
    write_manifest,
)


ROOT = Path(__file__).parents[1]


def _schema() -> dict:
    return json.loads(
        (ROOT / "schemas" / "knowledge" / "three_plane_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_manifest_declares_three_planes_and_no_materialization():
    first = build_manifest()
    second = build_manifest()

    assert first == second
    assert first["schema"] == SCHEMA
    assert first["materialization"] == {
        "status": "not_applied",
        "material_moved": False,
        "files_copied": 0,
        "writes_to_source_surfaces": False,
    }
    assert [item["surface_id"] for item in first["surfaces"]] == [
        "git_transport",
        "windows_director",
        "mak_operational",
    ]
    assert first["surfaces"][0]["authority_role"] == "projection_only"
    assert all(item["authority_role"] == "local_authority" for item in first["surfaces"][1:])
    assert all(item["transport"]["material_moved"] is False for item in first["surfaces"])
    assert all(item["hashes"]["status"] == "not_computed" for item in first["surfaces"])


def test_manifest_hashes_only_explicit_artifacts_and_is_order_independent(tmp_path: Path):
    first_path = tmp_path / "first.txt"
    second_path = tmp_path / "second.txt"
    first_path.write_bytes(b"alpha\n")
    second_path.write_bytes(b"beta\n")
    before = {path: path.read_bytes() for path in (first_path, second_path)}

    first = build_manifest(
        {"windows_director": [second_path, first_path, first_path]}
    )
    second = build_manifest(
        {"windows_director": [first_path, second_path]}
    )

    assert first == second
    evidence = first["surfaces"][1]["hashes"]
    assert evidence["status"] == "complete"
    assert [item["bytes"] for item in evidence["artifacts"]] == [6, 5]
    assert [item["sha256"] for item in evidence["artifacts"]] == [
        hashlib.sha256(b"alpha\n").hexdigest(),
        hashlib.sha256(b"beta\n").hexdigest(),
    ]
    assert {path: path.read_bytes() for path in (first_path, second_path)} == before


def test_manifest_is_canonical_ascii_and_schema_valid(tmp_path: Path):
    manifest = build_manifest()
    Draft202012Validator(_schema()).validate(manifest)
    output = tmp_path / "three_plane_manifest.json"
    write_manifest(manifest, output)
    first_bytes = output.read_bytes()
    write_manifest(build_manifest(), output)

    assert output.read_bytes() == first_bytes
    assert all(byte < 128 for byte in first_bytes)
    assert json.loads(first_bytes)["schema"] == SCHEMA


def test_unknown_or_missing_explicit_artifacts_fail_closed(tmp_path: Path):
    with pytest.raises(ManifestInputError, match="unknown surface"):
        build_manifest({"unknown": [tmp_path / "file.txt"]})
    with pytest.raises(ManifestInputError, match="not a file"):
        build_manifest({"windows_director": [tmp_path / "missing.txt"]})
