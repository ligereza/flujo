import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "projects" / "logo_clean_lab" / "scripts" / "validate_dataset.py"


def test_validator_accepts_well_formed_dataset(tmp_path: Path) -> None:
    sample_file = tmp_path / "cases.jsonl"
    sample_file.write_text(
        "\n".join(
            [
                '{"sample":"case_a","mode":"W","word":"FLUJO","before_points":120,"after_points":108,"removed":12,"moved":5,"collapsed":2,"round_fixed":1,"approved":true,"note":"ok","script_version":"v1"}',
                '{"sample":"case_b","mode":"O","word":"O","before_points":90,"after_points":86,"removed":4,"moved":3,"collapsed":1,"round_fixed":0,"approved":false,"note":"needs review","script_version":"v1"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(sample_file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert "Validated" in result.stdout
    assert "2" in result.stdout


def test_validator_rejects_missing_required_fields(tmp_path: Path) -> None:
    sample_file = tmp_path / "invalid.jsonl"
    sample_file.write_text(
        '{"sample":"bad","mode":"W","word":"X","before_points":50,"after_points":48,"removed":2,"moved":1,"collapsed":0,"round_fixed":0,"approved":true,"note":"ok"}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(sample_file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0
    assert "missing required field" in result.stderr.lower()
