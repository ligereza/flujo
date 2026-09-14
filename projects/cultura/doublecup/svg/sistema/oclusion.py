#!/usr/bin/env python3
"""oclusion.py -- la sombra de sombra.py, pero que quepa.

EL PROBLEMA CONCRETO
  sombra.py resolvio el horizon mapping y lo resolvio bien: cada celda guarda
  su curva de luz completa (N_AZ niveles cuantizados) y las celdas con la
  misma curva comparten @keyframes. El resultado real sobre /tmp/vc_test:
  2338 firmas distintas, 645 KB de CSS. sintesis.svg ya pesa 552 KB. Sumar
  las dos cosas da un archivo de mas de 1 MB para un SVG decorativo. No.

  Y el gasto no esta donde parece. Cada firma cuesta DOS cosas:
    - su @keyframes  (~90-200 bytes, depende de cuantos saltos tenga)
    - su regla .sN   (~45 bytes, y esta no se puede deduplicar)
  Con 2338 firmas, solo las reglas .sN ya son ~105 KB. Es decir: aunque los
  keyframes fuesen gratis, el presupuesto de 120 KB seguiria roto. HAY QUE
  BAJAR EL NUMERO DE CLASES, no solo el de keyframes.

LA OBSERVACION QUE LO ARREGLA
  La luz gira. Para una celda, ocluida por un unico pico, la curva de luz es
  aproximadamente la MISMA forma que la de su vecina, desplazada en azimut:
  el pico le tapa el sol un poco antes o un poco despues. Las 2338 curvas no
  son 2338 formas: son un punado de formas rotadas.

  Entonces se agrupa con distancia CICLICA: dos curvas son la misma si una es
  una rotacion de la otra. El prototipo va al @keyframes; la rotacion va al
  animation-delay negativo, que es gratis.

    clase = (prototipo k, desplazamiento s)   ->  K*N_AZ clases como mucho
    keyframes = K

  Es exactamente el truco de fase de relieve.py, pero generalizado: alli la
  curva tenia que ser una sinusoide para admitir delay; aqui admite CUALQUIER
  forma, incluidos los saltos de la oclusion, porque el prototipo se aprende
  de la escena en vez de suponerse.

  El clustering es k-means con alineacion ciclica (asignacion sobre las N_AZ
  rotaciones, centroide como media de los miembros ya alineados). Init por
  punto mas lejano, determinista: la pieza tiene que salir igual cada vez.

LO QUE SE PIERDE, DICHO SIN ADORNOS
  Se pierde detalle de forma. Una celda cuya curva tiene dos eclipses (dos
  picos distintos la tapan en dos azimuts) cae en un prototipo de un solo
  eclipse: pierde uno de los dos. El contraste medio baja poco (~4%) pero el
  error por celda no es despreciable, y la sombra queda mas "limpia" de lo
  que el relieve realmente es. Es un mapa de sombras plausible, no exacto.
  A cambio: de 645 KB a ~10 KB.

  Tambien se pierde la promesa implicita de sombra.py de que dos celdas con
  distinto CSS tienen distinta historia luminica. Aqui dos celdas de la misma
  clase pueden tener historias parecidas pero no iguales.

API
    clases, css, meta = firmas_luz(F, p)
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import Params, Historia, CampoSemantico, tokens
from relieve import RAMPA, normales


@dataclass
class Config:
    """Los parametros que mueven el trade-off tamano/fidelidad."""
    n_az: int = 24          # azimuts: resolucion temporal de la curva
    niveles: int = 10       # cuantizacion de la opacidad
    k_proto: int = 64       # prototipos de curva (0 = sin clustering, dedup exacto)
    # k_proto satura: por encima de ~32 los prototipos extra salen casi planos,
    # colapsan a clase estatica y el CSS no crece. Se deja 64 por margen.
    elev: float = 22.0      # elevacion de la luz en grados
    penumbra: float = 7.0   # banda de transicion sombra/luz
    altura: float = 150.0   # px de relieve para F=1: define cuanto ocluye
    pasos: int = 46         # pasos de marcha del rayo
    paso_px: float = 9.0
    amb: float = 0.10       # ambiente: la sombra no es negro absoluto
    ciclo: float = 20.0     # s por vuelta de la luz
    iters: int = 12         # iteraciones de k-means


CFG = Config()


# ------------------------------------------------------------------ el campo


def horizontes(F, p: Params, cfg: Config = CFG) -> np.ndarray:
    """h[a,f,c] = tangente del angulo de horizonte de (f,c) hacia el azimut a.

    Mismo metodo que sombra.py, reimplementado aqui para que el modulo no
    dependa de constantes de modulo ajenas (sombra.py fija N_AZ global y este
    modulo necesita barrerlo). Vectorizado: se desplaza la grilla entera.
    """
    H = F * cfg.altura
    nf, nc = p.filas, p.cols
    fi, ci = np.mgrid[0:nf, 0:nc]
    out = np.zeros((cfg.n_az, nf, nc))
    for a in range(cfg.n_az):
        th = 2 * math.pi * a / cfg.n_az
        dx, dy = math.cos(th), math.sin(th)
        mx = np.zeros((nf, nc))
        for s in range(1, cfg.pasos + 1):
            r = s * cfg.paso_px
            cc = np.clip(np.round(ci + dx * r / p.adv_x).astype(int), 0, nc - 1)
            ff = np.clip(np.round(fi + dy * r / p.adv_y).astype(int), 0, nf - 1)
            mx = np.maximum(mx, (H[ff, cc] - H) / r)
        out[a] = mx
    return out


def intensidades(F, p: Params, cfg: Config = CFG) -> np.ndarray:
    """I[a,f,c] en 0..1: Lambert difuso por la normal, atenuado por oclusion."""
    nx, ny, nz = normales(F, p)
    lz = math.sin(math.radians(cfg.elev))
    lh = math.cos(math.radians(cfg.elev))
    HZ = horizontes(F, p, cfg)
    tan_luz = math.tan(math.radians(cfg.elev))
    tan_pen = math.tan(math.radians(cfg.elev + cfg.penumbra))
    I = np.zeros((cfg.n_az, p.filas, p.cols))
    for a in range(cfg.n_az):
        th = 2 * math.pi * a / cfg.n_az
        lam = np.clip(nx * (lh * math.cos(th)) + ny * (lh * math.sin(th))
                      + nz * lz, 0.0, 1.0)
        v = np.clip((tan_pen - HZ[a]) / (tan_pen - tan_luz + 1e-9), 0.0, 1.0)
        I[a] = cfg.amb + (1.0 - cfg.amb) * lam * v
    return I / (float(I.max()) or 1.0)


# ------------------------------------------------------- clustering ciclico


def _rotaciones(C: np.ndarray) -> np.ndarray:
    """Rs[s] = cada curva rotada -s posiciones. Comparar una curva contra un
    prototipo rotado +s es lo mismo que comparar la curva rotada -s contra el
    prototipo, y asi el prototipo no se toca en el bucle."""
    n = C.shape[1]
    return np.stack([np.roll(C, -s, axis=1) for s in range(n)])


def _asignar(Rs: np.ndarray, P: np.ndarray):
    """Para cada curva, el par (prototipo, rotacion) que menos error da."""
    n, N, _ = Rs.shape
    pn = (P * P).sum(1)
    best = np.full(N, np.inf)
    bk = np.zeros(N, dtype=int)
    bs = np.zeros(N, dtype=int)
    for s in range(n):
        D = -2.0 * (Rs[s] @ P.T) + pn          # falta ||c||^2, constante en s y k
        k = D.argmin(1)
        d = D[np.arange(N), k]
        m = d < best
        best[m], bk[m], bs[m] = d[m], k[m], s
    return bk, bs, best


def agrupar(C: np.ndarray, k_proto: int, iters: int):
    """k-means con alineacion ciclica sobre las curvas de luz.

    Devuelve (P, ik, is_) con P[k] los prototipos y (ik,is_) la clase de cada
    curva. Init por punto mas lejano: determinista, sin semilla aleatoria,
    porque una pieza generativa que sale distinta cada corrida no es una pieza,
    es un accidente.
    """
    N, n = C.shape
    Rs = _rotaciones(C)
    k_proto = min(k_proto, N)

    # semilla: la curva de mayor contraste, luego siempre la mas lejana
    P = C[np.argmax(C.max(1) - C.min(1))][None, :].copy()
    mind = None
    while len(P) < k_proto:
        _, _, d = _asignar(Rs, P)
        mind = d if mind is None else np.minimum(mind, d)
        P = np.vstack([P, C[int(np.argmax(mind))]])
        mind = None

    for _ in range(iters):
        ik, is_, _ = _asignar(Rs, P)
        nuevo = P.copy()
        for k in range(len(P)):
            m = ik == k
            if not m.any():
                continue
            # la media se toma sobre los miembros YA alineados a su rotacion
            nuevo[k] = np.stack([Rs[s, i] for i, s in
                                 zip(np.nonzero(m)[0], is_[m])]).mean(0)
        if np.allclose(nuevo, P, atol=1e-6):
            P = nuevo
            break
        P = nuevo
    ik, is_, _ = _asignar(Rs, P)
    return P, ik, is_


# ----------------------------------------------------------------- emision


def _num(v: float) -> str:
    """Numero CSS lo mas corto posible: 0.25 -> .25, 1.00 -> 1."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    if s.startswith("0."):
        s = s[1:]
    return s or "0"


def _keyframes(curva, n_az: int) -> str:
    """Solo se emite el stop donde la curva CAMBIA: esta cuantizada, o sea que
    es escalonada, y los tramos planos no necesitan punto intermedio."""
    stops, prev = [], None
    for a, q in enumerate(curva):
        if q != prev:
            pc = f"{100.0 * a / n_az:.1f}".rstrip("0").rstrip(".")
            stops.append(f"{pc}%{{opacity:{_num(q)}}}")
            prev = q
    if curva[0] != prev:
        stops.append(f"100%{{opacity:{_num(curva[0])}}}")
    return "".join(stops)


def firmas_luz(F: np.ndarray, p: Params, cfg: Config = CFG):
    """Sombra por oclusion comprimida a clases CSS.

    F   -- campo semantico normalizado (filas, cols), tratado como altura.
    p   -- Params de motor.py (grilla y avances).
    cfg -- Config: n_az, niveles, k_proto son los que mueven el tamano.

    Devuelve (clases, css, meta):
      clases -- int (filas, cols), indice de clase .sN por celda; -1 si la
                celda no lleva glifo (el fondo no se anima).
      css    -- str con los @keyframes y las reglas .sN, listo para <style>.
      meta   -- dict: n_firmas, kb, contraste_medio, y el error de la
                compresion, que es el numero que hay que mirar con recelo.
    """
    I = intensidades(F, p, cfg)
    n = cfg.n_az

    # que celdas llevan glifo: mismo criterio que sombra.py (la rampa por altura)
    Fn = F / (float(F.max()) or 1.0)
    idx = np.clip((Fn ** 0.65 * (len(RAMPA) - 1)).round().astype(int),
                  0, len(RAMPA) - 1)
    vivas = np.array([[RAMPA[idx[f, c]] != " " for c in range(p.cols)]
                      for f in range(p.filas)])

    clases = np.full((p.filas, p.cols), -1, dtype=int)
    if not vivas.any():
        return clases, "", {"n_firmas": 0, "kb": 0.0, "contraste_medio": 0.0,
                            "error_medio": 0.0, "n_keyframes": 0}

    C = I[:, vivas].T.astype(float)            # (N celdas vivas, n_az)

    if cfg.k_proto and cfg.k_proto > 0:
        P, ik, is_ = agrupar(C, cfg.k_proto, cfg.iters)
        recon = np.stack([np.roll(P[k], s) for k, s in zip(ik, is_)])
    else:
        # baseline: el metodo de sombra.py, dedup exacto sobre la curva cuantizada
        Q = np.clip((C * (cfg.niveles - 1)).round().astype(int),
                    0, cfg.niveles - 1)
        _, ik = np.unique(Q, axis=0, return_inverse=True)
        is_ = np.zeros(len(C), dtype=int)
        P = np.unique(Q, axis=0) / (cfg.niveles - 1)
        recon = P[ik]

    # cuantizar los prototipos: menos niveles = menos stops = menos bytes
    Qp = np.clip((P * (cfg.niveles - 1)).round().astype(int), 0,
                 cfg.niveles - 1)
    Qv = Qp / (cfg.niveles - 1)

    # un prototipo constante no necesita animacion ni rotacion: todas sus
    # rotaciones son la misma clase estatica. Esto solo se ve despues de
    # cuantizar, y se lleva unas cuantas clases por delante.
    plano = (Qp == Qp[:, :1]).all(1)

    # tabla de clases realmente usadas: (prototipo, rotacion) -> indice
    llaves = {}
    ids = np.zeros(len(ik), dtype=int)
    for i, (k, s) in enumerate(zip(ik, is_)):
        lla = (int(k), 0 if plano[k] else int(s))
        j = llaves.get(lla)
        if j is None:
            j = llaves[lla] = len(llaves)
        ids[i] = j
    clases[vivas] = ids

    reglas, kf, hechos = [], [], set()
    for (k, s), j in llaves.items():
        if plano[k]:
            reglas.append(f".s{j}{{opacity:{_num(Qv[k, 0])}}}")
            continue
        if k not in hechos:
            kf.append(f"@keyframes k{k}{{{_keyframes(Qp[k] / (cfg.niveles - 1), n)}}}")
            hechos.add(k)
        # la rotacion s es un delay negativo: curva[a] = proto[a-s]
        d = cfg.ciclo * ((n - s) % n) / n
        det = f" -{d:.2f}s" if d else ""
        reglas.append(f".s{j}{{animation:k{k} {cfg.ciclo:g}s{det} "
                      f"infinite linear}}")
    css = "\n".join(kf + reglas)

    # metricas sobre la curva REALMENTE emitida, no sobre la ideal
    emitida = np.stack([np.roll(Qv[k], 0 if plano[k] else s)
                        for k, s in zip(ik, is_)])
    contraste = float((emitida.max(1) - emitida.min(1)).mean())
    error = float(np.abs(emitida - C).mean())
    meta = {
        "n_firmas": len(llaves),
        "n_keyframes": len(kf),
        "kb": round(len(css.encode("utf-8")) / 1024.0, 1),
        "contraste_medio": round(contraste, 4),
        "contraste_ideal": round(float((C.max(1) - C.min(1)).mean()), 4),
        "error_medio": round(error, 4),
        "celdas": int(vivas.sum()),
    }
    return clases, css, meta


# --------------------------------------------------------------- verificacion


def construir_svg(F, clases, css, meta, p: Params, cfg: Config = CFG) -> str:
    """SVG de control: la sombra sola, para mirarla y decidir si se lee."""
    Fn = F / (float(F.max()) or 1.0)
    idx = np.clip((Fn ** 0.65 * (len(RAMPA) - 1)).round().astype(int),
                  0, len(RAMPA) - 1)
    filas = []
    for f in range(p.filas):
        trozos, buf, bk = [], [], None
        for c in range(p.cols):
            ch = RAMPA[idx[f, c]]
            k = int(clases[f, c])
            k = None if k < 0 else k
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

    ley = (f"{cfg.n_az} azimuts | {cfg.niveles} niveles | {meta['n_firmas']} "
           f"clases desde {cfg.k_proto} prototipos | {meta['kb']} KB CSS")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>oclusion comprimida</title>
<desc>La sombra proyectada del campo semantico tratado como relieve. Las
curvas de luz de las celdas no son miles de formas distintas: son {cfg.k_proto}
formas rotadas, porque la luz gira y un mismo pico tapa a cada vecina un poco
antes o un poco despues. El prototipo va al keyframes, la rotacion va al
animation-delay. Sin frames y sin JS.</desc>
<style>
.mat{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;
     font-size:10px;white-space:pre;fill:#f8fafc}}
.sello{{font-family:ui-monospace,monospace;font-size:9px;fill:#64748b}}
{css}
</style>
<rect width="100%" height="100%" fill="#08070a"/>
<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" xml:space="preserve">{"".join(filas)}</text>
<text class="sello" x="10" y="898">{escape(ley)}</text>
</svg>
"""


def campo_de(repo: Path, p: Params, k_estados: int = 12) -> np.ndarray:
    """El campo de HEAD, exactamente como lo arma sombra.py."""
    h = Historia(repo, p)
    todos = h.commits()
    k = min(k_estados, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)
    crudos = [campo.campo(tk, 1.0) for tk in corpora]
    return crudos[-1] / (max(float(c.max()) for c in crudos) or 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida", default="/tmp/proto/sistema/oclusion_test.svg")
    ap.add_argument("--estados", type=int, default=12)
    ap.add_argument("--barrido", action="store_true",
                    help="mide la tabla de trade-offs (tarda)")
    a = ap.parse_args()

    p = Params()
    F = campo_de(Path(a.repo), p, a.estados)

    if a.barrido:
        print(f"{'n_az':>5} {'niv':>4} {'k':>5} {'firmas':>7} {'kf':>4} "
              f"{'KB':>7} {'contr':>7} {'ideal':>7} {'err':>6}")
        combos = [(24, 8, 0), (16, 8, 0), (12, 6, 0),
                  (24, 10, 64), (24, 8, 32), (24, 6, 16),
                  (16, 6, 14), (16, 6, 8), (12, 5, 8), (12, 4, 6)]
        for n_az, niv, kp in combos:
            c = Config(n_az=n_az, niveles=niv, k_proto=kp)
            _, _, m = firmas_luz(F, p, c)
            print(f"{n_az:>5} {niv:>4} {kp or '-':>5} {m['n_firmas']:>7} "
                  f"{m['n_keyframes']:>4} {m['kb']:>7} "
                  f"{m['contraste_medio']:>7.3f} {m['contraste_ideal']:>7.3f} "
                  f"{m['error_medio']:>6.3f}")
        print()

    clases, css, meta = firmas_luz(F, p, CFG)
    svg = construir_svg(F, clases, css, meta, p, CFG)
    Path(a.salida).write_text(svg, encoding="utf-8")

    print(f"config: n_az={CFG.n_az} niveles={CFG.niveles} k_proto={CFG.k_proto}")
    for k, v in meta.items():
        print(f"  {k:16} {v}")
    print(f"  {'svg_kb':16} {len(svg.encode('utf-8')) // 1024}")
    print(f"-> {a.salida}")


if __name__ == "__main__":
    main()
