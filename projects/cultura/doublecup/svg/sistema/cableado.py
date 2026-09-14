#!/usr/bin/env python3
"""cableado.py -- el vaso como circuito. Ruteo real, no decoracion.

CONTRA LA MEDIOCRIDAD DE COPIAR LA REFERENCIA
  La referencia (pipes de LED encendidos, trazas ortogonales, color saturado)
  es bellisima y es ARBITRARIA: las tuberias no van a ningun lado, el ruteo es
  ruido con estilo. Imitar eso seria hacer un fondo de pantalla.

  Aqui las tuberias SON el grafo semantico del repo. La matriz PPMI que
  motor.py usaba solo para sacar un PCA es, literalmente, una lista de
  adyacencias: que termino aparece cerca de que termino. Eso es el netlist.
  El ruteo lo hace un A* ortogonal sobre la grilla de caracteres, como un
  autorouter de PCB: penaliza giros, esquiva lo ya ocupado, y a veces FALLA
  (y cuando falla se ve, porque la conexion no existe en la imagen).

RESPUESTA AL PROBLEMA DE LOS POLOS
  Un mapa de grises obliga a declarar que es 0 y que es 255, y yo lo estaba
  resolviendo por estadistica (el maximo de la propia serie), o sea: nunca.
  Aqui no hay rampa. Una celda esta encendida o no lo esta. La unica decision
  es binaria y es verificable: existe la arista o no existe.

  El gradiente vuelve por otro lado: el BRILLO recorre la traza. Cada celda
  de una traza recibe el mismo @keyframes con un animation-delay proporcional
  a su posicion en el camino -> el pulso viaja. Sigue sin haber frames.

  El color de cada red no es paleta: es su rango en PPMI. Las conexiones mas
  fuertes son las mas frias/saturadas, las debiles se apagan hacia el fondo.
"""
from __future__ import annotations

import argparse
import heapq
import math
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import Params, Historia, CampoSemantico, tokens

N_NODOS = 26        # terminos cableados
N_ARISTAS = 34      # conexiones intentadas (ademas del arbol de cobertura)
GIRO = 3.0
CRUCE = 12.0        # coste de cruzar otra traza (capa distinta)          # penalizacion de doblar: fuerza trazas largas y rectas
CICLO = 6.0         # s que tarda el pulso en recorrer una traza
LARGO_PULSO = 0.16  # fraccion de la traza encendida a la vez

PALETA = ["#f0abfc", "#c084fc", "#818cf8", "#38bdf8", "#2dd4bf",
          "#facc15", "#fb7185", "#e879f9"]


def netlist(campo: CampoSemantico, masas: Counter, p: Params):
    """Nodos = terminos mas pesados. Aristas = pares con mayor PPMI."""
    orden = [w for w in campo.vocab if masas.get(w)]
    orden.sort(key=lambda w: -masas[w])
    nodos = orden[:N_NODOS]
    ids = [campo.vi[w] for w in nodos]
    M = campo.PPMI[np.ix_(ids, ids)].copy()
    np.fill_diagonal(M, 0.0)

    # arbol de cobertura maxima: garantiza que el circuito sea UNO, no islas
    dentro, fuera = {0}, set(range(1, len(nodos)))
    aristas = []
    while fuera:
        mejor = max(((a, b) for a in dentro for b in fuera),
                    key=lambda ab: M[ab[0], ab[1]])
        aristas.append((mejor[0], mejor[1], float(M[mejor])))
        dentro.add(mejor[1])
        fuera.discard(mejor[1])
    # extras: los pares mas fuertes que aun no estan
    ya = {frozenset(a[:2]) for a in aristas}
    pares = sorted(((float(M[i, j]), i, j)
                    for i in range(len(nodos)) for j in range(i + 1, len(nodos))),
                   reverse=True)
    for v, i, j in pares:
        if len(aristas) >= len(nodos) - 1 + N_ARISTAS:
            break
        if frozenset((i, j)) not in ya:
            aristas.append((i, j, v))
            ya.add(frozenset((i, j)))
    return nodos, aristas


def colocar(nodos, campo, p: Params):
    """Cada nodo cae donde lo puso el PCA, redondeado a celda, sin pisarse."""
    # el PCA amontona todo en el centro: se conserva el ORDEN de cada eje pero
    # se reparte por rango. es una transformacion monotona, no una invencion:
    # quien estaba a la izquierda sigue a la izquierda.
    ix = sorted(range(len(nodos)), key=lambda k: campo.px[campo.vi[nodos[k]]])
    iy = sorted(range(len(nodos)), key=lambda k: campo.py[campo.vi[nodos[k]]])
    rx = {k: n for n, k in enumerate(ix)}
    ry = {k: n for n, k in enumerate(iy)}
    N = max(1, len(nodos) - 1)

    pos, tomadas = [], set()
    for idx, w in enumerate(nodos):
        i = campo.vi[w]
        c0 = int(round(2 + rx[idx] / N * (p.cols - 16)))
        f0 = int(round(2 + ry[idx] / N * (p.filas - 5)))
        ancho = len(w) + 2
        for r in range(0, 40):
            hecho = False
            for df in range(-r, r + 1):
                for dc in (-r, r) if abs(df) < r else range(-r, r + 1):
                    f, c = f0 + df, c0 + dc
                    if not (1 <= f < p.filas - 1 and 1 <= c < p.cols - ancho):
                        continue
                    cel = {(f, c + k) for k in range(ancho)}
                    if cel & tomadas:
                        continue
                    tomadas |= cel
                    pos.append((f, c, ancho))
                    hecho = True
                    break
                if hecho:
                    break
            if hecho:
                break
        else:
            pos.append((f0, c0, ancho))
    return pos


def rutear(a, b, duro, blando, p: Params):
    """A* ortogonal con penalizacion de giro. Devuelve el camino o None.

    El estado incluye la direccion de llegada: sin eso, penalizar giros es
    imposible y el ruteo sale como fideo.
    """
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    ini, fin = a, b

    def h(n):
        return abs(n[0] - fin[0]) * 1.0 + abs(n[1] - fin[1]) * 1.0

    pq = [(h(ini), 0.0, ini, -1)]
    visto = {}
    padre = {}
    while pq:
        _, g, n, d = heapq.heappop(pq)
        if (n, d) in visto and visto[(n, d)] <= g:
            continue
        visto[(n, d)] = g
        if n == fin:
            cam, k = [n], (n, d)
            while k in padre:
                k = padre[k]
                cam.append(k[0])
            return cam[::-1]
        for nd, (df, dc) in enumerate(dirs):
            m = (n[0] + df, n[1] + dc)
            if not (0 <= m[0] < p.filas and 0 <= m[1] < p.cols):
                continue
            if m != fin and m in duro:
                continue
            # cruzar otra traza es caro pero legal: un circuito real tiene
            # capas. si no, el 85% de las conexiones no encuentra camino y la
            # imagen miente por omision.
            ng = (g + 1.0 + (GIRO if d != -1 and nd != d else 0.0)
                  + (CRUCE if m in blando else 0.0))
            if (m, nd) in visto and visto[(m, nd)] <= ng:
                continue
            padre[(m, nd)] = (n, d)
            heapq.heappush(pq, (ng + h(m), ng, m, nd))
    return None


GLIFO = {(0, 1): "-", (1, 0): "|",
         ("esq"): "+"}


def glifos(cam):
    """Traduce el camino a caracteres ASCII con codos."""
    out = []
    for i, (f, c) in enumerate(cam):
        pa = cam[i - 1] if i else None
        si = cam[i + 1] if i + 1 < len(cam) else None
        ejes = set()
        for o in (pa, si):
            if o:
                ejes.add("h" if o[0] == f else "v")
        ch = "+" if len(ejes) > 1 else ("-" if "h" in ejes else "|")
        out.append((f, c, ch))
    return out


def construir(repo: Path, p: Params, estados: int):
    h = Historia(repo, p)
    todos = h.commits()
    k = min(estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)
    masas = Counter(corpora[-1])

    nodos, aristas = netlist(campo, masas, p)
    pos = colocar(nodos, campo, p)

    duro = set()
    for f, c, w in pos:
        for kk in range(-1, w + 1):
            duro.add((f, c + kk))
    blando = set()

    # rutear de fuerte a debil: la conexion importante se lleva el espacio
    aristas.sort(key=lambda e: -e[2])
    trazas, fallidas = [], []
    for i, j, v in aristas:
        fi, ci, wi = pos[i]
        fj, cj, wj = pos[j]
        a = (fi, ci + wi)          # sale por la derecha del nodo
        b = (fj, cj - 1)           # entra por la izquierda del otro
        cam = rutear(a, b, duro - {a, b}, blando, p)
        if cam is None:
            fallidas.append((nodos[i], nodos[j]))
            continue
        blando.update(cam)
        trazas.append((cam, v, nodos[i], nodos[j]))
    return campo, nodos, pos, trazas, fallidas, masas, sel[-1]


def render(nodos, pos, trazas, masas, p: Params, sha, fecha, fallidas):
    rej = [[None] * p.cols for _ in range(p.filas)]   # (char, clase)
    vs = [t[1] for t in trazas] or [1.0]
    lo, hi = min(vs), max(vs)

    css = []
    for t, (cam, v, wa, wb) in enumerate(trazas):
        col = PALETA[t % len(PALETA)]
        fuerza = (v - lo) / (hi - lo + 1e-9)
        base = 0.30 + 0.42 * fuerza
        n = len(cam)
        css.append(f".n{t}{{fill:{col};opacity:{base:.2f}}}")
        for k, (f, c, ch) in enumerate(glifos(cam)):
            if not (0 <= f < p.filas and 0 <= c < p.cols):
                continue
            # el pulso viaja: la fase es la posicion en el camino
            d = -CICLO * k / n
            cls = f"n{t} g{t}_{k}"
            css.append(f".g{t}_{k}{{animation:pulso{t} {CICLO}s {d:.3f}s infinite linear}}")
            rej[f][c] = (ch, cls)
        w = max(0.5, LARGO_PULSO * 100)
        css.append(f"@keyframes pulso{t}{{0%{{opacity:1}}{w:.1f}%{{opacity:{base:.2f}}}"
                   f"100%{{opacity:{base:.2f}}}}}")

    for idx, (w, (f, c, an)) in enumerate(zip(nodos, pos)):
        etiqueta = f"[{w}]"
        for k, ch in enumerate(etiqueta[:an]):
            if 0 <= f < p.filas and 0 <= c + k < p.cols:
                m = masas.get(w, 1)
                rej[f][c + k] = (ch, "nodo")

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
            escape(t) if k is None else f'<tspan class="{k}">{escape(t)}</tspan>'
            for k, t in trozos) + "</tspan>")

    ley = (f"{len(nodos)} nodos  {len(trazas)} trazas ruteadas  "
           f"{len(fallidas)} sin ruta  |  {fecha} {sha[:7]}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>cableado semantico</title>
<desc>El netlist no es inventado: los nodos son los terminos con que el repo
se describe hoy y las trazas son sus adyacencias PPMI reales. El ruteo lo hace
un A* ortogonal con penalizacion de giro sobre la grilla de caracteres, y las
conexiones que no encuentran camino simplemente no aparecen. El pulso recorre
cada traza sin un solo frame: la fase de cada celda es su posicion en el
camino.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre}}
.nodo{{fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#475569}}
{chr(10).join(css)}
</style>
<rect width="100%" height="100%" fill="#05040a"/>
<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" xml:space="preserve">{"".join(filas)}</text>
<text class="sello" x="10" y="898">{escape(ley)}</text>
</svg>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida", default="/tmp/proto/sistema/cableado.svg")
    ap.add_argument("--estados", type=int, default=12)
    a = ap.parse_args()
    p = Params()
    campo, nodos, pos, trazas, fallidas, masas, (sha, fecha) = construir(
        Path(a.repo), p, a.estados)
    svg = render(nodos, pos, trazas, masas, p, sha, fecha, fallidas)
    Path(a.salida).write_text(svg, encoding="utf-8")
    largo = sum(len(t[0]) for t in trazas)
    print(f"nodos {len(nodos)} | trazas {len(trazas)} | sin ruta {len(fallidas)}")
    if fallidas:
        print("  sin ruta: " + ", ".join(f"{a}~{b}" for a, b in fallidas[:8]))
    print(f"celdas de cobre {largo} de {p.filas*p.cols} "
          f"({100*largo/(p.filas*p.cols):.1f}% de ocupacion)")
    print(f"{len(svg)//1024} KB -> {a.salida}")


if __name__ == "__main__":
    main()
