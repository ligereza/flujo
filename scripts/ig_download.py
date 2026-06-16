#!/usr/bin/env python3
"""Descarga posts públicos de Instagram para proyectos flyer.

Primero intenta yt-dlp. Si falla, marca manual_required sin dejar residuos.

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


def download_with_ytdlp(url: str, output_dir: Path) -> dict:
    try:
        import yt_dlp
    except ImportError:
        return {"status": "error", "reason": "yt_dlp_no_instalado", "url": url}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar archivos anteriores
    for f in output_dir.glob("input_ig.*"):
        f.unlink()
    for f in output_dir.glob("input_ig_video.*"):
        f.unlink()

    tmp = Path(tempfile.mkdtemp(prefix="ig_"))
    try:
        ydl_opts = {
            "outtmpl": str(tmp / "%(id)s.%(ext)s"),
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "writethumbnail": False,
            "writeinfojson": False,
            "writesubtitles": False,
            "skip_download": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files = sorted(tmp.glob("*"))
        images = [f for f in files if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
        videos = [f for f in files if f.suffix.lower() in (".mp4", ".mov", ".webm")]

        if not images and not videos:
            return {"status": "manual_required", "reason": "sin_archivos_descargables", "url": url}

        copied = []
        media_type = "image"
        if images:
            dst = output_dir / "input_ig.jpg"
            shutil.copy2(images[0], dst)
            copied.append(str(dst))
        if videos:
            media_type = "video" if not images else "carousel_or_video"
            dst = output_dir / "input_ig_video.mp4"
            shutil.copy2(videos[0], dst)
            copied.append(str(dst))

        return {
            "status": "downloaded",
            "shortcode": extract_shortcode(url),
            "url": url,
            "media_type": media_type,
            "files": copied,
            "title": info.get("title", "") if info else "",
        }
    except Exception as e:
        return {"status": "manual_required", "reason": str(e), "url": url}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def download_post(url: str, output_dir: Path) -> dict:
    """Descarga un post público de Instagram. Sin instaloader."""
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "reason": "shortcode_no_detectado", "url": url}

    return download_with_ytdlp(url, output_dir)


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
