# -*- coding: utf-8 -*-
"""VCD-09: aplicar airdrops por correo autorizaba con el header `From:`.

Del diagnostico de seguridad del 2026-07-27. `check_and_apply_email_airdrops()`
compara UNICAMENTE la direccion del `From:`, descarga un ZIP, lo aplica y
dispara commit/push. `From:` no es una firma: es texto que cualquiera escribe.

Y no la llama nadie -- se busco en todo el repo y no hay comando ni cron que la
invoque. Una mina sin consumidor. Lo proporcional no era inventarle firmas para
algo que no se usa, sino que no pueda dispararse sola.
"""
from __future__ import annotations

import os

from flujo.intake.reception import check_and_apply_email_airdrops


def test_apagada_por_defecto(monkeypatch):
    monkeypatch.delenv("FLUJO_IMAP_AUTOAPLICAR", raising=False)
    # aunque el resto del entorno estuviera puesto, no debe intentar nada
    for v in ("FLUJO_IMAP_HOST", "FLUJO_IMAP_USER", "FLUJO_IMAP_PASSWORD"):
        monkeypatch.setenv(v, "x")
    r = check_and_apply_email_airdrops()
    assert r["ok"] is False
    assert "apagado" in r["error"]


def test_el_error_dice_por_que_y_como(monkeypatch):
    """Una guarda que no explica se retira sin entender que protegia."""
    monkeypatch.delenv("FLUJO_IMAP_AUTOAPLICAR", raising=False)
    e = check_and_apply_email_airdrops()["error"]
    assert "From:" in e and "falsificable" in e
    assert "FLUJO_IMAP_AUTOAPLICAR=1" in e


def test_encenderla_es_explicito(monkeypatch):
    """Con la variable puesta vuelve a su camino normal (y ahi falla por falta
    de credenciales, que es otro error: prueba que la guarda no lo tapa)."""
    monkeypatch.setenv("FLUJO_IMAP_AUTOAPLICAR", "1")
    for v in ("FLUJO_IMAP_HOST", "FLUJO_IMAP_USER", "FLUJO_IMAP_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    r = check_and_apply_email_airdrops()
    assert r["ok"] is False
    assert "apagado" not in r["error"]
    assert "IMAP" in r["error"]
