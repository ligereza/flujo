"""Tests para flujo.dashboard."""

from pathlib import Path
import pytest

from flujo.dashboard import (
    collect_items,
    score_job,
    score_flyer,
    score_pieza,
    render_markdown,
    render_html,
    ItemScore,
    Priority,
)
from flujo.web.hub import build_dashboard_summary


@pytest.fixture
def repo(tmp_path: Path, monkeypatch):
    """Crea un repo con items de prueba."""
    # jobs
    jobs = tmp_path / "jobs" / "2026-06-17_test"
    jobs.mkdir(parents=True)
    (jobs / "brief.yaml").write_text(
        """id: 2026-06-17_test
estado: pendiente_datos
cliente: Acme
proyecto: Test
tipo_pieza: etiqueta
productos: []
pendientes:
  - confirmar medida
""",
        encoding="utf-8",
    )

    # flyer
    flyer = tmp_path / "projects" / "flyer_eventos" / "2026-06-17_test_flyer"
    flyer.mkdir(parents=True)
    (flyer / "manifest.json").write_text(
        '{"tool":"flyer_eventos","name":"test","status":"from_email_pending_download"}',
        encoding="utf-8",
    )

    # pieza
    pieza = tmp_path / "projects" / "piezas_vectoriales" / "test_pieza"
    pieza.mkdir(parents=True)
    (pieza / "config.json").write_text(
        '{"project":{"name":"Test Pieza"}}',
        encoding="utf-8",
    )

    # FIX: patchear ambos módulos donde se importa repo_root
    monkeypatch.setattr("flujo.dashboard.scoring.repo_root", lambda: tmp_path)
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    return tmp_path


def test_collect_items_finds_all_types(repo):
    items = collect_items()
    types = {i.type for i in items}
    assert "job" in types
    assert "flyer" in types
    assert "pieza" in types


def test_collect_items_sorts_by_priority(repo):
    items = collect_items()
    priorities = [i.priority for i in items]
    priority_order = {Priority.ALTA: 0, Priority.MEDIA: 1, Priority.BAJA: 2}
    indices = [priority_order[p] for p in priorities]
    assert indices == sorted(indices)


def test_score_job_high_priority_for_pendiente_datos(repo):
    brief = repo / "jobs" / "2026-06-17_test" / "brief.yaml"
    s = score_job(brief)
    assert s is not None
    assert s.score >= 70


def test_score_flyer_pending_download(repo):
    manifest = repo / "projects" / "flyer_eventos" / "2026-06-17_test_flyer" / "manifest.json"
    s = score_flyer(manifest)
    assert s is not None
    assert s.priority in (Priority.ALTA, Priority.MEDIA)


def test_score_pieza_no_outputs(repo):
    config = repo / "projects" / "piezas_vectoriales" / "test_pieza" / "config.json"
    s = score_pieza(config)
    assert s is not None
    assert s.score >= 50


def test_render_markdown_contains_sections(repo):
    items = collect_items()
    md = render_markdown(items)
    assert "# Daily report" in md
    assert "Total items" in md
    assert "Alta:" in md


def test_render_html_contains_structure(repo):
    items = collect_items()
    html = render_html(items)
    assert "<!doctype html>" in html.lower() or "<html" in html.lower()
    assert "Total items" in html


def test_build_dashboard_summary_counts_priority_groups(repo):
    items = collect_items()
    summary = build_dashboard_summary(items)
    assert summary["total_items"] >= 3
    assert summary["alta"] >= 1
    assert summary["media"] >= 0
    assert summary["baja"] >= 0
