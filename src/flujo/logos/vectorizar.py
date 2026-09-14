"""Raster -> SVG para logos de productoras, con fondo transparente.

Por que existe este modulo y no un script suelto: el 2026-07-25 se vectorizaron
8 logos a mano y costo tres pasadas fallidas. Todo lo que se aprendio ahi esta
codificado aca para que la novena vez sea un comando y no una investigacion.

Las tres trampas que costaron esas pasadas:

1. **Vectorizar el raster crudo** sale fiel pero enorme: el trazador sigue el
   grano de compresion del JPG. Un logo simple daba 464 KB. Se corrige
   cuantizando el color antes de trazar (`_posterizar`).

2. **Binarizar** (blanco/negro puro) rompe los logos de figura clara sobre
   fondo oscuro: el texto calado en blanco dentro de un circulo negro terminaba
   negro sobre negro. Por eso se posteriza en vez de binarizar: se pierde el
   grano pero se conserva cual region es figura y cual es fondo.

3. **Aplastar un PNG con alpha contra un fondo blanco** destruye la figura. Un
   logo puede ser 97% transparente: ahi la figura ES el canal alpha, no el
   color. Se detecta y se trata aparte (`_desde_alpha`).

Y el requisito que define la salida: el SVG NO debe traer rectangulo de fondo.
vtracer emite un path por region de color, incluido el fondo; ese path se
detecta y se quita (`_quitar_fondo`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Lado minimo al que se escala antes de trazar. El trazador sigue el borde de
# pixel: un borde de 1200 px da curvas notoriamente mas limpias que uno de 200.
LADO_MINIMO = 1200

# Si mas de esta fraccion del alpha es transparente, la figura vive en el alpha
# y no en el color.
UMBRAL_ALPHA = 0.55

EXTENSIONES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")


@dataclass
class ResultadoVector:
    """Que se hizo con un logo, para poder explicarlo despues."""

    origen: Path
    destino: Path
    kb: float
    via: str  # "alpha" | "color"
    colores: int
    recortado: bool
    paths_fondo_quitados: int

    def resumen(self) -> str:
        rec = ", recortado" if self.recortado else ""
        fondo = f", -{self.paths_fondo_quitados} path de fondo" if self.paths_fondo_quitados else ""
        return f"{self.destino.name}: {self.kb:.0f} KB (via {self.via}, {self.colores} colores{rec}{fondo})"


def _recortar_marco(im, tolerancia: int = 18):
    """Saca el marco plano que rodea al logo. Devuelve (imagen, si_recorto).

    Ojo: solo se aplica cuando el marco es realmente un sobrante. Si el fondo
    oscuro es parte del logo (un lockup blanco sobre negro), recortarlo invierte
    la lectura; por eso el llamador puede desactivarlo.
    """
    from PIL import Image, ImageChops

    fondo = Image.new("RGB", im.size, im.convert("RGB").getpixel((0, 0)))
    dif = ImageChops.difference(im.convert("RGB"), fondo).convert("L")
    caja = dif.point(lambda p: 255 if p > tolerancia else 0).getbbox()
    if caja and caja != (0, 0, im.size[0], im.size[1]):
        return im.crop(caja), True
    return im, False


def _escalar(im):
    from PIL import Image

    w, h = im.size
    if max(w, h) >= LADO_MINIMO:
        return im
    k = LADO_MINIMO / max(w, h)
    return im.resize((int(w * k), int(h * k)), Image.LANCZOS)


def _desde_alpha(im):
    """Figura = canal alpha. Devuelve RGB negro-sobre-blanco."""
    from PIL import Image

    alpha = im.split()[-1]
    caja = alpha.getbbox()
    if caja:
        im = im.crop(caja)
        alpha = im.split()[-1]
    mascara = alpha.point(lambda p: 0 if p > 60 else 255)
    return Image.merge("RGB", (mascara, mascara, mascara))


def _posterizar(im, colores: int):
    from PIL import Image

    return im.quantize(colors=colores, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")


_PATH_RE = re.compile(r'<path[^>]*?fill="(#[0-9a-fA-F]{6})"[^>]*?/>')


def _quitar_fondo(svg: str, colores_fondo: set[str]) -> tuple[str, int]:
    """Elimina los paths cuyo fill es un color de fondo -> SVG transparente.

    vtracer emite un path por region de color y el fondo es uno mas. Si no se
    quita, el logo llega con un rectangulo solido detras y hay que recortarlo a
    mano en Illustrator, que es justo lo que este modulo evita.
    """
    # vtracer no emite el fondo como un solo path: lo parte en varios. Quitar
    # solo el primero dejaba el rectangulo blanco igual. Pero quitarlos TODOS
    # por color borra partes del logo del mismo color (el texto calado en blanco
    # dentro de un circulo negro desaparecia y el SVG quedaba casi vacio).
    #
    # Por eso: se quitan todos y se mide. Si el archivo pierde demasiado, era el
    # logo y no el fondo, y se cae a quitar solo el primero.
    def _sub(agresivo: bool) -> tuple[str, int]:
        n = 0
        vistos: set[str] = set()

        def _r(m: re.Match) -> str:
            nonlocal n
            color = m.group(1).lower()
            if color not in colores_fondo:
                return m.group(0)
            if not agresivo and color in vistos:
                return m.group(0)
            vistos.add(color)
            n += 1
            return ""

        return _PATH_RE.sub(_r, svg), n

    completo, n_completo = _sub(True)
    if len(completo) >= len(svg) * 0.35:
        return completo, n_completo
    return _sub(False)


def _hex_de(px) -> str:
    return "#{:02x}{:02x}{:02x}".format(*px[:3])


def vectorizar(
    origen: str | Path,
    destino: str | Path | None = None,
    *,
    colores: int = 4,
    recortar: bool = True,
    fondo_transparente: bool = True,
) -> ResultadoVector:
    """Convierte un logo raster a SVG limpio.

    `recortar=False` para logos donde el fondo oscuro es parte de la pieza
    (un lockup blanco sobre negro): recortarlo invierte la lectura.
    """
    from PIL import Image
    import vtracer

    origen = Path(origen)
    if not origen.is_file():
        raise FileNotFoundError(f"no existe: {origen}")
    destino = Path(destino) if destino else origen.with_suffix(".svg")
    destino.parent.mkdir(parents=True, exist_ok=True)

    im = Image.open(origen)
    via = "color"
    recorto = False

    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        datos = list(rgba.split()[-1].getdata())
        transparencia = sum(1 for p in datos if p < 20) / max(1, len(datos))
        if transparencia >= UMBRAL_ALPHA:
            im = _desde_alpha(rgba)
            via, recorto = "alpha", True
        else:
            im = rgba.convert("RGB")
    else:
        im = im.convert("RGB")

    if via == "color":
        if recortar:
            im, recorto = _recortar_marco(im)
        im = _posterizar(im, colores)

    im = _escalar(im)

    # Colores de fondo a descartar: los de las cuatro esquinas ya posterizadas.
    w, h = im.size
    colores_fondo = {
        _hex_de(im.getpixel(p))
        for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
    }

    tmp = destino.with_suffix(".tmp.png")
    quitados = 0
    try:
        im.save(tmp)
        vtracer.convert_image_to_svg_py(
            str(tmp), str(destino),
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=10,
            color_precision=8,
            layer_difference=24,
            corner_threshold=60,
            length_threshold=4.0,
            splice_threshold=45,
        )
        if fondo_transparente:
            svg = destino.read_text(encoding="utf-8")
            svg, quitados = _quitar_fondo(svg, colores_fondo)
            destino.write_text(svg, encoding="utf-8")
    finally:
        tmp.unlink(missing_ok=True)

    return ResultadoVector(
        origen=origen,
        destino=destino,
        kb=destino.stat().st_size / 1024,
        via=via,
        colores=colores,
        recortado=recorto,
        paths_fondo_quitados=quitados,
    )


def vectorizar_lote(
    carpeta: str | Path,
    salida: str | Path | None = None,
    **kwargs,
) -> list[ResultadoVector]:
    """Vectoriza todos los raster de una carpeta. Los `.svg` de origen se ignoran
    (ya son vectoriales: copiarlos es mejor que retrazarlos)."""
    carpeta = Path(carpeta)
    salida = Path(salida) if salida else carpeta / "svg"
    salida.mkdir(parents=True, exist_ok=True)
    res: list[ResultadoVector] = []
    for f in sorted(carpeta.iterdir()):
        if f.suffix.lower() not in EXTENSIONES:
            continue
        res.append(vectorizar(f, salida / f"{f.stem}.svg", **kwargs))
    return res
