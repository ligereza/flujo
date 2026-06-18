"""Información de versión de flujo."""

__version__ = "0.16.0"
__version_info__ = (0, 16, 0)

# Changelog resumido por versión
CHANGELOG = {
    "0.16.0": {
        "fecha": "2026-06-17",
        "titulo": "CLI Completo + Pipeline Unificado",
        "highlights": [
            "CLI flujo ampliada con 20+ subcomandos (jobs, privacy, render, dashboard)",
            "Módulos nuevos: flujo.jobs, flujo.privacy, flujo.render, flujo.dashboard",
            "Modelos Pydantic para Brief y Job con estados bien definidos",
            "Tests unitarios e integración para los módulos nuevos",
            "Documentación: docs/CLI.md, docs/JOB_PIPELINE.md, RELEASE_v016.md",
        ],
    },
    "0.15.0": {
        "fecha": "2026-06-17",
        "titulo": "Intake Inteligente + Track M + Airdrop Profesional",
        "highlights": [
            "Intake de correos con detección de links de Instagram",
            "Track M: scripts JSX para Photoshop e Illustrator que leen palette.json",
            "Sistema de airdrop profesional (apply_airdrop.sh + finish_airdrop.sh)",
            "Limpieza estructural del repo",
        ],
    },
    "0.14.0": {
        "fecha": "2026-06-16",
        "titulo": "Análisis + Index + Export",
        "highlights": [
            "Análisis automático de colores y OCR",
            "Index SQLite de flyers",
            "Export ZIP listo para Photoshop/Illustrator",
        ],
    },
}


def get_version() -> str:
    """Devuelve la versión actual como string."""
    return __version__


def get_changelog() -> dict:
    """Devuelve el changelog completo."""
    return CHANGELOG


def get_latest_changes() -> list[str]:
    """Devuelve los highlights de la última versión."""
    return CHANGELOG.get(__version__, {}).get("highlights", [])
