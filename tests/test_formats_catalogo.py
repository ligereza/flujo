"""Tests del catálogo de formatos v2.0 (área/medio/herramienta/paramétrico).

Protege el catálogo oficial de la ONG contra regresiones:
- que todos los formatos esperados existan,
- que la metadata nueva se cargue,
- que los filtros funcionen,
- que los formatos paramétricos (pendones/banderas) no rompan nada.
"""

import pytest

from flujo.render.formats import list_formats, load_index, FormatInfo


def _ids():
    return {f.id for f in load_index()}


def test_catalogo_carga():
    formats = load_index()
    # el catálogo oficial tiene al menos los 12 formatos definidos
    assert len(formats) >= 12


def test_formatos_clave_existen():
    ids = _ids()
    esperados = {
        "evt_flyer_fisico_10x14",
        "evt_cartelera_individual_1080x1920",
        "evt_cartelera_triple_1080x1920",
        "evt_post_ig_1080x1350",
        "evt_brief_productora_pdf_universal",
        "sup_etiqueta_165x65",
        "sup_etiqueta_140x100",
        "sup_flyer_informativo_a5",
        "sup_pendon_rectangular",
        "sup_bandera_poligonal",
    }
    faltan = esperados - ids
    assert not faltan, f"faltan formatos en el catálogo: {faltan}"


def test_metadata_v2_se_carga():
    by_id = {f.id: f for f in load_index()}
    etq = by_id["sup_etiqueta_165x65"]
    assert etq.area == "suplementos"
    assert etq.medio == "impresion"
    assert "illustrator" in etq.herramienta


def test_cartelera_usa_blender():
    by_id = {f.id: f for f in load_index()}
    cart = by_id["evt_cartelera_individual_1080x1920"]
    assert cart.medio == "digital"
    assert "blender" in cart.herramienta
    # debe inferir productora/fecha/venue desde la imagen de IG
    assert "productora" in cart.inferir


def test_cartelera_triple_infiere_logo():
    by_id = {f.id: f for f in load_index()}
    triple = by_id["evt_cartelera_triple_1080x1920"]
    # en la triple SÍ se ven los logos
    assert "logo" in triple.inferir


def test_pendones_son_parametricos():
    by_id = {f.id: f for f in load_index()}
    assert by_id["sup_pendon_rectangular"].parametrico is True
    assert by_id["sup_bandera_poligonal"].parametrico is True


# --- filtros ---------------------------------------------------------------

def test_filtro_area_suplementos():
    sup = list_formats(area="suplementos")
    assert sup
    assert all(f.area == "suplementos" for f in sup)


def test_filtro_area_eventos():
    evt = list_formats(area="eventos")
    assert evt
    assert all(f.area == "eventos" for f in evt)


def test_filtro_medio_impresion_es_illustrator():
    """Regla clave: impresión real => Illustrator."""
    impr = list_formats(medio="impresion")
    assert impr
    assert all("illustrator" in f.herramienta for f in impr)


def test_filtro_medio_digital_no_es_illustrator():
    """Regla clave: digital => Photoshop/Blender, nunca solo Illustrator."""
    dig = list_formats(medio="digital")
    assert dig
    assert all("illustrator" not in f.herramienta for f in dig)


def test_filtro_herramienta_blender():
    bl = list_formats(herramienta="blender")
    assert bl
    assert all("blender" in f.herramienta for f in bl)


# --- robustez de paramétricos ---------------------------------------------

def test_str_no_rompe_con_parametrico():
    for f in load_index():
        s = str(f)  # no debe lanzar aunque canvas sea 0
        assert f.id in s


def test_has_template_flag():
    by_id = {f.id: f for f in load_index()}
    # con plantilla
    assert by_id["sup_etiqueta_165x65"].has_template
    # sin plantilla (template null)
    assert not by_id["evt_cartelera_individual_1080x1920"].has_template
