import re
import sys
from datetime import datetime
from pathlib import Path
from ..paths import flyer_base
from ..manifest import load_json, write_json
from .project import create_flyer_project
from ..ig.download import download_post

IG_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"(?:[A-Za-z0-9_.]+/)?"
    r"(?P<kind>p|reel|reels|tv)/(?P<code>[A-Za-z0-9_-]+)"
    r"/?",
    re.IGNORECASE,
)

def detect_media_guess(kind: str) -> str:
    return "video_possible" if kind in ("reel", "tv") else "image_or_carousel_possible"

def normalize_url(kind: str, code: str) -> str:
    # Instagram canonical route is /reel/ even if user pasted /reels/.
    kind = "reel" if kind.lower() == "reels" else kind.lower()
    return f"https://www.instagram.com/{kind}/{code}"

def extract_instagram_links(text: str):
    found = []
    seen = set()
    for m in IG_RE.finditer(text):
        kind, code = m.group("kind"), m.group("code")
        kind = "reel" if kind.lower() == "reels" else kind.lower()
        url = normalize_url(kind, code)
        if url not in seen:
            found.append({"kind": kind, "code": code, "url": url})
            seen.add(url)
    return found

def existing_instagram_keys(base: Path):
    keys = {}
    if not base.exists():
        return keys
    for manifest_path in base.glob("*/manifest.json"):
        data = load_json(manifest_path) or {}
        ig = data.get("instagram", {}) if isinstance(data.get("instagram"), dict) else {}
        shortcode = ig.get("shortcode", "")
        url = ig.get("url", "")
        proj = str(manifest_path.parent).replace("\\", "/")
        if shortcode:
            keys[f"shortcode:{shortcode}"] = proj
        if url:
            keys[f"url:{url.rstrip('/').split('?')[0]}"] = proj
    return keys

def update_manifest(project_dir: Path, item: dict, index: int, total: int):
    manifest_path = project_dir / "manifest.json"
    data = load_json(manifest_path) or {}
    kind, code, url = item["kind"], item["code"], item["url"]

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
        "media_guess": detect_media_guess(kind),
        "download_status": "pending",
        "manual_download_possible": True,
    }
    data.setdefault("extracted_info", {})
    data["extracted_info"].update({
        "event_name": "", "producer": "", "venue": "", "event_date": "",
        "needs_manual_review": True,
    })
    data["manual_review"] = {
        "required": True,
        "reason": "metadata_pending",
        "notes": [
            "Revisar si el post es imagen, carrusel o video.",
            "Si el perfil es privado, descargar manualmente.",
            "Completar nombre evento, productora, lugar y fecha.",
        ],
    }
    data.setdefault("notes", [])
    data["notes"].append("Creado desde correo. Falta descargar/analizar flyer.")

    # descarga
    try:
        result = download_post(url, project_dir / "input")
        ig = data["instagram"]
        ig["download_result"] = result
        if result.get("status") == "downloaded":
            ig.update({
                "download_status": "downloaded",
                "manual_download_possible": False,
                "media_type": result.get("media_type", ""),
                "file_count": result.get("file_count", 0),
                "owner": result.get("owner", ""),
                "date_utc": result.get("date", ""),
            })
            data["status"] = "downloaded_pending_review"
            data["notes"].append(f"Descarga automática exitosa: {result.get('media_type')}")
            if result.get("caption"):
                data["extracted_info"]["caption_from_ig"] = result["caption"]
            if result.get("owner"):
                data["extracted_info"]["producer_suggested"] = result["owner"]
        else:
            data["notes"].append(f"Descarga falló: {result.get('reason')}")
    except Exception as e:
        data["notes"].append(f"Error descarga: {e}")

    write_json(manifest_path, data)

def import_from_email(email_path: Path, force: bool = False) -> dict:
    text = Path(email_path).read_text(encoding="utf-8", errors="ignore")
    items = extract_instagram_links(text)
    base = flyer_base()
    existing = existing_instagram_keys(base)
    created = skipped = 0
    for i, item in enumerate(items, 1):
        code, url = item["code"], item["url"]
        if not force and (f"shortcode:{code}" in existing or f"url:{url}" in existing):
            skipped += 1
            continue
        project = create_flyer_project(base, f"ig_{code}", source_type="email")
        update_manifest(project, item, i, len(items))
        existing[f"shortcode:{code}"] = str(project)
        existing[f"url:{url}"] = str(project)
        created += 1
    return {"found": len(items), "created": created, "skipped": skipped}

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Importar flyers desde correo con links IG")
    ap.add_argument("email", help="ruta/correo.txt")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    res = import_from_email(args.email, force=args.force)
    print(f"Creados: {res['created']} | Omitidos: {res['skipped']} | Encontrados: {res['found']}")
    return 0
