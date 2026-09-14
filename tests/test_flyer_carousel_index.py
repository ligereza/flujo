"""Regression tests for the audited defect in _download_via_mirror.

_download_via_parth and _download_via_embed both thread the requested
carousel slide (Instagram's own `?img_index=N`, read by _indice_pedido) into
which candidate they pick. _download_via_mirror collected every slide into
`candidatos` but always returned candidatos[0], so when the two higher
fidelity paths failed and this fallback succeeded, it silently overwrote
input_ig.jpg with an unrequested slide. These tests pin the fixed contract:
same index handling as _download_via_embed (select by index; if the index
does not fit, print an AVISO and fall back to slide 0 -- never substitute
without saying so).

Fully offline: urllib.request.urlopen is monkeypatched, no network is used.
_download_via_mirror does `import urllib.request` internally, but that import
resolves to the same module object already in sys.modules, so patching the
attribute on the module reaches the call inside the function too.
"""

from __future__ import annotations

from pathlib import Path

from flujo.eventos.flyer_auto import _download_via_mirror, _indice_pedido


SLIDE_URLS = [
    f"https://scontent.cdninstagram.com/t51.82787-15/slide{i}.jpg" for i in range(4)
]


def _mirror_page_html(urls: list[str]) -> bytes:
    """Build a page with one swiper-slide div per url, in order.

    Mirrors the real markup shape _download_via_mirror's regex expects:
    each slide is its own `<div class="swiper-slide">` containing an
    `<img data-src="...">` for that slide.
    """
    slides = "".join(
        f'<div class="swiper-slide"><img data-src="{u}" class="x"></div>' for u in urls
    )
    return f"<html><body>{slides}</body></html>".encode("utf-8")


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _fake_urlopen_factory(shortcode: str, page_html: bytes, image_bytes: dict[str, bytes]):
    page_url = f"https://imginn.com/p/{shortcode}/"

    def _fake_urlopen(req, timeout=30):  # noqa: ANN001 - matches urllib.request.urlopen shape
        url = req.full_url
        if url == page_url:
            return _FakeResponse(page_html)
        if url in image_bytes:
            return _FakeResponse(image_bytes[url])
        raise AssertionError(f"test did not expect a fetch of {url}")

    return _fake_urlopen


def _install_fake_mirror(monkeypatch, urls: list[str], shortcode: str = "ABC123"):
    image_bytes = {u: f"BYTES_FOR_{u}".encode("ascii") for u in urls}
    page_html = _mirror_page_html(urls)
    monkeypatch.setattr(
        "urllib.request.urlopen", _fake_urlopen_factory(shortcode, page_html, image_bytes)
    )
    return image_bytes


def test_requested_index_returns_that_slide_not_the_first(monkeypatch, tmp_path: Path, capsys):
    """Load-bearing: img_index=3 over 4 candidates must return the third slide.

    Fails against the pre-fix code because that code always fetched
    candidatos[0] regardless of the index argument (which did not even
    exist on the old signature).
    """
    image_bytes = _install_fake_mirror(monkeypatch, SLIDE_URLS)

    out = _download_via_mirror("ABC123", tmp_path, indice=3)

    assert out.read_bytes() == image_bytes[SLIDE_URLS[2]]
    assert out.read_bytes() != image_bytes[SLIDE_URLS[0]]
    assert "AVISO" not in capsys.readouterr().out


def test_out_of_range_index_warns_instead_of_silently_substituting(
    monkeypatch, tmp_path: Path, capsys
):
    """img_index=9 over 4 candidates must not quietly come back as slide 0.

    Matches _download_via_embed's contract: fall back to the first slide but
    print an AVISO, so the operator is never misled about which slide they
    actually got.
    """
    image_bytes = _install_fake_mirror(monkeypatch, SLIDE_URLS)

    out = _download_via_mirror("ABC123", tmp_path, indice=9)

    assert out.read_bytes() == image_bytes[SLIDE_URLS[0]]
    captured = capsys.readouterr()
    assert "AVISO" in captured.out
    assert "9" in captured.out


def test_no_index_requested_defaults_to_first_slide_without_warning(
    monkeypatch, tmp_path: Path, capsys
):
    """Unchanged behaviour: no index asked for -> slide 0, and no AVISO."""
    image_bytes = _install_fake_mirror(monkeypatch, SLIDE_URLS)

    out = _download_via_mirror("ABC123", tmp_path)

    assert out.read_bytes() == image_bytes[SLIDE_URLS[0]]
    assert "AVISO" not in capsys.readouterr().out


def test_single_image_post_is_unchanged(monkeypatch, tmp_path: Path, capsys):
    """A non-carousel post (one candidate) still resolves to that one image."""
    single_url = [SLIDE_URLS[0]]
    image_bytes = _install_fake_mirror(monkeypatch, single_url)

    out = _download_via_mirror("ABC123", tmp_path)

    assert out.read_bytes() == image_bytes[single_url[0]]
    assert "AVISO" not in capsys.readouterr().out


def test_mirror_honours_the_shared_parser_not_a_second_one(monkeypatch, tmp_path: Path):
    """The index must come from _indice_pedido, not a second hand-rolled parser.

    Parses a real share-link with ?img_index=3 through _indice_pedido and
    feeds that straight into _download_via_mirror, the same way the caller
    at the run_eventos_flyer_auto call site does.
    """
    shared_url = "https://www.instagram.com/p/ABC123/?img_index=3&igsh=x"
    requested_index = _indice_pedido(shared_url)
    assert requested_index == 3

    image_bytes = _install_fake_mirror(monkeypatch, SLIDE_URLS)

    out = _download_via_mirror("ABC123", tmp_path, requested_index)

    assert out.read_bytes() == image_bytes[SLIDE_URLS[2]]
