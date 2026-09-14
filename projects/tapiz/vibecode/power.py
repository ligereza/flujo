"""
Medidor de potencia de generación.

Calcula cuán intensa es la actividad de salida en un ventana de tiempo reciente.
La potencia va de 0.0 (descanso) a 1.0 (máxima actividad).
"""

import time
from collections import deque
from typing import Deque, Tuple


class PowerMeter:
    """
    Mide la potencia de generación basándose en caracteres por segundo.
    No consume tokens: solo cuenta y mide tiempos.
    """

    def __init__(self, window: float = 1.0, threshold: int = 400):
        """
        Args:
            window: segundos de ventana de medición.
            threshold: caracteres por segundo que equivalen a potencia 1.0.
        """
        self.window = window
        self.threshold = max(1, threshold)
        self._events: Deque[Tuple[float, int]] = deque()
        self._last_pulse = 0.0

    def pulse(self, chars: int = 1):
        """Registra un pulso de actividad de `chars` caracteres."""
        now = time.monotonic()
        self._events.append((now, max(0, chars)))
        self._last_pulse = now

    def power(self) -> float:
        """Devuelve la potencia actual entre 0.0 y 1.0."""
        now = time.monotonic()
        cutoff = now - self.window

        # Elimina eventos antiguos
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

        total_chars = sum(n for _, n in self._events)
        rate = total_chars / self.window
        p = min(1.0, rate / self.threshold)

        # Si no ha habido pulso reciente, decae suavemente
        idle = now - self._last_pulse
        if idle > 0.3:
            decay = max(0.0, 1.0 - (idle - 0.3) / 1.5)
            p *= decay

        return p

    def is_resting(self) -> bool:
        """True si lleva más de 1.5 segundos sin actividad."""
        return time.monotonic() - self._last_pulse > 1.5
