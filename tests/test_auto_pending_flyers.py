from pathlib import Path

from flujo.automation import run_pending_flyers
from flujo.jobs.brief import load_brief


def test_run_pending_flyers_prepares_and_activates_job(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True)
    job_dir = jobs_dir / "2026-06-28_demo_flyer"
    job_dir.mkdir(parents=True)
    (job_dir / "pedido_original.txt").write_text(
        "Flyer para suplementos, 20x10 cm, texto aprobado, entrega editable SVG.",
        encoding="utf-8",
    )

    result = run_pending_flyers(base_dir=tmp_path)

    assert result["processed"] >= 1
    assert (job_dir / "reporte_job.md").exists()
    brief = load_brief(job_dir / "brief.yaml")
    assert brief.estado.value != "borrador"
