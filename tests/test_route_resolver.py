"""
Tests de src/flujo/route/resolver.py -- ruteo de piezas a carpetas. Gap #10 (no
tenia test). Fija la sutileza de orden (transversal gana aunque se pase --area),
los caminos de error (falta/invalida area, pieza no reconocida) y el match por
substring. Usa un indice sintetico: no depende del indice real en disco.
"""
from __future__ import annotations

from flujo.route.resolver import _match_pieza, resolver_ruta

IDX = {
    "transversales": {
        "marca": {"piezas": ["logo", "paleta"], "buscar_en": ["marca/src"], "trabajar_en": "marca/wip"},
    },
    "areas": {
        "EVENTOS": {"piezas": {
            "flyer": {"buscar_en": ["ev/src"], "trabajar_en": "ev/wip", "entregar_en": "ev/out"},
        }},
        "SUPLEMENTOS": {"piezas": {
            "pendon": {"buscar_en": ["sp/src"], "trabajar_en": "sp/wip", "entregar_en": "sp/out"},
        }},
    },
    "cuna": {"ruta": "cuna/"},
}


def test_match_pieza_por_substring():
    assert _match_pieza({"flyer": 1}, "flyer de la fiesta") == "flyer"
    assert _match_pieza({"flyer": 1}, "solo un pendon") is None
    assert _match_pieza({"flyer": 1}, None) is None


def test_transversal_no_necesita_area():
    r = resolver_ruta(IDX, pieza="logo del evento")
    assert r["ambito"] == "transversal"
    assert r["grupo"] == "marca"


def test_transversal_gana_aunque_se_pase_area():
    """Sutileza de orden: el loop transversal corre ANTES del de area, asi que
    'logo' resuelve transversal aunque se pida --area EVENTOS."""
    r = resolver_ruta(IDX, area="EVENTOS", pieza="logo")
    assert r["ambito"] == "transversal"


def test_falta_area_para_pieza_de_area():
    r = resolver_ruta(IDX, pieza="flyer")
    assert "error" in r
    assert "area" in r["error"].lower()


def test_area_invalida():
    r = resolver_ruta(IDX, area="MARKETING", pieza="flyer")
    assert "error" in r
    assert "invalida" in r["error"].lower()


def test_pieza_no_reconocida_en_area():
    r = resolver_ruta(IDX, area="EVENTOS", pieza="cosa inexistente")
    assert "error" in r
    assert "no reconocida" in r["error"].lower()


def test_resolucion_de_area_ok_con_substring():
    r = resolver_ruta(IDX, area="eventos", pieza="flyer de la fiesta")
    assert r["ambito"] == "area"
    assert r["area"] == "EVENTOS"
    assert r["pieza"] == "flyer"
    assert r["trabajar_en"] == "ev/wip"
    assert r["cuna"] == "cuna/"
