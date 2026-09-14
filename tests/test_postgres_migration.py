from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from flujo.knowledge.postgres_migration import (
    DataConversionError,
    MigrationInputError,
    TargetStateError,
    apply_plan,
    build_migration_plan,
    dry_run,
    map_sqlite_type,
    open_sqlite_read_only,
    quote_identifier,
    _source_files,
    verify_source,
    verify_target,
)


def _make_source(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        '''
        CREATE TABLE "odd""table" (
            "id""x" INTEGER PRIMARY KEY,
            "body""x" TEXT NOT NULL,
            "blob""x" BLOB,
            "real""x" REAL,
            "num""x" NUMERIC,
            "quote; DROP" TEXT
        );
        CREATE TABLE parent (id INTEGER PRIMARY KEY);
        CREATE TABLE child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES parent(id)
        );
        CREATE INDEX child_parent_idx ON child(parent_id);
        CREATE TABLE defaults (
            id INTEGER PRIMARY KEY,
            label TEXT DEFAULT 'ready',
            count INTEGER DEFAULT 3,
            created TEXT DEFAULT 'now',
            payload BLOB DEFAULT X'ABCD'
        );
        '''
    )
    connection.execute(
        'INSERT INTO "odd""table" VALUES (?, ?, ?, ?, ?, ?)',
        (1, "value'); DROP TABLE parent; --", b"binary", 1.5, "2.00", "quoted"),
    )
    connection.execute("INSERT INTO parent VALUES (1)")
    connection.execute("INSERT INTO child VALUES (1, 1)")
    connection.commit()
    connection.close()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_type_mapping_and_identifier_quoting_are_deterministic():
    assert quote_identifier('odd"table') == '"odd""table"'
    assert quote_identifier("quote; DROP") == '"quote; DROP"'
    assert map_sqlite_type("INTEGER PRIMARY KEY") == "BIGINT"
    assert map_sqlite_type("VARCHAR(80)") == "TEXT"
    assert map_sqlite_type("DOUBLE") == "DOUBLE PRECISION"
    assert map_sqlite_type("NUMERIC(12,2)") == "NUMERIC"
    assert map_sqlite_type("BLOB") == "BYTEA"
    assert map_sqlite_type("") == "BYTEA"
    with pytest.raises(MigrationInputError):
        quote_identifier("")
    with pytest.raises(MigrationInputError):
        quote_identifier("bad\x00name")


def test_plan_is_deterministic_and_preserves_source_evidence(tmp_path: Path):
    source = tmp_path / "evidence.db"
    _make_source(source)
    before = _file_hash(source)

    first = build_migration_plan(source, "rd_stage", source_id="windows_rd")
    second = build_migration_plan(source, "rd_stage", source_id="windows_rd")

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.writes_performed is False
    assert first.target_schema == "rd_stage"
    odd = next(table for table in first.tables if table.name == 'odd"table')
    assert odd.primary_key == ('id"x',)
    assert odd.columns[0].postgres_type == "BIGINT"
    assert odd.columns[-1].name == "quote; DROP"
    assert odd.foreign_keys == ()
    child = next(table for table in first.tables if table.name == "child")
    assert child.foreign_keys[0].target_table == "parent"
    assert child.indexes[0].origin == "c"
    assert child.indexes[0].columns == ("parent_id",)
    defaults = next(table for table in first.tables if table.name == "defaults")
    assert [column.default_sql for column in defaults.columns] == [None, "'ready'", "3", "'now'", "X'ABCD'"]
    assert child.row_count == 1
    assert _file_hash(source) == before


def test_source_is_read_only_and_plan_does_not_modify_bytes(tmp_path: Path):
    source = tmp_path / "readonly.db"
    _make_source(source)
    before = _file_hash(source)
    with open_sqlite_read_only(source) as connection:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("CREATE TABLE injected (value TEXT)")
    plan = build_migration_plan(source, "rd_stage")
    report = verify_source(source, plan)
    assert report.ok is True
    assert report.source_unchanged is True
    assert _file_hash(source) == before


def test_journal_is_part_of_source_fingerprint(tmp_path: Path):
    source = tmp_path / "journal.db"
    _make_source(source)
    plan = build_migration_plan(source, "rd_stage")
    journal = Path(str(source) + "-journal")
    journal.write_bytes(b"journal-evidence-v1")
    assert any(item.path.endswith("-journal") for item in _source_files(source))
    report = verify_source(source, plan)
    assert report.ok is False
    assert report.source_unchanged is False


def test_storage_class_mismatch_fails_closed(tmp_path: Path):
    source = tmp_path / "storage.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE values_table (value INTEGER)")
    connection.execute("INSERT INTO values_table VALUES (1.5)")
    connection.commit()
    connection.close()
    with pytest.raises(DataConversionError, match="round-trip"):
        build_migration_plan(source, "rd_stage")


def test_unsupported_default_fails_closed(tmp_path: Path):
    source = tmp_path / "default.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE values_table (value INTEGER DEFAULT (random()))")
    connection.commit()
    connection.close()
    with pytest.raises(MigrationInputError, match="default"):
        build_migration_plan(source, "rd_stage")


def test_dry_run_is_json_safe_and_contains_no_source_rows(tmp_path: Path):
    source = tmp_path / "dry-run.db"
    _make_source(source)
    result = dry_run(source, "rd_stage", source_id="windows_rd")
    assert result["plan_version"] == "sqlite-postgresql-migration-v1"
    assert result["writes_performed"] is False
    serialized = str(result)
    assert "binary" not in serialized
    assert "value'); DROP TABLE parent" not in serialized
    assert result["source_files"][0]["sha256"] == _file_hash(source)


def test_fail_closed_for_unsafe_target_and_unsupported_view(tmp_path: Path):
    source = tmp_path / "source.db"
    _make_source(source)
    with pytest.raises(TargetStateError):
        build_migration_plan(source, "pg_catalog")

    view_source = tmp_path / "view.db"
    connection = sqlite3.connect(view_source)
    connection.execute("CREATE TABLE base (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE VIEW public_view AS SELECT * FROM base")
    connection.commit()
    connection.close()
    with pytest.raises(MigrationInputError, match="views require"):
        build_migration_plan(view_source, "rd_stage")


class _FakeCursor:
    def __init__(self, schema_exists: bool = False, tables: tuple[str, ...] = ()):
        self.schema_exists = schema_exists
        self.tables = tables
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []
        self._result: list[tuple[object, ...]] = []

    def execute(self, statement: str, params=None):
        self.executed.append((statement, params))
        if "FROM pg_namespace" in statement:
            self._result = [(self.schema_exists,)]
        elif "FROM information_schema.tables" in statement:
            self._result = [(name,) for name in self.tables]
        else:
            self._result = []

    def executemany(self, statement: str, params):
        self.executemany_calls.append((statement, list(params)))

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)

    def close(self):
        pass


class _FakeConnection:
    def __init__(self, schema_exists: bool = False, tables: tuple[str, ...] = ()):
        self.cursor_value = _FakeCursor(schema_exists, tables)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_apply_uses_parameterized_values_and_never_promotes_or_drops(tmp_path: Path):
    source = tmp_path / "apply.db"
    _make_source(source)
    plan = build_migration_plan(source, "rd_stage")
    connection = _FakeConnection()

    report = apply_plan(connection, plan, batch_size=1)

    assert report.committed is True
    assert report.promotion_performed is False
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.cursor_value.executemany_calls
    for statement, batches in connection.cursor_value.executemany_calls:
        assert "%s" in statement
        assert "value'); DROP TABLE parent" not in statement
    all_sql = "\n".join(statement for statement, _ in connection.cursor_value.executed)
    assert "DROP SCHEMA" not in all_sql.upper()
    assert "DROP TABLE" not in all_sql.upper()
    assert "ALTER SCHEMA" not in all_sql.upper()
    assert "RENAME TO" not in all_sql.upper()
    assert 'ALTER TABLE "rd_stage"."child" ADD CONSTRAINT' in all_sql
    assert 'CREATE INDEX "rd_stage"."child_parent_idx"' in all_sql
    assert "DEFAULT 'ready'" in all_sql
    assert "DEFAULT decode('ABCD', 'hex')" in all_sql


def test_verify_target_rechecks_source_before_reporting_unchanged(tmp_path: Path):
    source = tmp_path / "verify.db"
    _make_source(source)
    plan = build_migration_plan(source, "rd_stage")
    journal = Path(str(source) + "-journal")
    journal.write_bytes(b"changed-after-plan")
    report = verify_target(_FakeConnection(), plan)
    assert report.source_unchanged is False
    assert report.ok is False
    assert any("fingerprint" in error for error in report.errors)


def test_existing_schema_is_rejected_without_explicit_empty_opt_in(tmp_path: Path):
    source = tmp_path / "existing.db"
    _make_source(source)
    plan = build_migration_plan(source, "rd_stage")
    connection = _FakeConnection(schema_exists=True, tables=())
    with pytest.raises(TargetStateError, match="already exists"):
        apply_plan(connection, plan)
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_apply_rejects_forged_sql_type_in_plan(tmp_path: Path):
    source = tmp_path / "forged.db"
    _make_source(source)
    plan = build_migration_plan(source, "rd_stage")
    table = plan.tables[0]
    forged_column = replace(table.columns[0], postgres_type="DROP SCHEMA rd_stage")
    forged_table = replace(table, columns=(forged_column,) + table.columns[1:])
    forged_plan = replace(plan, tables=(forged_table,) + plan.tables[1:])
    with pytest.raises(MigrationInputError, match="unsupported PostgreSQL type"):
        apply_plan(_FakeConnection(), forged_plan)
