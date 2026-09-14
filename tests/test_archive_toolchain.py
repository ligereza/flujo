from __future__ import annotations

import json
import builtins
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from flujo.knowledge.archive_observer import observe_archive
from flujo.knowledge.archive_reconstruction import project_archive_snapshot
from flujo.knowledge.archive_toolchain import (
    ArchiveToolchainError,
    SCHEMA,
    inspect_archive_projection,
    ingest_czkawka_duplicate_report,
    ingest_czkawka_similarity_report,
    project_tool_observations_to_context,
    record_tool_observations,
    serialize_output,
    validate_toolchain_output,
)
from flujo.knowledge.project_context import persist_context, read_context, validate_context
from flujo.knowledge.project_ir import LearningStore


def _projection(root: Path, *, archive_id: str = "tool-test") -> dict:
    batch = observe_archive(root, archive_id)
    return project_archive_snapshot(batch)


def test_real_toolchain_uses_projection_and_extracts_multiple_formats(tmp_path: Path):
    (tmp_path / "poster.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    )
    (tmp_path / "notes.txt").write_text("Escarlata remix\nBAH party\n", encoding="utf-8")
    projection = _projection(tmp_path)
    output = inspect_archive_projection(projection, root=tmp_path)
    assert output["schema"] == SCHEMA
    assert output["control"]["source_mutation"] is False
    assert output["reconciliation"]["artifacts_input"] == len(projection["artifacts"])
    assert output["reconciliation"]["artifact_loss"] == 0
    assert "czkawka" in output["tool_inventory"]
    if output["tool_inventory"]["czkawka"]["path_available"]:
        assert output["tool_inventory"]["czkawka"]["version"] == "12.0.1"
    assert validate_toolchain_output(output) is True
    assert any(row["observation_type"] == "file_signature" for row in output["observations"])
    assert any(row["observation_type"] == "text_fingerprint" for row in output["observations"])
    assert all(row["evidence_refs"] == [row["artifact_ref"]] for row in output["observations"])


def test_duplicate_bytes_remain_separate_and_share_only_content_in_source(tmp_path: Path):
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")
    projection = _projection(tmp_path)
    refs = {row["artifact_ref"] for row in projection["artifacts"] if row["kind"] == "file"}
    output = inspect_archive_projection(projection, root=tmp_path)
    observed_refs = {row["artifact_ref"] for row in output["observations"]}
    assert refs <= observed_refs
    assert len(refs) == 2
    assert len({row["artifact_ref"] for row in output["observations"]}) == 2


def test_symlink_and_unavailable_artifact_are_preserved_without_following(tmp_path: Path):
    (tmp_path / "target.txt").write_text("target", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to("target.txt")
    projection = _projection(tmp_path)
    link = next(row for row in projection["artifacts"] if row["relative_path"] == "link.txt")
    output = inspect_archive_projection(projection, root=tmp_path)
    rows = [row for row in output["observations"] if row["artifact_ref"] == link["artifact_ref"]]
    assert rows
    assert all(row["status"] == "unavailable" for row in rows)
    assert output["reconciliation"]["artifact_loss"] == 0


def test_ocr_is_explicit_and_read_only(tmp_path: Path):
    from PIL import Image

    image = Image.new("RGB", (120, 40), "white")
    image.save(tmp_path / "label.png")
    projection = _projection(tmp_path)
    output = inspect_archive_projection(projection, root=tmp_path, ocr=True)
    rows = [row for row in output["observations"] if row["observation_type"] == "ocr_text"]
    assert rows
    assert output["control"]["source_mutation"] is False


def test_native_psd_and_kra_structure_is_observed_without_render_or_mutation(tmp_path: Path):
    # psd-tools is an OPTIONAL capability: archive_toolchain.py and
    # diagnostico_proyectos.py both gate on `find_spec("psd_tools")` and
    # degrade when it is absent. It is present on MAK and absent in CI, so
    # importing it unguarded here is what turned a green local suite into a
    # red CI right after the 2026-08-29 push. Skip naming what is missing.
    pytest.importorskip("psd_tools", reason="psd-tools is optional and not installed here")
    from PIL import Image
    from psd_tools import PSDImage

    psd_path = tmp_path / "source.psd"
    psd = PSDImage.new(mode="RGB", size=(16, 8))
    psd.create_pixel_layer(Image.new("RGB", (16, 8), "black"), name="Source Layer")
    psd.save(psd_path)
    kra_path = tmp_path / "layout.kra"
    with zipfile.ZipFile(kra_path, "w") as archive:
        archive.writestr("mimetype", "application/x-krita")
        archive.writestr(
            "maindoc.xml",
            """<DOC xmlns=\"http://www.calligra.org/DTD/krita\" kritaVersion=\"5.3.1\">
            <IMAGE width=\"32\" height=\"16\" colorspacename=\"RGBA16\">
              <layer name=\"Render Source\" nodetype=\"paintlayer\"/>
            </IMAGE></DOC>""",
        )
        archive.writestr(
            "documentinfo.xml",
            """<document-info xmlns=\"http://www.calligra.org/DTD/document-info\">
            <about><title>layout</title><editing-cycles>2</editing-cycles></about>
            </document-info>""",
        )
        archive.writestr("preview.png", b"preview")
    output = inspect_archive_projection(_projection(tmp_path, archive_id="native-test"), root=tmp_path)
    native = {
        row["relative_path"]: row
        for row in output["observations"]
        if row["observation_type"] == "native_structure"
    }
    assert native["source.psd"]["status"] == "observed"
    assert native["source.psd"]["facts"]["layer_count"] == 1
    assert native["source.psd"]["facts"]["named_layers"][0]["name"] == "Source Layer"
    assert native["layout.kra"]["status"] == "observed"
    assert native["layout.kra"]["facts"]["width"] == 32
    assert native["layout.kra"]["facts"]["document_info"]["title"] == "layout"
    assert output["control"]["source_mutation"] is False


def test_native_surface_component_matches_explicit_raster_candidate(tmp_path: Path):
    pytest.importorskip("psd_tools", reason="psd-tools is optional and not installed here")
    from PIL import Image, ImageDraw
    from psd_tools import PSDImage

    pixels = Image.new("RGB", (40, 24), "white")
    draw = ImageDraw.Draw(pixels)
    draw.rectangle((8, 4, 31, 19), fill="black")
    pixels.save(tmp_path / "logo_asset.png")
    psd = PSDImage.new(mode="RGB", size=pixels.size)
    psd.create_pixel_layer(pixels, name="Brand logo")
    psd.save(tmp_path / "layout.psd")

    output = inspect_archive_projection(_projection(tmp_path, archive_id="surface-test"), root=tmp_path)
    assert validate_toolchain_output(output) is True
    surface_rows = [
        row for row in output["observations"]
        if row["observation_type"] == "surface_match_retrieval"
    ]
    assert surface_rows
    assert {row["facts"]["target_ref"] for row in surface_rows} == {
        row["artifact_ref"] for row in output["observations"]
        if row["relative_path"] == "logo_asset.png"
    }
    assert any("perceptual_surface_similarity" in row["facts"]["signals"] for row in surface_rows)
    context = project_tool_observations_to_context(output)
    assert validate_context(context) == []
    assert any(
        row["predicate"] == "technical_surface_match_candidate"
        for row in context["relations"]
    )
    assert all(row["metadata"]["truth_promotion"] is False for row in context["relations"])


def test_native_psd_degrades_explicitly_when_optional_package_is_missing(
        tmp_path: Path, monkeypatch):
    from flujo.knowledge import archive_toolchain

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "psd_tools" or name.startswith("psd_tools."):
            raise ImportError("optional package absent")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    result = archive_toolchain._psd(tmp_path / "source.psd", {}, 10)
    assert result["status"] == "unavailable"
    assert result["facts"] == {"format": "psd", "reason": "package_missing"}


def test_numbered_same_family_siblings_do_not_create_weak_media_edges(tmp_path: Path):
    from PIL import Image

    for index in range(1, 6):
        Image.new("RGB", (128, 64), (index * 20, 20, 20)).save(
            tmp_path / f"Isotipo Myra-{index:02d}.png"
        )

    output = inspect_archive_projection(_projection(tmp_path, archive_id="siblings"), root=tmp_path)
    context = project_tool_observations_to_context(output)

    assert validate_context(context) == []
    assert not any(
        row["predicate"] == "technical_media_match_candidate"
        for row in context["relations"]
    )


def test_unknown_ref_and_root_escape_fail_closed(tmp_path: Path):
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    projection = _projection(tmp_path)
    with pytest.raises(ArchiveToolchainError, match="unknown_artifact_ref"):
        inspect_archive_projection(projection, root=tmp_path, artifact_refs=["not-present"])
    bad = json.loads(json.dumps(projection))
    bad["artifacts"][0]["relative_path"] = "../outside.txt"
    with pytest.raises(ArchiveToolchainError, match="relative_path_invalid"):
        inspect_archive_projection(bad, root=tmp_path)


def test_output_is_deterministic_and_can_be_persisted_idempotently(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("one\ntwo\n", encoding="utf-8")
    projection = _projection(tmp_path, archive_id="archive-ledger")
    first = inspect_archive_projection(projection, root=tmp_path)
    second = inspect_archive_projection(projection, root=tmp_path)
    assert first == second
    assert serialize_output(first) == serialize_output(second)
    db = tmp_path / "learning.sqlite"
    store = LearningStore(db)
    first_id = record_tool_observations(store, first)
    second_id = record_tool_observations(store, second)
    assert first_id == second_id
    events = store.operational_events("archive-ledger")
    assert len(events) == 1
    assert events[0]["event_type"] == "archive_tool_observations"


def test_validator_rejects_unbound_observation(tmp_path: Path):
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    output = inspect_archive_projection(_projection(tmp_path), root=tmp_path)
    output["observations"][0]["evidence_refs"] = ["different-ref"]
    with pytest.raises(ArchiveToolchainError, match="evidence_unbound"):
        validate_toolchain_output(output)


def test_validator_rejects_fact_changes_without_recomputed_identity(tmp_path: Path):
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    output = inspect_archive_projection(_projection(tmp_path), root=tmp_path)
    output["observations"][0]["facts"]["tampered"] = True
    with pytest.raises(ArchiveToolchainError, match="id_mismatch"):
        validate_toolchain_output(output)


def test_czkawka_duplicate_report_becomes_candidate_without_physical_merge(tmp_path: Path):
    (tmp_path / "one.png").write_bytes(b"same-bytes")
    (tmp_path / "two.png").write_bytes(b"same-bytes")
    projection = _projection(tmp_path, archive_id="czkawka-test")
    output = inspect_archive_projection(projection, root=tmp_path)
    report = {"10": [[
        {"path": str(tmp_path / "one.png"), "size": 10, "hash": "a" * 64},
        {"path": str(tmp_path / "two.png"), "size": 10, "hash": "a" * 64},
    ]]}
    augmented = ingest_czkawka_duplicate_report(output, report, root=tmp_path)
    assert validate_toolchain_output(augmented) is True
    duplicates = [row for row in augmented["observations"] if row["observation_type"] == "duplicate_retrieval"]
    assert len(duplicates) == 2
    assert {tuple(row["facts"]["member_refs"]) for row in duplicates} == {
        tuple(sorted(row["artifact_ref"] for row in projection["artifacts"] if row["kind"] == "file"))
    }
    context = project_tool_observations_to_context(augmented)
    assert validate_context(context) == []
    assert sum(row["predicate"] == "technical_duplicate_candidate" for row in context["relations"]) == 1
    assert context["relations"][0]["metadata"]["physical_merge"] is False


def test_czkawka_report_ignores_group_with_unselected_path(tmp_path: Path):
    (tmp_path / "one.txt").write_text("same", encoding="utf-8")
    projection = _projection(tmp_path, archive_id="czkawka-skip")
    output = inspect_archive_projection(projection, root=tmp_path)
    report = {"4": [[
        {"path": str(tmp_path / "one.txt"), "size": 4, "hash": "b" * 64},
        {"path": str(tmp_path / "outside.txt"), "size": 4, "hash": "b" * 64},
    ]]}
    augmented = ingest_czkawka_duplicate_report(output, report, root=tmp_path)
    assert not any(row["observation_type"] == "duplicate_retrieval" for row in augmented["observations"])
    assert augmented["reconciliation"]["czkawka_skipped_groups"] == 1


def test_czkawka_image_similarity_becomes_candidate_not_identity(tmp_path: Path):
    (tmp_path / "one.png").write_bytes(b"image-one")
    (tmp_path / "two.png").write_bytes(b"image-two")
    projection = _projection(tmp_path, archive_id="czkawka-image")
    output = inspect_archive_projection(projection, root=tmp_path)
    report = [[
        {"path": str(tmp_path / "one.png"), "difference": 2},
        {"path": str(tmp_path / "two.png"), "difference": 2},
    ]]
    augmented = ingest_czkawka_similarity_report(
        output, report, root=tmp_path, mode="image", max_difference=10,
    )
    assert validate_toolchain_output(augmented) is True
    rows = [row for row in augmented["observations"] if row["observation_type"] == "similarity_retrieval"]
    assert len(rows) == 2
    assert rows[0]["facts"]["similarity_score"] == 0.8
    context = project_tool_observations_to_context(augmented)
    assert validate_context(context) == []
    matches = [row for row in context["relations"] if row["predicate"] == "technical_similarity_candidate"]
    assert len(matches) == 1
    assert matches[0]["metadata"]["physical_merge"] is False


def test_czkawka_video_signature_without_numeric_score_stays_candidate(tmp_path: Path):
    (tmp_path / "one.mp4").write_bytes(b"video-one")
    (tmp_path / "two.mov").write_bytes(b"video-two")
    projection = _projection(tmp_path, archive_id="czkawka-video")
    output = inspect_archive_projection(projection, root=tmp_path)
    report = [[
        {"path": str(tmp_path / "one.mp4"), "signature": {}},
        {"path": str(tmp_path / "two.mov"), "signature": {}},
    ]]
    augmented = ingest_czkawka_similarity_report(
        output, report, root=tmp_path, mode="video",
    )
    rows = [row for row in augmented["observations"] if row["observation_type"] == "similarity_retrieval"]
    assert len(rows) == 2
    assert rows[0]["facts"]["similarity_score"] is None
    context = project_tool_observations_to_context(augmented)
    matches = [row for row in context["relations"] if row["predicate"] == "technical_similarity_candidate"]
    assert len(matches) == 1
    assert "similarity_score" not in matches[0]["metadata"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required for the real media pair")
def test_real_tool_observations_reach_existing_context_consumer(tmp_path: Path):
    pytest.importorskip("imagehash", reason="ImageHash is optional and not installed here")
    from PIL import Image

    image_path = tmp_path / "MISIONAR (1-14-00-10).png"
    Image.new("RGB", (2048, 1024), "black").save(image_path)
    video_path = tmp_path / "MISIONAR .mp4"
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", "color=c=black:s=2048x1024:d=0.1", "-pix_fmt", "yuv420p",
        "-an", str(video_path),
    ], check=True, capture_output=True)
    projection = _projection(tmp_path, archive_id="context-tool-test")
    output = inspect_archive_projection(projection, root=tmp_path)
    package = project_tool_observations_to_context(output)
    assert validate_context(package) == []
    assert package["projects"] == []
    assert len(package["entities"]) == 2
    assert any(row["predicate"] == "technical_media_match_candidate" for row in package["relations"])
    db = tmp_path / "context.sqlite"
    persisted = persist_context(db, package)
    assert persisted["relation_count"] >= 1
    readback = read_context(db, context_id=package["context_id"])
    assert readback["available"] is True
    assert readback["contexts"][0]["relations"]


def test_cli_can_emit_existing_context_projection(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("DREF Escarlata\n", encoding="utf-8")
    projection_path = tmp_path / "projection.json"
    projection_path.write_text(
        json.dumps(_projection(tmp_path), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    observations_path = tmp_path / "observations.json"
    context_path = tmp_path / "context.json"
    result = subprocess.run(
        [
            sys.executable,  # not `.venv/bin/python`: that file does not exist in CI
            "tools/run_archive_toolchain.py",
            str(projection_path),
            "--root", str(tmp_path),
            "--output", str(observations_path),
            "--context-output", str(context_path),
        ],
        cwd=Path(__file__).parents[1],
        env={"PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    observations = json.loads(observations_path.read_text(encoding="utf-8"))
    context = json.loads(context_path.read_text(encoding="utf-8"))
    assert validate_toolchain_output(observations) is True
    assert validate_context(context) == []
    assert context["provenance"]["source_schema"] == SCHEMA
