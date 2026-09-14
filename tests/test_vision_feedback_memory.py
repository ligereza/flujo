from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from flujo.knowledge.archive_observer import observe_archive
from flujo.knowledge.archive_reconstruction import project_archive_snapshot
from flujo.knowledge.project_ir import LearningStore
from flujo.knowledge.vision_feedback_memory import (
    CASE_SCHEMA,
    CLIP_SCHEMA,
    MAK_OPERATING_KNOWLEDGE,
    OPERATING_KNOWLEDGE_SCHEMA,
    SCHEMA,
    VisionFeedbackError,
    analyze_case,
    build_prompt,
    case_from_archive_projection,
    case_from_project_context,
    clip_evidence_from_vectors,
    contexts_from_project_context,
    load_feedback,
    load_validation_memory,
    normalise_case,
    record_analysis,
    record_feedback,
)


def _case(tmp_path: Path) -> dict:
    media = tmp_path / "render.png"
    media.write_bytes(b"not decoded by the fake runner")
    return {
        "schema": CASE_SCHEMA,
        "archive_id": "archive-a",
        "snapshot_id": "snapshot-1",
        "input_hash": "sha256:input-a",
        "evidence_refs": ["ev:frame", "ev:catalog"],
        "artifacts": [
            {
                "artifact_ref": "archive-a:render.png",
                "relative_path": "render.png",
                "kind": "image/png",
                "local_path": str(media),
                "evidence_refs": ["ev:frame"],
            },
            {
                "artifact_ref": "archive-a:show.mp4",
                "relative_path": "show.mp4",
                "kind": "video/mp4",
                "evidence_refs": ["ev:catalog"],
            },
        ],
        "context": [
            {
                "context_ref": "catalog:show-1",
                "text": "An explicit public catalogue entry.",
                "evidence_refs": ["ev:catalog"],
            }
        ],
        "feedback": [],
    }


def _response() -> str:
    return json.dumps(
        {
            "observations": [
                {
                    "artifact_ref": "archive-a:render.png",
                    "observation_type": "visual_observation",
                    "statement": "A frame is visibly present.",
                    "evidence_refs": ["ev:frame"],
                }
            ],
            "relations": [
                {
                    "source_ref": "archive-a:render.png",
                    "relation": "manifestation_of",
                    "target_ref": "catalog:show-1",
                    "status": "candidate",
                    "evidence_refs": ["ev:catalog"],
                    "missing_evidence": ["explicit_visual_credit"],
                    "reason": "catalogue context is present; authorship is not inferred",
                }
            ],
            "missing_evidence": ["native_authoring_or_export_witness"],
            "alternatives": ["third_party_visual"]
        }
    )


def test_normalise_case_excludes_runtime_path_and_is_order_stable(tmp_path: Path):
    case = _case(tmp_path)
    first = normalise_case(case)
    case["artifacts"] = list(reversed(case["artifacts"]))
    second = normalise_case(case)
    assert first["input_case_hash"] == second["input_case_hash"]
    assert "local_path" not in json.dumps(first, sort_keys=True)


def test_prompt_excludes_runtime_path_even_for_raw_case(tmp_path: Path):
    case = _case(tmp_path)
    prompt = build_prompt(case)
    assert str(tmp_path) not in prompt
    assert "local_path" not in prompt


def test_prompt_contains_transferable_operating_knowledge_not_archive_evidence(tmp_path: Path):
    prompt = build_prompt(_case(tmp_path))
    assert "MAK OPERATING KNOWLEDGE (teacher packet; guidance, not archive evidence)" in prompt
    assert "escarlata-remix" in prompt
    assert "same_embedding_is_not_same_artifact_or_authorship" in prompt
    assert OPERATING_KNOWLEDGE_SCHEMA in prompt


def test_analysis_preserves_candidate_status_and_is_replayable(tmp_path: Path):
    case = _case(tmp_path)

    def runner(_case, _prompt):
        return _response()

    first = analyze_case(case, runner=runner)
    second = analyze_case(case, runner=runner)
    assert first == second
    assert first["schema"] == SCHEMA
    assert first["analysis"]["relations"][0]["status"] == "candidate"
    assert first["control"]["promotion"] == "none"
    assert first["provenance"]["operating_knowledge_schema"] == OPERATING_KNOWLEDGE_SCHEMA
    assert first["operating_knowledge_hash"]


def test_invalid_model_promotion_is_rejected_without_persisting_relation(tmp_path: Path):
    case = _case(tmp_path)

    def runner(_case, _prompt):
        value = json.loads(_response())
        value["relations"][0]["status"] = "supported"
        return json.dumps(value)

    result = analyze_case(case, runner=runner)
    assert result["analysis"]["relations"] == []
    assert result["analysis"]["model_violations"] == [{
        "kind": "bad_relation_status", "value": "supported"
    }]


def test_model_cannot_reuse_context_evidence_as_visual_artifact_evidence(tmp_path: Path):
    case = _case(tmp_path)

    def runner(_case, _prompt):
        value = json.loads(_response())
        value["observations"][0]["evidence_refs"] = ["ev:catalog"]
        return json.dumps(value)

    result = analyze_case(case, runner=runner)
    assert result["analysis"]["observations"] == []
    assert result["analysis"]["model_violations"] == [{
        "kind": "unbound_observation_evidence", "value": "archive-a:render.png"
    }]


def test_model_cannot_use_case_evidence_unbound_to_relation_endpoints(tmp_path: Path):
    case = _case(tmp_path)
    case["evidence_refs"].append("ev:unbound")

    def runner(_case, _prompt):
        value = json.loads(_response())
        value["relations"][0]["evidence_refs"] = ["ev:unbound"]
        return json.dumps(value)

    result = analyze_case(case, runner=runner)
    assert result["analysis"]["relations"] == []
    assert result["analysis"]["model_violations"] == [{
        "kind": "unbound_relation_evidence",
        "value": "archive-a:render.png->catalog:show-1",
    }]


def test_validator_errors_persist_as_non_evidence_memory(tmp_path: Path):
    case = _case(tmp_path)

    def runner(_case, _prompt):
        value = json.loads(_response())
        value["observations"][0]["evidence_refs"] = ["ev:catalog"]
        return json.dumps(value)

    result = analyze_case(case, runner=runner)
    store = LearningStore(tmp_path / "learning.sqlite")
    record_analysis(store, result)
    memory = load_validation_memory(store, "archive-a")
    assert memory == [{
        "snapshot_id": "snapshot-1",
        "model": "gemma3:4b",
        "violations": [{"kind": "unbound_observation_evidence", "value": "archive-a:render.png"}],
        "source": "automatic_validator",
    }]
    prompt = build_prompt(normalise_case(case), validation_memory=memory)
    assert "AUTOMATIC VALIDATION MEMORY (constraints, not evidence)" in prompt
    assert "unbound_observation_evidence" in prompt
    assert "PERSISTED FEEDBACK" in prompt


def test_validator_memory_replays_into_next_analysis_without_human_label(tmp_path: Path):
    case = _case(tmp_path)

    def invalid_runner(_case, _prompt):
        value = json.loads(_response())
        value["observations"][0]["evidence_refs"] = ["ev:catalog"]
        return json.dumps(value)

    store = LearningStore(tmp_path / "learning.sqlite")
    first = analyze_case(case, runner=invalid_runner)
    record_analysis(store, first)
    memory = load_validation_memory(store, "archive-a")
    seen = {}

    def next_runner(_case, prompt):
        seen["prompt"] = prompt
        return _response()

    second = analyze_case(case, runner=next_runner, validation_memory=memory)
    assert "unbound_observation_evidence" in seen["prompt"]
    assert second["analysis"]["observations"][0]["artifact_ref"] == "archive-a:render.png"


def test_feedback_is_persistent_negative_or_positive_memory(tmp_path: Path):
    case = _case(tmp_path)
    case["feedback"] = [
        {
            "feedback_id": "feedback-render-show",
            "source_ref": "archive-a:render.png",
            "target_ref": "catalog:show-1",
            "relation": "manifestation_of",
            "verdict": "contradict",
            "statement": "The visual was made by a third party.",
            "evidence_refs": ["ev:catalog"],
            "source": "explicit_evidence",
        }
    ]
    store = LearningStore(tmp_path / "learning.sqlite")
    first_ids = record_feedback(store, case)
    second_ids = record_feedback(store, case)
    assert first_ids == second_ids
    rows = load_feedback(store, "archive-a")
    assert len(rows) == 1
    assert rows[0]["verdict"] == "contradict"
    assert rows[0]["feedback_id"] == "feedback-render-show"
    prompt = build_prompt(normalise_case(case), rows)
    assert "third party" in prompt
    assert "contradict" in prompt


def test_model_analysis_and_feedback_are_separate_events(tmp_path: Path):
    case = _case(tmp_path)

    def runner(_case, _prompt):
        return _response()

    result = analyze_case(case, runner=runner)
    store = LearningStore(tmp_path / "learning.sqlite")
    event_id = record_analysis(store, result)
    assert event_id.startswith("vision-analysis-")
    events = store.operational_events("archive-a")
    assert len(events) == 1
    assert events[0]["event_type"] == "vision_analysis"
    assert load_feedback(store, "archive-a") == []


def test_clip_projection_is_deterministic_signal_only_and_keeps_physical_refs():
    vectors = {
        "archive-a:one.png": [1.0, 0.0],
        "archive-a:duplicate.png": [1.0, 0.0],
    }
    contexts = {"catalog:show-1": [1.0, 0.0]}
    first = clip_evidence_from_vectors(vectors, contexts, device="cuda")
    second = clip_evidence_from_vectors(dict(reversed(list(vectors.items()))), contexts, device="cuda")
    assert first == second
    assert first["schema"] == CLIP_SCHEMA
    assert [row["artifact_ref"] for row in first["artifact_embeddings"]] == [
        "archive-a:duplicate.png", "archive-a:one.png"
    ]
    assert len(first["alignments"]) == 2
    assert first["control"] == {
        "signal_only": True,
        "relation_promotion": False,
        "authorship_inference": False,
        "ranking": False,
    }


def test_clip_projection_rejects_invalid_vectors():
    with pytest.raises(VisionFeedbackError, match="clip_vector_zero"):
        clip_evidence_from_vectors({"archive-a:one.png": [0.0, 0.0]}, {})
    with pytest.raises(VisionFeedbackError, match="dimensions_mismatch"):
        clip_evidence_from_vectors(
            {"archive-a:one.png": [1.0, 0.0]},
            {"catalog:show-1": [1.0, 0.0, 0.0]},
        )


def test_clip_signal_is_passed_to_prompt_and_persisted_separately(tmp_path: Path):
    case = _case(tmp_path)
    clip_signal = clip_evidence_from_vectors(
        {"archive-a:render.png": [1.0, 0.0]},
        {"catalog:show-1": [1.0, 0.0]},
        device="cpu",
    )

    def runner(_case, prompt):
        assert "CLIP SIGNAL (weak feature only; never proof)" in prompt
        assert CLIP_SCHEMA in prompt
        return _response()

    result = analyze_case(case, runner=runner, clip_evidence=clip_signal)
    assert result["clip_evidence"] == clip_signal
    store = LearningStore(tmp_path / "learning.sqlite")
    record_analysis(store, result)
    event = store.operational_events("archive-a")[0]
    assert event["event_type"] == "vision_analysis"
    assert event["clip_evidence"] == clip_signal


def test_include_clip_uses_normalised_runtime_path_without_prompt_leak(tmp_path: Path, monkeypatch):
    case = _case(tmp_path)
    clip_signal = clip_evidence_from_vectors(
        {"archive-a:render.png": [1.0, 0.0]},
        {},
        device="cpu",
    )
    seen = {}

    def fake_extract(normalised, **_kwargs):
        seen["media_by_ref"] = normalised.get("_media_by_ref")
        seen["prompt_case"] = build_prompt(normalised)
        return clip_signal

    monkeypatch.setattr(
        "flujo.knowledge.vision_feedback_memory.extract_clip_evidence", fake_extract,
    )
    result = analyze_case(case, runner=lambda _case, _prompt: _response(), include_clip=True)
    assert result["clip_evidence"] == clip_signal
    assert seen["media_by_ref"] == {"archive-a:render.png": str(tmp_path / "render.png")}
    assert str(tmp_path) not in seen["prompt_case"]


def test_case_builder_connects_accepted_archive_projection_without_rescan(tmp_path: Path):
    root = tmp_path / "archive"
    root.mkdir()
    image = root / "exports" / "frame.png"
    image.parent.mkdir()
    image.write_bytes(b"bounded-observer-input")
    batch = observe_archive(root, "archive-builder")
    database = tmp_path / "learning.sqlite"
    ingest_observation_batch(database, batch)
    projection = project_archive_snapshot(
        replay_snapshot(database, archive_id="archive-builder", snapshot_id=batch["snapshot_id"])["snapshot"]
    )
    ref = next(item["artifact_ref"] for item in projection["artifacts"] if item["relative_path"] == "exports/frame.png")
    case = case_from_archive_projection(
        projection,
        artifact_refs=[ref],
        root=root,
        contexts=[{"context_ref": "ctx:catalog", "text": "An observed public visual context."}],
        evidence_refs=["ev:catalog"],
    )
    assert case["archive_id"] == projection["archive_id"]
    assert case["snapshot_id"] == projection["snapshot_id"]
    assert case["input_hash"] == projection["input_hash"]
    assert case["artifacts"][0]["artifact_ref"] == ref
    assert case["_media_by_ref"] == {ref: str(image)}
    assert str(root) not in build_prompt(case)
    replayed_case = normalise_case(case)
    assert replayed_case["_media_paths"] == [str(image)]
    assert replayed_case["_media_by_ref"] == {ref: str(image)}


def test_case_builder_rejects_ambiguous_or_unbounded_resolution(tmp_path: Path):
    projection = {
        "schema": "mak-archive-reconstruction-input-v1",
        "archive_id": "archive-a",
        "snapshot_id": "snapshot-a",
        "input_hash": "sha256:projection",
        "artifacts": [{"artifact_ref": "archive-a:file.png", "relative_path": "file.png", "kind": "image/png"}],
    }
    media = tmp_path / "file.png"
    media.write_bytes(b"bytes")
    with pytest.raises(VisionFeedbackError, match="root_and_artifact_paths"):
        case_from_archive_projection(
            projection,
            artifact_paths={"archive-a:file.png": media},
            root=tmp_path,
        )
    with pytest.raises(VisionFeedbackError, match="artifact_path_unknown_ref"):
        case_from_archive_projection(
            projection,
            artifact_paths={"archive-a:missing.png": media},
        )


def _context_package() -> dict:
    return {
        "schema": "mak-project-context-v1",
        "context_id": "context:fixture",
        "title": "Declared context fixture",
        "entities": [
            {"entity_id": "entity:track", "kind": "catalog_track", "display_name": "Escarlata (Remix)", "status": "observed", "purpose": "Named public context", "idea": "Candidate only"},
            {"entity_id": "entity:archive", "kind": "archive_artifact", "display_name": "ESCARLATA.mp4", "status": "candidate", "purpose": "Physical endpoint", "idea": "Path is not truth"},
        ],
        "sources": [
            {"source_id": "source:catalog", "source_type": "local_catalogue", "independence_group": "catalogue:fixture", "locator": "catalogue.json", "claim": "The catalogue names the track and collaborators.", "status": "observed"},
        ],
        "relations": [
            {"subject": "entity:archive", "predicate": "candidate_manifestation_of", "object": "entity:track", "status": "candidate", "source_ids": ["source:catalog"]},
        ],
        "projects": [],
        "unknowns": ["exact_delivery_binding"],
    }


def test_existing_context_graph_becomes_citation_bound_case_context(tmp_path: Path):
    media = tmp_path / "frame.png"
    media.write_bytes(b"frame")
    package = _context_package()
    contexts = contexts_from_project_context(package)
    by_ref = {item["context_ref"]: item for item in contexts}
    assert by_ref["entity:archive"]["evidence_refs"] == []
    assert by_ref["entity:track"]["evidence_refs"] == []
    source_context = by_ref["context-source:source:catalog"]
    assert source_context["evidence_refs"] == ["source:catalog"]
    assert "The catalogue names the track" in source_context["text"]
    relation_context = next(item for item in contexts if item["context_ref"].startswith("context-relation:"))
    assert relation_context["evidence_refs"] == ["source:catalog"]
    assert "source_id=source:catalog" in relation_context["text"]
    projection = {
        "schema": "mak-archive-reconstruction-input-v1",
        "archive_id": "archive-a",
        "snapshot_id": "snapshot-a",
        "input_hash": "sha256:projection",
        "artifacts": [{"artifact_ref": "archive-a:frame.png", "relative_path": "frame.png", "kind": "image/png"}],
    }
    case = case_from_project_context(
        projection,
        package,
        artifact_paths={"archive-a:frame.png": media},
    )
    assert case["context"] == contexts
    assert case["evidence_refs"] == ["source:catalog"]
    assert case["artifacts"][0]["evidence_refs"] == []


def test_context_graph_rejects_dangling_source_before_model_use():
    package = _context_package()
    package["relations"][0]["source_ids"] = ["source:missing"]
    with pytest.raises(VisionFeedbackError, match="context_package_invalid"):
        contexts_from_project_context(package)


def test_rejects_unknown_evidence_and_endpoint(tmp_path: Path):
    case = _case(tmp_path)
    case["feedback"] = [
        {
            "verdict": "support",
            "source_ref": "archive-a:missing.png",
            "target_ref": "catalog:show-1",
            "evidence_refs": ["ev:frame"],
        }
    ]
    with pytest.raises(VisionFeedbackError, match="unknown_endpoint"):
        normalise_case(case)


def test_cli_dry_run_is_available_without_model(tmp_path: Path, capsys):
    from flujo.knowledge.vision_feedback_memory import main

    path = tmp_path / "case.json"
    path.write_text(json.dumps(_case(tmp_path)), encoding="utf-8")
    assert main([str(path), "--dry-run"]) == 0
    assert "visual evidence analyst" in capsys.readouterr().out


def test_cli_can_start_from_existing_projection_and_context(tmp_path: Path, capsys):
    from flujo.knowledge.vision_feedback_memory import main

    media = tmp_path / "frame.png"
    media.write_bytes(b"frame")
    projection_path = tmp_path / "projection.json"
    projection_path.write_text(json.dumps({
        "schema": "mak-archive-reconstruction-input-v1",
        "archive_id": "archive-cli",
        "snapshot_id": "snapshot-cli",
        "input_hash": "sha256:projection-cli",
        "artifacts": [{"artifact_ref": "archive-cli:frame.png", "relative_path": "frame.png", "kind": "image/png"}],
    }), encoding="utf-8")
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(_context_package()), encoding="utf-8")
    assert main([
        "--projection", str(projection_path),
        "--context-package", str(context_path),
        "--root", str(tmp_path),
        "--artifact-ref", "archive-cli:frame.png",
        "--dry-run",
    ]) == 0
    output = capsys.readouterr().out
    assert "Declared context relation" in output
    assert "Declared evidence source" in output
    assert str(tmp_path) not in output
