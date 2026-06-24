"""Intake JSON 1.0 → job/brief.

Consume `schemas/intake.schema.json`, valida un pedido estructurado y crea un
job usable por el resto del pipeline. Es deliberadamente conservador: no
inventa medidas ni precios; cuando algo no está cerrado deja pendientes claros.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from ..jobs.brief import EstadoJob
from ..jobs.job import create_job
from ..paths import repo_root

try:  # PyYAML está en requirements, pero mantenemos fallback por portabilidad.
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class JsonIntakeResult:
    ok: bool
    job_dir: str = ""
    brief_path: str = ""
    resultado_path: str = ""
    estado: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ok": self.ok,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        if self.job_dir:
            data["job_dir"] = self.job_dir
        if self.brief_path:
            data["brief_path"] = self.brief_path
        if self.resultado_path:
            data["resultado_path"] = self.resultado_path
        if self.estado:
            data["estado"] = self.estado
        if self.errors:
            data["error"] = "; ".join(self.errors)
        if self.warnings:
            data["warning"] = "; ".join(self.warnings)
        return data


def load_intake_schema() -> dict[str, Any]:
    schema_path = repo_root() / "schemas" / "intake.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"No se encontró el esquema en: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Error leyendo JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("El intake debe ser un objeto JSON.")
    return data


def _json_path(error: Any) -> str:
    parts = [str(p) for p in getattr(error, "absolute_path", [])]
    return ".".join(parts) if parts else "$"


def validate_intake_data(data: dict[str, Any]) -> list[str]:
    """Valida contra JSON Schema y devuelve lista de errores humanos."""
    schema = load_intake_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{_json_path(e)}: {e.message}" for e in errors]


def _infer_orientation(ancho: Any, alto: Any, explicit: str = "") -> str:
    if explicit:
        return explicit
    try:
        a = float(ancho)
        b = float(alto)
    except Exception:
        return ""
    if abs(a - b) < 0.001:
        return "cuadrado"
    return "horizontal" if a > b else "vertical"


def _format_content_notes(pedido: dict[str, Any]) -> str:
    contenido = pedido.get("contenido", {}) or {}
    lines: list[str] = []
    for label, key in (
        ("Título", "titulo"),
        ("Subtítulo", "subtitulo"),
        ("Cuerpo", "cuerpo"),
        ("CTA", "llamado_accion"),
    ):
        value = contenido.get(key)
        if value:
            lines.append(f"{label}: {value}")
    extras = contenido.get("extras")
    if extras:
        lines.append("Extras JSON: " + json.dumps(extras, ensure_ascii=False, sort_keys=True))
    notas = pedido.get("notas")
    if notas:
        lines.append(f"Notas: {notas}")
    marca = pedido.get("marca") or {}
    if marca:
        lines.append("Marca JSON: " + json.dumps(marca, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines).strip() or "Intake JSON recibido; revisar contenido estructurado."


def _format_warnings_and_formats(pedido: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    posibles_formatos: list[str] = []
    fmt = pedido.get("formato_sugerido") or ""
    medidas = pedido.get("medidas") or {}

    if fmt:
        posibles_formatos.append(fmt)
        try:
            from ..render.formats import find_format_by_id

            if find_format_by_id(fmt) is None:
                warnings.append(
                    f"formato_sugerido '{fmt}' no existe en el catálogo local; revisar o inferir por medidas."
                )
        except Exception as e:
            warnings.append(f"no se pudo consultar catálogo de formatos: {e}")

    if medidas.get("ancho_cm") and medidas.get("alto_cm"):
        try:
            from ..render.formats import suggest_format

            for candidate in suggest_format(
                float(medidas["ancho_cm"]),
                float(medidas["alto_cm"]),
                str(pedido.get("tipo_pieza") or ""),
            )[:3]:
                if candidate.id not in posibles_formatos:
                    posibles_formatos.append(candidate.id)
        except Exception as e:
            warnings.append(f"no se pudo sugerir formato por medidas: {e}")

    return warnings, posibles_formatos


def _build_pendientes(pedido: dict[str, Any], warnings: list[str]) -> list[str]:
    pendientes: list[str] = []
    medidas = pedido.get("medidas") or {}
    entrega = pedido.get("entrega") or {}
    modificacion = pedido.get("modificacion") or {}

    if not pedido.get("tipo_pieza"):
        pendientes.append("Confirmar tipo de pieza.")
    if not modificacion and not pedido.get("formato_sugerido") and not (
        medidas.get("ancho_cm") and medidas.get("alto_cm")
    ):
        pendientes.append("Confirmar formato sugerido o medidas finales.")
    if not modificacion and not entrega.get("formatos"):
        pendientes.append("Confirmar formatos de entrega.")
    # Los warnings de catálogo no bloquean por sí solos: si hay medidas válidas,
    # el diseñador puede seguir y corregir el formato sugerido después.
    return pendientes


def _suggest_estado(pedido: dict[str, Any], pendientes: list[str]) -> str:
    if pendientes:
        return EstadoJob.PENDIENTE_DATOS.value
    medidas = pedido.get("medidas") or {}
    if pedido.get("modificacion"):
        return EstadoJob.BRIEF_EXTRAIDO.value
    if pedido.get("tipo_pieza") and (pedido.get("formato_sugerido") or (medidas.get("ancho_cm") and medidas.get("alto_cm"))):
        return EstadoJob.LISTO_PARA_DISENAR.value
    return EstadoJob.PENDIENTE_DATOS.value


def _dump_yaml(data: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    from ..jobs.brief import dump_yaml_simple

    return dump_yaml_simple(data)


def _write_estado(job_dir: Path, brief: dict[str, Any]) -> None:
    medidas = brief.get("medidas", {}) or {}
    pendientes = brief.get("pendientes", []) or []
    fmt = ", ".join(brief.get("posibles_formatos", []) or []) or "pendiente"
    medida_txt = "pendiente"
    if medidas.get("ancho_cm") and medidas.get("alto_cm"):
        medida_txt = f"{medidas['ancho_cm']} x {medidas['alto_cm']} cm"
    job_dir.joinpath("estado.md").write_text(
        f"""# Estado del job

Estado: {brief.get('estado')}

## Resumen

- Origen: intake JSON
- Cliente: {brief.get('cliente') or 'pendiente'}
- Tipo pieza: {brief.get('tipo_pieza') or 'pendiente'}
- Medida: {medida_txt}
- Formato(s): {fmt}
- Productos: {', '.join(brief.get('productos') or []) or 'pendiente'}

## Pendientes

{chr(10).join('- [ ] ' + p for p in pendientes) if pendientes else '- [ ] Revisar y aprobar brief.'}

## Próxima acción

- {'Resolver pendientes y luego activar.' if pendientes else 'Revisar brief.yaml y activar con `flujo job activate`.'}
""",
        encoding="utf-8",
    )


def _write_resultado(job_dir: Path, pedido: dict[str, Any], brief: dict[str, Any], warnings: list[str]) -> Path:
    medidas = pedido.get("medidas") or {}
    entrega = pedido.get("entrega") or {}
    modificacion = pedido.get("modificacion") or {}
    lines = [
        f"# Acuse intake JSON — {job_dir.name}",
        "",
        "## Recibido",
        "",
        f"- Folio/job: `{job_dir.name}`",
        f"- Solicitante: {(pedido.get('solicitante') or {}).get('nombre', 'pendiente')}",
        f"- Tipo pieza: {pedido.get('tipo_pieza')}",
        f"- Título: {(pedido.get('contenido') or {}).get('titulo')}",
        f"- Formato sugerido: {pedido.get('formato_sugerido') or 'no indicado'}",
        f"- Medidas: {medidas.get('ancho_cm', '?')} x {medidas.get('alto_cm', '?')} cm",
        f"- Entrega: {', '.join(entrega.get('formatos') or []) or 'pendiente'}",
        "",
        "## Estado inicial",
        "",
        f"- Estado: `{brief.get('estado')}`",
    ]
    if brief.get("pendientes"):
        lines += ["", "## Pendientes", ""] + [f"- {p}" for p in brief["pendientes"]]
    if warnings:
        lines += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    if modificacion:
        lines += [
            "",
            "## Modificación detectada",
            "",
            f"- Pieza existente: `{modificacion.get('pieza_existente')}`",
            f"- Tipo cambio: {', '.join(modificacion.get('tipo_cambio') or [])}",
        ]
        if modificacion.get("proporcion"):
            prop = modificacion["proporcion"]
            lines.append(
                f"- Comando sugerido proporción: `flujo render rescale {modificacion.get('pieza_existente')} -w {prop.get('ancho_cm')} -h {prop.get('alto_cm')}`"
            )
        if modificacion.get("resolucion"):
            res = modificacion["resolucion"]
            lines.append(
                f"- Comando sugerido resolución: `flujo render rescale {modificacion.get('pieza_existente')} --dpi {res.get('dpi')}`"
            )
    lines += [
        "",
        "## Archivos",
        "",
        f"- Brief: `{job_dir / 'brief.yaml'}`",
        f"- Pedido original: `{job_dir / 'pedido_original.txt'}`",
    ]
    out = job_dir / "resultado.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out


def process_json_intake(json_path: Path) -> dict[str, Any]:
    """Valida un archivo JSON de intake y crea un job a partir de él.

    Retorna un dict estable para CLI/tests:
    `{ok, job_dir, brief_path, resultado_path, estado, warnings, errors}`.
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return JsonIntakeResult(ok=False, errors=[f"El archivo no existe: {json_path}"]).as_dict()

    try:
        data = _load_json(json_path)
    except ValueError as e:
        return JsonIntakeResult(ok=False, errors=[str(e)]).as_dict()

    errors = validate_intake_data(data)
    if errors:
        return JsonIntakeResult(ok=False, errors=["Validación de esquema falló", *errors]).as_dict()

    pedido: dict[str, Any] = data.get("pedido", {}) or {}
    contenido = pedido.get("contenido", {}) or {}
    titulo = contenido.get("titulo") or pedido.get("id_externo") or "Pedido Sin Titulo"

    try:
        job_dir = create_job(name=str(titulo), source_path=json_path)
    except Exception as e:
        return JsonIntakeResult(ok=False, errors=[f"No se pudo crear el job: {e}"]).as_dict()

    warnings, posibles_formatos = _format_warnings_and_formats(pedido)
    pendientes = _build_pendientes(pedido, warnings)
    estado = _suggest_estado(pedido, pendientes)
    medidas = pedido.get("medidas") or {}
    entrega = pedido.get("entrega") or {}
    formats = entrega.get("formatos", []) or []
    restricciones = pedido.get("restricciones") or {}
    solicitante = pedido.get("solicitante") or {}

    brief: dict[str, Any] = {
        "id": job_dir.name,
        "estado": estado,
        "origen": "json_intake",
        "cliente": solicitante.get("nombre", ""),
        "proyecto": contenido.get("titulo", ""),
        "tipo_pieza": pedido.get("tipo_pieza", ""),
        "posibles_formatos": posibles_formatos,
        "medidas": {
            "ancho_cm": medidas.get("ancho_cm"),
            "alto_cm": medidas.get("alto_cm"),
            "orientacion": _infer_orientation(medidas.get("ancho_cm"), medidas.get("alto_cm"), medidas.get("orientacion", "")),
            "sangrado_mm": medidas.get("sangrado_mm"),
            "area_segura_mm": medidas.get("area_segura_mm"),
        },
        "entrega": {
            "editable_svg": "editable_svg" in formats if formats else True,
            "vectorizado_svg": "vectorizado_svg" in formats if formats else True,
            "pdf_impresion": "pdf_impresion" in formats if formats else False,
            "zip": "zip" in formats if formats else True,
            "otro": entrega.get("destino", ""),
        },
        "productos": pedido.get("productos", []) or [],
        "contenido": {
            "fuente": "json_intake",
            "texto_aprobado": False,
            "titulo": contenido.get("titulo", ""),
            "subtitulo": contenido.get("subtitulo", ""),
            "cuerpo": contenido.get("cuerpo", ""),
            "llamado_accion": contenido.get("llamado_accion", ""),
            "notas": _format_content_notes(pedido),
        },
        "restricciones": {
            "no_inventar_claims": restricciones.get("no_inventar_claims", True),
            "texto_vectorizado": restricciones.get("texto_vectorizado", True),
            "editable_para_illustrator": restricciones.get("editable_para_illustrator", True),
        },
        "pendientes": pendientes,
        "intake_json": {
            "version": data.get("intake_version"),
            "id_externo": pedido.get("id_externo", ""),
            "area": pedido.get("area", ""),
            "solicitante": solicitante,
            "fecha_limite": entrega.get("fecha_limite", ""),
            "warnings": warnings,
        },
    }
    if pedido.get("modificacion"):
        brief["modificacion"] = pedido["modificacion"]

    brief_path = job_dir / "brief.yaml"
    brief_path.write_text(_dump_yaml(brief), encoding="utf-8")
    _write_estado(job_dir, brief)
    resultado_path = _write_resultado(job_dir, pedido, brief, warnings)

    return JsonIntakeResult(
        ok=True,
        job_dir=str(job_dir),
        brief_path=str(brief_path),
        resultado_path=str(resultado_path),
        estado=estado,
        warnings=warnings,
    ).as_dict()
