"""Creación y listado de jobs."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

from ..paths import repo_root
from .brief import Brief, EstadoJob, load_brief


TEMPLATES_DIR = "_template"


def slugify(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9áéíóúñ]+", "-", s)
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "pedido"


@dataclass
class JobInfo:
    path: Path
    name: str
    estado: str
    tipo_pieza: str
    proyecto: str
    pendientes: int

    @property
    def exists(self) -> bool:
        return self.path.exists()


def _get_template_dir() -> Path:
    """Devuelve la ruta al directorio _template del paquete.

    Se incluye en el paquete Python para que funcione out-of-the-box.
    Si el repo tiene un jobs/_template local, se prefiere ese.
    """
    repo = repo_root()
    local = repo / "jobs" / TEMPLATES_DIR
    if local.exists():
        return local
    # fallback al template del paquete
    pkg = Path(__file__).resolve().parents[2] / "templates" / "jobs_template"
    if pkg.exists():
        return pkg
    return local  # se creará vacío


def _ensure_template(repo: Path) -> Path:
    """Asegura que exista jobs/_template con los archivos base."""
    tpl = repo / "jobs" / TEMPLATES_DIR
    if tpl.exists():
        return tpl
    tpl.mkdir(parents=True, exist_ok=True)
    # crear archivos base
    (tpl / "pedido_original.txt").write_text(
        "[Texto del pedido / correo original]\n",
        encoding="utf-8",
    )
    (tpl / "estado.md").write_text(
        "# Estado del job\n\nEstado: borrador\n\n## Próxima acción\n\n- Pegar texto del pedido en pedido_original.txt\n- Ejecutar `flujo job-prepare jobs/YYYY-MM-DD_nombre`\n",
        encoding="utf-8",
    )
    (tpl / "resultado.md").write_text(
        "# Resultado\n\nAún no activado. Resultado se completará al ejecutar `flujo job-activate`.\n",
        encoding="utf-8",
    )
    (tpl / "brief.yaml").write_text(
        "id: YYYY-MM-DD_nombre_pedido\n"
        "estado: borrador\n"
        "origen: correo_jefe\n"
        "cliente:\n"
        "proyecto:\n"
        "tipo_pieza:\n"
        "\n"
        "medidas:\n"
        "  ancho_cm:\n"
        "  alto_cm:\n"
        "  orientacion:\n"
        "  sangrado_mm:\n"
        "  area_segura_mm:\n"
        "\n"
        "entrega:\n"
        "  editable_svg: true\n"
        "  vectorizado_svg: true\n"
        "  pdf_impresion: false\n"
        "  zip: true\n"
        "  otro:\n"
        "\n"
        "productos: []\n"
        "\n"
        "contenido:\n"
        "  fuente: correo_original\n"
        "  texto_aprobado: false\n"
        "  notas:\n"
        "\n"
        "restricciones:\n"
        "  no_inventar_claims: true\n"
        "  texto_vectorizado: true\n"
        "  editable_para_illustrator: true\n"
        "\n"
        "pendientes: []\n",
        encoding="utf-8",
    )
    (tpl / ".gitkeep").write_text("", encoding="utf-8")
    return tpl


def create_job(name: str, source_path: Optional[Path] = None, repo: Optional[Path] = None) -> Path:
    """Crea un nuevo job a partir de un nombre (y opcionalmente texto fuente).

    Retorna el path al directorio del job creado.
    """
    repo = repo or repo_root()
    tpl = _ensure_template(repo)

    slug = slugify(name)
    job_dir = repo / "jobs" / f"{date.today().isoformat()}_{slug}"
    counter = 1
    while job_dir.exists():
        counter += 1
        job_dir = repo / "jobs" / f"{date.today().isoformat()}_{slug}-{counter:02d}"

    shutil.copytree(tpl, job_dir)
    # actualizar id en brief.yaml
    brief_path = job_dir / "brief.yaml"
    if brief_path.exists():
        text = brief_path.read_text(encoding="utf-8")
        text = text.replace("YYYY-MM-DD_nombre_pedido", job_dir.name)
        brief_path.write_text(text, encoding="utf-8")

    if source_path is not None and source_path.exists():
        src_text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
        (job_dir / "pedido_original.txt").write_text(src_text, encoding="utf-8")

    return job_dir


def list_jobs(repo: Optional[Path] = None, include_examples: bool = False) -> List[JobInfo]:
    """Lista todos los jobs en el repo."""
    repo = repo or repo_root()
    base = repo / "jobs"
    if not base.exists():
        return []

    results: List[JobInfo] = []
    for b in sorted(base.iterdir()):
        if b.name.startswith("_") and not include_examples:
            continue
        if not b.is_dir():
            continue
        brief_path = b / "brief.yaml"
        if not brief_path.exists():
            continue
        try:
            brief = load_brief(brief_path)
        except Exception:
            results.append(JobInfo(
                path=b, name=b.name, estado="error",
                tipo_pieza="", proyecto="", pendientes=0,
            ))
            continue
        results.append(JobInfo(
            path=b,
            name=b.name,
            estado=brief.estado.value,
            tipo_pieza=brief.tipo_pieza,
            proyecto=brief.proyecto,
            pendientes=len(brief.pendientes),
        ))
    return results


def find_job(name_or_path: str, repo: Optional[Path] = None) -> Optional[Path]:
    """Encuentra un job por nombre o path."""
    repo = repo or repo_root()
    p = Path(name_or_path)
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        repo / "jobs" / name_or_path,
        repo / name_or_path,
    ]
    # buscar por prefijo
    base = repo / "jobs"
    if base.exists():
        for d in base.iterdir():
            if d.name.startswith(name_or_path) or name_or_path in d.name:
                if (d / "brief.yaml").exists():
                    return d
    for c in candidates:
        if c.exists() and (c / "brief.yaml").exists():
            return c
    return None


def job_status(job_path: Path) -> JobInfo:
    """Devuelve el estado actual de un job."""
    brief_path = job_path / "brief.yaml"
    if not brief_path.exists():
        return JobInfo(
            path=job_path,
            name=job_path.name,
            estado="sin_brief",
            tipo_pieza="",
            proyecto="",
            pendientes=0,
        )
    brief = load_brief(brief_path)
    return JobInfo(
        path=job_path,
        name=job_path.name,
        estado=brief.estado.value,
        tipo_pieza=brief.tipo_pieza,
        proyecto=brief.proyecto,
        pendientes=len(brief.pendientes),
    )
