"""Iconos operativos del stand de reduccion de danos (glyphs SVG line-art).

Los 17 iconos base son funciones (cx, cy, scale, color) -> markup SVG centrado
en (cx, cy), portadas 1:1 desde web/src/components/PlanoTool.tsx para que el PDF
y el editor web muestren los mismos simbolos. La paleta COLORES espeja
ZONE_COLORS del web.

CATALOGO ABIERTO (2026-07-26). Criterio del usuario, textual: "puede la jefa de
eventos agregar un icono? si no, no es configurable". Antes no podia: habria
tenido que escribir paths SVG a mano en Python Y en TypeScript. Ahora suelta un
.svg en `data/plano_simbolos/` y lo declara en `data/plano_simbolos.json`; ver
ese archivo, que lleva las instrucciones. Los 17 base siguen en codigo y el
catalogo se SUMA: tambien puede reetiquetar o recolorear uno base sin tocarlo.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .engine import _ZONAS_ICONOS, es_masivo

# Espejo de ZONE_COLORS (PlanoTool.tsx) — misma paleta neon en web y PDF.
COLORES: Dict[str, str] = {
    "tent": "#2d5a4a", "table": "#10b981", "power": "#f59e0b", "light": "#fde047",
    "water": "#2563eb", "extinguisher": "#dc2626", "medical": "#dc2626",
    "security": "#f97316", "testeo": "#f59e0b", "contencion": "#7c3aed",
    "food": "#a16207", "heating": "#ef4444", "trash": "#71717a",
    "contact": "#0ea5e9", "sensory": "#8b5cf6",
    "sillon": "#0d9488", "toalla": "#0891b2",
}

# OJO: las CLAVES son identificadores y se quedan en ASCII (son llaves de datos,
# no palabras). Los VALORES se IMPRIMEN en el plano y en el rider que ve la jefa
# de eventos y el venue, asi que van en espanol correcto con acentos: mutilar un
# diacritico en una pieza que se entrega es un defecto, no un estilo.
ETIQUETAS: Dict[str, str] = {
    "tent": "Toldo 3x3", "table": "Mesas", "power": "Electricidad", "light": "Iluminación",
    "water": "Agua", "extinguisher": "Extintor", "medical": "Equipo Médico",
    "security": "Seguridad", "testeo": "Testeo", "contencion": "Contención",
    "food": "Alimentación", "heating": "Calefacción", "trash": "Basureros",
    "contact": "Producción", "sensory": "Baja Estim.",
    "sillon": "Sillón doble", "toalla": "Toalla Nova",
}


def _hx(cx: float, n: float, s: float) -> float:
    return cx + (n - 80) * s


def _hy(cy: float, n: float, s: float) -> float:
    return cy + (n - 80) * s


def _glyph_power(cx, cy, s, c):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return f'<path d="M {x(88)} {y(28)} L {x(52)} {y(88)} H {x(82)} L {x(72)} {y(132)} L {x(112)} {y(70)} H {x(82)} Z" fill="{c}"/>'


def _glyph_water(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(80)} {y(24)} C {x(116)} {y(70)} {x(126)} {y(92)} {x(110)} {y(118)} '
            f'C {x(94)} {y(144)} {x(58)} {y(144)} {x(48)} {y(116)} C {x(38)} {y(88)} {x(58)} {y(66)} {x(80)} {y(24)} Z" '
            f'fill="none" stroke="{c}" stroke-width="{sw}"/>')


def _glyph_table(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<rect x="{x(28)}" y="{y(54)}" width="{104*s:.1f}" height="{42*s:.1f}" rx="{6*s:.1f}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(46)} {y(96)} V {y(130)} M {x(114)} {y(96)} V {y(130)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_tent(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(22)} {y(122)} L {x(80)} {y(34)} L {x(138)} {y(122)} Z M {x(80)} {y(34)} V {y(122)}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>')


def _glyph_security(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(80)} {y(22)} L {x(124)} {y(40)} V {y(76)} C {x(124)} {y(104)} {x(106)} {y(126)} {x(80)} {y(140)} '
            f'C {x(54)} {y(126)} {x(36)} {y(104)} {x(36)} {y(76)} V {y(40)} Z" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(62)} {y(80)} L {x(76)} {y(94)} L {x(102)} {y(62)}" fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_medical(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(80)} {y(58)} V {y(106)} M {x(56)} {y(82)} H {x(104)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<path d="M {x(80)} {y(136)} C {x(34)} {y(96)} {x(28)} {y(66)} {x(48)} {y(46)} C {x(62)} {y(32)} {x(78)} {y(42)} {x(80)} {y(54)} '
            f'C {x(82)} {y(42)} {x(100)} {y(32)} {x(114)} {y(46)} C {x(134)} {y(66)} {x(126)} {y(98)} {x(80)} {y(136)} Z" '
            f'fill="none" stroke="{c}" stroke-width="{sw}"/>')


def _glyph_extinguisher(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<rect x="{x(60)}" y="{y(50)}" width="{42*s:.1f}" height="{88*s:.1f}" rx="{9*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(70)} {y(50)} V {y(34)} H {x(94)} V {y(50)} M {x(94)} {y(62)} H {x(120)} L {x(134)} {y(52)}" '
            f'stroke="{c}" fill="none" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_testeo(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{58*s:.1f}" fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(60)} {y(42)} H {x(100)} M {x(80)} {y(42)} V {y(82)} L {x(112)} {y(126)} H {x(48)} L {x(80)} {y(82)}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}"/>')


def _glyph_contencion(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{58*s:.1f}" fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(80)} {y(120)} C {x(44)} {y(88)} {x(44)} {y(62)} {x(62)} {y(52)} C {x(74)} {y(46)} {x(80)} {y(56)} {x(80)} {y(64)} '
            f'C {x(80)} {y(56)} {x(90)} {y(46)} {x(102)} {y(52)} C {x(120)} {y(62)} {x(116)} {y(90)} {x(80)} {y(120)} Z" fill="{c}"/>')


def _glyph_light(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(80)} {y(30)} C {x(52)} {y(30)} {x(38)} {y(54)} {x(50)} {y(80)} C {x(58)} {y(96)} {x(66)} {y(100)} {x(66)} {y(114)} '
            f'H {x(94)} C {x(94)} {y(100)} {x(102)} {y(96)} {x(110)} {y(80)} C {x(122)} {y(54)} {x(108)} {y(30)} {x(80)} {y(30)} Z" '
            f'fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(66)} {y(126)} H {x(94)} M {x(70)} {y(138)} H {x(90)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_food(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(56)} {y(34)} V {y(74)} M {x(56)} {y(74)} C {x(56)} {y(86)} {x(48)} {y(88)} {x(48)} {y(100)} V {y(132)} '
            f'M {x(56)} {y(34)} M {x(64)} {y(34)} V {y(74)} C {x(64)} {y(86)} {x(72)} {y(88)} {x(72)} {y(100)} V {y(132)}" '
            f'stroke="{c}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>'
            f'<path d="M {x(108)} {y(34)} C {x(96)} {y(34)} {x(92)} {y(52)} {x(92)} {y(70)} C {x(92)} {y(84)} {x(108)} {y(84)} {x(108)} {y(84)} '
            f'V {y(132)}" stroke="{c}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>')


def _glyph_trash(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(48)} {y(52)} H {x(112)} M {x(66)} {y(52)} V {y(42)} H {x(94)} V {y(52)} '
            f'M {x(56)} {y(52)} L {x(60)} {y(130)} H {x(100)} L {x(104)} {y(52)}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<path d="M {x(72)} {y(66)} V {y(118)} M {x(88)} {y(66)} V {y(118)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_contact(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<circle cx="{cx:.1f}" cy="{_hy(cy, 56, s):.1f}" r="{22*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(44)} {y(134)} C {x(44)} {y(102)} {x(64)} {y(90)} {x(80)} {y(90)} C {x(96)} {y(90)} {x(116)} {y(102)} {x(116)} {y(134)}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_sensory(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(112)} {y(96)} C {x(96)} {y(112)} {x(64)} {y(110)} {x(52)} {y(84)} C {x(42)} {y(62)} {x(54)} {y(38)} {x(76)} {y(32)} '
            f'C {x(62)} {y(52)} {x(70)} {y(84)} {x(112)} {y(96)} Z" fill="none" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>')


def _glyph_heating(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<path d="M {x(80)} {y(34)} C {x(64)} {y(54)} {x(96)} {y(66)} {x(80)} {y(92)} '
            f'M {x(64)} {y(70)} C {x(54)} {y(84)} {x(70)} {y(96)} {x(62)} {y(112)} "'
            f' fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_sillon(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<rect x="{x(24)}" y="{y(56)}" width="{18*s:.1f}" height="{62*s:.1f}" rx="{7*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<rect x="{x(118)}" y="{y(56)}" width="{18*s:.1f}" height="{62*s:.1f}" rx="{7*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<rect x="{x(40)}" y="{y(42)}" width="{80*s:.1f}" height="{26*s:.1f}" rx="{8*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<rect x="{x(40)}" y="{y(66)}" width="{80*s:.1f}" height="{42*s:.1f}" rx="{8*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(80)} {y(66)} V {y(108)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>')


def _glyph_toalla(cx, cy, s, c, sw):
    x = lambda n: _hx(cx, n, s); y = lambda n: _hy(cy, n, s)  # noqa: E731
    return (f'<ellipse cx="{x(80)}" cy="{y(46)}" rx="{34*s:.1f}" ry="{14*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<ellipse cx="{x(80)}" cy="{y(46)}" rx="{13*s:.1f}" ry="{5*s:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>'
            f'<path d="M {x(46)} {y(46)} V {y(96)} M {x(114)} {y(46)} V {y(96)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" fill="none"/>'
            f'<path d="M {x(46)} {y(96)} C {x(46)} {y(104)} {x(114)} {y(104)} {x(114)} {y(96)}" stroke="{c}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>'
            f'<path d="M {x(100)} {y(98)} C {x(120)} {y(102)} {x(124)} {y(114)} {x(108)} {y(120)} C {x(94)} {y(126)} {x(98)} {y(134)} {x(114)} {y(138)}" '
            f'stroke="{c}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>')


_GLYPHS: Dict[str, Callable[..., str]] = {
    "power": lambda cx, cy, s, c, sw: _glyph_power(cx, cy, s, c),
    "water": _glyph_water, "table": _glyph_table, "tent": _glyph_tent,
    "security": _glyph_security, "medical": _glyph_medical,
    "extinguisher": _glyph_extinguisher, "testeo": _glyph_testeo,
    "contencion": _glyph_contencion, "light": _glyph_light, "food": _glyph_food,
    "trash": _glyph_trash, "contact": _glyph_contact, "sensory": _glyph_sensory,
    "heating": _glyph_heating, "sillon": _glyph_sillon, "toalla": _glyph_toalla,
}


# ============================================================
# Catalogo editable: simbolos que agrega la jefa de eventos
# ============================================================

_CATALOGO_REL = "data/plano_simbolos.json"
_SVGS_REL = "data/plano_simbolos"

# Zonas validas del plano, derivadas de engine._ZONAS_ICONOS (nunca copiadas).
# Un simbolo que declare otra cosa cae en ZONA_POR_DEFECTO con aviso: antes, una
# clave que no figuraba en ninguna zona se descartaba EN SILENCIO y el icono
# simplemente no aparecia en el plano.
ZONAS_VALIDAS = tuple(z for z, _ in _ZONAS_ICONOS)
ZONA_POR_DEFECTO = ZONAS_VALIDAS[-1]

# `cuando` decide en que eventos aparece el simbolo.
CUANDOS_VALIDOS = ("siempre", "testeo", "jornada_larga", "masivo", "manual")

_RE_COMENTARIO = re.compile(r"<!--.*?-->", re.S)
_RE_SCRIPT = re.compile(r"<script\b.*?</script\s*>", re.S | re.I)
_RE_EVENTO = re.compile(r'\son[a-z]+\s*=\s*(".*?"|\'.*?\')', re.S | re.I)
_RE_DECL = re.compile(r"<\?xml.*?\?>|<!DOCTYPE.*?>", re.S | re.I)
_RE_SVG_ABRE = re.compile(r"<svg\b([^>]*)>", re.I)
_RE_VIEWBOX = re.compile(r'viewBox\s*=\s*["\']([^"\']+)["\']', re.I)
_RE_MEDIDA = re.compile(r'\b(width|height)\s*=\s*["\']([\d.]+)', re.I)


def _avisar(msg: str) -> None:
    print(f"AVISO plano_simbolos: {msg}", file=sys.stderr)


_RAIZ_FIJA: Optional[Path] = None


def _raiz() -> Path:
    return _RAIZ_FIJA or Path(__file__).resolve().parents[3]


def _medidas(atributos: str) -> Tuple[float, float]:
    """Ancho/alto del lienzo del SVG: viewBox si existe, si no width/height."""
    vb = _RE_VIEWBOX.search(atributos)
    if vb:
        partes = vb.group(1).replace(",", " ").split()
        if len(partes) == 4:
            try:
                w, h = float(partes[2]), float(partes[3])
                if w > 0 and h > 0:
                    return w, h
            except ValueError:
                pass
    medidas = {k.lower(): float(v) for k, v in _RE_MEDIDA.findall(atributos)}
    w, h = medidas.get("width", 0.0), medidas.get("height", 0.0)
    return (w, h) if w > 0 and h > 0 else (160.0, 160.0)


def _incrustar_svg(contenido: str, cx: float, cy: float, scale: float, color: str) -> str:
    """Encaja un .svg de la disenadora en la casilla del icono, centrado.

    Los iconos base dibujan en un lienzo de 160x160 escalado por `scale`; el
    aporte se reescala a esa misma caja conservando su proporcion, y se centra
    en (cx, cy). Si el archivo usa `currentColor` -- la convencion habitual al
    exportar desde Illustrator o Figma -- se reemplaza por el color del simbolo,
    de modo que el mismo archivo sirve para el tema dark y el blanco.

    Se recorta lo que no debe viajar dentro de un plano que se entrega: la
    declaracion XML, los comentarios, cualquier <script> y los atributos on*.
    Es limpieza por texto, no un parser completo de SVG: alcanza para una
    exportacion de diseno, y no pretende sanear un archivo hostil.
    """
    limpio = _RE_SCRIPT.sub("", _RE_COMENTARIO.sub("", _RE_DECL.sub("", contenido)))
    limpio = _RE_EVENTO.sub("", limpio)
    apertura = _RE_SVG_ABRE.search(limpio)
    if not apertura:
        return ""
    w, h = _medidas(apertura.group(1))
    interior = limpio[apertura.end():]
    cierre = interior.lower().rfind("</svg>")
    if cierre != -1:
        interior = interior[:cierre]
    interior = interior.replace("currentColor", color)

    k = (160.0 * scale) / max(w, h)
    tx, ty = cx - k * w / 2.0, cy - k * h / 2.0
    return f'<g transform="translate({tx:.2f} {ty:.2f}) scale({k:.4f})">{interior.strip()}</g>'


def _leer_catalogo() -> Dict[str, Dict[str, Any]]:
    """Lee data/plano_simbolos.json. Un simbolo invalido se salta CON aviso."""
    ruta = _raiz() / _CATALOGO_REL
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - se reporta, no se traga
        _avisar(f"{_CATALOGO_REL} no se pudo leer ({e}); se ignora el catalogo.")
        return {}

    catalogo: Dict[str, Dict[str, Any]] = {}
    for entrada in datos.get("simbolos") or []:
        if not isinstance(entrada, dict):
            continue
        sid = str(entrada.get("id") or "").strip()
        if not sid:
            _avisar("hay un simbolo sin 'id'; se salta.")
            continue

        svg_nombre = str(entrada.get("svg") or "").strip()
        marca: Optional[str] = None
        if svg_nombre:
            archivo = _raiz() / _SVGS_REL / svg_nombre
            if archivo.exists():
                try:
                    marca = archivo.read_text(encoding="utf-8")
                except Exception as e:  # noqa: BLE001
                    _avisar(f"'{sid}': no se pudo leer {svg_nombre} ({e}).")
            else:
                _avisar(f"'{sid}': falta el archivo {_SVGS_REL}/{svg_nombre}.")
        if marca is None and sid not in _GLYPHS:
            _avisar(f"'{sid}': sin dibujo y no es un icono base; se salta.")
            continue

        zona = str(entrada.get("zona") or ZONA_POR_DEFECTO).upper()
        if zona not in ZONAS_VALIDAS:
            _avisar(f"'{sid}': zona '{zona}' no existe; va a {ZONA_POR_DEFECTO}.")
            zona = ZONA_POR_DEFECTO
        cuando = str(entrada.get("cuando") or "siempre").lower()
        if cuando not in CUANDOS_VALIDOS:
            _avisar(f"'{sid}': cuando '{cuando}' no existe; se usa 'siempre'.")
            cuando = "siempre"

        catalogo[sid] = {
            "id": sid,
            "etiqueta": str(entrada.get("etiqueta") or sid),
            "color": str(entrada.get("color") or COLORES.get(sid) or "#9ca3af"),
            "svg": marca,
            "zona": zona,
            "cuando": cuando,
        }
    return catalogo


_COLORES_BASE: Dict[str, str] = dict(COLORES)
_ETIQUETAS_BASE: Dict[str, str] = dict(ETIQUETAS)

CATALOGO: Dict[str, Dict[str, Any]] = {}


def recargar_catalogo(raiz: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Relee el catalogo editable y lo aplica sobre los iconos base.

    Se llama sola al importar. `raiz` existe para apuntar a otro checkout (y es
    el enganche de los tests); COLORES y ETIQUETAS se mutan en su sitio porque
    engine.py las tiene referenciadas.
    """
    global _RAIZ_FIJA
    if raiz is not None:
        _RAIZ_FIJA = Path(raiz)

    CATALOGO.clear()
    CATALOGO.update(_leer_catalogo())

    # Volver a la base primero: si se quita un simbolo del JSON, su etiqueta o
    # su color no pueden quedar pegados de la carga anterior.
    COLORES.clear(); COLORES.update(_COLORES_BASE)
    ETIQUETAS.clear(); ETIQUETAS.update(_ETIQUETAS_BASE)

    # El catalogo se SUMA a los iconos base y puede reetiquetar o recolorear uno
    # existente sin tocar el codigo.
    for sid, s in CATALOGO.items():
        COLORES[sid] = s["color"]
        ETIQUETAS[sid] = s["etiqueta"]
    return CATALOGO


recargar_catalogo()


def zonas_de_iconos() -> List[Tuple[str, List[str]]]:
    """Agrupacion por zona del plano, con los simbolos del catalogo incluidos.

    Las zonas base viven en engine._ZONAS_ICONOS y NO se copian aca: dos copias
    de la misma lista se desincronizan sin que nadie lo note.
    """
    base: Dict[str, List[str]] = {z: list(ks) for z, ks in _ZONAS_ICONOS}
    for sid, s in CATALOGO.items():
        if sid not in _GLYPHS:  # un base recoloreado ya esta en su zona
            base.setdefault(s["zona"], []).append(sid)
    return [(z, base[z]) for z, _ in _ZONAS_ICONOS]


def icono(key: str, cx: float, cy: float, scale: float = 1.0, color: str | None = None) -> str:
    """Devuelve el markup SVG del icono `key` centrado en (cx, cy)."""
    c = color or COLORES.get(key, "#9ca3af")
    sw = max(3.0, 5.0 * scale)
    propio = CATALOGO.get(key)
    if propio and propio["svg"]:
        marca = _incrustar_svg(propio["svg"], cx, cy, scale, c)
        if marca:
            return marca
        _avisar(f"'{key}': el archivo no parece un SVG valido; se dibuja el marcador neutro.")
    fn = _GLYPHS.get(key)
    if fn is None:
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{34*scale:.1f}" fill="none" stroke="{c}" stroke-width="{sw}"/>')
    return fn(cx, cy, scale, c, sw)


def simbolos_de_evento(ev: Dict[str, Any]) -> List[str]:
    """Iconos operativos que corresponden al evento (regla logica del rider).

    Base siempre presente + condicionales por testeo / jornada / masivo, mas los
    del catalogo editable segun su `cuando`. Sillas quedan fuera a proposito
    (confunden el plano; el conteo va en el rider).

    Un evento tambien puede pedir simbolos sueltos en `simbolos_extra`, que es
    la via para los declarados con cuando="manual".
    """
    base = ["tent", "table", "power", "light", "water", "extinguisher",
            "medical", "security", "trash", "contact"]
    testeo = bool(ev.get("incluye_testeo", False))
    larga = float(ev.get("duracion_horas", 0) or 0) > 5
    masivo = es_masivo(ev)
    if testeo:
        base.append("testeo")
    if larga:
        base.append("food")
    if masivo:
        base += ["contencion", "sensory"]

    aplica = {"siempre": True, "testeo": testeo, "jornada_larga": larga,
              "masivo": masivo, "manual": False}
    for sid, s in CATALOGO.items():
        if aplica[s["cuando"]] and sid not in base:
            base.append(sid)

    for sid in ev.get("simbolos_extra") or []:
        sid = str(sid).strip()
        if sid and sid not in base:
            base.append(sid)
    return base
