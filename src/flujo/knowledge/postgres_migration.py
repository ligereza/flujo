"""Safe, deterministic SQLite to PostgreSQL migration primitives.

This module deliberately separates planning, source verification, and import.
It never drops or renames schemas and never treats a plan as a promotion.
PostgreSQL values are always sent through DB-API parameters.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, Sequence

from ._io_helpers import sha256_file as _sha256_file

PLAN_VERSION = "sqlite-postgresql-migration-v1"
_POSTGRES_SYSTEM_SCHEMAS = {"information_schema", "pg_catalog"}
_POSTGRES_TYPE_NAMES = {"BIGINT", "DOUBLE PRECISION", "NUMERIC", "TEXT", "BYTEA"}
_DEFAULT_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_SAFE_DEFAULT_KEYWORDS = {"NULL", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP"}
_FK_ACTIONS = {"NO ACTION", "RESTRICT", "CASCADE", "SET NULL", "SET DEFAULT"}
_FK_MATCHES = {"NONE", "SIMPLE", "FULL"}


class MigrationError(RuntimeError):
    """Base error for fail-closed migration operations."""


class MigrationInputError(MigrationError):
    """Raised when a source or plan is not safe to process."""


class SourceChangedError(MigrationInputError):
    """Raised when the SQLite source changes during a guarded operation."""


class TargetStateError(MigrationError):
    """Raised when the target could cause an implicit overwrite or promotion."""


class DataConversionError(MigrationInputError):
    """Raised when a SQLite value cannot be represented by its mapped type."""


@dataclass(frozen=True)
class SourceFileEvidence:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ColumnPlan:
    name: str
    declared_type: str
    postgres_type: str
    not_null: bool
    default_sql: str | None
    primary_key_position: int


@dataclass(frozen=True)
class ForeignKeyPlan:
    id: int
    sequence: int
    target_table: str
    source_columns: tuple[str, ...]
    target_columns: tuple[str, ...]
    on_update: str
    on_delete: str
    match: str


@dataclass(frozen=True)
class IndexPlan:
    name: str
    unique: bool
    origin: str
    partial: bool
    columns: tuple[str, ...]
    sqlite_sql: str | None


@dataclass(frozen=True)
class TablePlan:
    name: str
    sqlite_sql: str
    columns: tuple[ColumnPlan, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKeyPlan, ...]
    indexes: tuple[IndexPlan, ...]
    row_count: int
    row_hash: str


@dataclass(frozen=True)
class MigrationPlan:
    plan_version: str
    source_id: str
    source_path: str
    source_files: tuple[SourceFileEvidence, ...]
    target_schema: str
    tables: tuple[TablePlan, ...]
    writes_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe deterministic plan representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Serialize the plan without exposing source rows or secrets."""

        return json.dumps(self.as_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    source_unchanged: bool
    table_count: int
    expected_table_count: int
    table_results: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImportReport:
    source_id: str
    target_schema: str
    table_count: int
    row_count: int
    committed: bool
    promotion_performed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def quote_identifier(identifier: str) -> str:
    """Quote one PostgreSQL or SQLite identifier safely.

    Dots are kept inside one quoted identifier. Callers must quote each path
    component separately when addressing a schema-qualified object.
    """

    if not isinstance(identifier, str) or not identifier or "\x00" in identifier:
        raise MigrationInputError("identifier must be a non-empty string without NUL")
    return '"' + identifier.replace('"', '""') + '"'


def _validate_target_schema(schema: str) -> str:
    if not isinstance(schema, str) or not schema.strip():
        raise MigrationInputError("target schema must be a non-empty string")
    if schema.startswith("pg_") or schema in _POSTGRES_SYSTEM_SCHEMAS:
        raise TargetStateError("system PostgreSQL schemas are not valid migration targets")
    quote_identifier(schema)
    return schema


def map_sqlite_type(declared_type: str | None) -> str:
    """Map a SQLite declared type to a deterministic PostgreSQL type."""

    declared = str(declared_type or "").strip().upper()
    if "INT" in declared:
        return "BIGINT"
    if any(token in declared for token in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if any(token in declared for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    if "BLOB" in declared or not declared:
        return "BYTEA"
    if any(token in declared for token in ("NUMERIC", "DECIMAL")):
        return "NUMERIC"
    return "TEXT"


def _quote_sqlite_identifier(identifier: str) -> str:
    return quote_identifier(identifier)


def _source_files(path: Path) -> tuple[SourceFileEvidence, ...]:
    candidates = [path]
    candidates.extend(path.with_name(path.name + suffix) for suffix in ("-wal", "-shm", "-journal"))
    evidence = []
    for candidate in candidates:
        if candidate.exists():
            evidence.append(
                SourceFileEvidence(
                    path=str(candidate.resolve()),
                    size=candidate.stat().st_size,
                    sha256=_sha256_file(candidate),
                )
            )
    return tuple(evidence)


def _require_source(path: str | Path) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise MigrationInputError(f"SQLite source does not exist: {source}")
    return source


@contextmanager
def open_sqlite_read_only(path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open SQLite in URI read-only mode and enable query-only protection."""

    source = _require_source(path)
    uri = source.as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=0.2)
    except sqlite3.DatabaseError as exc:
        raise MigrationInputError(f"cannot open SQLite source read-only: {source}") from exc
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
    finally:
        connection.close()


def _table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names = []
    for row in rows:
        name = str(row[0])
        sql = str(row[1] or "")
        if "VIRTUAL TABLE" in sql.upper():
            raise MigrationInputError(f"virtual SQLite table is unsupported: {name}")
        names.append(name)
    unsupported = connection.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('view', 'trigger') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    views = [str(row[0]) for row in unsupported if row[1] == "view"]
    if views:
        raise MigrationInputError("SQLite views require an explicit projection: " + ", ".join(views))
    return tuple(names)


def _table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    if row is None or not row[0]:
        raise MigrationInputError(f"missing SQLite table evidence: {table}")
    return str(row[0])


def _columns(connection: sqlite3.Connection, table: str) -> tuple[ColumnPlan, ...]:
    rows = connection.execute(
        f"PRAGMA table_xinfo({_quote_sqlite_identifier(table)})"
    ).fetchall()
    result = []
    for row in rows:
        hidden = int(row[6] or 0)
        if hidden:
            raise MigrationInputError(f"hidden or generated SQLite column is unsupported: {table}.{row[1]}")
        declared_type = str(row[2] or "")
        result.append(
            ColumnPlan(
                name=str(row[1]),
                declared_type=declared_type,
                postgres_type=map_sqlite_type(declared_type),
                not_null=bool(row[3]),
                default_sql=None if row[4] is None else str(row[4]),
                primary_key_position=int(row[5] or 0),
            )
        )
    if not result:
        raise MigrationInputError(f"SQLite table has no visible columns: {table}")
    return tuple(result)


def _safe_default_sql(default_sql: str | None) -> str | None:
    """Return a PostgreSQL-safe literal default or fail closed."""

    if default_sql is None:
        return None
    value = default_sql.strip()
    if not value:
        raise MigrationInputError("empty SQLite default is unsupported")
    if value.upper() in _SAFE_DEFAULT_KEYWORDS or _DEFAULT_NUMBER.fullmatch(value):
        return value.upper() if value.upper() in _SAFE_DEFAULT_KEYWORDS else value
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        if "\x00" in value:
            raise MigrationInputError("NUL SQLite default is unsupported")
        return value
    if len(value) >= 3 and value[0] in "xX" and value[1] == "'" and value[-1] == "'":
        literal = value[2:-1]
        if len(literal) % 2 or re.fullmatch(r"[0-9A-Fa-f]*", literal) is None:
            raise MigrationInputError("invalid SQLite blob default")
        return "decode('" + literal.upper() + "', 'hex')"
    if value.startswith("(") and value.endswith(")"):
        inner = _safe_default_sql(value[1:-1])
        return None if inner is None else "(" + inner + ")"
    raise MigrationInputError(f"unsupported SQLite default expression: {default_sql}")


def _column_default_sql(column: ColumnPlan) -> str | None:
    """Validate a safe default against the mapped PostgreSQL column type."""

    value = _safe_default_sql(column.default_sql)
    if value is None or value.upper() == "NULL":
        return value
    if column.postgres_type in {"BIGINT", "DOUBLE PRECISION", "NUMERIC"}:
        candidate = value
        if len(candidate) >= 2 and candidate[0] == "'" and candidate[-1] == "'":
            candidate = candidate[1:-1].replace("''", "'")
        if not _DEFAULT_NUMBER.fullmatch(candidate):
            raise MigrationInputError(
                f"default is incompatible with {column.postgres_type}: {column.name}"
            )
        if column.postgres_type == "BIGINT" and not Decimal(candidate).is_finite():
            raise MigrationInputError(f"invalid BIGINT default: {column.name}")
        if column.postgres_type == "BIGINT" and not Decimal(candidate) == Decimal(candidate).to_integral_value():
            raise MigrationInputError(f"non-integral BIGINT default: {column.name}")
        return value
    if column.postgres_type == "TEXT":
        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            return value
        raise MigrationInputError(f"default is incompatible with TEXT: {column.name}")
    if column.postgres_type == "BYTEA":
        if value.startswith("decode('") and value.endswith("', 'hex')"):
            return value
        raise MigrationInputError(f"default is incompatible with BYTEA: {column.name}")
    raise MigrationInputError(f"unsupported default type: {column.postgres_type}")


def _foreign_keys(connection: sqlite3.Connection, table: str) -> tuple[ForeignKeyPlan, ...]:
    rows = connection.execute(
        f"PRAGMA foreign_key_list({_quote_sqlite_identifier(table)})"
    ).fetchall()
    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(int(row[0]), []).append(row)
    result = []
    for key_id in sorted(grouped):
        group = sorted(grouped[key_id], key=lambda item: int(item[1]))
        first = group[0]
        result.append(
            ForeignKeyPlan(
                id=key_id,
                sequence=int(first[1]),
                target_table=str(first[2]),
                source_columns=tuple(str(item[3]) for item in group),
                target_columns=tuple(str(item[4]) for item in group),
                on_update=str(first[5] or "NO ACTION").upper(),
                on_delete=str(first[6] or "NO ACTION").upper(),
                match=str(first[7] or "NONE").upper(),
            )
        )
    return tuple(result)


def _indexes(connection: sqlite3.Connection, table: str) -> tuple[IndexPlan, ...]:
    rows = connection.execute(
        f"PRAGMA index_list({_quote_sqlite_identifier(table)})"
    ).fetchall()
    result = []
    for row in sorted(rows, key=lambda item: str(item[1])):
        name = str(row[1])
        info = connection.execute(f"PRAGMA index_info({_quote_sqlite_identifier(name)})").fetchall()
        result.append(
            IndexPlan(
                name=name,
                unique=bool(row[2]),
                origin=str(row[3] or ""),
                partial=bool(row[4]) if len(row) > 4 else False,
                columns=tuple(str(item[2]) for item in sorted(info, key=lambda item: int(item[0]))),
                sqlite_sql=(
                    str(sql_row[0])
                    if (sql_row := connection.execute(
                        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
                    ).fetchone())
                    and sql_row[0]
                    else None
                ),
            )
        )
    return tuple(result)


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    return str(value)


def _read_table_rows(
    connection: sqlite3.Connection, table: str, columns: Sequence[ColumnPlan]
) -> tuple[list[sqlite3.Row], list[tuple[str, ...]]]:
    rows = connection.execute(f"SELECT * FROM {_quote_sqlite_identifier(table)}").fetchall()
    type_sql = ", ".join(
        f"typeof({_quote_sqlite_identifier(column.name)})" for column in columns
    )
    storage_rows = connection.execute(
        f"SELECT {type_sql} FROM {_quote_sqlite_identifier(table)}"
    ).fetchall()
    return rows, [tuple(str(value) for value in row) for row in storage_rows]


def _validate_storage_value(value: Any, storage_class: str, postgres_type: str) -> None:
    if value is None:
        if storage_class != "null":
            raise DataConversionError("SQLite storage class disagrees with NULL value")
        return
    if storage_class == "null":
        raise DataConversionError("SQLite NULL storage class contains a value")
    try:
        if postgres_type == "BIGINT":
            if storage_class != "integer" or not -(2**63) <= int(value) <= 2**63 - 1:
                raise DataConversionError("SQLite value cannot round-trip as BIGINT")
        elif postgres_type == "DOUBLE PRECISION":
            if storage_class not in {"integer", "real"}:
                raise DataConversionError("SQLite value cannot round-trip as DOUBLE PRECISION")
            number = float(value)
            if not math.isfinite(number) or (
                storage_class == "integer" and int(number) != int(value)
            ):
                raise DataConversionError("SQLite value cannot round-trip as DOUBLE PRECISION")
        elif postgres_type == "NUMERIC":
            if storage_class not in {"integer", "real", "text"}:
                raise DataConversionError("SQLite value cannot round-trip as NUMERIC")
            number = Decimal(str(value))
            if not number.is_finite():
                raise DataConversionError("SQLite value cannot round-trip as NUMERIC")
        elif postgres_type == "TEXT":
            if storage_class != "text" or not isinstance(value, str):
                raise DataConversionError("SQLite value cannot round-trip as TEXT")
        elif postgres_type == "BYTEA":
            if storage_class != "blob" or not isinstance(value, (bytes, bytearray, memoryview)):
                raise DataConversionError("SQLite value cannot round-trip as BYTEA")
    except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
        raise DataConversionError(
            f"SQLite value cannot round-trip as {postgres_type}"
        ) from exc


def _validate_storage_rows(
    rows: Sequence[Sequence[Any]],
    storage_rows: Sequence[Sequence[str]],
    columns: Sequence[ColumnPlan],
) -> None:
    if len(rows) != len(storage_rows):
        raise DataConversionError("SQLite row/storage evidence length differs")
    for row, storage_row in zip(rows, storage_rows):
        if len(row) != len(columns) or len(storage_row) != len(columns):
            raise DataConversionError("SQLite row/storage evidence width differs")
        for value, storage_class, column in zip(row, storage_row, columns):
            _validate_storage_value(value, storage_class, column.postgres_type)


def _canonical_value(value: Any, postgres_type: str) -> Any:
    if value is None:
        return None
    try:
        if postgres_type == "BIGINT":
            return int(value)
        if postgres_type == "DOUBLE PRECISION":
            return _json_value(float(value))
        if postgres_type == "NUMERIC":
            return format(Decimal(str(value)).normalize(), "f")
        if postgres_type == "BYTEA":
            if isinstance(value, str):
                value = value.encode("utf-8")
            return _json_value(bytes(value))
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise DataConversionError(f"value cannot be mapped to {postgres_type}") from exc


def _postgres_value(value: Any, postgres_type: str) -> Any:
    if value is None:
        return None
    canonical = _canonical_value(value, postgres_type)
    if postgres_type == "BIGINT":
        return int(canonical)
    if postgres_type == "DOUBLE PRECISION":
        return float(canonical)
    if postgres_type == "NUMERIC":
        return Decimal(canonical)
    if postgres_type == "BYTEA":
        if isinstance(value, str):
            return value.encode("utf-8")
        return bytes(value)
    return str(canonical)


def _row_hash(rows: Sequence[Sequence[Any]], columns: Sequence[ColumnPlan]) -> str:
    digests = []
    for row in rows:
        if len(row) != len(columns):
            raise DataConversionError("row width does not match SQLite table evidence")
        values = {
            column.name: _canonical_value(value, column.postgres_type)
            for column, value in zip(columns, row)
        }
        encoded = json.dumps(values, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        digests.append(hashlib.sha256(encoded.encode("utf-8")).hexdigest())
    digest = hashlib.sha256()
    for item in sorted(digests):
        digest.update(item.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_migration_plan(
    source_path: str | Path,
    target_schema: str,
    *,
    source_id: str = "sqlite_source",
) -> MigrationPlan:
    """Build a read-only plan with schema, provenance, and row evidence."""

    source = _require_source(source_path)
    target = _validate_target_schema(target_schema)
    if not isinstance(source_id, str) or not source_id.strip() or "\x00" in source_id:
        raise MigrationInputError("source_id must be a non-empty string without NUL")
    files_before = _source_files(source)
    with open_sqlite_read_only(source) as connection:
        tables = []
        for table_name in _table_names(connection):
            columns = _columns(connection, table_name)
            rows, storage_rows = _read_table_rows(connection, table_name, columns)
            _validate_storage_rows(rows, storage_rows, columns)
            for column in columns:
                _column_default_sql(column)
            table = TablePlan(
                name=table_name,
                sqlite_sql=_table_sql(connection, table_name),
                columns=columns,
                primary_key=tuple(
                    column.name
                    for column in sorted(columns, key=lambda item: item.primary_key_position)
                    if column.primary_key_position
                ),
                foreign_keys=_foreign_keys(connection, table_name),
                indexes=_indexes(connection, table_name),
                row_count=len(rows),
                row_hash=_row_hash(rows, columns),
            )
            tables.append(table)
    files_after = _source_files(source)
    if files_before != files_after:
        raise SourceChangedError("SQLite source changed while building migration plan")
    return MigrationPlan(
        plan_version=PLAN_VERSION,
        source_id=source_id,
        source_path=str(source),
        source_files=files_before,
        target_schema=target,
        tables=tuple(tables),
    )


def dry_run(
    source_path: str | Path,
    target_schema: str,
    *,
    source_id: str = "sqlite_source",
) -> dict[str, Any]:
    """Return the deterministic plan as a JSON-safe dry-run result."""

    return build_migration_plan(source_path, target_schema, source_id=source_id).as_dict()


def _current_source_matches(plan: MigrationPlan) -> bool:
    source = _require_source(plan.source_path)
    return _source_files(source) == plan.source_files


def verify_source(source_path: str | Path, plan: MigrationPlan) -> VerificationReport:
    """Verify source fingerprints and row evidence without writing anywhere."""

    errors: list[str] = []
    source_unchanged = False
    table_results: list[dict[str, Any]] = []
    try:
        source = _require_source(source_path)
        source_unchanged = _source_files(source) == plan.source_files
        if not source_unchanged:
            errors.append("source fingerprint differs from migration plan")
        if source_unchanged:
            current = build_migration_plan(source, plan.target_schema, source_id=plan.source_id)
            expected = plan.as_dict()
            actual = current.as_dict()
            expected.pop("writes_performed", None)
            actual.pop("writes_performed", None)
            if expected != actual:
                errors.append("source schema or row evidence differs from migration plan")
            table_results = [
                {"table": table.name, "ok": True, "row_count": table.row_count, "row_hash": table.row_hash}
                for table in plan.tables
            ]
    except (MigrationError, sqlite3.DatabaseError) as exc:
        errors.append(str(exc))
    return VerificationReport(
        ok=not errors,
        source_unchanged=source_unchanged,
        table_count=len(table_results),
        expected_table_count=len(plan.tables),
        table_results=tuple(table_results),
        errors=tuple(errors),
    )


def _schema_exists(cursor: Any, schema: str) -> bool:
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s)",
        (schema,),
    )
    row = cursor.fetchone()
    return bool(row and row[0])


def _target_tables(cursor: Any, schema: str) -> tuple[str, ...]:
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
        (schema,),
    )
    return tuple(str(row[0]) for row in cursor.fetchall())


def _create_table_sql(schema: str, table: TablePlan) -> str:
    fields = []
    for column in table.columns:
        nullability = " NOT NULL" if column.not_null else ""
        default = _column_default_sql(column)
        default_sql = " DEFAULT " + default if default is not None else ""
        fields.append(
            f"{quote_identifier(column.name)} {column.postgres_type}{default_sql}{nullability}"
        )
    if table.primary_key:
        fields.append(
            "PRIMARY KEY (" + ", ".join(quote_identifier(name) for name in table.primary_key) + ")"
        )
    return (
        f"CREATE TABLE {quote_identifier(schema)}.{quote_identifier(table.name)} ("
        + ", ".join(fields)
        + ")"
    )


def _foreign_key_sql(schema: str, table: TablePlan, foreign_key: ForeignKeyPlan) -> str:
    if foreign_key.on_update not in _FK_ACTIONS or foreign_key.on_delete not in _FK_ACTIONS:
        raise MigrationInputError("unsupported SQLite foreign-key action")
    if foreign_key.match not in _FK_MATCHES:
        raise MigrationInputError("unsupported SQLite foreign-key match mode")
    constraint_name = f"fk_{table.name}_{foreign_key.id}"
    statement = (
        f"ALTER TABLE {quote_identifier(schema)}.{quote_identifier(table.name)} "
        f"ADD CONSTRAINT {quote_identifier(constraint_name)} FOREIGN KEY ("
        + ", ".join(quote_identifier(name) for name in foreign_key.source_columns)
        + ") REFERENCES "
        + f"{quote_identifier(schema)}.{quote_identifier(foreign_key.target_table)} ("
        + ", ".join(quote_identifier(name) for name in foreign_key.target_columns)
        + ")"
    )
    if foreign_key.match == "FULL":
        statement += " MATCH FULL"
    statement += f" ON UPDATE {foreign_key.on_update} ON DELETE {foreign_key.on_delete}"
    return statement


def _index_sql(schema: str, table: TablePlan, index: IndexPlan) -> str:
    if index.origin != "c":
        raise MigrationInputError("automatic SQLite index cannot be emitted explicitly")
    if not index.columns:
        raise MigrationInputError(f"expression SQLite index is unsupported: {index.name}")
    statement = (
        "CREATE " + ("UNIQUE " if index.unique else "") + "INDEX "
        + f"{quote_identifier(schema)}.{quote_identifier(index.name)} ON "
        + f"{quote_identifier(schema)}.{quote_identifier(table.name)} ("
        + ", ".join(quote_identifier(name) for name in index.columns)
        + ")"
    )
    if index.partial:
        if not index.sqlite_sql:
            raise MigrationInputError(f"partial SQLite index has no SQL: {index.name}")
        match = re.search(r"\bWHERE\b(.+)$", index.sqlite_sql, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise MigrationInputError(f"partial SQLite index has no WHERE clause: {index.name}")
        predicate = match.group(1).strip()
        if not predicate or ";" in predicate or "\x00" in predicate or "--" in predicate or "/*" in predicate:
            raise MigrationInputError(f"unsafe partial SQLite index predicate: {index.name}")
        statement += " WHERE " + predicate
    return statement


def _validate_plan(plan: MigrationPlan) -> None:
    if plan.plan_version != PLAN_VERSION:
        raise MigrationInputError("unsupported migration plan version")
    _validate_target_schema(plan.target_schema)
    table_names = set()
    all_table_names = {candidate.name for candidate in plan.tables}
    table_columns = {
        candidate.name: {column.name for column in candidate.columns}
        for candidate in plan.tables
    }
    for table in plan.tables:
        if table.name in table_names:
            raise MigrationInputError("migration plan contains duplicate table names")
        table_names.add(table.name)
        quote_identifier(table.name)
        column_names = set()
        for column in table.columns:
            quote_identifier(column.name)
            if column.name in column_names:
                raise MigrationInputError(f"duplicate column in migration plan: {table.name}")
            column_names.add(column.name)
            if column.postgres_type not in _POSTGRES_TYPE_NAMES:
                raise MigrationInputError(f"unsupported PostgreSQL type in migration plan: {column.postgres_type}")
            _column_default_sql(column)
        if any(name not in column_names for name in table.primary_key):
            raise MigrationInputError(f"primary key references an unknown column: {table.name}")
        for foreign_key in table.foreign_keys:
            if foreign_key.target_table not in all_table_names:
                raise MigrationInputError(f"foreign key references unknown table: {foreign_key.target_table}")
            if len(foreign_key.source_columns) != len(foreign_key.target_columns):
                raise MigrationInputError(f"foreign key column count differs: {table.name}")
            if any(name not in column_names for name in foreign_key.source_columns):
                raise MigrationInputError(f"foreign key references unknown source column: {table.name}")
            if any(name not in table_columns[foreign_key.target_table] for name in foreign_key.target_columns):
                raise MigrationInputError(f"foreign key references unknown target column: {table.name}")
            if foreign_key.on_update not in _FK_ACTIONS or foreign_key.on_delete not in _FK_ACTIONS:
                raise MigrationInputError("unsupported foreign-key action in migration plan")
            if foreign_key.match not in _FK_MATCHES:
                raise MigrationInputError("unsupported foreign-key match in migration plan")
        for index in table.indexes:
            if index.origin == "c":
                if any(name not in column_names for name in index.columns):
                    raise MigrationInputError(f"index references unknown column: {index.name}")
                _index_sql(plan.target_schema, table, index)


def apply_plan(
    connection: Any,
    plan: MigrationPlan,
    *,
    allow_existing_empty_schema: bool = False,
    batch_size: int = 500,
) -> ImportReport:
    """Import a plan into a fresh target schema using parameterized values.

    The caller must supply a DB-API 2.0 connection. The function never drops,
    renames, or promotes a schema. Existing schemas are rejected by default.
    """

    if not isinstance(plan, MigrationPlan):
        raise MigrationInputError("apply_plan requires a MigrationPlan")
    _validate_plan(plan)
    if batch_size < 1:
        raise MigrationInputError("batch_size must be positive")
    if not _current_source_matches(plan):
        raise SourceChangedError("SQLite source fingerprint differs from migration plan")

    cursor = connection.cursor()
    committed = False
    row_count = 0
    try:
        cursor.execute("BEGIN")
        exists = _schema_exists(cursor, plan.target_schema)
        if exists:
            if not allow_existing_empty_schema:
                raise TargetStateError("target schema already exists; explicit empty-schema opt-in required")
            existing_tables = _target_tables(cursor, plan.target_schema)
            if existing_tables:
                raise TargetStateError("target schema is not empty")
        else:
            cursor.execute(f"CREATE SCHEMA {quote_identifier(plan.target_schema)}")

        for table in plan.tables:
            cursor.execute(_create_table_sql(plan.target_schema, table))

        with open_sqlite_read_only(plan.source_path) as source_connection:
            for table in plan.tables:
                rows, storage_rows = _read_table_rows(source_connection, table.name, table.columns)
                _validate_storage_rows(rows, storage_rows, table.columns)
                placeholders = ", ".join(["%s"] * len(table.columns))
                columns = ", ".join(quote_identifier(column.name) for column in table.columns)
                statement = (
                    f"INSERT INTO {quote_identifier(plan.target_schema)}.{quote_identifier(table.name)} "
                    f"({columns}) VALUES ({placeholders})"
                )
                values = [
                    tuple(
                        _postgres_value(value, column.postgres_type)
                        for column, value in zip(table.columns, row)
                    )
                    for row in rows
                ]
                for start in range(0, len(values), batch_size):
                    cursor.executemany(statement, values[start : start + batch_size])
                row_count += len(values)

        for table in plan.tables:
            for foreign_key in table.foreign_keys:
                cursor.execute(_foreign_key_sql(plan.target_schema, table, foreign_key))
            for index in table.indexes:
                if index.origin == "c":
                    cursor.execute(_index_sql(plan.target_schema, table, index))

        if not _current_source_matches(plan):
            raise SourceChangedError("SQLite source changed before PostgreSQL commit")
        connection.commit()
        committed = True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
    return ImportReport(
        source_id=plan.source_id,
        target_schema=plan.target_schema,
        table_count=len(plan.tables),
        row_count=row_count,
        committed=committed,
        promotion_performed=False,
    )


def verify_target(connection: Any, plan: MigrationPlan) -> VerificationReport:
    """Verify target table counts and normalized row hashes without mutation."""

    source_report = verify_source(plan.source_path, plan)
    errors: list[str] = list(source_report.errors)
    results: list[dict[str, Any]] = []
    cursor = connection.cursor()
    try:
        actual_tables = _target_tables(cursor, plan.target_schema)
        expected_names = tuple(table.name for table in plan.tables)
        if actual_tables != expected_names:
            errors.append("target table set differs from migration plan")
        for table in plan.tables:
            columns = ", ".join(quote_identifier(column.name) for column in table.columns)
            cursor.execute(
                f"SELECT {columns} FROM {quote_identifier(plan.target_schema)}."
                f"{quote_identifier(table.name)}"
            )
            rows = cursor.fetchall()
            actual_hash = _row_hash(rows, table.columns)
            ok = len(rows) == table.row_count and actual_hash == table.row_hash
            results.append(
                {
                    "table": table.name,
                    "ok": ok,
                    "row_count": len(rows),
                    "expected_row_count": table.row_count,
                    "row_hash": actual_hash,
                    "expected_row_hash": table.row_hash,
                }
            )
            if not ok:
                errors.append(f"target evidence differs for table: {table.name}")
    except Exception as exc:
        errors.append(f"target verification failed: {exc}")
    finally:
        cursor.close()
    return VerificationReport(
        ok=not errors,
        source_unchanged=source_report.source_unchanged,
        table_count=len(results),
        expected_table_count=len(plan.tables),
        table_results=tuple(results),
        errors=tuple(errors),
    )


__all__ = [
    "ColumnPlan",
    "DataConversionError",
    "ForeignKeyPlan",
    "ImportReport",
    "IndexPlan",
    "MigrationError",
    "MigrationInputError",
    "MigrationPlan",
    "PLAN_VERSION",
    "SourceChangedError",
    "SourceFileEvidence",
    "TablePlan",
    "TargetStateError",
    "VerificationReport",
    "apply_plan",
    "build_migration_plan",
    "dry_run",
    "map_sqlite_type",
    "open_sqlite_read_only",
    "quote_identifier",
    "verify_source",
    "verify_target",
]
