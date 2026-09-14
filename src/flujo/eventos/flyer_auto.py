"""EVENTOS Instagram flyer download + local Photoshop/Blender handoff.

Default behavior is safe:
- downloads Instagram image
- updates input_ig.jpg
- extracts a small palette preview
- does NOT open Photoshop or Blender unless explicit flags are used
"""

from __future__ import annotations

import colorsys
import glob
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WINDOWS_BASE = Path(r"C:\rd\AUTOMATIZACION")


@dataclass
class EventFlyerResult:
    ok: bool
    shortcode: str = ""
    base_dir: Path | None = None
    downloaded_image: Path | None = None
    input_image: Path | None = None
    palette_image: Path | None = None
    palette_json: Path | None = None
    blender_file: Path | None = None
    blender_render: Path | None = None
    droplet_path: Path | None = None
    psd_path: Path | None = None
    droplet_started: bool = False
    blender_started: bool = False
    blender_rendered: bool = False
    error: str = ""


def extract_instagram_shortcode(url: str) -> str:
    """Extract shortcode from Instagram post/reel URL."""
    text = (url or "").strip()
    patterns = [r"instagram\.com/(?:[^/]+/)?p/([^/?#]+)", r"instagram\.com/(?:[^/]+/)?reel/([^/?#]+)"]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    for marker in ("/p/", "/reel/"):
        if marker in text:
            return text.split(marker, 1)[1].split("/", 1)[0].split("?", 1)[0]
    raise ValueError("Invalid Instagram URL. Expected /p/ or /reel/ link.")


def default_base_dir() -> Path:
    """Carpeta de trabajo de la automatizacion de flyers.

    Orden: la variable propia, despues FLUJO_RD_ROOT (la que ya documenta el
    repo para el arbol de material), y recien al final el default de Windows.
    Encadenarla evita tener que declarar dos variables para lo mismo, y deja de
    depender de que exista una carpeta concreta en una maquina concreta.
    """
    env = os.getenv("FLUJO_EVENTOS_AUTOMATIZACION_DIR", "").strip()
    if env:
        return Path(env)
    raiz_rd = os.getenv("FLUJO_RD_ROOT", "").strip()
    if raiz_rd:
        return Path(raiz_rd) / "AUTOMATIZACION"
    return DEFAULT_WINDOWS_BASE if os.name == "nt" else Path.cwd() / "eventos_automatizacion"


def _first_downloaded_image(temp_dir: Path) -> Path:
    candidates: list[str] = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        candidates.extend(glob.glob(str(temp_dir / ext)))
    if not candidates:
        raise FileNotFoundError("No image was downloaded from Instagram.")
    return Path(sorted(candidates)[0]).resolve()


_MIRROR_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _indice_pedido(url: str) -> int:
    """El `img_index` del propio link, 1-based. 1 si no viene.

    Instagram ya pone `?img_index=2` en la URL cuando alguien comparte la
    segunda imagen de un carrusel. El dato estaba ahi y se ignoraba: se
    bajaba siempre la primera, asi que un pedido de la segunda devolvia una
    pieza equivocada sin avisar. No hace falta inventar sintaxis nueva.
    """
    try:
        query = urllib.parse.urlparse(url).query
        crudo = urllib.parse.parse_qs(query).get("img_index", ["1"])[0]
        return max(1, int(crudo))
    except (ValueError, TypeError):
        return 1


def _url_de_imagen(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("url", "src"):
            if item.get(key):
                return str(item[key])
    return ""


def _parth_pick_image_url(data: dict, indice: int = 1) -> str:
    """Elige UNA sola imagen del metadata de parth-dl.

    Video/reel -> thumbnail (el flyer necesita imagen fija).
    Post/carrusel -> la que pidio el link (`img_index`), y si no dice cual,
    la primera. Nunca todas.
    """
    images = data.get("images") or []
    if images:
        # Si el link pidio una que no existe, se cae a la primera en vez de
        # fallar: es preferible el flyer equivocado a ningun flyer, y el
        # numero de imagen se ve en el render.
        elegida = images[indice - 1] if 0 < indice <= len(images) else images[0]
        url_img = _url_de_imagen(elegida)
        if url_img:
            return url_img
    thumbnail = data.get("thumbnail")
    if thumbnail:
        return thumbnail
    raise FileNotFoundError("parth-dl no devolvio imagen ni thumbnail.")


def _bajar_imagen(image_url: str) -> bytes:
    """Baja la imagen imitando a Chrome de verdad, no solo en el User-Agent.

    Instagram devuelve 403 a Python en Linux aunque el User-Agent diga Chrome:
    lo que mira es la huella TLS del cliente, y la de urllib se nota. Medido el
    2026-07-27, cuando MAK fallo con `HTTP Error 403: Forbidden` en el mismo
    link que Windows bajaba sin problema.

    `curl_cffi` imita el handshake de Chrome y pasa. Si no esta instalado se
    usa urllib igual, porque en Windows funciona: esto no reemplaza el camino
    viejo, lo antepone donde hace falta.
    """
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        cffi_requests = None

    if cffi_requests is not None:
        try:
            r = cffi_requests.get(image_url, impersonate="chrome", timeout=30)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception:
            pass  # cae a urllib, que en Windows alcanza

    req = urllib.request.Request(image_url, headers={"User-Agent": _MIRROR_UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _download_via_parth(url: str, shortcode: str, temp_dir: Path) -> Path:
    """Via primaria de descarga: parth-dl (pip install parth-dl).

    Funciona con reels/video donde el mirror no llega; para video se usa el
    thumbnail como imagen base. Si el paquete no esta instalado o falla,
    el caller cae al mirror.
    """
    from parth_dl import get_info  # lazy: el repo funciona sin parth-dl

    data = get_info(url)
    image_url = _parth_pick_image_url(data, _indice_pedido(url))
    payload = _bajar_imagen(image_url)
    out = temp_dir / f"parth_{shortcode}.jpg"
    out.write_bytes(payload)
    return out


_EMBED_IMG_RE = re.compile(r'class="EmbeddedMediaImage"[^>]*src="([^"]+)"')
_EMBED_CTX = '"contextJSON":'


def _embed_html(shortcode: str) -> str:
    from curl_cffi import requests as cffi_requests

    pagina = "https://www.instagram.com/p/%s/embed/captioned/" % shortcode
    r = cffi_requests.get(pagina, impersonate="chrome", timeout=25)
    if r.status_code != 200:
        raise FileNotFoundError("el embed devolvio %s" % r.status_code)
    return r.text


def _embed_imagenes(html_txt: str) -> tuple[str, list[dict]]:
    """TODAS las imagenes del post, no solo la que muestra el embed.

    El `<img>` visible del embed trae una sola: la primera. Pero la pagina
    lleva ademas un `contextJSON` con el GraphQL completo, y ahi esta el
    carrusel entero (`edge_sidecar_to_children`). Medido el 2026-07-27 sobre
    un post real: el `<img>` daba 1 imagen y el contextJSON daba las 3.

    Se parsea con el decodificador de JSON y no con una expresion regular: el
    valor es una cadena JSON con JSON adentro, llena de comillas escapadas, y
    cualquier patron se corta en la primera.

    Devuelve (tipo, [{url, video}]). Si no hay contextJSON cae al `<img>`, que
    es mejor que nada.
    """
    i = html_txt.find(_EMBED_CTX)
    if i >= 0:
        try:
            interior, _ = json.JSONDecoder().raw_decode(html_txt, i + len(_EMBED_CTX))
            ctx = json.loads(interior)
            media = (ctx.get("gql_data") or {}).get("shortcode_media") or {}
            hijos = ((media.get("edge_sidecar_to_children") or {}).get("edges") or [])
            if hijos:
                salida = []
                for h in hijos:
                    n = h.get("node") or {}
                    if n.get("display_url"):
                        salida.append({"url": n["display_url"],
                                       "video": bool(n.get("is_video"))})
                if salida:
                    return media.get("__typename") or "GraphSidecar", salida
            if media.get("display_url"):
                # Un reel entrega su cuadro de portada, que es imagen fija y
                # sirve como base del flyer.
                return (media.get("__typename") or "GraphImage",
                        [{"url": media["display_url"],
                          "video": bool(media.get("is_video"))}])
        except (ValueError, TypeError):
            pass
    m = _EMBED_IMG_RE.search(html_txt)
    if m:
        u = m.group(1).encode().decode("unicode_escape").replace("&amp;", "&")
        return "SoloEmbed", [{"url": u, "video": False}]
    return "", []


def _download_via_embed(shortcode: str, temp_dir: Path, indice: int = 1) -> Path:
    """Via para Linux: la pagina de embed publica de Instagram.

    Por que existe: parth-dl no llega desde MAK. Instagram le devuelve un muro
    de login ("All extraction methods failed") antes siquiera de dar la
    metadata, asi que arreglar el fingerprint en la descarga de la imagen no
    alcanzaba -- fallaba un paso antes. Medido el 2026-07-27 con el flyer del
    issue #322, que Windows bajaba sin problema.

    Respeta que imagen del carrusel se pidio, porque el contextJSON las trae
    todas. Idea del usuario: en vez de pelear con que el embed muestre una
    sola, conseguir la lista completa y que el codigo elija. Se baja SOLO la
    elegida -- traer las cinco para descartar cuatro seria pagar el ancho de
    banda de todas para usar una.
    """
    tipo, imgs = _embed_imagenes(_embed_html(shortcode))
    if not imgs:
        raise FileNotFoundError(
            "el embed no traia imagen (puede ser privado, borrado o restringido)")
    elegida = imgs[indice - 1] if 0 < indice <= len(imgs) else imgs[0]
    out = temp_dir / f"embed_{shortcode}.jpg"
    out.write_bytes(_bajar_imagen(elegida["url"]))
    if indice > len(imgs):
        print(f"AVISO: se pidio la imagen {indice} pero el post tiene "
              f"{len(imgs)}. Se uso la primera.")
    return out


def _download_via_mirror(shortcode: str, temp_dir: Path, indice: int = 1) -> Path:
    """Fallback sin login: mirror publico (IG bloquea instaloader anonimo desde 2026).

    Mejor esfuerzo sobre un servicio de terceros: si el mirror cambia su HTML o
    muere, volver a instaloader con sesion logueada (instaloader --login).

    Respeta `indice` con el mismo criterio que _download_via_embed. Auditoria
    encontro que esta via juntaba TODAS las slides del carrusel en
    `candidatos` y siempre bajaba candidatos[0]: cuando parth-dl y el embed
    fallan y esta es la que entrega, pisaba input_ig.jpg -- la fuente unica
    del flyer -- con una slide distinta a la pedida, sin avisar. Se arreglo
    ese mismo caso en _download_via_embed y se salto este por descuido.
    """
    import html as html_mod
    import urllib.request

    def _fetch(url: str, referer: str | None = None) -> bytes:
        headers = {"User-Agent": _MIRROR_UA}
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()

    page = _fetch(f"https://imginn.com/p/{shortcode}/").decode("utf-8", "replace")
    # 1) preferir imagenes DENTRO del contenedor del post (swiper-slide);
    #    fuera de el aparecen avatares (t51.82787-19 en posts collab) y thumbs
    slides = re.findall(
        r'<div class="swiper-slide[^>]*>.*?(?:data-src|src)="(https://[^"]+)"', page, re.DOTALL)
    urls = slides or re.findall(
        r'(?:data-src|src)="(https://[^"]+(?:imginn|scontent|cdninstagram)[^"]+)"', page)
    urls = [html_mod.unescape(u) for u in urls
            if "rsrc.php" not in u and "lazy.jpg" not in u and (".jpg" in u or ".webp" in u)]
    # t51.82787-15 = media del post; -19 y t51.2885-19 = avatares (tambien en collab)
    post_media = [u for u in urls if "t51.82787-15" in u]
    candidatos = post_media or [u for u in urls
                                if "t51.2885-19" not in u and "t51.82787-19" not in u]
    if not candidatos:
        raise FileNotFoundError("El mirror no devolvio imagen del post.")
    # Mismo criterio que _download_via_embed: si el indice pedido no entra en
    # candidatos se avisa y se usa la primera, nunca se sustituye en silencio.
    elegida = candidatos[indice - 1] if 0 < indice <= len(candidatos) else candidatos[0]
    data = _fetch(elegida, referer="https://imginn.com/")
    out = temp_dir / f"mirror_{shortcode}.jpg"
    out.write_bytes(data)
    if indice > len(candidatos):
        print(f"AVISO: se pidio la imagen {indice} pero el post tiene "
              f"{len(candidatos)}. Se uso la primera.")
    return out


def _extract_palette(image_path: Path, palette_png: Path, palette_json: Path, colors_count: int = 6) -> list[str]:
    """Extract dominant colors and write a swatch PNG + JSON list."""
    from PIL import Image, ImageDraw

    img = Image.open(image_path).convert("RGB")
    thumb = img.copy()
    thumb.thumbnail((240, 240))
    # Adaptive palette is good enough for quick art direction.
    pal = thumb.convert("P", palette=Image.Palette.ADAPTIVE, colors=max(1, colors_count))
    palette = pal.getpalette() or []
    counts = pal.getcolors(maxcolors=240 * 240) or []
    counts = sorted(counts, reverse=True)[:colors_count]
    hex_colors: list[str] = []
    for _count, idx in counts:
        base = idx * 3
        if base + 2 < len(palette):
            rgb = tuple(palette[base:base + 3])
            hex_colors.append("#%02x%02x%02x" % rgb)

    if not hex_colors:
        hex_colors = ["#000000"]

    swatch_w, swatch_h = 140, 90
    out = Image.new("RGB", (swatch_w * len(hex_colors), swatch_h), "white")
    draw = ImageDraw.Draw(out)
    for i, color in enumerate(hex_colors):
        x = i * swatch_w
        draw.rectangle([x, 0, x + swatch_w, swatch_h], fill=color)
        draw.text((x + 10, swatch_h - 22), color.upper(), fill="white")
    palette_png.parent.mkdir(parents=True, exist_ok=True)
    out.save(palette_png)
    palette_json.write_text(json.dumps({"colors": hex_colors}, indent=2), encoding="utf-8")
    return hex_colors


def _photoshop_running() -> bool:
    if os.name != "nt":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Photoshop.exe"],
                             capture_output=True, text=True, timeout=15).stdout
        return "Photoshop.exe" in out
    except Exception:
        return False


def _start_droplet(droplet_path: Path, psd_path: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("Droplet launch is only supported on Windows.")
    if _photoshop_running():
        # varias instancias de Photoshop compiten y el droplet nunca entrega
        # (comprobado 2026-07-08: 5 instancias colgadas); mejor fallar claro
        raise RuntimeError(
            "Photoshop ya esta abierto: cierra las instancias antes de lanzar "
            "el droplet (multiples instancias se traban entre si)."
        )
    subprocess.Popen(["cmd", "/c", "start", "", str(droplet_path), str(psd_path)], shell=False)


def _write_predominant_color(image_path: Path, out_png: Path) -> str:
    """Color mas saturado del flyer -> PNG solido que RD.blend linkea para el
    hue del marco Y, via el mismo datablock, el vidrio decorativo.

    Antes elegia el mas luminoso y lo aclaraba 25% hacia blanco (pensado
    solo para el tinte sutil del vidrio); ese aclarado le daba a
    hue_de_rgb() un hue practicamente al azar en flyers de fondo claro, y
    dejaba vidrio/marco sin unificar en el mismo acento (bug real,
    encontrado 2026-09-09 con el flyer de Piknic). Sin aclarado: un solo
    color real manda en ambos.
    """
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    thumb = img.copy()
    thumb.thumbnail((240, 240))
    pal = thumb.convert("P", palette=Image.Palette.ADAPTIVE, colors=6)
    palette = pal.getpalette() or []
    counts = sorted(pal.getcolors(240 * 240) or [], reverse=True)[:6]
    colores = []
    for cnt, idx in counts:
        r, g, b = palette[idx * 3:idx * 3 + 3]
        _h, sat, _v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        colores.append((cnt, sat, (r, g, b)))
    if not colores:
        colores = [(1, 0.0, (0, 0, 0))]
    # el mas saturado entre los que tienen peso real (>15% del dominante)
    colores.sort(key=lambda c: (-c[1], -c[0]))
    candidato = next((c for c in colores if c[0] > counts[0][0] * 0.15), colores[0])
    r, g, b = candidato[2]
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 512), (r, g, b)).save(out_png)
    return f"#{r:02x}{g:02x}{b:02x}"


def _open_blender(blender_exe: str, blender_file: Path) -> None:
    subprocess.Popen([blender_exe, str(blender_file)], shell=False)


def _wait_for_file_update(path: Path, after_time: float, timeout_s: float = 300.0, poll_s: float = 2.0) -> bool:
    """Espera activa a que `path` exista con mtime posterior a `after_time`."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if path.exists() and path.stat().st_mtime >= after_time:
                return True
        except OSError:
            pass  # el Droplet puede estar escribiendo el archivo justo ahora
        time.sleep(poll_s)
    return False




_BLENDER_GPU_SCRIPT = Path(__file__).resolve().parent / "blender_gpu.py"
_BLENDER_NODES_SCRIPT = Path(__file__).resolve().parent / "blender_nodes.py"


def _render_blender_compuesto(
    blender_exe: str,
    blender_file: Path,
    frame_png: Path,
    input_img: Path,
    color_png: Path,
    output_path: Path,
) -> Path:
    """Render SIN Photoshop: blender_nodes.py recompone el material en memoria
    (FRAME2 + input + recolor por color predominante) y renderiza."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        blender_exe,
        "-b",
        str(blender_file),
        "--python",
        str(_BLENDER_NODES_SCRIPT),
        "--",
        "--frame",
        str(frame_png),
        "--input",
        str(input_img),
        "--color-png",
        str(color_png),
        "--salida",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def _render_blender_frame(blender_exe: str, blender_file: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Blender -o wants a path prefix; -f 1 appends frame number + extension.
    prefix = output_path.with_suffix("")
    # remove stale frames so a prior run cannot masquerade as this render
    for stale in prefix.parent.glob(prefix.name + "0001.*"):
        stale.unlink()
    cmd = [
        blender_exe,
        "-b",
        str(blender_file),
        # --python corre ANTES del render: fuerza GPU (OptiX/CUDA) en memoria,
        # no toca ni guarda el .blend (blender_gpu.py, agregado 2026-07-10;
        # sin esto Cycles renderiza en CPU por default).
        "--python",
        str(_BLENDER_GPU_SCRIPT),
        "-o",
        str(prefix),
        "-f",
        "1",
    ]
    subprocess.run(cmd, check=True)
    # Blender appends frame number + extension per the .blend's file_format
    # (not always PNG); pick up whatever it actually wrote.
    produced = sorted(prefix.parent.glob(prefix.name + "0001.*"))
    if not produced:
        raise FileNotFoundError(
            f"Blender no produjo {prefix.name}0001.*; revisa el formato de salida del .blend."
        )
    frame_file = produced[0]
    if output_path.exists():
        output_path.unlink()
    frame_file.rename(output_path)
    return output_path


def run_eventos_flyer_auto(
    url: str,
    base_dir: Path | None = None,
    run_droplet: bool = False,
    open_blender: bool = False,
    render_blender: bool = False,
    blender_exe: str = "blender",
    keep_temp: bool = False,
) -> EventFlyerResult:
    """Download Instagram flyer and optionally launch Blender (y legado Photoshop).

    Expected local files in base_dir:
    - RD.blend (plantilla textura; si falta, fallback a cartelera.blend frame 1)
    - FRAME2.png: si existe junto a RD.blend, el render compone por NODOS
      (blender_nodes.py: FRAME2 + input + recolor) y NO usa Photoshop.
    - Droplet_Flyer.exe + historia.psd + flyer_final.jpg: solo camino legado
      (sin FRAME2.png), con espera activa de hasta 300s al Droplet.
    - input_ig.jpg will be replaced/created
    - palette_ig.png and palette_ig.json will be written
    - render_output.png (salida del render con RD.blend)
    """
    base = (base_dir or default_base_dir()).resolve()
    droplet = base / "Droplet_Flyer.exe"
    psd = base / "historia.psd"
    blender_file = base / "cartelera.blend"
    blender_render = base / "preview_cartelera.png"
    rd_blend = base / "RD.blend"
    flyer_final = base / "flyer_final.jpg"  # output real del Droplet de Photoshop
    render_out = base / "render_output.png"
    input_img = base / "input_ig.jpg"
    palette_png = base / "palette_ig.png"
    palette_json = base / "palette_ig.json"
    temp_dir = base / "temp_flyer"

    try:
        shortcode = extract_instagram_shortcode(url)
        base.mkdir(parents=True, exist_ok=True)
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Tres vias, en orden de fidelidad:
        # 1. parth-dl: la mejor -- cubre reels (thumbnail) y respeta que imagen
        #    del carrusel se pidio. Funciona desde Windows.
        # 2. embed publico: la que llega desde Linux. Instagram le sirve un muro
        #    de login a parth-dl desde MAK (medido 2026-07-27, issue #322), pero
        #    el embed responde 200 imitando a Chrome. Entrega SOLO la primera
        #    imagen, asi que si el link pedia otra se avisa en vez de mentir.
        # 3. mirror: imginn quedo 403 Cloudflare (2026-07-22), best-effort.
        # instaloader confirmado no funcional (IG exige login incluso anonimo).
        indice = _indice_pedido(url)
        try:
            downloaded = _download_via_parth(url, shortcode, temp_dir)
        except Exception as e_parth:
            try:
                downloaded = _download_via_embed(shortcode, temp_dir, indice)
            except Exception as e_embed:
                print(f"parth-dl: {e_parth}\nembed: {e_embed}")
                downloaded = _download_via_mirror(shortcode, temp_dir, indice)

        if input_img.exists():
            input_img.unlink()
        shutil.copy(downloaded, input_img)
        _extract_palette(input_img, palette_png, palette_json)
        # RD.blend linkea RESULTADOS/color_predominante.png como material
        _write_predominant_color(input_img, base / "RESULTADOS" / "color_predominante.png")

        started_droplet = False
        droplet_launch_time = 0.0
        if run_droplet:
            if not droplet.exists():
                raise FileNotFoundError(f"Missing droplet: {droplet}")
            if not psd.exists():
                raise FileNotFoundError(f"Missing PSD: {psd}")
            droplet_launch_time = time.time()
            _start_droplet(droplet, psd)
            started_droplet = True

        started_blender = False
        rendered_blender = False
        if open_blender and not blender_file.exists():
            raise FileNotFoundError(f"Missing Blender file: {blender_file}")
        frame2 = base / "FRAME2.png"
        if render_blender:
            if rd_blend.exists() and frame2.exists():
                # camino SIN Photoshop (2026-07-10): blender_nodes.py compone
                # FRAME2 + input + recolor en nodos; flyer_final.jpg y el
                # Droplet dejan de ser necesarios.
                _render_blender_compuesto(
                    blender_exe, rd_blend, frame2, input_img,
                    base / "RESULTADOS" / "color_predominante.png", render_out,
                )
                blender_render = render_out
            elif rd_blend.exists():
                if started_droplet:
                    # legado con Droplet: espera activa a flyer_final.jpg
                    if not _wait_for_file_update(flyer_final, droplet_launch_time):
                        raise TimeoutError(
                            f"El Droplet no produjo {flyer_final} en 300s; "
                            "revisa Photoshop antes de renderizar."
                        )
                elif not (flyer_final.exists()
                          and flyer_final.stat().st_mtime >= input_img.stat().st_mtime):
                    # sin Droplet, RD.blend linkea flyer_final.jpg de disco: exige
                    # uno fresco para ESTE evento (mtime >= input recien bajado a
                    # las 350), no un sobrante de un evento anterior.
                    raise FileNotFoundError(
                        f"RD.blend legado necesita un {flyer_final} fresco para este evento; "
                        "corre el Droplet (run_droplet=True) o provee FRAME2.png para el "
                        "camino sin Photoshop."
                    )
                # RD.blend linkea flyer_final.jpg desde disco (validado 2026-07-08)
                _render_blender_frame(blender_exe, rd_blend, render_out)
                blender_render = render_out
            else:
                # fallback legado: frame 1 de cartelera.blend
                if not blender_file.exists():
                    raise FileNotFoundError(
                        f"Missing Blender file: ni {rd_blend} ni {blender_file}"
                    )
                if started_droplet:
                    if not _wait_for_file_update(flyer_final, droplet_launch_time):
                        raise TimeoutError(
                            f"El Droplet no produjo {flyer_final} en 300s; "
                            "revisa Photoshop antes de renderizar."
                        )
                _render_blender_frame(blender_exe, blender_file, blender_render)
            rendered_blender = True
        if open_blender:
            _open_blender(blender_exe, blender_file)
            started_blender = True

        if not keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return EventFlyerResult(
            ok=True,
            shortcode=shortcode,
            base_dir=base,
            downloaded_image=downloaded,
            input_image=input_img,
            palette_image=palette_png,
            palette_json=palette_json,
            blender_file=blender_file,
            blender_render=blender_render,
            droplet_path=droplet,
            psd_path=psd,
            droplet_started=started_droplet,
            blender_started=started_blender,
            blender_rendered=rendered_blender,
        )
    except Exception as exc:
        if not keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return EventFlyerResult(
            ok=False,
            base_dir=base,
            input_image=input_img,
            palette_image=palette_png,
            palette_json=palette_json,
            blender_file=blender_file,
            blender_render=blender_render,
            droplet_path=droplet,
            psd_path=psd,
            error=str(exc),
        )
