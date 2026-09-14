"""Tests smoke para flujo v0.16.

Versión ampliada con tests para los nuevos módulos.
"""

import pytest
from pathlib import Path

PIL = pytest.importorskip("PIL", reason="Pillow requerido para flujo.analyze")
from PIL import Image  # noqa: E402


def test_health():
    from flujo.paths import repo_root
    root = repo_root()
    assert root.exists()


def test_version():
    from flujo.version import get_version, get_changelog
    v = get_version()
    assert v.startswith("0.")
    cl = get_changelog()
    assert v in cl


def test_analyze_colors(tmp_path):
    from flujo.analyze.colors import extract_palette

    # Imagen 32x32 generada en memoria con 3 bloques de color solido
    # (rojo / verde / azul), nada de fixture binaria en el repo.
    size = 32
    img = Image.new("RGB", (size, size), (255, 0, 0))
    third = size // 3
    for x in range(size):
        for y in range(size):
            if x < third:
                img.putpixel((x, y), (255, 0, 0))
            elif x < 2 * third:
                img.putpixel((x, y), (0, 255, 0))
            else:
                img.putpixel((x, y), (0, 0, 255))

    test_img = tmp_path / "test_image.png"
    img.save(test_img, format="PNG")

    result = extract_palette(test_img, n_colors=3)
    assert "colors" in result
    assert len(result["colors"]) >= 1


def test_import_cli():
    from flujo.cli import app
    assert app is not None


def test_modules_importable():
    """Verifica que todos los nuevos módulos se pueden importar."""
    import flujo.jobs
    import flujo.jobs.brief
    import flujo.jobs.job
    import flujo.jobs.lifecycle
    import flujo.privacy
    import flujo.privacy.scan
    import flujo.privacy.sanitize
    import flujo.privacy.report
    import flujo.render
    import flujo.render.formats
    import flujo.render.piezas
    import flujo.dashboard
    import flujo.dashboard.scoring
    import flujo.dashboard.report
    import flujo.version
