"""Versión y changelog de flujo."""
__version__ = "0.25.0"
VERSION = __version__
__version_info__ = (0, 25, 0)
def get_version(): return __version__
def get_changelog():
    return {
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["README reescrito como guía definitiva para agentes (airdrops, pipeline, formatos, app)", "Especificación de intake por JSON para colegas (docs/INTAKE_JSON.md)", "JSON Schema validable (schemas/intake.schema.json) + ejemplos por formato", "Catálogo de formatos documentado y plan de recepción automática"]},
        "0.24.1": {"titulo": "Fix Airdrop rutas Windows", "fecha": "2026-06-18", "highlights": ["scan_airdrop() usa rel.as_posix() => rutas con '/' consistentes en Windows y Linux/macOS"]},
        "0.24.0": {"titulo": "Fix Airdrop CLI", "fecha": "2026-06-18", "highlights": ["Reparados los comandos flujo airdrop (list/dry-run/apply)", "Versión centralizada y sincronizada", "Tests de regresión del airdrop"]},
        "0.23.0": {"titulo": "Airdrop Status Command", "fecha": "2026-06-18", "highlights": ["Añadido flujo airdrop status"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Sistema de Airdrop automatizado", "Auto-checkpoint + Push"]}
    }
