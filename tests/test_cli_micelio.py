"""Tests for `flujo micelio *`: the envelope commands wrapping flujo.micelio.

`flujo.micelio` itself is covered by tests/test_micelio*.py, but nothing in
this suite drove the CLI subcommands before -- they were exercised only by a
human copy-pasting into a terminal. Each test asserts on the printed sobre or
exit code, not just "it did not crash" (a run that silently drops the
`criterio` a nutriente needs would still exit 0 with the wrong content).
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app

runner = CliRunner()


def _seed(criterio: list) -> dict:
    return {
        "formato": "micelio/1",
        "tipo": "semilla",
        "asunto": "probar el ciclo",
        "cuerpo": {"idea": "medir algo"},
        "criterio": criterio,
    }


def _green_file_criterion(path: Path) -> list:
    (path / "listo.txt").write_text("contenido real", encoding="utf-8")
    return [{"tipo": "archivo", "ruta": "listo.txt", "nombre": "existe"}]


def _red_file_criterion() -> list:
    return [{"tipo": "archivo", "ruta": "no_existe.txt", "nombre": "existe"}]


# --------------------------------------------------------------- formato

def test_formato_prints_pasteable_text_to_stdout():
    result = runner.invoke(app, ["micelio", "formato"])
    assert result.exit_code == 0
    assert "micelio/1" in result.output


def test_formato_writes_to_a_file_when_output_flag_is_given(tmp_path: Path):
    target = tmp_path / "formato.txt"
    result = runner.invoke(app, ["micelio", "formato", "--salida", str(target)])
    assert result.exit_code == 0
    assert target.exists()
    assert "micelio/1" in target.read_text(encoding="utf-8")


# --------------------------------------------------------------- validar

def test_validar_a_well_formed_sobre_prints_its_asunto(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "validar", str(sobre_path)])
    assert result.exit_code == 0
    assert "probar el ciclo" in result.output
    assert "criterio archivo" in result.output


def test_validar_rejects_a_sobre_missing_criterio(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    malformado = {"formato": "micelio/1", "tipo": "semilla", "asunto": "x", "cuerpo": {}}
    sobre_path.write_text(json.dumps(malformado), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "validar", str(sobre_path)])
    assert result.exit_code == 1
    assert "sobre invalido" in result.output.lower()


def test_validar_a_missing_file_exits_with_code_two():
    result = runner.invoke(app, ["micelio", "validar", "/no/existe/nunca.json"])
    assert result.exit_code == 2
    assert "no pude leerlo" in result.output.lower()


# --------------------------------------------------------------- fruto

def test_fruto_measures_a_jsonl_dataset_and_reports_coverage(tmp_path: Path):
    dataset = tmp_path / "fichas.jsonl"
    records = [{"titulo": "a", "nota": "x"}, {"titulo": "b", "nota": ""}, {"titulo": "c", "nota": ""}]
    dataset.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "fruto", str(dataset), "--asunto", "estado fichas"])
    assert result.exit_code == 0
    # After the pasteable JSON, the console prints `anomalia` lines; only
    # the first object is the envelope itself.
    payload, _ = json.JSONDecoder().raw_decode(result.output)
    assert payload["tipo"] == "fruto"
    assert payload["cuerpo"]["medido"]["registros"] == 3
    # "nota" is empty in 2/3 rows (67%), below the 40% coverage floor -> flagged.
    assert any(a["campo"] == "nota" for a in payload["cuerpo"]["anomalias"])


def test_fruto_on_a_missing_dataset_exits_with_code_two():
    result = runner.invoke(app, ["micelio", "fruto", "/no/existe/dataset.jsonl"])
    assert result.exit_code == 2
    assert "no pude leerlo" in result.output.lower()


def test_fruto_writes_a_pasteable_file_when_output_flag_is_given(tmp_path: Path):
    dataset = tmp_path / "d.json"
    dataset.write_text(json.dumps({"items": [{"a": 1}]}), encoding="utf-8")
    target = tmp_path / "fruto.json"
    result = runner.invoke(app, ["micelio", "fruto", str(dataset), "--salida", str(target)])
    assert result.exit_code == 0
    assert target.exists()
    assert "bytes, pegable" in result.output


# --------------------------------------------------------------- verificar

def test_verificar_reports_verde_and_exits_zero(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_green_file_criterion(tmp_path))), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "verificar", str(sobre_path), "--raiz", str(tmp_path)])
    assert result.exit_code == 0
    assert "VERDE" in result.output


def test_verificar_reports_rojo_and_exits_one(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "verificar", str(sobre_path), "--raiz", str(tmp_path)])
    assert result.exit_code == 1
    assert "ROJO" in result.output


def test_verificar_an_invalid_sobre_exits_with_code_two(tmp_path: Path):
    sobre_path = tmp_path / "roto.json"
    sobre_path.write_text("esto no es json", encoding="utf-8")
    result = runner.invoke(app, ["micelio", "verificar", str(sobre_path)])
    assert result.exit_code == 2
    assert "sobre invalido" in result.output.lower()


# --------------------------------------------------------------- cosechar

def test_cosechar_a_green_criterio_returns_a_fruto_and_exits_zero(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_green_file_criterion(tmp_path))), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "cosechar", str(sobre_path), "--raiz", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tipo"] == "fruto"


def test_cosechar_a_red_criterio_returns_a_hongo_and_exits_one(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "cosechar", str(sobre_path), "--raiz", str(tmp_path)])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["tipo"] == "hongo"
    assert payload["cuerpo"]["fallaron"]


def test_cosechar_writes_the_hongo_to_disk_when_output_flag_is_given(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    target = tmp_path / "resultado.json"
    result = runner.invoke(app, ["micelio", "cosechar", str(sobre_path),
                                  "--raiz", str(tmp_path), "--salida", str(target)])
    assert result.exit_code == 1
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["tipo"] == "hongo"


# --------------------------------------------------------------- depositar

def test_depositar_without_aplicar_writes_nothing(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    queue_path = tmp_path / "material.jsonl"
    result = runner.invoke(app, ["micelio", "depositar", str(sobre_path), "--cola", str(queue_path)])
    assert result.exit_code == 0
    assert "ensayo" in result.output.lower()
    assert not queue_path.exists()


def test_depositar_with_aplicar_writes_the_queue_and_the_sobre(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    queue_path = tmp_path / "material.jsonl"
    result = runner.invoke(app, ["micelio", "depositar", str(sobre_path),
                                  "--cola", str(queue_path), "--aplicar"])
    assert result.exit_code == 0
    assert queue_path.exists()
    written = queue_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(written) == 1
    task = json.loads(written[0])
    assert task["depto"] == "codex"
    assert task["estado"] == "pendiente"


def test_depositar_twice_deduplicates_by_id(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    queue_path = tmp_path / "material.jsonl"
    runner.invoke(app, ["micelio", "depositar", str(sobre_path), "--cola", str(queue_path), "--aplicar"])
    result = runner.invoke(app, ["micelio", "depositar", str(sobre_path), "--cola", str(queue_path), "--aplicar"])
    assert result.exit_code == 0
    assert "ya estaba en la cola" in result.output
    assert len(queue_path.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_depositar_on_a_missing_file_fails_instead_of_depositing_garbage():
    """Unlike validar/fruto/verificar/cosechar, depositar does not catch
    OSError around `leer()` -- it still fails non-zero and writes nothing,
    it just does it via an uncaught exception instead of a clean message."""
    result = runner.invoke(app, ["micelio", "depositar", "no-existe-nunca.json"])
    assert result.exit_code != 0
    assert isinstance(result.exception, (FileNotFoundError, OSError))


def test_depositar_rejects_an_unknown_depto(tmp_path: Path):
    sobre_path = tmp_path / "sobre.json"
    sobre_path.write_text(json.dumps(_seed(_red_file_criterion())), encoding="utf-8")
    result = runner.invoke(app, ["micelio", "depositar", str(sobre_path), "--depto", "marketing"])
    assert result.exit_code == 2
    assert "--depto tiene que ser codex o research" in result.output
