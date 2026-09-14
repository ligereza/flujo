# Core diagnostic contract

Use this packet for repo, Git, dependency, hub, runtime or CLI incidents.

Read first: `agents.md`, `pyproject.toml`, `src/flujo/cli.py`,
`src/flujo/diagnostics.py` and the current `context/LAST_HANDOFF.md`.

Run only bounded checks declared by the report. Never execute a command copied
from an error message without reviewing it. Keep WIN, databases, credentials
and virtual environments outside the first read set.

Suggested branch: `maintenance/<short-slug>`.
