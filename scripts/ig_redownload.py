#!/usr/bin/env python3
"""Reintenta descarga de Instagram en proyectos flyer fallidos.

Uso:
  py scripts/ig_redownload.py          # solo pendientes/manual
  py scripts/ig_redownload.py --all    # todos
  py scripts/ig_redownload.py --project projects/flyer_eventos/2026-06-16_ig_ABC123
"""

import sys
from pathlib import Path

from _common import repo_root, load_json, write_json

try:
    from ig_download import download_post
except ImportError:
    print("ERROR: no se pudo importar ig_download")
    sys.exit(1)

BASE = repo_root() / "projects" / "flyer_eventos"

def redownload_project(project_dir: Path) -> dict:
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        return {"status": "skip", "reason": "no_manifest"}

    data = load_json(manifest_path) or {}
    ig = data.get("instagram", {})
    url = ig.get("url", "")
    if not url:
        return {"status": "skip", "reason": "no_url"}

    download_status = ig.get("download_status", "")
    # por defecto solo reintentar fallidos
    result = download_post(url, project_dir / "input")

    ig["download_result"] = result
    ig["download_retry_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")

    if result["status"] == "downloaded":
        ig["download_status"] = "downloaded"
        ig["manual_download_possible"] = False
        ig["media_type"] = result.get("media_type", "")
        ig["file_count"] = result.get("file_count", 0)
        ig["owner"] = result.get("owner", "")
        ig["date_utc"] = result.get("date", "")
        data["status"] = "downloaded_pending_review"
        data.setdefault("notes", []).append(f"Redescarga exitosa: {result.get('media_type')}")
        if result.get("caption"):
            data.setdefault("extracted_info", {})["caption_from_ig"] = result["caption"]
    else:
        ig["download_status"] = "failed"
        data.setdefault("notes", []).append(f"Redescarga falló: {result.get('reason')}")

    data["instagram"] = ig
    write_json(manifest_path, data)
    return result

def main():
    re_all = "--all" in sys.argv
    project_arg = None
    for a in sys.argv[1:]:
        if not a.startswith("--") and Path(a).exists():
            project_arg = Path(a)

    if project_arg:
        projects = [project_arg]
    else:
        projects = sorted([p for p in BASE.glob("*") if p.is_dir() and (p / "manifest.json").exists()]) if BASE.exists() else []

    if not projects:
        print("No hay proyectos flyer.")
        return

    ok = 0
    fail = 0
    skip = 0

    for proj in projects:
        manifest = load_json(proj / "manifest.json") or {}
        ig = manifest.get("instagram", {})
        status = ig.get("download_status", "")
        url = ig.get("url", "")

        if not url:
            continue

        if not re_all and status == "downloaded":
            skip += 1
            continue

        print(f"→ {proj.name} | {url} | status={status}")
        res = redownload_project(proj)
        if res.get("status") == "downloaded":
            print(f"  OK descargado: {res.get('media_type')} | {res.get('file_count',0)} archivos")
            ok += 1
        elif res.get("status") == "skip":
            skip += 1
        else:
            print(f"  FAIL: {res.get('reason')}")
            fail += 1

    print("")
    print(f"Resumen: OK={ok} FAIL={fail} SKIP={skip}")

if __name__ == "__main__":
    main()
