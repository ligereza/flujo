"""Herramientas comerciales: briefs multiformato y cotizaciones base."""

from .multiformato import (
    FORMAT_DEFINITIONS,
    detect_requested_formats,
    is_multiformat_quote_request,
    build_package_documents,
    write_multiformat_package,
    generate_from_path,
)

__all__ = [
    "FORMAT_DEFINITIONS",
    "detect_requested_formats",
    "is_multiformat_quote_request",
    "build_package_documents",
    "write_multiformat_package",
    "generate_from_path",
]
