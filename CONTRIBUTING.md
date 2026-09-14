# Contributing to FLUJO

FLUJO is an autonomous repository. Read `AGENTS.md`, `README.md` and
`STATUS.md` before changing code. Do not assume a parent checkout or import
from MAK or XIO.

## Change flow

1. Work on a short-lived topic branch from `main`.
2. Keep the change inside the FLUJO boundary. External integrations use
   `contracts/`, `schemas/`, typed JSON, `source_ref` or an API.
3. Do not add databases, WAL/SHM files, secrets, caches, private data or
   generated output.
4. Run the smallest relevant checks and `git diff --check`.
5. Merge reviewed work back to `main`; do not create permanent domain or
   checkout branches.

## Minimum verification

```bash
PYTHONPATH=src python -m compileall src/flujo
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
PYTHONPATH=src python -m flujo --help
```

Python 3.10+ is supported. Prefer typed code and deterministic, read-only
adapters for external sources.
- No `print()` inside modules: use `rich.console` or logging.
- Tests with pytest under `tests/test_<module>.py`.
- Do not commit heavy files or credentials.
- Windows uses `py` (not `python`/`python3`).

## Language

Write everything in this repo in English: code, comments, docs, commit messages,
PR titles and bodies. The one exception is anything a human reads as a product —
RD pieces and data, iskvw curation — which goes in correct Spanish **with
diacritics**. A title reading "reduciendo ano" instead of "reduciendo daño" is
not a typo, it is a defect that reaches the client.
