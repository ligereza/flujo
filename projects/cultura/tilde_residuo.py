"""
Tilde -- cosecha del residuo intraducible (instrumento honesto).

Semilla: (+)3 (12-jul-2026, puente/SEMILLAS.md) -- "tilde_meter mide tokens =
dialecto Omega degradado. La Tilde NO es ahorro de tokens, es residuo
intraducible." desktop/tilde_meter.py cuenta tokens; eso es medir la Tilde en su
dialecto degradado. Este modulo la mide como la define el nucleo (doc 01): el
residuo que NO cruza un cambio de codigo, nombrado con precision, visible solo
contra un fondo de traduccion que funciona (restriccion de Davidson).

El cruce de codigo aca es el plegado del espanol a ASCII: quitar diacriticos y
borrar las aperturas invertidas. Es una traduccion que mayormente funciona -- el
texto plegado sigue siendo legible -- y por eso el residuo se ve. La virgulilla
de la 'n' -> 'n' (la tilde de esta pieza) es el caso mas filoso: 'ano' pierde su
marca y se vuelve 'ano'.

Estatutos (regla de escritura #2 del MOTOR):
- "plegado" / "cruce de codigo": PROCEDIMIENTO. No es un operador matematico.
- "residuo": PROCEDIMIENTO respaldado por doc 01. Es lo que el plegado destruye y
  no se recupera del fondo solo. Se nombra (que, entre que y que, su costo); no se
  decora.
- "fondo legible": la restriccion de Davidson operativizada. Si el plegado no deja
  fondo legible, nada cruzo: es ruido, no Tilde.

Esta pieza NO devuelve un conteo de tokens en ningun punto: ese seria el dialecto
degradado que (+)3 rechaza.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import List

# Aperturas invertidas del espanol: no son diacriticos (no descomponen), pero el
# plegado a ASCII las borra. Su perdida es pragmatica: el espanol avisa la
# pregunta/exclamacion ANTES de la frase; el fondo plegado pierde ese aviso temprano.
_APERTURA = {"¿", "¡"}

# Costo de significado de los residuos mas filosos: pares minimos reales donde
# perder la marca cambia o invierte el sentido. Curado a mano y a proposito (ver
# la Omega11 en TILDE_RESIDUO.md): cuanto duele cada perdida no se computa.
_COSTO_POR_CHAR = {
    "ñ": "'ano' (year) -> 'ano' (anus); la marca ES la virgulilla homonima de esta pieza",
    "Ñ": "'ANO' (year) -> 'ANO' (anus); la virgulilla homonima de esta pieza",
    "á": "'papa' (dad) -> 'papa' (potato/pope)",
    "é": "'el' (he) -> 'el' (the)",
    "í": "'si' (yes) -> 'si' (if)",
    "ó": "'hablo' (spoke) -> 'hablo' (I speak)",
    "ú": "'aun' (still) -> 'aun' (even)",
    "ü": "'pinguino' -> 'pinguino'; la u deja de sonar",
    "¿": "el espanol marca la pregunta antes de abrirla; se pierde el aviso temprano",
    "¡": "el espanol marca la exclamacion antes de abrirla; se pierde el aviso temprano",
}


@dataclass
class Residuo:
    """Una marca que no cruzo el plegado, nombrada con precision."""

    indice: int          # posicion en el texto original
    original: str        # el caracter con marca ('n' con virgulilla)
    plegado: str         # a que colapso ('n'); '' si se borro entero
    marca: str           # identidad Unicode de lo perdido ('COMBINING TILDE')
    costo: str           # costo de significado (par minimo si es filoso)


@dataclass
class Cosecha:
    """
    Resultado de cosechar la Tilde de un texto.

    veredicto:
      - "tilde": hay fondo legible Y residuo -> es una Tilde real.
      - "traduccion_total": fondo legible pero nada se perdio -> no hay residuo.
      - "ruido": no quedo fondo legible (nada cruzo) -> no es Tilde (Davidson).
    """

    fondo: str
    residuos: List[Residuo] = field(default_factory=list)
    veredicto: str = "tilde"
    motivo: str = ""

    @property
    def es_tilde(self) -> bool:
        return self.veredicto == "tilde"


def plegar(texto: str) -> str:
    """
    La traduccion que mayormente funciona: espanol -> ASCII. Quita diacriticos
    (NFD + descartar marcas combinantes) y borra las aperturas invertidas. El
    resultado sigue siendo legible: ese es el fondo contra el que se ve el residuo.
    """
    texto = unicodedata.normalize("NFC", texto)
    salida = []
    for ch in texto:
        if ch in _APERTURA:
            continue
        descompuesto = unicodedata.normalize("NFD", ch)
        base = "".join(c for c in descompuesto if not unicodedata.combining(c))
        salida.append(base)
    return "".join(salida)


def _fondo_legible(original: str, fondo: str) -> bool:
    """
    Restriccion de Davidson (doc 01): el residuo solo es visible contra un fondo
    de traduccion que funciona. Si el plegado no conserva la mayoria del material
    alfabetico como ASCII legible, nada cruzo: es ruido, no Tilde.
    """
    orig_alpha = [c for c in original if c.isalpha()]
    if not orig_alpha:
        return False
    fondo_ascii = [c for c in fondo if c.isalpha() and c.isascii()]
    if not fondo_ascii:
        return False
    return len(fondo_ascii) >= 0.5 * len(orig_alpha)


def _costo_de(ch: str, marca_nombre: str, base: str) -> str:
    if ch in _COSTO_POR_CHAR:
        return _COSTO_POR_CHAR[ch]
    return f"diacritico {marca_nombre} sobre '{base}'"


def cosechar(texto: str) -> Cosecha:
    """
    Cosecha la Tilde: el residuo que NO cruza el plegado a ASCII, nombrado con
    precision. NO cuenta tokens (esa es la lectura degradada que critica (+)3):
    devuelve QUE se perdio, entre que y que, y su costo de significado.

    Normaliza a NFC primero: 'n con virgulilla' entra igual venga precompuesta
    (un caracter) o descompuesta (n + marca combinante). El residuo es el mismo
    caracter, asi que la cosecha no depende de como se tipeo la entrada.
    """
    texto = unicodedata.normalize("NFC", texto)
    fondo = plegar(texto)
    if not _fondo_legible(texto, fondo):
        return Cosecha(
            fondo=fondo,
            residuos=[],
            veredicto="ruido",
            motivo="nada cruzo: sin fondo de traduccion legible, esto es ruido (Davidson, doc 01)",
        )

    residuos: List[Residuo] = []
    for i, ch in enumerate(texto):
        if ch in _APERTURA:
            nombre = unicodedata.name(ch, "MARCA DE APERTURA DESCONOCIDA")
            residuos.append(
                Residuo(indice=i, original=ch, plegado="", marca=nombre,
                        costo=_costo_de(ch, nombre, ""))
            )
            continue
        descompuesto = unicodedata.normalize("NFD", ch)
        marcas = [c for c in descompuesto if unicodedata.combining(c)]
        if not marcas:
            continue  # cruzo limpio, sin residuo
        base = "".join(c for c in descompuesto if not unicodedata.combining(c))
        for m in marcas:
            nombre = unicodedata.name(m, "MARCA COMBINANTE DESCONOCIDA")
            residuos.append(
                Residuo(indice=i, original=ch, plegado=base, marca=nombre,
                        costo=_costo_de(ch, nombre, base))
            )

    if not residuos:
        return Cosecha(
            fondo=fondo,
            residuos=[],
            veredicto="traduccion_total",
            motivo="nada se perdio: traduccion total, no hay residuo que cosechar",
        )
    return Cosecha(fondo=fondo, residuos=residuos, veredicto="tilde")


def render(cosecha: Cosecha) -> str:
    """Muestra la cosecha en texto. Nunca imprime un conteo de tokens."""
    lineas = [f"fondo (traduccion que funciona): {cosecha.fondo!r}"]
    if cosecha.veredicto == "ruido":
        lineas.append(f"[ruido] {cosecha.motivo}")
        return "\n".join(lineas)
    if cosecha.veredicto == "traduccion_total":
        lineas.append(f"[sin residuo] {cosecha.motivo}")
        return "\n".join(lineas)
    lineas.append(f"residuo intraducible ({len(cosecha.residuos)} marca(s)):")
    for r in cosecha.residuos:
        origen = r.plegado if r.plegado else "(borrado)"
        lineas.append(f"  @{r.indice} {r.original!r} -> '{origen}' | {r.marca} | {r.costo}")
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys

    # El instrumento imprime diacriticos; la consola Windows (cp1252) no los
    # encodea. Forzar UTF-8 en stdout para no reventar al mostrar el residuo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    texto = " ".join(sys.argv[1:]) or "El año pasado, ¿aún hablás español, pingüino?"
    print(render(cosechar(texto)))
