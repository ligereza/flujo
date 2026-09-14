from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from src.flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from src.flujo.knowledge.archive_observer import observe_archive
from src.flujo.knowledge.archive_reconstruction import project_archive_snapshot
from src.flujo.knowledge.operational_memberships import (
    CAPABILITIES,
    CAPABILITY_SCHEMA,
    EVENT_SCHEMA,
    OperationalMembershipError,
    build_operational_event,
    event_id_for,
    events_from_unit_assignments,
    persist_operational_event,
    project_archive_capabilities,
    project_artifact_capabilities,
    project_operational_memberships,
    project_store_memberships,
    proposition_id_for,
    reopen_event_for_material_evidence,
    unit_lineage_ref_for,
    validate_capability_payload,
    validate_membership_projection,
    validate_operational_event,
)
from src.flujo.knowledge.project_ir import LearningStore


def _event(
    *,
    archive_id: str = "archive-a",
    subject_ref: str = "artifact:shared",
    object_ref: str = "unit:a",
    role: str = "resource",
    event_type: str = "PROPOSE",
    evidence_refs: tuple[str, ...] = (),
    negative_evidence_refs: tuple[str, ...] = (),
    signal_refs: tuple[str, ...] = (),
    payload: dict | None = None,
    supersedes_event_id: str | None = None,
    caused_by_event_ids: tuple[str, ...] = (),
    recorded_at: str = "2026-08-27T10:00:00+00:00",
) -> dict:
    return build_operational_event(
        archive_id=archive_id,
        subject_ref=subject_ref,
        predicate="member_of",
        object_ref=object_ref,
        role=role,
        event_type=event_type,
        scope_ref="test",
        evidence_refs=evidence_refs,
        negative_evidence_refs=negative_evidence_refs,
        signal_refs=signal_refs,
        payload=payload or {},
        supersedes_event_id=supersedes_event_id,
        caused_by_event_ids=caused_by_event_ids,
        recorded_at=recorded_at,
    )


def test_shared_resource_memberships_are_independent() -> None:
    a = _event(object_ref="unit:a")
    b = _event(object_ref="unit:b")
    payload = project_operational_memberships([a, b])
    assert validate_membership_projection(payload) is True
    assert len(payload["memberships"]) == 2
    assert {item["object_ref"] for item in payload["memberships"]} == {"unit:a", "unit:b"}
    assert payload["reconciliation"]["truth_promotions"] == 0


def test_rejecting_a_does_not_change_b_and_is_negative_memory() -> None:
    a_propose = _event(object_ref="unit:a", evidence_refs=("obs:a",))
    a_reject = _event(
        object_ref="unit:a",
        event_type="REJECT",
        negative_evidence_refs=("decision:not-a",),
        supersedes_event_id=a_propose["event_id"],
        payload={"reopen_triggers": ["native_reference_added"]},
    )
    b = _event(object_ref="unit:b", evidence_refs=("obs:b",))
    payload = project_operational_memberships([a_propose, a_reject, b])
    by_object = {item["object_ref"]: item for item in payload["memberships"]}
    assert by_object["unit:a"]["status"] == "rejected"
    assert by_object["unit:b"]["status"] == "proposed"
    assert [item["object_ref"] for item in payload["negative_memory"]] == ["unit:a"]
    assert payload["negative_memory"][0]["reopen_triggers"] == ["native_reference_added"]


def test_only_declared_material_evidence_reopens_a_rejection_end_to_end(tmp_path: Path) -> None:
    store = LearningStore(tmp_path / "learning.sqlite")
    proposed = _event(payload={"reopen_triggers": ["native_reference_added"]})
    rejected = _event(
        event_type="REJECT",
        negative_evidence_refs=("decision:not-a",),
        supersedes_event_id=proposed["event_id"],
        caused_by_event_ids=(proposed["event_id"],),
        payload={"reopen_triggers": ["native_reference_added"]},
    )
    for event in (proposed, rejected):
        persist_operational_event(store, event)
    assert project_store_memberships(store, "archive-a")["memberships"][0]["status"] == "rejected"
    with pytest.raises(OperationalMembershipError, match="reopen_trigger_not_allowed"):
        reopen_event_for_material_evidence(rejected, trigger="file_renamed")
    reopened = reopen_event_for_material_evidence(
        rejected,
        trigger="native_reference_added",
        evidence_refs=("obs:native-manifest",),
        signal_refs=("signal:native-reference",),
    )
    persist_operational_event(store, reopened)
    view = project_store_memberships(store, "archive-a")
    assert view["memberships"][0]["status"] == "proposed"
    assert view["memberships"][0]["proposition_id"] == proposed["proposition_id"]
    assert view["memberships"][0]["evidence_refs"] == ["obs:native-manifest"]
    assert view["negative_memory"] == []


def test_conflicting_concurrent_decisions_are_not_resolved_by_time() -> None:
    propose = _event()
    accept = _event(
        event_type="ACCEPT",
        supersedes_event_id=propose["event_id"],
        recorded_at="2026-08-27T12:00:00+00:00",
    )
    reject = _event(
        event_type="REJECT",
        negative_evidence_refs=("decision:not-a",),
        supersedes_event_id=propose["event_id"],
        recorded_at="2026-08-27T09:00:00+00:00",
    )
    payload = project_operational_memberships([reject, accept, propose])
    assert payload["memberships"][0]["status"] == "conflicted"


def test_proposition_identity_excludes_evidence_and_event_time() -> None:
    first = _event(evidence_refs=("obs:one",), recorded_at="2026-08-27T09:00:00+00:00")
    second = _event(evidence_refs=("obs:two",), recorded_at="2026-08-27T12:00:00+00:00")
    assert first["proposition_id"] == second["proposition_id"]
    assert first["event_id"] != second["event_id"]
    assert proposition_id_for(
        archive_id="archive-a",
        subject_ref="artifact:shared",
        predicate="member_of",
        object_ref="unit:a",
        role="resource",
        scope_ref="test",
    ) == first["proposition_id"]


def test_unit_lineage_excludes_snapshot_and_membership_changes() -> None:
    base = {
        "role": "project_unit",
        "root_path": "projects/a",
        "anchor_refs": ["artifact:a.blend"],
        "member_refs": [],
    }
    changed = copy.deepcopy(base)
    changed["member_refs"] = ["artifact:a.mp4"]
    assert unit_lineage_ref_for(base, "archive-a") == unit_lineage_ref_for(changed, "archive-a")


def test_existing_learning_store_is_append_only_and_idempotent(tmp_path: Path) -> None:
    store = LearningStore(tmp_path / "learning.sqlite")
    first = _event(recorded_at="2026-08-27T09:00:00+00:00")
    retry = dict(first)
    retry["recorded_at"] = "2026-08-27T12:00:00+00:00"
    assert event_id_for(first) == event_id_for(retry)
    assert persist_operational_event(store, first) == persist_operational_event(store, retry)
    with sqlite3.connect(store.database) as con:
        assert con.execute("SELECT COUNT(*) FROM mak_operational_events").fetchone()[0] == 1
        stored_time = con.execute("SELECT recorded_at FROM mak_operational_events").fetchone()[0]
    assert stored_time == first["recorded_at"]
    with pytest.raises(sqlite3.IntegrityError):
        with store.connect() as con:
            con.execute("DELETE FROM mak_operational_events")


def test_store_projection_is_archive_isolated_and_cli_is_read_only(tmp_path: Path) -> None:
    db = tmp_path / "learning.sqlite"
    store = LearningStore(db)
    persist_operational_event(store, _event(archive_id="archive-a"))
    persist_operational_event(store, _event(archive_id="archive-b"))
    a = project_store_memberships(store, "archive-a")
    assert a["archive_id"] == "archive-a"
    assert all(item["archive_id"] == "archive-a" for item in a["memberships"])
    output = tmp_path / "view.json"
    result = subprocess.run(
        [
            sys.executable, "tools/inspect_operational_memberships.py",
            "--db", str(db), "--archive-id", "archive-a", "--output", str(output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["archive_id"] == "archive-a"


def test_unit_assignments_become_proposals_only() -> None:
    units = {
        "archive_id": "archive-a",
        "snapshot_id": "snapshot:1",
        "units": [{
            "unit_id": "unit:snapshot-specific",
            "role": "project_unit",
            "root_path": "projects/a",
            "anchor_refs": ["artifact:a.blend"],
        }],
        "assignments": [{"artifact_ref": "artifact:a.mp4", "status": "assigned", "unit_id": "unit:snapshot-specific"}],
    }
    events = events_from_unit_assignments(units)
    assert len(events) == 1
    assert events[0]["event_type"] == "PROPOSE"
    assert events[0]["role"] == "unknown"
    assert events[0]["payload"]["source_unit_id"] == "unit:snapshot-specific"


def test_malformed_event_fails_closed() -> None:
    event = _event()
    event["event_id"] = "event:forged"
    with pytest.raises(OperationalMembershipError):
        validate_operational_event(event)


def test_duplicate_event_ids_fail_closed_in_projection() -> None:
    event = _event()
    with pytest.raises(OperationalMembershipError):
        project_operational_memberships([event, copy.deepcopy(event)])


@given(st.sampled_from(["2026-08-27T09:00:00+00:00", "2027-01-01T00:00:00+00:00"]))
def test_property_recording_time_never_changes_event_identity(recorded_at: str) -> None:
    event = _event(recorded_at=recorded_at)
    other = dict(event, recorded_at="2099-01-01T00:00:00+00:00")
    assert event_id_for(event) == event_id_for(other)
    assert validate_operational_event(event) is True


def test_event_schema_is_canonical() -> None:
    assert _event()["schema"] == EVENT_SCHEMA


def _capability_projection(tmp_path: Path) -> dict:
    root = tmp_path / "capability-archive"
    media = root / "media"
    media.mkdir(parents=True)
    (media / "still.png").write_bytes(b"png")
    (media / "clip.mp4").write_bytes(b"mp4")
    (media / "script.py").write_text("print('ok')", encoding="utf-8")
    (media / "mystery.xyz").write_bytes(b"unknown")
    (root / "link.mp4").symlink_to(media / "clip.mp4")
    database = tmp_path / "capability.sqlite"
    batch = observe_archive(root, "capability-archive")
    ingest_observation_batch(database, batch)
    snapshot = replay_snapshot(
        database,
        archive_id="capability-archive",
        snapshot_id=batch["snapshot_id"],
    )["snapshot"]
    return project_archive_snapshot(snapshot)


def test_capability_projection_replays_real_archive_without_claiming_providers(
    tmp_path: Path,
) -> None:
    projection = _capability_projection(tmp_path)
    before = copy.deepcopy(projection)
    payload = project_archive_capabilities(projection)

    assert payload["schema"] == CAPABILITY_SCHEMA
    assert validate_capability_payload(projection, payload) is True
    assert project_archive_capabilities(projection) == payload
    assert projection == before
    assert payload["reconciliation"]["artifacts_projected"] == len(projection["artifacts"])
    assert payload["reconciliation"]["capability_rows"] == len(projection["artifacts"]) * len(CAPABILITIES)
    assert payload["control"] == {
        "database_write": False,
        "source_mutation": False,
        "promotion": "none",
        "dispatch": False,
    }

    by_name = {record["relative_path"]: record for record in payload["capabilities"]}
    video = by_name["media/clip.mp4"]
    still = by_name["media/still.png"]
    script = by_name["media/script.py"]
    unknown = by_name["media/mystery.xyz"]
    link = by_name["link.mp4"]

    def states(record: dict) -> dict[str, str]:
        return {row["capability"]: row["state"] for row in record["capabilities"]}

    assert states(video)["transcribe"] == "possible"
    assert states(video)["semantic_search"] == "blocked"
    assert states(still)["ocr"] == "possible"
    # The observer declares this .py file as text because its media type is
    # text/x-python; the capability layer does not override that observation
    # from the suffix.  The explicit code-family contract is tested below.
    assert states(script)["index_code"] == "unsupported"
    assert states(script)["execute"] == "unsupported"
    assert states(unknown)["preview"] == "unsupported"
    assert states(link)["preview"] == "blocked"
    assert all(states(record)[name] == "blocked" for record in by_name.values() for name in ("backup", "export"))
    assert all(
        row["evidence_refs"] == [record["artifact_ref"]]
        for record in by_name.values()
        for row in record["capabilities"]
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert "mtime_ns" not in encoded
    assert str(tmp_path) not in encoded


def test_capability_projection_fails_closed_and_never_accepts_volatile_input(
    tmp_path: Path,
) -> None:
    projection = _capability_projection(tmp_path)
    malformed_projection = copy.deepcopy(projection)
    malformed_projection["artifacts"][0]["mtime_ns"] = 1
    with pytest.raises(OperationalMembershipError, match="fields_invalid"):
        project_archive_capabilities(malformed_projection)

    payload = project_archive_capabilities(projection)
    malformed_payload = copy.deepcopy(payload)
    malformed_payload["capabilities"][0]["capabilities"][0]["state"] = "possible"
    with pytest.raises(OperationalMembershipError, match="not_replayable"):
        validate_capability_payload(projection, malformed_payload)


def test_single_artifact_capability_contract_preserves_physical_identity() -> None:
    artifact = {
        "artifact_id": "artifact:file",
        "physical_id": "physical:file",
        "artifact_ref": "archive-artifact:file",
        "references": ["archive-artifact:file"],
        "relative_path": "project/scene.py",
        "parent_path": "project",
        "basename": "scene.py",
        "stem": "scene",
        "suffix_chain": [".py"],
        "kind": "file",
        "availability": "available",
        "family": "code",
        "media_type": "text/x-python",
        "size": 1,
        "sha256": "sha256:abc",
        "content_id": "content:abc",
        "derived_flags": {},
    }
    result = project_artifact_capabilities(artifact)
    assert result["artifact_ref"] == "archive-artifact:file"
    assert result["physical_id"] == "physical:file"
    assert [row["capability"] for row in result["capabilities"]] == list(CAPABILITIES)


def test_membership_cli_can_join_capabilities_without_writing_them(
    tmp_path: Path,
) -> None:
    projection = _capability_projection(tmp_path)
    projection_path = tmp_path / "reconstruction-input.json"
    projection_path.write_text(
        json.dumps(projection, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    database = tmp_path / "membership.sqlite"
    event = _event(
        archive_id="capability-archive",
        subject_ref="archive-artifact:file",
        object_ref="unit:project",
    )
    persist_operational_event(LearningStore(database), event)
    result = subprocess.run(
        [
            sys.executable,
            "tools/inspect_operational_memberships.py",
            "--db", str(database),
            "--archive-id", "capability-archive",
            "--projection", str(projection_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["memberships"][0]["subject_ref"] == "archive-artifact:file"
    assert output["capability_projection"]["schema"] == CAPABILITY_SCHEMA
    assert output["capability_projection"]["archive_id"] == "capability-archive"
