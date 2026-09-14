import os
import pytest
from unittest.mock import MagicMock

from flujo.intake.reception import check_and_apply_email_airdrops

def test_reception_missing_env(monkeypatch):
    # Aplicar por correo esta apagado por defecto desde VCD-09 (el `From:` es
    # falsificable). Estos dos tests miden el camino normal, asi que lo
    # encienden; que este apagado por defecto lo cubre tests/test_imap_apagado.py
    monkeypatch.setenv("FLUJO_IMAP_AUTOAPLICAR", "1")
    monkeypatch.delenv("FLUJO_IMAP_HOST", raising=False)
    monkeypatch.delenv("FLUJO_IMAP_USER", raising=False)
    monkeypatch.delenv("FLUJO_IMAP_PASSWORD", raising=False)

    res = check_and_apply_email_airdrops()
    assert res["ok"] is False
    assert "Faltan variables" in res["error"]

def test_reception_success_no_mails(monkeypatch):
    monkeypatch.setenv("FLUJO_IMAP_AUTOAPLICAR", "1")
    monkeypatch.setenv("FLUJO_IMAP_HOST", "imap.test.com")
    monkeypatch.setenv("FLUJO_IMAP_USER", "test_user")
    monkeypatch.setenv("FLUJO_IMAP_PASSWORD", "test_pass")

    mock_mail = MagicMock()
    mock_mail.search.return_value = ("OK", [b""])

    import imaplib
    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host: mock_mail)

    res = check_and_apply_email_airdrops()
    assert res["ok"] is True
    assert res["processed"] == 0
    assert "No hay correos" in res["message"] or "No se encontraron" in res["message"]
