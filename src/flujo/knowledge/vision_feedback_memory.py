"""Local multimodal analysis with append-only MAK feedback memory.

The primary local model is Gemma 3 4B through Ollama.  This module is a
bounded adapter, not a new inference framework: it consumes an archive case,
asks the existing local model for observations and candidate relations, and
stores model observations or explicit corrections in the existing
``LearningStore.mak_operational_events`` ledger.

Model output is never promoted to authorship, identity, work, publication or
curatorial truth.  Feedback is separated from model output so a model guess
cannot train itself.  A supported or contradicted feedback event must carry
the evidence references that justify it; ``unknown`` remains an unresolved
state rather than a forced negative label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .project_ir import LearningStore, ProjectIRError, stable_json
from .archive_reconstruction import SCHEMA as ARCHIVE_PROJECTION_SCHEMA
from .project_context import SCHEMA as PROJECT_CONTEXT_SCHEMA, validate_context


SCHEMA = "mak-vision-feedback-memory-v1"
CASE_SCHEMA = "mak-vision-case-v1"
MODEL_NAME = "gemma3:4b"
CLIP_MODEL_NAME = "ViT-B/32"
CLIP_SCHEMA = "mak-clip-vision-evidence-v1"
CLIP_SOURCE = "openai/CLIP"
PROVIDER = "ollama"
ALGORITHM_VERSION = "gemma-vision-feedback-2"
OPERATING_KNOWLEDGE_SCHEMA = "mak-relational-operating-knowledge-v1"

# This is the transferable operating knowledge learned while directing MAK.
# It is guidance for the local model, never archive evidence.  Keeping it
# versioned and in the same adapter makes the student model replaceable while
# the method survives a model change.
MAK_OPERATING_KNOWLEDGE = {
    "schema": OPERATING_KNOWLEDGE_SCHEMA,
    "version": "1",
    "mission": "Relate an artistic archive through evidence and context without turning proximity into authorship, identity, delivery or cultural truth.",
    "layers": [
        "physical_artifact",
        "authoring_or_process",
        "output_or_manifestation",
        "publication_or_event",
        "person_client_collaboration",
        "title_or_display_label",
    ],
    "operating_rules": [
        "A declared archive/person boundary is context for the archive, not proof that every file was made by that person.",
        "Filename, path token, visual similarity and embedding similarity are locating signals only; they never prove authorship, work identity, delivery or publication.",
        "The same song, client, event or idea can have multiple visuals, versions and shows; do not merge them.",
        "A final image or video may be observed without its native authoring file; a native blend or AEP may exist without proving which export was delivered.",
        "A third-party visual may be present because it was used, commissioned, shared or archived; usage and authorship are separate relations.",
        "Platform title, text printed inside a cover, filename and work identity are separate layers. An untitled or abstract work remains unresolved rather than being renamed by inference.",
        "When evidence is insufficient, preserve the artifact and emit a candidate with missing evidence; never erase it and never manufacture certainty.",
    ],
    "relation_patterns": [
        {
            "pattern": "public_collaboration_context",
            "basis": "explicit catalogue, publication or source claim",
            "may_propose": ["shared_collaboration_context", "candidate_manifestation_of"],
            "must_not_claim": ["physical_merge", "authorship_of_visual", "exact_delivery"],
        },
        {
            "pattern": "show_or_event_visual",
            "basis": "explicit event/show context plus an observed visual or frame",
            "may_propose": ["presented_in_event", "candidate_visual_manifestation"],
            "must_not_claim": ["visual_made_by_artist", "one_visual_per_song", "same_work_truth"],
        },
        {
            "pattern": "native_authoring_to_output",
            "basis": "native project, explicit material binding and export witness",
            "may_propose": ["exported_from", "version_of", "manifestation_of"],
            "must_not_claim": ["mere_same_basename_is_binding", "missing_native_file_is_negative_authorship"],
        },
        {
            "pattern": "shared_resource",
            "basis": "explicit local topology or source binding",
            "may_propose": ["shared_resource_of"],
            "must_not_claim": ["transitive_merge_of_units", "same_work"],
        },
        {
            "pattern": "third_party_or_commissioned_visual",
            "basis": "explicit credit, client/event context or contradictory attribution",
            "may_propose": ["used_in_context", "commissioned_for", "candidate_third_party_production"],
            "must_not_claim": ["artist_authorship_without_credit_or_native_witness"],
        },
    ],
    "teaching_examples": [
        {
            "id": "escarlata-remix",
            "lesson": "A named collaboration track can relate DREFQUILA and HARRY as a public/contextual collaboration while local visual endpoints remain separate candidate manifestations.",
            "preserve": ["track context", "multiple visual/show possibilities", "missing exact delivery binding"],
            "forbid": ["merge archives", "infer who made the visual", "treat title match as delivery proof"],
        },
        {
            "id": "bah-event-context",
            "lesson": "A brand or event context such as BAH/Bees and Honey can connect people, shows and commissions without making every associated media file one artwork.",
            "preserve": ["contextual association", "event role", "separate physical artifacts"],
            "forbid": ["transitive merge", "authorship from event proximity", "one project per folder name"],
        },
        {
            "id": "third-party-show-visual",
            "lesson": "A visual seen in a show may be produced by a third party; the archive can prove observation or use while authorship remains unresolved.",
            "preserve": ["observed output", "show context", "counterevidence and missing credit"],
            "forbid": ["equate possession with authorship", "reject the visual because no blend/AEP exists"],
        },
        {
            "id": "xpedrito-title-layers",
            "lesson": "A platform title, cover text and physical media can deliberately point to different works or moments; labels are relational presentation, not identity replacement.",
            "preserve": ["display label", "source work identity", "untitled state"],
            "forbid": ["rename source artifact", "force title-to-file equality"],
        },
    ],
    "counterexamples": [
        "same_basename_different_roots_is_not_same_work",
        "same_embedding_is_not_same_artifact_or_authorship",
        "same_song_is_not_one_visual_or_one_show",
        "native_file_presence_is_not_delivery_proof_without_export_witness",
        "archive_membership_is_not_artist_authorship",
    ],
    "decision_protocol": [
        "Classify the supplied endpoints by role and context before proposing a relation.",
        "Use only evidence_refs bound to an endpoint or to the relation context.",
        "State the relation as candidate or unresolved and include the missing witness when needed.",
        "Keep physical artifacts, archives and units separate unless an explicit binding says otherwise.",
        "Return a useful observation even when the cultural relation remains unresolved.",
    ],
}

FEEDBACK_VERDICTS = frozenset({"support", "contradict", "correction"})
RELATION_STATUSES = frozenset({"candidate", "unresolved", "contradicted"})
MAX_TEXT = 2000
MAX_ITEMS = 128
PROMPT_CONTEXT_TEXT = 360


class VisionFeedbackError(ValueError):
    """Raised when a vision case, response or feedback event is invalid."""


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _sorted_unique(values: Any, *, limit: int = MAX_ITEMS) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    if not isinstance(values, Sequence):
        raise VisionFeedbackError("expected_string_list")
    result = {_text(item, 500) for item in values if _text(item, 500)}
    return sorted(result)[:limit]


def _digest(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _mapping(value: Any, error: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VisionFeedbackError(error)
    return value


def _normalise_artifacts(raw: Any) -> tuple[list[dict[str, Any]], list[str], dict[str, str]]:
    if not isinstance(raw, list):
        raise VisionFeedbackError("artifacts_not_list")
    artifacts: list[dict[str, Any]] = []
    media_paths: list[str] = []
    media_by_ref: dict[str, str] = {}
    seen: set[str] = set()
    for index, item in enumerate(raw[:MAX_ITEMS]):
        row = _mapping(item, f"artifact_{index}_not_object")
        ref = _text(row.get("artifact_ref") or row.get("physical_id"), 500)
        if not ref:
            raise VisionFeedbackError(f"artifact_{index}_missing_ref")
        if ref in seen:
            raise VisionFeedbackError(f"duplicate_artifact_ref:{ref}")
        seen.add(ref)
        path_value = _text(row.get("local_path") or row.get("path"), 2000)
        if path_value:
            path = Path(path_value).expanduser()
            if not path.is_file():
                raise VisionFeedbackError(f"media_not_file:{path_value}")
            media_paths.append(str(path))
            media_by_ref[ref] = str(path)
        artifacts.append({
            "artifact_ref": ref,
            "kind": _text(row.get("kind") or row.get("media_type") or "unknown", 120),
            "relative_path": _text(row.get("relative_path"), 1000),
            "evidence_refs": _sorted_unique(row.get("evidence_refs", [])),
            "content_sha256": _text(row.get("content_sha256") or row.get("sha256"), 128),
            "local_path": path_value,
        })
    if not artifacts:
        raise VisionFeedbackError("artifacts_empty")
    return sorted(artifacts, key=lambda item: item["artifact_ref"]), media_paths, media_by_ref


def _normalise_context(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise VisionFeedbackError("context_not_list")
    contexts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw[:MAX_ITEMS]):
        row = _mapping(item, f"context_{index}_not_object")
        ref = _text(row.get("context_ref") or row.get("ref"), 500)
        text = _text(row.get("text") or row.get("statement"), MAX_TEXT)
        if not ref or not text:
            raise VisionFeedbackError(f"context_{index}_missing_ref_or_text")
        if ref in seen:
            raise VisionFeedbackError(f"duplicate_context_ref:{ref}")
        seen.add(ref)
        contexts.append({
            "context_ref": ref,
            "text": text,
            "evidence_refs": _sorted_unique(row.get("evidence_refs", [])),
        })
    return sorted(contexts, key=lambda item: item["context_ref"])


def _normalise_feedback(raw: Any, refs: set[str], evidence_refs: set[str]) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise VisionFeedbackError("feedback_not_list")
    feedback: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw[:MAX_ITEMS]):
        row = _mapping(item, f"feedback_{index}_not_object")
        verdict = _text(row.get("verdict"), 40).casefold()
        if verdict not in FEEDBACK_VERDICTS:
            raise VisionFeedbackError(f"feedback_{index}_bad_verdict")
        source_ref = _text(row.get("source_ref"), 500)
        target_ref = _text(row.get("target_ref"), 500)
        for endpoint in (source_ref, target_ref):
            if endpoint and endpoint not in refs:
                raise VisionFeedbackError(f"feedback_{index}_unknown_endpoint:{endpoint}")
        evidence = _sorted_unique(row.get("evidence_refs", []))
        if any(ref not in evidence_refs for ref in evidence):
            raise VisionFeedbackError(f"feedback_{index}_unknown_evidence")
        material = {
            "source_ref": source_ref,
            "target_ref": target_ref,
            "relation": _text(row.get("relation"), 160),
            "verdict": verdict,
            "statement": _text(row.get("statement") or row.get("correction"), MAX_TEXT),
            "evidence_refs": evidence,
        }
        feedback_id = _text(row.get("feedback_id"), 200) or "feedback-" + _digest(material)[:32]
        if feedback_id in seen:
            raise VisionFeedbackError(f"duplicate_feedback_id:{feedback_id}")
        seen.add(feedback_id)
        material["feedback_id"] = feedback_id
        material["source"] = _text(row.get("source") or "explicit_evidence", 200)
        feedback.append(material)
    return sorted(feedback, key=lambda item: item["feedback_id"])


def normalise_case(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a case and remove runtime-only paths from its semantic view."""
    if not isinstance(raw, Mapping) or raw.get("schema") != CASE_SCHEMA:
        raise VisionFeedbackError("case_bad_schema")
    archive_id = _text(raw.get("archive_id"), 500)
    snapshot_id = _text(raw.get("snapshot_id"), 500)
    if not archive_id or not snapshot_id:
        raise VisionFeedbackError("case_identity_incomplete")
    artifacts, media_paths, media_by_ref = _normalise_artifacts(raw.get("artifacts"))
    inherited_media = raw.get("_media_by_ref", {})
    if inherited_media is not None:
        if not isinstance(inherited_media, Mapping):
            raise VisionFeedbackError("_media_by_ref_not_mapping")
        artifact_refs = {item["artifact_ref"] for item in artifacts}
        for ref, value in inherited_media.items():
            ref_text = _text(ref, 500)
            if ref_text not in artifact_refs:
                raise VisionFeedbackError(f"_media_by_ref_unknown_ref:{ref_text}")
            path = Path(str(value)).expanduser()
            if not path.is_file():
                raise VisionFeedbackError(f"media_not_file:{path}")
            media_by_ref[ref_text] = str(path)
        media_paths = [media_by_ref[ref] for ref in sorted(media_by_ref)]
    contexts = _normalise_context(raw.get("context", []))
    refs = {item["artifact_ref"] for item in artifacts}
    refs.update(item["context_ref"] for item in contexts)
    evidence_refs = set(_sorted_unique(raw.get("evidence_refs", [])))
    for item in artifacts + contexts:
        evidence_refs.update(item["evidence_refs"])
    feedback = _normalise_feedback(raw.get("feedback", []), refs, evidence_refs)
    provided_input_hash = _text(raw.get("input_hash"), 160)
    semantic = {
        "schema": CASE_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": provided_input_hash,
        "evidence_refs": sorted(evidence_refs),
        "artifacts": [{key: value for key, value in item.items() if key != "local_path"} for item in artifacts],
        "context": contexts,
        "feedback": feedback,
    }
    return {
        **semantic,
        "input_case_hash": _digest(semantic),
        "_media_paths": sorted(set(media_paths)),
        "_media_by_ref": {ref: media_by_ref[ref] for ref in sorted(media_by_ref)},
    }


def case_from_archive_projection(
    projection: Mapping[str, Any],
    *,
    artifact_refs: Sequence[str] | None = None,
    artifact_paths: Mapping[str, str | Path] | None = None,
    root: str | Path | None = None,
    contexts: Sequence[Mapping[str, Any]] = (),
    evidence_refs: Sequence[str] = (),
    feedback: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a bounded vision case from an accepted archive projection.

    The projection deliberately has no absolute root.  A caller may supply
    explicit artifact paths or one root; resolution only touches the listed
    relative paths and never scans the filesystem.  Missing paths remain
    inventory-only artifacts, while ``artifact_paths`` entries must be real
    files so a visual capability cannot silently receive a directory or a
    fabricated identity.
    """
    if not isinstance(projection, Mapping):
        raise VisionFeedbackError("projection_not_object")
    required = {"schema", "archive_id", "snapshot_id", "input_hash", "artifacts"}
    if projection.get("schema") != ARCHIVE_PROJECTION_SCHEMA:
        raise VisionFeedbackError("projection_bad_schema")
    if not required.issubset(projection):
        raise VisionFeedbackError("projection_missing_required_fields")
    archive_id = _text(projection.get("archive_id"), 500)
    snapshot_id = _text(projection.get("snapshot_id"), 500)
    input_hash = _text(projection.get("input_hash"), 160)
    source_artifacts = projection.get("artifacts")
    if not isinstance(source_artifacts, list):
        raise VisionFeedbackError("projection_artifacts_not_list")
    by_ref: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(source_artifacts):
        if not isinstance(item, Mapping):
            raise VisionFeedbackError(f"projection_artifact_{index}_not_object")
        ref = _text(item.get("artifact_ref"), 500)
        relative_path = _text(item.get("relative_path"), 1000)
        if not ref or not relative_path or ref in by_ref:
            raise VisionFeedbackError("projection_artifact_identity_invalid")
        by_ref[ref] = item

    path_map: dict[str, str] = {}
    if artifact_paths is not None:
        if not isinstance(artifact_paths, Mapping):
            raise VisionFeedbackError("artifact_paths_not_mapping")
        for ref, value in artifact_paths.items():
            ref_text = _text(ref, 500)
            if ref_text not in by_ref:
                raise VisionFeedbackError(f"artifact_path_unknown_ref:{ref_text}")
            path = Path(str(value)).expanduser()
            if not path.is_file():
                raise VisionFeedbackError(f"media_not_file:{path}")
            path_map[ref_text] = str(path)

    if artifact_refs is None:
        selected_refs = sorted(path_map or by_ref)
    else:
        if isinstance(artifact_refs, (str, bytes)):
            raise VisionFeedbackError("artifact_refs_not_list")
        selected_refs = [str(ref).strip() for ref in artifact_refs]
        if len(selected_refs) != len(set(selected_refs)):
            raise VisionFeedbackError("duplicate_artifact_ref")
        if selected_refs != sorted(selected_refs):
            selected_refs.sort()
    if not selected_refs:
        raise VisionFeedbackError("artifact_selection_empty")
    if len(selected_refs) > MAX_ITEMS:
        raise VisionFeedbackError("artifact_selection_requires_bound")
    if any(ref not in by_ref for ref in selected_refs):
        raise VisionFeedbackError("artifact_selection_unknown_ref")
    if any(ref not in selected_refs for ref in path_map):
        raise VisionFeedbackError("artifact_path_outside_selection")
    if root is not None and artifact_paths is not None:
        raise VisionFeedbackError("root_and_artifact_paths_are_ambiguous")

    resolved_root = Path(root).expanduser() if root is not None else None
    rows: list[dict[str, Any]] = []
    for ref in selected_refs:
        source = by_ref[ref]
        row = {
            "artifact_ref": ref,
            "relative_path": _text(source.get("relative_path"), 1000),
            "kind": _text(source.get("kind") or source.get("media_type") or "unknown", 120),
            "evidence_refs": [],
        }
        if source.get("sha256"):
            row["content_sha256"] = _text(source.get("sha256"), 128)
        if ref in path_map:
            row["local_path"] = path_map[ref]
        elif resolved_root is not None:
            relative = PurePosixPath(row["relative_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise VisionFeedbackError("projection_relative_path_invalid")
            candidate = resolved_root.joinpath(*relative.parts)
            if candidate.is_file():
                row["local_path"] = str(candidate)
        rows.append(row)

    if isinstance(evidence_refs, (str, bytes)):
        raise VisionFeedbackError("evidence_refs_not_list")
    evidence = _sorted_unique(list(evidence_refs))
    case = {
        "schema": CASE_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "evidence_refs": evidence,
        "artifacts": rows,
        "context": [dict(item) for item in contexts],
        "feedback": [dict(item) for item in feedback],
    }
    return normalise_case(case)


def contexts_from_project_context(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project the existing context graph into citation-bound model context.

    Entity descriptions and source claims are copied as declared context, not
    converted into artwork facts.  ``source_ids`` are the only evidence refs
    attached to an entity, and the existing context validator is the boundary
    that proves those IDs belong to the package.
    """
    if not isinstance(package, Mapping) or package.get("schema") != PROJECT_CONTEXT_SCHEMA:
        raise VisionFeedbackError("context_package_bad_schema")
    errors = validate_context(package)
    if errors:
        raise VisionFeedbackError("context_package_invalid:" + ",".join(errors))
    contexts: list[dict[str, Any]] = []
    for entity in sorted(package["entities"], key=lambda item: str(item.get("entity_id", ""))):
        entity_ref = _text(entity.get("entity_id"), 500)
        parts = [
            "Declared context entity: " + _text(entity.get("display_name"), 500),
            "kind=" + _text(entity.get("kind"), 100),
            "status=" + _text(entity.get("status"), 100),
        ]
        for label in ("purpose", "idea"):
            value = _text(entity.get(label), MAX_TEXT)
            if value:
                parts.append(label + "=" + value)
        contexts.append({
            "context_ref": entity_ref,
            "text": "; ".join(parts),
            "evidence_refs": [],
        })
    for source in sorted(package["sources"], key=lambda item: str(item.get("source_id", ""))):
        source_id = _text(source.get("source_id"), 500)
        parts = [
            "Declared evidence source: " + source_id,
            "type=" + _text(source.get("source_type"), 120),
            "status=" + _text(source.get("status"), 100),
            "locator=" + _text(source.get("locator"), 1000),
        ]
        claim = _text(source.get("claim"), MAX_TEXT)
        if claim:
            parts.append("claim=" + claim)
        contexts.append({
            "context_ref": "context-source:" + source_id,
            "text": "; ".join(parts),
            "evidence_refs": [source_id],
        })
    for relation in sorted(
        package["relations"],
        key=lambda item: (
            str(item.get("subject", "")), str(item.get("predicate", "")),
            str(item.get("object", "")), stable_json(item.get("source_ids", [])),
        ),
    ):
        source_ids = sorted(str(item) for item in relation["source_ids"])
        relation_material = {
            "subject": relation["subject"],
            "predicate": relation["predicate"],
            "object": relation["object"],
            "status": relation["status"],
            "source_ids": source_ids,
        }
        relation_ref = "context-relation:" + _digest(relation_material)[:32]
        parts = [
            "Declared context relation: "
            + _text(relation["subject"], 500)
            + " --"
            + _text(relation["predicate"], 200)
            + "/"
            + _text(relation["status"], 100)
            + "--> "
            + _text(relation["object"], 500),
        ]
        for source_id in source_ids:
            parts.append("source_id=" + source_id)
        contexts.append({
            "context_ref": relation_ref,
            "text": "; ".join(parts),
            "evidence_refs": source_ids,
        })
    return sorted(contexts, key=lambda item: str(item["context_ref"]))


def case_from_project_context(
    projection: Mapping[str, Any],
    context_package: Mapping[str, Any],
    *,
    artifact_refs: Sequence[str] | None = None,
    artifact_paths: Mapping[str, str | Path] | None = None,
    root: str | Path | None = None,
    evidence_refs: Sequence[str] = (),
    feedback: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Connect the accepted archive projection to the existing context graph."""
    contexts = contexts_from_project_context(context_package)
    package_evidence = [ref for context in contexts for ref in context["evidence_refs"]]
    return case_from_archive_projection(
        projection,
        artifact_refs=artifact_refs,
        artifact_paths=artifact_paths,
        root=root,
        contexts=contexts,
        evidence_refs=[*evidence_refs, *package_evidence],
        feedback=feedback,
    )


def _normalise_vector(vector: Sequence[Any]) -> list[float]:
    values = [float(value) for value in vector]
    if not values or not all(math.isfinite(value) for value in values):
        raise VisionFeedbackError("clip_vector_invalid")
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude <= 0.0:
        raise VisionFeedbackError("clip_vector_zero")
    return [value / magnitude for value in values]


def _vector_digest(vector: Sequence[float]) -> str:
    rounded = [round(float(value), 8) for value in vector]
    return _digest({"dimension": len(rounded), "values": rounded})


def clip_evidence_from_vectors(
    artifact_vectors: Mapping[str, Sequence[Any]],
    context_vectors: Mapping[str, Sequence[Any]],
    *,
    device: str = "unknown",
) -> dict[str, Any]:
    """Build deterministic CLIP evidence from already encoded vectors.

    This is deliberately a signal projection: it emits no relation status and
    never merges physical artifacts.  Tests and offline replays can inject
    vectors without importing torch; the runtime extractor below supplies the
    vectors from OpenAI CLIP.
    """
    artifacts: dict[str, list[float]] = {}
    contexts: dict[str, list[float]] = {}
    for ref, vector in artifact_vectors.items():
        if not _text(ref, 500):
            raise VisionFeedbackError("clip_artifact_ref_missing")
        artifacts[_text(ref, 500)] = _normalise_vector(vector)
    for ref, vector in context_vectors.items():
        if not _text(ref, 500):
            raise VisionFeedbackError("clip_context_ref_missing")
        contexts[_text(ref, 500)] = _normalise_vector(vector)
    dimensions = {len(vector) for vector in [*artifacts.values(), *contexts.values()]}
    if len(dimensions) > 1:
        raise VisionFeedbackError("clip_embedding_dimensions_mismatch")
    alignments: list[dict[str, Any]] = []
    for artifact_ref in sorted(artifacts):
        for context_ref in sorted(contexts):
            left, right = artifacts[artifact_ref], contexts[context_ref]
            if len(left) != len(right):
                raise VisionFeedbackError("clip_embedding_dimensions_mismatch")
            alignments.append({
                "artifact_ref": artifact_ref,
                "context_ref": context_ref,
                "cosine_similarity": round(sum(a * b for a, b in zip(left, right)), 8),
                "evidence_type": "weak_cross_modal_signal",
            })
    return {
        "schema": CLIP_SCHEMA,
        "model": CLIP_MODEL_NAME,
        "source": CLIP_SOURCE,
        "device": _text(device, 40) or "unknown",
        "artifact_embeddings": [
            {"artifact_ref": ref, "embedding_dim": len(artifacts[ref]), "embedding_sha256": _vector_digest(artifacts[ref])}
            for ref in sorted(artifacts)
        ],
        "context_embeddings": [
            {"context_ref": ref, "embedding_dim": len(contexts[ref]), "embedding_sha256": _vector_digest(contexts[ref])}
            for ref in sorted(contexts)
        ],
        "alignments": alignments,
        "control": {
            "signal_only": True,
            "relation_promotion": False,
            "authorship_inference": False,
            "ranking": False,
        },
    }


def extract_clip_evidence(
    case: Mapping[str, Any],
    *,
    device: str | None = None,
    download_root: str | Path | None = None,
) -> dict[str, Any]:
    """Encode case images and supplied context text with OpenAI CLIP."""
    try:
        import clip  # type: ignore[import-not-found]
        import torch
        from PIL import Image
    except ImportError as exc:
        raise VisionFeedbackError("clip_runtime_unavailable") from exc
    requested = device or ("cuda" if torch.cuda.is_available() else "cpu")
    try:
        load_options: dict[str, Any] = {"device": requested, "jit": False}
        if download_root:
            load_options["download_root"] = str(download_root)
        model, preprocess = clip.load(CLIP_MODEL_NAME, **load_options)
        model.eval()
        artifact_vectors: dict[str, list[float]] = {}
        for artifact in case.get("artifacts", []):
            if not isinstance(artifact, Mapping):
                continue
            path_value = artifact.get("local_path")
            if not path_value:
                media_by_ref = case.get("_media_by_ref", {})
                if isinstance(media_by_ref, Mapping):
                    path_value = media_by_ref.get(str(artifact.get("artifact_ref")))
            if not path_value:
                continue
            path = Path(str(path_value))
            with Image.open(path).convert("RGB") as image:
                tensor = preprocess(image).unsqueeze(0).to(requested)
            with torch.no_grad():
                vector = model.encode_image(tensor).float().cpu().flatten().tolist()
            artifact_vectors[str(artifact["artifact_ref"])] = vector
        context_vectors: dict[str, list[float]] = {}
        contexts = [item for item in case.get("context", []) if isinstance(item, Mapping)]
        texts = [str(item.get("text") or "") for item in contexts]
        if texts:
            tokens = clip.tokenize(texts, truncate=True).to(requested)
            with torch.no_grad():
                encoded = model.encode_text(tokens).float().cpu()
            for item, vector in zip(contexts, encoded.tolist()):
                context_vectors[str(item["context_ref"])] = vector
    except (OSError, RuntimeError, ValueError) as exc:
        raise VisionFeedbackError("clip_inference_failed") from exc
    return clip_evidence_from_vectors(artifact_vectors, context_vectors, device=requested)


def _public_case(case: Mapping[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in case.items() if not key.startswith("_")}
    # A local path is an execution handle, not semantic evidence.  Keep the
    # prompt portable even when callers pass a pre-normalised case or a raw
    # mapping directly instead of going through ``normalise_case`` first.
    if isinstance(payload.get("artifacts"), list):
        payload["artifacts"] = [
            {key: value for key, value in item.items() if key != "local_path"}
            if isinstance(item, Mapping) else item
            for item in payload["artifacts"]
        ]
    # The full context remains in the case hash and result.  The prompt gets
    # only citation-bearing context rows, because an entity label without a
    # source is not evidence and large duplicated context crowds out the
    # teacher packet and the actual artifacts.
    if isinstance(payload.get("context"), list):
        prompt_context: list[dict[str, Any]] = []
        for item in payload["context"]:
            if not isinstance(item, Mapping) or not item.get("evidence_refs"):
                continue
            prompt_context.append({
                "context_ref": item.get("context_ref"),
                "text": _text(item.get("text"), PROMPT_CONTEXT_TEXT),
                "evidence_refs": list(item.get("evidence_refs", [])),
            })
        payload["context"] = sorted(prompt_context, key=lambda item: str(item["context_ref"]))
    return payload


def _prompt_clip_evidence(clip_evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep CLIP's prompt signal small while retaining its audit identity."""
    if not isinstance(clip_evidence, Mapping):
        return {}
    return {
        key: clip_evidence[key]
        for key in ("schema", "model", "source", "device", "alignments", "control")
        if key in clip_evidence
    }


def build_prompt(
    case: Mapping[str, Any],
    feedback: Sequence[Mapping[str, Any]] = (),
    clip_evidence: Mapping[str, Any] | None = None,
    validation_memory: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Build a deterministic English prompt with evidence and prior feedback."""
    payload = _public_case(case)
    feedback_rows = sorted((dict(row) for row in feedback), key=lambda row: str(row.get("feedback_id", "")))
    validation_rows = sorted(
        (dict(row) for row in validation_memory),
        key=lambda row: (str(row.get("snapshot_id", "")), str(row.get("model", ""))),
    )
    knowledge_section = json.dumps(
        MAK_OPERATING_KNOWLEDGE, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    clip_section = json.dumps(
        _prompt_clip_evidence(clip_evidence), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (
        "You are MAK's local visual evidence analyst. Reply with JSON only.\n"
        "The archive belongs to one declared archive_id, but filenames and paths are not cultural truth.\n"
        "Describe what is observable. Propose only reversible candidate relations between supplied refs.\n"
        "Never infer authorship, ownership, work identity, publication, intention, or delivery from a filename, "
        "path, visual style, or your own prior response. Do not merge physical artifacts.\n"
        "Use only supplied evidence_refs. If a relation needs proof, put the gap in missing_evidence.\n"
        "Evidence_refs on an observation must belong to that artifact; relation evidence must belong to one of its endpoints.\n"
        "Evidence-free context labels are retained outside this prompt; do not cite them as evidence.\n"
        "A correction or contradiction is memory about a prior inference, not proof of a different artwork.\n"
        "MAK OPERATING KNOWLEDGE (teacher packet; guidance, not archive evidence):\n"
        + knowledge_section + "\n\n"
        "Return exactly these top-level keys: observations, relations, missing_evidence, alternatives.\n"
        "Each observation: artifact_ref, observation_type, statement, evidence_refs.\n"
        "Each relation: source_ref, relation, target_ref, status (candidate|unresolved|contradicted), "
        "evidence_refs, missing_evidence, reason.\n"
        "All endpoints must be refs supplied in the case. Do not invent refs.\n\n"
        "CASE:\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n\n"
        "CLIP SIGNAL (weak feature only; never proof):\n" + clip_section + "\n\n"
        "PERSISTED FEEDBACK:\n" + json.dumps(
            feedback_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n\nAUTOMATIC VALIDATION MEMORY (constraints, not evidence):\n"
        + json.dumps(validation_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _json_from_model(text: str) -> Mapping[str, Any]:
    cleaned = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    if "```" in cleaned:
        chunks = [chunk for chunk in cleaned.split("```") if "{" in chunk]
        cleaned = chunks[-1] if chunks else cleaned
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise VisionFeedbackError("model_response_not_json")
    # Some terminal/model combinations emit a literal line break inside a
    # JSON string.  Escape controls only while inside a JSON string; keeping
    # structural whitespace untouched preserves strict parsing.
    repaired: list[str] = []
    in_string = False
    escaped = False
    for char in cleaned[start:end + 1]:
        if in_string and ord(char) < 0x20:
            repaired.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}.get(char, f"\\u{ord(char):04x}"))
            continue
        repaired.append(char)
        if char == '"' and not escaped:
            in_string = not in_string
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    try:
        value = json.loads("".join(repaired))
    except json.JSONDecodeError as exc:
        raise VisionFeedbackError("model_response_invalid_json") from exc
    return _mapping(value, "model_response_not_object")


def _normalise_model_output(
    raw: Mapping[str, Any],
    refs: set[str],
    evidence_refs: set[str],
    artifact_evidence: Mapping[str, set[str]],
    context_evidence: Mapping[str, set[str]],
) -> dict[str, Any]:
    observations_raw = raw.get("observations", [])
    relations_raw = raw.get("relations", [])
    if not isinstance(observations_raw, list) or not isinstance(relations_raw, list):
        raise VisionFeedbackError("model_observations_or_relations_not_list")
    observations: list[dict[str, Any]] = []
    violations: list[dict[str, str]] = []
    for index, item in enumerate(observations_raw[:MAX_ITEMS]):
        row = _mapping(item, f"model_observation_{index}_not_object")
        artifact_ref = _text(row.get("artifact_ref"), 500)
        if artifact_ref not in refs:
            violations.append({"kind": "unknown_observation_ref", "value": artifact_ref})
            continue
        evidence = _sorted_unique(row.get("evidence_refs", []))
        if any(ref not in evidence_refs for ref in evidence):
            violations.append({"kind": "unknown_observation_evidence", "value": artifact_ref})
            continue
        if any(ref not in artifact_evidence.get(artifact_ref, set()) for ref in evidence):
            violations.append({"kind": "unbound_observation_evidence", "value": artifact_ref})
            continue
        observations.append({
            "artifact_ref": artifact_ref,
            "observation_type": _text(row.get("observation_type") or "visual_observation", 120),
            "statement": _text(row.get("statement"), MAX_TEXT),
            "evidence_refs": evidence,
        })
    relations: list[dict[str, Any]] = []
    for index, item in enumerate(relations_raw[:MAX_ITEMS]):
        row = _mapping(item, f"model_relation_{index}_not_object")
        source_ref = _text(row.get("source_ref"), 500)
        target_ref = _text(row.get("target_ref"), 500)
        if source_ref not in refs or target_ref not in refs:
            violations.append({
                "kind": "unknown_relation_endpoint",
                "value": f"{source_ref}->{target_ref}",
            })
            continue
        if source_ref == target_ref:
            violations.append({"kind": "self_relation", "value": source_ref})
            continue
        status = _text(row.get("status"), 40).casefold()
        if status not in RELATION_STATUSES:
            violations.append({"kind": "bad_relation_status", "value": status})
            continue
        evidence = _sorted_unique(row.get("evidence_refs", []))
        if any(ref not in evidence_refs for ref in evidence):
            violations.append({
                "kind": "unknown_relation_evidence",
                "value": f"{source_ref}->{target_ref}",
            })
            continue
        endpoint_evidence = (
            artifact_evidence.get(source_ref, set())
            | artifact_evidence.get(target_ref, set())
            | context_evidence.get(source_ref, set())
            | context_evidence.get(target_ref, set())
        )
        if any(ref not in endpoint_evidence for ref in evidence):
            violations.append({
                "kind": "unbound_relation_evidence",
                "value": f"{source_ref}->{target_ref}",
            })
            continue
        relations.append({
            "source_ref": source_ref,
            "relation": _text(row.get("relation"), 160) or "related_to",
            "target_ref": target_ref,
            "status": status,
            "evidence_refs": evidence,
            "missing_evidence": _sorted_unique(row.get("missing_evidence", [])),
            "reason": _text(row.get("reason"), MAX_TEXT),
        })
    return {
        "observations": sorted(observations, key=lambda row: (row["artifact_ref"], row["observation_type"], row["statement"])),
        "relations": sorted(relations, key=lambda row: (row["source_ref"], row["relation"], row["target_ref"])),
        "missing_evidence": _sorted_unique(raw.get("missing_evidence", [])),
        "alternatives": _sorted_unique(raw.get("alternatives", [])),
        "model_violations": sorted(violations, key=lambda row: (row["kind"], row["value"])),
    }


def run_ollama(
    case: Mapping[str, Any],
    prompt: str,
    *,
    model: str = MODEL_NAME,
    executable: str | None = None,
    timeout: int = 180,
) -> str:
    """Run one local Ollama vision request; never invokes a shell."""
    binary = executable or shutil.which("ollama") or "/usr/local/bin/ollama"
    if not Path(binary).is_file() and shutil.which(binary) is None:
        raise VisionFeedbackError("ollama_not_available")
    paths = list(case.get("_media_paths", []))
    if not paths:
        raise VisionFeedbackError("vision_media_required")
    command = [binary, "run", model, "--format", "json", "--nowordwrap", *paths, prompt]
    environment = dict(os.environ)
    environment["OLLAMA_NOHISTORY"] = "1"
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            check=False, env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise VisionFeedbackError("ollama_execution_failed") from exc
    if completed.returncode != 0:
        detail = _text(completed.stderr[-400:], 400).replace("\n", " ")
        suffix = ":" + detail if detail else ""
        raise VisionFeedbackError(f"ollama_exit_{completed.returncode}{suffix}")
    return completed.stdout.strip()


def analyze_case(
    raw_case: Mapping[str, Any],
    *,
    feedback: Sequence[Mapping[str, Any]] = (),
    runner: Callable[[Mapping[str, Any], str], str] | None = None,
    model: str = MODEL_NAME,
    executable: str | None = None,
    timeout: int = 180,
    include_clip: bool = False,
    clip_evidence: Mapping[str, Any] | None = None,
    clip_device: str | None = None,
    clip_download_root: str | Path | None = None,
    validation_memory: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Analyze one case and return an auditable, non-promoting projection."""
    case = normalise_case(raw_case)
    refs = {item["artifact_ref"] for item in case["artifacts"]}
    refs.update(item["context_ref"] for item in case["context"])
    evidence_refs = set(case["evidence_refs"])
    feedback_rows = _normalise_feedback(
        list(case["feedback"]) + [dict(row) for row in feedback], refs, evidence_refs,
    )
    clip_signal = dict(clip_evidence) if clip_evidence is not None else None
    if include_clip and clip_signal is None:
        clip_signal = extract_clip_evidence(
            case, device=clip_device, download_root=clip_download_root,
        )
    prompt = build_prompt(case, feedback_rows, clip_signal, validation_memory)
    response = runner(case, prompt) if runner else run_ollama(
        case, prompt, model=model, executable=executable, timeout=timeout,
    )
    artifact_evidence = {
        str(item["artifact_ref"]): set(item["evidence_refs"])
        for item in case["artifacts"]
    }
    context_evidence = {
        str(item["context_ref"]): set(item["evidence_refs"])
        for item in case["context"]
    }
    parsed = _normalise_model_output(
        _json_from_model(response), refs, evidence_refs, artifact_evidence, context_evidence,
    )
    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "provider": PROVIDER,
        "model": model,
        "archive_id": case["archive_id"],
        "snapshot_id": case["snapshot_id"],
        "input_hash": case["input_hash"],
        "input_case_hash": case["input_case_hash"],
        "operating_knowledge_hash": _digest(MAK_OPERATING_KNOWLEDGE),
        "feedback_context": feedback_rows,
        "clip_evidence": clip_signal,
        "analysis": parsed,
        "model_response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "control": {
            "promotion": "none",
            "training_permitted": False,
            "database_write": False,
            "truth_promotion": False,
            "user_review_required": False,
        },
        "provenance": {
            "input_schema": CASE_SCHEMA,
            "operating_knowledge_schema": OPERATING_KNOWLEDGE_SCHEMA,
            "operating_knowledge_hash": _digest(MAK_OPERATING_KNOWLEDGE),
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "media_count": len(case["_media_paths"]),
        "source": "local_ollama_vision",
        },
    }


def _event_id(kind: str, material: Mapping[str, Any]) -> str:
    return f"vision-{kind}-" + _digest(material)[:32]


def _case_identity(case: Mapping[str, Any]) -> dict[str, str]:
    normalised = normalise_case(case)
    return {
        "archive_id": normalised["archive_id"],
        "snapshot_id": normalised["snapshot_id"],
        "input_case_hash": normalised["input_case_hash"],
        "input_hash": normalised["input_hash"],
    }


def record_feedback(
    store: LearningStore,
    raw_case: Mapping[str, Any],
    feedback: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Persist explicit support/contradiction/correction in the existing ledger."""
    case = normalise_case(raw_case)
    rows = _normalise_feedback(
        list(feedback if feedback is not None else case["feedback"]),
        {item["artifact_ref"] for item in case["artifacts"]} | {item["context_ref"] for item in case["context"]},
        set(case["evidence_refs"]),
    )
    if not rows:
        raise VisionFeedbackError("feedback_empty")
    identity = _case_identity(case)
    event_ids: list[str] = []
    for row in rows:
        material = {**identity, "feedback": row}
        event = {
            "event_id": _event_id("feedback", material),
            **identity,
            "proposition_id": "vision-feedback:" + row["feedback_id"],
            "event_type": "vision_feedback",
            "feedback": row,
            "control": {"promotion": "none", "training_permitted": False},
            "provenance": {"source": row["source"], "evidence_refs": row["evidence_refs"]},
        }
        event_ids.append(store.append_operational_event(event))
    return event_ids


def record_analysis(store: LearningStore, analysis: Mapping[str, Any]) -> str:
    """Persist model observations as an append-only event, never as feedback."""
    if analysis.get("schema") != SCHEMA:
        raise VisionFeedbackError("analysis_bad_schema")
    required = ("archive_id", "snapshot_id", "input_case_hash", "analysis")
    if any(not _text(analysis.get(key), 500) for key in required[:3]):
        raise VisionFeedbackError("analysis_identity_incomplete")
    material = {
        "archive_id": analysis["archive_id"],
        "snapshot_id": analysis["snapshot_id"],
        "input_case_hash": analysis["input_case_hash"],
        "model": analysis.get("model", ""),
        "model_response_sha256": analysis.get("model_response_sha256", ""),
        "operating_knowledge_hash": analysis.get("operating_knowledge_hash", ""),
        "analysis": analysis["analysis"],
        "clip_evidence": analysis.get("clip_evidence"),
    }
    event = {
        "event_id": _event_id("analysis", material),
        "archive_id": analysis["archive_id"],
        "snapshot_id": analysis["snapshot_id"],
        "input_case_hash": analysis["input_case_hash"],
        "input_hash": _text(analysis.get("input_hash"), 160),
        "proposition_id": "vision-analysis:" + analysis["input_case_hash"],
        "event_type": "vision_analysis",
        "model": _text(analysis.get("model"), 160),
        "analysis": analysis["analysis"],
        "model_response_sha256": _text(analysis.get("model_response_sha256"), 128),
        "operating_knowledge_hash": _text(analysis.get("operating_knowledge_hash"), 128),
        "clip_evidence": analysis.get("clip_evidence"),
        "control": {"promotion": "none", "training_permitted": False},
        "provenance": analysis.get("provenance", {}),
    }
    return store.append_operational_event(event)


def load_feedback(store: LearningStore, archive_id: str) -> list[dict[str, Any]]:
    """Read only the feedback memory for one archive, in stable order."""
    rows: list[dict[str, Any]] = []
    for event in store.operational_events(archive_id):
        if event.get("event_type") != "vision_feedback":
            continue
        row = event.get("feedback")
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return sorted(rows, key=lambda row: _text(row.get("feedback_id"), 200))


def load_validation_memory(
    store: LearningStore,
    archive_id: str,
    *,
    limit: int = MAX_ITEMS,
) -> list[dict[str, Any]]:
    """Read validator failures as constraints, never as evidence or labels."""
    rows: list[dict[str, Any]] = []
    for event in store.operational_events(archive_id):
        if event.get("event_type") != "vision_analysis":
            continue
        analysis = event.get("analysis")
        if not isinstance(analysis, Mapping):
            continue
        violations = analysis.get("model_violations")
        if not isinstance(violations, list) or not violations:
            continue
        safe_violations: list[dict[str, str]] = []
        for violation in violations[:MAX_ITEMS]:
            if not isinstance(violation, Mapping):
                continue
            kind = _text(violation.get("kind"), 120)
            value = _text(violation.get("value"), 500)
            if kind:
                safe_violations.append({"kind": kind, "value": value})
        if not safe_violations:
            continue
        rows.append({
            "snapshot_id": _text(event.get("snapshot_id"), 500),
            "model": _text(event.get("model"), 160),
            "violations": sorted(safe_violations, key=lambda row: (row["kind"], row["value"])),
            "source": "automatic_validator",
        })
    return rows[-limit:]


def _load_json(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return _mapping(value, "case_not_object")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", help="mak-vision-case-v1 JSON path, or - for stdin")
    parser.add_argument("--projection", type=Path, default=None, help="accepted mak-archive-reconstruction-input-v1 JSON")
    parser.add_argument("--context-package", type=Path, default=None, help="existing mak-project-context-v1 JSON")
    parser.add_argument("--root", type=Path, default=None, help="explicit archive root for listed projection paths")
    parser.add_argument("--artifact-ref", action="append", default=None, help="physical artifact_ref to include; repeatable")
    parser.add_argument("--db", type=Path, default=None, help="existing LearningStore path")
    parser.add_argument("--record-analysis", action="store_true")
    parser.add_argument("--record-feedback", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="print prompt without invoking the model")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--ollama", default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--with-clip", action="store_true", help="encode images/context with OpenAI CLIP ViT-B/32")
    parser.add_argument("--clip-device", default=None)
    parser.add_argument("--clip-download-root", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.projection is not None:
            projection = _load_json(str(args.projection))
            selected_refs = args.artifact_ref
            if args.context_package is not None:
                raw = case_from_project_context(
                    projection,
                    _load_json(str(args.context_package)),
                    artifact_refs=selected_refs,
                    root=args.root,
                )
            else:
                raw = case_from_archive_projection(
                    projection,
                    artifact_refs=selected_refs,
                    root=args.root,
                )
        elif args.case:
            raw = _load_json(args.case)
        else:
            raise VisionFeedbackError("case_or_projection_required")
        case = normalise_case(raw)
        if args.record_feedback:
            if args.db is None:
                raise VisionFeedbackError("record_feedback_requires_db")
            ids = record_feedback(LearningStore(args.db), case)
            print(json.dumps({"schema": SCHEMA, "event_ids": ids}, ensure_ascii=False, sort_keys=True))
            return 0
        store = LearningStore(args.db) if args.db else None
        prior = load_feedback(store, case["archive_id"]) if store else []
        validation_memory = load_validation_memory(store, case["archive_id"]) if store else []
        if args.dry_run:
            print(build_prompt(
                case, [*prior, *case["feedback"]], validation_memory=validation_memory,
            ))
            return 0
        result = analyze_case(
            case, feedback=prior, model=args.model, executable=args.ollama, timeout=args.timeout,
            include_clip=args.with_clip, clip_device=args.clip_device,
            clip_download_root=args.clip_download_root,
            validation_memory=validation_memory,
        )
        if args.record_analysis:
            if args.db is None:
                raise VisionFeedbackError("record_analysis_requires_db")
            record_analysis(LearningStore(args.db), result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, VisionFeedbackError, ProjectIRError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
