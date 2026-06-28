"""Tests para el motor de planos de stands (projects/plano/plano_stands.py)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PLANO_DIR = REPO / "projects" / "plano"
SCRIPT = PLANO_DIR / "plano_stands.py"
EJEMPLO = PLANO_DIR / "ejemplos" / "evento_ejemplo.json"


def _run_script(args: list) -> subprocess.CompletedProcess:
    """Ejecuta plano_stands.py como subproceso con PYTHONPATH correcto."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    src_path = str(REPO / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + existing if existing else "")
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


@pytest.mark.skipif(not SCRIPT.exists(), reason="proyecto plano no está presente")
class TestPlanoStands:
    def test_ejemplo_json_existe(self):
        assert EJEMPLO.exists(), f"Falta ejemplo: {EJEMPLO}"

    def test_genera_svg(self):
        res = _run_script([str(EJEMPLO)])
        assert res.returncode == 0, f"stderr: {res.stderr}"
        svg = res.stdout
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "PLANO" in svg
        assert "Stand Informativo" in svg
        assert "Stand Testeo" in svg
        assert "Contención" in svg

    def test_genera_rider(self):
        res = _run_script([str(EJEMPLO), "--rider"])
        assert res.returncode == 0, f"stderr: {res.stderr}"
        rider = res.stdout
        assert "RIDER TÉCNICO" in rider
        assert "ALIMENTACIÓN" in rider
        assert "2 mesa(s)" in rider
        assert "testeo" in rider.lower()
        assert "ZONA DE CONTENCIÓN" in rider

    def test_evento_pequeno_sin_extras(self, tmp_path):
        peq = tmp_path / "evento_pequeno.json"
        peq.write_text(
            json.dumps(
                {
                    "nombre": "Evento pequeño",
                    "duracion_horas": 3,
                    "voluntarios": 3,
                    "asistentes_estimados": 100,
                    "incluye_testeo": False,
                    "masivo": False,
                }
            ),
            encoding="utf-8",
        )
        res = _run_script([str(peq), "--rider"])
        assert res.returncode == 0, f"stderr: {res.stderr}"
        rider = res.stdout
        assert "1 mesa(s)" in rider
        assert "colación" not in rider.lower()
        assert "alimentación" not in rider.lower()
        assert "testeo" not in rider.lower()
        assert "contención" not in rider.lower()

    def test_evento_masivo_agrega_contencion(self, tmp_path):
        masivo = tmp_path / "evento_masivo.json"
        masivo.write_text(
            json.dumps(
                {
                    "nombre": "Evento masivo",
                    "duracion_horas": 2,
                    "voluntarios": 2,
                    "asistentes_estimados": 2500,
                    "incluye_testeo": False,
                    "masivo": False,
                }
            ),
            encoding="utf-8",
        )
        res = _run_script([str(masivo), "--rider"])
        assert res.returncode == 0, f"stderr: {res.stderr}"
        rider = res.stdout
        assert "ZONA DE CONTENCIÓN" in rider
