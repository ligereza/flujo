"""Normaliza el color observado de los testeos RD 2025. Nada se pierde.

El problema: `testeo_observaciones_fuente` tiene 5.333 observaciones con color,
pero `result_normalized_candidate` es NULL en 4.767 de ellas. El color vive solo
en `result_raw`, en crudo, con 136 variantes para lo que en realidad son unos
pocos resultados:

- mayusculas y espacios: `Negro` / `negro` / `negro ` / ` negro`
- tildes: `Sin reaccion` / `Sin reacción` / `sin reacción`
- el negativo dicho de seis formas distintas
- compuestos con cinco separadores: `Negro y naranjo`, `Negro+Rojo`,
  `Negro con naranjo`, `Naranjo/Rojo`, `negro naranjo`
- orden invertido: `negro y naranjo` y `naranjo y negro` son lo mismo
- tipeos: `zul`, `sim`, `Morada`
- 284 observaciones que son encabezados filtrados: `Resultado test 1..4`

Sigue el patron de `src/flujo/rd/vocab.py`: vocabulario CERRADO, alias
normalizados, y lo que no matchea no se descarta -- queda marcado para revision
humana con su valor crudo intacto.

Regla del dominio que manda sobre cualquier comodidad de graficado: un
resultado colorimetrico es PRESUNTIVO. Esto normaliza el COLOR OBSERVADO, no
identifica sustancias. Un compuesto (`negro y naranjo`) son dos colores y se
conserva como dos: colapsarlo al primero seria inventar una observacion.
"""
from __future__ import annotations

import re
import unicodedata

# Vocabulario cerrado de color observado.
COLORES: tuple[str, ...] = (
    "NEGRO", "AZUL", "CELESTE", "MORADO", "AMARILLO", "NARANJO",
    "ROJO", "VERDE", "ROSADO", "CAFE", "GRIS", "BLANCO",
)

# Resultados que no son un color.
SIN_REACCION = "SIN_REACCION"
NO_INTERPRETABLE = "NO_INTERPRETABLE"

_ALIAS_COLOR: dict[str, str] = {
    "negro": "NEGRO", "negra": "NEGRO",
    "azul": "AZUL", "zul": "AZUL", "azulado": "AZUL",
    "celeste": "CELESTE", "celest": "CELESTE",
    "morado": "MORADO", "morada": "MORADO", "violeta": "MORADO",
    "purpura": "MORADO", "lila": "MORADO",
    "amarillo": "AMARILLO", "amarilla": "AMARILLO",
    "naranjo": "NARANJO", "naranja": "NARANJO", "naranjas": "NARANJO",
    "anaranjado": "NARANJO",
    "rojo": "ROJO", "roja": "ROJO", "rojizo": "ROJO",
    "verde": "VERDE", "verdoso": "VERDE",
    "rosado": "ROSADO", "rosa": "ROSADO", "rosada": "ROSADO",
    "cafe": "CAFE", "marron": "CAFE", "cafe_oscuro": "CAFE",
    "gris": "GRIS", "grisaceo": "GRIS",
    # Tipeos y plurales presentes en la fuente. Completar la tabla de alias no
    # es sobreajustar: es lo que vocab.py llama normalizar el alias.
    "natanjo": "NARANJO", "naranj": "NARANJO", "naranjoo": "NARANJO",
    # Plurales que la fuente usa y el mapa no tenia: medidos en el corpus,
    # `rojos` (13 observaciones) y `naranjos` (8) se perdian como no
    # reconocidos dentro de compuestos reales («negro tonos rojos»).
    "rojos": "ROJO", "rojas": "ROJO", "naranjos": "NARANJO",
    "verdes": "VERDE", "celestes": "CELESTE", "amarillos": "AMARILLO",
    "amarillas": "AMARILLO", "blancos": "BLANCO", "blancas": "BLANCO",
    "grises": "GRIS", "cafes": "CAFE", "rosados": "ROSADO", "rosadas": "ROSADO",
    "negros": "NEGRO", "negras": "NEGRO", "morados": "MORADO",
    "moradas": "MORADO", "caffe": "CAFE", "azules": "AZUL",
    "blanco": "BLANCO", "blanca": "BLANCO",
}

# El negativo, dicho de todas las formas que aparecen en la fuente.
_ALIAS_SIN_REACCION: frozenset[str] = frozenset({
    "negativo", "negativa", "sin_reaccion", "sin_reacciona", "no_reacciona",
    "no_reaccion", "no_reacciono", "ninguna", "ninguno", "nada", "sin",
    "sim", "n_a", "na", "-", "0", "cero", "sin_cambio", "incoloro",
    "no_hay_reaccion", "sin_color", "niguna", "nunguna",
    "nhr", "no_reacciona_nada", "poca_reaccion",
})

# Encabezados que se colaron como dato, y nombres de reactivo en la columna de
# resultado. No son observaciones: son ruido de la planilla, y se marcan como
# tal en vez de contarse como un color.
_RUIDO_PATRONES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^resultado(_test)?(_\d+)?$"),
    re.compile(r"^test(_\d+)?$"),
    re.compile(r"^column(_\d+)?$"),
    re.compile(r"^sustancia$|^formato$|^otro$|^otros$"),
    re.compile(r"^(marquis|mecke|simons?|froehde|mandelin|liebermann|"
               r"zimmermann|morris|robadope|ehrlich|hofmann)$"),
)

# Nombres de sustancia escritos en la columna de COLOR. No es un tipeo: es una
# identificacion presuntiva puesta donde va una observacion, y contradice la
# politica del dominio (`observed_color_only_not_identity_purity_or_dose`).
# Se marca aparte para que la revision humana lo vea, en vez de esconderlo
# entre los "sin mapear".
_SUSTANCIAS_EN_COLOR: frozenset[str] = frozenset({
    "mdma", "mda", "mdea", "anfeta", "anfetamina", "metanfetamina",
    "ketamina", "keta", "cocaina", "fentanilo", "fentanyl", "2cb", "2c_b",
    "lsd", "ghb", "tusi", "tussi", "heroina", "opiaceo", "opiaceos",
})

# Palabras que describen la MUESTRA, no la reaccion. Un `Polvo rosado` en la
# columna de resultado no es un reactivo que viro a rosado: es alguien que
# anoto la pastilla donde va el color del test. Confundirlos es el error mas
# facil de cometer con esta planilla, porque las dos columnas contienen
# nombres de color -- «Cupra morada» y «Morado» se ven igual en una lista.
#
# Medido sobre el corpus: 27 celdas de resultado traen una descripcion de
# muestra, y hoy su color entra a la matriz como si fuera una reaccion.
_PRESENTACION: frozenset[str] = frozenset({
    "polvo", "polvos", "pastilla", "pastillas", "pasti", "cristal",
    "cristales", "pildora", "pildoras", "comprimido", "capsula", "capsulas",
    "roca", "piedra", "papel", "papelillo", "gota", "gotas", "liquido",
    "tira", "troquel", "molde",
})

# Matices que califican el color sin cambiarlo. Se conservan aparte: "rojo
# oscuro" sigue siendo ROJO, pero el matiz es informacion real del observador.
_MATICES: dict[str, str] = {
    "oscuro": "oscuro", "oscura": "oscuro", "claro": "claro", "clara": "claro",
    "palido": "palido", "palida": "palido", "intenso": "intenso",
    "fuerte": "intenso", "leve": "leve", "tenue": "leve",
    "trazas": "trazas", "traza": "trazas", "poco": "leve",
    "oscuto": "oscuro", "levemente": "leve", "puntos": "puntos",
    "punto": "puntos", "linea": "linea", "lineas": "linea",
    # Medidos en el corpus: `tonos` (19), `pintas` (7), `pinta` (3).
    "tonos": "tonos", "tono": "tonos", "pintas": "puntos", "pinta": "puntos",
    "leves": "leve", "poca": "leve", "pocas": "leve", "pastel": "palido",
}

# Un veredicto donde va una observacion. `positivo` (167 celdas) lo escriben
# sobre Froehde, Simon y Marquis -- reactivos que SI dan color -- asi que no es
# la lectura de una tira de si/no: es alguien que anoto su conclusion en vez
# del color que vio. Es el mismo problema que `identidad_en_columna_de_color`
# y se marca igual, sin inventarle un color.
_VEREDICTOS: frozenset[str] = frozenset({
    "positivo", "positiva", "positivos", "si", "no", "afirmativo",
})

# Separadores de un resultado compuesto. El espacio va ultimo: primero se
# intentan los explicitos para no partir "sin reaccion".
_SEPARADORES = ("+", "/", " y ", " con ", " mas ", ",", " & ", "-")

# "a" conecta los extremos de un rango del catalogo: "violeta a negro".
_CONECTORES = frozenset({"y", "con", "mas", "de", "el", "la", "un", "una", "a"})


def _slug(value: str) -> str:
    """Minuscula, sin tildes, espacios y guiones a `_`. Igual que vocab.py."""
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\s\-/]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _partir(raw: str) -> list[str]:
    """Separa un resultado compuesto en sus partes, sin perder ninguna."""
    texto = " " + (raw or "").strip().lower() + " "
    for sep in _SEPARADORES:
        texto = texto.replace(sep, "|")
    partes = [p.strip() for p in texto.split("|")]
    # Sin separador explicito, dos colores pueden venir pegados por espacio
    # ("negro naranjo"). Se parte por palabra y se filtran conectores.
    salida: list[str] = []
    for parte in partes:
        if not parte:
            continue
        palabras = [w for w in re.split(r"\s+", parte) if w and _slug(w) not in _CONECTORES]
        reconocidas = [w for w in palabras if _slug(w) in _ALIAS_COLOR]
        salida.extend(palabras if len(reconocidas) < 2 else palabras)
    return [p for p in salida if p]


def normalizar(raw: str | None,
               etiquetas_de_muestra: frozenset[str] | None = None) -> dict:
    """Devuelve la lectura normalizada de un `result_raw`.

    Siempre devuelve algo: `status` dice cuanta confianza merece, y `raw`
    conserva el original intacto para que una revision humana pueda auditarlo.

    `etiquetas_de_muestra` son los nombres de troquel que el propio corpus usa
    en la columna de formato (`cupra`, `tesla`, `gucci`, `redbull`...). No se
    pueden enumerar aca: cada temporada trae troqueles nuevos, y la lista la
    conoce el dato, no este modulo. Cuando una de esas palabras aparece en la
    columna de RESULTADO, la celda esta describiendo la pastilla y su color no
    es una reaccion: sale con `status=descripcion_de_muestra` y NO entra a la
    matriz.
    """
    original = "" if raw is None else str(raw)
    slug = _slug(original)

    if not slug:
        return {"raw": original, "outcome": NO_INTERPRETABLE, "colores": [],
                "matices": [], "status": "vacio", "revisar": True}

    for patron in _RUIDO_PATRONES:
        if patron.match(slug):
            return {"raw": original, "outcome": NO_INTERPRETABLE, "colores": [],
                    "matices": [], "status": "encabezado_o_reactivo", "revisar": True}

    if slug in _ALIAS_SIN_REACCION:
        return {"raw": original, "outcome": SIN_REACCION, "colores": [],
                "matices": [], "status": "canonico", "revisar": False}

    colores: list[str] = []
    matices: list[str] = []
    sin_reconocer: list[str] = []
    identidades: list[str] = []
    muestra: list[str] = []
    veredictos: list[str] = []
    for parte in _partir(original):
        clave = _slug(parte)
        if not clave or clave in _CONECTORES:
            continue
        if clave in _ALIAS_COLOR:
            color = _ALIAS_COLOR[clave]
            if color not in colores:
                colores.append(color)
        elif clave in _MATICES:
            matiz = _MATICES[clave]
            if matiz not in matices:
                matices.append(matiz)
        elif clave in _ALIAS_SIN_REACCION:
            continue  # "sin reaccion" dentro de un compuesto no aporta color
        elif clave in _SUSTANCIAS_EN_COLOR:
            identidades.append(parte)
        elif clave in _PRESENTACION or clave in (etiquetas_de_muestra or ()):
            muestra.append(parte)
        elif clave in _VEREDICTOS:
            veredictos.append(parte)
        else:
            sin_reconocer.append(parte)

    # La descripcion de la muestra manda sobre todo lo demas: si la celda dice
    # `Cupra morada`, ese morado es de la pastilla y no puede contarse como
    # una reaccion de ningun reactivo.
    if muestra:
        return {"raw": original, "outcome": NO_INTERPRETABLE, "colores": [],
                "matices": matices, "status": "descripcion_de_muestra",
                "sin_reconocer": sin_reconocer, "identidades": identidades,
                "muestra": muestra, "revisar": True}

    if not colores:
        if identidades:
            status = "identidad_en_columna_de_color"
        elif veredictos:
            status = "veredicto_en_columna_de_color"
        else:
            status = "sin_mapear"
        return {"raw": original, "outcome": NO_INTERPRETABLE, "colores": [],
                "matices": matices, "status": status,
                "sin_reconocer": sin_reconocer, "identidades": identidades,
                "veredictos": veredictos, "revisar": True}

    status = ("identidad_en_columna_de_color" if identidades
              else "canonico" if not sin_reconocer else "parcial")
    return {
        "raw": original,
        "outcome": "REACCION",
        "colores": colores,
        # Clave estable: `negro y naranjo` y `naranjo y negro` agrupan igual.
        "clave": "+".join(sorted(colores)),
        "matices": matices,
        "status": status,
        "sin_reconocer": sin_reconocer,
        "identidades": identidades,
        "veredictos": veredictos,
        # Un veredicto JUNTO a un color no borra el color: el color es la
        # observacion y el veredicto sobra. Solo se pide revision.
        "revisar": bool(sin_reconocer or identidades or veredictos),
        "compuesto": len(colores) > 1,
    }


# Hex para pintar cada color observado. NO es el hex de la tabla `reactivos`
# (eso es la reaccion esperada de una familia): esto es como se dibuja el color
# que la persona anoto.
HEX: dict[str, str] = {
    "NEGRO": "#1a1a1a", "AZUL": "#2f5fd0", "CELESTE": "#5fb4e5",
    "MORADO": "#7c3aa8", "AMARILLO": "#e8c33a", "NARANJO": "#e8813a",
    "ROJO": "#c9372c", "VERDE": "#3f9b52", "ROSADO": "#e58fae",
    "CAFE": "#8a5a3c", "GRIS": "#9aa0a6", "BLANCO": "#f2f2ee",
    SIN_REACCION: "#3a3f47", NO_INTERPRETABLE: "#5a5a5a",
}


__all__ = ["normalizar", "COLORES", "SIN_REACCION", "NO_INTERPRETABLE", "HEX"]
