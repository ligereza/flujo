#!/usr/bin/env python3
"""plano_stands.py — motor headless de planos de stands (prototipo).

Genera un plano de intervención en terreno (stands, mesas, sillas, zona de
contención) y un rider con requerimientos derivados por REGLAS, a partir de las
CONSTANTES de realidad. Sin GUI, sin AutoCAD: solo matemáticas → SVG.

Uso:
    python plano_stands.py ejemplos/evento_ejemplo.json > plano.svg
    python plano_stands.py ejemplos/evento_ejemplo.json --rider   # imprime el rider

Diseño en capas puras y testeables:
    CONSTANTES  -> medidas reales (m)
    REGLAS      -> parámetros del evento -> lista de requerimientos
    solve_layout-> coloca módulos en coordenadas (m)
    render_svg  -> dibuja a escala
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ============================================================
# 1. CONSTANTES DE REALIDAD (metros)
# ============================================================
CONSTANTES = {
    "mesa":        {"w": 2.0, "h": 0.7},     # mesa rectangular estándar
    "silla":       {"w": 0.5, "h": 0.5},     # asiento
    "toldo_3x3":   {"w": 3.0, "h": 3.0},     # stand base
    "toldo_3x45":  {"w": 4.5, "h": 3.0},
    "toldo_6x3":   {"w": 6.0, "h": 3.0},
    "pasillo_min": 1.2,                       # ancho mínimo de circulación
    "asiento_area": 0.5,                      # lado de un asiento
}


# ============================================================
# 2. REGLAS (constantes operativas) -> requerimientos del rider
# ============================================================
def reglas_rider(ev: Dict) -> List[str]:
    """Deriva requerimientos del rider según los parámetros del evento."""
    req: List[str] = []
    horas = float(ev.get("duracion_horas", 0))
    voluntarios = int(ev.get("voluntarios", 0))
    asistentes = int(ev.get("asistentes_estimados", 0))
    testeo = bool(ev.get("incluye_testeo", False))
    masivo = asistentes >= 2000 or bool(ev.get("masivo", False))

    if horas > 5:
        req.append("Jornada > 5 h: ALIMENTACIÓN obligatoria para el equipo (producción o costo extra).")
    elif horas > 4:
        req.append("Jornada > 4 h: agregar colación / viático para el equipo.")

    # 1 mesa base; +1 cada 5 voluntarios
    mesas = 1 + max(0, (voluntarios - 1)) // 5
    req.append(f"{voluntarios} voluntarios → {mesas} mesa(s) (1 base + 1 por cada 5).")

    if testeo:
        req.append("Incluye testeo: +1 stand contiguo + 1 mesa extra para reactivos (ventilación obligatoria).")
    if masivo:
        req.append("Evento masivo: agregar ZONA DE CONTENCIÓN/DESCANSO de baja estimulación sensorial.")
    if asistentes:
        req.append(f"{asistentes} asistentes estimados: dimensionar personal y material acorde.")
    req.append("Coordinación previa con producción, seguridad y equipo médico. Acceso para carga/descarga.")
    return req


def modulos_desde_evento(ev: Dict) -> List[Dict]:
    """Decide qué módulos (stands/zonas) incluir según el evento."""
    voluntarios = int(ev.get("voluntarios", 0))
    testeo = bool(ev.get("incluye_testeo", False))
    masivo = ev.get("masivo") or int(ev.get("asistentes_estimados", 0)) >= 2000

    mods = [{"tipo": "stand", "nombre": "Stand Informativo", "toldo": "toldo_3x3",
             "mesas": 1, "sillas": min(voluntarios, 4)}]
    if testeo:
        mods.append({"tipo": "stand", "nombre": "Stand Testeo", "toldo": "toldo_3x3",
                     "mesas": 2, "sillas": min(max(voluntarios - 4, 1), 4)})
    if masivo:
        mods.append({"tipo": "zona", "nombre": "Contención / Descanso", "toldo": "toldo_3x3",
                     "mesas": 0, "sillas": 0})
    return mods


# ============================================================
# 3. LAYOUT — coloca módulos en fila con pasillo (coordenadas en metros)
# ============================================================
@dataclass
class Caja:
    nombre: str
    x: float
    y: float
    w: float
    h: float
    hijos: List["Caja"] = field(default_factory=list)
    rol: str = "stand"


def solve_layout(ev: Dict) -> Tuple[List[Caja], float, float]:
    """Coloca los módulos en una fila horizontal separados por pasillos.

    Devuelve (cajas, ancho_total_m, alto_total_m).
    """
    mods = modulos_desde_evento(ev)
    pasillo = CONSTANTES["pasillo_min"]
    x = 0.0
    cajas: List[Caja] = []
    max_h = 0.0
    for m in mods:
        toldo = CONSTANTES[m["toldo"]]
        caja = Caja(m["nombre"], x, 0.0, toldo["w"], toldo["h"], rol=m["tipo"])
        # mesas dentro del stand (alineadas arriba)
        mw, mh = CONSTANTES["mesa"]["w"], CONSTANTES["mesa"]["h"]
        for i in range(m.get("mesas", 0)):
            my = 0.2 + i * (mh + 0.15)
            caja.hijos.append(Caja(f"mesa", 0.2, my, min(mw, toldo["w"] - 0.4), mh, rol="mesa"))
        # sillas (fila inferior)
        sa = CONSTANTES["asiento_area"]
        for i in range(m.get("sillas", 0)):
            sx = 0.2 + i * (sa + 0.1)
            if sx + sa > toldo["w"]:
                break
            caja.hijos.append(Caja("silla", sx, toldo["h"] - sa - 0.2, sa, sa, rol="silla"))
        cajas.append(caja)
        max_h = max(max_h, toldo["h"])
        x += toldo["w"] + pasillo
    ancho_total = max(0.0, x - pasillo)
    return cajas, ancho_total, max_h


# ============================================================
# 4. RENDER SVG (escala metros -> px)
# ============================================================
def render_svg(ev: Dict, px_por_metro: float = 90.0) -> str:
    cajas, W_m, H_m = solve_layout(ev)
    margin = 0.8  # m de margen
    W = (W_m + 2 * margin) * px_por_metro
    H = (H_m + 2 * margin + 1.2) * px_por_metro  # +espacio para título
    s = px_por_metro
    ox, oy = margin * s, (margin + 0.8) * s

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">']
    out.append(f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbf8f1"/>')
    out.append(f'<text x="{ox}" y="{0.5*s}" font-family="Inter,Arial" font-size="{0.32*s}" font-weight="700" fill="#1f6f4e">'
               f'PLANO — {esc(ev.get("nombre","Evento"))}</text>')
    out.append(f'<text x="{ox}" y="{0.82*s}" font-family="Inter,Arial" font-size="{0.17*s}" fill="#5a6b62">'
               f'Escala 1m = {px_por_metro:.0f}px · {len(cajas)} módulo(s) · generado por constantes</text>')

    for c in cajas:
        cx, cy = ox + c.x * s, oy + c.y * s
        col = "#1f6f4e" if c.rol == "stand" else "#7b5cff"
        out.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{c.w*s:.0f}" height="{c.h*s:.0f}" '
                   f'fill="rgba(31,111,78,0.05)" stroke="{col}" stroke-width="3" rx="6"/>')
        out.append(f'<text x="{cx+6:.0f}" y="{cy+0.3*s:.0f}" font-family="Inter,Arial" font-size="{0.16*s}" '
                   f'font-weight="700" fill="{col}">{esc(c.nombre)}</text>')
        out.append(f'<text x="{cx+6:.0f}" y="{cy+c.h*s-6:.0f}" font-family="Inter,Arial" font-size="{0.12*s}" '
                   f'fill="#5a6b62">{c.w:g}×{c.h:g} m</text>')
        for h in c.hijos:
            hx, hy = cx + h.x * s, cy + h.y * s
            if h.rol == "mesa":
                out.append(f'<rect x="{hx:.0f}" y="{hy:.0f}" width="{h.w*s:.0f}" height="{h.h*s:.0f}" '
                           f'fill="#d4b78f" stroke="#a8855a" stroke-width="1"/>')
            else:  # silla
                out.append(f'<rect x="{hx:.0f}" y="{hy:.0f}" width="{h.w*s:.0f}" height="{h.h*s:.0f}" '
                           f'fill="#e63946" rx="2"/>')
    out.append('</svg>')
    return "\n".join(out)


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_rider(ev: Dict) -> str:
    lines = [f"RIDER TÉCNICO — {ev.get('nombre','Evento')}", "=" * 40, ""]
    lines.append(f"Duración: {ev.get('duracion_horas','?')} h · Voluntarios: {ev.get('voluntarios','?')} "
                 f"· Asistentes est.: {ev.get('asistentes_estimados','?')}")
    lines.append("")
    lines.append("Requerimientos (derivados por reglas):")
    for r in reglas_rider(ev):
        lines.append(f"  • {r}")
    return "\n".join(lines)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 0
    path = argv[0]
    ev = json.load(open(path, encoding="utf-8"))
    if "--rider" in argv:
        print(render_rider(ev))
    else:
        print(render_svg(ev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
