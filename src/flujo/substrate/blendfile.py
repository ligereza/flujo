"""Read what a .blend file declares it opens, without running Blender.

WHY THIS EXISTS

774 of the 917 project rows in the archive index are ``dimensionality='3d'``,
and the identity substrate had never opened a single one of the 928 ``.blend``
files on the disk. The evidence supply and the consumer's population were nearly
disjoint.

Colocation cannot substitute for reading. Measured on this corpus: only 6 of 801
directories containing a ``.blend`` also contain the ``.exr`` or ``.vdb`` that
belong to it. A 3D dependency is not recoverable from the filesystem layout. The
file has to be opened.

Blender is never launched. That is a hard constraint here, and it is also the
right design: launching an application to learn what it references makes the
answer depend on that application's version, its addons and its ability to find
the files -- three things that change the answer without changing the file.

WHAT AUTHORITY THIS HAS

Bounded, and the bound is declared rather than implied.

  * A path found IS declared by the file. That is a positive with real weight.
  * A path NOT found may still exist. Blender stores references in places this
    reader does not model: node groups, library overrides, linked scenes,
    drivers, and packed data with no path at all. ``vocabulary`` is therefore NO,
    which by the rule in ``epistemics`` means a negative from this reader is
    NOT evidence of absence.

That is the same failure mode as the QuickTime ``XMP_`` atom, and the field that
records it exists precisely because that one was silent.

FORMAT

A 12 byte header -- ``BLENDER`` then a pointer-size char (``_``=4, ``-``=8) then
an endianness char (``v``=little, ``V``=big) then three version chars -- followed
by file-blocks: a 4 byte code, a 4 byte length, an old pointer, an SDNA index, a
count, and a body. ``ENDB`` terminates.

Measured on a 400 file sample of this corpus: 204 are zstd compressed, 30 gzip,
131 plain, and 8 carry a header this reader rejects. Both compressions are
handled; the 8 are reported as DECODER_LIMIT rather than as files without
dependencies, because those two are not the same claim.
"""

from __future__ import annotations

import gzip
import io
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .epistemics import (
    Completeness,
    DECODER_LIMIT,
    NO,
    UNASSESSED,
    YES,
)

CONTRACT = "mak-blendfile-v1"

BLENDER_MAGIC = b"BLENDER"
GZIP_MAGIC = b"\x1f\x8b"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

# Decompressed size ceiling. A cap that is hit must be reported, never silently
# truncated into "this file declares nothing".
MAX_DECOMPRESSED = 768 << 20
MAX_BLOCKS = 4_000_000

# Block codes whose bodies are known to carry external file references. Kept as
# data so a missing one is visible. Bodies of every other code are also scanned,
# because Blender puts many paths in generic DATA blocks belonging to an ID.
PATH_BEARING_CODES = {
    b"LI\0\0": "library",        # a linked .blend
    b"IM\0\0": "image",          # a texture or a rendered frame
    b"SO\0\0": "sound",
    b"MC\0\0": "movieclip",
    b"CF\0\0": "cachefile",      # alembic / usd
    b"VF\0\0": "vfont",
    b"SC\0\0": "scene",          # carries the render output path
    b"GLOB": "global",           # the blend's own path when it was saved
}

# A path, as Blender writes it. "//" is Blender's own marker for "relative to
# this .blend", which is why it is the strongest single signal available here.
_PATH = re.compile(
    rb"(?://|/|[A-Za-z]:[\\/])[^\x00-\x1f\x7f]{2,1023}")

# Preview thumbnails. Their bodies are raw pixel rows, and pixel rows match any
# byte-level path pattern by accident: a first pass reported 278 "declared
# paths" for a carpet model, all of them image data from TEST blocks. Excluded
# by block code, which is exact, rather than by filtering the strings later.
NON_PATH_CODES = {b"TEST"}

# A run of letters or digits. A real path has one; a row of pixels does not.
_WORD = re.compile(rb"[A-Za-z0-9]{2,}")
_MEDIA_HINT = re.compile(
    rb"\.(?:blend|exr|png|jpe?g|tga|tif{1,2}|hdr|vdb|abc|usd[acz]?|fbx|obj|"
    rb"mp4|mov|wav|mp3|ttf|otf|bphys|uni|dpx|cin|psd|webp|sbsar)\b",
    re.IGNORECASE)


class BlendError(Exception):
    """This reader could not model the file. DECODER_LIMIT, not "no deps"."""


@dataclass(frozen=True)
class BlendHeader:
    pointer_size: int
    little_endian: bool
    version: str
    compression: str            # "none" | "gzip" | "zstd"


@dataclass
class BlendReferences:
    path: str
    header: BlendHeader | None = None
    declared: list[dict[str, Any]] = field(default_factory=list)
    blocks_seen: int = 0
    truncated: bool = False
    error: str = ""
    decoder: str = ""

    @property
    def completeness(self) -> Completeness:
        return Completeness(
            # Traversal is YES only when ENDB was reached with no cap hit.
            traversal=YES if (not self.truncated and not self.error) else NO,
            # Never YES. See the module docstring: node groups, overrides and
            # linked scenes are not modelled, so a miss proves nothing.
            vocabulary=NO,
            authority=UNASSESSED,
            corpus=UNASSESSED,
            semantic=NO,
            note="a declared path is evidence; a missing path is not evidence "
                 "of absence for this reader",
        )

    @property
    def unknown_cause(self) -> str | None:
        return DECODER_LIMIT if self.error else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "path": self.path,
            "version": self.header.version if self.header else None,
            "pointer_size": self.header.pointer_size if self.header else None,
            "compression": self.header.compression if self.header else None,
            "declared": self.declared,
            "declared_count": len(self.declared),
            "blocks_seen": self.blocks_seen,
            "truncated": self.truncated,
            "error": self.error,
            "decoder": self.decoder,
            "completeness": self.completeness.as_dict(),
            "unknown_cause": self.unknown_cause,
        }


def _zstd_available() -> str:
    return shutil.which("zstd") or ""


def decompress(path: Path) -> tuple[bytes, str, str]:
    """Return (payload, compression, decoder_note).

    The decoder used is returned because a system binary's version changes the
    result, and a result whose decoder is unrecorded is not reproducible.
    """
    with path.open("rb") as handle:
        magic = handle.read(4)
    if magic[:2] == GZIP_MAGIC:
        with gzip.open(path, "rb") as stream:
            return stream.read(MAX_DECOMPRESSED + 1), "gzip", "python:gzip"
    if magic == ZSTD_MAGIC:
        binary = _zstd_available()
        if not binary:
            raise BlendError("zstd_compressed_and_no_decoder_available")
        out = subprocess.run([binary, "-d", "-c", "--long=31", str(path)],
                             capture_output=True, timeout=300)
        if out.returncode != 0:
            raise BlendError(f"zstd_failed:{out.stderr[:80].decode('ascii', 'replace')}")
        version = subprocess.run([binary, "--version"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
        return out.stdout, "zstd", f"system:{version[:60]}"
    return path.read_bytes(), "none", "python:raw"


def parse_header(payload: bytes) -> BlendHeader:
    if len(payload) < 12 or payload[:7] != BLENDER_MAGIC:
        raise BlendError("not_a_blend_header")
    pointer_char = payload[7:8]
    endian_char = payload[8:9]
    if pointer_char not in (b"_", b"-"):
        raise BlendError(f"bad_pointer_size_char:{pointer_char!r}")
    if endian_char not in (b"v", b"V"):
        raise BlendError(f"bad_endian_char:{endian_char!r}")
    return BlendHeader(
        pointer_size=4 if pointer_char == b"_" else 8,
        little_endian=endian_char == b"v",
        version=payload[9:12].decode("ascii", "replace"),
        compression="none",
    )


def iter_blocks(payload: bytes, header: BlendHeader
                ) -> Iterator[tuple[bytes, bytes]]:
    """Yield (code, body) for each file-block. Raises on a malformed chain."""
    order = "<" if header.little_endian else ">"
    size_fmt = order + "i"
    offset = 12
    total = len(payload)
    blocks = 0
    while offset + 12 + header.pointer_size <= total:
        code = payload[offset:offset + 4]
        (length,) = struct.unpack_from(size_fmt, payload, offset + 4)
        if length < 0:
            raise BlendError(f"negative_block_length_at_{offset}")
        body_start = offset + 8 + header.pointer_size + 8
        body_end = body_start + length
        if body_end > total:
            raise BlendError(f"block_overruns_payload_at_{offset}")
        if code == b"ENDB":
            return
        yield code, payload[body_start:body_end]
        offset = body_end
        blocks += 1
        if blocks > MAX_BLOCKS:
            raise BlendError("block_cap_exceeded")
    raise BlendError("payload_ended_without_ENDB")


def _paths_in(body: bytes) -> list[bytes]:
    """Path-like strings, with three filters that pixel data cannot pass.

    Blender's "//" prefix alone is not sufficient evidence: image data contains
    it constantly. What binary noise does not survive is having to be valid
    UTF-8, having to contain a real word, and having to name a media extension
    or end as a directory.
    """
    found = []
    for match in _PATH.finditer(body):
        raw = match.group(0)
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not _WORD.search(raw):
            continue
        if _MEDIA_HINT.search(raw) or raw.endswith((b"/", b"\\")):
            found.append(raw)
    return found


def read_references(path: str | Path) -> BlendReferences:
    """Everything this .blend declares it opens. Blender is not launched."""
    target = Path(path)
    out = BlendReferences(path=str(target))
    try:
        payload, compression, decoder = decompress(target)
        out.decoder = decoder
        if len(payload) > MAX_DECOMPRESSED:
            out.truncated = True
            payload = payload[:MAX_DECOMPRESSED]
        header = parse_header(payload)
        out.header = BlendHeader(header.pointer_size, header.little_endian,
                                 header.version, compression)
    except (BlendError, OSError, EOFError,
            subprocess.SubprocessError) as error:
        out.error = str(error)[:160]
        return out

    seen: set[tuple[str, str]] = set()
    try:
        for code, body in iter_blocks(payload, out.header):
            out.blocks_seen += 1
            if code in NON_PATH_CODES:
                continue
            kind = PATH_BEARING_CODES.get(code, "data")
            for raw in _paths_in(body):
                text = raw.decode("utf-8", "replace")
                key = (kind, text)
                if key in seen:
                    continue
                seen.add(key)
                out.declared.append({
                    "kind": kind,
                    "block_code": code.rstrip(b"\0").decode("ascii", "replace"),
                    "declared_path": text,
                    # Blender's own marker for "next to this .blend".
                    "relative_to_blend": text.startswith("//"),
                })
    except BlendError as error:
        out.error = str(error)[:160]
        out.truncated = True
    return out
