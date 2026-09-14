from __future__ import annotations

import json
import struct
from pathlib import Path

from flujo.substrate.aepfile import DECODER_LIMIT, EXHAUSTIVE, read_references


def _chunk(kind: bytes, payload: bytes) -> bytes:
    padding = b"\0" if len(payload) % 2 else b""
    return kind + struct.pack(">I", len(payload)) + payload + padding


def _aep(*chunks: bytes, declared_size: int | None = None) -> bytes:
    payload = b"".join(chunks)
    size = declared_size if declared_size is not None else 4 + len(payload)
    return b"RIFX" + struct.pack(">I", size) + b"Egg!" + payload


def test_read_references_extracts_nested_rifx_payload_and_preserves_metadata(tmp_path: Path):
    record = json.dumps({
        "fullpath": r"C:\RD\SHOW\clip.mp4",
        "platform": 1,
        "server_name": "ISKVW",
        "server_volume_name": "Windows",
        "target_is_folder": False,
    }).encode("utf-8")
    nested = _chunk(b"LIST", b"foot" + _chunk(b"data", record))
    path = tmp_path / "project.aep"
    path.write_bytes(_aep(nested))

    result = read_references(path)

    assert result.completeness == EXHAUSTIVE
    assert result.error == ""
    assert result.header and result.header.form == "Egg!"
    assert result.chunks_seen == 1
    assert result.declared == [{
        "kind": "after_effects_reference",
        "scan_method": "whole_file_structured_scan",
        "byte_offset": 33,
        "declared_path": r"C:\RD\SHOW\clip.mp4",
        "target_is_folder": False,
        "platform": 1,
        "server_name": "ISKVW",
        "server_volume_name": "Windows",
    }]


def test_invalid_and_truncated_files_are_not_reported_as_empty(tmp_path: Path):
    invalid = tmp_path / "invalid.aep"
    invalid.write_bytes(b"not-aep")
    assert read_references(invalid).completeness == DECODER_LIMIT
    assert read_references(invalid).error == "invalid_rifx_header"

    truncated = tmp_path / "truncated.aep"
    truncated.write_bytes(_aep(_chunk(b"data", b'{"fullpath":"C:\\\\x.mp4"}'), declared_size=9999))
    result = read_references(truncated)
    assert result.completeness == DECODER_LIMIT
    assert result.truncated is True


def test_declared_rifx_size_can_have_valid_trailing_bytes(tmp_path: Path):
    record = json.dumps({"fullpath": r"C:\RD\SHOW\trailing.mp4"}).encode()
    body = _chunk(b"data", record)
    path = tmp_path / "trailing.aep"
    path.write_bytes(_aep(body, declared_size=4 + len(body)) + b"ADOBE-TRAILER")

    result = read_references(path)

    assert result.completeness == EXHAUSTIVE
    assert result.truncated is False
    assert result.header and result.header.trailing_bytes == len(b"ADOBE-TRAILER")
    assert result.declared[0]["declared_path"] == r"C:\RD\SHOW\trailing.mp4"


def test_optional_empty_server_name_is_metadata_not_decoder_failure(tmp_path: Path):
    record = json.dumps({
        "fullpath": r"C:\RD\SHOW\clip.mp4",
        "server_name": "",
        "server_volume_name": "Windows",
    }).encode()
    path = tmp_path / "empty-server.aep"
    path.write_bytes(_aep(_chunk(b"data", record)))

    result = read_references(path)

    assert result.completeness == EXHAUSTIVE
    assert result.error == ""
    assert result.declared[0]["server_name"] == ""


def test_reader_does_not_emit_render_edges(tmp_path: Path):
    record = json.dumps({"fullpath": r"C:\RD\SHOW\output.mp4", "target_is_folder": False}).encode()
    path = tmp_path / "project.aep"
    path.write_bytes(_aep(_chunk(b"data", record)))
    result = read_references(path)
    assert result.declared[0]["kind"] == "after_effects_reference"
    assert "renders_to" not in result.declared[0]
