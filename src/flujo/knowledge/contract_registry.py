"""Stable contracts for Project IR formats, consumers and state gates.

This registry reuses the existing Project IR format map and router catalog. It
does not scan or copy a source tree, and it never turns a filename into a
semantic claim. Materialization is explicit; stale rows are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .project_ir import FORMAT_FAMILIES, PROJECT_STATES, stable_json
from .project_router import TOOL_CATALOG


CONTRACT_SCHEMA = "mak-project-contract-registry-v1"
REGISTRY_TABLE = "project_contracts"
AUDIT_TABLE = "project_contract_audits"
DEPENDENCIES = {
    "math_kernel": ("python3", "flujo.knowledge.math_kernel"),
    "source_learning_bridge": ("python3", "flujo.knowledge.source_learning"),
    "project_intake": ("python3", "sqlite3"),
    "research_job_router": ("python3", "tools.interpretive_garden_workflow"),
    "blend_scene_audit": ("python3", "blender_optional"),
    "knowledge_reconciliation": ("python3", "sqlite3"),
    "research_opportunity_gate": ("python3", "tools.interpretive_garden_workflow"),
    "tennis_shot_event_consumer": ("python3", "flujo.tennis.shot_events"),
    "research_source_capture": ("python3", "tools.source_pipeline"),
    "deep_learning_gate": ("python3", "flujo.knowledge.deep_learning_gate"),
    "research_simulation_consumer": ("python3", "flujo.knowledge.research_simulation"),
}


def _contract_id(kind: str, key: str) -> str:
    digest = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()
    return f"contract-{kind}-{digest[:20]}"


def _row(kind: str, key: str, payload: Mapping[str, Any], source_ref: str) -> dict[str, Any]:
    encoded = stable_json(dict(payload))
    return {
        "contract_id": _contract_id(kind, key),
        "kind": kind,
        "contract_key": key,
        "payload": dict(payload),
        "source_ref": source_ref,
        "status": "declared",
        "fingerprint": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }


def contract_snapshot() -> list[dict[str, Any]]:
    """Return deterministic contracts from active source declarations."""
    rows: list[dict[str, Any]] = []
    for suffix, family in sorted(FORMAT_FAMILIES.items()):
        rows.append(_row(
            "format", suffix,
            {
                "suffix": suffix,
                "format_family": family,
                "recognized": True,
                "unknown_policy": "abstain_if_no_consumer",
            },
            "src/flujo/knowledge/project_ir.py:FORMAT_FAMILIES",
        ))
    for contract in TOOL_CATALOG:
        rows.append(_row(
            "consumer", contract.tool_id,
            {
                "tool_id": contract.tool_id,
                "path": contract.path,
                "purpose": contract.purpose,
                "formats": list(contract.formats),
                "domains": list(contract.domains),
                "mode": contract.mode,
                "output": contract.output,
                "dependencies": list(DEPENDENCIES.get(contract.tool_id, ("python3",))),
                "selection_policy": "router_score_then_abstain_on_ambiguity",
            },
            "src/flujo/knowledge/project_router.py:TOOL_CATALOG",
        ))
    for state in PROJECT_STATES:
        rows.append(_row(
            "state", state,
            {
                "state": state,
                "execution_gate": state in {"active", "verified"},
                "requires_evidence": state in {"unknown", "review_required", "quarantined", "contradicted"},
                "retention": "retain_append_only",
            },
            "src/flujo/knowledge/project_ir.py:PROJECT_STATES",
        ))
    return rows


def validate_snapshot(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        for key in ("contract_id", "kind", "contract_key", "payload", "source_ref", "status", "fingerprint"):
            if not row.get(key):
                errors.append(f"{prefix}.{key}_missing")
        contract_id = str(row.get("contract_id") or "")
        if contract_id in seen:
            errors.append(f"{prefix}.duplicate_contract_id")
        seen.add(contract_id)
        if not isinstance(row.get("payload"), Mapping):
            errors.append(f"{prefix}.payload_not_object")
    return errors


class ContractRegistry:
    """Explicit writer and read-only summary for the shared learning DB."""

    def __init__(self, database: str | Path):
        self.database = Path(database).expanduser()

    def connect(self) -> sqlite3.Connection:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.database)

    @staticmethod
    def ensure_schema(con: sqlite3.Connection) -> None:
        con.execute(
            """CREATE TABLE IF NOT EXISTS project_contracts (
                contract_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                contract_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                updated_at TEXT NOT NULL,
                UNIQUE(kind, contract_key)
            )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_project_contracts_kind ON project_contracts(kind, status)")

    def materialize(self, rows: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        selected = list(rows if rows is not None else contract_snapshot())
        errors = validate_snapshot(selected)
        if errors:
            raise ValueError("invalid_contract_snapshot: " + ",".join(errors[:10]))
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        current_keys = {(str(row["kind"]), str(row["contract_key"])) for row in selected}
        with self.connect() as con:
            self.ensure_schema(con)
            for row in selected:
                con.execute(
                    """INSERT INTO project_contracts
                       (contract_id,kind,contract_key,payload_json,source_ref,status,fingerprint,updated_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(contract_id) DO UPDATE SET
                         kind=excluded.kind, contract_key=excluded.contract_key,
                         payload_json=excluded.payload_json, source_ref=excluded.source_ref,
                         status=excluded.status, fingerprint=excluded.fingerprint,
                         updated_at=excluded.updated_at""",
                    (
                        row["contract_id"], row["kind"], row["contract_key"],
                        stable_json(row["payload"]), row["source_ref"], row.get("status", "declared"),
                        row["fingerprint"], now,
                    ),
                )
            stale = 0
            for kind, key in con.execute("SELECT kind,contract_key FROM project_contracts WHERE status!='stale'").fetchall():
                if (kind, key) not in current_keys:
                    con.execute(
                        "UPDATE project_contracts SET status='stale',updated_at=? WHERE kind=? AND contract_key=?",
                        (now, kind, key),
                    )
                    stale += 1
            total = con.execute("SELECT COUNT(*) FROM project_contracts").fetchone()[0]
            active = con.execute("SELECT COUNT(*) FROM project_contracts WHERE status!='stale'").fetchone()[0]
        return {"schema": CONTRACT_SCHEMA, "materialized": len(selected), "active": active, "stale": stale, "total": total}

    def summary(self) -> dict[str, Any]:
        if not self.database.is_file():
            return {"available": False, "reason": "database_missing"}
        try:
            con = sqlite3.connect("file:" + str(self.database) + "?mode=ro", uri=True)
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (REGISTRY_TABLE,)).fetchone()
            if not exists:
                con.close()
                return {"available": False, "reason": "contract_registry_not_initialized"}
            counts = {row[0]: row[1] for row in con.execute("SELECT kind,COUNT(*) FROM project_contracts WHERE status!='stale' GROUP BY kind")}
            statuses = {row[0]: row[1] for row in con.execute("SELECT status,COUNT(*) FROM project_contracts GROUP BY status")}
            con.close()
            return {"available": True, "schema": CONTRACT_SCHEMA, "counts": counts, "statuses": statuses}
        except (OSError, sqlite3.Error) as exc:
            return {"available": False, "reason": type(exc).__name__}

    def read(self) -> list[dict[str, Any]]:
        """Read materialized contracts without creating a table."""
        if not self.database.is_file():
            return []
        try:
            con = sqlite3.connect("file:" + str(self.database) + "?mode=ro", uri=True)
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (REGISTRY_TABLE,)).fetchone()
            if not exists:
                con.close()
                return []
            rows = con.execute(
                "SELECT contract_id,kind,contract_key,payload_json,source_ref,status,fingerprint,updated_at "
                "FROM project_contracts ORDER BY kind,contract_key"
            ).fetchall()
            con.close()
            return [
                {
                    "contract_id": row[0], "kind": row[1], "contract_key": row[2],
                    "payload": json.loads(row[3]), "source_ref": row[4], "status": row[5],
                    "fingerprint": row[6], "updated_at": row[7],
                }
                for row in rows
            ]
        except (OSError, sqlite3.Error, json.JSONDecodeError):
            return []

    @staticmethod
    def ensure_audit_schema(con: sqlite3.Connection) -> None:
        con.execute(
            """CREATE TABLE IF NOT EXISTS project_contract_audits (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                UNIQUE(run_id, contract_id)
            )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_project_contract_audits_run ON project_contract_audits(run_id, status)")

    def record_audit(self, rows: Iterable[Mapping[str, Any]], *, run_id: str) -> dict[str, Any]:
        selected = list(rows)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self.connect() as con:
            self.ensure_audit_schema(con)
            for row in selected:
                con.execute(
                    """INSERT INTO project_contract_audits
                       (run_id,contract_id,status,evidence_json,observed_at)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(run_id,contract_id) DO UPDATE SET
                         status=excluded.status,evidence_json=excluded.evidence_json,
                         observed_at=excluded.observed_at""",
                    (run_id, row["contract_id"], row["status"], stable_json(row.get("evidence", {})), now),
                )
            counts = {row[0]: row[1] for row in con.execute(
                "SELECT status,COUNT(*) FROM project_contract_audits WHERE run_id=? GROUP BY status", (run_id,)
            )}
        return {"run_id": run_id, "recorded": len(selected), "statuses": counts}


def _source_path(root: Path, source_ref: str) -> Path:
    return root / source_ref.split(":", 1)[0]


def _dependency_check(name: str, root: str | Path | None = None) -> dict[str, Any]:
    if name == "python3":
        return {"name": name, "available": bool(shutil.which("python3")), "required": True}
    if name == "sqlite3":
        return {"name": name, "available": importlib.util.find_spec("sqlite3") is not None, "required": True}
    if name == "blender_optional":
        from .runtime_tools import resolve_blender
        path = resolve_blender(root)
        return {
            "name": name,
            "available": path is not None,
            "required": False,
            **({"path": str(path)} if path else {}),
        }
    if name.endswith("_optional"):
        binary = name.removesuffix("_optional")
        return {"name": name, "available": bool(shutil.which(binary)), "required": False}
    return {"name": name, "available": importlib.util.find_spec(name) is not None, "required": True}


def audit_contracts(rows: Iterable[Mapping[str, Any]], root: str | Path) -> list[dict[str, Any]]:
    """Check source paths/dependencies; no import side effects or execution."""
    base = Path(root).expanduser().resolve()
    results = []
    for row in rows:
        source = _source_path(base, str(row.get("source_ref") or ""))
        evidence: dict[str, Any] = {
            "source_ref": row.get("source_ref", ""),
            "source_exists": source.is_file(),
        }
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        dependencies = []
        if row.get("kind") == "consumer":
            path = base / str(payload.get("path") or "")
            evidence["consumer_path"] = str(payload.get("path") or "")
            evidence["consumer_exists"] = path.is_file()
            dependencies = [_dependency_check(str(item), base) for item in payload.get("dependencies", [])]
            evidence["dependencies"] = dependencies
        required_missing = not evidence["source_exists"]
        if row.get("kind") == "consumer":
            required_missing = required_missing or not evidence["consumer_exists"]
        required_missing = required_missing or any(not item["available"] and item["required"] for item in dependencies)
        optional_missing = any(not item["available"] and not item["required"] for item in dependencies)
        status = "unavailable" if required_missing else "needs_evidence" if optional_missing else "verified"
        results.append({"contract_id": row.get("contract_id"), "kind": row.get("kind"), "contract_key": row.get("contract_key"), "status": status, "evidence": evidence})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("command", choices=("snapshot", "materialize", "summary", "audit"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="MAK root used by audit")
    parser.add_argument("--record", action="store_true", help="persist an audit run; default is read-only")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    registry = ContractRegistry(args.db)
    if args.command == "snapshot":
        print(json.dumps({"schema": CONTRACT_SCHEMA, "contracts": contract_snapshot()}, ensure_ascii=False))
    elif args.command == "materialize":
        print(json.dumps(registry.materialize(), ensure_ascii=False))
    elif args.command == "summary":
        print(json.dumps(registry.summary(), ensure_ascii=False))
    else:
        rows = registry.read()
        audited = audit_contracts(rows, args.root)
        result: dict[str, Any] = {
            "schema": "mak-project-contract-audit-v1",
            "read_only": not args.record,
            "contracts": len(audited),
            "statuses": {status: sum(1 for row in audited if row["status"] == status) for status in ("verified", "needs_evidence", "unavailable")},
            "results": audited,
        }
        if args.record:
            run_id = args.run_id or "audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            result["recording"] = registry.record_audit(audited, run_id=run_id)
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
