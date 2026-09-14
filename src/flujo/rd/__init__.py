"""Base de datos RD (Reduciendo Dano): proyeccion consultable de los datos
canonicos de la ONG -- reactivos (colorimetria presuntiva), packs de servicio y
suplementos.

La DB es GENERADA, no una fuente de verdad: se construye desde los archivos
canonicos (reactivos.json, plano/packs.py, contenido_suplementos_rd.json) con
`build_rd_db()`. Regenerarla nunca la desincroniza -- si cambia una fuente, se
reconstruye. data/rd.db esta gitignored (patron *.db).
"""
from __future__ import annotations

from .database import (
    DEFAULT_DB_PATH,
    build_rd_db,
    connect,
    disclaimer,
    eventos,
    lookup_familia,
    packs,
    productora,
    productoras,
    productoras_por_tipo,
    reactivos_por_familia,
    reactivos_por_reactivo,
    suplementos,
    testing_evidence_summary,
    testing_observations,
    venues,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "build_rd_db",
    "connect",
    "disclaimer",
    "eventos",
    "lookup_familia",
    "packs",
    "productora",
    "productoras",
    "productoras_por_tipo",
    "reactivos_por_familia",
    "reactivos_por_reactivo",
    "suplementos",
    "testing_evidence_summary",
    "testing_observations",
    "venues",
]
