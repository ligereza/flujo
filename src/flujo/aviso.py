#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One line out to the phone, for when nobody is at the machine.

The user's framing, and it is the whole spec: ntfy is for when he is NOT near
the PC. At the keyboard the hub already shows the return code and the stderr;
a notification on top of that would be noise. Away from it, a button that
failed in silence is worse than no button.

So this is deliberately small: no queue, no retry, no state. If
`FLUJO_NTFY_TOPIC` is not set it does nothing and SAYS it did nothing --
returning True on a no-op would be the same defect this repo spent a day on,
a plausible value filling an absence.

MAK has had `ntfy_publish` since July and it carries a gotcha worth reusing
rather than rediscovering: the `Title` header must be ASCII, so a title with
Spanish diacritics has to be folded or the request fails. The message body is
UTF-8 and keeps its accents.
"""
from __future__ import annotations

import os
import unicodedata
import urllib.request

TIEMPO_LIMITE = 10


def _ascii(texto: str, tope: int = 120) -> str:
    """El header Title no acepta acentos. El CUERPO si, y los conserva."""
    plano = unicodedata.normalize("NFKD", texto or "")
    return plano.encode("ascii", "ignore").decode()[:tope]


def avisar(mensaje: str, titulo: str = "flujo", topic: str | None = None) -> bool:
    """Publish one line to ntfy. Returns whether it actually went out.

    Never raises: a notification failing must not take down whatever was being
    reported. And it never blocks for long -- ten seconds is already generous
    for something nobody is waiting on.
    """
    topic = topic or os.environ.get("FLUJO_NTFY_TOPIC", "")
    if not topic:
        return False
    try:
        req = urllib.request.Request(
            "https://ntfy.sh/" + topic,
            data=(mensaje or "").encode("utf-8"),
            headers={"Title": _ascii(titulo) or "flujo",
                     "Priority": "default"},
        )
        urllib.request.urlopen(req, timeout=TIEMPO_LIMITE).read()
        return True
    except Exception:                            # noqa: BLE001 - best effort
        return False


def configurado() -> bool:
    """Whether there is anywhere to send. The hub reports this so the interface
    can say 'nobody will be told' instead of implying someone will."""
    return bool(os.environ.get("FLUJO_NTFY_TOPIC", ""))
