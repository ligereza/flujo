"""Pipeline completo: correo → jobs + briefs + (opcional) proyectos."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..paths import repo_root
from ..flyer.import_email import import_from_email
from ..jobs.brief import brief_from_text
from ..jobs.job import create_job
from ..jobs.lifecycle import prepare_job
from ..privacy.scan import scan_text
from .email_parser import parse_email_content


# Heurística de inferencia de tipo y medidas
TYPE_HINTS = {
    "etiqueta": {"tipo": "etiqueta", "ancho": 16.5, "alto": 6.5},
    "sticker": {"tipo": "sticker", "ancho": 10, "alto": 10},
    "flyer": {"tipo": "flyer", "ancho": 21, "alto": 29.7},
    "dossier": {"tipo": "dossier", "ancho": 21, "alto": 29.7},
    "one page": {"tipo": "one_page", "ancho": 21, "alto": 29.7},
    "one-page": {"tipo": "one_page", "ancho": 21, "alto": 29.7},
    "presentacion": {"tipo": "presentacion", "ancho": 21, "alto": 29.7},
    "carrusel": {"tipo": "carrusel", "ancho": 10.8, "alto": 10.8},
    "rider": {"tipo": "rider", "ancho": 29.7, "alto": 21},
    "tarjeta": {"tipo": "tarjeta", "ancho": 9, "alto": 5},
}


@dataclass
class PipelineResult:
    """Resultado del pipeline de intake."""
    email_path: Path
    parsed: dict = field(default_factory=dict)
    jobs_created: List[Path] = field(default_factory=list)
    flyers_created: int = 0
    flyers_skipped: int = 0
    privacy_risk: str = "bajo"
    inferred: Optional[dict] = None
    errors: List[str] = field(default_factory=list)


def _infer_type_and_size(text: str) -> Optional[dict]:
    text_lower = text.lower()
    for keyword, data in TYPE_HINTS.items():
        if keyword in text_lower:
            return dict(data)
    return None


def process_email_to_jobs(
    email_path: Path,
    force: bool = False,
    auto_prepare: bool = True,
    auto_create_project: bool = False,
) -> PipelineResult:
    """Procesa un correo: detecta tipo, crea jobs/briefs, opcionalmente activa proyectos.

    Para flyers (IG links): usa `import_from_email` (crea projects/flyer_eventos/<date>_ig_<shortcode>).
    Para pedidos de diseño: crea jobs/<date>_<slug> y ejecuta job-prepare.
    """
    email_path = Path(email_path)
    result = PipelineResult(email_path=email_path)
    if not email_path.exists():
        result.errors.append(f"No existe: {email_path}")
        return result

    text = email_path.read_text(encoding="utf-8", errors="ignore")

    # Paso 1: escaneo de privacidad
    scan = scan_text(text, source=str(email_path.name))
    result.privacy_risk = scan.risk

    # Paso 2: parseo
    parsed = parse_email_content(text)
    result.parsed = parsed

    # Paso 3: flyers (links IG)
    if parsed["instagram_links"]:
        try:
            res = import_from_email(email_path, force=force)
            result.flyers_created = res["created"]
            result.flyers_skipped = res["skipped"]
        except Exception as e:
            result.errors.append(f"flyers: {e}")

    # Paso 4: si parece pedido de diseño (no solo flyers)
    if parsed["project_type"] != "flyer" or parsed["sections"]:
        # intentar inferir tipo/medidas
        inferred = _infer_type_and_size(text)
        result.inferred = inferred

        # usar nombre basado en secciones
        title = (
            parsed["sections"].get("titulo")
            or parsed["sections"].get("evento")
            or email_path.stem
        )
        try:
            job_dir = create_job(title, source_path=email_path)
            result.jobs_created.append(job_dir)
            if auto_prepare:
                prep = prepare_job(job_dir, high_privacy=(scan.risk == "alto"))
                if not prep.ok:
                    result.errors.extend(prep.errors)
            if auto_create_project and not inferred:
                # no hay tipo, no crear proyecto
                pass
        except Exception as e:
            result.errors.append(f"job: {e}")

    return result
