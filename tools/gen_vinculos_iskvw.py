#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Links between works, each one carrying the reason it exists.

The archive contract has `vinculos` and until now they were built from shared
TAGS in the curated portfolio json -- and `gen_archivo_iskvw.py` says so in its
own comment: "se declara `clase: etiqueta` y NO `semantico`: nadie midio que se
parezcan, comparten una palabra". Correct, and it left the 7.985 concept
mentions the perception pass extracted completely unused.

A link with a reason can be refuted. A link without one is decoration, and a
graph of decoration looks exactly like a graph of findings.

Measured over the 1.401 ig fichas before writing a line of this:

    vocabulary                     1.662 concepts, 1.541 after folding
                                   plural and accents
    concepts in exactly one work     819 (53%) -- they link nothing
    pairs sharing >=1 specific       31.846 -- too many to mean anything
    pairs sharing >=2               1.830, reaching 860 works (63%)

So the threshold is not taste: one shared concept produces 31.846 pairs over
1.359 works, which is a hairball. Two produces a graph a person can read, and
the reasons hold up -- `dualidad, espiritualidad, muerte, transicion, viaje`
between two works is a theme, not a coincidence.

THREE EXCLUSIONS, all of them counted and REPORTED, never silent:

- concepts in a single work: they cannot link anything;
- the most frequent ones (`naturaleza`, `arte digital`, `abstracto`...): a
  concept in 305 works is a CATEGORY, not a link, and letting it in connects
  everything to everything;
- concepts above `--tope-obras`: same reason, measured rather than named.

A cap nobody reports reads as "that was everything there was", which is the
defect this repo keeps paying for.

    py tools/gen_vinculos_iskvw.py FICHAS.jsonl
    py tools/gen_vinculos_iskvw.py FICHAS.jsonl --salida iskvw/datos/vinculos.json
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


def plegar(texto) -> str:
    """Lowercase, no diacritics, and a naive plural fold.

    `figura humana`(113) and `figuras humanas`(112) were two entries for one
    idea -- exactly half the signal thrown away. The fold is deliberately dumb
    (drop a trailing s on words over four letters): a real stemmer would need a
    dependency, and being wrong on `mes`/`me` matters less here than splitting
    every plural in the archive.
    """
    d = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in d if not unicodedata.combining(c)).lower().strip()
    # WORD BY WORD. The first version folded only the end of the string, so
    # `figuras humanas` became `figuras humana` and did NOT match `figura
    # humana` -- exactly the 113/112 pair that motivated all of this. The test
    # caught it before it shipped; the counts above were taken with the broken
    # version, which is why the folded vocabulary reads 1.541 there and fewer
    # here.
    return " ".join(p[:-1] if len(p) > 4 and p.endswith("s") else p
                    for p in t.split())


def conceptos_por_obra(filas):
    """(work -> folded keys, key -> the spelling the model wrote).

    The fold exists to GROUP, not to display. `colores` folds to `colore` and
    `patrones` to `patrone`, which work as keys and are not words: letting them
    out in a link's reason would put "patrone geometrico" in front of a human.
    Same rule as the accent -- normalise to join, show what was written.
    """
    obras: dict[str, set[str]] = {}
    formas: dict[str, Counter] = {}
    for d in filas:
        cs = set()
        for crudo in ((d.get("vision") or {}).get("conceptos") or []):
            texto = str(crudo or "").strip()
            if not texto:
                continue
            clave = plegar(texto)
            if not clave:
                continue
            cs.add(clave)
            formas.setdefault(clave, Counter())[" ".join(texto.lower().split())] += 1
        if cs:
            obras[d["id"]] = cs
    # The most used spelling represents the group. On a tie the longer one
    # wins, which is usually the one carrying the accent.
    canon = {k: max(c.items(), key=lambda x: (x[1], len(x[0])))[0]
             for k, c in formas.items()}
    return obras, canon


def vinculos(obras, minimo=2, comunes=6, tope_obras=60, canon=None):
    """Pairs, their shared concepts, and what was left out and why."""
    voc = Counter(c for cs in obras.values() for c in cs)
    fuera_comunes = {c for c, _ in voc.most_common(comunes)}
    fuera_unicos = {c for c, n in voc.items() if n < 2}
    fuera_amplios = {c for c, n in voc.items()
                     if n > tope_obras and c not in fuera_comunes}
    usables = set(voc) - fuera_comunes - fuera_unicos - fuera_amplios

    por_concepto = defaultdict(list)
    for obra, cs in obras.items():
        for c in cs & usables:
            por_concepto[c].append(obra)

    compartidos: dict[tuple[str, str], list[str]] = defaultdict(list)
    for concepto, ids in por_concepto.items():
        for a, b in combinations(sorted(set(ids)), 2):
            compartidos[(a, b)].append(concepto)

    salida = []
    for (a, b), cs in compartidos.items():
        if len(cs) < minimo:
            continue
        salida.append({
            "de": a, "a": b,
            "peso": round(min(1.0, len(cs) / 6.0), 3),
            # `concepto`, not `semantico`: nobody measured that they resemble
            # each other, they share named ideas. The class says what the link
            # is made of.
            "clase": "concepto",
            "porque": sorted((canon or {}).get(c, c) for c in cs),
        })
    salida.sort(key=lambda v: (-len(v["porque"]), v["de"], v["a"]))
    descartes = {
        "vocabulario": len(voc),
        "en_una_sola_obra": len(fuera_unicos),
        "demasiado_comunes": sorted((canon or {}).get(c, c)
                                    for c in fuera_comunes),
        "sobre_el_tope": len(fuera_amplios),
        "usables": len(usables),
        "pares_con_al_menos_uno": len(compartidos),
    }
    return salida, descartes


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fichas", type=Path)
    p.add_argument("--minimo", type=int, default=2,
                   help="conceptos compartidos para que exista el vinculo")
    p.add_argument("--comunes", type=int, default=6,
                   help="cuantos de los mas frecuentes se excluyen")
    p.add_argument("--tope-obras", type=int, default=60, dest="tope_obras",
                   help="un concepto en mas obras que esto es una categoria")
    p.add_argument("--salida", type=Path, default=None)
    a = p.parse_args()

    if not a.fichas.exists():
        print("no existe: %s" % a.fichas, file=sys.stderr)
        return 2
    filas = []
    for linea in a.fichas.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea:
            try:
                filas.append(json.loads(linea))
            except ValueError:
                continue
    obras, canon = conceptos_por_obra(filas)
    if not obras:
        print("ninguna ficha trae conceptos: no hay vinculos que construir")
        return 1
    vs, d = vinculos(obras, a.minimo, a.comunes, a.tope_obras, canon)
    alcanzadas = {v["de"] for v in vs} | {v["a"] for v in vs}

    print("fichas leidas: %d | con conceptos: %d" % (len(filas), len(obras)))
    print("vocabulario: %d conceptos" % d["vocabulario"])
    print("  fuera por estar en UNA sola obra: %d (no pueden vincular nada)"
          % d["en_una_sola_obra"])
    print("  fuera por demasiado comunes: %s" % ", ".join(d["demasiado_comunes"]))
    print("  fuera por estar en mas de %d obras: %d"
          % (a.tope_obras, d["sobre_el_tope"]))
    print("  usables: %d" % d["usables"])
    print()
    print("pares que comparten al menos uno: %d" % d["pares_con_al_menos_uno"])
    print("vinculos con >= %d conceptos: %d" % (a.minimo, len(vs)))
    print("obras alcanzadas: %d (%.0f%% de las que tienen conceptos)"
          % (len(alcanzadas), 100.0 * len(alcanzadas) / len(obras)))
    print()
    print("los mas fuertes:")
    for v in vs[:5]:
        print("   %s <-> %s  (%d): %s"
              % (v["de"], v["a"], len(v["porque"]), ", ".join(v["porque"][:6])))

    if a.salida:
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        a.salida.write_text(json.dumps(
            {"formato": "vinculos/1", "total": len(vs),
             "obras_alcanzadas": len(alcanzadas), "descartes": d,
             "vinculos": vs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print()
        print("escrito: %s" % a.salida)
    else:
        print()
        print("(informe solamente. Para guardarlo: --salida <archivo.json>)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
