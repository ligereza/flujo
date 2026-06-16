#!/usr/bin/env python3
"""Descarga posts públicos de Instagram para proyectos flyer.

Uso:
  py scripts/ig_download.py <url> <output_dir>

Ejemplo:
  py scripts/ig_download.py https://www.instagram.com/p/ABC123/ projects/flyer_eventos/2026-06-16_evento/input
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


def download_post(url: str, output_dir: Path) -> dict:
    """Descarga un post público de Instagram. Devuelve metadata del resultado."""
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "reason": "shortcode_no_detectado", "url": url}

    try:
        import instaloader
    except ImportError:
        return {"status": "error", "reason": "instaloader_no_instalado", "url": url}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar archivos anteriores
    for f in output_dir.glob("input_ig.*"):
        f.unlink()

    tmp = Path(tempfile.mkdtemp(prefix="ig_"))

    try:
        L = instaloader.Instaloader(
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            download_geotags=False,
            filename_pattern="{shortcode}",
        )
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        L.download_post(post, target=str(tmp))

        # Buscar archivos descargados
        images = sorted(tmp.glob("*.jpg"))
        videos = sorted(tmp.glob("*.mp4"))
        files = sorted(tmp.glob("*"))

        if not images and not videos:
            return {"status": "error", "reason": "sin_archivos", "url": url}

        # Priorizar imagen; si es video, copiar ambos
        media_type = "image"
        if not images and videos:
            media_type = "video"
        elif images and videos:
            media_type = "carousel_or_video"

        copied = []
        if images:
            src = images[0]
            dst = output_dir / "input_ig.jpg"
            shutil.copy2(src, dst)
            copied.append(str(dst))
        if videos:
            src = videos[0]
            dst = output_dir / "input_ig_video.mp4"
            shutil.copy2(src, dst)
            copied.append(str(dst))

        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": media_type,
            "files": copied,
            "caption": post.caption or "",
        }

    except instaloader.exceptions.LoginRequiredException:
        return {"status": "manual_required", "reason": "login_requerido", "url": url}
    except instaloader.exceptions.ProfileNotExistsException:
        return {"status": "manual_required", "reason": "perfil_no_existe", "url": url}
    except Exception as e:
        return {"status": "manual_required", "reason": str(e), "url": url}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
