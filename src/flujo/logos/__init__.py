"""Vectorizacion de logos: raster -> SVG limpio, con fondo transparente.

Entrada: el logo como venga (png/jpg/webp, con o sin alpha).
Salida: un SVG sin rectangulo de fondo, listo para meter en un rider, un plano
o la web sin recortar nada a mano.

Ver `vectorizar.py` para el detalle de por que cada paso existe.
"""

from .vectorizar import ResultadoVector, vectorizar, vectorizar_lote

__all__ = ["vectorizar", "vectorizar_lote", "ResultadoVector"]
