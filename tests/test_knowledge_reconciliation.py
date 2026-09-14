from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
import flujo.knowledge.reconciliation as reconciliation

from flujo.knowledge.reconciliation import (
    NAMESPACES,
    ReconciliationInputError,
    build_reconciliation_plan,
    inspect_sqlite,
    write_plan,
)


def _make_db(path: Path, *, candidate: bool) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
        """
    )
    connection.execute(
        "CREATE TABLE reactivos (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL%s)"
        % (", evidence TEXT" if candidate else "")
    )
    connection.executemany("INSERT INTO meta VALUES (?, ?)", [("owner", "RD")])
    if candidate:
        connection.executemany(
            "INSERT INTO reactivos VALUES (?, ?, ?)",
            [(1, "Marquis", "source-a"), (2, "Mecke", "source-b")],
        )
    else:
        connection.executemany(
            "INSERT INTO reactivos VALUES (?, ?)", [(1, "Marquis"), (2, "Modified")]
        )
    if not candidate:
        connection.execute("CREATE TABLE legacy_only (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO legacy_only VALUES (1, 'preserved')")
    if candidate:
        connection.execute("CREATE TABLE testeo_fuentes (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
        connection.execute("INSERT INTO testeo_fuentes VALUES ('source-1', 'abc')")
    connection.commit()
    connection.close()


def test_plan_is_deterministic_and_preserves_source_hashes(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    _make_db(candidate, candidate=True)
    _make_db(legacy, candidate=False)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (candidate, legacy)}

    first = build_reconciliation_plan(candidate, legacy)
    second = build_reconciliation_plan(candidate, legacy)
    assert first == second
    assert first["target"]["namespaces"]["portfolio"]["status"] == "NOT_CONFIGURED"
    assert first["migration"]["writes_performed"] is False
    assert first["comparison"]["tables"]["reactivos"]["status"] == "conflict"
    assert first["comparison"]["tables"]["reactivos"]["conflicts"][0]["key"] == [2]
    assert first["comparison"]["tables"]["testeo_fuentes"]["status"] == "candidate_only"
    assert first["comparison"]["tables"]["legacy_only"]["status"] == "legacy_only"
    serialized = json.dumps(first, ensure_ascii=True)
    assert "keyed_rows" not in serialized
    assert "row_digest_counts" not in serialized
    assert "_private_rows" not in serialized
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (candidate, legacy)} == before


def test_schema_delta_is_visible_for_changed_shared_table(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    _make_db(candidate, candidate=True)
    _make_db(legacy, candidate=False)
    plan = build_reconciliation_plan(candidate, legacy)
    table = plan["comparison"]["tables"]["reactivos"]
    assert table["schema_delta"] == {
        "candidate_only_columns": ["evidence"],
        "legacy_only_columns": [],
        "changed_common_columns": [],
        "candidate_only_foreign_keys": [],
        "legacy_only_foreign_keys": [],
        "candidate_only_indexes": [],
        "legacy_only_indexes": [],
        "changed_primary_key": False,
        "changed_table_sql": True,
    }


def test_plan_has_all_engine_neutral_namespaces_and_provenance_contract(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    _make_db(candidate, candidate=True)
    _make_db(legacy, candidate=False)
    plan = build_reconciliation_plan(candidate, legacy)
    assert tuple(plan["target"]["namespaces"]) == NAMESPACES
    assert plan["target"]["assertion_required_fields"] == [
        "source_or_evidence",
        "producer",
        "owner",
        "confidence_or_status",
        "visibility",
        "timestamp_or_version",
    ]
    assert plan["inputs"]["candidate"]["role"] == "CANDIDATE_AUTHORITY"
    assert plan["inputs"]["legacy"]["role"] == "LEGACY_PROJECTION"
    assert all(item["read_only"] for item in plan["inputs"].values())


def test_engine_neutral_contract_declares_target_namespaces():
    contract = json.loads(
        (Path(__file__).parents[1] / "schemas" / "knowledge" / "unified_knowledge.schema.json")
        .read_text(encoding="utf-8")
    )
    assert contract["$id"] == "mak-unified-knowledge-db-target-v1"
    assert [item["const"] for item in contract["properties"]["namespaces"]["prefixItems"]] == list(NAMESPACES)
    assert contract["properties"]["portfolio"]["properties"]["status"]["const"] == "NOT_CONFIGURED"


def test_write_plan_is_canonical(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    _make_db(candidate, candidate=True)
    _make_db(legacy, candidate=False)
    plan = build_reconciliation_plan(candidate, legacy)
    output = tmp_path / "plan.json"
    write_plan(plan, output)
    first_bytes = output.read_bytes()
    write_plan(build_reconciliation_plan(candidate, legacy), output)
    assert output.read_bytes() == first_bytes
    assert json.loads(first_bytes)["schema"] == "mak-unified-knowledge-reconciliation-v1"


def test_plan_redacts_private_paths_and_does_not_accept_candidate_truth(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    _make_db(candidate, candidate=True)
    _make_db(legacy, candidate=False)
    plan = build_reconciliation_plan(candidate, legacy)
    serialized = json.dumps(plan, ensure_ascii=True)
    assert str(tmp_path) not in serialized
    assert plan["inputs"]["candidate"]["path"] == "candidate.db"
    assert plan["inputs"]["candidate"]["path_disclosure"] == "basename_only"
    assert plan["inputs"]["candidate"]["accepted_truth"] is False
    assert plan["inputs"]["candidate"]["authority_status"] == "unaccepted_input"
    assert plan["migration"]["candidate_authority_accepted"] is False
    assert plan["target"]["materialization"] == "not_applied"


def test_schema_comparison_includes_foreign_keys_and_indexes(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    for path in (candidate, legacy):
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER)")
        connection.execute("INSERT INTO parent VALUES (1)")
        connection.execute("INSERT INTO child VALUES (1, 1)")
        connection.commit()
        connection.close()
    connection = sqlite3.connect(candidate)
    connection.executescript(
        "ALTER TABLE child RENAME TO child_old;"
        "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id));"
        "INSERT INTO child SELECT * FROM child_old;"
        "DROP TABLE child_old;"
        "CREATE INDEX child_parent_idx ON child(parent_id);"
    )
    connection.commit()
    connection.close()
    plan = build_reconciliation_plan(candidate, legacy)
    table = plan["comparison"]["tables"]["child"]
    assert table["schema_equal"] is False
    assert table["schema_delta"]["candidate_only_foreign_keys"]
    assert table["schema_delta"]["candidate_only_indexes"]


def test_non_keyed_row_conflicts_are_explicit(tmp_path: Path):
    candidate = tmp_path / "candidate.db"
    legacy = tmp_path / "legacy.db"
    for path, values in ((candidate, [("same",), ("candidate",)]), (legacy, [("same",), ("legacy",)])):
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE notes (value TEXT NOT NULL)")
        connection.executemany("INSERT INTO notes VALUES (?)", values)
        connection.commit()
        connection.close()
    table = build_reconciliation_plan(candidate, legacy)["comparison"]["tables"]["notes"]
    assert table["key_coverage"] is None
    assert table["row_delta"] == {
        "candidate_only": 1,
        "legacy_only": 1,
        "shared": 1,
        "different_digest_kinds": 2,
    }


def test_missing_provenance_is_reported_per_table(tmp_path: Path):
    database = tmp_path / "candidate.db"
    _make_db(database, candidate=True)
    snapshot = inspect_sqlite(database, source_id="fixture", role="CANDIDATE_AUTHORITY")
    report = snapshot["tables"]["meta"]["provenance"]
    assert report["complete"] is False
    assert "visibility" in report["missing_fields"]
    assert report["status"] == "missing_fields_review_required"


def test_empty_database_is_not_an_applied_target(tmp_path: Path):
    candidate = tmp_path / "empty.db"
    legacy = tmp_path / "legacy.db"
    sqlite3.connect(candidate).close()
    _make_db(legacy, candidate=False)
    plan = build_reconciliation_plan(candidate, legacy)
    assert plan["inputs"]["candidate"]["empty_database"] is True
    assert plan["inputs"]["candidate"]["accepted_truth"] is False
    assert plan["target"]["engine"] == "engine_neutral"
    assert plan["target"]["materialization"] == "not_applied"
    assert plan["migration"]["writes_performed"] is False


def test_missing_and_corrupt_sources_fail_without_creating_outputs(tmp_path: Path):
    missing = tmp_path / "missing.db"
    with pytest.raises(ReconciliationInputError, match="missing"):
        inspect_sqlite(missing, source_id="fixture", role="candidate")
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a sqlite database")
    with pytest.raises(ReconciliationInputError, match="cannot inspect"):
        inspect_sqlite(corrupt, source_id="fixture", role="candidate")
    assert not (tmp_path / "plan.json").exists()


def test_locked_source_fails_fast_and_sources_remain_unchanged(tmp_path: Path):
    database = tmp_path / "locked.db"
    _make_db(database, candidate=True)
    before = database.read_bytes()
    locker = sqlite3.connect(database)
    locker.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(ReconciliationInputError, match="locked|read-only"):
            inspect_sqlite(database, source_id="fixture", role="candidate")
    finally:
        locker.rollback()
        locker.close()
    assert database.read_bytes() == before
    assert not database.with_name("locked.db-journal").exists()


def test_source_change_during_read_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database = tmp_path / "changing.db"
    _make_db(database, candidate=True)
    original = reconciliation._table_snapshot
    changed = False

    def mutate_once(connection: sqlite3.Connection, table: str):
        nonlocal changed
        result = original(connection, table)
        if not changed:
            database.write_bytes(database.read_bytes() + b"\n")
            changed = True
        return result

    monkeypatch.setattr(reconciliation, "_table_snapshot", mutate_once)
    with pytest.raises(reconciliation.SourceChangedDuringReadError, match="changed during read"):
        inspect_sqlite(database, source_id="fixture", role="candidate")
