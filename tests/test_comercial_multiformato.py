import json
from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app
from flujo.comercial.multiformato import (
    build_package_documents,
    detect_requested_formats,
    is_multiformat_quote_request,
    write_multiformat_package,
)
from flujo.intake.email_parser import parse_pedido_text
from flujo.jobs.brief import brief_from_text


PEDIDO = (
    "Necesito enviar un brief que explique la estructura imagen / texto de; "
    "flyers, etiquetas, pendones, post de instagram junto con una cotización"
)


def test_detect_multiformat_quote_request():
    assert is_multiformat_quote_request(PEDIDO) is True
    assert detect_requested_formats(PEDIDO) == ["flyer", "etiqueta", "pendon", "post_instagram"]


def test_parse_pedido_text_routes_to_package_quote_tool():
    data = parse_pedido_text(PEDIDO)
    assert data["tipo"] == "paquete_cotizacion"
    assert data["formato"] == "paquete_comercial_multiformato"
    assert data["tool"] == "brief paquete-cotizacion"
    assert data["formatos_detectados"] == ["flyer", "etiqueta", "pendon", "post_instagram"]


def test_brief_from_text_does_not_collapse_multiformat_to_etiqueta():
    brief = brief_from_text(PEDIDO, job_id="demo")
    assert brief.tipo_pieza == "paquete_cotizacion"
    assert set(brief.productos) >= {"flyer", "etiqueta", "pendon", "post_instagram"}


def test_write_multiformat_package_outputs_expected_docs(tmp_path: Path):
    written = write_multiformat_package(tmp_path, PEDIDO, cliente="Cliente Demo")
    expected = {
        "brief_estructura_multiformato.md",
        "tabla_formatos.md",
        "cotizacion_base.md",
        "preguntas_para_cerrar.md",
        "manifest.json",
    }
    assert expected == set(written)
    brief = (tmp_path / "brief_estructura_multiformato.md").read_text(encoding="utf-8")
    quote = (tmp_path / "cotizacion_base.md").read_text(encoding="utf-8")
    assert "Flyer" in brief
    assert "Etiqueta" in brief
    assert "Pendón" in brief
    assert "Post de Instagram" in brief
    assert "A definir" in quote
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cliente"] == "Cliente Demo"


def test_cli_brief_paquete_cotizacion_from_text_file(tmp_path: Path):
    source = tmp_path / "pedido.txt"
    source.write_text(PEDIDO, encoding="utf-8")
    out = tmp_path / "salida"
    result = CliRunner().invoke(app, ["brief", "paquete-cotizacion", str(source), "--output", str(out)])
    assert result.exit_code == 0
    assert (out / "brief_estructura_multiformato.md").exists()
    assert (out / "cotizacion_base.md").exists()


def test_build_package_documents_preserves_flexible_sizes_and_proportions():
    source = "Quiero flyer 20x30 cm, etiqueta 7x5 cm, pendon 1.5x3 m y un post con proporción 4:5."
    docs = build_package_documents(source, cliente="Cliente Demo")
    brief = docs["brief_estructura_multiformato.md"]
    manifest = json.loads(docs["manifest.json"])
    assert "20x30 cm" in brief
    assert "1.5x3 m" in brief
    assert "4:5" in brief
    assert manifest["flexible_specs"][0]["label"] == "flyer"
    assert manifest["flexible_specs"][0]["size"] == "20x30 cm"
