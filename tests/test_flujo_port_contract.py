"""Ratchets for the FLUJO port contract and for packaging portability.

Two defects are pinned here.

The first: ``run_server`` and ``launch`` decided whether to hunt for a free
port by comparing the requested port against the default, so an explicit
``--port 8765`` was indistinguishable from no flag at all and got moved to
8766 in silence.  The declared port never bound and the surface answered
somewhere else.  Auto-detection is now opt-in through ``auto_port``.

The second: the editable install on this box records
``file:///home/mak/flujo`` as its source, so ``flujo.__file__`` resolves
through the compatibility adapter.  That is a property of where ``pip
install -e`` was run, not of the packaging metadata -- and this file pins the
metadata so it stays that way.  If packaging ever hard-codes a box path,
FLUJO stops being portable and this test says so.
"""
from __future__ import annotations

import ast
import inspect
import json
import socket
from pathlib import Path

from flujo.web import hub


ROOT = Path(__file__).resolve().parents[1]


def test_contract_port_matches_the_branch_profile():
    profile = json.loads((ROOT / "branch_profile.json").read_text(encoding="utf-8"))
    declared = profile.get("hub", {}).get("default_port")
    assert hub.CONTRACT_PORT == 8765
    assert declared == hub.CONTRACT_PORT, (
        "the port the code contracts for and the port branch_profile.json "
        "declares must be the same number"
    )


def test_auto_port_is_opt_in_on_both_entrypoints():
    for function in (hub.run_server, hub.launch):
        signature = inspect.signature(function)
        assert "auto_port" in signature.parameters, f"{function.__name__} lost auto_port"
        assert signature.parameters["auto_port"].default is False, (
            f"{function.__name__} must not hunt for a port unless asked"
        )
        assert signature.parameters["port"].default == hub.CONTRACT_PORT


def test_no_entrypoint_infers_auto_port_from_the_port_value():
    # The regression that mattered: `if port == 8765` treated an explicit
    # request as a default. Guarding on the value in any form brings it back.
    source = (ROOT / "src" / "flujo" / "web" / "hub.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if not (isinstance(test.left, ast.Name) and test.left.id == "port"):
            continue
        if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in test.ops):
            offenders.append(node.lineno)
    assert not offenders, (
        "hub.py branches on the port value at lines "
        f"{offenders}; auto-detection must be driven by auto_port"
    )


def test_find_free_port_starts_at_the_contract_port():
    signature = inspect.signature(hub._find_free_port)
    assert signature.parameters["start_port"].default == hub.CONTRACT_PORT
    # A real bind/release: the helper must return a port it could actually
    # take, not merely the number it started from.
    chosen = hub._find_free_port("127.0.0.1", hub.CONTRACT_PORT, 8)
    assert hub.CONTRACT_PORT <= chosen < hub.CONTRACT_PORT + 8
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", chosen))


def test_packaging_declares_no_box_specific_path():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "/home/mak" not in text, (
        "packaging must not hard-code this box; FLUJO has to install from its "
        "own branch content on any machine"
    )
    assert 'where = ["src"]' in text, "the package root must stay relative"


def test_the_adapter_is_not_a_packaging_requirement():
    # `flujo` may exist as a compatibility adapter on this box, but nothing in
    # the branch content may require that topology to build or import.
    for relative in ("pyproject.toml", "requirements.txt", "requirements-flujo.txt"):
        candidate = ROOT / relative
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8")
        assert "/home/mak/flujo" not in text, f"{relative} requires the local adapter"
