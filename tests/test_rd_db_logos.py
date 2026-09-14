# -*- coding: utf-8 -*-
"""El panel de base de datos no puede contar un logo que después no muestra.

Medido en vivo el 2026-07-26 con el hub corriendo: el resumen decía "6/20 con
logo vectorial" pero el endpoint sólo resolvía por slug, así que `freedom` --
cuyo archivo se llama `club_freedom.svg`, dato que sólo está en su ficha --
contaba como logo existente y devolvía 404. El panel mostraba "logo vectorial"
sobre un recuadro vacío.

Además pedía el logo de las 20 productoras aunque 14 no tienen ninguno: 18
errores 404 en la consola del navegador, que se leen como una falla de la app.
"""
from __future__ import annotations

import json

from flujo.web.hub import HubRequestHandler
from flujo.rd.panel import datos_panel


def _armar(raiz, *, vector=(), descargas=(), fichas=None):
    logos = raiz / "knowledge" / "logos"
    (logos / "vector").mkdir(parents=True)
    (logos / "descargas").mkdir(parents=True)
    for nombre in vector:
        (logos / "vector" / nombre).write_text("<svg/>", encoding="utf-8")
    for nombre in descargas:
        (logos / "descargas" / nombre).write_bytes(b"x")
    fichas_dir = raiz / "data" / "productoras"
    fichas_dir.mkdir(parents=True)
    for slug, ref in (fichas or {}).items():
        contenido = {"logos": [{"knowledge": ref}]} if ref else {}
        (fichas_dir / f"{slug}.json").write_text(json.dumps(contenido), encoding="utf-8")
    return logos


def test_encuentra_el_logo_aunque_el_archivo_no_se_llame_como_el_slug(tmp_path):
    """`gridsystem` -> grid_system.svg, por comparación normalizada."""
    logos = _armar(tmp_path, vector=("grid_system.svg",))
    cands = HubRequestHandler._candidatos_logo(logos, "gridsystem")
    assert any(c.is_file() for c in cands)


def test_usa_el_nombre_que_declara_la_ficha(tmp_path):
    """`freedom` -> club_freedom.svg: eso NO se deduce del slug, lo dice su json.

    Es el caso que quedaba desalineado: contado como vector, servido como 404.
    """
    logos = _armar(tmp_path, vector=("club_freedom.svg",),
                   fichas={"freedom": "club_freedom.yaml"})
    ref = HubRequestHandler._ref_logo_de_ficha(tmp_path, "freedom")
    assert ref == "club_freedom"
    assert any(c.is_file() for c in HubRequestHandler._candidatos_logo(logos, "freedom", ref))


def test_sin_logo_no_hay_candidato(tmp_path):
    """Para que el panel pueda no pedirlo, en vez de coleccionar 404."""
    logos = _armar(tmp_path, vector=("otra.svg",))
    assert not any(c.is_file() for c in HubRequestHandler._candidatos_logo(logos, "amelie"))


def test_prefiere_el_vector_sobre_la_descarga(tmp_path):
    """El vector es el que sirve para imprimir; la descarga es el respaldo."""
    logos = _armar(tmp_path, vector=("amelie.svg",), descargas=("amelie.png",))
    primero = next(c for c in HubRequestHandler._candidatos_logo(logos, "amelie") if c.is_file())
    assert primero.suffix == ".svg"


def test_una_ficha_rota_no_tumba_el_panel(tmp_path):
    fichas = tmp_path / "data" / "productoras"
    fichas.mkdir(parents=True)
    (fichas / "rota.json").write_text("{no es json", encoding="utf-8")
    assert HubRequestHandler._ref_logo_de_ficha(tmp_path, "rota") == ""


def test_el_panel_solo_pide_el_logo_si_existe():
    """Regresión de los 18 errores en consola."""
    from pathlib import Path

    panel = (Path(__file__).resolve().parents[1] / "web" / "src" / "components"
             / "RdDbPanel.tsx").read_text(encoding="utf-8")
    assert "p.logo.archivo !== false" in panel, (
        "el panel volvió a pedir el logo de todas las productoras"
    )


def test_datos_panel_expone_fuentes_primarias_de_eventos(tmp_path):
    fichas = tmp_path / "data" / "productoras"
    fichas.mkdir(parents=True)
    (tmp_path / "knowledge" / "logos" / "vector").mkdir(parents=True)
    (tmp_path / "knowledge" / "venues").mkdir(parents=True)
    (fichas / "acme.json").write_text(json.dumps({
        "name": "Acme",
        "eventos": [
            {
                "nombre": "Evento oficial",
                "fecha": "2026-11-20",
                "fuente": "post oficial https://www.instagram.com/p/DaRCFPhCfdM/",
            },
            {
                "nombre": "Evento rumor",
                "fecha": "needs_confirmation",
                "fuente": "comentario sin URL",
            },
        ],
    }), encoding="utf-8")

    data = datos_panel(tmp_path)
    eventos = data["productoras"][0]["eventos"]

    assert data["resumen"]["eventos_sin_fuente_primaria"] == 1
    assert eventos[0]["fuentes_primarias"] == ["https://www.instagram.com/p/DaRCFPhCfdM/"]
    assert eventos[0]["sin_fuente_primaria"] is False
    assert eventos[1]["fuentes_primarias"] == []
    assert eventos[1]["sin_fuente_primaria"] is True
