"""Tests for the hand-rolled no-PyYAML fallback parser in src/flujo/dashboard/scoring.py.

_try_yaml uses real PyYAML (installed in this dev/CI env, so it is never exercised
in its ImportError branch). _read_brief_simple / _coerce are the fallback path that
only runs in an environment without PyYAML -- never exercised by score_job() in CI.
Per task instructions we call the PRIVATE fallback functions DIRECTLY so this fallback
path actually gets test coverage, and we compare its output against _try_yaml (real
PyYAML) on the same text to pin down where the two agree.
"""

from __future__ import annotations

import pytest

from flujo.dashboard.scoring import _coerce, _read_brief_simple, _try_yaml


# ---------------------------------------------------------------------------
# _coerce
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("True", True),
        ("yes", True),
        ("si", True),
        ("sí", True),
        ("false", False),
        ("False", False),
        ("no", False),
    ],
)
def test_coerce_bool_words(raw, expected):
    assert _coerce(raw) is expected


def test_coerce_int():
    assert _coerce("42") == 42
    assert isinstance(_coerce("42"), int)


def test_coerce_comma_decimal_float():
    # Spanish-locale style decimal comma must be normalized to a dot and parsed as float.
    assert _coerce("3,5") == pytest.approx(3.5)
    assert isinstance(_coerce("3,5"), float)


def test_coerce_dot_decimal_float():
    assert _coerce("3.5") == pytest.approx(3.5)


def test_coerce_plain_string_strips_quotes():
    assert _coerce('"hola mundo"') == "hola mundo"
    assert _coerce("'hola'") == "hola"
    assert _coerce("hola") == "hola"


def test_coerce_empty_string():
    assert _coerce("") == ""


# ---------------------------------------------------------------------------
# _read_brief_simple vs _try_yaml (real PyYAML) -- must agree on simple briefs
# ---------------------------------------------------------------------------

SIMPLE_BRIEF = """estado: listo_para_disenar
cliente: Bar Norte
"""


def test_read_brief_simple_matches_yaml_on_flat_keys():
    simple = _read_brief_simple(SIMPLE_BRIEF)
    real = _try_yaml(SIMPLE_BRIEF)
    assert real is not None, "PyYAML must be installed in this dev/CI env for this comparison"
    assert simple == real
    assert simple["estado"] == "listo_para_disenar"
    assert simple["cliente"] == "Bar Norte"


NESTED_BRIEF = """estado: en_diseno
contenido:
  texto_aprobado: true
  version: 2
"""


def test_read_brief_simple_matches_yaml_on_one_level_nesting():
    simple = _read_brief_simple(NESTED_BRIEF)
    real = _try_yaml(NESTED_BRIEF)
    assert real is not None
    assert simple == real
    assert simple["contenido"]["texto_aprobado"] is True
    assert simple["contenido"]["version"] == 2


COMMENTS_AND_BLANKS_BRIEF = """# comentario inicial
estado: borrador

# otro comentario
cliente: Bar Sur
"""


def test_read_brief_simple_ignores_comments_and_blank_lines():
    simple = _read_brief_simple(COMMENTS_AND_BLANKS_BRIEF)
    real = _try_yaml(COMMENTS_AND_BLANKS_BRIEF)
    assert real is not None
    assert simple == real


# ---------------------------------------------------------------------------
# REAL BUG: multi-line YAML list items ("key:\n  - item") are silently dropped
# by _read_brief_simple. Root cause in src/flujo/dashboard/scoring.py:
#
#   if indent == 0:
#       current_section = None
#       current_list = None
#       if val == "":
#           current_section = key
#           data[key] = {}          # <-- list keys land here as an empty dict
#       else:
#           data[key] = _coerce(val)
#           if key in ("productos", "pendientes", "posibles_formatos"):
#               current_list = key   # <-- only reachable when val != "", i.e.
#                                     #     "pendientes: something" on one line,
#                                     #     which never happens for a real
#                                     #     multi-line YAML list.
#
# Standard YAML lists are written as:
#   pendientes:
#     - falta logo
#     - falta texto
# For that shape, "pendientes:" has val == "", so current_list is NEVER set,
# and the "- " lines are skipped by:
#   if content.startswith("- ") and current_list:
# leaving data["pendientes"] == {} (empty dict) instead of a populated list.
#
# Impact: if this fallback path is ever exercised (PyYAML missing), score_job()
# reads `pendientes = data.get("pendientes", []) or []` -> {} is falsy -> treated
# as "no pendientes", silently under-scoring jobs that do have pending items.
# ---------------------------------------------------------------------------

LIST_BRIEF = """estado: listo_para_disenar
pendientes:
  - falta logo
  - falta texto
"""


# REGRESION: el fallback _read_brief_simple tiraba las listas YAML multi-linea
# (`key:` + `- item`) porque current_list solo se seteaba en la rama val != ''.
# Arreglado 2026-07-17 (scoring.py, rama val=='' + key de lista -> lista). Este
# test fija que no vuelva: la ruta fallback (sin PyYAML, el .exe) parsea igual
# que _try_yaml.
def test_read_brief_simple_parses_multiline_list_like_yaml():
    simple = _read_brief_simple(LIST_BRIEF)
    real = _try_yaml(LIST_BRIEF)
    assert real is not None
    assert real["pendientes"] == ["falta logo", "falta texto"]
    assert simple == real
