"""Tests smoke para flujo v0.16.

Versión ampliada con tests para los nuevos módulos.
"""

import pytest
from pathlib import Path


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


def test_analyze_colors():
    from flujo.analyze.colors import extract_palette
    test_img = Path(__file__).parent / "test_image.png"
    if not test_img.exists():
        pytest.skip("test_image.png no encontrado")
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
