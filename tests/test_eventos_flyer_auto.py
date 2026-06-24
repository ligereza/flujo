from pathlib import Path

import pytest
from PIL import Image

from flujo.eventos.flyer_auto import extract_instagram_shortcode, run_eventos_flyer_auto


def test_extract_instagram_shortcode_post_and_reel():
    assert extract_instagram_shortcode("https://www.instagram.com/p/ABC123/?igsh=x") == "ABC123"
    assert extract_instagram_shortcode("https://instagram.com/reel/XYZ789/") == "XYZ789"


def test_extract_instagram_shortcode_invalid():
    with pytest.raises(ValueError):
        extract_instagram_shortcode("https://example.com/nope")


def test_run_eventos_flyer_auto_copies_input_and_palette(monkeypatch, tmp_path: Path):
    def fake_download(shortcode: str, temp_dir: Path) -> Path:
        img = temp_dir / "downloaded.jpg"
        Image.new("RGB", (20, 20), "purple").save(img)
        return img

    monkeypatch.setattr("flujo.eventos.flyer_auto._download_instagram", fake_download)
    result = run_eventos_flyer_auto("https://www.instagram.com/p/ABC123/", base_dir=tmp_path)

    assert result.ok is True
    assert result.shortcode == "ABC123"
    assert (tmp_path / "input_ig.jpg").exists()
    assert (tmp_path / "palette_ig.png").exists()
    assert (tmp_path / "palette_ig.json").exists()
    assert result.droplet_started is False
    assert result.blender_started is False
    assert result.blender_rendered is False
    assert not (tmp_path / "temp_flyer").exists()


def test_run_eventos_flyer_auto_blender_render_mock(monkeypatch, tmp_path: Path):
    def fake_download(shortcode: str, temp_dir: Path) -> Path:
        img = temp_dir / "downloaded.jpg"
        Image.new("RGB", (20, 20), "red").save(img)
        return img

    def fake_render(blender_exe: str, blender_file: Path, output_path: Path) -> Path:
        output_path.write_bytes(b"render")
        return output_path

    monkeypatch.setattr("flujo.eventos.flyer_auto._download_instagram", fake_download)
    monkeypatch.setattr("flujo.eventos.flyer_auto._render_blender_frame", fake_render)
    (tmp_path / "cartelera.blend").write_bytes(b"blend")

    result = run_eventos_flyer_auto(
        "https://www.instagram.com/p/ABC123/",
        base_dir=tmp_path,
        render_blender=True,
    )

    assert result.ok is True
    assert result.blender_rendered is True
    assert (tmp_path / "preview_cartelera.png").read_bytes() == b"render"
