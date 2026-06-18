"""Módulo de privacidad para textos antes de usar con IAs externas.

Detecta y sanitiza:
  - emails
  - RUT chileno
  - teléfonos (CL)
  - URLs
  - palabras sensibles (salud, sustancias, menores, etc.)
"""

from .scan import scan_text, ScanResult
from .sanitize import sanitize_text, REPLACEMENTS
from .report import write_report

__all__ = [
    "scan_text",
    "ScanResult",
    "sanitize_text",
    "REPLACEMENTS",
    "write_report",
]
