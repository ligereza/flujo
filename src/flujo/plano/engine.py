"""Motor de planos de stands para eventos.

Genera planos SVG y riders de texto a partir de constantes de realidad
(medidas de mesas, toldos, sillas, pasillos) y reglas operativas sobre los
parámetros del evento.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

def _load_flujo_styles() -> Dict[str, Any]:
    """Carga estilos desde flujo si existe (integración con línea editorial)."""
    from ..paths import asset_root
    flujo_path = asset_root() / "projects" / "flujo" / "flujo.json"
    if flujo_path.exists():
        try:
            data = json.loads(flujo_path.read_text(encoding="utf-8"))
            return data.get("colors", {})
        except Exception:
            pass
    return {}


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
def reglas_rider(ev: Dict[str, Any]) -> List[str]:
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
    req.append(f"{voluntarios} voluntarios -> {mesas} mesa(s) (1 base + 1 por cada 5).")

    if testeo:
        req.append("Incluye testeo: +1 stand contiguo + 1 mesa extra para reactivos (ventilación obligatoria).")
    if masivo:
        req.append("Evento masivo: agregar ZONA DE CONTENCIÓN/DESCANSO de baja estimulación sensorial.")
    if asistentes:
        req.append(f"{asistentes} asistentes estimados: dimensionar personal y material acorde.")
    req.append("Coordinación previa con producción, seguridad y equipo médico. Acceso para carga/descarga.")
    return req


def modulos_desde_evento(ev: Dict[str, Any]) -> List[Dict[str, Any]]:
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


def solve_layout(ev: Dict[str, Any]) -> Tuple[List[Caja], float, float]:
    """Coloca los módulos según layout_mode.

    Soporta:
    - "row" (default, fila horizontal con pasillos) — legacy
    - "grid_2x" — colocación aproximada en grilla 2 columnas (más compacta)

    El evento puede declarar "layout_mode": "grid_2x".
    Ver también schemas/layout_primitives.schema.json para evolución declarativa futura.
    """
    mods = modulos_desde_evento(ev)
    layout_mode = ev.get("layout_mode", "row")
    pasillo = CONSTANTES["pasillo_min"]

    if layout_mode == "grid_2x":
        return _solve_grid_2x(mods, pasillo)

    # default: fila (row)
    return _solve_row(mods, pasillo)


def _solve_row(mods: List[Dict], pasillo: float) -> Tuple[List[Caja], float, float]:
    """Implementación original en fila."""
    x = 0.0
    cajas: List[Caja] = []
    max_h = 0.0
    for m in mods:
        toldo = CONSTANTES[m["toldo"]]
        caja = Caja(m["nombre"], x, 0.0, toldo["w"], toldo["h"], rol=m["tipo"])
        mw, mh = CONSTANTES["mesa"]["w"], CONSTANTES["mesa"]["h"]
        for i in range(m.get("mesas", 0)):
            my = 0.2 + i * (mh + 0.15)
            caja.hijos.append(Caja("mesa", 0.2, my, min(mw, toldo["w"] - 0.4), mh, rol="mesa"))
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


def _solve_grid_2x(mods: List[Dict], pasillo: float) -> Tuple[List[Caja], float, float]:
    """Layout simple en grilla de 2 columnas (demo de estructura más declarativa)."""
    col_w = max((CONSTANTES[m["toldo"]]["w"] for m in mods), default=3.0)
    row_h = max((CONSTANTES[m["toldo"]]["h"] for m in mods), default=3.0)
    cajas: List[Caja] = []
    for idx, m in enumerate(mods):
        col = idx % 2
        row = idx // 2
        toldo = CONSTANTES[m["toldo"]]
        x = col * (col_w + pasillo)
        y = row * (row_h + pasillo * 0.6)
        caja = Caja(m["nombre"], x, y, toldo["w"], toldo["h"], rol=m["tipo"])
        # simplificado: mesas/sillas dentro
        mw, mh = CONSTANTES["mesa"]["w"], CONSTANTES["mesa"]["h"]
        for i in range(min(m.get("mesas", 0), 2)):
            caja.hijos.append(Caja("mesa", 0.2, 0.2 + i * (mh + 0.1), mw, mh, rol="mesa"))
        sa = CONSTANTES["asiento_area"]
        for i in range(min(m.get("sillas", 0), 3)):
            caja.hijos.append(Caja("silla", 0.2 + i * (sa + 0.08), toldo["h"] - sa - 0.15, sa, sa, rol="silla"))
        cajas.append(caja)
    cols = 2 if len(mods) > 1 else 1
    rows = (len(mods) + 1) // 2
    ancho = cols * col_w + (cols - 1) * pasillo
    alto = rows * row_h + (rows - 1) * pasillo * 0.6
    return cajas, ancho, alto


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# 4. RENDER SVG (escala metros -> px)
# ============================================================
def render_svg(ev: Dict[str, Any], px_por_metro: float = 90.0) -> str:
    """Render SVG con estilos de flujo si disponible (integración línea editorial)."""
    cajas, W_m, H_m = solve_layout(ev)
    styles = _load_flujo_styles()
    ink = styles.get("ink", "#1f2a24")
    accent = styles.get("accent", "#1f6f4e")
    paper = styles.get("paper", "#fbf8f1")

    margin = 0.8
    W = (W_m + 2 * margin) * px_por_metro
    H = (H_m + 2 * margin + 1.2) * px_por_metro
    s = px_por_metro
    ox, oy = margin * s, (margin + 0.8) * s

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">']
    out.append(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{paper}"/>')
    out.append(f'<text x="{ox}" y="{0.5*s}" font-family="Inter,Arial" font-size="{0.32*s}" font-weight="700" fill="{ink}">'
               f'PLANO — {_esc(ev.get("nombre","Evento"))}</text>')
    out.append(f'<text x="{ox}" y="{0.82*s}" font-family="Inter,Arial" font-size="{0.17*s}" fill="{ink}">'
               f'Escala 1m = {px_por_metro:.0f}px · {len(cajas)} módulo(s) · flujo</text>')

    for c in cajas:
        cx, cy = ox + c.x * s, oy + c.y * s
        col = accent if c.rol == "stand" else "#7b5cff"
        out.append(f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{c.w*s:.0f}" height="{c.h*s:.0f}" '
                   f'fill="rgba(31,111,78,0.05)" stroke="{col}" stroke-width="3" rx="6"/>')
        out.append(f'<text x="{cx+6:.0f}" y="{cy+0.3*s:.0f}" font-family="Inter,Arial" font-size="{0.16*s}" '
                   f'font-weight="700" fill="{col}">{_esc(c.nombre)}</text>')
        out.append(f'<text x="{cx+6:.0f}" y="{cy+c.h*s-6:.0f}" font-family="Inter,Arial" font-size="{0.12*s}" '
                   f'fill="{ink}">{c.w:g}×{c.h:g} m</text>')
        for h in c.hijos:
            hx, hy = cx + h.x * s, cy + h.y * s
            if h.rol == "mesa":
                out.append(f'<rect x="{hx:.0f}" y="{hy:.0f}" width="{h.w*s:.0f}" height="{h.h*s:.0f}" '
                           f'fill="#d4b78f" stroke="#a8855a" stroke-width="1"/>')
            else:
                out.append(f'<rect x="{hx:.0f}" y="{hy:.0f}" width="{h.w*s:.0f}" height="{h.h*s:.0f}" '
                           f'fill="#e63946" rx="2"/>')
    out.append('</svg>')
    return "\n".join(out)


# ============================================================
# 5. RIDER de texto
# ============================================================
def render_rider(ev: Dict[str, Any]) -> str:
    lines = [f"RIDER TÉCNICO — {ev.get('nombre','Evento')}", "=" * 40, ""]
    lines.append(f"Duración: {ev.get('duracion_horas','?')} h · Voluntarios: {ev.get('voluntarios','?')} "
                 f"· Asistentes est.: {ev.get('asistentes_estimados','?')}")
    lines.append("")
    lines.append("Requerimientos (derivados por reglas):")
    for r in reglas_rider(ev):
        lines.append(f"  • {r}")
    return "\n".join(lines)


# ============================================================
# 6. Carga de evento
# ============================================================
def load_evento(path: Path) -> Dict[str, Any]:
    """Carga un evento desde un archivo JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("El evento debe ser un objeto JSON")
    return data
