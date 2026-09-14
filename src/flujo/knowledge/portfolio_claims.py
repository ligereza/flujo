"""Claim base: what can honestly be said, at which layer, in which state.

This is a read-only projection over sources that already exist.  It scans no
archive, writes no source, opens no network and creates no second authority.

Three rules govern every claim it emits:

1. A claim belongs to exactly one of the eight layers and is never promoted
   across layers.  The absence of a relation between two files does not imply
   the absence of a relation between their contexts.
2. No route may promote the claim it generated.  ``supported_candidate``
   requires a second, independently named route.
3. ``es_mio`` and ``hice_esta_parte`` cannot exceed ``candidate`` from archive
   evidence alone; only a named third-party receipt lifts them.  A native
   project file does not imply own process: it may have arrived only to supply
   a third party's resource.

Uncertainty is paid in *scope*, not in a question to the operator: a claim
carries the narrowest scope its evidence supports.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .portfolio_format import (
    CLAIMS,
    CLAIM_STATE_CEILING,
    LAYERS,
    PERMISSION_RANK,
    STATE_RANK,
)
from .product_view import stable_json
from .screen_setup_evidence import derived_variant_groups, scan_screen_setups


SCHEMA = "mak-portfolio-claims-v1"
ALGORITHM_VERSION = "portfolio-claims-1"

# Extension families.  These are observations about file structure, never
# authorship: a container holding a native project file did not necessarily
# author what the project renders.
NATIVE_PROJECT_EXTENSIONS = {
    ".aep": "After Effects", ".blend": "Blender", ".psd": "Photoshop",
    ".prproj": "Premiere", ".ai": "Illustrator", ".c4d": "Cinema 4D",
    ".nk": "Nuke", ".hip": "Houdini", ".kra": "Krita", ".indd": "InDesign",
    ".als": "Ableton Live", ".flp": "FL Studio", ".sesx": "Audition",
    ".drp": "DaVinci Resolve", ".afdesign": "Affinity Designer",
    ".afphoto": "Affinity Photo",
}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".gif"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".heic", ".svg"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff", ".flac", ".m4a", ".ogg"}

# Reader-facing labels for a practice kind.  The internal vocabulary is for the
# projection; a document must not print "delivery" at a jury.
PRACTICE_KIND_LABEL = {
    "production": "contexto de produccion",
    "delivery": "contexto de entrega",
    "published_export": "publicaciones exportadas",
    "render_output": "salida renderizada",
    "source_footage": "material fuente",
    "installed_tool": "herramienta instalada",
    "loose_root_file": "archivo suelto",
    "system_metadata": "metadata de sistema",
    "indexed_only": "solo indexado",
}

# Structural markers of a container that is not a practice at all.
_APP_BUNDLE_SEGMENTS = {"Contents", "Plugins", "Frameworks", "Resources"}
_CAMERA_CARD_SEGMENTS = {"DCIM", "PRIVATE", "AVCHD", "CLIP", "MP_ROOT"}
# Cloud-sync scratch names.  A sync artifact is bookkeeping, not a container:
# Dropbox writes ".sb-<hex>-<rand>", and conflicted copies carry these markers.
_SYNC_MARKERS = (".sb-", ".~lock.", "conflicted copy", "Conflict)", ".tmp.drivedownload")

PRACTICE_KINDS = (
    "production",        # native project files present: production happened here
    "delivery",          # outputs without native projects
    "published_export",  # outputs named by a platform media id: manifestations
    "render_output",     # a frame sequence, not a practice
    "source_footage",    # camera-card dumps, not authored here
    "installed_tool",    # software: tool-inventory evidence, not a practice
    "loose_root_file",   # a single file at the volume root, not a container
    "system_metadata",   # filesystem bookkeeping
    "indexed_only",      # present but nothing distinguishes it
)

_MIN_SEQUENCE_RATIO = 0.9
_MIN_SEQUENCE_COUNT = 100
_MAX_CAPTION_SAMPLES = 6


class PortfolioClaimsError(ValueError):
    """Existing sources cannot support a claim base."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _ro(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise PortfolioClaimsError(f"source_missing:{path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioClaimsError(f"json_source_invalid:{path}") from exc


def _year(mtime_ns: int | None) -> int | None:
    if not mtime_ns:
        return None
    return datetime.datetime.fromtimestamp(mtime_ns / 1e9, tz=datetime.timezone.utc).year


def _plural(count: int, singular: str, plural: str) -> str:
    """Agreement matters: a client-facing document must not read as generated."""
    return f"{count} {singular if count == 1 else plural}"


def _span(first: int | None, last: int | None) -> str:
    start, end = _year(first), _year(last)
    if start is None or end is None:
        return "sin fecha observada"
    return str(start) if start == end else f"{start}–{end}"


# A frame export uses a short zero-padded counter.  A 17-digit stem is a
# platform media id, which is a publication locator, not a rendered frame.
_MAX_FRAME_DIGITS = 6
_MIN_PLATFORM_ID_DIGITS = 12
_FRAME_EXTENSIONS = IMAGE_EXTENSIONS | {".exr", ".dpx", ".tga", ".tif"}


def _numeric_stem(name: str) -> str | None:
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return stem if stem and stem.isdigit() else None


def _extension_of(name: str) -> str:
    return "." + name.rsplit(".", 1)[1].lower() if "." in name else ""


def _is_frame_sequence_member(name: str) -> bool:
    """A rendered frame: short numeric counter and a frame-image extension."""
    stem = _numeric_stem(name)
    return (
        stem is not None
        and len(stem) <= _MAX_FRAME_DIGITS
        and _extension_of(name) in _FRAME_EXTENSIONS
    )


def _is_platform_locator(name: str) -> bool:
    """A published-post export named by its platform media id."""
    stem = _numeric_stem(name)
    return stem is not None and len(stem) >= _MIN_PLATFORM_ID_DIGITS


def _container_evidence(index_path: Path) -> dict[str, dict[str, Any]]:
    """Aggregate every observable per container root, read-only."""
    con = _ro(index_path)
    try:
        containers: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "asset_count": 0,
            "bytes": 0,
            "native_tools": Counter(),
            "video_count": 0,
            "image_count": 0,
            "audio_count": 0,
            "other_count": 0,
            "media_kinds": Counter(),
            "hash_states": Counter(),
            "sequence_count": 0,
            "platform_locator_count": 0,
            "loose_root_count": 0,
            "app_bundle_hits": 0,
            "camera_card_hits": 0,
            "second_level": Counter(),
            "mtime_first": None,
            "mtime_last": None,
            "dot_prefixed": False,
        })
        for row in con.execute(
            "SELECT relative_path,extension,media_kind,bytes,mtime_ns,hash_state FROM assets"
        ):
            path = str(row["relative_path"] or "")
            if not path:
                continue
            parts = path.split("/")
            root = parts[0]
            bucket = containers[root]
            bucket["asset_count"] += 1
            bucket["bytes"] += int(row["bytes"] or 0)
            bucket["media_kinds"][str(row["media_kind"] or "")] += 1
            bucket["hash_states"][str(row["hash_state"] or "")] += 1
            bucket["dot_prefixed"] = root.startswith(".")
            extension = str(row["extension"] or "").lower()
            if extension in NATIVE_PROJECT_EXTENSIONS:
                bucket["native_tools"][extension] += 1
            elif extension in VIDEO_EXTENSIONS:
                bucket["video_count"] += 1
            elif extension in IMAGE_EXTENSIONS:
                bucket["image_count"] += 1
            elif extension in AUDIO_EXTENSIONS:
                bucket["audio_count"] += 1
            else:
                bucket["other_count"] += 1
            if _is_frame_sequence_member(parts[-1]):
                bucket["sequence_count"] += 1
            if _is_platform_locator(parts[-1]):
                bucket["platform_locator_count"] += 1
            if len(parts) == 1:
                bucket["loose_root_count"] += 1
            if len(parts) > 1:
                bucket["second_level"][parts[1]] += 1
                if parts[1] in _APP_BUNDLE_SEGMENTS:
                    bucket["app_bundle_hits"] += 1
                if parts[1] in _CAMERA_CARD_SEGMENTS:
                    bucket["camera_card_hits"] += 1
            for segment in parts[1:-1]:
                if segment in _CAMERA_CARD_SEGMENTS:
                    bucket["camera_card_hits"] += 1
                    break
            mtime = int(row["mtime_ns"] or 0)
            if mtime > 0:
                if bucket["mtime_first"] is None or mtime < bucket["mtime_first"]:
                    bucket["mtime_first"] = mtime
                if bucket["mtime_last"] is None or mtime > bucket["mtime_last"]:
                    bucket["mtime_last"] = mtime
        projects: Counter[str] = Counter()
        for row in con.execute("SELECT container_root FROM projects"):
            projects[str(row["container_root"] or "")] += 1
    finally:
        con.close()
    for root, bucket in containers.items():
        bucket["container"] = root
        bucket["project_count"] = int(projects.get(root, 0))
        bucket["native_count"] = sum(bucket["native_tools"].values())
        bucket["tools"] = sorted(
            NATIVE_PROJECT_EXTENSIONS[ext] for ext in bucket["native_tools"])
        bucket["native_tools"] = dict(sorted(bucket["native_tools"].items()))
        bucket["media_kinds"] = dict(sorted(bucket["media_kinds"].items()))
        bucket["hash_states"] = dict(sorted(bucket["hash_states"].items()))
        bucket["top_second_level"] = [
            name for name, _ in bucket["second_level"].most_common(5)]
        del bucket["second_level"]
        bucket["span"] = _span(bucket["mtime_first"], bucket["mtime_last"])
    return dict(containers)


def _classify(bucket: Mapping[str, Any]) -> tuple[str, str]:
    """Decide what kind of evidence a container holds, and say on what basis.

    This classifies the *evidence*, never the authorship.  Path structure is a
    legitimate observation about a filesystem; it is never a claim about a work.
    """
    assets = int(bucket["asset_count"])
    container = str(bucket["container"])
    if bucket["dot_prefixed"] or (assets and bucket["bytes"] == 0):
        return "system_metadata", "root is dot-prefixed or holds no bytes"
    if any(marker in container for marker in _SYNC_MARKERS):
        return "system_metadata", (
            "the container name carries a cloud-sync scratch marker: this is "
            "bookkeeping written by a sync client, not a project container")
    if bucket["app_bundle_hits"] and not bucket["native_count"] and not bucket["video_count"]:
        return "installed_tool", (
            f"{bucket['app_bundle_hits']} assets sit under an application-bundle "
            f"segment with no native project file and no video output")
    if bucket["camera_card_hits"] and not bucket["native_count"]:
        return "source_footage", (
            "assets sit under a camera-card directory structure with no native "
            "project file")
    if assets and bucket["loose_root_count"] == assets:
        return "loose_root_file", (
            "every asset sits directly at the volume root: this is a file, not a "
            "project container")
    if (
        assets >= _MIN_SEQUENCE_COUNT
        and not bucket["native_count"]
        and bucket["sequence_count"] / assets >= _MIN_SEQUENCE_RATIO
    ):
        return "render_output", (
            f"{bucket['sequence_count']} of {assets} filenames are a short zero-padded "
            f"frame counter with a frame-image extension and no native project file")
    if (
        assets >= _MIN_SEQUENCE_COUNT
        and not bucket["native_count"]
        and bucket["platform_locator_count"] / assets >= _MIN_SEQUENCE_RATIO
    ):
        return "published_export", (
            f"{bucket['platform_locator_count']} of {assets} filenames are a platform "
            f"media id: these are exported manifestations of published posts")
    if bucket["native_count"]:
        return "production", (
            f"{bucket['native_count']} native project files present "
            f"({', '.join(bucket['tools'])})")
    if bucket["video_count"] or bucket["image_count"]:
        return "delivery", (
            f"{bucket['video_count']} video and {bucket['image_count']} image assets "
            f"with no native project file")
    return "indexed_only", "nothing observable distinguishes this container"


def _authority(authority_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(authority_path)
    containers = payload.get("containers") if isinstance(payload, Mapping) else None
    if not isinstance(containers, Mapping):
        raise PortfolioClaimsError("research_authority_containers_missing")
    result: dict[str, dict[str, Any]] = {}
    for key, raw in containers.items():
        if not isinstance(raw, Mapping):
            continue
        urls = [str(url) for url in raw.get("evidence_urls", []) if url]
        result[str(key)] = {
            "kind": str(raw.get("kind") or ""),
            "confidence": str(raw.get("confidence") or ""),
            "canonical_name": str(raw.get("canonical_name") or ""),
            "evidence_url_count": len(urls),
        }
    return result


def _declared_input_basenames(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        return {}
    return {
        str(key).lower(): int(value)
        for key, value in payload.items() if isinstance(value, int)
    }


def _declared_dependency_targets(path: Path | None) -> dict[str, list[str]]:
    """Inputs a native scene explicitly declares, grouped by container.

    This is the causal-connectivity evidence: a scene naming its own resources
    explains a chain (source -> resource -> output).  It is dependency context,
    never authorship of what consumed it.
    """
    if path is None or not path.is_file():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise PortfolioClaimsError(f"blend_targets_not_array:{path}")
    grouped: dict[str, list[str]] = defaultdict(list)
    for value in payload:
        target = str(value or "")
        if not target:
            continue
        root = target.split("/", 1)[0] if "/" in target else ""
        if root:
            grouped[root].append(target)
    return {key: sorted(value) for key, value in grouped.items()}


def _attestations(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    """Load named-authority attestations, indexed by the subject they cover.

    An attestation is the only route that lifts a role or authorship claim past
    ``candidate``.  A negative attestation ("this is not mine") is accepted
    without corroboration because it reduces what the system asserts.
    """
    if path is None or not path.is_file():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        raise PortfolioClaimsError("attestations_not_object")
    rows = payload.get("attestations")
    if not isinstance(rows, list):
        raise PortfolioClaimsError("attestations_missing")
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise PortfolioClaimsError("attestation_row_invalid")
        establishes = raw.get("establishes")
        if not isinstance(establishes, Mapping):
            raise PortfolioClaimsError(
                f"attestation_establishes_missing:{raw.get('attestation_id')}")
        attestor = str(raw.get("attested_by") or "").strip()
        if not attestor:
            raise PortfolioClaimsError(
                f"attestation_attestor_missing:{raw.get('attestation_id')}")
        state = str(establishes.get("state_granted") or "")
        if state not in STATE_RANK:
            raise PortfolioClaimsError(
                f"attestation_state_invalid:{raw.get('attestation_id')}")
        record = {
            "attestation_id": str(raw.get("attestation_id") or ""),
            "attested_by": attestor,
            "statement": str(raw.get("statement") or ""),
            "verb": str(establishes.get("verb") or ""),
            "layer": str(establishes.get("layer") or ""),
            "state_granted": state,
            "negative": bool(establishes.get("negative")),
            "context_label": str(establishes.get("context_label") or ""),
            "role": str(establishes.get("role") or ""),
            "does_not_establish": [
                str(item) for item in (raw.get("does_not_establish") or [])],
            "corroborating_evidence": [
                str(item) for item in (raw.get("corroborating_evidence") or [])],
            "reliability_note": str(raw.get("reliability_note") or ""),
        }
        for subject in establishes.get("subjects") or []:
            index[str(subject)].append(record)
    return {key: value for key, value in index.items()}


def _overrides(path: Path | None) -> dict[str, dict[str, Any]]:
    """Load the declared practice partition, if one exists.

    Overrides are how a human correction generalizes: one line here reconfigures
    every claim about that container.  Absent, the projection still decides.
    """
    if path is None or not path.is_file():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        raise PortfolioClaimsError("practice_overrides_not_object")
    rows = payload.get("practices")
    if not isinstance(rows, Mapping):
        raise PortfolioClaimsError("practice_overrides_missing_practices")
    result: dict[str, dict[str, Any]] = {}
    for container, raw in rows.items():
        if not isinstance(raw, Mapping):
            raise PortfolioClaimsError(f"practice_override_invalid:{container}")
        permission = str(raw.get("permission") or "unnamed")
        if permission not in PERMISSION_RANK:
            raise PortfolioClaimsError(f"practice_override_permission_invalid:{container}")
        kind = str(raw.get("kind") or "")
        if kind and kind not in PRACTICE_KINDS:
            raise PortfolioClaimsError(f"practice_override_kind_invalid:{container}")
        result[str(container)] = {
            "kind": kind,
            "permission": permission,
            "practice_id": str(raw.get("practice_id") or ""),
            "role": str(raw.get("role") or ""),
            "property_regime": str(raw.get("property_regime") or ""),
            "context_label": str(raw.get("context_label") or ""),
            "attested_by": str(raw.get("attested_by") or ""),
            "note": str(raw.get("note") or ""),
            # What is explicitly *not* the operator's part.  A general caveat is
            # not an exclusion, so the two fields stay separate.
            "not_mine": str(raw.get("not_mine") or ""),
        }
    return result


class _ClaimBuilder:
    """Accumulate claims while enforcing the anti-self-promotion invariant."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []

    def add(
        self,
        *,
        verb: str,
        layer: str,
        subject: str,
        scope: str,
        state: str,
        permission: str,
        generated_by: str,
        supported_by: list[str],
        caption_fields: Mapping[str, Any],
        evidence_refs: list[str],
        evidence_kinds: list[str],
        refuted_by: str,
    ) -> None:
        if verb not in CLAIMS:
            raise PortfolioClaimsError(f"claim_verb_invalid:{verb}")
        if layer not in LAYERS:
            raise PortfolioClaimsError(f"claim_layer_invalid:{layer}")
        if state not in STATE_RANK:
            raise PortfolioClaimsError(f"claim_state_invalid:{state}")
        if permission not in PERMISSION_RANK:
            raise PortfolioClaimsError(f"claim_permission_invalid:{permission}")

        independent = sorted({name for name in supported_by if name != generated_by})
        effective = state
        # Rule 2: no route promotes its own claim.
        if STATE_RANK[state] >= STATE_RANK["supported_candidate"] and not independent:
            self.violations.append({
                "subject": subject, "verb": verb, "requested_state": state,
                "generated_by": generated_by,
                "reason": "no independent route supports this claim",
            })
            effective = "candidate"
        # Rule 3: hard ceilings the archive cannot lift on its own.
        ceiling = CLAIM_STATE_CEILING.get(verb)
        if ceiling is not None and STATE_RANK[effective] > STATE_RANK[ceiling]:
            self.violations.append({
                "subject": subject, "verb": verb, "requested_state": effective,
                "generated_by": generated_by,
                "reason": f"{verb} cannot exceed {ceiling} without a third-party receipt",
            })
            effective = ceiling

        basis = {
            "verb": verb, "layer": layer, "subject": subject, "scope": scope,
            "generated_by": generated_by, "caption_fields": dict(caption_fields),
        }
        self.rows.append({
            "claim_id": "claim:" + hashlib.sha256(
                stable_json(basis).encode("utf-8")).hexdigest()[:32],
            "verb": verb,
            "layer": layer,
            "subject": subject,
            "scope": scope,
            "state": effective,
            "requested_state": state,
            "permission": permission,
            "generated_by": generated_by,
            "supported_by": independent,
            "independent_route_count": len(independent),
            "caption_fields": dict(caption_fields),
            "evidence_kinds": sorted(set(evidence_kinds)),
            "evidence_refs": sorted(set(evidence_refs)),
            "refuted_by": refuted_by,
        })


def compile_portfolio_claims(
    *,
    index_path: str | Path,
    authority_path: str | Path,
    archive_path: str | Path | None = None,
    declared_inputs_path: str | Path | None = None,
    blend_targets_path: str | Path | None = None,
    practices_path: str | Path | None = None,
    attestations_path: str | Path | None = None,
    screen_setup_root: str | Path | None = None,
    human_relations: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compile the claim base from existing read-only sources."""
    index = Path(index_path).expanduser().resolve()
    authority_file = Path(authority_path).expanduser().resolve()
    archive = Path(archive_path).expanduser().resolve() if archive_path else None
    declared_inputs = (
        Path(declared_inputs_path).expanduser() if declared_inputs_path else None)
    blend_targets = (
        Path(blend_targets_path).expanduser() if blend_targets_path else None)
    overrides_file = Path(practices_path).expanduser() if practices_path else None

    containers = _container_evidence(index)
    if not containers:
        raise PortfolioClaimsError("index_has_no_container")
    authority = _authority(authority_file)
    declared = _declared_input_basenames(declared_inputs) if declared_inputs else {}
    dependency_targets = _declared_dependency_targets(blend_targets)
    overrides = _overrides(overrides_file)
    attestations_file = (
        Path(attestations_path).expanduser() if attestations_path else None)
    attestations = _attestations(attestations_file)
    setup_root = Path(screen_setup_root).expanduser() if screen_setup_root else None
    screen_scan: dict[str, Any] | None = None
    if setup_root is not None and setup_root.is_dir():
        screen_scan = scan_screen_setups(setup_root)

    builder = _ClaimBuilder()
    practices: list[dict[str, Any]] = []

    for root in sorted(containers):
        bucket = containers[root]
        kind, basis = _classify(bucket)
        override = overrides.get(root, {})
        declared_kind = override.get("kind") or ""
        effective_kind = declared_kind or kind
        permission = override.get("permission") or "unnamed"
        context_label = override.get("context_label") or root
        practice_id = override.get("practice_id") or f"practice:{effective_kind}:{root}"
        auth = authority.get(root)
        index_ref = f"{index}#assets(container_root={root})"

        practices.append({
            "container": root,
            "practice_id": practice_id,
            "kind": effective_kind,
            "kind_observed": kind,
            "kind_declared": declared_kind or None,
            "basis": basis,
            "permission": permission,
            "permission_source": "declared" if override.get("permission") else "default_unnamed",
            "role": override.get("role") or "unknown",
            "property_regime": override.get("property_regime") or "unknown",
            "context_label": context_label,
            "attested_by": override.get("attested_by") or None,
            "note": override.get("note") or None,
            "asset_count": bucket["asset_count"],
            "bytes": bucket["bytes"],
            "project_count": bucket["project_count"],
            "native_count": bucket["native_count"],
            "tools": bucket["tools"],
            "video_count": bucket["video_count"],
            "image_count": bucket["image_count"],
            "platform_locator_count": bucket["platform_locator_count"],
            "frame_sequence_count": bucket["sequence_count"],
            "span": bucket["span"],
            "external_authority": auth,
            "source_ref": index_ref,
        })

        # Only a practice can carry portfolio claims.  A tool, a frame dump, a
        # camera card and filesystem bookkeeping are evidence about the archive,
        # never about the person.
        if effective_kind not in {"production", "delivery"}:
            continue

        if bucket["native_count"]:
            for extension, count in bucket["native_tools"].items():
                tool = NATIVE_PROJECT_EXTENSIONS[extension]
                builder.add(
                    verb="puedo", layer="process",
                    subject=f"{practice_id}#tool:{tool}",
                    scope=f"container:{root}",
                    state="observed", permission=permission,
                    generated_by="index:native_project_extension",
                    supported_by=["index:native_project_extension"],
                    caption_fields={
                        "technique": tool, "tool": tool,
                        "artifact_count": _plural(count, "proyecto nativo", "proyectos nativos"),
                        "span": bucket["span"],
                        "context_label": context_label,
                        "scope_note": f"en {context_label}",
                    },
                    evidence_refs=[f"{index}#assets(extension={extension},container_root={root})"],
                    evidence_kinds=["native_project_file"],
                    refuted_by="the extension is absent, or the files are received resources with no export chain",
                )

        if bucket["native_count"]:
            resolved = dependency_targets.get(root, [])
            declared_here = sorted({
                target.rsplit("/", 1)[-1].lower() for target in resolved
            } & set(declared)) if declared else []
            # Two independent routes: the index observes the native scene, and
            # the declaration file records what that scene names as its input.
            supported_structure = ["index:native_project_extension"]
            if resolved:
                supported_structure.append("declared:native_scene_inputs")
            # The dominant tool by count, not the alphabetically first one: saying
            # "After Effects" for a container that is 426 Blender files is false.
            dominant_extension = max(
                bucket["native_tools"].items(), key=lambda item: (item[1], item[0]),
                default=(None, 0),
            )[0]
            primary_tool = (
                NATIVE_PROJECT_EXTENSIONS[dominant_extension]
                if dominant_extension else "proyecto nativo"
            )
            tool_mix = ", ".join(
                f"{NATIVE_PROJECT_EXTENSIONS[ext]} {count}"
                for ext, count in sorted(
                    bucket["native_tools"].items(),
                    key=lambda item: (-item[1], item[0]))[:3]
            )
            structure_note = (
                f"{context_label}: "
                + _plural(bucket["native_count"], "proyecto nativo", "proyectos nativos")
                + (f" ({tool_mix})" if tool_mix else "")
                + (", " + _plural(len(resolved), "insumo declarado resuelto aqui",
                                  "insumos declarados resueltos aqui")
                   if resolved else ", sin insumos declarados resueltos")
                + (f", {len(declared_here)} de ellos declarados por mas de una escena"
                   if declared_here else "")
            )
            builder.add(
                verb="puedo", layer="process",
                subject=f"{practice_id}#structure",
                scope=f"container:{root}",
                state="supported_candidate" if resolved else "observed",
                permission=permission,
                generated_by="index:native_project_extension",
                supported_by=supported_structure,
                caption_fields={
                    "artifact_kind": f"herramienta dominante {primary_tool}",
                    "structure_note": structure_note,
                    "declared_input_count": len(resolved),
                    "source_artifact": f"{primary_tool} en {context_label}",
                    "output_note": (
                        f"{bucket['video_count']} video y {bucket['image_count']} imagen"),
                },
                evidence_refs=sorted({
                    f"{index}#assets(container_root={root})",
                    *([str(blend_targets)] if resolved and blend_targets else []),
                    *([str(declared_inputs)] if declared_here and declared_inputs else []),
                }),
                evidence_kinds=(
                    ["native_project_file", "scene_graph"]
                    + (["declared_inputs"] if resolved else [])
                ),
                refuted_by=(
                    "the native projects are received resources with no export chain, or "
                    "the declared inputs resolve to a different container"
                ),
            )

        builder.add(
            verb="puedo", layer="process",
            subject=f"{practice_id}#scale:assets",
            scope=f"container:{root}",
            state="observed", permission=permission,
            generated_by="index:asset_aggregate",
            supported_by=["index:asset_aggregate"],
            caption_fields={
                "scale_metric": f"archivos de trabajo en {context_label}",
                "value": bucket["asset_count"],
                "context_label": context_label,
            },
            evidence_refs=[index_ref],
            evidence_kinds=["asset_count"],
            refuted_by="the index reports a different count for this container",
        )
        builder.add(
            verb="puedo", layer="process",
            subject=f"{practice_id}#scale:bytes",
            scope=f"container:{root}",
            state="observed", permission=permission,
            caption_fields={
                "scale_metric": f"volumen de material en {context_label}",
                "value": f"{bucket['bytes'] / 1e9:.1f} GB",
                "context_label": context_label,
            },
            generated_by="index:asset_aggregate",
            supported_by=["index:asset_aggregate"],
            evidence_refs=[index_ref],
            evidence_kinds=["bytes"],
            refuted_by="the index reports different byte totals",
        )

        if bucket["mtime_first"] and bucket["mtime_last"]:
            # mtime alone is a weak, single-route observation: it stays candidate
            # unless an external authority independently dates the context.
            supported = ["index:mtime_span"]
            if auth and auth["evidence_url_count"]:
                supported.append("authority:evidence_urls")
            builder.add(
                verb="puedo", layer="process",
                subject=f"{practice_id}#timeline",
                scope=f"container:{root}",
                state="supported_candidate" if len(supported) > 1 else "candidate",
                permission=permission,
                generated_by="index:mtime_span",
                supported_by=supported,
                caption_fields={
                    "engagement": context_label,
                    "first_seen": _year(bucket["mtime_first"]),
                    "last_seen": _year(bucket["mtime_last"]),
                    "elapsed": bucket["span"],
                },
                evidence_refs=[f"{index}#assets(mtime_ns,container_root={root})"],
                evidence_kinds=["mtime_span"],
                refuted_by="filesystem mtimes were rewritten by a copy, or the dates contradict a dated publication",
            )

        # Context: the container exists as an indexed project container.  With a
        # URL-backed authority it gains a second independent route.
        supported_context = ["index:container_root"]
        if auth and auth["evidence_url_count"]:
            supported_context.append("authority:evidence_urls")
        builder.add(
            verb="ocurrio", layer="context",
            subject=f"{practice_id}#context",
            scope=f"container:{root}",
            state="supported_candidate" if len(supported_context) > 1 else "candidate",
            permission=permission,
            generated_by="index:container_root",
            supported_by=supported_context,
            caption_fields={
                "context_label": context_label,
                "kind": (auth or {}).get("kind") or PRACTICE_KIND_LABEL.get(effective_kind, effective_kind),
                "role_note": override.get("role") or "rol no declarado",
                "span": bucket["span"],
                "year": _year(bucket["mtime_last"]),
            },
            evidence_refs=sorted({
                index_ref,
                *([f"{authority_file}#containers/{root}"] if auth else []),
            }),
            evidence_kinds=["container_root"] + (["external_authority"] if auth else []),
            refuted_by="the container is not an indexed project container, or the authority names a different entity",
        )

        # An attestation from a named authority is the second independent route
        # the archive cannot supply on its own.
        context_subject = f"{practice_id}#context"
        for record in attestations.get(context_subject, []):
            builder.add(
                verb=record["verb"] or "ocurrio",
                layer=record["layer"] or "context",
                subject=f"{practice_id}#attested_context",
                scope=f"container:{root}",
                state=record["state_granted"],
                permission=permission,
                generated_by=f"attestation:{record['attested_by']}",
                supported_by=[
                    f"attestation:{record['attested_by']}",
                    "index:container_root",
                ],
                caption_fields={
                    "context_label": record["context_label"] or context_label,
                    "kind": (auth or {}).get("kind") or PRACTICE_KIND_LABEL.get(effective_kind, effective_kind),
                    "role_note": record["role"] or override.get("role") or "rol atestiguado",
                    "span": bucket["span"],
                    "year": _year(bucket["mtime_last"]),
                    "part_done": record["role"] or "presencia atestiguada",
                    "part_not_done": "; ".join(record["does_not_establish"][:2]) or "no declarado",
                },
                evidence_refs=sorted({
                    index_ref,
                    *( [str(attestations_file)] if attestations_file else [] ),
                }),
                evidence_kinds=["third_party_receipt", "container_root"],
                refuted_by=(
                    f"the attestation {record['attestation_id']} is corrected or withdrawn"
                ),
            )

        # Role: declared only.  Archive evidence cannot lift it past candidate,
        # and without a declaration it is not claimed at all.
        if override.get("role"):
            role_subject = f"{practice_id}#role"
            attested = bool(override.get("attested_by")) or bool(
                attestations.get(role_subject) or attestations.get(context_subject))
            builder.add(
                verb="hice_esta_parte", layer="role",
                subject=f"{practice_id}#role",
                scope=f"container:{root}",
                state="externally_attested" if attested else "candidate",
                permission=permission,
                generated_by="declared:practice_partition",
                supported_by=(
                    ["declared:practice_partition", f"attestation:{override['attested_by']}"]
                    if attested else ["declared:practice_partition"]
                ),
                caption_fields={
                    "context_label": context_label,
                    "part_done": override["role"],
                    "part_not_done": (
                        override.get("not_mine")
                        or "no declarado en esta practica"),
                    "year": _year(bucket["mtime_last"]),
                },
                evidence_refs=[str(overrides_file)] if overrides_file else [],
                evidence_kinds=["declared_practice_role"] + (
                    ["third_party_receipt"] if attested else []),
                refuted_by="the declared role is corrected, or a third party attests a different division of work",
            )

        # A container with outputs and no native project is received or delivered
        # material: an explicit "not mine" claim, which F3 requires.
        if effective_kind == "delivery":
            builder.add(
                verb="hice_esta_parte", layer="role",
                subject=f"{practice_id}#not_produced_here",
                scope=f"container:{root}",
                state="candidate", permission=permission,
                generated_by="index:no_native_project_file",
                supported_by=["index:no_native_project_file"],
                caption_fields={
                    "artifact_note": f"{context_label} ({bucket['video_count']} video, {bucket['image_count']} imagen)",
                    # A positive attestation about the context must qualify this
                    # claim, or a reader sees a contradiction: the show is
                    # attested while the container shows no production.
                    "reason": (
                        "sin proyecto nativo en este contenedor, asi que no hay "
                        "evidencia de produccion aqui"
                        + (
                            "; el contexto si esta atestiguado, de modo que la "
                            "ausencia es de este contenedor y no del trabajo"
                            if attestations.get(context_subject) else ""
                        )
                    ),
                    "context_label": context_label,
                },
                evidence_refs=[index_ref],
                evidence_kinds=["received_only_artifact", "no_export_chain"],
                refuted_by="a native project or export chain for this container is found elsewhere",
            )

    # Relations a person drew between two published items.  These are the only
    # curatorial claims in the base: a reading about why two things belong
    # together.  A relation is never evidence that two items are one work.
    relation_rows = list(human_relations or [])
    for relation in relation_rows:
        left = str(relation.get("left") or "")
        right = str(relation.get("right") or "")
        kind = str(relation.get("relation") or "")
        if not left or not right or not kind:
            continue
        asserts = str(relation.get("asserts") or "unmapped")
        confirmed = bool(relation.get("confirmed"))
        drawn_by = str(relation.get("drawn_by") or "human")
        supported = [f"person:{drawn_by}"]
        if confirmed:
            supported.append("person:feedback_accept")
        builder.add(
            verb="significa", layer="curatorial",
            subject=f"relation:{left}|{right}|{kind}",
            scope="published_items",
            state=str(relation.get("state") or "candidate"),
            permission="public",
            generated_by="person:drawn_relation",
            supported_by=supported,
            caption_fields={
                "relation": kind,
                "asserts": asserts,
                "left": left,
                "right": right,
                "reading": (
                    "estructura de publicacion o fecha declarada por la fuente"
                    if asserts.startswith("source_")
                    else "lectura de la persona sobre lo que comparten"
                ),
                "confirmation": (
                    "confirmada en la superficie de feedback"
                    if confirmed else "dibujada y no reconfirmada"
                ),
            },
            evidence_refs=sorted({
                f"connections:{left}|{right}|{kind}",
                *([f"feedback:{left}|{right}|{kind}"] if confirmed else []),
            }),
            evidence_kinds=(
                ["person_drawn_relation"]
                + (["third_party_receipt"] if confirmed else [])
            ),
            refuted_by=(
                "the person removes the relation, or the publication structure it "
                "rests on turns out to be different"
            ),
        )

    # Archive-wide totals per tool.  A client reads "After Effects across twelve
    # engagements", not the same tool repeated once per container.
    tool_totals: dict[str, dict[str, Any]] = {}
    for row in practices:
        if row["kind"] not in {"production", "delivery"}:
            continue
        bucket = containers[row["container"]]
        for extension, count in bucket["native_tools"].items():
            tool = NATIVE_PROJECT_EXTENSIONS[extension]
            entry = tool_totals.setdefault(tool, {
                "count": 0, "containers": 0, "first": None, "last": None,
            })
            entry["count"] += count
            entry["containers"] += 1
            for key, value in (("first", bucket["mtime_first"]), ("last", bucket["mtime_last"])):
                if value is None:
                    continue
                current = entry[key]
                if current is None:
                    entry[key] = value
                elif key == "first":
                    entry[key] = min(current, value)
                else:
                    entry[key] = max(current, value)
    for tool, entry in sorted(tool_totals.items()):
        builder.add(
            verb="puedo", layer="process",
            subject=f"archive#tool_total:{tool}",
            scope="archive",
            state="observed", permission="unnamed",
            generated_by="index:native_project_extension_total",
            supported_by=["index:native_project_extension_total"],
            caption_fields={
                "technique": tool,
                "tool": tool,
                "artifact_count": _plural(entry["count"], "proyecto nativo", "proyectos nativos"),
                "span": _span(entry["first"], entry["last"]),
                "context_label": _plural(
                    entry["containers"], "contexto de trabajo", "contextos de trabajo"),
                "scope_note": "en " + _plural(
                    entry["containers"], "contexto", "contextos"),
                "scale_metric": f"proyectos nativos de {tool} en el archivo",
                "value": entry["count"],
            },
            evidence_refs=[f"{index}#assets(extension,native_project)"],
            evidence_kinds=["native_project_file", "media_kind_distribution"],
            refuted_by=(
                "the index reports a different total for this extension, or the files are "
                "received resources rather than authored projects"
            ),
        )

    # Live screen setups: the strongest surviving evidence of live practice, and
    # the only kind a generative tool cannot fabricate coherently.  A setup
    # proves a configuration at a place, never authorship of what played on it.
    screen_variant_groups: list[dict[str, Any]] = []
    if screen_scan is not None:
        screen_variant_groups = derived_variant_groups(screen_scan)
        stale_labels = {
            row["file_stem"] for row in screen_scan["setups"]
            if row["label_reliability"] == "stale_label_from_save_as"
        }
        for setup in screen_scan["setups"]:
            stem = setup["file_stem"]
            subject = f"screen_setup:{stem}"
            records = attestations.get(subject, [])
            # A save-as leaves a stale label; without an attestation the venue
            # reading stays candidate, with one it is attested.
            attested = bool(records)
            base_state = (
                "externally_attested" if attested
                else "candidate" if stem in stale_labels
                else "supported_candidate"
            )
            supported = ["file:screen_setup_structure"]
            if attested:
                supported.append(f"attestation:{records[0]['attested_by']}")
            elif stem not in stale_labels:
                supported.append("file:embedded_configuration_timestamps")
            builder.add(
                verb="ocurrio", layer="context",
                subject=subject,
                scope=f"screen_setup:{setup['source_ref']}",
                state=base_state, permission="unnamed",
                generated_by="file:screen_setup_structure",
                supported_by=supported,
                caption_fields={
                    "context_label": (
                        records[0]["context_label"] if attested else stem),
                    "kind": "montaje de proyeccion en vivo",
                    "role_note": (
                        records[0]["role"] if attested
                        else f"{setup['screen_count']} pantallas, {setup['slice_count']} superficies mapeadas"),
                    "span": (
                        f"{setup['earliest_configured_day']}–{setup['latest_configured_day']}"
                        if setup["earliest_configured_day"] else "sin fecha interna"),
                    "year": (
                        int(setup["latest_configured_day"][:4])
                        if setup["latest_configured_day"] else None),
                },
                evidence_refs=sorted({
                    setup["source_ref"],
                    *([str(attestations_file)] if attested and attestations_file else []),
                }),
                evidence_kinds=(
                    ["live_screen_setup", "embedded_configuration_timestamp"]
                    + (["third_party_receipt"] if attested else [])
                ),
                refuted_by=(
                    "the document is a save-as whose label and embedded ids belong to an "
                    "earlier room, and no attestation covers this venue"
                ),
            )
            builder.add(
                verb="puedo", layer="process",
                subject=f"{subject}#mapping",
                scope=f"screen_setup:{setup['source_ref']}",
                state="observed", permission="unnamed",
                generated_by="file:screen_setup_structure",
                supported_by=["file:screen_setup_structure"],
                caption_fields={
                    "artifact_kind": f"montaje {setup['tool']} {setup['tool_version']}",
                    "structure_note": (
                        f"lienzo {setup['canvas']}, {setup['screen_count']} pantallas, "
                        f"{setup['slice_count']} superficies con warp bezier"
                        + (f" ({', '.join(setup['screen_names'][:3])})"
                           if setup["screen_names"] else "")),
                    "declared_input_count": setup["slice_count"],
                    "source_artifact": f"{setup['tool']} · {stem}",
                    "output_note": f"salida a {setup['output_device_count']} dispositivos",
                    "technique": f"mapeo de proyeccion {setup['canvas']}",
                    "tool": setup["tool"],
                    "artifact_count": setup["slice_count"],
                    "span": (
                        f"{setup['earliest_configured_day']}–{setup['latest_configured_day']}"
                        if setup["earliest_configured_day"] else "sin fecha interna"),
                    "scale_metric": "superficies mapeadas con warp en un solo montaje",
                    "value": setup["slice_count"],
                    "engagement": stem,
                    "first_seen": setup["earliest_configured_day"],
                    "last_seen": setup["latest_configured_day"],
                    "elapsed": (
                        f"{setup['configured_day_count']} dias de configuracion registrados"),
                },
                evidence_refs=[setup["source_ref"]],
                evidence_kinds=["live_screen_setup", "scene_graph"],
                refuted_by=(
                    "the document does not parse as a screen setup, or the geometry differs "
                    "from what the file declares"
                ),
            )

    # A declared native-scene input is dependency context: it argues for reuse of
    # a resource, never for authorship of what consumed it.
    declared_claim_count = 0
    if declared:
        declared_claim_count = len(declared)

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "sources": {
            "index": {"path": str(index), "sha256": _sha256(index)},
            "research_authority": {
                "path": str(authority_file), "sha256": _sha256(authority_file)},
            **({"iskvw_archive": {"path": str(archive), "sha256": _sha256(archive)}}
               if archive and archive.is_file() else {}),
            **({"declared_inputs": {
                "path": str(declared_inputs),
                "sha256": _sha256(declared_inputs),
                "basename_count": declared_claim_count,
                "role": "dependency_context_only",
            }} if declared_inputs and declared_inputs.is_file() else {}),
            **({"blend_dependency_targets": {
                "path": str(blend_targets),
                "sha256": _sha256(blend_targets),
                "container_count": len(dependency_targets),
                "target_count": sum(len(v) for v in dependency_targets.values()),
                "role": "dependency_context_only",
            }} if blend_targets and blend_targets.is_file() else {}),
            **({"attestations": {
                "path": str(attestations_file),
                "sha256": _sha256(attestations_file),
                "subject_count": len(attestations),
                "role": "named_authority_receipt",
            }} if attestations_file and attestations_file.is_file() else {}),
            **({"screen_setups": {
                "path": str(setup_root),
                "scan_hash": screen_scan["scan_hash"],
                "setup_count": screen_scan["setup_count"],
                "total_slices": screen_scan["total_slices"],
                "configured_day_span": screen_scan["configured_day_span"],
                "label_reliability_counts": screen_scan["label_reliability_counts"],
            }} if screen_scan is not None else {}),
            **({"practice_partition": {
                "path": str(overrides_file), "sha256": _sha256(overrides_file),
                "declared_container_count": len(overrides),
            }} if overrides_file and overrides_file.is_file() else {}),
        },
        "human_relation_count": len(relation_rows),
        "human_relation_states": dict(sorted(Counter(
            str(row.get("state") or "candidate") for row in relation_rows).items())),
        "human_relation_asserts": dict(sorted(Counter(
            str(row.get("asserts") or "unmapped") for row in relation_rows).items())),
        "screen_setup_variant_groups": screen_variant_groups,
        "practice_count": len(practices),
        "practice_kind_counts": dict(sorted(Counter(
            row["kind"] for row in practices).items())),
        "claimable_practice_count": sum(
            1 for row in practices if row["kind"] in {"production", "delivery"}),
        "practices": practices,
        "claim_count": len(builder.rows),
        "claims_by_verb": dict(sorted(Counter(row["verb"] for row in builder.rows).items())),
        "claims_by_state": dict(sorted(Counter(row["state"] for row in builder.rows).items())),
        "claims_by_layer": dict(sorted(Counter(row["layer"] for row in builder.rows).items())),
        "claims": sorted(builder.rows, key=lambda row: (row["verb"], row["subject"])),
        "invariants": {
            "no_route_promotes_its_own_claim": {
                "enforced": True,
                "downgrades": len([
                    row for row in builder.violations
                    if row["reason"] == "no independent route supports this claim"]),
            },
            "authorship_ceiling": {
                "enforced": True,
                "ceilings": dict(sorted(CLAIM_STATE_CEILING.items())),
                "downgrades": len([
                    row for row in builder.violations
                    if "third-party receipt" in row["reason"]]),
            },
            "downgrade_log": sorted(
                builder.violations, key=lambda row: (row["subject"], row["verb"])),
            "layers_never_promoted": True,
            "uncertainty_paid_in_scope": True,
        },
        "control": {
            "source_rescan": False,
            "physical_mutation": False,
            "database_write": False,
            "network_called": False,
            "publication": False,
            "submission": False,
            "training_permitted": False,
            "promotion": "none",
        },
    }
    result["claims_hash"] = "sha256:" + hashlib.sha256(
        stable_json({k: v for k, v in result.items() if k != "claims_hash"}
                    ).encode("utf-8")).hexdigest()
    return result


def validate_portfolio_claims(payload: Any) -> bool:
    """Independently falsify a claim base without recompiling it."""
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise PortfolioClaimsError("schema_invalid")
    claims = payload.get("claims")
    if not isinstance(claims, list):
        raise PortfolioClaimsError("claims_must_be_array")
    seen: set[str] = set()
    for row in claims:
        if not isinstance(row, Mapping):
            raise PortfolioClaimsError("claim_row_invalid")
        claim_id = str(row.get("claim_id") or "")
        if not claim_id or claim_id in seen:
            raise PortfolioClaimsError(f"claim_id_invalid_or_duplicate:{claim_id}")
        seen.add(claim_id)
        verb, state = str(row.get("verb")), str(row.get("state"))
        if verb not in CLAIMS or state not in STATE_RANK:
            raise PortfolioClaimsError(f"claim_vocabulary_invalid:{claim_id}")
        if str(row.get("layer")) not in LAYERS:
            raise PortfolioClaimsError(f"claim_layer_invalid:{claim_id}")
        if str(row.get("permission")) not in PERMISSION_RANK:
            raise PortfolioClaimsError(f"claim_permission_invalid:{claim_id}")
        ceiling = CLAIM_STATE_CEILING.get(verb)
        attested = "third_party_receipt" in (row.get("evidence_kinds") or [])
        if ceiling and STATE_RANK[state] > STATE_RANK[ceiling] and not attested:
            raise PortfolioClaimsError(f"claim_exceeds_authorship_ceiling:{claim_id}")
        supported = row.get("supported_by")
        if not isinstance(supported, list):
            raise PortfolioClaimsError(f"claim_supported_by_invalid:{claim_id}")
        if str(row.get("generated_by")) in supported:
            raise PortfolioClaimsError(f"claim_self_promoted:{claim_id}")
        if STATE_RANK[state] >= STATE_RANK["supported_candidate"] and not supported:
            raise PortfolioClaimsError(f"claim_unsupported_promotion:{claim_id}")
        if not str(row.get("refuted_by") or "").strip():
            raise PortfolioClaimsError(f"claim_missing_refutation:{claim_id}")
        if not (row.get("evidence_refs") or row.get("evidence_kinds")):
            raise PortfolioClaimsError(f"claim_missing_evidence:{claim_id}")
    control = payload.get("control")
    if not isinstance(control, Mapping) or control.get("database_write") is not False:
        raise PortfolioClaimsError("control_invalid")
    if control.get("training_permitted") is not False or control.get("promotion") != "none":
        raise PortfolioClaimsError("control_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION", "NATIVE_PROJECT_EXTENSIONS", "PRACTICE_KINDS",
    "PortfolioClaimsError", "SCHEMA", "compile_portfolio_claims",
    "validate_portfolio_claims",
]
