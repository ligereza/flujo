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

__all__ = ["__version__", "__version_info__", "get_version", "get_changelog"]
