"""Tests for src/flujo/comercial/suplementos_config.py.

What this pins (rewritten 2026-07-26): the module reads the APPROVED content
file and holds no product data of its own. It used to carry a hardcoded dict
with four supplements that do not exist ("Recovery", "Colágeno Fit",
"Omega+ Immune", "Sleep Relax"), gym copy for a harm-reduction NGO, and
placeholder Dominican phone numbers -- and `flujo suplementos list` printed all
of it as the real line.

The user's rule: for supplements the text comes from the file an RD manager
sends, and that file wins. So the tests below check the module mirrors that file
rather than checking any particular content, which would just move the
fabrication into the test.
"""
from __future__ import annotations

import json

import pytest

from flujo.comercial.suplementos_config import (
    CONTENIDO_REL,
    Suplemento,
    get_suplemento,
    list_suplementos,
    proyecto,
    suplementos,
)
from flujo.paths import repo_root


def _contenido() -> dict:
    return json.loads((repo_root() / CONTENIDO_REL).read_text(encoding="utf-8"))


def test_lee_el_archivo_aprobado_y_no_inventa_nada():
    """Every supplement, and only those, come from the approved file."""
    esperados = [f["title"] for f in _contenido()["flyers"]]
    assert list_suplementos() == esperados


def test_get_suplemento_case_insensitive_y_por_id():
    a = get_suplemento("IMPULSO")
    b = get_suplemento("impulso")
    assert a is b
    assert isinstance(a, Suplemento)
    # el id del archivo tambien resuelve
    assert get_suplemento(a.id) is a


def test_el_contenido_es_verbatim_del_archivo():
    fuente = {f["title"]: f for f in _contenido()["flyers"]}
    for titulo, supl in suplementos().items():
        assert supl.descripcion == list(fuente[titulo].get("description", []))
        assert supl.items == list(fuente[titulo].get("items", []))
        assert supl.tag == fuente[titulo].get("tag", "")


def test_el_color_sale_de_la_paleta_del_archivo():
    paleta = _contenido()["palette"]
    for supl in suplementos().values():
        if supl.accent in paleta:
            assert supl.color_acento == paleta[supl.accent]


def test_suplemento_desconocido_lanza_keyerror():
    """No silent fallback: something not in the approved file does not exist."""
    with pytest.raises(KeyError, match="no existe"):
        get_suplemento("SustanciaQueNoExiste-xyz")


def test_no_quedan_campos_de_contacto():
    """The QR and the website are baked into the approved template and are the
    same on every piece, so nothing injects them per supplement. This also keeps
    placeholder phone numbers from creeping back in."""
    supl = get_suplemento("IMPULSO")
    for campo in ("contacto_label", "qr_text", "whatsapp_label"):
        assert not hasattr(supl, campo), f"{campo} volvio a aparecer"


def test_proyecto_expone_las_constantes_de_marca():
    proy = proyecto()
    assert proy.get("brand")
    assert proy.get("website")
