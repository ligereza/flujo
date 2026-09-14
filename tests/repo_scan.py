"""One enumerator for every gate that guards what is about to enter the repo.

A ratchet that protects against a datum entering has to look at what is
entering. Enumerating with plain ``git ls-files`` sees only TRACKED files, so a
brand-new file passes the local gate unseen and fails once it is already
committed -- with the thing the gate exists to stop already in history.

That gap was measured twice on this repository, from opposite directions:

- ``tests/test_higiene_docs.py`` carried it in its own docstring: "cuatro README
  vendorizados pasaron el pytest local y tumbaron el CI", resolved with a manual
  workaround ("git add first"). A workaround that lives in a person's memory
  fails again.
- ``tests/test_privacidad_repo.py`` hit it on 2026-08-21 when a new test file
  carried a real Windows username through the local gate.

``tools/idioma.py`` already did the right thing, which is why the language
ratchet caught its violations immediately while the other two did not. This
module makes that behaviour the shared default instead of a per-file accident.

Not every gate wants this. ``test_higiene_repo.py`` asserts that user-editable
config IS tracked, so including untracked files there would defeat its purpose.
The rule is: a gate that asks "is this already committed?" uses ``git ls-files``;
a gate that asks "may this enter?" uses ``versionable_files()``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def versionable_files(patterns: tuple[str, ...] = (), *,
                      repo: Path | None = None) -> list[str]:
    """Tracked files plus new ones that .gitignore does not exclude.

    ``patterns`` are git pathspecs such as ``("*.md",)``. Order is stable and
    duplicates are removed, so a caller can rely on the result as a set or a
    sequence. Returns an empty list when git is unavailable, which lets a caller
    skip rather than silently pass.
    """
    root = repo or REPO
    seen: list[str] = []
    for extra in ([], ["--others", "--exclude-standard"]):
        command = ["git", "ls-files", *extra]
        if patterns:
            command += ["--", *patterns]
        result = subprocess.run(command, cwd=root, capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            return []
        seen.extend(line for line in result.stdout.split("\n") if line)
    return list(dict.fromkeys(seen))
