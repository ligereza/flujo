"""Módulo de gestión de jobs y briefs.

Sistema de lifecycle para jobs creativos:
  borrador → brief_extraído_pendiente_revision → pendiente_datos
    → listo_para_disenar → en_diseno → generado → entregado
"""

from .brief import (
    Brief,
    EstadoJob,
    Medidas,
    Entrega,
    Contenido,
    Restricciones,
    load_brief,
    save_brief,
    parse_yaml_simple,
    brief_from_text,
)
from .job import create_job, list_jobs, find_job, job_status, JobInfo
from .lifecycle import (
    prepare_job,
    activate_job,
    suggest_next_action,
    JobResult,
)

__all__ = [
    "Brief",
    "EstadoJob",
    "Medidas",
    "Entrega",
    "Contenido",
    "Restricciones",
    "load_brief",
    "save_brief",
    "parse_yaml_simple",
    "brief_from_text",
    "create_job",
    "list_jobs",
    "find_job",
    "job_status",
    "JobInfo",
    "prepare_job",
    "activate_job",
    "suggest_next_action",
    "JobResult",
]
