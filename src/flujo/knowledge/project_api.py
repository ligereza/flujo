"""Read-only API helpers shared by the local Hub surfaces.

Both the canonical ``flujo serve`` Hub and the legacy 8900 MAK projection use
this module.  It intentionally never calls ``ensure_schema``: a GET or route
preview must not silently migrate the real knowledge database.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .project_ir import validate_project_ir
from .project_router import route_project
from .episode_runner import probe_declared_consumer, record_probe
from .learning_policy import learning_summary as learning_policy_summary


# Reuse the adapter's own accepted-outcome set instead of writing a second
# list: two copies of "what counts as done" is how the ledger and the recorder
# would drift apart.
from .learning_policy import VERIFIED_OUTCOME_STATUSES as VERIFIED_EPISODE_STATUSES


def _open_episode_rows(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Return open episode rows after applying the per-project resolution gate.

    Episodes are immutable history. A project that recorded ``needs_evidence``
    and later recorded a verified execution has answered that item, so counting
    the old row as pending manufactures permanent urgency. Verified, succeeded
    and accepted rows are never "open" by themselves; every other state stays
    open until a later verified episode exists for the same project.

    Read-only: this only reads ``project_episodes`` in row order.
    """
    latest_verified: dict[str, int] = {}
    rows: list[tuple[int, str, str, str]] = []
    columns = {row[1] for row in con.execute("PRAGMA table_info(project_episodes)")}
    phase_expression = "phase" if "phase" in columns else "''"
    for rowid, project_id, phase, status in con.execute(
        f"SELECT rowid, project_id, {phase_expression}, status "
        "FROM project_episodes ORDER BY rowid"
    ):
        state = str(status or "").casefold()
        project = str(project_id or "")
        rows.append((int(rowid), project, str(phase or "unknown"), state))
        if state in VERIFIED_EPISODE_STATUSES:
            latest_verified[project] = int(rowid)
    # A later episode that explicitly names an earlier episode is its
    # successor in the same append-only lineage.  The parent remains useful
    # history, but it is no longer a second current uncertainty.  Older
    # fixtures may not have the parent column, hence the bounded compatibility
    # path above and the separate query below.
    superseded: set[int] = set()
    if "parent_episode_id" in columns and "episode_id" in columns:
        children = con.execute(
            "SELECT parent_episode_id FROM project_episodes "
            "WHERE parent_episode_id IS NOT NULL AND parent_episode_id != ''"
        )
        parent_ids = {str(row[0]) for row in children}
        if parent_ids:
            for rowid, episode_id, project in con.execute(
                "SELECT rowid, episode_id, project_id FROM project_episodes"
            ):
                if str(episode_id) in parent_ids:
                    superseded.add(int(rowid))

    open_rows: list[tuple[str, str, str]] = []
    for rowid, project, phase, state in rows:
        if state in VERIFIED_EPISODE_STATUSES:
            continue
        if rowid in superseded:
            continue
        if latest_verified.get(project, -1) > rowid:
            continue  # a later verified episode answered this one
        open_rows.append((project, phase, state))
    return open_rows


def _open_episode_states(con: sqlite3.Connection) -> dict[str, int]:
    """Count only the episode states a project has not resolved yet."""
    counts: dict[str, int] = {}
    for _project, _phase, state in _open_episode_rows(con):
        counts[state] = counts.get(state, 0) + 1
    return counts


def _review_queue_summary(
    con: sqlite3.Connection,
    open_episode_rows: list[tuple[str, str, str]],
) -> dict[str, Any]:
    """Expose bounded review composition without creating a second queue."""
    by_source_kind: dict[str, int] = {}
    project_items: list[dict[str, Any]] = []
    total_projects = 0
    for project_id, title, encoded in con.execute(
        "SELECT project_id,title,ir_json FROM project_records "
        "WHERE state='review_required' ORDER BY project_id"
    ):
        total_projects += 1
        try:
            record = json.loads(encoded)
        except (TypeError, json.JSONDecodeError):
            record = {}
        source = record.get("source", {}) if isinstance(record, dict) else {}
        kind = str(source.get("kind") or "unknown") if isinstance(source, dict) else "unknown"
        by_source_kind[kind] = by_source_kind.get(kind, 0) + 1
        evidence = record.get("evidence", []) if isinstance(record, dict) else []
        evidence_kinds = sorted({
            str(item.get("kind")) for item in evidence
            if isinstance(item, dict) and item.get("kind")
        })
        unknowns = record.get("unknowns", []) if isinstance(record, dict) else []
        safe_unknowns = [str(item)[:300] for item in unknowns
                         if isinstance(item, (str, int, float))]
        project_items.append({
            "project_id": str(project_id),
            "title": str(title),
            "source_kind": kind,
            "source_root_observed_present": (
                source.get("root_exists") if isinstance(source, dict) else None
            ),
            "unknown_count": len(record.get("unknowns", [])) if isinstance(record, dict) and isinstance(record.get("unknowns", []), list) else 0,
            "unknowns": safe_unknowns,
            "evidence_kinds": evidence_kinds,
            "next_action": str(record.get("next_action") or "") if isinstance(record, dict) else "",
        })

    by_phase_status: dict[str, dict[str, int]] = {}
    for _project, phase, status in open_episode_rows:
        phase_key = str(phase or "unknown")
        status_key = str(status or "unknown")
        phase_counts = by_phase_status.setdefault(phase_key, {})
        phase_counts[status_key] = phase_counts.get(status_key, 0) + 1
    return {
        "projects": {
            "total": total_projects,
            "by_source_kind": dict(sorted(by_source_kind.items())),
            "items": sorted(project_items, key=lambda item: (
                item["source_kind"], item["project_id"]
            )),
        },
        "episodes": {
            "open_total": len(open_episode_rows),
            "by_phase_status": {
                phase: dict(sorted(statuses.items()))
                for phase, statuses in sorted(by_phase_status.items())
            },
        },
    }


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)


def learning_summary(database: str | Path) -> dict[str, Any]:
    path = Path(database).expanduser()
    if not path.is_file():
        return {"available": False, "reason": "database_missing", "database": path.name}
    try:
        con = _read_only_connection(path)
        tables = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
            "('project_records','project_episodes','semantic_rules','project_contracts')"
        )}
        if "project_records" not in tables:
            con.close()
            return {"available": False, "reason": "learning_schema_not_initialized", "database": path.name}
        result: dict[str, Any] = {"available": True, "database": path.name}
        result["policy"] = learning_policy_summary(path)
        result["projects"] = {row[0]: row[1] for row in con.execute("SELECT state,COUNT(*) FROM project_records GROUP BY state")}
        result["episodes"] = {row[0]: row[1] for row in con.execute("SELECT status,COUNT(*) FROM project_episodes GROUP BY status")}
        # The histogram above counts every episode ever recorded, and episodes
        # are append-only. Using it for the attention list makes an item that
        # can never be cleared by doing the work: record the verified execution
        # a `needs_evidence` episode asks for and the old row still counts, so
        # the operator can no longer tell "there is work" from "the work was
        # done". Open state is therefore computed per project: a non-verified
        # episode stays open only while that project has no later verified one,
        # which is exactly what its own next_action describes ("attach
        # verifiable evidence, then run the validator again").
        open_episode_rows = _open_episode_rows(con)
        result["episodes_open"] = {
            status: sum(1 for _project, _phase, row_status in open_episode_rows
                        if row_status == status)
            for status in sorted({row[2] for row in open_episode_rows})
        }
        result["review_queue"] = _review_queue_summary(con, open_episode_rows)
        result["rules"] = {row[0]: row[1] for row in con.execute("SELECT status,COUNT(*) FROM semantic_rules GROUP BY status")} if "semantic_rules" in tables else {}
        if "project_contracts" in tables:
            result["contracts"] = {
                "available": True,
                "counts": {
                    row[0]: row[1] for row in con.execute(
                        "SELECT kind,COUNT(*) FROM project_contracts WHERE status!='stale' GROUP BY kind"
                    )
                },
                "statuses": {
                    row[0]: row[1] for row in con.execute(
                        "SELECT status,COUNT(*) FROM project_contracts GROUP BY status"
                    )
                },
            }
        else:
            result["contracts"] = {"available": False, "reason": "contract_registry_not_initialized"}
        if "project_contract_audits" in {
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='project_contract_audits'"
            )
        }:
            latest_run = con.execute(
                "SELECT run_id FROM project_contract_audits GROUP BY run_id "
                "ORDER BY MAX(observed_at) DESC, run_id DESC LIMIT 1"
            ).fetchone()
            run_id = latest_run[0] if latest_run else None
            attention = []
            if run_id:
                for contract_key, status, evidence_json in con.execute(
                    "SELECT contract_id,status,evidence_json FROM project_contract_audits "
                    "WHERE run_id=? AND status!='verified' ORDER BY contract_id", (run_id,)
                ):
                    try:
                        evidence = json.loads(evidence_json)
                    except json.JSONDecodeError:
                        evidence = {}
                    dependencies = evidence.get("dependencies", []) if isinstance(evidence, dict) else []
                    missing = [item.get("name") for item in dependencies if isinstance(item, dict) and not item.get("available")]
                    attention.append({"contract_id": contract_key, "status": status, "missing": missing})
            result["audits"] = {
                "available": bool(run_id),
                "latest_run": run_id,
                "statuses": {
                    row[0]: row[1] for row in con.execute(
                        "SELECT status,COUNT(*) FROM project_contract_audits WHERE run_id=? GROUP BY status",
                        (run_id,),
                    )
                } if run_id else {},
                "attention": attention,
            }
        else:
            result["audits"] = {"available": False, "reason": "contract_audit_not_initialized"}
        result["latest_abstain"] = None
        if "project_episodes" in tables:
            row = con.execute(
                "SELECT episode_id,project_id,status,phase,objective,started_at,finished_at "
                "FROM project_episodes WHERE status='abstained' "
                "ORDER BY COALESCE(finished_at,started_at,episode_id) DESC LIMIT 1"
            ).fetchone()
            if row:
                result["latest_abstain"] = {
                    "episode_id": row[0],
                    "project_id": row[1],
                    "status": row[2],
                    "phase": row[3],
                    "objective": row[4],
                    "started_at": row[5],
                    "finished_at": row[6],
                }
        con.close()
        return result
    except (OSError, sqlite3.Error) as exc:
        return {"available": False, "reason": type(exc).__name__, "database": path.name}


def operational_status(database: str | Path, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return the bounded machine-readable status of the MAK knowledge loop.

    This is deliberately read-only.  ``learning_summary`` remains the
    compatibility payload for existing consumers; this normalized envelope is
    the single status surface for the CLI and the Hub.  It reports evidence
    gaps and safe abstentions as actionable state rather than pretending that
    either one is a successful prediction.
    """
    path = Path(database).expanduser()
    summary = learning_summary(path)
    attention: list[dict[str, Any]] = []

    def add_item(
        item_id: str,
        kind: str,
        status: str,
        severity: str,
        reason: str,
        next_action: str,
        *,
        ref: str | None = None,
    ) -> None:
        attention.append({
            "id": item_id,
            "kind": kind,
            "status": status,
            "severity": severity,
            "reason": reason,
            "next_action": next_action,
            **({"ref": ref} if ref else {}),
        })

    if not summary.get("available"):
        add_item(
            "learning_ledger",
            "ledger",
            "unavailable",
            "attention",
            str(summary.get("reason", "database_missing")),
            "initialize or configure the local MAK knowledge database before recording results",
            ref=str(path),
        )
    else:
        for state, count in sorted((summary.get("projects") or {}).items()):
            if state == "blocked":
                add_item(
                    f"projects:{state}", "projects", state, "blocked",
                    f"{count} project(s) are blocked",
                    "inspect the project evidence and unblock only after a bounded validation",
                )
            elif state == "review_required":
                queue = summary.get("review_queue") or {}
                project_queue = queue.get("projects") if isinstance(queue, dict) else {}
                source_counts = project_queue.get("by_source_kind", {}) if isinstance(project_queue, dict) else {}
                source_detail = ", ".join(
                    f"{kind}={amount}" for kind, amount in sorted(source_counts.items())
                )
                open_episodes = (queue.get("episodes", {}).get("open_total")
                                 if isinstance(queue, dict) and isinstance(queue.get("episodes"), dict)
                                 else None)
                reason = f"{count} project(s) require review"
                if source_detail:
                    reason += f"; source kinds: {source_detail}"
                if open_episodes is not None:
                    reason += f"; open episodes: {open_episodes}"
                add_item(
                    f"projects:{state}", "projects", state, "attention",
                    reason,
                    "review evidence and consumer before allowing a project transition",
                )

        # Historical counts stay in `episodes` as evidence; the actionable list
        # reads `episodes_open` so a resolved episode stops being urgent.
        open_states = summary.get("episodes_open")
        if not isinstance(open_states, dict):
            open_states = summary.get("episodes") or {}
        for status, count in sorted(open_states.items()):
            if status in {"failed", "error"}:
                add_item(
                    f"episodes:{status}", "episodes", status, "blocked",
                    f"{count} episode(s) failed",
                    "inspect the recorded failure and rerun only the bounded step",
                )
            elif status == "needs_evidence":
                add_item(
                    f"episodes:{status}", "episodes", status, "attention",
                    f"{count} episode(s) need evidence",
                    "attach verifiable evidence, then run the validator again",
                )
            elif status == "abstained":
                add_item(
                    f"episodes:{status}", "episodes", status, "info",
                    f"{count} episode(s) abstained safely",
                    "keep the abstention until the missing evidence or an independent test exists",
                )
            elif status not in {"verified", "succeeded", "completed"}:
                add_item(
                    f"episodes:{status}", "episodes", status, "attention",
                    f"{count} episode(s) are not terminal",
                    "inspect the episode before starting another attempt",
                )

        policy = summary.get("policy") or {}
        if policy.get("status") == "abstain":
            reason = str(policy.get("reason", "policy_abstain"))
            add_item(
                "learning_policy",
                "policy",
                "abstain",
                "info",
                reason,
                "collect an independent verified project before promoting a general policy",
            )

        for audit in (summary.get("audits") or {}).get("attention", []):
            contract_id = str(audit.get("contract_id", "contract"))
            audit_status = str(audit.get("status", "unknown"))
            severity = "blocked" if audit_status in {"failed", "error"} else "attention"
            missing = audit.get("missing") or []
            reason = f"contract audit is {audit_status}"
            if missing:
                reason += f"; missing: {', '.join(map(str, missing))}"
            add_item(
                f"contract:{contract_id}",
                "contract_audit",
                audit_status,
                severity,
                reason,
                "restore or explicitly quarantine the missing dependency, then rerun the contract audit",
                ref=contract_id,
            )

    severities = {item["severity"] for item in attention}
    if not summary.get("available"):
        overall = "unknown"
    elif "blocked" in severities:
        overall = "blocked"
    elif "attention" in severities:
        overall = "attention"
    elif summary.get("available"):
        overall = "ready"
    else:
        overall = "unknown"

    next_actions: list[str] = []
    for item in attention:
        action = item["next_action"]
        if action not in next_actions:
            next_actions.append(action)

    return {
        "schema": "mak-operational-status-v1",
        "status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(path),
        "read_only": True,
        "repo_root": str(Path(repo_root).expanduser()) if repo_root is not None else None,
        "learning": summary,
        "attention": attention,
        "counts": {
            "attention": sum(1 for item in attention if item["severity"] == "attention"),
            "blocked": sum(1 for item in attention if item["severity"] == "blocked"),
            "info": sum(1 for item in attention if item["severity"] == "info"),
        },
        "next_actions": next_actions,
    }


def promoted_rules(database: str | Path) -> list[dict[str, Any]]:
    path = Path(database).expanduser()
    if not path.is_file():
        return []
    try:
        con = _read_only_connection(path)
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='semantic_rules'").fetchone()
        if not exists:
            con.close()
            return []
        rows = con.execute("SELECT rule_id,trigger_json,action_json,status FROM semantic_rules WHERE status='promoted'").fetchall()
        con.close()
        return [{"rule_id": row[0], "trigger_json": row[1], "action_json": row[2], "status": row[3]} for row in rows]
    except (OSError, sqlite3.Error):
        return []


def route_payload(body: Mapping[str, Any], database: str | Path) -> tuple[dict[str, Any], int]:
    project = body.get("project") if isinstance(body, Mapping) else None
    if not isinstance(project, Mapping):
        project = body if isinstance(body, Mapping) else None
    if not isinstance(project, Mapping):
        return {"ok": False, "error": "project debe ser un objeto"}, 400
    errors = validate_project_ir(project)
    if errors:
        return {"ok": False, "error": "invalid_project_ir", "details": errors[:20]}, 400
    decision = route_project(project, rules=promoted_rules(database))
    return {"ok": True, "decision": decision, "learning": learning_summary(database)}, 200


def probe_payload(
    body: Mapping[str, Any], database: str | Path, *, repo_root: str | Path,
    record: bool = False, episode_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Route plus bounded probe; persistence is explicit and existing-project only."""
    routed, status = route_payload(body, database)
    if status != 200:
        return routed, status
    project = body.get("project") if isinstance(body, Mapping) else None
    if not isinstance(project, Mapping):
        project = body
    decision = routed["decision"]
    probe = probe_declared_consumer(project, decision, repo_root=repo_root)
    result: dict[str, Any] = {**routed, "probe": probe, "recorded": False, "episode_id": None}
    if record:
        import sqlite3
        from .project_ir import LearningStore
        with sqlite3.connect("file:" + str(Path(database).expanduser()) + "?mode=ro", uri=True) as con:
            exists = con.execute("SELECT 1 FROM project_records WHERE project_id=?", (project.get("project_id"),)).fetchone()
        if not exists:
            return {"ok": False, "error": "project_must_be_persisted_before_recording"}, 409
        try:
            result["episode_id"] = record_probe(
                LearningStore(database), project, decision, probe, episode_id=episode_id,
            )
        except (OSError, ValueError, sqlite3.Error) as exc:
            return {"ok": False, "error": str(exc)[:300]}, 409
        result["recorded"] = True
    return result, 200
