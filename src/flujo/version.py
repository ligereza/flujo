"""Versión y changelog de flujo."""
__version__ = "0.28.0"
VERSION = __version__
__version_info__ = (0, 28, 0)
def get_version(): return __version__
def get_changelog():
    return {
        "0.28.0": {"titulo": "Editor visual Gradio (src/flujo/web)", "fecha": "2026-06-18", "highlights": ["Editor propio en src/flujo/web/: catálogo filtrable → editar datos/proporción → preview SVG → exportar", "Preview SVG liviano sin dependencias (web/svg_preview.py) con soporte de elemento image", "flujo serve usa el editor nuevo (--legacy para el antiguo); --port/--host", "Reusa render.rescale para proporción/DPI; 17 tests nuevos (lógica pura)"]},
        "0.27.0": {"titulo": "Catálogo oficial de formatos ONG (v2.0)", "fecha": "2026-06-18", "highlights": ["12 formatos con area/medio/herramienta/parametrico", "filtros en render formats", "Eventos/Suplementos"]},
        "0.26.0": {"titulo": "Render rescale + bloque modificacion", "fecha": "2026-06-18", "highlights": ["flujo render rescale (proporción/DPI)", "bloque modificacion en intake JSON"]},
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["README guía para agentes", "intake JSON + schema + ejemplos"]},
        "0.24.1": {"titulo": "Fix Airdrop rutas Windows", "fecha": "2026-06-18", "highlights": ["scan_airdrop() usa rel.as_posix()"]},
        "0.24.0": {"titulo": "Fix Airdrop CLI", "fecha": "2026-06-18", "highlights": ["Reparados los comandos flujo airdrop", "Versión centralizada", "Tests de regresión"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Sistema de Airdrop automatizado", "Auto-checkpoint + Push"]}
    }
