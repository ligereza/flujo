"""Intake: detección y parseo de correos / pedidos.

Submódulos:
  email_parser  — extraer links de IG, secciones, detectar tipo de proyecto
  pipeline      — pipeline completo correo → job → brief
"""

from .email_parser import (
    extract_instagram_links,
    detect_project_type,
    parse_email_content,
    parse_email_file,
)
from .pipeline import process_email_to_jobs

__all__ = [
    "extract_instagram_links",
    "detect_project_type",
    "parse_email_content",
    "parse_email_file",
    "process_email_to_jobs",
]
