"""Pipeline de lifecycle de un job: prepare → activate → render."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..paths import repo_root
from .brief import (
    Brief,
    EstadoJob,
    load_brief,
    save_brief,
    brief_from_text,
)
from .job import JobInfo, job_status


@dataclass
class JobResult:
    """Resultado de ejecutar una etapa del lifecycle."""

    ok: bool
    job_path: Path
    estado_inicial: EstadoJob
    estado_final: EstadoJob
    steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    project_path: Optional[Path] = None
    privacy_report: Optional[Path] = None


# ============================================================
# Mapeos de acciones
# ============================================================

_NEXT_ACTION: dict = {
    EstadoJob.BORRADOR: "Pegar texto del pedido y ejecutar: `flujo job-prepare`",
    EstadoJob.BRIEF_EXTRAIDO: "Revisar brief.yaml y completar datos faltantes",
    EstadoJob.PENDIENTE_DATOS: "Resolver pendientes del brief y revisar privacidad",
    EstadoJob.LISTO_PARA_DISENAR: "Activar: `flujo job-activate`",
    EstadoJob.EN_DISENO: "Ajustar config.json del proyecto y `flujo render`",
    EstadoJob.GENERADO: "Revisar outputs y preparar entrega",
    EstadoJob.ENTREGADO: "Sin acción automática",
    EstadoJob.PAUSADO: "Revisar manualmente",
    EstadoJob.CANCELADO: "Sin acción",
}


def suggest_next_action(brief: Brief) -> str:
    """Sugiere la próxima acción para un brief según su estado."""
    base = _NEXT_ACTION.get(brief.estado, "Sin acción automática")
    if brief.pendientes and brief.estado in (
        EstadoJob.BRIEF_EXTRAIDO,
        EstadoJob.PENDIENTE_DATOS,
    ):
        base += f" ({len(brief.pendientes)} pendientes)"
    return base


# ============================================================
# prepare_job
# ============================================================

def prepare_job(
    job_path: Path,
    high_privacy: bool = False,
    run_privacy: bool = True,
    run_brief_extract: bool = True,
) -> JobResult:
    """Ejecuta el pipeline de preparación: privacidad → brief → reporte → estado.

    Pasos:
      1. Escaneo de privacidad (si hay pedido_original.txt)
      2. Extracción automática del brief desde el texto
      3. Generación de reporte_job.md
      4. Asignación de estado sugerido (pendiente_datos o listo_para_disenar)
    """
    job_path = Path(job_path)
    result = JobResult(
        ok=True,
        job_path=job_path,
        estado_inicial=EstadoJob.BORRADOR,
        estado_final=EstadoJob.BORRADOR,
    )

    if not job_path.exists():
        result.ok = False
        result.errors.append(f"No existe job: {job_path}")
        return result

    brief_path = job_path / "brief.yaml"
    if brief_path.exists():
        brief = load_brief(brief_path)
    else:
        brief = Brief(id=job_path.name)

    result.estado_inicial = brief.estado

    # Paso 1: privacidad
    privacy_report = None
    if run_privacy:
        try:
            from ..privacy import scan_text, sanitize_text, write_report

            pedido = job_path / "pedido_original.txt"
            if pedido.exists():
                scan = scan_text(pedido.read_text(encoding="utf-8", errors="ignore"))
                sanitize_text(
                    pedido.read_text(encoding="utf-8", errors="ignore"),
                    job_path / "pedido_sanitizado.txt",
                )
                privacy_report = job_path / "privacy_report.md"
                write_report(privacy_report, scan, source_name=str(pedido.name))
                high_privacy = scan["risk"] == "alto"
                result.privacy_report = privacy_report
                result.steps.append("privacy_check")
        except Exception as e:
            result.errors.append(f"privacidad: {e}")

    # Paso 2: extracción de brief
    if run_brief_extract:
        try:
            pedido = job_path / "pedido_sanitizado.txt"
            if not pedido.exists():
                pedido = job_path / "pedido_original.txt"
            if pedido.exists():
                text = pedido.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    extracted = brief_from_text(text, job_id=job_path.name)
                    # Mezclar: extraer solo si el brief está vacío o en borrador
                    if not brief.tipo_pieza or brief.estado == EstadoJob.BORRADOR:
                        if not brief.tipo_pieza:
                            brief.tipo_pieza = extracted.tipo_pieza
                        if not brief.medidas.ancho_cm:
                            brief.medidas.ancho_cm = extracted.medidas.ancho_cm
                        if not brief.medidas.alto_cm:
                            brief.medidas.alto_cm = extracted.medidas.alto_cm
                        if not brief.medidas.orientacion:
                            brief.medidas.orientacion = extracted.medidas.orientacion
                        if not brief.medidas.sangrado_mm and extracted.medidas.sangrado_mm:
                            brief.medidas.sangrado_mm = extracted.medidas.sangrado_mm
                        # productos nuevos solo si no hay
                        if not brief.productos and extracted.productos:
                            brief.productos = extracted.productos
                        # pendientes: combinar sin duplicar
                        for p in extracted.pendientes:
                            if p not in brief.pendientes:
                                brief.pendientes.append(p)
                        if brief.estado == EstadoJob.BORRADOR:
                            brief.estado = EstadoJob.BRIEF_EXTRAIDO
                    save_brief(brief_path, brief)
                    result.steps.append("brief_extract")
        except Exception as e:
            result.errors.append(f"brief_extract: {e}")
            # refrescar desde disco
            if brief_path.exists():
                brief = load_brief(brief_path)

    # Paso 3: reporte
    try:
        _write_job_report(job_path, brief)
        result.steps.append("job_report")
    except Exception as e:
        result.errors.append(f"job_report: {e}")

    # Paso 4: sugerir estado
    new_status = _suggest_status(brief, high_privacy=high_privacy)
    if brief.estado != new_status:
        brief.estado = new_status
        save_brief(brief_path, brief)
        result.steps.append(f"estado_sugerido:{new_status.value}")

    # Actualizar estado.md
    try:
        _write_estado(job_path, brief)
        result.steps.append("estado_md")
    except Exception as e:
        result.errors.append(f"estado_md: {e}")

    result.estado_final = brief.estado
    return result


def _suggest_status(brief: Brief, high_privacy: bool = False) -> EstadoJob:
    """Sugiere el estado siguiente del brief."""
    if high_privacy:
        return EstadoJob.PENDIENTE_DATOS
    if brief.pendientes:
        return EstadoJob.PENDIENTE_DATOS
    if not brief.tiene_datos_criticos():
        return EstadoJob.PENDIENTE_DATOS
    if brief.estado in (EstadoJob.BORRADOR, EstadoJob.BRIEF_EXTRAIDO):
        return EstadoJob.LISTO_PARA_DISENAR
    return brief.estado


def _write_job_report(job_path: Path, brief: Brief) -> Path:
    """Genera reporte_job.md."""
    privacy_section = ""
    pr = job_path / "privacy_report.md"
    if pr.exists():
        privacy_section = "\n## Privacidad\n\n```txt\n" + pr.read_text(encoding="utf-8", errors="ignore").strip() + "\n```\n"
    pending_section = ""
    if brief.pendientes:
        pending_section = "\n## Pendientes\n\n" + "".join(f"- [ ] {p}\n" for p in brief.pendientes)

    out = job_path / "reporte_job.md"
    out.write_text(
        f"""# Reporte job — {job_path.name}

## Brief

- Estado: {brief.estado.value}
- Cliente: {brief.cliente or 'pendiente'}
- Proyecto: {brief.proyecto or 'pendiente'}
- Tipo pieza: {brief.tipo_pieza or 'pendiente'}
- Medida: {(f"{brief.medidas.ancho_cm:g} x {brief.medidas.alto_cm:g} cm") if brief.medidas.ancho_cm and brief.medidas.alto_cm else 'pendiente'}
- Productos: {', '.join(brief.productos) if brief.productos else 'pendiente'}
{privacy_section}{pending_section}

## Próxima acción sugerida

- {suggest_next_action(brief)}

## Comandos rápidos

```bash
flujo job-prepare "{job_path}"
flujo job-activate "{job_path}"
flujo render projects/piezas_vectoriales/<proyecto>/config.json
```
""",
        encoding="utf-8",
    )
    return out


def _write_estado(job_path: Path, brief: Brief) -> Path:
    """Actualiza estado.md."""
    out = job_path / "estado.md"
    out.write_text(
        f"""# Estado del job

Estado: {brief.estado.value}

## Resumen

- Tipo pieza: {brief.tipo_pieza or 'pendiente'}
- Medida: {(f"{brief.medidas.ancho_cm:g} x {brief.medidas.alto_cm:g} cm") if brief.medidas.ancho_cm and brief.medidas.alto_cm else 'pendiente'}
- Orientación: {brief.medidas.orientacion or 'pendiente'}
- Productos: {', '.join(brief.productos) if brief.productos else 'pendiente'}

## Pendientes

{chr(10).join('- [ ] ' + p for p in brief.pendientes) if brief.pendientes else '- [ ] Revisar y aprobar brief.'}

## Próxima acción

- {suggest_next_action(brief)}
""",
        encoding="utf-8",
    )
    return out


# ============================================================
# activate_job: brief → proyecto en projects/piezas_vectoriales/
# ============================================================

def activate_job(
    job_path: Path,
    project_name: Optional[str] = None,
    template: Optional[str] = None,
) -> JobResult:
    """Activa un job: crea un proyecto base desde brief.yaml y marca en_diseno."""
    job_path = Path(job_path)
    result = JobResult(
        ok=True,
        job_path=job_path,
        estado_inicial=EstadoJob.BORRADOR,
        estado_final=EstadoJob.BORRADOR,
    )
    if not job_path.exists():
        result.ok = False
        result.errors.append(f"No existe job: {job_path}")
        return result

    brief_path = job_path / "brief.yaml"
    if not brief_path.exists():
        result.ok = False
        result.errors.append(f"No existe brief.yaml en {job_path}")
        return result
    brief = load_brief(brief_path)
    result.estado_inicial = brief.estado

    try:
        from ..render.piezas import create_project_from_brief

        project_dir = create_project_from_brief(
            brief_path,
            project_name=project_name,
            explicit_template=template,
        )
        result.project_path = project_dir
        result.steps.append("brief_to_project")
    except Exception as e:
        result.ok = False
        result.errors.append(f"brief_to_project: {e}")
        return result

    # cambiar estado
    if brief.estado == EstadoJob.LISTO_PARA_DISENAR or brief.estado == EstadoJob.PENDIENTE_DATOS:
        brief.estado = EstadoJob.EN_DISENO
    else:
        brief.estado = EstadoJob.EN_DISENO
    save_brief(brief_path, brief)
    result.estado_final = brief.estado
    result.steps.append("estado:en_diseno")

    # escribir resultado.md
    if project_name is None:
        project_name = project_dir.name if result.project_path else ""
    rp = job_path / "resultado.md"
    rp.write_text(
        f"""# Resultado

## Job activado

- Job: `{job_path}`
- Estado: {brief.estado.value}
- Proyecto: `{result.project_path}`
- Config: `{result.project_path / 'config.json' if result.project_path else '?'}`
- Brief fuente: `{brief_path}`

## Próxima acción

```bash
flujo render "{result.project_path / 'config.json' if result.project_path else ''}"
```

## Estado

Job actualizado a `en_diseno`.
""",
        encoding="utf-8",
    )
    return result
