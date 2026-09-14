# MAK dependency surface

This classification is based on the current `pyproject.toml`, root
`requirements.txt`, area contracts and import sites. It is a navigation and
installation contract; it does not install, upgrade or remove anything.

## Base runtime

The root package is the shared source of truth for the three areas:

- `matplotlib`, `pyyaml`, `Pillow`, `pydantic`, `typer`, `rich`,
  `jsonschema`, `requests`, `boto3`.
- `contracts/departments/*/requirements.txt` intentionally includes the root
  manifest instead of creating three unconstrained dependency stacks.
- All three areas are usable in offline mode when provider credentials and
  optional actions are absent.

## Optional slices

| Slice | Dependencies | Owner / gate |
|---|---|---|
| Tests and local contract checks | `pytest`, `pytest-cov`, `pyflakes` | `.[dev]`; current runtime may not have pytest |
| RD/venue rendering | `cairosvg`, Pillow, matplotlib | `.[render]`; foreground validation only |
| Desktop FLUJO app | `pywebview`, optional `pystray` | `.[web,desktop-extras]`; separate from MAK hub |
| Portfolio/static web | browser/static assets; optional `pywebview` for desktop FLUJO | no provider required to edit locally |
| Research provider scraping | Firecrawl/Tavily/Crawl4AI | optional, explicit gate; not in base requirements |
| XIO bridge | Flask in staged files | excluded from current MAK objective; no install or service |
| Packaging | PyInstaller | `.[build]`; build-time only |

## Rules

- `pip check` output from a global Windows environment is not a requirements
  file and must not be copied into this project.
- Provider clients are not base dependencies: urllib/offline corpus paths are
  the default, and live scraping requires explicit authorization.
- Blender/GPU modules belong to the EVENT render boundary, not the RD,
  Cultura or ISKVW base contracts.
- No Windows-only package is required by the current Linux hub contracts.
- A dependency may move into an area-specific extra later only after an
  import/runtime proof and a consumer list exist.
