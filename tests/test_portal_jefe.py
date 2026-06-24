from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app
from flujo.jobs.job import create_job


runner = CliRunner()


def test_portal_export_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    out = tmp_path / "portal.html"

    result = runner.invoke(app, ["portal", "--output", str(out), "--repo-url", "https://github.com/ligereza/vibecodeine"])

    assert result.exit_code == 0, result.output
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "Portal de pedidos" in html
    assert "Nuevo pedido" in html
    assert "pedido_diseno.yml" in html


def test_portal_export_with_job(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    job = create_job("Festival Portal")
    brief = job / "brief.yaml"
    text = brief.read_text(encoding="utf-8")
    text = text.replace("estado: borrador", "estado: en_diseno")
    text = text.replace("tipo_pieza:", "tipo_pieza: flyer")
    text = text.replace("proyecto:", "proyecto: Festival Portal")
    brief.write_text(text, encoding="utf-8")
    out = tmp_path / "portal.html"

    result = runner.invoke(app, ["portal", "--output", str(out)])

    assert result.exit_code == 0, result.output
    html = out.read_text(encoding="utf-8")
    assert "Festival Portal" in html
    assert "en_diseno" in html
