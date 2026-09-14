from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from flujo.substrate.schema import RENDERS_TO, Substrate
from tools.render_output_edges import (
    DEFAULT_NO_INFO,
    DriveRoot,
    RESOLVED_VERDICT,
    build_evidence,
    classify_scene_path,
    main,
)


def _block(code: bytes, body: bytes, *, pointer_size: int = 8) -> bytes:
    return (code + struct.pack("<i", len(body)) + b"\0" * pointer_size
            + struct.pack("<ii", 0, 1) + body)


def _blend(*blocks: bytes) -> bytes:
    return (b"BLENDER-v404" + b"".join(blocks)
            + _block(b"ENDB", b""))


def _field(value: str, size: int = 1024) -> bytes:
    raw = value.encode("utf-8")
    return raw + b"\0" * max(1, size - len(raw))


def test_default_output_path_carries_no_location_information(tmp_path: Path):
    result = classify_scene_path(
        "/tmp\\", blend_path=tmp_path / "scene.blend", scan_root=tmp_path,
        drive_map={"C": DriveRoot("C", True, "fixture")})

    assert result.verdict == DEFAULT_NO_INFO
    assert result.path is None


def test_resolved_directory_is_classified_without_selecting_a_file(tmp_path: Path):
    output = tmp_path / "renders"
    output.mkdir()
    (output / "frame.png").write_bytes(b"png")
    blend = tmp_path / "scene.blend"

    result = classify_scene_path(
        "C:\\renders\\", blend_path=blend, scan_root=tmp_path,
        drive_map={"C": DriveRoot("C", True, "fixture")})

    assert result.verdict == RESOLVED_VERDICT
    assert result.path == str(output)


def test_evidence_object_is_directory_and_keeps_candidate_cardinality(tmp_path: Path):
    evidence = build_evidence(
        root_id="fixture", relative_path="scene.blend", ordinal=0,
        resolved_path=str(tmp_path / "renders"), candidate_count_value=3,
        suspect=False, recorded_at="2026-08-24T00:00:00+00:00")

    assert evidence.predicate == RENDERS_TO
    assert evidence.object == f"basename:{tmp_path / 'renders'}"
    assert evidence.candidate_count == 3
    assert "candidate file(s)" in evidence.detail
    assert "frame" not in evidence.object


def test_cli_writes_only_directory_edge_to_the_requested_sidecar(tmp_path: Path):
    root = tmp_path / "disk"
    output = root / "renders"
    output.mkdir(parents=True)
    (output / "frame.png").write_bytes(b"png")
    (root / "scene.blend").write_bytes(
        _blend(_block(b"SC\0\0", _field("C:\\renders\\"))))
    sidecar = tmp_path / "evidence.db"
    report = tmp_path / "report.json"

    assert main(["--root", str(root), "--out", str(sidecar),
                 "--report", str(report)]) == 0

    edges = Substrate(sidecar).edges(predicate=RENDERS_TO)
    assert len(edges) == 1
    assert edges[0]["object"] == f"basename:{output}"
    assert edges[0]["candidate_count"] == 1
    assert "frame.png" not in edges[0]["object"]


def test_cli_does_not_persist_a_suspect_non_image_directory(tmp_path: Path):
    root = tmp_path / "disk"
    output = root / "working"
    output.mkdir(parents=True)
    (output / "scene.blend").write_bytes(b"blend")
    (root / "scene.blend").write_bytes(
        _blend(_block(b"SC\0\0", _field("C:\\working\\"))))
    sidecar = tmp_path / "evidence.db"
    report = tmp_path / "report.json"

    assert main(["--root", str(root), "--out", str(sidecar),
                 "--report", str(report)]) == 0

    assert Substrate(sidecar).edges(predicate=RENDERS_TO) == []
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["result"]["suspect_resolved_count"] == 1
    assert payload["result"]["evidence_written"] == 0


def test_help_does_not_create_a_path_named_help(tmp_path: Path):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])

    assert caught.value.code == 0
    assert not (tmp_path / "--help").exists()
