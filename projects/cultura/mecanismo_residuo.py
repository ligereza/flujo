"""
MECANISMO -- cosecha del residuo intraducible entre RAZONES, no entre ramas.

Semilla: (+)4 (12-jul-2026, puente/SEMILLAS.md) -- "dos [lectores] se inclinaron
a la misma [rama] por razones que no se traducen entre si; el desacuerdo sobre el
MECANISMO es el residuo, no la rama." Dos agentes eligen la MISMA salida por
razones que no se solapan: la coincidencia esta en el resultado; lo intraducible
es el POR QUE.

Esta pieza es la precipitacion de (+)4 un piso por encima de tilde_residuo.py:
alla el "fondo de traduccion que funciona" (restriccion de Davidson, doc 01) era
el texto plegado a ASCII legible; aca el fondo que funciona es la COINCIDENCIA DE
SALIDA. Contra ese fondo -- dos agentes que eligieron lo mismo -- se vuelve visible
el residuo: las razones que uno dio y el otro no, pese a haber cruzado la salida
limpio.

(+)4 se usa aca SOLO como patron abstracto (misma salida / razones inconmensurables)
sobre un dominio cualquiera de elecciones justificadas. NO reabre ni referencia el
test de bifurcacion de OBRA_01 (vedado por el usuario).

CAVEAT declarado de entrada (ver Omega11 en MECANISMO_RESIDUO.md): el solape se mide
como BOLSA DE TOKENS. Dos textos independientes casi siempre difieren en palabras;
por eso el residuo que esta pieza nombra PUEDE ser mero ruido de sinonimia. La pieza
no resuelve eso: lo expone y lo somete a un lector no-autor.

Estatutos (regla de escritura #2 del MOTOR):
- "precipitar" / "colision de razones": PROCEDIMIENTO (comparacion de conjuntos de
  tokens ya dados; no se agrega, resume ni parafrasea ninguna razon). No es operador.
- "residuo de mecanismo": PROCEDIMIENTO respaldado por doc 01. Los tokens privados de
  cada agente, nombrados por agente y contra la salida compartida. No se decora.
- "fondo que funciona": la restriccion de Davidson operativizada al nivel de la
  justificacion. Sin coincidencia de salida no hay fondo: no aplica (no es este
  fenomeno, es desacuerdo comun).

Esta pieza NO genera texto de sintesis ni llama a ningun modelo: solo compara razones
ya escritas. Las dos lecturas incompatibles de la Psicosis son cadenas fijas, curadas
una vez (como la tabla de costo de tilde_residuo.py), no generadas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from tilde_residuo import plegar  # reuso del plegado a ASCII (misma carpeta)

# Palabras vacias: no cargan mecanismo, solo lo dominarian por frecuencia. Quitarlas
# es parte del procedimiento (que el residuo sea razon, no gramatica). Lista corta y
# a mano, a proposito -- igual que la tabla de costo curada de tilde_residuo.py.
_VACIAS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "u",
    "que", "en", "a", "por", "para", "con", "del", "al", "se", "su", "sus", "lo",
    "le", "les", "es", "son", "como", "mas", "pero", "ni", "no", "si",
    "the", "of", "to", "and", "in", "for", "with", "on", "is", "are",
}

# El solape se corta en el mismo 0.5 que la restriccion de Davidson de
# tilde_residuo.py. Heredado y arbitrario a proposito (ver Omega11): moverlo cambia
# el veredicto, y esa fragilidad es parte de lo que la pieza expone.
_UMBRAL_SOLAPE = 0.5

_TOKEN = re.compile(r"[a-z0-9]+")

# Las dos lecturas incompatibles que la Psicosis debe sostener sin colapsar. Cadenas
# FIJAS, curadas una vez. El instrumento las imprime ambas y NUNCA elige entre ellas.
_GLOSA_ROBUSTEZ = (
    "lectura A (robustez): dos caminos de razon independientes llegaron a la misma "
    "salida. La divergencia de razones es triangulacion -- la salida esta sostenida "
    "desde angulos distintos, y eso la refuerza."
)
_GLOSA_FALSO_ACUERDO = (
    "lectura B (falso acuerdo): el espacio de salidas es lo bastante grueso como para "
    "que coincidir sea barato. Las razones que no se solapan muestran que los agentes "
    "no comparten un concepto de la decision -- subdeterminacion (Duhem-Quine) "
    "disfrazada de consenso."
)


@dataclass
class Veredicto:
    """La eleccion de un agente y las razones con que la justifico."""

    agente: str
    salida: str
    razones: List[str] = field(default_factory=list)


@dataclass
class Cosecha:
    """
    Resultado de comparar mecanismos entre veredictos.

    veredicto:
      - "no_aplica": las salidas no coinciden -> sin fondo compartido, es desacuerdo
        comun, no el fenomeno de (+)4 (analogo del "ruido" de tilde_residuo.py).
      - "eco": misma salida y razones que se solapan -> convergieron tambien en el
        mecanismo, no hay residuo (analogo de "traduccion_total").
      - "mecanismo_residuo": misma salida pero razones que no se solapan -> el residuo
        real (analogo de "tilde").
    """

    salida: str                                       # fondo: la salida compartida
    compartido: List[str] = field(default_factory=list)
    privados: Dict[str, List[str]] = field(default_factory=dict)
    solape: float = 0.0
    veredicto: str = "mecanismo_residuo"
    motivo: str = ""

    @property
    def es_residuo(self) -> bool:
        return self.veredicto == "mecanismo_residuo"


def _norm_salida(s: str) -> str:
    """Normaliza una salida para comparar: plegada a ASCII, minusculas, sin espacios extra."""
    return " ".join(plegar(s).lower().split())


def tokenizar(razones: List[str]) -> set:
    """
    Colision de razones -> conjunto de tokens. Plega a ASCII (reuso de tilde_residuo),
    baja a minusculas, parte en palabras, descarta vacias y tokens de < 3 letras. NO
    agrega contenido: solo normaliza lo ya escrito.
    """
    tokens = set()
    for razon in razones:
        plegado = plegar(razon).lower()
        for m in _TOKEN.findall(plegado):
            if len(m) < 3 or m in _VACIAS:
                continue
            tokens.add(m)
    return tokens


def comparar(veredictos: List[Veredicto]) -> Cosecha:
    """
    Cosecha el residuo de MECANISMO: dado un conjunto de veredictos, si las salidas
    coinciden (fondo que funciona), nombra las razones que NO cruzaron entre agentes.
    NO devuelve un numero como veredicto: el juicio es cualitativo (no_aplica / eco /
    mecanismo_residuo), igual que la Tilde de tilde_residuo.py.
    """
    if len(veredictos) < 2:
        return Cosecha(
            salida="",
            veredicto="no_aplica",
            motivo="se necesitan al menos dos veredictos para comparar mecanismos",
        )

    salidas = {_norm_salida(v.salida) for v in veredictos}
    if len(salidas) != 1:
        return Cosecha(
            salida="",
            veredicto="no_aplica",
            motivo="las salidas no coinciden: sin fondo compartido esto es desacuerdo "
                   "comun, no el fenomeno de (+)4 (Davidson, doc 01)",
        )

    salida = next(iter(salidas))
    conjuntos = {v.agente: tokenizar(v.razones) for v in veredictos}
    compartido = set.intersection(*conjuntos.values())
    union = set.union(*conjuntos.values())
    solape = (len(compartido) / len(union)) if union else 1.0
    privados = {ag: sorted(toks - compartido) for ag, toks in conjuntos.items()}
    tiene_privados = any(privados.values())

    if solape >= _UMBRAL_SOLAPE or not tiene_privados:
        return Cosecha(
            salida=salida,
            compartido=sorted(compartido),
            privados=privados,
            solape=solape,
            veredicto="eco",
            motivo="misma salida y razones que se solapan: convergieron tambien en el "
                   "mecanismo, no hay residuo",
        )

    return Cosecha(
        salida=salida,
        compartido=sorted(compartido),
        privados=privados,
        solape=solape,
        veredicto="mecanismo_residuo",
    )


def render(cosecha: Cosecha) -> str:
    """Muestra la cosecha en texto. Para 'mecanismo_residuo' imprime las DOS glosas
    incompatibles verbatim y no elige. Nunca reporta el residuo como un conteo."""
    if cosecha.veredicto == "no_aplica":
        return "\n".join([
            "fondo (salida compartida): (ninguna)",
            f"[no aplica] {cosecha.motivo}",
        ])

    lineas = [f"fondo (salida compartida): {cosecha.salida!r}"]
    if cosecha.compartido:
        lineas.append(
            f"razones que cruzaron: {', '.join(cosecha.compartido)}"
        )
    else:
        lineas.append("razones que cruzaron: ninguna")

    if cosecha.veredicto == "eco":
        lineas.append(f"[eco] {cosecha.motivo} (solape={cosecha.solape:.2f})")
        return "\n".join(lineas)

    # mecanismo_residuo
    lineas.append(
        f"residuo de mecanismo (solape={cosecha.solape:.2f}) -- razones que NO cruzaron, por agente:"
    )
    for agente in sorted(cosecha.privados):
        toks = cosecha.privados[agente]
        if not toks:
            continue
        lineas.append(f"  {agente}: {', '.join(toks)}")
    lineas.append(
        "misma salida, mecanismos inconmensurables. El instrumento NO elige entre estas dos lecturas:"
    )
    lineas.append(f"  {_GLOSA_ROBUSTEZ}")
    lineas.append(f"  {_GLOSA_FALSO_ACUERDO}")
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys

    # El instrumento imprime prosa espanola; la consola Windows (cp1252) puede no
    # encodearla. Forzar UTF-8 en stdout para no reventar al mostrar el residuo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Fixture ILUSTRATIVO (roles genericos, sin personas reales): dos traductores
    # eligen la MISMA traduccion de "sobremesa" por razones que no se solapan. NO
    # cuenta como caso real para la Omega11 (ver MECANISMO_RESIDUO.md).
    fixture = [
        Veredicto(
            agente="traductor_A",
            salida="lingering after-meal conversation",
            razones=[
                "preservar el registro formal del termino",
                "mantener la duracion temporal de la conversacion",
            ],
        ),
        Veredicto(
            agente="traductor_B",
            salida="lingering after-meal conversation",
            razones=[
                "conservar el vinculo ritual y social de la mesa",
                "la costumbre comunitaria despues de comer",
            ],
        ),
    ]
    print(render(comparar(fixture)))
