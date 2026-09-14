"""
MARCA SIN PRECIO -- el juicio curado y su proxy mecanico, lado a lado, sin fusion.

Semilla: (+)5 (12-jul-2026, puente/SEMILLAS.md) -- "el costo de significado del
residuo NO cruza a codigo: se cura a mano (tabla curada); lo intraducible se corrio
de la marca al VALOR de la marca." (+)5 no es una idea: es lo que cayo al construir
projects/cultura/tilde_residuo.py. Aquella pieza nombro QUE se perdio con precision
Unicode, pero el COSTO -- cuanto duele 'ano' (year) -> 'ano' (anus) -- quedo en
_COSTO_POR_CHAR, una tabla que el programa importa pero no puede generar. El residuo
subio un piso: de la marca al valor de la marca.

Que hace esta pieza:
- Importa (NO re-escribe) la tabla curada _COSTO_POR_CHAR desde tilde_residuo.
- Calcula un proxy MECANICO por entrada, elegido ORTOGONAL al criterio de curaduria:
  la distancia de codepoint entre el caracter y su forma plegada (plegar()). Es una
  propiedad formal de Unicode; no sabe -- no puede saber -- si el plegado produce un
  par minimo real. Por eso su ranking no es el ranking del dolor: es un control.
- Renderiza la MISMA tabla bajo dos lentes de vocabulario intercambiado
  (--lente linguistico | --lente marca). Los VALORES subyacentes son identicos byte a
  byte; solo cambian los encabezados. La bifurcacion (Psicosis) vive ahi: los mismos
  datos leidos como documentacion-de-perdida o como ficha-de-activo, y el codigo no
  decide cual lectura es la correcta.
- Se NIEGA, como acto de codigo, a fusionar juicio curado + proxy en un solo numero:
  tasar_por_ley() levanta CostoNoTraducible. No es una funcion sin terminar: es un
  limite declarado. Ese es (+)5 hecho ejecutable.

Estatuto de terminos (regla de escritura #2 del MOTOR):
- "proxy mecanico": PROCEDIMIENTO formal (distancia de codepoint via plegar). No mide
  significado; es ortogonal al criterio con que un humano eligio cada entrada.
- "lente": PROCEDIMIENTO de reencuadre de vocabulario. NUNCA agrega contenido: los dos
  lentes emiten los mismos valores; el self-check lo verifica.
- "valor curado": la cadena de juicio importada de _COSTO_POR_CHAR, escrita a mano. El
  codigo la muestra; no la computa ni la puede recuperar del proxy.

Limite duro: el lente "marca" es SOLO vocabulario (activo / valor / tasacion). NUNCA es
un numero con signo monetario, NUNCA se conecta a ningun flujo de cotizacion. El proxy
se rotula "distancia de codepoint" en AMBOS lentes para que jamas se lea como dinero.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NoReturn

# tilde_residuo vive en el mismo directorio (projects/cultura/). Al correr el
# script, su carpeta entra sola a sys.path[0]; en pytest se inserta CULTURA_DIR.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tilde_residuo import _COSTO_POR_CHAR, plegar  # noqa: E402


class CostoNoTraducible(Exception):
    """
    Se levanta cuando se pide fusionar el valor curado (juicio a mano) y el proxy
    mecanico en un solo puntaje. Ese cruce es exactamente lo que (+)5 dice que NO
    cruza a codigo. La excepcion no es un error del programa: es el operador Tilde
    enactuado como limite. La puerta esta cerrada a proposito.
    """


# Sentinela explicito: el resultado de intentar tasar el costo por regla mecanica.
# No hay numero. Lo intraducible se queda sin cruzar.
NO_CRUZA = "NO_CRUZA"


@dataclass(frozen=True)
class Entrada:
    """
    Una fila de la tabla, con sus dos columnas irreconciliables al lado.

    Los dos lentes leen esta MISMA Entrada; solo cambian los encabezados. Por eso
    los valores son identicos entre lentes por construccion.
    """

    marca: str          # el caracter con marca ('n con virgulilla', 'a con acento', apertura)
    base: str           # su forma plegada (plegar()); '' si el plegado la borra
    costo_curado: str   # el juicio a mano, importado de _COSTO_POR_CHAR; NUNCA computado
    proxy: int          # proxy mecanico ORTOGONAL: distancia de codepoint (formal)


# Vocabulario por lente. Solo encabezados: ningun lente toca los valores.
# El rotulo del proxy es identico en ambos ("distancia de codepoint") para que el
# lente "marca" no pueda leerse jamas como una cifra de dinero.
_PROXY_ROTULO = "distancia de codepoint (formal, no dinero)"

LENTES: Dict[str, Dict[str, str]] = {
    "linguistico": {
        "titulo": "residuo intraducible y su costo -- lente linguistico",
        "col_marca": "residuo",
        "col_base": "fondo plegado",
        "col_costo": "costo de significado (curado a mano)",
        "col_proxy": f"proxy mecanico ({_PROXY_ROTULO})",
    },
    "marca": {
        "titulo": "el valor de la marca y su tasacion -- lente marca",
        "col_marca": "activo",
        "col_base": "marca base (plegada)",
        "col_costo": "valor curado (a mano)",
        "col_proxy": f"tasacion mecanica ({_PROXY_ROTULO})",
    },
}


def proxy_mecanico(marca: str) -> int:
    """
    Proxy MECANICO y determinista: distancia de codepoint entre el caracter y su
    forma plegada. Es ortogonal al criterio de curaduria de _COSTO_POR_CHAR, que
    pregunta algo semantico (perder esta marca, produce un par minimo real donde el
    sentido cambia o se invierte?). Este proxy no sabe nada de eso: solo resta dos
    puntos de codigo Unicode. Si el plegado borra el caracter (aperturas), el destino
    se toma en la posicion nula (0). Puramente formal, reproducible, ciego al dolor.
    """
    marca = unicodedata.normalize("NFC", marca)
    origen = ord(marca[0])
    base = plegar(marca)
    destino = ord(base[0]) if base else 0
    return abs(origen - destino)


def tabla() -> List[Entrada]:
    """
    Construye la tabla una sola vez, independiente del lente. Toma el juicio curado
    tal cual (importado, no re-escrito) y le agrega al lado el proxy mecanico. Nunca
    los combina: quedan como dos columnas que el resto de la pieza se niega a fundir.
    """
    filas: List[Entrada] = []
    for ch, costo in _COSTO_POR_CHAR.items():
        filas.append(
            Entrada(
                marca=ch,
                base=plegar(ch),
                costo_curado=costo,
                proxy=proxy_mecanico(ch),
            )
        )
    return filas


def _fila_valores(e: Entrada) -> str:
    """
    La linea de datos de una fila. IDENTICA entre lentes por construccion: no
    menciona ningun encabezado, solo los valores. El self-check y el test comparan
    justo estas lineas para probar que el reencuadre no agrega contenido.
    """
    origen = e.base if e.base else "(borrado)"
    return f"  {e.marca!r} -> {origen!r} | {e.costo_curado} | {e.proxy}"


def render(entradas: List[Entrada], lente: str = "linguistico") -> str:
    """
    Renderiza la tabla bajo un lente. Solo el titulo, la linea de columnas y la nota
    cambian con el lente; las lineas de datos son las mismas en ambos.
    """
    if lente not in LENTES:
        raise ValueError(f"lente desconocido: {lente!r}; use {sorted(LENTES)}")
    voc = LENTES[lente]
    lineas = [
        f"=== {voc['titulo']} ===",
        (
            f"columnas: {voc['col_marca']} | {voc['col_base']} | "
            f"{voc['col_costo']} | {voc['col_proxy']}"
        ),
    ]
    for e in entradas:
        lineas.append(_fila_valores(e))
    lineas.append(
        f"nota: '{voc['col_costo']}' se cura a mano y NO se computa; "
        f"'{voc['col_proxy']}' es una distancia formal. Esta pieza NO los fusiona "
        "(ver tasar_por_ley); lo intraducible no cruza a codigo (+5)."
    )
    return "\n".join(lineas)


def filas_de_datos(render_salida: str) -> List[str]:
    """Extrae las lineas de datos (las que empiezan con dos espacios) de un render."""
    return [ln for ln in render_salida.splitlines() if ln.startswith("  ")]


def tasar_por_ley(entrada: Entrada) -> NoReturn:
    """
    Intenta tasar el costo del residuo por una regla mecanica -- es decir, fusionar
    el valor curado (juicio a mano) con el proxy mecanico en un solo puntaje. Se
    NIEGA: levanta CostoNoTraducible. Ese es el nucleo de (+)5 hecho codigo: el costo
    de significado no cruza a la maquina; el proxy es formal y ciego al dolor, y
    mezclarlos fabricaria un numero que no significa nada. No hay fallback que valga
    -- por eso tampoco devuelve NO_CRUZA en silencio: lo dice fuerte.
    """
    raise CostoNoTraducible(
        f"el costo curado de {entrada.marca!r} ('{entrada.costo_curado}') no se funde "
        f"con su proxy mecanico ({entrada.proxy}): el valor de significado no cruza a "
        "codigo (+5). Se cura a mano o no existe; NO_CRUZA."
    )


def _self_check() -> None:
    """
    Verificacion interna barata: los dos lentes deben emitir lineas de datos
    identicas (solo difieren encabezados). Si divergen, la pieza estaria agregando
    contenido al reencuadrar -- violacion del limite del Precursor.
    """
    filas = tabla()
    ling = filas_de_datos(render(filas, "linguistico"))
    marca = filas_de_datos(render(filas, "marca"))
    if ling != marca:
        raise AssertionError(
            "los lentes divergen en los datos: el reencuadre agrego contenido"
        )


def main(argv: List[str]) -> int:
    lente = "linguistico"
    if "--lente" in argv:
        i = argv.index("--lente")
        if i + 1 < len(argv):
            lente = argv[i + 1]
    if lente not in LENTES:
        print(f"lente desconocido: {lente!r}; use {sorted(LENTES)}")
        return 2

    _self_check()  # los lentes no agregan contenido
    filas = tabla()
    print(render(filas, lente))

    # Enactuar el limite en voz alta: pedir la fusion y mostrar la negativa. Esto es
    # descriptivo -- no computa nada; solo hace visible que la puerta esta cerrada.
    print("\n-- intento de tasacion por regla (tasar_por_ley) --")
    try:
        tasar_por_ley(filas[0])
    except CostoNoTraducible as exc:
        print(f"  CostoNoTraducible: {exc}")
    return 0


if __name__ == "__main__":
    # La consola Windows (cp1252) no encodea 'n con virgulilla' ni las aperturas;
    # forzar UTF-8 para no reventar al mostrar la tabla.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
