# -*- coding: utf-8 -*-
"""Trazar una imagen para usarla como símbolo del plano.

Pedido del usuario, 2026-07-26: "se puede integrar tool tracer si ella carga una
imagen y no un svg". Se traza la SILUETA, que es lo que es un icono, y el
resultado se le muestra antes de guardar: un trazado automático puede salir
sucio y quien decide si sirve es quien lo mira.

Por qué trazar y no incrustar el PNG: el símbolo termina en un A4 impreso. Una
imagen chica incrustada se ve pixelada; un contorno escala limpio y además
obedece el color declarado, igual que los 17 íconos de fábrica.
"""
from __future__ import annotations

import io

import pytest

from flujo.plano.trazador import TrazadoImposible, trazar


def _png(dibujar, tamano=(400, 400), fondo=(0, 0, 0, 0)) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", tamano, fondo)
    dibujar(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_traza_una_silueta_simple():
    datos = _png(lambda d: d.ellipse([40, 40, 360, 360], fill=(20, 20, 20, 255)))
    svg = trazar(datos)
    assert svg.startswith("<svg") and "</svg>" in svg
    assert 'viewBox="0 0 160 160"' in svg
    # currentColor es la convencion del resto del catalogo: un archivo sirve
    # para el plano oscuro y para el blanco.
    assert 'fill="currentColor"' in svg
    assert "currentColor" in svg and svg.count("M ") >= 1


def test_conserva_los_huecos_del_icono():
    """Un anillo tiene que salir anillo, no disco: el hueco se cala."""
    datos = _png(lambda d: (
        d.ellipse([40, 40, 360, 360], fill=(20, 20, 20, 255)),
        d.ellipse([150, 150, 250, 250], fill=(0, 0, 0, 0)),
    ))
    svg = trazar(datos)
    assert 'fill-rule="evenodd"' in svg
    assert svg.count("M ") >= 2, "falta el contorno interior"


def test_funciona_sobre_fondo_opaco_sin_transparencia():
    """Un JPG no trae alfa: la tinta se decide por contraste."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 300), (255, 255, 255))
    ImageDraw.Draw(img).rectangle([60, 60, 240, 240], fill=(10, 10, 10))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    svg = trazar(buf.getvalue())
    assert "M " in svg


def test_icono_claro_sobre_fondo_oscuro():
    """El caso invertido no puede devolver el fondo como si fuera el icono."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 300), (12, 12, 12))
    ImageDraw.Draw(img).ellipse([90, 90, 210, 210], fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    svg = trazar(buf.getvalue())
    # Si tomara el fondo, el contorno seria el borde del lienzo entero.
    assert "M " in svg
    assert len(svg) < 4000


def test_el_resultado_es_liviano():
    """Va dentro de un plano que se imprime: no puede pesar como una foto."""
    datos = _png(lambda d: d.ellipse([40, 40, 360, 360], fill=(20, 20, 20, 255)))
    assert len(trazar(datos)) < 8000


@pytest.mark.parametrize("datos,esperado", [
    (b"esto no es una imagen", "no es una imagen"),
])
def test_rechaza_lo_que_no_es_imagen(datos, esperado):
    with pytest.raises(TrazadoImposible) as e:
        trazar(datos)
    assert esperado in str(e.value)


def test_imagen_sin_contraste_avisa_en_vez_de_devolver_basura():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (200, 200), (128, 128, 128)).save(buf, "PNG")
    with pytest.raises(TrazadoImposible) as e:
        trazar(buf.getvalue())
    assert "contraste" in str(e.value)


def test_el_trazo_entra_al_catalogo_como_cualquier_simbolo(tmp_path, monkeypatch):
    """Lo trazado no es un caso aparte: se guarda y se dibuja igual que un SVG."""
    import json

    from flujo.plano import iconos
    from flujo.web.hub import HubRequestHandler

    (tmp_path / "data" / "plano_simbolos").mkdir(parents=True)
    (tmp_path / "data" / "plano_simbolos.json").write_text(
        json.dumps({"simbolos": []}), encoding="utf-8")
    monkeypatch.setattr("flujo.web.hub.repo_root", lambda: tmp_path)
    iconos.recargar_catalogo(tmp_path)
    try:
        svg = trazar(_png(lambda d: d.ellipse([40, 40, 360, 360], fill=(20, 20, 20, 255))))
        handler = HubRequestHandler.__new__(HubRequestHandler)
        res = handler._guardar_simbolo_plano({"etiqueta": "Zona de carga", "svg": svg})
        assert res["ok"], res
        marca = iconos.icono("zona_de_carga", 100, 100, 1.0)
        assert "<g transform" in marca and "currentColor" not in marca
    finally:
        iconos._RAIZ_FIJA = None
        iconos.recargar_catalogo()
