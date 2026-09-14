"""Turn files into the five entities, recording evidence for every relation.

Nothing is inferred here beyond what an extractor read. The only judgement is
which identifier to use as the state key, and that choice is recorded in
``id_source`` so a reader can see it was made.

The state key preference, and why:

1. ``xmpMM:InstanceID`` -- the writer's own name for "this incarnation". It is
   the closest thing in the corpus to what ArtifactState means.
2. the content digest -- byte identity, when no embedded id exists.
3. a synthetic key over (root, path, size, mtime) -- a last resort, and it is
   the only key that a path change destroys. Recorded as ``synthetic`` so a
   later pass can tell which states are fragile.

A file inside an archive gets a ``container_path`` on its Observation. The
archive is a container, never a project.
"""

from __future__ import annotations

import hashlib
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .resolution import candidate_count, is_present
from .schema import (
    AUTHORITIES,
    NOT_RESOLVABLE_BY_THIS_LAYER,
    OBJ_BASENAME,
    OBJ_CONTENT,
    OBJ_EXTERNAL_ID,
    OBJ_LINEAGE,
    OBJ_OBSERVATION,
    RESOLVED,
    UNRESOLVED_IN_CORPUS,
    DERIVED_FROM,
    OBSERVED_AT,
    PANTRY_COPY_OF,
    REFERENCES,
    REVISION_IN_LINEAGE,
    SAME_CONTENT,
    SAME_LINEAGE,
    USES,
    ArtifactState,
    Content,
    Evidence,
    Lineage,
    Observation,
    Substrate,
    SubstrateError,
)
from .xmp import extract as xmp_extract

CONTRACT = "mak-substrate-ingest-v1"

# The weak extractor, kept behind its own authority. See AUTHORITIES for the
# reasons it is weak; this pattern is the one that produced the measured 104/37/19
# on SHOWCAUPOLICAN and 232/73/0 on sampier.
RESOLUME_PATH = re.compile(
    rb'[A-Za-z]:[\\/][^"<>\x00]{4,300}?'
    rb'\.(?:mov|mp4|png|jpg|jpeg|tif|exr|avi|mkv|webm|gif|psd|aep)', re.I)
RESOLUME_EXT = {".avc", ".xml"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _eid(*parts: Any) -> str:
    return "ev:" + hashlib.sha256("\x1f".join(str(p) for p in parts)
                                  .encode("utf-8")).hexdigest()[:32]


def _oid(*parts: Any) -> str:
    return "obs:" + hashlib.sha256("\x1f".join(str(p) for p in parts)
                                   .encode("utf-8")).hexdigest()[:32]


def state_key(instance_id: str | None, content_id: str | None,
              root_id: str, relative_path: str, size: int | None,
              mtime: str | None) -> tuple[str, str]:
    """The state key and where it came from. The order is the whole design."""
    if instance_id:
        return f"state:instance:{instance_id}", "xmp_instance_id"
    if content_id:
        return f"state:content:{content_id.split(':', 1)[-1]}", "content"
    synthetic = hashlib.sha256(
        f"{root_id}\x1f{relative_path}\x1f{size}\x1f{mtime}".encode()).hexdigest()[:32]
    return f"state:synthetic:{synthetic}", "synthetic"


def ingest_file(sub: Substrate, path: str | Path, *, root_id: str,
                relative_path: str, container_path: str | None = None,
                hash_content: bool = True, read_xmp: bool = True,
                read_references: bool = False) -> dict[str, Any]:
    """Record one file as Content + ArtifactState + Lineage + Observation + Evidence."""
    path = Path(path)
    try:
        stat = path.stat()
    except OSError as exc:
        raise SubstrateError(f"unreadable_file: {path}: {exc}") from exc
    mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(
        timespec="seconds")
    now = _now()
    out: dict[str, Any] = {"path": str(path), "evidence": 0}

    content_id: str | None = None
    if hash_content:
        content = Content.of_file(path)
        sub.put_content(content)
        content_id = content.content_id
        out["content_id"] = content_id

    fields = None
    xmp_method, xmp_completeness = "not_read", "not_read"
    if read_xmp:
        result = xmp_extract(str(path))
        xmp_method, xmp_completeness = result.method, result.completeness
        out["xmp"] = {"method": xmp_method, "completeness": xmp_completeness,
                      "packets": result.packets,
                      "negative_is_evidence": result.negative_is_evidence}
        if result.fields and result.fields.has_any:
            fields = result.fields

    sid, id_source = state_key(
        fields.instance_id if fields else None, content_id, root_id,
        relative_path, stat.st_size, mtime)
    sub.put_state(ArtifactState(
        state_id=sid, content_id=content_id,
        document_id=fields.document_id if fields else None,
        instance_id=fields.instance_id if fields else None,
        original_document_id=fields.original_document_id if fields else None,
        creator_tool=fields.creator_tool if fields else None,
        claimed_created=fields.create_date if fields else None,
        claimed_modified=fields.modify_date if fields else None,
        id_source=id_source))
    out["state_id"] = sid
    out["id_source"] = id_source

    observation = Observation(
        observation_id=_oid(root_id, relative_path, container_path or "", mtime),
        state_id=sid, root_id=root_id, relative_path=relative_path,
        container_path=container_path, observed_at=now,
        basename=os.path.basename(relative_path),
        extension=os.path.splitext(relative_path)[1].lower(),
        fs_size=stat.st_size, fs_mtime=mtime)
    sub.put_observation(observation)
    out["observation_id"] = observation.observation_id

    def record(predicate: str, obj: str, authority: str, extractor: str,
               method: str, completeness: str, detail: str = "",
               ordinal: int | None = None,
               object_kind: str = OBJ_EXTERNAL_ID,
               resolution: str | None = None) -> None:
        # An external id is resolved against the corpus HERE, provisionally: the
        # referent may not have been read yet, which is why
        # Substrate.resolve_pending_references exists as a later pass.
        candidates = 0
        if resolution is None:
            if object_kind == OBJ_EXTERNAL_ID:
                # is_present, not truthiness: a Resolution is a frozen
                # dataclass and every instance is truthy, so `if resolve(...)`
                # would read Absent as RESOLVED. Many counts as present here on
                # purpose -- "this id resolves in the corpus" does not depend on
                # WHICH state carries it, so it survives the collision.
                found = sub.resolve_external_id(obj)
                candidates = candidate_count(found)
                resolution = (RESOLVED if is_present(found)
                              else UNRESOLVED_IN_CORPUS)
            elif object_kind == OBJ_BASENAME:
                resolution = NOT_RESOLVABLE_BY_THIS_LAYER
            else:
                resolution = RESOLVED
        cause = ""
        if resolution == UNRESOLVED_IN_CORPUS:
            cause = "MISSING_EVIDENCE"
        elif resolution == NOT_RESOLVABLE_BY_THIS_LAYER:
            cause = "DECODER_LIMIT"
        sub.put_evidence(Evidence(
            evidence_id=_eid(sid, predicate, obj, authority, ordinal),
            subject=sid, predicate=predicate, object=obj, authority=authority,
            extractor=extractor, method=method,
            search_completeness=completeness, recorded_at=now, detail=detail,
            ordinal=ordinal, object_kind=object_kind,
            object_resolution=resolution, unknown_cause=cause,
            candidate_count=candidates))
        out["evidence"] += 1

    record(OBSERVED_AT, observation.observation_id, "filesystem", "os.stat",
           "stat", "exhaustive",
           f"{root_id}:{relative_path}"
           + (f" inside {container_path}" if container_path else ""),
           object_kind=OBJ_OBSERVATION)

    if content_id:
        record(SAME_CONTENT, content_id, "content_digest", "hashlib.sha256",
               "whole_file", "exhaustive", "full digest over every byte",
               object_kind=OBJ_CONTENT)

    if fields:
        lineage = Lineage.key_for(fields.document_id, fields.original_document_id)
        if lineage:
            sub.put_lineage(lineage, sid)
            record(SAME_LINEAGE, lineage.lineage_id, "xmp_packet", "xmp.extract",
                   xmp_method, xmp_completeness,
                   f"key from {lineage.key_source}", object_kind=OBJ_LINEAGE)
            out["lineage_id"] = lineage.lineage_id

        if fields.derived_from:
            parent = (fields.derived_from.get("instance_id")
                      or fields.derived_from.get("document_id"))
            if parent:
                record(DERIVED_FROM, f"xmp:{parent}", "xmp_packet", "xmp.extract",
                       xmp_method, xmp_completeness,
                       "xmpMM:DerivedFrom, the immediate parent state")

        # History: operations on THIS document's own chain. Self-continuity.
        for index, event in enumerate(fields.history):
            target = event.get("instance_id")
            if not target:
                continue
            record(REVISION_IN_LINEAGE, f"xmp:{target}", "xmp_packet",
                   "xmp.extract", xmp_method, xmp_completeness,
                   f"action={event.get('action', '?')} "
                   f"agent={event.get('software_agent', '?')} "
                   f"when={event.get('when', '?')}", ordinal=index)

        # Ingredients: OTHER documents that went in. Cross-document. Not the same
        # class of edge as History, and never merged with it.
        for index, ref in enumerate(fields.ingredients):
            target = (ref.get("document_id") or ref.get("instance_id")
                      or ref.get("file_path"))
            if not target:
                continue
            record(USES, f"xmp:{target}", "xmp_packet", "xmp.extract",
                   xmp_method, xmp_completeness,
                   f"xmpMM:Ingredients entry; file_path={ref.get('file_path', '')}",
                   ordinal=index)

        for index, ref in enumerate(fields.pantry):
            target = ref.get("document_id") or ref.get("instance_id")
            if target:
                record(PANTRY_COPY_OF, f"xmp:{target}", "xmp_packet",
                       "xmp.extract", xmp_method, xmp_completeness,
                       "xmpMM:Pantry embedded ingredient metadata", ordinal=index)

    if read_references and observation.extension in RESOLUME_EXT:
        try:
            blob = path.read_bytes()
        except OSError:
            blob = b""
        seen: set[str] = set()
        for index, match in enumerate(RESOLUME_PATH.finditer(blob)):
            mentioned = match.group(0).decode("utf-8", "replace")
            key = os.path.basename(mentioned.replace("\\", "/")).lower()
            if key in seen:
                continue
            seen.add(key)
            record(REFERENCES, f"basename:{key}", "resolume_reference_regex",
                   "ingest.RESOLUME_PATH", "byte_regex", "bounded_window",
                   "a MENTION of a path, not a verified dependency. Weak "
                   "authority: this is not a parser and cannot see a reference "
                   "stored in another form.", ordinal=index,
                   object_kind=OBJ_BASENAME)
        out["references"] = len(seen)
    return out


def walk_root(root: str | Path, *, root_id: str,
              extensions: Iterable[str] | None = None,
              limit: int | None = None) -> Iterator[tuple[Path, str]]:
    """Yield (absolute path, relative path) under a root. No interpretation."""
    root = Path(root)
    wanted = {e.lower() for e in extensions} if extensions else None
    count = 0
    for current, _dirs, files in os.walk(root):
        for name in sorted(files):
            if wanted and os.path.splitext(name)[1].lower() not in wanted:
                continue
            absolute = Path(current) / name
            yield absolute, str(absolute.relative_to(root))
            count += 1
            if limit and count >= limit:
                return


def ingest_archive(sub: Substrate, archive: str | Path, *, root_id: str,
                   relative_path: str, hash_content: bool = True,
                   limit: int | None = None) -> dict[str, Any]:
    """Record the entries of a ZIP without treating the archive as a project.

    Every member becomes a state with an Observation whose ``container_path`` is
    the archive. The digest is computed from the decompressed bytes, so a file
    keeps its Content identity across zip and unzip -- which is the whole point.
    """
    archive = Path(archive)
    if not zipfile.is_zipfile(archive):
        raise SubstrateError(f"not_a_zip: {archive}")
    now = _now()
    recorded = 0
    with zipfile.ZipFile(archive) as zf:
        for index, info in enumerate(zf.infolist()):
            if info.is_dir():
                continue
            if limit and recorded >= limit:
                break
            with zf.open(info) as handle:
                digest = hashlib.sha256()
                total = 0
                while True:
                    block = handle.read(1 << 20)
                    if not block:
                        break
                    digest.update(block)
                    total += len(block)
            content_id = f"sha256:{digest.hexdigest()}"
            if hash_content:
                sub.put_content(Content(content_id=content_id, size=total,
                                        format_detected=os.path.splitext(
                                            info.filename)[1].lower()))
            sid, id_source = state_key(None, content_id if hash_content else None,
                                       root_id, info.filename, total, None)
            sub.put_state(ArtifactState(state_id=sid,
                                        content_id=content_id if hash_content else None,
                                        id_source=id_source))
            observation = Observation(
                observation_id=_oid(root_id, info.filename, str(relative_path), index),
                state_id=sid, root_id=root_id, relative_path=info.filename,
                container_path=str(relative_path), observed_at=now,
                basename=os.path.basename(info.filename),
                extension=os.path.splitext(info.filename)[1].lower(),
                fs_size=total, fs_mtime=None)
            sub.put_observation(observation)
            sub.put_evidence(Evidence(
                evidence_id=_eid(sid, OBSERVED_AT, observation.observation_id,
                                 "filesystem", index),
                subject=sid, predicate=OBSERVED_AT,
                object=observation.observation_id, authority="filesystem",
                extractor="zipfile", method="archive_entry",
                search_completeness="exhaustive", recorded_at=now,
                detail=f"inside archive {relative_path}"))
            if hash_content:
                sub.put_evidence(Evidence(
                    evidence_id=_eid(sid, SAME_CONTENT, content_id,
                                     "content_digest", None),
                    subject=sid, predicate=SAME_CONTENT, object=content_id,
                    authority="content_digest", extractor="hashlib.sha256",
                    method="decompressed_stream", search_completeness="exhaustive",
                    recorded_at=now,
                    detail="digest of the DECOMPRESSED bytes, so zip and unzip "
                           "yield the same Content"))
            recorded += 1
    return {"archive": str(archive), "entries_recorded": recorded}
