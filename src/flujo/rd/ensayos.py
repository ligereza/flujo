"""Vocabulario cerrado de REACTIVO y de SUSTANCIA DECLARADA. Solo ortografia.

Sigue el patron de `vocab.py` y `colorimetria.py`: alias -> canonico, y lo que
no matchea NO se descarta, queda marcado para revision con su valor crudo.

Lo que este modulo hace y lo que no:

  SI  unir `tusi`, `tussi` y `tu si`; unir `simon`, `simons` y `simon's`.
      Eso es ortografia, y es lo que permite que una lectura se pueda contar
      junto a otra igual en vez de aparecer en tres filas distintas del
      grafico.

  NO  decir que significa un color, ni que sustancia hay, ni si el resultado
      coincide con lo declarado. El veredicto es de la persona a cargo en la
      mesa. Aca un ensayo es: REACTIVO X dio COLOR C. Nada mas.

Todo canonico conserva sus variantes crudas (`variantes()`), para que un total
siempre se pueda abrir y ver de que celdas salio.
"""
from __future__ import annotations

import re
import unicodedata

# Reactivos que RD elabora y vende. La lista es la de su tienda, no una
# eleccion nuestra: https://reduciendodano.cl/tienda/
REACTIVOS: tuple[str, ...] = (
    "MARQUIS", "SIMONS", "FROEHDE", "MECKE", "MANDELIN", "LIEBERMANN",
    "MORRIS", "ROBADOPE", "ZIMMERMANN", "EHRLICH", "HOFMANN", "CBD_THC",
    "TIRA_FENTANILO", "TIRA_XYLAZINA", "TIRA_BENZODIACEPINAS", "TEST_GHB",
)

# Alias -> reactivo canonico. Cada grafia esta medida en el corpus real.
_ALIAS_REACTIVO: dict[str, str] = {
    "marquis": "MARQUIS", "maquis": "MARQUIS", "marqui": "MARQUIS",
    "marquiz": "MARQUIS",
    # RD lo llama «Simon's»; la tabla curada lo abrevio a «Simon» y por eso
    # 418 lecturas quedaban en una fila aparte de las 1.173 de `simon`.
    "simon": "SIMONS", "simons": "SIMONS", "simon_s": "SIMONS",
    "simon_a": "SIMONS", "simmons": "SIMONS", "symon": "SIMONS",
    "froehde": "FROEHDE", "frohede": "FROEHDE", "froehede": "FROEHDE",
    "frohde": "FROEHDE", "froede": "FROEHDE",
    "mecke": "MECKE", "meke": "MECKE",
    "mandelin": "MANDELIN", "mandelina": "MANDELIN",
    "liebermann": "LIEBERMANN", "lieberman": "LIEBERMANN",
    "libermann": "LIEBERMANN", "liberman": "LIEBERMANN",
    # `mr` da azul y morado: el vocabulario exacto de Morris.
    "morris": "MORRIS", "mr": "MORRIS", "mr_a": "MORRIS", "morriss": "MORRIS",
    "robadope": "ROBADOPE", "robandole": "ROBADOPE", "robadop": "ROBADOPE",
    "robodope": "ROBADOPE",
    "zimmermann": "ZIMMERMANN", "zimmerman": "ZIMMERMANN",
    "zimermann": "ZIMMERMANN", "zimerman": "ZIMMERMANN",
    "zimmermam": "ZIMMERMANN",
    "ehrlich": "EHRLICH", "erlich": "EHRLICH",
    "hofmann": "HOFMANN", "hoffman": "HOFMANN", "hofman": "HOFMANN",
    "cbd_thc": "CBD_THC", "cbdthc": "CBD_THC", "thc_cbd": "CBD_THC",
    # El voluntario nombra el kit por lo que testea, no por el reactivo: en la
    # columna de reactivo escribe `Cannabis` y en la de resultado `Azul`. Es el
    # kit CBD:THC. La proyeccion de la base ya lo traducia; este vocabulario no,
    # y esas filas se descartaban como si no se hubiera analizado nada.
    "cannabis": "CBD_THC",
    "fentanyl_strip": "TIRA_FENTANILO", "tira_de_fentanilo": "TIRA_FENTANILO",
    "tira_fentanilo": "TIRA_FENTANILO", "fentanilo": "TIRA_FENTANILO",
    "xylazina": "TIRA_XYLAZINA", "tira_xylazina": "TIRA_XYLAZINA",
    "ghb": "TEST_GHB", "test_ghb": "TEST_GHB",
}

# Sustancia DECLARADA por quien trae la muestra. Es lo que dice, no lo que es.
SUSTANCIAS: tuple[str, ...] = (
    "MDMA", "MDA", "KETAMINA", "COCAINA", "2C_B", "TUSI", "ANFETAMINA",
    "METANFETAMINA", "LSD", "HONGOS", "DMT", "GHB", "MEFEDRONA", "CANNABIS",
    "BENZODIACEPINA", "POPPER", "CAFEINA", "NO_DECLARA", "NO_SABE",
)

_ALIAS_SUSTANCIA: dict[str, str] = {
    "mdma": "MDMA", "extasis": "MDMA", "exta": "MDMA", "molly": "MDMA",
    "cristal_mdma": "MDMA", "mdma_cristal": "MDMA",
    "mda": "MDA", "sass": "MDA",
    "ketamina": "KETAMINA", "keta": "KETAMINA", "ketamine": "KETAMINA",
    "k": "KETAMINA", "special_k": "KETAMINA",
    "cocaina": "COCAINA", "coca": "COCAINA", "coke": "COCAINA",
    "cocaine": "COCAINA", "perico": "COCAINA",
    "2c_b": "2C_B", "2cb": "2C_B", "2_c_b": "2C_B", "dosc": "2C_B",
    # RD lo dice en su propia tienda: el nombre viene foneticamente de «2C-B»,
    # pero lo que circula en Chile con ese nombre rara vez contiene 2C-B. Son
    # DOS declaraciones distintas y no se colapsan entre si.
    "tusi": "TUSI", "tussi": "TUSI", "tu_si": "TUSI", "tuci": "TUSI",
    "tusibi": "TUSI", "tusy": "TUSI", "tus_si": "TUSI", "tussy": "TUSI",
    "anfetamina": "ANFETAMINA", "anfeta": "ANFETAMINA", "speed": "ANFETAMINA",
    "metanfetamina": "METANFETAMINA", "meta": "METANFETAMINA",
    "lsd": "LSD", "acido": "LSD", "carton": "LSD",
    "hongos": "HONGOS", "psilocibina": "HONGOS", "hongo": "HONGOS",
    "dmt": "DMT", "changa": "DMT",
    "ghb": "GHB", "gbl": "GHB", "ghb_gbl": "GHB",
    "mefedrona": "MEFEDRONA", "mefe": "MEFEDRONA", "4mmc": "MEFEDRONA",
    "cannabis": "CANNABIS", "marihuana": "CANNABIS", "thc": "CANNABIS",
    "benzodiacepina": "BENZODIACEPINA", "benzo": "BENZODIACEPINA",
    "clonazepam": "BENZODIACEPINA", "alprazolam": "BENZODIACEPINA",
    "popper": "POPPER", "cafeina": "CAFEINA",
    "no_sabe": "NO_SABE", "no_se": "NO_SABE", "desconocido": "NO_SABE",
    "unknown": "NO_SABE", "sin_declarar": "NO_DECLARA",
    # `pasti`, `pastilla`: la persona declaro un FORMATO, no una sustancia.
    # Mandarlas a MDMA seria el veredicto que este modulo no da -- una
    # pastilla puede ser cualquier cosa, y eso es justamente el punto.
    "pasti": "NO_DECLARA", "pastilla": "NO_DECLARA",
    "pastillas": "NO_DECLARA", "polvo": "NO_DECLARA", "cristal": "NO_DECLARA",
}


def _slug(value: object) -> str:
    texto = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", texto)).strip("_")


def _normalizar(crudo: object, alias: dict[str, str], canonicos: tuple[str, ...]) -> dict:
    """Canonico + estado. Lo que no matchea conserva su crudo y pide revision."""
    original = "" if crudo is None else str(crudo).strip()
    clave = _slug(original)
    if not clave:
        return {"raw": original, "canonico": None, "status": "vacio", "revisar": True}
    if clave in alias:
        return {"raw": original, "canonico": alias[clave],
                "status": "canonico", "revisar": False}
    arriba = clave.upper()
    if arriba in canonicos:
        return {"raw": original, "canonico": arriba,
                "status": "canonico", "revisar": False}
    return {"raw": original, "canonico": None, "status": "sin_mapear", "revisar": True}


def normalizar_reactivo(crudo: object) -> dict:
    """`Simon's`, `simons`, `SIMON` -> SIMONS. Sin decir que detecta."""
    return _normalizar(crudo, _ALIAS_REACTIVO, REACTIVOS)


def normalizar_sustancia(crudo: object) -> dict:
    """`Tusi`, `tussi`, `tu si` -> TUSI. Es lo DECLARADO, no lo identificado."""
    return _normalizar(crudo, _ALIAS_SUSTANCIA, SUSTANCIAS)


def variantes(filas: object, campo: str, normalizador) -> dict[str, dict[str, int]]:
    """Por cada canonico, de que grafias crudas salio y cuantas veces.

    Es lo que hace auditable un total: `TUSI 33` se abre y muestra
    `Tusi 12 · tusi 8 · tussi 6 · Tussi 5 · tu si 2`. Sin esto, una
    normalizacion es una caja negra y el numero deja de ser fidedigno.
    """
    salida: dict[str, dict[str, int]] = {}
    for fila in filas or ():
        crudo = fila.get(campo) if hasattr(fila, "get") else fila[campo]
        lectura = normalizador(crudo)
        clave = lectura["canonico"] or f"(sin mapear) {lectura['raw']}"
        bolsa = salida.setdefault(clave, {})
        bolsa[lectura["raw"]] = bolsa.get(lectura["raw"], 0) + 1
    return salida
