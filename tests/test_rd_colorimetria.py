"""El color del TEST no es el color de la MUESTRA.

Las dos columnas de la planilla contienen nombres de color y se confunden de
vista: «Cupra morada» (la pastilla) al lado de «Morado» (lo que viro el
reactivo). Medido sobre el corpus, 48 celdas de resultado traen en realidad
una descripcion de la muestra, y su color entraba a la matriz de colorimetria
como si fuera una reaccion.

El vocabulario de troqueles no se puede enumerar en el codigo -- cada
temporada trae sellos nuevos -- asi que se lee del propio corpus, de la
columna de formato.
"""
from __future__ import annotations

import pytest

from flujo.rd.colorimetria import COLORES, normalizar

# Como las arma el panel: tokens de `format_raw` que no son un color.
TROQUELES = frozenset({"cupra", "tesla", "gucci", "redbull", "perignon", "batman"})


def _leer(raw: str):
    return normalizar(raw, TROQUELES)


@pytest.mark.parametrize("raw", [
    "Cupra morada", "cupra morada", "Redbull rosada", "Gucci naranja pastel",
    "Batman azul",
])
def test_un_troquel_con_color_es_la_muestra_no_la_reaccion(raw):
    lectura = _leer(raw)
    assert lectura["status"] == "descripcion_de_muestra"
    assert lectura["colores"] == [], "ese color es de la pastilla, no del test"
    assert lectura["revisar"] is True


@pytest.mark.parametrize("raw", [
    "Polvo rosado", "Pastilla rosada", "Cristal blanco", "polvo blanco",
])
def test_una_palabra_de_presentacion_tambien_describe_la_muestra(raw):
    """`polvo`, `pastilla`, `cristal` no dependen del corpus: son cerradas."""
    lectura = normalizar(raw)
    assert lectura["status"] == "descripcion_de_muestra"
    assert lectura["colores"] == []


@pytest.mark.parametrize("raw,esperado", [
    ("Negro", ["NEGRO"]),
    ("blanco", ["BLANCO"]),
    ("Negro y naranjo", ["NEGRO", "NARANJO"]),
    ("negro tonos rojos", ["NEGRO", "ROJO"]),
    ("amarillo con puntos naranjos", ["AMARILLO", "NARANJO"]),
    ("Sin reaccion", []),
])
def test_una_lectura_legitima_no_se_marca_como_muestra(raw, esperado):
    lectura = _leer(raw)
    assert lectura["status"] != "descripcion_de_muestra"
    assert lectura["colores"] == esperado


def test_un_color_mal_escrito_no_se_confunde_con_un_troquel():
    """`amarillos` y `azil` estan a una letra del vocabulario canonico.

    El panel los excluye de la lista de sellos por distancia; si entraran,
    una lectura real se marcaria como descripcion de la muestra.
    """
    from flujo.rd.panel import _distancia
    for token in ("amarillos", "blancos", "azil", "negras"):
        assert any(_distancia(token, c.lower()) <= 2 for c in COLORES), token
    # y un troquel de verdad no se parece a ningun color
    for token in ("cupra", "batman", "redbull"):
        assert not any(_distancia(token, c.lower()) <= 2 for c in COLORES), token


def test_un_veredicto_no_es_un_color():
    """`positivo` lo escriben sobre Froehde, Simon y Marquis -- reactivos que
    SI dan color. Es una conclusion puesta donde va la observacion."""
    lectura = _leer("positivo")
    assert lectura["status"] == "veredicto_en_columna_de_color"
    assert lectura["colores"] == []
    assert lectura["revisar"] is True


def test_un_veredicto_junto_a_un_color_no_borra_el_color():
    lectura = _leer("positivo azul")
    assert lectura["colores"] == ["AZUL"]
    assert lectura["revisar"] is True


def test_la_muestra_manda_sobre_la_identidad_y_sobre_el_color():
    """Una celda puede traer varias cosas mal puestas a la vez."""
    lectura = _leer("Cupra morada mdma")
    assert lectura["status"] == "descripcion_de_muestra"
    assert lectura["colores"] == []
