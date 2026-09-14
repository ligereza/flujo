"""
Paridad -- auditar el medidor contra el residuo que dice medir (FLAT CURRENCY).

Semilla: (+)3 (12-jul-2026, puente/SEMILLAS.md) -- "tilde_meter mide tokens =
dialecto Omega degradado. La Tilde NO es ahorro de tokens, es residuo
intraducible." desktop/tilde_meter.py reduce lo que se pierde a un escalar
contable; eso es medir la Tilde en su dialecto degradado.

Esta pieza NO reemplaza el medidor (eso ya lo hizo projects/cultura/tilde_residuo.py,
que construyo la alternativa honesta). Esta pieza PONE AL MEDIDOR EN EL BANCO:
corre el instrumento acusado (tilde_meter.measure) y el honesto
(tilde_residuo.cosechar) sobre el MISMO texto real y no curado -- los asuntos de
los commits de este repo (git log --format=%s) -- y cosecha donde sus veredictos
sobre "cuanto se degrado" se INVIERTEN.

Precursor: colisiona dos instrumentos que ya existen, alimentandolos el mismo
plegado (tilde_residuo.plegar es el "compressed" que tilde_meter.measure espera).
No se agrega contenido: ni plegado nuevo, ni tabla de costo nueva, ni texto
inventado. El umbral que baja: nadie habia tenido que mirar las dos salidas lado
a lado.

Hallazgo empirico que da forma a la pieza (verificado contra el codigo real, no
adivinado): cuando el "compressed" es el plegado completo, tilde_meter.measure
devuelve survival = 0.0 para TODO texto con marcas -- el plegado mata todas las
marcas. El numero de cabecera del medidor (survival) no puede rankear nada: todo
empata en 0.0. Ese es el PRIMER aplanamiento (la tasa de cambio plana del titulo).
Para rankear, el medidor tiene que caer a su UNICO escalar que varia: el CONTEO
de marcas perdidas (marks_in - marks_out). Ese conteo es el dialecto degradado que
(+)3 acusa: paga 1 unidad por marca sin mirar su denominacion. Una 'n con
virgulilla' (ano/ano, inversion de sentido) y una 'a con acento' (mas/mas, perdida
leve) valen exactamente 1 en su libro contable. El SEGUNDO aplanamiento -- la
inversion que esta pieza cosecha -- es que ese ranking-por-conteo se INVIERTE
contra el ranking-por-costo del instrumento honesto.

CAVEAT DE REFLEXIVIDAD (declarado arriba, no descubierto despues): el "costo" con
que el lado honesto rankea sale de _COSTO_POR_CHAR, la tabla curada a mano de
tilde_residuo.py -- MISMO linaje que esta pieza. Esta pieza prueba un script
contra su hermano, no contra una nocion de costo independiente del autor. Que un
residuo sea "filoso" (inversion de sentido, la clase ano/ano) se deriva LEYENDO el
string de costo que ya existe en esa tabla (contiene una flecha '->' de una palabra
que se vuelve otra), no agregando juicio nuevo. El regularizador humano (ver
TILDE_PARIDAD.md) existe justo para corregir este sesgo desde afuera.

Esta pieza NO imprime un unico puntaje de auditoria: eso seria repetir el pecado
que audita. Imprime el detalle por caso, los pares invertidos, y conteos como
marco secundario -- nunca colapsados a un numero.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# tilde_residuo vive en este mismo directorio (projects/cultura/).
_CULTURA_DIR = Path(__file__).resolve().parent
# tilde_meter vive en tools/ (movido de desktop/ 2026-07-25, poda de stack
# muerto), que NO es un paquete: se agrega su carpeta al path.
_DESKTOP_DIR = _CULTURA_DIR.resolve().parents[1] / "tools"

for _d in (_CULTURA_DIR, _DESKTOP_DIR):
    _s = str(_d)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# Instrumento honesto (la alternativa de (+)3) -- se IMPORTA, no se reimplementa.
from tilde_residuo import _COSTO_POR_CHAR, cosechar, plegar  # noqa: E402
# Instrumento acusado (el dialecto degradado) -- se IMPORTA, no se reimplementa.
from tilde_meter import measure  # noqa: E402


# Se necesitan al menos dos textos marcados para siquiera formar un par y comparar
# rankings. Menos que eso: no hay senal, y la pieza lo dice en vez de inventar
# (mismo espiritu que el veredicto "ruido" de tilde_residuo / restriccion de Davidson).
_MIN_MARCADOS = 2


def _es_filoso(costo: str) -> bool:
    """
    Deriva la clase 'filoso' LEYENDO la tabla curada existente, sin agregar juicio.
    Las entradas de inversion de sentido (par minimo real: ano/ano, papa/papa,
    el/el, si/si, hablo/hablo, aun/aun) describen una palabra que se vuelve OTRA:
    su string de costo lleva la flecha '->' MAS una glosa entre parentesis (el
    sentido de cada lado). La perdida fonetica de la dieresis (pinguino/pinguino,
    la u deja de sonar) lleva '->' pero NO glosa entre parentesis: es la MISMA
    palabra, no una inversion, y por eso NO es filosa. Las aperturas pragmaticas
    no llevan ninguna de las dos. Reflexivo a proposito: el criterio es de la
    misma tabla; ver caveat del modulo.
    """
    return "->" in costo and "(" in costo


@dataclass
class Caso:
    """Un texto leido por los dos instrumentos, lado a lado."""

    texto: str
    marcas_perdidas: int          # dialecto del medidor: conteo (marks_in - marks_out)
    survival: Optional[float]     # numero de cabecera del medidor (degenera a 0.0)
    veredicto_honesto: str        # 'tilde' / 'traduccion_total' / 'ruido' (cosechar)
    filosos: List[str] = field(default_factory=list)   # residuos de inversion de sentido
    curados: List[str] = field(default_factory=list)   # residuos con costo curado
    costos: List[str] = field(default_factory=list)     # nombre+costo de cada residuo

    @property
    def tiene_filoso(self) -> bool:
        return bool(self.filosos)


def analizar_texto(texto: str) -> Optional[Caso]:
    """
    Corre los dos instrumentos sobre el mismo texto con el mismo plegado.
    Devuelve None si el texto no tiene marcas (nada que auditar en el).
    """
    plegado = plegar(texto)
    med = measure(texto, plegado)          # instrumento acusado
    if med["marks_in"] == 0:
        return None                        # sin marcas: no entra al banco
    marcas_perdidas = med["marks_in"] - med["marks_out"]

    cos = cosechar(texto)                  # instrumento honesto
    filosos: List[str] = []
    curados: List[str] = []
    costos: List[str] = []
    for r in cos.residuos:
        costo = _COSTO_POR_CHAR.get(r.original)
        if costo is None:
            continue                       # residuo sin costo curado: no se juzga
        curados.append(r.original)
        costos.append(f"{r.original!r} ({r.marca}): {costo}")
        if _es_filoso(costo):
            filosos.append(r.original)

    return Caso(
        texto=texto,
        marcas_perdidas=marcas_perdidas,
        survival=med["survival"],
        veredicto_honesto=cos.veredicto,
        filosos=filosos,
        curados=curados,
        costos=costos,
    )


def auditar(textos: List[str]) -> Tuple[List[Caso], str, str]:
    """
    Audita un corpus. Devuelve (casos_marcados, veredicto, motivo).

    veredicto:
      - "auditable": hay >= _MIN_MARCADOS textos con marcas -> se puede comparar.
      - "ruido": muy pocos textos marcados -> sin senal, no se inventa un resultado.
    """
    casos = [c for c in (analizar_texto(t) for t in textos) if c is not None]
    if len(casos) < _MIN_MARCADOS:
        return (
            casos,
            "ruido",
            f"insufficient signal: solo {len(casos)} texto(s) con marcas en el "
            f"corpus (se necesitan >= {_MIN_MARCADOS} para comparar rankings)",
        )
    return casos, "auditable", ""


def detectar_inversiones(casos: List[Caso]) -> List[Tuple[Caso, Caso]]:
    """
    Cosecha la Tilde de esta pieza: los pares donde los dos rankings se invierten.

    Orden determinista: se ordenan los casos por (marcas_perdidas, texto). Un par
    (X, Y) es una inversion cuando el medidor dice que X se degrado MENOS que Y
    (menos marcas perdidas) pero el instrumento honesto dice que X cuesta MAS que Y
    (X carga un residuo de inversion de sentido, Y no). Ese desacuerdo es el
    residuo: lo que no cruza del dialecto del conteo al dialecto del costo.
    """
    ordenados = sorted(casos, key=lambda c: (c.marcas_perdidas, c.texto))
    inversiones: List[Tuple[Caso, Caso]] = []
    for i, x in enumerate(ordenados):
        for y in ordenados[i + 1:]:
            # y viene despues, asi que marcas_perdidas[y] >= marcas_perdidas[x].
            if y.marcas_perdidas > x.marcas_perdidas and x.tiene_filoso and not y.tiene_filoso:
                inversiones.append((x, y))
    return inversiones


def _clip(texto: str, n: int = 48) -> str:
    texto = texto.replace("\n", " ")
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def render(casos: List[Caso], veredicto: str, motivo: str,
           max_inversiones: int = 12) -> str:
    """
    Muestra la auditoria en texto. Nunca colapsa a un unico puntaje: detalle por
    caso (primario), pares invertidos (primario), conteos (marco secundario).
    """
    lineas: List[str] = ["== PARIDAD: el medidor en el banco (seed (+)3) =="]

    if veredicto == "ruido":
        lineas.append(f"[ruido] {motivo}")
        return "\n".join(lineas)

    survivals = {c.survival for c in casos}
    if survivals == {0.0}:
        lineas.append(
            "primer aplanamiento: survival del medidor = 0.0 en TODOS los casos; "
            "su numero de cabecera no rankea nada (todo empata)."
        )
    else:
        lineas.append(f"survival observados: {sorted(s for s in survivals if s is not None)}")

    lineas.append("")
    lineas.append("por caso (medidor | honesto):")
    for c in sorted(casos, key=lambda c: (-c.marcas_perdidas, c.texto)):
        marca = "FILOSO" if c.tiene_filoso else ("curado" if c.curados else "sin-costo")
        detalle = "; ".join(f"{ch!r}" for ch in c.filosos) if c.filosos else "-"
        lineas.append(
            f"  medidor: {c.marcas_perdidas} marca(s) perdida(s), survival={c.survival}"
            f"  |  honesto: {marca} [{detalle}]  |  {_clip(c.texto)!r}"
        )

    inversiones = detectar_inversiones(casos)
    lineas.append("")
    lineas.append("INVERSIONES (medidor dice 'X se perdio menos' pero honesto dice 'X cuesta mas'):")
    if not inversiones:
        lineas.append(
            "  ninguna: en este corpus, mas marcas perdidas siempre acompano el "
            "costo mas filoso -- conteo y costo coinciden (ver Omega11)."
        )
    else:
        for x, y in inversiones[:max_inversiones]:
            lineas.append(
                f"  INVERSION: X={_clip(x.texto, 32)!r} (perdio {x.marcas_perdidas}, filoso "
                f"{[repr(f) for f in x.filosos]}) < Y={_clip(y.texto, 32)!r} "
                f"(perdio {y.marcas_perdidas}, sin filoso)"
            )
        if len(inversiones) > max_inversiones:
            lineas.append(f"  ... y {len(inversiones) - max_inversiones} par(es) mas")

    # Marco secundario, nunca el resultado: conteos, no un puntaje.
    lineas.append("")
    lineas.append(
        f"(marco: {len(casos)} texto(s) marcado(s); "
        f"{sum(1 for c in casos if c.tiene_filoso)} con residuo filoso; "
        f"{len(inversiones)} par(es) invertido(s))"
    )
    return "\n".join(lineas)


def corpus_desde_git(n: int = 200) -> List[str]:
    """
    Asuntos de commit (SOLO %s: nunca el autor) del repo, como corpus real y no
    curado. Lanza si git no esta disponible o no es un repo: la pieza no inventa
    un corpus.
    """
    salida = subprocess.run(
        ["git", "log", f"-n{n}", "--format=%s"],
        cwd=str(_CULTURA_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [ln for ln in salida.stdout.splitlines() if ln.strip()]


def corpus_desde_archivo(path: str) -> List[str]:
    """Corpus portable: un asunto por linea. Para tests y para correr sin git."""
    contenido = Path(path).read_text(encoding="utf-8")
    return [ln for ln in contenido.splitlines() if ln.strip()]


if __name__ == "__main__":
    import argparse

    # El instrumento imprime diacriticos; forzar UTF-8 en stdout para que la
    # consola Windows (cp1252) no reviente al mostrar el residuo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Audita tilde_meter (conteo) contra tilde_residuo (costo) sobre texto real."
    )
    ap.add_argument("--file", help="corpus portable: un asunto de commit por linea")
    ap.add_argument("-n", type=int, default=200, help="cuantos commits leer de git log")
    args = ap.parse_args()

    if args.file:
        textos = corpus_desde_archivo(args.file)
    else:
        try:
            textos = corpus_desde_git(args.n)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"[ruido] no hay git log disponible: {e}")
            sys.exit(1)

    casos, veredicto, motivo = auditar(textos)
    print(render(casos, veredicto, motivo))
