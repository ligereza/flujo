#!/usr/bin/env python3
import re
import sys
import json
from pathlib import Path
from datetime import datetime

from _common import repo_root, slugify, load_json, write_json, create_flyer_project

try:
    from ig_download import download_post
except ImportError:
    download_post = None

IG_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?P<kind>p|reel|tv)/(?P<code>[A-Za-z0-9_-]+)/*[^\s]*"
)

BASE = repo_root() / "projects" / "flyer_eventos"


def detect_media_guess(kind):
    if kind == "p":
        return "image_or_carousel_possible"
    if kind in ["reel", "tv"]:
        return "video_possible"
    return "unknown"


def normalize_url(kind, code):
    return f"https://www.instagram.com/{kind}/{code}"


def existing_instagram_keys():
    """Devuelve shortcodes/urls ya existentes en manifests."""
    keys = {}

    if not BASE.exists():
        return keys

    for manifest in BASE.glob("*/manifest.json"):
        data = load_json(manifest)
        if not isinstance(data, dict):
            continue

        project = manifest.parent

        ig = data.get("instagram", {}) if isinstance(data.get("instagram"), dict) else {}
        src = data.get("source", {}) if isinstance(data.get("source"), dict) else {}

        shortcode = ig.get("shortcode", "")
        url = ig.get("url", "") or src.get("instagram_url", "")

        if shortcode:
            keys[f"shortcode:{shortcode}"] = str(project).replace("\\", "/")

        if url:
            normalized = url.rstrip("/").split("?")[0]
            keys[f"url:{normalized}"] = str(project).replace("\\", "/")

    return keys


def update_manifest(project_dir, item, index, total):
    manifest = project_dir / "manifest.json"
    data = load_json(manifest) or {}

    kind = item["kind"]
    code = item["code"]
    url = item["url"]
    media_guess = detect_media_guess(kind)

    data["status"] = "from_email_pending_download"
    data["source"] = {
        "type": "email",
        "email_imported_at": datetime.now().isoformat(timespec="seconds"),
        "link_index": index,
        "link_total": total,
    }

    data["instagram"] = {
        "url": url,
        "type": kind,
        "shortcode": code,
        "media_guess": media_guess,
        "download_status": "pending",
        "manual_download_possible": True,
    }

    data.setdefault("extracted_info", {})
    data["extracted_info"].update({
        "event_name": "",
        "producer": "",
        "venue": "",
        "event_date": "",
        "needs_manual_review": True,
    })

    data["manual_review"] = {
        "required": True,
        "reason": "metadata_pending",
        "notes": [
            "Revisar si el post es imagen, carrusel o video.",
            "Si el perfil es privado, shadowban o requiere login, descargar manualmente.",
            "Completar nombre evento, productora, lugar y fecha desde el flyer.",
        ],
    }

    data.setdefault("notes", [])
    data["notes"].append("Creado desde correo. Falta descargar/analizar flyer.")

    if kind in ["reel", "tv"]:
        data["notes"].append("Link parece video. Puede requerir descarga manual o captura de frame.")

    if download_post:
        try:
            result = download_post(url, project_dir / "input")
            data["instagram"]["download_result"] = result
            if result["status"] == "downloaded":
                data["instagram"]["download_status"] = "downloaded"
                data["instagram"]["manual_download_possible"] = False
                data["status"] = "downloaded_pending_review"
                data["notes"].append(f"Descarga automática exitosa: {result.get('media_type', 'unknown')}")
                data["notes"].append(f"Archivos: {', '.join(result.get('files', []))}")
                if result.get("caption"):
                    data["extracted_info"]["caption_from_ig"] = result["caption"]
            else:
                data["notes"].append(f"Descarga automática falló: {result.get('reason', 'unknown')}")
        except Exception as e:
            data["notes"].append(f"Error en descarga automática: {e}")

    write_json(manifest, data)


def extract_instagram_links(text):
    found = []

    for m in IG_RE.finditer(text):
        kind = m.group("kind")
        code = m.group("code")
        url = normalize_url(kind, code)

        found.append({
            "kind": kind,
            "code": code,
            "url": url
        })

    unique = []
    seen = set()
    for item in found:
        if item["url"] not in seen:
            unique.append(item)
            seen.add(item["url"])

    return unique


def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]

    if len(args) < 1:
        print('Uso: py scripts/flyer_from_email.py "ruta/correo.txt" [--force]')
        sys.exit(1)

    email_path = Path(args[0])

    if not email_path.exists():
        print(f"ERROR: no existe archivo: {email_path}")
        sys.exit(1)

    text = email_path.read_text(encoding="utf-8", errors="ignore")
    items = extract_instagram_links(text)

    if not items:
        print("No encontré links de Instagram.")
        sys.exit(0)

    existing = existing_instagram_keys()

    print(f"Encontré {len(items)} link(s) de Instagram.")
    print(f"Modo force: {'sí' if force else 'no'}")
    print("")

    created = 0
    skipped = 0

    for i, item in enumerate(items, start=1):
        kind = item["kind"]
        code = item["code"]
        url = item["url"]
        media_guess = detect_media_guess(kind)

        key_shortcode = f"shortcode:{code}"
        key_url = f"url:{url}"

        if not force and (key_shortcode in existing or key_url in existing):
            found_project = existing.get(key_shortcode) or existing.get(key_url)
            print(f"[{i}/{len(items)}] DUPLICADO, se omite")
            print(f"URL: {url}")
            print(f"Existe en: {found_project}")
            print("Usa --force si realmente quieres crear otro proyecto.")
            print("")
            skipped += 1
            continue

        name = f"email_evento_{i:02d}"

        print(f"[{i}/{len(items)}] Creando proyecto")
        print(f"URL: {url}")
        print(f"Tipo: {kind}")
        print(f"Media guess: {media_guess}")

        project = create_flyer_project(BASE, name, source_type="email")
        update_manifest(project, item, i, len(items))

        existing[key_shortcode] = str(project).replace("\\", "/")
        existing[key_url] = str(project).replace("\\", "/")

        created += 1
        print(f"OK: {project}")
        print("")

    print("Resumen:")
    print(f"- Creados: {created}")
    print(f"- Omitidos por duplicado: {skipped}")
    print("")
    print("Revisa con:")
    print("bash scripts/flyer_list.sh")
    print("bash scripts/flyer_index.sh")
    print("bash scripts/flyer_status_latest.sh")


if __name__ == "__main__":
    main()
