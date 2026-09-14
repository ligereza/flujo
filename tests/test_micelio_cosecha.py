#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The return leg of the circuit, which was the half that did not exist.

The user's flow, in his words: he goes to a web model with the repo link and
asks for a `semilla`; he deposits it; **if there is a bug the micelio hands him
a `hongo`**; he passes the hongo to the web model, which answers with a
`nutriente`; if the nutriente fixes it, the seed runs and a `fruto` is created.

What existed was a semaphore that printed VERDE or ROJO to a console. That is
useless to the only reader that matters in this loop: a web model with no API,
which gets exactly what a person pastes into a chat and nothing else.

So the hongo is not an error log. It is the envelope that lets a model write
the correction WITHOUT SEEING THE MACHINE -- what was asked, which criteria went
red with their literal message, and the real content of the files the criterion
names. A hongo missing that forces the model to guess, and guessing is what this
circuit exists to remove.
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from flujo import micelio  # noqa: E402


def _semilla(criterio, asunto="hacer una cosa"):
    return {"formato": "micelio/1", "tipo": "semilla", "asunto": asunto,
            "cuerpo": {"objetivo": "que exista"}, "criterio": criterio}


# --------------------------------------------------------------- the two ends

def test_green_grows_a_fruto(tmp_path):
    (tmp_path / "x.txt").write_text("hola", encoding="utf-8")
    s = _semilla([{"tipo": "archivo", "ruta": "x.txt", "min_bytes": 1}])
    r = micelio.cosechar(s, tmp_path)
    assert r["tipo"] == "fruto"
    assert r["cuerpo"]["verde"] is True
    assert r["asunto"].startswith("crecio:")


def test_red_grows_a_hongo(tmp_path):
    s = _semilla([{"tipo": "archivo", "ruta": "no_existe.txt", "min_bytes": 1}])
    r = micelio.cosechar(s, tmp_path)
    assert r["tipo"] == "hongo"
    assert r["asunto"].startswith("no crecio:")


def test_hongo_is_a_declared_type():
    assert "hongo" in micelio.TIPOS


# ------------------------------------------------- what the hongo has to carry

def test_the_hongo_names_which_criterion_failed_and_with_what_message(tmp_path):
    s = _semilla([{"tipo": "archivo", "ruta": "falta.txt", "min_bytes": 10}])
    r = micelio.cosechar(s, tmp_path)
    fallaron = r["cuerpo"]["fallaron"]
    assert len(fallaron) == 1
    assert "falta.txt" in fallaron[0]["detalle"], (
        "un rojo que no dice que se esperaba obliga a adivinar")


def test_the_hongo_keeps_what_already_passed(tmp_path):
    """So the model does not break what works while fixing what does not."""
    (tmp_path / "ok.txt").write_text("hola", encoding="utf-8")
    s = _semilla([{"tipo": "archivo", "ruta": "ok.txt", "min_bytes": 1},
                  {"tipo": "archivo", "ruta": "falta.txt", "min_bytes": 1}])
    r = micelio.cosechar(s, tmp_path)
    assert len(r["cuerpo"]["pasaron"]) == 1
    assert len(r["cuerpo"]["fallaron"]) == 1


def test_the_hongo_carries_the_real_content_of_the_files(tmp_path):
    """Without it the nutriente is written blind."""
    (tmp_path / "m.py").write_text("def normalizar(t):\n    return t\n",
                                   encoding="utf-8")
    s = _semilla([{"tipo": "caso", "modulo": "m.py", "funcion": "normalizar",
                   "entrada": ["A"], "salida": "a"}])
    r = micelio.cosechar(s, tmp_path)
    assert r["tipo"] == "hongo"
    assert "def normalizar" in r["cuerpo"]["lo_que_hay"]["m.py"]


def test_a_file_the_criterion_names_and_does_not_exist_says_so(tmp_path):
    """Absent is a different fact from empty, and filling it with a plausible
    value is what destroys the field that measures it."""
    s = _semilla([{"tipo": "caso", "modulo": "no_esta.py", "funcion": "f",
                   "entrada": [], "salida": 1}])
    r = micelio.cosechar(s, tmp_path)
    assert r["cuerpo"]["lo_que_hay"]["no_esta.py"] == "(no existe)"


def test_the_original_request_travels_with_the_hongo(tmp_path):
    s = _semilla([{"tipo": "archivo", "ruta": "falta.txt", "min_bytes": 1}])
    r = micelio.cosechar(s, tmp_path)
    assert r["cuerpo"]["que_se_pidio"] == {"objetivo": "que exista"}
    assert r["criterio"] == s["criterio"], (
        "el nutriente tiene que volver con el MISMO criterio")


def test_the_hongo_says_what_to_answer_with():
    """The web model does not know this repo. If the envelope does not say
    `nutriente`, it will answer prose."""
    r = micelio.cosechar(_semilla([{"tipo": "archivo", "ruta": "x", "min_bytes": 1}]),
                         Path("."))
    assert "nutriente" in r["cuerpo"]["que_hacer"]


def test_a_seed_with_no_criterion_is_a_hongo_not_a_fruto(tmp_path):
    """Nothing to verify is NOT green -- that would stamp success on work
    nobody measured."""
    s = _semilla([])
    r = micelio.cosechar(s, tmp_path)
    assert r["tipo"] == "hongo"
    assert "no trae criterio" in r["cuerpo"]["fallaron"][0]["detalle"]


def test_a_huge_file_is_cut_and_the_cut_is_declared(tmp_path):
    """A hongo that silently drops the failing file reads as if the failure had
    no context."""
    (tmp_path / "grande.py").write_text("x" * 50_000, encoding="utf-8")
    s = _semilla([{"tipo": "caso", "modulo": "grande.py", "funcion": "f",
                   "entrada": [], "salida": 1}])
    r = micelio.cosechar(s, tmp_path, tope=1000)
    assert r["recortado"]["grande.py"]["bytes_totales"] == 50_000
    assert len(r["cuerpo"]["lo_que_hay"]["grande.py"]) <= 1000


# ------------------------------------------------------------------- the CLI

def test_the_command_exits_1_on_a_hongo_so_a_script_can_gate_on_it(tmp_path):
    ruta = tmp_path / "s.json"
    ruta.write_text(json.dumps(
        _semilla([{"tipo": "archivo", "ruta": "falta.txt", "min_bytes": 1}])),
        encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "flujo", "micelio", "cosechar",
                        str(ruta), "--raiz", str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(RAIZ), timeout=180)
    assert r.returncode == 1
    assert '"tipo": "hongo"' in r.stdout


def test_the_format_tells_the_web_model_about_the_hongo():
    """It is the only instruction that model gets."""
    f = micelio.formato_para_el_modelo()
    assert "hongo" in f
    assert "nutriente" in f
    assert "no lo aflojes" in f, (
        "un criterio ablandado da verde sobre trabajo que no se hizo")
