#!/usr/bin/env python3
"""Map the test suite by the commit that added each file. Read-only.

The purpose of a test is already written down, in the message of the commit
that introduced it. Reading 350 test files to infer what they cover is the
expensive way; reading the ~164 commit subjects that added them is the cheap
way, and it also gives WHEN and IN WHAT COMPANY -- which the files themselves
do not.

That company is the whole point. Test files added in the same commit are one
design decision, taken once. A file that lands alone, weeks later, in an area
that already had tests is accretion: somebody saw a gap and filled it without
reading what was already there. Accretion is where the same property gets
verified twice, so this reports the two shapes separately instead of counting
tests, which says nothing.

Usage:
    python3 tools/medir_tests.py              # areas that grew across commits
    python3 tools/medir_tests.py --cronologia # every commit, oldest first

Reading the output: an area with many commits is a QUESTION, not a verdict.
`ig` grew over five separate dates and is not redundant at all -- each of its
subjects names a different bug (canonical URL, parth-dl, curl_cffi fallback),
so each file pins a different regression. An area whose subjects are broad
("consolidate", "publish", "establish") is the one worth opening.

It changes nothing. It runs one `git log` and reads no test file except to
count `def test_` lines.

The output is Spanish because a person reads it; identifiers and comments are
English because tests/test_idioma_ratchet.py enforces that for new code.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"
# tokens that carry no subject: every file is a test, and half of MAK is "mak"
STOP = {"mak", "test"}


def additions() -> dict[str, tuple[str, str, str]]:
    """Oldest add per test path, as (date, sha, subject).

    `git log` is newest-first, so a later assignment overwrites a newer add
    with an older one. That matters for files deleted and restored: what we
    want is when the idea first appeared, not when it came back.
    """
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--name-only", "--date=short",
         "--format=@@@%ad|%h|%s", "--", "tests/"],
        cwd=REPO, capture_output=True, text=True, timeout=180, check=False).stdout
    birth: dict[str, tuple[str, str, str]] = {}
    current: tuple[str, str, str] | None = None
    for line in out.splitlines():
        if line.startswith("@@@"):
            date, sha, subject = line[3:].split("|", 2)
            current = (date, sha, subject)
        elif line.strip() and current is not None:
            birth[line.strip()] = current
    return {p: c for p, c in birth.items()
            if (REPO / p).is_file() and Path(p).name.startswith("test_")}


def count_tests(path: str) -> int:
    try:
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return len(re.findall(r"^\s*def test_", text, re.M))


def subject_area(path: str) -> str:
    tokens = [t for t in Path(path).stem.split("_")[1:] if t not in STOP]
    return tokens[0] if tokens else "?"


def report_areas(birth: dict[str, tuple[str, str, str]]) -> None:
    areas: dict[str, list] = defaultdict(list)
    for path, commit in birth.items():
        areas[subject_area(path)].append((*commit, path))

    rows = []
    for name, items in areas.items():
        rows.append((len({i[1] for i in items}), len({i[0] for i in items}),
                     len(items), name, sorted(items)))

    print("AREAS QUE CRECIERON EN COMMITS SEPARADOS")
    print("  (donde una propiedad tiene mas chance de estar verificada dos veces)\n")
    for n_commits, n_dates, n_files, name, items in sorted(rows, reverse=True):
        if n_commits < 3:
            continue
        print(f"  {name}   {n_files} archivos, {n_commits} commits, {n_dates} fechas")
        for date, sha, subject, path in items:
            print(f"      {date}  {sha}  {path[6:]:44} {subject[:54]}")
        print()

    whole = [r for r in rows if r[0] == 1 and r[2] > 1]
    print(f"AREAS QUE LLEGARON ENTERAS EN UN SOLO COMMIT: {len(whole)}")
    for _, _, n_files, name, items in sorted(whole, key=lambda r: -r[2]):
        print(f"  {name}: {n_files} archivos, {items[0][0]} {items[0][1]}"
              f"  {items[0][2][:52]}")


def report_chronology(birth: dict[str, tuple[str, str, str]]) -> None:
    groups: OrderedDict = OrderedDict()
    for path, commit in sorted(birth.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        groups.setdefault(commit, []).append(path)
    for (date, sha, subject), paths in groups.items():
        total = sum(count_tests(p) for p in paths)
        plural = "s" if len(paths) > 1 else ""
        print(f"\n{date}  {sha}  ({len(paths)} archivo{plural}, {total} tests)")
        print(f"    {subject[:96]}")
        for path in sorted(paths):
            print(f"      {count_tests(path):4}  {path[6:]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mapa de la suite por el commit que agrego cada archivo.")
    parser.add_argument("--cronologia", action="store_true",
                        help="lista cada commit de alta, del mas viejo al mas nuevo")
    args = parser.parse_args()

    birth = additions()
    on_disk = len(list(TESTS.glob("test_*.py")))
    print(f"archivos de test con alta ubicada: {len(birth)} de {on_disk}")
    print(f"commits que los introdujeron: {len({c[1] for c in birth.values()})}")
    print(f"funciones test: {sum(count_tests(p) for p in birth)}\n")
    if args.cronologia:
        report_chronology(birth)
    else:
        report_areas(birth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
