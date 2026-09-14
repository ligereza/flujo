"""Descarga de posts de Instagram: parth-dl primaria, curl_cffi secundaria.

imginn retirado 2026-07-25, causa: 403 Cloudflare permanente desde
2026-07-22, resurreccion: mirror publico funcional verificado.

curl_cffi NO se retira: es la via que hace funcionar la descarga en Linux
(box MAK), donde parth-dl pega login-wall por fingerprint TLS -- verificado
2026-07-23. Se restauro el 2026-07-25 tras haber sido podada por error junto
con imginn.
"""

import html as html_mod
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

SHORTCODE_RE = [
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?p/([A-Za-z0-9_-]+)"),
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?reels?/([A-Za-z0-9_-]+)"),
    re.compile(r"/(?:[A-Za-z0-9_.]+/)?tv/([A-Za-z0-9_-]+)"),
]

_FETCH_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_SNAPINSTA_BASE = "https://snapinsta.ai/"
_SNAPINSTA_MEDIA_UA = "TelegramBot (like TwitterBot)"


def extract_shortcode(url: str) -> str | None:
    for rx in SHORTCODE_RE:
        m = rx.search(url)
        if m:
            return m.group(1)
    return None


def canonicalizar_url(url: str) -> str:
    """Quita el username de la ruta: /usuario/p/SC/ -> /p/SC/.

    parth-dl devuelve 403 con la forma con username (issues #5 y #171,
    2026-07-22). Preserva tipo (p|reel|tv) y query params.
    """
    return re.sub(
        r"(instagram\.com)/[A-Za-z0-9_.]+/(p|reel|tv)/",
        r"\1/\2/",
        url,
    )


def indice_pedido(url: str) -> int:
    """El `img_index` del propio link, 1-based. 1 si no viene.

    Instagram ya pone `?img_index=2` en la URL cuando alguien comparte la
    segunda imagen de un carrusel -- el dato esta ahi, no hace falta
    inventar sintaxis nueva. Mismo criterio que
    `eventos/flyer_auto.py::_indice_pedido`; se duplica (es puro, sin
    dependencias, poco probable que cambie) en vez de importar un modulo
    orientado a Windows/Blender/Photoshop desde el runner de Linux.
    """
    try:
        query = urllib.parse.urlparse(url).query
        crudo = urllib.parse.parse_qs(query).get("img_index", ["1"])[0]
        return max(1, int(crudo))
    except (ValueError, TypeError):
        return 1


def _url_requires_video(url: str) -> bool:
    """Return whether the URL path declares a video-like Instagram post."""
    return bool(re.search(r"/(?:reels?|tv)/", url, re.IGNORECASE))


def _fetch(url: str, referer: str | None = None) -> bytes:
    headers = {"User-Agent": _FETCH_UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _post_form(url: str, fields: dict[str, str], referer: str) -> bytes:
    """POST a form with the same public, no-login provider boundary."""
    data = urllib.parse.urlencode(fields).encode("utf-8")
    headers = {
        "User-Agent": _FETCH_UA,
        "Referer": referer,
        "Origin": "https://snapinsta.ai",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def _download_file(url: str, destination: Path) -> Path:
    """Download one media URL without holding the whole file in memory."""
    headers = {"User-Agent": _FETCH_UA, "Referer": "https://www.instagram.com/"}
    req = urllib.request.Request(url, headers=headers)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as response:
        with destination.open("wb") as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)
    return destination


def _parth_image_urls(data: dict) -> tuple[list[str], bool]:
    """Extrae (urls_de_imagen, es_video) del metadata de parth-dl.

    Video/reel -> [thumbnail]; post/carrusel -> todas las imagenes (el
    contrato historico de este modulo entrega el carrusel completo; la
    regla "solo primera" es del flujo flyer, no de aca).
    """
    urls: list[str] = []
    for item in data.get("images") or []:
        if isinstance(item, str) and item:
            urls.append(item)
        elif isinstance(item, dict):
            u = item.get("url") or item.get("src")
            if u:
                urls.append(u)
    is_video = data.get("type") == "video"
    if not urls and data.get("thumbnail"):
        urls = [data["thumbnail"]]
    return urls, is_video


def _meta_content(html: str, prop: str) -> str | None:
    """Extrae content="..." de un <meta property="prop" .../>, en cualquier
    orden de atributos (property antes o despues de content)."""
    prop_re = re.escape(prop)
    pattern = re.compile(
        r'<meta\s+[^>]*?property=["\']' + prop_re + r'["\'][^>]*?content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        pattern2 = re.compile(
            r'<meta\s+[^>]*?content=["\']([^"\']+)["\'][^>]*?property=["\']' + prop_re + r'["\']',
            re.IGNORECASE,
        )
        m = pattern2.search(html)
    if not m:
        return None
    return html_mod.unescape(m.group(1))


_EMBED_CTX = '"contextJSON":'


def _embed_context(session, shortcode: str) -> dict | None:
    """Full GraphQL media object from Instagram's public embed page.

    `og:image` (the previous approach here) is a single, generic
    link-preview image: for a carousel it is only the first slide, and even
    for a lone post it can be a smaller/cropped rendition picked for social
    cards, not the actual asset. The embed page's `contextJSON` carries the
    real GraphQL `shortcode_media`, including `edge_sidecar_to_children`
    with every slide's own `display_url` at its real size. Ported from
    `eventos/flyer_auto.py::_embed_imagenes` (measured 2026-07-27: the
    visible `<img>` gave 1 image, contextJSON gave the real 3) -- that fix
    was never carried over when this module was written, so every carousel
    (and every post whose og:image happens to be a crop) landed here with
    a single, potentially-cropped image and nothing said so.
    """
    page = session.get(
        f"https://www.instagram.com/p/{shortcode}/embed/captioned/",
        impersonate="chrome", timeout=30,
    )
    if page.status_code != 200:
        return None
    i = page.text.find(_EMBED_CTX)
    if i < 0:
        return None
    try:
        inner, _ = json.JSONDecoder().raw_decode(page.text, i + len(_EMBED_CTX))
        ctx = json.loads(inner)
    except (ValueError, TypeError):
        return None
    return (ctx.get("gql_data") or {}).get("shortcode_media") or None


def _cffi_download(url: str, shortcode: str, output_dir: Path) -> dict | None:
    """Via secundaria: curl_cffi con impersonate="chrome".

    parth-dl (Linux) recibe login-wall de IG por fingerprint TLS; curl_cffi
    imita el fingerprint TLS de Chrome y obtiene la pagina real (verificado
    2026-07-23 en el box MAK Debian, https://www.instagram.com/p/DZdW4_vmY4l/).
    Lazy import: el repo funciona sin la dep. None => no hay via secundaria.
    """
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        return None
    try:
        session = cffi_requests.Session()
        media = _embed_context(session, shortcode)

        image_urls: list[str] = []
        is_video = False
        video_url = None
        caption = ""
        if media is not None:
            is_video = bool(media.get("is_video"))
            children = ((media.get("edge_sidecar_to_children") or {}).get("edges") or [])
            if children:
                image_urls = [
                    node["display_url"]
                    for node in (edge.get("node") or {} for edge in children)
                    if node.get("display_url") and not node.get("is_video")
                ]
            elif media.get("display_url"):
                image_urls = [media["display_url"]]
            if is_video:
                video_url = media.get("video_url")
            caption_edges = (media.get("edge_media_to_caption") or {}).get("edges") or []
            if caption_edges:
                caption = caption_edges[0].get("node", {}).get("text", "") or ""

        if not image_urls or (is_video and not video_url):
            page = session.get(url, impersonate="chrome", timeout=30)
            html = page.text
            if not image_urls:
                fallback = _meta_content(html, "og:image")
                if fallback:
                    image_urls = [fallback]
            if not video_url:
                video_url = _meta_content(html, "og:video")
                is_video = is_video or video_url is not None
            if not caption:
                caption = (_meta_content(html, "og:description")
                           or _meta_content(html, "og:title") or "")

        if not image_urls and not video_url:
            return None

        image_files: list[str] = []
        for index, image_url in enumerate(image_urls, start=1):
            name = "input_ig.jpg" if index == 1 else f"input_ig_{index}.jpg"
            img_resp = session.get(image_url, impersonate="chrome", timeout=30)
            dst = output_dir / name
            dst.write_bytes(img_resp.content)
            image_files.append(str(dst))
        files = list(image_files)
        video_dst = None
        if video_url:
            video_resp = session.get(video_url, impersonate="chrome", timeout=120)
            video_dst = output_dir / "input_ig.mp4"
            video_dst.write_bytes(video_resp.content)
            files.append(str(video_dst))
        if caption:
            (output_dir / "ig_caption.txt").write_text(caption, encoding="utf-8")
    except Exception:
        return None

    media_type = "video" if video_dst else ("carousel" if len(image_files) > 1 else "image")
    return {
        "status": "downloaded",
        "shortcode": shortcode,
        "url": url,
        "media_type": media_type,
        "files": files,
        "video_files": [str(video_dst)] if video_dst else [],
        "image_files": image_files,
        "file_count": len(files),
        "caption": caption,
        "owner": "",
        "date": "",
        "is_video": bool(video_dst),
    }


def _decode_snapinsta_layer(source: str) -> str | None:
    """Unpack one obfuscated response layer from SnapInsta's public form."""
    packed = re.search(
        r'eval\(function\(h,u,n,t,e,r\).*?\}\("([^\"]*)",\s*\d+,"'
        r'([^\"]*)",\s*(\d+),\s*(\d+),\s*\d+\)\)',
        source,
        re.DOTALL,
    )
    if not packed:
        return None
    encoded, alphabet_map, offset, exponent = packed.groups()
    offset = int(offset)
    exponent = int(exponent)
    delimiter = alphabet_map[exponent]
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
    head = alphabet[:exponent]
    digits = alphabet[:10]
    decoded: list[str] = []
    i = 0
    while i < len(encoded):
        chunk: list[str] = []
        while i < len(encoded) and encoded[i] != delimiter:
            chunk.append(encoded[i])
            i += 1
        if i < len(encoded):
            i += 1
        for index, char in enumerate(alphabet_map):
            chunk = [str(index) if item == char else item for item in chunk]
        value = 0
        for power, char in enumerate(reversed(chunk)):
            digit = head.find(char)
            if digit >= 0:
                value += digit * (exponent ** power)
        chars: list[str] = []
        while value > 0:
            chars.append(digits[value % 10])
            value = (value - (value % 10)) // 10
        decoded.append(chr(int("".join(reversed(chars)) or "0") - offset))
    raw = bytes(ord(char) & 0xFF for char in "".join(decoded))
    return raw.decode("utf-8", errors="replace")


def _unpack_snapinsta_response(source: str) -> str:
    """Decode the small chain of JS wrappers returned by the public form."""
    current = source
    for _ in range(3):
        decoded = _decode_snapinsta_layer(current)
        if decoded is None:
            return current
        current = decoded
    return current


def _is_mp4_file(path: Path) -> bool:
    """Reject provider false positives such as JPEG bytes labelled MP4."""
    try:
        if path.stat().st_size < 32_000:
            return False
        with path.open("rb") as stream:
            header = stream.read(32)
    except OSError:
        return False
    return len(header) >= 12 and header[4:8] == b"ftyp"


def _snapinsta_download(url: str, shortcode: str, output_dir: Path) -> dict | None:
    """Fallback via SnapInsta's public no-login web form.

    This is deliberately a video-only fallback. The page is not an official
    API, its response is obfuscated JavaScript, and its CDN can return a JPEG
    for a reel. Accept only a real MP4 signature and a meaningful file size.
    """
    try:
        page = _fetch(_SNAPINSTA_BASE)
        token_match = re.search(
            rb'<input\s+name=["\']token["\']\s+value=["\']([^"\']+)',
            page,
            re.IGNORECASE,
        )
        if not token_match:
            return None
        token = token_match.group(1).decode("utf-8", errors="replace")
        response = _post_form(
            _SNAPINSTA_BASE + "action2.php",
            {"url": url, "action": "post", "lang": "en", "token": token},
            _SNAPINSTA_BASE,
        )
        unpacked = _unpack_snapinsta_response(
            response.decode("utf-8", errors="replace")
        )
        links = re.findall(
            r"https://d\.rapidcdn\.app/v2\?token=[^'\"\\\s]+?&dl=1",
            unpacked,
        )
        if not links:
            return None
        media_url = html_mod.unescape(links[-1]).replace("\\/", "/")
        video_dst = output_dir / "input_ig.mp4"
        partial = output_dir / "input_ig.mp4.part"
        request = urllib.request.Request(
            media_url,
            headers={
                "User-Agent": _SNAPINSTA_MEDIA_UA,
                "Referer": _SNAPINSTA_BASE,
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response_stream:
            with partial.open("wb") as stream:
                shutil.copyfileobj(response_stream, stream, length=1024 * 1024)
        if not _is_mp4_file(partial):
            partial.unlink(missing_ok=True)
            return None
        partial.replace(video_dst)
        poster = output_dir / "input_ig.jpg"
        image_files = [str(poster)] if poster.exists() else []
        return {
            "status": "downloaded",
            "shortcode": shortcode,
            "url": url,
            "media_type": "video",
            "files": image_files + [str(video_dst)],
            "video_files": [str(video_dst)],
            "image_files": image_files,
            "file_count": len(image_files) + 1,
            "caption": "",
            "owner": "",
            "date": "",
            "is_video": True,
        }
    except Exception:
        return None


def _parth_download(url: str, shortcode: str, output_dir: Path) -> dict:
    """Via primaria: parth-dl (pip install parth-dl).

    Lanza ImportError si el paquete no esta instalado, o la excepcion que
    corresponda (red, sin archivos) si la descarga falla. download_post()
    clasifica y convierte esas excepciones en un resultado manual_required.
    """
    from parth_dl import get_info  # lazy: el repo funciona sin parth-dl instalado

    data = get_info(url)
    entries = data.get("entries") or []
    if not entries:
        raise RuntimeError("sin_archivos")
    copied = []
    image_files = []
    video_files = []
    image_index = 0
    video_index = 0
    for entry in entries:
        formats = [f for f in entry.get("formats") or [] if f.get("url")]
        if not formats:
            continue
        selected = max(
            formats,
            key=lambda f: (int(f.get("width") or 0) * int(f.get("height") or 0),
                           bool(f.get("has_audio"))),
        )
        kind = entry.get("kind")
        if kind == "video":
            video_index += 1
            name = "input_ig.mp4" if video_index == 1 else f"input_ig_{video_index}.mp4"
            dst = _download_file(selected["url"], output_dir / name)
            video_files.append(str(dst))
            copied.append(str(dst))
        elif kind == "image":
            image_index += 1
            name = "input_ig.jpg" if image_index == 1 else f"input_ig_{image_index}.jpg"
            dst = _download_file(selected["url"], output_dir / name)
            image_files.append(str(dst))
            copied.append(str(dst))

    declared_video = data.get("type") == "video" or any(
        entry.get("kind") == "video" for entry in entries
    )
    if declared_video and not video_files:
        raise RuntimeError("video_sin_mp4")

    # Keep a poster for the department and for operators, even when the actual
    # render input is a video. It is not used as a substitute for the MP4.
    if video_files and not image_files and data.get("thumbnail"):
        poster = _download_file(data["thumbnail"], output_dir / "input_ig.jpg")
        image_files.append(str(poster))
        copied.insert(0, str(poster))
    if not copied:
        raise RuntimeError("sin_archivos")
    media_type = "video" if video_files else (
        "carousel" if len(image_files) > 1 else "image"
    )
    return {
        "status": "downloaded",
        "shortcode": shortcode,
        "url": url,
        "media_type": media_type,
        "files": copied,
        "video_files": video_files,
        "image_files": image_files,
        "file_count": len(copied),
        "caption": data.get("caption") or data.get("description") or "",
        "owner": data.get("uploader") or "",
        "date": "",
        "is_video": bool(video_files),
    }


def download_post(url: str, output_dir: Path, retries: int = 1) -> dict:
    """Descarga IG: parth-dl, curl_cffi y SnapInsta video fallback.

    parth-dl cubre posts, carruseles y video/reel (thumbnail como imagen),
    pero en Linux puede pegar login-wall por fingerprint TLS -- ahi entra
    curl_cffi (verificado 2026-07-23 en el box MAK). Si ninguna via sirve,
    retorna manual_required con la razon. imginn quedo 403 Cloudflare
    (retirado 2026-07-25); instaloader murio (IG exige login incluso anonimo).
    SnapInsta solo se usa para rutas video-like y valida la firma MP4.
    """
    url = canonicalizar_url(url)
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "reason": "shortcode_no_detectado", "url": url}
    requires_video = _url_requires_video(url)
    indice = indice_pedido(url)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for f in output_dir.glob("input_ig*"):
        f.unlink(missing_ok=True)
    (output_dir / "ig_caption.txt").unlink(missing_ok=True)

    def _con_indice(resultado: dict) -> dict:
        # Todas las vias bajan el carrusel entero, en orden; cual slide usa
        # el render es una decision de consumo, no de descarga, asi que se
        # anota aca en un solo punto en vez de en cada _*_download.
        disponibles = len(resultado.get("image_files") or [])
        resultado["requested_image_index"] = indice
        resultado["requested_image_index_available"] = 0 < indice <= disponibles
        return resultado

    last_err = ""
    for attempt in range(retries + 1):
        try:
            resultado = _parth_download(url, shortcode, output_dir)
            if requires_video and not resultado.get("video_files"):
                raise RuntimeError("video_sin_mp4")
            return _con_indice(resultado)
        except ImportError:
            last_err = "parth_dl_no_instalado"
            break
        except Exception as e:
            err = str(e)
            if "404" in err or "not found" in err.lower():
                err = "post_no_encontrado"
            elif "429" in err or "Too Many Requests" in err:
                err = "rate_limit"
            elif not err:
                err = "error_desconocido"
            last_err = err
            if attempt < retries:
                time.sleep(2 + attempt * 3)
                continue
            break

    resultado = _cffi_download(url, shortcode, output_dir)
    if resultado is not None:
        if requires_video and not resultado.get("video_files"):
            last_err = "video_sin_mp4"
        else:
            return _con_indice(resultado)

    if requires_video:
        resultado = _snapinsta_download(url, shortcode, output_dir)
        if resultado is not None and resultado.get("video_files"):
            return resultado

    manual = {"status": "manual_required", "reason": last_err, "url": url}
    if requires_video:
        manual.update({"media_type": "video", "video_files": [], "is_video": False})
    return manual
