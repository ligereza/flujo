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


def test_flyer_from_email_crea_proyectos(tmp_path, monkeypatch):
    """El importador crea un proyecto por cada link nuevo."""
    import shutil
    import sys

    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from _common import repo_root

    # Copiar estructura base a tmp para no tocar el repo real
    base = tmp_path / "flyer_eventos"
    base.mkdir()
    monkeypatch.setenv("FLYER_BASE", str(base))

    email = tmp_path / "correo_test.txt"
    email.write_text(
        "Hola, mira estos eventos:\n"
        "https://www.instagram.com/p/TEST001example\n"
        "https://www.instagram.com/reel/TEST002example\n",
        encoding="utf-8",
    )

    # Sobrescribir BASE temporalmente en el script
    script = ROOT / "scripts" / "flyer_from_email.py"
    source = script.read_text(encoding="utf-8").replace(
        "BASE = repo_root() / \"projects\" / \"flyer_eventos\"",
        f"BASE = Path(r'{base.as_posix()}').resolve()",
    )
    temp_script = tmp_path / "flyer_from_email_test.py"
    temp_script.write_text(source, encoding="utf-8")

    # Copiar helper al mismo tmp para que el script lo importe
    shutil.copy(ROOT / "scripts" / "_common.py", tmp_path / "_common.py")

    monkeypatch.chdir(ROOT)
    subprocess.run([sys.executable, str(temp_script), str(email)], check=True)

    proyectos = [p for p in base.iterdir() if p.is_dir()]
    assert len(proyectos) == 2, f"Esperaba 2 proyectos, encontré {len(proyectos)}"
    for p in proyectos:
        assert (p / "manifest.json").exists()


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


def test_flujo_daily_genera_reporte(tmp_path, monkeypatch):
    """flujo_daily.py genera un reporte con los items encontrados."""
    import shutil

    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from _common import repo_root
    from flujo_daily import collect_items, render_report

    # Usar el repo real para datos
    monkeypatch.chdir(ROOT)
    items = collect_items()
    report = render_report(items)
    assert "Prioridad" in report
    assert "Total items" in report
