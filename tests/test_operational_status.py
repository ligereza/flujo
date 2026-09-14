"""Tests for the unified, read-only MAK status envelope."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from flujo.knowledge.project_api import operational_status
from flujo.knowledge.project_ir import LearningStore, build_project_ir
from flujo.knowledge.system_status import (
    _mount_component,
    _provider_source_root,
    _repo_component,
    system_status,
)


def test_operational_status_is_read_only_and_surfaces_next_actions(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    project = build_project_ir(
        project_id="status-demo",
        title="Status demo",
        source_root=tmp_path,
        state="review_required",
        unknowns=["evidence"],
    )
    store.save_project(project)
    store.record_episode(
        project_id=project["project_id"],
        objective="bounded probe",
        phase="gate",
        action={"tool": "project_router"},
        observation={},
        outcome={"decision": "abstain"},
        validation={"status": "needs_evidence"},
        status="needs_evidence",
        episode_id="episode-status-demo",
    )
    before = (database.stat().st_size, database.stat().st_mtime_ns)

    result = operational_status(database, repo_root=tmp_path)

    after = (database.stat().st_size, database.stat().st_mtime_ns)
    assert before == after
    assert result["schema"] == "mak-operational-status-v1"
    assert result["read_only"] is True
    assert result["status"] == "attention"
    assert result["counts"]["attention"] >= 2
    ids = {item["id"] for item in result["attention"]}
    assert "projects:review_required" in ids
    assert "episodes:needs_evidence" in ids
    assert result["next_actions"]
    project_attention = next(item for item in result["attention"] if item["id"] == "projects:review_required")
    assert "source kinds: folder=1" in project_attention["reason"]
    assert "open episodes: 1" in project_attention["reason"]
    review_queue = result["learning"]["review_queue"]
    assert review_queue["projects"]["total"] == 1
    assert review_queue["projects"]["by_source_kind"] == {"folder": 1}
    assert review_queue["projects"]["items"] == [{
        "project_id": "status-demo",
        "title": "Status demo",
        "source_kind": "folder",
        "source_root_observed_present": True,
        "unknown_count": 1,
        "unknowns": ["evidence"],
        "evidence_kinds": [],
        "next_action": "review_evidence",
    }]
    assert review_queue["episodes"] == {
        "open_total": 1,
        "by_phase_status": {"gate": {"needs_evidence": 1}},
    }


def test_operational_status_reports_missing_ledger_without_writing(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite"

    result = operational_status(database, repo_root=tmp_path)

    assert result["status"] == "unknown"
    assert result["read_only"] is True
    assert result["attention"][0]["id"] == "learning_ledger"
    assert not database.exists()


def test_system_status_keeps_component_contract_when_provider_box_is_absent(tmp_path: Path) -> None:
    result = system_status(
        tmp_path / "missing.sqlite",
        repo_root=tmp_path,
        physical_root=tmp_path,
    )

    assert result["schema"] == "mak-system-status-v1"
    assert all("severity" in component for component in result["components"].values())
    assert result["components"]["providers"]["severity"] == "attention"


def test_system_status_resolves_provider_box_from_physical_adapter_root(tmp_path: Path) -> None:
    repo = tmp_path / "flujo"
    physical = tmp_path / "mak"
    provider = physical / "cultura" / "mak_plataforma" / "providers.py"
    provider.parent.mkdir(parents=True)
    provider.write_text("# fixture provider registry\n", encoding="utf-8")

    assert _provider_source_root(repo, physical) == physical


def test_system_status_accepts_declared_absence_of_root_contract(tmp_path: Path) -> None:
    repo = tmp_path / "flujo"
    physical = tmp_path / "mak"
    (physical / "cultura" / "mak_plataforma").mkdir(parents=True)
    (repo / "src" / "flujo" / "knowledge").mkdir(parents=True)
    (repo / "web").mkdir()
    (repo / "context" / "diagnostics" / "contracts").mkdir(parents=True)
    (physical / "cultura" / "mak_plataforma" / "hub.py").write_text("# fixture\n", encoding="utf-8")
    (repo / "src" / "flujo" / "knowledge" / "project_api.py").write_text("# fixture\n", encoding="utf-8")
    (repo / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "context" / "diagnostics" / "contracts" / "core.md").write_text(
        "There is no contract file, and that is the decision.\n", encoding="utf-8"
    )

    result = _repo_component(repo, physical)

    assert result["status"] == "ready"
    assert result["evidence"]["contract"]["exists"] is False
    assert result["evidence"]["contract"]["policy"]["state"] == "intentionally_absent"
    assert result["evidence"]["hub_source"]["role"] == "fallback"
    assert result["evidence"]["hub_source"]["path"] == str(
        physical / "cultura" / "mak_plataforma" / "hub.py"
    )


def test_system_status_reports_local_storage_mounts_without_remote_access(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "GoogleDrive").mkdir()
    (tmp_path / "OneDrive").mkdir()
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    import flujo.knowledge.system_status as status_module
    monkeypatch.setattr(status_module.subprocess, "run", fake_run)

    result = _mount_component(tmp_path)

    assert result["status"] == "ready"
    assert all(item["mounted"] is True for item in result["evidence"]["mounts"].values())
    assert calls == [
        ["mountpoint", "-q", str(tmp_path / "GoogleDrive")],
        ["mountpoint", "-q", str(tmp_path / "OneDrive")],
    ]


def test_storage_status_separates_historical_rate_limit_from_current_error(tmp_path: Path, monkeypatch) -> None:
    from flujo.knowledge.project_ir import LearningStore
    import flujo.knowledge.system_status as status_module

    (tmp_path / "GoogleDrive").mkdir()
    (tmp_path / "OneDrive").mkdir()
    database = tmp_path / "learning.sqlite"
    LearningStore(database).append_operational_event({
        "event_id": "storage-health:test-success",
        "archive_id": "storage",
        "proposition_id": "storage:GoogleDrive",
        "event_type": "health_probe",
        "recorded_at": "2026-09-12T02:14:26+00:00",
        "result": {"status": "succeeded", "operation": "root_list"},
    })

    def fake_run(args, **_kwargs):
        if args[0] == "mountpoint":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[0] == "systemctl":
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "ActiveState=active\nSubState=running\nExecMainStatus=0\n"
                    "ExecMainStartTimestamp=Fri 2026-09-11 22:06:57 -03\n"
                ),
                stderr="",
            )
        return SimpleNamespace(
            returncode=0,
            stdout="2026-09-09T23:32:16-0300 host rclone RATE_LIMIT_EXCEEDED\n",
            stderr="",
        )

    monkeypatch.setattr(status_module.subprocess, "run", fake_run)
    result = _mount_component(tmp_path, database)

    assert result["status"] == "ready"
    assert result["evidence"]["GoogleDrive_operational_recency"]["rate_limit_classification"] == "historical_error"


def test_flujo_adapter_resolves_physical_learning_authority(tmp_path: Path, monkeypatch) -> None:
    from flujo.web import hub

    repo = tmp_path / "flujo"
    local = repo / "data" / "mak_knowledge.db"
    physical = tmp_path / "data" / "mak_knowledge.db"
    local.parent.mkdir(parents=True)
    physical.parent.mkdir(parents=True)
    local.write_bytes(b"")
    physical.write_bytes(b"authoritative")
    monkeypatch.delenv("MAK_LEARNING_DB", raising=False)
    monkeypatch.setattr(hub, "repo_root", lambda: repo)

    assert hub.project_learning_db() == physical
