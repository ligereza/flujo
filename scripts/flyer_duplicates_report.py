#!/usr/bin/env python3
"""Detecta posibles proyectos flyer duplicados.

No borra nada. Solo genera reporte.

Uso:
  py scripts/flyer_duplicates_report.py

Salida:
  data/flyer_duplicates_report.json
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE = Path("projects/flyer_eventos")
OUT = Path("data/flyer_duplicates_report.json")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


def normalize_url(url):
    return str(url or "").strip().rstrip("/").split("?")[0]


def main():
    by_shortcode = defaultdict(list)
    by_url = defaultdict(list)
    projects = []

    if BASE.exists():
        for manifest in sorted(BASE.glob("*/manifest.json")):
            data = load_json(manifest)
            project = str(manifest.parent).replace("\\", "/")

            ig = data.get("instagram", {}) if isinstance(data.get("instagram"), dict) else {}
            src = data.get("source", {}) if isinstance(data.get("source"), dict) else {}

            shortcode = ig.get("shortcode", "")
            url = normalize_url(ig.get("url", "") or src.get("instagram_url", ""))

            item = {
                "project": project,
                "name": data.get("name", manifest.parent.name),
                "status": data.get("status", ""),
                "shortcode": shortcode,
                "url": url,
            }
            projects.append(item)

            if shortcode:
                by_shortcode[shortcode].append(item)
            if url:
                by_url[url].append(item)

    duplicates = []

    for shortcode, items in sorted(by_shortcode.items()):
        if len(items) > 1:
            duplicates.append({
                "type": "shortcode",
                "key": shortcode,
                "count": len(items),
                "projects": items,
                "suggestion": "Conservar el proyecto más completo y mover duplicados manualmente si corresponde. No borrar automático."
            })

    for url, items in sorted(by_url.items()):
        if len(items) > 1:
            duplicates.append({
                "type": "url",
                "key": url,
                "count": len(items),
                "projects": items,
                "suggestion": "Conservar el proyecto más completo y mover duplicados manualmente si corresponde. No borrar automático."
            })

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_count": len(projects),
        "duplicate_group_count": len(duplicates),
        "duplicates": duplicates,
        "projects": projects,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Reporte duplicados flyer ===")
    print(f"Proyectos revisados: {len(projects)}")
    print(f"Grupos duplicados: {len(duplicates)}")
    print(f"Archivo: {OUT}")

    if duplicates:
        print("")
        for group in duplicates:
            print(f"- {group['type']}={group['key']} ({group['count']} proyectos)")
            for item in group["projects"]:
                print(f"  · {item['project']} | {item['status']}")

    print("")
    print("No se borró ni movió nada.")


if __name__ == "__main__":
    main()
