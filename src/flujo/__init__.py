"""flujo - hub operativo de Reduciendo Dano.

Subpaquetes:
  flujo.index   indexador real del arbol de material ($FLUJO_RD_ROOT) para agentes (solo lectura)
  flujo.route   router de rutas de RD (no mueve archivos)
  flujo.serve   servidor local del hub + endpoints /api (stdlib)
  flujo.hub     utilidades del hub
"""
from .version import __version__
