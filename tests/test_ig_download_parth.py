# -*- coding: utf-8 -*-
"""Seleccion parth-dl en flujo.ig.download (issue #145, patron de #142)."""
from flujo.ig.download import _parth_image_urls

# Forma real del reel DZ3bAdGhp7y (parth-dl 1.1.0, 2026-07-22), URLs recortadas.
VIDEO_META = {
    "thumbnail": "https://cdn/thumb.jpg",
    "type": "video",
    "formats": [{"url": "https://cdn/video.mp4", "width": 720, "height": 1280}],
    "images": [],
}


def test_video_devuelve_thumbnail_y_flag():
    urls, is_video = _parth_image_urls(VIDEO_META)
    assert urls == ["https://cdn/thumb.jpg"]
    assert is_video is True


def test_carrusel_devuelve_todas_en_orden():
    meta = {
        "type": "image",
        "thumbnail": "https://cdn/thumb.jpg",
        "images": [{"url": "https://cdn/uno.jpg"}, {"url": "https://cdn/dos.jpg"}],
    }
    urls, is_video = _parth_image_urls(meta)
    assert urls == ["https://cdn/uno.jpg", "https://cdn/dos.jpg"]
    assert is_video is False


def test_images_como_strings():
    urls, _ = _parth_image_urls({"images": ["https://cdn/a.jpg"]})
    assert urls == ["https://cdn/a.jpg"]


def test_sin_nada_devuelve_vacio():
    urls, is_video = _parth_image_urls({"type": "video", "images": [], "thumbnail": ""})
    assert urls == []
    assert is_video is True
