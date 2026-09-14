#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the artist's hand before it enters the gate.

`iskvw/datos/curaduria.json` is edited by a human (by hand or with
`iskvw/editor.html`) and the consumer, `aplicar_curaduria()`, obeys it
SILENTLY: an unknown id is skipped without noise (by design -- the curation
may name works today's filter left out), a missing signed svg falls back to
the generated one, an out-of-range abstraccion is clamped. Every one of those
silences is right for the published site and wrong for the moment of editing:
a typo'd id means an edit the artist made simply never happens, and nobody
says so.

This tool is the loud counterpart. It checks the file against the schema the
consumer actually reads (cultura/mak_plataforma/contrato_archivo.py) and
against the REAL archive on disk, and reports findings the consumer would
swallow:

  ERROR  -- the file lies or would break the generator (bad JSON, duplicate
            ids, a non-boolean mostrar, a regimen nobody implements, mangled
            diacritics: the 'reduciendo ano' defect class).
  AVISO  -- legal but silently ignored or meaningless (unknown id, signed
            svg that is not on disk, `mostrar: true` noise, abstraccion the
            consumer will clamp).

Also validates `iskvw/datos/tablero.json` (the feature-flag board the same
panel edits) with its own rule: every value should be a boolean switch.

Exit code 1 when there is at least one ERROR, 0 otherwise: usable in CI and
before every commit of a downloaded file.

Uso:
    py tools/validar_curaduria.py
    py tools/validar_curaduria.py --curaduria descargas/curaduria.json
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CURADURIA = RAIZ / "iskvw" / "datos" / "curaduria.json"
TABLERO = RAIZ / "iskvw" / "datos" / "tablero.json"
ARCHIVO = RAIZ / "iskvw" / "datos" / "archivo.json"
CAMPO = RAIZ / "iskvw" / "datos" / "campo.json"
OBRAS = RAIZ / "iskvw" / "datos" / "obras.json"
ANIMADAS = RAIZ / "iskvw" / "datos" / "animadas.json"

sys.path.insert(0, str(RAIZ / "cultura" / "mak_plataforma"))
import contrato_archivo  # noqa: E402

# What the consumer implements today. A regimen outside this set reaches the
# skin and silently falls back to the default ramp -- the artist decided
# something and nothing happened.
REGIMENES = {"semantico", "industrial"}

# The fields aplicar_curaduria() reads per piece. An unknown field is legal
# (forward compatibility: the panel preserves it) but says nothing today.
CAMPOS_PIEZA = {"titulo", "mostrar", "abstraccion", "svg", "regimen",
                "peso", "serie", "nota"}

# Fields whose VALUE a human reads: they must carry correct Spanish, so
# mojibake in them is an ERROR, not a style.
CAMPOS_HUMANOS = {"titulo", "nota", "serie"}

# The classic marks of a double-encoded or lossy text. '\u00c3' followed by
# one of these is UTF-8 read as latin-1 ("\u00c3\u00b1" where "\u00f1" was
# meant), '\u00c2' the same defect on inverted punctuation, and the
# "\u00e2\u0080" pair the 3-byte case (em dash, curly quotes). U+FFFD is a
# byte that already died. Deliberately narrow: a legitimate title could carry
# '\u00c3' alone (S\u00e3o), so only the bigrams that mangled Spanish text
# produces are flagged. Escaped, not literal, so this tool itself stays
# printable on a cp1252 console (the higiene ratchet measures that).
_MOJIBAKE_TRAS_C3 = ("\u00a1\u00a9\u00ad\u00b1\u00b3\u00ba"  # aeinou con tilde
                     "\u0081\u0089\u008d\u0091\u0093\u009a")  # mayusculas
_MOJIBAKE_TRAS_C2 = "\u00a1\u00bf\u00b0\u00b7\u00b4"


def texto_mangled(texto: str) -> str | None:
    """The reason a human-read string is mangled, or None if it is sound."""
    if "\ufffd" in texto:
        return "contiene U+FFFD (un byte ya perdido)"
    for i, ch in enumerate(texto[:-1]):
        if ch == "\u00c3" and texto[i + 1] in _MOJIBAKE_TRAS_C3:
            return "mojibake UTF-8 leído como latin-1 (%r)" % texto[i:i + 2]
        if ch == "\u00c2" and texto[i + 1] in _MOJIBAKE_TRAS_C2:
            return "mojibake UTF-8 leído como latin-1 (%r)" % texto[i:i + 2]
    if "\u00e2\u0080" in texto:
        return "mojibake UTF-8 leído como latin-1 (em dash o comillas)"
    if any("\u0080" <= ch <= "\u009f" for ch in texto):
        return "contiene controles C1 (residuo de doble decodificación)"
    return None


def _pares_sin_duplicados(hallazgos, contexto):
    """An object_pairs_hook that reports duplicate keys instead of letting
    json.loads keep the LAST one silently -- in this file a duplicated piece
    id is two decisions of the artist, one of which vanishes."""
    def hook(pares):
        vistos, obj = set(), {}
        for k, v in pares:
            if k in vistos:
                hallazgos.append(("ERROR", "clave-duplicada",
                                  "%s: la clave %r aparece dos veces; "
                                  "JSON se queda con la última sin avisar"
                                  % (contexto, k)))
            vistos.add(k)
            obj[k] = v
        return obj
    return hook


def ids_conocidos() -> tuple[set, str]:
    """Every piece id the archive can currently produce, and where it came
    from. archivo.json (the generated union) when present; otherwise the
    same sources gen_archivo_iskvw.py unites: campo + obras + animadas."""
    if ARCHIVO.is_file():
        d = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return {p.get("id") for p in d.get("piezas") or []}, "datos/archivo.json"
    ids: set = set()
    fuentes = []
    if CAMPO.is_file():
        d = json.loads(CAMPO.read_text(encoding="utf-8"))
        ids |= {contrato_archivo._id(p.get("id"))
                for p in d.get("piezas") or []}
        fuentes.append("campo.json")
    if OBRAS.is_file():
        d = json.loads(OBRAS.read_text(encoding="utf-8"))
        obras = d if isinstance(d, list) else d.get("obras") or []
        ids |= {contrato_archivo._id(o.get("id") or o.get("title"))
                for o in obras}
        fuentes.append("obras.json")
    if ANIMADAS.is_file():
        d = json.loads(ANIMADAS.read_text(encoding="utf-8"))
        ids |= {"animada-%s" % f["obra_id"]
                for f in d.get("piezas") or [] if f.get("obra_id")}
        fuentes.append("animadas.json")
    ids.discard(None)
    ids.discard("")
    return ids, "+".join(fuentes) or "(sin fuentes)"


def _es_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validar_texto_humano(h, campo, pid, valor):
    if not isinstance(valor, str) or not valor.strip():
        h.append(("ERROR", "texto-invalido",
                  "pieza %r: %s debe ser texto no vacío" % (pid, campo)))
        return
    razon = texto_mangled(valor)
    if razon:
        h.append(("ERROR", "diacriticos",
                  "pieza %r: %s con texto dañado -- %s. Esto lo lee una "
                  "persona: español correcto con tildes." % (pid, campo, razon)))
    elif unicodedata.normalize("NFC", valor) != valor:
        h.append(("AVISO", "no-nfc",
                  "pieza %r: %s viene en forma descompuesta (NFD); se ve "
                  "bien pero rompe búsquedas por igualdad" % (pid, campo)))


def validar_curaduria(texto: str, conocidos: set, existe=None) -> list:
    """The findings for one curaduria.json body, as (nivel, codigo, mensaje).

    `existe` answers whether a signed-svg path is on disk; injectable for
    tests, defaults to the real repo root -- the same contract as
    aplicar_curaduria().
    """
    if existe is None:
        existe = lambda src: (RAIZ / src).is_file()  # noqa: E731
    h: list = []
    try:
        cur = json.loads(texto, object_pairs_hook=_pares_sin_duplicados(
            h, "curaduria.json"))
    except ValueError as e:
        return [("ERROR", "json", "curaduria.json no es JSON válido: %s" % e)]
    if not isinstance(cur, dict):
        return h + [("ERROR", "forma", "curaduria.json debe ser un objeto")]

    if not isinstance(cur.get("version", 1), int):
        h.append(("AVISO", "version", "version debería ser un entero"))
    reg = cur.get("regimen")
    if reg is not None and reg not in REGIMENES:
        h.append(("ERROR", "regimen",
                  "regimen global %r no existe; la piel implementa: %s"
                  % (reg, ", ".join(sorted(REGIMENES)))))

    piezas = cur.get("piezas")
    if piezas is None:
        piezas = {}
    if not isinstance(piezas, dict):
        h.append(("ERROR", "forma", "piezas debe ser un objeto id -> edición"))
        return h

    for pid, c in piezas.items():
        if not isinstance(c, dict):
            h.append(("ERROR", "forma",
                      "pieza %r: la edición debe ser un objeto" % pid))
            continue
        if not c:
            h.append(("AVISO", "vacia",
                      "pieza %r: entrada vacía, no dice nada; el panel la "
                      "habría eliminado" % pid))
        if pid != pid.strip() or not pid:
            h.append(("ERROR", "id", "id %r con espacios o vacío" % pid))
        elif any(ord(ch) > 127 for ch in pid):
            h.append(("AVISO", "id-no-ascii",
                      "id %r lleva caracteres fuera de ASCII: los ids son "
                      "claves de máquina y ninguna fuente los genera así"
                      % pid))
        if conocidos and pid not in conocidos:
            h.append(("AVISO", "id-desconocido",
                      "pieza %r no existe en el archivo actual: el consumidor "
                      "la ignora sin ruido. Si es un typo, esta edición nunca "
                      "ocurre." % pid))
        for campo, valor in c.items():
            if campo not in CAMPOS_PIEZA:
                h.append(("AVISO", "campo-desconocido",
                          "pieza %r: el campo %r no lo lee ningún consumidor "
                          "hoy (viaja intacto, pero no hace nada)"
                          % (pid, campo)))
                continue
            if campo in CAMPOS_HUMANOS:
                _validar_texto_humano(h, campo, pid, valor)
            elif campo == "mostrar":
                if valor is True:
                    h.append(("AVISO", "mostrar-true",
                              "pieza %r: mostrar=true es el valor por defecto "
                              "y no debería viajar" % pid))
                elif valor is not False:
                    h.append(("ERROR", "mostrar",
                              "pieza %r: mostrar debe ser true/false" % pid))
            elif campo == "abstraccion":
                if not _es_numero(valor):
                    h.append(("ERROR", "abstraccion",
                              "pieza %r: abstraccion debe ser un número"
                              % pid))
                elif not 0 <= valor <= 1:
                    h.append(("AVISO", "abstraccion-rango",
                              "pieza %r: abstraccion %s fuera de 0..1; el "
                              "consumidor la acota y el archivo queda "
                              "afirmando otra cosa" % (pid, valor)))
            elif campo == "peso":
                if not _es_numero(valor) or valor <= 0:
                    h.append(("ERROR", "peso",
                              "pieza %r: peso debe ser un número > 0 (una "
                              "pieza sin materia es mostrar=false)" % pid))
            elif campo == "regimen":
                if valor not in REGIMENES:
                    h.append(("ERROR", "regimen",
                              "pieza %r: regimen %r no existe; la piel "
                              "implementa: %s"
                              % (pid, valor, ", ".join(sorted(REGIMENES)))))
            elif campo == "svg":
                if not isinstance(valor, str) or not valor.strip():
                    h.append(("ERROR", "svg",
                              "pieza %r: svg debe ser una ruta de texto"
                              % pid))
                elif not existe(valor):
                    h.append(("AVISO", "svg-ausente",
                              "pieza %r: el svg firmado %r no está en disco; "
                              "el consumidor lo ignora y conserva el generado"
                              % (pid, valor)))
    return h


def validar_tablero(texto: str) -> list:
    """The board is COMPLETE state: every key travels, every value should be
    a boolean switch. A non-boolean is preserved by the panel but cannot be
    flipped, so it is said."""
    h: list = []
    try:
        tab = json.loads(texto, object_pairs_hook=_pares_sin_duplicados(
            h, "tablero.json"))
    except ValueError as e:
        return [("ERROR", "json", "tablero.json no es JSON válido: %s" % e)]
    if not isinstance(tab, dict):
        return h + [("ERROR", "forma", "tablero.json debe ser un objeto")]
    if not isinstance(tab.get("version", 1), int):
        h.append(("AVISO", "version", "version debería ser un entero"))
    mejoras = tab.get("mejoras")
    if not isinstance(mejoras, dict):
        h.append(("ERROR", "forma",
                  "mejoras debe ser un objeto clave -> true/false"))
        return h
    for clave, valor in mejoras.items():
        if not isinstance(valor, bool):
            h.append(("AVISO", "no-booleana",
                      "mejora %r: el valor %r no es un interruptor; el panel "
                      "lo muestra de sólo lectura" % (clave, valor)))
    return h


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--curaduria", type=Path, default=CURADURIA,
                    help="ruta al curaduria.json a validar (por defecto el del repo)")
    ap.add_argument("--tablero", type=Path, default=TABLERO,
                    help="ruta al tablero.json a validar (por defecto el del repo)")
    args = ap.parse_args(argv)

    hallazgos: list = []
    conocidos, fuente = ids_conocidos()
    print("archivo de referencia: %d ids desde %s" % (len(conocidos), fuente))

    if args.curaduria.is_file():
        cuerpo = args.curaduria.read_text(encoding="utf-8")
        h = validar_curaduria(cuerpo, conocidos)
        n_piezas = 0
        try:
            n_piezas = len((json.loads(cuerpo) or {}).get("piezas") or {})
        except ValueError:
            pass
        print("%s: %d piezas curadas" % (args.curaduria, n_piezas))
        hallazgos += h
    else:
        print("%s: no existe (nada que validar ahí)" % args.curaduria)

    if args.tablero.is_file():
        hallazgos += validar_tablero(args.tablero.read_text(encoding="utf-8"))
    else:
        print("%s: no existe (nada que validar ahí)" % args.tablero)

    for nivel, codigo, mensaje in hallazgos:
        print("%s [%s] %s" % (nivel, codigo, mensaje))
    errores = sum(1 for n, _, _ in hallazgos if n == "ERROR")
    avisos = len(hallazgos) - errores
    print("— %d errores, %d avisos" % (errores, avisos))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
