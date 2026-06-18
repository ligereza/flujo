"""Tests para flujo.jobs.lifecycle y flujo.jobs.job."""

import shutil
from datetime import date
from pathlib import Path

import pytest

from flujo.jobs.job import create_job, list_jobs, find_job, JobInfo
from flujo.jobs.lifecycle import prepare_job, activate_job, suggest_next_action
from flujo.jobs.brief import (
    Brief,
    EstadoJob,
    Medidas,
    save_brief,
    load_brief,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Crea un repo mínimo con la estructura esperada."""
    (tmp_path / "jobs").mkdir()
    (tmp_path / "projects" / "piezas_vectoriales").mkdir(parents=True)
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    return tmp_path


def test_create_job_creates_structure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    # crear jobs dir manualmente
    (tmp_path / "jobs").mkdir()
    job = create_job("etiquetas acme")
    assert job.exists()
    assert (job / "brief.yaml").exists()
    assert (job / "pedido_original.txt").exists()
    assert (job / "estado.md").exists()
    assert job.name.startswith(date.today().isoformat())


def test_create_job_with_source(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    src = tmp_path / "correo.txt"
    src.write_text("Necesito etiqueta 16.5x6.5 cm de producto Impulso.", encoding="utf-8")
    job = create_job("etiquetas acme", source_path=src)
    assert job.exists()
    content = (job / "pedido_original.txt").read_text(encoding="utf-8")
    assert "Impulso" in content


def test_list_jobs_filters_templates(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    create_job("uno")
    create_job("dos")
    jobs = list_jobs()
    assert len(jobs) == 2
    assert all(isinstance(j, JobInfo) for j in jobs)


def test_find_job_by_partial_name(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    job = create_job("etiquetas-acme-test")
    found = find_job("etiquetas")
    assert found is not None
    assert found.name == job.name


def test_prepare_job_extracts_brief(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    src = tmp_path / "correo.txt"
    src.write_text(
        "Pedido urgente. Etiqueta 16.5x6.5 cm con producto Impulso. Sangrado 3mm.",
        encoding="utf-8",
    )
    job = create_job("etiquetas-acme", source_path=src)
    res = prepare_job(job, run_privacy=True)
    assert res.ok
    assert res.privacy_report is not None
    assert res.privacy_report.exists()
    # brief.yaml debe tener tipo y medida
    brief = load_brief(job / "brief.yaml")
    assert brief.tipo_pieza == "etiqueta"
    assert brief.medidas.ancho_cm == 16.5


def test_suggest_next_action():
    from flujo.jobs.brief import Brief, EstadoJob
    b = Brief(estado=EstadoJob.LISTO_PARA_DISENAR)
    action = suggest_next_action(b)
    assert "activar" in action.lower() or "job-activate" in action


def test_activate_job_creates_project(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    (tmp_path / "projects" / "piezas_vectoriales").mkdir(parents=True)
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas").mkdir(parents=True)

    # Crear job con brief listo
    src = tmp_path / "correo.txt"
    src.write_text("Etiqueta 16.5x6.5 cm con Impulso.", encoding="utf-8")
    job = create_job("etiquetas-acme", source_path=src)
    prepare_job(job, run_privacy=True)

    res = activate_job(job)
    assert res.ok
    assert res.project_path is not None
    assert res.project_path.exists()
    assert (res.project_path / "config.json").exists()
    brief = load_brief(job / "brief.yaml")
    assert brief.estado == EstadoJob.EN_DISENO
