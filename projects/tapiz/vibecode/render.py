"""
Renderizado ANSI de la salida transformada.

Convierte el texto en un patrón en negativo: el texto es gris tenue o invisible
y los espacios se iluminan proporcionalmente a la potencia de generación.
"""

import re
from typing import List, Tuple


RESET = "\033[0m"


def ansi_fg(n: int) -> str:
    return f"\033[38;5;{n}m"


def ansi_bg(n: int) -> str:
    return f"\033[48;5;{n}m"


def tokenize(text: str) -> List[Tuple[str, str]]:
    """Divide el texto en tokens ('space' o 'word') conservando espacios."""
    parts = re.split(r"(\s+)", text)
    tokens = []
    for part in parts:
        if not part:
            continue
        tokens.append(("space" if part.isspace() else "word", part))
    return tokens


def style_text(text: str, power: float, mode: str = "negative") -> str:
    """
    Aplica estilo ANSI al texto según la potencia.

    Args:
        text: texto de salida (código).
        power: potencia de actividad entre 0.0 y 1.0.
        mode: 'negative' ilumina el fondo de los espacios; 'blocks' usa densidad.
    """
    if not text:
        return text

    tokens = tokenize(text)
    out: List[str] = []

    # Intensidad del espacio: de negro (0) a blanco grisáceo (23 en escala 232-255)
    bg_shade = int(232 + power * 22)
    # Texto: de muy gris (245) a un poco más visible (251) según la potencia
    fg_shade = int(238 + power * 10)

    fg = ansi_fg(fg_shade)
    bg = ansi_bg(bg_shade)
    blocks = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    for kind, part in tokens:
        if kind == "space":
            if mode == "negative":
                # Fondo iluminado, carácter invisible (espacio real)
                if power < 0.05:
                    # Descanso: espacios casi invisibles
                    out.append(ansi_bg(232) + part + RESET)
                else:
                    out.append(bg + part + RESET)
            else:  # blocks
                length = len(part)
                idx = min(length, len(blocks) - 1)
                block = blocks[idx] * length
                out.append(fg + bg + block + RESET)
        else:
            # Palabras en gris, apenas visibles. En descanso total, prácticamente invisibles.
            out.append(fg + part + RESET)

    return "".join(out)
