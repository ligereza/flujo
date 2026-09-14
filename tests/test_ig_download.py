"""Tests offline para flujo.ig.download: parsing de shortcode y flujo de
download_post con parth-dl mockeado (_parth_download). Nunca toca la red.
"""

from pathlib import Path
import sys
import types

import pytest

import flujo.paths  # noqa: F401
from flujo.ig import download as ig_download
from flujo.ig.download import download_post, extract_shortcode, indice_pedido


# ---------------- indice_pedido ----------------

def test_indice_pedido_sin_img_index():
    assert indice_pedido("https://www.instagram.com/p/ABC123/") == 1


def test_indice_pedido_con_img_index():
    assert indice_pedido("https://www.instagram.com/p/ABC123/?img_index=3") == 3


def test_indice_pedido_invalido_cae_a_1():
    assert indice_pedido("https://www.instagram.com/p/ABC123/?img_index=nope") == 1


def test_indice_pedido_cero_o_negativo_cae_a_1():
    assert indice_pedido("https://www.instagram.com/p/ABC123/?img_index=0") == 1
    assert indice_pedido("https://www.instagram.com/p/ABC123/?img_index=-2") == 1


# ---------------- extract_shortcode ----------------

def test_extract_shortcode_post_directo():
    assert extract_shortcode("https://www.instagram.com/p/DXelZPPCOuM/") == "DXelZPPCOuM"


def test_extract_shortcode_con_usuario():
    assert extract_shortcode("https://www.instagram.com/sundeckfiestas/p/ABC123/") == "ABC123"


def test_extract_shortcode_reel():
    assert extract_shortcode("https://www.instagram.com/reel/XYZ789/") == "XYZ789"


def test_extract_shortcode_reels_plural():
    assert extract_shortcode("https://www.instagram.com/reels/XYZ789/") == "XYZ789"


def test_extract_shortcode_tv():
    assert extract_shortcode("https://www.instagram.com/tv/IGTVCODE/") == "IGTVCODE"


def test_extract_shortcode_no_match():
    assert extract_shortcode("https://www.instagram.com/sundeckfiestas/") is None


def test_extract_shortcode_url_vacia():
    assert extract_shortcode("") is None


# ---------------- download_post (parth-dl mockeado via _parth_download) ----------------

def test_download_post_shortcode_no_detectado():
    out = download_post("https://www.instagram.com/sundeckfiestas/", Path("no-importa"))
    assert out["status"] == "error"
    assert out["reason"] == "shortcode_no_detectado"


def test_download_post_reel_sin_mp4_no_se_convierte_en_imagen(monkeypatch, tmp_path):
    def fake_parth(url, shortcode, output_dir):
        dst = output_dir / "input_ig.jpg"
        dst.write_bytes(b"poster")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "image",
            "files": [str(dst)],
            "video_files": [],
            "image_files": [str(dst)],
            "file_count": 1,
            "is_video": False,
        }

    def fake_cffi(url, shortcode, output_dir):
        return fake_parth(url, shortcode, output_dir)

    monkeypatch.setattr(ig_download, "_parth_download", fake_parth)
    monkeypatch.setattr(ig_download, "_cffi_download", fake_cffi)

    out = download_post("https://www.instagram.com/reel/VIDEO3/", tmp_path)

    assert out["status"] == "manual_required"
    assert out["reason"] == "video_sin_mp4"
    assert out["media_type"] == "video"


def test_download_post_reel_usa_snapinsta_solo_como_video_fallback(monkeypatch, tmp_path):
    def fail_primary(url, shortcode, output_dir):
        raise RuntimeError("login wall")

    def fake_snap(url, shortcode, output_dir):
        dst = output_dir / "input_ig.mp4"
        dst.write_bytes(b"mp4")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "video",
            "files": [str(dst)],
            "video_files": [str(dst)],
            "image_files": [],
            "file_count": 1,
            "is_video": True,
        }

    monkeypatch.setattr(ig_download, "_parth_download", fail_primary)
    monkeypatch.setattr(ig_download, "_cffi_download", lambda *args: None)
    monkeypatch.setattr(ig_download, "_snapinsta_download", fake_snap)

    out = download_post("https://www.instagram.com/reel/VIDEO4/", tmp_path)

    assert out["status"] == "downloaded"
    assert out["media_type"] == "video"
    assert out["video_files"] == [str(tmp_path / "input_ig.mp4")]


def test_is_mp4_file_rechaza_jpeg_disfrazado(tmp_path):
    fake_jpeg = tmp_path / "fake.mp4"
    fake_jpeg.write_bytes(b"\xff\xd8\xff\xe0" + b"x" * 40_000)
    fake_mp4 = tmp_path / "real.mp4"
    fake_mp4.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"x" * 40_000)

    assert ig_download._is_mp4_file(fake_jpeg) is False
    assert ig_download._is_mp4_file(fake_mp4) is True


def test_download_post_exitoso_imagen(monkeypatch, tmp_path):
    def fake_parth(url, shortcode, output_dir):
        dst = output_dir / "input_ig.jpg"
        dst.write_bytes(b"fake-jpg-bytes")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "image",
            "files": [str(dst)],
            "file_count": 1,
            "caption": "hola",
            "owner": "cuenta",
            "date": "",
            "is_video": False,
        }

    monkeypatch.setattr(ig_download, "_parth_download", fake_parth)

    out_dir = tmp_path / "out"
    out = download_post("https://www.instagram.com/p/ABC123/", out_dir)

    assert out["status"] == "downloaded"
    assert out["shortcode"] == "ABC123"
    assert out["media_type"] == "image"
    assert out["file_count"] == 1
    assert (out_dir / "input_ig.jpg").read_bytes() == b"fake-jpg-bytes"


def test_download_post_exitoso_carousel(monkeypatch, tmp_path):
    def fake_parth(url, shortcode, output_dir):
        dst1 = output_dir / "input_ig.jpg"
        dst2 = output_dir / "input_ig_2.jpg"
        dst1.write_bytes(b"x")
        dst2.write_bytes(b"x")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "carousel",
            "files": [str(dst1), str(dst2)],
            "file_count": 2,
            "caption": "",
            "owner": "",
            "date": "",
            "is_video": False,
        }

    monkeypatch.setattr(ig_download, "_parth_download", fake_parth)

    out_dir = tmp_path / "out"
    out = download_post("https://www.instagram.com/p/CAROUSEL1/", out_dir)

    assert out["status"] == "downloaded"
    assert out["media_type"] == "carousel"
    assert out["file_count"] == 2
    assert (out_dir / "input_ig.jpg").exists()
    assert (out_dir / "input_ig_2.jpg").exists()


def _fake_carousel_parth(image_count: int):
    """Mock _parth_download returning `image_count` real, on-disk slides."""
    def fake_parth(url, shortcode, output_dir):
        image_files = []
        for i in range(1, image_count + 1):
            name = "input_ig.jpg" if i == 1 else f"input_ig_{i}.jpg"
            dst = output_dir / name
            dst.write_bytes(b"x")
            image_files.append(str(dst))
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "carousel" if image_count > 1 else "image",
            "files": image_files,
            "image_files": image_files,
            "file_count": image_count,
            "caption": "",
            "owner": "",
            "date": "",
            "is_video": False,
        }
    return fake_parth


def test_download_post_respeta_img_index_del_link(monkeypatch, tmp_path):
    """Instagram pone `?img_index=N` cuando alguien comparte esa slide del
    carrusel; el sistema debe anotar cual se pidio (y que existe) en vez de
    ignorarlo y renderizar siempre la primera."""
    monkeypatch.setattr(ig_download, "_parth_download", _fake_carousel_parth(3))

    out = download_post("https://www.instagram.com/p/CAROUSEL2/?img_index=2", tmp_path)

    assert out["status"] == "downloaded"
    assert out["requested_image_index"] == 2
    assert out["requested_image_index_available"] is True


def test_download_post_img_index_fuera_de_rango_se_marca_no_disponible(monkeypatch, tmp_path):
    """Se pidio la slide 5 pero el post solo tiene 3: no se sustituye en
    silencio, se marca como no disponible para que el caller avise y use
    la primera."""
    monkeypatch.setattr(ig_download, "_parth_download", _fake_carousel_parth(3))

    out = download_post("https://www.instagram.com/p/CAROUSEL3/?img_index=5", tmp_path)

    assert out["status"] == "downloaded"
    assert out["requested_image_index"] == 5
    assert out["requested_image_index_available"] is False


def test_download_post_sin_img_index_pide_la_primera(monkeypatch, tmp_path):
    monkeypatch.setattr(ig_download, "_parth_download", _fake_carousel_parth(3))

    out = download_post("https://www.instagram.com/p/CAROUSEL4/", tmp_path)

    assert out["requested_image_index"] == 1
    assert out["requested_image_index_available"] is True


def test_parth_download_video_conserva_mp4_y_poster(monkeypatch, tmp_path):
    fake_pkg = types.ModuleType("parth_dl")
    fake_pkg.get_info = lambda _url: {
        "type": "video",
        "thumbnail": "https://cdn.example/poster.jpg",
        "entries": [{
            "kind": "video",
            "formats": [{
                "url": "https://cdn.example/reel.mp4",
                "width": 576,
                "height": 768,
                "has_audio": True,
            }],
        }],
    }
    monkeypatch.setitem(sys.modules, "parth_dl", fake_pkg)

    def fake_download(url, destination):
        destination.write_bytes(b"mp4" if url.endswith(".mp4") else b"jpg")
        return destination

    monkeypatch.setattr(ig_download, "_download_file", fake_download)
    out = ig_download._parth_download("https://www.instagram.com/reel/VIDEO1/", "VIDEO1", tmp_path)

    assert out["media_type"] == "video"
    assert out["is_video"] is True
    assert out["video_files"] == [str(tmp_path / "input_ig.mp4")]
    assert out["image_files"] == [str(tmp_path / "input_ig.jpg")]
    assert (tmp_path / "input_ig.mp4").read_bytes() == b"mp4"


def test_parth_download_video_sin_mp4_falla(monkeypatch, tmp_path):
    fake_pkg = types.ModuleType("parth_dl")
    fake_pkg.get_info = lambda _url: {
        "type": "video",
        "thumbnail": "https://cdn.example/poster.jpg",
        "entries": [{"kind": "video", "formats": []}],
    }
    monkeypatch.setitem(sys.modules, "parth_dl", fake_pkg)

    with pytest.raises(RuntimeError, match="video_sin_mp4"):
        ig_download._parth_download(
            "https://www.instagram.com/reel/VIDEO2/", "VIDEO2", tmp_path)


def test_download_post_limpia_archivos_previos(monkeypatch, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "input_ig.jpg").write_bytes(b"viejo")
    (out_dir / "input_ig_2.jpg").write_bytes(b"viejo2")
    (out_dir / "ig_caption.txt").write_text("caption vieja", encoding="utf-8")

    def fake_parth(url, shortcode, output_dir):
        # a esta altura download_post ya debio limpiar los archivos previos
        assert not (output_dir / "input_ig_2.jpg").exists()
        dst = output_dir / "input_ig.jpg"
        dst.write_bytes(b"nuevo-bytes")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "image",
            "files": [str(dst)],
            "file_count": 1,
            "caption": "",
            "owner": "",
            "date": "",
            "is_video": False,
        }

    monkeypatch.setattr(ig_download, "_parth_download", fake_parth)

    out = download_post("https://www.instagram.com/p/NUEVO1/", out_dir)

    assert out["status"] == "downloaded"
    assert not (out_dir / "input_ig_2.jpg").exists()
    assert (out_dir / "input_ig.jpg").read_bytes() == b"nuevo-bytes"


def test_download_post_sin_archivos_es_manual_required(monkeypatch, tmp_path):
    def boom(url, shortcode, output_dir):
        raise RuntimeError("sin_archivos")

    monkeypatch.setattr(ig_download, "_parth_download", boom)
    out = download_post("https://www.instagram.com/p/SINARCHIVOS/", tmp_path / "out", retries=0)
    assert out["status"] == "manual_required"
    assert out["reason"] == "sin_archivos"


def test_download_post_rate_limit(monkeypatch, tmp_path):
    def boom(url, shortcode, output_dir):
        raise RuntimeError("429 Too Many Requests")

    monkeypatch.setattr(ig_download, "_parth_download", boom)
    out = download_post("https://www.instagram.com/p/RATE1/", tmp_path / "out", retries=0)
    assert out["status"] == "manual_required"
    assert out["reason"] == "rate_limit"


def test_download_post_reintenta_y_luego_funciona(monkeypatch, tmp_path):
    calls = {"n": 0}

    def flaky(url, shortcode, output_dir):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("post not found")
        dst = output_dir / "input_ig.jpg"
        dst.write_bytes(b"ok")
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "image",
            "files": [str(dst)],
            "file_count": 1,
            "caption": "",
            "owner": "",
            "date": "",
            "is_video": False,
        }

    monkeypatch.setattr(ig_download, "_parth_download", flaky)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)

    out = download_post("https://www.instagram.com/p/RETRY1/", tmp_path / "out", retries=1)
    assert out["status"] == "downloaded"
    assert calls["n"] == 2


def test_download_post_parth_dl_no_instalado(monkeypatch, tmp_path):
    def boom(url, shortcode, output_dir):
        raise ImportError("no module named parth_dl")

    monkeypatch.setattr(ig_download, "_parth_download", boom)
    out = download_post("https://www.instagram.com/p/NOPKG1/", tmp_path / "out", retries=2)
    assert out["status"] == "manual_required"
    assert out["reason"] == "parth_dl_no_instalado"
