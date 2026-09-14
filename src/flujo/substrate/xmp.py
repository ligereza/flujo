"""Locate and parse XMP packets, declaring whether the search was exhaustive.

The first scan of this corpus used a bounded window -- the first 256 KB and the
last 128 KB of every file -- and found 1367 packets. That number is a lower
bound and nothing else: a miss proves nothing, because the packet may sit in the
middle of a large file. The PNG result made the gap obvious. 120 of 14345 PNGs
showed an ``<?xpacket`` marker inside the window while only 48 yielded a
DocumentID, which is the signature of a container format whose metadata chunk
does not live where a fixed window can see it.

So this module locates packets the way each format actually stores them:

- PNG   walks the chunk table for ``iTXt`` or legacy ``tEXt`` chunks keyed
        ``XML:com.adobe.xmp``, inflating iTXt when the compression flag is set
- JPEG  walks the marker segments for ``APP1`` carrying the Adobe XAP header
        (XMP spec part 3), including the Extended XMP header
- MP4   walks the box tree for the ``uuid`` box whose UUID is the one Adobe
  MOV   registered for XMP, descending into ``moov`` and ``udta``
- rest  reads the whole file when it is small enough, otherwise a window

and every result records WHICH method ran and whether it was exhaustive. A
negative from an exhaustive walk is evidence of absence. A negative from a
window is not, and the two must never be added together.

Nothing here decides a relation. It extracts fields and says how it found them.
"""

from __future__ import annotations

import os
import re
import struct
import zlib
from dataclasses import dataclass, field
from typing import Any, Iterable

from .epistemics import (
    KNOWN_CONTAINERS,
    NO,
    UNASSESSED,
    YES,
    Completeness,
)

CONTRACT = "mak-xmp-extract-v1"

# How the packet was looked for. Only EXHAUSTIVE licenses a negative.
EXHAUSTIVE = "exhaustive"
BOUNDED = "bounded_window"
UNSUPPORTED = "unsupported_format"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_XMP_KEYWORD = b"XML:com.adobe.xmp"
JPEG_XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
JPEG_XMP_EXT_HEADER = b"http://ns.adobe.com/xmp/extension/\x00"
# The UUID Adobe registered for an XMP packet inside an ISO base media file.
MP4_XMP_UUID = bytes.fromhex("BE7ACFCB97A942E89C71999491E3AFAC")
# QuickTime's own container for the same payload.
QUICKTIME_XMP_ATOM = b"XMP_"

PACKET_START = re.compile(rb"<\?xpacket begin=")
PACKET_END = re.compile(rb"<\?xpacket end=[^>]*\?>")

FULL_READ_CAP = 96 * 1024 * 1024      # read whole files up to this size
WINDOW_HEAD = 512 * 1024
WINDOW_TAIL = 256 * 1024

PNG_EXT = {".png", ".apng"}
JPEG_EXT = {".jpg", ".jpeg", ".jpe", ".jfif"}
ISOBMFF_EXT = {".mp4", ".mov", ".m4v", ".m4a", ".heic", ".heif"}


class XmpError(ValueError):
    """The file could not be read as the declared format."""


# --------------------------------------------------------------- field parsing
#
# The packet is RDF/XML. A real XML parse is preferable, but Adobe writers emit
# packets that are occasionally truncated or doubled inside one file, and a
# strict parser then yields nothing at all. So fields are pulled lexically and
# the structural nesting that MATTERS -- History versus Ingredients -- is
# recovered from the enclosing element, not from proximity.

_SIMPLE = {
    "document_id": (b"xmpMM:DocumentID", b"stRef:documentID"),
    "instance_id": (b"xmpMM:InstanceID", b"stRef:instanceID"),
    "original_document_id": (b"xmpMM:OriginalDocumentID", b"stRef:originalDocumentID"),
}
RE_TOOL = re.compile(rb"xmp:CreatorTool[^\x00>]{0,12}?[\">]\s*([^\"<\x00]{2,80})")
RE_CREATE = re.compile(rb"xmp:CreateDate[^\x00>]{0,12}?[\">]\s*([^\"<\x00]{4,40})")
RE_MODIFY = re.compile(rb"xmp:ModifyDate[^\x00>]{0,12}?[\">]\s*([^\"<\x00]{4,40})")


def _attr_or_text(blob: bytes, name: bytes) -> str | None:
    """Value of ``name`` whether it was written as an attribute or an element."""
    for pattern in (name + rb'\s*=\s*"([^"]{1,200})"',
                    b"<" + name + rb"[^>]*>\s*([^<]{1,200})\s*</" + name + b">"):
        found = re.search(pattern, blob)
        if found:
            value = found.group(1).strip()
            if value:
                return value.decode("utf-8", "replace")
    return None


def _section(blob: bytes, name: bytes) -> bytes | None:
    """The bytes of one xmpMM container element, e.g. History or Ingredients."""
    open_tag = re.search(b"<" + name + rb"[\s>]", blob)
    if not open_tag:
        return None
    close = blob.find(b"</" + name + b">", open_tag.start())
    if close == -1:
        return None
    return blob[open_tag.start():close]


def _list_items(section: bytes) -> list[bytes]:
    """Each rdf:li in a Seq or Bag, as raw bytes."""
    items: list[bytes] = []
    for match in re.finditer(rb"<rdf:li\b", section):
        start = match.start()
        close = section.find(b"</rdf:li>", start)
        if close == -1:
            # A self-closing li carries everything in its attributes.
            end = section.find(b"/>", start)
            if end == -1:
                continue
            items.append(section[start:end])
        else:
            items.append(section[start:close])
    return items


@dataclass
class XmpFields:
    """What one packet says. Nothing here is a relation yet."""

    document_id: str | None = None
    instance_id: str | None = None
    original_document_id: str | None = None
    creator_tool: str | None = None
    create_date: str | None = None
    modify_date: str | None = None
    # The immediate parent state, if the writer recorded one.
    derived_from: dict[str, str] = field(default_factory=dict)
    # Operations on THIS document's own chain. Each entry is a self-state.
    history: list[dict[str, str]] = field(default_factory=list)
    # OTHER documents that went into this one. A different relation entirely.
    ingredients: list[dict[str, str]] = field(default_factory=list)
    # Embedded copies of ingredient metadata.
    pantry: list[dict[str, str]] = field(default_factory=list)

    @property
    def has_any(self) -> bool:
        return bool(self.document_id or self.instance_id
                    or self.original_document_id or self.derived_from
                    or self.history or self.ingredients or self.pantry)

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "instance_id": self.instance_id,
            "original_document_id": self.original_document_id,
            "creator_tool": self.creator_tool,
            "create_date": self.create_date,
            "modify_date": self.modify_date,
            "derived_from": dict(self.derived_from),
            "history": [dict(h) for h in self.history],
            "ingredients": [dict(i) for i in self.ingredients],
            "pantry": [dict(p) for p in self.pantry],
        }


def parse_packet(packet: bytes) -> XmpFields:
    """Pull the declared fields out of one RDF/XML packet."""
    out = XmpFields()
    for attribute, names in _SIMPLE.items():
        for name in names:
            value = _attr_or_text(packet, name)
            if value:
                setattr(out, attribute, value)
                break
    for attribute, pattern in (("creator_tool", RE_TOOL), ("create_date", RE_CREATE),
                               ("modify_date", RE_MODIFY)):
        found = pattern.search(packet)
        if found:
            setattr(out, attribute, found.group(1).decode("utf-8", "replace").strip())

    derived = _section(packet, b"xmpMM:DerivedFrom")
    if derived is not None:
        out.derived_from = _ref_fields(derived)
    else:
        # A DerivedFrom written entirely as attributes on a self-closing element.
        inline = re.search(rb"<xmpMM:DerivedFrom\b([^>]*)/>", packet)
        if inline:
            out.derived_from = _ref_fields(inline.group(1))

    history = _section(packet, b"xmpMM:History")
    if history is not None:
        for item in _list_items(history):
            entry = _event_fields(item)
            if entry:
                out.history.append(entry)

    ingredients = _section(packet, b"xmpMM:Ingredients")
    if ingredients is not None:
        for item in _list_items(ingredients):
            entry = _ref_fields(item)
            if entry:
                out.ingredients.append(entry)

    pantry = _section(packet, b"xmpMM:Pantry")
    if pantry is not None:
        for item in _list_items(pantry):
            entry = _ref_fields(item)
            if entry:
                out.pantry.append(entry)
    return out


def _ref_fields(blob: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, name in (("document_id", b"stRef:documentID"),
                      ("instance_id", b"stRef:instanceID"),
                      ("original_document_id", b"stRef:originalDocumentID"),
                      ("file_path", b"stRef:filePath"),
                      ("from_part", b"stRef:fromPart"),
                      ("to_part", b"stRef:toPart"),
                      ("mask_markers", b"stRef:maskMarkers")):
        value = _attr_or_text(blob, name)
        if value:
            out[key] = value
    return out


def _event_fields(blob: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, name in (("action", b"stEvt:action"),
                      ("instance_id", b"stEvt:instanceID"),
                      ("software_agent", b"stEvt:softwareAgent"),
                      ("when", b"stEvt:when"),
                      ("changed", b"stEvt:changed"),
                      ("parameters", b"stEvt:parameters")):
        value = _attr_or_text(blob, name)
        if value:
            out[key] = value
    return out


# ------------------------------------------------------------ format locators

def _packets_from_blob(blob: bytes) -> list[bytes]:
    """Every packet in a buffer. Adobe writers sometimes emit more than one."""
    out: list[bytes] = []
    for start in PACKET_START.finditer(blob):
        end = PACKET_END.search(blob, start.end())
        out.append(blob[start.start(): end.end() if end else min(len(blob),
                                                                start.start() + 2_000_000)])
    if not out:
        # A packet may be stored without the xpacket wrapper.
        for match in re.finditer(rb"<x:xmpmeta\b", blob):
            close = blob.find(b"</x:xmpmeta>", match.start())
            if close != -1:
                out.append(blob[match.start(): close + 12])
    return out


def _png_packets(path: str) -> tuple[list[bytes], str]:
    """Walk the PNG chunk table. Exhaustive by construction.

    Current writers use an ``iTXt`` chunk, but real Adobe exports in this
    corpus also use the older ``tEXt`` chunk with the same keyword. The iTXt
    chunk may be zlib-compressed, which is why a window scan of a PNG finds an
    ``<?xpacket`` marker only when the writer happened to leave it uncompressed.
    """
    out: list[bytes] = []
    methods: set[str] = set()
    with open(path, "rb") as handle:
        if handle.read(8) != PNG_MAGIC:
            raise XmpError("not_a_png")
        while True:
            header = handle.read(8)
            if len(header) < 8:
                break
            length, kind = struct.unpack(">I4s", header)
            if length > 64 * 1024 * 1024:
                break
            if kind in (b"iTXt", b"tEXt"):
                data = handle.read(length)
                handle.read(4)
                nul = data.find(b"\x00")
                if nul == -1 or data[:nul] != PNG_XMP_KEYWORD:
                    continue
                if kind == b"tEXt":
                    out.append(data[nul + 1:])
                    methods.add("png_text_chunk")
                    continue
                rest = data[nul + 1:]
                if len(rest) < 2:
                    continue
                compressed, _method = rest[0], rest[1]
                rest = rest[2:]
                # language tag then translated keyword, both NUL terminated
                for _ in range(2):
                    cut = rest.find(b"\x00")
                    if cut == -1:
                        rest = b""
                        break
                    rest = rest[cut + 1:]
                if not rest:
                    continue
                if compressed == 1:
                    try:
                        rest = zlib.decompress(rest)
                    except zlib.error:
                        continue
                out.append(rest)
                methods.add("png_itxt_chunk")
            elif kind == b"IEND":
                break
            else:
                handle.seek(length + 4, os.SEEK_CUR)
    if methods == {"png_itxt_chunk"}:
        method = "png_itxt_chunk"
    elif methods == {"png_text_chunk"}:
        method = "png_text_chunk"
    elif methods:
        method = "png_xmp_chunks"
    else:
        method = "png_chunk_scan"
    return out, method


def _jpeg_packets(path: str) -> list[bytes]:
    """Walk JPEG marker segments. Exhaustive over the metadata region."""
    out: list[bytes] = []
    with open(path, "rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise XmpError("not_a_jpeg")
        while True:
            byte = handle.read(1)
            if not byte:
                break
            if byte != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if not marker or marker in (b"\xd8", b"\x01") or b"\xd0" <= marker <= b"\xd7":
                continue
            if marker in (b"\xd9", b"\xda"):   # EOI or start of scan
                break
            size_bytes = handle.read(2)
            if len(size_bytes) < 2:
                break
            size = struct.unpack(">H", size_bytes)[0] - 2
            if size < 0:
                break
            payload = handle.read(size)
            if marker == b"\xe1":
                if payload.startswith(JPEG_XMP_HEADER):
                    out.append(payload[len(JPEG_XMP_HEADER):])
                elif payload.startswith(JPEG_XMP_EXT_HEADER):
                    # Extended XMP: 32-byte GUID, 4-byte length, 4-byte offset.
                    out.append(payload[len(JPEG_XMP_EXT_HEADER) + 40:])
    return out


def _isobmff_packets(path: str, depth: int = 0, start: int = 0,
                     end: int | None = None) -> list[bytes]:
    """Walk the ISO base media box tree for Adobe's XMP uuid box."""
    out: list[bytes] = []
    size_total = os.path.getsize(path) if end is None else end
    with open(path, "rb") as handle:
        offset = start
        while offset < size_total:
            handle.seek(offset)
            header = handle.read(8)
            if len(header) < 8:
                break
            size, kind = struct.unpack(">I4s", header)
            body = offset + 8
            if size == 1:
                extended = handle.read(8)
                if len(extended) < 8:
                    break
                size = struct.unpack(">Q", extended)[0]
                body = offset + 16
            elif size == 0:
                size = size_total - offset
            if size < 8:
                break
            if kind == b"uuid":
                uuid = handle.read(16)
                if uuid == MP4_XMP_UUID:
                    out.append(handle.read(max(offset + size - body - 16, 0)))
            elif kind == QUICKTIME_XMP_ATOM:
                # QuickTime does not use Adobe's uuid box. It stores the packet in
                # an atom named literally "XMP_" inside moov/udta. Looking only
                # for the uuid box found 0 packets in 1372 real .mov files while a
                # crude window scan found 180 -- the format-aware method was WORSE
                # than the naive one until this branch existed. Measured on
                # "DREF CHOCOLATE/bosa lova.mov": ftyp, moov(udta > XMP_), free, mdat.
                out.append(handle.read(max(offset + size - body, 0)))
            elif kind in (b"moov", b"udta", b"trak", b"meta") and depth < 4:
                out.extend(_isobmff_packets(path, depth + 1, body, offset + size))
            offset += size
    return out


def _generic_packets(path: str, size: int) -> tuple[list[bytes], str]:
    """Whole file when small enough, otherwise a window. Says which it did."""
    with open(path, "rb") as handle:
        if size <= FULL_READ_CAP:
            return _packets_from_blob(handle.read()), EXHAUSTIVE
        head = handle.read(WINDOW_HEAD)
        handle.seek(-WINDOW_TAIL, os.SEEK_END)
        return _packets_from_blob(head + handle.read()), BOUNDED


# Which declared vocabulary each locator draws on. The .mov failure was a
# vocabulary gap that the old single flag could not express, so the mapping is
# data now.
LOCATOR_VOCABULARY = {
    "png_itxt_chunk": "png",
    "png_text_chunk": "png",
    "png_xmp_chunks": "png",
    "png_chunk_scan": "png",
    "jpeg_app1_segment": "jpeg",
    "isobmff_uuid_box": "isobmff",
    "whole_file_packet_scan": "generic",
    "window_packet_scan": "generic",
}


@dataclass
class XmpResult:
    """What was found, and exactly how complete the looking was.

    ``completeness`` is kept as a one-word summary of the TRAVERSAL question
    only, because that is all the previous version meant. ``levels`` carries the
    five independent verdicts, and it is the field a caller should read before
    treating a miss as absence.
    """

    path: str
    extension: str
    size: int
    method: str
    completeness: str
    packets: int
    fields: XmpFields | None
    error: str = ""

    @property
    def levels(self) -> Completeness:
        vocabulary_key = LOCATOR_VOCABULARY.get(self.method, "generic")
        declared = KNOWN_CONTAINERS.get(vocabulary_key, {})
        traversal = YES if (self.completeness == EXHAUSTIVE and not self.error) else NO
        return Completeness(
            traversal=traversal,
            vocabulary=declared.get("vocabulary_complete", NO),
            # This layer never sees a group, so it cannot speak for an authority
            # over one; and it cannot know whether the corpus is complete.
            authority=UNASSESSED,
            corpus=UNASSESSED,
            # Applications strip metadata on export. Absence of a packet never
            # implies absence of provenance, so this is NO by construction.
            semantic=NO,
            note=f"locator={self.method} vocabulary={vocabulary_key}")

    @property
    def negative_is_evidence(self) -> bool:
        """Traversal AND vocabulary must both hold. Traversal alone was the bug."""
        return self.levels.negative_is_evidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "path": self.path,
            "extension": self.extension,
            "size": self.size,
            "method": self.method,
            "search_completeness": self.completeness,
            "completeness_levels": self.levels.as_dict(),
            "negative_is_evidence": self.negative_is_evidence,
            "packets": self.packets,
            "fields": self.fields.as_dict() if self.fields else None,
            "error": self.error,
        }


def extract(path: str) -> XmpResult:
    """Locate every packet by the format's own rules, then parse the last one.

    The last packet wins when a file carries several: Adobe writers append on
    save, so the final packet is the current state. The count is reported so a
    caller can see that a choice was made.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return XmpResult(path, ext, 0, "stat", UNSUPPORTED, 0, None, str(exc))

    method, completeness = "generic", BOUNDED
    try:
        if ext in PNG_EXT:
            packets, method = _png_packets(path)
            completeness = EXHAUSTIVE
        elif ext in JPEG_EXT:
            packets, method, completeness = _jpeg_packets(path), "jpeg_app1_segment", EXHAUSTIVE
        elif ext in ISOBMFF_EXT:
            packets, method, completeness = _isobmff_packets(path), "isobmff_uuid_box", EXHAUSTIVE
        else:
            packets, completeness = _generic_packets(path, size)
            method = "whole_file_packet_scan" if completeness == EXHAUSTIVE \
                else "window_packet_scan"
    except (OSError, XmpError, struct.error) as exc:
        return XmpResult(path, ext, size, method, UNSUPPORTED, 0, None, str(exc))

    if not packets:
        return XmpResult(path, ext, size, method, completeness, 0, None)
    parsed = parse_packet(packets[-1])
    return XmpResult(path, ext, size, method, completeness, len(packets), parsed)
