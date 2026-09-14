"""Attack the .blend reader: a miss must never read as an absence.

Each test fails if a specific confusion is reintroduced:

- a file this reader cannot model must report DECODER_LIMIT, not "declares
  nothing". Those are different claims and only the second one is a lie.
- ``vocabulary`` must never be YES. Blender stores references in node groups,
  library overrides and linked scenes that this reader does not model, so a
  negative from it is not evidence of absence. This is the exact field whose
  absence hid the QuickTime XMP failure for a whole scan.
- a preview thumbnail must yield zero paths. Its body is raw pixel rows, and a
  first version of the path regex reported 278 "declared paths" for a carpet
  model, every one of them image data.
- the same payload plain and gzipped must declare the same thing, or the
  compression is deciding the answer.
"""

from __future__ import annotations

import gzip
import struct
from pathlib import Path

import pytest

from flujo.substrate.blendfile import (
    BLENDER_MAGIC,
    BlendError,
    read_references,
)
from flujo.substrate.epistemics import DECODER_LIMIT, NO, YES


def block(code: bytes, body: bytes, *, pointer_size: int = 8) -> bytes:
    """One file-block: code, length, old pointer, SDNA index, count, body."""
    assert len(code) == 4
    return (code + struct.pack("<i", len(body)) + b"\0" * pointer_size
            + struct.pack("<ii", 0, 1) + body)


def build_blend(blocks: bytes, *, version: bytes = b"404") -> bytes:
    # BLENDER + pointer-size char + endianness char + 3 version chars.
    return BLENDER_MAGIC + b"-" + b"v" + version + blocks + block(b"ENDB", b"")


def _foreign_windows_path(name: str) -> str:
    """A Windows path built from parts, never written as a literal.

    The repo's privacy ratchet rejects any ``C:\\Users\\<name>`` literal in the
    tree, and it is right to: the real .blend files on the disk carry the
    ORIGINAL authors' account names -- three different strangers in the first
    five files sampled -- and a literal in the repo is how one of those ends up
    committed. The reader is tested against the shape, not against a name.
    """
    return "\\".join(("C:", "Users", "anon", "Desktop", name))


def field(text: str, size: int = 1024) -> bytes:
    """A NUL-padded char array, the way Blender stores a path."""
    raw = text.encode("utf-8")
    return raw + b"\0" * max(1, size - len(raw))


def test_declared_image_path_is_found(tmp_path: Path) -> None:
    target = tmp_path / "scene.blend"
    target.write_bytes(build_blend(
        block(b"IM\0\0", field("//textures/skin.png"))))
    result = read_references(target)
    assert result.error == ""
    paths = [d["declared_path"] for d in result.declared]
    assert "//textures/skin.png" in paths
    entry = next(d for d in result.declared if d["declared_path"].endswith("skin.png"))
    assert entry["kind"] == "image"
    # Blender's own marker for "next to this .blend" must be preserved: it is
    # the difference between a resolvable and an unresolvable reference.
    assert entry["relative_to_blend"] is True


def test_library_and_absolute_path_keep_their_kind(tmp_path: Path) -> None:
    target = tmp_path / "linked.blend"
    target.write_bytes(build_blend(
        block(b"LI\0\0", field("//../lib/rig.blend"))
        + block(b"GLOB", field(_foreign_windows_path("linked.blend")))))
    result = read_references(target)
    kinds = {d["kind"] for d in result.declared}
    assert "library" in kinds
    assert "global" in kinds
    absolute = next(d for d in result.declared if d["kind"] == "global")
    assert absolute["relative_to_blend"] is False


def test_thumbnail_block_declares_nothing(tmp_path: Path) -> None:
    # A preview block whose body is pixel rows. Byte-wise it is full of "//"
    # runs; none of them is a path.
    pixels = b"".join(bytes([0x2f, 0x2f, 0x2f, 0xff, i % 251, i % 239, i % 241])
                      for i in range(4000))
    target = tmp_path / "preview.blend"
    target.write_bytes(build_blend(block(b"TEST", pixels)))
    result = read_references(target)
    assert result.error == ""
    assert result.declared == []


def test_unreadable_header_is_decoder_limit_not_absence(tmp_path: Path) -> None:
    target = tmp_path / "not.blend"
    target.write_bytes(b"BLENDER17-01" + b"\0" * 64)
    result = read_references(target)
    # The distinction the whole module exists for.
    assert result.error
    assert result.unknown_cause == DECODER_LIMIT
    assert result.declared == []
    assert result.completeness.traversal == NO


def test_truncated_chain_is_reported_not_swallowed(tmp_path: Path) -> None:
    good = build_blend(block(b"IM\0\0", field("//textures/a.png")))
    target = tmp_path / "cut.blend"
    # Remove the ENDB terminator and part of the last block.
    target.write_bytes(good[:-6])
    result = read_references(target)
    assert result.truncated or result.error


def test_gzip_and_plain_declare_the_same(tmp_path: Path) -> None:
    payload = build_blend(block(b"IM\0\0", field("//tex/wall.jpg")))
    plain = tmp_path / "plain.blend"
    plain.write_bytes(payload)
    packed = tmp_path / "packed.blend"
    packed.write_bytes(gzip.compress(payload))
    a, b = read_references(plain), read_references(packed)
    assert a.error == "" and b.error == ""
    assert ([d["declared_path"] for d in a.declared]
            == [d["declared_path"] for d in b.declared])
    assert a.header.compression == "none"
    assert b.header.compression == "gzip"


def test_vocabulary_is_never_complete(tmp_path: Path) -> None:
    """The field that would have caught the .mov failure a scan earlier."""
    target = tmp_path / "any.blend"
    target.write_bytes(build_blend(block(b"IM\0\0", field("//t/a.png"))))
    completeness = read_references(target).completeness
    assert completeness.traversal == YES
    assert completeness.vocabulary == NO
    # Therefore: finding nothing in a .blend proves nothing about the .blend.
    assert completeness.negative_is_evidence is False
    assert "not known to be complete" in completeness.strongest_negative_claim


def test_a_path_without_a_word_is_not_a_path(tmp_path: Path) -> None:
    """Binary noise that happens to start with a slash."""
    target = tmp_path / "noise.blend"
    target.write_bytes(build_blend(block(b"DATA", b"//" + bytes(range(32, 127)) * 3)))
    result = read_references(target)
    # It may find nothing; what it must not do is claim a media file.
    assert all(".png" not in d["declared_path"] for d in result.declared)


def test_duplicate_declarations_collapse_per_kind(tmp_path: Path) -> None:
    same = field("//tex/repeat.png")
    target = tmp_path / "dupes.blend"
    target.write_bytes(build_blend(
        block(b"IM\0\0", same) + block(b"IM\0\0", same) + block(b"IM\0\0", same)))
    result = read_references(target)
    repeats = [d for d in result.declared
               if d["declared_path"] == "//tex/repeat.png" and d["kind"] == "image"]
    assert len(repeats) == 1
