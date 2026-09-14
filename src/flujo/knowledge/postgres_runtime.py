"""Safe runtime boundary for the MAK PostgreSQL knowledge database.

This module intentionally keeps PostgreSQL behind the ``psql`` executable.
The default contract uses the local Unix socket on MAK. TCP and password
authentication are explicit opt-in paths supplied by environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Mapping, Sequence


DEFAULT_DATABASE = "mak_knowledge"
DEFAULT_USER = "mak"
DEFAULT_SOCKET_DIR = "/var/run/postgresql"
DEFAULT_PSQL = "/usr/bin/psql"
DEFAULT_PORT = "5432"
TARGET_SCHEMAS = (
    "core",
    "mak",
    "rd",
    "portfolio",
    "relations",
    "products",
    "audit",
)


class ConfigurationError(ValueError):
    """Raised when an unsafe or incomplete PostgreSQL configuration is found."""


@dataclass(frozen=True)
class PostgresConfig:
    """Resolved PostgreSQL connection settings.

    ``password`` is retained only in memory so the subprocess environment can
    receive it. It is never placed in the command argument list or in a health
    report.
    """

    database: str = DEFAULT_DATABASE
    user: str = DEFAULT_USER
    transport: str = "unix"
    socket_dir: str = DEFAULT_SOCKET_DIR
    host: str | None = None
    port: str = DEFAULT_PORT
    password: str | None = None
    psql_path: str = DEFAULT_PSQL
    schemas: tuple[str, ...] = TARGET_SCHEMAS


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class HealthReport:
    installed: bool
    online: bool
    connectable: bool
    schema_ready: bool
    primary_writer: bool
    error: str | None = None
    details: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a serialization-safe report without credentials."""

        return {
            "installed": self.installed,
            "online": self.online,
            "connectable": self.connectable,
            "schema_ready": self.schema_ready,
            "primary_writer": self.primary_writer,
            "error": self.error,
            "details": dict(self.details),
        }


Runner = Callable[[Sequence[str], Mapping[str, str]], CommandResult]


def resolve_config(env: Mapping[str, str] | None = None) -> PostgresConfig:
    """Resolve the explicit MAK PostgreSQL environment contract.

    Defaults are Unix-socket-first and target ``mak_knowledge`` as the ``mak``
    role. Supplying ``MAK_POSTGRES_HOST`` or ``MAK_POSTGRES_PORT`` is an
    explicit TCP request. TCP requires both values. A password is accepted
    only on a complete TCP configuration and is passed through ``PGPASSWORD``
    to ``psql``; it is never a command argument.
    """

    values = os.environ if env is None else env
    database = values.get("MAK_POSTGRES_DATABASE", DEFAULT_DATABASE)
    user = values.get("MAK_POSTGRES_USER", DEFAULT_USER)
    socket_dir = values.get("MAK_POSTGRES_SOCKET_DIR", DEFAULT_SOCKET_DIR)
    psql_path = values.get("MAK_POSTGRES_PSQL", DEFAULT_PSQL)
    explicit_transport = values.get("MAK_POSTGRES_TRANSPORT", "").strip().lower()
    host = values.get("MAK_POSTGRES_HOST")
    explicit_port = values.get("MAK_POSTGRES_PORT")
    password = values.get("MAK_POSTGRES_PASSWORD")
    password_requested = "MAK_POSTGRES_PASSWORD" in values

    if not database or not user or not psql_path:
        raise ConfigurationError("database, user, and psql path must be configured")
    if explicit_transport not in {"", "unix", "tcp"}:
        raise ConfigurationError("MAK_POSTGRES_TRANSPORT must be unix or tcp")

    transport = explicit_transport or ("tcp" if host or "MAK_POSTGRES_PORT" in values else "unix")
    if transport == "unix":
        if host or "MAK_POSTGRES_PORT" in values:
            raise ConfigurationError("TCP host or port requires MAK_POSTGRES_TRANSPORT=tcp")
        if password_requested:
            raise ConfigurationError("password authentication requires a complete TCP configuration")
        return PostgresConfig(
            database=database,
            user=user,
            transport=transport,
            socket_dir=socket_dir,
            psql_path=psql_path,
        )

    if not host or not explicit_port:
        raise ConfigurationError("TCP requires MAK_POSTGRES_HOST and MAK_POSTGRES_PORT")
    if password_requested and not password:
        raise ConfigurationError("MAK_POSTGRES_PASSWORD cannot be empty when requested")
    return PostgresConfig(
        database=database,
        user=user,
        transport=transport,
        socket_dir=socket_dir,
        host=host,
        port=explicit_port,
        password=password,
        psql_path=psql_path,
    )


def build_psql_command(config: PostgresConfig, sql: str) -> list[str]:
    """Build an argument-list-only ``psql`` command."""

    if not sql.strip():
        raise ValueError("SQL must not be empty")
    command = [config.psql_path, "-X", "-v", "ON_ERROR_STOP=1"]
    if config.transport == "unix":
        command.extend(["-h", config.socket_dir])
    else:
        if not config.host or not config.port:
            raise ConfigurationError("TCP command requires host and port")
        command.extend(["-h", config.host, "-p", config.port])
    command.extend(["-U", config.user, "-d", config.database, "-At", "-c", sql])
    return command


def _subprocess_runner(command: Sequence[str], environment: Mapping[str, str]) -> CommandResult:
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        env=dict(environment),
        shell=False,
    )
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _is_installed(config: PostgresConfig) -> bool:
    path = Path(config.psql_path)
    if path.is_absolute():
        return path.is_file()
    return shutil.which(config.psql_path) is not None


def _run_query(config: PostgresConfig, sql: str, runner: Runner) -> CommandResult:
    environment = dict(os.environ)
    if config.password is not None:
        environment["PGPASSWORD"] = config.password
    return runner(build_psql_command(config, sql), environment)


def _safe_error(result: CommandResult) -> str:
    message = (result.stderr or result.stdout).strip().splitlines()
    return message[0][:240] if message else "psql command failed"


def _parse_postgres_boolean(value: str) -> bool | None:
    """Parse canonical PostgreSQL boolean and setting spellings strictly."""

    token = value.strip().lower()
    if token in {"t", "true", "on"}:
        return True
    if token in {"f", "false", "off"}:
        return False
    return None


def health_report(
    config: PostgresConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    runner: Runner = _subprocess_runner,
) -> HealthReport:
    """Probe PostgreSQL with separate installed, online, and readiness states."""

    try:
        resolved = config or resolve_config(env)
    except ConfigurationError as exc:
        return HealthReport(False, False, False, False, False, str(exc))

    installed = _is_installed(resolved)
    if not installed:
        return HealthReport(False, False, False, False, False, "psql is not installed")

    online_result = _run_query(resolved, "SELECT 1;", runner)
    online = online_result.returncode == 0 and online_result.stdout.strip() == "1"
    if not online:
        return HealthReport(True, False, False, False, False, _safe_error(online_result))

    connection_result = _run_query(
        resolved,
        "SELECT current_database() || E'\\t' || current_user;",
        runner,
    )
    connectable = connection_result.returncode == 0 and bool(connection_result.stdout.strip())
    if not connectable:
        return HealthReport(True, True, False, False, False, _safe_error(connection_result))

    schema_sql = (
        "SELECT nspname FROM pg_namespace WHERE nspname IN ("
        + ",".join("'" + name.replace("'", "''") + "'" for name in resolved.schemas)
        + ") ORDER BY nspname;"
    )
    schema_result = _run_query(resolved, schema_sql, runner)
    found_schemas = set(schema_result.stdout.split()) if schema_result.returncode == 0 else set()
    schema_ready = schema_result.returncode == 0 and set(resolved.schemas).issubset(found_schemas)
    if not schema_ready:
        return HealthReport(
            True,
            True,
            True,
            False,
            False,
            _safe_error(schema_result) if schema_result.returncode else "required schemas are missing",
        )

    writer_result = _run_query(
        resolved,
        "SELECT pg_is_in_recovery()::text || E'\\t' || current_setting('transaction_read_only');",
        runner,
    )
    writer_details = {
        "database": resolved.database,
        "user": resolved.user,
        "transport": resolved.transport,
    }
    primary_writer = False
    writer_error: str | None = None
    if writer_result.returncode != 0:
        writer_error = _safe_error(writer_result)
    else:
        state = writer_result.stdout.strip().split()
        if len(state) != 2:
            writer_error = "invalid PostgreSQL primary-state output"
        else:
            recovery = _parse_postgres_boolean(state[0])
            read_only = _parse_postgres_boolean(state[1])
            writer_details.update(
                {
                    "pg_is_in_recovery": state[0].lower(),
                    "transaction_read_only": state[1].lower(),
                }
            )
            if recovery is None or read_only is None:
                writer_error = "invalid PostgreSQL primary-state output"
            else:
                primary_writer = recovery is False and read_only is False
                if not primary_writer:
                    writer_error = "PostgreSQL is in recovery or transaction is read-only"
    return HealthReport(
        True,
        True,
        True,
        True,
        primary_writer,
        writer_error,
        writer_details,
    )
