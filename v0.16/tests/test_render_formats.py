"""Tests para flujo.render.formats y flujo.render.piezas."""

import json
import shutil
from pathlib import Path

import pytest

from flujo.render.formats import list_formats, suggest_format, FormatInfo
from flujo.render.piezas import (
    create_project_from_brief,
    validate_config,
    render_config,
    list_projects,
)


@pytest.fixture
def repo_with_index(tmp_path: Path, monkeypatch):
    """Crea un repo con INDEX_FORMATOS.json y plantillas."""
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas").mkdir(parents=True)

    index = {
        "formatos": [
            {
                "id": "etiqueta_horizontal_165x65",
                "tipo": "etiqueta",
                "template": "tools/piezas_vectoriales/plantillas/etiqueta_165x65.json",
                "real_size_cm": {"width": 16.5, "height": 6.5},
                "canvas": {"width": 3300, "height": 1300},
                "descripcion": "Etiqueta horizontal",
            },
            {
                "id": "flyer_a4",
                "tipo": "flyer",
                "template": "tools/piezas_vectoriales/plantillas/flyer_a4.json",
                "real_size_cm": {"width": 21, "height": 29.7},
                "canvas": {"width": 2480, "height": 3508},
                "descripcion": "Flyer A4",
            },
        ]
    }
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas" / "INDEX_FORMATOS.json").write_text(
        json.dumps(index), encoding="utf-8"
    )

    # plantillas
    plantilla_etiqueta = {
        "project": {"name": "etiqueta_base"},
        "canvas": {"width": 3300, "height": 1300, "real_size_cm": {"width": 16.5, "height": 6.5}},
        "documents": [{"id": "doc1", "elements": [{"type": "text", "content": "TITULO PRINCIPAL"}]}],
    }
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas" / "etiqueta_165x65.json").write_text(
        json.dumps(plantilla_etiqueta), encoding="utf-8"
    )

    plantilla_flyer = {
        "project": {"name": "flyer_base"},
        "canvas": {"width": 2480, "height": 3508, "real_size_cm": {"width": 21, "height": 29.7}},
        "documents": [{"id": "doc1", "elements": [{"type": "text", "content": "TITULO PRINCIPAL"}]}],
    }
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas" / "flyer_a4.json").write_text(
        json.dumps(plantilla_flyer), encoding="utf-8"
    )

    (tmp_path / "jobs").mkdir()
    (tmp_path / "projects" / "piezas_vectoriales").mkdir(parents=True)

    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    return tmp_path


def test_list_formats(repo_with_index):
    formats = list_formats()
    assert len(formats) == 2
    assert all(isinstance(f, FormatInfo) for f in formats)


def test_suggest_format_by_size(repo_with_index):
    sugs = suggest_format(16.5, 6.5, "etiqueta")
    assert len(sugs) > 0
    assert "etiqueta" in sugs[0].id or "etiqueta" in sugs[0].tipo


def test_suggest_format_by_type_only(repo_with_index):
    sugs = suggest_format(None, None, "flyer")
    assert any("flyer" in f.id or "flyer" in f.tipo for f in sugs)


def test_create_project_from_brief_uses_template(repo_with_index):
    job = repo_with_index / "jobs" / "2026-06-17_test"
    job.mkdir(parents=True)
    brief_text = """id: 2026-06-17_test
estado: listo_para_disenar
cliente: Acme
proyecto: Etiqueta Acme
tipo_pieza: etiqueta
medidas:
  ancho_cm: 16.5
  alto_cm: 6.5
  orientacion: horizontal
productos:
  - Impulso
pendientes: []
"""
    (job / "brief.yaml").write_text(brief_text, encoding="utf-8")

    project = create_project_from_brief(job / "brief.yaml")
    assert project.exists()
    assert (project / "config.json").exists()
    cfg = json.loads((project / "config.json").read_text(encoding="utf-8"))
    assert cfg["project"]["name"] == "Etiqueta Acme"
    assert cfg["canvas"]["width"] == 3300


def test_validate_config_ok(repo_with_index):
    cfg = {
        "project": {"name": "test"},
        "canvas": {"width": 1000, "height": 1000, "real_size_cm": {"width": 10, "height": 10}},
        "documents": [{"id": "d1", "elements": [{"type": "text", "content": "x"}]}],
    }
    path = repo_with_index / "config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    errors = validate_config(path)
    assert errors == []


def test_validate_config_missing_canvas(repo_with_index):
    cfg = {"documents": [{"elements": []}]}
    path = repo_with_index / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    errors = validate_config(path)
    assert any("canvas" in e for e in errors)


def test_validate_config_missing_documents(repo_with_index):
    cfg = {"canvas": {"width": 1000, "height": 1000}}
    path = repo_with_index / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    errors = validate_config(path)
    assert any("documents" in e for e in errors)


def test_create_project_universal_base_when_no_match(tmp_path, monkeypatch):
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas").mkdir(parents=True)
    # no INDEX_FORMATOS.json → base universal
    (tmp_path / "jobs").mkdir()
    (tmp_path / "projects" / "piezas_vectoriales").mkdir(parents=True)
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)

    job = tmp_path / "jobs" / "2026-06-17_test"
    job.mkdir()
    brief_text = """id: 2026-06-17_test
estado: listo_para_disenar
cliente: Acme
proyecto: Pieza X
tipo_pieza: otro
medidas:
  ancho_cm:
  alto_cm:
productos: []
pendientes: []
"""
    (job / "brief.yaml").write_text(brief_text, encoding="utf-8")

    project = create_project_from_brief(job / "brief.yaml")
    assert project.exists()
    cfg = json.loads((project / "config.json").read_text(encoding="utf-8"))
    assert cfg["project"]["slug"] == "pieza-x"
