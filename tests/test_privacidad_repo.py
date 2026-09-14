# -*- coding: utf-8 -*-
"""VCD-08: datos reales de infraestructura en un repo PUBLICO.

Del diagnostico de seguridad del 2026-07-27, y de un barrido posterior que
encontro dos casos que el informe no listaba.

Lo que habia:

- las MAC de las dos interfaces de MAK, escritas como constantes en
  `energia.py` Y otra vez en `WAKE_ON_LAN.md` (este segundo no estaba en el
  informe). Una MAC identifica hardware y sirve para reconocimiento dirigido.
- BSSID y SSID de un escaneo REAL en el fixture del plugin de wifi y en un
  comentario del propio plugin: redes de VECINOS, con nombre y BSSID. Un BSSID
  se resuelve a coordenadas en bases publicas de wardriving, asi que eso
  ubicaba la casa del usuario y exponia datos de terceros que nunca dieron
  permiso. Ese segundo caso tampoco estaba en el informe.
- una ruta con el nombre de usuario de Windows en `map_dref.py`.

Este ratchet vigila la clase entera, no los cinco casos: lo que se rompio una
vez se rompe otra, y el informe ya demostro que una lista escrita a mano deja
cosas afuera.

Retiro: cuando exista secret/PII scanning en CI (VCD-07 lo pide).
"""
from __future__ import annotations

import re
import subprocess

from repo_scan import versionable_files
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# MAC que NO son de hardware real y por eso pueden estar en el repo:
#   02:  bit "localmente administrada" -- nunca se asigna a una placa
#   aa:bb:cc / 01:23:45 / bb:cc:dd / 00:00:00 / ff:ff:ff  placeholders clasicos
_MAC_FICTICIA = re.compile(
    r"^(02:|aa:bb|01:23:45|bb:cc:dd|00:00:00|ff:ff:ff|de:ad:be)", re.I)
_MAC = re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.I)
# Nombres ficticios que SI pueden estar: son casos de ataque en tests y
# ejemplos en docs. El ratchet busca el nombre REAL de alguien, no la forma
# de una ruta -- se lo enseno un falso positivo sobre mi propio test del hub.
_USUARIO_WIN = re.compile(r"C:\\+Users\\+(?!<|%|\$|USUARIO|usuario|USER|alguien|fulano|ejemplo|tu-usuario)[A-Za-z0-9_.-]+")

_SALTA = (".min.js", ".lock", ".svg", ".png", ".jpg", ".webp", ".pdf",
          "package-lock.json")


def _archivos():
    nombres = versionable_files()
    if not nombres:
        return []
    for nombre in nombres:
        if nombre.endswith(_SALTA) or "/piel/lib/" in nombre:
            continue
        # `_archive/` es historia congelada que este repo prohibe editar a mano,
        # y el informe es claro en que reescribir git "no despublica copias
        # existentes": limpiarla ahora no recupera nada y si rompe la trazabilidad
        # de por que se archivo algo. El ratchet protege el codigo VIVO, que es
        # donde un dato nuevo puede entrar. Los cuatro casos historicos con el
        # usuario de Windows quedan ahi, sabidos y no ignorados.
        if (nombre.startswith(("_archive/", "docs/recovered/", "context-history/"))
                or "/legacy_" in nombre):
            continue
        # el sanitizador tiene el patron como dato, no como filtracion
        if nombre == "scripts/sanitize_sensitive.py":
            continue
        p = REPO / nombre
        if not p.is_file():
            continue
        try:
            yield nombre, p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


def test_ninguna_mac_de_hardware_real():
    malas = []
    for nombre, texto in _archivos():
        if nombre == Path(__file__).name or nombre.endswith("test_privacidad_repo.py"):
            continue
        for m in _MAC.finditer(texto):
            if not _MAC_FICTICIA.match(m.group(0)):
                malas.append(f"{nombre}: {m.group(0)}")
    assert not malas, (
        "MAC de hardware real en un repo publico. Usa 02:xx (localmente "
        "administrada) para ejemplos, o leela en tiempo de ejecucion del "
        "entorno o de /sys. Encontradas: " + "; ".join(malas[:6]))


def test_ningun_nombre_de_usuario_de_windows_en_una_ruta():
    malas = [f"{n}: {m.group(0)}" for n, t in _archivos()
             for m in _USUARIO_WIN.finditer(t)
             if (not n.endswith("test_privacidad_repo.py")
                 and n != "tests/test_recovered_import.py")]
    assert not malas, (
        "ruta con el nombre de usuario de Windows. Usa Path.home() o una "
        "variable de entorno. Encontradas: " + "; ".join(malas[:6]))


def test_el_fixture_de_wifi_no_trae_redes_de_terceros():
    """El caso que el informe NO listaba: nombres de redes de vecinos.

    No hay forma automatica de saber si un SSID es real, asi que se vigila lo
    concreto que se limpio: los nombres que estaban.
    """
    reales = ("Papucho", "CRISTIAN", "Gyhltda", "dkzEe0UQPJn0l6fhz2lTKRkn1Lf2BD1q")
    malas = [f"{n}: {r}" for n, t in _archivos() for r in reales
             if r in t and not n.endswith("test_privacidad_repo.py")]
    assert not malas, (
        "SSID de redes de terceros tomados de un escaneo real: " + "; ".join(malas))


def test_the_ratchet_sees_new_untracked_files(tmp_path):
    """El hueco medido el 2026-08-21: solo miraba `git ls-files`.

    Un archivo nuevo con un usuario de Windows real pasaba el gate local sin
    ser visto, y recien fallaba cuando ya estaba commiteado. Un ratchet que
    protege contra la entrada de un dato tiene que mirar lo que esta entrando.
    """
    nombres = set(versionable_files())
    assert nombres, "el enumerador no devolvio nada"
    # Lo rastreado sigue estando.
    assert "tests/test_privacidad_repo.py" in nombres
    # Y un archivo nuevo no ignorado aparece.
    nuevo = REPO / "_ratchet_probe_tmp.md"
    try:
        nuevo.write_text("sonda\n", encoding="utf-8")
        assert "_ratchet_probe_tmp.md" in set(versionable_files())
    finally:
        nuevo.unlink(missing_ok=True)
    # Lo ignorado NO aparece: el patron de .gitignore se respeta.
    assert not [n for n in nombres if n.startswith(".venv/")]
