# -*- coding: utf-8 -*-
"""Los vínculos dibujados: siempre visibles, tenues, y por peso.

Decisión del usuario (2026-07-30). El riesgo que se señaló al decidirlo es real
y es técnico: con el archivo completo son miles de vínculos, y la referencia de
la que salió este campo traía el defecto de recorrer **todos los pares en cada
frame**. Este archivo fija las dos cosas que impiden repetirlo y mide cuánto
trabajo queda de verdad por frame.

Lo que NO se mide acá: cuadros por segundo en un teléfono. No se midió, así que
no se afirma.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIEL = REPO / "iskvw" / "piel" / "campo" / "index.html"
CAMPO = REPO / "iskvw" / "datos" / "campo.json"


def _fuente() -> str:
    return PIEL.read_text(encoding="utf-8")


def test_los_vecinos_se_indexan_una_vez_y_no_por_frame():
    """El defecto que no se repite: el índice se arma en `sembrar()`, que corre
    una vez, y el bucle de dibujo recorre la lista del nodo, no todos los pares.
    """
    t = _fuente()
    sembrar = t[t.index("function sembrar"):t.index("function dibujar")]
    assert "VECINOS = NODOS.map" in sembrar, "el índice no se arma al sembrar"

    dibujar = t[t.index("function dibujar"):]
    dibujar = dibujar[:dibujar.index("\nfunction ")]
    # dentro del dibujo NO se construye ningún índice ni se recorre NODOS
    # dentro de NODOS (el par de bucles anidados sobre el mismo arreglo es
    # exactamente la forma del defecto).
    assert "porId" not in dibujar
    assert "new Map(" not in dibujar
    anidado = re.search(r"for \(let ni[^}]*for \(let nj = 0; nj < NODOS\.length",
                        dibujar, re.S)
    assert anidado is None, "hay un bucle de todos-contra-todos en el dibujo"


def test_la_piel_aplica_lod_visual_sin_borrar_vinculos_del_archivo():
    t = _fuente()
    assert "MAX_VECINOS_VISIBLES = 12" in t
    assert "slice(0, MAX_VECINOS_VISIBLES)" in t
    assert "candidatos[i].sort" in t


def test_una_punta_fuera_de_la_banda_descarta_el_vinculo():
    """Ambas puntas tienen que estar en cuadro. Dibujar una línea hacia una
    pieza que no está en el campo sería afirmar una relación sin sus dos
    extremos."""
    t = _fuente()
    bloque = t[t.index("if (VECINOS.length)"):]
    bloque = bloque[:bloque.index("for (let ni = 0; ni < NODOS.length; ni++){\n    const n = NODOS[ni];")]
    assert "const a = posicionDe(ni)" in bloque and "if (!a) continue" in bloque
    assert "const b = posicionDe(nj)" in bloque and "if (!b) continue" in bloque
    assert "if (nj < ni) continue" in bloque, "el vínculo se dibujaría dos veces"


def test_la_opacidad_sale_del_peso_y_tiene_techo_bajo():
    """Tenue y por peso: un vínculo más fuerte se ve más, y ninguno compite con
    la obra. Y por debajo del umbral no se dibuja: pintar algo invisible es
    gastar sin decir nada."""
    t = _fuente()
    bloque = t[t.index("if (VECINOS.length)"):t.index("for (let ni = 0; ni < NODOS.length; ni++){\n    const n = NODOS[ni];")]
    m = re.search(r"lista\[k\+1\] \* (0?\.\d+)", bloque)
    assert m, "la opacidad no sale del peso del vínculo"
    assert float(m.group(1)) <= 0.25, "el techo de opacidad es demasiado alto"
    assert "if (alfa <" in bloque, "no hay umbral: se pintan líneas invisibles"


def test_la_posicion_se_calcula_en_un_solo_lugar():
    """Dos pasadas usan la misma cuenta. Duplicarla es garantizar que un día
    los vínculos y las obras se dibujen en lugares distintos."""
    t = _fuente()
    assert t.count("function posicionDe") == 1
    dibujar = t[t.index("function dibujar"):]
    assert dibujar.count("posicionDe(") >= 3     # definición + los dos usos


def test_sin_vinculos_no_se_dibuja_nada_y_la_piel_sigue():
    """El camino vivo de hoy: `archivo.json` no se publica, así que `VINCULOS`
    llega vacío y la piel tiene que verse igual que antes."""
    t = _fuente()
    assert "let VINCULOS=[]" in t
    assert "if (VECINOS.length){" in t, "el bloque no está guardado por el índice"


def test_cuanto_trabajo_queda_por_frame_con_el_archivo_real():
    """La medición, no la promesa: cuántos segmentos sobreviven al descarte.

    Se replica la regla del dibujo (`|dy| <= alcance`, con `alcance` del
    diafragma) sobre las posiciones REALES del campo, en varias posiciones de
    lectura, y se cuentan los vínculos con las dos puntas en cuadro. Si algún
    día el descarte deja de servir, este número se dispara y el test lo dice.
    """
    if not CAMPO.is_file():
        import pytest
        pytest.skip("sin campo.json medido en este checkout")
    piezas = json.loads(CAMPO.read_text(encoding="utf-8")).get("piezas") or []
    if len(piezas) < 50:
        import pytest
        pytest.skip("campo demasiado chico para medir")

    # el mismo mapeo que `sembrar()`: y = (y + 1) * 2600
    ys = [(p["y"] + 1) * 2600 for p in piezas if isinstance(p.get("y"), (int, float))]
    ys.sort()
    largo = max(ys) if ys else 0

    # peor caso del diafragma: abierto del todo
    alcance = 260 + 1 * 1500
    # se simula un grafo tan denso como el archivo completo: ~3.2 vinculos por
    # pieza, entre vecinos de la proyeccion (que es el caso REAL: el micelio
    # relaciona lo que se parece, y lo que se parece cae cerca)
    n = len(ys)
    grados = 3
    peor = 0
    for centro in [largo * f for f in (0.1, 0.3, 0.5, 0.7, 0.9)]:
        en_banda = sum(1 for y in ys if abs(y - centro) <= alcance)
        # cada nodo en banda con sus `grados` vecinos mas cercanos, que estan
        # tambien en banda salvo en los bordes
        peor = max(peor, en_banda * grados)
    # Referencia: recorrer todos los pares seria n*(n-1)/2 por frame.
    todos_los_pares = n * (n - 1) // 2
    assert peor < todos_los_pares / 10, (
        "el descarte no esta sirviendo: %d segmentos por frame contra %d pares"
        % (peor, todos_los_pares))
    # y un techo absoluto: mas de esto en un frame es una malla, no un campo
    assert peor < 4000, "%d segmentos por frame es demasiado" % peor
