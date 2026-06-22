#!/usr/bin/env python3
"""
flujo Tapiz Void — Stream negativo de espacios de código (brand enforced).

Visualiza patrones de estructura (indentación y vacíos) sin colorear el código.
Solo los espacios se vuelven visibles como patrón en negativo. Premium dark pro.

Diseñado para:
- Análisis profesional de estructura de código / briefs.
- No acumular recursos: ventana deslizante.
- Auto-generación para patrones continuos (internal use).

Uso (siempre con flujo brand en mente):
    python projects/tapiz/vibecode_void.py archivo.py
    ...
"""

import sys
import re
import time
import random
import argparse
import shutil
from typing import List, Tuple, Optional

# ANSI helpers
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def bg_gray(n: int) -> str:
    """Color de fondo gris en escala 0 (negro) a 23 (blanco)."""
    n = max(0, min(n, 23))
    return f"\033[48;5;{232 + n}m"


def fg_gray(n: int) -> str:
    """Color de texto gris en escala 0 (negro) a 23 (blanco)."""
    n = max(0, min(n, 23))
    return f"\033[38;5;{232 + n}m"


# Texto invisible: mismo color que el fondo del terminal (negro aprox)
TEXT_INVISIBLE = "\033[38;5;232m"
# Texto fantasma tenue
TEXT_GHOST = "\033[38;5;240m"
# Espacio visible: fondo gris claro
SPACE_VISIBLE = bg_gray(18)


def tokenize(line: str) -> List[Tuple[str, str]]:
    """Divide la línea en tokens ('word' | 'space', texto)."""
    parts = re.split(r"(\s+)", line)
    tokens = []
    for part in parts:
        if not part:
            continue
        tokens.append(("space" if part.isspace() else "word", part))
    return tokens


def render_line_negative(line: str, width: int, ghost: bool = False) -> str:
    """
    Renderiza una línea en modo negativo: texto invisible, espacios visibles.
    Si ghost=True, el texto se ve en gris tenue.
    """
    tokens = tokenize(line)
    text_color = TEXT_GHOST if ghost else TEXT_INVISIBLE
    out = []
    chars_used = 0

    for kind, part in tokens:
        if chars_used >= width:
            break
        if kind == "space":
            # Recorta el bloque si excede el ancho
            take = min(len(part), width - chars_used)
            out.append(SPACE_VISIBLE + " " * take + RESET)
            chars_used += take
        else:
            take = min(len(part), width - chars_used)
            out.append(text_color + part[:take] + RESET)
            chars_used += take

    # Relleno hasta el ancho con fondo negro
    if chars_used < width:
        out.append(" " * (width - chars_used))
    return "".join(out)


def render_line_blocks(line: str, width: int, ghost: bool = False) -> str:
    """
    Renderiza los espacios como bloques de altura/densidad variable.
    Cada bloque de espacios se mapea a un carácter Unicode según su longitud.
    """
    tokens = tokenize(line)
    text_color = TEXT_GHOST if ghost else TEXT_INVISIBLE
    blocks = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    out = []
    chars_used = 0

    for kind, part in tokens:
        if chars_used >= width:
            break
        if kind == "space":
            take = min(len(part), width - chars_used)
            idx = min(take, len(blocks) - 1)
            # Gris más claro si el bloque es más largo
            shade = min(18 + take, 23)
            char = blocks[idx] if take < len(blocks) else "█"
            out.append(bg_gray(shade) + char * take + RESET)
            chars_used += take
        else:
            take = min(len(part), width - chars_used)
            out.append(text_color + part[:take] + RESET)
            chars_used += take

    if chars_used < width:
        out.append(" " * (width - chars_used))
    return "".join(out)


# ---------------------------------------------------------------------------
# Generación procedural de código "sintácticamente plausible"
# ---------------------------------------------------------------------------
NAMES = ["data", "items", "results", "values", "tensor", "features", "labels", "model"]
FUNCS = ["process", "transform", "compute", "normalize", "encode", "decode", "predict", "forward"]
OPS = ["+", "-", "*", "/", "**", "%", "//"]


def generate_line(indent: int = 0, mode: str = "code") -> str:
    """Genera una línea de código Python procedural."""
    if mode == "blank":
        return ""
    if mode == "comment":
        return " " * indent + f"# {random.choice(['step', 'layer', 'block', 'attention', 'loop'])} {random.randint(1, 99)}"

    indent_str = " " * indent
    choice = random.random()

    if choice < 0.15:
        return f"{indent_str}def {random.choice(FUNCS)}_{random.choice(NAMES)}({', '.join(random.sample(NAMES, k=random.randint(1, 3)))}):"
    if choice < 0.25:
        return f"{indent_str}for {random.choice(NAMES)} in {random.choice(NAMES)}:"
    if choice < 0.35:
        return f"{indent_str}if {random.choice(NAMES)} {random.choice(['>', '<', '==', '>='])} {random.uniform(0, 100):.2f}:"
    if choice < 0.45:
        return f"{indent_str}return {random.choice(NAMES)}"
    if choice < 0.55:
        a, b = random.sample(NAMES, 2)
        return f"{indent_str}{a} = {b} {random.choice(OPS)} {random.uniform(0, 10):.2f}"
    if choice < 0.65:
        a = random.choice(NAMES)
        return f"{indent_str}{a} = [{random.choice(NAMES)} for _ in range({random.randint(2, 20)})]"
    if choice < 0.75:
        a = random.choice(NAMES)
        return f"{indent_str}{a} = {{k: v for k, v in {random.choice(NAMES)}.items()}}"
    if choice < 0.85:
        a = random.choice(NAMES)
        return f"{indent_str}{a} = list(map(lambda x: x {random.choice(OPS)} {random.randint(2, 9)}, {random.choice(NAMES)}))"
    return f"{indent_str}{random.choice(NAMES)}.append({random.choice(NAMES)})"


def auto_generator():
    """Generador infinito de líneas de código con indentación variable."""
    indent = 0
    while True:
        r = random.random()
        if r < 0.05:
            yield ""
        elif r < 0.10:
            yield generate_line(indent, "comment")
        else:
            line = generate_line(indent, "code")
            yield line
            # Simular lógica de indentación
            if line.rstrip().endswith(":"):
                indent += 4
                if indent > 20:
                    indent = 0
            elif random.random() < 0.2 and indent >= 4:
                indent -= 4


# ---------------------------------------------------------------------------
# Motor de streaming con ventana deslizante
# ---------------------------------------------------------------------------
def stream_window(
    source,
    width: int,
    height: int,
    style: str = "negative",
    ghost: bool = False,
    speed: float = 0.05,
    typewriter: bool = True,
    auto: bool = False,
):
    """
    Muestra el código fuente línea por línea, visualizando solo los espacios.
    - source: iterable de líneas (strings).
    - width/height: dimensiones del canvas.
    - style: 'negative' (fondos) o 'blocks' (densidad).
    - typewriter: revela cada línea carácter a carácter simulando escritura IA.
    - auto: si es True, la fuente ya es un generador infinito.
    """
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write(CLEAR)
    sys.stdout.flush()

    buffer: List[str] = []
    render_fn = render_line_negative if style == "negative" else render_line_blocks

    try:
        for line in source:
            # Normaliza fin de línea
            line = line.rstrip("\n").rstrip("\r")

            if typewriter:
                # Revela la línea carácter a carácter, mostrando los espacios
                for pos in range(1, len(line) + 1):
                    partial = line[:pos]
                    current = buffer + [partial]
                    draw(current, render_fn, width, height, ghost)
                    time.sleep(speed * 0.3)

            buffer.append(line)
            if len(buffer) > height:
                buffer.pop(0)

            draw(buffer, render_fn, width, height, ghost)
            time.sleep(speed)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write(RESET)
        sys.stdout.flush()


def draw(buffer: List[str], render_fn, width: int, height: int, ghost: bool):
    """Dibuja la ventana actual en pantalla."""
    sys.stdout.write(CLEAR)
    # Centrado vertical: si hay menos líneas que altura, rellenar arriba
    padding_top = max(0, height - len(buffer))
    for _ in range(padding_top):
        sys.stdout.write(" " * width + "\n")

    for line in buffer:
        sys.stdout.write(render_fn(line, width, ghost) + "\n")

    # Barra de estado sutil
    sys.stdout.write(
        fg_gray(8) + "─" * width + RESET + "\n"
        + fg_gray(10) + "VibeCode Void | ventana: "
        + f"{len(buffer)}/{height} | Ctrl+C para salir" + RESET + "\n"
    )
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="flujo Tapiz Void — visualizador pro de patrones en espacios (brand enforced desde projects/flujo/flujo.json). Dark premium, no experimental."
    )
    parser.add_argument("file", nargs="?", help="Archivo de código")
    parser.add_argument(
        "-w", "--width", type=int, default=0,
        help="Ancho del canvas (0 = auto)"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=0,
        help="Alto del canvas (0 = auto)"
    )
    parser.add_argument(
        "-s", "--style", choices=["negative", "blocks"], default="negative",
        help="Estilo visual: negative (espacios con fondo) o blocks (densidad)"
    )
    parser.add_argument(
        "-g", "--ghost", action="store_true",
        help="Mostrar el código en gris tenue (no completamente invisible)"
    )
    parser.add_argument(
        "-a", "--auto", action="store_true",
        help="Auto-generar código procedural infinitamente"
    )
    parser.add_argument(
        "--speed", type=float, default=0.05,
        help="Segundos entre líneas (default 0.05)"
    )
    parser.add_argument(
        "--no-typewriter", action="store_true",
        help="Mostrar líneas completas sin efecto máquina de escribir"
    )
    parser.add_argument(
        "--lines", type=int, default=0,
        help="Límite de líneas a procesar (0 = infinito)"
    )

    args = parser.parse_args()

    # Dimensiones
    term_w, term_h = shutil.get_terminal_size()
    width = args.width or term_w
    height = args.height or max(10, term_h - 2)

    # Fuente de líneas
    if args.auto:
        source = auto_generator()
        limit = args.lines or 0
    elif args.file:
        try:
            f = open(args.file, "r", encoding="utf-8")
            source = (line for line in f)
            limit = args.lines or 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif not sys.stdin.isatty():
        source = (line for line in sys.stdin)
        limit = args.lines or 0
    else:
        print("No hay entrada. Usa --auto, un archivo o pipe.", file=sys.stderr)
        sys.exit(1)

    if limit > 0:
        source = (line for _, line in zip(range(limit), source))

    stream_window(
        source,
        width=width,
        height=height,
        style=args.style,
        ghost=args.ghost,
        speed=args.speed,
        typewriter=not args.no_typewriter,
        auto=args.auto,
    )


if __name__ == "__main__":
    main()
