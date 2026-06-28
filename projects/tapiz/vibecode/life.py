"""
Motor de vida de VibeCode.

Activa un proxy ligero sobre sys.stdout para transformar la salida en tiempo real
según la potencia de generación.
"""

import sys
import threading
import time
from typing import Optional, TextIO, Any, Callable

from .power import PowerMeter
from .render import style_text


class VibeStdout:
    """
    Proxy de stdout que transforma la salida en un patrón de espacios vivo.
    El texto original se conserva (copiable) pero con estilo ANSI.
    """

    def __init__(self, original: TextIO, meter: PowerMeter, mode: str = "negative"):
        self.original = original
        self.meter = meter
        self.mode = mode
        self._lock = threading.Lock()
        self._buffer = ""
        self._closed = False

    def _flush_buffer(self):
        if self._buffer:
            p = self.meter.power()
            styled = style_text(self._buffer, p, self.mode)
            self.original.write(styled)
            self._buffer = ""

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            text = str(text)
        if not text:
            return 0

        with self._lock:
            self.meter.pulse(len(text))
            self._buffer += text

            # Escribe líneas completas para mantener fluidez visual,
            # pero acumula texto parcial para no partir palabras en medio de ANSI.
            if "\n" in text or "\r" in text:
                self._flush_buffer()
            else:
                # Si el buffer crece mucho, forzamos flush para evitar latencia visual
                if len(self._buffer) > 120:
                    self._flush_buffer()

            # Flush original para que la salida se vea en tiempo real
            self.original.flush()
            return len(text)

    def flush(self) -> None:
        with self._lock:
            self._flush_buffer()
            self.original.flush()

    def writelines(self, lines: Any) -> None:
        for line in lines:
            self.write(line)

    def isatty(self) -> bool:
        return getattr(self.original, "isatty", lambda: False)()

    def __getattr__(self, name: str) -> Any:
        # Delega cualquier otro atributo al stdout original
        return getattr(self.original, name)

    def close(self) -> None:
        # No cerramos el stdout original, solo dejamos de usar este proxy
        self._closed = True


class LifeContext:
    """Context manager para activar VibeCode durante un bloque de código."""

    def __init__(self, mode: str = "negative"):
        self.mode = mode
        self._original: Optional[TextIO] = None
        self._meter = PowerMeter()
        self._proxy: Optional[VibeStdout] = None

    def __enter__(self):
        self._original = sys.stdout
        self._proxy = VibeStdout(self._original, self._meter, self.mode)
        sys.stdout = self._proxy
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proxy:
            self._proxy.flush()
        sys.stdout = self._original
        return False

    def power(self) -> float:
        return self._meter.power()


def init(mode: str = "negative") -> LifeContext:
    """
    Activa VibeCode de forma global en sys.stdout.
    Devuelve el contexto para poder consultar potencia o desactivar.
    """
    ctx = LifeContext(mode=mode)
    ctx.__enter__()
    return ctx


def deinit(ctx: Optional[LifeContext] = None) -> None:
    """Restaura sys.stdout. Si se pasa el contexto de init(), se usa ese."""
    if ctx is not None:
        ctx.__exit__(None, None, None)
    else:
        # Fallback: intenta restaurar el stdout original si detectamos nuestro proxy
        if isinstance(sys.stdout, VibeStdout):
            sys.stdout = sys.stdout.original


def watch(mode: str = "negative") -> LifeContext:
    """Context manager: with vibecode.watch(): ..."""
    return LifeContext(mode=mode)


def life(fn: Callable) -> Callable:
    """Decorador: @vibecode.life def my_agent(): ..."""
    def wrapper(*args, **kwargs):
        with LifeContext():
            return fn(*args, **kwargs)
    return wrapper


def pulse(chars: int = 1) -> None:
    """Si hay un proxy activo, registra un pulso manual (útil para agentes personalizados)."""
    if isinstance(sys.stdout, VibeStdout):
        sys.stdout.meter.pulse(chars)
