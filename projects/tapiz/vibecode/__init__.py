"""
VibeCode — Librería de acompañamiento visual para la generación de código.

Como Colorama, se instala y se activa con una llamada ligera. A partir de ahí,
la salida del código toma vida: los espacios se iluminan, el texto respira,
y la intensidad es proporcional a la velocidad de generación.

Cuando la IA descansa, la visualización también descansa.

Uso básico:
    import vibecode
    vibecode.init()

    # ... aquí el agente o la IA generan código ...

    vibecode.deinit()

Uso como context manager:
    with vibecode.watch():
        agent.run()

Uso como decorador:
    @vibecode.life
    def my_agent(prompt):
        ...
"""

from .life import init, deinit, watch, life, pulse

__all__ = ["init", "deinit", "watch", "life", "pulse"]
__version__ = "0.1.0"
