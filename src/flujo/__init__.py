"""flujo — Dimensiones del Orden · arte y automatización.

Paquete principal. La CLI está en `flujo.cli:main`.

Submódulos principales:
  flujo.jobs      — lifecycle de jobs creativos (borrador → ... → entregado)
  flujo.privacy   — escaneo y sanitización de PII antes de IAs externas
  flujo.render    — render de piezas vectoriales desde config.json
  flujo.dashboard — reporte diario de items pendientes
  flujo.flyer     — importación y gestión de flyers desde Instagram
  flujo.analyze   — análisis de colores y OCR
  flujo.export    — exportación ZIP para Photoshop/Illustrator
  flujo.index     — índice SQLite de flyers
  flujo.ig        — descarga de Instagram con instaloader
  flujo.intake    — parseo y pipeline de correos
  flujo.version   — versión y changelog
"""

from .version import __version__, __version_info__, get_version, get_changelog

def _load_dotenv():
    import os
    from pathlib import Path
    p = Path(__file__).resolve().parent
    for _ in range(5):
        env_path = p / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")
            break
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            break
        p = p.parent

_load_dotenv()

__all__ = ["__version__", "__version_info__", "get_version", "get_changelog"]
