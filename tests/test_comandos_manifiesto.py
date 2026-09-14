#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The CLI as DATA, so a button (or a free agent) can drive it.

`MAPA.md` already carries the command table generated from real CLI
introspection -- but it comes out as markdown, so using it means copy-paste. A
button cannot read prose, and neither can an agent that does not know this
repo. `context/comandos.json` is the same truth in the shape a machine
consumes, generated from the SAME tree, so the two cannot fork.

Two things these tests pin, and both are the lesson of 2026-07-31:

1. **The manifest is generated, never hand-kept.** A second hand-written list
   is how `refutar.py` lost watsonx and how `CLAVES_VISION` swallowed `_motor`:
   a list that stopped matching reality and discarded in silence.
2. **`destructivo: null` means nobody declared it, and that is NOT `false`.**
   Filling an absence with a plausible value is exactly what destroys the field
   that measures it. The first version of this manifest guessed by looking for
   verbs inside the command name; a name does not say what a command does.
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANIFIESTO = RAIZ / "context" / "comandos.json"
GENERADOR = RAIZ / "tools" / "gen_mapa_comandos.py"


def _cargar():
    return json.loads(MANIFIESTO.read_text(encoding="utf-8"))


def test_the_manifest_exists_and_declares_its_format():
    d = _cargar()
    assert d["formato"] == "comandos/1"
    assert d["total"] == len(d["comandos"])
    assert d["total"] > 50, "el CLI real tiene decenas de comandos"


def test_every_command_carries_what_a_button_needs():
    """Name, how to invoke it, what it needs, and whether it is ready. A button
    with only a name is a button that cannot say why it will fail."""
    for c in _cargar()["comandos"]:
        for campo in ("cmd", "invocacion", "desc", "requiere", "estado",
                      "destructivo"):
            assert campo in c, (c.get("cmd"), campo)
        assert c["invocacion"].startswith("py -m flujo ")
        assert c["invocacion"].endswith(c["cmd"])


def test_state_says_ready_or_says_what_is_missing():
    """This is what lets an interface show OBJECTIVES instead of commands: a
    command is `listo`, or it names what it lacks."""
    for c in _cargar()["comandos"]:
        if c["requiere"]:
            assert c["estado"].startswith("falta: ")
            assert c["requiere"] in c["estado"]
        else:
            assert c["estado"] == "listo"


def test_undeclared_destructiveness_is_null_not_false():
    """`false` would claim 'this is safe' about a command nobody classified.
    That is the same defect as a default that fills an absence -- the field
    exists to attribute, and a default destroys it."""
    d = _cargar()
    valores = {str(c["destructivo"]) for c in d["comandos"]}
    assert valores <= {"True", "None"}, valores
    assert any(c["destructivo"] is None for c in d["comandos"]), (
        "si todo estuviera declarado, el null dejaria de existir y habria que "
        "revisar este test -- no borrarlo")
    assert any(c["destructivo"] is True for c in d["comandos"])


def test_the_manifest_is_not_stale_against_the_real_cli():
    """The same `--check` that keeps MAPA.md honest now covers the manifest.
    A manifest nobody checks is documentation, and documentation rots."""
    r = subprocess.run([sys.executable, str(GENERADOR), "--check"],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=str(RAIZ), timeout=300)
    assert r.returncode == 0, (
        "context/comandos.json quedo desfasado del CLI real. "
        "Corre: py tools/gen_mapa_comandos.py\n" + r.stdout + r.stderr)


def test_the_manifest_and_the_table_come_from_one_tree():
    """Two generators is how a hand-written copy goes stale in silence."""
    fuente = GENERADOR.read_text(encoding="utf-8")
    assert "arbol = arbol_cli()" in fuente
    assert "manifiesto(arbol)" in fuente and "render(arbol)" in fuente
