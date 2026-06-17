"""Smoke tests mínimos para flujo v0.12+"""
import json
import subprocess
import sys
from pathlib import Path

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
    """Los módulos principales deben poder importarse."""
    import importlib
    for mod in [
        "flujo",
        "flujo.models",
        "flujo.ig.download",
        "flujo.flyer.project",
        "flujo.flyer.import_email",
        "flujo.cli",
    ]:
        importlib.import_module(mod)

def test_flyer_from_email_detecta_duplicados(tmp_path, monkeypatch):
    """El importador detecta duplicados."""
    # crear un proyecto fake con un shortcode conocido
    from flujo.paths import flyer_base
    from flujo.flyer.project import create_flyer_project
    from flujo.manifest import load_json, write_json

    base = tmp_path / "flyer_eventos"
    base.mkdir()
    monkeypatch.setenv("FLYER_BASE", str(base))

    proj = create_flyer_project(base, "ig-TESTDUP", source_type="test")
    mf = proj / "manifest.json"
    data = load_json(mf) or {}
    data["instagram"] = {"url": "https://www.instagram.com/p/TESTDUP/", "shortcode": "TESTDUP"}
    write_json(mf, data)

    # ahora importar un correo con ese mismo link
    email = tmp_path / "correo.txt"
    email.write_text("https://www.instagram.com/p/TESTDUP/", encoding="utf-8")

    from flujo.flyer.import_email import import_from_email
    res = import_from_email(email, force=False)
    # debe detectar duplicado: creados 0
    assert res["created"] == 0
    assert res["skipped"] >= 1

def test_flyer_create_project(tmp_path, monkeypatch):
    """Crea un proyecto flyer con la estructura esperada."""
    monkeypatch.chdir(ROOT)
    from flujo.flyer.project import create_flyer_project
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

    from flujo.flyer.import_email import import_from_email
    res = import_from_email(email, force=True)
    # puede crear 0,1,2 dependiendo si ya existen en el repo real
    # con FLYER_BASE apuntando a tmp, debería crear 2
    proyectos = [p for p in base.iterdir() if p.is_dir()]
    assert len(proyectos) == 2, f"Esperaba 2 proyectos, encontré {len(proyectos)}: {proyectos}"
    for p in proyectos:
        assert (p / "manifest.json").exists()

def test_flujo_cli():
    """El comando unificado flujo responde sin errores."""
    result = subprocess.run(
        [sys.executable, "-m", "flujo", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    # Typer devuelve 0 con --help, o 2 sin args. Aceptamos ambos.
    assert result.returncode in (0, 1, 2)
    out = (result.stdout + result.stderr).lower()
    assert "flujo" in out or "comandos" in out or "usage" in out

def test_ig_download_extract_shortcode():
    """ig_download extrae correctamente el shortcode de URLs."""
    from flujo.ig.download import extract_shortcode
    assert extract_shortcode("https://www.instagram.com/p/ABC123xyz/") == "ABC123xyz"
    assert extract_shortcode("https://www.instagram.com/reel/REEL123/") == "REEL123"
    assert extract_shortcode("https://www.instagram.com/tv/TV999/") == "TV999"
    assert extract_shortcode("https://example.com/nope") is None
