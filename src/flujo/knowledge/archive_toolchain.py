"""Read-only adoption of mature open-source archive inspection tools.

The archive observer remains the only component allowed to enumerate an
archive.  This adapter consumes an accepted Stage 2A projection and inspects
only the explicitly listed physical paths.  It records technical evidence
from ExifTool, ffprobe, Tesseract, file/libmagic, Mutagen, Hachoir, ImageHash
and pypdf without turning any result into authorship, work identity,
publication or cultural truth.

No tool in this module edits an input file.  The optional LearningStore hook
persists the complete output as one idempotent append-only operational event;
the default API and CLI only return/write JSON.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from ._contract_helpers import sha256_ref as _digest
from .project_ir import LearningStore
from .project_context import SCHEMA as PROJECT_CONTEXT_SCHEMA, validate_context


SCHEMA = "mak-archive-tool-observations-v1"
PROJECTION_SCHEMA = "mak-archive-reconstruction-input-v1"
ALGORITHM_VERSION = "open-source-toolchain-1"
EVENT_TYPE = "archive_tool_observations"
MAX_TEXT = 4000
MAX_TAGS = 64
MAX_STREAMS = 32
MAX_ARTIFACTS = 4096
DEFAULT_TIMEOUT = 30
DEFAULT_EXIFTOOL = "/home/mak/tools/exiftool-13.59/exiftool"
DEFAULT_CZKAWKA = "/home/mak/tools/czkawka/12.0.1/czkawka_cli"
MAX_CONTEXT_RELATIONS = 200
MAX_SURFACE_COMPONENTS = 64
MAX_SURFACE_MATCHES = 128
SURFACE_PHASH_DISTANCE = 10


class ArchiveToolchainError(ValueError):
    """Raised when the accepted projection or tool result is invalid."""


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def _sorted_unique(values: Any, limit: int = MAX_TAGS) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    if not isinstance(values, Sequence):
        raise ArchiveToolchainError("expected_string_list")
    return sorted({_text(value, 500) for value in values if _text(value, 500)})[:limit]


def _json_surface(value: Any, path: str = "output") -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ArchiveToolchainError(f"non_finite_value:{path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_surface(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ArchiveToolchainError(f"non_string_key:{path}")
            _json_surface(item, f"{path}.{key}")
        return
    raise ArchiveToolchainError(f"non_json_value:{path}")


def _validate_projection(
    projection: Mapping[str, Any], *, allow_large: bool = False,
) -> tuple[str, str, str, list[Mapping[str, Any]]]:
    if not isinstance(projection, Mapping):
        raise ArchiveToolchainError("projection_must_be_object")
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise ArchiveToolchainError("projection_bad_schema")
    archive_id = _text(projection.get("archive_id"), 500)
    snapshot_id = _text(projection.get("snapshot_id"), 500)
    input_hash = _text(projection.get("input_hash"), 200)
    if not archive_id or not snapshot_id or not input_hash:
        raise ArchiveToolchainError("projection_identity_incomplete")
    artifacts = projection.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ArchiveToolchainError("projection_artifacts_invalid")
    if len(artifacts) > MAX_ARTIFACTS and not allow_large:
        raise ArchiveToolchainError("projection_artifacts_overbound")
    refs: set[str] = set()
    paths: set[str] = set()
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, Mapping):
            raise ArchiveToolchainError(f"artifact_{index}_not_object")
        ref = _text(raw.get("artifact_ref"), 500)
        path = _text(raw.get("relative_path"), 4000)
        if not ref or not path or path.startswith("/") or "\\" in path:
            raise ArchiveToolchainError(f"artifact_{index}_identity_invalid")
        posix = PurePosixPath(path)
        if posix.as_posix() != path or any(part in {"", ".", ".."} for part in path.split("/")):
            raise ArchiveToolchainError(f"artifact_{index}_relative_path_invalid")
        if ref in refs or path in paths:
            raise ArchiveToolchainError("projection_duplicate_artifact")
        refs.add(ref)
        paths.add(path)
    return archive_id, snapshot_id, input_hash, [dict(item) for item in artifacts]


def _selected_artifacts(
    artifacts: Sequence[Mapping[str, Any]],
    artifact_refs: Sequence[str] | None,
) -> list[Mapping[str, Any]]:
    if artifact_refs is None:
        return list(artifacts)
    requested = _sorted_unique(artifact_refs, limit=MAX_ARTIFACTS)
    by_ref = {str(item["artifact_ref"]): item for item in artifacts}
    unknown = sorted(set(requested) - set(by_ref))
    if unknown:
        raise ArchiveToolchainError("unknown_artifact_ref:" + ",".join(unknown))
    return [by_ref[ref] for ref in requested]


def _tool_path(name: str, explicit: str | None = None) -> str | None:
    candidate = explicit or os.environ.get("MAK_" + name.upper())
    if name == "exiftool" and not candidate and Path(DEFAULT_EXIFTOOL).is_file():
        candidate = DEFAULT_EXIFTOOL
    if name == "czkawka" and not candidate and Path(DEFAULT_CZKAWKA).is_file():
        candidate = DEFAULT_CZKAWKA
    if candidate:
        if Path(candidate).is_file() or shutil.which(candidate):
            return candidate
        return None
    return shutil.which(name)


def _tool_version(name: str, executable: str | None) -> str | None:
    if not executable:
        return None
    command = [executable, "-ver"] if name == "exiftool" else [executable, "--version"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip()
    if name == "ffprobe":
        match = re.search(r"ffprobe version ([^ ]+)", output)
        return match.group(1) if match else _text(output.splitlines()[0] if output else "", 120)
    if name == "tesseract":
        match = re.search(r"tesseract ([^ \n]+)", output)
        return match.group(1) if match else _text(output.splitlines()[0] if output else "", 120)
    if name == "czkawka":
        match = re.search(r"czkawka ([^ \n]+)", output, re.IGNORECASE)
        return match.group(1) if match else _text(output.splitlines()[0] if output else "", 120)
    return _text(output.splitlines()[0] if output else "", 120) or None


def _run_json_tool(command: list[str], timeout: int) -> tuple[Any, str | None]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError as exc:
        return None, type(exc).__name__
    if result.returncode != 0:
        return None, "exit_" + str(result.returncode)
    try:
        value = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return None, "invalid_json"
    return value, None


def _run_text_tool(command: list[str], timeout: int) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError as exc:
        return None, type(exc).__name__
    if result.returncode != 0:
        return None, "exit_" + str(result.returncode)
    return result.stdout, None


def _observation_id(
    archive_id: str,
    snapshot_id: str,
    artifact_ref: str,
    observation_type: str,
    method: Mapping[str, Any],
    facts: Mapping[str, Any],
) -> str:
    return "tool-observation:" + _digest({
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "artifact_ref": artifact_ref,
        "observation_type": observation_type,
        "method": method,
        "facts": facts,
    })[7:]


def _observation(
    archive_id: str,
    snapshot_id: str,
    artifact: Mapping[str, Any],
    observation_type: str,
    status: str,
    method: Mapping[str, Any],
    facts: Mapping[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    ref = str(artifact["artifact_ref"])
    clean_facts = dict(facts)
    if reason:
        clean_facts["reason"] = reason
    row = {
        "observation_id": _observation_id(archive_id, snapshot_id, ref, observation_type, method, clean_facts),
        "artifact_ref": ref,
        "relative_path": str(artifact["relative_path"]),
        "observation_type": observation_type,
        "status": status,
        "method": dict(method),
        "evidence_refs": [ref],
        "facts": clean_facts,
    }
    return row


def _file_signature(path: Path, artifact: Mapping[str, Any], tools: Mapping[str, Any], timeout: int) -> dict[str, Any]:
    executable = tools.get("file", {}).get("path")
    if not executable:
        return _observation_result("file_signature", "unavailable", tools.get("file", {}), {"reason": "tool_missing"})
    output, error = _run_text_tool([executable, "--brief", "--mime-type", str(path)], timeout)
    if error:
        return _observation_result("file_signature", "error", tools["file"], {"reason": error})
    mime_type = _text(output, 200)
    return _observation_result("file_signature", "observed", tools["file"], {"mime_type": mime_type})


def _observation_result(
    observation_type: str,
    status: str,
    method: Mapping[str, Any],
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    return {"observation_type": observation_type, "status": status, "method": dict(method), "facts": dict(facts)}


def _surface_tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", _text(value, 1000))
    }


def _surface_signature(image: Any) -> dict[str, Any] | None:
    """Return a bounded visual signature for a rendered native layer.

    The signature is retrieval evidence only.  It deliberately omits pixels,
    absolute paths and layer content claims so a native file remains an input
    or resource rather than becoming an inferred artwork.
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return None
    try:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        bbox = alpha.getbbox()
        if bbox is None:
            return None
        cropped = rgba.crop(bbox)
        background = Image.new("RGB", cropped.size, (255, 255, 255))
        background.paste(cropped.convert("RGB"), mask=cropped.getchannel("A"))
        return {
            "width": int(cropped.width),
            "height": int(cropped.height),
            "phash": str(imagehash.phash(background)),
            "dhash": str(imagehash.dhash(background)),
            "ahash": str(imagehash.average_hash(background)),
        }
    except Exception:
        return None


def _exiftool(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    tool = tools.get("exiftool", {})
    executable = tool.get("path")
    if not executable:
        return _observation_result("embedded_metadata", "unavailable", tool, {"reason": "tool_missing"})
    fields = [
        "FileType", "MIMEType", "ImageWidth", "ImageHeight", "Duration", "VideoFrameRate",
        "AudioSampleRate", "AudioChannels", "CreateDate", "ModifyDate", "DateTimeOriginal",
        "Artist", "Title", "Album", "Description", "Software", "Comment", "DocumentTitle",
        "PageCount", "XMP:DocumentID", "XMP:InstanceID", "XMP:CreatorTool",
    ]
    command = [executable, "-j", "-G1", "-s", *["-" + field for field in fields], str(path)]
    value, error = _run_json_tool(command, timeout)
    if error:
        return _observation_result("embedded_metadata", "error", tool, {"reason": error})
    rows = value if isinstance(value, list) else None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], Mapping):
        return _observation_result("embedded_metadata", "observed", tool, {"fields": {}})
    selected: dict[str, Any] = {}
    for key, item in sorted(rows[0].items()):
        if key == "SourceFile" or item in (None, "", []):
            continue
        if isinstance(item, (str, int, float, bool)):
            selected[key] = item
        elif isinstance(item, list):
            selected[key] = [_text(value, 500) for value in item[:MAX_TAGS]]
    return _observation_result("embedded_metadata", "observed", tool, {"fields": selected})


def _ffprobe(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    tool = tools.get("ffprobe", {})
    executable = tool.get("path")
    if not executable:
        return None
    command = [
        executable, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path),
    ]
    value, error = _run_json_tool(command, timeout)
    if error:
        return _observation_result("media_streams", "error", tool, {"reason": error})
    format_row = value.get("format", {}) if isinstance(value, Mapping) else {}
    streams = value.get("streams", []) if isinstance(value, Mapping) else []
    if not isinstance(format_row, Mapping):
        format_row = {}
    if not isinstance(streams, list):
        streams = []
    safe_format = {
        key: format_row[key]
        for key in ("format_name", "format_long_name", "duration", "size", "bit_rate", "nb_streams")
        if key in format_row
    }
    safe_streams: list[dict[str, Any]] = []
    for stream in streams[:MAX_STREAMS]:
        if not isinstance(stream, Mapping):
            continue
        row = {
            key: stream[key]
            for key in (
                "index", "codec_type", "codec_name", "codec_long_name", "profile", "width", "height",
                "pix_fmt", "r_frame_rate", "avg_frame_rate", "sample_rate", "channels", "channel_layout",
                "duration", "bit_rate", "nb_frames",
            )
            if key in stream and isinstance(stream[key], (str, int, float, bool))
        }
        tags = stream.get("tags")
        if isinstance(tags, Mapping):
            row["tags"] = {
                _text(key, 120): _text(item, 500)
                for key, item in sorted(tags.items())
                if _text(key, 120) and item not in (None, "")
            }
        safe_streams.append(row)
    return _observation_result("media_streams", "observed", tool, {"format": safe_format, "streams": safe_streams})


def _mutagen(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    del timeout
    try:
        import mutagen
    except ImportError:
        return _observation_result("audio_tags", "unavailable", {"tool": "mutagen"}, {"reason": "package_missing"})
    try:
        audio = mutagen.File(path, easy=True)
    except Exception as exc:  # library parser boundary; preserve reason, not traceback
        return _observation_result("audio_tags", "error", {"tool": "mutagen", "version": getattr(mutagen, "version_string", None)}, {"reason": type(exc).__name__})
    if audio is None:
        return None
    tags: dict[str, list[str]] = {}
    for key, value in sorted((audio.tags or {}).items()):
        if isinstance(value, (list, tuple)):
            tags[_text(key, 120)] = [_text(item, 500) for item in value[:MAX_TAGS]]
        else:
            tags[_text(key, 120)] = [_text(value, 500)]
    info = getattr(audio, "info", None)
    facts: dict[str, Any] = {"tags": tags}
    for key in ("length", "bitrate", "sample_rate", "channels"):
        value = getattr(info, key, None)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            facts[key] = value
    return _observation_result("audio_tags", "observed", {"tool": "mutagen", "version": getattr(mutagen, "version_string", None)}, facts)


def _image(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    """Observe an image, degrading per capability instead of all at once.

    Until 2026-08-30 Pillow and ImageHash were treated as one capability named
    "Pillow+ImageHash": if `imagehash` was missing, the whole observation
    returned `unavailable` -- including `width` and `height`, which only ever
    needed Pillow. That mattered beyond tidiness: `technical_media_match_candidate`
    is built by comparing image dimensions against video dimensions, so on any
    clean install (CI included, where `imagehash` is in neither the `dev` nor the
    `render` extra) that relation could never be produced at all.

    Now the two degrade separately. Pillow alone yields dimensions, mode and
    format; the perceptual hashes appear only when ImageHash is there, and the
    tool string says which halves actually ran, so a reader can tell a partial
    observation from a complete one instead of guessing.
    """
    del timeout
    try:
        from PIL import Image
    except ImportError:
        return _observation_result("image_features", "unavailable", {"tool": "Pillow"}, {"reason": "package_missing"})
    try:
        import imagehash
    except ImportError:
        imagehash = None
    tool = "Pillow+ImageHash" if imagehash is not None else "Pillow"
    try:
        with Image.open(path) as image:
            facts: dict[str, Any] = {
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": image.format,
            }
            if imagehash is not None:
                rgb = image.convert("RGB")
                facts["phash"] = str(imagehash.phash(rgb))
                facts["dhash"] = str(imagehash.dhash(rgb))
                facts["ahash"] = str(imagehash.average_hash(rgb))
            else:
                facts["perceptual_hashes"] = "unavailable:imagehash_missing"
    except Exception as exc:
        return _observation_result("image_features", "error", {"tool": tool}, {"reason": type(exc).__name__})
    return _observation_result("image_features", "observed", {"tool": tool}, facts)


def _psd(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    del tools, timeout
    try:
        from psd_tools import PSDImage
    except ImportError:
        return _observation_result(
            "native_structure", "unavailable",
            {"tool": "psd-tools", "version": None},
            {"format": "psd", "reason": "package_missing"},
        )
    try:
        document = PSDImage.open(path)
        layer_rows: list[dict[str, Any]] = []

        def visit(layers: Any, depth: int = 0) -> None:
            for layer in layers:
                kind = _text(getattr(layer, "kind", None), 80) or type(layer).__name__.casefold()
                layer_rows.append({
                    "depth": depth,
                    "name": _text(getattr(layer, "name", None), 500),
                    "kind": kind,
                    "visible": bool(getattr(layer, "visible", False)),
                    "opacity": getattr(layer, "opacity", None),
                })
                if kind in {"group", "artboard"}:
                    try:
                        visit(layer, depth + 1)
                    except Exception:
                        # A malformed child must not discard the parent facts.
                        layer_rows[-1]["children_error"] = True

        visit(document)
        kind_counts: dict[str, int] = {}
        for row in layer_rows:
            kind_counts[row["kind"]] = kind_counts.get(row["kind"], 0) + 1
        surface_components: list[dict[str, Any]] = []
        surface_tokens: set[str] = set()
        for layer_index, layer in enumerate(document.descendants()):
            kind = _text(getattr(layer, "kind", None), 80) or type(layer).__name__.casefold()
            name = _text(getattr(layer, "name", None), 500)
            surface_tokens.update(_surface_tokens(name))
            if not getattr(layer, "visible", False) or kind in {"group", "artboard"}:
                continue
            try:
                signature = _surface_signature(layer.composite())
            except Exception:
                signature = None
            if signature is None:
                continue
            component = {
                "component_id": "native-component:" + _digest({
                    "layer_index": layer_index,
                    "name": name,
                    "kind": kind,
                    "signature": signature,
                })[7:],
                "layer_index": layer_index,
                "name": name,
                "kind": kind,
                **signature,
            }
            surface_components.append(component)
        return _observation_result(
            "native_structure", "observed",
            {"tool": "psd-tools", "version": _module_version("psd_tools")},
            {
                "format": "psd",
                "width": int(document.width),
                "height": int(document.height),
                "depth": int(document.depth),
                "color_mode": int(document.color_mode),
                "layer_count": len(layer_rows),
                "kind_counts": dict(sorted(kind_counts.items())),
                "named_layers": layer_rows[:MAX_TAGS],
                "layer_list_truncated": len(layer_rows) > MAX_TAGS,
                "surface_components": surface_components[:MAX_SURFACE_COMPONENTS],
                "surface_components_total": len(surface_components),
                "surface_components_truncated": len(surface_components) > MAX_SURFACE_COMPONENTS,
                "surface_tokens": sorted(surface_tokens)[:MAX_TAGS],
            },
        )
    except Exception as exc:
        return _observation_result(
            "native_structure", "error",
            {"tool": "psd-tools", "version": _module_version("psd_tools")},
            {"format": "psd", "reason": type(exc).__name__},
        )


def _xml_local_name(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _kra(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    del tools, timeout
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if sum(max(0, info.file_size) for info in infos) > 64 * 1024 * 1024:
                return _observation_result(
                    "native_structure", "error",
                    {"tool": "python-zipfile", "version": None},
                    {"format": "kra", "reason": "archive_budget_exceeded"},
                )
            names = sorted(info.filename for info in infos if info.filename)
            main_raw = archive.read("maindoc.xml") if "maindoc.xml" in archive.namelist() else b""
            info_raw = archive.read("documentinfo.xml") if "documentinfo.xml" in archive.namelist() else b""
        main_root = ET.fromstring(main_raw) if main_raw else None
        info_root = ET.fromstring(info_raw) if info_raw else None
        image = next(
            (element for element in main_root.iter() if _xml_local_name(element.tag) == "IMAGE"),
            None,
        ) if main_root is not None else None
        layers = [
            element for element in main_root.iter()
            if _xml_local_name(element.tag) == "layer"
        ] if main_root is not None else []
        about = next(
            (element for element in info_root.iter() if _xml_local_name(element.tag) == "about"),
            None,
        ) if info_root is not None else None
        info_values: dict[str, str] = {}
        if about is not None:
            for element in about:
                value = _text(element.text, 1000)
                if value:
                    info_values[_xml_local_name(element.tag)] = value
        layer_names = sorted(
            _text(element.attrib.get("name"), 500)
            for element in layers
            if _text(element.attrib.get("name"), 500)
        )
        kind_counts: dict[str, int] = {}
        for element in layers:
            kind = _text(element.attrib.get("nodetype"), 100)
            if kind:
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
        facts: dict[str, Any] = {
            "format": "kra",
            "entry_count": len(names),
            "entries": names[:MAX_TAGS],
            "entries_truncated": len(names) > MAX_TAGS,
            "has_maindoc": bool(main_raw),
            "has_documentinfo": bool(info_raw),
            "has_preview": "preview.png" in names,
            "has_mergedimage": "mergedimage.png" in names,
            "layer_count": len(layers),
            "layer_names": layer_names[:MAX_TAGS],
            "layer_list_truncated": len(layer_names) > MAX_TAGS,
            "kind_counts": dict(sorted(kind_counts.items())),
            "document_info": info_values,
        }
        if image is not None:
            for key in ("width", "height", "colorspacename", "profile", "name", "mime"):
                value = image.attrib.get(key)
                if value not in (None, ""):
                    facts[key] = int(value) if key in {"width", "height"} else _text(value, 500)
            facts["krita_version"] = _text(main_root.attrib.get("kritaVersion"), 120) if main_root is not None else ""
        return _observation_result(
            "native_structure", "observed" if main_raw else "unavailable",
            {"tool": "python-zipfile+ElementTree", "version": None},
            facts if main_raw else {"format": "kra", "reason": "maindoc_missing", **facts},
        )
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        return _observation_result(
            "native_structure", "error",
            {"tool": "python-zipfile+ElementTree", "version": None},
            {"format": "kra", "reason": type(exc).__name__},
        )


def _pdf(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    del timeout
    try:
        from pypdf import PdfReader
    except ImportError:
        return _observation_result("pdf_metadata", "unavailable", {"tool": "pypdf"}, {"reason": "package_missing"})
    try:
        reader = PdfReader(str(path), strict=False)
        metadata = reader.metadata or {}
        safe_metadata = {
            _text(key, 120): _text(value, 1000)
            for key, value in sorted(metadata.items())
            if _text(key, 120) and value not in (None, "")
        }
        return _observation_result("pdf_metadata", "observed", {"tool": "pypdf", "version": _module_version("pypdf")}, {
            "pages": len(reader.pages), "metadata": safe_metadata,
        })
    except Exception as exc:
        return _observation_result("pdf_metadata", "error", {"tool": "pypdf", "version": _module_version("pypdf")}, {"reason": type(exc).__name__})


def _safe_metadata(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return _text(value, 500)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            _text(key, 120): _safe_metadata(item, depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if _text(key, 120)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_metadata(item, depth + 1) for item in list(value)[:MAX_TAGS]]
    return _text(value, 500)


def _hachoir(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    del tools, timeout
    try:
        from hachoir.metadata import extractMetadata
        from hachoir.parser import createParser
    except ImportError:
        return _observation_result("binary_metadata", "unavailable", {"tool": "hachoir"}, {"reason": "package_missing"})
    parser = None
    try:
        parser = createParser(str(path))
        if parser is None:
            return None
        with parser:
            metadata = extractMetadata(parser)
        fields = metadata.exportDictionary() if metadata is not None else {}
        if not isinstance(fields, Mapping):
            fields = {}
        return _observation_result("binary_metadata", "observed", {
            "tool": "hachoir", "version": _module_version("hachoir"),
        }, {"fields": _safe_metadata(fields)})
    except Exception as exc:
        return _observation_result("binary_metadata", "error", {
            "tool": "hachoir", "version": _module_version("hachoir"),
        }, {"reason": type(exc).__name__})


def _module_version(name: str) -> str | None:
    if name == "mutagen":
        try:
            import mutagen
            return _text(getattr(mutagen, "version_string", None), 120) or None
        except ImportError:
            return None
    try:
        module = __import__(name)
    except ImportError:
        return None
    return _text(getattr(module, "__version__", None), 120) or None


def _text_fingerprint(path: Path, artifact: Mapping[str, Any]) -> dict[str, Any] | None:
    family = str(artifact.get("family", ""))
    if family not in {"text", "data", "code"}:
        return None
    try:
        raw = path.read_bytes()[:1024 * 1024]
    except OSError as exc:
        return _observation_result("text_fingerprint", "error", {"tool": "python-stdlib"}, {"reason": type(exc).__name__})
    text = raw.decode("utf-8", errors="replace")
    return _observation_result("text_fingerprint", "observed", {"tool": "python-stdlib"}, {
        "bytes_sampled": len(raw),
        "sample_sha256": hashlib.sha256(raw).hexdigest(),
        "line_count_sample": text.count("\n") + (1 if text else 0),
        "token_count_sample": len(re.findall(r"\S+", text)),
    })


def _ocr(path: Path, tools: Mapping[str, Any], timeout: int) -> dict[str, Any] | None:
    tool = tools.get("tesseract", {})
    executable = tool.get("path")
    if not executable:
        return _observation_result("ocr_text", "unavailable", tool, {"reason": "tool_missing"})
    output, error = _run_text_tool([executable, str(path), "stdout", "--psm", "6"], timeout)
    if error:
        return _observation_result("ocr_text", "error", tool, {"reason": error})
    text = _text(output, MAX_TEXT)
    return _observation_result("ocr_text", "observed", tool, {
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "token_count": len(re.findall(r"\S+", text)),
    })


def _capabilities(artifact: Mapping[str, Any], tools: Mapping[str, Any]) -> list[dict[str, Any]]:
    family = str(artifact.get("family", "unknown"))
    suffix = PurePosixPath(str(artifact.get("relative_path", ""))).suffix.casefold()
    capabilities: list[tuple[str, str, str | None]] = [("backup", "possible", None), ("version", "possible", None)]
    if family in {"image", "video", "audio", "document"}:
        capabilities.append(("preview", "possible", None))
    if family == "image":
        capabilities.extend([
            ("ocr", "possible" if tools.get("tesseract", {}).get("path") else "unsupported", "tesseract"),
            ("semantic_search", "possible" if tools.get("imagehash", {}).get("available") else "unsupported", "ImageHash"),
            ("duplicate_retrieval", "possible" if tools.get("czkawka", {}).get("path") else "unsupported", "czkawka"),
        ])
    if family in {"video", "audio"}:
        capabilities.append(("transcribe", "possible" if tools.get("ffmpeg", {}).get("path") else "unsupported", "ffmpeg"))
        capabilities.append(("semantic_search", "possible" if tools.get("ffprobe", {}).get("path") else "unsupported", "ffprobe"))
    if family == "video":
        capabilities.append(("duplicate_retrieval", "possible" if tools.get("czkawka", {}).get("path") else "unsupported", "czkawka"))
    if family == "document":
        capabilities.append(("ocr", "possible" if tools.get("tesseract", {}).get("path") else "unsupported", "tesseract"))
        capabilities.append(("semantic_search", "possible" if tools.get("pypdf", {}).get("available") else "unsupported", "pypdf"))
    if suffix == ".psd":
        capabilities.append(("inspect_native_structure", "possible" if tools.get("psd_tools", {}).get("available") else "unsupported", "psd-tools"))
    elif suffix == ".kra":
        capabilities.append(("inspect_native_structure", "possible", "python-zipfile+ElementTree"))
    return [
        {"capability": name, "status": status, "provider": provider}
        for name, status, provider in sorted(capabilities)
    ]


def _tool_inventory(exiftool: str | None = None) -> dict[str, dict[str, Any]]:
    names = {name: _tool_path(name, exiftool if name == "exiftool" else None) for name in (
        "exiftool", "ffprobe", "ffmpeg", "tesseract", "file", "czkawka",
    )}
    inventory: dict[str, dict[str, Any]] = {}
    for name, path in names.items():
        inventory[name] = {"path_available": bool(path), "path": path, "version": _tool_version(name, path)}
    inventory["imagehash"] = {"available": _module_version("imagehash") is not None, "version": _module_version("imagehash")}
    inventory["pypdf"] = {"available": _module_version("pypdf") is not None, "version": _module_version("pypdf")}
    inventory["mutagen"] = {"available": _module_version("mutagen") is not None, "version": _module_version("mutagen")}
    inventory["hachoir"] = {"available": _module_version("hachoir") is not None, "version": _module_version("hachoir")}
    inventory["psd_tools"] = {"available": _module_version("psd_tools") is not None, "version": _module_version("psd_tools")}
    return inventory


def _safe_path(root: Path, relative_path: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative_path).parts)
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    if not candidate_resolved.is_relative_to(root_resolved):
        raise ArchiveToolchainError("artifact_path_escapes_root")
    return candidate


def inspect_archive_projection(
    projection: Mapping[str, Any],
    *,
    root: str | os.PathLike[str],
    artifact_refs: Sequence[str] | None = None,
    ocr: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    exiftool: str | None = None,
) -> dict[str, Any]:
    """Inspect listed projection artifacts with installed open-source tools.

    ``root`` is only a path resolver.  The function never enumerates it; every
    inspected path must already be present in the accepted projection.
    """
    archive_id, snapshot_id, input_hash, artifacts = _validate_projection(
        projection, allow_large=artifact_refs is not None,
    )
    if not isinstance(root, (str, os.PathLike)):
        raise ArchiveToolchainError("root_required")
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        raise ArchiveToolchainError("root_not_directory")
    selected = _selected_artifacts(artifacts, artifact_refs)
    tools = _tool_inventory(exiftool)
    observations: list[dict[str, Any]] = []
    capability_rows: list[dict[str, Any]] = []
    skipped = 0
    errors = 0
    for artifact in selected:
        ref = str(artifact["artifact_ref"])
        kind = str(artifact.get("kind", "unknown"))
        method_base = {"tool": "archive-toolchain", "algorithm_version": ALGORITHM_VERSION}
        if kind != "file" or str(artifact.get("availability", "")) != "available":
            observations.append(_observation(
                archive_id, snapshot_id, artifact, "tool_inspection", "unavailable", method_base,
                {}, "artifact_not_available_file",
            ))
            skipped += 1
            continue
        path = _safe_path(root_path, str(artifact["relative_path"]))
        try:
            stat_result = path.lstat()
        except OSError as exc:
            observations.append(_observation(
                archive_id, snapshot_id, artifact, "tool_inspection", "error", method_base,
                {}, type(exc).__name__,
            ))
            errors += 1
            continue
        if not path.is_file() or path.is_symlink():
            observations.append(_observation(
                archive_id, snapshot_id, artifact, "tool_inspection", "unavailable", method_base,
                {}, "runtime_path_not_regular_file",
            ))
            skipped += 1
            continue
        del stat_result
        per_artifact: list[dict[str, Any] | None] = []
        per_artifact.append(_file_signature(path, artifact, tools, timeout))
        per_artifact.append(_exiftool(path, tools, timeout))
        family = str(artifact.get("family", ""))
        if family in {"audio", "video"}:
            per_artifact.append(_ffprobe(path, tools, timeout))
        if family == "audio":
            per_artifact.append(_mutagen(path, tools, timeout))
        if family == "image":
            per_artifact.append(_image(path, tools, timeout))
            if ocr:
                per_artifact.append(_ocr(path, tools, timeout))
        suffix = PurePosixPath(str(artifact["relative_path"])).suffix.casefold()
        if suffix == ".psd":
            per_artifact.append(_psd(path, tools, timeout))
        elif suffix == ".kra":
            per_artifact.append(_kra(path, tools, timeout))
        if family == "document" and str(artifact.get("media_type")) == "application/pdf":
            per_artifact.append(_pdf(path, tools, timeout))
        per_artifact.append(_hachoir(path, tools, timeout))
        per_artifact.append(_text_fingerprint(path, artifact))
        for result in per_artifact:
            if not result:
                continue
            row = _observation(
                archive_id, snapshot_id, artifact,
                str(result["observation_type"]), str(result["status"]),
                result["method"], result["facts"],
            )
            observations.append(row)
            if row["status"] == "error":
                errors += 1
        for capability in _capabilities(artifact, tools):
            capability_rows.append({"artifact_ref": ref, **capability})
    observations.extend(_surface_match_observations(archive_id, snapshot_id, observations))
    observations.sort(key=lambda row: row["observation_id"])
    capability_rows.sort(key=lambda row: (row["artifact_ref"], row["capability"], row["status"]))
    reconciliation = {
        "artifacts_input": len(artifacts),
        "artifacts_selected": len(selected),
        "artifacts_covered": len({row["artifact_ref"] for row in observations}),
        "artifacts_inspected": len({row["artifact_ref"] for row in observations}) - skipped,
        "observations_emitted": len(observations),
        "surface_matches_emitted": sum(
            row.get("observation_type") == "surface_match_retrieval" for row in observations
        ),
        "observation_ids_unique": len({row["observation_id"] for row in observations}) == len(observations),
        "skipped_artifacts": skipped,
        "tool_errors": errors,
        "artifact_loss": len(selected) - len({row["artifact_ref"] for row in observations}),
        "status": "complete" if errors == 0 else "complete_with_tool_errors",
    }
    output = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "source_projection_schema": PROJECTION_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "tool_inventory": tools,
        "observations": observations,
        "capabilities": capability_rows,
        "control": {
            "read_only": True,
            "source_mutation": False,
            "database_write": False,
            "promotion": "none",
            "artistic_truth": False,
        },
        "reconciliation": reconciliation,
        "provenance": {
            "root_used_as_resolver_only": True,
            "artifact_selection": "accepted_projection_only",
            "evidence_binding": "artifact_ref",
        },
    }
    _json_surface(output)
    return output


def ingest_czkawka_duplicate_report(
    output: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Attach a Czkawka duplicate report to an existing observation bundle.

    Czkawka scans directories rather than an explicit projection.  Therefore
    this boundary accepts its report only when every member of a duplicate
    group resolves to a physical artifact already present in ``output``.
    Unknown paths are skipped as external-to-selection groups; they never
    become MAK endpoints.  The report's hash is retained as a tool fact, not
    promoted to ``content_id`` or artwork identity.
    """
    validate_toolchain_output(output)
    if not isinstance(report, Mapping):
        raise ArchiveToolchainError("czkawka_report_not_object")
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        raise ArchiveToolchainError("root_not_directory")
    base = copy.deepcopy(dict(output))
    by_path = {
        os.path.abspath(os.fspath(root_path / PurePosixPath(str(row["relative_path"])))): str(row["artifact_ref"])
        for row in base["observations"]
        if row.get("status") != "unavailable"
    }
    version = _text(base.get("tool_inventory", {}).get("czkawka", {}).get("version"), 120) or "unknown"
    existing_groups: set[str] = set()
    new_rows: list[dict[str, Any]] = []
    skipped_groups = 0
    for size_key in sorted(report, key=str):
        groups = report[size_key]
        if not isinstance(groups, list):
            raise ArchiveToolchainError("czkawka_report_groups_invalid")
        for group in groups:
            if not isinstance(group, list) or len(group) < 2:
                raise ArchiveToolchainError("czkawka_report_group_invalid")
            members: list[tuple[str, str, int]] = []
            for entry in group:
                if not isinstance(entry, Mapping):
                    raise ArchiveToolchainError("czkawka_report_member_invalid")
                raw_path = entry.get("path")
                raw_hash = _text(entry.get("hash"), 200)
                raw_size = entry.get("size")
                if not isinstance(raw_path, str) or not os.path.isabs(raw_path):
                    raise ArchiveToolchainError("czkawka_report_path_invalid")
                if not raw_hash or not isinstance(raw_size, int) or raw_size < 0:
                    raise ArchiveToolchainError("czkawka_report_member_identity_invalid")
                ref = by_path.get(os.path.abspath(raw_path))
                if ref is None:
                    members = []
                    break
                members.append((ref, raw_hash, raw_size))
            if not members or len({item[0] for item in members}) < 2:
                skipped_groups += 1
                continue
            members.sort(key=lambda item: item[0])
            member_refs = [item[0] for item in members]
            hashes = {item[1] for item in members}
            sizes = {item[2] for item in members}
            if len(hashes) != 1 or len(sizes) != 1:
                raise ArchiveToolchainError("czkawka_report_group_inconsistent")
            group_id = _digest({
                "tool": "czkawka", "hash_type": "BLAKE3", "hash": next(iter(hashes)),
                "size": next(iter(sizes)), "member_refs": member_refs,
            })[7:]
            if group_id in existing_groups:
                continue
            existing_groups.add(group_id)
            facts = {
                "group_id": "czkawka-group:" + group_id,
                "group_hash": next(iter(hashes)),
                "hash_type": "BLAKE3",
                "size": next(iter(sizes)),
                "member_refs": member_refs,
            }
            method = {"tool": "czkawka", "version": version, "mode": "duplicates"}
            for ref, _hash, _size in members:
                artifact = {"artifact_ref": ref, "relative_path": next(
                    row["relative_path"] for row in base["observations"] if row["artifact_ref"] == ref
                )}
                new_rows.append(_observation(
                    str(base["archive_id"]), str(base["snapshot_id"]), artifact,
                    "duplicate_retrieval", "observed", method, facts,
                ))
    base["observations"] = sorted(
        [*base["observations"], *new_rows],
        key=lambda row: str(row["observation_id"]),
    )
    inventory = copy.deepcopy(base.get("tool_inventory", {}))
    inventory["czkawka"] = {
        **dict(inventory.get("czkawka", {})),
        "invoked": True,
        "mode": "duplicates",
    }
    base["tool_inventory"] = inventory
    reconciliation = dict(base["reconciliation"])
    reconciliation["observations_emitted"] = len(base["observations"])
    reconciliation["observation_ids_unique"] = len({
        row["observation_id"] for row in base["observations"]
    }) == len(base["observations"])
    reconciliation["czkawka_groups"] = len(existing_groups)
    reconciliation["czkawka_member_refs"] = len({
        ref for row in new_rows for ref in row["facts"]["member_refs"]
    })
    reconciliation["czkawka_skipped_groups"] = skipped_groups
    base["reconciliation"] = reconciliation
    provenance = dict(base.get("provenance", {}))
    provenance["czkawka_report_ingested"] = True
    provenance["duplicate_identity_policy"] = "tool_hash_is_evidence_not_content_id"
    base["provenance"] = provenance
    validate_toolchain_output(base)
    return base


def ingest_czkawka_similarity_report(
    output: Mapping[str, Any],
    report: Sequence[Any],
    *,
    root: str | os.PathLike[str],
    mode: str,
    max_difference: float = 10.0,
) -> dict[str, Any]:
    """Attach Czkawka image/video similarity groups to an observation bundle.

    The report is accepted only for already selected physical artifacts.  The
    numeric difference is preserved as a retrieval feature; the derived
    similarity score is not a confidence value and never promotes a work,
    version, authorship or publication relation.
    """
    validate_toolchain_output(output)
    if mode not in {"image", "video"}:
        raise ArchiveToolchainError("czkawka_similarity_mode_invalid")
    if not isinstance(report, list):
        raise ArchiveToolchainError("czkawka_similarity_report_not_list")
    if not isinstance(max_difference, (int, float)) or not math.isfinite(float(max_difference)) or max_difference <= 0:
        raise ArchiveToolchainError("czkawka_similarity_threshold_invalid")
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        raise ArchiveToolchainError("root_not_directory")
    base = copy.deepcopy(dict(output))
    by_path = {
        os.path.abspath(os.fspath(root_path / PurePosixPath(str(row["relative_path"])))): str(row["artifact_ref"])
        for row in base["observations"]
        if row.get("status") != "unavailable"
    }
    version = _text(base.get("tool_inventory", {}).get("czkawka", {}).get("version"), 120) or "unknown"
    group_ids: set[str] = set()
    new_rows: list[dict[str, Any]] = []
    skipped_groups = 0
    for group in report:
        if not isinstance(group, list) or len(group) < 2:
            raise ArchiveToolchainError("czkawka_similarity_group_invalid")
        members: list[tuple[str, float | None]] = []
        for entry in group:
            if not isinstance(entry, Mapping):
                raise ArchiveToolchainError("czkawka_similarity_member_invalid")
            raw_path = entry.get("path")
            difference = entry.get("difference")
            if not isinstance(raw_path, str) or not os.path.isabs(raw_path):
                raise ArchiveToolchainError("czkawka_similarity_path_invalid")
            if mode == "image" and (
                not isinstance(difference, (int, float))
                or not math.isfinite(float(difference))
            ):
                raise ArchiveToolchainError("czkawka_similarity_difference_invalid")
            if mode == "video" and difference is not None and (
                not isinstance(difference, (int, float))
                or not math.isfinite(float(difference))
            ):
                raise ArchiveToolchainError("czkawka_similarity_difference_invalid")
            ref = by_path.get(os.path.abspath(raw_path))
            if ref is None:
                members = []
                break
            members.append((ref, float(difference) if difference is not None else None))
        if not members or len({item[0] for item in members}) < 2:
            skipped_groups += 1
            continue
        members.sort(key=lambda item: item[0])
        member_refs = [item[0] for item in members]
        differences = [item[1] for item in members if item[1] is not None]
        difference = max(differences) if differences else None
        group_id = _digest({
            "tool": "czkawka", "mode": mode, "member_refs": member_refs,
            "difference": difference, "max_difference": float(max_difference),
        })[7:]
        if group_id in group_ids:
            continue
        group_ids.add(group_id)
        facts = {
            "group_id": "czkawka-similarity-group:" + group_id,
            "member_refs": member_refs,
            "difference": difference,
            "max_difference": float(max_difference),
            "similarity_score": (
                max(0.0, min(1.0, 1.0 - difference / float(max_difference)))
                if difference is not None else None
            ),
            "mode": mode,
            "comparison": "perceptual_difference" if mode == "image" else "temporal_visual_signature",
        }
        method = {
            "tool": "czkawka", "version": version, "mode": mode,
            "max_difference": float(max_difference),
        }
        relative_by_ref = {
            str(row["artifact_ref"]): str(row["relative_path"])
            for row in base["observations"]
        }
        for ref, _difference in members:
            new_rows.append(_observation(
                str(base["archive_id"]), str(base["snapshot_id"]),
                {"artifact_ref": ref, "relative_path": relative_by_ref[ref]},
                "similarity_retrieval", "observed", method, facts,
            ))
    base["observations"] = sorted(
        [*base["observations"], *new_rows],
        key=lambda row: str(row["observation_id"]),
    )
    inventory = copy.deepcopy(base.get("tool_inventory", {}))
    inventory["czkawka"] = {
        **dict(inventory.get("czkawka", {})), "invoked": True, "mode": mode,
    }
    base["tool_inventory"] = inventory
    reconciliation = dict(base["reconciliation"])
    reconciliation["observations_emitted"] = len(base["observations"])
    reconciliation["observation_ids_unique"] = len({
        row["observation_id"] for row in base["observations"]
    }) == len(base["observations"])
    reconciliation["czkawka_similarity_groups"] = len(group_ids)
    reconciliation["czkawka_similarity_member_refs"] = len({
        ref for row in new_rows for ref in row["facts"]["member_refs"]
    })
    reconciliation["czkawka_similarity_skipped_groups"] = skipped_groups
    base["reconciliation"] = reconciliation
    provenance = dict(base.get("provenance", {}))
    provenance["czkawka_similarity_report_ingested"] = True
    provenance["similarity_identity_policy"] = "retrieval_score_is_not_artistic_confidence"
    base["provenance"] = provenance
    validate_toolchain_output(base)
    return base


def validate_toolchain_output(output: Mapping[str, Any]) -> bool:
    """Strictly validate this adapter's output without reading the filesystem."""
    if not isinstance(output, Mapping) or output.get("schema") != SCHEMA:
        raise ArchiveToolchainError("toolchain_output_bad_schema")
    for key in ("archive_id", "snapshot_id", "input_hash", "algorithm_version"):
        if not _text(output.get(key), 500):
            raise ArchiveToolchainError("toolchain_output_identity_incomplete")
    observations = output.get("observations")
    if not isinstance(observations, list):
        raise ArchiveToolchainError("toolchain_observations_not_list")
    refs: set[str] = set()
    ids: set[str] = set()
    for row in observations:
        if not isinstance(row, Mapping):
            raise ArchiveToolchainError("tool_observation_not_object")
        required = {"observation_id", "artifact_ref", "relative_path", "observation_type", "status", "method", "evidence_refs", "facts"}
        if set(row) != required:
            raise ArchiveToolchainError("tool_observation_field_set_invalid")
        observation_id = _text(row.get("observation_id"), 500)
        ref = _text(row.get("artifact_ref"), 500)
        if not observation_id.startswith("tool-observation:") or not ref:
            raise ArchiveToolchainError("tool_observation_identity_invalid")
        if row.get("status") not in {"observed", "unavailable", "error"}:
            raise ArchiveToolchainError("tool_observation_status_invalid")
        if row.get("evidence_refs") != [ref]:
            raise ArchiveToolchainError("tool_observation_evidence_unbound")
        if not isinstance(row.get("method"), Mapping) or not isinstance(row.get("facts"), Mapping):
            raise ArchiveToolchainError("tool_observation_payload_invalid")
        if observation_id in ids:
            raise ArchiveToolchainError("duplicate_tool_observation_id")
        expected_id = _observation_id(
            str(output["archive_id"]), str(output["snapshot_id"]), ref,
            str(row["observation_type"]), row["method"], row["facts"],
        )
        if observation_id != expected_id:
            raise ArchiveToolchainError("tool_observation_id_mismatch")
        relative_path = str(row["relative_path"])
        if not relative_path or relative_path.startswith("/") or "\\" in relative_path:
            raise ArchiveToolchainError("tool_observation_path_invalid")
        ids.add(observation_id)
        refs.add(ref)
    if observations != sorted(observations, key=lambda row: str(row["observation_id"])):
        raise ArchiveToolchainError("tool_observations_not_deterministic")
    reconciliation = output.get("reconciliation")
    if not isinstance(reconciliation, Mapping) or reconciliation.get("observation_ids_unique") is not True:
        raise ArchiveToolchainError("tool_reconciliation_invalid")
    _json_surface(dict(output))
    return True


def _observation_index(output: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    by_ref: dict[str, list[Mapping[str, Any]]] = {}
    for row in output["observations"]:
        by_ref.setdefault(str(row["artifact_ref"]), []).append(row)
    for rows in by_ref.values():
        rows.sort(key=lambda row: str(row["observation_id"]))
    return dict(sorted(by_ref.items()))


def _dimensions(row: Mapping[str, Any]) -> tuple[int, int] | None:
    facts = row.get("facts", {})
    if not isinstance(facts, Mapping):
        return None
    if row.get("observation_type") == "image_features":
        width, height = facts.get("width"), facts.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            return width, height
    if row.get("observation_type") == "media_streams":
        streams = facts.get("streams", [])
        if isinstance(streams, list):
            for stream in streams:
                if not isinstance(stream, Mapping) or stream.get("codec_type") != "video":
                    continue
                width, height = stream.get("width"), stream.get("height")
                if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
                    return width, height
    return None


def _technical_media_families(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return observed media families without treating names as identity.

    The context projection has a deliberately weak fallback that compares a
    shared local name token and dimensions.  That fallback is useful for a
    still and its video rendition, but it is noisy for numbered image siblings
    such as ``Isotipo-01.png`` through ``Isotipo-05.png``.  Keep the
    observation rows themselves intact and use this family signal only to
    decide whether that weak context edge is warranted.
    """
    families: set[str] = set()
    for row in rows:
        observation_type = row.get("observation_type")
        facts = row.get("facts", {})
        if observation_type == "image_features":
            families.add("image")
            continue
        if observation_type != "media_streams" or not isinstance(facts, Mapping):
            continue
        streams = facts.get("streams", [])
        if not isinstance(streams, list):
            continue
        for stream in streams:
            if not isinstance(stream, Mapping):
                continue
            codec_type = stream.get("codec_type")
            if codec_type in {"audio", "video"}:
                families.add(str(codec_type))
    return families


def _surface_phash_distance(left: Any, right: Any) -> int | None:
    if not isinstance(left, str) or not isinstance(right, str):
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except (TypeError, ValueError):
        return None


def _surface_hash_informative(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return len(set(value.casefold())) > 1


def _surface_path_tokens(relative_path: str) -> set[str]:
    path = PurePosixPath(relative_path)
    return _surface_tokens(path.stem) | _surface_tokens(path.parent.as_posix())


def _surface_token_overlap(native_tokens: Sequence[str], relative_path: str) -> list[str]:
    path_tokens = _surface_path_tokens(relative_path)
    overlap = {
        token
        for token in path_tokens
        if len(token) >= 4 and any(
            token == native or token in native or native in token
            for native in native_tokens
            if len(native) >= 4
        )
    }
    return sorted(overlap)


def _surface_asset_path(relative_path: str) -> bool:
    stem_tokens = _surface_tokens(PurePosixPath(relative_path).stem)
    return bool(stem_tokens.intersection({"logo", "isotipo", "brand", "icon", "mark", "asset"}))


def _surface_match_observations(
    archive_id: str,
    snapshot_id: str,
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Find bounded native-layer to raster retrieval matches.

    A match is a technical edge between a native document and an explicitly
    selected raster artifact.  Text-token overlap is admitted only for
    asset-like filenames; otherwise the edge requires a perceptual hash match.
    This prevents a shared artist/client token from becoming a project claim.
    """
    native_rows = [
        row for row in observations
        if row.get("observation_type") == "native_structure" and row.get("status") == "observed"
    ]
    image_rows = [
        row for row in observations
        if row.get("observation_type") == "image_features" and row.get("status") == "observed"
    ]
    rows: list[dict[str, Any]] = []
    for native in sorted(native_rows, key=lambda row: str(row.get("artifact_ref", ""))):
        facts = native.get("facts", {})
        if not isinstance(facts, Mapping):
            continue
        components = facts.get("surface_components", [])
        if not isinstance(components, list):
            components = []
        native_tokens = facts.get("surface_tokens", [])
        if not isinstance(native_tokens, list):
            native_tokens = []
        for target in sorted(image_rows, key=lambda row: str(row.get("artifact_ref", ""))):
            if target.get("artifact_ref") == native.get("artifact_ref"):
                continue
            target_facts = target.get("facts", {})
            if not isinstance(target_facts, Mapping):
                continue
            best: tuple[int, Mapping[str, Any]] | None = None
            target_phash = target_facts.get("phash")
            for component in components:
                if not isinstance(component, Mapping):
                    continue
                distance = _surface_phash_distance(component.get("phash"), target_phash)
                if distance is None:
                    continue
                candidate = (distance, component)
                if best is None or (distance, str(component.get("component_id", ""))) < (
                    best[0], str(best[1].get("component_id", ""))
                ):
                    best = candidate
            token_overlap = _surface_token_overlap(native_tokens, str(target.get("relative_path", "")))
            signals: list[str] = []
            visual_distance = (
                _surface_phash_distance(best[1].get("phash"), target_facts.get("phash"))
                if best is not None else None
            )
            dhash_distance = (
                _surface_phash_distance(best[1].get("dhash"), target_facts.get("dhash"))
                if best is not None else None
            )
            visual_match = (
                best is not None
                and visual_distance is not None
                and visual_distance <= SURFACE_PHASH_DISTANCE
                and dhash_distance is not None
                and dhash_distance <= 12
                and _surface_hash_informative(best[1].get("dhash"))
                and _surface_hash_informative(target_facts.get("dhash"))
            )
            if visual_match:
                signals.append("perceptual_surface_similarity")
            if token_overlap and _surface_asset_path(str(target.get("relative_path", ""))):
                signals.append("native_text_asset_token_overlap")
            if not signals:
                continue
            visual_component = (
                best[1]
                if visual_match
                else {}
            )
            match_facts = {
                "target_ref": str(target["artifact_ref"]),
                "component_id": visual_component.get("component_id"),
                "component_name": visual_component.get("name"),
                "signals": sorted(signals),
                "phash_distance": visual_distance if visual_component else None,
                "dhash_distance": dhash_distance if visual_component else None,
                "token_overlap": token_overlap,
                "comparison": "native_surface_retrieval",
                "truth_promotion": False,
                "physical_merge": False,
            }
            artifact = {
                "artifact_ref": str(native["artifact_ref"]),
                "relative_path": str(native["relative_path"]),
            }
            rows.append(_observation(
                archive_id, snapshot_id, artifact, "surface_match_retrieval", "observed",
                {"tool": "archive-toolchain", "algorithm_version": ALGORITHM_VERSION},
                match_facts,
            ))
            if len(rows) >= MAX_SURFACE_MATCHES:
                return sorted(rows, key=lambda row: str(row["observation_id"]))
    return sorted(rows, key=lambda row: str(row["observation_id"]))


def _parent_and_tokens(relative_path: str) -> tuple[str, set[str]]:
    path = PurePosixPath(relative_path)
    tokens = {
        token.casefold()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", path.stem)
    }
    return ("" if path.parent.as_posix() == "." else path.parent.as_posix()), tokens


def _technical_sources(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(str(row["observation_id"]) for row in rows if row.get("status") == "observed")


def project_tool_observations_to_context(output: Mapping[str, Any]) -> dict[str, Any]:
    """Project technical observations into the existing context graph contract.

    This is a read-only graph projection.  It creates only physical-artifact
    entities, technical source cards and candidate technical matches.  It does
    not create projects or claim that a technical match is the same artwork.
    """
    validate_toolchain_output(output)
    archive_id = str(output["archive_id"])
    snapshot_id = str(output["snapshot_id"])
    by_ref = _observation_index(output)
    entity_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    artifact_meta: dict[str, tuple[str, set[str]]] = {}
    for ref, rows in by_ref.items():
        relative_path = str(rows[0]["relative_path"])
        parent, tokens = _parent_and_tokens(relative_path)
        artifact_meta[ref] = (parent, tokens)
        entity_rows.append({
            "entity_id": ref,
            "kind": "physical_artifact",
            "display_name": relative_path,
            "status": "observed",
            "origin": "archive_toolchain",
        })
        for row in rows:
            source_rows.append({
                "source_id": row["observation_id"],
                "source_type": "technical_tool_observation",
                "independence_group": "tool:" + str(row["method"].get("tool", "unknown")),
                "locator": ref,
                "claim": "technical_observation:" + str(row["observation_type"]),
                "status": "observed" if row["status"] == "observed" else "candidate",
                "metadata": {
                    "artifact_ref": ref,
                    "relative_path": relative_path,
                    "status": row["status"],
                    "method": dict(row["method"]),
                    "facts": dict(row["facts"]),
                },
            })

    relation_rows: list[dict[str, Any]] = []
    refs = sorted(by_ref)
    dimension_by_ref: dict[str, list[tuple[Mapping[str, Any], tuple[int, int]]]] = {}
    media_families_by_ref: dict[str, set[str]] = {}
    for ref, rows in by_ref.items():
        dimension_by_ref[ref] = [
            (row, dimensions)
            for row in rows
            if (dimensions := _dimensions(row)) is not None
        ]
        media_families_by_ref[ref] = _technical_media_families(rows)
    for index, left_ref in enumerate(refs):
        for right_ref in refs[index + 1:]:
            left_parent, left_tokens = artifact_meta[left_ref]
            right_parent, right_tokens = artifact_meta[right_ref]
            if left_parent != right_parent or not left_tokens.intersection(right_tokens):
                continue
            # A shared local token and canvas size is only a useful fallback
            # when it bridges different media families (for example a PNG
            # still and an MP4 rendition).  Same-family siblings are commonly
            # numbered variants, frames or exports; the dedicated duplicate,
            # sequence and surface-retrieval observations carry those signals
            # without manufacturing a second weak relation for every pair.
            left_families = media_families_by_ref[left_ref]
            right_families = media_families_by_ref[right_ref]
            if not left_families or not right_families or left_families == right_families:
                continue
            shared_dimensions = {
                dimensions
                for _left_row, dimensions in dimension_by_ref[left_ref]
                for _right_row, right_dimensions in dimension_by_ref[right_ref]
                if dimensions == right_dimensions
            }
            if not shared_dimensions:
                continue
            left_sources = _technical_sources([row for row, _ in dimension_by_ref[left_ref]])
            right_sources = _technical_sources([row for row, _ in dimension_by_ref[right_ref]])
            source_ids = sorted(set(left_sources + right_sources))
            if len(source_ids) < 2:
                continue
            relation_rows.append({
                "subject": left_ref,
                "predicate": "technical_media_match_candidate",
                "object": right_ref,
                "status": "candidate",
                "source_ids": source_ids,
                "metadata": {
                    "signals": ["shared_local_parent", "shared_name_token", "shared_dimensions"],
                    "dimensions": [list(item) for item in sorted(shared_dimensions)],
                    "truth_promotion": False,
                },
            })
    for observation_type, predicate, signal in (
        ("duplicate_retrieval", "technical_duplicate_candidate", "exact_duplicate_tool_hash"),
        ("similarity_retrieval", "technical_similarity_candidate", "visual_similarity_retrieval"),
    ):
        groups: dict[str, set[str]] = {}
        for ref, rows in by_ref.items():
            for row in rows:
                if row.get("observation_type") != observation_type or row.get("status") != "observed":
                    continue
                facts = row.get("facts", {})
                if not isinstance(facts, Mapping):
                    continue
                group_id = _text(facts.get("group_id"), 200)
                member_refs = facts.get("member_refs")
                if not group_id or not isinstance(member_refs, list):
                    continue
                if all(isinstance(item, str) and item in by_ref for item in member_refs):
                    groups.setdefault(group_id, set()).update(member_refs)
        for group_id, group_refs in sorted(groups.items()):
            ordered_refs = sorted(group_refs)
            for left_index, left_ref in enumerate(ordered_refs):
                for right_ref in ordered_refs[left_index + 1:]:
                    if len(relation_rows) >= MAX_CONTEXT_RELATIONS:
                        break
                    left_rows = [
                        row for row in by_ref[left_ref]
                        if row.get("observation_type") == observation_type
                        and row.get("status") == "observed"
                        and row.get("facts", {}).get("group_id") == group_id
                    ]
                    right_rows = [
                        row for row in by_ref[right_ref]
                        if row.get("observation_type") == observation_type
                        and row.get("status") == "observed"
                        and row.get("facts", {}).get("group_id") == group_id
                    ]
                    source_ids = sorted({
                        str(row["observation_id"])
                        for row in [*left_rows, *right_rows]
                    })
                    if not source_ids:
                        continue
                    metadata = {
                        "signals": [signal], "group_id": group_id,
                        "physical_merge": False, "truth_promotion": False,
                    }
                    if observation_type == "similarity_retrieval":
                        values = [
                            row.get("facts", {}).get("similarity_score")
                            for row in [*left_rows, *right_rows]
                            if isinstance(row.get("facts", {}).get("similarity_score"), (int, float))
                        ]
                        if values:
                            metadata["similarity_score"] = min(values)
                    relation_rows.append({
                        "subject": left_ref, "predicate": predicate,
                        "object": right_ref, "status": "candidate",
                        "source_ids": source_ids, "metadata": metadata,
                    })
                if len(relation_rows) >= MAX_CONTEXT_RELATIONS:
                    break
    for row in output["observations"]:
        if row.get("observation_type") != "surface_match_retrieval" or row.get("status") != "observed":
            continue
        facts = row.get("facts", {})
        if not isinstance(facts, Mapping):
            continue
        target_ref = facts.get("target_ref")
        source_ref = row.get("artifact_ref")
        if not isinstance(target_ref, str) or target_ref not in by_ref or target_ref == source_ref:
            continue
        relation_rows.append({
            "subject": str(source_ref),
            "predicate": "technical_surface_match_candidate",
            "object": target_ref,
            "status": "candidate",
            "source_ids": [str(row["observation_id"])],
            "metadata": {
                "signals": list(facts.get("signals", [])),
                "component_id": facts.get("component_id"),
                "component_name": facts.get("component_name"),
                "phash_distance": facts.get("phash_distance"),
                "token_overlap": list(facts.get("token_overlap", [])),
                "physical_merge": False,
                "truth_promotion": False,
            },
        })
    context_id = "tool-context:" + _digest({
        "archive_id": archive_id, "snapshot_id": snapshot_id, "input_hash": output["input_hash"],
        "observations": output["observations"],
    })[7:]
    package = {
        "schema": PROJECT_CONTEXT_SCHEMA,
        "context_id": context_id,
        "title": "Technical archive observations " + archive_id,
        "scope": "archive_technical_observations",
        "entities": sorted(entity_rows, key=lambda row: row["entity_id"]),
        "sources": sorted(source_rows, key=lambda row: row["source_id"]),
        "relations": sorted(relation_rows, key=lambda row: (row["subject"], row["predicate"], row["object"])),
        "projects": [],
        "provenance": {
            "source_schema": SCHEMA,
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "input_hash": output["input_hash"],
            "control": {"read_only": True, "truth_promotion": False, "project_creation": False},
        },
    }
    errors = validate_context(package)
    if errors:
        raise ArchiveToolchainError("context_projection_invalid:" + ",".join(errors))
    return package


def record_tool_observations(store: LearningStore, output: Mapping[str, Any]) -> str:
    """Persist one idempotent observation bundle in the existing ledger."""
    validate_toolchain_output(output)
    material = {key: output[key] for key in (
        "schema", "algorithm_version", "source_projection_schema", "archive_id", "snapshot_id", "input_hash",
        "tool_inventory", "observations", "capabilities", "control", "reconciliation", "provenance",
    )}
    event_id = "archive-tools:" + _digest(material)[7:]
    event = {
        "event_id": event_id,
        "archive_id": output["archive_id"],
        "proposition_id": "archive-tools:" + str(output["snapshot_id"]),
        "event_type": EVENT_TYPE,
        "schema": SCHEMA,
        "snapshot_id": output["snapshot_id"],
        "input_hash": output["input_hash"],
        "toolchain": material,
        "control": {"database_write": True, "source_mutation": False, "promotion": "none"},
    }
    return store.append_operational_event(event)


def serialize_output(output: Mapping[str, Any], *, indent: int | None = None) -> str:
    validate_toolchain_output(output)
    return json.dumps(output, ensure_ascii=False, sort_keys=True, indent=indent, separators=None if indent is not None else (",", ":"), allow_nan=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projection", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--artifact-ref", action="append", default=None)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--exiftool", default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--czkawka-report", type=Path, default=None)
    parser.add_argument(
        "--czkawka-mode", choices=("duplicates", "image", "video"),
        default="duplicates",
    )
    parser.add_argument(
        "--context-output", type=Path, default=None,
        help="optional mak-project-context-v1 projection from these observations",
    )
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    projection = json.loads(args.projection.read_text(encoding="utf-8"))
    output = inspect_archive_projection(
        projection, root=args.root, artifact_refs=args.artifact_ref, ocr=args.ocr,
        timeout=args.timeout, exiftool=args.exiftool,
    )
    if args.czkawka_report:
        report = json.loads(args.czkawka_report.read_text(encoding="utf-8"))
        if args.czkawka_mode == "duplicates":
            output = ingest_czkawka_duplicate_report(output, report, root=args.root)
        else:
            output = ingest_czkawka_similarity_report(
                output, report, root=args.root, mode=args.czkawka_mode,
            )
    if args.db:
        record_tool_observations(LearningStore(args.db), output)
    if args.context_output:
        context = project_tool_observations_to_context(output)
        args.context_output.parent.mkdir(parents=True, exist_ok=True)
        args.context_output.write_text(
            json.dumps(
                context, ensure_ascii=False, sort_keys=True, indent=2,
                allow_nan=False,
            ) + "\n", encoding="utf-8"
        )
    rendered = serialize_output(output, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


__all__ = [
    "ALGORITHM_VERSION",
    "ArchiveToolchainError",
    "EVENT_TYPE",
    "PROJECTION_SCHEMA",
    "SCHEMA",
    "inspect_archive_projection",
    "ingest_czkawka_duplicate_report",
    "ingest_czkawka_similarity_report",
    "main",
    "project_tool_observations_to_context",
    "record_tool_observations",
    "serialize_output",
    "validate_toolchain_output",
]
