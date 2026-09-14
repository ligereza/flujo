#!/usr/bin/env python3
"""relieve.py -- depth map / normal map del vaso semantico.

TESIS
  El campo escalar F(x,y) que motor.py umbralaba para sacar un contorno YA ES
  UN MAPA DE ALTURA. Umbralarlo era tirar informacion: de una superficie
  continua nos quedabamos con dos curvas de nivel.

  Aqui no se umbrala. F se trata como relieve y se le calcula la normal:

      N = normalize( -dF/dx , -dF/dy , 1/k )

  De ahi salen tres cosas que antes no existian:
    1. DEPTH MAP   -- F crudo, en gris. La topografia semantica desnuda.
    2. NORMAL MAP  -- N codificada en RGB, convencion tangent-space
                      (r=x*.5+.5, g=y*.5+.5, b=z). Verde arriba, lila abajo.
    3. RELIEVE ASCII -- Lambert por celda. El GLIFO ya no es el corpus: es la
                      luminancia, elegido de una rampa de densidad. La imagen
                      vuelve a ser ascii-art, pero de una superficie que no
                      existe fuera de este repo.

EL TRUCO QUE EVITA EL FLIPBOOK
  Con luz que gira en el plano xy:  l = (cos t, sin t, lz)
      I(t) = Nx*cos t + Ny*sin t + Nz*lz
           = A*cos(t - phi) + C      con A = hypot(Nx,Ny), phi = atan2(Ny,Nx)

  Es decir: la intensidad de CADA celda es una sinusoide de la misma
  frecuencia, y solo difiere en amplitud y FASE. Entonces no hacen falta
  frames: una sola grilla estatica, un solo @keyframes, y a cada celda se le
  da su `animation-delay` negativo = su fase, y su amplitud por clase.

  La luz gira sobre un relieve real sin que exista un solo frame intermedio.
  El costo no es N copias de la grilla: son ~A*P clases CSS.

USO
  python3 relieve.py --repo /tmp/vc_test --salida-dir .
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import Params, Historia, CampoSemantico, tokens

# rampa de densidad: de vacio a solido (ASCII de 7 bits, monoespaciada)
RAMPA = " .:-=+*#%@"

N_AMP = 6      # buckets de amplitud
N_FASE = 24    # buckets de fase -> resolucion angular de la luz
CICLO_LUZ = 16.0
LZ = 0.55      # componente vertical de la luz: cuanto ambiente hay
K_REL = 2.6    # exageracion del relieve (mayor k = mas escarpado: nz = 1/k)


def normales(F: np.ndarray, p: Params):
    """Gradiente en unidades de PIXEL, no de celda: la celda es 1:2 y si se
    ignora, el relieve sale estirado en vertical (mismo error que estiraba
    el vaso de v1)."""
    dy, dx = np.gradient(F)
    dx /= p.adv_x
    dy /= p.adv_y
    # escalar a un rango util: el campo es suave y los gradientes minusculos
    s = max(float(np.abs(dx).max()), float(np.abs(dy).max()), 1e-9)
    dx, dy = dx / s, dy / s
    nx, ny, nz = -dx, -dy, np.full_like(F, 1.0 / K_REL)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / n, ny / n, nz / n


# ------------------------------------------------------------------ salidas


def svg_mapa(A: np.ndarray, p: Params, titulo: str, desc: str, rgb=None) -> str:
    """Vuelca una matriz como grilla de rects. Depth o normal, mismo molde."""
    W, H = p.cols * p.adv_x, p.filas * p.adv_y
    out = []
    for f in range(p.filas):
        for c in range(p.cols):
            if rgb is None:
                v = int(round(255 * float(np.clip(A[f, c], 0, 1))))
                col = f"#{v:02x}{v:02x}{v:02x}"
            else:
                r, g, b = (int(round(255 * float(np.clip(x[f, c], 0, 1))))
                           for x in rgb)
                col = f"#{r:02x}{g:02x}{b:02x}"
            out.append(f'<rect x="{c*p.adv_x:.0f}" y="{f*p.adv_y:.0f}" '
                       f'width="{p.adv_x:.0f}" height="{p.adv_y:.0f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
            f'width="100%" height="100%" shape-rendering="crispEdges">'
            f'<title>{escape(titulo)}</title><desc>{escape(desc)}</desc>'
            + "".join(out) + "</svg>\n")


def svg_relieve(F, nx, ny, nz, texto: str, p: Params) -> str:
    """El relieve ASCII con luz giratoria, sin un solo frame."""
    A = np.hypot(nx, ny)                     # amplitud de la sinusoide
    PHI = np.arctan2(ny, nx)                 # fase
    C = nz * LZ                              # termino constante (ambiente)
    amax = float(A.max()) or 1.0

    # --- el glifo lo elige la ALTURA (no la luz): la topografia es fija,
    #     la luz solo la ilumina. Asi el ascii no parpadea de forma.
    Fn = F / (float(F.max()) or 1.0)
    idx = np.clip((Fn ** 0.65 * (len(RAMPA) - 1)).round().astype(int),
                  0, len(RAMPA) - 1)

    filas, usadas = [], set()
    base = {a: [] for a in range(N_AMP)}
    for f in range(p.filas):
        trozos, buf, bk = [], [], None
        for c in range(p.cols):
            ch = RAMPA[idx[f, c]]
            a = int(round(A[f, c] / amax * (N_AMP - 1)))
            base[a].append(float(C[f, c]))
            ph = int(round(((PHI[f, c] + math.pi) / (2 * math.pi)) * N_FASE)) % N_FASE
            k = (a, ph) if ch != " " else None
            if k != bk and buf:
                trozos.append((bk, "".join(buf)))
                buf = []
            bk = k
            buf.append(ch)
            if k:
                usadas.add(k)
        if buf:
            trozos.append((bk, "".join(buf)))
        cuerpo = "".join(escape(t) if k is None
                         else f'<tspan class="a{k[0]}p{k[1]}">{escape(t)}</tspan>'
                         for k, t in trozos)
        filas.append(f'<tspan x="{p.x0:.0f}" dy="{p.adv_y:.0f}">{cuerpo}</tspan>')

    css = []
    for a, ph in sorted(usadas):
        amp = a / (N_AMP - 1)
        # I = C + A*cos(t - phi). C es el ambiente REAL de ese bucket (nz*LZ),
        # no un numero elegido: una celda plana mira al espectador y es la mas
        # clara aunque no oscile. el delay negativo ES la fase.
        c0 = sum(base[a]) / len(base[a]) if base[a] else LZ
        lo = max(0.05, min(1.0, c0 - 0.85 * amp))
        hi = max(lo + 0.02, min(1.0, c0 + 0.85 * amp))
        d = -CICLO_LUZ * ph / N_FASE
        css.append(f".a{a}p{ph}{{animation:luz{a} {CICLO_LUZ}s {d:.3f}s "
                   f"infinite linear}}")
        css.append(f"@keyframes luz{a}{{0%{{opacity:{hi:.3f}}}"
                   f"50%{{opacity:{lo:.3f}}}100%{{opacity:{hi:.3f}}}}}")
    # dedup de keyframes (uno por amplitud, no por par)
    css = sorted(set(css))

    leyenda = (f"depth->glifo  normal->fase de luz  |  {len(usadas)} clases  "
               f"|  rampa '{RAMPA.strip()}'")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>relieve semantico</title>
<desc>El campo semantico del repo tratado como superficie. El glifo lo decide
la altura; la iluminacion, la normal. La luz gira en 16s y no existe ningun
frame: la intensidad de cada celda es una sinusoide de la misma frecuencia y
distinta fase, asi que la fase es un animation-delay negativo.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre;fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#64748b}}
{chr(10).join(css)}
</style>
<rect width="100%" height="100%" fill="#08070a"/>
<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" xml:space="preserve">{"".join(filas)}</text>
<text class="sello" x="10" y="898">{escape(leyenda)}</text>
</svg>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida-dir", default="/tmp/proto/sistema")
    ap.add_argument("--estados", type=int, default=12)
    ap.add_argument("--sigma", type=float, default=None)
    a = ap.parse_args()

    p = Params()
    if a.sigma:
        p.sigma = a.sigma
    h = Historia(Path(a.repo), p)
    todos = h.commits()
    k = min(a.estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)

    crudos = [campo.campo(tk, 1.0) for tk in corpora]
    escala = max(float(c.max()) for c in crudos) or 1.0
    F = crudos[-1] / escala                      # HEAD
    nx, ny, nz = normales(F, p)

    d = Path(a.salida_dir)
    (d / "depth.svg").write_text(svg_mapa(
        F, p, "depth map semantico",
        "El campo escalar sin umbralar. Blanco = alta densidad semantica."),
        encoding="utf-8")
    (d / "normal.svg").write_text(svg_mapa(
        None, p, "normal map semantico",
        "Normales de la superficie semantica en tangent-space RGB.",
        rgb=(nx * .5 + .5, ny * .5 + .5, nz)), encoding="utf-8")
    (d / "relieve.svg").write_text(
        svg_relieve(F, nx, ny, nz, h.corpus(sel[-1][0]), p), encoding="utf-8")

    print(f"campo  max {F.max():.3f}  media {F.mean():.3f}")
    print(f"grad   |nx| max {np.abs(nx).max():.3f}  |ny| max {np.abs(ny).max():.3f}")
    print(f"pend   celdas con inclinacion >30deg: {(nz < math.cos(math.radians(30))).sum()}")
    for f in (d / "depth.svg", d / "normal.svg", d / "relieve.svg"):
        print(f"  {f.stat().st_size//1024:4} KB  {f}")


if __name__ == "__main__":
    main()
