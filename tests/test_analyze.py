"""Tests offline para flujo.analyze.colors y flujo.analyze.run.

Usa imagenes PIL minimas en memoria (nada de red, nada de OCR real: el
paso de OCR se mockea para no depender de tesseract instalado).
"""

from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL", reason="Pillow requerido para flujo.analyze")
from PIL import Image  # noqa: E402

import flujo.paths  # noqa: F401
import flujo.analyze.colors as colors_mod
import flujo.analyze.run as run_mod
import flujo.analyze.ocr as ocr_mod


def _make_image(path: Path, size=(20, 20)):
    """Imagen con dos bloques de color solido: mitad roja, mitad azul."""
    img = Image.new("RGB", size, (255, 0, 0))
    w, h = size
    for x in range(w // 2, w):
        for y in range(h):
            img.putpixel((x, y), (0, 0, 255))
    img.save(path, format="JPEG")
    return path


# ---------------- extract_palette ----------------

def test_extract_palette_devuelve_colores_dominantes(tmp_path):
    img_path = _make_image(tmp_path / "input_ig.jpg")
    out = colors_mod.extract_palette(img_path, n_colors=3)

    assert out["source_image"] == "input_ig.jpg"
    assert out["width"] == 20
    assert out["height"] == 20
    assert isinstance(out["colors"], list)
    assert len(out["colors"]) <= 3
    for c in out["colors"]:
        assert c["hex"].startswith("#")
        assert len(c["hex"]) == 7
        assert len(c["rgb"]) == 3
        assert 0 <= c["pct"] <= 1


def test_extract_palette_porcentajes_suman_cercano_a_uno(tmp_path):
    img_path = _make_image(tmp_path / "input_ig.jpg")
    out = colors_mod.extract_palette(img_path, n_colors=5)
    total = sum(c["pct"] for c in out["colors"])
    assert 0.9 <= total <= 1.0


def test_extract_palette_redimensiona_imagenes_grandes(tmp_path):
    img_path = tmp_path / "grande.jpg"
    Image.new("RGB", (400, 100), (10, 20, 30)).save(img_path, format="JPEG")
    out = colors_mod.extract_palette(img_path, n_colors=2)
    # max_side=200 -> se debe reducir manteniendo aspecto (400x100 -> 200x50)
    assert out["width"] == 200
    assert out["height"] == 50


# ---------------- save_palette_preview ----------------

def test_save_palette_preview_crea_png(tmp_path):
    palette = {"colors": [
        {"hex": "#ff0000", "rgb": [255, 0, 0], "pct": 0.5},
        {"hex": "#0000ff", "rgb": [0, 0, 255], "pct": 0.5},
    ]}
    out_path = tmp_path / "sub" / "palette.png"
    ok = colors_mod.save_palette_preview(palette, out_path, width=100, height=20)
    assert ok is True
    assert out_path.exists()
    img = Image.open(out_path)
    assert img.size == (100, 20)


def test_save_palette_preview_sin_colores_devuelve_false(tmp_path):
    ok = colors_mod.save_palette_preview({"colors": []}, tmp_path / "x.png")
    assert ok is False


# ---------------- analyze_project (run.py) ----------------

def _make_project(tmp_path):
    project_dir = tmp_path / "proj1"
    input_dir = project_dir / "input"
    input_dir.mkdir(parents=True)
    _make_image(input_dir / "input_ig.jpg")
    return project_dir


def test_analyze_project_sin_imagen(tmp_path):
    project_dir = tmp_path / "vacio"
    (project_dir / "input").mkdir(parents=True)
    out = run_mod.analyze_project(project_dir)
    assert out["error"] == "no_image_found"


def test_analyze_project_ok_con_ocr_no_disponible(tmp_path, monkeypatch):
    project_dir = _make_project(tmp_path)

    # OCR mockeado: nunca depender de tesseract real instalado
    monkeypatch.setattr(ocr_mod, "run_ocr", lambda image_path: {"available": False, "reason": "mock"})

    out = run_mod.analyze_project(project_dir)

    assert out["status"] == "ok"
    assert "palette" in out
    assert out["palette"]["colors"]
    assert (project_dir / "analysis" / "palette.json").exists()
    assert (project_dir / "analysis" / "palette.png").exists()
    assert out["ocr"]["available"] is False
    assert (project_dir / "analysis" / "ocr_status.json").exists()
    assert out["manifest_updated"] is True

    manifest = run_mod.load_json(project_dir / "manifest.json")
    assert manifest["steps"]["analysis"] == "done"
    assert manifest["analysis"]["ocr_ran"] is False
    assert manifest["analysis"]["palette_colors"]


def test_analyze_project_ocr_con_texto_genera_hints(tmp_path, monkeypatch):
    project_dir = _make_project(tmp_path)

    monkeypatch.setattr(
        ocr_mod, "run_ocr",
        lambda image_path: {"available": True, "text": "evento 12/06 @cuenta_test #fiesta", "chars": 30, "lines": 1},
    )

    out = run_mod.analyze_project(project_dir)

    assert out["ocr"]["chars"] == 30
    assert "hints" in out["ocr"]
    assert (project_dir / "analysis" / "ocr.txt").exists()
    assert (project_dir / "analysis" / "ocr_hints.json").exists()

    manifest = run_mod.load_json(project_dir / "manifest.json")
    assert manifest["analysis"]["ocr_ran"] is True


def test_analyze_project_preserva_manifest_existente(tmp_path, monkeypatch):
    project_dir = _make_project(tmp_path)
    (project_dir / "manifest.json").write_text(
        '{"otro_campo": "preservar", "steps": {"intake": "done"}}', encoding="utf-8"
    )
    monkeypatch.setattr(ocr_mod, "run_ocr", lambda image_path: {"available": False})

    run_mod.analyze_project(project_dir)

    manifest = run_mod.load_json(project_dir / "manifest.json")
    assert manifest["otro_campo"] == "preservar"
    assert manifest["steps"]["intake"] == "done"
    assert manifest["steps"]["analysis"] == "done"


# ---------------- find_latest_flyer ----------------

def test_find_latest_flyer_sin_carpeta(monkeypatch, tmp_path):
    missing = tmp_path / "no_existe"
    import flujo.paths as paths_mod
    monkeypatch.setattr(paths_mod, "flyer_base", lambda: missing)
    assert run_mod.find_latest_flyer() is None


def test_find_latest_flyer_devuelve_mas_reciente(monkeypatch, tmp_path):
    base = tmp_path / "flyers"
    base.mkdir()
    older = base / "2026-01-01_a"
    older.mkdir()
    (older / "manifest.json").write_text("{}", encoding="utf-8")
    newer = base / "2026-02-01_b"
    newer.mkdir()
    (newer / "manifest.json").write_text("{}", encoding="utf-8")
    no_manifest = base / "2026-03-01_sin_manifest"
    no_manifest.mkdir()

    import flujo.paths as paths_mod
    monkeypatch.setattr(paths_mod, "flyer_base", lambda: base)
    latest = run_mod.find_latest_flyer()
    assert latest.name == "2026-02-01_b"
