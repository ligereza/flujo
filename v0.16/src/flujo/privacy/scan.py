"""Escaneo de privacidad: detección de datos personales y sensibles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any


# Patrones de PII (Personally Identifiable Information)
PATTERNS: Dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "rut_chile": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"),
    "telefono_cl": re.compile(r"(?<!\d)(?:\+?56\s*)?(?:9\s*)?\d{4}\s*\d{4}(?!\d)"),
    "url": re.compile(r"https?://\S+|www\.\S+", re.I),
    "tarjeta": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "direccion": re.compile(r"\b(?:calle|avenida|av\.|pasaje|psje)\s+[\w\s]+\d+", re.I),
}


SENSITIVE_KEYWORDS = [
    "salud", "diagnóstico", "diagnostico", "médico", "medico", "psicológica", "psicologica",
    "consumo", "sustancias", "droga", "drogas", "menor de edad", "menores", "rut",
    "dirección", "direccion", "domicilio", "cuenta bancaria", "transferencia", "tarjeta",
    "trabajador", "trabajadora", "asistente", "voluntario", "voluntaria",
]


# Palabras que elevan el riesgo a "alto"
HIGH_RISK_KEYWORDS = {
    "salud", "diagnóstico", "diagnostico", "médico", "medico",
    "consumo", "sustancias", "droga", "drogas",
    "menor de edad", "menores",
    "psicológica", "psicologica",
}


@dataclass
class ScanResult:
    """Resultado del escaneo de privacidad."""

    source: str = ""
    matches: Dict[str, List[str]] = field(default_factory=dict)
    sensitive_keywords: List[str] = field(default_factory=list)
    total_pii: int = 0
    risk: str = "bajo"  # bajo | medio | alto
    requiere_sanitizacion: bool = False
    requiere_revision_humana: bool = False
    aprobado_para_ia_externa: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def scan_text(text: str, source: str = "") -> ScanResult:
    """Escanea el texto y devuelve un ScanResult con todos los hallazgos."""
    result = ScanResult(source=source)

    for name, pat in PATTERNS.items():
        matches = pat.findall(text)
        if matches:
            # normalizar a strings y recortar
            result.matches[name] = [str(m)[:80] for m in matches[:10]]
            result.total_pii += len(matches)

    result.sensitive_keywords = sorted({
        kw for kw in SENSITIVE_KEYWORDS if kw.lower() in text.lower()
    })

    # calcular riesgo
    if result.total_pii == 0 and not result.sensitive_keywords:
        result.risk = "bajo"
    elif any(k in HIGH_RISK_KEYWORDS for k in result.sensitive_keywords):
        result.risk = "alto"
    elif result.total_pii > 0:
        result.risk = "medio"
    else:
        # solo keywords sensibles pero no críticas
        result.risk = "medio"

    result.requiere_sanitizacion = result.total_pii > 0
    result.requiere_revision_humana = result.risk == "alto"
    result.aprobado_para_ia_externa = result.risk == "bajo"

    return result
