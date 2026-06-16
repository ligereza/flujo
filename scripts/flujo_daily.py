#!/usr/bin/env python3
"""Genera un reporte diario de próximas acciones del repo flujo."""
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

from _common import repo_root, load_json

ROOT = repo_root()
OUTPUT = ROOT / "context" / "DAILY.md"

PRIORITY_ORDER = {"alta": 0, "media": 1, "baja": 2}


def priority_label(score: int) -> str:
    if score >= 70:
        return "alta"
    if score >= 40:
        return "media"
    return "baja"


def score_job(brief_path: Path) -> dict | None:
    if not brief_path.exists():
        return None
    try:
        data = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    estado = data.get("estado", "borrador")
    pendientes = data.get("pendientes", []) or []
    entrega = data.get("entrega", {})
    texto_aprobado = data.get("contenido", {}).get("texto_aprobado", False)

    score = 0
    reason = []

    if estado in ("borrador", "pendiente_datos"):
        score += 80
        reason.append("faltan datos críticos")
    elif estado == "listo_para_disenar":
        score += 50
        reason.append("listo para diseñar")
    elif estado == "en_diseno":
        score += 30
        reason.append("en diseño")

    if pendientes:
        score += min(len(pendientes) * 5, 20)
        reason.append(f"{len(pendientes)} pendientes")

    if not texto_aprobado:
        score += 10
        reason.append("texto no aprobado")

    return {
        "type": "job",
        "path": brief_path.parent,
        "name": brief_path.parent.name,
        "estado": estado,
        "score": score,
        "priority": priority_label(score),
        "reason": ", ".join(reason) or "revisar",
        "pendientes": pendientes[:5],
    }


def format_pendiente(p):
    if isinstance(p, dict):
        return " — ".join(f"{k}: {v}" for k, v in p.items())
    return str(p)


def score_flyer(manifest_path: Path) -> dict | None:
    data = load_json(manifest_path)
    if not data:
        return None

    status = data.get("status", "created")
    name = data.get("name", manifest_path.parent.name)
    instagram = data.get("instagram", {})

    score = 0
    reason = []

    if status == "from_email_pending_download":
        score += 75
        reason.append("falta descargar de Instagram")
    elif status == "created":
        score += 25
        reason.append("creado, falta completar datos")
    elif status == "in_progress":
        score += 40
        reason.append("en progreso")

    if instagram.get("media_guess") == "video_possible":
        score += 10
        reason.append("parece video")

    return {
        "type": "flyer",
        "path": manifest_path.parent,
        "name": name,
        "status": status,
        "score": score,
        "priority": priority_label(score),
        "reason": ", ".join(reason) or "revisar",
    }


def score_pieza(config_path: Path) -> dict | None:
    data = load_json(config_path)
    if not data:
        return None

    project = config_path.parent
    salida = project / "salida_generada"
    editable = salida / "01_editables_svg" if salida.exists() else None

    score = 0
    reason = []

    if not salida.exists() or not any(editable.glob("*.svg")) if editable else True:
        score += 60
        reason.append("sin salidas generadas")
    else:
        score += 10
        reason.append("salidas generadas, revisar")

    return {
        "type": "pieza",
        "path": project,
        "name": data.get("project", {}).get("name", project.name),
        "score": score,
        "priority": priority_label(score),
        "reason": ", ".join(reason) or "revisar",
    }


def collect_items():
    items = []

    # Jobs
    for brief in (ROOT / "jobs").glob("*/brief.yaml"):
        if brief.parent.name.startswith("_"):
            continue
        item = score_job(brief)
        if item:
            items.append(item)

    # Flyers
    for manifest in (ROOT / "projects" / "flyer_eventos").glob("*/manifest.json"):
        item = score_flyer(manifest)
        if item:
            items.append(item)

    # Piezas vectoriales
    for config in (ROOT / "projects" / "piezas_vectoriales").glob("*/config.json"):
        item = score_pieza(config)
        if item:
            items.append(item)

    items.sort(key=lambda x: (PRIORITY_ORDER[x["priority"]], -x["score"]))
    return items


def render_report(items):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Daily report — {date}",
        "",
        "Resumen de próximas acciones ordenadas por prioridad.",
        "",
        f"- Total items: {len(items)}",
        f"- Alta: {sum(1 for i in items if i['priority'] == 'alta')}",
        f"- Media: {sum(1 for i in items if i['priority'] == 'media')}",
        f"- Baja: {sum(1 for i in items if i['priority'] == 'baja')}",
        "",
        "## Acciones prioritarias",
        "",
    ]

    if not items:
        lines.append("No hay items pendientes. 🎉")
        return "\n".join(lines)

    current_priority = None
    for item in items:
        if item["priority"] != current_priority:
            current_priority = item["priority"]
            lines.append(f"### Prioridad {current_priority}")
            lines.append("")

        lines.append(f"- **[{item['type']}]** `{item['name']}` — {item['reason']} (score: {item['score']})")
        if item["type"] == "job" and item.get("pendientes"):
            for p in item["pendientes"]:
                lines.append(f"  - {format_pendiente(p)}")
        lines.append(f"  - Ruta: `{item['path']}`")
        lines.append("")

    lines.extend([
        "## Comandos rápidos",
        "",
        "```bash",
        "py scripts/flujo.py health",
        "py scripts/flujo.py job-next",
        "py scripts/flujo.py summary",
        "```",
    ])

    return "\n".join(lines)


def main():
    items = collect_items()
    report = render_report(items)
    OUTPUT.write_text(report, encoding="utf-8")
    print(f"Reporte generado: {OUTPUT}")
    print("")
    print(report)


if __name__ == "__main__":
    main()
