#!/usr/bin/env python3
"""sombra.py -- raycasting por celda sobre el relieve semantico.

relieve.py se quedo corto y lo dije: iluminacion difusa sin oclusion. Un pico
no oscurecia el valle detras. Aqui si.

EL METODO: horizon mapping.
  Para cada celda y cada azimut de la luz, se marcha por el rayo y se guarda
  el angulo de elevacion MAXIMO que estorba:

      h(x,y,theta) = max_r  atan2( F(x+r*dx, y+r*dy) - F(x,y) , r )

  La celda esta en sombra si la elevacion de la luz no supera ese horizonte.
  Sombra suave: se interpola en una banda de PENUMBRA grados alrededor.

EL PROBLEMA QUE ESO CREA
  relieve.py podia evitar los frames porque la intensidad de cada celda era
  una sinusoide: misma frecuencia, distinta fase -> animation-delay negativo.
  La sombra rompe eso. La oclusion no es armonica: es una funcion arbitraria
  del azimut, con saltos.

LA SOLUCION, QUE ADEMAS ES MEJOR QUE EL TRUCO ANTERIOR
  Se abandona la forma cerrada y se calcula la curva completa: para cada
  celda, la intensidad en los N azimuts. Eso da una FIRMA de N niveles
  cuantizados. Dos celdas con la misma firma comparten @keyframes.

  Es decir: no se deduplica por fase, se deduplica por HISTORIA LUMINICA
  COMPLETA. Es mas general (admite sombras, oclusion, lo que sea) y resulta
  mas barato de lo que parece, porque el relieve es suave y las firmas se
  repiten muchisimo. El numero de clases lo decide la escena, no yo.

  Sigue sin haber un solo frame: hay una grilla y un CSS.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import Params, Historia, CampoSemantico, tokens
from relieve import RAMPA, K_REL, normales

N_AZ = 24          # azimuts de la luz: resolucion temporal
ELEV = 22.0        # elevacion de la luz sobre el plano, en grados
PENUMBRA = 7.0     # grados de transicion sombra/luz
ALTURA = 150.0     # px de altura del relieve para F=1 (define cuanto ocluye)
PASOS = 46         # pasos de marcha del rayo
PASO_PX = 9.0      # px por paso
NIVELES = 8       # cuantizacion de la opacidad
AMB = 0.10         # luz ambiente: la sombra no es negra absoluto
CICLO = 20.0


def horizontes(F, p: Params):
    """h[a,f,c] = tangente del angulo de horizonte de la celda (f,c) hacia el
    azimut a. Vectorizado: para cada azimut y cada radio se desplaza la grilla
    entera en vez de recorrer celda por celda."""
    H = F * ALTURA
    nf, nc = p.filas, p.cols
    fi, ci = np.mgrid[0:nf, 0:nc]
    out = np.zeros((N_AZ, nf, nc))
    for a in range(N_AZ):
        th = 2 * math.pi * a / N_AZ
        dx, dy = math.cos(th), math.sin(th)
        mx = np.zeros((nf, nc))
        for s in range(1, PASOS + 1):
            r = s * PASO_PX
            cc = np.clip(np.round(ci + dx * r / p.adv_x).astype(int), 0, nc - 1)
            ff = np.clip(np.round(fi + dy * r / p.adv_y).astype(int), 0, nf - 1)
            dz = H[ff, cc] - H
            mx = np.maximum(mx, dz / r)
        out[a] = mx
    return out


def intensidades(F, p: Params):
    """I[a,f,c] en 0..1: Lambert difuso por la normal, atenuado por oclusion."""
    nx, ny, nz = normales(F, p)
    lz = math.sin(math.radians(ELEV))
    lh = math.cos(math.radians(ELEV))
    HZ = horizontes(F, p)
    tan_luz = math.tan(math.radians(ELEV))
    tan_pen = math.tan(math.radians(ELEV + PENUMBRA))
    I = np.zeros((N_AZ, p.filas, p.cols))
    for a in range(N_AZ):
        th = 2 * math.pi * a / N_AZ
        lam = nx * (lh * math.cos(th)) + ny * (lh * math.sin(th)) + nz * lz
        lam = np.clip(lam, 0.0, 1.0)
        # visibilidad: 1 si el horizonte esta por debajo de la luz
        v = np.clip((tan_pen - HZ[a]) / (tan_pen - tan_luz + 1e-9), 0.0, 1.0)
        I[a] = AMB + (1.0 - AMB) * lam * v
    return I / (I.max() or 1.0)


def construir_svg(F, I, p: Params) -> str:
    Fn = F / (float(F.max()) or 1.0)
    idx = np.clip((Fn ** 0.65 * (len(RAMPA) - 1)).round().astype(int),
                  0, len(RAMPA) - 1)
    Q = np.clip((I * (NIVELES - 1)).round().astype(int), 0, NIVELES - 1)

    firmas: dict[tuple, int] = {}
    filas = []
    for f in range(p.filas):
        trozos, buf, bk = [], [], None
        for c in range(p.cols):
            ch = RAMPA[idx[f, c]]
            if ch == " ":
                k = None
            else:
                fir = tuple(int(Q[a, f, c]) for a in range(N_AZ))
                k = firmas.setdefault(fir, len(firmas))
            if k != bk and buf:
                trozos.append((bk, "".join(buf)))
                buf = []
            bk = k
            buf.append(ch)
        if buf:
            trozos.append((bk, "".join(buf)))
        filas.append(f'<tspan x="{p.x0:.0f}" dy="{p.adv_y:.0f}">' + "".join(
            escape(t) if k is None else f'<tspan class="s{k}">{escape(t)}</tspan>'
            for k, t in trozos) + "</tspan>")

    css = []
    for fir, k in firmas.items():
        # la curva cuantizada es escalonada: solo se emite el stop donde CAMBIA
        stops, prev = [], None
        for a, q in enumerate(fir):
            if q != prev:
                stops.append(f"{100.0*a/N_AZ:.1f}%{{opacity:{q/(NIVELES-1):.2f}}}")
                prev = q
        if fir[0] != prev:
            stops.append(f"100%{{opacity:{fir[0]/(NIVELES-1):.2f}}}")
        css.append(f"@keyframes f{k}{{{''.join(stops)}}}"
                   f".s{k}{{animation:f{k} {CICLO}s infinite linear}}")

    ley = (f"raycast {N_AZ} azimuts | elev {ELEV:.0f}deg | "
           f"{len(firmas)} firmas de {p.filas*p.cols} celdas")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>relieve semantico con oclusion</title>
<desc>Cada celda lanza {N_AZ} rayos sobre el campo semantico tratado como
altura y guarda su angulo de horizonte. La luz gira a {ELEV:.0f} grados sobre el
plano; una celda se apaga cuando otra mas alta se interpone. No hay frames:
cada celda tiene su curva de luz completa como @keyframes, y las celdas que
comparten curva comparten clase.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre;fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#64748b}}
{chr(10).join(css)}
</style>
<rect width="100%" height="100%" fill="#08070a"/>
<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" xml:space="preserve">{"".join(filas)}</text>
<text class="sello" x="10" y="898">{escape(ley)}</text>
</svg>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida", default="/tmp/proto/sistema/sombra.svg")
    ap.add_argument("--estados", type=int, default=12)
    a = ap.parse_args()

    p = Params()
    h = Historia(Path(a.repo), p)
    todos = h.commits()
    k = min(a.estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)
    crudos = [campo.campo(tk, 1.0) for tk in corpora]
    F = crudos[-1] / (max(float(c.max()) for c in crudos) or 1.0)

    I = intensidades(F, p)
    svg = construir_svg(F, I, p)
    Path(a.salida).write_text(svg, encoding="utf-8")

    ocl = (I.min(0) < 0.5 * I.max(0)).sum()
    print(f"celdas que entran en sombra en algun azimut: {ocl} / {p.filas*p.cols}")
    print(f"contraste medio por celda (max-min): {(I.max(0)-I.min(0)).mean():.3f}")
    print(f"{len(svg)//1024} KB -> {a.salida}")


if __name__ == "__main__":
    main()
