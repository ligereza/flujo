"""Tests para flujo.intake."""

from pathlib import Path

import pytest

from flujo.intake.email_parser import (
    extract_instagram_links,
    detect_project_type,
    parse_email_content,
    parse_email_file,
)


def test_extract_instagram_links_basic():
    text = """
Hola, mirá esto:
https://www.instagram.com/p/ABC123/
y también:
https://www.instagram.com/reel/XYZ789/
"""
    links = extract_instagram_links(text)
    assert len(links) == 2
    assert "https://www.instagram.com/p/ABC123/" in links
    assert "https://www.instagram.com/reel/XYZ789/" in links


def test_extract_no_links():
    assert extract_instagram_links("Hola mundo") == []


def test_detect_project_type_etiqueta():
    assert detect_project_type("Necesito una etiqueta para producto") == "etiqueta"


def test_detect_project_type_rider():
    assert detect_project_type("Hacer un rider de intervención") == "rider"


def test_detect_project_type_default():
    assert detect_project_type("Hola, ¿qué tal?") == "flyer"


def test_parse_email_content_full():
    text = """
Hola,
necesito una etiqueta 16.5x6.5 cm para producto Impulso.
Links:
https://www.instagram.com/p/ABCDEF/
"""
    res = parse_email_content(text)
    assert res["project_type"] == "etiqueta"
    assert res["link_count"] == 1
    assert "titulo" in res["sections"] or "fecha" in res["sections"] or "medidas" in res["sections"]


def test_parse_email_file(tmp_path: Path):
    f = tmp_path / "correo.txt"
    f.write_text("Necesito una etiqueta para producto Impulso.", encoding="utf-8")
    res = parse_email_file(f)
    assert "project_type" in res
    assert res["project_type"] == "etiqueta"


def test_parse_email_file_missing(tmp_path: Path):
    f = tmp_path / "no_existe.txt"
    res = parse_email_file(f)
    assert "error" in res


def test_detect_private_account():
    assert detect_project_type("Esto es privado") == "flyer"  # no detecta privado como tipo
    from flujo.intake.email_parser import detect_private_account
    assert detect_private_account("El perfil es privado") is True
    assert detect_private_account("Hola mundo") is False
