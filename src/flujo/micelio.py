#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The envelope that lets a frontier model with no API drive this organism.

The constraint this is built for, in the user's words: tomorrow the strong
model is gone and the IBM credit expires within weeks. What is left is a pile
of free, weak models running unattended, plus ONE high-capability model the
user can only TALK to, in a browser, with no API. So the bus between them
cannot be a network call. It has to be a file that pastes into a chat window
and pastes back out.

Three verbs, ONE envelope. Three separate schemas would mean the web model has
to learn three shapes, and by the third month they are three dialects that no
longer fit together:

    semilla    an idea, translated by the strong model into something the
               organism can germinate on its own. It travels IN.
    fruto      what the organism grew, small enough to PASTE. It travels OUT.
    nutriente  a corrective order. It travels IN, and it carries its own
               acceptance criterion.

The one rule that makes the cycle safe, and the reason `criterio` is not
optional: an order written by a model that never ran the code, applied by an
organism that does not verify, is exactly how this repo produced 4.275 inert
lines. So a nutriente never says "fix the parser". It says *this input must
produce this output*, and then a weak model does not need to understand
anything -- it iterates until the check goes green. What decides is not
anybody's opinion. It is whether the case passed.

Stdlib only, on purpose: MAK imports this from its own clone of the repo, and
the box has no dependencies this file could rely on.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORMATO = "micelio/1"
TIPOS = ("semilla", "hongo", "fruto", "nutriente")

# A fruto that does not fit in a chat window breaks the cycle at its most
# important step: the return trip. 12 KB is about 3.000 tokens, which leaves
# the window for the conversation itself. The cap is ENFORCED when writing and
# what it dropped is REPORTED -- a silent truncation reads as "that was
# everything", which is the defect this repo keeps paying for.
TOPE_FRUTO_BYTES = 12_000

TIPOS_CRITERIO = ("caso", "comando", "archivo", "campo")


class SobreInvalido(ValueError):
    """The envelope does not meet the format. The message is read by a human
    or pasted back to the web model that wrote it, so it names WHAT is missing
    instead of returning a code."""


@dataclass
class Resultado:
    """What verificar() returns. `verde` is the only thing that decides."""

    verde: bool
    checks: list[dict] = field(default_factory=list)

    def texto(self) -> str:
        lineas = []
        for c in self.checks:
            marca = "OK  " if c["verde"] else "FALLA"
            lineas.append("%s %s: %s" % (marca, c["nombre"], c["detalle"]))
        lineas.append("VERDE" if self.verde else "ROJO")
        return "\n".join(lineas)


# --------------------------------------------------------------- validacion

def _exigir(cond: bool, mensaje: str) -> None:
    if not cond:
        raise SobreInvalido(mensaje)


def validar(sobre: dict) -> dict:
    """Validate the envelope and return it. Raises `SobreInvalido` with a
    message a human -- or the model that wrote it -- can act on without reading
    any code."""
    _exigir(isinstance(sobre, dict), "el sobre tiene que ser un objeto JSON")
    _exigir(sobre.get("formato") == FORMATO,
            'falta `"formato": "%s"` (vino %r)' % (FORMATO, sobre.get("formato")))
    tipo = sobre.get("tipo")
    _exigir(tipo in TIPOS,
            '`tipo` tiene que ser uno de %s (vino %r)' % (", ".join(TIPOS), tipo))
    _exigir(isinstance(sobre.get("asunto"), str) and sobre["asunto"].strip(),
            "`asunto` es una linea que dice de que se trata, y falta")
    _exigir(isinstance(sobre.get("cuerpo"), dict),
            "`cuerpo` tiene que ser un objeto")

    if tipo in ("semilla", "nutriente"):
        crit = sobre.get("criterio")
        _exigir(isinstance(crit, list) and crit,
                "un %s SIN `criterio` no se puede aceptar: sin criterio nadie "
                "puede decir si se cumplio, y el organismo no tiene con que "
                "decidir cuando parar" % tipo)
        for i, c in enumerate(crit):
            _validar_criterio(c, i)
    return sobre


def _validar_criterio(c: Any, i: int) -> None:
    donde = "criterio[%d]" % i
    _exigir(isinstance(c, dict), "%s tiene que ser un objeto" % donde)
    t = c.get("tipo")
    _exigir(t in TIPOS_CRITERIO,
            "%s.tipo tiene que ser uno de %s (vino %r)"
            % (donde, ", ".join(TIPOS_CRITERIO), t))
    if t == "caso":
        for k in ("modulo", "funcion", "entrada", "salida"):
            _exigir(k in c, "%s de tipo caso necesita `%s`" % (donde, k))
        _exigir(isinstance(c["entrada"], list),
                "%s.entrada es la lista de argumentos" % donde)
    elif t == "comando":
        _exigir(isinstance(c.get("cmd"), list) and c["cmd"],
                "%s de tipo comando necesita `cmd` como lista" % donde)
    elif t == "archivo":
        _exigir(isinstance(c.get("ruta"), str) and c["ruta"],
                "%s de tipo archivo necesita `ruta`" % donde)
    elif t == "campo":
        for k in ("ruta", "campo"):
            _exigir(k in c, "%s de tipo campo necesita `%s`" % (donde, k))


def leer(ruta: str | Path) -> dict:
    """Read and validate. Accepts JSON pasted with markdown around it, because
    a web model answers with a fenced block however firmly it is asked not to."""
    texto = Path(ruta).read_text(encoding="utf-8")
    return validar(desde_texto(texto))


def desde_texto(texto: str) -> dict:
    """Pull the envelope out of whatever the user pasted."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto)
    crudo = (m.group(1) if m else texto).strip()
    try:
        return json.loads(crudo)
    except ValueError as e:
        raise SobreInvalido(
            "eso no es JSON valido (%s). Si lo pegaste de un chat, revisa que "
            "no haya quedado texto de conversacion adentro." % e) from e


# ------------------------------------------------------------ verificacion

def verificar(sobre: dict, raiz: str | Path = ".") -> Resultado:
    """Run the `criterio` and return green/red.

    This is the semaphore of the whole cycle. A weak model does not need to
    understand the request: it repeats until this goes green. That is why every
    check ALSO returns its detail -- a red that does not say what was expected
    forces guessing, and guessing is what this circuit exists to remove.
    """
    raiz = Path(raiz)
    checks: list[dict] = []
    for i, c in enumerate(sobre.get("criterio") or []):
        nombre = c.get("nombre") or "%s[%d]" % (c.get("tipo", "?"), i)
        try:
            verde, detalle = _correr_criterio(c, raiz)
        except Exception as e:                    # noqa: BLE001 - se reporta
            verde, detalle = False, "%s: %s" % (type(e).__name__, e)
        checks.append({"nombre": nombre, "verde": verde, "detalle": detalle})
    return Resultado(verde=all(c["verde"] for c in checks) and bool(checks),
                     checks=checks)


# Las tres preguntas que convierten una OCURRENCIA en una tarea. Inventar que
# hacer esta bien; decidirlo sin formato no.
#
# Medido el 2026-08-01: MAK se puso a las 02:00 a "generar una base de datos de
# tatuajes por tipo de imagen y elementos". Nadie lo decidio. Salio de
# `oportunidad_codigo` de una foto de 2020 -- un campo donde al modelo se le
# pide explicitamente que ESPECULE ("si la obra sugiere un procedimiento que
# podria automatizarse, describi que programa la generaria") -- y `material.py`
# lo convierte textual en orden de trabajo. Ese campo viene lleno en el 77,9%
# de 1.354 obras.
#
# Y la tercera pregunta existe por un error MIO del mismo dia: conclui que
# nadie conectaba los conceptos de un ensayo con el motor de iconos, cuando
# `tools/iconos_conjunto.py` existe, tiene tests, produjo 16 iconos y esta
# registrado en CAPACIDADES.md -- un archivo que edite cinco veces esa noche
# sin leerlo nunca. Un grep vacio no es evidencia de ausencia: es evidencia de
# que la consulta fue estrecha.
PREGUNTAS_PROPUESTA = (
    ("consumidor",
     "QUIEN lo va a usar cuando este hecho. No 'seria util': un nombre. Sin "
     "consumidor no es una tarea, es una ocurrencia."),
    ("ya_busque_en",
     "DONDE buscaste que no exista ya, y que encontraste. Como minimo el "
     "registro VIVO de CAPACIDADES.md y la tabla de MAPA.md, que estan "
     "generados y no se pudren."),
    ("criterio",
     "COMO se sabe que salio bien, en la forma que corre una maquina. Es el "
     "mismo `criterio` de una semilla."),
)


def evaluar_propuesta(propuesta: dict) -> dict:
    """Does this idea qualify as a task? Returns what is missing, never a bare no.

    Inventing what to do is fine. Deciding it without a format is not: that is
    how a model musing over a photo of a tattoo became a work order at 2am.

    This does not judge whether the idea is GOOD -- nobody can automate that.
    It asks the three things whose absence turns any idea into noise: who will
    use it, where you looked for it already, and how anyone will know it
    worked.
    """
    faltan = []
    for clave, porque in PREGUNTAS_PROPUESTA:
        valor = propuesta.get(clave)
        if clave == "criterio":
            ok = isinstance(valor, list) and bool(valor)
        else:
            ok = bool(str(valor or "").strip())
        if not ok:
            faltan.append({"falta": clave, "porque": porque})
    return {"formato": FORMATO, "tipo": "propuesta",
            "asunto": str(propuesta.get("asunto") or "")[:200],
            "es_tarea": not faltan,
            "le_falta": faltan}


def cosechar(sobre: dict, raiz: str | Path = ".", tope: int = TOPE_FRUTO_BYTES) -> dict:
    """Run the criterion and RETURN AN ENVELOPE: `fruto` if green, `hongo` if red.

    This is the return leg of the circuit and it was missing. The semaphore
    existed and printed VERDE or ROJO to a console, which is useless to the
    only reader that matters here: a web model with no API, that gets whatever
    a person pastes into a chat.

    The user's flow, in his words: he asks a web model for a `semilla`, deposits
    it, and **if there is a bug the micelio hands him a `hongo`**; he passes the
    hongo to the web model, which answers with a `nutriente`; if the nutriente
    fixes it, the seed runs and a `fruto` is created.

    So the hongo is not an error log. It is the envelope a model needs to write
    a correction WITHOUT seeing the machine: what was asked, which criteria went
    red and with what literal message, and what the organism actually produced.
    Anything cut is declared -- a hongo that silently drops the failing file
    reads as if the failure had no context.
    """
    r = verificar(sobre, raiz)
    rojos = [c for c in r.checks if not c["verde"]]
    base = {
        "formato": FORMATO,
        "de": sobre.get("asunto", "")[:200],
        "criterio": sobre.get("criterio") or [],
    }
    if r.verde:
        return dict(base, tipo="fruto", asunto="crecio: " + sobre.get("asunto", "")[:150],
                    cuerpo={"verde": True,
                            "checks": r.checks,
                            "que_se_pidio": sobre.get("cuerpo") or {}})

    # Lo que el organismo produjo, para que el modelo web pueda corregirlo sin
    # ver la maquina. Sin esto el nutriente se escribe a ciegas.
    piezas, recortado = _piezas_del_criterio(sobre, raiz, tope)
    if not r.checks:
        rojos = [{"nombre": "sin criterio", "verde": False,
                  "detalle": "el sobre no trae criterio: no hay nada que "
                             "verificar, y eso NO es verde"}]
    hongo = dict(base, tipo="hongo",
                 asunto="no crecio: " + sobre.get("asunto", "")[:150],
                 cuerpo={"verde": False,
                         "fallaron": rojos,
                         "pasaron": [c for c in r.checks if c["verde"]],
                         "que_se_pidio": sobre.get("cuerpo") or {},
                         "lo_que_hay": piezas,
                         "que_hacer": "Devolve un sobre `nutriente` con el "
                                      "mismo `criterio`, diciendo QUE cambiar y "
                                      "DONDE. No expliques nada fuera del JSON."})
    if recortado:
        hongo["recortado"] = recortado
    return hongo


def _piezas_del_criterio(sobre: dict, raiz: Path | str, tope: int) -> tuple[dict, dict]:
    """The files the criterion points at, so the hongo carries the evidence."""
    raiz = Path(raiz)
    piezas: dict[str, str] = {}
    recortado: dict[str, Any] = {}
    rutas: list[str] = []
    for c in sobre.get("criterio") or []:
        for clave in ("modulo", "ruta"):
            if c.get(clave):
                rutas.append(str(c[clave]))
    gastado = 0
    for ruta in dict.fromkeys(rutas):
        p = raiz / ruta
        if not p.is_file():
            piezas[ruta] = "(no existe)"
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            piezas[ruta] = "(no se pudo leer: %s)" % e
            continue
        disponible = max(0, tope - gastado)
        if len(texto) > disponible:
            recortado[ruta] = {"bytes_totales": len(texto),
                               "bytes_incluidos": disponible}
            texto = texto[:disponible]
        gastado += len(texto)
        piezas[ruta] = texto
    return piezas, recortado


def _correr_criterio(c: dict, raiz: Path) -> tuple[bool, str]:
    t = c["tipo"]
    if t == "archivo":
        p = raiz / c["ruta"]
        if not p.exists():
            return False, "no existe %s" % c["ruta"]
        minimo = int(c.get("min_bytes", 1))
        n = p.stat().st_size
        return n >= minimo, "%s pesa %d bytes (min %d)" % (c["ruta"], n, minimo)

    if t == "campo":
        p = raiz / c["ruta"]
        if not p.exists():
            return False, "no existe %s" % c["ruta"]
        d = json.loads(p.read_text(encoding="utf-8"))
        valor = d
        for parte in str(c["campo"]).split("."):
            valor = valor[parte] if isinstance(valor, dict) else None
            if valor is None:
                return False, "no hay campo %s en %s" % (c["campo"], c["ruta"])
        if "igual" in c:
            return valor == c["igual"], "%s = %r (esperaba %r)" % (
                c["campo"], valor, c["igual"])
        if "min" in c:
            n = len(valor) if isinstance(valor, (list, dict, str)) else valor
            return n >= c["min"], "%s = %s (min %s)" % (c["campo"], n, c["min"])
        return True, "%s presente" % c["campo"]

    if t == "comando":
        # Separate process with a timeout: a command that hangs cannot hang
        # the semaphore. No shell: the list is the list.
        r = subprocess.run([str(x) for x in c["cmd"]], cwd=str(raiz),
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=int(c.get("timeout", 120)))
        esperado = int(c.get("codigo", 0))
        salida = ((r.stdout or "") + (r.stderr or "")).strip()
        if "contiene" in c and c["contiene"] not in salida:
            return False, "la salida no contiene %r" % c["contiene"]
        return r.returncode == esperado, "codigo %d (esperaba %d)%s" % (
            r.returncode, esperado,
            "" if r.returncode == esperado else " -- " + salida.splitlines()[-1][:120]
            if salida else "")

    if t == "caso":
        # The module runs in a separate process on purpose: the code being
        # verified was written by a model, and a `while True` of its own cannot
        # be allowed to hang the organism verifying it.
        guion = (
            "import json,sys,importlib.util\n"
            "spec=importlib.util.spec_from_file_location('m',%r)\n"
            "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "print(json.dumps(getattr(m,%r)(*json.loads(%r))))\n"
            % (str(raiz / c["modulo"]), c["funcion"], json.dumps(c["entrada"])))
        r = subprocess.run([sys.executable, "-c", guion], capture_output=True,
                           text=True, encoding="utf-8",
                           timeout=int(c.get("timeout", 30)))
        if r.returncode != 0:
            ultima = (r.stderr or "").strip().splitlines() or ["sin stderr"]
            return False, "reventó: %s" % ultima[-1][:120]
        obtenido = json.loads((r.stdout or "").strip().splitlines()[-1])
        ok = obtenido == c["salida"]
        return ok, "%s(%s) -> %r%s" % (
            c["funcion"], ", ".join(repr(x) for x in c["entrada"]), obtenido,
            "" if ok else " (esperaba %r)" % (c["salida"],))

    return False, "tipo de criterio desconocido: %r" % t


# ------------------------------------------------------------------- fruto

def fruto(asunto: str, medido: dict, anomalias: list, muestras: list,
          punteros: list | None = None, tope: int = TOPE_FRUTO_BYTES) -> dict:
    """Build a fruit that FITS in a chat window.

    A fruit is not a dump. If the organism returned its 3.138 fichas they paste
    nowhere and the cycle breaks on the return trip, which is its most
    important step. It carries: the measured state, what is ANOMALOUS, a few
    samples, and pointers to where the rest lives.

    Whatever is cut is DECLARED in `recortado`. A silent truncation reads as
    "that was everything", the lie this repo has already paid for more than
    once.
    """
    sobre = {
        "formato": FORMATO,
        "tipo": "fruto",
        "asunto": asunto,
        "cuerpo": {
            "medido": medido,
            "anomalias": list(anomalias),
            "muestras": list(muestras),
            "punteros": list(punteros or []),
        },
        "recortado": {},
    }
    # Cut from the tail of the long lists, never through the middle of an
    # element: half a sample is a sample that lies.
    for clave in ("muestras", "anomalias"):
        while (len(json.dumps(sobre, ensure_ascii=False).encode("utf-8")) > tope
               and sobre["cuerpo"][clave]):
            sobre["cuerpo"][clave].pop()
            sobre["recortado"][clave] = sobre["recortado"].get(clave, 0) + 1
    return sobre


def medir_dataset(ruta: str | Path, muestras: int = 4) -> tuple[dict, list, list]:
    """Measure a .json/.jsonl and return (medido, anomalias, muestras).

    Answers the question that has no mechanical answer today: **which fields
    carry data and which do not**. Measured 2026-07-31 over the curation's
    3.138 fichas: `ocr_texto` empty in 76% and `datos_evento` empty in 69%.
    That emptiness does not distinguish "there was no text" from "I did not
    try", which is why no skin can trust the field. Coverage does not fix it,
    but it makes it VISIBLE, and that was the missing step.

    A field under 40% is reported as an anomaly -- not because 40 is magic, but
    because a field missing from more than half the records is not a field, it
    is a promise.
    """
    p = Path(ruta)
    registros: list[dict] = []
    texto = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".jsonl":
        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if isinstance(d, dict):
                registros.append(d)
    else:
        d = json.loads(texto)
        for clave in ("piezas", "obras", "items", "registros"):
            if isinstance(d, dict) and isinstance(d.get(clave), list):
                registros = [x for x in d[clave] if isinstance(x, dict)]
                break
        else:
            if isinstance(d, list):
                registros = [x for x in d if isinstance(x, dict)]

    total = len(registros)
    if not total:
        return {"archivo": p.name, "registros": 0}, [
            {"campo": None, "problema": "el archivo no trae registros que medir"}
        ], []

    presente: dict[str, int] = {}
    for r in registros:
        for k, v in r.items():
            if v not in (None, "", [], {}):
                presente[k] = presente.get(k, 0) + 1
            else:
                presente.setdefault(k, 0)

    cobertura = {k: round(100 * n / total) for k, n in sorted(presente.items())}
    anomalias = [
        {"campo": k, "cobertura_pct": pct,
         "problema": "vacio en el %d%% de los registros; un vacio no dice si "
                     "no habia dato o si no se intento medir" % (100 - pct)}
        for k, pct in cobertura.items() if pct < 40
    ]
    medido = {"archivo": p.name, "registros": total, "cobertura_pct": cobertura}
    # Samples from the POOR end: an average record teaches nothing, an empty
    # one shows exactly what the skin is going to receive.
    ordenados = sorted(registros,
                       key=lambda r: sum(1 for v in r.values()
                                         if v not in (None, "", [], {})))
    return medido, anomalias, ordenados[:muestras]


def escribir(sobre: dict, ruta: str | Path) -> Path:
    p = Path(ruta)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sobre, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")
    return p


# ------------------------------------------------------------- el formato

def formato_para_el_modelo() -> str:
    """What the user pastes into the web model BEFORE describing the idea.

    It exists so the expensive half of the cycle does not depend on the user
    remembering the rules: copy this, paste it, and the model already knows
    what it has to return. The text itself stays in Spanish -- it is read by a
    human and by the model, so it is a product string, not a comment.
    """
    return _FORMATO_TXT


_FORMATO_TXT = """\
Vas a escribir un SOBRE para un organismo automatico (se llama MAK). El sobre
es un unico objeto JSON. No expliques nada fuera del JSON.

    {
      "formato": "micelio/1",
      "tipo": "semilla" | "nutriente",
      "asunto": "una linea que diga de que se trata",
      "cuerpo": { ... },
      "criterio": [ ... ]
    }

QUE ES CADA TIPO

  semilla    una idea mia, traducida a algo que el organismo pueda germinar
             solo, sin que yo este mirando. En `cuerpo` va lo que decidas que
             necesita: objetivo, campos, restricciones. Se concreto.

  nutriente  una orden de correccion sobre algo que ya existe y salio mal.
             En `cuerpo` va que hay que arreglar y donde.

EL `criterio` ES OBLIGATORIO Y ES LA PARTE QUE IMPORTA

Quien va a ejecutar esto es un modelo DEBIL, sin supervision. No puede juzgar
si entendio bien. Por eso el sobre tiene que traer como se sabe que salio
bien, en una forma que una maquina pueda correr. No escribas "que quede mejor"
ni "que sea mas organico": eso no lo puede verificar nadie.

Hay cuatro formas de criterio y solo cuatro:

  {"tipo":"caso","modulo":"ruta/x.py","funcion":"f","entrada":[1,2],"salida":3}
      importa el modulo, llama la funcion con esos argumentos, compara.
      Es la mas fuerte. Usala siempre que puedas.

  {"tipo":"comando","cmd":["py","-m","pytest","tests/x.py"],"codigo":0}
      corre el comando, exige ese codigo de salida.
      Opcional: "contiene":"texto que debe aparecer en la salida".

  {"tipo":"archivo","ruta":"datos/x.json","min_bytes":100}
      el archivo tiene que existir y pesar al menos eso.

  {"tipo":"campo","ruta":"datos/x.json","campo":"a.b","min":10}
      ese campo del JSON tiene que existir; "min" para tamano, "igual" para
      un valor exacto.

REGLAS

1. Si no sabes escribir un criterio verificable para algo, DECILO en `asunto`
   y no lo inventes. Un criterio falso es peor que ninguno: da verde sobre
   trabajo que no se hizo.
2. Varios criterios estan bien. Todos tienen que dar verde.
3. No pongas rutas absolutas ni datos personales: el repo es publico.
4. Devolve SOLO el JSON.

QUE VAS A RECIBIR DE VUELTA, Y ES UNA DE DOS

El organismo corre el criterio y devuelve un sobre. Siempre uno de estos dos:

  fruto   crecio. El criterio dio verde entero. No hay nada que corregir.

  hongo   NO crecio. Trae, para que puedas escribir la correccion SIN VER LA
          MAQUINA:
            "fallaron":    que criterios se pusieron rojos, con el mensaje
                           literal de cada uno
            "pasaron":     los que si, para que no rompas lo que funciona
            "que_se_pidio": el cuerpo de la semilla original
            "lo_que_hay":  el contenido REAL de los archivos que el criterio
                           nombra, tal como estan ahora
            "recortado":   si algo no entro, cuanto se dejo afuera

SI TE LLEGA UN HONGO, TU RESPUESTA ES UN NUTRIENTE

Un sobre `"tipo":"nutriente"` con el MISMO `criterio` -- no lo aflojes para que
pase: un criterio ablandado da verde sobre trabajo que no se hizo. En `cuerpo`
va que cambiar y donde. Mira `fallaron` antes que nada: ahi esta el mensaje
literal, que dice mas que cualquier suposicion sobre por que fallo.

El ciclo entero es: semilla -> (hongo -> nutriente -> hongo -> ...) -> fruto.
Se repite hasta que crece, y quien decide si crecio es el criterio, no vos ni
yo.

`recortado` no es un detalle: si dice algo, lo que estas leyendo NO es todo.
"""
