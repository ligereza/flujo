#!/usr/bin/env python3
"""Comando unificado para operaciones frecuentes del repo flujo."""
import subprocess
import sys
from pathlib import Path

from _common import repo_root

ROOT = repo_root()
PY = sys.executable


COMMANDS = {
    "health": ([PY, str(ROOT / "scripts" / "flujo_health.py")], []),
    "clean": (["bash", str(ROOT / "scripts" / "limpiar_basura.sh")], []),
    "job-from-text": ([PY, str(ROOT / "scripts" / "job_from_text.py")], ["name", "email_path"]),
    "job prepare": ([PY, str(ROOT / "scripts" / "job_prepare.py")], ["job_path"]),
    "job-next": ([PY, str(ROOT / "scripts" / "job_next_actions.py")], []),
    "brief-to-project": ([PY, str(ROOT / "scripts" / "brief_to_project.py")], ["brief_path"]),
    "render": ([PY, str(ROOT / "scripts" / "project_render.py")], ["config_path"]),
    "job activate": ([PY, str(ROOT / "scripts" / "job_activate.py")], ["job_path"]),
    "privacy": ([PY, str(ROOT / "scripts" / "privacy_check_job.py")], ["job_path"]),
    "formatos": ([PY, str(ROOT / "scripts" / "piezas_formatos.py")], []),
    "validate": ([PY, str(ROOT / "scripts" / "piezas_validate_config.py")], []),
    "summary": ([PY, str(ROOT / "scripts" / "piezas_project_summary.py")], []),
    "components": ([PY, str(ROOT / "scripts" / "piezas_components.py")], []),
    "inspect": ([PY, str(ROOT / "scripts" / "project_inspect.py")], ["project_path"]),
    "backlog": ([PY, str(ROOT / "scripts" / "backlog_list.py")], []),
    "rider-presets": ([PY, str(ROOT / "scripts" / "rider_presets.py")], []),
    "rider-new": ([PY, str(ROOT / "scripts" / "rider_new.py")], ["name"]),
    "new-flyer": ([PY, str(ROOT / "scripts" / "flyer_create_project.py")], ["name"]),
    "daily": ([PY, str(ROOT / "scripts" / "flujo_daily.py")], []),
    "pipeline": ([PY, str(ROOT / "scripts" / "flujo_pipeline.py")], ["name", "email_path"]),
    "app": ([PY, str(ROOT / "scripts" / "app.py")], []),
}


def get_available_commands():
    """Return only commands whose script files exist."""
    available = {}
    for cmd, (base_cmd, args) in COMMANDS.items():
        # Extract script file path from base_cmd
        script_file = None
        for part in base_cmd:
            if part.endswith('.py') or part.endswith('.sh'):
                script_file = part
                break

        if script_file and Path(script_file).exists():
            available[cmd] = (base_cmd, args)

    return available


def usage():
    available = get_available_commands()
    print("Uso: py scripts/flujo.py <comando> [args...]")
    print("")
    print("Comandos disponibles:")
    for cmd in sorted(available.keys()):
        _, args = available[cmd]
        arg_str = " ".join(f"<{a}>" for a in args)
        print(f"  {cmd:<18} {arg_str}")
    print("")
    print("Ejemplos:")
    print("  py scripts/flujo.py health")
    print("  py scripts/flujo.py new-flyer \"fiesta techno\"")


def print_error_missing_command(cmd):
    """Print error for a retired/missing command to stderr."""
    available = get_available_commands()
    sys.stderr.write(f"ERROR: comando '{cmd}' fue retirado\n")
    sys.stderr.write("Sugerencia: ejecuta 'py -m flujo --help'\n")
    sys.stderr.write("Comandos disponibles:\n")
    for acmd in sorted(available.keys()):
        sys.stderr.write(f"  {acmd}\n")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print_error_missing_command(cmd)
        sys.exit(2)

    base_cmd, expected = COMMANDS[cmd]

    # Check if the script file exists
    script_file = None
    for part in base_cmd:
        if part.endswith('.py') or part.endswith('.sh'):
            script_file = part
            break

    if script_file and not Path(script_file).exists():
        print_error_missing_command(cmd)
        sys.exit(2)

    if len(args) < len(expected):
        print(f"ERROR: el comando '{cmd}' requiere {len(expected)} argumentos: {expected}")
        usage()
        sys.exit(1)

    full_cmd = base_cmd + args
    print("$", " ".join(full_cmd))
    try:
        subprocess.run(full_cmd, check=True, cwd=ROOT)
    except subprocess.CalledProcessError as e:
        print(f"\nError ejecutando '{cmd}': returncode {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
