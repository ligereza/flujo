#!/usr/bin/env python3
"""sintesis.py -- reintegracion. Todo lo anterior en una sola pieza.

QUE VUELVE, Y DE DONDE

  v1 (la obra)       la anatomia de dos capas: MATERIA (un bloque de texto
                     monoespaciado) y FORMA (una mascara tallada encima).
                     "el vaso emerge del coloreado, no del texto".
  prototipo_01       capas con GLIFOS IDENTICOS en POSICIONES IDENTICAS no
                     hierven al superponerse: solo migra el color de celda a
                     celda. Aqui hay tres copias del mismo bloque.
  motor.py           la forma no se impone: se deriva del campo semantico, y
                     muta de forma continua entre 12 estados con SMIL sobre
                     `d`. El area respira porque el umbral es absoluto.
  relieve.py         el campo es un mapa de altura. Su iluminacion difusa da
                     el AMBIENTE de cada celda: la topografia sigue ahi,
                     debajo del circuito, decidiendo que zona esta iluminada.
  cableado.py        la materia ya no es el corpus: es el netlist ruteado.
                     A* ortogonal sobre la grilla de caracteres.

LO QUE SE CORRIGE (los dos adornos disfrazados de dato que confese)
  1. el COLOR de cada red ya no es paleta rotativa: es su PPMI mapeado a una
     rampa fria->caliente. Conexion fuerte = caliente.
  2. la VELOCIDAD del pulso ya no es constante: el ciclo es inversamente
     proporcional a la fuerza. Lo que el repo tiene mas trillado, late mas
     rapido.

LA TESIS QUE CIERRA
  Coding y codeina se reparten las dos capas y no se tocan:
    la MATERIA es el proyecto (netlist, deriva con cada commit, es coding)
    la FORMA es el vaso (contorno, es la referencia fija, es codeina)
  Una imagen contiene informacion potencial que hay que LEER para que valga.
  Aqui hay dos lecturas superpuestas y ninguna tapa a la otra: de lejos es un
  vaso; de cerca es el grafo real de lo que el repo dice de si mismo.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import (Params, Historia, CampoSemantico, tokens, contorno,
                   path_d, PAL)
from relieve import normales
from cableado import netlist, colocar, rutear, glifos, CRUCE

CICLO_HIST = 26.0     # s del recorrido por la historia
PULSO_MIN = 2.6       # s -- traza mas fuerte (late mas rapido)
PULSO_MAX = 9.0       # s -- traza mas debil
LZ = 0.55


def rampa(t: float) -> str:
    """frio -> caliente. t=0 conexion debil, t=1 conexion fuerte."""
    paradas = [(0.00, (56, 78, 117)), (0.35, (129, 140, 248)),
               (0.62, (192, 132, 252)), (0.82, (232, 121, 249)),
               (1.00, (250, 204, 21))]
    for (a, ca), (b, cb) in zip(paradas, paradas[1:]):
        if t <= b:
            u = (t - a) / (b - a + 1e-9)
            r, g, bl = (int(round(ca[k] + (cb[k] - ca[k]) * u)) for k in range(3))
            return f"#{r:02x}{g:02x}{bl:02x}"
    return "#facc15"


def construir(repo: Path, p: Params, k_estados: int):
    h = Historia(repo, p)
    todos = h.commits()
    k = min(k_estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)

    crudos = [campo.campo(tk, 1.0) for tk in corpora]
    escala = max(float(c.max()) for c in crudos) or 1.0
    estados = []
    for (sha, fecha), tk, c in zip(sel, corpora, crudos):
        F = c / escala
        estados.append({
            "sha": sha[:7], "fecha": fecha, "tokens": len(tk),
            "area_vidrio": int((F >= p.u_vidrio).sum()),
            "area_liquido": int((F >= p.u_liquido).sum()),
            "c_vidrio": contorno(F, p.u_vidrio, p),
            "c_liquido": contorno(F, p.u_liquido, p),
        })
    F = crudos[-1] / escala

    # --- materia: el circuito de HEAD ------------------------------------
    masas = Counter(corpora[-1])
    nodos, aristas = netlist(campo, masas, p)
    pos = colocar(nodos, campo, p)
    duro = set()
    for f, c, w in pos:
        for kk in range(-1, w + 1):
            duro.add((f, c + kk))
    blando = set()
    aristas.sort(key=lambda e: -e[2])
    vs = [a[2] for a in aristas] or [1.0]
    lo, hi = min(vs), max(vs)
    trazas, fallidas = [], []
    for i, j, v in aristas:
        fi, ci, wi = pos[i]
        fj, cj, _ = pos[j]
        a, b = (fi, ci + wi), (fj, cj - 1)
        cam = rutear(a, b, duro - {a, b}, blando, p)
        if cam is None:
            fallidas.append((nodos[i], nodos[j]))
            continue
        blando.update(cam)
        trazas.append({"cam": cam, "v": v,
                       "t": (v - lo) / (hi - lo + 1e-9),
                       "a": nodos[i], "b": nodos[j]})
    return campo, F, estados, nodos, pos, trazas, fallidas, sel[-1]


def render(F, estados, nodos, pos, trazas, p: Params, sha, fecha, fallidas):
    # --- ambiente: el relieve sigue debajo, decidiendo el brillo base -----
    nx, ny, nz = normales(F, p)
    AMB = np.clip(0.52 + 0.55 * nz * LZ + 0.30 * (F / (F.max() or 1)), 0.45, 1.0)

    rej = [[None] * p.cols for _ in range(p.filas)]
    css = []
    for t, tr in enumerate(trazas):
        col = rampa(tr["t"])
        ciclo = PULSO_MAX + (PULSO_MIN - PULSO_MAX) * tr["t"]
        n = len(tr["cam"])
        css.append(f".n{t}{{fill:{col}}}")
        css.append(f"@keyframes p{t}{{0%{{opacity:1}}16%{{opacity:.62}}"
                   f"100%{{opacity:.62}}}}")
        for kk, (f, c, ch) in enumerate(glifos(tr["cam"])):
            if not (0 <= f < p.filas and 0 <= c < p.cols):
                continue
            d = -ciclo * kk / n
            amb = float(AMB[f, c])
            css.append(f".g{t}_{kk}{{opacity:{amb:.2f};"
                       f"animation:p{t} {ciclo:.2f}s {d:.3f}s infinite linear}}")
            rej[f][c] = (ch, f"n{t} g{t}_{kk}")
    for w, (f, c, an) in zip(nodos, pos):
        for kk, ch in enumerate(f"[{w}]"[:an]):
            if 0 <= f < p.filas and 0 <= c + kk < p.cols:
                rej[f][c + kk] = (ch, "nodo")

    # --- el bloque de materia: UNA vez, glifos identicos en las 3 copias ---
    filas = []
    for f in range(p.filas):
        trozos, buf, bk = [], [], None
        for c in range(p.cols):
            cel = rej[f][c]
            ch, k = (cel[0], cel[1]) if cel else (" ", None)
            if k != bk and buf:
                trozos.append((bk, "".join(buf)))
                buf = []
            bk = k
            buf.append(ch)
        if buf:
            trozos.append((bk, "".join(buf)))
        filas.append(f'<tspan x="{p.x0:.0f}" dy="{p.adv_y:.0f}">' + "".join(
            escape(x) if k is None else f'<tspan class="{k}">{escape(x)}</tspan>'
            for k, x in trozos) + "</tspan>")
    BLOQUE = (f'<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" '
              f'xml:space="preserve">{"".join(filas)}</text>')

    # --- forma: el contorno que respira ----------------------------------
    n = len(estados)
    def anim(clave):
        vals = ";".join(path_d(e[clave]) for e in estados)
        vals += ";" + path_d(estados[0][clave])
        return (f'<animate attributeName="d" dur="{CICLO_HIST}s" '
                f'repeatCount="indefinite" calcMode="spline" '
                f'keySplines="{" ".join(["0.4 0 0.2 1"] * n)}" values="{vals}"/>')

    sellos = ""
    for i, e in enumerate(estados):
        sellos += (f'<text class="sello" x="10" y="898" opacity="0">'
                   f'{escape(e["fecha"])}  {e["sha"]}  {e["area_vidrio"]} celdas'
                   f'<animate attributeName="opacity" dur="{CICLO_HIST}s" '
                   f'repeatCount="indefinite" values="0;0;1;1;0;0" '
                   f'keyTimes="0;{i/n:.4f};{(i+.04)/n:.4f};{(i+.96)/n:.4f};'
                   f'{(i+1)/n:.4f};1"/></text>')

    ley = (f"{len(nodos)} nodos  {len(trazas)} trazas  {len(fallidas)} sin ruta"
           f"  |  materia: netlist  forma: campo  luz: relieve")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>vaso semantico -- sintesis</title>
<desc>Dos capas que no se tocan. La MATERIA es el circuito real del proyecto:
los terminos con que el repo se describe hoy, ruteados por sus co-ocurrencias.
La FORMA es el vaso: el contorno del campo semantico, que respira entre {n}
estados de la historia. Lo de adentro deriva con cada commit; el recipiente es
la referencia que no puede derivar. De lejos es un vaso, de cerca es un grafo.
El brillo base de cada celda lo da el relieve del propio campo; el pulso viaja
mas rapido por las conexiones mas fuertes.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre}}
.nodo{{fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#475569;letter-spacing:.5px}}
.sustrato{{opacity:.13}}
.vidrio{{opacity:1;filter:url(#cristal)}}
.liquido{{opacity:1;filter:url(#tinte)}}
.levita{{animation:levitar 9s infinite ease-in-out;transform-origin:center}}
@keyframes levitar{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}
{chr(10).join(css)}
</style>
<defs>
  <filter id="cristal"><feColorMatrix type="matrix" values="
     0.9 0.9 0.9 0 0.15
     0.9 0.95 0.95 0 0.17
     0.95 0.95 1.0 0 0.20
     0 0 0 1 0"/></filter>
  <filter id="tinte"><feColorMatrix type="matrix" values="
     1.25 0 0 0 0.10
     0.25 0.55 0 0 0.02
     0.90 0 1.30 0 0.22
     0 0 0 1 0"/></filter>
  <mask id="mv"><rect width="100%" height="100%" fill="black"/>
    <path fill="white" d="{path_d(estados[0]['c_vidrio'])}">{anim('c_vidrio')}</path></mask>
  <mask id="ml"><rect width="100%" height="100%" fill="black"/>
    <path fill="white" d="{path_d(estados[0]['c_liquido'])}">{anim('c_liquido')}</path></mask>
</defs>
<rect width="100%" height="100%" fill="{PAL['canvas']}"/>
<g class="levita">
  <g class="sustrato">{BLOQUE}</g>
  <g class="vidrio" mask="url(#mv)">{BLOQUE}</g>
  <g class="liquido" mask="url(#ml)">{BLOQUE}</g>
</g>
{sellos}
<text class="sello" x="10" y="886">{escape(ley)}</text>
</svg>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida", default="/tmp/proto/sistema/sintesis.svg")
    ap.add_argument("--estados", type=int, default=12)
    a = ap.parse_args()
    p = Params()
    campo, F, estados, nodos, pos, trazas, fallidas, (sha, fecha) = construir(
        Path(a.repo), p, a.estados)
    svg = render(F, estados, nodos, pos, trazas, p, sha, fecha, fallidas)
    Path(a.salida).write_text(svg, encoding="utf-8")

    dentro = sum(1 for tr in trazas for (f, c) in tr["cam"]
                 if F[f, c] >= p.u_vidrio)
    cobre = sum(len(tr["cam"]) for tr in trazas)
    print(f"estados {len(estados)}  area {estados[0]['area_vidrio']} -> "
          f"{estados[-1]['area_vidrio']} celdas")
    print(f"trazas {len(trazas)}  sin ruta {len(fallidas)}  cobre {cobre}")
    print(f"cobre DENTRO del vaso: {dentro} ({100*dentro/max(1,cobre):.1f}%)")
    print(f"pulso {PULSO_MAX}s (debil) -> {PULSO_MIN}s (fuerte)")
    print(f"{len(svg)//1024} KB -> {a.salida}")


if __name__ == "__main__":
    main()
