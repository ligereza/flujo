import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from flujo.cli import app


runner = CliRunner()


def _valid_payload() -> dict:
    return {
        "intake_version": "1.0",
        "pedido": {
            "id_externo": "REQ-CLI-1",
            "area": "eventos",
            "solicitante": {"nombre": "Equipo Eventos", "canal": "formulario"},
            "tipo_pieza": "flyer",
            "medidas": {"ancho_cm": 10, "alto_cm": 14, "orientacion": "vertical"},
            "productos": ["flyer_evento"],
            "contenido": {
                "titulo": "Prueba CLI Intake",
                "subtitulo": "Subtítulo",
                "cuerpo": "Contenido base",
            },
            "entrega": {"formatos": ["editable_svg", "zip"]},
        },
    }


def test_cli_intake_json_creates_job_ack(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    src = tmp_path / "pedido.json"
    src.write_text(json.dumps(_valid_payload(), ensure_ascii=False), encoding="utf-8")

    result = runner.invoke(app, ["intake", "json", str(src), "--no-show-ack"])

    assert result.exit_code == 0, result.output
    assert "Intake JSON procesado" in result.output
    jobs = sorted((tmp_path / "jobs").glob("*_prueba-cli-intake"))
    assert len(jobs) == 1
    job = jobs[0]
    assert (job / "brief.yaml").exists()
    assert (job / "estado.md").exists()
    assert (job / "resultado.md").exists()

    brief = yaml.safe_load((job / "brief.yaml").read_text(encoding="utf-8"))
    assert brief["origen"] == "json_intake"
    assert brief["estado"] == "listo_para_disenar"
    assert brief["contenido"]["titulo"] == "Prueba CLI Intake"


def test_cli_intake_json_invalid_schema_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    src = tmp_path / "malo.json"
    src.write_text(json.dumps({"intake_version": "1.0", "pedido": {}}), encoding="utf-8")

    result = runner.invoke(app, ["intake", "json", str(src), "--no-show-ack"])

    assert result.exit_code != 0
    assert "Validación de esquema falló" in result.output
    assert not (tmp_path / "jobs").exists() or not list((tmp_path / "jobs").glob("20*"))
