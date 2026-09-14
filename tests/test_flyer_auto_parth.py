# -*- coding: utf-8 -*-
"""Seleccion de imagen desde metadata parth-dl (issue #131: links de video)."""
import pytest

from flujo.eventos.flyer_auto import _parth_pick_image_url

# Forma real capturada del reel DZ3bAdGhp7y (parth-dl 1.1.0, 2026-07-22),
# URLs recortadas: solo importa la estructura.
VIDEO_META = {
    "thumbnail": "https://instagram.fscl4-1.fna.fbcdn.net/v/t51.82787-15/thumb.jpg",
    "duration": 20.014,
    "uploader": "sentirfestival",
    "type": "video",
    "formats": [
        {
            "url": "https://instagram.fscl4-1.fna.fbcdn.net/o1/v/video.mp4",
            "width": 720,
            "height": 1280,
            "format_id": "graphql-video-0",
            "has_audio": True,
        }
    ],
    "images": [],
}


def test_video_usa_thumbnail():
    assert _parth_pick_image_url(VIDEO_META).endswith("thumb.jpg")


def test_carrusel_solo_primera_imagen_dicts():
    meta = {
        "type": "image",
        "thumbnail": "https://cdn/thumb.jpg",
        "images": [{"url": "https://cdn/uno.jpg"}, {"url": "https://cdn/dos.jpg"}],
    }
    assert _parth_pick_image_url(meta) == "https://cdn/uno.jpg"


def test_carrusel_solo_primera_imagen_strings():
    meta = {"images": ["https://cdn/uno.jpg", "https://cdn/dos.jpg"]}
    assert _parth_pick_image_url(meta) == "https://cdn/uno.jpg"


def test_sin_imagen_ni_thumbnail_lanza():
    with pytest.raises(FileNotFoundError):
        _parth_pick_image_url({"type": "video", "images": [], "thumbnail": ""})
