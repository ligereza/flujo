"""Versión y changelog de flujo."""
__version__ = "0.26.0"
VERSION = __version__
__version_info__ = (0, 26, 0)
def get_version(): return __version__
def get_changelog():
    return {
        "0.26.0": {"titulo": "Render rescale + bloque modificacion", "fecha": "2026-06-18", "highlights": ["Nuevo 'flujo render rescale': cambia proporción (medida cm) o resolución (DPI) de un config.json", "Distingue pixelado (DPI) de cambio de proporción; reescala elementos opcionalmente", "Bloque 'modificacion' en el intake JSON para pedidos de cambio sobre piezas existentes", "17 tests nuevos (test_render_rescale)"]},
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["README guía definitiva para agentes", "Especificación de intake por JSON + JSON Schema + ejemplos"]},
        "0.24.1": {"titulo": "Fix Airdrop rutas Windows", "fecha": "2026-06-18", "highlights": ["scan_airdrop() usa rel.as_posix()"]},
        "0.24.0": {"titulo": "Fix Airdrop CLI", "fecha": "2026-06-18", "highlights": ["Reparados los comandos flujo airdrop", "Versión centralizada", "Tests de regresión"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Sistema de Airdrop automatizado", "Auto-checkpoint + Push"]}
    }
