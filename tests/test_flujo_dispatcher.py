"""Tests for scripts/flujo.py dispatcher error handling."""
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repo root directory."""
    return Path(__file__).resolve().parents[1]


def test_retired_command_exits_2_with_stderr():
    """Test that invoking a retired command exits 2 and mentions the command name."""
    repo_root = get_repo_root()
    result = subprocess.run(
        [sys.executable, "scripts/flujo.py", "job-from-text"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    assert result.returncode == 2, f"Expected exit code 2, got {result.returncode}"
    assert "job-from-text" in result.stderr, f"Expected 'job-from-text' in stderr, got: {result.stderr}"
    assert "retirado" in result.stderr.lower(), f"Expected 'retirado' in stderr, got: {result.stderr}"


def test_unknown_command_exits_2():
    """Test that invoking an unknown command exits 2."""
    repo_root = get_repo_root()
    result = subprocess.run(
        [sys.executable, "scripts/flujo.py", "nonexistent-command"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    assert result.returncode == 2, f"Expected exit code 2, got {result.returncode}"
    assert "nonexistent-command" in result.stderr, f"Expected 'nonexistent-command' in stderr, got: {result.stderr}"


def test_no_args_shows_usage():
    """Test that no arguments shows usage (not a traceback)."""
    repo_root = get_repo_root()
    result = subprocess.run(
        [sys.executable, "scripts/flujo.py"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should exit 1 for usage/help
    assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"
    # Should not have a traceback
    assert "Traceback" not in result.stderr, f"Unexpected traceback in output: {result.stderr}"
    assert "Traceback" not in result.stdout, f"Unexpected traceback in output: {result.stdout}"
    # Should show usage info
    assert "Comandos disponibles" in result.stdout, f"Expected usage message in stdout, got: {result.stdout}"


def test_working_command_still_available():
    """Test that a working command (health) is still available and listed."""
    repo_root = get_repo_root()
    result = subprocess.run(
        [sys.executable, "scripts/flujo.py"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should show usage with available commands
    assert "health" in result.stdout, f"Expected 'health' in available commands, got: {result.stdout}"
    assert "daily" in result.stdout, f"Expected 'daily' in available commands, got: {result.stdout}"
    # Antes se exigia tambien "app", que en este despachador venia de
    # scripts/app.py -- la interfaz Gradio vieja, archivada el 2026-07-26 por
    # estar rota. La entrada real a la app es `py -m flujo app`, no este
    # despachador, y este test dice en su propio docstring que verifica un
    # comando que FUNCIONA. Exigir uno muerto era lo contrario.


def test_retired_command_not_in_available_list():
    """Test that retired commands are not shown in available commands."""
    repo_root = get_repo_root()
    # Call with a retired command
    result = subprocess.run(
        [sys.executable, "scripts/flujo.py", "job-from-text"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Check the list of available commands in stderr
    assert "Comandos disponibles" in result.stderr, f"Expected 'Comandos disponibles' in stderr, got: {result.stderr}"
    # Should not include the retired command in the available list
    lines = result.stderr.split("\n")
    available_section_start = next(i for i, line in enumerate(lines) if "Comandos disponibles" in line)
    available_commands = []
    for line in lines[available_section_start + 1:]:
        line = line.strip()
        if line and not line.startswith("ERROR"):
            available_commands.append(line)

    available_str = " ".join(available_commands)
    assert "job-from-text" not in available_str, f"job-from-text should not be in available commands: {available_str}"
