#!/usr/bin/env python3
"""Report env vars read outside src/flujo that MAPA.md does not document.

`tests/test_mapa_completo.py::test_toda_variable_de_entorno_esta_documentada`
scanned only `src/flujo`, so every variable read in `cultura/` or `tools/` --
where the Hub, Research and Codex actually live -- escaped the documentation
rule. Widening the scan found 82 at once, and a gate that cannot pass gets
disabled instead of obeyed, so the wider zones are held by a pin that may only
shrink.

    python3 tools/env_baseline.py            # report the current gap
    python3 tools/env_baseline.py --write    # rewrite the pin deliberately
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "tests" / "fixtures" / "env_documentado_baseline.txt"
WIDER_ZONES = ("cultura", "tools")

# Same shape the map gate uses: os.environ.get("X") / os.environ["X"] / getenv.
ENV_READ = re.compile(
    r"""os\.environ(?:\.get\(|\[)\s*["']([A-Z][A-Z0-9_]+)["']"""
    r"""|os\.getenv\(\s*["']([A-Z][A-Z0-9_]+)["']""")

# Set by the OS or by a runner, never something a person configures for MAK.
NOT_CONFIGURABLE = {
    "PATH", "HOME", "USER", "PWD", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL",
    "PYTHONPATH", "VIRTUAL_ENV", "CI", "GITHUB_ACTIONS", "GITHUB_TOKEN",
    "GITHUB_REPOSITORY", "GITHUB_WORKSPACE", "RUNNER_OS", "SHELL", "TERM",
    "DISPLAY", "XDG_RUNTIME_DIR", "SYSTEMROOT", "APPDATA", "LOCALAPPDATA",
    "USERPROFILE", "COMSPEC", "OS", "PROCESSOR_ARCHITECTURE",
}


def read_pin() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return {
        line.strip()
        for line in BASELINE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def scan(zones: tuple[str, ...] = WIDER_ZONES) -> set[str]:
    found: set[str] = set()
    for zone in zones:
        root = REPO / zone
        if not root.is_dir():
            continue
        for source in root.rglob("*.py"):
            try:
                text = source.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for first, second in ENV_READ.findall(text):
                found.add(first or second)
    return {name for name in found if name not in NOT_CONFIGURABLE}


def undocumented() -> list[str]:
    mapa = (REPO / "MAPA.md").read_text(encoding="utf-8")
    return sorted(name for name in scan() if name not in mapa)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="rewrite the pin with the current gap")
    args = parser.parse_args(argv)

    current = undocumented()
    pinned = read_pin()
    nuevos = sorted(set(current) - pinned)
    resueltos = sorted(pinned - set(current))

    print(f"env vars read in {'/'.join(WIDER_ZONES)} and undocumented: {len(current)}")
    print(f"pinned: {len(pinned)}  new: {len(nuevos)}  documented since the pin: {len(resueltos)}")
    if nuevos:
        print("NEW (document in MAPA.md section 4):")
        for name in nuevos:
            print(f"  {name}")
    if resueltos:
        print("documented since the pin (lower it by deleting these lines):")
        for name in resueltos:
            print(f"  {name}")

    if args.write:
        header = BASELINE.read_text(encoding="utf-8").split("\n")
        comments = [line for line in header if line.lstrip().startswith("#")]
        BASELINE.write_text("\n".join(comments) + "\n" + "\n".join(current) + "\n",
                            encoding="utf-8")
        print(f"pin rewritten: {len(current)} entries")
        return 0
    return 1 if nuevos else 0


if __name__ == "__main__":
    raise SystemExit(main())
