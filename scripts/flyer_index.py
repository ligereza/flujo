#!/usr/bin/env python3
"""Genera un índice simple de proyectos flyer.

Uso:
  py scripts/flyer_index.py

Salida:
  - imprime resumen en consola
  - crea/actualiza data/flyer_index.json
"""

import json
from pathlib import Path
from datetime import datetime

BASE = Path("projects/flyer_eventos")
OUT = Path("data/flyer_index.json")


def load_manifest(project: Path):
    manifest = project / "manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "error": f"manifest inválido: {exc}",
            "project": str(project).replace("\\", "/")
        }


def get_nested(data, *keys, default=""):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def main():
    projects = []

    if BASE.exists():
        for project in sorted(p for p in BASE.iterdir() if p.is_dir()):
            data = load_manifest(project)
            if data is None:
                projects.append({
                    "project": str(project).replace("\\", "/"),
                    "name": project.name,
                    "status": "missing_manifest",
                    "instagram_url": "",
                    "instagram_type": "",
                    "media_guess": "",
                    "needs_manual_review": True,
                })
                continue

            projects.append({
                "project": str(project).replace("\\", "/"),
                "name": data.get("name", project.name),
                "status": data.get("status", ""),
                "instagram_url": get_nested(data, "instagram", "url") or get_nested(data, "source", "instagram_url"),
                "instagram_type": get_nested(data, "instagram", "type"),
                "media_guess": get_nested(data, "instagram", "media_guess"),
                "needs_manual_review": bool(
                    get_nested(data, "manual_review", "required", default=False)
                    or get_nested(data, "extracted_info", "needs_manual_review", default=False)
                ),
            })

    index = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(projects),
        "projects": projects,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Índice flyer ===")
    print(f"Proyectos: {len(projects)}")
    print(f"Archivo: {OUT}")
    print("")

    if not projects:
        print("No hay proyectos flyer.")
        return

    for item in projects:
        flag = "MANUAL" if item["needs_manual_review"] else "OK"
        media = item["media_guess"] or "sin-media"
        print(f"- [{flag}] {item['project']} | {item['status']} | {media}")


if __name__ == "__main__":
    main()
