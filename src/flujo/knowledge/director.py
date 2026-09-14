"""Safe, checkpointed director for MAK Learn v2.

The director coordinates a declared Project Router decision and a bounded
read-only probe.  It never executes an arbitrary command: only tools declared
by the router catalog with ``mode == read_only`` can enter the run.  Every
state transition is persisted in ``mak_run_events`` and the final observation
is recorded as the existing conservative learning episode.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Mapping

from .episode_runner import probe_declared_consumer, record_probe
from .project_ir import LearningStore, ProjectIRError
from .project_router import ROUTER_SCHEMA, TOOL_CATALOG


DIRECTOR_SCHEMA = "mak-director-v1"
DIRECTOR_STATES = ("proposed", "running", "observed", "validated", "recorded", "rejected")
READ_ONLY_TOOL_IDS = frozenset(
    contract.tool_id for contract in TOOL_CATALOG if contract.mode == "read_only"
)
OBSERVATION_STATUSES = frozenset({"succeeded", "failed", "abstained", "needs_evidence"})
VALIDATION_STATUSES = frozenset({"ok", "passed", "verified", "ready"})
RECOVERY_ACTIONS = {
    "proposed": "continue_start",
    "running": "reprobe_required",
    "observed": "continue_validate",
    "validated": "continue_record_if_passed",
    "recorded": "terminal",
    "rejected": "terminal",
}


class DirectorError(ProjectIRError):
    """A proposed director transition is invalid or unsafe."""


class MakDirector:
    """Coordinate one bounded run and persist every checkpoint."""

    def __init__(
        self,
        store: LearningStore,
        *,
        repo_root: str | Path,
        source_snapshot_hash: str,
        code_commit: str,
        tool_versions: Mapping[str, Any],
    ) -> None:
        if not source_snapshot_hash:
            raise DirectorError("director_missing_source_snapshot_hash")
        if not code_commit:
            raise DirectorError("director_missing_code_commit")
        if not isinstance(tool_versions, Mapping):
            raise DirectorError("director_tool_versions_not_mapping")
        self.store = store
        self.repo_root = Path(repo_root).expanduser()
        self.source_snapshot_hash = str(source_snapshot_hash)
        self.code_commit = str(code_commit)
        self.tool_versions = dict(tool_versions)

    @staticmethod
    def _project_id(project: Mapping[str, Any]) -> str:
        project_id = str(project.get("project_id") or "").strip()
        if not project_id:
            raise DirectorError("director_missing_project_id")
        return project_id

    @staticmethod
    def _selected_tool(decision: Mapping[str, Any]) -> str:
        if decision.get("schema") != ROUTER_SCHEMA:
            raise DirectorError("director_bad_router_schema")
        if decision.get("decision") == "abstain":
            return ""
        if decision.get("decision") != "select":
            raise DirectorError("director_bad_router_decision")
        selected = decision.get("selected")
        if not isinstance(selected, Mapping):
            raise DirectorError("director_selected_tool_missing")
        tool_id = str(selected.get("tool_id") or "")
        if tool_id not in READ_ONLY_TOOL_IDS:
            raise DirectorError("director_tool_not_allowlisted")
        if str(selected.get("mode") or "") != "read_only":
            raise DirectorError("director_tool_not_read_only")
        return tool_id

    def _event(
        self, run: Mapping[str, Any], *, event_type: str, state: str,
        payload: Mapping[str, Any], episode_id: str | None = None,
    ) -> str:
        if state not in DIRECTOR_STATES:
            raise DirectorError(f"director_bad_state: {state}")
        return self.store.append_run_event(
            run_id=str(run["run_id"]),
            event_id=None,
            project_id=str(run["project_id"]),
            episode_id=episode_id,
            parent_event_id=str(run["event_id"]) if run.get("event_id") else None,
            event_type=event_type,
            state=state,
            payload=dict(payload),
            source_snapshot_hash=self.source_snapshot_hash,
            code_commit=self.code_commit,
            tool_versions=self.tool_versions,
        )

    @staticmethod
    def _advance(run: Mapping[str, Any], event_id: str, state: str, **extra: Any) -> dict[str, Any]:
        return {**dict(run), "state": state, "event_id": event_id, **extra}

    @staticmethod
    def _require_state(run: Mapping[str, Any], expected: str) -> None:
        if str(run.get("state") or "") != expected:
            raise DirectorError(
                f"director_invalid_transition: {run.get('state')}->{expected}"
            )

    def propose(
        self, project: Mapping[str, Any], decision: Mapping[str, Any], *,
        run_id: str | None = None, episode_id: str | None = None,
    ) -> dict[str, Any]:
        project_id = self._project_id(project)
        tool_id = self._selected_tool(decision)
        run_id = run_id or "run_" + uuid.uuid4().hex
        run = {
            "schema": DIRECTOR_SCHEMA,
            "run_id": run_id,
            "project_id": project_id,
            "episode_id": episode_id,
            "tool_id": tool_id,
            "decision": dict(decision),
            "state": "proposed",
            "event_id": None,
        }
        event_id = self._event(
            run,
            event_type="director.propose",
            state="proposed",
            payload={
                "decision": str(decision.get("decision") or ""),
                "reason": str(decision.get("reason") or ""),
                "tool_id": tool_id,
                "router_decision": dict(decision),
            },
        )
        return self._advance(run, event_id, "proposed")

    def start(self, run: Mapping[str, Any]) -> dict[str, Any]:
        self._require_state(run, "proposed")
        event_id = self._event(
            run, event_type="director.start", state="running",
            payload={"tool_id": str(run.get("tool_id") or ""), "execution": "bounded_probe"},
        )
        return self._advance(run, event_id, "running")

    def observe(self, run: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
        self._require_state(run, "running")
        if not isinstance(probe, Mapping):
            raise DirectorError("director_probe_not_mapping")
        status = str(probe.get("status") or "").casefold()
        if status not in OBSERVATION_STATUSES:
            raise DirectorError("director_probe_bad_status")
        reported_tool = str(probe.get("tool_id") or "")
        if run.get("tool_id") and reported_tool and reported_tool != run["tool_id"]:
            raise DirectorError("director_probe_tool_mismatch")
        validation = probe.get("validation")
        if validation is not None and not isinstance(validation, Mapping):
            raise DirectorError("director_probe_validation_not_mapping")
        event_id = self._event(
            run, event_type="director.observe", state="observed",
            payload={"status": status, "tool_id": reported_tool, "probe": dict(probe)},
        )
        return self._advance(run, event_id, "observed", probe=dict(probe))

    def validate(
        self, run: Mapping[str, Any], *,
        replay_evaluation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_state(run, "observed")
        probe = run.get("probe")
        if not isinstance(probe, Mapping):
            raise DirectorError("director_probe_missing")
        validation = probe.get("validation")
        validation = dict(validation) if isinstance(validation, Mapping) else {}
        validation_status = str(validation.get("status") or "").casefold()
        passed = validation_status in VALIDATION_STATUSES
        replay_gate = "not_provided"
        if replay_evaluation is not None:
            if not isinstance(replay_evaluation, Mapping):
                raise DirectorError("director_replay_evaluation_not_mapping")
            replay_gate = str(replay_evaluation.get("status") or "").casefold()
            if replay_gate not in {"passed", "failed", "abstained"}:
                raise DirectorError("director_replay_evaluation_bad_status")
            passed = passed and replay_gate == "passed"
        event_id = self._event(
            run, event_type="director.validate", state="validated",
            payload={
                "validation": validation,
                "passed": passed,
                "replay_gate": replay_gate,
                "replay_evaluation": dict(replay_evaluation or {}),
            },
        )
        return self._advance(
            run, event_id, "validated", validation_passed=passed,
            replay_gate=replay_gate,
            replay_evaluation=dict(replay_evaluation or {}),
        )

    def record(
        self, run: Mapping[str, Any], project: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._require_state(run, "validated")
        probe = run.get("probe")
        validation = probe.get("validation") if isinstance(probe, Mapping) else {}
        validation_status = str(validation.get("status") or "").casefold() if isinstance(validation, Mapping) else ""
        if validation_status in {"failed", "rejected", "invalid"}:
            raise DirectorError("director_validation_failed")
        decision = run.get("decision")
        if not isinstance(decision, Mapping) or not isinstance(probe, Mapping):
            raise DirectorError("director_record_inputs_missing")
        episode_id = record_probe(
            self.store, project, decision, probe,
            episode_id=str(run.get("episode_id") or "") or None,
            source_snapshot_hash=self.source_snapshot_hash,
            code_commit=self.code_commit,
            tool_versions=self.tool_versions,
        )
        event_id = self._event(
            run, event_type="director.record", state="recorded",
            episode_id=episode_id,
            payload={
                "episode_id": episode_id,
                "probe_status": str(probe.get("status") or ""),
                "validation_passed": bool(run.get("validation_passed")),
                "replay_gate": str(run.get("replay_gate") or "not_provided"),
            },
        )
        return self._advance(run, event_id, "recorded", episode_id=episode_id)

    def run_read_only_probe(
        self, project: Mapping[str, Any], decision: Mapping[str, Any], *,
        run_id: str | None = None, episode_id: str | None = None,
        replay_evaluation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the safe orchestration path; the probe itself never spawns a process."""
        run = self.propose(project, decision, run_id=run_id, episode_id=episode_id)
        run = self.start(run)
        probe = probe_declared_consumer(project, decision, repo_root=self.repo_root)
        run = self.observe(run, probe)
        run = self.validate(run, replay_evaluation=replay_evaluation)
        run = self.record(run, project)
        return {"schema": DIRECTOR_SCHEMA, "run": run, "events": self.checkpoint(run["run_id"])}

    def checkpoint(self, run_id: str) -> dict[str, Any]:
        events = self.store.run_events(run_id)
        if not events:
            raise DirectorError("director_checkpoint_missing")
        latest = events[-1]
        return {
            "schema": DIRECTOR_SCHEMA,
            "run_id": run_id,
            "state": latest["state"],
            "event_id": latest["event_id"],
            "event_count": len(events),
            "resumable": latest["state"] not in {"recorded", "rejected"},
            "events": events,
        }

    def recovery_plan(self, run_id: str) -> dict[str, Any]:
        """Return a non-mutating recovery recommendation for an interrupted run."""
        checkpoint = self.checkpoint(run_id)
        state = str(checkpoint["state"])
        action = RECOVERY_ACTIONS.get(state, "quarantine_unknown_state")
        safe_to_record = False
        if state == "validated":
            events = checkpoint["events"]
            payload = events[-1].get("payload") if isinstance(events[-1].get("payload"), Mapping) else {}
            safe_to_record = bool(payload.get("passed"))
            if not safe_to_record:
                validation = payload.get("validation") if isinstance(payload.get("validation"), Mapping) else {}
                validation_status = str(validation.get("status") or "").casefold()
                action = (
                    "quarantine_failed_validation"
                    if validation_status in {"failed", "rejected", "invalid"}
                    else "quarantine_pending_validation"
                )
        return {
            "schema": DIRECTOR_SCHEMA,
            "run_id": run_id,
            "state": state,
            "action": action,
            "safe_to_record": safe_to_record,
            "mutated": False,
            "checkpoint_event_id": checkpoint["event_id"],
        }

    def resume(self, run_id: str) -> dict[str, Any]:
        """Reconstruct the latest in-memory run view from durable checkpoints."""
        checkpoint = self.checkpoint(run_id)
        events = checkpoint["events"]
        first = events[0]
        proposal = first.get("payload") if isinstance(first.get("payload"), Mapping) else {}
        decision = proposal.get("router_decision")
        if not isinstance(decision, Mapping):
            raise DirectorError("director_checkpoint_missing_decision")
        latest = events[-1]
        run: dict[str, Any] = {
            "schema": DIRECTOR_SCHEMA,
            "run_id": run_id,
            "project_id": first["project_id"],
            "episode_id": latest.get("episode_id"),
            "tool_id": str(proposal.get("tool_id") or ""),
            "decision": dict(decision),
            "state": latest["state"],
            "event_id": latest["event_id"],
        }
        for event in events:
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if event["state"] == "observed":
                run["probe"] = dict(payload.get("probe") or {})
            if event["state"] == "validated":
                run["validation_passed"] = bool(payload.get("passed"))
                run["replay_gate"] = str(payload.get("replay_gate") or "not_provided")
                run["replay_evaluation"] = dict(payload.get("replay_evaluation") or {})
            if event["state"] == "recorded":
                run["episode_id"] = payload.get("episode_id")
        return {"schema": DIRECTOR_SCHEMA, "checkpoint": checkpoint, "run": run}
