"""Versión y changelog de flujo."""
__version__ = "0.29.0"
VERSION = __version__
__version_info__ = (0, 29, 0)
def get_version(): return __version__
def get_changelog():
    return {
        "0.29.0": {"titulo": "Auto-checkpoint en Python puro (fix Windows/bash)", "fecha": "2026-06-18", "highlights": ["run_auto_checkpoint usa git directo, sin bash (arregla 'execvpe(/bin/bash) failed' en Windows)", "flujo airdrop apply ahora SÍ commitea y pushea solo en Windows", "Reintenta el commit si un pre-commit hook modifica archivos", "4 tests de regresión (test_airdrop_checkpoint)"]},
        "0.28.0": {"titulo": "Editor visual Gradio (src/flujo/web)", "fecha": "2026-06-18", "highlights": ["Editor propio: catálogo → editar datos/proporción → preview SVG → exportar", "Preview SVG liviano con soporte de elemento image", "flujo serve usa el editor nuevo (--legacy para el antiguo)"]},
        "0.27.0": {"titulo": "Catálogo oficial de formatos ONG (v2.0)", "fecha": "2026-06-18", "highlights": ["12 formatos con area/medio/herramienta/parametrico", "filtros en render formats"]},
        "0.26.0": {"titulo": "Render rescale + bloque modificacion", "fecha": "2026-06-18", "highlights": ["flujo render rescale (proporción/DPI)", "bloque modificacion en intake JSON"]},
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["README guía para agentes", "intake JSON + schema + ejemplos"]},
        "0.24.1": {"titulo": "Fix Airdrop rutas Windows", "fecha": "2026-06-18", "highlights": ["scan_airdrop() usa rel.as_posix()"]},
        "0.24.0": {"titulo": "Fix Airdrop CLI", "fecha": "2026-06-18", "highlights": ["Reparados los comandos flujo airdrop", "Versión centralizada"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Sistema de Airdrop automatizado", "Auto-checkpoint + Push"]}
    }
