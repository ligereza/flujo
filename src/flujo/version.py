"""Versión y changelog de flujo."""
__version__ = "0.33.0"
VERSION = __version__
__version_info__ = (0, 33, 0)
def get_version(): return __version__
def get_changelog():
    return {
        "0.33.0": {"titulo": "Plano como módulo propio + costos + editor + fixes", "fecha": "2026-06-18", "highlights": ["Motor de planos migrado a src/flujo/plano/ (engine + costs)", "flujo plano ahora usa el módulo directamente (sin subprocess)", "Nuevo flag --costs en flujo plano para desglose de cotización", "Editor visual autocontenido: projects/plano/plano_editor.html", "projects/plano/plano_stands.py delega en flujo.plano", "Fix patrón de tarjeta en privacy/scan.py con validación Luhn", "Cache de repo_root() con lru_cache para mejorar rendimiento", "Nueva ruta plano_base() en paths.py", "Tests para flujo.plano y flujo plano --costs"]},
        "0.32.0": {"titulo": "Airdrop integral: limpieza, plano CLI, docs y fixes", "fecha": "2026-06-18", "highlights": ["Eliminadas carpetas temporales de Instagram commitadas por error", "Nuevo comando: flujo plano <evento.json> (generador de stands)", "Fix advertencia de deprecación Pillow 14 en analyze/colors.py", "Tests para plano_stands.py", "Sincronizadas versiones de README/PARA_IA/AGENT_GUIDE", "Script de limpieza para carpetas temp ig_*", "Fix SyntaxError en scripts/sanitize_sensitive.py", "Motor airdrop ahora permite actualizar .gitignore"]},
        "0.31.0": {"titulo": "Proyecto satélite 'plano' (generador paramétrico)", "fecha": "2026-06-18", "highlights": ["projects/plano/: planos de stands por 'constantes de realidad' (sin AutoCAD)", "Motor headless plano_stands.py: constantes + reglas operativas + layout + SVG", "Rider derivado por reglas (>4h colación, >5h alimentación, +mesa por 5 voluntarios, testeo, masivo)", "Referencia: generador radial de teatro original. Estado: por desarrollar (estilo tapiz)"]},
        "0.30.2": {"titulo": "IG: usuario en URL + descarga + paleta en el editor", "fecha": "2026-06-18", "highlights": ["Detecta instagram.com/<usuario>/p/CODE/", "descarga + paleta en pestaña INSTAGRAM"]},
        "0.30.1": {"titulo": "Fixes editor: IG sin esquema, preview responsive, orientación", "fecha": "2026-06-18", "highlights": ["IG sin https://", "preview responsive", "formatos verticales correctos"]},
        "0.30.0": {"titulo": "Auto-fit de texto + avisos IG + acuse de recibo", "fecha": "2026-06-18", "highlights": ["Auto-fit de texto", "pestañas INSTAGRAM y ACUSE"]},
        "0.29.0": {"titulo": "Auto-checkpoint en Python puro (fix Windows/bash)", "fecha": "2026-06-18", "highlights": ["run_auto_checkpoint sin bash"]},
        "0.28.0": {"titulo": "Editor visual Gradio (src/flujo/web)", "fecha": "2026-06-18", "highlights": ["Editor catálogo → preview SVG → exportar"]},
        "0.27.0": {"titulo": "Catálogo oficial de formatos ONG (v2.0)", "fecha": "2026-06-18", "highlights": ["12 formatos area/medio/herramienta"]},
        "0.26.0": {"titulo": "Render rescale + bloque modificacion", "fecha": "2026-06-18", "highlights": ["render rescale proporción/DPI"]},
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["intake JSON + schema"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Airdrop automatizado + push"]}
    }
