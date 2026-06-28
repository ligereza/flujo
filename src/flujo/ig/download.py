import re
import shutil
import tempfile
import time
from pathlib import Path

SHORTCODE_RE = [
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?p/([A-Za-z0-9_-]+)"),
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?reels?/([A-Za-z0-9_-]+)"),
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?tv/([A-Za-z0-9_-]+)"),
]

def extract_shortcode(url: str) -> str | None:
    for rx in SHORTCODE_RE:
        m = rx.search(url)
        if m:
            return m.group(1)
    return None

def download_post(url: str, output_dir: Path, retries: int = 1) -> dict:
    try:
        import instaloader
    except ImportError:
        return {"status": "error", "reason": "instaloader_no_instalado", "url": url}

    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "reason": "shortcode_no_detectado", "url": url}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for f in output_dir.glob("input_ig*"):
        f.unlink(missing_ok=True)
    (output_dir / "ig_caption.txt").unlink(missing_ok=True)

    last_err = ""
    for attempt in range(retries + 1):
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
                last_err = "sin_archivos"
                raise RuntimeError(last_err)

            copied = []
            media_type = "image"

            if images:
                for i, img in enumerate(images, 1):
                    dst = output_dir / ("input_ig.jpg" if i == 1 else f"input_ig_{i}.jpg")
                    shutil.copy2(img, dst)
                    copied.append(str(dst))
                if len(images) > 1:
                    media_type = "carousel"

            if videos:
                media_type = "video" if not images else "carousel_or_video"
                dst = output_dir / "input_ig_video.mp4"
                shutil.copy2(videos[0], dst)
                copied.append(str(dst))

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
            if "Login required" in err or "login" in err.lower():
                err = "login_requerido_o_privado"
            elif "not found" in err.lower() or "does not exist" in err.lower():
                err = "post_no_encontrado"
            elif "429" in err or "Too Many Requests" in err:
                err = "rate_limit"
            last_err = err
            if attempt < retries:
                time.sleep(2 + attempt * 3)
                continue
            return {"status": "manual_required", "reason": err, "url": url}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return {"status": "manual_required", "reason": last_err, "url": url}
