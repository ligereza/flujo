#!/usr/bin/env python3
"""Descarga posts públicos de Instagram para proyectos flyer.

Usa únicamente instaloader. Sin yt-dlp.

Uso:
  py scripts/ig_download.py <url> <output_dir>
"""

import re
import sys
import shutil
import tempfile
from pathlib import Path

from _common import repo_root

ROOT = repo_root()

def extract_shortcode(url: str) -> str | None:
    patterns = [
        r"/p/([A-Za-z0-9_-]+)",
        r"/reel/([A-Za-z0-9_-]+)",
        r"/tv/([A-Za-z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None

def download_with_instaloader(url: str, output_dir: Path) -> dict:
    try:
        import instaloader
    except ImportError:
        return {"status": "error", "reason": "instaloader_no_instalado", "url": url}

    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "reason": "shortcode_no_detectado", "url": url}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar archivos anteriores de IG
    for f in output_dir.glob("input_ig*"):
        f.unlink()
    for f in output_dir.glob("ig_caption.txt"):
        f.unlink()

    tmp = Path(tempfile.mkdtemp(prefix="ig_"))
    try:
        L = instaloader.Instaloader(
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            download_geotags=False,
            filename_pattern="{shortcode}",
            quiet=True,
        )
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=str(tmp))

        images = sorted(tmp.glob("*.jpg"))
        videos = sorted(tmp.glob("*.mp4"))

        if not images and not videos:
            return {"status": "manual_required", "reason": "sin_archivos", "url": url}

        copied = []
        media_type = "image"

        # Copiar todas las imágenes (carrusel)
        if images:
            for i, img in enumerate(images, 1):
                if i == 1:
                    dst = output_dir / "input_ig.jpg"
                else:
                    dst = output_dir / f"input_ig_{i}.jpg"
                shutil.copy2(img, dst)
                copied.append(str(dst))

            if len(images) > 1:
                media_type = "carousel"

        # Copiar video si existe
        if videos:
            media_type = "video" if not images else "carousel_or_video"
            dst = output_dir / "input_ig_video.mp4"
            shutil.copy2(videos[0], dst)
            copied.append(str(dst))

        # Guardar caption aparte, útil para revisar
        caption = post.caption or ""
        if caption:
            (output_dir / "ig_caption.txt").write_text(caption, encoding="utf-8")

        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": media_type,
            "files": copied,
            "file_count": len(copied),
            "caption": caption,
            "owner": post.owner_username,
            "date": post.date_utc.isoformat() if post.date_utc else "",
            "is_video": post.is_video,
        }

    except Exception as e:
        err = str(e)
        # Mensajes más claros para casos comunes
        if "Login required" in err or "login" in err.lower():
            err = "login_requerido_o_privado"
        elif "not found" in err.lower() or "does not exist" in err.lower():
            err = "post_no_encontrado"
        elif "429" in err or "Too Many Requests" in err:
            err = "rate_limit"
        return {"status": "manual_required", "reason": err, "url": url}

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def download_post(url: str, output_dir: Path) -> dict:
    """Descarga un post público de Instagram con instaloader.

    API compatible con la versión anterior que tenía fallback yt-dlp.
    """
    return download_with_instaloader(url, output_dir)

def main():
    if len(sys.argv) < 3:
        print("Uso: py scripts/ig_download.py <url> <output_dir>")
        sys.exit(1)
    url = sys.argv[1]
    output_dir = Path(sys.argv[2])
    result = download_post(url, output_dir)
    print(result)
    if result["status"] == "downloaded":
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
