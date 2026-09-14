"""Regresión: links de Instagram con <usuario> antes de /p/ (formato real)."""

from flujo.intake.email_parser import extract_instagram_links as ex


def test_url_con_usuario_antes_de_p():
    url = "https://www.instagram.com/sundeckfiestas/p/DXelZPPCOuM/"
    assert ex(url) == [url]


def test_url_con_usuario_reel():
    assert ex("instagram.com/cuenta/reel/XYZ/") == ["https://instagram.com/cuenta/reel/XYZ/"]


def test_url_con_usuario_con_punto():
    assert ex("www.instagram.com/sundeck.fiestas/p/ABC123") == [
        "https://www.instagram.com/sundeck.fiestas/p/ABC123"
    ]


def test_url_con_usuario_y_querystring():
    assert ex("https://www.instagram.com/sundeckfiestas/p/DXelZPPCOuM/?igsh=zz") == [
        "https://www.instagram.com/sundeckfiestas/p/DXelZPPCOuM/"
    ]


def test_url_directa_sigue_funcionando():
    assert ex("https://www.instagram.com/p/DXelZPPCOuM/") == [
        "https://www.instagram.com/p/DXelZPPCOuM/"
    ]


def test_perfil_puro_no_cuenta():
    assert ex("https://www.instagram.com/sundeckfiestas/") == []
    assert ex("instagram.com/sundeckfiestas") == []


def test_mezcla_usuario_y_directo():
    out = ex("mira instagram.com/cuenta/p/A1/ y instagram.com/p/B2/")
    assert out == ["https://instagram.com/cuenta/p/A1/", "https://instagram.com/p/B2/"]
