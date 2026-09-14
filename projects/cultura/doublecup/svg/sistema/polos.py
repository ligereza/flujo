#!/usr/bin/env python3
"""polos.py -- los dos polos de la escala de grises: ERROR y PLACER.

EL PROBLEMA QUE RESUELVE

  Todo mapeo a gris obliga a decidir que es el 0 y que es el 255. Hasta ahora
  el campo de motor.py era "masa semantica": cuanto se habla de un termino.
  Eso da un relieve construido sobre ACTIVIDAD, y la actividad es decoracion:
  sube igual cuando el proyecto funciona y cuando se cae.

  Aqui los polos son:

      255  ERROR                 lo unico que deja rastro. Un fix es la prueba
                                 documental de que algo dolio. Genera altura.
      0    PLACER ASINTOMATICO   el codigo que sale bien no genera commit de
                                 arreglo. Es silencio. No tiene relieve porque
                                 no dejo huella que medir.

  El campo P (placer) NO se usa para levantar terreno. Se calcula por dos
  razones honestas:
    1. es superponible con E y permite ver donde el repo trabajo sin sangrar;
    2. sirve de CERTIFICADO DE SILENCIO. Una celda con E=0 puede ser placer
       (hubo actividad, no hubo dano) o puede ser vacio (no paso nada). Sin P
       las dos son indistinguibles y el 0 seria una mentira comoda.

LOS DOS EJES DE ERROR (la decision que este modulo resuelve midiendo)

  DENSIDAD     cuantos commits de error tocan cada termino. Picos agudos:
               premia el bug fest de una tarde.
  PERSISTENCIA en cuantos DIAS distintos ese termino siguio apareciendo en
               commits de error. Mesetas: premia el dano cronico, la zona que
               nunca termino de cerrarse.

  Se implementan las dos, se comparan numericamente en __main__ y se
  recomienda una. Ver RECOMENDACION al final del docstring.

METODO

  1. Se lee la historia entera con un solo `git log` (mensaje + numstat).
  2. Cada commit se clasifica error / placer / neutro por lexico sobre el
     mensaje. El diff-stat NO vota la clase (los nombres de fichero no dicen
     si algo se rompio); solo aporta terminos, y con peso menor que el asunto.
  3. La masa de cada commit se reparte entre los terminos del vocabulario de
     CampoSemantico que aparecen en el.
  4. Esa masa se difunde sobre la MISMA grilla y las MISMAS posiciones PCA
     (campo.px, campo.py, campo.vi) que usa el campo actual. Por construccion
     E, P y el campo de motor.py son superponibles pixel a pixel.

LIMITE HONESTO
  El vocabulario sale de README y documentación vigente, no de los mensajes de
  commit. Muchos commits no contienen NINGUN termino del vocabulario: esos
  commits existieron pero no tienen donde depositar masa. La cobertura real
  se imprime en __main__. Es una perdida conocida, no un descuido: el mapa
  tiene que ser el mismo mapa o los campos no se pueden superponer.

RECOMENDACION: PERSISTENCIA (numeros reproducibles en __main__)

  Por termino, los dos ejes correlacionan Pearson 0.81 / Spearman 0.74: se
  parecen, pero no son el mismo orden. Como campos CRUDOS son indistinguibles
  (0.993, MAE 0.014) y la eleccion daria igual. Ya RECTIFICADOS -- que es lo
  que se pinta -- divergen: Pearson 0.741, MAE 0.049. Es decir: la decision
  solo importa despues de quitar el fondo comun, y ahi importa de verdad.

  Donde discrepan, discrepan asi: densidad encabeza con `xio` y `mak`
  (subsistemas concretos que se rompieron mucho en pocas sesiones: picos
  agudos); persistencia encabeza con `context`, `flujo`, `src`, `tests`
  (13, 12, 12 y 11 dias distintos con fix: mesetas). Densidad esta ademas
  contaminada por el tamano del commit -- un commit gordo deposita mas masa
  aunque sea un solo fallo -- mientras que persistencia cuenta dias y es
  inmune a eso.

  La tesis de la pieza es que el error deja CICATRIZ. Una cicatriz es, por
  definicion, lo que dura despues de que el corte se cerro. Persistencia mide
  duracion; densidad mide el aparato del accidente. Se recomienda
  persistencia, y es el default del parametro `eje`.

  Contra mi propia recomendacion: con 21 dias de historia la persistencia solo
  puede tomar 21 valores y hay muchisimos empates en la cola. Sobre un repo de
  anos seria claramente mejor; sobre este, es mejor por argumento mas que por
  margen estadistico. Queda dicho.
"""
from __future__ import annotations

import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from motor import Params, Historia, CampoSemantico, tokens

# ------------------------------------------------------------------- lexicos

RE_ERROR = re.compile(
    r"\b(fix|fixes|fixed|bug|bugs|error|errors|revert|reverts|broken|break|"
    r"breaks|fail|fails|failing|hotfix|patch|crash|regres\w*|roto|rompe|"
    r"arregl\w*|fallo|falla)\b", re.I)

RE_PLACER = re.compile(
    r"\b(add|adds|added|new|feat|feature|art|design|ui|ux|color|colour|anim\w*|"
    r"nice|clean|cleanup|refactor|polish|pulido|mejora\w*|nuevo|nueva|"
    r"estil\w*|dise\w*)\b", re.I)

ERROR, PLACER, NEUTRO = "error", "placer", "neutro"

# Las palabras que DECIDEN la clase no pueden ademas cobrar masa: si "fix"
# clasifica el commit como error y encima deposita altura en la coordenada de
# "fix", el mapa mide su propio clasificador. Se excluyen del deposito.
LEXICO = set("""fix fixes fixed bug bugs error errors revert reverts broken break
breaks fail fails failing hotfix patch crash roto rompe fallo falla add adds added
new feat feature art design ui ux color colour nice clean cleanup refactor polish
pulido nuevo nueva""".split())

PESO_ASUNTO = 1.0     # los terminos del mensaje pesan entero
PESO_RUTA = 0.35      # los de las rutas del diff-stat pesan menos: son contexto


# --------------------------------------------------------------- extraccion


def leer_commits(historia: Historia) -> list[dict]:
    """Un solo `git log` con mensaje y numstat. Orden cronologico ascendente.

    Devuelve dicts con: sha, fecha, asunto, cuerpo, ficheros, lineas, clase.
    """
    sep = "\x01COMMIT\x01"
    out = historia._git("log", "--reverse", "--numstat", "--date=short",
                        f"--format={sep}%H%x02%ad%x02%s%x02%b")
    commits = []
    for bloque in out.split(sep):
        if not bloque.strip():
            continue
        cab, _, resto = bloque.partition("\n")
        campos = cab.split("\x02")
        if len(campos) < 3:
            continue
        sha, fecha, asunto = campos[0], campos[1], campos[2]
        cuerpo = campos[3] if len(campos) > 3 else ""
        ficheros, lineas = [], 0
        for l in resto.split("\n"):
            partes = l.split("\t")
            if len(partes) == 3:
                ficheros.append(partes[2])
                for n in partes[:2]:
                    if n.isdigit():
                        lineas += int(n)
        commits.append({
            "sha": sha, "fecha": fecha, "asunto": asunto, "cuerpo": cuerpo,
            "ficheros": ficheros, "lineas": lineas,
            "clase": clasificar(asunto, cuerpo),
        })
    return commits


def clasificar(asunto: str, cuerpo: str = "") -> str:
    """error / placer / neutro a partir del texto del commit.

    El asunto manda. El cuerpo solo desempata: un commit cuyo asunto dice
    'feat' pero cuyo cuerpo entero habla de un fallo sigue siendo trabajo con
    dano registrado. Si ambos lexicos aparecen en el asunto gana ERROR: el
    rastro de dano no se cancela porque en el mismo commit se anadiera algo
    bonito. El placer es lo que NO deja rastro; si dejo rastro de fix, hubo
    error.
    """
    e = bool(RE_ERROR.search(asunto))
    p = bool(RE_PLACER.search(asunto))
    if e:
        return ERROR
    if p:
        return PLACER
    if RE_ERROR.search(cuerpo):
        return ERROR
    if RE_PLACER.search(cuerpo):
        return PLACER
    return NEUTRO


def terminos_commit(c: dict, vi: dict) -> dict:
    """Terminos del vocabulario presentes en un commit, con su peso.

    Mensaje (asunto+cuerpo) a peso entero, rutas del diff-stat a peso menor.
    """
    w = defaultdict(float)
    for t in tokens(c["asunto"] + " " + c["cuerpo"]):
        if t in vi and t not in LEXICO:
            w[t] += PESO_ASUNTO
    ruta_txt = " ".join(re.split(r"[/._\-]", " ".join(c["ficheros"])))
    for t in set(tokens(ruta_txt)):
        if t in vi:
            w[t] += PESO_RUTA
    return dict(w)


# ------------------------------------------------------------------- ejes


def masas_polares(commits: list[dict], vi: dict):
    """Acumula, por termino: densidad y persistencia de error, y masa de placer.

    densidad[w]     suma de pesos de w sobre commits de clase ERROR.
                    Un dia con 20 fixes del mismo termino suma 20.
    persistencia[w] numero de DIAS distintos con al menos un commit de error
                    que menciona w. Un dia con 20 fixes suma 1. Mide cuanto
                    tiempo el termino siguio siendo territorio de fallo.
    placer[w]       suma de pesos sobre commits de clase PLACER.
    """
    densidad = Counter()
    placer = Counter()
    dias_error = defaultdict(set)
    dias_totales = set()
    tocados = 0
    for c in commits:
        dias_totales.add(c["fecha"])
        w = terminos_commit(c, vi)
        if w:
            tocados += 1
        if c["clase"] == ERROR:
            for t, m in w.items():
                densidad[t] += m
                dias_error[t].add(c["fecha"])
        elif c["clase"] == PLACER:
            for t, m in w.items():
                placer[t] += m
    persistencia = Counter({t: float(len(d)) for t, d in dias_error.items()})
    meta = {"dias": len(dias_totales), "commits_con_vocab": tocados}
    return densidad, persistencia, placer, meta


# ------------------------------------------------------------------- campos


def _splat(masas, campo: CampoSemantico, p: Params) -> np.ndarray:
    """Difunde masa por termino sobre la grilla, en el mapa PCA existente.

    Misma gaussiana y mismo log1p que CampoSemantico.campo: los campos que
    salen de aqui son sumables/restables con el campo de motor.py.
    """
    F = np.zeros((p.filas, p.cols))
    s2 = 2 * p.sigma ** 2
    for w, m in masas.items():
        i = campo.vi.get(w)
        if i is None or m <= 0:
            continue
        d2 = (campo.GX - campo.px[i]) ** 2 + (campo.GY - campo.py[i]) ** 2
        F += math.log1p(m) * np.exp(-d2 / s2)
    return F


def _norm(F: np.ndarray) -> np.ndarray:
    m = float(F.max())
    return F / m if m > 0 else F


def campos_polares(historia, campo, corpora, p, eje: str = "persistencia") -> dict:
    """Devuelve los campos polares del repo en el espacio de `campo`.

    Parametros
      historia  Historia (motor.py) ya construida sobre el repo.
      campo     CampoSemantico ya construido: aporta vocab, vi, px, py, grilla.
      corpora   lista de listas de tokens por estado (la que se uso para
                construir `campo`). Se usa solo para el campo de referencia
                A (actividad), que sirve de control contra el que comparar.
      p         Params.
      eje       "densidad" o "persistencia": que medida alimenta E y H.

    Claves devueltas
      E   campo de ERROR, normalizado 0..1 (segun `eje`).
      P   campo de PLACER, normalizado 0..1.
      H   MAPA DE ALTURA HONESTO, 0..1. Ver justificacion abajo.
      E_densidad, E_persistencia   los dos ejes, ambos normalizados, para
          poder compararlos sin recalcular.
      S   soporte = evidencia total normalizada (error + placer). Dice donde
          hay derecho a afirmar algo. No es altura: es confianza.
      D   delta = E - P, en [-1, 1]. Firmado: negativo = zona trabajada y
          sin dano. Diagnostico, no relieve.
      A   campo de ACTIVIDAD (el de motor.py, normalizado): el relieve
          decorativo contra el que se contrasta H.
      masas    dict con los Counters crudos por termino.
      clases   conteo de commits por clase.
      meta     cobertura, dias, parametros de la corrida.

    QUE ES EL 0 Y QUE ES EL 255 EN H

      H = normalizar( max(E - P, 0) )      altura RECTIFICADA

      255 (H=1)  la zona donde el exceso de error sobre placer es maximo: el
                 racimo de terminos del que el repo SOLO habla cuando algo se
                 rompio. Cicatriz pura.
      0   (H=0)  todo lo demas, y son dos cosas distintas que el suelo junta:
                 (a) PLACER ASINTOMATICO -- hubo trabajo y no dejo rastro de
                     dano (E<=P, con S>0). Es el silencio, y es el 0 legitimo.
                 (b) ignorancia -- nunca paso nada ahi (S~0).
                 H=0 con S>0 es (a); H=0 con S~0 es (b). Por eso se devuelve
                 S: el suelo de este mapa no es homogeneo y no se disimula.

      POR QUE SE RESTA P, SI EL PLACER "NO DEJA RASTRO"
      Precisamente por eso. P no excava -- por eso hay max(...,0) y nunca hay
      altura negativa. P se resta como MODELO NULO: mide cuanto habla el repo
      de una zona por el mero hecho de estar viva. Si un termino aparece tanto
      en commits de placer como en commits de error, su altura no es cicatriz,
      es verbosidad. Restar P deja solo el error que EXCEDE la locuacidad de
      base. La operacion no le da relieve al placer: se lo quita al ruido.

      Y esto es medible, no retorico. Sobre este repo:
          corr(E, actividad) = 0.96    E crudo es casi el campo decorativo
          corr(H, actividad) = 0.13    H rectificado ya no lo es
      Un relieve con corr 0.96 contra "cuanto se habla" seria decoracion con
      otro nombre. La resta es lo que convierte el mapa en un mapa de dano.
      El campo E crudo se devuelve igualmente, sin rectificar, por si se
      prefiere el relieve ingenuo.
    """
    commits = leer_commits(historia)
    dens, pers, plac, meta = masas_polares(commits, campo.vi)

    E_dens = _norm(_splat(dens, campo, p))
    E_pers = _norm(_splat(pers, campo, p))
    P = _norm(_splat(plac, campo, p))
    E = E_pers if eje == "persistencia" else E_dens

    S = _norm(_splat(dens if eje == "densidad" else pers, campo, p)
              + _splat(plac, campo, p))
    # H: altura RECTIFICADA. Ver justificacion del 0 y el 255 en el docstring.
    H = _norm(np.maximum(E - P, 0.0))
    H_dens = _norm(np.maximum(E_dens - P, 0.0))
    H_pers = _norm(np.maximum(E_pers - P, 0.0))

    A = _norm(campo.campo(corpora[-1], 1.0)) if corpora else np.zeros_like(E)

    clases = Counter(c["clase"] for c in commits)
    meta.update({"eje": eje, "commits": len(commits),
                 "cobertura": meta["commits_con_vocab"] / max(1, len(commits))})
    return {
        "E": E, "P": P, "H": H, "S": S, "D": E - P, "A": A,
        "E_densidad": E_dens, "E_persistencia": E_pers,
        "H_densidad": H_dens, "H_persistencia": H_pers,
        "masas": {"densidad": dens, "persistencia": pers, "placer": plac},
        "clases": dict(clases), "commits": commits, "meta": meta,
    }


# -------------------------------------------------------------- comparacion


def _rank(v: np.ndarray) -> np.ndarray:
    o = np.argsort(np.argsort(v))
    return o.astype(float)


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def comparar_ejes(res: dict, campo: CampoSemantico, top: int = 12) -> dict:
    """Densidad vs persistencia: correlaciones, cabeceras y distancia de relieve."""
    vocab = campo.vocab
    d = np.array([res["masas"]["densidad"].get(w, 0.0) for w in vocab])
    q = np.array([res["masas"]["persistencia"].get(w, 0.0) for w in vocab])
    viv = (d > 0) | (q > 0)

    Ed, Ep = res["E_densidad"], res["E_persistencia"]
    return {
        "n_terminos_con_error": int(viv.sum()),
        "pearson_terminos": _corr(d[viv], q[viv]),
        "spearman_terminos": _corr(_rank(d[viv]), _rank(q[viv])),
        "pearson_campos": _corr(Ed, Ep),
        "mae_campos": float(np.abs(Ed - Ep).mean()),
        "max_dif_campos": float(np.abs(Ed - Ep).max()),
        "pearson_alturas": _corr(res["H_densidad"], res["H_persistencia"]),
        "mae_alturas": float(np.abs(res["H_densidad"]
                                    - res["H_persistencia"]).mean()),
        "top_densidad": sorted(((w, float(res["masas"]["densidad"][w]))
                                for w in vocab if res["masas"]["densidad"][w]),
                               key=lambda x: -x[1])[:top],
        "top_persistencia": sorted(((w, float(res["masas"]["persistencia"][w]))
                                    for w in vocab
                                    if res["masas"]["persistencia"][w]),
                                   key=lambda x: -x[1])[:top],
    }


def cicatrices(res: dict, campo: CampoSemantico, top: int = 12) -> list[tuple]:
    """Las cicatrices del repo: terminos con dano cronico y poco placer.

    Ordena por persistencia (dias distintos con fix) y desempata penalizando
    el placer: un termino muy tocado por fixes PERO tambien muy celebrado es
    zona viva; una cicatriz es la que solo aparece cuando algo se rompe.

      indice = persistencia * (1 - placer_rel/2)

    Es una heuristica, no una medida fuerte: con 21 dias de historia la
    persistencia toma pocos valores distintos y hay muchos empates.
    """
    pers, plac = res["masas"]["persistencia"], res["masas"]["placer"]
    pmax = max(plac.values()) if plac else 1.0
    fila = []
    for w in campo.vocab:
        if not pers.get(w):
            continue
        pr = plac.get(w, 0.0) / (pmax or 1.0)
        fila.append((w, pers[w], plac.get(w, 0.0), pers[w] * (1 - pr / 2)))
    fila.sort(key=lambda x: -x[3])
    return fila[:top]


# --------------------------------------------------------------------- svg


def svg_polos(E: np.ndarray, P: np.ndarray, p: Params, sep: float = 24.0) -> str:
    """E y P como dos mapas de grises lado a lado. Molde: svg_mapa de relieve.py.

    Izquierda ERROR, derecha PLACER. Mismo negro y mismo blanco en las dos:
    se pueden comparar a ojo porque comparten la escala 0..255.
    """
    W, H = p.cols * p.adv_x, p.filas * p.adv_y
    ancho = W * 2 + sep
    alto = H + 22
    out = []
    for dx, A in ((0.0, E), (W + sep, P)):
        for f in range(p.filas):
            for c in range(p.cols):
                v = int(round(255 * float(np.clip(A[f, c], 0, 1))))
                out.append(f'<rect x="{dx + c*p.adv_x:.0f}" y="{f*p.adv_y:.0f}" '
                           f'width="{p.adv_x:.0f}" height="{p.adv_y:.0f}" '
                           f'fill="#{v:02x}{v:02x}{v:02x}"/>')
    et = (f'<text x="0" y="{H+15:.0f}" fill="#94a3b8" font-size="11" '
          f'font-family="ui-monospace,monospace">E -- error (255 = maxima '
          f'cicatriz)</text>'
          f'<text x="{W+sep:.0f}" y="{H+15:.0f}" fill="#94a3b8" font-size="11" '
          f'font-family="ui-monospace,monospace">P -- placer (no es altura: '
          f'es certificado de silencio)</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {ancho:.0f} {alto:.0f}" width="100%" height="100%" '
            f'shape-rendering="crispEdges">'
            f'<title>polos -- error y placer</title>'
            f'<desc>{escape("Dos campos en el mismo espacio PCA que el campo semantico. El de la izquierda es lo que dolio; el de la derecha es lo que no dejo rastro de dolor. Solo el izquierdo tiene derecho a levantar relieve.")}</desc>'
            f'<rect width="100%" height="100%" fill="#08070a"/>'
            + "".join(out) + et + "</svg>\n")


# -------------------------------------------------------------------- main


def _tabla(titulo, filas, cols):
    print(f"\n{titulo}")
    print("  " + "  ".join(c.ljust(14) if i == 0 else c.rjust(10)
                           for i, c in enumerate(cols)))
    for f in filas:
        print("  " + "  ".join(
            str(x).ljust(14) if i == 0 else f"{x:10.2f}" if isinstance(x, float)
            else str(x).rjust(10) for i, x in enumerate(f)))


def main():
    repo = Path("/tmp/vc_test")
    p = Params()
    h = Historia(repo, p)
    todos = h.commits()
    k = min(12, len(todos))
    sel = [todos[round(i * (len(todos) - 1) / (k - 1))] for i in range(k)]
    corpora = [tokens(h.corpus(sha)) for sha, _ in sel]
    campo = CampoSemantico(corpora, p)

    res = campos_polares(h, campo, corpora, p, eje="persistencia")
    m, cl = res["meta"], res["clases"]
    print("polos.py -- ERROR / PLACER sobre /tmp/vc_test")
    print(f"  commits {m['commits']}  dias {m['dias']}")
    print(f"  clases: error {cl.get('error',0)}  placer {cl.get('placer',0)}  "
          f"neutro {cl.get('neutro',0)}")
    print(f"  cobertura de vocabulario: {m['commits_con_vocab']}/{m['commits']} "
          f"commits depositan masa ({100*m['cobertura']:.1f}%)")
    print(f"  terminos con masa de error: "
          f"{len(res['masas']['persistencia'])}/{len(campo.vocab)}")

    cmp = comparar_ejes(res, campo)
    print("\nDENSIDAD vs PERSISTENCIA")
    print(f"  terminos con error > 0        {cmp['n_terminos_con_error']}")
    print(f"  Pearson  (masa por termino)   {cmp['pearson_terminos']:.4f}")
    print(f"  Spearman (rangos)             {cmp['spearman_terminos']:.4f}")
    print(f"  Pearson  (campo vs campo)     {cmp['pearson_campos']:.4f}")
    print(f"  MAE entre relieves (0..1)     {cmp['mae_campos']:.4f}")
    print(f"  maxima diferencia local       {cmp['max_dif_campos']:.4f}")
    print(f"  -- ya RECTIFICADOS (H = relu(E-P)), que es lo que se pinta:")
    print(f"  Pearson  (H_dens vs H_pers)   {cmp['pearson_alturas']:.4f}")
    print(f"  MAE entre alturas             {cmp['mae_alturas']:.4f}")
    print("  Sin rectificar los dos ejes son el mismo mapa (0.99) y la")
    print("  eleccion daria igual. Rectificados divergen de verdad: ahi si")
    print("  hay que elegir, y por eso la decision no es cosmetica.")

    _tabla("TOP densidad (fixes ponderados)", cmp["top_densidad"],
           ["termino", "masa"])
    _tabla("TOP persistencia (dias con fix)", cmp["top_persistencia"],
           ["termino", "dias"])
    _tabla("CICATRICES (persistencia penalizada por placer)",
           [(w, d, pl, ix) for w, d, pl, ix in cicatrices(res, campo)],
           ["termino", "dias", "placer", "indice"])

    print("\nCONTRA EL CAMPO DECORATIVO (donde el modulo se autodelata)")
    print(f"  Pearson E vs A (actividad)    {_corr(res['E'], res['A']):.4f}"
          f"   <- E crudo ES decoracion")
    print(f"  Pearson H vs A (actividad)    {_corr(res['H'], res['A']):.4f}"
          f"   <- H rectificado ya no")
    print(f"  Pearson E vs P (campos)       {_corr(res['E'], res['P']):.4f}")
    ve = np.array([res["masas"]["persistencia"].get(w, 0.0) for w in campo.vocab])
    vp = np.array([res["masas"]["placer"].get(w, 0.0) for w in campo.vocab])
    print(f"  Pearson E vs P (por termino)  {_corr(ve, vp):.4f}")
    print(f"  Spearman E vs P (por termino) {_corr(_rank(ve), _rank(vp)):.4f}")
    print("  Lectura: por termino, error y placer solo comparten 0.47 -- hay")
    print("  senal real. Pero la gaussiana de sigma=46 px los vuelve el mismo")
    print("  mapa (0.99): E crudo mide la GEOMETRIA del PCA, no el polo. Esa")
    print("  es la medida debil, y es exactamente lo que arregla restar P.")

    print("\nSENSIBILIDAD A SIGMA (el difuminado es quien borra los polos)")
    print("  sigma   corr(E,P)   corr(E,A)   MAE(Edens,Epers)")
    import copy
    for s in (46.0, 30.0, 18.0, 10.0, 6.0):
        ps = copy.copy(p)
        ps.sigma = s
        cs = CampoSemantico(corpora, ps)
        ed = _norm(_splat(res["masas"]["densidad"], cs, ps))
        ep = _norm(_splat(res["masas"]["persistencia"], cs, ps))
        pp = _norm(_splat(res["masas"]["placer"], cs, ps))
        aa = _norm(cs.campo(corpora[-1], 1.0))
        print(f"  {s:5.1f}   {_corr(ep, pp):9.4f}   {_corr(ep, aa):9.4f}   "
              f"{float(np.abs(ed-ep).mean()):16.4f}")
    print("  Bajar sigma ayuda poco: ni a 6 px se separan (0.88). El difuminado")
    print("  no es el culpable principal -- el confundido es E crudo. La resta")
    print("  E-P funciona a CUALQUIER sigma porque quita el fondo comun.")
    ceros = res["H"] < 0.02
    print(f"  celdas con H~0                {int(ceros.sum())}/{res['H'].size}")
    print(f"    de esas, con soporte S>0.02 {int((ceros & (res['S'] > 0.02)).sum())}"
          f"  (placer verificado)")
    print(f"    de esas, sin soporte        {int((ceros & (res['S'] <= 0.02)).sum())}"
          f"  (ignorancia, no placer)")

    salida = Path("/tmp/proto/sistema/polos_test.svg")
    salida.write_text(svg_polos(res["E"], res["P"], p), encoding="utf-8")
    print(f"\n{salida.stat().st_size//1024} KB -> {salida}")


if __name__ == "__main__":
    main()
