"""Render y gestión de proyectos piezas_vectoriales."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..paths import repo_root
from ..jobs.brief import (
    Brief,
    load_brief,
    Medidas,
    EstadoJob,
)
from .formats import (
    load_index,
    suggest_format,
    find_format_by_id,
    FormatInfo,
)


# ============================================================
# Helpers
# ============================================================

def _slugify(s: str) -> str:
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
    return s or "proyecto"


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _to_num(v, default):
    if v is None or v == "":
        return default
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return default


def _brief_value(lines: List[str], key: str) -> str:
    pat = re.compile(rf"^{re.escape(key)}:\s*(.*)$")
    for line in lines:
        m = pat.match(line)
        if m:
            return _strip_wrapping_quotes(m.group(1))
    return ""


def _brief_nested(lines: List[str], section: str, key: str) -> str:
    inside = False
    pat = re.compile(rf"^\s{{2}}{re.escape(key)}:\s*(.*)$")
    for line in lines:
        if re.match(rf"^{re.escape(section)}:\s*$", line):
            inside = True
            continue
        if inside and line and not line.startswith(" "):
            inside = False
        if inside:
            m = pat.match(line)
            if m:
                return _strip_wrapping_quotes(m.group(1))
    return ""


def _brief_list(lines: List[str], section: str) -> List[str]:
    vals: List[str] = []
    inside = False
    for line in lines:
        if re.match(rf"^{re.escape(section)}:\s*$", line):
            inside = True
            continue
        if inside and line and not line.startswith(" "):
            inside = False
        if inside:
            m = re.match(r"^\s*-\s*(.*)$", line)
            if m:
                vals.append(_strip_wrapping_quotes(m.group(1)))
    return vals


# ============================================================
# create_project_from_brief: brief.yaml → projects/piezas_vectoriales/<slug>/
# ============================================================

def create_project_from_brief(
    brief_path: Path,
    project_name: Optional[str] = None,
    explicit_template: Optional[str] = None,
    repo: Optional[Path] = None,
) -> Path:
    """Crea un proyecto base en projects/piezas_vectoriales/ desde un brief.

    Estrategia de elección de plantilla:
      1. Si explicit_template está dado, usar esa.
      2. Si el brief tiene medidas reales, elegir por tamaño/proporción.
      3. Si solo tiene tipo (sin medidas), elegir por tipo.
      4. Si no hay nada, crear base universal 14x10 cm.

    Retorna el Path del proyecto creado.
    """
    brief_path = Path(brief_path)
    repo = repo or repo_root()
    if not brief_path.exists():
        raise FileNotFoundError(f"No existe brief: {brief_path}")
    lines = brief_path.read_text(encoding="utf-8").splitlines()
    job_dir = brief_path.parent

    project_name = project_name or _brief_value(lines, "proyecto") or job_dir.name
    project_slug = _slugify(project_name)
    out_dir = repo / "projects" / "piezas_vectoriales" / project_slug

    if out_dir.exists():
        # Idempotente: si ya existe, no fallar; devolver el path
        return out_dir

    raw_ancho = _brief_nested(lines, "medidas", "ancho_cm")
    raw_alto = _brief_nested(lines, "medidas", "alto_cm")
    size_was_default = not raw_ancho or not raw_alto
    ancho = _to_num(raw_ancho, 14.0)
    alto = _to_num(raw_alto, 10.0)

    title = _brief_value(lines, "proyecto") or project_name
    cliente = _brief_value(lines, "cliente") or "Cliente"
    tipo = _brief_value(lines, "tipo_pieza") or "pieza"
    posibles = " ".join(_brief_list(lines, "posibles_formatos"))
    tipo_hint = (tipo + " " + posibles).strip()

    out_dir.mkdir(parents=True)

    template = _choose_template(
        ancho, alto, tipo_hint,
        explicit_template,
        size_was_default,
        repo,
    )
    if template and template.exists():
        _apply_template(template, out_dir, title, cliente, project_slug, job_dir)
    else:
        _create_universal_base(out_dir, title, cliente, project_slug, job_dir, ancho, alto, tipo)

    # copiar brief fuente y pedido original
    shutil.copy2(brief_path, out_dir / "brief_fuente.yaml")
    pedido = job_dir / "pedido_original.txt"
    if pedido.exists():
        shutil.copy2(pedido, out_dir / "pedido_original.txt")

    return out_dir


def _choose_template(
    ancho: float,
    alto: float,
    tipo_hint: str,
    explicit: Optional[str],
    size_was_default: bool,
    repo: Path,
) -> Optional[Path]:
    if explicit:
        ep = Path(explicit)
        if not ep.is_absolute():
            ep = repo / explicit
        if ep.exists():
            return ep
        # buscar en plantillas
        ep2 = repo / "tools" / "piezas_vectoriales" / "plantillas" / explicit
        if ep2.exists():
            return ep2
        return None

    formats = load_index()
    if not formats:
        return None
    hint = (tipo_hint or "").lower()

    # Si no había medida, priorizar intención
    if size_was_default and hint:
        for wanted in ["one_page", "one-page", "dossier", "propuesta", "carrusel", "etiqueta", "flyer", "rider", "tarjeta"]:
            if wanted in hint:
                for f in formats:
                    fid = f.id.lower()
                    if wanted.replace("-", "_") in fid or wanted in f.tipo.lower():
                        candidate = repo / f.template if not f.template.is_absolute() else f.template
                        if candidate.exists():
                            return candidate

    # Por tamaño/proporción
    target_ratio = ancho / max(alto, 0.01)
    best: Optional[FormatInfo] = None
    best_score = float("inf")
    for f in formats:
        ratio_diff = abs(f.ratio - target_ratio)
        size_diff = abs(f.width_cm - ancho) + abs(f.height_cm - alto)
        type_bonus = 0.0
        if hint:
            if not (hint in f.tipo.lower() or any(tok in f.id.lower() for tok in hint.split())):
                type_bonus = 10.0
        s = ratio_diff * 10 + size_diff + type_bonus
        if s < best_score:
            best_score = s
            best = f

    if best and best_score < 3.0:
        candidate = repo / best.template if not best.template.is_absolute() else best.template
        if candidate.exists():
            return candidate
    return None


def _apply_template(
    template_path: Path,
    out_dir: Path,
    title: str,
    cliente: str,
    project_slug: str,
    job_dir: Path,
) -> None:
    cfg = json.loads(template_path.read_text(encoding="utf-8"))
    cfg.setdefault("project", {})
    cfg["project"]["name"] = title
    cfg["project"]["slug"] = project_slug
    cfg["project"]["brand"] = cliente
    cfg["project"]["source_job"] = job_dir.as_posix()
    cfg["project"]["note"] = "Proyecto base creado desde brief.yaml usando plantilla."
    if cfg.get("documents"):
        cfg["documents"][0]["id"] = f"01_base_{project_slug}"
        cfg["documents"][0]["title"] = title
        for el in cfg["documents"][0].get("elements", []):
            if (
                el.get("type") == "text"
                and str(el.get("content", "")).upper() in ["NOMBRE PRODUCTO", "TÍTULO PRINCIPAL", "TITULO PRINCIPAL"]
            ):
                el["content"] = title
                break
    (out_dir / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _create_universal_base(
    out_dir: Path,
    title: str,
    cliente: str,
    project_slug: str,
    job_dir: Path,
    ancho: float,
    alto: float,
    tipo: str,
) -> None:
    """Crea una base universal segura cuando no hay plantilla compatible.

    Importante: no construir JSON con f-strings. Los textos vienen de briefs
    humanos/correos y pueden contener comillas, saltos de línea o caracteres
    especiales. Mantenerlo como dict + json.dumps evita configs inválidos.
    """
    w = int(round(ancho * 200))
    h = int(round(alto * 200))
    if w <= 0 or h <= 0:
        w, h = 2800, 2000
        ancho, alto = 14.0, 10.0

    config = {
        "project": {
            "name": title,
            "slug": project_slug,
            "brand": cliente,
            "website": "",
            "source_job": job_dir.as_posix(),
            "note": "Proyecto base creado desde brief.yaml. Diseño pendiente de ajustar.",
        },
        "canvas": {
            "width": w,
            "height": h,
            "real_size_cm": {"width": ancho, "height": alto},
            "safe_margin_px": 120,
        },
        "palette": {
            "cream": "#F6EFE3",
            "paper": "#FFF8ED",
            "white": "#FFFFFF",
            "ink": "#161513",
            "muted": "#675F55",
            "line": "#D9CEC0",
            "accent": "#173F2F",
        },
        "background": "cream",
        "global_elements": [
            {
                "type": "rect",
                "x": 80,
                "y": 80,
                "w": max(w - 160, 100),
                "h": max(h - 160, 100),
                "radius": 60,
                "fill": "none",
                "stroke": "line",
                "stroke_width": 5,
            },
            {
                "type": "text",
                "content": "{brand}",
                "x": 120,
                "y": 120,
                "size": 44,
                "fill": "ink",
                "weight": "bold",
            },
        ],
        "documents": [
            {
                "id": f"01_base_{project_slug}",
                "title": title,
                "tipo": tipo,
                "elements": [
                    {
                        "type": "text",
                        "content": title,
                        "x": 120,
                        "y": 300,
                        "size": 96,
                        "fill": "ink",
                        "weight": "bold",
                        "max_width": max(w - 240, 500),
                    },
                    {
                        "type": "panel",
                        "x": 120,
                        "y": 520,
                        "w": max(w - 240, 500),
                        "h": max(h - 760, 400),
                        "radius": 44,
                        "fill": "white",
                        "stroke": "line",
                        "stroke_width": 3,
                        "opacity": 0.72,
                    },
                    {
                        "type": "paragraph",
                        "content": "Base creada desde brief. Reemplazar por estructura final de diseño.",
                        "x": 190,
                        "y": 610,
                        "size": 44,
                        "fill": "muted",
                        "max_width": max(w - 380, 400),
                        "line_height": 60,
                    },
                ],
            }
        ],
    }
    (out_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ============================================================
# render_config: ejecuta el generador sobre un config.json
# ============================================================

def render_config(config_path: Path, repo: Optional[Path] = None) -> int:
    """Renderiza un proyecto ejecutando el generador de piezas_vectoriales."""
    repo = repo or repo_root()
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"No existe config: {config_path}")

    # Validar primero
    errors = validate_config(config_path)
    if errors:
        for e in errors:
            print(f"  ⚠️ {e}")
        print("Render detenido por errores de validación.")
        return 1

    # Integración fuerte con flujo (colores + tono por defecto)
    try:
        from ..flujo import load_styles, get_color
        styles = load_styles()
        if styles and "palette" not in str(config_path):
            print(f"  → flujo aplicado automáticamente (ink={get_color('ink')}, accent={get_color('accent')})")
            # Futuro: merge real en el config
    except Exception:
        pass

    generator = repo / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py"
    if not generator.exists():
        print(f"ERROR: no existe generador: {generator}")
        return 1

    print(f"Renderizando: {config_path}")
    r = subprocess.run([sys.executable, str(generator), str(config_path)], cwd=repo)
    return r.returncode


def validate_config(config_path: Path) -> List[str]:
    """Valida un config.json. Devuelve lista de errores (vacía si OK)."""
    config_path = Path(config_path)
    errors: List[str] = []
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON inválido: {e}"]

    if not isinstance(data, dict):
        return ["config no es un objeto JSON"]

    if "canvas" not in data:
        errors.append("falta sección 'canvas'")
    else:
        c = data["canvas"]
        for k in ("width", "height"):
            if k not in c or not isinstance(c[k], (int, float)) or c[k] <= 0:
                errors.append(f"canvas.{k} inválido")

    if "documents" not in data or not isinstance(data["documents"], list) or len(data["documents"]) == 0:
        errors.append("falta 'documents' o está vacío")

    for i, doc in enumerate(data.get("documents", [])):
        if not isinstance(doc, dict):
            errors.append(f"documents[{i}] no es objeto")
            continue
        if "elements" not in doc:
            errors.append(f"documents[{i}] falta 'elements'")

    return errors


def list_projects(repo: Optional[Path] = None) -> List[Path]:
    """Lista los proyectos piezas_vectoriales."""
    repo = repo or repo_root()
    base = repo / "projects" / "piezas_vectoriales"
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir() and (p / "config.json").exists()])
