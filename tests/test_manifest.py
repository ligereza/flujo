"""
Tests de src/flujo/manifest.py -- persistencia del manifest de un job (integridad
de archivos). Gap #6. Fija: el merge preserva claves desconocidas del JSON en
disco, el deep-merge de instagram/extracted_info, y que un JSON corrupto no
revienta (ni load ni save).
"""
from __future__ import annotations

from flujo.manifest import load_manifest, save_manifest
from flujo.models import Manifest


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "manifest.json"
    m = Manifest(name="evento X", status="ready")
    save_manifest(p, m)
    got = load_manifest(p)
    assert got.name == "evento X"
    assert got.status == "ready"


def test_save_preserva_claves_desconocidas(tmp_path):
    """Un re-save no debe tirar claves que otro proceso/version dejo en el
    JSON (extra='allow' + merge sobre el dict existente)."""
    import json

    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"name": "orig", "campo_futuro": {"x": 1}}), encoding="utf-8")
    save_manifest(p, Manifest(name="actualizado"))
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["name"] == "actualizado"
    assert data["campo_futuro"] == {"x": 1}   # sobrevive el re-save


def test_save_deep_merge_instagram(tmp_path):
    import json

    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"instagram": {"handle": "@rd", "extra": "keep"}}), encoding="utf-8")
    m = Manifest()
    m.instagram.handle = "@nuevo"
    save_manifest(p, m)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["instagram"]["handle"] == "@nuevo"
    assert data["instagram"]["extra"] == "keep"   # deep-merge, no overwrite total


def test_load_manifest_corrupto_no_revienta(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{ esto no es json valido", encoding="utf-8")
    m = load_manifest(p)          # fallback a Manifest() por defecto
    assert isinstance(m, Manifest)


def test_save_sobre_corrupto_no_revienta(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{{{ corrupto", encoding="utf-8")
    save_manifest(p, Manifest(name="recuperado"))
    m = load_manifest(p)
    assert m.name == "recuperado"


def test_load_inexistente_devuelve_default(tmp_path):
    m = load_manifest(tmp_path / "no_existe.json")
    assert isinstance(m, Manifest)
    assert m.name == ""
