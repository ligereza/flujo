"""Tests para scripts/validate_airdrop.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_airdrop", ROOT / "scripts" / "validate_airdrop.py")
validate_airdrop_mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["validate_airdrop"] = validate_airdrop_mod
SPEC.loader.exec_module(validate_airdrop_mod)


def _messages(findings):
    return "\n".join(f"{f.level} {f.path} {f.message}" for f in findings)


def test_empty_airdrop_fails(tmp_path: Path):
    base = tmp_path / "_airdrop"
    base.mkdir()
    rels, findings = validate_airdrop_mod.validate_airdrop(base)
    assert rels == []
    assert any("ZIP vacío" in f.message for f in findings)


def test_missing_handoff_fails(tmp_path: Path):
    base = tmp_path / "_airdrop"
    (base / "src" / "flujo").mkdir(parents=True)
    (base / "src" / "flujo" / "cli.py").write_text("print('x')\n", encoding="utf-8")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    assert "Falta HANDOFF" in _messages(findings)


def test_valid_airdrop_passes(tmp_path: Path):
    base = tmp_path / "_airdrop"
    base.mkdir()
    (base / "HANDOFF_2026-06-21_test.md").write_text("# Handoff\n", encoding="utf-8")
    (base / "requirements.txt").write_text("rich>=13.0\n", encoding="utf-8")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    assert not [f for f in findings if f.level == "ERROR"]


def test_zero_byte_file_fails(tmp_path: Path):
    base = tmp_path / "_airdrop"
    base.mkdir()
    (base / "HANDOFF_2026-06-21_test.md").write_text("# Handoff\n", encoding="utf-8")
    (base / "empty.txt").write_text("", encoding="utf-8")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    assert "0 bytes" in _messages(findings)


def test_forbidden_generated_files_fail(tmp_path: Path):
    base = tmp_path / "_airdrop"
    (base / "src" / "flujo" / "__pycache__").mkdir(parents=True)
    (base / "HANDOFF_2026-06-21_test.md").write_text("# Handoff\n", encoding="utf-8")
    (base / "src" / "flujo" / "__pycache__" / "x.pyc").write_bytes(b"123")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    text = _messages(findings)
    assert "generada prohibida" in text or ".pyc" in text


def test_markdown_path_fails(tmp_path: Path):
    base = tmp_path / "_airdrop"
    base.mkdir()
    (base / "HANDOFF_2026-06-21_test.md").write_text("# Handoff\n", encoding="utf-8")
    (base / "[cli.py](http:bad)").write_text("x\n", encoding="utf-8")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    assert "Markdown" in _messages(findings)


def test_airdrop_engine_requires_flag(tmp_path: Path):
    base = tmp_path / "_airdrop"
    (base / "src" / "flujo").mkdir(parents=True)
    (base / "HANDOFF_2026-06-21_test.md").write_text("# Handoff\n", encoding="utf-8")
    (base / "src" / "flujo" / "airdrop.py").write_text("# change\n", encoding="utf-8")
    _, findings = validate_airdrop_mod.validate_airdrop(base)
    assert "motor de airdrop" in _messages(findings)
    _, findings_allowed = validate_airdrop_mod.validate_airdrop(base, allow_airdrop_engine=True)
    assert "motor de airdrop" not in _messages(findings_allowed)
