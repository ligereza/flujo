# tests/test_smoke.py — versión optimizada

import pytest
from pathlib import Path

def test_health():
    from flujo.paths import repo_root
    root = repo_root()
    assert root.exists()

def test_analyze_colors():
    from flujo.analyze.colors import extract_palette

    # Usar imagen pequeña de prueba
    test_img = Path(__file__).parent / "test_image.png"

    if not test_img.exists():
        pytest.skip("test_image.png no encontrado")

    result = extract_palette(test_img, n_colors=3)
    assert "colors" in result
    assert len(result["colors"]) >= 1

def test_import_cli():
    from flujo.cli import app
    assert app is not None
