"""Interfaz web de flujo.

- Nuevo workspace principal (HTML pro): context/flujo_hub.html + visualizadores
  Se sirve con `flujo serve` o `flujo app`.

- Editor Gradio legacy (catálogo de formatos + preview).
"""

from .hub import launch as launch_hub
