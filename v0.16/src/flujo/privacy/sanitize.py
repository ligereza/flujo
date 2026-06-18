"""Sanitización: reemplazo de datos personales por placeholders."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


# (patrón, reemplazo)
REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[EMAIL]"),
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"(?<!\d)(?:\+?56\s*)?(?:9\s*)?\d{4}\s*\d{4}(?!\d)"), "[TELEFONO]"),
    (re.compile(r"https?://\S+|www\.\S+", re.I), "[URL]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[TARJETA]"),
]


SANITIZE_HEADER = "[[SANITIZADO: revisar manualmente antes de compartir con IA externa]]\n\n"


def sanitize_text(text: str, output: Path | None = None) -> str:
    """Sanitiza el texto reemplazando PII por placeholders.

    Si se pasa `output`, también escribe el texto sanitizado a ese archivo.
    Retorna siempre el texto sanitizado como string.
    """
    out = text
    for pat, repl in REPLACEMENTS:
        out = pat.sub(repl, out)
    sanitized = SANITIZE_HEADER + out
    if output is not None:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(sanitized, encoding="utf-8")
    return sanitized
