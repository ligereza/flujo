# -*- coding: utf-8 -*-
"""Via secundaria curl_cffi (impersonate=chrome) en flujo.ig.download.

parth-dl pega login-wall de IG por fingerprint TLS en Linux; curl_cffi
imita el fingerprint TLS de Chrome y pasa (verificado 2026-07-23, box MAK
Debian). curl_cffi es dep opcional: se mockea via sys.modules (no esta
instalada en este entorno de tests), snapshot/restore en finally para no
contaminar otros tests.

La via real prueba primero la pagina de embed (`contextJSON`, que trae el
carrusel completo con la resolucion real de cada slide) y solo cae a
`og:image` -- una sola imagen generica, recortada para tarjetas de
previsualizacion -- si el embed no trae nada util. Los tests de la via de
respaldo (og:image) simulan un embed sin contextJSON a proposito, para
ejercitar exactamente esa caida.
"""
import importlib.util
import sys
import types

import pytest

from flujo.ig.download import _cffi_download


class _FakeResponse:
    def __init__(self, text="", content=b"", status_code=200):
        self.text = text
        self.content = content
        self.status_code = status_code


class _FakeSession:
    """Mapea url -> _FakeResponse (o Exception a levantar). Registra calls."""

    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        resp = self._responses.get(url)
        if resp is None:
            raise RuntimeError(f"url inesperada en el fake: {url}")
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.fixture
def fake_curl_cffi():
    """Instala un curl_cffi falso en sys.modules; restaura (pop) en finally."""
    installed = {}

    def _install(responses):
        fake_requests_mod = types.ModuleType("curl_cffi.requests")
        fake_requests_mod.Session = lambda *a, **k: _FakeSession(responses)
        fake_pkg = types.ModuleType("curl_cffi")
        fake_pkg.requests = fake_requests_mod
        sys.modules["curl_cffi"] = fake_pkg
        sys.modules["curl_cffi.requests"] = fake_requests_mod
        installed["session_responses"] = responses
        return fake_requests_mod

    try:
        yield _install
    finally:
        sys.modules.pop("curl_cffi", None)
        sys.modules.pop("curl_cffi.requests", None)


SHORTCODE = "DZdW4_vmY4l"
PAGE_URL = f"https://www.instagram.com/p/{SHORTCODE}/"
EMBED_URL = f"https://www.instagram.com/p/{SHORTCODE}/embed/captioned/"
IMG_URL = "https://scontent.cdninstagram.com/v/t51.29350-15/photo.jpg"

# Embed page with no usable contextJSON: forces the fallback to og:image,
# which is exactly what the fallback-path tests below want to exercise.
EMBED_SIN_CONTEXTJSON = "<html><body>no embed data here</body></html>"


def _context_json_html(shortcode_media: dict) -> str:
    """An embed page whose contextJSON carries the given shortcode_media."""
    import json
    inner = json.dumps({"gql_data": {"shortcode_media": shortcode_media}})
    # contextJSON itself is a JSON-encoded STRING (double-encoded), same as
    # the real page: the outer value is a JSON string literal.
    return '<html><body><script>{"contextJSON":%s}</script></body></html>' % json.dumps(inner)


def _page_html(extra_meta="", caption='caption de prueba con &quot;comillas&quot;'):
    return f"""<html><head>
<meta property="og:image" content="{IMG_URL}" />
<meta property="og:description" content="{caption}" />
{extra_meta}
</head><body></body></html>"""


def test_og_image_presente_descarga_y_contrato_correcto(fake_curl_cffi, tmp_path):
    fake_curl_cffi({
        EMBED_URL: _FakeResponse(text=EMBED_SIN_CONTEXTJSON),
        PAGE_URL: _FakeResponse(text=_page_html()),
        IMG_URL: _FakeResponse(content=b"jpg-bytes-reales"),
    })

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is not None
    assert out["status"] == "downloaded"
    assert out["shortcode"] == SHORTCODE
    assert out["url"] == PAGE_URL
    assert out["media_type"] == "image"
    assert out["is_video"] is False
    assert out["file_count"] == 1
    assert out["files"] == [str(tmp_path / "input_ig.jpg")]
    assert (tmp_path / "input_ig.jpg").read_bytes() == b"jpg-bytes-reales"
    assert out["caption"] == 'caption de prueba con "comillas"'


def test_sin_og_image_retorna_none(fake_curl_cffi, tmp_path):
    html = '<html><head><meta property="og:title" content="sin imagen" /></head></html>'
    fake_curl_cffi({
        EMBED_URL: _FakeResponse(text=EMBED_SIN_CONTEXTJSON),
        PAGE_URL: _FakeResponse(text=html),
    })

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is None
    assert not (tmp_path / "input_ig.jpg").exists()


@pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is not None,
    reason="curl_cffi instalado: no se puede simular su ausencia y el test saldria a la red real",
)
def test_sin_curl_cffi_instalado_retorna_none_sin_explotar(tmp_path):
    # Sin fixture: curl_cffi NO esta en sys.modules -> ImportError real dentro
    # de _cffi_download -> None.
    #
    # 2026-07-26: sacar el modulo de sys.modules NO alcanza si el paquete esta
    # instalado -- Python lo re-importa del disco, _cffi_download funciona, y el
    # test hacia una descarga REAL contra Instagram (falla en la maquina del
    # usuario con curl_cffi 0.15.0; verde en CI solo porque ahi no esta el
    # paquete). Un test que sale a la red segun el entorno no mide nada: se
    # salta donde no puede simularse. Retiro: si la descarga se inyecta por
    # dependencia y deja de importarse adentro de la funcion.
    sys.modules.pop("curl_cffi", None)
    sys.modules.pop("curl_cffi.requests", None)

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is None


def test_og_video_presente_baja_thumbnail_igual(fake_curl_cffi, tmp_path):
    video_url = "https://scontent.cdninstagram.com/v/video.mp4"
    html = _page_html(extra_meta=f'<meta property="og:video" content="{video_url}" />')
    fake_curl_cffi({
        EMBED_URL: _FakeResponse(text=EMBED_SIN_CONTEXTJSON),
        PAGE_URL: _FakeResponse(text=html),
        IMG_URL: _FakeResponse(content=b"thumbnail-bytes"),
        video_url: _FakeResponse(content=b"mp4-bytes"),
    })

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is not None
    assert out["is_video"] is True
    assert out["media_type"] == "video"
    assert out["files"] == [str(tmp_path / "input_ig.jpg"), str(tmp_path / "input_ig.mp4")]
    assert out["video_files"] == [str(tmp_path / "input_ig.mp4")]
    assert (tmp_path / "input_ig.jpg").read_bytes() == b"thumbnail-bytes"
    assert (tmp_path / "input_ig.mp4").read_bytes() == b"mp4-bytes"


def test_caption_escrita_en_archivo(fake_curl_cffi, tmp_path):
    fake_curl_cffi({
        EMBED_URL: _FakeResponse(text=EMBED_SIN_CONTEXTJSON),
        PAGE_URL: _FakeResponse(text=_page_html(caption="hola &amp; chau &#39;test&#39;")),
        IMG_URL: _FakeResponse(content=b"x"),
    })

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is not None
    caption_file = tmp_path / "ig_caption.txt"
    assert caption_file.exists()
    assert caption_file.read_text(encoding="utf-8") == "hola & chau 'test'"
    assert out["caption"] == "hola & chau 'test'"


def test_excepcion_de_red_retorna_none(fake_curl_cffi, tmp_path):
    fake_curl_cffi({EMBED_URL: RuntimeError("connection reset")})

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is None
    assert not (tmp_path / "input_ig.jpg").exists()


def test_embed_contextjson_carrusel_trae_todas_las_slides(fake_curl_cffi, tmp_path):
    """The actual bug: a carousel used to collapse to one og:image crop.

    contextJSON's edge_sidecar_to_children carries every slide at its real
    display_url; this is what the render should have been fed all along.
    """
    slide_urls = [
        "https://scontent.cdninstagram.com/v/slide1.jpg",
        "https://scontent.cdninstagram.com/v/slide2.jpg",
        "https://scontent.cdninstagram.com/v/slide3.jpg",
    ]
    shortcode_media = {
        "is_video": False,
        "edge_sidecar_to_children": {
            "edges": [{"node": {"display_url": u, "is_video": False}} for u in slide_urls]
        },
        "edge_media_to_caption": {"edges": [{"node": {"text": "carrusel real"}}]},
    }
    responses = {EMBED_URL: _FakeResponse(text=_context_json_html(shortcode_media))}
    for i, u in enumerate(slide_urls, start=1):
        responses[u] = _FakeResponse(content=f"slide-{i}-bytes".encode())
    fake_curl_cffi(responses)

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is not None
    assert out["media_type"] == "carousel"
    assert out["file_count"] == 3
    assert out["image_files"] == [
        str(tmp_path / "input_ig.jpg"),
        str(tmp_path / "input_ig_2.jpg"),
        str(tmp_path / "input_ig_3.jpg"),
    ]
    assert (tmp_path / "input_ig.jpg").read_bytes() == b"slide-1-bytes"
    assert (tmp_path / "input_ig_2.jpg").read_bytes() == b"slide-2-bytes"
    assert (tmp_path / "input_ig_3.jpg").read_bytes() == b"slide-3-bytes"
    assert out["caption"] == "carrusel real"
    # PAGE_URL/og:image was never registered above: contextJSON already had
    # everything needed, so if the code fell back to it the fake session
    # would raise "url inesperada" and this test would fail loud instead.


def test_embed_contextjson_post_simple_no_cae_a_og_image(fake_curl_cffi, tmp_path):
    """A single-image post already resolved by contextJSON must not touch
    the og:image fallback at all -- that is the crop-prone path."""
    shortcode_media = {
        "is_video": False,
        "display_url": IMG_URL,
        "edge_media_to_caption": {"edges": []},
    }
    fake_curl_cffi({
        EMBED_URL: _FakeResponse(text=_context_json_html(shortcode_media)),
        IMG_URL: _FakeResponse(content=b"full-res-bytes"),
        # PAGE_URL intentionally NOT registered: if the code touches it,
        # the fake session raises "url inesperada" and the test fails loud.
    })

    out = _cffi_download(PAGE_URL, SHORTCODE, tmp_path)

    assert out is not None
    assert out["media_type"] == "image"
    assert out["image_files"] == [str(tmp_path / "input_ig.jpg")]
    assert (tmp_path / "input_ig.jpg").read_bytes() == b"full-res-bytes"
