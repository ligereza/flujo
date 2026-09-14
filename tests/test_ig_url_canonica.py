"""Tests de canonicalizar_url: la forma /usuario/p/SC/ daba 403 en parth-dl
(issues #5 y #171, 2026-07-22)."""

from flujo.ig.download import canonicalizar_url, extract_shortcode


def test_username_post_se_normaliza():
    assert (canonicalizar_url("https://www.instagram.com/iskvw/p/DUBSp7ikae2/")
            == "https://www.instagram.com/p/DUBSp7ikae2/")


def test_username_reel_preserva_tipo():
    assert (canonicalizar_url("https://www.instagram.com/sundeckfiestas/reel/DXelZPPCOuM/")
            == "https://www.instagram.com/reel/DXelZPPCOuM/")


def test_forma_canonica_queda_igual():
    url = "https://www.instagram.com/p/DZdW4_vmY4l/?igsh=M3E2cWl3dDV1a25l"
    assert canonicalizar_url(url) == url


def test_query_params_se_preservan():
    assert (canonicalizar_url("https://www.instagram.com/iskvw/p/ABC123/?igsh=xyz")
            == "https://www.instagram.com/p/ABC123/?igsh=xyz")


def test_shortcode_tras_canonicalizar():
    assert extract_shortcode(
        canonicalizar_url("https://www.instagram.com/iskvw/p/DUBSp7ikae2/")) == "DUBSp7ikae2"
