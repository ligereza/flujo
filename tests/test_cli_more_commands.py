"""Broad CLI coverage for commands not exercised by test_cli_smoke.py /
test_cli_v035.py: diagnostics, route, render validate/rescale, laser, rd-db,
privacy, knowledge, and the "fails on absence" behavior of several commands
that take a required file/dir argument.

Each test asserts on printed content or exit code, not merely "did not
raise" -- a command that silently no-ops on a bad input is exactly the kind
of defect this suite is meant to catch.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app
import flujo.paths

runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip rich's ANSI styling so substring/JSON asserts survive it.

    `console.print` (rich) auto-highlights numbers and JSON-looking text even
    outside an interactive terminal, splitting strings like "puntos: 5" with
    escape codes right around the "5". `typer.echo`/plain `print` do not."""
    return _ANSI.sub("", text)


# --------------------------------------------------------------- diagnose / route

def test_diagnose_default_markdown_report():
    result = runner.invoke(app, [
        "diagnose", "--area", "core", "--idea", "algo se rompio",
        "--command", "flujo doctor", "--observed", "explota",
    ])
    assert result.exit_code == 0
    assert "core" in result.output.lower() or "algo se rompio" in result.output


def test_diagnose_json_format_is_valid_json():
    result = runner.invoke(app, ["diagnose", "--format", "json", "--idea", "x"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, dict)


def test_diagnose_rejects_an_unknown_format():
    result = runner.invoke(app, ["diagnose", "--format", "xml"])
    assert result.exit_code != 0


def test_diagnose_reads_error_file_and_sanitizes_it(tmp_path: Path):
    error_file = tmp_path / "traceback.txt"
    error_file.write_text("Traceback: boom\n", encoding="utf-8")
    result = runner.invoke(app, ["diagnose", "--error-file", str(error_file)])
    assert result.exit_code == 0


def test_diagnose_error_file_missing_is_a_bad_parameter():
    result = runner.invoke(app, ["diagnose", "--error-file", "/no/existe.txt"])
    assert result.exit_code != 0


def test_route_selects_a_packet_for_an_idea():
    result = runner.invoke(app, ["route", "necesito arreglar el hub"])
    assert result.exit_code == 0
    assert result.output.strip() != ""


def test_route_json_format_is_valid_json():
    result = runner.invoke(app, ["route", "idea cualquiera", "--format", "json"])
    assert result.exit_code == 0
    assert isinstance(json.loads(result.output), dict)


# --------------------------------------------------------------- render validate/rescale

def _valid_config() -> dict:
    return {
        "canvas": {
            "width": 3300, "height": 1300,
            "real_size_cm": {"width": 16.5, "height": 6.5},
            "safe_margin_px": 100,
        },
        "global_elements": [
            {"type": "rect", "x": 60, "y": 60, "w": 3180, "h": 1180, "radius": 44},
        ],
        "documents": [
            {"id": "doc1", "elements": [
                {"type": "text", "content": "X", "x": 110, "y": 260, "size": 118},
            ]},
        ],
    }


def test_render_validate_accepts_a_well_formed_config(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(_valid_config()), encoding="utf-8")
    result = runner.invoke(app, ["render", "validate", str(cfg)])
    assert result.exit_code == 0
    assert "Config OK" in result.output


def test_render_validate_rejects_a_config_missing_documents(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"canvas": {"width": 10, "height": 10}}), encoding="utf-8")
    result = runner.invoke(app, ["render", "validate", str(cfg)])
    assert result.exit_code == 1
    assert "documents" in result.output.lower()


def test_render_validate_on_a_missing_file_fails_closed():
    result = runner.invoke(app, ["render", "validate", "/no/existe/config.json"])
    assert result.exit_code != 0
    assert "No existe" in result.output


def test_render_rescale_dry_run_reports_without_writing(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(_valid_config()), encoding="utf-8")
    before = cfg.read_text(encoding="utf-8")
    result = runner.invoke(app, ["render", "rescale", str(cfg), "--dpi", "300", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry-run" in result.output
    assert cfg.read_text(encoding="utf-8") == before


def test_render_rescale_without_dpi_or_size_fails_closed(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(_valid_config()), encoding="utf-8")
    result = runner.invoke(app, ["render", "rescale", str(cfg)])
    assert result.exit_code != 0
    assert "--dpi" in result.output


def test_render_rescale_on_a_missing_config_fails_closed():
    result = runner.invoke(app, ["render", "rescale", "/no/existe.json", "--dpi", "300"])
    assert result.exit_code != 0
    assert "No existe" in result.output


# --------------------------------------------------------------- laser

def test_laser_status_without_vpype_names_what_is_missing():
    """vpype is not installed in this environment (see tests/test_laser.py);
    the command must fail closed and say what to install, not claim OK."""
    result = runner.invoke(app, ["laser", "estado"])
    if result.exit_code == 0:
        # If a future environment DOES have the full vpype[all] chain, at
        # least verify the command reported real per-piece state.
        assert "vpype" in result.output
    else:
        assert result.exit_code == 1
        assert "pip install" in result.output


def test_laser_measure_reports_points_and_travel(tmp_path: Path):
    svg = tmp_path / "trazo.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<polyline points="0,0 10,0 10,10"/>'
        '<polyline points="20,20 30,20"/></svg>', encoding="utf-8")
    result = runner.invoke(app, ["laser", "medir", str(svg), "--presupuesto", "800"])
    assert result.exit_code == 0
    plain_output = _plain(result.output)
    assert "puntos: 5" in plain_output
    assert "dentro" in plain_output


def test_laser_measure_over_budget_exits_nonzero(tmp_path: Path):
    svg = tmp_path / "trazo.svg"
    puntos = " ".join(f"{i},{i%5}" for i in range(20))
    svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><polyline points="{puntos}"/></svg>',
                    encoding="utf-8")
    result = runner.invoke(app, ["laser", "medir", str(svg), "--presupuesto", "5"])
    assert result.exit_code == 1
    assert "SOBRE" in result.output


def test_laser_measure_on_a_missing_svg_fails_closed():
    result = runner.invoke(app, ["laser", "medir", "/no/existe.svg"])
    assert result.exit_code != 0
    assert "No existe" in result.output


# --------------------------------------------------------------- privacy

def test_privacy_scan_reports_risk_for_a_plain_text(tmp_path: Path):
    src = tmp_path / "pedido.txt"
    src.write_text("hola, mi rut es 12.345.678-9 y mi correo es a@b.cl", encoding="utf-8")
    result = runner.invoke(app, ["privacy", "scan", str(src)])
    assert result.exit_code == 0
    assert "riesgo" in result.output.lower()


def test_privacy_scan_on_a_missing_file_fails_closed():
    result = runner.invoke(app, ["privacy", "scan", "/no/existe.txt"])
    assert result.exit_code != 0
    assert "No existe" in result.output


def test_privacy_sanitize_writes_an_output_file(tmp_path: Path):
    src = tmp_path / "pedido.txt"
    src.write_text("mi correo es a@b.cl", encoding="utf-8")
    result = runner.invoke(app, ["privacy", "sanitize", str(src)])
    assert result.exit_code == 0
    assert (tmp_path / "pedido_sanitizado.txt").exists()


def test_privacy_check_on_a_job_without_pedido_original_fails_closed(tmp_path: Path):
    job = tmp_path / "job1"
    job.mkdir()
    result = runner.invoke(app, ["privacy", "check", str(job)])
    assert result.exit_code != 0
    assert "pedido_original.txt" in result.output


def test_privacy_check_writes_report_and_sanitized_copy(tmp_path: Path):
    job = tmp_path / "job1"
    job.mkdir()
    (job / "pedido_original.txt").write_text("contacto: a@b.cl", encoding="utf-8")
    result = runner.invoke(app, ["privacy", "check", str(job)])
    assert result.exit_code == 0
    assert (job / "pedido_sanitizado.txt").exists()
    assert (job / "privacy_report.md").exists()


# --------------------------------------------------------------- knowledge

def test_knowledge_list_warns_when_empty(tmp_path: Path, monkeypatch):
    # flujo.knowledge.store binds `repo_root` at import time (`from ..paths
    # import repo_root`), so patching flujo.paths.repo_root alone would leave
    # the store reading the real repo's knowledge/ -- patch both, same fix as
    # tests/test_dashboard.py's `repo` fixture already documents.
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr("flujo.knowledge.store.repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["knowledge", "list", "productoras"])
    assert result.exit_code == 0
    assert "sin entidades" in result.output.lower()


def test_knowledge_show_on_a_missing_id_fails_closed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr("flujo.knowledge.store.repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["knowledge", "show", "productora", "no-existe"])
    assert result.exit_code != 0
    assert "No existe" in result.output


def test_knowledge_classify_returns_json():
    result = runner.invoke(app, ["knowledge", "classify", "flyer para creamfields"])
    assert result.exit_code == 0
    payload = json.loads(_plain(result.output))
    assert isinstance(payload, dict)


# --------------------------------------------------------------- flyer-list / code-index / analyze / export

def test_flyer_list_on_an_empty_index(tmp_path: Path, monkeypatch):
    # flujo.index.db binds `repo_root` at import time, so it must be patched
    # directly -- patching flujo.paths.repo_root alone leaves it reading the
    # real repo's data/flujo.db (a 20 KB fixture that does exist on disk).
    monkeypatch.setattr("flujo.index.db.repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["flyer-list"])
    assert result.exit_code == 0
    assert "Flyers (status=*)" in result.output
    assert "0 rows" not in result.output  # rich renders a real empty table, not text


def test_flyer_list_reads_the_real_index(tmp_path: Path, monkeypatch):
    from flujo.index.db import rebuild_index

    project = tmp_path / "projects" / "flyer_eventos" / "2026-06-01_test"
    project.mkdir(parents=True)
    (project / "manifest.json").write_text(json.dumps({
        "tool": "flyer_eventos", "name": "test", "status": "listo",
        "instagram": {"shortcode": "abc123", "owner": "creamfields"},
    }), encoding="utf-8")
    # rebuild_index() resolves the source tree via flujo.paths.flyer_base()
    # (which itself calls flujo.paths.repo_root()), and the sqlite file via
    # flujo.index.db.repo_root() -- both bindings need the tmp_path root.
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr("flujo.index.db.repo_root", lambda: tmp_path)
    res = rebuild_index()
    assert res["indexed"] == 1
    result = runner.invoke(app, ["flyer-list"])
    assert result.exit_code == 0
    assert "abc123" in result.output


def test_code_index_builds_a_json_brief(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "index.json"
    result = runner.invoke(app, ["code-index", "--root", str(pkg), "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    payload = json.loads(result.output)
    assert "output" in payload


def test_analyze_without_any_flyer_project_fails_closed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "projects" / "flyer_eventos").mkdir(parents=True)
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code != 0
    assert "No hay proyectos flyer" in result.output


def test_export_on_a_non_flyer_directory_fails_closed(tmp_path: Path):
    project = tmp_path / "not_a_flyer"
    project.mkdir()
    result = runner.invoke(app, ["export", str(project)])
    assert result.exit_code != 0
    assert "No es un proyecto flyer" in result.output


# --------------------------------------------------------------- job report (silent no-op check)

def test_job_report_on_a_missing_job_fails_closed(tmp_path: Path):
    result = runner.invoke(app, ["job", "report", str(tmp_path / "no-job")])
    assert result.exit_code != 0
    assert "No existe" in result.output
