#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Geometria DEMO de la sala radial SCD Plaza Egana -> data/venues/.

Que es y que NO es. Es una geometria DERIVADA del generador de referencia
`projects/plano/referencia_plano_teatro.py` (v3.4, valores por defecto): el
mismo modelo radial -- cuerda 10 m, sagita 0,9 m, radio 14,34 m -- proyectado a
polilineas 3D para que el visor tenga con que arrancar. NO es una visita con
instrumento: nadie firma este archivo y ninguna cota se levanto en sala.

La confianza por polilinea es, en este archivo, una DEMOSTRACION del sistema de
tiers, y esta puesta donde corresponde: el contorno del escenario sale de cotas
fijas del generador (`medido`), la butaqueria sale del modelo radial
(`ajustado`), y todo lo que tiene altura -- muros, balcon -- es una suposicion
(`no_verificado`), porque el plano es una planta y una planta no sabe cuanto
mide el techo. Cuando alguien mida la sala de verdad, este archivo se reemplaza
entero y el visor no se entera.

Uso:
    py tools/venue_geometria_scd.py            # escribe data/venues/scd-plaza-egana.json
    py tools/venue_geometria_scd.py --stdout   # lo imprime, no escribe
    py tools/venue_geometria_scd.py --check    # verifica el JSON, no escribe
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DESTINO = REPO / "data" / "venues" / "scd-plaza-egana.json"

# --------------------------------------------------------------- cotas de referencia
# Todo esto son los valores por defecto de PlanoTeatroVisualizer (v3.4).
ANCHO_ESC = 10.0        # cuerda del escenario
PROF_RECTA = 3.6        # profundidad hasta la linea de boca
PROF_TOTAL = 4.5        # profundidad al centro (con la curva)
DIST_FILA1 = 2.0
HUELLA = 0.9            # profundidad de fila
CANT_FILAS = 7
ANCHO_BUTACA = 0.55
PROF_BUTACA = 0.48
ANCHO_PASILLO = 1.2
C_FF, L_FF = 20, 5      # butacas centro / lateral en la ultima fila
DIST_BALCON = 3.8
CANT_FILAS_BALCON = 3
DIST_BACK_WALL = 5.0
MARGEN_MURO_DEG = 6.0
PASILLO_BACKSTAGE = 1.0

# Alturas: NINGUNA esta medida. Van declaradas como suposicion y el archivo lo
# dice en cada polilinea que las usa.
ALTURA_MURO = 6.0
ALTURA_BALCON = 3.2
ALTURA_ANTEPECHO = 1.0

SAGITA = PROF_TOTAL - PROF_RECTA
RADIO = (SAGITA ** 2 + (ANCHO_ESC / 2) ** 2) / (2 * SAGITA)
Y_CENTRO = PROF_TOTAL - RADIO          # centro virtual del abanico radial

MEDIDO = "cotas fijas del generador de referencia v3.4"
DERIVADO = "derivado del modelo radial (cuerda/sagita)"
SUPUESTO = "altura supuesta, sin medicion"


def _r(v: float) -> float:
    return round(v, 3)


def punto(r: float, ang: float, z: float = 0.0) -> list[float]:
    """Un punto del abanico radial: angulo desde el eje, radio desde el centro."""
    return [_r(r * math.sin(ang)), _r(Y_CENTRO + r * math.cos(ang)), _r(z)]


def arco(r: float, a0: float, a1: float, n: int, z: float = 0.0) -> list[list[float]]:
    n = max(2, n)
    return [punto(r, a0 + (a1 - a0) * i / n, z) for i in range(n + 1)]


def poli(puntos, confianza, etiqueta, capa, metodo) -> dict:
    return {
        "puntos": puntos,
        "confianza": confianza,
        "etiqueta": etiqueta,
        "capa": capa,
        "metodo": metodo,
    }


def banda(r: float, a0: float, a1: float, n: int, z: float = 0.0) -> list[list[float]]:
    """Un bloque de butacas: la fila tiene profundidad, asi que es una banda cerrada."""
    ext = arco(r + PROF_BUTACA / 2, a0, a1, n, z)
    int_ = arco(r - PROF_BUTACA / 2, a1, a0, n, z)
    return ext + int_ + [ext[0]]


def vertical(p: list[float], z: float) -> list[list[float]]:
    return [[p[0], p[1], p[2]], [p[0], p[1], _r(z)]]


# --------------------------------------------------------------- angulos del abanico
def angulos_ultima_fila() -> tuple[float, float, float, float]:
    r_last = RADIO + DIST_FILA1 + (CANT_FILAS - 1) * HUELLA
    a_cen = C_FF * ANCHO_BUTACA / r_last
    a_pas = ANCHO_PASILLO / r_last
    a_lat = L_FF * ANCHO_BUTACA / r_last
    a_max = a_cen / 2 + a_pas + a_lat + math.radians(MARGEN_MURO_DEG)
    return a_cen, a_pas, a_lat, a_max


def filas(r_inicio: float, cantidad: float, a_cen_ref: float, a_lat_ref: float,
          a_pas: float, z: float, confianza: str, capa: str, metodo: str,
          prefijo: str) -> tuple[list[dict], int]:
    """Las filas de un cuerpo (platea o balcon), alineadas radialmente."""
    salida, butacas = [], 0
    for f in range(int(cantidad)):
        r = r_inicio + f * HUELLA
        n_cen = round(a_cen_ref * r / ANCHO_BUTACA)
        n_lat = round(a_lat_ref * r / ANCHO_BUTACA)
        butacas += n_cen + 2 * n_lat
        a_cen = n_cen * ANCHO_BUTACA / r
        a_lat = n_lat * ANCHO_BUTACA / r
        seg_cen = max(2, round(n_cen / 2))
        seg_lat = max(2, round(n_lat / 2))
        salida.append(poli(
            banda(r, -a_cen / 2, a_cen / 2, seg_cen, z),
            confianza, f"{prefijo}{f + 1} centro · {n_cen} butacas", capa, metodo))
        for signo in (1, -1):
            a0 = signo * (a_cen / 2 + a_pas)
            a1 = a0 + signo * a_lat
            lado = "derecha" if signo > 0 else "izquierda"
            salida.append(poli(
                banda(r, min(a0, a1), max(a0, a1), seg_lat, z),
                confianza, f"{prefijo}{f + 1} {lado} · {n_lat} butacas", capa, metodo))
    return salida, butacas


# --------------------------------------------------------------- las piezas de la sala
def geometria() -> tuple[list[dict], int]:
    a_cen, a_pas, a_lat, a_max = angulos_ultima_fila()
    p: list[dict] = []
    media = ANCHO_ESC / 2
    ang_boca = math.asin(media / RADIO)

    # --- escenario: lo unico con cotas propias -----------------------------
    curva = arco(RADIO, -ang_boca, ang_boca, 24)
    p.append(poli(
        [[-media, 0.0, 0.0], [media, 0.0, 0.0]],
        "medido", "fondo de escenario · cuerda 10,00 m", "escenario", MEDIDO))
    for signo in (-1, 1):
        p.append(poli(
            [[_r(signo * media), 0.0, 0.0], [_r(signo * media), PROF_RECTA, 0.0]],
            "medido", f"hombro {'derecho' if signo > 0 else 'izquierdo'} · 3,60 m",
            "escenario", MEDIDO))
    p.append(poli(
        curva, "medido", "linea de boca · sagita 0,90 m sobre 3,60 m", "escenario", MEDIDO))
    p.append(poli(
        [[-media, PROF_RECTA, 0.0], [media, PROF_RECTA, 0.0]],
        "medido", "linea recta de boca", "escenario", MEDIDO))

    # --- pasillos backstage: forma del generador, sin cota propia ----------
    x_esc, x_fin = ANCHO_ESC / 1.6, ANCHO_ESC / 1.6 + PASILLO_BACKSTAGE
    y_atras = PROF_RECTA - PASILLO_BACKSTAGE * 5.0
    for signo in (-1, 1):
        p.append(poli(
            [[_r(signo * x_esc), PROF_RECTA, 0.0],
             [_r(signo * x_fin), PROF_RECTA, 0.0],
             [_r(signo * x_fin), _r(y_atras), 0.0]],
            "ajustado", "pasillo backstage", "backstage", DERIVADO))
    p.append(poli(
        [[_r(-x_fin), _r(y_atras), 0.0], [_r(x_fin), _r(y_atras), 0.0]],
        "ajustado", "cierre trasero backstage", "backstage", DERIVADO))

    # --- platea ------------------------------------------------------------
    r_fila1 = RADIO + DIST_FILA1
    bloques, butacas = filas(r_fila1, CANT_FILAS, a_cen, a_lat, a_pas, 0.0,
                             "ajustado", "butacas", DERIVADO, "F")
    p += bloques

    r_ult = r_fila1 + (CANT_FILAS - 1) * HUELLA
    for signo in (1, -1):
        for ang in (signo * a_cen / 2, signo * (a_cen / 2 + a_pas)):
            p.append(poli(
                [punto(r_fila1 - 0.6, ang), punto(r_ult + 0.6, ang)],
                "ajustado", "eje de pasillo", "pasillos", DERIVADO))

    # --- muros: planta derivada, altura supuesta ---------------------------
    r_fondo = r_ult + DIST_BALCON + (CANT_FILAS_BALCON - 1) * HUELLA + 2.2
    for signo in (1, -1):
        a = signo * a_max
        base = [punto(RADIO, a), punto(r_fondo, a)]
        p.append(poli(base, "ajustado",
                      f"muro lateral {'derecho' if signo > 0 else 'izquierdo'} · planta",
                      "muros", DERIVADO))
        p.append(poli([[q[0], q[1], ALTURA_MURO] for q in base], "no_verificado",
                      "muro lateral · coronacion a 6,00 m SUPUESTOS", "muros_alto",
                      SUPUESTO))
        for q in base:
            p.append(poli(vertical(q, ALTURA_MURO), "no_verificado",
                          "arista vertical · altura supuesta", "muros_alto", SUPUESTO))
    fondo = arco(r_fondo, -a_max, a_max, 28)
    p.append(poli(fondo, "ajustado", "muro de fondo · planta", "muros", DERIVADO))
    p.append(poli([[q[0], q[1], ALTURA_MURO] for q in fondo], "no_verificado",
                  "muro de fondo · coronacion SUPUESTA", "muros_alto", SUPUESTO))

    # --- balcon: todo lo que vuela es suposicion ---------------------------
    r_balcon = r_ult + DIST_BALCON
    bal, butacas_bal = filas(r_balcon, CANT_FILAS_BALCON, a_cen, a_lat, a_pas,
                             ALTURA_BALCON, "no_verificado", "balcon", SUPUESTO, "B")
    p += bal
    antepecho = arco(r_balcon - 0.4, -a_max * 0.92, a_max * 0.92, 26, ALTURA_BALCON)
    p.append(poli(antepecho, "no_verificado",
                  "antepecho de balcon · a 3,20 m SUPUESTOS", "balcon", SUPUESTO))
    p.append(poli([[q[0], q[1], _r(ALTURA_BALCON + ALTURA_ANTEPECHO)] for q in antepecho],
                  "no_verificado", "baranda de balcon · SUPUESTA", "balcon", SUPUESTO))
    for q in (antepecho[0], antepecho[-1]):
        p.append(poli(vertical(q, ALTURA_BALCON + ALTURA_ANTEPECHO), "no_verificado",
                      "montante de baranda", "balcon", SUPUESTO))
    return p, butacas + butacas_bal


def documento() -> dict:
    polilineas, butacas = geometria()
    aristas = sum(len(pl["puntos"]) - 1 for pl in polilineas)
    return {
        "id": "scd-plaza-egana",
        "nombre": "Teatro SCD Plaza Egaña",
        "ciudad": "Santiago",
        "comuna": "Ñuñoa",
        "tipo": "teatro",
        "publico": True,
        "fecha_captura": "2026-07-30",
        "fuente_datos": "documento",
        "licencia": "ODbL-1.0",
        "notas": (
            "DEMO. La geometría de este archivo está DERIVADA del generador de "
            "referencia projects/plano/referencia_plano_teatro.py (v3.4, valores por "
            "defecto), no de una visita con instrumento: nadie la firma y ninguna cota "
            "se levantó en sala. Sirve para que el visor 3D tenga material real de "
            "trabajo y para mostrar cómo se dibuja cada nivel de confianza. Pendiente: "
            "cotas reales. Cuando existan, este archivo se reemplaza entero."
        ),
        "escenario": {
            "ancho": {"m": ANCHO_ESC, "confianza": "aportado", "metodo": MEDIDO},
            "profundidad": {"m": PROF_TOTAL, "confianza": "aportado", "metodo": MEDIDO},
        },
        "proyeccion": {
            "superficie": "desconocido",
            "notas": "sin datos: el plano de referencia es una planta, no dice nada de proyección.",
        },
        "residuos": [
            {"descripcion": "El plano de referencia es una PLANTA: ninguna altura está "
                            "medida. Muros (6,00 m), balcón (3,20 m) y baranda (1,00 m) "
                            "son supuestos y van marcados no_verificado.",
             "magnitud_m": 6.0},
            {"descripcion": "La sala se dibuja plana: la pendiente de la platea y la "
                            "altura del escenario sobre el piso no se midieron, así que "
                            "el modelo las deja en cero en vez de inventarlas."},
            {"descripcion": "Los muros laterales son radiales, así que la sala se abre "
                            "hacia el fondo más de lo que se abre una sala real. Es el "
                            "modelo del generador, no una medición del recinto."},
        ],
        "geometria": {
            "unidad": "m",
            "nota": (
                "DEMO derivada del generador de referencia v3.4 (radio %.3f m, centro "
                "virtual en y=%.3f m). La confianza por polilínea es real en su "
                "criterio y demostrativa en su origen: escenario = cotas fijas del "
                "generador, butacas = modelo radial, todo lo que tiene altura = "
                "suposición. %d polilíneas, %d aristas, %d butacas en el modelo."
                % (RADIO, Y_CENTRO, len(polilineas), aristas, butacas)
            ),
            "polilineas": polilineas,
        },
    }


def main(argv: list[str]) -> int:
    doc = documento()
    texto = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    if "--check" in argv and "--stdout" in argv:
        print("use only one of --check or --stdout", file=sys.stderr)
        return 2
    if "--check" in argv:
        try:
            existente = json.loads(DESTINO.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read canonical venue JSON: {exc}", file=sys.stderr)
            return 2
        if existente != doc:
            print(f"out of date: {DESTINO.relative_to(REPO)}", file=sys.stderr)
            return 1
        print(f"OK {DESTINO.relative_to(REPO)} matches generator")
        return 0
    if "--stdout" in argv:
        print(texto)
        return 0
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8")
    pl = doc["geometria"]["polilineas"]
    aristas = sum(len(x["puntos"]) - 1 for x in pl)
    conteo: dict[str, int] = {}
    for x in pl:
        conteo[x["confianza"]] = conteo.get(x["confianza"], 0) + len(x["puntos"]) - 1
    print(f"{DESTINO.relative_to(REPO)} · {len(pl)} polilineas · {aristas} aristas · "
          f"{len(texto.encode('utf-8')) / 1024:.0f} KB")
    for k in sorted(conteo):
        print(f"  {k:<15} {conteo[k]:>4} aristas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
