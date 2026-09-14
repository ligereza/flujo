#!/usr/bin/env python3
"""motor.py -- sistema generativo del vaso semantico.

Sucesor de prototipo_04. Deja de ser un script que produce una imagen y pasa
a ser un motor con estados, parametros y regimenes.

CAMBIO DE ARQUITECTURA (lo que lo vuelve sistema y no dibujo):

  prototipo_04:  K frames = K copias completas de la grilla, corte duro.
                 152 KB, flipbook, area constante por construccion.

  motor.py:      el MATERIAL se teje UNA sola vez (el corpus vivo de HEAD).
                 la FORMA sale del campo semantico como CONTORNO VECTORIAL,
                 y el contorno se anima con SMIL interpolando `d`.
                 -> la forma muta de manera continua, no a saltos
                 -> el navegador calcula los intermedios, no yo
                 -> el area puede crecer y encoger (umbral absoluto)

  El contorno se muestrea por 128 rayos desde el centroide del campo, asi
  que todos los estados tienen exactamente los mismos puntos y `d` interpola
  sin trucos. Limite honesto: solo formas estrelladas respecto al centroide.

REGIMENES
  --modo serie      la historia: N commits -> N estados del contorno (default)
  --modo vivo       solo HEAD: un estado, sin animacion (para regenerar por
                    visita desde un servidor)
  --modo manifiesto no dibuja: vuelca el estado derivado a JSON

CONSERVACION
  Siempre escribe un manifiesto .json junto al SVG: vocabulario, posiciones
  del mapa semantico, masas por checkpoint, umbrales y contornos. La forma
  deja de existir solo dentro del SVG. Ese era el punto unico de fallo.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict, field as dfield
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

# ---------------------------------------------------------------- parametros


@dataclass
class Params:
    filas: int = 72
    cols: int = 100
    adv_x: float = 6.0          # px por columna
    adv_y: float = 12.0         # px por fila (la celda es 1:2)
    x0: float = 10.0
    y0: float = 20.0
    vocab: int = 200
    ventana: int = 8            # ventana de co-ocurrencia
    sigma: float = 46.0         # px -- radio del grano semantico
    rayos: int = 128            # resolucion del contorno
    u_vidrio: float = 0.30      # UMBRAL ABSOLUTO (no cuantil): el area respira
    u_liquido: float = 0.62
    ciclo: float = 24.0         # s del recorrido historico
    fuentes: tuple = ("README.md", "docs/CLI.md")


PAL = {
    "canvas": "#08070a", "sustrato": "#1e293b", "vidrio": "#f8fafc",
    "liq1": "#c084fc", "liq2": "#e879f9", "liq3": "#9333ea", "sello": "#64748b",
}

STOP = set("""the a an and or of to in for on with is are be was were it its this that
these those as at by from not no if then than so such can may will shall should would
you your we our they them he she his her i me my do does did done have has had else
py python run use used using file files code repo project name new all any each per via
one two three when what which who how why there here also only more most other same
como para con los las una unos unas del que por sus este esta estos estas ser son fue
hay muy pero mas sin sobre entre desde hasta cuando donde cual quien todo toda todos
https http com www github md txt json html svg png yml yaml sh js ts tsx jsx""".split())
TOK = re.compile(r"[a-z_][a-z0-9_]{2,}")


def tokens(txt: str) -> list[str]:
    return [t for t in TOK.findall(txt.lower()) if t not in STOP and not t.isdigit()]


# ------------------------------------------------------------------- lectura


class Historia:
    """Acceso al repo como serie temporal de auto-descripciones."""

    def __init__(self, repo: Path, p: Params):
        self.repo, self.p = repo, p

    def _git(self, *a) -> str:
        r = subprocess.run(["git", "-C", str(self.repo), *a],
                           capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""

    def commits(self) -> list[tuple[str, str]]:
        out = self._git("log", "--reverse", "--format=%H|%ad", "--date=short")
        return [tuple(l.split("|")) for l in out.strip().split("\n") if "|" in l]

    def corpus(self, sha: str) -> str:
        return "\n".join(filter(None, (self._git("show", f"{sha}:{f}")
                                       for f in self.p.fuentes)))


# --------------------------------------------------------------- campo/forma


class CampoSemantico:
    """Mapa fijo de terminos + campo escalar variable en el tiempo."""

    def __init__(self, corpora: list[list[str]], p: Params):
        self.p = p
        glob = Counter()
        for tk in corpora:
            glob.update(tk)
        self.vocab = [w for w, _ in glob.most_common(p.vocab)]
        self.vi = {w: i for i, w in enumerate(self.vocab)}
        self._mapa(corpora)
        gy, gx = np.mgrid[0:p.filas, 0:p.cols]
        self.GX = p.x0 + gx * p.adv_x
        self.GY = p.y0 + gy * p.adv_y

    def _mapa(self, corpora):
        """Co-ocurrencia -> PPMI -> PCA 2D. Posiciones FIJAS en el tiempo."""
        V, p = len(self.vocab), self.p
        CO = np.zeros((V, V))
        for tk in corpora:
            ids = [self.vi[t] for t in tk if t in self.vi]
            for i, a in enumerate(ids):
                for b in ids[i + 1:i + 1 + p.ventana]:
                    CO[a, b] += 1
                    CO[b, a] += 1
        tot = CO.sum() or 1.0
        pr = CO.sum(1) / tot
        with np.errstate(divide="ignore", invalid="ignore"):
            M = np.log((CO / tot) / (np.outer(pr, pr) + 1e-12) + 1e-12)
        M = np.maximum(M, 0.0)
        self.PPMI = M      # el netlist: adyacencia semantica, no solo insumo del PCA
        U, S, _ = np.linalg.svd(M - M.mean(0), full_matrices=False)
        P = U[:, :2] * S[:2]
        for d in (0, 1):
            lo, hi = P[:, d].min(), P[:, d].max()
            P[:, d] = (P[:, d] - lo) / (hi - lo + 1e-9)
        self.px = p.x0 + P[:, 0] * (p.cols - 12) * p.adv_x
        self.py = p.y0 + P[:, 1] * (p.filas - 8) * p.adv_y

    def campo(self, tk: list[str], escala: float) -> np.ndarray:
        """Campo escalar del estado. `escala` es la norma global de la serie:
        por eso el area puede crecer -- no se normaliza cada frame por si mismo."""
        c = Counter(tk)
        F = np.zeros((self.p.filas, self.p.cols))
        s2 = 2 * self.p.sigma ** 2
        for w, m in c.items():
            i = self.vi.get(w)
            if i is None:
                continue
            d2 = (self.GX - self.px[i]) ** 2 + (self.GY - self.py[i]) ** 2
            F += math.log1p(m) * np.exp(-d2 / s2)
        return F / escala


def contorno(F: np.ndarray, umbral: float, p: Params) -> list[tuple[float, float]]:
    """Contorno por rayos desde el centroide del campo.

    Devuelve SIEMPRE p.rayos puntos, en el mismo orden angular, para que dos
    contornos distintos se puedan interpolar con `d` sin ningun ajuste.
    """
    W = np.maximum(F, 0)
    if W.sum() <= 0:
        W = np.ones_like(F)
    ys, xs = np.mgrid[0:p.filas, 0:p.cols]
    cy = p.y0 + (W * ys).sum() / W.sum() * p.adv_y
    cx = p.x0 + (W * xs).sum() / W.sum() * p.adv_x
    Rmax = math.hypot(p.cols * p.adv_x, p.filas * p.adv_y)
    pts = []
    for k in range(p.rayos):
        a = 2 * math.pi * k / p.rayos
        dx, dy = math.cos(a), math.sin(a)
        r_ok = 0.0
        r = 2.0
        while r < Rmax:
            x, y = cx + dx * r, cy + dy * r
            c = int(round((x - p.x0) / p.adv_x))
            f = int(round((y - p.y0) / p.adv_y))
            if 0 <= f < p.filas and 0 <= c < p.cols:
                if F[f, c] >= umbral:
                    r_ok = r
            r += 3.0
        pts.append((cx + dx * r_ok, cy + dy * r_ok))
    return pts


def path_d(pts) -> str:
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    d += "".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return d + "Z"


# -------------------------------------------------------------------- tejido


def tejer_material(texto: str, p: Params) -> str:
    """El material se teje UNA vez. No lleva clases: el color lo pone la mascara."""
    flujo = re.sub(r"\s+", " ", texto).strip() or " "
    filas, i = [], 0
    for _ in range(p.filas):
        trozo = []
        for _ in range(p.cols):
            trozo.append(flujo[i])
            i = (i + 1) % len(flujo)
        filas.append(f'<tspan x="{p.x0:.0f}" dy="{p.adv_y:.0f}">'
                     f'{escape("".join(trozo))}</tspan>')
    return "".join(filas)


def construir(repo: Path, p: Params, k_estados: int, modo: str):
    h = Historia(repo, p)
    todos = h.commits()
    if not todos:
        raise SystemExit("sin historia git")
    if modo == "vivo":
        sel = [todos[-1]]
    else:
        k = min(k_estados, len(todos))
        sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)] \
            if k > 1 else [todos[-1]]

    estados = []
    for sha, fecha in sel:
        txt = h.corpus(sha)
        estados.append({"sha": sha[:7], "fecha": fecha, "texto": txt,
                        "tokens": tokens(txt)})
    campo = CampoSemantico([e["tokens"] for e in estados], p)

    # escala global: el pico maximo de TODA la serie. asi el area respira.
    crudos = [campo.campo(e["tokens"], 1.0) for e in estados]
    escala = max(float(c.max()) for c in crudos) or 1.0
    for e, c in zip(estados, crudos):
        F = c / escala
        e["campo_max"] = float(F.max())
        e["area_vidrio"] = int((F >= p.u_vidrio).sum())
        e["area_liquido"] = int((F >= p.u_liquido).sum())
        e["c_vidrio"] = contorno(F, p.u_vidrio, p)
        e["c_liquido"] = contorno(F, p.u_liquido, p)
    return estados, campo, escala


def render(estados, p: Params) -> str:
    mat = tejer_material(estados[-1]["texto"], p)
    n = len(estados)
    dur = f"{p.ciclo}s"

    def anim(clave):
        vals = ";".join(path_d(e[clave]) for e in estados)
        if n > 1:
            vals += ";" + path_d(estados[0][clave])
        return (f'<animate attributeName="d" dur="{dur}" repeatCount="indefinite" '
                f'calcMode="spline" keySplines="{" ".join(["0.4 0 0.2 1"] * n)}" '
                f'values="{vals}"/>') if n > 1 else ""

    sellos = ""
    if n > 1:
        paso = p.ciclo / n
        for i, e in enumerate(estados):
            sellos += (f'<text class="sello" x="10" y="898" opacity="0">'
                       f'{escape(e["fecha"])}  {e["sha"]}  '
                       f'{e["area_vidrio"]} celdas'
                       f'<animate attributeName="opacity" dur="{dur}" '
                       f'repeatCount="indefinite" values="0;0;1;1;0;0" '
                       f'keyTimes="0;{i/n:.4f};{(i+.03)/n:.4f};'
                       f'{(i+.97)/n:.4f};{(i+1)/n:.4f};1"/></text>')
    else:
        e = estados[0]
        sellos = (f'<text class="sello" x="10" y="898">{escape(e["fecha"])}  '
                  f'{e["sha"]}  {e["area_vidrio"]} celdas  [vivo]</text>')

    css = f"""
.mat {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
        "Liberation Mono", monospace; font-size:10px; white-space:pre; }}
.sello {{ font-family: ui-monospace, monospace; font-size:9px;
          fill:{PAL['sello']}; letter-spacing:.5px; }}
.sustrato {{ fill:{PAL['sustrato']}; opacity:.35; }}
.vidrio {{ fill:{PAL['vidrio']}; }}
.liquido {{ fill:{PAL['liq1']}; animation: pulso 5s infinite alternate ease-in-out; }}
@keyframes pulso {{ 0%{{fill:{PAL['liq3']}}} 50%{{fill:{PAL['liq1']}}}
                    100%{{fill:{PAL['liq2']}}} }}
.levita {{ animation: levitar 7s infinite ease-in-out; transform-origin:center; }}
@keyframes levitar {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}} }}
"""
    T = (f'<text class="mat" x="{p.x0:.0f}" y="{p.y0:.0f}" '
         f'xml:space="preserve">{mat}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676 904" width="100%" height="100%">
<title>vaso semantico -- sistema generativo</title>
<desc>El material se teje una vez: el corpus vivo del repo. La forma es el
contorno de un campo semantico derivado de la historia real del proyecto, y
muta de forma continua entre {n} estados. El navegador calcula los
intermedios. Umbral absoluto: el area del vaso crece y encoge con el peso
semantico, no esta fijada por diseno.</desc>
<style>{css}</style>
<defs>
  <mask id="mv"><rect width="100%" height="100%" fill="black"/>
    <path fill="white" d="{path_d(estados[0]['c_vidrio'])}">{anim('c_vidrio')}</path></mask>
  <mask id="ml"><rect width="100%" height="100%" fill="black"/>
    <path fill="white" d="{path_d(estados[0]['c_liquido'])}">{anim('c_liquido')}</path></mask>
</defs>
<rect width="100%" height="100%" fill="{PAL['canvas']}"/>
<g class="levita">
  <g class="sustrato">{T}</g>
  <g class="vidrio" mask="url(#mv)">{T}</g>
  <g class="liquido" mask="url(#ml)">{T}</g>
</g>
{sellos}
</svg>
"""


def manifiesto(estados, campo, escala, p: Params) -> dict:
    return {
        "sistema": "vaso-semantico/motor.py",
        "params": asdict(p),
        "escala_global": escala,
        "mapa": [{"termino": w, "x": round(float(campo.px[i]), 2),
                  "y": round(float(campo.py[i]), 2)}
                 for i, w in enumerate(campo.vocab)],
        "estados": [{
            "sha": e["sha"], "fecha": e["fecha"], "chars": len(e["texto"]),
            "tokens": len(e["tokens"]), "campo_max": round(e["campo_max"], 4),
            "area_vidrio": e["area_vidrio"], "area_liquido": e["area_liquido"],
            "contorno_vidrio": [[round(x, 1), round(y, 1)] for x, y in e["c_vidrio"]],
            "contorno_liquido": [[round(x, 1), round(y, 1)] for x, y in e["c_liquido"]],
        } for e in estados],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/vc_test")
    ap.add_argument("--salida", default="/tmp/proto/sistema/vaso.svg")
    ap.add_argument("--modo", choices=("serie", "vivo", "manifiesto"), default="serie")
    ap.add_argument("--estados", type=int, default=12)
    ap.add_argument("--sigma", type=float, default=None)
    ap.add_argument("--u-vidrio", type=float, default=None)
    ap.add_argument("--u-liquido", type=float, default=None)
    ap.add_argument("--ciclo", type=float, default=None)
    a = ap.parse_args()

    p = Params()
    for k, v in (("sigma", a.sigma), ("u_vidrio", a.u_vidrio),
                 ("u_liquido", a.u_liquido), ("ciclo", a.ciclo)):
        if v is not None:
            setattr(p, k, v)

    estados, campo, escala = construir(Path(a.repo), p, a.estados, a.modo)
    man = manifiesto(estados, campo, escala, p)
    out = Path(a.salida)
    Path(str(out.with_suffix('')) + ".json").write_text(
        json.dumps(man, indent=1), encoding="utf-8")
    if a.modo != "manifiesto":
        out.write_text(render(estados, p), encoding="utf-8")

    for e in estados:
        print(f"  {e['fecha']}  {e['sha']}  pico {e['campo_max']:.3f}  "
              f"vidrio {e['area_vidrio']:5}  liquido {e['area_liquido']:5}")
    if a.modo != "manifiesto":
        print(f"\n{len(estados)} estados | {out.stat().st_size//1024} KB -> {out}")
    print(f"manifiesto -> {out.with_suffix('')}.json")


if __name__ == "__main__":
    main()
