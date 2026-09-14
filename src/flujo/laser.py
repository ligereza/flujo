# -*- coding: utf-8 -*-
"""Vector aesthetics for laser and plotter: the vpype chain, wrapped.

One tool, two lives (the plano/rider pattern): as an OPERATOR tool it turns
any image into plotter/laser-ready vector art -- `hatched` converts dark
zones into hatching (a solid logo stops arriving hollow), `flow` converts an
image into long continuous flow-field strokes (few pen-ups, laser-friendly).
As a PORTFOLIO feeder, `lote` walks a material folder and writes SVGs plus a
manifest into the repo paths that `contrato_archivo.desde_laser` reads, so
each derived piece enters the archive linked to its curated work.

External-tool pattern (same as Blender/Edge elsewhere in flujo): vpype is a
pip-installed CLI, this module shells out to it and fails with instructions,
never with a traceback. Determinism: `flow` accepts a seed and `lote` derives
it from the file name, so the same material produces the same piece.

What needs NO external tool (pure Python, always available): `medir` reads
the real geometry and reports vertices, subpaths, drawn length and pen-up
travel; `escribir_ild`/`leer_ild` close route B of the toolkit by writing
ILDA format 5 (2D RGB) directly -- the format QuickShow imports -- with the
file re-read for verification. Both work on any single-stroke SVG, not only
on this module's output.

Install (once), measured 2026-07-30 -- the PyPI builds of both plugins are
broken against numpy 2.x (flow: kdtree TypeError; hatched: shapely empty
MultiLineString), so the pin and the git build are REQUIRED, not preference:
    pip install "vpype[all]" "numpy<2"
    pip install "git+https://github.com/plottertools/hatched"
    pip install "git+https://github.com/serycjon/vpype-flow-imager"

Verified state per mode (2026-07-30, this machine): hatched WORKS (168 pts
on the test image, within budget). flow_img installs and registers but two
runs on a 400px test exceeded 10 minutes without finishing -- treat flow as
experimental until someone measures a completed run; hatched is the proven
route.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _vpype() -> str | None:
    """The vpype executable, including the one pip put in this venv's bin.

    `shutil.which` alone missed it: vpype is a declared dev dependency and
    `.venv/bin/vpype` exists, but that directory is not on PATH when the suite
    runs as `./.venv/bin/python -m pytest`, so `verificar()` reported the chain
    as absent and `test_estado_reporta_la_cadena_real` skipped with "vpype not
    installed" on a machine where it IS installed.
    """
    from .knowledge.runtime_tools import resolve_console_script

    found = resolve_console_script("vpype", env_var="VPYPE_EXE")
    return str(found) if found else None


def verificar() -> dict:
    """What of the chain is actually present, measured by running it."""
    estado = {"vpype": False, "hatched": False, "flow": False}
    exe = _vpype()
    if not exe:
        return estado
    estado["vpype"] = True
    try:
        ayuda = subprocess.run([exe, "--help"], capture_output=True, text=True,
                               timeout=30).stdout
    except Exception:
        return estado
    estado["hatched"] = "hatched" in ayuda
    estado["flow"] = "flow_img" in ayuda
    return estado


def puntos(svg: Path) -> int:
    """Vertices de polilinea del SVG: la aproximacion honesta al costo en
    puntos ILDA. El toolkit del usuario fija 600-1000 puntos por frame a
    30 kpps; un SVG medio aplanado trae 15.000-20.000, asi que presupuestar
    no es opcional (docs/laser/TOOLKIT_INDICE.md)."""
    import re
    texto = svg.read_text(encoding="utf-8", errors="replace")
    # vpype emite tres formas: <line> suelto (2 puntos), <polyline points>
    # (un punto por par x,y) y <path d> (un punto por par de coordenadas).
    n = 2 * len(re.findall(r"<line\b", texto))
    for m in re.finditer(r'points="([^"]+)"', texto):
        n += len(re.findall(r"-?\d[\d.eE+-]*[,\s]+-?\d", m.group(1)))
    for m in re.finditer(r'\bd="([^"]+)"', texto):
        n += len(re.findall(r"-?\d[\d.eE+-]*[,\s]+-?\d", m.group(1)))
    return n


# ---------------------------------------------------------------------------
# SVG geometry layer (pure Python, no vpype required).
#
# The regex counter above stays as the budget's fast path; this layer parses
# the ACTUAL coordinates so pen-up travel (blanked jumps, the thing that burns
# points without drawing -- toolkit: 10 subpaths eat ~150 points) can be
# MEASURED, and so the same polylines can be written out as ILDA.
# ---------------------------------------------------------------------------

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # SVG affine (a, b, c, d, e, f)


def _mult(m1: tuple, m2: tuple) -> tuple:
    """Compose SVG affines: apply m2 first, then m1 (parent x child)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _aplicar(m: tuple, x: float, y: float) -> "tuple[float, float]":
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _transformacion(texto: str) -> tuple:
    """Parse an SVG `transform` attribute into one affine matrix."""
    m = _IDENT
    for fn, args in re.findall(r"(\w+)\s*\(([^)]*)\)", texto or ""):
        v = [float(x) for x in re.findall(_NUM, args)]
        if fn == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif fn == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif fn == "matrix" and len(v) == 6:
            t = tuple(v)
        elif fn == "rotate":
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = _mult(_mult((1, 0, 0, 1, v[1], v[2]), t),
                          (1, 0, 0, 1, -v[1], -v[2]))
        elif fn == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif fn == "skewY":
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            raise RuntimeError(f"transform SVG no soportado: {fn}")
        m = _mult(m, t)
    return m


def _pares(texto: str) -> "list[tuple[float, float]]":
    v = [float(x) for x in re.findall(_NUM, texto or "")]
    return list(zip(v[0::2], v[1::2]))


def _ruta_d(d: str) -> "list[list[tuple[float, float]]]":
    """Parse a path `d` of M/L/H/V/Z (abs and rel) into polylines.

    Curves are refused ON PURPOSE: converting a curve to points is vpype's
    job (`vpype read in.svg write out.svg` linearizes everything); guessing a
    flattening here would duplicate the registered tool badly.
    """
    tokens = re.findall(r"([A-Za-z])|(" + _NUM + ")", d)
    polys: list[list[tuple[float, float]]] = []
    actual: list[tuple[float, float]] = []
    cmd = ""
    x = y = 0.0
    nums: list[float] = []
    i = 0
    plano = [t[0] or t[1] for t in tokens]
    while i < len(plano):
        tok = plano[i]
        if tok.isalpha():
            if tok in "CcSsQqTtAa":
                raise RuntimeError(
                    "el SVG trae curvas (comando '%s'): aplanar primero con "
                    "vpype  (vpype read entrada.svg write plano.svg)" % tok)
            if tok not in "MmLlHhVvZz":
                raise RuntimeError(f"comando de path SVG no soportado: {tok}")
            cmd = tok
            if cmd in "Zz":
                if actual:
                    actual.append(actual[0])
                    polys.append(actual)
                    x, y = actual[0]
                    actual = []
                i += 1
                continue
            i += 1
            continue
        # a number: consume what the current command needs
        if cmd in "Hh":
            nx = float(tok)
            x = x + nx if cmd == "h" else nx
            actual.append((x, y))
            i += 1
            continue
        if cmd in "Vv":
            ny = float(tok)
            y = y + ny if cmd == "v" else ny
            actual.append((x, y))
            i += 1
            continue
        if i + 1 >= len(plano) or plano[i + 1].isalpha():
            raise RuntimeError("path SVG con coordenada suelta")
        nx, ny = float(tok), float(plano[i + 1])
        i += 2
        if cmd in "Mm":
            if cmd == "m":
                nx, ny = x + nx, y + ny
            if actual:
                polys.append(actual)
            actual = [(nx, ny)]
            x, y = nx, ny
            cmd = "L" if cmd == "M" else "l"  # implicit lineto per SVG spec
            continue
        if cmd in "Ll":
            if cmd == "l":
                nx, ny = x + nx, y + ny
            actual.append((nx, ny))
            x, y = nx, ny
            continue
        raise RuntimeError("path SVG: coordenadas sin comando")
    if actual:
        polys.append(actual)
    return [p for p in polys if len(p) >= 1]


_IGNORAR = {"defs", "metadata", "style", "title", "desc", "clipPath",
            "namedview", "pattern", "marker", "mask", "symbol"}
_CON_TRAZO = {"line", "polyline", "polygon", "path"}


def polilineas(svg: Path) -> "list[list[tuple[float, float]]]":
    """Every stroke of the SVG as absolute-coordinate polylines, in document
    order (= draw order after vpype's linesort).

    Shapes that would need flattening (rect, circle, text, curves) raise with
    the vpype instruction instead of silently dropping geometry: a shape that
    vanishes between the screen and the laser is the exact defect this tool
    exists to prevent.
    """
    try:
        raiz = ET.fromstring(svg.read_text(encoding="utf-8", errors="replace"))
    except ET.ParseError as e:
        raise RuntimeError(f"SVG ilegible ({svg}): {e}") from e
    polys: list[list[tuple[float, float]]] = []

    def caminar(el, m):
        etiqueta = el.tag.rsplit("}", 1)[-1]
        if etiqueta in _IGNORAR:
            return
        m = _mult(m, _transformacion(el.get("transform", "")))
        if etiqueta == "line":
            polys.append([
                _aplicar(m, float(el.get("x1", 0)), float(el.get("y1", 0))),
                _aplicar(m, float(el.get("x2", 0)), float(el.get("y2", 0)))])
        elif etiqueta in ("polyline", "polygon"):
            pts = [_aplicar(m, x, y) for x, y in _pares(el.get("points", ""))]
            if etiqueta == "polygon" and pts:
                pts.append(pts[0])
            if pts:
                polys.append(pts)
        elif etiqueta == "path":
            for poly in _ruta_d(el.get("d", "")):
                polys.append([_aplicar(m, x, y) for x, y in poly])
        elif etiqueta in ("rect", "circle", "ellipse", "text", "image", "use"):
            raise RuntimeError(
                "el SVG trae <%s>, que aqui no se traza: aplanar primero con "
                "vpype  (vpype read entrada.svg write plano.svg)" % etiqueta)
        for hijo in el:
            caminar(hijo, m)

    caminar(raiz, _IDENT)
    return polys


def _largo(puntos_xy: "list[tuple[float, float]]") -> float:
    return sum(math.dist(puntos_xy[i], puntos_xy[i + 1])
               for i in range(len(puntos_xy) - 1))


def medir(svg: Path) -> dict:
    """The frame's real cost, in numbers: vertices, subpaths, drawn length
    and PEN-UP TRAVEL (the blanked jumps between subpaths, in document
    units). The toolkit's design rule is <8 subpaths and every blank jump
    burns points without drawing -- so the benefit of linemerge/linesort is
    something to measure here, not to claim."""
    polys = polilineas(svg)
    viaje = sum(math.dist(polys[i][-1], polys[i + 1][0])
                for i in range(len(polys) - 1))
    return {
        "puntos": sum(len(p) for p in polys),
        "trazos": len(polys),
        "dibujo": round(sum(_largo(p) for p in polys), 1),
        "viaje_apagado": round(viaje, 1),
    }


def _medir_o_nota(svg: Path) -> dict:
    """medir(), degraded to a recorded note when the geometry is not plain
    lines (never a traceback, never silence)."""
    try:
        m = medir(svg)
        return {"trazos": m["trazos"], "viaje_apagado": m["viaje_apagado"]}
    except RuntimeError as e:
        return {"trazos": None, "viaje_apagado": None,
                "nota_medicion": str(e)[:160]}


# Tolerancias de linesimplify (mm) que se prueban EN ORDEN hasta caber en el
# presupuesto. Deterministas: mismo input, mismo resultado.
_TOLERANCIAS = (0.2, 0.5, 1.0, 2.0, 4.0, 8.0)


def _correr(args: "list[str]") -> None:
    exe = _vpype()
    if not exe:
        raise RuntimeError(
            "vpype no esta instalado. Instalar con:\n"
            '  pip install "vpype[all]" hatched\n'
            '  pip install "git+https://github.com/serycjon/vpype-flow-imager"')
    proc = subprocess.run([exe, *args], capture_output=True, text=True,
                          timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("vpype fallo:\n" + (proc.stderr or proc.stdout)[-800:])


def _ajustar_al_presupuesto(salida: Path, presupuesto: int) -> dict:
    """Simplifica EN ORDEN de tolerancias hasta caber en el presupuesto.

    Devuelve {puntos, tolerancia, dentro}: si ni la tolerancia mas gruesa
    alcanza, `dentro` queda False y el operador decide -- nunca se recorta
    geometria en silencio (la regla de no-silent-caps del repo).
    """
    actual = puntos(salida)
    tol_usada = None
    for tol in _TOLERANCIAS:
        if actual <= presupuesto:
            break
        _correr(["read", str(salida), "linesimplify", "-t", f"{tol}mm",
                 "linemerge", "linesort", "write", str(salida)])
        actual = puntos(salida)
        tol_usada = tol
    return {"puntos": actual, "tolerancia_mm": tol_usada,
            "dentro": actual <= presupuesto}


def _generar(generador: "list[str]", salida: Path, presupuesto: int,
             medir_viaje: bool) -> dict:
    """Run generator -> (optionally measure) -> linemerge+linesort -> budget.

    With medir_viaje the sort's benefit becomes two NUMBERS (pen-up travel
    before and after, document units) at the cost of one extra vpype pass;
    without it the single-call pipeline of PR #413 runs byte-identical.
    """
    medida_extra: dict = {}
    if medir_viaje:
        _correr([*generador, "write", str(salida)])
        antes = _medir_o_nota(salida)
        _correr(["read", str(salida), "linemerge", "linesort",
                 "write", str(salida)])
        despues = _medir_o_nota(salida)
        medida_extra = {"viaje_apagado_antes": antes["viaje_apagado"],
                        "viaje_apagado_despues": despues["viaje_apagado"]}
    else:
        _correr([*generador, "linemerge", "linesort", "write", str(salida)])
    medida = _ajustar_al_presupuesto(salida, presupuesto)
    medida.update(_medir_o_nota(salida))
    medida.update(medida_extra)
    return medida


def hatched(imagen: Path, salida: Path, pitch: int = 4,
            niveles: "tuple[int, int, int]" = (64, 128, 192),
            presupuesto: int = 800, medir_viaje: bool = False) -> dict:
    """Dark zones become hatching: the plotterist technique, laser-ready.

    linemerge+linesort minimise pen-up travel (blanked jumps); the point
    budget then simplifies until the frame is drawable at 30 kpps.
    """
    salida.parent.mkdir(parents=True, exist_ok=True)
    return _generar(["hatched", "--levels", *map(str, niveles),
                     "--pitch", str(pitch), str(imagen)],
                    salida, presupuesto, medir_viaje)


def flow(imagen: Path, salida: Path, semilla: int = 7,
         escala_ruido: float | None = None, presupuesto: int = 800,
         medir_viaje: bool = False) -> dict:
    """The image becomes long continuous flow-field strokes.

    Seeded: same image + same seed = same drawing (the timecode-as-seed
    thesis applied to laser material).
    """
    salida.parent.mkdir(parents=True, exist_ok=True)
    args = ["flow_img", "--seed", str(semilla)]
    if escala_ruido is not None:
        args += ["--noise_coeff", str(escala_ruido)]
    return _generar([*args, str(imagen)], salida, presupuesto, medir_viaje)


# ---------------------------------------------------------------------------
# ILDA writer (format 5, 2D true color) -- closes route B of the toolkit.
#
# QuickShow imports ONLY .ILD/.LDA/.LDB/.LDS/.LPC, never SVG (hard
# restriction 5), and no ILDA package exists on PyPI nor as a vpype plugin
# (restriction 7) -- until now the route needed Modulaser (subscription) or
# msvg2ild (monochrome). This writer follows the ILDA IDTF spec, format 5:
# 32-byte header, 8-byte records (X int16 BE, Y int16 BE, status, Blue,
# Green, Red -- the spec orders true color B,G,R, reverse of the palette
# format), EOF = header with 0 records. Golden rule of the toolkit honoured:
# Type 5 RGB always, never a palette table.
# ---------------------------------------------------------------------------

_ILDA_MARGEN = 32000       # fit inside +/-32000 of the +/-32767 space
_ILDA_BLANK = 0x40         # status bit 6: laser off while travelling
_ILDA_ULTIMO = 0x80        # status bit 7: last point of the frame


def _ascii8(texto: str) -> bytes:
    limpio = "".join(c for c in texto if 32 <= ord(c) < 127)[:8]
    return limpio.encode("ascii").ljust(8, b"\x00")


def _cabecera_ild(formato: int, nombre: str, registros: int,
                  frame: int = 0, total: int = 1) -> bytes:
    return (b"ILDA" + b"\x00\x00\x00" + bytes([formato]) + _ascii8(nombre)
            + _ascii8("flujo") + struct.pack(">HHH", registros, frame, total)
            + b"\x00\x00")


def _encajar_ilda(polys: "list[list[tuple[float, float]]]"
                  ) -> "list[list[tuple[int, int]]]":
    """Center and uniform-scale into ILDA space; SVG y-down becomes ILDA
    y-up. Aspect is preserved: the projector's square space must not stretch
    the piece."""
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    lado = max(max(xs) - min(xs), max(ys) - min(ys))
    escala = (2 * _ILDA_MARGEN / lado) if lado > 0 else 1.0
    tope = 32767
    return [[(max(-tope, min(tope, round((x - cx) * escala))),
              max(-tope, min(tope, round(-(y - cy) * escala))))
             for x, y in p] for p in polys]


def escribir_ild(svg: Path, salida: Path,
                 color: "tuple[int, int, int]" = (255, 255, 255),
                 reposo: int = 4, nombre: str | None = None) -> dict:
    """SVG polylines -> one ILDA format-5 frame, importable by QuickShow.

    Each subpath gets `reposo` blanked dwell points at its start and end so
    the scanners settle before the beam opens (each blank jump costs points:
    that is why the count reported here is the REAL one, dwell included, and
    why it can exceed the SVG vertex count). No resampling is done: points
    map 1:1 plus dwell, deterministic byte-for-byte.
    """
    crudo = polilineas(svg)
    if not crudo:
        raise RuntimeError(f"SVG sin trazos que enviar al laser: {svg}")
    polys = _encajar_ilda(crudo)
    registros: "list[tuple[int, int, int, tuple[int, int, int]]]" = []
    for p in polys:
        registros += [(p[0][0], p[0][1], _ILDA_BLANK, (0, 0, 0))] * reposo
        registros += [(x, y, 0, color) for x, y in p]
        registros += [(p[-1][0], p[-1][1], _ILDA_BLANK, (0, 0, 0))] * reposo
    if len(registros) > 0xFFFF:
        raise RuntimeError(
            "frame ILDA sobre el limite de 65535 puntos (%d): simplificar "
            "antes (flujo laser hatched/flow ya presupuesta)" % len(registros))
    datos = bytearray(_cabecera_ild(5, nombre or salida.stem, len(registros)))
    for i, (x, y, estado, (r, g, b)) in enumerate(registros):
        if i == len(registros) - 1:
            estado |= _ILDA_ULTIMO
        datos += struct.pack(">hhBBBB", x, y, estado, b, g, r)
    datos += _cabecera_ild(5, nombre or salida.stem, 0)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(bytes(datos))
    en_blanco = sum(1 for reg in registros if reg[2] & _ILDA_BLANK)
    return {"puntos_ild": len(registros), "en_blanco": en_blanco,
            "trazos": len(polys)}


def leer_ild(ruta: Path) -> "list[dict]":
    """Read back a format-5 .ild: the verification half of the writer
    (measured, not trusted -- the CLI re-reads every file it writes)."""
    datos = ruta.read_bytes()
    frames = []
    pos = 0
    while pos + 32 <= len(datos):
        if datos[pos:pos + 4] != b"ILDA":
            raise RuntimeError(f"no es un archivo ILDA: {ruta}")
        formato = datos[pos + 7]
        nombre = datos[pos + 8:pos + 16].rstrip(b"\x00 ").decode(
            "ascii", "replace")
        n, frame, total = struct.unpack(">HHH", datos[pos + 24:pos + 30])
        pos += 32
        if n == 0:
            break
        if formato != 5:
            raise RuntimeError(
                f"formato ILDA {formato} no soportado (solo 5, 2D RGB)")
        puntos_f = []
        for _ in range(n):
            x, y, estado, b, g, r = struct.unpack(">hhBBBB",
                                                  datos[pos:pos + 8])
            puntos_f.append({"x": x, "y": y,
                             "apagado": bool(estado & _ILDA_BLANK),
                             "ultimo": bool(estado & _ILDA_ULTIMO),
                             "rgb": (r, g, b)})
            pos += 8
        frames.append({"nombre": nombre, "formato": formato,
                       "frame": frame, "total": total, "puntos": puntos_f})
    return frames


def _semilla_de(nombre: str) -> int:
    return int.from_bytes(hashlib.sha256(nombre.encode()).digest()[:4], "big")


def lote(carpeta: Path, destino: Path, manifiesto: Path,
         modo: str = "flow", limite: int | None = None,
         ild: bool = False) -> "list[dict]":
    """Walk a material folder, derive one laser piece per image, write the
    manifest `contrato_archivo.desde_laser` reads.

    The join key with the curated field is the file STEM (the IG media id):
    campo.json's `archivo` carries `posts/<media_id>.mp4`, the material
    folder carries `<media_id>.jpg` -- same digits, same work. With `ild`
    each SVG also lands as a QuickShow-importable .ild next to it (manifest
    rows gain `ild` + `puntos_ild`; default output stays SVG-only).
    """
    imagenes = sorted(p for p in carpeta.iterdir()
                      if p.suffix.lower() in EXTENSIONES)
    if limite:
        imagenes = imagenes[:limite]
    filas = []
    for img in imagenes:
        salida = destino / f"{img.stem}.svg"
        try:
            if modo == "hatched":
                medida = hatched(img, salida)
            else:
                medida = flow(img, salida, semilla=_semilla_de(img.stem))
        except RuntimeError as e:
            filas.append({"stem": img.stem, "error": str(e)[:200]})
            continue
        fila = {
            "stem": img.stem,
            "src": salida.as_posix(),
            "modo": modo,
            "semilla": _semilla_de(img.stem) if modo == "flow" else None,
            "puntos": medida["puntos"],
            "dentro_presupuesto": medida["dentro"],
            "trazos": medida.get("trazos"),
            "viaje_apagado": medida.get("viaje_apagado"),
        }
        if ild:
            try:
                r = escribir_ild(salida, salida.with_suffix(".ild"))
                fila["ild"] = salida.with_suffix(".ild").as_posix()
                fila["puntos_ild"] = r["puntos_ild"]
            except RuntimeError as e:
                fila["ild_error"] = str(e)[:200]
        filas.append(fila)
    manifiesto.parent.mkdir(parents=True, exist_ok=True)
    manifiesto.write_text(
        json.dumps({"version": 1, "modo": modo, "piezas": filas},
                   ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    return filas
