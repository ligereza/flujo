#!/usr/bin/env python3
"""Esconde el changelog de flujo dentro de un SVG entregado (semilla +3: el canal
ilegible = residuo).

Mecanismo elegido: un <metadata id="flujo-steg-changelog"> insertado como PRIMER
hijo del <svg> raiz, con el payload como JSON compacto codificado en base64 puro
(sin newlines) dentro de un CDATA. Por que este mecanismo y no otro:

- <metadata> es un "elemento descriptivo" del spec SVG (misma familia que <title>/
  <desc>): ningun renderer conforme lo pinta. No es una convencion nuestra, es
  contrato del formato -> Omega11(b) (que no cambie el render) queda garantizado
  por spec, no por suerte.
- Los SVG de suplementos_rd ya usan <metadata> para texto descriptivo (ver
  02_impulso_dark_.svg linea 2), asi que el mecanismo no es ajeno al archivo real.
- Comentarios XML (<!-- -->) tambien son invisibles, pero los optimizadores SVGO
  agresivos los barren por default; <metadata> sobrevive mejor una pasada de
  limpieza porque borrarlo es una decision explicita, no el default.
- CDATA con base64 evita pelear con escapes XML (&, <, >, comillas) si el payload
  llegara a crecer; base64 es puro ASCII, no rompe encoding.
- embed() SOLO inserta bytes nuevos; nunca reescribe una linea existente (salvo
  reemplazar un marcador propio previo, para que re-embeber sea idempotente). Esto
  hace que Omega11(a)/(b) sean verificables por construccion: el contenido
  original queda literal, byte a byte, dentro del archivo resultante.

Uso CLI:
    py tools/svg/steg_changelog.py embed <in.svg> <out.svg>
    py tools/svg/steg_changelog.py extract <archivo.svg>
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

MARKER_ID = "flujo-steg-changelog"

# Bloque completo: <metadata id="..."><![CDATA[b64]]></metadata>
_BLOCK_RE = re.compile(
    r'<metadata id="' + re.escape(MARKER_ID) + r'"><!\[CDATA\[([A-Za-z0-9+/=]+)\]\]></metadata>'
)

# Punto de insercion: justo despues del tag de apertura <svg ...>
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)


def _get_flujo_version() -> str:
    """Version actual de flujo. Import directo; si el paquete no esta en el
    sys.path del caller (ej. corrido fuera del repo) cae a subprocess `py -c`."""
    try:
        from flujo.version import get_version

        return str(get_version())
    except Exception:
        try:
            out = subprocess.run(
                [sys.executable, "-c", "from flujo.version import get_version; print(get_version())"],
                cwd=str(Path(__file__).resolve().parents[2]),
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            return out.stdout.strip() or "unknown"
        except Exception:
            return "unknown"


def _get_git_hash() -> str:
    """Hash corto de HEAD. 'unknown' si no hay git disponible (no es fatal)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _build_payload() -> dict[str, str]:
    return {
        "version": _get_flujo_version(),
        "git_hash": _get_git_hash(),
        "date": date.today().isoformat(),
    }


def _encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return base64.b64encode(raw).decode("ascii")


def _decode_payload(b64: str) -> dict[str, Any]:
    raw = base64.b64decode(b64.encode("ascii"))
    data: Any = json.loads(raw.decode("ascii"))
    if not isinstance(data, dict):
        raise ValueError("payload esteganografico no es un objeto JSON")
    return data


def embed(svg_path: str | Path, out_path: str | Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Esconde version+hash+fecha (o `payload` si se pasa uno) en `svg_path` y
    escribe el resultado en `out_path`. Devuelve el payload embebido.

    No modifica ningun byte existente del SVG: si ya hay un marcador propio lo
    reemplaza (re-embed idempotente); si no, inserta el bloque nuevo pegado al
    tag de apertura <svg ...>, antes de cualquier otro contenido.
    """
    src = Path(svg_path).read_text(encoding="utf-8")
    data = payload if payload is not None else _build_payload()
    block = f'<metadata id="{MARKER_ID}"><![CDATA[{_encode_payload(data)}]]></metadata>'

    # Barre TODOS los marcadores propios previos (incluso duplicados por
    # tampering/merge) y luego inserta uno solo en la posicion canonica.
    src = _BLOCK_RE.sub("", src)
    m = _SVG_OPEN_RE.search(src)
    if not m:
        raise ValueError(f"{svg_path}: no se encontro un tag <svg ...> de apertura")
    insert_at = m.end()
    out = src[:insert_at] + block + src[insert_at:]

    Path(out_path).write_text(out, encoding="utf-8")
    return data


def extract(svg_path: str | Path) -> dict[str, Any] | None:
    """Devuelve el payload embebido en `svg_path`, o None si el archivo esta limpio."""
    src = Path(svg_path).read_text(encoding="utf-8")
    m = _BLOCK_RE.search(src)
    if not m:
        return None
    try:
        return _decode_payload(m.group(1))
    except Exception:
        return None


def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="steg_changelog.py",
        description="Esconde/lee el changelog de flujo en el canal no-renderizable de un SVG.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_embed = sub.add_parser("embed", help="esconde version+hash+fecha en un SVG")
    p_embed.add_argument("in_svg", help="SVG de entrada")
    p_embed.add_argument("out_svg", nargs="?", help="SVG de salida (default: sobrescribe in_svg)")

    p_extract = sub.add_parser("extract", help="lee el payload escondido de un SVG")
    p_extract.add_argument("svg", help="archivo SVG a inspeccionar")

    args = parser.parse_args()

    if args.cmd == "embed":
        out_svg = args.out_svg or args.in_svg
        data = embed(args.in_svg, out_svg)
        print(f"embebido en {out_svg}: {json.dumps(data, ensure_ascii=True)}")
        return 0

    if args.cmd == "extract":
        data = extract(args.svg)
        if data is None:
            print("sin payload (SVG limpio)")
            return 1
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
