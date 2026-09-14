from __future__ import annotations

from pathlib import Path

import pytest

from flujo.knowledge.postgres_runtime import (
    CommandResult,
    ConfigurationError,
    PostgresConfig,
    build_psql_command,
    health_report,
    resolve_config,
)


def test_default_contract_is_unix_socket_first() -> None:
    config = resolve_config({})

    assert config.database == "mak_knowledge"
    assert config.user == "mak"
    assert config.transport == "unix"
    assert config.socket_dir == "/var/run/postgresql"
    assert config.password is None

    command = build_psql_command(config, "SELECT 1;")
    assert command[:6] == ["/usr/bin/psql", "-X", "-v", "ON_ERROR_STOP=1", "-h", "/var/run/postgresql"]
    assert "-d" in command and "mak_knowledge" in command


def test_explicit_tcp_override_requires_complete_host_and_port() -> None:
    config = resolve_config(
        {
            "MAK_POSTGRES_TRANSPORT": "tcp",
            "MAK_POSTGRES_HOST": "127.0.0.1",
            "MAK_POSTGRES_PORT": "5432",
            "MAK_POSTGRES_USER": "runtime_user",
        }
    )

    command = build_psql_command(config, "SELECT 1;")
    assert ["-h", "127.0.0.1", "-p", "5432"] == command[4:8]
    assert "runtime_user" in command

    with pytest.raises(ConfigurationError, match="HOST and MAK_POSTGRES_PORT"):
        resolve_config({"MAK_POSTGRES_TRANSPORT": "tcp", "MAK_POSTGRES_HOST": "127.0.0.1"})


def test_password_is_rejected_on_unix_socket_and_never_enters_arguments() -> None:
    with pytest.raises(ConfigurationError, match="password authentication"):
        resolve_config({"MAK_POSTGRES_PASSWORD": "secret"})
    with pytest.raises(ConfigurationError, match="password authentication"):
        resolve_config({"MAK_POSTGRES_PASSWORD": ""})

    config = resolve_config(
        {
            "MAK_POSTGRES_TRANSPORT": "tcp",
            "MAK_POSTGRES_HOST": "127.0.0.1",
            "MAK_POSTGRES_PORT": "5432",
            "MAK_POSTGRES_PASSWORD": "secret",
        }
    )
    command = build_psql_command(config, "SELECT 1;")
    assert "secret" not in command


def test_password_is_available_only_to_injected_runner_environment(tmp_path: Path) -> None:
    fake_psql = tmp_path / "psql"
    fake_psql.write_text("", encoding="ascii")
    config = resolve_config(
        {
            "MAK_POSTGRES_TRANSPORT": "tcp",
            "MAK_POSTGRES_HOST": "127.0.0.1",
            "MAK_POSTGRES_PORT": "5432",
            "MAK_POSTGRES_PASSWORD": "secret",
            "MAK_POSTGRES_PSQL": str(fake_psql),
        }
    )
    captured: list[tuple[list[str], dict[str, str]]] = []

    def runner(command: list[str], environment: dict[str, str]) -> CommandResult:
        captured.append((command, environment))
        return CommandResult(2, "", "authentication failed")

    health_report(config, runner=runner)

    assert captured
    assert all("secret" not in argument for argument in captured[0][0])
    assert captured[0][1]["PGPASSWORD"] == "secret"


def test_health_report_uses_injected_runner_and_distinguishes_states(tmp_path: Path) -> None:
    fake_psql = tmp_path / "psql"
    fake_psql.write_text("", encoding="ascii")
    config = PostgresConfig(psql_path=str(fake_psql))
    calls: list[tuple[list[str], dict[str, str]]] = []
    responses = iter(
        [
            CommandResult(0, "1\n"),
            CommandResult(0, "mak_knowledge" + chr(9) + "mak\n"),
            CommandResult(0, "audit\ncore\nmak\nportfolio\nproducts\nrd\nrelations\n"),
            CommandResult(0, "false" + chr(9) + "off\n"),
        ]
    )

    def runner(command: list[str], environment: dict[str, str]) -> CommandResult:
        calls.append((command, environment))
        return next(responses)

    report = health_report(config, runner=runner)

    assert report.as_dict() == {
        "installed": True,
        "online": True,
        "connectable": True,
        "schema_ready": True,
        "primary_writer": True,
        "error": None,
        "details": {
            "database": "mak_knowledge",
            "user": "mak",
            "transport": "unix",
            "pg_is_in_recovery": "false",
            "transaction_read_only": "off",
        },
    }
    assert len(calls) == 4
    assert all("secret" not in argument for command, _ in calls for argument in command)
    assert "transaction_read_only" in calls[-1][0][-1]


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("f" + chr(9) + "off\n", True),
        ("true" + chr(9) + "false\n", False),
        ("t" + chr(9) + "on\n", False),
        ("false" + chr(9) + "off\n", True),
        ("maybe" + chr(9) + "off\n", False),
    ],
)
def test_health_report_requires_primary_and_read_write_state(
    tmp_path: Path, state: str, expected: bool
) -> None:
    fake_psql = tmp_path / "psql"
    fake_psql.write_text("", encoding="ascii")
    config = PostgresConfig(psql_path=str(fake_psql), schemas=("pg_catalog",))
    responses = iter(
        [
            CommandResult(0, "1\n"),
            CommandResult(0, "mak_knowledge" + chr(9) + "mak\n"),
            CommandResult(0, "pg_catalog\n"),
            CommandResult(0, state),
        ]
    )

    report = health_report(config, runner=lambda _command, _environment: next(responses))

    assert report.primary_writer is expected


def test_health_report_is_fail_closed_when_tcp_configuration_is_incomplete() -> None:
    fake_psql = Path("C:/does-not-exist/psql")
    report = health_report(
        env={
            "MAK_POSTGRES_TRANSPORT": "tcp",
            "MAK_POSTGRES_HOST": "127.0.0.1",
            "MAK_POSTGRES_PSQL": str(fake_psql),
        }
    )

    assert report.installed is False
    assert report.online is False
    assert report.connectable is False
    assert report.schema_ready is False
    assert report.primary_writer is False
    assert report.error == "TCP requires MAK_POSTGRES_HOST and MAK_POSTGRES_PORT"


def test_health_report_does_not_claim_connectable_when_online_query_fails(tmp_path: Path) -> None:
    fake_psql = tmp_path / "psql"
    fake_psql.write_text("", encoding="ascii")
    calls: list[list[str]] = []

    def runner(command: list[str], environment: dict[str, str]) -> CommandResult:
        calls.append(command)
        return CommandResult(2, "", "socket unavailable")

    report = health_report(PostgresConfig(psql_path=str(fake_psql)), runner=runner)

    assert report.installed is True
    assert report.online is False
    assert report.connectable is False
    assert report.schema_ready is False
    assert report.primary_writer is False
    assert report.error == "socket unavailable"
    assert len(calls) == 1
