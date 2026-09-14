"""
Primitivas ANSI compartidas de VibeCode.

Unica fuente de: codigos de control, colores 256, escala de grises,
caracteres de bloque y tokenizacion espacio/palabra. Antes estas piezas
estaban duplicadas en render.py, vibecode_spaces.py y vibecode_void.py.
"""

import re
from typing import List, Tuple

RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_SCREEN = "\033[2J\033[H"

# Texto invisible: mismo color que el fondo del terminal (negro aprox)
TEXT_INVISIBLE = "\033[38;5;232m"
# Texto fantasma tenue
TEXT_GHOST = "\033[38;5;240m"

# Caracteres de densidad para el modo blocks
BLOCKS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def fg256(n: int) -> str:
    """Color de texto ANSI 256."""
    return f"\033[38;5;{n}m"


def bg256(n: int) -> str:
    """Color de fondo ANSI 256."""
    return f"\033[48;5;{n}m"


def fg_gray(n: int) -> str:
    """Color de texto gris en escala 0 (negro) a 23 (blanco)."""
    n = max(0, min(n, 23))
    return fg256(232 + n)


def bg_gray(n: int) -> str:
    """Color de fondo gris en escala 0 (negro) a 23 (blanco)."""
    n = max(0, min(n, 23))
    return bg256(232 + n)


_WS = re.compile(r"(\s+)")


def tokenize(text: str) -> List[Tuple[str, str]]:
    """Divide el texto en tokens ('space' | 'word', texto) conservando espacios."""
    tokens = []
    for part in _WS.split(text):
        if not part:
            continue
        tokens.append(("space" if part.isspace() else "word", part))
    return tokens
