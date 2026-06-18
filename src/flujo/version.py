"""Versión y changelog de flujo."""
__version__ = "0.24.1"
VERSION = __version__
__version_info__ = (0, 24, 1)
def get_version(): return __version__
def get_changelog():
    return {
        "0.24.1": {"titulo": "Fix Airdrop rutas Windows", "fecha": "2026-06-18", "highlights": ["scan_airdrop() usa rel.as_posix() => rutas con '/' consistentes en Windows y Linux/macOS", "Corrige test_airdrop que fallaba solo en Windows por backslashes"]},
        "0.24.0": {"titulo": "Fix Airdrop CLI", "fecha": "2026-06-18", "highlights": ["Reparados los comandos flujo airdrop (list/dry-run/apply) que estaban rotos por desincronización cli.py↔airdrop.py", "Versión centralizada y sincronizada (pyproject + version.py + --help)", "Tests de regresión del airdrop (tests/test_airdrop.py)"]},
        "0.23.0": {"titulo": "Airdrop Status Command", "fecha": "2026-06-18", "highlights": ["Añadido flujo airdrop status", "Sincronización de versión global"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Sistema de Airdrop automatizado", "Auto-checkpoint + Push"]}
    }
