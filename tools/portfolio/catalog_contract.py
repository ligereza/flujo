"""Contract loader for the curated public portfolio project catalogue.

This is deliberately separate from ``iskvw/datos/obras.json``. The project
catalogue describes public projects and their administration state; the ISKVW
file describes visual works rendered by a skin. They may be related later by
an explicit id or relation, but neither file is an implicit replacement for
the other.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CATALOG_CONTRACT = "portfolio_project_catalog"
CATALOG_VERSION = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class CatalogContractError(ValueError):
    """Raised when the curated portfolio catalogue cannot be consumed."""


def _required_text(item: dict[str, Any], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CatalogContractError(f"project[{index}] missing non-empty {field}")
    return value.strip()


def load_catalog(path: Path, *, source_label: str | None = None) -> dict[str, Any]:
    """Load and validate the curated project catalogue without modifying it."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogContractError(f"cannot read catalogue {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("proyectos"), list):
        raise CatalogContractError("catalogue must contain a proyectos list")

    seen: set[str] = set()
    projects: list[dict[str, Any]] = []
    for index, raw in enumerate(data["proyectos"]):
        if not isinstance(raw, dict):
            raise CatalogContractError(f"project[{index}] must be an object")
        item = dict(raw)
        project_id = _required_text(item, "id", index)
        if not _ID.fullmatch(project_id):
            raise CatalogContractError(
                f"project[{index}] id must be lowercase ASCII slug: {project_id!r}"
            )
        if project_id in seen:
            raise CatalogContractError(f"duplicate project id: {project_id}")
        seen.add(project_id)
        for field in ("nombre", "linea", "estado", "descripcion"):
            _required_text(item, field, index)
        tags = item.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise CatalogContractError(f"project[{index}] tags must be a string list")
        projects.append(item)

    return {
        "titulo": data.get("titulo", ""),
        "proyectos": projects,
        "contract": {
            "name": CATALOG_CONTRACT,
            "version": CATALOG_VERSION,
            "source": source_label or path.as_posix(),
            "visual_works_source": "iskvw/datos/obras.json",
        },
    }
