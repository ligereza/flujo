from pathlib import Path

from flujo.comercial.svg_validator import (
    EXPECTED_CONTRAPORTADA_SIZE,
    render_svg_validation_report,
    validate_svg_file,
)


def test_validate_svg_file_ok(tmp_path: Path):
    svg = tmp_path / "ok.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2800" viewBox="0 0 2000 2800">'
        '<g><text x="10" y="20">IMPULSO</text></g></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, expected_size=EXPECTED_CONTRAPORTADA_SIZE)
    assert report["ok"] is True
    assert report["summary"]["width"] == 1181
    assert report["summary"]["height"] == 1654


def test_validate_svg_file_detecta_placeholder_y_tamano(tmp_path: Path):
    svg = tmp_path / "bad.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="200">'
        '<g><text>NOMBRE DEL</text></g></svg>',
        encoding="utf-8",
    )
    report = validate_svg_file(svg, expected_size=EXPECTED_CONTRAPORTADA_SIZE)
    assert report["ok"] is False
    errors = " ".join(report["errors"])
    assert "Tamano inesperado" in errors
    assert "Placeholders" in errors


def test_render_svg_validation_report():
    report = {"ok": True, "errors": [], "warnings": [], "summary": {"path": "x.svg", "width": 1181, "height": 1654}}
    text = render_svg_validation_report(report)
    assert "VALIDACION SVG SUPLEMENTOS RD" in text
    assert "Estado: OK" in text
