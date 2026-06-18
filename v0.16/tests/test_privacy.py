"""Tests para flujo.privacy."""

from pathlib import Path

import pytest

from flujo.privacy import scan_text, sanitize_text, write_report


def test_scan_detects_email():
    text = "Contactame a juan@example.com por favor."
    s = scan_text(text)
    assert "email" in s.matches
    assert "juan@example.com" in s.matches["email"][0]


def test_scan_detects_rut():
    text = "Mi RUT es 12.345.678-9"
    s = scan_text(text)
    assert "rut_chile" in s.matches


def test_scan_detects_phone():
    text = "Llámame al +56 9 1234 5678"
    s = scan_text(text)
    assert "telefono_cl" in s.matches


def test_scan_detects_url():
    text = "Ver más en https://example.com/foo"
    s = scan_text(text)
    assert "url" in s.matches


def test_scan_high_risk_keywords():
    text = "Caso de salud de un menor de edad, diagnóstico médico."
    s = scan_text(text)
    assert s.risk == "alto"
    assert s.requiere_revision_humana
    assert not s.aprobado_para_ia_externa


def test_scan_low_risk_empty():
    s = scan_text("Hola, ¿cómo estás?")
    assert s.risk == "bajo"
    assert s.aprobado_para_ia_externa


def test_sanitize_replaces_email():
    text = "Escribirme a juan@test.com por favor."
    out = sanitize_text(text)
    assert "[EMAIL]" in out
    assert "juan@test.com" not in out


def test_sanitize_replaces_rut():
    text = "RUT: 12.345.678-9"
    out = sanitize_text(text)
    assert "[RUT]" in out


def test_sanitize_replaces_phone():
    text = "Llamar al +56 9 1234 5678"
    out = sanitize_text(text)
    assert "[TELEFONO]" in out


def test_sanitize_writes_file(tmp_path: Path):
    src = tmp_path / "src.txt"
    src.write_text("Email: juan@test.com, RUT: 12.345.678-9", encoding="utf-8")
    out = tmp_path / "out.txt"
    text = src.read_text(encoding="utf-8")
    sanitize_text(text, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "[EMAIL]" in content
    assert "[RUT]" in content


def test_write_report(tmp_path: Path):
    src = tmp_path / "src.txt"
    src.write_text("juan@test.com", encoding="utf-8")
    scan = scan_text(src.read_text(encoding="utf-8"))
    out = tmp_path / "report.md"
    write_report(out, scan, source_name="src.txt")
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "riesgo_privacidad" in content
    assert "email" in content
