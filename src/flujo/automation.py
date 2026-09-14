from __future__ import annotations

from pathlib import Path
from typing import Any

from .jobs.brief import EstadoJob, load_brief, save_brief
from .jobs.lifecycle import activate_job, prepare_job
from .paths import repo_root, workspace_root


def run_pending_flyers(base_dir: str | Path | None = None) -> dict[str, Any]:
    """Automatiza el siguiente paso de jobs pendientes de flyer.

    El flujo es simple y local: prepara cada job, y si ya está listo para diseño
    lo activa hacia un proyecto base. Esto permite que al abrir la app se avance
    de forma automática sobre los flyers pendientes.
    """

    root = Path(base_dir) if base_dir is not None else (workspace_root() if workspace_root().exists() else repo_root())
    jobs_dir = root / "jobs"
    if not jobs_dir.exists():
        return {"ok": True, "processed": 0, "jobs": [], "note": "No jobs directory found"}

    processed = []
    for job_dir in sorted([p for p in jobs_dir.iterdir() if p.is_dir() and not p.name.startswith("_")], key=lambda p: p.name):
        brief_path = job_dir / "brief.yaml"
        if not brief_path.exists():
            prepare_res = prepare_job(job_dir, run_privacy=True, run_brief_extract=True)
            brief = load_brief(job_dir / "brief.yaml") if (job_dir / "brief.yaml").exists() else None
            processed.append({
                "job": job_dir.name,
                "action": "prepared",
                "state": brief.estado.value if brief else "unknown",
                "report": str(job_dir / "reporte_job.md"),
            })
            continue

        brief = load_brief(brief_path)
        if brief.estado in (EstadoJob.BORRADOR, EstadoJob.BRIEF_EXTRAIDO, EstadoJob.PENDIENTE_DATOS):
            prep = prepare_job(job_dir, run_privacy=True, run_brief_extract=True)
            brief = load_brief(brief_path)
            processed.append({
                "job": job_dir.name,
                "action": "prepared",
                "state": brief.estado.value,
                "report": str(job_dir / "reporte_job.md"),
            })
            if prep.ok and brief.estado in (EstadoJob.LISTO_PARA_DISENAR, EstadoJob.EN_DISENO):
                try:
                    activate_res = activate_job(job_dir)
                    processed[-1]["activated"] = bool(activate_res.project_path)
                except Exception as exc:
                    processed[-1]["activate_error"] = str(exc)
            continue

        if brief.estado in (EstadoJob.LISTO_PARA_DISENAR, EstadoJob.EN_DISENO):
            try:
                activate_res = activate_job(job_dir)
                processed.append({
                    "job": job_dir.name,
                    "action": "activated",
                    "state": brief.estado.value,
                    "project": str(activate_res.project_path) if activate_res.project_path else None,
                })
            except Exception as exc:  # pragma: no cover - best effort
                processed.append({
                    "job": job_dir.name,
                    "action": "activation_failed",
                    "state": brief.estado.value,
                    "error": str(exc),
                })

    return {"ok": True, "processed": len(processed), "jobs": processed, "root": str(root)}
