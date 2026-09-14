"""Signed airdrops (VCD-09 close): manifest + detached HMAC signature.

The mail path used to authorize by comparing the forgeable `From:` header and
then apply + push code. The fix is a signed artifact plus explicit human
approval:

- `flujo airdrop sign` writes a deterministic SHA-256 manifest and a detached
  HMAC-SHA256 signature (key from FLUJO_AIRDROP_HMAC_KEY).
- With NO key configured, apply/dry-run behave exactly as before.
- With the key configured, apply refuses unsigned or tampered payloads naming
  the exact file and reason; `--allow-unsigned` is the documented HUMAN
  override, and the IMAP autoapply path never uses it.
"""

from __future__ import annotations

import inspect

import pytest
from typer.testing import CliRunner

import flujo.airdrop as airdrop
import flujo.paths  # noqa: F401 -- monkeypatch("flujo.paths.repo_root") needs the submodule imported
from flujo.cli import app

runner = CliRunner()

KEY_ENV = "FLUJO_AIRDROP_HMAC_KEY"


def _patch_root(monkeypatch, root):
    monkeypatch.setattr(airdrop, "repo_root", lambda: root)
    monkeypatch.setattr("flujo.paths.repo_root", lambda: root)


def _payload(root):
    """A minimal valid-looking payload with two files."""
    base = root / "_airdrop"
    (base / "docs").mkdir(parents=True)
    (base / "docs" / "nota.md").write_text("contenido original", encoding="utf-8")
    (base / "docs" / "registro.txt").write_text("contenido de prueba", encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# Signing: key required, deterministic manifest.
# ---------------------------------------------------------------------------

def test_sign_requires_key(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv(KEY_ENV, raising=False)
    _payload(tmp_path)
    with pytest.raises(RuntimeError) as exc:
        airdrop.sign_airdrop()
    assert KEY_ENV in str(exc.value)


def test_sign_requires_payload(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    with pytest.raises(RuntimeError):
        airdrop.sign_airdrop()


def test_manifest_and_signature_are_deterministic(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)

    m1, s1 = airdrop.sign_airdrop()
    first_manifest = m1.read_bytes()
    first_sig = s1.read_text(encoding="ascii")

    m2, s2 = airdrop.sign_airdrop()
    assert m2.read_bytes() == first_manifest, "same payload must give same manifest bytes"
    assert s2.read_text(encoding="ascii") == first_sig, "same payload must give same signature"


def test_verify_roundtrip_ok(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)
    airdrop.sign_airdrop()
    assert airdrop.verify_airdrop() == []


# ---------------------------------------------------------------------------
# Tamper detection: the refusal names the exact file.
# ---------------------------------------------------------------------------

def test_tampered_file_is_named(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    base = _payload(tmp_path)
    airdrop.sign_airdrop()

    # flip one byte of one payload file
    target = base / "docs" / "nota.md"
    raw = bytearray(target.read_bytes())
    raw[0] ^= 0x01
    target.write_bytes(bytes(raw))

    problems = airdrop.verify_airdrop()
    assert len(problems) == 1
    assert "docs/nota.md" in problems[0]
    assert "no coincide" in problems[0]


def test_tampered_payload_refuses_apply_and_applies_nothing(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    base = _payload(tmp_path)
    airdrop.sign_airdrop()
    (base / "docs" / "nota.md").write_text("adulterado", encoding="utf-8")

    with pytest.raises(airdrop.AirdropSignatureError) as exc:
        airdrop.apply_airdrop()
    assert "docs/nota.md" in str(exc.value)
    assert not (tmp_path / "docs" / "nota.md").exists(), "refusal must happen before any copy"
    assert not (tmp_path / "_airdrop_backups").exists()


def test_extra_unsigned_file_is_named(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    base = _payload(tmp_path)
    airdrop.sign_airdrop()
    (base / "docs" / "colado.md").write_text("no firmado", encoding="utf-8")

    problems = airdrop.verify_airdrop()
    assert any("docs/colado.md" in p and "sin firmar" in p for p in problems)


def test_wrong_key_is_rejected(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-a")
    _payload(tmp_path)
    airdrop.sign_airdrop()
    monkeypatch.setenv(KEY_ENV, "clave-b")
    problems = airdrop.verify_airdrop()
    assert len(problems) == 1
    assert "firma HMAC" in problems[0]


# ---------------------------------------------------------------------------
# Missing manifest, in both modes.
# ---------------------------------------------------------------------------

def test_missing_manifest_with_key_refuses_apply(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)

    problems = airdrop.verify_airdrop()
    assert any(airdrop.SIGNED_MANIFEST_NAME in p for p in problems)

    with pytest.raises(airdrop.AirdropSignatureError):
        airdrop.apply_airdrop()
    assert not (tmp_path / "docs" / "nota.md").exists()


def test_missing_manifest_without_key_applies_like_today(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv(KEY_ENV, raising=False)
    _payload(tmp_path)

    changes = airdrop.apply_airdrop()
    assert {c["rel"] for c in changes} == {
        "docs/nota.md", "docs/registro.txt",
    }
    assert (tmp_path / "docs" / "nota.md").read_text(encoding="utf-8") == "contenido original"


def test_no_key_dry_run_and_scan_unchanged(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv(KEY_ENV, raising=False)
    _payload(tmp_path)
    assert airdrop.apply_airdrop(dry_run=True) == airdrop.scan_airdrop()
    assert not (tmp_path / "docs" / "nota.md").exists()


def test_human_override_applies_unsigned_with_key(tmp_path, monkeypatch):
    """The documented human approval: a person typing --allow-unsigned."""
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)
    changes = airdrop.apply_airdrop(allow_unsigned=True)
    assert changes
    assert (tmp_path / "docs" / "nota.md").exists()


def test_signature_artifacts_are_never_applied_as_payload(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)
    airdrop.sign_airdrop()

    rels = {c["rel"] for c in airdrop.scan_airdrop()}
    assert airdrop.SIGNED_MANIFEST_NAME not in rels
    assert airdrop.SIGNATURE_NAME not in rels

    airdrop.apply_airdrop()
    assert not (tmp_path / airdrop.SIGNED_MANIFEST_NAME).exists()
    assert not (tmp_path / airdrop.SIGNATURE_NAME).exists()


# ---------------------------------------------------------------------------
# CLI: sign / verify, loud failure, exit codes.
# ---------------------------------------------------------------------------

def test_cli_sign_then_verify_ok(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)

    result = runner.invoke(app, ["airdrop", "sign"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["airdrop", "verify"])
    assert result.exit_code == 0, result.output
    assert "2" in result.output  # 2 archivos verificados


def test_cli_verify_fails_loud_naming_the_file(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    base = _payload(tmp_path)
    airdrop.sign_airdrop()
    (base / "docs" / "nota.md").write_text("adulterado", encoding="utf-8")

    result = runner.invoke(app, ["airdrop", "verify"])
    assert result.exit_code == 1, result.output
    assert "docs/nota.md" in result.output


def test_cli_sign_without_key_fails(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv(KEY_ENV, raising=False)
    _payload(tmp_path)
    result = runner.invoke(app, ["airdrop", "sign"])
    assert result.exit_code == 1, result.output
    assert KEY_ENV in result.output


# ---------------------------------------------------------------------------
# IMAP autoapply wiring: the mail path demands a VALID signature, always.
# ---------------------------------------------------------------------------

def test_imap_gate_refuses_without_key(tmp_path, monkeypatch):
    from flujo.intake.reception import _signed_airdrop_gate

    _patch_root(monkeypatch, tmp_path)
    monkeypatch.delenv(KEY_ENV, raising=False)
    _payload(tmp_path)
    error = _signed_airdrop_gate()
    assert error is not None and KEY_ENV in error


def test_imap_gate_refuses_unsigned_payload(tmp_path, monkeypatch):
    from flujo.intake.reception import _signed_airdrop_gate

    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)
    error = _signed_airdrop_gate()
    assert error is not None and airdrop.SIGNED_MANIFEST_NAME in error


def test_imap_gate_accepts_valid_signature(tmp_path, monkeypatch):
    from flujo.intake.reception import _signed_airdrop_gate

    _patch_root(monkeypatch, tmp_path)
    monkeypatch.setenv(KEY_ENV, "clave-de-prueba")
    _payload(tmp_path)
    airdrop.sign_airdrop()
    assert _signed_airdrop_gate() is None


def test_imap_path_never_uses_the_human_override():
    """--allow-unsigned is a person typing it; automation must not know it."""
    from flujo.intake import reception

    source = inspect.getsource(reception)
    # the flag may appear in prose (comments/docstrings) but never as a code
    # literal that could reach the apply command line
    assert '"--allow-unsigned"' not in source
    assert "'--allow-unsigned'" not in source
    assert "allow_unsigned=True" not in source
