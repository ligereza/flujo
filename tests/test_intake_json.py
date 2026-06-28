import os
import json
import yaml
from pathlib import Path
from flujo.paths import repo_root, workspace_root
from flujo.intake.json_parser import process_json_intake

def test_json_intake_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path))
    mock_intake = {
        "intake_version": "1.0",
        "pedido": {
            "id_externo": "REQ-101",
            "area": "eventos",
            "solicitante": {
                "nombre": "Juan Pérez",
                "canal": "correo"
            },
            "tipo_pieza": "flyer",
            "medidas": {
                "ancho_cm": 15.0,
                "alto_cm": 20.0,
                "orientacion": "vertical",
                "sangrado_mm": 2.0,
                "area_segura_mm": 5.0
            },
            "productos": ["flyer_evento"],
            "contenido": {
                "titulo": "Rave Solidaria 2026",
                "subtitulo": "Música por una causa",
                "cuerpo": "Únete a nosotros este sábado...",
                "llamado_accion": "Compra tu entrada en el link"
            },
            "entrega": {
                "formatos": ["editable_svg", "vectorizado_svg", "zip"]
            }
        }
    }
    json_file = tmp_path / "mock_intake.json"
    json_file.write_text(json.dumps(mock_intake, ensure_ascii=False), encoding="utf-8")
    res = process_json_intake(json_file)
    assert res["ok"] is True
    job_dir = Path(res["job_dir"])
    assert job_dir.exists()
    assert "rave-solidaria-2026" in job_dir.name
    brief_yaml_path = job_dir / "brief.yaml"
    assert brief_yaml_path.exists()
    with open(brief_yaml_path, "r", encoding="utf-8") as f:
        brief = yaml.safe_load(f)
    assert brief["origen"] == "json_intake"
    assert brief["cliente"] == "Juan Pérez"
    assert brief["tipo_pieza"] == "flyer"
    assert brief["medidas"]["ancho_cm"] == 15.0
    assert brief["medidas"]["alto_cm"] == 20.0
    assert brief["contenido"]["titulo"] == "Rave Solidaria 2026"
    assert brief["contenido"]["subtitulo"] == "Música por una causa"
    assert brief["entrega"]["editable_svg"] is True
    assert brief["entrega"]["vectorizado_svg"] is True
    assert brief["entrega"]["pdf_impresion"] is False
    assert brief["entrega"]["zip"] is True
