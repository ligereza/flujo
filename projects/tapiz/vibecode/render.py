"""
Renderizado ANSI de la salida transformada.

Convierte el texto en un patrón en negativo: el texto es gris tenue o invisible
y los espacios se iluminan proporcionalmente a la potencia de generación.
"""

from typing import List

from .ansi import BLOCKS, RESET, bg256 as ansi_bg, fg256 as ansi_fg, tokenize


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
                idx = min(length, len(BLOCKS) - 1)
                block = BLOCKS[idx] * length
                out.append(fg + bg + block + RESET)
        else:
            # Palabras en gris, apenas visibles. En descanso total, prácticamente invisibles.
            out.append(fg + part + RESET)

    return "".join(out)
