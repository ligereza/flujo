"""Módulo de render: piezas vectoriales desde config.json."""

from .piezas import (
    create_project_from_brief,
    render_config,
    validate_config,
    list_projects,
)
from .formats import (
    load_index,
    list_formats,
    suggest_format,
    FormatInfo,
)

__all__ = [
    "create_project_from_brief",
    "render_config",
    "validate_config",
    "list_projects",
    "load_index",
    "list_formats",
    "suggest_format",
    "FormatInfo",
]
