# Dependency contract

`pyproject.toml` is the only dependency source of truth for the repository.
The optional groups are the portable contracts:

- `.` — runtime/core tools;
- `.[dev]` — tests and development checks;
- `.[render]` — raster and perceptual SVG checks;
- `.[web]` — optional desktop webview;
- `.[desktop-extras]` — optional tray support;
- `.[build]` — optional packaging.

## Branch rule

A topic branch that needs a package changes `pyproject.toml` in the same
commit as the code and updates its branch contract and handoff. It must not
invent a branch-only virtual environment or a second untracked dependency
list. The focused install command is recorded in the branch contract.

## Recommended installs

```bash
python -m pip install -e ".[dev,render]"
python -m pytest tests/ -q
```

`requirements.txt` and `requirements-dev.txt` remain only as compatibility
inputs for older consumers. CI, setup and security checks must install from
`pyproject.toml`; changes to the compatibility files alone do not define a
working branch.

No dependency install starts a service, processes jobs or calls an external
provider. Runtime credentials remain outside the repository.
