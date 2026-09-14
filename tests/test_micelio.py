#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The envelope that survives losing every API.

The constraint: the strong model goes away and the IBM credit expires within
weeks. What is left is free, weak models running unattended plus ONE capable
model the user can only TALK to, in a browser. The bus between them is a file
that pastes into a chat and pastes back out.

What these tests pin is the single rule that makes the cycle safe: a seed or a
nutrient WITHOUT an acceptance criterion is rejected. An order written by a
model that never ran the code, applied by an organism that does not verify, is
how this repo produced 4.275 inert lines. With a criterion, a weak model does
not need to understand anything -- it iterates until the check goes green, and
what decides is not anybody's opinion.
"""
import json

import pytest

from flujo import micelio


# ------------------------------------------------------------- el contrato

def test_a_seed_without_criterion_is_refused():
    """The rule the whole design rests on."""
    sobre = {"formato": "micelio/1", "tipo": "semilla", "asunto": "algo",
             "cuerpo": {"objetivo": "que quede mas organico"}}
    with pytest.raises(micelio.SobreInvalido) as e:
        micelio.validar(sobre)
    assert "criterio" in str(e.value)
    # and the message says WHY, because it is read by a human or pasted back
    # to the model that wrote it
    assert "cuando parar" in str(e.value)


def test_a_nutrient_without_criterion_is_refused_too():
    sobre = {"formato": "micelio/1", "tipo": "nutriente", "asunto": "arregla el parser",
             "cuerpo": {"que": "el parser"}}
    with pytest.raises(micelio.SobreInvalido):
        micelio.validar(sobre)


def test_a_fruit_needs_no_criterion():
    """A fruit reports, it does not order. Demanding a criterion of it would
    be demanding that the organism prove its own homework."""
    sobre = micelio.fruto("estado", {"registros": 3}, [], [])
    assert micelio.validar(sobre)["tipo"] == "fruto"


def test_the_wrong_format_version_is_named_not_guessed():
    with pytest.raises(micelio.SobreInvalido) as e:
        micelio.validar({"formato": "micelio/9", "tipo": "fruto",
                         "asunto": "x", "cuerpo": {}})
    assert "micelio/1" in str(e.value)


def test_a_criterion_of_an_unknown_kind_is_refused():
    sobre = {"formato": "micelio/1", "tipo": "semilla", "asunto": "x",
             "cuerpo": {}, "criterio": [{"tipo": "que_quede_lindo"}]}
    with pytest.raises(micelio.SobreInvalido) as e:
        micelio.validar(sobre)
    assert "caso" in str(e.value)


# ------------------------------------------------- lo que pega un humano

def test_the_envelope_survives_being_pasted_out_of_a_chat():
    """A web model answers with ```json and a sentence around it no matter how
    firmly it was asked not to. Refusing that would put the friction on the one
    step the user does by hand."""
    pegado = ('Claro, acá va:\n\n```json\n'
              '{"formato":"micelio/1","tipo":"fruto","asunto":"x","cuerpo":{}}\n'
              '```\n\nAvisame si querés más.\n')
    assert micelio.desde_texto(pegado)["tipo"] == "fruto"


def test_conversation_left_inside_says_so_instead_of_crashing():
    with pytest.raises(micelio.SobreInvalido) as e:
        micelio.desde_texto("me parece que el JSON seria algo asi, no?")
    assert "JSON" in str(e.value)


# --------------------------------------------------------- el semaforo

def _semilla(tmp_path, entrada, salida):
    return {
        "formato": "micelio/1", "tipo": "semilla", "asunto": "plegar",
        "cuerpo": {},
        "criterio": [{"nombre": "caso", "tipo": "caso", "modulo": "m.py",
                      "funcion": "f", "entrada": [entrada], "salida": salida}],
    }


def test_the_semaphore_goes_green_when_the_case_passes(tmp_path):
    (tmp_path / "m.py").write_text("def f(x):\n    return x.strip('-')\n",
                                   encoding="utf-8")
    r = micelio.verificar(_semilla(tmp_path, "-hola-", "hola"), tmp_path)
    assert r.verde is True


def test_the_semaphore_goes_red_and_says_what_was_expected(tmp_path):
    """A red that does not say what was expected forces guessing, and guessing
    is exactly what this circuit exists to remove."""
    (tmp_path / "m.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
    r = micelio.verificar(_semilla(tmp_path, "-hola-", "hola"), tmp_path)
    assert r.verde is False
    assert "esperaba 'hola'" in r.checks[0]["detalle"]


def test_code_that_raises_is_a_red_not_a_crash(tmp_path):
    """The code under verification was written by a model. Its exception must
    become a verdict, never take down the organism verifying it."""
    (tmp_path / "m.py").write_text("def f(x):\n    return x.name.value\n",
                                   encoding="utf-8")
    r = micelio.verificar(_semilla(tmp_path, "hola", "hola"), tmp_path)
    assert r.verde is False
    assert "AttributeError" in r.checks[0]["detalle"]


def test_no_criterion_is_not_green(tmp_path):
    """Vacuous truth is the classic way an empty check reads as a pass."""
    r = micelio.verificar({"formato": "micelio/1", "tipo": "fruto",
                           "asunto": "x", "cuerpo": {}}, tmp_path)
    assert r.verde is False


def test_the_file_and_field_criteria_measure_what_they_say(tmp_path):
    (tmp_path / "d.json").write_text(json.dumps({"a": {"b": [1, 2, 3]}}),
                                     encoding="utf-8")
    sobre = {"formato": "micelio/1", "tipo": "semilla", "asunto": "x",
             "cuerpo": {},
             "criterio": [
                 {"tipo": "archivo", "ruta": "d.json", "min_bytes": 5},
                 {"tipo": "campo", "ruta": "d.json", "campo": "a.b", "min": 3},
             ]}
    assert micelio.verificar(sobre, tmp_path).verde is True
    sobre["criterio"][1]["min"] = 4
    assert micelio.verificar(sobre, tmp_path).verde is False


# ------------------------------------------------------------- el fruto

def test_the_fruit_fits_in_a_chat_window_and_declares_what_it_dropped():
    """A fruit that does not fit breaks the cycle on its return trip, and a
    silent truncation reads as 'that was everything'."""
    muchas = [{"id": "pieza-%04d" % i, "texto": "x" * 200} for i in range(200)]
    f = micelio.fruto("volcado", {"registros": 200}, [], muchas)
    assert len(json.dumps(f, ensure_ascii=False).encode("utf-8")) <= micelio.TOPE_FRUTO_BYTES
    assert f["recortado"]["muestras"] > 0
    # what survived is whole: half a sample is a sample that lies
    for m in f["cuerpo"]["muestras"]:
        assert set(m) == {"id", "texto"}


def test_a_small_fruit_declares_nothing_dropped():
    f = micelio.fruto("chico", {"registros": 1}, [], [{"id": "a"}])
    assert f["recortado"] == {}


# ------------------------------------------------------------- la medicion

def test_coverage_makes_the_thin_substrate_visible(tmp_path):
    """The question that had no mechanical answer: which fields have data and
    which do not. Measured on the real fichas the same day: `ocr_texto` empty
    in 76% of 3.138 records."""
    p = tmp_path / "f.jsonl"
    p.write_text("\n".join(json.dumps(
        {"id": str(i), "ocr": "" if i else "hola", "cat": "obra"})
        for i in range(10)), encoding="utf-8")
    medido, anomalias, muestras = micelio.medir_dataset(p)
    assert medido["registros"] == 10
    assert medido["cobertura_pct"]["ocr"] == 10
    assert medido["cobertura_pct"]["cat"] == 100
    assert [a["campo"] for a in anomalias] == ["ocr"]
    # the samples come from the POOR end: an average record teaches nothing
    assert muestras[0]["ocr"] == ""


def test_an_empty_dataset_is_an_anomaly_not_a_clean_report(tmp_path):
    p = tmp_path / "v.jsonl"
    p.write_text("", encoding="utf-8")
    medido, anomalias, _ = micelio.medir_dataset(p)
    assert medido["registros"] == 0
    assert anomalias, "zero records must be reported, never look like success"
