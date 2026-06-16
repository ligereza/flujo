"""Smoke tests mínimos para flujo."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_jsons_son_validos():
    """Todos los JSONs trackeados deben cargar sin errores."""
    invalidos = []
    for p in ROOT.rglob("*.json"):
        if any(part in p.parts for part in [".git", "salida_generada", "02_editables_svg", "03_final_vectorizado_svg", "04_preview", "05_exports"]):
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            invalidos.append(f"{p}: {e}")
    assert not invalidos, "\n".join(invalidos)


def test_scripts_importan():
    """Los scripts principales deben poder importarse sin errores de sintaxis."""
    scripts = [
        ROOT / "scripts" / "flyer_from_email.py",
        ROOT / "scripts" / "piezas_generar.py",
        ROOT / "scripts" / "flujo_health.py",
        ROOT / "scripts" / "job_from_text.py",
        ROOT / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py",
    ]
    for script in scripts:
        if not script.exists():
            pytest.skip(f"No existe {script}")
        source = script.read_text(encoding="utf-8")
        compile(source, script.name, "exec")


def test_generar_piezas_vectoriales(tmp_path, monkeypatch):
    """El generador de piezas vectoriales produce archivos esperados."""
    import shutil

    cfg = ROOT / "projects" / "piezas_vectoriales" / "etiquetas_ejemplo" / "config.json"
    assert cfg.exists(), "No existe config de ejemplo"

    # Copiar a tmp para no dejar residuos en el repo
    work = tmp_path / "etiquetas_ejemplo"
    shutil.copytree(cfg.parent, work, ignore=shutil.ignore_patterns("salida_generada"))
    out = work / "salida_generada"

    monkeypatch.chdir(ROOT)
    subprocess.run([sys.executable, str(ROOT / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py"), str(work / "config.json")], check=True)

    assert (out / "01_editables_svg").exists()
    assert (out / "02_vectorizados_svg").exists()
    assert (out / "03_preview" / "preview.html").exists()
    assert (out / "04_exports").exists()

    for svg in (out / "02_vectorizados_svg").glob("*.svg"):
        txt = svg.read_text(encoding="utf-8")
        assert "<text" not in txt, f"SVG vectorizado contiene texto vivo: {svg}"


def test_flyer_from_email_detecta_duplicados():
    """El importador de correo detecta duplicados sin crear proyectos nuevos."""
    inbox = ROOT / "inbox" / "correo_prueba.txt"
    if not inbox.exists():
        pytest.skip("No existe inbox de prueba")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "flyer_from_email.py"), str(inbox)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "DUPLICADO" in result.stdout or "Creados: 0" in result.stdout


def test_flyer_create_project(tmp_path, monkeypatch):
    """Crea un proyecto flyer con la estructura esperada."""
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from _common import create_flyer_project

    monkeypatch.chdir(ROOT)
    project = create_flyer_project(tmp_path, "fiesta de prueba", source_type="test")
    assert project.exists()
    assert (project / "manifest.json").exists()
    assert (project / "README.md").exists()
    for folder in ["input", "working", "exports", "refs", "analysis", "ai"]:
        assert (project / folder / ".gitkeep").exists()

    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tool"] == "flyer_eventos"
    assert manifest["source"]["type"] == "test"


def test_flujo_cli():
    """El comando unificado flujo.py responde sin errores."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "flujo.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Comandos disponibles" in result.stdout

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "flujo.py"), "health"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "OK: health check" in result.stdout
