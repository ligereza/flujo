#!/usr/bin/env python3
"""union.py -- la pieza entera, con las mentiras de sintesis.py corregidas.

QUE CAMBIA RESPECTO DE sintesis.py, Y POR QUE

  1. EL RELIEVE ERA CODIGO MUERTO.
     Cada celda de cobre declaraba `opacity:AMB` y acto seguido le aplicaba
     `animation:pN` sobre LA MISMA PROPIEDAD. La animacion gana siempre: el
     ambiente calculado con las normales no pintaba un solo pixel. La leyenda
     decia "luz: relieve" y era falsa.
     Arreglo: el ambiente vive en `fill-opacity`, el pulso en `opacity`. Son
     canales distintos y se multiplican en el compositor.

  2. LA ALTURA ERA ACTIVIDAD DISFRAZADA.
     motor.py levantaba relieve donde el repo HABLA. Medido: corr 0.96 con el
     campo de actividad. Eso es decoracion con otro nombre.
     Arreglo: la altura es H = normalizar(max(E - P, 0)) de polos.py, con el
     eje de error medido por PERSISTENCIA (dias distintos con fix). El placer
     no excava: se resta como modelo nulo para descontar la locuacidad de base.
     corr(H, actividad) = 0.13. El vaso ya no dibuja donde se habla: dibuja
     donde dolio.

  3. EL VASO NO EXISTIA EL 27% DEL CICLO.
     Los primeros estados tenian area 0 y su `d` era 129 comandos al mismo
     punto. El peor frame caia justo en la costura del loop.
     Arreglo: se descartan los estados de area nula y el loop cierra
     repitiendo el ultimo, no volviendo al primero.

  4. NO HABIA SOMBRA.
     Entra oclusion.py: horizon mapping comprimido por rotacion ciclica,
     11 KB en vez de 645. La luz gira sobre el terreno de cicatrices.

  5. EL CONTRASTE ERA 1.05:1.
     La rampa de color usaba solo su cuarto frio porque `t` era min-max y la
     distribucion de PPMI esta sesgada.
     Arreglo: `t` por CUANTIL (rango), que reparte la rampa entera. Idem el
     pulso. Mas sustrato mas claro y suelo de pulso mas alto.

LAS TRES CAPAS, Y QUE AFIRMA CADA UNA
  TERRENO  el mapa de cicatrices como relieve ascii, iluminado por una luz que
           gira y que se ocluye de verdad. Es el pasado: donde se rompio.
  MATERIA  el netlist ruteado de HEAD. Es el presente: como se habla el repo
           hoy. Color = fuerza PPMI por cuantil. Pulso = misma fuerza.
  FORMA    el contorno de H a traves de la historia. Es el vaso: la referencia.

  Coding es la materia (deriva con cada commit). Codeina es la forma.
"""
from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import (Params, Historia, CampoSemantico, tokens, contorno,
                   path_d, PAL)
from relieve import normales, RAMPA
from cableado import netlist, colocar, rutear, glifos
from polos import leer_commits, masas_polares, _splat, _norm
from oclusion import firmas_luz

CICLO_HIST = 26.0
PULSO_MIN = 2.6
PULSO_MAX = 9.0
LZ = 0.55
PISO_PULSO = 0.78     # antes .62: el pulso apagaba demasiado
OP_SUSTRATO = 0.62    # antes .13: el contraste medido era 1.05:1
OP_TERRENO = 0.55


def rampa(t: float) -> str:
    """frio -> caliente. t es CUANTIL, no min-max: la rampa se usa entera."""
    paradas = [(0.00, (56, 78, 117)), (0.35, (129, 140, 248)),
               (0.62, (192, 132, 252)), (0.82, (232, 121, 249)),
               (1.00, (250, 204, 21))]
    for (a, ca), (b, cb) in zip(paradas, paradas[1:]):
        if t <= b:
            u = (t - a) / (b - a + 1e-9)
            r, g, bl = (int(round(ca[k] + (cb[k] - ca[k]) * u)) for k in range(3))
            return f"#{r:02x}{g:02x}{bl:02x}"
    return "#facc15"


# ------------------------------------------------------- altura por estado


def alturas(historia, campo, sel, p):
    """H de cada estado historico, en escala GLOBAL comun.

    polos.py da el H de HEAD. Para que la forma respire hace falta el H de
    cada momento: se corta la lista de commits en la fecha del estado y se
    recalculan las masas polares con ese prefijo. La normalizacion es unica
    para los N estados (umbral absoluto, no por cuantil): asi el area puede
    crecer, que es justamente lo que se quiere ver.
    """
    commits = leer_commits(historia)
    idx = {c["sha"]: i for i, c in enumerate(commits)}
    crudos = []
    for sha, _ in sel:
        corte = idx.get(sha, len(commits) - 1) + 1
        _, pers, plac, _ = masas_polares(commits[:corte], campo.vi)
        E = _splat(pers, campo, p)
        P = _splat(plac, campo, p)
        # la resta se hace en crudo y con P reescalado al maximo de E: si no,
        # un P medido en otras unidades borraria E entero o no lo tocaria.
        me, mp = float(E.max()), float(P.max())
        if mp > 0 and me > 0:
            P = P * (me / mp)
        crudos.append(np.maximum(E - P, 0.0))
    esc = max(float(c.max()) for c in crudos) or 1.0
    return [c / esc for c in crudos], commits


# ------------------------------------------------------------------ armado


def construir(repo: Path, p: Params, k_estados: int):
    h = Historia(repo, p)
    todos = h.commits()
    k = min(k_estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)

    Hs, commits = alturas(h, campo, sel, p)

    estados = []
    for (sha, fecha), Hf in zip(sel, Hs):
        av = int((Hf >= p.u_vidrio).sum())
        if av == 0:
            continue          # (3) un estado sin area no es un estado
        estados.append({
            "sha": sha[:7], "fecha": fecha,
            "area_vidrio": av,
            "area_liquido": int((Hf >= p.u_liquido).sum()),
            "c_vidrio": contorno(Hf, p.u_vidrio, p),
            "c_liquido": contorno(Hf, p.u_liquido, p),
        })
    F = Hs[-1]

    masas = Counter(corpora[-1])
    nodos, aristas = netlist(campo, masas, p)
    pos = colocar(nodos, campo, p)
    duro = set()
    for f, c, w in pos:
        for kk in range(-1, w + 1):
            duro.add((f, c + kk))
    blando = set()
    aristas.sort(key=lambda e: -e[2])
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
        trazas.append({"cam": cam, "v": v, "a": nodos[i], "b": nodos[j]})

    # (5) t por CUANTIL: la rampa completa, no su cuarto frio
    orden = sorted(range(len(trazas)), key=lambda k: trazas[k]["v"])
    n1 = max(1, len(trazas) - 1)
    for r, k in enumerate(orden):
        trazas[k]["t"] = r / n1
    return campo, F, estados, nodos, pos, trazas, fallidas, sel[-1], commits


# ----------------------------------------------------------------- render


def render(F, estados, nodos, pos, trazas, p, fallidas, meta_ocl_out):
    nx, ny, nz = normales(F, p)
    AMB = np.clip(0.72 + 0.40 * nz * LZ + 0.25 * F, 0.68, 1.0)

    # --- TERRENO: relieve ascii con sombra rotatoria ---------------------
    clases_ocl, css_ocl, meta_ocl = firmas_luz(F, p)
    meta_ocl_out.update(meta_ocl)
    Fn = F / (float(F.max()) or 1.0)
    gi = np.clip((Fn ** 0.65 * (len(RAMPA) - 1)).round().astype(int),
                 0, len(RAMPA) - 1)
    terreno = []
    for f in range(p.filas):
        trozos, buf, bk = [], [], None
        for c in range(p.cols):
            ch = RAMPA[gi[f, c]]
            k = int(clases_ocl[f, c]) if ch != " " else -1
            if k != bk and buf:
                trozos.append((bk, "".join(buf)))
                buf = []
            bk = k
            buf.append(ch)
        if buf:
            trozos.append((bk, "".join(buf)))
        terreno.append(f'<tspan x="{p.x0:.0f}" dy="{p.adv_y:.0f}">' + "".join(
            escape(x) if k is None or k < 0 else f'<tspan class="s{k}">{escape(x)}</tspan>'
            for k, x in trozos) + "</tspan>")
    TERRENO = (f'<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" '
               f'xml:space="preserve">{"".join(terreno)}</text>')

    # --- MATERIA: el circuito -------------------------------------------
    rej = [[None] * p.cols for _ in range(p.filas)]
    css = []
    for t, tr in enumerate(trazas):
        col = rampa(tr["t"])
        ciclo = PULSO_MAX + (PULSO_MIN - PULSO_MAX) * tr["t"]
        n = len(tr["cam"])
        css.append(f".n{t}{{fill:{col}}}")
        css.append(f"@keyframes p{t}{{0%{{opacity:1}}16%{{opacity:{PISO_PULSO}}}"
                   f"100%{{opacity:{PISO_PULSO}}}}}")
        for kk, (f, c, ch) in enumerate(glifos(tr["cam"])):
            if not (0 <= f < p.filas and 0 <= c < p.cols):
                continue
            d = -ciclo * kk / n
            # (1) ambiente en fill-opacity, pulso en opacity: canales distintos
            css.append(f".g{t}_{kk}{{fill-opacity:{float(AMB[f,c]):.2f};"
                       f"animation:p{t} {ciclo:.2f}s {d:.3f}s infinite linear}}")
            rej[f][c] = (ch, f"n{t} g{t}_{kk}")
    for w, (f, c, an) in zip(nodos, pos):
        for kk, ch in enumerate(f"[{w}]"[:an]):
            if 0 <= f < p.filas and 0 <= c + kk < p.cols:
                rej[f][c + kk] = (ch, "nodo")

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

    # --- FORMA ------------------------------------------------------------
    n = len(estados)

    def anim(clave):
        # (3) el loop cierra en el ULTIMO estado, no vuelve al primero
        vals = ";".join(path_d(e[clave]) for e in estados)
        vals += ";" + path_d(estados[-1][clave])
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
           f"  |  altura: error-placer (persistencia)  |  {meta_ocl['n_firmas']} "
           f"firmas de luz")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>vaso semantico -- union</title>
<desc>Tres capas. El TERRENO es el mapa de cicatrices del repo: altura =
persistencia del error menos el placer que la explica, iluminado por una luz
que gira y que se ocluye por horizon mapping. La MATERIA es el netlist real de
HEAD ruteado con A* ortogonal; el color y la velocidad del pulso son la fuerza
PPMI de cada conexion, repartida por cuantil. La FORMA es el contorno de esa
altura a lo largo de {n} estados de la historia. Lo de adentro deriva con cada
commit; el recipiente es la referencia que no puede derivar.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre}}
.nodo{{fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#64748b;letter-spacing:.5px}}
.terreno{{opacity:{OP_TERRENO};fill:#94a3c4}}
.sustrato{{opacity:{OP_SUSTRATO}}}
.vidrio{{opacity:1;filter:url(#cristal)}}
.liquido{{opacity:1;filter:url(#tinte)}}
.levita{{animation:levitar 9s infinite ease-in-out;transform-origin:center}}
@keyframes levitar{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}
{chr(10).join(css)}
{css_ocl}
@media (prefers-reduced-motion:reduce){{
  *{{animation:none!important}}
}}
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
<g class="terreno">{TERRENO}</g>
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
    ap.add_argument("--salida", default="/tmp/proto/sistema/union.svg")
    ap.add_argument("--estados", type=int, default=14)
    a = ap.parse_args()
    p = Params()
    (campo, F, estados, nodos, pos, trazas, fallidas,
     (sha, fecha), commits) = construir(Path(a.repo), p, a.estados)
    mo = {}
    svg = render(F, estados, nodos, pos, trazas, p, fallidas, mo)
    Path(a.salida).write_text(svg, encoding="utf-8")

    dentro = sum(1 for tr in trazas for (f, c) in tr["cam"]
                 if F[f, c] >= p.u_vidrio)
    cobre = sum(len(tr["cam"]) for tr in trazas)
    A = _norm(campo.campo(Counter(), 1.0)) if False else None
    print(f"estados con area > 0: {len(estados)}  "
          f"area {estados[0]['area_vidrio']} -> {estados[-1]['area_vidrio']}")
    print(f"trazas {len(trazas)}  sin ruta {len(fallidas)}  cobre {cobre}")
    print(f"cobre DENTRO del vaso: {dentro} ({100*dentro/max(1,cobre):.1f}%)")
    print(f"oclusion: {mo['n_firmas']} firmas  {mo['kb']:.1f} KB CSS  "
          f"contraste {mo['contraste_medio']:.3f}")
    print(f"{len(svg)//1024} KB -> {a.salida}")


if __name__ == "__main__":
    main()
