"""
Fila Cero -- el que escribio no puede ser contagiado por lo que escribio.

Semilla: (+)1 (11-jul-2026, puente/SEMILLAS.md) -- "asimetria de acceso: quien
puede ser contagiado por cual rama; el que escribio no puede ser contagiado por
lo que escribio." (de OBRA_01). OBRA_01 AFIRMA esa inmunidad en prosa; su Omega11
solo mide el contagio del LECTOR. Aca la inmunidad del autor deja de ser una
afirmacion y se vuelve una propiedad estructural del modelo de datos: en el libro
mayor de contagio, la fila del autor sobre su propia rama NO tiene campo 'antes'
libre -- se DERIVA, siempre igual a 'despues', por construccion, no por medicion.

El cruce de codigo aca es literario -> registro: se toma el material de OBRA_01
(ramas, "quien se contagia de cual") y se lo colisiona con el esquema de un libro
mayor de contacto / bitacora de blame (quien toco que, cuando, que cambio). No se
agrega narrativa nueva. Lo que baja de umbral es la VISIBILIDAD de la asimetria:
en prosa hay que confiar en la afirmacion; como esquema, la fila del autor
literalmente no puede portar un 'antes' libre.

Estatutos (regla de escritura #2 del MOTOR):
- "libro mayor de contagio" / "fila": PROCEDIMIENTO (esquema de bitacora prestado).
  No es un operador matematico.
- "delta": PROCEDIMIENTO. Es un hecho registrado (antes != despues), exacto. NO es
  "contagio": contagio afirma causa; delta solo aporta una diferencia con fecha.
- "fila cero": la fila del autor sobre su propia rama, congelada por construccion.
  No es un permiso ("no podes editar tu fila") -- es que el dato no existe: el
  autor no recibe un campo 'antes' para su propia rama, solo lo reciben los demas.

LIMITE DURO (psicosis): esta pieza solo guarda etiquetas de texto libre que el
lector elige sobre SU PROPIA postura -- nunca inferidas, nunca diagnosticas, nunca
sobre un tercero real. No perfila a nadie: 'antes'/'despues' los escribe quien lee.

Esta pieza NUNCA afirma que un delta fue CAUSADO por la rama: la causa no cruza a
codigo (ver contagio-vs-delta en FILA_CERO.md). Por eso cada delta se reporta como
"causa NO verificada", y esa honestidad es el residuo (Tilde) que cosecha.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Rama:
    """
    Una rama del corpus: un material que alguien escribio y firmo.

    'postura' es la etiqueta de texto libre que el AUTOR eligio para su propia
    rama (p.ej. "Duda"). Es tambien, por (+)1, su 'antes' y su 'despues' sobre esa
    rama: el autor no puede moverse respecto de lo que escribio, asi que su lectura
    de si mismo esta congelada en esa postura.
    """

    id: str
    autor_id: str
    postura: str


@dataclass(frozen=True)
class Lectura:
    """
    Una lectura de una rama por un lector, con su postura antes y despues.

    Construccion asimetrica (el motor de (+)1):
      - Si lector_id != rama.autor_id: el lector aporta 'antes' y 'despues' libres
        (los escribe el, sobre su propia postura -- nunca inferidos).
      - Si lector_id == rama.autor_id: NO se acepta 'antes'/'despues' distintos.
        Se DERIVAN ambos como la 'postura' de la rama. Intentar construir una
        auto-lectura del autor con antes != despues es imposible: levanta
        ValueError. La fila del autor sobre su propia rama no tiene 'antes' libre;
        es la Fila Cero, congelada por construccion (no filtrada despues).

    Se usa la fabrica `Lectura.registrar(rama, lector_id, antes=?, despues=?)`; el
    __init__ crudo no deberia invocarse a mano para auto-lecturas (no conoce la
    rama). `registrar` es el unico punto donde vive la regla.
    """

    rama_id: str
    lector_id: str
    autor_id: str
    antes: str
    despues: str
    es_autor: bool

    def __post_init__(self) -> None:
        # La Fila Cero es estructural, no una convencion de la fabrica: incluso el
        # constructor crudo rechaza una auto-lectura del autor con antes != despues.
        # Por (+)1, el que escribio no es contagiado por lo que escribio, y eso no
        # se puede eludir esquivando `registrar`.
        if self.es_autor and self.antes != self.despues:
            raise ValueError(
                f"Fila Cero: auto-lectura del autor {self.lector_id!r} con "
                f"antes={self.antes!r} != despues={self.despues!r} es imposible por "
                f"construccion (no por filtro posterior): su antes y su despues se "
                f"derivan de la postura, no se ingresan."
            )

    @property
    def delta(self) -> bool:
        """True si la postura cambio entre antes y despues. Para la Fila Cero
        (autor sobre su rama) es SIEMPRE False, por construccion, no por medicion."""
        return self.antes != self.despues

    @classmethod
    def registrar(
        cls,
        rama: Rama,
        lector_id: str,
        antes: Optional[str] = None,
        despues: Optional[str] = None,
    ) -> "Lectura":
        """
        Registra una lectura respetando la asimetria de acceso de (+)1.

        Lector ajeno: exige antes/despues (texto libre del propio lector).
        Autor sobre su rama: DERIVA antes==despues==rama.postura y RECHAZA cualquier
        intento de pasar un antes/despues distinto de la postura (levanta ValueError).
        """
        es_autor = lector_id == rama.autor_id
        if es_autor:
            # La Fila Cero: el autor no recibe un campo 'antes' libre. Si alguien
            # intenta declarar un movimiento del autor sobre su propia rama, no se
            # filtra en silencio: se rechaza. La inmunidad es estructural.
            for etiqueta, valor in (("antes", antes), ("despues", despues)):
                if valor is not None and valor != rama.postura:
                    raise ValueError(
                        f"Fila Cero: el autor {lector_id!r} no puede declarar "
                        f"{etiqueta}={valor!r} sobre su propia rama {rama.id!r}. "
                        f"Por (+)1, el que escribio no es contagiado por lo que "
                        f"escribio: su antes y su despues se derivan de la postura "
                        f"{rama.postura!r}, no se ingresan."
                    )
            return cls(
                rama_id=rama.id,
                lector_id=lector_id,
                autor_id=rama.autor_id,
                antes=rama.postura,
                despues=rama.postura,
                es_autor=True,
            )
        # Lector ajeno: antes/despues son obligatorios y los escribe el lector.
        if antes is None or despues is None:
            raise ValueError(
                f"El lector {lector_id!r} debe declarar su propio antes y despues "
                f"sobre la rama {rama.id!r} (texto libre, sobre su propia postura)."
            )
        return cls(
            rama_id=rama.id,
            lector_id=lector_id,
            autor_id=rama.autor_id,
            antes=antes,
            despues=despues,
            es_autor=False,
        )


@dataclass
class LibroMayor:
    """El libro mayor de contagio: ramas + lecturas registradas contra ellas."""

    ramas: Dict[str, Rama] = field(default_factory=dict)
    lecturas: List[Lectura] = field(default_factory=list)

    def agregar_rama(self, rama: Rama) -> None:
        self.ramas[rama.id] = rama

    def leer(
        self,
        rama_id: str,
        lector_id: str,
        antes: Optional[str] = None,
        despues: Optional[str] = None,
    ) -> Lectura:
        rama = self.ramas[rama_id]
        lectura = Lectura.registrar(rama, lector_id, antes=antes, despues=despues)
        self.lecturas.append(lectura)
        return lectura


def render(libro: LibroMayor) -> str:
    """
    Muestra el libro mayor como tabla y NO resuelve la bifurcacion.

    Imprime, en orden: la tabla rama/lector/antes/despues/delta; la lectura
    incompatible sin colapsar (soberania vs punto ciego); y, por cada delta, la
    nota Tilde que nombra el residuo (delta registrado, causa NO verificada).
    """
    filas = [("RAMA", "LECTOR", "ANTES", "DESPUES", "DELTA")]
    for lec in libro.lecturas:
        filas.append(
            (
                lec.rama_id,
                lec.lector_id,
                lec.antes,
                lec.despues,
                "si" if lec.delta else "no",
            )
        )
    anchos = [max(len(f[i]) for f in filas) for i in range(5)]
    lineas = []
    for j, f in enumerate(filas):
        lineas.append("  ".join(f[i].ljust(anchos[i]) for i in range(5)).rstrip())
        if j == 0:
            lineas.append("  ".join("-" * anchos[i] for i in range(5)))

    # La bifurcacion no se resuelve: las dos lecturas de la Fila Cero se sostienen.
    lineas.append("")
    lineas.append("La fila del autor sobre su propia rama muestra antes==despues,")
    lineas.append("igual en forma que un lector que no cambio de postura. Dos lecturas")
    lineas.append("incompatibles de esa misma forma, y no se elige entre ellas:")
    lineas.append("  soberania: esta congelada porque el autor manda sobre lo suyo;")
    lineas.append("             nada externo lo mueve.")
    lineas.append("  punto ciego: esta congelada porque el instrumento le prohibe al")
    lineas.append("             autor registrar movimiento sobre su propia obra; es")
    lineas.append("             el unico al que el libro, por estructura, no escucha.")
    lineas.append("  soberania o punto ciego -- las dos lecturas se sostienen.")

    # Tilde: por cada delta, nombrar el residuo. La causa no cruza a codigo.
    deltas = [lec for lec in libro.lecturas if lec.delta]
    lineas.append("")
    if deltas:
        lineas.append("residuo (Tilde) -- contagio no cruza a codigo, solo delta:")
        for lec in deltas:
            lineas.append(
                f"  {lec.lector_id} @ {lec.rama_id}: "
                f"{lec.antes!r} -> {lec.despues!r} | delta registrado, causa NO verificada"
            )
        lineas.append(
            "  'delta' prueba que antes!=despues (exacto). 'contagio' afirmaria que"
        )
        lineas.append(
            "  la RAMA lo causo -- eso NO cruza: podria ser animo, cansancio u otra"
        )
        lineas.append(
            "  cosa entre las dos posturas. Ese hueco es el residuo, y no lo cierra"
        )
        lineas.append("  mas codigo.")
    else:
        lineas.append("residuo (Tilde): ningun delta registrado; nada que cosechar.")
    return "\n".join(lineas)


def _demo() -> LibroMayor:
    """
    Escenario de demo. Fixture sembrado en OBRA_01 (Rama A paranoia / Rama B duda),
    con ids de lector ANONIMIZADOS -- la pieza es un instrumento general, OBRA_01 es
    solo el primer fixture, no su tema. autor_id 'autor_01' escribio ambas ramas.
    """
    libro = LibroMayor()
    libro.agregar_rama(Rama(id="rama_A", autor_id="autor_01", postura="Paranoia"))
    libro.agregar_rama(Rama(id="rama_B", autor_id="autor_01", postura="Duda"))

    # El autor lee sus propias ramas: Fila Cero, congelada por construccion.
    libro.leer("rama_A", "autor_01")
    libro.leer("rama_B", "autor_01")

    # Lectores ajenos declaran su propio antes/despues (texto libre, sobre si).
    libro.leer("rama_A", "lector_gamma", antes="neutral", despues="Paranoia")
    libro.leer("rama_B", "lector_delta", antes="neutral", despues="Duda")
    libro.leer("rama_B", "lector_epsilon", antes="Duda", despues="Duda")
    return libro


if __name__ == "__main__":
    import sys

    # El render usa solo ASCII, pero forzamos UTF-8 por consistencia con la otra
    # pieza del workspace y por si un fixture futuro trae acentos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(render(_demo()))
