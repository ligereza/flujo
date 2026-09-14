"""Validacion del generador .noisette contra un archivo REAL de Chataigne.

Historia: build_chataigne_noisette_experimental se reescribio 4 veces
(v0.48.2-v0.48.5) adivinando el schema, y la regla del repo prohibia tocarlo
de nuevo sin un .noisette real como fixture. 2026-07-16 se encontraron los
archivos reales guardados por el Chataigne 1.10.3 del usuario (C:/IA/prueba*
.noisette, sesion OSC 127.0.0.1:7000 + Sound Card LTC + 2 Actions) y se
copiaron a tests/fixtures/. Estos tests comparan la FORMA (claves,
controlAddress, tipos de item) del output del generador contra ese ground
truth -- los valores (host, puerto, timecodes) pueden variar, la estructura
no.

Fixtures:
- chataigne_1103_real.noisette: sesion completa (OSC + Sound Card + State
  con 2 Actions From Input Value sobre ltcTime -> Custom Message OSC).
- chataigne_1103_real_min.noisette: sesion minima guardada por el mismo
  Chataigne (sanity de claves top-level y metaData).
"""
from __future__ import annotations

import json
from pathlib import Path

from flujo.resolume.automator import (
    ShowCue,
    build_chataigne_noisette_experimental,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REAL = FIXTURES / "chataigne_1103_real.noisette"
REAL_MIN = FIXTURES / "chataigne_1103_real_min.noisette"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _shape(obj: object) -> object:
    """Forma estructural: claves de dicts (recursivo); las listas de
    parametros Chataigne se reducen al set de controlAddress; valores
    escalares se reducen a su tipo."""
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) and "controlAddress" in x for x in obj):
            return sorted(str(x["controlAddress"]) for x in obj)
        return [_shape(x) for x in obj]
    return type(obj).__name__


def _sample_cues(n: int = 2) -> list[ShowCue]:
    return [
        ShowCue(title=f"cue{i}", smpte=f"00:0{i}:00:00", layer=1, clip=i)
        for i in range(1, n + 1)
    ]


def _osc_module(doc: dict) -> dict:
    mods = [m for m in doc["modules"]["items"] if m.get("type") == "OSC"]
    assert mods, "sin modulo OSC"
    return mods[0]


def _actions(doc: dict) -> list[dict]:
    return doc["states"]["items"][0]["processors"]["items"]


def test_fixtures_son_chataigne_1103_reales() -> None:
    for path in (REAL, REAL_MIN):
        doc = _load(path)
        assert doc["metaData"] == {"version": "1.10.3", "versionNumber": 68099}, path


def test_top_level_keys_identicas_al_real() -> None:
    real = _load(REAL)
    gen = build_chataigne_noisette_experimental(_sample_cues())
    assert sorted(gen.keys()) == sorted(real.keys())
    # y el minimo real coincide tambien (no es casualidad de una sesion)
    assert sorted(_load(REAL_MIN).keys()) == sorted(real.keys())


def test_metadata_identica_al_real() -> None:
    real = _load(REAL)
    gen = build_chataigne_noisette_experimental(_sample_cues())
    assert gen["metaData"] == real["metaData"]


def test_modulo_osc_misma_forma_que_el_real() -> None:
    real_osc = _osc_module(_load(REAL))
    gen_osc = _osc_module(build_chataigne_noisette_experimental(_sample_cues()))
    assert _shape(gen_osc) == _shape(real_osc)


def test_action_misma_forma_que_el_real() -> None:
    real_actions = _actions(_load(REAL))
    gen = build_chataigne_noisette_experimental(_sample_cues(2))
    gen_actions = _actions(gen)
    assert len(real_actions) == 2  # la sesion real tiene 2 Actions
    for real_a, gen_a in zip(real_actions, gen_actions):
        assert _shape(gen_a) == _shape(real_a)


def test_action_naming_y_arg_address_como_el_real() -> None:
    """El controlAddress interno del argumento #1 codifica el shortName del
    action (action, action1, ...) -- exactamente como los guarda Chataigne."""
    real = _load(REAL)
    gen = build_chataigne_noisette_experimental(_sample_cues(2))
    for doc in (real, gen):
        actions = _actions(doc)
        for idx, a in enumerate(actions, start=1):
            short = "action" if idx == 1 else f"action{idx - 1}"
            arg = a["consequences"]["items"][0]["command"]["argManager"]["items"][0]
            assert arg["param"]["controlAddress"] == (
                f"/states/state1/processors/{short}/consequencesTRUE/"
                "consequence/command/arguments/#1/#1"
            )


def test_state_parameters_como_el_real() -> None:
    real_state = _load(REAL)["states"]["items"][0]
    gen_state = build_chataigne_noisette_experimental(_sample_cues())["states"]["items"][0]
    real_addrs = sorted(p["controlAddress"] for p in real_state["parameters"])
    gen_addrs = sorted(p["controlAddress"] for p in gen_state["parameters"])
    assert gen_addrs == real_addrs == ["/active", "/miniMode", "/viewUIPosition"]
    assert gen_state["type"] == real_state["type"] == "State"


def test_condicion_ltc_y_comparador_como_el_real() -> None:
    real_cond = _actions(_load(REAL))[0]["conditions"]["items"][0]
    gen_cond = _actions(build_chataigne_noisette_experimental(_sample_cues()))[0][
        "conditions"
    ]["items"][0]
    for cond in (real_cond, gen_cond):
        assert cond["type"] == "From Input Value"
        vals = {p["controlAddress"]: p["value"] for p in cond["parameters"]}
        assert vals["/inputValue"] == "/modules/soundCard/values/ltc/ltcTime"
        comp = {p["controlAddress"]: p["value"] for p in cond["comparator"]["parameters"]}
        assert comp["/comparisonFunction"] == ">="
        assert isinstance(comp["/reference"], float)


def test_roundtrip_json_estable() -> None:
    gen = build_chataigne_noisette_experimental(_sample_cues(3))
    text = json.dumps(gen, ensure_ascii=False, indent=2)
    assert json.loads(text) == gen
